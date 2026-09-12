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
# collect_games() blocks for the whole batch before returning, so a large
# DAILY_ENRICH_LIMIT run can take hours - long enough that a dropped DB
# connection (observed in practice against Supabase's pooler) loses the
# entire run's progress. Committing in small batches bounds that loss to at
# most one batch, and makes newly-collected games queryable well before the
# full run finishes.
BATCH_ENRICH_LIMIT = 50


def main() -> None:
    settings = get_settings()
    session_factory = get_sessionmaker(settings.database_url)
    run_id = str(uuid.uuid4())
    started_at = dt.datetime.now(dt.UTC)

    total_collected = 0
    # run_normalizer() is now scoped to just the current batch's app_ids
    # (not a full games_raw scan - see its docstring), so its return value
    # is a per-batch delta and must be summed across batches for the
    # summary row. run_scorer() still scans the whole `games` table (much
    # smaller than games_raw's raw_json blobs) on every call, so its return
    # value already describes the full current state - keep only the most
    # recent call's number for that one, never sum it (an earlier version
    # summed a full-state number across batches and reported a wrong total).
    processed_total = 0
    skipped_total = 0
    scored = 0

    try:
        while total_collected < DAILY_ENRICH_LIMIT:
            batch_limit = min(BATCH_ENRICH_LIMIT, DAILY_ENRICH_LIMIT - total_collected)
            with session_factory() as session:
                known_app_ids = get_known_app_ids(session)
                records = collect_games(
                    GENRES, known_app_ids=frozenset(known_app_ids), limit=batch_limit
                )
                if not records:
                    break

                upsert_raw_games(session, records)
                # Normalize/score after every batch (not just once at the
                # end) so `games`/`game_scores` - the tables the webapp
                # actually queries - stay current while a large run is still
                # in progress, instead of only updating once the whole run
                # (which can take hours) finishes or fails.
                #
                # app_ids=records.keys() scopes the normalizer to just this
                # batch instead of re-scanning all of games_raw (whose
                # raw_json blobs run several KB each) on every iteration -
                # doing that scan every batch was pulling the whole,
                # ever-growing raw table over the wire dozens of times per
                # run and was the main driver of a Supabase egress overage.
                processed, skipped = run_normalizer(session, app_ids=records.keys())
                processed_total += processed
                skipped_total += skipped
                scored = run_scorer(
                    session,
                    prior_strength=settings.bayesian_prior_strength,
                    min_cohort_size=settings.min_cohort_size,
                )
                session.commit()

            total_collected += len(records)

            if len(records) < batch_limit:
                # Fewer new candidates than asked for means the genre
                # candidate lists are exhausted for today - further looping
                # would just repeat empty SteamSpy fetches.
                break

        with session_factory() as session:
            record_pipeline_run(
                session,
                run_id=run_id,
                status="ok",
                games_collected=total_collected,
                games_new=processed_total,
                started_at=started_at,
                notes=f"skipped={skipped_total} scored={scored}",
            )
            session.commit()
    except Exception as exc:
        with session_factory() as session:
            record_pipeline_run(
                session,
                run_id=run_id,
                status="failed",
                games_collected=total_collected,
                games_new=processed_total,
                started_at=started_at,
                notes=str(exc),
            )
            session.commit()
        raise


if __name__ == "__main__":
    main()
