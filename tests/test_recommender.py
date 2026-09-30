"""Tests for Module 2 — the basic recommendation engine."""

import pytest

from src import config
from src.models.book import Book
from src.recommendation.basic_recommender import (
    BasicRecommender, Recommendation, compare_features, extract_features, weighted_score,
)


@pytest.fixture
def recommender(sample_books):
    return BasicRecommender(sample_books)


def test_weights_add_up_to_one():
    assert sum(config.RECOMMENDER_WEIGHTS.values()) == pytest.approx(1.0)


def test_returns_list_of_recommendations(recommender, catalog):
    result = recommender.recommend(catalog.get("1"), n=3)
    assert isinstance(result, list)
    assert all(isinstance(r, Recommendation) for r in result)
    assert all(0 <= r.score <= 1 for r in result)


def test_selected_book_is_excluded(recommender, catalog):
    result = recommender.recommend(catalog.get("1"), n=10)
    assert "1" not in [r.book.id for r in result]


def test_most_similar_book_comes_first(recommender, catalog):
    # Book 2 shares author, genres, two keywords and title words with book 1
    result = recommender.recommend(catalog.get("1"), n=3)
    assert result[0].book.id == "2"
    assert result[1].book.id in {"3", "12"}  # other fantasy books


def test_results_are_sorted_by_score(recommender, catalog):
    scores = [r.score for r in recommender.recommend(catalog.get("6"), n=10)]
    assert scores == sorted(scores, reverse=True)


def test_unrelated_books_are_not_recommended(recommender, catalog):
    # The romance novel shares nothing with the fantasy book
    result = recommender.recommend(catalog.get("1"), n=10)
    assert "9" not in [r.book.id for r in result]


def test_handles_insufficient_results(recommender, catalog):
    # Only book 5 is similar to book 4, so asking for 15 returns fewer
    result = recommender.recommend(catalog.get("4"), n=15)
    assert 1 <= len(result) < 15
    assert result[0].book.id == "5"


def test_book_without_metadata_gets_empty_list(recommender, catalog):
    assert recommender.recommend(catalog.get("10"), n=5) == []


def test_zero_or_negative_n(recommender, catalog):
    assert recommender.recommend(catalog.get("1"), n=0) == []


def test_other_editions_and_duplicates_are_removed(sample_books):
    edition = Book(id="99", title="Dragon Realm (Realm #1)", authors=("Alice Stone",),
                   categories=("Fantasy",), keywords=("magic",), rating=4.0)
    copy_a = Book(id="100", title="Twin Book", authors=("Z",), categories=("Fantasy",),
                  keywords=("magic", "dragons"), rating=4.0)
    copy_b = Book(id="101", title="twin  book", authors=("z",), categories=("Fantasy",),
                  keywords=("magic", "dragons"), rating=4.0)
    books = sample_books + [edition, copy_a, copy_b]
    result = BasicRecommender(books).recommend(books[0], n=15)
    result_ids = [r.book.id for r in result]
    assert "99" not in result_ids                           # another edition of the selected book
    assert len({"100", "101"} & set(result_ids)) == 1       # only one copy of a duplicate work
    assert len(result_ids) == len(set(result_ids))


def test_exclude_ids_parameter(recommender, catalog):
    result = recommender.recommend(catalog.get("1"), n=10, exclude_ids={"2"})
    assert "2" not in [r.book.id for r in result]


def test_results_are_deterministic(recommender, catalog):
    first = [(r.book.id, r.score) for r in recommender.recommend(catalog.get("3"), n=10)]
    second = [(r.book.id, r.score) for r in recommender.recommend(catalog.get("3"), n=10)]
    assert first == second


def test_explanations_describe_real_overlap(recommender, catalog):
    top = recommender.recommend(catalog.get("1"), n=1)[0]
    text = " ".join(top.reasons)
    assert "Same author: Alice Stone" in text
    assert "Fantasy" in text
    assert "magic" in text and "dragons" in text


def test_component_scores_by_hand(catalog):
    a = extract_features(catalog.get("6"))  # habits, productivity, behavior
    b = extract_features(catalog.get("7"))  # behavior, brain, habits
    parts = compare_features(a, b)
    assert parts["keywords"] == pytest.approx(2 / 4)  # {habits, behavior} / 4 unique
    assert parts["genre"] == pytest.approx(1 / 3)     # {Psychology} / 3 unique
    assert parts["author"] == 0
    assert parts["rating"] == pytest.approx((4.0 - 1) / 4)
    expected = 0.35 * 0.5 + 0.30 * (1 / 3) + 0.10 * 0.75
    assert weighted_score(parts, config.RECOMMENDER_WEIGHTS) == pytest.approx(expected)
