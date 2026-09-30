"""The Book model: one clear, typed representation used by every module.

Both the local CSV dataset and the Google Books API are converted into
Book objects, so the rest of the program never deals with raw CSV rows or
raw API JSON.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.utils.helpers import display_value, format_rating, format_year


@dataclass(frozen=True)
class Book:
    """A single book.

    `frozen=True` makes a Book read-only after creation, so no module can
    accidentally change the shared dataset. Multi-valued fields use tuples
    (immutable lists) for the same reason.

    Missing information is stored as an empty value ("", (), None) and is
    shown to users as "Not available".
    """

    id: str
    title: str
    authors: tuple[str, ...] = ()
    isbn: str = ""
    description: str = ""
    categories: tuple[str, ...] = ()  # broad genres, e.g. ("Fantasy", "Young Adult")
    keywords: tuple[str, ...] = ()    # descriptive reader tags, e.g. ("magic", "dragons")
    publisher: str = ""
    published_year: Optional[int] = None
    language: str = ""
    rating: Optional[float] = None       # EXTERNAL average rating from the dataset/API
    rating_count: Optional[int] = None   # how many people gave the external rating
    cover_url: str = ""
    source: str = "local"

    # -- convenient text versions for display ---------------------------------
    @property
    def author_text(self) -> str:
        return display_value(self.authors)

    @property
    def genre_text(self) -> str:
        return display_value(self.categories)

    @property
    def year_text(self) -> str:
        return format_year(self.published_year)

    @property
    def rating_text(self) -> str:
        return format_rating(self.rating, self.rating_count)

    def short_label(self) -> str:
        """One-line label used in numbered lists: 'Title — Author (Year)'."""
        first_author = self.authors[0] if self.authors else display_value(None)
        extra_authors = " et al." if len(self.authors) > 1 else ""
        year = f" ({self.year_text})" if self.published_year is not None else ""
        return f"{self.title} — {first_author}{extra_authors}{year}"

    def to_display_dict(self) -> dict[str, str]:
        """All fields as user-friendly strings (used by the CLI and Streamlit)."""
        return {
            "Title": display_value(self.title),
            "Author": self.author_text,
            "Genre": self.genre_text,
            "Keywords": display_value(self.keywords),
            "Year": self.year_text,
            "External rating": self.rating_text,
            "Publisher": display_value(self.publisher),
            "ISBN": display_value(self.isbn),
            "Language": display_value(self.language),
            "Source": display_value(self.source),
        }
