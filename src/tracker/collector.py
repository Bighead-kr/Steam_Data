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
    # Without `cc`, Steam prices the response by the requester's IP geolocation
    # (observed: a Korea-based request got price_overview in KRW, e.g.
    # 2,980,000 = W29,800 - `price_cents` is documented and consumed
    # everywhere downstream as USD, so pin the country explicitly).
    response = client.get(STEAM_APPDETAILS_URL, params={"appids": str(app_id), "cc": "us"})
    response.raise_for_status()
    entry = response.json().get(str(app_id)) or {}
    if not entry.get("success"):
        return None
    return entry.get("data")


def collect_games(
    genres: list[str],
    *,
    client: httpx.Client | None = None,
    known_app_ids: frozenset[int] = frozenset(),
    limit: int | None = None,
    steamspy_sleep_seconds: float = 1.0,
    appdetails_sleep_seconds: float = 1.5,
    sleep: Callable[[float], None] = time.sleep,
) -> dict[int, dict]:
    """Fetch candidate games for `genres` from SteamSpy + Steam Store API
    and return {app_id: raw_json} ready for `pipeline.upsert_raw_games`.

    `known_app_ids` (typically every app_id already in `games_raw`) is
    skipped before any Steam Store call - a genre's candidate list can run
    into the tens of thousands, so re-enriching already-collected games on
    every run would blow through Steam Store's rate limit for no reason.
    `limit` caps how many *new* app ids get enriched in one call, so a
    single run finishes in bounded time regardless of how large a genre is;
    remaining candidates are picked up by the next run.

    One HTTP call at a time: `steamspy_sleep_seconds` between SteamSpy calls
    (SteamSpy's documented limit is 1 req/sec for this endpoint) and the
    slower `appdetails_sleep_seconds` between Steam Store calls (Steam
    Store's undocumented but widely-reported limit is ~200 req/5 min per
    IP, i.e. an average of 1.5 sec/req).
    """
    owned_client = client is None
    client = client or httpx.Client(timeout=10.0)
    try:
        candidates: dict[int, dict] = {}
        for genre in genres:
            candidates.update(_fetch_steamspy_genre(client, genre))
            sleep(steamspy_sleep_seconds)

        new_app_ids = [app_id for app_id in candidates if app_id not in known_app_ids]
        if limit is not None:
            new_app_ids = new_app_ids[:limit]

        results: dict[int, dict] = {}
        for app_id in new_app_ids:
            try:
                appdetails = _fetch_steam_appdetails(client, app_id)
            except httpx.HTTPStatusError:
                # Steam Store occasionally 500s for a single app id for no
                # documented reason (observed live: a multi-hour run lost
                # its entire, otherwise-successful progress to one bad app
                # id). Skip just this one - it's simply not in `results`,
                # so it isn't added to known_app_ids and gets retried on
                # the next run - rather than raising and losing every
                # other app already enriched in this batch.
                sleep(appdetails_sleep_seconds)
                continue
            results[app_id] = {"appdetails": appdetails, "steamspy": candidates[app_id]}
            sleep(appdetails_sleep_seconds)

        return results
    finally:
        if owned_client:
            client.close()
