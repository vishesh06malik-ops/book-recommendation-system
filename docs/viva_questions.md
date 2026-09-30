# Viva Preparation — BookWise

Answers are short on purpose. Explain them in your own words, and open the file
mentioned if the examiner wants to see code.

## A. Python fundamentals

**1. What is the difference between a list and a tuple?**
Both are ordered sequences. A list is *mutable* (you can append, remove, change items)
and a tuple is *immutable*. In BookWise, favourites are a list because they change,
and a book's `authors` is a tuple because loaded book data should never change.
Tuples are also used for fixed data such as `RATING_SCALE = (1, 5)`.

**2. What is the difference between a list and a set?**
A list keeps order and allows duplicates. A set has no order and **no duplicates**,
and it checks membership (`x in s`) very fast. Preferred genres are a set, so the same
genre can't be stored twice. Similarity uses set intersection (`&`) and union (`|`).

**3. What is a dictionary and where do you use it?**
A collection of key → value pairs with fast lookup by key. Examples: `_by_id`
(book id → Book), `ratings` (book id → stars), `RECOMMENDER_WEIGHTS`
(component → weight) and the CLI menu (number → function).

**4. Why use a dictionary to find a book instead of a loop?**
A loop checks up to 10,000 books one by one. A dictionary jumps straight to the
key, and the time does not grow with the number of books.

**5. What is a function? Why so many small ones?**
A named, reusable block of code with inputs (parameters) and an output (return value).
Small functions such as `jaccard_similarity` or `clean_isbn` do one job, so they are
easy to read, reuse and test on their own.

**6. What is a module and a package?**
A module is one `.py` file. A package is a folder of modules with an `__init__.py`.
BookWise is split into packages such as `src/search`, `src/recommendation` and `src/user`.

**7. What are exceptions? Give examples from the project.**
Objects that represent errors. With `try/except` the program can handle them instead of
crashing. BookWise catches specific ones (`ValueError` for bad numbers,
`json.JSONDecodeError` for a corrupted profile, `requests.exceptions.Timeout` for a slow
API) and defines its own: `DatasetError`, `StorageError`, `InvalidRatingError`,
`GoogleBooksUnavailable`.

**8. Why not write `except:` everywhere?**
A bare `except` also hides programming mistakes and even Ctrl+C. Catching specific
exceptions means we only handle errors we expect and understand. The single broad
handler, in `main.py`, only logs the error and shows a polite message.

**9. Why use `with open(...)`?**
It is a context manager. The file is closed automatically, even if an error occurs
while reading or writing.

**10. What is a class and an object?**
A class is a blueprint and an object is one thing built from it. `BasicRecommender` is
a class, and `service.basic` is an object of it that holds the features of all
10,000 books.

**11. What is a dataclass? Why is `Book` frozen?**
`@dataclass` writes `__init__`, `__repr__` and `__eq__` for us from the listed fields.
`frozen=True` makes objects read-only, so no module can accidentally change the shared
book data.

**12. What are `@property`, `@classmethod` and `@staticmethod`?**
A property is a method used like an attribute (`book.year_text`). A classmethod gets the
class instead of an object and is used as an alternative constructor
(`BookCatalog.from_csv`). A staticmethod is a plain function placed inside a class
because it belongs there logically (`UserManager.validate_rating`).

**13. What is JSON? Why store user data in JSON?**
JSON is a text format for lists, dictionaries, strings and numbers. The user profile
is small and nested, and it maps directly onto JSON. It is also human-readable and
needs no database server.

**14. What is the difference between CSV and JSON here?**
CSV is a table (one book per row, fixed columns), which suits the book dataset.
JSON holds nested structures (a list of favourites, a dict of ratings), which suits
the profile.

**15. What is a list comprehension?**
A short way to build a list from a loop, e.g.
`[book for book in books if book.rating]`. BookWise also uses set and dict
comprehensions.

## B. About the project

**16. Why did you choose this problem?**
Readers struggle to find books that match their taste among thousands of titles. It is a
real problem, and it needs almost every Python Essentials topic: strings for search,
sets and dictionaries for similarity, files for data, exceptions for robustness.

**17. What is the problem statement?**
Build a command-line application that lets a user search a real book dataset, browse
genres, and receive explainable recommendations, both for a chosen book and
personalised from their favourites, ratings and preferred genres. It must run
offline without any API key.

**18. What are the modules?**
(1) Book Search & Discovery, (2) Recommendation Engine, (3) User Preferences &
Personalisation. There are also supporting modules: data manager, storage, optional
Google Books API, and the interfaces.

**19. How does search work?**
The search text is prepared once. Each search loops over the books and gives
each match a score (e.g. exact title 4, starts-with 3, contains 2, all words 1),
then sorts by score and popularity. It is case- and whitespace-insensitive. ISBN
search accepts hyphens, missing zeros and ISBN-13.

**20. How does recommendation work?**
Each book becomes sets of keywords, genres, authors and title words. For a selected
book, every other book gets
`0.35·keywords + 0.30·genre + 0.15·author + 0.10·title + 0.10·rating`, where each part
is a Jaccard similarity (shared ÷ total). The selected book and its other editions are
removed, results are sorted, and the top N are shown with reasons.

**21. What is Jaccard similarity?**
|A ∩ B| ÷ |A ∪ B|. For example, {habits, productivity, behavior} and
{behavior, brain, habits} share 2 of 4 different words, so the similarity is 0.5.

**22. How did you choose the weights?**
By how informative each signal is. Keywords are the most specific. Genres are
reliable but broad. Author is a strong but yes/no signal. Title words mostly detect
series. Rating is only a small tie-breaker. The weights are documented in
`config.py`. They were not tuned with user data, because we have none (honest limitation).

**23. Why content-based recommendation?**
It needs only book information, works for a single new user (no "cold start" for the
user), and every result can be explained. Collaborative filtering would need many
users' ratings.

**24. What is TF-IDF?**
A way to turn text into numbers. TF is how often a word appears in this book. IDF is
how rare the word is across all books. Their product is high for words that are
distinctive for this book, such as "vampires", and low for words found everywhere,
such as "fiction".

**25. What is cosine similarity?**
`cos(A,B) = (A·B) / (‖A‖‖B‖)`: the cosine of the angle between two vectors. 1 means
the same direction (same word proportions), 0 means nothing in common. Example: (1,1,0)
and (1,0,1) → 1 / (√2·√2) = 0.5.

**26. Why keep the basic recommender if TF-IDF exists?**
The basic one needs no library, can be calculated by hand, and is the core of the Python
Essentials work. TF-IDF is an optional enhancement. If scikit-learn is missing, BookWise
automatically uses the basic engine.

**27. How is personalisation implemented?**
From the profile: preferred genres, liked books (favourites + ratings ≥ 4), disliked
books (ratings ≤ 2) and recent history. The score is
`0.35·genre match + 0.40·similarity to closest liked + 0.15·similarity to closest viewed
+ 0.10·rating − 0.30·similarity to closest disliked`. The reasons name the preferred
genre or the liked book.

**28. How is data stored?**
Books: `data/books.csv` (read-only). User data: `user_data/profile.json`, saved after
every change using a temporary file and `os.replace`, so a crash can't corrupt it.

**29. What happens if the JSON file is corrupted?**
It is renamed to `profile.json.corrupt-<timestamp>` (not deleted), the error is logged,
and BookWise continues with an empty profile.

**30. What happens if the Google Books API fails?**
All failures (no internet, timeout, HTTP 400/403/429/5xx, invalid JSON) become one
`GoogleBooksUnavailable` exception. The user sees "Live book search is currently
unavailable. You can continue using the local book database." The core app never needs
the API.

**31. How do you keep the API key secret?**
It is read from an environment variable (optionally from a `.env` file). `.env` is in
`.gitignore`, only `.env.example` with a placeholder is committed, and the key is never
printed or logged. A test checks that it does not appear in the logs.

**32. Where does the dataset come from? Did you make up any data?**
goodbooks-10k (Zygmunt Zając, CC BY-SA 4.0) on GitHub. Nothing is invented. Descriptions and
publishers are not in the dataset, so they show "Not available". Genres are derived
from real reader tags with a documented mapping.

**33. How did you handle missing and bad data?**
Invalid numbers become `None`, invalid ISBNs (failed check digit) become empty, rows
without id/title are skipped, repeated ids and duplicate works are removed. Missing
values are shown as "Not available".

**34. How did you test the project?**
With pytest: over 100 tests covering data loading (valid, missing file, missing columns,
bad rows), search, recommendations (excluding the selected book, duplicates, too few
results, deterministic order), user data, storage, the dataset cleaning rules, and the
API with a fake network session, so tests never go online. The CLI was also tested manually.

**35. What are the limitations?**
Only ~10,000 popular books up to about 2017. There are no descriptions. Genres come from
crowd tags. Recommendation quality has not been measured against real users. There is
one local user profile. Content-based results stay close to what you already read.

**36. How can the project be improved?**
Collaborative filtering with the dataset's ratings file, an offline evaluation
(precision@k), multiple user profiles, caching API results, and a larger dataset with
descriptions.

**37. Why is the CLI the main interface and Streamlit optional?**
The course requires a program that runs from the command line without a GUI. Streamlit
is only a second view over the same `BookWiseService`, so there is no duplicated logic.
