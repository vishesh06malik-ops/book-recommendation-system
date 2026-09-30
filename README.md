# BookWise — Smart Book Discovery & Recommendation System

> *Discover books you'll love.*

BookWise is a command-line Python application for searching a real dataset of
books, browsing genres, and getting **explainable** recommendations, both
"books similar to this one" and "books for me" (from your favourites, ratings
and preferred genres).

*Course:* Python Essentials · *Platform:* VITyarthi — Evaluated Course Project

---

## Problem statement

Readers struggle to choose their next book from a huge number of titles. Store
rankings show what is popular, not what fits a particular reader, and they rarely
explain *why* a book is suggested. BookWise is a small, offline, transparent tool
that searches a public dataset of 10,000 books and recommends titles with a clear
reason for every suggestion.

## Motivation

The problem naturally uses the whole Python Essentials syllabus: string processing
for search, **sets and dictionaries** for similarity, **file handling** for CSV and
JSON, **exceptions** for robustness, **modules and classes** for structure. The
result is something useful that can be explained line by line.

## Objectives

1. Load and clean a real, legally usable book dataset.
2. Let users search by title, author, genre, ISBN and keyword, and browse genres.
3. Recommend similar books with a transparent, weighted Python algorithm.
4. Store favourites, personal ratings and genre preferences between runs.
5. Personalise recommendations from those preferences, with explanations.
6. Offer optional enhancements (TF-IDF, Google Books, web UI) without making the core depend on them.
7. Verify behaviour with automated tests.

## Features

### Core (plain Python, works offline)

| # | Menu option | What it does |
|---|---|---|
| 1 | Search Books | Title, author, genre, ISBN (ISBN-10/13, with or without hyphens) or keyword search; ranked, numbered results |
| 2 | Browse Genres | 22 genres with book counts; most-rated books first; paged lists |
| 3 | View Book Details | Title, author, genre, year, external rating, your rating, ISBN, keywords, description |
| 4 | Get Recommendations | Top 5/10/15 similar books, each with "Similar because …" reasons |
| 5 | My Favourites | View, open and remove favourites (saved immediately) |
| 6 | Rate a Book | Personal 1–5 ★ rating, validated, kept separate from the dataset's average rating |
| 7 | My Preferences | Select or unselect preferred genres; reset profile |
| 8 | Personalized Recommendations | Ranked for your genres, liked and disliked books, and viewing history, with reasons |
| 9 | About Project | Dataset credit and feature status |

### Optional enhancements

* **Advanced recommender**: TF-IDF + cosine similarity (scikit-learn). If scikit-learn is missing, the basic engine is used automatically.
* **Live search**: Google Books API (Search → option 6). Works without a key for light use. Every failure is handled gracefully.
* **Web interface**: Streamlit (`app.py`) using the same backend.

## Functional requirements

| ID | Requirement |
|---|---|
| FR1 | The system shall load books from `data/books.csv` and report a clear error if the file is missing or invalid. |
| FR2 | The system shall search by title, author, genre, ISBN and keyword, case- and whitespace-insensitively. |
| FR3 | The system shall list genres and the books in each genre. |
| FR4 | The system shall display full details of a selected book, showing "Not available" for missing fields. |
| FR5 | The system shall recommend the top N (5/10/15) similar books, excluding the selected book and duplicates, with explanations. |
| FR6 | The system shall let the user add, view and remove favourites, persisted between runs. |
| FR7 | The system shall let the user rate books 1–5 and reject any other input. |
| FR8 | The system shall let the user select preferred genres (no duplicates). |
| FR9 | The system shall produce personalised recommendations from preferences, ratings, favourites and history, with explanations. |
| FR10 | The system may search Google Books online. Failure must not affect the other features. |

## Non-functional requirements

| Area | Requirement |
|---|---|
| Usability | Numbered menus; invalid input re-prompts instead of crashing; no stack traces or raw data structures shown |
| Reliability | Atomic saves; corrupted profile is backed up, not lost; all API errors handled |
| Portability | Python 3.10+; the core uses only the standard library, `pathlib` paths and UTF-8 files so it is not tied to one OS (tested with Python 3.10–3.13 on Linux) |
| Performance | Data loaded and indexed once per run; TF-IDF built once and cached (see `docs/testing.md` for measured timings) |
| Security | No secrets in code or git; API key from environment only and never logged; no `eval`/`exec`; external JSON validated |
| Maintainability | Modular packages, central `config.py`, docstrings, automated tests |
| Transparency | Every recommendation includes the reasons that produced its score |

## Technologies

| Technology | Used for | Required? |
|---|---|---|
| Python 3.10+ standard library (`csv`, `json`, `re`, `dataclasses`, `pathlib`, `logging`) | Entire core application | **Yes** |
| scikit-learn | TF-IDF + cosine similarity | Optional |
| requests, python-dotenv | Google Books API, `.env` loading | Optional |
| Streamlit | Web interface | Optional |
| pytest | Automated tests | For testing |

## Architecture

```
User → CLI (main.py) / Streamlit (app.py) → BookWiseService → Search | Recommendation | User
                                                            → CSV dataset | JSON profile | Google Books API
```

Both interfaces call the same `BookWiseService`, so no logic is duplicated.
Diagrams (system, workflow, use case, components, data flow): **[docs/architecture.md](docs/architecture.md)**.

## Dataset

**goodbooks-10k** by Zygmunt Zając, <https://github.com/zygmuntz/goodbooks-10k>,
licensed **CC BY-SA 4.0**. `data/books.csv` is a cleaned adaptation, distributed
under the same licence. It includes validated ISBNs, and genres and keywords derived
from Goodreads reader tags. The dataset has **no descriptions or publishers**, so these show
"Not available". Full details, columns, preprocessing and limitations: **[data/README.md](data/README.md)**.

## Recommendation algorithm (summary)

```
score = 0.35·Jaccard(keywords) + 0.30·Jaccard(genres) + 0.15·same_author
      + 0.10·Jaccard(title words) + 0.10·rating_signal
```

Jaccard similarity = shared items ÷ all different items. Weights live in
`src/config.py` with a justification for each. Details, the TF-IDF/cosine version,
the personalisation formula and worked examples: **[docs/algorithm.md](docs/algorithm.md)**.

## Installation

The core needs **only Python 3.10+**. Installing the requirements enables the optional features and pytest.

**macOS / Linux**
```bash
cd bookwise
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**Windows**
```bash
cd bookwise
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## Configuration

* All settings (paths, weights, limits, timeouts) are in `src/config.py`.
* **Optional Google Books key:** copy `.env.example` to `.env` and replace the placeholder:
  ```
  GOOGLE_BOOKS_API_KEY=your_api_key_here
  ```
  `.env` is ignored by git. Never commit it.
* Optional environment variables: `BOOKWISE_DATASET` (another CSV) and `BOOKWISE_USER_DATA` (another profile file).

## Running (terminal)

```bash
python main.py        # use python3 on macOS/Linux if "python" is not found
```

To rebuild `data/books.csv` from the original goodbooks-10k files (needs internet once):

```bash
python scripts/prepare_dataset.py
```

## Optional: Streamlit web interface

```bash
pip install streamlit        # included in requirements.txt
streamlit run app.py
```

Pages: Home, Search, Discover, Recommendations (similar + for you), Favourites, Profile, About.

## Testing

```bash
pytest
```

The tests never access the internet (the Google Books client is tested with a fake
HTTP session). Test coverage, manual test cases and measured results are in
**[docs/testing.md](docs/testing.md)**.

## Project structure

```
bookwise/
├── main.py                     # CLI entry point
├── app.py                      # optional Streamlit UI
├── requirements.txt  .gitignore  .env.example  pytest.ini
├── data/
│   ├── books.csv               # cleaned goodbooks-10k (CC BY-SA 4.0)
│   └── README.md               # dataset documentation
├── scripts/
│   └── prepare_dataset.py      # download + clean the dataset
├── src/
│   ├── config.py               # all settings and weights
│   ├── services.py             # BookWiseService (shared by CLI and Streamlit)
│   ├── models/book.py          # Book dataclass
│   ├── data/data_manager.py    # CSV loading, BookCatalog
│   ├── search/search_engine.py # Module 1: search & discovery
│   ├── recommendation/
│   │   ├── basic_recommender.py    # Module 2: weighted set similarity
│   │   ├── content_recommender.py  # optional TF-IDF + cosine
│   │   └── personalization.py      # Module 3: personalised ranking
│   ├── user/user_manager.py    # favourites, ratings, preferences, history
│   ├── storage/storage_manager.py  # safe JSON save/load
│   ├── api/google_books.py     # optional Google Books client
│   ├── cli/                    # menus and input validation
│   └── utils/helpers.py        # text, similarity and formatting helpers
├── tests/                      # pytest suite + synthetic fixture data
└── docs/
    ├── architecture.md   algorithm.md   testing.md   project_guide.md
    ├── python_essentials_mapping.md   project_report.md   viva_questions.md
```

Created at run time and ignored by git: `user_data/` (your profile), `logs/`, `data/raw/`.

## Limitations

* ~10,000 popular books, as collected around 2017. Newer or niche books are missing (the optional live search helps).
* No descriptions or publishers in the dataset. Genres are derived from crowd-sourced tags.
* Recommendation quality has **not** been measured against real user feedback. No accuracy figures are claimed.
* Content-based only: suggestions stay close to what the user already likes.
* One local user profile per data file.

## Future scope

* Collaborative filtering with goodbooks-10k's `ratings.csv`, plus an offline precision@k evaluation.
* Multiple user profiles.
* Caching live search results; richer metadata (descriptions) from an open dataset.
* A hybrid score that combines TF-IDF and the weighted Python score.

## Credits and licence

* Dataset: goodbooks-10k © Zygmunt Zając, CC BY-SA 4.0. `data/books.csv` is an adapted version under CC BY-SA 4.0.
* Libraries: scikit-learn, requests, python-dotenv, Streamlit, pytest (each under its own licence).
* Source code: original work written for this course project.
