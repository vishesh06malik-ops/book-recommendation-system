"""Shared pytest fixtures. Makes the project root importable as `src`."""

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.data.data_manager import BookCatalog, load_books  # noqa: E402

FIXTURE_CSV = Path(__file__).parent / "fixtures" / "sample_books.csv"


@pytest.fixture
def sample_books():
    return load_books(FIXTURE_CSV)


@pytest.fixture
def catalog(sample_books):
    return BookCatalog(sample_books)
