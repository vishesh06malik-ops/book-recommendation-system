"""Tests for loading the dataset (src/data/data_manager.py) and the Book model."""

import pytest

from src import config
from src.data.data_manager import DatasetError, load_books
from src.models.book import Book


def test_valid_dataset_loads_expected_books(sample_books):
    ids = [book.id for book in sample_books]
    # 14 data rows: 1 duplicate id and 1 row without id are skipped
    assert len(sample_books) == 12
    assert ids[0] == "1"
    assert all(isinstance(book, Book) for book in sample_books)


def test_duplicate_id_keeps_first_row(sample_books):
    first = [book for book in sample_books if book.id == "1"]
    assert len(first) == 1
    assert first[0].title == "Dragon Realm (Realm #1)"


def test_multi_value_fields_become_tuples(catalog):
    book = catalog.get("1")
    assert book.authors == ("Alice Stone",)
    assert book.categories == ("Fantasy", "Young Adult")
    assert "dragons" in book.keywords


def test_missing_values_are_empty_not_crashing(catalog):
    book = catalog.get("10")
    assert book.authors == ()
    assert book.rating is None
    assert book.published_year is None
    assert book.author_text == config.NOT_AVAILABLE
    assert book.year_text == config.NOT_AVAILABLE


def test_non_numeric_values_become_missing(catalog):
    book = catalog.get("12")
    assert book.published_year is None
    assert book.rating is None
    assert book.rating_count is None


def test_bc_year_is_displayed_correctly(catalog):
    assert catalog.get("11").year_text == "700 BC"


def test_missing_file_raises_dataset_error(tmp_path):
    with pytest.raises(DatasetError, match="not found"):
        load_books(tmp_path / "does_not_exist.csv")


def test_missing_required_column_raises(tmp_path):
    path = tmp_path / "books.csv"
    path.write_text("id,authors\n1,Someone\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="title"):
        load_books(path)


def test_file_with_only_bad_rows_raises(tmp_path):
    path = tmp_path / "books.csv"
    path.write_text("id,title,authors\n,,\n,,\n", encoding="utf-8")
    with pytest.raises(DatasetError, match="no usable books"):
        load_books(path)


def test_binary_garbage_file_raises_dataset_error(tmp_path):
    path = tmp_path / "books.csv"
    path.write_bytes(b"\xff\xfe\x00\x00garbage\x80\x81")
    with pytest.raises(DatasetError):
        load_books(path)


def test_catalog_lookup_and_genres(catalog):
    assert catalog.get("999") is None
    genres = dict(catalog.genres())
    assert genres["Fantasy"] == 4  # books 1, 2, 3 and 12
    fantasy = catalog.books_in_genre("Fantasy")
    # sorted by number of external ratings, highest first
    assert fantasy[0].id == "3"
    assert catalog.books_in_genre("Unknown genre") == []


def test_get_many_ignores_unknown_ids(catalog):
    assert [b.id for b in catalog.get_many(["2", "nope", "5"])] == ["2", "5"]


def test_display_dict_never_shows_raw_missing_values(catalog):
    shown = catalog.get("10").to_display_dict()
    for value in shown.values():
        assert value not in ("None", "nan", "[]", "()", "")
