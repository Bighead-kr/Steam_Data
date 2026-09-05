# Steam/SteamSpy Collector (Phase B, Step 8) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the `collect_games()` stub in `src/tracker/collector.py` with a real implementation that pulls candidate games from SteamSpy's per-genre endpoint and enriches each with Steam Store's `appdetails` endpoint, producing the `{app_id: {"appdetails": ..., "steamspy": ...}}` shape already consumed by `normalize_game()` and `pipeline.upsert_raw_games()`.

**Architecture:** Two small HTTP-fetch helpers (SteamSpy genre listing, Steam Store appdetails) injected with an `httpx.Client` so tests substitute `httpx.MockTransport` instead of hitting the network. `collect_games()` composes them: one SteamSpy call per requested genre to build the candidate `app_id` set, then one Steam Store call per candidate app to fill in official genres/price/release date. A caller-supplied `sleep` function (defaulting to `time.sleep`) is called between HTTP calls so production respects the ~1 req/sec courtesy limit while tests run instantly.

**Tech Stack:** Python 3.12, `httpx` (client + `MockTransport` for tests), `pytest`.

**Spec:** `docs/superpowers/specs/2026-09-05-steam-hidden-gems-design.md` (Data sources section, Phase B step 8, `games_raw` shape in Data Model section).

## Global Constraints

- Raw records stored in `games_raw.raw_json` must keep the existing shape: `{"appdetails": <steam store data or None>, "steamspy": <steamspy record>}` — `normalize_game()` already depends on this exact shape and must not change.
- Rate-limit courtesy: one HTTP call at a time, with a sleep between calls (SteamSpy and Steam Store both recommend ~1 req/sec, per the spec's Deployment section).
- No new runtime dependency beyond `httpx`, which is already used in this repo (currently listed only under the `dev` extra) — promote it to a main dependency since `collector.py` now needs it outside of tests.
- Genres passed into `collect_games()` are SteamSpy genre-request values (e.g. `"Indie"`, `"Simulation"`) — `scripts/run_pipeline.py`'s `GENRES` list already exists and does not change in this plan.

---

## File Structure

- Modify `pyproject.toml`: move `httpx` from `dev` extra to `dependencies`.
- Modify `src/tracker/collector.py`: replace the `NotImplementedError` stub with `collect_games()` plus two private fetch helpers (`_fetch_steamspy_genre`, `_fetch_steam_appdetails`).
- Modify `tests/test_collector.py`: replace the Phase-A "raises NotImplementedError" test with real behavior tests against `httpx.MockTransport`.

## Task 1: Promote `httpx` to a main dependency

**Files:**
- Modify: `pyproject.toml`

**Interfaces:**
- Produces: `httpx` importable from `src/tracker/collector.py` at runtime (not just under `pip install -e ".[dev]"`).

- [ ] **Step 1: Edit `pyproject.toml`**

Move `"httpx>=0.27",` out of the `dev` list in `[project.optional-dependencies]` and into `[project] dependencies`:

```toml
[project]
name = "steam-hidden-gems"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "sqlalchemy>=2.0",
    "alembic>=1.13",
    "psycopg[binary]>=3.1",
    "pydantic-settings>=2.2",
    "pyyaml>=6.0",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "httpx>=0.27",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "testcontainers[postgresql]>=4.0",
    "ruff>=0.5",
]
```

- [ ] **Step 2: Reinstall the package to pick up the dependency move**

Run: `pip install -e ".[dev]"`
Expected: succeeds, no errors.

- [ ] **Step 3: Commit**

```bash
git add pyproject.toml
git commit -m "build: move httpx to main dependencies for collector" \
  -m "" \
  -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" \
  -m "Claude-Session: https://claude.ai/code/session_01R74jCvjuTMaxZPoMSty3cA"
```

## Task 2: SteamSpy genre-candidate fetcher

**Files:**
- Modify: `src/tracker/collector.py`
- Test: `tests/test_collector.py`

**Interfaces:**
- Produces: `_fetch_steamspy_genre(client: httpx.Client, genre: str) -> dict[int, dict]` — keys are `int` app ids, values are the raw per-game SteamSpy JSON objects (same shape as the `"steamspy"` half of the fixtures in `tests/fixtures/steam_samples.py`).
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_collector.py` (replacing its current content — see Task 4 for the final full-file version; for now just add this test alongside the existing one):

```python
import httpx

from tracker.collector import _fetch_steamspy_genre


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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_collector.py::test_fetch_steamspy_genre_parses_response_into_int_keyed_dict -v`
Expected: FAIL with `ImportError` / `AttributeError` — `_fetch_steamspy_genre` does not exist yet.

- [ ] **Step 3: Implement `_fetch_steamspy_genre`**

Replace the top of `src/tracker/collector.py` (keep `CollectorNotImplementedError` for now — it is removed in Task 4) with:

```python
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_collector.py::test_fetch_steamspy_genre_parses_response_into_int_keyed_dict -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tracker/collector.py tests/test_collector.py
git commit -m "feat(collector): fetch SteamSpy per-genre candidates" \
  -m "" \
  -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" \
  -m "Claude-Session: https://claude.ai/code/session_01R74jCvjuTMaxZPoMSty3cA"
```

## Task 3: Steam Store appdetails fetcher

**Files:**
- Modify: `src/tracker/collector.py`
- Test: `tests/test_collector.py`

**Interfaces:**
- Produces: `_fetch_steam_appdetails(client: httpx.Client, app_id: int) -> dict | None` — returns the `data` object on success, `None` when Steam reports `success: false` (delisted/invalid app, matching the `RAW_APPDETAILS_NULL` fixture shape already handled by `normalize_game()`).
- Consumes: nothing from other tasks.

- [ ] **Step 1: Write the failing tests**

Add to `tests/test_collector.py`:

```python
from tracker.collector import _fetch_steam_appdetails


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
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/test_collector.py -k fetch_steam_appdetails -v`
Expected: FAIL — `_fetch_steam_appdetails` does not exist yet.

- [ ] **Step 3: Implement `_fetch_steam_appdetails`**

Add to `src/tracker/collector.py` (below `_fetch_steamspy_genre`):

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_collector.py -k fetch_steam_appdetails -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/tracker/collector.py tests/test_collector.py
git commit -m "feat(collector): fetch Steam Store appdetails per app" \
  -m "" \
  -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" \
  -m "Claude-Session: https://claude.ai/code/session_01R74jCvjuTMaxZPoMSty3cA"
```

## Task 4: `collect_games()` composition + rate limiting

**Files:**
- Modify: `src/tracker/collector.py`
- Test: `tests/test_collector.py` (final full-file rewrite)

**Interfaces:**
- Consumes: `_fetch_steamspy_genre` and `_fetch_steam_appdetails` from Tasks 2-3.
- Produces: `collect_games(genres: list[str], *, client: httpx.Client | None = None, sleep: Callable[[float], None] = time.sleep) -> dict[int, dict]` — this is the function `scripts/run_pipeline.py` already calls as `collect_games(GENRES)`, and its return value is passed straight into `pipeline.upsert_raw_games()`.

- [ ] **Step 1: Write the failing test**

Replace `tests/test_collector.py` entirely with:

```python
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_collector.py -v`
Expected: FAIL on the `collect_games` tests — `collect_games` still raises `CollectorNotImplementedError`.

- [ ] **Step 3: Implement `collect_games()`**

Replace the remainder of `src/tracker/collector.py` (the old `collect_games` stub and now-unused `CollectorNotImplementedError`) so the full file reads:

```python
"""Collect Steam/SteamSpy candidate games for the configured target genres.

For each genre, fetch SteamSpy's per-genre candidate list, then enrich each
candidate app id with Steam Store's appdetails. Returns the exact
{app_id: {"appdetails": ..., "steamspy": ...}} shape `normalize_game()`
expects and `pipeline.upsert_raw_games()` stores verbatim.
"""

from __future__ import annotations

import time
from typing import Callable

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
```

Note: `CollectorNotImplementedError` is removed here — nothing outside `collector.py` and its own tests imports it (confirm with `grep -rn CollectorNotImplementedError src/ tests/ scripts/` before deleting; it should only appear in the file being rewritten and the old test file already replaced in Step 1).

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/test_collector.py -v`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add src/tracker/collector.py tests/test_collector.py
git commit -m "feat(collector): implement collect_games for Phase B" \
  -m "" \
  -m "Co-Authored-By: Claude Sonnet 5 <noreply@anthropic.com>" \
  -m "Claude-Session: https://claude.ai/code/session_01R74jCvjuTMaxZPoMSty3cA"
```

## Task 5: Full regression pass

**Files:** none (verification only)

- [ ] **Step 1: Run the full non-DB test suite**

Run: `pytest tests/ -v --ignore=tests/test_migrations.py --ignore=tests/test_api.py --ignore=tests/test_pipeline.py`
Expected: all pass (these three ignored files need Docker/testcontainers, which this task does not touch).

- [ ] **Step 2: Run `ruff` to confirm lint cleanliness**

Run: `ruff check src/tracker/collector.py tests/test_collector.py`
Expected: no errors.

- [ ] **Step 3: If Docker is available, run the full suite including DB-backed tests**

Run: `docker compose up -d && pytest tests/ -v`
Expected: all pass. (If Docker isn't available in this environment, skip — this task doesn't change any DB-touching code.)

---

## Self-Review Notes

- **Spec coverage:** Implements spec's Phase B step 8 (collector) exactly — SteamSpy candidate list per target genre + Steam Store appdetails enrichment, output shape matching the Data Model section's `games_raw.raw_json`.
- **Not covered by this plan** (spec's remaining Phase B steps 9-11 — scoring-constant tuning against real data, production deployment to Supabase/Render/Vercel, and the case-study writeup): these need a live `STEAM_API_KEY`/`DATABASE_URL` and account setup the user must do, so they're follow-up work once this collector is merged and can be run once against real data.
- **Type consistency:** `collect_games` signature (`genres: list[str]`) matches the existing call site in `scripts/run_pipeline.py:22` (`collect_games(GENRES)`) and the existing `tests/test_collector.py` call style (`collect_games(genres=[...])` also still works since `genres` is a positional-or-keyword parameter).
