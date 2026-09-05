from fixtures.steam_samples import (
    RAW_APPDETAILS_NULL,
    RAW_DLC,
    RAW_FREE_TO_PLAY,
    RAW_GENRE_STRING_ONLY,
    RAW_MISSING_RELEASE_DATE,
    RAW_PRICE_OVERVIEW_NULL,
    RAW_ROGUELIKE,
    RAW_STEAMSPY_TAGS_ARRAY,
)

from tracker.normalizer import normalize_game


def test_normalize_full_game():
    app_id, raw = RAW_ROGUELIKE
    result = normalize_game(app_id, raw)

    assert result["app_id"] == 100001
    assert result["name"] == "Dungeon of Echoes"
    assert result["genres"] == ["Indie", "RPG"]
    assert result["tags"] == ["Roguelike", "Indie", "Pixel Graphics"]
    assert result["release_date"].isoformat() == "2021-03-12"
    assert result["price_cents"] == 1999
    assert result["is_dlc"] is False
    assert result["review_count"] == 4500
    assert round(result["review_score_pct"], 2) == round(4200 / 4500 * 100, 2)
    assert result["owners_low"] == 100000
    assert result["owners_high"] == 200000
    assert result["avg_playtime_min"] == 480
    assert result["cohort_genre"] == "indie"
    assert result["cohort_year"] == 2021


def test_normalize_free_to_play_has_zero_price():
    app_id, raw = RAW_FREE_TO_PLAY
    result = normalize_game(app_id, raw)
    assert result["price_cents"] == 0


def test_normalize_dlc_flags_is_dlc():
    app_id, raw = RAW_DLC
    result = normalize_game(app_id, raw)
    assert result["is_dlc"] is True


def test_normalize_skips_games_without_release_date():
    app_id, raw = RAW_MISSING_RELEASE_DATE
    assert normalize_game(app_id, raw) is None


def test_normalize_falls_back_to_steamspy_genre_string():
    app_id, raw = RAW_GENRE_STRING_ONLY
    result = normalize_game(app_id, raw)
    assert result["genres"] == ["Simulation", "Management"]
    assert result["tags"] == []
    assert result["cohort_genre"] == "simulation"


def test_normalize_handles_null_appdetails_without_raising():
    """appdetails: null (e.g. Steam's appdetails API returning
    {"success": false}) must not raise AttributeError. With no appdetails,
    there is also no release date, so the record is skipped (returns None)."""
    app_id, raw = RAW_APPDETAILS_NULL
    assert normalize_game(app_id, raw) is None


def test_normalize_handles_null_price_overview():
    app_id, raw = RAW_PRICE_OVERVIEW_NULL
    result = normalize_game(app_id, raw)
    assert result is not None
    assert result["price_cents"] is None


def test_normalize_handles_steamspy_tags_as_array():
    """SteamSpy returns "tags": [] (a JSON array, not an object) for games
    with no tags yet - must not raise AttributeError."""
    app_id, raw = RAW_STEAMSPY_TAGS_ARRAY
    result = normalize_game(app_id, raw)
    assert result is not None
    assert result["tags"] == []
