import httpx

from tracker.collector import _fetch_steam_appdetails, _fetch_steamspy_genre, collect_games


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
    steamspy_by_genre = {
        "Indie": {100001: {"genre": "Indie, RPG", "positive": 10, "negative": 1}},
        "Roguelike": {
            100001: {"genre": "Indie, RPG", "positive": 10, "negative": 1},
            100002: {"genre": "Roguelike", "positive": 3, "negative": 0},
        },
    }
    appdetails_by_id = {
        100001: {"name": "Dungeon of Echoes"},
        100002: {"name": "Tiny Roguelike Gem"},
    }

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("request") == "genre":
            genre = request.url.params["genre"]
            return httpx.Response(
                200,
                json={str(k): v for k, v in steamspy_by_genre[genre].items()},
            )
        app_id = int(request.url.params["appids"])
        return httpx.Response(
            200,
            json={str(app_id): {"success": True, "data": appdetails_by_id[app_id]}},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleeps: list[float] = []

    result = collect_games(["Indie", "Roguelike"], client=client, sleep=sleeps.append)

    assert result == {
        100001: {
            "appdetails": {"name": "Dungeon of Echoes"},
            "steamspy": {"genre": "Indie, RPG", "positive": 10, "negative": 1},
        },
        100002: {
            "appdetails": {"name": "Tiny Roguelike Gem"},
            "steamspy": {"genre": "Roguelike", "positive": 3, "negative": 0},
        },
    }
    # 2 genre calls + 2 per-app appdetails calls = 4 sleeps (one after each call)
    assert len(sleeps) == 4


def test_collect_games_keeps_appdetails_none_when_steam_reports_failure():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.params.get("request") == "genre":
            return httpx.Response(200, json={"100003": {"genre": "Indie", "positive": 1, "negative": 0}})
        return httpx.Response(200, json={"100003": {"success": False}})

    client = httpx.Client(transport=httpx.MockTransport(handler))

    result = collect_games(["Indie"], client=client, sleep=lambda _: None)

    assert result == {
        100003: {
            "appdetails": None,
            "steamspy": {"genre": "Indie", "positive": 1, "negative": 0},
        }
    }
