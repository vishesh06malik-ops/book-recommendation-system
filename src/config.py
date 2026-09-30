"""
Central configuration for BookWise.

Every tunable value lives here so that no other module hard-codes paths,
limits or weights. Changing behaviour means editing one file.
"""

from __future__ import annotations

import os
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
# Both paths can be overridden with environment variables (used for testing and demos).
DATASET_PATH = Path(os.environ.get("BOOKWISE_DATASET", PROJECT_ROOT / "data" / "books.csv"))
USER_DATA_PATH = Path(os.environ.get("BOOKWISE_USER_DATA", PROJECT_ROOT / "user_data" / "profile.json"))
LOG_PATH = PROJECT_ROOT / "logs" / "bookwise.log"

# Columns the dataset MUST have. Everything else is optional.
REQUIRED_COLUMNS = ("id", "title", "authors")
# Separator used inside a CSV cell that holds several values (authors, genres...).
MULTI_VALUE_SEPARATOR = "|"

# ---------------------------------------------------------------------------
# User interface
# ---------------------------------------------------------------------------
NOT_AVAILABLE = "Not available"
DEFAULT_RECOMMENDATION_COUNT = 5
ALLOWED_RECOMMENDATION_COUNTS = (5, 10, 15)
MAX_SEARCH_RESULTS = 20
MAX_HISTORY_ITEMS = 50
RATING_SCALE = (1, 5)  # (lowest, highest) personal rating

# ---------------------------------------------------------------------------
# Basic recommender weights (must add up to 1.0, so a score is between 0 and 1)
#
# Why these values?
#  * KEYWORDS 0.35 - each book has up to 12 descriptive reader tags
#    ("dystopian", "magic", "vampires"). They are the most specific signal
#    we have, so they get the largest share.
#  * GENRE 0.30 - genres are reliable but broad (22 of them for 10,000
#    books), so they matter slightly less than keywords.
#  * AUTHOR 0.15 - the same author is a strong hint, but it is a yes/no
#    signal; a large weight would make every result the same author.
#  * TITLE 0.10 - shared title words mostly catch books in the same series
#    ("Harry Potter and the ..."). Useful, but noisy for common words.
#  * RATING 0.10 - a small quality prior. It only separates books that are
#    otherwise similarly relevant; it can never make an unrelated book win.
# ---------------------------------------------------------------------------
RECOMMENDER_WEIGHTS = {
    "keywords": 0.35,
    "genre": 0.30,
    "author": 0.15,
    "title": 0.10,
    "rating": 0.10,
}
# A component must reach this value before it is mentioned in an explanation.
EXPLANATION_THRESHOLD = 0.15
# Books with no similarity at all (only the rating prior) are not recommended.
MIN_SIMILARITY_SCORE = 0.05

# ---------------------------------------------------------------------------
# Personalisation weights (see docs/algorithm.md)
#   genre      - how many of the book's genres the user said they prefer
#   liked      - similarity to books the user liked (favourites, ratings >= 4)
#   history    - similarity to recently viewed books (a weaker signal)
#   rating     - small quality prior, same idea as above
#   disliked   - similarity to books rated <= 2 is SUBTRACTED
# ---------------------------------------------------------------------------
PERSONAL_WEIGHTS = {
    "genre": 0.35,
    "liked": 0.40,
    "history": 0.15,
    "rating": 0.10,
    "disliked": 0.30,
}
LIKED_RATING_THRESHOLD = 4     # ratings >= this count as "liked"
DISLIKED_RATING_THRESHOLD = 2  # ratings <= this count as "disliked"
HISTORY_ITEMS_USED = 10        # only the most recent views influence ranking

# ---------------------------------------------------------------------------
# Advanced (TF-IDF) recommender
# ---------------------------------------------------------------------------
TFIDF_MAX_FEATURES = 20000
# How many times each field is repeated in the combined text (a simple way
# to give some fields more influence in TF-IDF).
TFIDF_FIELD_WEIGHTS = {"title": 1, "authors": 2, "categories": 2, "keywords": 3, "description": 1}

# ---------------------------------------------------------------------------
# Google Books API (optional)
# ---------------------------------------------------------------------------
GOOGLE_BOOKS_URL = "https://www.googleapis.com/books/v1/volumes"
API_TIMEOUT = 8  # seconds
API_MAX_RESULTS = 10
API_KEY_ENV_VAR = "GOOGLE_BOOKS_API_KEY"
