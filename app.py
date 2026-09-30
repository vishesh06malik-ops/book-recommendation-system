"""BookWise — optional Streamlit web interface.

    streamlit run app.py

This file contains ONLY presentation code. Every feature calls the same
BookWiseService used by the command-line app (main.py), so there is no
duplicated search or recommendation logic.
"""

from __future__ import annotations

import streamlit as st

from src import config
from src.api.google_books import GoogleBooksUnavailable
from src.data.data_manager import DatasetError
from src.models.book import Book
from src.search.search_engine import SEARCH_MODES
from src.services import ENGINE_ADVANCED, ENGINE_BASIC, BookWiseService
from src.storage.storage_manager import StorageError
from src.utils.helpers import display_value, setup_logging, stars

PAGES = ("Home", "Search", "Discover", "Recommendations", "Favourites", "Profile", "About")

st.set_page_config(page_title="BookWise", page_icon="📚", layout="wide")
setup_logging()


@st.cache_resource(show_spinner="Loading the book database...")
def get_service() -> BookWiseService:
    """Create the service once and reuse it across reruns (Streamlit re-runs this file on every click)."""
    return BookWiseService()


# ---------------------------------------------------------------------------
# Callbacks: they change session state BEFORE the next rerun
# ---------------------------------------------------------------------------
def go_to_recommendations(book_id: str) -> None:
    st.session_state["selected_book"] = book_id
    st.session_state["page"] = "Recommendations"


def toggle_favourite(service: BookWiseService, book_id: str) -> None:
    try:
        if service.users.is_favourite(book_id):
            service.users.remove_favourite(book_id)
        else:
            service.users.add_favourite(book_id)
    except StorageError as error:
        st.session_state["flash"] = str(error)


def save_rating(service: BookWiseService, book_id: str, key: str) -> None:
    try:
        service.users.rate_book(book_id, st.session_state[key])
        st.session_state["flash"] = f"Saved your rating: {stars(st.session_state[key])}"
    except (StorageError, ValueError) as error:
        st.session_state["flash"] = str(error)


# ---------------------------------------------------------------------------
# Reusable display pieces
# ---------------------------------------------------------------------------
def book_card(service: BookWiseService, book: Book, key: str, reasons: list[str] | None = None,
              score: float | None = None) -> None:
    """Show one book with its actions inside an expander."""
    label = book.short_label() + (f"  ·  score {score:.2f}" if score is not None else "")
    with st.expander(label):
        left, right = st.columns([1, 4])
        with left:
            if book.cover_url:
                st.image(book.cover_url, width=110)
            else:
                st.caption("No cover available")
        with right:
            for name, value in book.to_display_dict().items():
                st.markdown(f"**{name}:** {value}")
            st.markdown(f"**Description:** {display_value(book.description)}")
            if reasons:
                st.markdown("**Why recommended:**\n" + "\n".join(f"- {r}" for r in reasons))

        is_local = service.catalog.get(book.id) is not None
        if not is_local:
            st.caption("From Google Books — favourites and ratings are available for local books.")
        cols = st.columns(3)
        cols[0].button("Similar books", key=f"rec-{key}", on_click=go_to_recommendations, args=(book.id,))
        if is_local:
            favourite = service.users.is_favourite(book.id)
            cols[1].button("♥ Remove favourite" if favourite else "♡ Add to favourites", key=f"fav-{key}",
                           on_click=toggle_favourite, args=(service, book.id))
            current = service.users.get_rating(book.id) or 3
            rating_key = f"rating-{key}"
            cols[2].select_slider("Your rating", options=[1, 2, 3, 4, 5], value=current, key=rating_key,
                                  format_func=stars)
            cols[2].button("Save rating", key=f"save-{key}", on_click=save_rating,
                           args=(service, book.id, rating_key))


def recommendation_list(service: BookWiseService, recommendations, key: str) -> None:
    for i, rec in enumerate(recommendations):
        book_card(service, rec.book, f"{key}-{i}-{rec.book.id}", rec.reasons, rec.score)


# ---------------------------------------------------------------------------
# Pages
# ---------------------------------------------------------------------------
def page_home(service: BookWiseService) -> None:
    st.title("📚 BookWise")
    st.subheader("Discover books you'll love.")
    profile = service.users.profile
    cols = st.columns(4)
    cols[0].metric("Books", f"{len(service.catalog):,}")
    cols[1].metric("Genres", len(service.genres()))
    cols[2].metric("Your favourites", len(profile.favourites))
    cols[3].metric("Your ratings", len(profile.ratings))
    st.write("Use the sidebar to search, browse genres, get recommendations and manage your profile.")
    recent = service.history_books(5)
    if recent:
        st.markdown("#### Recently viewed")
        for book in recent:
            book_card(service, book, f"home-{book.id}")


def page_search(service: BookWiseService) -> None:
    st.header("Search")
    labels = [label for _, label in SEARCH_MODES] + ["Google Books (online)"]
    mode_label = st.radio("Search by", labels, horizontal=True)
    query = st.text_input("Search for")
    if not query.strip():
        st.info("Type something to search for.")
        return
    if mode_label == "Google Books (online)":
        try:
            results = service.live_search(query)
        except GoogleBooksUnavailable as error:
            st.warning(str(error))
            return
    else:
        mode = dict((label, key) for key, label in SEARCH_MODES)[mode_label]
        results = service.search(query, mode)
    if not results:
        st.warning(f"No books found for '{query}'.")
        return
    st.caption(f"{len(results)} result(s)")
    for book in results:
        book_card(service, book, f"search-{book.id}")


def page_discover(service: BookWiseService) -> None:
    st.header("Discover by genre")
    options = [f"{genre} ({count:,})" for genre, count in service.genres()]
    choice = st.selectbox("Genre", options)
    genre = choice.rsplit(" (", 1)[0]
    books = service.books_in_genre(genre)
    shown = st.slider("How many books to show", 10, 100, 20, step=10)
    st.caption(f"{len(books):,} books in {genre}, most rated first")
    for book in books[:shown]:
        book_card(service, book, f"genre-{book.id}")


def page_recommendations(service: BookWiseService) -> None:
    st.header("Recommendations")
    similar_tab, personal_tab = st.tabs(["Similar to a book", "Recommended for you"])
    with similar_tab:
        similar_books_section(service)
    with personal_tab:
        personal_section(service)


def similar_books_section(service: BookWiseService) -> None:
    selected = service.get_book(st.session_state.get("selected_book", ""))
    query = st.text_input("Find a book by title", value=selected.title if selected else "")
    matches = service.search(query, "title", limit=10) if query.strip() else []
    if selected and selected not in matches:
        matches.insert(0, selected)
    if not matches:
        st.info("Type a title to choose a book.")
        return
    book = st.selectbox("Book", matches, format_func=lambda b: b.short_label())
    cols = st.columns(2)
    n = cols[0].selectbox("How many", config.ALLOWED_RECOMMENDATION_COUNTS)
    engines = {"Basic — weighted similarity": ENGINE_BASIC}
    if service.advanced_available:
        engines["Advanced — TF-IDF + cosine similarity"] = ENGINE_ADVANCED
    engine = engines[cols[1].radio("Engine", list(engines))]

    service.view_book(book)
    with st.spinner("Finding similar books..."):
        recommendations, engine_name = service.recommend(book, n, engine)
    if not recommendations:
        st.warning("No similar books found — this book may have too little information to compare.")
        return
    st.caption(f"Engine used: {engine_name}")
    recommendation_list(service, recommendations, "rec")


def page_favourites(service: BookWiseService) -> None:
    st.header("My favourites")
    favourites = service.favourite_books()
    if not favourites:
        st.info("No favourites yet — add some from Search or Discover.")
    for book in favourites:
        book_card(service, book, f"fav-{book.id}")


def personal_section(service: BookWiseService) -> None:
    if not service.has_personal_signals():
        st.info("Choose preferred genres on the Profile page, or add favourites and ratings.")
        return
    recommendations = service.personalized(config.DEFAULT_RECOMMENDATION_COUNT * 2)
    if not recommendations:
        st.warning("No personalised recommendations found yet.")
    recommendation_list(service, recommendations, "personal")


def page_profile(service: BookWiseService) -> None:
    st.header("My profile")
    profile = service.users.profile
    chosen = st.multiselect("Preferred genres", service.genre_names(), default=sorted(profile.preferred_genres))
    if st.button("Save preferences"):
        try:
            service.users.set_preferred_genres(chosen)
            st.success("Preferences saved.")
        except StorageError as error:
            st.error(str(error))
    st.subheader("My ratings")
    rated = service.rated_books()
    if not rated:
        st.caption("You have not rated any books yet.")
    for book, rating in rated:
        st.write(f"{stars(rating)}  {book.short_label()}")


def page_about(service: BookWiseService) -> None:
    st.header("About BookWise")
    st.markdown(f"""
BookWise is a Python Essentials course project (VITyarthi): a book search and
recommendation system whose core runs in the terminal (`python main.py`).
This web page is an optional second interface that uses exactly the same Python backend.

* **Dataset:** goodbooks-10k by Zygmunt Zajac — CC BY-SA 4.0 ({len(service.catalog):,} books)
* **Basic recommender:** weighted Jaccard similarity of genres, keywords, authors and title words
* **Advanced recommender:** TF-IDF + cosine similarity ({'available' if service.advanced_available else 'install scikit-learn to enable'})
* **Live search:** optional Google Books API

"Rating" is the readers' average from the dataset; "Your rating" is stored only on this computer.
""")


def main() -> None:
    try:
        service = get_service()
    except DatasetError as error:
        st.error(f"BookWise could not start: {error}")
        st.stop()

    if "page" not in st.session_state:
        st.session_state["page"] = "Home"
    st.sidebar.title("📚 BookWise")
    st.sidebar.radio("Go to", PAGES, key="page")
    if "flash" in st.session_state:
        st.toast(st.session_state.pop("flash"))

    pages = {
        "Home": page_home, "Search": page_search, "Discover": page_discover,
        "Recommendations": page_recommendations, "Favourites": page_favourites,
        "Profile": page_profile, "About": page_about,
    }
    pages[st.session_state["page"]](service)


main()
