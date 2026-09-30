"""Advanced content-based recommender: TF-IDF + cosine similarity (optional).

This is an ENHANCEMENT. It needs scikit-learn; if scikit-learn is not
installed, `ADVANCED_AVAILABLE` is False and BookWise simply uses the basic
recommender instead.

Idea in one paragraph
---------------------
Every book becomes one piece of text (title, authors, genres, keywords,
description). TF-IDF turns that text into a list of numbers (a vector):
a word gets a HIGH number if it appears in this book but in FEW other
books ("vampires"), and a LOW number if it is everywhere ("fiction").
Two books are similar when their vectors point in a similar direction,
which is measured by cosine similarity:

    cos(A, B) = (A · B) / (||A|| x ||B||)       (0 = unrelated, 1 = identical)
"""

from __future__ import annotations

import logging
from typing import Optional

from src import config
from src.models.book import Book
from src.recommendation.basic_recommender import (
    Recommendation, compare_features, edition_key, explain, extract_features, select_top,
)
from src.search.search_engine import compact

logger = logging.getLogger(__name__)

try:  # scikit-learn is optional
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    ADVANCED_AVAILABLE = True
except ImportError:  # pragma: no cover - depends on the environment
    ADVANCED_AVAILABLE = False


def book_to_document(book: Book) -> str:
    """Combine the useful text fields of a book into one string for TF-IDF.

    * Multi-word values are joined with '_' so 'Science Fiction' stays one
      token (science_fiction) instead of matching every book with 'science'.
    * Author names are compacted ('Alice Stone' -> alicestone) so books do
      not look similar just because two authors share a first name.
    * Fields are repeated according to config.TFIDF_FIELD_WEIGHTS, which is
      a simple way to make keywords count more than title words.
    """
    weights = config.TFIDF_FIELD_WEIGHTS
    fields = {
        "title": book.title,
        "authors": " ".join(compact(name) for name in book.authors),
        "categories": " ".join(g.lower().replace(" ", "_").replace("&", "and") for g in book.categories),
        "keywords": " ".join(k.lower().replace(" ", "_") for k in book.keywords),
        "description": book.description,
    }
    parts = []
    for name, text in fields.items():
        if text:
            parts.extend([text] * weights.get(name, 1))
    return " ".join(parts)


class AdvancedContentRecommender:
    """TF-IDF recommender. The matrix is built once and reused for every request."""

    name = "Advanced (TF-IDF + cosine similarity)"

    def __init__(self, books: list[Book]):
        if not ADVANCED_AVAILABLE:
            raise RuntimeError("scikit-learn is not installed")
        self.books = books
        self._position = {book.id: i for i, book in enumerate(books)}
        self._features = {book.id: extract_features(book) for book in books}  # for explanations
        self.vectorizer = TfidfVectorizer(stop_words="english", max_features=config.TFIDF_MAX_FEATURES,
                                          sublinear_tf=True)
        self.matrix = self.vectorizer.fit_transform(book_to_document(b) for b in books)
        logger.info("TF-IDF matrix built: %d books x %d terms", *self.matrix.shape)

    def _vector_for(self, book: Book):
        position = self._position.get(book.id)
        if position is not None:
            return self.matrix[position]
        return self.vectorizer.transform([book_to_document(book)])  # e.g. a Google Books result

    def recommend(self, book: Book, n: int = config.DEFAULT_RECOMMENDATION_COUNT,
                  exclude_ids: Optional[set[str]] = None) -> list[Recommendation]:
        if n <= 0:
            return []
        vector = self._vector_for(book)
        if vector.nnz == 0:  # the book has no usable text at all
            return []
        similarities = cosine_similarity(vector, self.matrix).ravel()
        exclude_ids = set(exclude_ids or ()) | {book.id}

        candidates = []
        for position, score in enumerate(similarities):
            other = self.books[position]
            if other.id in exclude_ids or score < config.MIN_SIMILARITY_SCORE:
                continue
            candidates.append(Recommendation(other, round(float(score), 4), {"cosine": float(score)}))

        top = select_top(candidates, n, excluded_keys={edition_key(book)})
        source_features = self._features.get(book.id) or extract_features(book)
        for rec in top:
            parts = compare_features(source_features, self._features[rec.book.id])
            reasons = [r for r in explain(book, rec.book, parts) if not r.startswith("Some overlap")]
            rec.reasons = [f"High text similarity (TF-IDF cosine = {rec.score:.2f})"] + reasons
        return top

