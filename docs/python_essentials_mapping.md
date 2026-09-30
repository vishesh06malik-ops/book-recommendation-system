# Python Essentials → BookWise mapping

Every concept below is **actually used** in the project. The "Where" column points to
the file and function so you can open it during the viva.

## Core concepts

| Concept | Project usage | Where |
|---|---|---|
| **Variables & data types** | `str` titles, `int` years and rating counts, `float` ratings, `bool` flags, `None` for missing values | `models/book.py` (`Book` fields), `config.py` |
| **Type hints** | Every function states its parameter and return types, e.g. `def search(self, query: str, mode: str = "title") -> list[Book]` | all modules |
| **Arithmetic operators** | Weighted score `sum(weight * value)`, rating signal `(rating − 1) / 4`, ISBN check digit `total % 11` | `basic_recommender.weighted_score`, `extract_features`, `scripts/prepare_dataset.is_valid_isbn10` |
| **Comparison & logical operators** | Range checks `low <= number <= high`, `and` / `or` / `not` in validation | `user_manager.validate_rating`, `cli/input_helpers.ask_int` |
| **Membership operator `in`** | `if book.id in exclude_ids`, `query in title` | `basic_recommender.recommend`, `search_engine._score_title` |
| **Set operators** `&`, `\|`, `-`, `<=` | Intersection and union for Jaccard similarity; `words <= title_words` (subset) for "every word matches"; `liked − disliked` | `helpers.jaccard_similarity`, `search_engine._score_title`, `user_manager.liked_ids` |
| **Conditionals** (`if / elif / else`) | Title-match ranking (exact > starts-with > contains > all words); menu options; HTTP status handling | `search_engine._score_title`, `cli_app.show_book`, `google_books.search_google_books` |
| **`while` loops** | Main menu loop until 0 is chosen; keep asking until input is valid; paging | `cli_app.run`, `input_helpers.ask_int`, `cli_app.choose_book` |
| **`for` loops** | Compare the selected book with every other book; read CSV rows | `basic_recommender.recommend`, `data_manager.load_books` |
| **`break` / `continue`** | Stop after N results; skip excluded or duplicate books | `basic_recommender.select_top`, `recommend` |
| **`enumerate`** | Numbered lists shown to the user ("1. …, 2. …") | `cli_app.choose_book`, `print_recommendations` |
| **Strings** | `lower()`, `strip()`, `split()`, `join()`, `startswith()`, `replace()`, slicing, f-strings, `textwrap` | `helpers.normalize_text`, `helpers.shorten`, `search_engine.compact` |
| **Regular expressions** (`re`) | Split text into words, validate ISBN format, recognise shelf tags, strip HTML | `helpers.tokenize`, `prepare_dataset.clean_isbn`, `NOISE_TAG_PATTERN`, `google_books.normalize_volume` |
| **Lists** | Search results, recommendation lists, favourites (ordered), viewing history (most recent first) | `search_engine.search`, `user_manager.UserProfile` |
| **List methods** | `append`, `insert(0, …)`, `remove`, `sort(key=…)`, slicing `[:limit]` | `user_manager.record_view`, `remove_favourite`, `search_engine.search` |
| **Tuples** | Immutable book fields (`authors`, `categories`); fixed menus `SEARCH_MODES`; `RATING_SCALE = (1, 5)`; returning two values `(score, components)`; `(genre, count)` pairs; tuple sort keys | `models/book.py`, `search_engine.py`, `config.py`, `basic_recommender.similarity`, `data_manager.genres` |
| **Tuple unpacking** | `low, high = config.RATING_SCALE`; `for genre, count in genres` | `user_manager.validate_rating`, `cli_app.browse_genres` |
| **Dictionaries** | Book lookup by id (`_by_id`), genre index, user ratings (`book_id → stars`), recommender weights, CLI menu dispatch (`number → method`), search-mode dispatch (`mode → scoring function`) | `data_manager.BookCatalog`, `user_manager`, `config.py`, `cli_app.__init__`, `search_engine.search` |
| **Dictionary methods** | `get()` with default, `setdefault()`, `items()`, `dict.fromkeys()` (remove duplicates, keep order) | `data_manager.BookCatalog.__init__`, `_split_multi` |
| **Sets** | Keyword/genre/author sets for similarity; preferred genres (no duplicates); ids already seen; excluded ids | `basic_recommender.extract_features`, `user_manager.UserProfile.preferred_genres`, `data_manager.load_books` |
| **frozenset** | Stop-word list that can never be changed | `helpers.STOPWORDS` |
| **Comprehensions** | List, set and dict comprehensions everywhere, e.g. `{book.id: book for book in books}` | `data_manager`, `basic_recommender`, `search_engine` |
| **Generator expression** | Documents fed to TF-IDF without building a list | `content_recommender.AdvancedContentRecommender.__init__` |
| **`sorted` / `sort` with `key` and `lambda`** | Sort by score (descending), then rating count, then id → deterministic order | `basic_recommender.select_top`, `search_engine.search` |
| **Built-ins** | `len`, `sum`, `min`, `max`, `any`, `isinstance` | `basic_recommender`, `personalization`, `google_books.normalize_volume` |

## Functions

| Concept | Project usage | Where |
|---|---|---|
| Defining small functions | Each does one job: `tokenize`, `jaccard_similarity`, `clean_isbn`, `row_to_book`, `edition_key` … | `helpers.py`, `data_manager.py`, `prepare_dataset.py` |
| Default parameters | `recommend(book, n=config.DEFAULT_RECOMMENDATION_COUNT)` | `basic_recommender.py` |
| Returning several values | `similarity()` returns `(score, components)` | `basic_recommender.py` |
| Docstrings | Every important function explains what it does and why | all modules |
| Functions as values | A dict maps search modes to scoring functions; callbacks passed to Streamlit buttons; `save_safely(action, …)` receives a function | `search_engine.search`, `app.py`, `cli_app.save_safely` |
| `lambda` | Sort keys, small callbacks | `search_engine.search`, `cli_app.show_book` |

## Modules and packages

| Concept | Project usage |
|---|---|
| Own modules | 14 source files, each with one responsibility (see `docs/architecture.md`) |
| Packages (`__init__.py`) | `src/`, `src/models/`, `src/search/` … |
| `import` / `from … import` | e.g. `from src.models.book import Book` |
| Standard library | `csv`, `json`, `re`, `os`, `pathlib`, `dataclasses`, `logging`, `textwrap`, `urllib`, `subprocess`, `shutil`, `time` |
| Third-party (optional) | `requests`, `python-dotenv`, `scikit-learn`, `streamlit`, `pytest` |
| Optional import with fallback | `try: from sklearn … except ImportError: ADVANCED_AVAILABLE = False` (`content_recommender.py`) |
| `if __name__ == "__main__":` | `main.py`, `scripts/prepare_dataset.py` |

## File handling

| Concept | Project usage | Where |
|---|---|---|
| `with open(...)` | Every file is opened with a context manager, so it is always closed | `data_manager.load_books`, `storage_manager` |
| Encodings | `utf-8` everywhere; `utf-8-sig` accepts Excel-saved CSVs | `data_manager.load_books` |
| CSV reading/writing | `csv.DictReader` / `csv.DictWriter` | `data_manager.py`, `prepare_dataset.py` |
| JSON reading/writing | `json.load` / `json.dump` for the user profile | `storage_manager.py` |
| Safe (atomic) writes | Write a `.tmp` file, then `os.replace` | `storage_manager.save_json` |
| `pathlib.Path` | Portable paths on Windows/macOS/Linux | `config.py` |

## Exception handling

| Concept | Project usage | Where |
|---|---|---|
| `try / except` with **specific** exceptions | `ValueError`, `OSError`, `json.JSONDecodeError`, `csv.Error`, `UnicodeDecodeError`, `requests.exceptions.Timeout` … | throughout |
| Custom exception classes | `DatasetError`, `StorageError`, `InvalidRatingError(ValueError)`, `GoogleBooksUnavailable` | `data_manager`, `storage_manager`, `user_manager`, `google_books` |
| `raise … from …` | Keep the technical cause for the log, show a simple message to the user | `data_manager.load_books` |
| Last-resort handler | `main.py` catches `KeyboardInterrupt`/`EOFError` (Ctrl+C) and unexpected errors: no stack trace is shown | `main.py` |
| Input validation | Invalid menu choices, numbers, ratings and empty searches never crash | `input_helpers.ask_int`, `user_manager.validate_rating` |

## Object-oriented programming (used only where it helps)

| Concept | Project usage |
|---|---|
| Classes and objects | `BookCatalog`, `SearchEngine`, `BasicRecommender`, `AdvancedContentRecommender`, `PersonalizedRecommender`, `UserManager`, `BookWiseService`, `BookWiseCLI`. Each keeps data together with the operations on it |
| `__init__` and attributes | e.g. `BasicRecommender.__init__` pre-computes features once |
| `@dataclass` | `Book` (frozen = immutable), `UserProfile`, `Recommendation`, `UserSignals` |
| `@property` | `Book.author_text`, `Book.year_text` |
| `@classmethod` | `BookCatalog.from_csv`, `UserProfile.from_dict` (alternative constructors) |
| `@staticmethod` | `UserManager.validate_rating`, the search scoring functions |
| Inheritance | Custom exceptions inherit from `Exception` / `ValueError` |
| Polymorphism (duck typing) | The basic and TF-IDF recommenders both provide `recommend()` and `name`, so `BookWiseService.recommend` uses either one without `if` checks |
| Composition | `BookWiseService` *has* a catalog, a search engine, recommenders and a user manager |
| Dunder method | `BookCatalog.__len__` lets you write `len(catalog)` |

## Beyond the basics (used with a clear purpose)

| Concept | Purpose | Where |
|---|---|---|
| APIs / HTTP (`requests`) | Optional live search | `google_books.py` |
| Environment variables | API key and alternative data paths, never hard-coded | `google_books.get_api_key`, `config.py` |
| Logging | Technical errors go to `logs/bookwise.log`, not to the screen; API keys are never logged | `helpers.setup_logging` |
| Caching | TF-IDF matrix built once; features and indexes built once | `services._advanced_recommender`, `BasicRecommender.__init__` |
| Unit testing (`pytest`) | Fixtures, `parametrize`, `tmp_path`, `monkeypatch`, fake HTTP session | `tests/` |
