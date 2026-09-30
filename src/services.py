"""Application service layer: the single entry point used by BOTH interfaces.

    CLI (src/cli/cli_app.py)  ─┐
                               ├──►  BookWiseService  ──► search / recommendation / user / storage / api
    Streamlit (app.py)        ─┘

Because all logic lives here and in the modules below it, the CLI and the
Streamlit app can never disagree about how search or recommendations work.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

from src import config
from src.api import google_books
from src.data.data_manager import BookCatalog
from src.models.book import Book
from src.recommendation import content_recommender
from src.recommendation.basic_recommender import BasicRecommender, Recommendation
from src.recommendation.personalization import PersonalizedRecommender, UserSignals
from src.search.search_engine import SearchEngine
from src.user.user_manager import UserManager

logger = logging.getLogger(__name__)

ENGINE_BASIC = "basic"
ENGINE_ADVANCED = "advanced"


class BookWiseService:
    """Loads everything once and offers every feature as a simple method."""

    def __init__(self, dataset_path: Path = config.DATASET_PATH, user_data_path: Path = config.USER_DATA_PATH):
        self.catalog = BookCatalog.from_csv(dataset_path)  # may raise DatasetError
        self.search_engine = SearchEngine(self.catalog.books)
        self.basic = BasicRecommender(self.catalog.books)
        self.personal = PersonalizedRecommender(self.basic)
        self.users = UserManager(user_data_path)
        self._advanced = None                       # built only when first needed
        self._external_books: dict[str, Book] = {}  # books found through Google Books

    # -- books -------------------------------------------------------------------
    def get_book(self, book_id: str) -> Optional[Book]:
        return self.catalog.get(book_id) or self._external_books.get(book_id)

    def search(self, query: str, mode: str = "title", limit: int = config.MAX_SEARCH_RESULTS) -> list[Book]:
        return self.search_engine.search(query, mode, limit)

    def genres(self) -> list[tuple[str, int]]:
        return self.catalog.genres()

    def genre_names(self) -> list[str]:
        return sorted(name for name, _ in self.catalog.genres())

    def books_in_genre(self, genre: str) -> list[Book]:
        return self.catalog.books_in_genre(genre)

    def view_book(self, book: Book) -> None:
        """Remember that the user opened this book (used by personalisation)."""
        if self.catalog.get(book.id):  # only local books can be recommended later
            self.users.record_view(book.id)

    # -- recommendations ---------------------------------------------------------
    @property
    def advanced_available(self) -> bool:
        return content_recommender.ADVANCED_AVAILABLE

    def _advanced_recommender(self):
        """Build the TF-IDF model the first time it is requested, then reuse it (cache)."""
        if self._advanced is None and self.advanced_available:
            try:
                self._advanced = content_recommender.AdvancedContentRecommender(self.catalog.books)
            except (ValueError, MemoryError, RuntimeError) as error:
                logger.error("Could not build the TF-IDF model: %s", error)
                return None
        return self._advanced

    def recommend(self, book: Book, n: int = config.DEFAULT_RECOMMENDATION_COUNT,
                  engine: str = ENGINE_BASIC) -> tuple[list[Recommendation], str]:
        """Similar books. Returns (recommendations, name of the engine actually used).

        If the advanced engine is requested but unavailable, the basic one is used.
        """
        recommender = self.basic
        if engine == ENGINE_ADVANCED:
            recommender = self._advanced_recommender() or self.basic
        try:
            return recommender.recommend(book, n), recommender.name
        except Exception:  # noqa: BLE001 - last line of defence; the user sees an empty list
            logger.exception("Unexpected error while recommending for book %s", book.id)
            return [], recommender.name

    def personalized(self, n: int = config.DEFAULT_RECOMMENDATION_COUNT) -> list[Recommendation]:
        users = self.users
        profile = users.profile
        signals = UserSignals(
            preferred_genres=set(profile.preferred_genres),
            liked_ids=users.liked_ids(),
            disliked_ids=users.disliked_ids(),
            history_ids=users.recent_history(),
            exclude_ids=set(profile.ratings) | set(profile.favourites),
        )
        try:
            return self.personal.recommend(signals, n)
        except Exception:  # noqa: BLE001
            logger.exception("Unexpected error in personalised recommendations")
            return []

    def has_personal_signals(self) -> bool:
        profile = self.users.profile
        return bool(profile.preferred_genres or profile.favourites or profile.ratings or profile.history)

    # -- user features (thin wrappers so interfaces only talk to the service) ----
    def favourite_books(self) -> list[Book]:
        return [b for b in (self.get_book(i) for i in self.users.profile.favourites) if b]

    def rated_books(self) -> list[tuple[Book, int]]:
        pairs = []
        for book_id, rating in self.users.profile.ratings.items():
            book = self.get_book(book_id)
            if book:
                pairs.append((book, rating))
        return sorted(pairs, key=lambda pair: (-pair[1], pair[0].title))

    def history_books(self, limit: int = 10) -> list[Book]:
        return self.catalog.get_many(self.users.profile.history[:limit])

    # -- optional Google Books ----------------------------------------------------
    def live_search(self, query: str) -> list[Book]:
        """Search Google Books. Raises google_books.GoogleBooksUnavailable on any failure."""
        books = google_books.search_google_books(query)
        for book in books:
            self._external_books[book.id] = book  # so favourites/details work for them this session
        return books
