import pytest
from fastapi.testclient import TestClient
from fixtures.steam_samples import (
    RAW_DLC,
    RAW_FREE_TO_PLAY,
    RAW_GENRE_STRING_ONLY,
    RAW_ROGUELIKE,
)
from testcontainers.postgres import PostgresContainer

from tracker.models import Base
from tracker.pipeline import run_normalizer, run_scorer, upsert_raw_games


@pytest.fixture(scope="module")
def client():
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        db_url = postgres.get_connection_url()
        from tracker.api.app import app, get_session
        from tracker.db import get_engine, get_sessionmaker

        engine = get_engine(db_url)
        Base.metadata.create_all(engine)
        session_factory = get_sessionmaker(db_url)

        with session_factory() as session:
            records = dict([RAW_ROGUELIKE, RAW_FREE_TO_PLAY, RAW_GENRE_STRING_ONLY])
            upsert_raw_games(session, records)
            session.commit()
            run_normalizer(session)
            session.commit()
            run_scorer(session, prior_strength=50.0, min_cohort_size=1)
            session.commit()

        def override_get_session():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        yield TestClient(app)


def test_cors_allows_browser_requests_from_any_origin(client):
    """The Next.js webapp calls this API cross-origin (different port in dev,
    different domain once deployed); without CORS headers the browser's
    fetch() fails before the response body is ever read."""
    response = client.get("/games/gems", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"


def test_list_gems_returns_ranked_results(client):
    response = client.get("/games/gems")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 3
    scores = [g["hidden_gem_score"] for g in body]
    assert scores == sorted(scores, reverse=True)


def test_list_gems_filters_by_genre(client):
    response = client.get("/games/gems", params={"genre": "simulation"})
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "Farm Manager Deluxe"


def test_list_gems_filters_by_max_price(client):
    response = client.get("/games/gems", params={"max_price_cents": 0})
    assert response.status_code == 200
    body = response.json()
    assert [g["name"] for g in body] == ["Free Roguelite Arena"]


def test_list_gems_tag_filter_applies_before_limit():
    """Regression test: the tag filter must apply to the full candidate set
    *before* slicing to `limit`, not after. Seeds 4 games where only 2 carry
    the "Roguelike" tag, with `limit=3` (greater than the 2 tag-matching
    games, less than the 4 total games). If a future change moved the
    `limit` into the SQL query (applied before the Python tag filter), this
    would risk returning fewer than the 2 tag-matching games.
    """
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        db_url = postgres.get_connection_url()
        from tracker.api.app import app, get_session
        from tracker.db import get_engine, get_sessionmaker

        engine = get_engine(db_url)
        Base.metadata.create_all(engine)
        session_factory = get_sessionmaker(db_url)

        with session_factory() as session:
            records = dict(
                [RAW_ROGUELIKE, RAW_FREE_TO_PLAY, RAW_DLC, RAW_GENRE_STRING_ONLY]
            )
            upsert_raw_games(session, records)
            session.commit()
            run_normalizer(session)
            session.commit()
            run_scorer(session, prior_strength=50.0, min_cohort_size=1)
            session.commit()

        def override_get_session():
            with session_factory() as session:
                yield session

        app.dependency_overrides[get_session] = override_get_session
        try:
            local_client = TestClient(app)
            response = local_client.get(
                "/games/gems", params={"tag": "Roguelike", "limit": 3}
            )
            assert response.status_code == 200
            body = response.json()
            assert {g["name"] for g in body} == {
                "Dungeon of Echoes",
                "Free Roguelite Arena",
            }
        finally:
            app.dependency_overrides.pop(get_session, None)
