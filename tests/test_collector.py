import httpx
import pytest

from tracker.collector import (
    _fetch_steam_appdetails,
    _fetch_steamspy_appdetails,
    _fetch_steamspy_genre,
    collect_games,
)


def make_handler(
    *,
    steamspy_by_genre: dict[str, dict[int, dict]],
    appdetails_by_id: dict[int, dict],
    steamspy_details_by_id: dict[int, dict] | None = None,
    steam_status: dict[int, int] | None = None,
):
    """One MockTransport handler covering all three endpoints a run touches:
    SteamSpy's genre listing, SteamSpy's per-app record, and Steam Store's
    appdetails."""
    steamspy_details_by_id = steamspy_details_by_id or {}
    steam_status = steam_status or {}

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("request") == "genre":
            listing = steamspy_by_genre[params["genre"]]
            return httpx.Response(200, json={str(k): v for k, v in listing.items()})
        if params.get("request") == "appdetails":
            app_id = int(params["appid"])
            return httpx.Response(200, json=steamspy_details_by_id.get(app_id, {"name": None}))
        app_id = int(params["appids"])
        if steam_status.get(app_id, 200) != 200:
            return httpx.Response(steam_status[app_id], text="Internal Server Error")
        return httpx.Response(
            200, json={str(app_id): {"success": True, "data": appdetails_by_id[app_id]}}
        )

    return handler


def test_fetch_steamspy_genre_parses_response_into_int_keyed_dict():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["request"] == "genre"
        assert request.url.params["genre"] == "Indie"
        return httpx.Response(
            200,
            json={
                "100001": {"genre": "Indie, RPG", "positive": 10, "negative": 1},
                "100002": {"genre": "Indie", "positive": 5, "negative": 0},
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = _fetch_steamspy_genre(client, "Indie")

    assert result == {
        100001: {"genre": "Indie, RPG", "positive": 10, "negative": 1},
        100002: {"genre": "Indie", "positive": 5, "negative": 0},
    }


def test_fetch_steamspy_appdetails_returns_the_record_with_tags():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["request"] == "appdetails"
        assert request.url.params["appid"] == "100001"
        return httpx.Response(
            200, json={"name": "Dungeon of Echoes", "tags": {"Roguelike": 900, "Indie": 500}}
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))

    assert _fetch_steamspy_appdetails(client, 100001) == {
        "name": "Dungeon of Echoes",
        "tags": {"Roguelike": 900, "Indie": 500},
    }


def test_fetch_steamspy_appdetails_retries_a_transient_overload():
    """SteamSpy reports overload as HTTP 200 carrying the plain text
    'Connection failed: Too many connections' - observed live on roughly 6%
    of requests during a busy stretch. Retrying gets the record; treating
    the blip as 'no tags' would make it permanent."""
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.params["appid"])
        if len(calls) < 3:
            return httpx.Response(200, text="Connection failed: Too many connections")
        return httpx.Response(200, json={"name": "Dungeon of Echoes", "tags": {"Roguelike": 9}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []

    result = _fetch_steamspy_appdetails(client, 100001, sleep=sleeps.append)

    assert result == {"name": "Dungeon of Echoes", "tags": {"Roguelike": 9}}
    assert len(calls) == 3
    assert sleeps == [3.0, 6.0]


def test_fetch_steamspy_appdetails_raises_when_the_overload_persists():
    """Giving up must raise, not return None: None means 'SteamSpy has no
    such app' and would have the caller record an empty tag set forever."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="Connection failed: Too many connections")

    client = httpx.Client(transport=httpx.MockTransport(handler))

    with pytest.raises(ValueError):
        _fetch_steamspy_appdetails(client, 100001, sleep=lambda _: None)


def test_fetch_steamspy_appdetails_returns_none_for_an_unknown_app():
    """SteamSpy answers an app id it doesn't know with a record of nulls and
    a 200, not an error status."""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"appid": 999999, "name": None, "tags": []})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    assert _fetch_steamspy_appdetails(client, 999999) is None


def test_fetch_steam_appdetails_returns_data_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["appids"] == "100001"
        return httpx.Response(
            200,
            json={"100001": {"success": True, "data": {"name": "Dungeon of Echoes"}}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = _fetch_steam_appdetails(client, 100001)

    assert result == {"name": "Dungeon of Echoes"}


def test_fetch_steam_appdetails_returns_none_when_unsuccessful():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"999999": {"success": False}})

    client = httpx.Client(transport=httpx.MockTransport(handler))
    result = _fetch_steam_appdetails(client, 999999)

    assert result is None


def test_collect_games_merges_steamspy_and_appdetails_across_genres():
    handler = make_handler(
        steamspy_by_genre={
            "Simulation": {100002: {"positive": 3, "negative": 0}},
            "Indie": {
                100001: {"positive": 10, "negative": 1},
                100002: {"positive": 3, "negative": 0},
            },
        },
        appdetails_by_id={
            100001: {"name": "Dungeon of Echoes"},
            100002: {"name": "Tiny Roguelike Gem"},
        },
        steamspy_details_by_id={
            100001: {"name": "Dungeon of Echoes", "tags": {"Roguelike": 900}},
            100002: {"name": "Tiny Roguelike Gem", "tags": {"Management": 40}},
        },
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []

    result = collect_games(["Simulation", "Indie"], client=client, sleep=sleeps.append)

    assert result == {
        100002: {
            "appdetails": {"name": "Tiny Roguelike Gem"},
            "steamspy": {
                "positive": 3,
                "negative": 0,
                "name": "Tiny Roguelike Gem",
                "tags": {"Management": 40},
            },
            "source_genre": "Simulation",
        },
        100001: {
            "appdetails": {"name": "Dungeon of Echoes"},
            "steamspy": {
                "positive": 10,
                "negative": 1,
                "name": "Dungeon of Echoes",
                "tags": {"Roguelike": 900},
            },
            "source_genre": "Indie",
        },
    }
    # 2 genre calls (steamspy pace) + 2 per-app rounds (steam store pace).
    # The per-app SteamSpy call rides inside the round and adds no sleep.
    assert sleeps == [1.0, 1.0, 1.5, 1.5]


def test_collect_games_records_the_first_genre_that_listed_an_app():
    """`genres` is passed most-specific-first, so a simulation game that
    also sits in the (much larger) indie list must stay cohorted as
    simulation - otherwise every cohort collapses into "indie"."""
    handler = make_handler(
        steamspy_by_genre={
            "Simulation": {100001: {"positive": 10, "negative": 1}},
            "Indie": {100001: {"positive": 10, "negative": 1}},
        },
        appdetails_by_id={100001: {"name": "Farm Manager Deluxe"}},
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Simulation", "Indie"], client=client, sleep=lambda _: None)

    assert result[100001]["source_genre"] == "Simulation"


def test_collect_games_falls_back_to_the_listing_record_when_steamspy_details_fail():
    """Tags are an enrichment; a SteamSpy hiccup must cost us the tags, not
    the whole game."""

    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("request") == "genre":
            return httpx.Response(200, json={"100001": {"positive": 10, "negative": 1}})
        if params.get("request") == "appdetails":
            return httpx.Response(503, text="Service Unavailable")
        return httpx.Response(200, json={"100001": {"success": True, "data": {"name": "X"}}})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Indie"], client=client, sleep=lambda _: None)

    assert result[100001]["steamspy"] == {"positive": 10, "negative": 1}


def test_collect_games_skips_known_app_ids():
    handler = make_handler(
        steamspy_by_genre={
            "Indie": {100001: {"positive": 10, "negative": 1}, 100002: {"positive": 5}}
        },
        appdetails_by_id={100001: {"name": "100001"}, 100002: {"name": "100002"}},
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(
        ["Indie"], client=client, known_app_ids=frozenset({100001}), sleep=lambda _: None
    )

    assert list(result.keys()) == [100002]


def test_collect_games_respects_limit_on_new_candidates():
    handler = make_handler(
        steamspy_by_genre={"Indie": {app_id: {"positive": 1} for app_id in (100001, 100002, 100003)}},
        appdetails_by_id={app_id: {"name": str(app_id)} for app_id in (100001, 100002, 100003)},
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Indie"], client=client, limit=2, sleep=lambda _: None)

    assert len(result) == 2


def test_collect_games_keeps_appdetails_none_when_steam_reports_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        params = request.url.params
        if params.get("request") == "genre":
            return httpx.Response(200, json={"100003": {"positive": 1, "negative": 0}})
        if params.get("request") == "appdetails":
            return httpx.Response(200, json={"name": None})
        return httpx.Response(200, json={"100003": {"success": False}})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Indie"], client=client, sleep=lambda _: None)

    assert result == {
        100003: {
            "appdetails": None,
            "steamspy": {"positive": 1, "negative": 0},
            "source_genre": "Indie",
        }
    }


def test_collect_games_skips_a_single_appdetails_server_error_without_losing_the_batch():
    """Regression test: Steam Store occasionally 500s for one app id with
    no documented cause. A multi-hour real run lost its entire, otherwise-
    successful progress when this happened on one app id near the end of
    the batch - collect_games() must skip just that app id and keep the
    others already collected, not raise and lose everything."""
    handler = make_handler(
        steamspy_by_genre={"Indie": {app_id: {"positive": 1} for app_id in (100001, 100002, 100003)}},
        appdetails_by_id={app_id: {"name": str(app_id)} for app_id in (100001, 100003)},
        steam_status={100002: 500},
    )
    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Indie"], client=client, sleep=lambda _: None)

    assert set(result.keys()) == {100001, 100003}
