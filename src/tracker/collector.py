"""Collect Steam/SteamSpy candidate games for the configured target genres.

For each genre, fetch SteamSpy's per-genre candidate list, then enrich each
candidate app id with Steam Store's appdetails. Returns the exact
{app_id: {"appdetails": ..., "steamspy": ...}} shape `normalize_game()`
expects and `pipeline.upsert_raw_games()` stores verbatim.
"""

from __future__ import annotations

import time
from collections.abc import Callable

import httpx

STEAMSPY_URL = "https://steamspy.com/api.php"
STEAM_APPDETAILS_URL = "https://store.steampowered.com/api/appdetails"


def _fetch_steamspy_genre(client: httpx.Client, genre: str) -> dict[int, dict]:
    """Fetch SteamSpy's candidate list for one genre.

    SteamSpy's `genre` request returns a JSON object keyed by app id
    (as a string) -> that game's full SteamSpy record. Limited to roughly
    the top 1000 games for the genre, per SteamSpy's own documentation.
    """
    response = client.get(STEAMSPY_URL, params={"request": "genre", "genre": genre})
    response.raise_for_status()
    return {int(app_id): record for app_id, record in response.json().items()}


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


def collect_games(
    genres: list[str],
    *,
    client: httpx.Client | None = None,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[int, dict]:
    """Fetch candidate games for `genres` from SteamSpy + Steam Store API
    and return {app_id: raw_json} ready for `pipeline.upsert_raw_games`.

    One HTTP call at a time with a sleep between calls, per SteamSpy's and
    Steam Store's courtesy rate limit (~1 req/sec, undocumented but
    conventional for both).
    """
    owned_client = client is None
    client = client or httpx.Client(timeout=10.0)
    try:
        candidates: dict[int, dict] = {}
        for genre in genres:
            candidates.update(_fetch_steamspy_genre(client, genre))
            sleep(1.0)

        results: dict[int, dict] = {}
        for app_id, steamspy_record in candidates.items():
            appdetails = _fetch_steam_appdetails(client, app_id)
            results[app_id] = {"appdetails": appdetails, "steamspy": steamspy_record}
            sleep(1.0)

        return results
    finally:
        if owned_client:
            client.close()
