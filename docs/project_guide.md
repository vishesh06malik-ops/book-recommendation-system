# BookWise — Project Guide

This guide explains how the whole application works, from the first line of
`main.py` to the TF-IDF matrix. Read it in order: beginner → intermediate → advanced.

---

# Part 1 — Beginner

## 1.1 What happens when you type `python main.py`

```
main.py
 ├─ setup_logging()                 → technical messages go to logs/bookwise.log
 ├─ BookWiseService()               → loads everything ONCE
 │    ├─ BookCatalog.from_csv()     → reads data/books.csv into Book objects
 │    ├─ SearchEngine(books)        → prepares lower-case search text
 │    ├─ BasicRecommender(books)    → builds keyword/genre/author sets for every book
 │    ├─ PersonalizedRecommender()  → re-uses those sets
 │    └─ UserManager()              → reads user_data/profile.json (or starts empty)
 └─ BookWiseCLI(service).run()      → the menu loop
```

The menu loop is a `while True:` loop. It prints the menu, reads a number with
`ask_int()` (which keeps asking until the input is valid), and calls the matching
method from a dictionary:

```python
self.actions = {1: self.search_books, 2: self.browse_genres, ...}
...
choice = ask_int("Enter your choice: ", 0, 9)
if choice == 0:
    return
self.actions[choice]()
```

A dictionary of functions is shorter and easier to extend than ten `elif` branches.

## 1.2 Files and what they do

| File | In one sentence |
|---|---|
| `main.py` | Starts the program and catches anything that would otherwise crash it |
| `src/config.py` | All settings (paths, weights, limits) in one place |
| `src/models/book.py` | What a "book" is |
| `src/data/data_manager.py` | Reads the CSV file and turns rows into books |
| `src/search/search_engine.py` | Finds books by title, author, genre, ISBN or keyword |
| `src/recommendation/basic_recommender.py` | Finds similar books with sets and a weighted formula |
| `src/recommendation/personalization.py` | Ranks books for *you* |
| `src/recommendation/content_recommender.py` | Optional TF-IDF version of "similar books" |
| `src/user/user_manager.py` | Your favourites, ratings, genres and history |
| `src/storage/storage_manager.py` | Saves and loads JSON safely |
| `src/api/google_books.py` | Optional online search |
| `src/services.py` | Connects all modules; used by both interfaces |
| `src/cli/cli_app.py` | Menus and printing |
| `app.py` | Optional Streamlit web interface |
| `scripts/prepare_dataset.py` | One-time dataset download and cleaning |

## 1.3 The Python ideas you will see most

**Dictionary**: a collection of *key → value* pairs, with very fast lookup by key.
In BookWise, `catalog._by_id["42"]` finds book 42 immediately, without looping over
10,000 books. Your ratings are also a dictionary: `{"42": 5, "7": 2}`.

**Set**: an unordered collection with **no duplicates**. It supports maths-like
operations: `a & b` gives what both sets have, and `a | b` gives everything in either.
Your preferred genres are a set, so selecting "Fantasy" twice changes nothing. Book
similarity is based on sets (see Part 2).

**List vs tuple**: both are ordered sequences. A list can change (`append`,
`remove`), and a tuple cannot. Favourites are a **list** because they change. A book's
authors are a **tuple** because a loaded book should never change.

**Function**: a named, reusable block of code. BookWise has many small functions
(`tokenize`, `clean_isbn`, `jaccard_similarity`), so each one is easy to test.

**Module**: a `.py` file you can `import`. A **package** is a folder of modules with
an `__init__.py` file (`src/search/`).

**Class**: a blueprint that keeps data and the functions using that data together.
`BasicRecommender` stores the pre-computed feature sets *and* the `recommend()` method
that uses them. BookWise only uses classes where this grouping helps. Many parts are
plain functions.

**Exception**: an error object. `try/except` lets the program react to an error
instead of crashing. BookWise defines its own exceptions (`DatasetError`,
`InvalidRatingError` …) so that each error has a clear, friendly message.

**File handling**: `with open(path, encoding="utf-8") as file:` opens a file and
*always* closes it, even if an error happens inside the block.

---

# Part 2 — Intermediate

## 2.1 Data processing pipeline

```
goodbooks-10k raw files ──(scripts/prepare_dataset.py)──► data/books.csv ──(load_books)──► list[Book]
```

`prepare_dataset.py` (run once) repairs ISBNs with the check-digit formula,
converts years, splits authors, removes duplicate works, and derives **genres** and
**keywords** from Goodreads reader tags (e.g. `sci-fi` → *Science Fiction*).
See `data/README.md`.

`load_books()` (run at every start) uses `csv.DictReader`. Each row becomes a
dictionary like `{"id": "1", "title": "...", "authors": "A|B", ...}`, and
`row_to_book()` converts it into a `Book`:

* text numbers → `int` / `float` (invalid → `None`)
* `"Fantasy|Young Adult"` → `("Fantasy", "Young Adult")`
* rows without id or title are skipped and counted
* a repeated id keeps only the first row
* a missing file, missing required column or unreadable file → `DatasetError`

Missing values stay empty inside the program. They become **"Not available"** only
when displayed (`helpers.display_value`), so the logic never has to compare against
display text.

## 2.2 How search works

`SearchEngine.__init__` prepares, for every book, its lower-case title, compacted
author names (`"J.K. Rowling"` → `"jkrowling"`), genres and a set of all words.
A search then loops over this prepared list and gives each book a score:

| Mode | Scoring |
|---|---|
| Title | exact 4 > starts with 3 > contains 2 > all words present in any order 1 |
| Author | exact 3 > starts/ends with 2 > contains 1 (punctuation and case ignored) |
| Genre | exact genre 2 > partial name 1 |
| ISBN | exact match. Hyphens are removed, missing leading zeros are restored, and ISBN-13 (978…) is converted to ISBN-10 |
| Keyword | *every* query word must appear in title/authors/genres/keywords. Title matches count extra |

Results are sorted by score, then by number of ratings, then alphabetically, so the
same search always gives the same order.

## 2.3 How the basic recommendation works

Each book becomes four sets (keywords, genres, authors, title words) and one number
(rating). Two books are compared with **Jaccard similarity** = shared ÷ total
different, per set, and combined with fixed weights:

```
score = 0.35·keywords + 0.30·genre + 0.15·author + 0.10·title + 0.10·rating
```

Full details, the reasons for each weight and a worked example are in
`docs/algorithm.md`.

## 2.4 How data is stored

```json
{
  "favourites": ["1", "58"],
  "history": ["58", "1", "3"],
  "preferred_genres": ["Fantasy", "Science Fiction"],
  "ratings": {"1": 5, "7": 2}
}
```

* JSON has no sets, so `preferred_genres` is saved as a sorted list and turned back
  into a set when loaded.
* **Every change is saved immediately.** Closing the terminal never loses data.
* **Safe write**: data is first written to `profile.json.tmp`, then `os.replace()`
  swaps it in one step. A crash while writing cannot leave a half-written file.
* **Corrupted file**: if `profile.json` is not valid JSON, it is renamed to
  `profile.json.corrupt-<time>` (kept for inspection) and BookWise starts with an
  empty profile.
* **Untrusted content**: `UserProfile.from_dict` checks every value's type. A
  hand-edited file with `"ratings": {"1": 9}` is ignored instead of crashing.

## 2.5 How the API works

An **API** lets one program ask another for data. BookWise sends an HTTP GET request:

```
GET https://www.googleapis.com/books/v1/volumes?q=atomic+habits&maxResults=10
```

Google answers with JSON. `normalize_volume()` checks every field's type and
converts the result into the same `Book` class, so the rest of BookWise doesn't know
or care where a book came from.

Everything that can go wrong becomes one exception, `GoogleBooksUnavailable`:

| Problem | How it is detected |
|---|---|
| No internet | `requests.exceptions.ConnectionError` |
| Too slow | `timeout=8` → `requests.exceptions.Timeout` |
| Invalid key / bad request | HTTP 400 |
| Forbidden | HTTP 403 |
| Rate limit | HTTP 429 |
| Server problem | HTTP 5xx |
| Not JSON / wrong shape | `ValueError` from `.json()`, or not a dict |

The user then sees: *"Live book search is currently unavailable. You can continue
using the local book database."* The API key is read from the environment (`.env`),
sent only as a request parameter, and never printed or logged.

---

# Part 3 — Advanced

## 3.1 TF-IDF

TF-IDF turns each book's text into a vector of numbers. A word gets a high value if
it is common in *this* book but rare across *all* books. Words like "fiction" appear
everywhere and carry little information, while "vampires" is distinctive. The matrix
(10,000 books × up to 20,000 words) is sparse: almost all values are 0, so only
non-zero values are stored. See `docs/algorithm.md` §2 for the formulas.

## 3.2 Cosine similarity

`cos(A,B) = (A·B) / (‖A‖‖B‖)` compares the *direction* of two vectors. Because
TF-IDF vectors are already scaled to length 1, this equals the dot product.
scikit-learn computes it for one book against all 10,000 books in a single
call, which is much faster than a Python loop.

## 3.3 Personalisation

The profile becomes a `UserSignals` object: preferred genres (set), liked ids,
disliked ids and recent history. For every candidate book:

```
score = 0.35·genre_match + 0.40·closest_liked + 0.15·closest_viewed + 0.10·rating − 0.30·closest_disliked
```

"Closest" means the highest content similarity to any book in that group, and that
book's title is used in the explanation ("Similar to *X*, which you liked"). Books
already rated, favourited or viewed are not recommended again.

## 3.4 Architecture decisions

* **One service, two interfaces.** `BookWiseService` is the only thing the CLI and
  Streamlit call, so there is no duplicated logic.
* **Compute once, use many times.** Search text, feature sets and the TF-IDF matrix
  are built once. The TF-IDF matrix is built lazily, only if you actually choose
  the advanced engine.
* **Optional means optional.** scikit-learn, requests, python-dotenv and Streamlit
  are all imported inside `try/except ImportError`, or only by the optional file.
  The CLI runs with plain Python.
* **Deterministic ordering.** Every sort has a tie-breaker, so tests can check
  exact results.
* **Fail softly.** Custom exceptions carry friendly messages. `main.py` is the last
  safety net, and technical details go to the log file.

## 3.5 Ideas for extending the project

* Collaborative filtering using goodbooks-10k `ratings.csv` ("readers who liked X also liked Y")
* An offline evaluation (precision@k) with held-out ratings from that file
* Multiple user profiles
* Caching Google Books results between runs
