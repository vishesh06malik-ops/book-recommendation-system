# BookWise — Testing

## 1. How to run

```bash
pytest            # all tests (quiet mode is set in pytest.ini)
pytest -v         # one line per test
pytest tests/test_search.py
```

The tests use `tests/fixtures/sample_books.csv`, a **synthetic** 12-book file written by hand
with made-up titles and deliberate edge cases (duplicate id, row without id, a book with no
metadata, a BC year, non-numeric values). This makes expected results exact and independent of
the real dataset. The Google Books tests use a fake HTTP session and **never** access the
internet. Temporary files go into pytest's `tmp_path`, so your real profile is never touched.

## 2. Automated test suite

| File | What is tested | Tests |
|---|---|---|
| `test_data_manager.py` | Valid dataset; duplicate ids; multi-value fields → tuples; missing values; non-numeric values; BC years; missing file; missing required column; file with only bad rows; binary garbage; catalogue look-ups and genre counts; display never shows `None`/`nan`/`[]` | 13 |
| `test_search.py` | Title ranking; case/whitespace insensitivity; word order; author search ignoring punctuation; partial genre; ISBN with hyphens, missing zero and ISBN-13; keyword AND logic; no results; empty/blank/None query; unknown mode; result limit | 14 |
| `test_recommender.py` | Weights sum to 1; return type and score range; selected book excluded; most similar first; sorted; unrelated books excluded; fewer results than requested; book without metadata; n = 0; other editions and duplicate works removed; `exclude_ids`; deterministic output; explanations; hand-calculated score | 14 |
| `test_personalization.py` | `genre_match` examples; empty profile; genre-driven results; liked-book similarity; disliked book lowers score; history/excluded not repeated; unknown ids ignored; deterministic | 8 |
| `test_content_recommender.py` | TF-IDF document building; ranking, exclusion, no duplicates, cosine range; empty text; external (Google Books) book; fallback to basic engine without scikit-learn; model built once and cached | 6 |
| `test_storage.py` | JSON round-trip; missing file; corrupted JSON backed up; unserialisable data; favourites add/remove persisted; valid ratings (1, 5, "4", " 3 "); invalid ratings (0, 6, −1, "abc", "", "4.5", None, True); rating replaced; genre set persisted; history order; liked/disliked rules; hand-edited JSON with wrong types; wrong top-level type | 23 |
| `test_api.py` | Normalisation of a full volume; duplicates; missing metadata; wrong JSON types; empty results; HTTP 400/403/429/500/503/404; timeout, no connection, other request errors; malformed JSON; key read from environment and **not** logged; placeholder key ignored | 16 |
| `test_prepare_dataset.py` | ISBN repair and check digit (incl. `X`); years; placeholder covers; shelf-tag filter; genre/keyword derivation and threshold; duplicate removal keeping the most-rated edition; rows without title | 19 |

*(Counts include each `parametrize` case.)*

### Result (recorded by the developer)

```
PENDING_PYTEST_RESULT
```

Environment: PENDING_ENVIRONMENT

## 3. Manual CLI tests

These were run with `python main.py` on the real dataset. Each "Observed" entry describes
what actually happened.

PENDING_MANUAL_TABLE

## 4. Measured performance

PENDING_PERFORMANCE

How to measure on your own computer:

```bash
python -c "import time; t=time.perf_counter(); from src.services import BookWiseService; s=BookWiseService(); print('startup', round(time.perf_counter()-t, 2), 's')"
```

## 5. Streamlit

PENDING_STREAMLIT

## 6. What is not tested automatically

* The interactive CLI menus are tested manually (section 3), not with pytest.
* The real Google Books service is deliberately not called by tests.
* Recommendation *quality* (whether users like the suggestions) cannot be unit-tested.
  The tests check correctness properties (exclusion, ordering, duplicates, determinism,
  exact scores), not user satisfaction.
