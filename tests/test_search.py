"""Tests for Module 1 — Book Search & Discovery."""

import pytest

from src.search.search_engine import SearchEngine, compact, normalize_isbn


@pytest.fixture
def engine(sample_books):
    return SearchEngine(sample_books)


def ids(books):
    return [book.id for book in books]


def test_title_search_ranks_exact_then_prefix(engine):
    assert ids(engine.search("Dragon Realm (Realm #1)", "title"))[0] == "1"
    result = ids(engine.search("dragon realm", "title"))
    assert set(result) == {"1", "2"}
    assert result[0] == "1"  # same score -> more external ratings first


def test_title_search_is_case_and_whitespace_insensitive(engine):
    assert ids(engine.search("   WIZARD    school  ", "title")) == ["3"]


def test_title_search_words_in_any_order(engine):
    assert ids(engine.search("school wizard", "title")) == ["3"]


def test_author_search_ignores_punctuation_and_case(engine):
    assert ids(engine.search("carla reyes", "author")) == ["4", "5"]
    assert ids(engine.search("REYES", "author")) == ["4", "5"]
    assert ids(engine.search("c.a.r.l.a", "author")) == ["4", "5"]


def test_genre_search_partial_name(engine):
    assert set(ids(engine.search("mystery", "genre"))) == {"4", "5"}
    assert "8" in ids(engine.search("science", "genre"))


def test_isbn_search_accepts_missing_zero_hyphens_and_isbn13(engine):
    assert ids(engine.search("0-439-02348-3", "isbn")) == ["1"]
    assert ids(engine.search("439023483", "isbn")) == ["1"]
    assert ids(engine.search("978-0-439-02348-1", "isbn")) == ["1"]


def test_keyword_search_needs_all_words(engine):
    assert set(ids(engine.search("habits", "keyword"))) == {"6", "7"}
    assert ids(engine.search("habits productivity", "keyword")) == ["6"]


def test_no_results_returns_empty_list(engine):
    assert engine.search("zzzz no such book", "title") == []
    assert engine.search("123", "isbn") == []


@pytest.mark.parametrize("query", ["", "   ", None])
def test_empty_query_returns_empty_list(engine, query):
    assert engine.search(query, "title") == []


def test_unknown_mode_returns_empty_list(engine):
    assert engine.search("dragon", "publisher-name") == []


def test_limit_is_respected(engine):
    assert len(engine.search("fantasy", "genre", limit=2)) == 2


def test_helpers():
    assert compact("J.K. Rowling") == "jkrowling"
    assert normalize_isbn("978-0-316-01584-4") == "0316015849"
    assert normalize_isbn("080442957x") == "080442957X"
