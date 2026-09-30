"""Tests for Module 3 — personalised recommendations."""

import pytest

from src.recommendation.basic_recommender import BasicRecommender
from src.recommendation.personalization import PersonalizedRecommender, UserSignals, genre_match


@pytest.fixture
def personal(sample_books):
    return PersonalizedRecommender(BasicRecommender(sample_books))


def ids(recs):
    return [r.book.id for r in recs]


def test_genre_match_examples():
    assert genre_match({"Psychology", "Non-fiction"}, {"Psychology", "Self Help"}) == 0.5
    assert genre_match({"Fantasy"}, {"Fantasy", "Romance", "Horror"}) == 1.0
    assert genre_match(set(), {"Fantasy"}) == 0.0


def test_no_signals_gives_no_recommendations(personal):
    assert personal.recommend(UserSignals()) == []


def test_preferred_genre_drives_results(personal):
    recs = personal.recommend(UserSignals(preferred_genres={"Mystery & Thriller"}), n=5)
    assert set(ids(recs)) == {"4", "5"}
    assert "You prefer Mystery & Thriller" in recs[0].reasons


def test_liked_book_finds_similar_books(personal):
    recs = personal.recommend(UserSignals(liked_ids={"6"}), n=3)
    assert ids(recs)[0] == "7"  # shares habits/behavior/Psychology
    assert any('which you liked' in reason for reason in recs[0].reasons)
    assert "6" not in ids(recs)  # a liked book is never recommended back


def test_disliked_book_lowers_ranking(personal):
    liked_only = personal.recommend(UserSignals(preferred_genres={"Fantasy"}), n=5)
    with_dislike = personal.recommend(UserSignals(preferred_genres={"Fantasy"}, disliked_ids={"2"}), n=5)
    score_before = {r.book.id: r.score for r in liked_only}["1"]
    score_after = {r.book.id: r.score for r in with_dislike}["1"]
    assert score_after < score_before  # book 1 closely resembles disliked book 2
    assert "2" not in ids(with_dislike)


def test_excluded_and_history_books_not_repeated(personal):
    signals = UserSignals(preferred_genres={"Fantasy"}, history_ids=["3"], exclude_ids={"1"})
    result = ids(personal.recommend(signals, n=10))
    assert "1" not in result and "3" not in result
    assert "2" in result


def test_unknown_ids_in_profile_are_ignored(personal):
    recs = personal.recommend(UserSignals(liked_ids={"does-not-exist"}, preferred_genres={"Romance"}))
    assert ids(recs) == ["9"]


def test_personal_ranking_is_deterministic(personal):
    signals = UserSignals(preferred_genres={"Fantasy", "Psychology"}, liked_ids={"1"})
    assert ids(personal.recommend(signals, n=10)) == ids(personal.recommend(signals, n=10))
