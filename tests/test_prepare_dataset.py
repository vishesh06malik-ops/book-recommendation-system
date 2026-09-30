"""Tests for the cleaning rules in scripts/prepare_dataset.py (no network used)."""

import csv
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import prepare_dataset as prep  # noqa: E402


@pytest.mark.parametrize("raw, expected", [
    ("439023483", "0439023483"),   # leading zero restored, check digit valid
    ("0316015849", "0316015849"),
    ("080442957X", "080442957X"),  # 'X' check digit
    ("439023484", ""),             # wrong check digit
    ("9.78043902348e+12", ""),     # damaged ISBN-13 float is rejected
    ("", ""),
])
def test_clean_isbn(raw, expected):
    assert prep.clean_isbn(raw) == expected


def test_clean_year_and_cover():
    assert prep.clean_year("2008.0") == "2008"
    assert prep.clean_year("-720.0") == "-720"
    assert prep.clean_year("") == ""
    assert prep.clean_cover_url("https://s.gr-assets.com/assets/nophoto/book/111x148.png") == ""
    assert prep.clean_cover_url("https://images.gr-assets.com/books/1m/2.jpg").endswith("2.jpg")


@pytest.mark.parametrize("tag, useful", [
    ("fantasy", True), ("sci-fi", True), ("brown", True),
    ("to-read", False), ("currently-reading", False), ("books-i-own", False),
    ("favorites", False), ("kindle", False), ("2014-reads", False), ("ספרים", False),
])
def test_tag_filter(tag, useful):
    assert prep.is_useful_tag(tag) is useful


def test_genres_and_keywords_from_tags():
    tags = [("to-read", 100000), ("fantasy", 5000), ("favorites", 4000),
            ("young-adult", 3000), ("dystopian", 2000), ("rare-tag", 10)]
    genres, keywords = prep.derive_genres_and_keywords(tags)
    assert genres == ["Fantasy", "Science Fiction", "Young Adult"]
    assert keywords == ["fantasy", "young adult", "dystopian"]  # rare tag below threshold
    assert prep.derive_genres_and_keywords([]) == ([], [])


def test_build_rows_removes_duplicates_and_keeps_most_rated(tmp_path):
    books_csv = tmp_path / "books.csv"
    fields = ["book_id", "goodreads_book_id", "isbn", "authors", "original_publication_year",
              "title", "language_code", "average_rating", "ratings_count", "image_url"]
    rows = [
        ["1", "100", "439023483", "A Writer", "2008.0", "Same Book", "eng", "4.1", "50", ""],
        ["2", "200", "", "A Writer", "2009.0", "same  book", "eng", "4.0", "900", ""],
        ["3", "300", "", "B Writer, C Writer", "", "Other Book", "", "3.9", "10", ""],
        ["4", "400", "", "Nobody", "", "", "", "", "", ""],
    ]
    with open(books_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(fields)
        writer.writerows(rows)

    tags = {"300": [("horror", 40)]}
    result, stats = prep.build_rows(books_csv, tags)
    assert [r["id"] for r in result] == ["2", "3"]
    assert stats["duplicates_removed"] == 1
    assert stats["skipped_no_title"] == 1
    other = result[1]
    assert other["authors"] == "B Writer|C Writer"
    assert other["categories"] == "Horror"
    assert other["published_year"] == ""
