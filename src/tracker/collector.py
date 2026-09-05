import httpx

STEAMSPY_URL = "https://steamspy.com/api.php"


class CollectorNotImplementedError(NotImplementedError):
    """Raised because the real Steam/SteamSpy collector ships in Phase B."""


def _fetch_steamspy_genre(client: httpx.Client, genre: str) -> dict[int, dict]:
    """Fetch SteamSpy's candidate list for one genre.

    SteamSpy's `genre` request returns a JSON object keyed by app id
    (as a string) -> that game's full SteamSpy record. Limited to roughly
    the top 1000 games for the genre, per SteamSpy's own documentation.
    """
    response = client.get(STEAMSPY_URL, params={"request": "genre", "genre": genre})
    response.raise_for_status()
    return {int(app_id): record for app_id, record in response.json().items()}


def collect_games(genres: list[str]) -> dict[int, dict]:
    """Fetch candidate games for `genres` from SteamSpy + Steam Store API
    and return {app_id: raw_json} ready for `pipeline.upsert_raw_games`.

    Not implemented in Phase A — Phase A develops normalizer/scorer/API
    against tests/fixtures/steam_samples.py instead. See
    docs/superpowers/specs/2026-09-05-steam-hidden-gems-design.md.
    """
    raise CollectorNotImplementedError(
        "collect_games ships in Phase B once real Steam/SteamSpy calls are "
        "wired up; Phase A uses tests/fixtures/steam_samples.py instead."
    )
