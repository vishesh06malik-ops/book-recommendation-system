"""Loading the book dataset from CSV and giving fast access to it."""

from __future__ import annotations

import csv
import logging
from pathlib import Path
from typing import Iterable, Optional

from src import config
from src.models.book import Book

logger = logging.getLogger(__name__)


class DatasetError(Exception):
    """Raised when the dataset cannot be used at all (missing file, wrong columns, no rows).

    A custom exception lets the CLI show one friendly message instead of a stack trace.
    """


# ---------------------------------------------------------------------------
# Converting text cells into proper Python values
# ---------------------------------------------------------------------------
def _split_multi(value: Optional[str]) -> tuple[str, ...]:
    """'Fantasy|Young Adult' -> ('Fantasy', 'Young Adult'); '' -> ()."""
    if not value:
        return ()
    parts = [part.strip() for part in value.split(config.MULTI_VALUE_SEPARATOR)]
    # dict.fromkeys removes duplicates while keeping order
    return tuple(dict.fromkeys(part for part in parts if part))


def _to_int(value: Optional[str]) -> Optional[int]:
    try:
        return int(float(value)) if value not in (None, "") else None
    except ValueError:
        return None


def _to_float(value: Optional[str]) -> Optional[float]:
    try:
        number = float(value) if value not in (None, "") else None
    except ValueError:
        return None
    if number is None or number != number:  # reject NaN
        return None
    return number


def row_to_book(row: dict[str, str]) -> Book:
    """Convert one CSV row (a dictionary of strings) into a Book.

    Raises ValueError when a required value is empty.
    """
    book_id = (row.get("id") or "").strip()
    title = (row.get("title") or "").strip()
    if not book_id or not title:
        raise ValueError("row has no id or title")

    rating = _to_float(row.get("rating"))
    if rating is not None and not 0 <= rating <= 5:
        rating = None  # out-of-range ratings are treated as missing

    return Book(
        id=book_id,
        title=title,
        authors=_split_multi(row.get("authors")),
        isbn=(row.get("isbn") or "").strip(),
        description=(row.get("description") or "").strip(),
        categories=_split_multi(row.get("categories")),
        keywords=_split_multi(row.get("keywords")),
        publisher=(row.get("publisher") or "").strip(),
        published_year=_to_int(row.get("published_year")),
        language=(row.get("language") or "").strip(),
        rating=rating,
        rating_count=_to_int(row.get("rating_count")),
        cover_url=(row.get("cover_url") or "").strip(),
        source=(row.get("source") or "local").strip(),
    )


def load_books(path: Path = config.DATASET_PATH) -> list[Book]:
    """Read the dataset CSV and return a list of Book objects.

    * Rows that cannot be converted are skipped (and counted in the log).
    * A repeated id keeps the first row only.
    * Raises DatasetError if the file is missing, unreadable, lacks
      required columns, or contains no usable rows.
    """
    path = Path(path)
    if not path.exists():
        raise DatasetError(
            f"Dataset not found at {path}. Run 'python scripts/prepare_dataset.py' first "
            "(see data/README.md)."
        )

    books: list[Book] = []
    seen_ids: set[str] = set()
    skipped = duplicates = 0
    try:
        # utf-8-sig also accepts files saved by Excel (which adds an invisible BOM)
        with open(path, newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            columns = set(reader.fieldnames or [])
            missing = [name for name in config.REQUIRED_COLUMNS if name not in columns]
            if missing:
                raise DatasetError(f"Dataset is missing required column(s): {', '.join(missing)}")

            for row in reader:
                try:
                    book = row_to_book(row)
                except (ValueError, AttributeError):
                    skipped += 1
                    continue
                if book.id in seen_ids:
                    duplicates += 1
                    continue
                seen_ids.add(book.id)
                books.append(book)
    except (OSError, UnicodeDecodeError, csv.Error) as error:
        logger.error("Could not read dataset %s: %s", path, error)
        raise DatasetError(f"The dataset file could not be read ({type(error).__name__}).") from error

    if skipped or duplicates:
        logger.warning("Dataset %s: skipped %d malformed and %d duplicate rows", path, skipped, duplicates)
    if not books:
        raise DatasetError("The dataset contains no usable books.")
    logger.info("Loaded %d books from %s", len(books), path)
    return books


class BookCatalog:
    """The loaded collection of books with quick look-ups.

    Why a class? The catalogue has data (the books) plus the indexes built
    from them, and several operations that use both. Keeping them together
    means the indexes are built once and always match the book list.
    """

    def __init__(self, books: Iterable[Book]):
        self.books: list[Book] = list(books)
        # Dictionary index: find a book by id in constant time instead of a loop.
        self._by_id: dict[str, Book] = {book.id: book for book in self.books}
        # Genre index: genre name -> list of books in that genre.
        self._by_genre: dict[str, list[Book]] = {}
        for book in self.books:
            for genre in book.categories:
                self._by_genre.setdefault(genre, []).append(book)

    @classmethod
    def from_csv(cls, path: Path = config.DATASET_PATH) -> "BookCatalog":
        return cls(load_books(path))

    def __len__(self) -> int:
        return len(self.books)

    def get(self, book_id: str) -> Optional[Book]:
        return self._by_id.get(str(book_id))

    def get_many(self, book_ids: Iterable[str]) -> list[Book]:
        """Books for the given ids, silently ignoring unknown ids."""
        return [self._by_id[book_id] for book_id in book_ids if book_id in self._by_id]

    def genres(self) -> list[tuple[str, int]]:
        """(genre, number_of_books) pairs, most common first."""
        pairs = [(genre, len(books)) for genre, books in self._by_genre.items()]
        return sorted(pairs, key=lambda pair: (-pair[1], pair[0]))

    def books_in_genre(self, genre: str) -> list[Book]:
        """Books of one genre, most-rated first (a simple popularity order)."""
        books = self._by_genre.get(genre, [])
        return sorted(books, key=lambda b: (-(b.rating_count or 0), b.title))
