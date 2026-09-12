from __future__ import annotations

import datetime as dt
from collections.abc import Collection

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracker.models import Game, GameRaw, GameScore, PipelineRun
from tracker.normalizer import normalize_game
from tracker.scorer import score_games


def get_known_app_ids(session: Session) -> set[int]:
    return set(session.execute(select(GameRaw.app_id)).scalars().all())


def upsert_raw_games(session: Session, records: dict[int, dict]) -> None:
    if not records:
        return
    rows = [{"app_id": app_id, "raw_json": raw} for app_id, raw in records.items()]
    stmt = insert(GameRaw).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=[GameRaw.app_id],
        set_={"raw_json": stmt.excluded.raw_json, "fetched_at": dt.datetime.now(dt.UTC)},
    )
    session.execute(stmt)


def run_normalizer(
    session: Session, *, app_ids: Collection[int] | None = None, batch_size: int = 1000
) -> tuple[int, int]:
    """Normalize `games_raw` rows into `games`.

    `app_ids=None` (the default) scans the whole table - needed for a full
    backfill, but each `games_raw.raw_json` blob is several KB (movie/
    screenshot URLs, descriptions), so re-scanning the whole table on every
    call gets expensive as it grows. `run_pipeline.py`'s per-batch loop
    passes just that batch's app_ids to avoid re-transferring rows that
    haven't changed since the last call.
    """
    query = select(GameRaw)
    if app_ids is not None:
        query = query.where(GameRaw.app_id.in_(app_ids))
    raw_rows = session.execute(query).scalars().all()
    processed = 0
    skipped = 0
    upsert_rows = []
    for raw_row in raw_rows:
        try:
            normalized = normalize_game(raw_row.app_id, raw_row.raw_json)
        except Exception:  # noqa: BLE001 - any malformed raw record must not abort the batch
            # Malformed/incomplete API records (unexpected shapes normalize_game
            # doesn't defend against) should not abort the whole batch - treat
            # them the same as the "no release date" skip case below.
            skipped += 1
            continue
        if normalized is None:
            skipped += 1
            continue
        upsert_rows.append(normalized)
        processed += 1

    for i in range(0, len(upsert_rows), batch_size):
        chunk = upsert_rows[i : i + batch_size]
        stmt = insert(Game).values(chunk)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in Game.__table__.columns
            if col.name != "app_id"
        }
        stmt = stmt.on_conflict_do_update(index_elements=[Game.app_id], set_=update_cols)
        session.execute(stmt)

    return processed, skipped


def run_scorer(
    session: Session,
    prior_strength: float,
    min_cohort_size: int,
    *,
    batch_size: int = 1000,
) -> int:
    games = session.execute(select(Game)).scalars().all()
    game_dicts = [
        {
            "app_id": g.app_id,
            "review_count": g.review_count,
            "review_score_pct": g.review_score_pct,
            "owners_low": g.owners_low,
            "owners_high": g.owners_high,
            "cohort_genre": g.cohort_genre,
            "cohort_year": g.cohort_year,
        }
        for g in games
    ]
    scores = score_games(game_dicts, prior_strength=prior_strength, min_cohort_size=min_cohort_size)
    if not scores:
        return 0

    for s in scores:
        s["computed_at"] = dt.datetime.now(dt.UTC)

    for i in range(0, len(scores), batch_size):
        chunk = scores[i : i + batch_size]
        stmt = insert(GameScore).values(chunk)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in GameScore.__table__.columns
            if col.name != "app_id"
        }
        stmt = stmt.on_conflict_do_update(index_elements=[GameScore.app_id], set_=update_cols)
        session.execute(stmt)
    return len(scores)


def record_pipeline_run(
    session: Session,
    run_id: str,
    status: str,
    games_collected: int,
    games_new: int,
    started_at: dt.datetime,
    notes: str | None = None,
) -> None:
    # Create-only: no on_conflict_do_update needed since each run_id is unique per run.
    stmt = insert(PipelineRun).values(
        run_id=run_id,
        started_at=started_at,
        finished_at=dt.datetime.now(dt.UTC),
        status=status,
        games_collected=games_collected,
        games_new=games_new,
        notes=notes,
    )
    session.execute(stmt)
