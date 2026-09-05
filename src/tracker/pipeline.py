from __future__ import annotations

import datetime as dt

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from tracker.models import Game, GameRaw, GameScore, PipelineRun
from tracker.normalizer import normalize_game
from tracker.scorer import score_games


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


def run_normalizer(session: Session) -> tuple[int, int]:
    raw_rows = session.execute(select(GameRaw)).scalars().all()
    processed = 0
    skipped = 0
    upsert_rows = []
    for raw_row in raw_rows:
        normalized = normalize_game(raw_row.app_id, raw_row.raw_json)
        if normalized is None:
            skipped += 1
            continue
        upsert_rows.append(normalized)
        processed += 1

    if upsert_rows:
        stmt = insert(Game).values(upsert_rows)
        update_cols = {
            col.name: stmt.excluded[col.name]
            for col in Game.__table__.columns
            if col.name != "app_id"
        }
        stmt = stmt.on_conflict_do_update(index_elements=[Game.app_id], set_=update_cols)
        session.execute(stmt)

    return processed, skipped


def run_scorer(session: Session, prior_strength: float, min_cohort_size: int) -> int:
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

    stmt = insert(GameScore).values(scores)
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
    notes: str | None = None,
) -> None:
    stmt = insert(PipelineRun).values(
        run_id=run_id,
        started_at=dt.datetime.now(dt.UTC),
        finished_at=dt.datetime.now(dt.UTC),
        status=status,
        games_collected=games_collected,
        games_new=games_new,
        notes=notes,
    )
    session.execute(stmt)
