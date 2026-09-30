# Dataset: goodbooks-10k

BookWise uses a cleaned copy of **goodbooks-10k**, a public dataset of the
10,000 most-rated books on Goodreads (at the time the dataset was collected).

| | |
|---|---|
| **Name** | goodbooks-10k |
| **Author** | Zygmunt Zając |
| **Source** | https://github.com/zygmuntz/goodbooks-10k |
| **Licence** | [Creative Commons Attribution-ShareAlike 4.0 (CC BY-SA 4.0)](https://creativecommons.org/licenses/by-sa/4.0/) |
| **Files used** | `books.csv`, `book_tags.csv`, `tags.csv` |
| **File produced** | `data/books.csv` (committed to this repository) |

**Licence obligations.** CC BY-SA 4.0 allows sharing and adapting the data
(including in this public repository) as long as we **credit the author**, **link
the licence**, **say that changes were made**, and **share the adapted data under
the same licence**. `data/books.csv` is an adaptation of goodbooks-10k, and it
is distributed under CC BY-SA 4.0. The changes are listed under *Preprocessing* below.

## How to obtain / rebuild the data

`data/books.csv` is already included, so BookWise runs without internet.
To rebuild it from the original files:

```bash
python3 scripts/prepare_dataset.py
```

The script downloads the three raw files into `data/raw/` (ignored by git),
processes them, and overwrites `data/books.csv`. If the download fails (for example, because
there's no internet or a firewall blocks it), download the three files manually from
`https://github.com/zygmuntz/goodbooks-10k`, put them in `data/raw/` and run the
script again.

## Columns of `data/books.csv`

| Column | Type | Meaning | Origin |
|---|---|---|---|
| `id` | integer | goodbooks-10k `book_id` (1–10000) | `books.csv` |
| `isbn` | text | ISBN-10, validated with its check digit; empty if invalid | `books.csv` → `isbn` |
| `title` | text | Title as shown on Goodreads (may include series info, e.g. "(Harry Potter, #1)") | `books.csv` → `title` |
| `authors` | text, `\|`-separated | Author names | `books.csv` → `authors` |
| `categories` | text, `\|`-separated | Broad genres derived from reader tags (see below) | `book_tags.csv` + `tags.csv` |
| `keywords` | text, `\|`-separated | Up to 12 most used descriptive reader tags | `book_tags.csv` + `tags.csv` |
| `published_year` | integer | Original publication year; negative = BC | `books.csv` → `original_publication_year` |
| `language` | text | Language code (e.g. `eng`, `en-US`) | `books.csv` → `language_code` |
| `rating` | decimal | Average Goodreads rating, 1–5 (the **external** rating) | `books.csv` → `average_rating` |
| `rating_count` | integer | Number of Goodreads ratings | `books.csv` → `ratings_count` |
| `cover_url` | text | Cover image URL; empty when Goodreads only has a placeholder | `books.csv` → `image_url` |
| `source` | text | Always `goodbooks-10k` | — |

`data_manager.py` requires only `id`, `title` and `authors`. `description` and `publisher`
columns are also read if present, but goodbooks-10k has no such columns.

## Preprocessing (what `prepare_dataset.py` changes)

1. **ISBN repair.** Spreadsheet software removed leading zeros (`0439023483` was
   stored as `439023483`). ISBN-10 always has 10 characters, so the value is
   padded with zeros and then **verified with the ISBN-10 check-digit formula**.
   Values that fail are left empty. Nothing is guessed.
2. **ISBN-13 is not used.** In the source, `isbn13` was saved as a floating-point
   number (`9.78043902348e+12`), which permanently lost the last digits.
3. **Years.** `2008.0` → `2008`. Ancient works keep negative years (`-720` is shown as "720 BC").
4. **Covers.** Goodreads' generic "nophoto" image is treated as *no cover*.
5. **Authors** are split on commas into a list.
6. **Genres and keywords come from reader tags.** For each book, BookWise:
   * removes "shelf" tags that describe the reader, not the book (`to-read`,
     `favorites`, `owned`, `kindle`, `2015-reads`, tags in non-Latin script ...);
   * keeps the remaining tags used by at least 2% as many readers as the book's most used
     descriptive tag (this drops rare, personal tags);
   * looks at the top 25 of these and maps them onto 22 broad genres using the table
     `GENRE_RULES` in the script (e.g. `sci-fi`, `dystopian` → *Science Fiction*);
   * stores the top 12 as keywords (`young-adult` → "young adult").
7. **Duplicates.** Rows with the same normalised title and first author are treated as
   the same work. Only the row with the most ratings is kept.

The script prints the exact number of rows read, duplicates removed, invalid ISBNs
and books without a genre.

## Fields that are not available

| Field | Status |
|---|---|
| Description / summary | **Not in the dataset.** Shown as "Not available". |
| Publisher | **Not in the dataset.** Shown as "Not available". |
| Official genre | Not in the dataset. Genres are *derived* from reader tags, as described above. |

BookWise never invents values for missing fields. Books found through the optional Google
Books search may include a description and a publisher.

## Limitations

* The dataset only covers **popular** books (the 10,000 most rated at collection time,
  around 2017). Newer books and less-known books are missing.
* Reader tags are crowd-sourced. Genres derived from them can be incomplete or surprising
  (e.g. a humorous fantasy novel may not get *Humor*).
* Goodreads average ratings reflect Goodreads users, not all readers.
* The dataset favours English-language books.
