"""Repair `games_raw` rows collected before the collector stored tags and
source genre, without re-fetching Steam Store appdetails for all of them.

Two independent phases, both resumable:

  --phase source-genre   2 SteamSpy calls total. Stamps every raw row with
                         the genre list it belongs to, which is what
                         cohort_genre is derived from. Seconds to run.

  --phase tags           One SteamSpy call per game that has no tags yet,
                         paced at 1 req/sec. Hours for a full table, but it
                         can be stopped and resumed at any point - rows
                         that already have tags are skipped.

Both phases re-normalize what they touched; the scorer runs once at the end
(it always recomputes the whole table anyway).

    python scripts/backfill_steamspy.py --phase source-genre
    python scripts/backfill_steamspy.py --phase tags --limit 2000
"""

import argparse
import sys
import time
from pathlib import Path

import httpx
from sqlalchemy import func, select
from sqlalchemy.orm import Session, attributes

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from tracker.collector import _fetch_steamspy_appdetails, _fetch_steamspy_genre
from tracker.config import TARGET_GENRES, get_settings
from tracker.db import get_sessionmaker
from tracker.models import GameRaw
from tracker.pipeline import run_normalizer, run_scorer

COMMIT_EVERY = 200


def _mark_dirty(row: GameRaw) -> None:
    # SQLAlchemy can't see mutations *inside* a JSONB dict, so an in-place
    # edit to raw_json is invisible to the flush without this.
    attributes.flag_modified(row, "raw_json")


def backfill_source_genre(session: Session, client: httpx.Client) -> int:
    genre_of: dict[int, str] = {}
    for genre in TARGET_GENRES:
        for app_id in _fetch_steamspy_genre(client, genre):
            genre_of.setdefault(app_id, genre)
        time.sleep(1.0)
    print(f"[source-genre] steamspy lists cover {len(genre_of)} app ids")

    updated: list[int] = []
    rows = session.execute(select(GameRaw)).scalars().all()
    for row in rows:
        genre = genre_of.get(row.app_id)
        if genre is None or row.raw_json.get("source_genre") == genre:
            continue
        row.raw_json = {**row.raw_json, "source_genre": genre}
        _mark_dirty(row)
        updated.append(row.app_id)

    session.commit()
    print(f"[source-genre] stamped {len(updated)} of {len(rows)} rows")
    if updated:
        processed, skipped = run_normalizer(session, app_ids=updated)
        session.commit()
        print(f"[source-genre] normalized {processed}, skipped {skipped}")
    return len(updated)


def _app_ids_needing_tags(session: Session, limit: int | None) -> list[int]:
    """Ask the database which rows still need tags, instead of pulling every
    raw_json blob over the wire to decide in Python.

    games_raw holds ~9.7k rows of several KB each (screenshot and movie URLs,
    descriptions), so a full SELECT is tens of MB - and this script is meant
    to be stopped and resumed, which would pay that cost again every time.
    The same mistake in the normalizer was the main driver of a Supabase
    egress overage."""
    stmt = select(GameRaw.app_id).where(
        ~func.jsonb_exists(GameRaw.raw_json["steamspy"], "tags")
    ).order_by(GameRaw.app_id)
    if limit is not None:
        stmt = stmt.limit(limit)
    return list(session.execute(stmt).scalars().all())


def backfill_tags(session: Session, client: httpx.Client, limit: int | None) -> int:
    app_ids = _app_ids_needing_tags(session, limit)
    print(f"[tags] {len(app_ids)} rows to enrich (1 req/sec)")

    done: list[int] = []
    pending: list[int] = []
    for i, app_id in enumerate(app_ids, start=1):
        row = session.get(GameRaw, app_id)
        if row is None:
            continue
        try:
            detailed = _fetch_steamspy_appdetails(client, row.app_id)
        except (httpx.HTTPError, ValueError) as exc:
            # Leave the row untouched so the next run retries it.
            print(f"[tags] {row.app_id} failed ({exc.__class__.__name__}), will retry next run")
            time.sleep(1.0)
            continue
        if detailed is not None:
            steamspy = {**(row.raw_json.get("steamspy") or {}), **detailed}
            row.raw_json = {**row.raw_json, "steamspy": steamspy}
        else:
            # SteamSpy knows nothing about this app; record an empty tag set
            # so the next run doesn't ask again forever.
            steamspy = {**(row.raw_json.get("steamspy") or {}), "tags": {}}
            row.raw_json = {**row.raw_json, "steamspy": steamspy}
        _mark_dirty(row)
        pending.append(row.app_id)
        time.sleep(1.0)

        if len(pending) >= COMMIT_EVERY:
            session.commit()
            run_normalizer(session, app_ids=pending)
            session.commit()
            done.extend(pending)
            pending = []
            print(f"[tags] {i}/{len(app_ids)} enriched")
            # Committed rows stay in the identity map holding their raw_json
            # blobs; over a full run that is the whole table in memory again.
            session.expunge_all()

    if pending:
        session.commit()
        run_normalizer(session, app_ids=pending)
        session.commit()
        done.extend(pending)
    print(f"[tags] enriched {len(done)} rows")
    return len(done)


def main() -> None:
    # The tags phase runs for hours and its only progress report is these
    # prints; piped to a file (nohup, a background job) Python block-buffers
    # stdout and the file stays empty the whole time.
    sys.stdout.reconfigure(line_buffering=True)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--phase", choices=["source-genre", "tags", "all"], default="all")
    parser.add_argument("--limit", type=int, default=None, help="max rows for the tags phase")
    args = parser.parse_args()

    settings = get_settings()
    session_factory = get_sessionmaker(settings.database_url)

    with session_factory() as session, httpx.Client(timeout=20.0) as client:
        if args.phase in ("source-genre", "all"):
            backfill_source_genre(session, client)
        if args.phase in ("tags", "all"):
            backfill_tags(session, client, args.limit)

        scored = run_scorer(
            session,
            prior_strength=settings.bayesian_prior_strength,
            min_cohort_size=settings.min_cohort_size,
        )
        session.commit()
        print(f"[scorer] {scored} games scored")


if __name__ == "__main__":
    main()
