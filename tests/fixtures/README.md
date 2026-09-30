# Test fixtures

`sample_books.csv` is **synthetic test data** written by hand for the unit tests.
The titles and authors are made up on purpose and are **not** real books.
It deliberately contains edge cases: a duplicate id, a row without an id,
a book with no metadata, a BC publication year and non-numeric values.

The real application data lives in `data/books.csv` (goodbooks-10k).
