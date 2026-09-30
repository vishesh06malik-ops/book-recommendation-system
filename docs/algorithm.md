# BookWise — Recommendation Algorithms

BookWise has three ranking methods:

1. **Basic recommender** (core, pure Python): "books similar to this book"
2. **Advanced recommender** (optional, scikit-learn): the same question answered with TF-IDF and cosine similarity
3. **Personalised recommender** (core, pure Python): "books for *me*"

All three are **content-based**. They compare what books *are* (genres, themes,
authors, words), not what other users did. The dataset has no per-user data that
we use, and this approach can explain every result.

---

## 1. Basic recommender (`src/recommendation/basic_recommender.py`)

### Step by step

```
Selected book
      ↓
Extract features      → four Python sets + one number
      ↓
Compare with every other book (loop over 10,000 books)
      ↓
Calculate similarity  → five components between 0 and 1, weighted sum
      ↓
Remove the selected book, other editions of it, and books with no real similarity
      ↓
Sort by score (ties: more ratings first, then id, so the order is always the same)
      ↓
Return Top N (5, 10 or 15), each with an explanation
```

### Features of one book

| Feature | Python type | Example ("Dragon Realm (Realm #1)") |
|---|---|---|
| keywords | `set[str]` | `{"magic", "dragons", "adventure"}` |
| genres | `set[str]` | `{"Fantasy", "Young Adult"}` |
| authors | `set[str]` (letters only, lower-case) | `{"alicestone"}` |
| title words | `set[str]` (no stop-words, no numbers) | `{"dragon", "realm"}` |
| rating signal | `float` | `(4.2 − 1) / 4 = 0.80` |

### Jaccard similarity: comparing two sets

```
            |A ∩ B|        number of things both have
J(A, B) = ─────────  =  ────────────────────────────────
            |A ∪ B|        number of different things in total
```

It is 0 when the sets share nothing and 1 when they are identical. In Python it is
one line: `len(a & b) / len(a | b)`.

### The scoring formula

```
final_score = 0.35 × Jaccard(keywords)
            + 0.30 × Jaccard(genres)
            + 0.15 × (1 if any author is shared else 0)
            + 0.10 × Jaccard(title words)
            + 0.10 × rating_signal_of_candidate
```

The weights are in `config.RECOMMENDER_WEIGHTS` and add up to 1, so every score is
between 0 and 1. Here is why each weight has its value:

| Component | Weight | Justification |
|---|---|---|
| Keywords | 0.35 | Most specific information we have (up to 12 reader tags such as "dystopian", "vampires") |
| Genre | 0.30 | Reliable but broad: only 22 genres for 10,000 books |
| Author | 0.15 | A strong hint, but only yes/no. A larger weight would make every list "more by the same author" |
| Title | 0.10 | Mostly catches series ("Harry Potter and the …"). Noisy for common words |
| Rating | 0.10 | A small quality prior that separates otherwise equally similar books. It can never make an unrelated book win (see the filter below) |

**Filter:** a candidate must score at least `0.05` *without* the rating part.
A highly rated book with nothing in common is never recommended.

These weights are a reasoned starting point. They were **not** tuned on measured
user feedback, because the project has no such data (see *Limitations*).

### Worked example (from the test data in `tests/fixtures/sample_books.csv`)

Selected: **Small Steps Big Change**. Candidate: **Mind Patterns** (rating 4.0).

| Component | Selected | Candidate | Calculation | Value |
|---|---|---|---|---|
| keywords | {habits, productivity, behavior} | {behavior, brain, habits} | 2 shared / 4 different | 0.50 |
| genre | {Self Help, Psychology} | {Psychology, Non-fiction} | 1 / 3 | 0.33 |
| author | Dan Moore | Eve Chen | not shared | 0 |
| title | {small, steps, big, change} | {mind, patterns} | 0 / 6 | 0 |
| rating | – | 4.0 | (4.0 − 1) / 4 | 0.75 |

```
score = 0.35×0.50 + 0.30×0.33 + 0.15×0 + 0.10×0 + 0.10×0.75
      = 0.175 + 0.100 + 0 + 0 + 0.075 = 0.35
```

This exact calculation is checked by `test_component_scores_by_hand` in
`tests/test_recommender.py`.

### Explanations

Reasons are built from the same components that produced the score. A component
is mentioned only if it is at least `0.15` (`EXPLANATION_THRESHOLD`):

```
2. Mind Patterns — Eve Chen (2012)
   Similar because:
   ✓ Same genre: Psychology
   ✓ Shared themes: behavior, habits
   ✓ Highly rated by readers (4.00/5)
```

### Duplicates and editions

`edition_key(book)` = (normalised title, first author). The selected book's key
and every key already chosen are skipped. So two editions of the same work never
both appear, and the selected book never appears under a different id.

### Cost

For one request the loop does about 10,000 × 4 small set operations. The sets are
built once when the program starts (`BasicRecommender.__init__`), not on every
request. See `docs/testing.md` for the measured time.

---

## 2. Advanced recommender: TF-IDF + cosine similarity (`content_recommender.py`)

This is optional. It is used only if scikit-learn is installed **and** the user picks it.

### Step 1: one text per book

```
title + authors×2 + genres×2 + keywords×3 (+ description, if any)
```

Repeating a field is a simple way to give it more weight. Multi-word values are
joined (`Science Fiction` → `science_fiction`) so that "science" in a physics book
does not match science fiction. Author names are compacted (`alicestone`) so two
different authors called "John" are not treated as similar.

### Step 2: TF-IDF, turning text into numbers

For every word *t* in book *d*:

* **TF (term frequency)**: how often *t* appears in *d*. We use `1 + log(count)`
  (`sublinear_tf=True`), so repeating a word 10 times does not make it 10 times
  more important.
* **IDF (inverse document frequency)**: how *rare* *t* is across all books:
  `idf(t) = ln((1 + N) / (1 + df(t))) + 1`, where N = number of books and
  df(t) = number of books containing t.
* **TF-IDF = TF × IDF.** A word gets a high value if it is frequent in *this* book
  but rare overall ("vampires"). Words found in almost every book ("fiction")
  get a low value. English stop-words ("the", "and") are removed completely.

Each book becomes a vector with one number per word in the vocabulary (up to 20,000
words). Most numbers are 0, so scikit-learn stores it as a *sparse* matrix. Each
vector is scaled to length 1.

### Step 3: cosine similarity

```
               A · B
cos(A, B) = ───────────
            ‖A‖ × ‖B‖
```

* `A · B` (dot product) = multiply matching positions and add them up
* `‖A‖` = length of the vector = √(sum of squares)

It measures the **angle** between two vectors. 1 means they point the same way
(same words in the same proportions), and 0 means no shared words. Book length does
not matter, only the direction does.

**Tiny example.** The vocabulary is [magic, dragons, detective].
Book A = (1, 1, 0), book B = (1, 0, 1).

```
A · B  = 1×1 + 1×0 + 0×1 = 1
‖A‖    = √(1² + 1² + 0²) = √2
‖B‖    = √2
cos    = 1 / (√2 × √2) = 0.5
```

### Step 4: rank

The similarity of the selected book to *all* books is computed in one call
(`cosine_similarity(vector, matrix)`). The ranking then uses exactly the same
`select_top` function as the basic recommender (exclusions, editions, tie-breaking).
Explanations show the cosine value plus the shared genres and themes.

### Why keep both engines?

| | Basic | TF-IDF |
|---|---|---|
| Needs a library | No | scikit-learn |
| Easy to calculate by hand | Yes | Partly |
| Knows that rare words matter more | No (every keyword counts the same) | Yes |
| Uses description text (for Google Books results) | Only through keywords/genres | Yes |

The TF-IDF matrix is built **once**, the first time the user selects the advanced
engine, and then cached in `BookWiseService`.

---

## 3. Personalised recommendations (`personalization.py`)

### Signals from the user profile

| Signal | Source | Python type |
|---|---|---|
| Preferred genres | menu 7 | `set[str]` |
| Liked books | favourites **plus** ratings ≥ 4, **minus** anything rated ≤ 2 | `set[str]` |
| Disliked books | ratings ≤ 2 | `set[str]` |
| Recent history | the last 10 books opened | `list[str]` |

### Formula (for each candidate book not yet rated, favourited or viewed)

```
score = 0.35 × genre_match
      + 0.40 × similarity to the closest LIKED book
      + 0.15 × similarity to the closest recently VIEWED book
      + 0.10 × rating_signal
      − 0.30 × similarity to the closest DISLIKED book
```

* `genre_match = |book genres ∩ preferred genres| / min(|book genres|, |preferred|)`.
  For example, preferred {Psychology, Self Help} and book {Psychology, Non-fiction}
  give 1 shared out of 2 possible = 0.5.
* "Similarity" is the basic recommender's content score without the rating part,
  rescaled to 0–1.
* **Liked books** get the largest weight because acting on a book is the strongest
  evidence of taste. **Viewing** is weaker evidence (you may have opened it and not
  liked it), so it gets less. **Disliked** similarity is subtracted, so a book that
  closely resembles one you rated 1★ drops down the list.
* A candidate must have some personal connection (genre, liked or history ≥ 0.05).
  The rating alone never qualifies a book.

### Explanation example

```
1. The Quiet Detective — Carla Reyes (2017)
   Recommended for you because:
   ✓ You prefer Mystery & Thriller
   ✓ Similar to "Cold Case Files", which you liked
   ✓ Highly rated by readers (4.10/5)
```

---

## 4. Limitations of the approach

* **No accuracy measurement.** There is no set of real users with known preferences
  to test against, so BookWise reports **no** accuracy, precision or recall figures.
  One could be measured in future with the goodbooks-10k `ratings.csv` file
  (hide some of each user's high ratings and check whether they are recommended).
* **Content-based "filter bubble".** Recommendations stay close to what the user
  already knows. The system does not recommend something different that similar
  readers enjoyed (that would need collaborative filtering).
* **Tag quality.** Genres and keywords come from crowd-sourced tags. A book with
  few or unusual tags gets weaker recommendations.
* **Series dominate.** For books in long series, the next volumes usually fill the
  top places, because they share author, title words and tags.
