"""Optional live search in the Google Books catalogue.

The core application never depends on this module. Every failure (no
internet, timeout, bad key, rate limit, server error, strange JSON) is
turned into one exception, GoogleBooksUnavailable, with a friendly
message, so the caller only has to handle a single case.

Results are converted into the same Book class used for the local dataset
(see normalize_volume), so the rest of the program never touches raw JSON.

What is an API? An Application Programming Interface is a way for one
program to ask another for data. Here we send an HTTP GET request to
Google's server with a search term, and it answers with JSON text.
"""

from __future__ import annotations

import logging
import os
import re
from typing import Optional

from src import config
from src.models.book import Book

logger = logging.getLogger(__name__)

try:
    import requests
except ImportError:  # pragma: no cover
    requests = None

try:
    from dotenv import load_dotenv
    load_dotenv(config.PROJECT_ROOT / ".env")  # reads GOOGLE_BOOKS_API_KEY from .env if present
except ImportError:  # pragma: no cover - python-dotenv is optional
    pass

UNAVAILABLE_MESSAGE = ("Live book search is currently unavailable.\n"
                       "You can continue using the local book database.")

# Friendly explanations for HTTP status codes (the technical detail goes to the log only).
HTTP_MESSAGES = {
    400: "the request was rejected (the API key may be invalid)",
    403: "access was refused (check the API key and that the Books API is enabled)",
    429: "too many requests were sent; please try again later",
}


class GoogleBooksUnavailable(Exception):
    """Live search failed. `str(error)` is safe to show to the user."""

    def __init__(self, reason: str):
        super().__init__(f"{UNAVAILABLE_MESSAGE}\n(Reason: {reason})")
        self.reason = reason


def get_api_key() -> Optional[str]:
    """Read the key from the environment. It is never printed or logged."""
    key = os.environ.get(config.API_KEY_ENV_VAR, "").strip()
    if not key or key == "your_api_key_here":
        return None
    return key


def is_available() -> bool:
    return requests is not None


def _year_from(date_text: str) -> Optional[int]:
    match = re.match(r"^(-?\d{4})", date_text or "")
    return int(match.group(1)) if match else None


def _clean_list(value) -> tuple[str, ...]:
    if not isinstance(value, list):
        return ()
    return tuple(str(item).strip() for item in value if isinstance(item, str) and item.strip())


def normalize_volume(item) -> Optional[Book]:
    """Convert one Google Books 'volume' (a dict from JSON) into a Book.

    Returns None if the item is not usable (no id or no title).
    External data is never trusted: every field is type-checked.
    """
    if not isinstance(item, dict):
        return None
    info = item.get("volumeInfo")
    volume_id = item.get("id")
    if not isinstance(info, dict) or not isinstance(volume_id, str):
        return None
    title = info.get("title")
    if not isinstance(title, str) or not title.strip():
        return None
    subtitle = info.get("subtitle")
    if isinstance(subtitle, str) and subtitle.strip():
        title = f"{title.strip()}: {subtitle.strip()}"

    isbn = ""
    identifiers = info.get("industryIdentifiers")
    if isinstance(identifiers, list):
        found = {i.get("type"): i.get("identifier") for i in identifiers if isinstance(i, dict)}
        isbn = str(found.get("ISBN_10") or found.get("ISBN_13") or "")

    rating = info.get("averageRating")
    rating = float(rating) if isinstance(rating, (int, float)) and 0 <= rating <= 5 else None
    count = info.get("ratingsCount")
    count = int(count) if isinstance(count, int) and count >= 0 else None

    images = info.get("imageLinks") if isinstance(info.get("imageLinks"), dict) else {}
    cover = images.get("thumbnail") or images.get("smallThumbnail") or ""
    description = info.get("description") if isinstance(info.get("description"), str) else ""

    # Google categories look like "Fiction / Fantasy / Epic": split them into parts.
    categories = []
    for category in _clean_list(info.get("categories")):
        categories.extend(part.strip() for part in category.split("/") if part.strip())

    return Book(
        id=f"gb:{volume_id}",
        title=title.strip(),
        authors=_clean_list(info.get("authors")),
        isbn=isbn,
        description=re.sub(r"<[^>]+>", "", description).strip(),  # drop simple HTML tags
        categories=tuple(dict.fromkeys(categories)),
        publisher=info.get("publisher") if isinstance(info.get("publisher"), str) else "",
        published_year=_year_from(info.get("publishedDate") if isinstance(info.get("publishedDate"), str) else ""),
        language=info.get("language") if isinstance(info.get("language"), str) else "",
        rating=rating,
        rating_count=count,
        cover_url=str(cover).replace("http://", "https://") if cover else "",
        source="Google Books",
    )


def search_google_books(query: str, max_results: int = config.API_MAX_RESULTS, session=None) -> list[Book]:
    """Search Google Books and return normalised Book objects.

    Raises GoogleBooksUnavailable for every kind of failure.
    `session` can be replaced by a fake object in tests, so tests never use the internet.
    """
    query = (query or "").strip()
    if not query:
        return []
    if requests is None:
        raise GoogleBooksUnavailable("the 'requests' package is not installed")

    params = {"q": query, "maxResults": max(1, min(40, max_results)), "printType": "books"}
    key = get_api_key()
    if key:
        params["key"] = key
    http = session or requests

    try:
        response = http.get(config.GOOGLE_BOOKS_URL, params=params, timeout=config.API_TIMEOUT)
    except requests.exceptions.Timeout:
        logger.warning("Google Books request timed out")
        raise GoogleBooksUnavailable("the request timed out") from None
    except requests.exceptions.ConnectionError:
        logger.warning("Google Books: no connection")
        raise GoogleBooksUnavailable("no internet connection") from None
    except requests.exceptions.RequestException as error:
        logger.warning("Google Books request failed: %s", type(error).__name__)
        raise GoogleBooksUnavailable("the request failed") from None

    status = response.status_code
    if status != 200:
        logger.warning("Google Books returned HTTP %s", status)  # the key is never logged
        reason = HTTP_MESSAGES.get(status)
        if reason is None:
            reason = "the service is having problems" if status >= 500 else f"unexpected response (HTTP {status})"
        raise GoogleBooksUnavailable(reason)

    try:
        data = response.json()
    except ValueError:
        logger.warning("Google Books returned invalid JSON")
        raise GoogleBooksUnavailable("the response could not be read") from None
    if not isinstance(data, dict):
        raise GoogleBooksUnavailable("the response could not be read")

    items = data.get("items")
    if not isinstance(items, list):
        return []  # a valid answer with zero results has no "items" key
    books = [book for book in (normalize_volume(item) for item in items) if book is not None]
    return list({book.id: book for book in books}.values())  # drop repeated volumes
