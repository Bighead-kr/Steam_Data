import copy

import pytest
from fixtures.steam_samples import (
    RAW_FREE_TO_PLAY,
    RAW_MISSING_RELEASE_DATE,
    RAW_ROGUELIKE,
)
from sqlalchemy import select
from testcontainers.postgres import PostgresContainer

from tracker.models import Base, Game, GameRaw, GameScore
from tracker.pipeline import (
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
        )
        session.commit()


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
