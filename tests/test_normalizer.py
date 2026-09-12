from fixtures.steam_samples import (
    RAW_APPDETAILS_NULL,
    RAW_CONTENT_DESCRIPTOR_FIRST,
    RAW_CONTENT_DESCRIPTORS_ONLY,
    RAW_DLC,
    RAW_FREE_TO_PLAY,
    RAW_GENRE_LISTING_SHAPE,
    RAW_GENRE_STRING_ONLY,
    RAW_MISSING_RELEASE_DATE,
    RAW_PRICE_OVERVIEW_NULL,
    RAW_ROGUELIKE,
    RAW_SOURCE_GENRE,
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


def test_normalize_cohort_genre_skips_content_descriptors():
    """genres[0] can be a content-rating descriptor (Sexual Content, Nudity,
    Violent, Gore, ...), not a real genre - cohort_genre must skip past
    those to the first actual genre."""
    app_id, raw = RAW_CONTENT_DESCRIPTOR_FIRST
    result = normalize_game(app_id, raw)
    assert result["genres"][0] == "Sexual Content"  # raw genre order preserved
    assert result["cohort_genre"] == "indie"


def test_normalize_cohort_genre_falls_back_to_unknown_when_only_descriptors():
    app_id, raw = RAW_CONTENT_DESCRIPTORS_ONLY
    result = normalize_game(app_id, raw)
    assert result["cohort_genre"] == "unknown"


def test_normalize_uses_source_genre_as_the_cohort_key():
    """The SteamSpy list an app was collected from beats Steam's own
    genres[0]. Steam orders that array by genre id, so Action (id 1) crowds
    out Simulation (id 28) on any game carrying both - on the production
    table genres[0] produced 4,558 "action" cohorts and exactly one
    "simulation", making the webapp's genre filter useless."""
    app_id, raw = RAW_SOURCE_GENRE
    result = normalize_game(app_id, raw)
    assert result["genres"][0] == "Action"  # raw genre order preserved
    assert result["cohort_genre"] == "simulation"


def test_normalize_genre_listing_shape_yields_no_tags():
    """Pins the bug that shipped: a row collected from SteamSpy's genre
    listing has no `tags` key whatsoever, so it normalizes to an empty tag
    list. Such rows need the per-app SteamSpy call (see the collector) or
    the tag backfill - they are not something normalize_game can rescue."""
    app_id, raw = RAW_GENRE_LISTING_SHAPE
    result = normalize_game(app_id, raw)
    assert result is not None
    assert result["tags"] == []
    # ...and with no source_genre recorded either, it falls back to Steam's
    # genre order, which is exactly how "action" came to dominate.
    assert result["cohort_genre"] == "action"


def test_normalize_handles_steamspy_tags_as_array():
    """SteamSpy returns "tags": [] (a JSON array, not an object) for games
    with no tags yet - must not raise AttributeError."""
    app_id, raw = RAW_STEAMSPY_TAGS_ARRAY
    result = normalize_game(app_id, raw)
    assert result is not None
    assert result["tags"] == []
