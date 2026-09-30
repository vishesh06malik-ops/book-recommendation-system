"""Module 1 — Book Search & Discovery.

Searching 10,000 books with a simple loop takes a few milliseconds, so no
database or search library is needed. To keep each search fast, the text
that is searched is prepared once (lower-cased, punctuation removed) when
the SearchEngine is created, instead of on every search.
"""

from __future__ import annotations

from typing import Callable, Optional

from src import config
from src.models.book import Book
from src.utils.helpers import normalize_text, tokenize

# The search modes offered to the user. A tuple of (key, label) pairs:
# fixed data that should never change while the program runs.
SEARCH_MODES = (
    ("title", "Title"),
    ("author", "Author"),
    ("genre", "Genre"),
    ("isbn", "ISBN"),
    ("keyword", "Keyword"),
)


def compact(text: Optional[str]) -> str:
    """Keep only letters and digits: 'J.K. Rowling' -> 'jkrowling'.

    This lets 'jk rowling', 'J. K. Rowling' and 'j.k.rowling' all match.
    """
    return "".join(ch for ch in (text or "").lower() if ch.isalnum())


def normalize_isbn(text: str) -> str:
    """Remove spaces/hyphens and convert an ISBN-13 starting with 978 into ISBN-10.

    The dataset stores ISBN-10, but modern books print ISBN-13 on the cover.
    Every '978' ISBN-13 has an ISBN-10 twin: drop '978' and the last digit,
    then recompute the ISBN-10 check digit.
    """
    value = "".join(ch for ch in text.upper() if ch.isdigit() or ch == "X")
    if len(value) == 13 and value.startswith("978"):
        core = value[3:12]
        total = sum(int(digit) * (10 - i) for i, digit in enumerate(core))
        check = (11 - total % 11) % 11
        value = core + ("X" if check == 10 else str(check))
    elif 0 < len(value) < 10:
        value = value.zfill(10)  # a leading zero may have been lost
    return value


class SearchEngine:
    """Searches a list of books by title, author, genre, ISBN or keyword."""

    def __init__(self, books: list[Book]):
        self.books = books
        # Pre-computed search data for every book (a list of dictionaries).
        self._index = [
            {
                "book": book,
                "title": normalize_text(book.title),
                "title_compact": compact(book.title),
                "title_words": tokenize(book.title, remove_stopwords=False),
                "authors": [compact(name) for name in book.authors],
                "genres": [normalize_text(g) for g in book.categories],
                "all_words": tokenize(" ".join([
                    book.title, " ".join(book.authors), " ".join(book.categories),
                    " ".join(book.keywords), book.description, book.publisher,
                ]), remove_stopwords=False),
            }
            for book in books
        ]

    # -- public entry point ------------------------------------------------------
    def search(self, query: str, mode: str = "title", limit: int = config.MAX_SEARCH_RESULTS) -> list[Book]:
        """Return up to `limit` matching books, best matches first.

        An empty query or unknown mode returns an empty list (never an error),
        so the caller does not have to guard every call.
        """
        query = normalize_text(query)
        if not query:
            return []
        # A dictionary that maps each mode to the function that scores one entry.
        scorers: dict[str, Callable[[dict, str], float]] = {
            "title": self._score_title,
            "author": self._score_author,
            "genre": self._score_genre,
            "isbn": self._score_isbn,
            "keyword": self._score_keyword,
        }
        scorer = scorers.get(mode)
        if scorer is None:
            return []

        if mode == "isbn":
            query = normalize_isbn(query)
        matches = []
        for entry in self._index:
            score = scorer(entry, query)
            if score > 0:
                matches.append((score, entry["book"]))

        # Best score first; among equal scores, the more widely rated book first,
        # then alphabetical, so the order is always the same (deterministic).
        matches.sort(key=lambda pair: (-pair[0], -(pair[1].rating_count or 0), pair[1].title))
        return [book for _, book in matches[:limit]]

    # -- scoring functions: return 0 for "no match", higher is better -----------
    @staticmethod
    def _score_title(entry: dict, query: str) -> float:
        title = entry["title"]
        if title == query:
            return 4
        if title.startswith(query):
            return 3
        if query in title or compact(query) in entry["title_compact"]:
            return 2
        words = tokenize(query, remove_stopwords=False)
        if words and words <= entry["title_words"]:  # every query word is in the title
            return 1
        return 0

    @staticmethod
    def _score_author(entry: dict, query: str) -> float:
        wanted = compact(query)
        best = 0
        for name in entry["authors"]:
            if name == wanted:
                best = max(best, 3)
            elif name.startswith(wanted) or name.endswith(wanted):
                best = max(best, 2)
            elif wanted in name:
                best = max(best, 1)
        return best

    @staticmethod
    def _score_genre(entry: dict, query: str) -> float:
        if query in entry["genres"]:
            return 2
        return 1 if any(query in genre for genre in entry["genres"]) else 0

    @staticmethod
    def _score_isbn(entry: dict, query: str) -> float:
        return 1 if query and entry["book"].isbn == query else 0

    @staticmethod
    def _score_keyword(entry: dict, query: str) -> float:
        """Every word of the query must appear somewhere in the book's text.
        Words found in the title count extra."""
        words = tokenize(query, remove_stopwords=True) or tokenize(query, remove_stopwords=False)
        if not words or not words <= entry["all_words"]:
            return 0
        return 1 + len(words & entry["title_words"])
