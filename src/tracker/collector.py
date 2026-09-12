"""Collect Steam/SteamSpy candidate games for the configured target genres.

For each genre, fetch SteamSpy's per-genre candidate list, then enrich each
candidate app id with Steam Store's appdetails *and* SteamSpy's per-app
appdetails. Returns the exact
{app_id: {"appdetails": ..., "steamspy": ..., "source_genre": ...}} shape
`normalize_game()` expects and `pipeline.upsert_raw_games()` stores verbatim.
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
    (as a string) -> that game's SteamSpy record. Note that these records
    are *not* the full per-app record: the genre listing omits `tags` (and
    `genre`/`languages`) entirely - see `_fetch_steamspy_appdetails()`.
    """
    response = client.get(STEAMSPY_URL, params={"request": "genre", "genre": genre})
    response.raise_for_status()
    return {int(app_id): record for app_id, record in response.json().items()}


def _fetch_steamspy_appdetails(
    client: httpx.Client,
    app_id: int,
    *,
    attempts: int = 3,
    backoff_seconds: float = 3.0,
    sleep: Callable[[float], None] = time.sleep,
) -> dict | None:
    """Fetch SteamSpy's full per-app record, which carries `tags`.

    The genre listing this collector starts from has no `tags` key at all
    (verified live: its records stop at `ccu`), so without this second call
    every game normalizes to an empty tag list and the webapp's tag filter
    can never match anything.

    Two different failures have to stay distinguishable, because callers
    treat them differently:

      returns None  SteamSpy has no record for this app id. It answers with
                    a record full of nulls rather than an error status, so
                    "no name" is the tell. Nothing to wait for.
      raises        We never got an answer. SteamSpy reports overload as
                    HTTP 200 with the plain-text body 'Connection failed:
                    Too many connections' (observed live, ~6% of requests
                    during a busy stretch), which json() rejects. That is
                    transient, so back off and retry before giving up - a
                    caller that records an empty tag set here would make a
                    momentary blip permanent.
    """
    for attempt in range(1, attempts + 1):
        response = client.get(
            STEAMSPY_URL, params={"request": "appdetails", "appid": str(app_id)}
        )
        response.raise_for_status()
        try:
            record = response.json()
        except ValueError:
            if attempt == attempts:
                raise
            sleep(backoff_seconds * attempt)
            continue
        if not isinstance(record, dict) or not record.get("name"):
            return None
        return record
    return None


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

    Each record keeps `source_genre`: the genre whose SteamSpy list first
    surfaced this app. That is the honest cohort key - it is the question
    the webapp's genre filter actually asks ("show me indie games") - and
    unlike Steam's own `genres[0]` it is reachable for every genre we
    collect. Pass `genres` most-specific-first (roguelike before indie), so
    a roguelike that also sits in the indie list is cohorted as the former.

    One HTTP call at a time: `steamspy_sleep_seconds` between SteamSpy genre
    calls (SteamSpy's documented limit is 1 req/sec) and the slower
    `appdetails_sleep_seconds` between per-app rounds (Steam Store's
    undocumented but widely-reported limit is ~200 req/5 min per IP, i.e. an
    average of 1.5 sec/req). The per-app SteamSpy call rides inside that
    same round, so consecutive SteamSpy appdetails calls stay 1.5 sec apart
    and add no wall-clock time to a run.
    """
    owned_client = client is None
    client = client or httpx.Client(timeout=10.0)
    try:
        candidates: dict[int, dict] = {}
        source_genre: dict[int, str] = {}
        for genre in genres:
            listing = _fetch_steamspy_genre(client, genre)
            for app_id, record in listing.items():
                # setdefault, not update: the first (most specific) genre
                # that lists an app wins, so cohorts stay stable no matter
                # how many later lists also contain it.
                candidates.setdefault(app_id, record)
                source_genre.setdefault(app_id, genre)
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
            results[app_id] = {
                "appdetails": appdetails,
                "steamspy": _steamspy_record(client, app_id, candidates[app_id]),
                "source_genre": source_genre[app_id],
            }
            sleep(appdetails_sleep_seconds)

        return results
    finally:
        if owned_client:
            client.close()


def _steamspy_record(client: httpx.Client, app_id: int, listing_record: dict) -> dict:
    """The genre-listing record, upgraded with the per-app record when the
    extra call succeeds. Falling back to the listing record on failure keeps
    a transient SteamSpy hiccup from costing us the game entirely - we just
    lose its tags."""
    try:
        detailed = _fetch_steamspy_appdetails(client, app_id)
    except (httpx.HTTPError, ValueError):
        return listing_record
    if detailed is None:
        return listing_record
    return {**listing_record, **detailed}
