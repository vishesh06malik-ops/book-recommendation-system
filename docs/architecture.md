# BookWise — Architecture

## 1. Layers

```
User
 ↓
CLI (main.py → src/cli)   /   Streamlit (app.py, optional)
 ↓
Application service (src/services.py → BookWiseService)
 ↓
Search  /  Recommendation  /  User management
 ↓
Storage (JSON)  /  Dataset (CSV)  /  Google Books API (optional)
```

The main design rule is that **interfaces contain no business logic**. The CLI and
the Streamlit app only read input and show output. Everything else, like searching,
scoring, saving and calling the API, is done by modules that both interfaces share
through `BookWiseService`. So the two interfaces can never behave differently, and
the logic can be tested without typing into menus.

## 2. System architecture diagram

```mermaid
flowchart TB
    user([User])
    subgraph Interfaces
        cli["CLI<br/>main.py, src/cli/"]
        web["Streamlit UI (optional)<br/>app.py"]
    end
    service["BookWiseService<br/>src/services.py"]
    subgraph Modules
        search["Module 1: Search & Discovery<br/>search_engine.py"]
        basic["Module 2: Recommendation Engine<br/>basic_recommender.py"]
        tfidf["TF-IDF recommender (optional)<br/>content_recommender.py"]
        personal["Module 3: Personalisation<br/>personalization.py"]
        users["User manager<br/>user_manager.py"]
        api["Google Books client (optional)<br/>google_books.py"]
    end
    subgraph Data
        catalog["BookCatalog + Book model<br/>data_manager.py, book.py"]
        csv[("data/books.csv")]
        json[("user_data/profile.json")]
        google[("Google Books API")]
    end
    user --> cli & web
    cli & web --> service
    service --> search & basic & tfidf & personal & users & api
    personal --> basic
    search & basic & tfidf --> catalog
    catalog --> csv
    users --> storage["storage_manager.py"] --> json
    api --> google
```

## 3. Component responsibilities

| Component | File | Responsibility |
|---|---|---|
| Entry point | `main.py` | Sets up logging, creates the service, starts the CLI, and turns crashes, Ctrl+C and dataset errors into friendly messages |
| CLI | `src/cli/cli_app.py`, `input_helpers.py` | Menus, numbered lists, paging, input validation |
| Streamlit UI | `app.py` | Optional web pages that call the same service |
| Service | `src/services.py` | One object that loads everything once and exposes every feature as a method; caches the TF-IDF model |
| Configuration | `src/config.py` | Paths, limits, recommendation weights, API settings |
| Book model | `src/models/book.py` | Immutable `Book` dataclass plus display helpers ("Not available") |
| Data manager | `src/data/data_manager.py` | Reads and validates the CSV, converts rows into `Book`s, builds the id and genre indexes (`BookCatalog`) |
| Search engine | `src/search/search_engine.py` | Title, author, genre, ISBN and keyword search with ranking |
| Basic recommender | `src/recommendation/basic_recommender.py` | Weighted set similarity, top-N, duplicate removal, explanations |
| Advanced recommender | `src/recommendation/content_recommender.py` | TF-IDF vectors + cosine similarity, built once |
| Personalisation | `src/recommendation/personalization.py` | Ranks the catalogue for the user's genres, likes, dislikes and history |
| User manager | `src/user/user_manager.py` | Favourites, ratings (validated), genre preferences, history |
| Storage | `src/storage/storage_manager.py` | Atomic JSON save; backs up corrupted files |
| API client | `src/api/google_books.py` | HTTP request, error handling, JSON → `Book` normalisation |
| Helpers | `src/utils/helpers.py` | Text normalisation, tokenising, Jaccard, formatting, logging setup |
| Dataset preparation | `scripts/prepare_dataset.py` | One-time download and cleaning of goodbooks-10k |

## 4. Application workflow

```mermaid
flowchart TD
    start([python main.py]) --> load{Load data/books.csv}
    load -- missing or invalid --> fail[Show friendly message and exit]
    load -- ok --> menu[Show main menu]
    menu --> choice{Choice}
    choice -- 1 --> s[Search: choose mode, enter text] --> results[Numbered results] --> details
    choice -- 2 --> g[Browse genres] --> results
    choice -- 3 --> find[Find book by title/ISBN/ID] --> details[Book details]
    choice -- 4 --> find2[Find book] --> recs[Choose N and engine → recommendations with reasons]
    choice -- 5 --> fav[Favourites: open/remove]
    choice -- 6 --> rate[Rate a book 1-5]
    choice -- 7 --> pref[Select genres / reset profile]
    choice -- 8 --> pers[Personalised recommendations]
    choice -- 9 --> about[About]
    choice -- 0 --> exit([Goodbye])
    details --> act{Action}
    act -- favourite / rate --> save[(profile.json)]
    act -- recommendations --> recs
    fav & rate & pref --> save
    recs & pers --> details
```

After every option finishes, the program returns to the main menu (the `while True` loop in `BookWiseCLI.run`).

## 5. Use-case diagram

Mermaid has no UML use-case diagram, so a flowchart is used in the same style: the
actor is on the left and the use cases are in the system boundary.

```mermaid
flowchart LR
    reader((Reader))
    gb((Google Books<br/>service))
    subgraph BookWise
        uc1([Search books])
        uc2([Browse genres])
        uc3([View book details])
        uc4([Get similar books])
        uc5([Manage favourites])
        uc6([Rate a book])
        uc7([Set genre preferences])
        uc8([Get personalised recommendations])
        uc9([Live search online])
    end
    reader --- uc1 & uc2 & uc3 & uc4 & uc5 & uc6 & uc7 & uc8 & uc9
    uc9 --- gb
    uc1 -. includes .-> uc3
    uc4 -. includes .-> uc3
```

## 6. Module / component diagram (imports)

```mermaid
flowchart LR
    main[main.py] --> cli[cli.cli_app] --> services
    app[app.py] --> services
    services --> data[data.data_manager] --> book[models.book]
    services --> search[search.search_engine]
    services --> basic[recommendation.basic_recommender]
    services --> content[recommendation.content_recommender]
    services --> personal[recommendation.personalization]
    services --> user[user.user_manager] --> storage[storage.storage_manager]
    services --> api[api.google_books] --> book
    basic --> search
    content --> basic
    personal --> basic
    book --> helpers[utils.helpers]
    search --> helpers
    basic --> helpers
    config[config] -.used by all.- services
```

There are no circular imports. Lower layers (models, helpers, storage) never import
higher layers (services, interfaces).

## 7. Data-flow diagram

```mermaid
flowchart LR
    raw[(goodbooks-10k raw CSVs)] -->|prepare_dataset.py: clean, derive genres| csv[(data/books.csv)]
    csv -->|load_books: validate rows| books[list of Book]
    books --> idx[BookCatalog indexes<br/>id → Book, genre → Books]
    books --> feats[Feature sets per book<br/>keywords, genres, authors, title words]
    books --> tfidf[TF-IDF matrix<br/>built on first use]
    query[/User query/] --> se[SearchEngine] --> out[/Result list/]
    idx --> se
    feats --> rec[Basic / personalised scoring] --> out2[/Top-N + reasons/]
    tfidf --> rec
    actions[/Favourite, rate, prefer genre, view/] --> um[UserManager] -->|atomic save| profile[(profile.json)]
    profile -->|signals| rec
    gbq[/Live query/] --> gapi[Google Books API] -->|JSON → normalize_volume| books2[Book objects]
```

## 8. Key design decisions

| Decision | Reason |
|---|---|
| The core uses only the standard library (`csv`, `json`, `re`, `dataclasses`) | It runs anywhere with plain Python, and it shows Python fundamentals instead of hiding them behind libraries |
| CSV for books, JSON for user data (not SQLite) | The book data is read-only and tabular, so CSV fits. The user data is a small nested structure (lists, a dict, a set), which maps directly to JSON. A database would add complexity without a clear benefit at this size |
| `Book` is a frozen dataclass with tuple fields | A single, typed shape for local and API books. Being immutable prevents accidental edits of shared data |
| Features and indexes are computed once | Searching and recommending then only compare pre-built sets |
| TF-IDF is optional and built lazily | The core never depends on scikit-learn. The ~1 s build cost is paid only if the user asks for the advanced engine, and only once |
| One custom exception per failure area (`DatasetError`, `StorageError`, `InvalidRatingError`, `GoogleBooksUnavailable`) | Interfaces catch a small set of clear errors and show friendly text. Technical details go to `logs/bookwise.log` |
| Configuration in one file | Weights and limits can be changed and justified in one place |
