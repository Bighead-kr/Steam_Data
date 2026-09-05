"""GitHub Actions cron entrypoint. Raises CollectorNotImplementedError until
Phase B wires up real Steam/SteamSpy calls — this is expected in Phase A."""

import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tracker.collector import collect_games
from tracker.config import get_settings
from tracker.db import get_sessionmaker
from tracker.pipeline import record_pipeline_run, run_normalizer, run_scorer, upsert_raw_games

GENRES = ["indie", "roguelike", "simulation", "management"]


def main() -> None:
    settings = get_settings()
    session_factory = get_sessionmaker(settings.database_url)
    run_id = str(uuid.uuid4())

    with session_factory() as session:
        try:
            records = collect_games(GENRES)
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
                notes=str(exc),
            )
            session.commit()
            raise


if __name__ == "__main__":
    main()
