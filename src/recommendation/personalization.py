"""Module 3 — User Preferences & Personalisation.

Personalised score for a candidate book (weights in config.PERSONAL_WEIGHTS):

    score = 0.35 x genre_match       how well its genres match your preferred genres
          + 0.40 x liked_similarity  similarity to the closest book you liked
          + 0.15 x history_similarity similarity to the closest book you viewed recently
          + 0.10 x rating_signal      external rating, 1-5 stars mapped to 0-1
          - 0.30 x disliked_similarity similarity to the closest book you rated low

Every part is a number from 0 to 1, so the reasons shown to the user come
straight from the numbers that produced the ranking.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from src import config
from src.models.book import Book
from src.recommendation.basic_recommender import (
    BasicRecommender, Recommendation, compare_features, edition_key, select_top, weighted_score,
)


@dataclass
class UserSignals:
    """The parts of a user profile that influence personalised ranking."""

    preferred_genres: set[str] = field(default_factory=set)
    liked_ids: set[str] = field(default_factory=set)
    disliked_ids: set[str] = field(default_factory=set)
    history_ids: list[str] = field(default_factory=list)
    exclude_ids: set[str] = field(default_factory=set)  # already rated / favourite / viewed

    def is_empty(self) -> bool:
        return not (self.preferred_genres or self.liked_ids or self.history_ids)


def genre_match(book_genres: set[str], preferred: set[str]) -> float:
    """Share of the possible genre matches that actually match.

    Example: preferred {Psychology, Self Help}, book {Psychology, Non-fiction}
    -> 1 shared out of min(2, 2) possible = 0.5
    """
    if not book_genres or not preferred:
        return 0.0
    return len(book_genres & preferred) / min(len(book_genres), len(preferred))


class PersonalizedRecommender:
    """Ranks the whole catalogue for one user, re-using the basic recommender's features."""

    def __init__(self, basic: BasicRecommender):
        self.basic = basic
        # Content similarity uses the same weights as the basic recommender,
        # but WITHOUT the rating part (rating is added separately below).
        weights = dict(basic.weights)
        rating_weight = weights.pop("rating", 0)
        total = sum(weights.values()) or 1
        self.content_weights = {k: v / total for k, v in weights.items()}  # rescaled to sum to 1
        self._rating_weight = rating_weight

    def _content_similarity(self, source_features: dict, target_features: dict) -> float:
        return weighted_score(compare_features(source_features, target_features), self.content_weights)

    def _closest(self, features: dict, reference_books: list[Book]) -> tuple[float, Optional[Book]]:
        """The reference book most similar to `features`, and that similarity."""
        best_score, best_book = 0.0, None
        for ref in reference_books:
            score = self._content_similarity(self.basic.features[ref.id], features)
            if score > best_score:
                best_score, best_book = score, ref
        return best_score, best_book

    def recommend(self, signals: UserSignals, n: int = config.DEFAULT_RECOMMENDATION_COUNT) -> list[Recommendation]:
        """Top-n personalised recommendations with reasons. Empty if the user has no signals."""
        if n <= 0 or signals.is_empty():
            return []
        w = config.PERSONAL_WEIGHTS
        by_id = self.basic.by_id
        liked = [by_id[i] for i in sorted(signals.liked_ids) if i in by_id]
        disliked = [by_id[i] for i in sorted(signals.disliked_ids) if i in by_id]
        history = [by_id[i] for i in signals.history_ids[: config.HISTORY_ITEMS_USED]
                   if i in by_id and i not in signals.liked_ids]
        excluded = signals.exclude_ids | signals.liked_ids | signals.disliked_ids | set(signals.history_ids)

        candidates = []
        for book in self.basic.books:
            if book.id in excluded:
                continue
            features = self.basic.features[book.id]
            parts = {
                "genre": genre_match(features["genres"], signals.preferred_genres),
                "liked": 0.0, "history": 0.0, "disliked": 0.0,
                "rating": features["rating"],
            }
            parts["liked"], liked_book = self._closest(features, liked)
            parts["history"], history_book = self._closest(features, history)
            parts["disliked"], _ = self._closest(features, disliked)

            personal = w["genre"] * parts["genre"] + w["liked"] * parts["liked"] + w["history"] * parts["history"]
            if personal < config.MIN_SIMILARITY_SCORE:
                continue  # nothing personal connects this book to the user
            score = personal + w["rating"] * parts["rating"] - w["disliked"] * parts["disliked"]
            rec = Recommendation(book, round(max(score, 0.0), 4), parts)
            rec.reasons = self._explain(book, parts, signals, liked_book, history_book)
            candidates.append(rec)

        return select_top(candidates, n, excluded_keys={edition_key(b) for b in liked + disliked})

    @staticmethod
    def _explain(book: Book, parts: dict, signals: UserSignals,
                 liked_book: Optional[Book], history_book: Optional[Book]) -> list[str]:
        threshold = config.EXPLANATION_THRESHOLD
        reasons = []
        shared_genres = [g for g in book.categories if g in signals.preferred_genres]
        if shared_genres:
            reasons.append(f"You prefer {', '.join(shared_genres)}")
        if liked_book and parts["liked"] >= threshold:
            reasons.append(f"Similar to \"{liked_book.title}\", which you liked")
        if history_book and parts["history"] >= threshold:
            reasons.append(f"Similar to \"{history_book.title}\", which you viewed recently")
        if book.rating is not None and book.rating >= 4.0:
            reasons.append(f"Highly rated by readers ({book.rating:.2f}/5)")
        if parts["disliked"] >= threshold:
            reasons.append("Ranked a little lower: resembles a book you rated low")
        return reasons or ["Some overlap with your preferences"]
