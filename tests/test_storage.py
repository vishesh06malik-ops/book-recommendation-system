"""Tests for JSON storage and the user profile (favourites, ratings, preferences)."""

import json

import pytest

from src.storage.storage_manager import StorageError, load_json, save_json
from src.user.user_manager import InvalidRatingError, UserManager, UserProfile


# -- storage_manager ----------------------------------------------------------
def test_save_then_load_round_trip(tmp_path):
    path = tmp_path / "data.json"
    save_json(path, {"a": [1, 2], "b": "text"})
    assert load_json(path, default=None) == {"a": [1, 2], "b": "text"}
    assert not (tmp_path / "data.json.tmp").exists()  # temp file was replaced


def test_missing_file_returns_default(tmp_path):
    assert load_json(tmp_path / "nothing.json", default={"x": 1}) == {"x": 1}


def test_corrupted_json_returns_default_and_keeps_backup(tmp_path):
    path = tmp_path / "profile.json"
    path.write_text("{ this is not json", encoding="utf-8")
    assert load_json(path, default={}) == {}
    backups = list(tmp_path.glob("profile.json.corrupt-*"))
    assert len(backups) == 1
    assert backups[0].read_text(encoding="utf-8") == "{ this is not json"


def test_unserialisable_data_raises_storage_error(tmp_path):
    with pytest.raises(StorageError):
        save_json(tmp_path / "x.json", {"bad": object()})


# -- favourites ---------------------------------------------------------------
def test_add_and_remove_favourite_persists(tmp_path):
    path = tmp_path / "profile.json"
    manager = UserManager(path)
    assert manager.add_favourite("3") is True
    assert manager.add_favourite("3") is False  # no duplicates
    assert UserManager(path).profile.favourites == ["3"]  # survives a restart

    assert manager.remove_favourite("3") is True
    assert manager.remove_favourite("3") is False
    assert UserManager(path).profile.favourites == []


# -- ratings ------------------------------------------------------------------
@pytest.mark.parametrize("value, expected", [(1, 1), (5, 5), ("4", 4), (" 3 ", 3)])
def test_valid_ratings_are_accepted(tmp_path, value, expected):
    manager = UserManager(tmp_path / "p.json")
    assert manager.rate_book("7", value) == expected
    assert manager.get_rating("7") == expected


@pytest.mark.parametrize("value", [0, 6, -1, "abc", "", "4.5", None, True])
def test_invalid_ratings_are_rejected(tmp_path, value):
    manager = UserManager(tmp_path / "p.json")
    with pytest.raises(InvalidRatingError):
        manager.rate_book("7", value)
    assert manager.get_rating("7") is None


def test_new_rating_replaces_old_one(tmp_path):
    manager = UserManager(tmp_path / "p.json")
    manager.rate_book("7", 2)
    manager.rate_book("7", 5)
    assert UserManager(tmp_path / "p.json").profile.ratings == {"7": 5}


# -- preferences and history --------------------------------------------------
def test_preferred_genres_are_a_set_and_persist(tmp_path):
    path = tmp_path / "p.json"
    manager = UserManager(path)
    manager.set_preferred_genres(["Fantasy", "Fantasy", " Romance ", ""])
    assert UserManager(path).profile.preferred_genres == {"Fantasy", "Romance"}
    assert manager.toggle_genre("Fantasy") is False
    assert manager.toggle_genre("Horror") is True
    assert UserManager(path).profile.preferred_genres == {"Romance", "Horror"}


def test_history_is_most_recent_first_without_duplicates(tmp_path):
    manager = UserManager(tmp_path / "p.json")
    for book_id in ["1", "2", "3", "1"]:
        manager.record_view(book_id)
    assert manager.profile.history == ["1", "3", "2"]


def test_liked_and_disliked_signals(tmp_path):
    manager = UserManager(tmp_path / "p.json")
    manager.add_favourite("1")
    manager.add_favourite("9")
    manager.rate_book("2", 5)
    manager.rate_book("9", 1)  # a low rating overrides being a favourite
    manager.rate_book("4", 3)  # neutral: neither liked nor disliked
    assert manager.liked_ids() == {"1", "2"}
    assert manager.disliked_ids() == {"9"}


def test_profile_from_hand_edited_json_ignores_bad_values():
    profile = UserProfile.from_dict({
        "favourites": ["1", "1", 2, None, {"x": 1}],
        "ratings": {"1": 5, "2": 9, "3": "4", "4": True},
        "preferred_genres": ["Fantasy", 7, ""],
        "history": "not a list of ids",
    })
    assert profile.favourites == ["1", "2"]
    assert profile.ratings == {"1": 5}
    assert profile.preferred_genres == {"Fantasy"}
    assert profile.history == []  # wrong type is ignored, not iterated character by character


def test_profile_file_with_wrong_top_level_type(tmp_path):
    path = tmp_path / "p.json"
    path.write_text(json.dumps([1, 2, 3]), encoding="utf-8")
    assert UserManager(path).profile == UserProfile()
