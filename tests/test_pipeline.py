import copy
import datetime as dt

import pytest
from fixtures.steam_samples import (
    RAW_DLC,
    RAW_FREE_TO_PLAY,
    RAW_GENRE_STRING_ONLY,
    RAW_LOW_REVIEW_COUNT,
    RAW_MALFORMED_RECORD,
    RAW_MISSING_RELEASE_DATE,
    RAW_ROGUELIKE,
)
from sqlalchemy import select
from testcontainers.postgres import PostgresContainer

from tracker.models import Base, Game, GameRaw, GameScore
from tracker.pipeline import (
    get_known_app_ids,
    record_pipeline_run,
    run_normalizer,
    run_scorer,
    upsert_raw_games,
)


@pytest.fixture(scope="module")
def db_session_factory():
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        db_url = postgres.get_connection_url()
        from tracker.db import get_engine, get_sessionmaker

        engine = get_engine(db_url)
        Base.metadata.create_all(engine)
        yield get_sessionmaker(db_url)


def test_full_pipeline_normalizes_and_scores_fixtures(db_session_factory):
    records = dict([RAW_ROGUELIKE, RAW_FREE_TO_PLAY, RAW_MISSING_RELEASE_DATE])

    with db_session_factory() as session:
        upsert_raw_games(session, records)
        session.commit()

        processed, skipped = run_normalizer(session)
        session.commit()
        assert processed == 2  # RAW_MISSING_RELEASE_DATE is skipped
        assert skipped == 1

        scored = run_scorer(session, prior_strength=50.0, min_cohort_size=1)
        session.commit()
        assert scored == 2

        games = session.execute(select(Game)).scalars().all()
        assert {g.app_id for g in games} == {100001, 100002}

        scores = session.execute(select(GameScore)).scalars().all()
        assert {s.app_id for s in scores} == {100001, 100002}
        for s in scores:
            assert -1.0 <= s.hidden_gem_score <= 1.0

        record_pipeline_run(
            session,
            run_id="test-run-1",
            status="ok",
            games_collected=3,
            games_new=2,
            started_at=dt.datetime.now(dt.UTC),
        )
        session.commit()


def test_get_known_app_ids_returns_existing_raw_app_ids(db_session_factory):
    with db_session_factory() as session:
        upsert_raw_games(session, dict([RAW_ROGUELIKE, RAW_FREE_TO_PLAY]))
        session.commit()

        assert get_known_app_ids(session) >= {100001, 100002}


def test_upsert_raw_games_is_idempotent(db_session_factory):
    records = dict([RAW_ROGUELIKE])
    with db_session_factory() as session:
        upsert_raw_games(session, records)
        upsert_raw_games(session, records)  # re-run should not error or duplicate
        session.commit()

        rows = session.execute(
            select(GameRaw).where(GameRaw.app_id == 100001)
        ).scalars().all()
        assert len(rows) == 1


def test_rerun_updates_existing_game_and_score_data(db_session_factory):
    """Re-running the pipeline on changed source data must UPDATE existing
    Game/GameScore rows, not just avoid duplicating them (the cron use case:
    review counts change between weekly runs)."""
    app_id, raw = RAW_ROGUELIKE

    with db_session_factory() as session:
        upsert_raw_games(session, {app_id: raw})
        session.commit()
        run_normalizer(session)
        session.commit()
        run_scorer(session, prior_strength=50.0, min_cohort_size=1)
        session.commit()

        review_count_before = session.get(Game, app_id).review_count
        quality_score_before = session.get(GameScore, app_id).quality_score

        mutated_raw = copy.deepcopy(raw)
        mutated_raw["steamspy"]["positive"] = 100
        mutated_raw["steamspy"]["negative"] = 900

        upsert_raw_games(session, {app_id: mutated_raw})
        session.commit()
        processed, _skipped = run_normalizer(session)
        session.commit()
        # db_session_factory is module-scoped and shared with other tests in this
        # file, so other raw rows may already exist; assert only on this game.
        assert processed >= 1

        scored = run_scorer(session, prior_strength=50.0, min_cohort_size=1)
        session.commit()
        assert scored >= 1

        game_after = session.get(Game, app_id)
        score_after = session.get(GameScore, app_id)

        assert game_after.review_count == 1000
        assert game_after.review_count != review_count_before
        assert score_after.quality_score != quality_score_before


def test_run_normalizer_skips_malformed_row_without_aborting_batch(db_session_factory):
    """A single malformed/incomplete raw record must not raise out of
    run_normalizer and abort the whole batch - it should be counted as
    skipped, and other rows in the same batch must still be processed.

    db_session_factory is module-scoped and shared with other tests in this
    file, so raw rows accumulate across tests (run_normalizer processes all
    games_raw rows each call) - assert only on this test's own two rows,
    not on the absolute processed/skipped counts.
    """
    good_app_id, good_raw = RAW_LOW_REVIEW_COUNT
    bad_app_id, bad_raw = RAW_MALFORMED_RECORD

    with db_session_factory() as session:
        upsert_raw_games(session, {good_app_id: good_raw, bad_app_id: bad_raw})
        session.commit()

        processed, skipped = run_normalizer(session)
        session.commit()

        assert processed >= 1
        assert skipped >= 1

        good_game = session.get(Game, good_app_id)
        assert good_game is not None
        assert session.get(Game, bad_app_id) is None


def test_run_normalizer_and_run_scorer_chunk_across_batches(db_session_factory):
    """Upserts must be chunked into multiple statements rather than one
    giant VALUES(...) list (Postgres' ~65535 bind-param ceiling). Verified
    at small scale via an overridable batch_size, with 5 fixture rows split
    across 3 batches of size 2."""
    records = dict(
        [
            RAW_ROGUELIKE,
            RAW_FREE_TO_PLAY,
            RAW_DLC,
            RAW_GENRE_STRING_ONLY,
            RAW_LOW_REVIEW_COUNT,
        ]
    )

    with db_session_factory() as session:
        upsert_raw_games(session, records)
        session.commit()

        processed, _skipped = run_normalizer(session, batch_size=2)
        session.commit()
        assert processed >= 5

        scored = run_scorer(session, prior_strength=50.0, min_cohort_size=1, batch_size=2)
        session.commit()
        assert scored >= 5

        games = session.execute(select(Game)).scalars().all()
        assert {100001, 100002, 100003, 100006, 100005} <= {g.app_id for g in games}

        scores = session.execute(select(GameScore)).scalars().all()
        assert {100001, 100002, 100003, 100006, 100005} <= {s.app_id for s in scores}
