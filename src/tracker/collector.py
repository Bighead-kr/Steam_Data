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


STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


def _fetch_steam_appdetails(client: httpx.Client, app_id: int) -> dict | None:
    """Fetch Steam Store's appdetails for one app.

    Returns None when Steam reports success: false (delisted/invalid app
    id) - normalize_game() already treats a None `appdetails` value as a
    known, handled case (see RAW_APPDETAILS_NULL fixture).
    """
    response = client.get(STEAM_APPDETAILS_URL, params={"appids": str(app_id)})
    response.raise_for_status()
    entry = response.json().get(str(app_id)) or {}
    if not entry.get("success"):
        return None
    return entry.get("data")


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
