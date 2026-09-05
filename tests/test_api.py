import pytest
from fastapi.testclient import TestClient
from fixtures.steam_samples import (
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
