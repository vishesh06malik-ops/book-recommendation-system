"""Small, reusable helper functions (text processing and display formatting)."""

from __future__ import annotations

import logging
import re
from typing import Iterable, Optional

from src import config

# Very common English words that carry no meaning for matching.
# A frozenset is an immutable set: fast "in" checks and it can never be changed by accident.
STOPWORDS = frozenset({
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "into",
    "is", "it", "its", "of", "on", "or", "the", "to", "with", "vol", "volume",
    "book", "books", "part", "edition", "novel",
})

_WORD_PATTERN = re.compile(r"[a-z0-9]+")


def normalize_text(text: Optional[str]) -> str:
    """Lower-case, trim and collapse repeated whitespace: '  Atomic   HABITS ' -> 'atomic habits'."""
    if not text:
        return ""
    return " ".join(str(text).lower().split())


def tokenize(text: Optional[str], remove_stopwords: bool = True) -> set[str]:
    """Split text into a SET of lower-case words.

    A set is used because we only care WHICH words appear, not how often,
    and set operations (&, |) make overlap calculations one line long.
    Single characters and pure numbers ('1', '#2') are dropped.
    """
    words = set(_WORD_PATTERN.findall(normalize_text(text)))
    words = {word for word in words if len(word) > 1 and not word.isdigit()}
    if remove_stopwords:
        words -= STOPWORDS
    return words


def jaccard_similarity(first: set, second: set) -> float:
    """Jaccard similarity = |A ∩ B| / |A ∪ B|, a number from 0 (nothing shared) to 1 (identical)."""
    if not first or not second:
        return 0.0
    return len(first & second) / len(first | second)


def display_value(value) -> str:
    """Turn any value into user-friendly text, replacing missing values with 'Not available'.

    Handles None, empty strings, empty lists/tuples and float NaN.
    """
    if value is None:
        return config.NOT_AVAILABLE
    if isinstance(value, float) and value != value:  # NaN is the only value not equal to itself
        return config.NOT_AVAILABLE
    if isinstance(value, (list, tuple, set, frozenset)):
        items = [str(item) for item in value if str(item).strip()]
        return ", ".join(items) if items else config.NOT_AVAILABLE
    text = str(value).strip()
    return text if text else config.NOT_AVAILABLE


def format_year(year: Optional[int]) -> str:
    """2018 -> '2018', -720 -> '720 BC', None -> 'Not available'."""
    if year is None:
        return config.NOT_AVAILABLE
    return f"{-year} BC" if year < 0 else str(year)


def format_rating(rating: Optional[float], count: Optional[int] = None) -> str:
    """4.34, 4780653 -> '4.34 / 5 (4,780,653 ratings)'."""
    if rating is None:
        return config.NOT_AVAILABLE
    text = f"{rating:.2f} / 5"
    if count:
        text += f" ({count:,} ratings)"
    return text


def stars(rating: int) -> str:
    """3 -> '★★★☆☆'."""
    low, high = config.RATING_SCALE
    rating = max(low, min(high, int(rating)))
    return "★" * rating + "☆" * (high - rating)


def shorten(text: str, width: int = 60) -> str:
    """Cut long text and add '...' so lists stay on one line."""
    text = text or ""
    return text if len(text) <= width else text[: width - 3].rstrip() + "..."


def unique_in_order(items: Iterable) -> list:
    """Remove duplicates but keep the original order (a plain set would lose the order)."""
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def setup_logging() -> None:
    """Send log messages to logs/bookwise.log, never to the user's screen.

    Only technical events are logged (file errors, API failures). API keys and
    user data are never written to the log.
    """
    root = logging.getLogger()
    if root.handlers:  # already configured (e.g. by tests or Streamlit)
        return
    try:
        config.LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = logging.FileHandler(config.LOG_PATH, encoding="utf-8")
    except OSError:
        handler = logging.NullHandler()  # logging must never stop the app
    handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s"))
    root.addHandler(handler)
    root.setLevel(logging.INFO)
