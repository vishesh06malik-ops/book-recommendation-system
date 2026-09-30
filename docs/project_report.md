# Project Report Material — BookWise

> Structured material for the final college report. Copy the sections into the
> required report template and rewrite them in your own words.
> Items marked **[FILL IN]** must come from your own runs or details. Do not invent them.

**Student:** [FILL IN name, registration number]
**Course:** Python Essentials · **Platform:** VITyarthi · **Semester:** [FILL IN]
**Repository:** [FILL IN GitHub URL]

---

## 1. Title

**BookWise — Smart Book Discovery & Recommendation System**
*Discover books you'll love.*

## 2. Abstract

Choosing a book from thousands of titles is hard, and most platforms rank by popularity
without explaining their suggestions. BookWise is a command-line application written in
Python that loads a public dataset of 10,000 popular books (goodbooks-10k, CC BY-SA 4.0).
It supports search by title, author, genre, ISBN and keyword, and it recommends books with a
transparent content-based algorithm. The core recommender represents every book as sets of
keywords, genres, authors and title words, and combines Jaccard similarities with documented
weights. A personalisation module ranks books using the user's preferred genres, favourites,
ratings and viewing history, and every recommendation comes with the reasons behind its score. User data
is stored in JSON with atomic writes. Optional enhancements add a TF-IDF/cosine-similarity
recommender (scikit-learn), live search through the Google Books API, and a Streamlit web
interface, all built on the same backend. The core needs only the Python standard library
and works offline. The system is covered by an automated pytest suite of [FILL IN: number from
`pytest` output] tests.

## 3. Introduction

Recommendation systems help users find relevant items in large collections. The two main
families are *collaborative filtering* (users who liked X also liked Y) and *content-based
filtering* (items similar to what you liked). This project applies Python Essentials concepts
(data structures, functions, modules, file handling, exceptions and basic OOP) to build a
content-based book recommender that a beginner can read, run and explain.

## 4. Problem statement

Design and implement a Python command-line application that lets a reader:
search a real book dataset; browse by genre; view book details; obtain the top-N most
similar books to a chosen book, with reasons; maintain favourites, personal ratings and
genre preferences that persist between runs; and receive personalised recommendations.
The core system must work without internet access, API keys or a GUI.

## 5. Objectives

1. Load, validate and clean a legally usable public book dataset.
2. Implement case-insensitive search over five fields and genre browsing.
3. Implement an explainable, weighted similarity recommender in plain Python.
4. Persist user favourites, ratings and preferences safely.
5. Personalise recommendations with an explainable scoring formula.
6. Add optional TF-IDF, Google Books and Streamlit features without core dependency.
7. Verify correctness through automated unit tests and manual testing.

## 6. Existing approach and its problems

| Existing approach | Problem |
|---|---|
| Bestseller / top-rated lists | Same list for everyone; ignores personal taste |
| Large platforms' recommendations | Closed algorithms; no explanation of *why* a book is suggested; need an account and internet |
| Manual browsing by genre | Genres are broad; hard to find books with specific themes |

## 7. Proposed solution

A modular Python application with a command-line interface and an optional web interface
over one shared service layer. It uses content-based filtering on sets of descriptive
features, which is transparent, needs no other users' data, works for a single user, and
can be explained line by line.

## 8. Functional requirements

FR1 Load dataset with clear errors · FR2 Five-mode search · FR3 Genre browsing ·
FR4 Book details with "Not available" for missing data · FR5 Top-N recommendations excluding
the selected book and duplicates, with explanations · FR6 Favourites (add/view/remove,
persisted) · FR7 Validated 1–5 personal ratings · FR8 Preferred genres (set) ·
FR9 Personalised recommendations with explanations · FR10 Optional live search with graceful
failure. (Full table in README.)

## 9. Non-functional requirements

Usability (numbered menus, re-prompting), reliability (atomic saves, corrupted-file backup,
API error handling), portability (Python 3.10+, standard library only for the core), performance
(indexes and TF-IDF built once), security (no committed secrets, key never logged, external
data validated), maintainability (modules, central config, tests), transparency (reasons for
every recommendation).

## 10. System architecture

Layers: User → CLI / Streamlit → `BookWiseService` → Search / Recommendation / User
management → CSV dataset / JSON storage / Google Books API.
Insert the diagrams from `docs/architecture.md`: system architecture (§2), workflow (§4),
use case (§5), component (§6), data flow (§7). (Paste the Mermaid code into
<https://mermaid.live> to export images.)

## 11. Modules

| Module | Responsibility | Main files |
|---|---|---|
| 1. Book Search & Discovery | Title/author/genre/ISBN/keyword search, genre browsing, details | `search_engine.py`, `data_manager.py` |
| 2. Recommendation Engine | Weighted set similarity, top-N, duplicates, explanations; optional TF-IDF | `basic_recommender.py`, `content_recommender.py` |
| 3. User Preferences & Personalisation | Favourites, ratings, genres, history, personalised ranking | `user_manager.py`, `personalization.py`, `storage_manager.py` |
| Supporting | Dataset preparation, API client, interfaces, configuration | `prepare_dataset.py`, `google_books.py`, `cli/`, `app.py`, `config.py` |

## 12. Algorithms

* **Search ranking:** exact > prefix > substring > all-words match; ties broken by popularity.
* **Basic recommendation:** `0.35·J(keywords) + 0.30·J(genres) + 0.15·author + 0.10·J(title) + 0.10·rating`, where `J(A,B) = |A∩B| / |A∪B|`.
* **Advanced recommendation:** TF-IDF vectors of the combined text + cosine similarity `A·B / (‖A‖‖B‖)`.
* **Personalisation:** `0.35·genre_match + 0.40·closest_liked + 0.15·closest_viewed + 0.10·rating − 0.30·closest_disliked`.
* **ISBN-10 validation:** `Σ digit_i × (10 − i) ≡ 0 (mod 11)`.

Include the worked example from `docs/algorithm.md` §1.

## 13. Dataset

goodbooks-10k (Zygmunt Zając, GitHub, CC BY-SA 4.0): `books.csv`, `book_tags.csv`,
`tags.csv`. After preprocessing: [FILL IN from `prepare_dataset.py` output: number of books,
duplicates removed, invalid ISBNs, books without genre]. There are no descriptions or publishers.
Genres are derived from reader tags. See `data/README.md`.

## 14. Implementation

* Language: Python [FILL IN your version]; core uses only the standard library.
* Data structures: see `docs/python_essentials_mapping.md` (lists, tuples, dictionaries,
  sets, dataclasses).
* Key implementation points: pre-computed indexes and feature sets; frozen `Book`
  dataclass; dictionary-based menu dispatch; custom exceptions; atomic JSON writes;
  lazy, cached TF-IDF model; API responses normalised into `Book` objects.
* Screenshots: [FILL IN — main menu, search results, book details, recommendations with
  reasons, personalised recommendations, preferences, error handling example].

## 15. Testing

Automated: pytest suite in `tests/` (data loading, search, recommenders, personalisation,
storage and user data, dataset cleaning rules, API with a fake HTTP session).
Result on your machine: [FILL IN the last line of `pytest` output].
Manual test cases: see the table in `docs/testing.md` and record your own results.

## 16. Results

Report only what you observed and measured. For example:

* Test suite result: [FILL IN]
* Startup time and recommendation time on your computer: [FILL IN — measure with the
  commands in `docs/testing.md`]
* Example recommendation lists for 2–3 books you know, with the explanations shown: [FILL IN]
* Your own qualitative judgement of whether they make sense: [FILL IN]

No accuracy, precision or recall figures are reported, because the project has no labelled
evaluation data (see Limitations and Future scope).

## 17. Limitations

* Only ~10,000 popular books, collected around 2017. No descriptions or publishers.
* Genres come from crowd-sourced tags and can be incomplete.
* Weights are justified by reasoning, not tuned on user data. Recommendation quality has not been evaluated quantitatively.
* Content-based filtering keeps suggestions close to known tastes.
* Single local user profile.

## 18. Future scope

Collaborative filtering and offline evaluation (precision@k) using goodbooks-10k
`ratings.csv`; multiple user profiles; caching live-search results; richer metadata;
a hybrid TF-IDF + weighted score.

## 19. Conclusion

BookWise shows how core Python features (sets, dictionaries, functions, modules, file
handling and exceptions) are enough to build a useful, robust and explainable
recommendation system on real data. The optional machine-learning enhancement is kept
separate, so the project stays understandable while still showing how TF-IDF and cosine
similarity improve text-based matching.

## 20. References

1. Zając, Z. (2017). *goodbooks-10k: a new dataset for book recommendations.* GitHub. https://github.com/zygmuntz/goodbooks-10k (CC BY-SA 4.0).
2. Python Software Foundation. *The Python Standard Library documentation.* https://docs.python.org/3/library/
3. Pedregosa, F. et al. (2011). *Scikit-learn: Machine Learning in Python.* Journal of Machine Learning Research 12, 2825–2830.
4. scikit-learn documentation: `TfidfVectorizer`, `cosine_similarity`. https://scikit-learn.org/stable/
5. Google. *Google Books API — Using the API.* https://developers.google.com/books/docs/v1/using
6. Jaccard, P. (1901). Étude comparative de la distribution florale dans une portion des Alpes et des Jura. *Bulletin de la Société Vaudoise des Sciences Naturelles* 37, 547–579.
7. Manning, C. D., Raghavan, P., Schütze, H. (2008). *Introduction to Information Retrieval.* Cambridge University Press (TF-IDF and cosine similarity).
8. pytest documentation. https://docs.pytest.org/
