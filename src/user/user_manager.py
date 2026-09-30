"""The user's personal data: favourites, personal ratings, preferred genres and history."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from src import config
from src.storage.storage_manager import load_json, save_json

logger = logging.getLogger(__name__)


class InvalidRatingError(ValueError):
    """Raised when a personal rating is not a whole number from 1 to 5."""


@dataclass
class UserProfile:
    """Everything BookWise remembers about the user.

    Data structure choices:
    * favourites      -> list  (keeps the order books were added)
    * ratings         -> dict  (book id -> 1..5, one rating per book)
    * preferred_genres-> set   (a genre can only be preferred once)
    * history         -> list  (most recently viewed first)
    """

    favourites: list[str] = field(default_factory=list)
    ratings: dict[str, int] = field(default_factory=dict)
    preferred_genres: set[str] = field(default_factory=set)
    history: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        """Convert to plain JSON-friendly types (JSON has no sets, so sort into a list)."""
        return {
            "favourites": list(self.favourites),
            "ratings": dict(self.ratings),
            "preferred_genres": sorted(self.preferred_genres),
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, data) -> "UserProfile":
        """Build a profile from loaded JSON, ignoring anything with the wrong type.

        The file could have been edited by hand, so nothing is trusted blindly.
        """
        if not isinstance(data, dict):
            return cls()
        low, high = config.RATING_SCALE

        def as_list(value) -> list:
            return value if isinstance(value, list) else []

        favourites = [str(x) for x in as_list(data.get("favourites")) if isinstance(x, (str, int))]
        ratings = {}
        raw_ratings = data.get("ratings", {})
        if isinstance(raw_ratings, dict):
            for book_id, value in raw_ratings.items():
                if isinstance(value, int) and not isinstance(value, bool) and low <= value <= high:
                    ratings[str(book_id)] = value
        genres = {str(g) for g in as_list(data.get("preferred_genres")) if isinstance(g, str) and g.strip()}
        history = [str(x) for x in as_list(data.get("history")) if isinstance(x, (str, int))]

        return cls(
            favourites=list(dict.fromkeys(favourites)),  # drop duplicates, keep order
            ratings=ratings,
            preferred_genres=genres,
            history=list(dict.fromkeys(history))[: config.MAX_HISTORY_ITEMS],
        )


class UserManager:
    """Changes the user profile and saves every change to disk immediately."""

    def __init__(self, path: Path = config.USER_DATA_PATH, autosave: bool = True):
        self.path = Path(path)
        self.autosave = autosave
        self.profile = UserProfile.from_dict(load_json(self.path, default={}))

    def save(self) -> None:
        """Write the profile to disk (may raise StorageError)."""
        save_json(self.path, self.profile.to_dict())

    def _changed(self) -> None:
        if self.autosave:
            self.save()

    # -- favourites ------------------------------------------------------------
    def is_favourite(self, book_id: str) -> bool:
        return book_id in self.profile.favourites

    def add_favourite(self, book_id: str) -> bool:
        """Add a favourite. Returns False if it was already a favourite."""
        if self.is_favourite(book_id):
            return False
        self.profile.favourites.append(book_id)
        self._changed()
        return True

    def remove_favourite(self, book_id: str) -> bool:
        """Remove a favourite. Returns False if it was not a favourite."""
        if not self.is_favourite(book_id):
            return False
        self.profile.favourites.remove(book_id)
        self._changed()
        return True

    # -- personal ratings ------------------------------------------------------
    @staticmethod
    def validate_rating(value) -> int:
        """Accept 1-5 as int or text ('4', ' 4 '); raise InvalidRatingError otherwise."""
        low, high = config.RATING_SCALE
        if isinstance(value, bool):
            raise InvalidRatingError(f"Rating must be a whole number from {low} to {high}.")
        try:
            number = int(str(value).strip())
        except (TypeError, ValueError):
            raise InvalidRatingError(f"Rating must be a whole number from {low} to {high}.") from None
        if not low <= number <= high:
            raise InvalidRatingError(f"Rating must be between {low} and {high}.")
        return number

    def rate_book(self, book_id: str, value) -> int:
        """Store the user's own rating (replaces an earlier one). Returns the stored rating."""
        rating = self.validate_rating(value)
        self.profile.ratings[book_id] = rating
        self._changed()
        return rating

    def get_rating(self, book_id: str):
        return self.profile.ratings.get(book_id)

    def remove_rating(self, book_id: str) -> bool:
        if book_id not in self.profile.ratings:
            return False
        del self.profile.ratings[book_id]
        self._changed()
        return True

    # -- genre preferences -----------------------------------------------------
    def set_preferred_genres(self, genres: Iterable[str]) -> None:
        self.profile.preferred_genres = {g.strip() for g in genres if g and g.strip()}
        self._changed()

    def toggle_genre(self, genre: str) -> bool:
        """Add the genre if missing, remove it if present. Returns True if now preferred."""
        if genre in self.profile.preferred_genres:
            self.profile.preferred_genres.discard(genre)
            now_preferred = False
        else:
            self.profile.preferred_genres.add(genre)
            now_preferred = True
        self._changed()
        return now_preferred

    # -- history ---------------------------------------------------------------
    def record_view(self, book_id: str) -> None:
        """Move the book to the front of the history (no duplicates, limited length)."""
        history = [b for b in self.profile.history if b != book_id]
        history.insert(0, book_id)
        self.profile.history = history[: config.MAX_HISTORY_ITEMS]
        self._changed()

    # -- signals used by personalisation ---------------------------------------
    def disliked_ids(self) -> set[str]:
        return {b for b, r in self.profile.ratings.items() if r <= config.DISLIKED_RATING_THRESHOLD}

    def liked_ids(self) -> set[str]:
        """Favourites plus highly rated books, minus anything the user rated low."""
        highly_rated = {b for b, r in self.profile.ratings.items() if r >= config.LIKED_RATING_THRESHOLD}
        return (set(self.profile.favourites) | highly_rated) - self.disliked_ids()

    def recent_history(self) -> list[str]:
        return self.profile.history[: config.HISTORY_ITEMS_USED]

    def reset(self) -> None:
        """Forget everything (used by the 'clear profile' option)."""
        self.profile = UserProfile()
        self._changed()
