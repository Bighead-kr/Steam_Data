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
    RAW_PRICE_OVERVIEW_NULL,
    RAW_ROGUELIKE,
)
from sqlalchemy import insert, select
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


def test_run_normalizer_app_ids_scopes_to_only_those_rows(db_session_factory):
    """run_pipeline.py passes app_ids=records.keys() per collection batch so
    the normalizer doesn't re-scan/re-transfer the whole (large, raw_json-
    heavy) games_raw table on every batch - only the given app_ids' raw rows
    should be read and normalized, others left untouched.

    Uses fixtures no earlier test in this module has normalized yet
    (db_session_factory is module-scoped and shared), so the "left
    untouched" assertion isn't polluted by another test's Game row.
    """
    dlc_id, dlc_raw = RAW_DLC
    genre_id, genre_raw = RAW_GENRE_STRING_ONLY
    assert session_has_no_game(db_session_factory, dlc_id, genre_id)

    with db_session_factory() as session:
        upsert_raw_games(session, {dlc_id: dlc_raw, genre_id: genre_raw})
        session.commit()

        processed, skipped = run_normalizer(session, app_ids=[dlc_id])
        session.commit()

        assert processed == 1
        assert skipped == 0
        assert session.get(Game, dlc_id) is not None
        # genre_id's raw row exists but was outside app_ids - must not be
        # normalized as a side effect of this call.
        assert session.get(Game, genre_id) is None


def session_has_no_game(db_session_factory, *app_ids: int) -> bool:
    with db_session_factory() as session:
        return all(session.get(Game, app_id) is None for app_id in app_ids)


def test_run_normalizer_and_run_scorer_chunk_across_batches(db_session_factory):
    """Upserts must be chunked into multiple statements rather than one
    giant VALUES(...) list (Postgres' ~65535 bind-param ceiling). Verified
    at small scale via an overridable batch_size, with 5 fixture rows split
    across 3 batches of size 2."""
    records = dict(
        [
            RAW_ROGUELIKE,
            RAW_FREE_TO_PLAY,
            RAW_PRICE_OVERVIEW_NULL,
            RAW_GENRE_STRING_ONLY,
            RAW_LOW_REVIEW_COUNT,
        ]
    )
    app_ids = {100001, 100002, 100008, 100006, 100005}

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
        assert app_ids <= {g.app_id for g in games}

        scores = session.execute(select(GameScore)).scalars().all()
        assert app_ids <= {s.app_id for s in scores}


def test_run_scorer_excludes_dlc_and_deletes_its_stale_score(db_session_factory):
    """DLC is normalized (it's a real Steam app) but must never be scored:
    its reviews and owners ride on the base game, so letting it into a
    cohort skews every percentile in it. A score written before this rule
    existed has to be cleaned up too, not just left in place by the upsert."""
    with db_session_factory() as session:
        upsert_raw_games(session, dict([RAW_ROGUELIKE, RAW_FREE_TO_PLAY, RAW_DLC]))
        session.commit()
        run_normalizer(session)
        session.commit()

        # A stale score, as an older scorer would have written it.
        session.execute(
            insert(GameScore).values(
                app_id=100003,
                quality_score=90.0,
                quality_pctile=1.0,
                exposure_pctile=1.0,
                hidden_gem_score=0.0,
                computed_at=dt.datetime.now(dt.UTC),
            )
        )
        session.commit()

        run_scorer(session, prior_strength=50.0, min_cohort_size=1)
        session.commit()

        assert session.get(Game, 100003) is not None
        assert session.get(GameScore, 100003) is None
        assert session.get(GameScore, 100001) is not None
