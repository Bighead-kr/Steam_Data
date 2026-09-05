import httpx
import pytest

from tracker.collector import CollectorNotImplementedError, _fetch_steamspy_genre, collect_games


def test_collect_games_raises_not_implemented_in_phase_a():
    with pytest.raises(CollectorNotImplementedError, match="Phase B"):
        collect_games(genres=["indie", "roguelike"])


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
