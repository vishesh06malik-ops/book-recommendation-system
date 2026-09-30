"""The command-line interface: menus, prompts and printing.

This file only talks to the user. All real work (searching, recommending,
saving) is delegated to BookWiseService, so the Streamlit app can reuse it.
"""

from __future__ import annotations

import textwrap
from typing import Optional

from src import config
from src.api.google_books import GoogleBooksUnavailable
from src.cli.input_helpers import LINE, ask_int, ask_text, ask_yes_no, heading, pause
from src.models.book import Book
from src.recommendation.basic_recommender import Recommendation
from src.search.search_engine import SEARCH_MODES
from src.services import ENGINE_ADVANCED, ENGINE_BASIC, BookWiseService
from src.storage.storage_manager import StorageError
from src.user.user_manager import InvalidRatingError
from src.utils.helpers import display_value, shorten, stars

PAGE_SIZE = 15

BANNER = """
==================================================
                  BOOKWISE
       Smart Book Discovery & Recommendation
==================================================
"""

MAIN_MENU = """
1. Search Books
2. Browse Genres
3. View Book Details
4. Get Recommendations
5. My Favourites
6. Rate a Book
7. My Preferences
8. Personalized Recommendations
9. About Project
0. Exit
"""


class BookWiseCLI:
    def __init__(self, service: BookWiseService):
        self.service = service
        # Dictionary dispatch: menu number -> method. Cleaner than a long if/elif chain.
        self.actions = {
            1: self.search_books,
            2: self.browse_genres,
            3: self.view_book_details,
            4: self.get_recommendations,
            5: self.my_favourites,
            6: self.rate_a_book,
            7: self.my_preferences,
            8: self.personalized_recommendations,
            9: self.about,
        }

    # ======================================================================
    # Main loop
    # ======================================================================
    def run(self) -> None:
        print(BANNER)
        print(f"Loaded {len(self.service.catalog):,} books.")
        while True:
            print(MAIN_MENU)
            choice = ask_int("Enter your choice: ", 0, 9)
            if choice == 0:
                print("\nThank you for using BookWise. Goodbye!")
                return
            self.actions[choice]()

    # ======================================================================
    # Reusable building blocks
    # ======================================================================
    def choose_book(self, books: list[Book], title: str) -> Optional[Book]:
        """Show a numbered, paged list and return the chosen book (or None for back)."""
        if not books:
            print("\nNo books to show.")
            return None
        page = 0
        pages = (len(books) - 1) // PAGE_SIZE + 1
        while True:
            start = page * PAGE_SIZE
            heading(f"{title}  (page {page + 1} of {pages}, {len(books)} books)")
            for number, book in enumerate(books[start:start + PAGE_SIZE], start=start + 1):
                rating = f"{book.rating:.2f}" if book.rating is not None else "-"
                print(f"{number:>3}. {shorten(book.short_label(), 62)}  [{rating}]")
            options = "number = open, 0 = back"
            if page + 1 < pages:
                options += ", n = next page"
            if page > 0:
                options += ", p = previous page"
            answer = ask_text(f"\nChoose ({options}): ").lower()
            if answer == "n" and page + 1 < pages:
                page += 1
            elif answer == "p" and page > 0:
                page -= 1
            elif answer == "0":
                return None
            elif answer.isdigit() and 1 <= int(answer) <= len(books):
                return books[int(answer) - 1]
            else:
                print("  Invalid choice, please try again.")

    def find_book(self) -> Optional[Book]:
        """Let the user identify a book by title, ISBN or BookWise id."""
        query = ask_text("\nEnter a book title, ISBN or BookWise ID (blank = back): ")
        if not query:
            return None
        book = self.service.get_book(query)
        if book:
            return book
        results = self.service.search(query, "isbn") or self.service.search(query, "title")
        if not results:
            results = self.service.search(query, "keyword")
        if not results:
            print(f"\nNo books found for '{query}'.")
            return None
        if len(results) == 1:
            return results[0]
        return self.choose_book(results, f"Books matching '{query}'")

    def print_book(self, book: Book) -> None:
        """Book details as readable text (never a raw dictionary)."""
        user_rating = self.service.users.get_rating(book.id)
        print(f"\n{LINE}")
        print(f"TITLE:        {book.title}")
        print(f"AUTHOR:       {book.author_text}")
        print(f"GENRE:        {book.genre_text}")
        print(f"YEAR:         {book.year_text}")
        print(f"RATING:       {book.rating_text}   (readers' average from {book.source})")
        print(f"YOUR RATING:  {stars(user_rating) + f' ({user_rating}/5)' if user_rating else 'Not rated yet'}")
        print(f"PUBLISHER:    {display_value(book.publisher)}")
        print(f"ISBN:         {display_value(book.isbn)}")
        print(f"KEYWORDS:     {display_value(book.keywords)}")
        print(LINE)
        print("\nDESCRIPTION:")
        description = book.description or config.NOT_AVAILABLE
        print(textwrap.fill(shorten(description, 1200), width=70))

    def print_recommendations(self, recommendations: list[Recommendation], header: str,
                              reason_title: str = "Similar because:") -> None:
        heading(header)
        for number, rec in enumerate(recommendations, start=1):
            print(f"\n{number}. {rec.book.short_label()}")
            print(f"   Score: {rec.score:.2f}")
            print(f"   {reason_title}")
            for reason in rec.reasons:
                print(f"   ✓ {reason}")

    def save_safely(self, action, success_message: str) -> None:
        """Run a user-data change and report storage problems without crashing."""
        try:
            result = action()
        except StorageError as error:
            print(f"\n{error} Please check that the project folder is writable.")
            return
        if result is not False:
            print(f"\n{success_message}")

    # ======================================================================
    # Book details screen
    # ======================================================================
    def show_book(self, book: Book) -> None:
        self.service.view_book(book)
        is_local = self.service.catalog.get(book.id) is not None
        while True:
            self.print_book(book)
            if not is_local:
                print("\n(This book comes from Google Books. Favourites and ratings are available"
                      " for books in the local database.)")
                print("\n1. Find similar books in the local database\n2. Back")
                if ask_int("\nChoose: ", 1, 2) == 1:
                    self.show_recommendations_for(book)
                    continue
                return

            favourite = self.service.users.is_favourite(book.id)
            print(f"\n1. {'Remove from favourites' if favourite else 'Add to favourites'}")
            print("2. Rate this book\n3. Get recommendations\n4. Back")
            choice = ask_int("\nChoose: ", 1, 4)
            if choice == 1:
                if favourite:
                    self.save_safely(lambda: self.service.users.remove_favourite(book.id),
                                     "Removed from your favourites.")
                else:
                    self.save_safely(lambda: self.service.users.add_favourite(book.id),
                                     "Added to your favourites. ♥")
            elif choice == 2:
                self.ask_rating(book)
            elif choice == 3:
                self.show_recommendations_for(book)
            else:
                return

    def ask_rating(self, book: Book) -> None:
        print(f"\nRate '{shorten(book.title, 50)}':")
        for value in range(config.RATING_SCALE[1], config.RATING_SCALE[0] - 1, -1):
            print(f"  {value} {stars(value)}")
        text = ask_text("Your rating (1-5, blank = cancel): ")
        if not text:
            return
        try:
            rating = self.service.users.validate_rating(text)
        except InvalidRatingError as error:
            print(f"\n{error}")
            return
        self.save_safely(lambda: self.service.users.rate_book(book.id, rating),
                         f"Saved your rating: {stars(rating)} ({rating}/5)")

    # ======================================================================
    # 1. Search
    # ======================================================================
    def search_books(self) -> None:
        heading("SEARCH BOOKS")
        print("Search by:")
        for number, (_, label) in enumerate(SEARCH_MODES, start=1):
            print(f"{number}. {label}")
        live_option = len(SEARCH_MODES) + 1
        print(f"{live_option}. Live search: Google Books (needs internet)")
        print("0. Back")
        choice = ask_int("\nChoose: ", 0, live_option)
        if choice == 0:
            return
        if choice == live_option:
            self.live_search()
            return

        mode, label = SEARCH_MODES[choice - 1]
        query = ask_text(f"Enter {label.lower()}: ")
        if not query:
            print("\nPlease type something to search for.")
            return
        results = self.service.search(query, mode)
        if not results:
            print(f"\nNo books found for {label.lower()} '{query}'. Try fewer or different words.")
            return
        book = self.choose_book(results, f"Results for {label.lower()} '{query}'")
        if book:
            self.show_book(book)

    def live_search(self) -> None:
        query = ask_text("Search Google Books for: ")
        if not query:
            print("\nPlease type something to search for.")
            return
        print("Searching online...")
        try:
            results = self.service.live_search(query)
        except GoogleBooksUnavailable as error:
            print(f"\n{error}")
            return
        if not results:
            print(f"\nGoogle Books found nothing for '{query}'.")
            return
        book = self.choose_book(results, f"Google Books results for '{query}'")
        if book:
            self.show_book(book)

    # ======================================================================
    # 2. Browse genres
    # ======================================================================
    def browse_genres(self) -> None:
        genres = self.service.genres()
        heading("BROWSE GENRES")
        for number, (genre, count) in enumerate(genres, start=1):
            print(f"{number:>3}. {genre} ({count:,} book{'' if count == 1 else 's'})")
        print("  0. Back")
        choice = ask_int("\nChoose a genre: ", 0, len(genres))
        if choice == 0:
            return
        genre = genres[choice - 1][0]
        book = self.choose_book(self.service.books_in_genre(genre), f"{genre} — most rated first")
        if book:
            self.show_book(book)

    # ======================================================================
    # 3 & 4. Details and recommendations
    # ======================================================================
    def view_book_details(self) -> None:
        heading("VIEW BOOK DETAILS")
        book = self.find_book()
        if book:
            self.show_book(book)

    def get_recommendations(self) -> None:
        heading("GET RECOMMENDATIONS")
        book = self.find_book()
        if book:
            self.show_recommendations_for(book)

    def show_recommendations_for(self, book: Book) -> None:
        counts = config.ALLOWED_RECOMMENDATION_COUNTS
        count_text = "/".join(str(c) for c in counts)
        answer = ask_text(f"How many recommendations? ({count_text}, Enter = {config.DEFAULT_RECOMMENDATION_COUNT}): ")
        n = int(answer) if answer.isdigit() and int(answer) in counts else config.DEFAULT_RECOMMENDATION_COUNT

        engine = ENGINE_BASIC
        if self.service.advanced_available:
            print("\nRecommendation engine:\n1. Basic — weighted similarity (pure Python)"
                  "\n2. Advanced — TF-IDF + cosine similarity")
            if ask_int("Choose (Enter = 1): ", 1, 2, allow_blank=True) == 2:
                engine = ENGINE_ADVANCED
                print("Preparing the TF-IDF model (first time only)...")

        recommendations, engine_name = self.service.recommend(book, n, engine)
        if not recommendations:
            print(f"\nNo similar books found for '{book.title}'. It may have too little information"
                  " (no genres or keywords) to compare.")
            pause()
            return
        if len(recommendations) < n:
            print(f"\nOnly {len(recommendations)} sufficiently similar books were found.")
        self.print_recommendations(recommendations, f"Because you looked at '{shorten(book.title, 40)}' — {engine_name}")
        self.open_from_recommendations(recommendations)

    def open_from_recommendations(self, recommendations: list[Recommendation]) -> None:
        choice = ask_int("\nOpen a book (number) or 0 to go back: ", 0, len(recommendations))
        if choice:
            self.show_book(recommendations[choice - 1].book)

    # ======================================================================
    # 5. Favourites
    # ======================================================================
    def my_favourites(self) -> None:
        while True:
            favourites = self.service.favourite_books()
            heading(f"MY FAVOURITES ({len(favourites)})")
            if not favourites:
                print("You have no favourites yet. Open any book and choose 'Add to favourites'.")
                pause()
                return
            for number, book in enumerate(favourites, start=1):
                print(f"{number:>3}. {shorten(book.short_label(), 70)}")
            print("\n1. Open a book\n2. Remove a favourite\n0. Back")
            choice = ask_int("\nChoose: ", 0, 2)
            if choice == 0:
                return
            number = ask_int("Book number (0 = cancel): ", 0, len(favourites))
            if number == 0:
                continue
            book = favourites[number - 1]
            if choice == 1:
                self.show_book(book)
            else:
                self.save_safely(lambda book_id=book.id: self.service.users.remove_favourite(book_id),
                                 f"Removed '{shorten(book.title, 40)}' from your favourites.")

    # ======================================================================
    # 6. Ratings
    # ======================================================================
    def rate_a_book(self) -> None:
        heading("RATE A BOOK")
        rated = self.service.rated_books()
        if rated:
            print("Your ratings so far:")
            for book, rating in rated[:10]:
                print(f"  {stars(rating)}  {shorten(book.title, 55)}")
            if len(rated) > 10:
                print(f"  ... and {len(rated) - 10} more")
        book = self.find_book()
        if book:
            if self.service.catalog.get(book.id) is None:
                print("\nOnly books in the local database can be rated.")
                return
            self.print_book(book)
            self.ask_rating(book)

    # ======================================================================
    # 7. Preferences
    # ======================================================================
    def my_preferences(self) -> None:
        users = self.service.users
        genre_names = self.service.genre_names()
        while True:
            profile = users.profile
            heading("MY PREFERENCES")
            print(f"Favourites: {len(profile.favourites)}   Ratings: {len(profile.ratings)}"
                  f"   Recently viewed: {len(profile.history)}")
            print("\nSelect your favourite genres ([x] = selected):")
            for number, genre in enumerate(genre_names, start=1):
                mark = "x" if genre in profile.preferred_genres else " "
                print(f"{number:>3}. [{mark}] {genre}")
            print("\nType numbers separated by commas to select/unselect (e.g. 2,5,7)")
            print("c = clear all genres, r = reset ALL my data, 0 = back")
            answer = ask_text("\nChoose: ").lower()
            if answer == "0":
                return
            if answer == "c":
                self.save_safely(lambda: users.set_preferred_genres([]), "Genre preferences cleared.")
            elif answer == "r":
                if ask_yes_no("Delete all favourites, ratings, preferences and history?"):
                    self.save_safely(users.reset, "Your profile has been reset.")
            else:
                self.toggle_genres(answer, genre_names)

    def toggle_genres(self, answer: str, genre_names: list[str]) -> None:
        numbers = set()
        for part in answer.split(","):
            part = part.strip()
            if part.isdigit() and 1 <= int(part) <= len(genre_names):
                numbers.add(int(part))
            elif part:
                print(f"  Ignored '{part}': not a genre number.")
        for number in sorted(numbers):
            genre = genre_names[number - 1]
            try:
                selected = self.service.users.toggle_genre(genre)
            except StorageError as error:
                print(f"\n{error}")
                return
            print(f"  {'Selected' if selected else 'Unselected'}: {genre}")

    # ======================================================================
    # 8. Personalised recommendations
    # ======================================================================
    def personalized_recommendations(self) -> None:
        if not self.service.has_personal_signals():
            heading("PERSONALIZED RECOMMENDATIONS")
            print("BookWise does not know your taste yet. To get personal suggestions:")
            print("  • choose favourite genres in 'My Preferences' (menu 7)")
            print("  • add favourites or rate books you have read (menus 5 and 6)")
            pause()
            return
        recommendations = self.service.personalized(config.DEFAULT_RECOMMENDATION_COUNT * 2)
        if not recommendations:
            print("\nNo personalised recommendations could be found. Try selecting more genres.")
            pause()
            return
        self.print_recommendations(recommendations, "RECOMMENDED FOR YOU", "Recommended for you because:")
        self.open_from_recommendations(recommendations)

    # ======================================================================
    # 9. About
    # ======================================================================
    def about(self) -> None:
        heading("ABOUT BOOKWISE")
        print(textwrap.dedent(f"""\
            BookWise — Discover books you'll love.
            A Python Essentials course project (VITyarthi).

            Books in the local database : {len(self.service.catalog):,}
            Dataset                     : goodbooks-10k by Zygmunt Zajac (CC BY-SA 4.0)
                                          github.com/zygmuntz/goodbooks-10k
            Basic recommender           : weighted set similarity (pure Python)
            Advanced recommender        : {'available (TF-IDF + cosine similarity)' if self.service.advanced_available else 'not available (install scikit-learn)'}
            Live search                 : optional Google Books API

            Ratings shown as "RATING" are Goodreads readers' averages from the
            dataset. "YOUR RATING" is your own rating, stored only on this computer.
            Your data file: {self.service.users.path}
        """))
        pause()
