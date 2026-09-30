"""Tests for the optional TF-IDF recommender and the service-level fallback."""

import pytest

from src.models.book import Book
from src.recommendation import content_recommender
from src.recommendation.content_recommender import book_to_document
from src.services import ENGINE_ADVANCED, BookWiseService
from tests.conftest import FIXTURE_CSV

sklearn_needed = pytest.mark.skipif(not content_recommender.ADVANCED_AVAILABLE,
                                    reason="scikit-learn not installed")


def test_document_keeps_multi_word_values_together():
    book = Book(id="1", title="T", authors=("Alice Stone",), categories=("Science Fiction",),
                keywords=("young adult",))
    document = book_to_document(book)
    assert "science_fiction" in document
    assert "alicestone" in document
    assert document.count("young_adult") == 3  # keywords weight in config


@sklearn_needed
def test_tfidf_recommendations(sample_books):
    recommender = content_recommender.AdvancedContentRecommender(sample_books)
    source = next(b for b in sample_books if b.id == "1")
    result = recommender.recommend(source, n=5)
    ids = [r.book.id for r in result]
    assert ids[0] == "2"                    # the sequel shares the most words
    assert "1" not in ids                   # selected book excluded
    assert len(ids) == len(set(ids))        # no duplicates
    scores = [r.score for r in result]
    assert scores == sorted(scores, reverse=True)
    assert all(0 < s <= 1 for s in scores)  # cosine similarity range
    assert result[0].reasons[0].startswith("High text similarity (TF-IDF cosine")


@sklearn_needed
def test_tfidf_book_without_text_returns_empty(sample_books):
    recommender = content_recommender.AdvancedContentRecommender(sample_books)
    assert recommender.recommend(Book(id="x", title="the of and"), n=5) == []


@sklearn_needed
def test_tfidf_works_for_external_books(sample_books):
    recommender = content_recommender.AdvancedContentRecommender(sample_books)
    outside = Book(id="gb:1", title="Crime at the Station", categories=("Mystery & Thriller",),
                   keywords=("detective", "crime"))
    assert {r.book.id for r in recommender.recommend(outside, n=2)} == {"4", "5"}


def test_service_falls_back_to_basic_when_sklearn_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(content_recommender, "ADVANCED_AVAILABLE", False)
    service = BookWiseService(FIXTURE_CSV, tmp_path / "p.json")
    recs, engine = service.recommend(service.get_book("1"), 3, ENGINE_ADVANCED)
    assert engine.startswith("Basic")
    assert recs[0].book.id == "2"


@sklearn_needed
def test_service_builds_tfidf_once(tmp_path):
    service = BookWiseService(FIXTURE_CSV, tmp_path / "p.json")
    service.recommend(service.get_book("1"), 3, ENGINE_ADVANCED)
    first_model = service._advanced
    _, engine = service.recommend(service.get_book("4"), 3, ENGINE_ADVANCED)
    assert service._advanced is first_model  # cached, not rebuilt
    assert engine.startswith("Advanced")
