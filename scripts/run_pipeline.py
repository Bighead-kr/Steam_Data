"""GitHub Actions cron entrypoint. Raises CollectorNotImplementedError until
Phase B wires up real Steam/SteamSpy calls — this is expected in Phase A."""

import datetime as dt
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tracker.collector import collect_games
from tracker.config import get_settings
from tracker.db import get_sessionmaker
from tracker.pipeline import (
    get_known_app_ids,
    record_pipeline_run,
    run_normalizer,
    run_scorer,
    upsert_raw_games,
)

GENRES = ["indie", "roguelike", "simulation", "management"]
# Steam Store's undocumented rate limit (~200 req/5min per IP) means a single
# run can only safely enrich a few thousand new games - candidates per genre
# can run into the tens of thousands, so collection continues across days.
DAILY_ENRICH_LIMIT = 5000


def main() -> None:
    settings = get_settings()
    session_factory = get_sessionmaker(settings.database_url)
    run_id = str(uuid.uuid4())
    started_at = dt.datetime.now(dt.UTC)

    with session_factory() as session:
        try:
            known_app_ids = get_known_app_ids(session)
            records = collect_games(
                GENRES, known_app_ids=frozenset(known_app_ids), limit=DAILY_ENRICH_LIMIT
            )
            upsert_raw_games(session, records)
            session.commit()

            processed, skipped = run_normalizer(session)
            session.commit()

            scored = run_scorer(
                session,
                prior_strength=settings.bayesian_prior_strength,
                min_cohort_size=settings.min_cohort_size,
            )
            session.commit()

            record_pipeline_run(
                session,
                run_id=run_id,
                status="ok",
                games_collected=len(records),
                games_new=processed,
                started_at=started_at,
                notes=f"skipped={skipped} scored={scored}",
            )
            session.commit()
        except Exception as exc:
            session.rollback()
            record_pipeline_run(
                session,
                run_id=run_id,
                status="failed",
                games_collected=0,
                games_new=0,
                started_at=started_at,
                notes=str(exc),
            )
            session.commit()
            raise


if __name__ == "__main__":
    main()
