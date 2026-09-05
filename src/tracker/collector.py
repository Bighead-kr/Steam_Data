class CollectorNotImplementedError(NotImplementedError):
    """Raised because the real Steam/SteamSpy collector ships in Phase B."""


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
