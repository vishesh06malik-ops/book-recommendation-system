"""Module 2 — Recommendation Engine (basic, pure Python).

How it works (see docs/algorithm.md for a worked example):

    Selected book
        -> extract features (sets of keywords, genres, authors, title words)
        -> compare with every other book (Jaccard similarity of the sets)
        -> combine the parts with the weights in config.RECOMMENDER_WEIGHTS
        -> remove the selected book, other editions of it and duplicates
        -> sort by score
        -> return the top N, each with a human-readable explanation

No machine-learning library is used: only sets, dictionaries, loops,
functions and sorting.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Iterable, Optional

from src import config
from src.models.book import Book
from src.search.search_engine import compact
from src.utils.helpers import jaccard_similarity, normalize_text, tokenize

logger = logging.getLogger(__name__)


@dataclass
class Recommendation:
    """One recommended book, its score (0-1) and why it was recommended."""

    book: Book
    score: float
    components: dict[str, float] = field(default_factory=dict)
    reasons: list[str] = field(default_factory=list)


def extract_features(book: Book) -> dict:
    """Turn a book into sets that can be compared.

    Sets are ideal: 'what do two books have in common?' is simply the
    intersection (a & b), and 'everything either has' is the union (a | b).
    """
    rating_signal = 0.0
    if book.rating is not None:
        rating_signal = min(1.0, max(0.0, (book.rating - 1) / 4))  # 1..5 stars -> 0..1
    return {
        "keywords": {normalize_text(k) for k in book.keywords},
        "genres": set(book.categories),
        "authors": {compact(name) for name in book.authors if compact(name)},
        "title_words": tokenize(book.title),
        "rating": rating_signal,
    }


def edition_key(book: Book) -> tuple[str, str]:
    """Books with the same normalised title and first author are treated as the same work."""
    first_author = compact(book.authors[0]) if book.authors else ""
    return normalize_text(book.title), first_author


def compare_features(source: dict, target: dict) -> dict[str, float]:
    """Similarity of two books per component, each a number from 0 to 1."""
    return {
        "keywords": jaccard_similarity(source["keywords"], target["keywords"]),
        "genre": jaccard_similarity(source["genres"], target["genres"]),
        "author": 1.0 if source["authors"] & target["authors"] else 0.0,
        "title": jaccard_similarity(source["title_words"], target["title_words"]),
        "rating": target["rating"],
    }


def weighted_score(components: dict[str, float], weights: dict[str, float]) -> float:
    """final_score = sum(weight x component)."""
    return sum(weights[name] * components.get(name, 0.0) for name in weights)


def explain(source: Book, target: Book, components: dict[str, float]) -> list[str]:
    """Build plain-English reasons from the components that actually contributed."""
    reasons = []
    threshold = config.EXPLANATION_THRESHOLD
    if components.get("author"):
        shared = [a for a in target.authors if compact(a) in {compact(x) for x in source.authors}]
        reasons.append(f"Same author: {', '.join(shared)}")
    if components.get("genre", 0) >= threshold:
        shared = [g for g in target.categories if g in source.categories]
        reasons.append(f"Same genre: {', '.join(shared)}")
    if components.get("keywords", 0) >= threshold:
        source_keys = {normalize_text(k) for k in source.keywords}
        shared = [k for k in target.keywords if normalize_text(k) in source_keys]
        reasons.append(f"Shared themes: {', '.join(shared[:5])}")
    if components.get("title", 0) >= threshold:
        shared = sorted(tokenize(source.title) & tokenize(target.title))
        reasons.append(f"Similar title words: {', '.join(shared)} (possibly the same series)")
    if target.rating is not None and target.rating >= 4.0:
        reasons.append(f"Highly rated by readers ({target.rating:.2f}/5)")
    return reasons or ["Some overlap in genres or themes"]


def select_top(candidates: Iterable[Recommendation], n: int, excluded_keys: set) -> list[Recommendation]:
    """Sort candidates and keep the best `n`, skipping duplicate works.

    Sort order: score (high first), then external rating count, then id,
    so equal scores always come out in the same order.
    """
    ordered = sorted(candidates, key=lambda r: (-r.score, -(r.book.rating_count or 0), r.book.id))
    chosen: list[Recommendation] = []
    seen_keys = set(excluded_keys)
    for rec in ordered:
        key = edition_key(rec.book)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        chosen.append(rec)
        if len(chosen) == n:
            break
    return chosen


class BasicRecommender:
    """Content-based recommender built from Python sets and weighted scores."""

    name = "Basic (weighted similarity)"

    def __init__(self, books: list[Book], weights: Optional[dict[str, float]] = None):
        self.books = books
        self.weights = weights or config.RECOMMENDER_WEIGHTS
        # Features are extracted ONCE here, not on every recommendation request.
        self.features: dict[str, dict] = {book.id: extract_features(book) for book in books}
        self.by_id = {book.id: book for book in books}

    def similarity(self, source: Book, target: Book) -> tuple[float, dict[str, float]]:
        """Score how similar `target` is to `source`. Returns (score, components)."""
        components = compare_features(self._features_of(source), self._features_of(target))
        return weighted_score(components, self.weights), components

    def _features_of(self, book: Book) -> dict:
        # Books from outside the dataset (e.g. Google Books) are handled too.
        return self.features.get(book.id) or extract_features(book)

    def recommend(self, book: Book, n: int = config.DEFAULT_RECOMMENDATION_COUNT,
                  exclude_ids: Optional[set[str]] = None) -> list[Recommendation]:
        """Top-n books similar to `book`, best first.

        Excludes: the book itself, other editions of it, any id in
        `exclude_ids`, and books whose only similarity is their rating.
        Fewer than n results are returned if not enough books are similar.
        """
        if n <= 0:
            return []
        exclude_ids = set(exclude_ids or ()) | {book.id}
        source = self._features_of(book)
        rating_weight = self.weights.get("rating", 0)

        candidates = []
        for other in self.books:
            if other.id in exclude_ids:
                continue
            components = compare_features(source, self.features[other.id])
            score = weighted_score(components, self.weights)
            content_score = score - rating_weight * components["rating"]
            if content_score < config.MIN_SIMILARITY_SCORE:
                continue  # rating alone is not a reason to recommend
            candidates.append(Recommendation(other, round(score, 4), components))

        top = select_top(candidates, n, excluded_keys={edition_key(book)})
        for rec in top:
            rec.reasons = explain(book, rec.book, rec.components)
        return top
