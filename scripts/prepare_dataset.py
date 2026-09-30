"""
prepare_dataset.py — build data/books.csv from the public goodbooks-10k dataset.

Run once from the project root:

    python3 scripts/prepare_dataset.py

What it does
------------
1. Downloads three raw CSV files from the goodbooks-10k GitHub repository
   into data/raw/ (skipped if they are already there).
2. Cleans the book metadata (ISBNs, years, authors, cover URLs).
3. Turns the most common Goodreads user tags of every book into
   (a) a list of broad genres and (b) a list of keywords.
4. Removes duplicate books.
5. Writes the result to data/books.csv.

Dataset: goodbooks-10k by Zygmunt Zajac,
https://github.com/zygmuntz/goodbooks-10k — licensed CC BY-SA 4.0.
The generated data/books.csv is a derived work under the same licence.

Only the Python standard library is used, so this script runs even before
`pip install -r requirements.txt`.
"""

from __future__ import annotations

import csv
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
OUTPUT_PATH = PROJECT_ROOT / "data" / "books.csv"

BASE_URL = "https://raw.githubusercontent.com/zygmuntz/goodbooks-10k/master/"
RAW_FILES = ("books.csv", "book_tags.csv", "tags.csv")
DOWNLOAD_TIMEOUT = 60  # seconds

# How many of a book's most-used (clean) tags we look at.
TOP_TAGS_FOR_GENRES = 25
MAX_KEYWORDS = 12

# A clean tag only counts if at least this share of the book's
# most popular clean tag's count used it. This drops rare, personal tags.
MIN_TAG_SHARE = 0.02

# Broad genres and the Goodreads tag names that indicate each one.
# A book receives a genre when one of its top clean tags is in the set.
GENRE_RULES: dict[str, set[str]] = {
    "Fiction": {"fiction", "literary-fiction", "literature", "novels", "general-fiction",
                "contemporary", "contemporary-fiction", "adult-fiction"},
    "Fantasy": {"fantasy", "high-fantasy", "epic-fantasy", "urban-fantasy", "magic",
                "paranormal", "fairy-tales", "dragons"},
    "Science Fiction": {"science-fiction", "sci-fi", "scifi", "sf", "dystopian",
                        "dystopia", "post-apocalyptic", "space-opera", "cyberpunk"},
    "Mystery & Thriller": {"mystery", "mysteries", "thriller", "thrillers", "crime",
                           "suspense", "mystery-thriller", "detective", "crime-fiction",
                           "psychological-thriller"},
    "Romance": {"romance", "love", "chick-lit", "contemporary-romance",
                "historical-romance", "paranormal-romance", "romantic"},
    "Horror": {"horror", "supernatural", "ghosts", "vampires", "zombies"},
    "Historical Fiction": {"historical-fiction", "historical", "hist-fic"},
    "Young Adult": {"young-adult", "ya", "ya-fiction", "teen", "young-adult-fiction"},
    "Children's": {"children", "childrens", "children-s", "kids", "childrens-books",
                   "middle-grade", "picture-books", "juvenile"},
    "Classics": {"classics", "classic", "classic-literature"},
    "Non-fiction": {"non-fiction", "nonfiction", "non-fic"},
    "Biography & Memoir": {"biography", "memoir", "memoirs", "autobiography",
                           "biographies", "biography-memoir"},
    "Self Help": {"self-help", "self-improvement", "personal-development",
                  "productivity", "motivation", "personal-growth"},
    "Psychology": {"psychology", "neuroscience"},
    "Business & Economics": {"business", "economics", "finance", "leadership",
                             "management", "entrepreneurship", "marketing"},
    "Philosophy": {"philosophy"},
    "History": {"history", "world-history", "american-history", "military-history"},
    "Science": {"science", "popular-science", "physics", "biology", "nature",
                "mathematics", "astronomy"},
    "Religion & Spirituality": {"religion", "spirituality", "christian", "christianity",
                                "faith", "theology", "buddhism"},
    "Poetry": {"poetry", "poems"},
    "Humor": {"humor", "humour", "comedy", "funny"},
    "Graphic Novels & Comics": {"graphic-novels", "graphic-novel", "comics", "manga",
                                "comic-books"},
}

# Tags that describe a reader's shelf, not the book itself.
NOISE_TAG_PATTERN = re.compile(
    r"(read|(^|-)own(ed|s)?($|-)|favo|kindle|ebook|e-book|audio|library|shelf|wish|buy|"
    r"dnf|tbr|default|borrowed|bought|gift|maybe|stars?$|^my-|^i-|"
    r"^books?$|book-club|bookclub|series|unfinished|abandoned|re-read|"
    r"sale|free|collection|hardcover|paperback|nook|ibooks|goodreads)"
)
VALID_TAG_PATTERN = re.compile(r"^[a-z][a-z-]{1,40}$")  # plain english letters/hyphens only


# ---------------------------------------------------------------------------
# Step 1: download
# ---------------------------------------------------------------------------
def download_raw_files() -> bool:
    """Download any missing raw file. Returns True when all files are present."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    all_present = True
    for name in RAW_FILES:
        target = RAW_DIR / name
        if target.exists() and target.stat().st_size > 0:
            print(f"  ✓ {name} already downloaded")
            continue
        url = BASE_URL + name
        print(f"  ↓ downloading {name} ...")
        if download_with_urllib(url, target) or download_with_curl(url, target):
            print(f"    saved {target.stat().st_size / 1_000_000:.1f} MB")
        else:
            all_present = False
    return all_present


def download_with_urllib(url: str, target: Path) -> bool:
    try:
        with urllib.request.urlopen(url, timeout=DOWNLOAD_TIMEOUT) as response:
            data = response.read()
        target.write_bytes(data)
        return True
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        # A common cause on macOS: the python.org installer's SSL certificates
        # were never installed ("CERTIFICATE_VERIFY_FAILED").
        print(f"    Python download failed ({error}); trying curl ...")
        return False


def download_with_curl(url: str, target: Path) -> bool:
    """Fallback: the `curl` program ships with macOS, Linux and Windows 10+
    and uses the operating system's own certificates."""
    curl = shutil.which("curl")
    if not curl:
        print("    curl is not installed.")
        return False
    try:
        # A list of arguments (not one string) means no shell is involved.
        subprocess.run([curl, "-fsSL", "--max-time", str(DOWNLOAD_TIMEOUT * 3), "-o", str(target), url],
                       check=True)
        return target.exists() and target.stat().st_size > 0
    except (subprocess.CalledProcessError, OSError) as error:
        print(f"  ✗ could not download {url}: {error}")
        if target.exists():
            target.unlink()  # remove a half-written file
        return False


# ---------------------------------------------------------------------------
# Step 2: small cleaning helpers (tested in tests/test_prepare_dataset.py)
# ---------------------------------------------------------------------------
def is_valid_isbn10(isbn: str) -> bool:
    """Check an ISBN-10 with its check-digit rule: sum(digit * weight) % 11 == 0,
    where the weights are 10, 9, ..., 1 and a final 'X' means 10."""
    if len(isbn) != 10 or not isbn[:9].isdigit():
        return False
    last = isbn[9]
    if not (last.isdigit() or last == "X"):
        return False
    total = 0
    for position, char in enumerate(isbn):
        value = 10 if char == "X" else int(char)
        total += value * (10 - position)
    return total % 11 == 0


def clean_isbn(raw: str) -> str:
    """Restore leading zeros lost by spreadsheet tools, then validate.

    goodbooks-10k stores '0439023483' as '439023483'. ISBN-10 is always
    ten characters, so padding with zeros is a restoration, not a guess;
    the check digit then confirms it. Invalid values become ''.
    """
    value = (raw or "").strip().upper()
    if not value or not re.fullmatch(r"[0-9]{1,9}[0-9X]", value):
        return ""
    value = value.zfill(10)
    return value if is_valid_isbn10(value) else ""


def clean_year(raw: str) -> str:
    """'2008.0' -> '2008'; '-720.0' -> '-720' (i.e. 720 BC); '' -> ''."""
    try:
        return str(int(float(raw)))
    except (TypeError, ValueError):
        return ""


def clean_cover_url(raw: str) -> str:
    """Goodreads uses a generic 'nophoto' image when no cover exists."""
    url = (raw or "").strip()
    if not url.startswith("http") or "nophoto" in url:
        return ""
    return url


def split_authors(raw: str) -> list[str]:
    """'J.K. Rowling, Mary GrandPré' -> ['J.K. Rowling', 'Mary GrandPré']."""
    return [name.strip() for name in (raw or "").split(",") if name.strip()]


def is_useful_tag(tag: str) -> bool:
    """True for descriptive tags like 'fantasy'; False for shelf tags like 'to-read'."""
    return bool(VALID_TAG_PATTERN.match(tag)) and not NOISE_TAG_PATTERN.search(tag)


def derive_genres_and_keywords(tag_counts: list[tuple[str, int]]) -> tuple[list[str], list[str]]:
    """Turn (tag_name, count) pairs for ONE book into (genres, keywords).

    Only descriptive tags used by at least MIN_TAG_SHARE of the top
    descriptive tag's users are considered.
    """
    clean = [(tag, count) for tag, count in tag_counts if is_useful_tag(tag)]
    clean.sort(key=lambda pair: (-pair[1], pair[0]))
    if not clean:
        return [], []
    threshold = clean[0][1] * MIN_TAG_SHARE
    top_tags = [tag for tag, count in clean[:TOP_TAGS_FOR_GENRES] if count >= threshold]

    genres = []
    for genre, genre_tags in GENRE_RULES.items():  # dict order keeps output stable
        if any(tag in genre_tags for tag in top_tags):
            genres.append(genre)
    keywords = [tag.replace("-", " ") for tag in top_tags[:MAX_KEYWORDS]]
    return genres, keywords


def duplicate_key(title: str, authors: list[str]) -> tuple[str, str]:
    """Two rows are the same book when normalised title and first author match."""
    norm_title = re.sub(r"\s+", " ", title.lower()).strip()
    first_author = authors[0].lower() if authors else ""
    return norm_title, first_author


# ---------------------------------------------------------------------------
# Step 3: processing
# ---------------------------------------------------------------------------
def load_tag_names(path: Path) -> dict[str, str]:
    with open(path, newline="", encoding="utf-8") as file:
        return {row["tag_id"]: row["tag_name"].strip().lower() for row in csv.DictReader(file)}


def load_book_tags(path: Path, tag_names: dict[str, str]) -> dict[str, list[tuple[str, int]]]:
    """goodreads_book_id -> [(tag_name, count), ...]"""
    tags_by_book: dict[str, list[tuple[str, int]]] = {}
    with open(path, newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            name = tag_names.get(row["tag_id"])
            try:
                count = int(row["count"])
            except (TypeError, ValueError):
                continue
            if name and count > 0:
                tags_by_book.setdefault(row["goodreads_book_id"], []).append((name, count))
    return tags_by_book


OUTPUT_COLUMNS = ["id", "isbn", "title", "authors", "categories", "keywords",
                  "published_year", "language", "rating", "rating_count",
                  "cover_url", "source"]


def build_rows(books_path: Path, tags_by_book: dict[str, list[tuple[str, int]]]) -> tuple[list[dict], dict]:
    """Clean every book row. Returns (rows, statistics)."""
    stats = {"input_rows": 0, "skipped_no_title": 0, "duplicates_removed": 0,
             "invalid_isbn": 0, "no_genre": 0}
    best_by_key: dict[tuple[str, str], dict] = {}

    with open(books_path, newline="", encoding="utf-8") as file:
        for row in csv.DictReader(file):
            stats["input_rows"] += 1
            title = (row.get("title") or row.get("original_title") or "").strip()
            if not title:
                stats["skipped_no_title"] += 1
                continue
            authors = split_authors(row.get("authors", ""))
            isbn = clean_isbn(row.get("isbn", ""))
            if not isbn:
                stats["invalid_isbn"] += 1
            genres, keywords = derive_genres_and_keywords(
                tags_by_book.get(row.get("goodreads_book_id", ""), []))
            if not genres:
                stats["no_genre"] += 1
            try:
                rating_count = int(float(row.get("ratings_count") or 0))
            except ValueError:
                rating_count = 0

            cleaned = {
                "id": row["book_id"].strip(),
                "isbn": isbn,
                "title": title,
                "authors": "|".join(authors),
                "categories": "|".join(genres),
                "keywords": "|".join(keywords),
                "published_year": clean_year(row.get("original_publication_year", "")),
                "language": (row.get("language_code") or "").strip(),
                "rating": (row.get("average_rating") or "").strip(),
                "rating_count": str(rating_count) if rating_count else "",
                "cover_url": clean_cover_url(row.get("image_url", "")),
                "source": "goodbooks-10k",
            }
            key = duplicate_key(title, authors)
            existing = best_by_key.get(key)
            if existing is None:
                best_by_key[key] = cleaned
            else:
                stats["duplicates_removed"] += 1
                # keep the edition with more ratings
                if rating_count > int(existing["rating_count"] or 0):
                    best_by_key[key] = cleaned

    rows = sorted(best_by_key.values(), key=lambda r: int(r["id"]))
    return rows, stats


def write_output(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)


def main() -> int:
    print("BookWise dataset preparation (goodbooks-10k, CC BY-SA 4.0)")
    print("Step 1/3: raw files")
    if not download_raw_files():
        print("\nSome files could not be downloaded. Download them manually from")
        print(f"  {BASE_URL}<file name>")
        print(f"and place them in {RAW_DIR}, then run this script again.")
        return 1

    print("Step 2/3: processing")
    try:
        tag_names = load_tag_names(RAW_DIR / "tags.csv")
        tags_by_book = load_book_tags(RAW_DIR / "book_tags.csv", tag_names)
        rows, stats = build_rows(RAW_DIR / "books.csv", tags_by_book)
    except (OSError, KeyError, csv.Error) as error:
        print(f"  ✗ could not process the raw files: {error}")
        return 1

    print("Step 3/3: writing")
    write_output(rows, OUTPUT_PATH)
    print(f"\nWrote {len(rows)} books to {OUTPUT_PATH.relative_to(PROJECT_ROOT)}")
    for name, value in stats.items():
        print(f"  {name.replace('_', ' ')}: {value}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
