"""Tests for the optional Google Books API module.

A fake session object replaces the real network, so these tests never use
the internet and never need an API key.
"""

import pytest
import requests

from src.api import google_books
from src.api.google_books import GoogleBooksUnavailable, normalize_volume, search_google_books


class FakeResponse:
    def __init__(self, status_code=200, payload=None, bad_json=False):
        self.status_code = status_code
        self._payload = payload
        self._bad_json = bad_json

    def json(self):
        if self._bad_json:
            raise ValueError("Expecting value: line 1 column 1")
        return self._payload


class FakeSession:
    """Records the request and returns a prepared response (or raises an error)."""

    def __init__(self, response=None, error=None):
        self.response, self.error, self.calls = response, error, []

    def get(self, url, params=None, timeout=None):
        self.calls.append({"url": url, "params": params, "timeout": timeout})
        if self.error:
            raise self.error
        return self.response


VOLUME = {
    "id": "abc123",
    "volumeInfo": {
        "title": "Atomic Habits",
        "subtitle": "An Easy & Proven Way",
        "authors": ["James Clear"],
        "publisher": "Penguin",
        "publishedDate": "2018-10-16",
        "description": "<p>Tiny changes.</p>",
        "industryIdentifiers": [{"type": "ISBN_13", "identifier": "9780735211292"},
                                {"type": "ISBN_10", "identifier": "0735211299"}],
        "categories": ["Self-Help / Personal Growth"],
        "averageRating": 4.5,
        "ratingsCount": 120,
        "imageLinks": {"thumbnail": "http://books.google.com/cover.jpg"},
        "language": "en",
    },
}


def test_successful_search_is_normalised_into_books():
    session = FakeSession(FakeResponse(200, {"items": [VOLUME, VOLUME]}))
    books = search_google_books("atomic habits", session=session)
    assert len(books) == 1  # duplicate volume removed
    book = books[0]
    assert book.id == "gb:abc123"
    assert book.title == "Atomic Habits: An Easy & Proven Way"
    assert book.authors == ("James Clear",)
    assert book.isbn == "0735211299"
    assert book.published_year == 2018
    assert book.description == "Tiny changes."
    assert book.categories == ("Self-Help", "Personal Growth")
    assert book.cover_url.startswith("https://")
    assert book.source == "Google Books"
    assert session.calls[0]["timeout"] > 0


def test_missing_metadata_is_handled():
    book = normalize_volume({"id": "x", "volumeInfo": {"title": "Only Title"}})
    assert book.authors == () and book.rating is None and book.published_year is None
    assert normalize_volume({"id": "x", "volumeInfo": {}}) is None       # no title
    assert normalize_volume({"volumeInfo": {"title": "No id"}}) is None
    assert normalize_volume("not a dict") is None


def test_wrong_types_in_json_are_ignored():
    weird = {"id": "y", "volumeInfo": {"title": "T", "authors": "not a list",
                                       "averageRating": "5", "ratingsCount": -3,
                                       "publishedDate": 2001, "imageLinks": []}}
    book = normalize_volume(weird)
    assert book.authors == () and book.rating is None and book.rating_count is None
    assert book.published_year is None and book.cover_url == ""


def test_empty_results():
    assert search_google_books("zzzz", session=FakeSession(FakeResponse(200, {"totalItems": 0}))) == []
    assert search_google_books("   ", session=FakeSession(FakeResponse(200, {}))) == []


@pytest.mark.parametrize("status, text", [
    (400, "API key may be invalid"),
    (403, "access was refused"),
    (429, "too many requests"),
    (500, "service is having problems"),
    (503, "service is having problems"),
    (404, "HTTP 404"),
])
def test_http_errors_become_friendly_error(status, text):
    with pytest.raises(GoogleBooksUnavailable) as info:
        search_google_books("x", session=FakeSession(FakeResponse(status, {})))
    assert text in str(info.value)
    assert "Live book search is currently unavailable" in str(info.value)


@pytest.mark.parametrize("error, text", [
    (requests.exceptions.Timeout(), "timed out"),
    (requests.exceptions.ConnectionError(), "no internet connection"),
    (requests.exceptions.TooManyRedirects(), "request failed"),
])
def test_network_errors_become_friendly_error(error, text):
    with pytest.raises(GoogleBooksUnavailable, match=text):
        search_google_books("x", session=FakeSession(error=error))


def test_malformed_json():
    with pytest.raises(GoogleBooksUnavailable, match="could not be read"):
        search_google_books("x", session=FakeSession(FakeResponse(200, bad_json=True)))
    with pytest.raises(GoogleBooksUnavailable, match="could not be read"):
        search_google_books("x", session=FakeSession(FakeResponse(200, ["a", "list"])))


def test_api_key_comes_from_environment_and_is_not_logged(monkeypatch, caplog):
    monkeypatch.setenv("GOOGLE_BOOKS_API_KEY", "secret-test-key")
    session = FakeSession(FakeResponse(403, {}))
    with pytest.raises(GoogleBooksUnavailable):
        search_google_books("x", session=session)
    assert session.calls[0]["params"]["key"] == "secret-test-key"
    assert "secret-test-key" not in caplog.text


def test_placeholder_or_missing_key_is_not_sent(monkeypatch):
    monkeypatch.setenv("GOOGLE_BOOKS_API_KEY", "your_api_key_here")
    assert google_books.get_api_key() is None
    monkeypatch.delenv("GOOGLE_BOOKS_API_KEY")
    session = FakeSession(FakeResponse(200, {}))
    search_google_books("x", session=session)
    assert "key" not in session.calls[0]["params"]
