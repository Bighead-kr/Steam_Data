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
            records = dict([RAW_ROGUELIKE, RAW_FREE_TO_PLAY, RAW_GENRE_STRING_ONLY, RAW_DLC])
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
    # 4 games are seeded; the 4th is DLC and must not be ranked among games.
    assert len(body) == 3
    assert "Dungeon of Echoes: Soundtrack" not in {g["name"] for g in body}
    scores = [g["hidden_gem_score"] for g in body]
    assert scores == sorted(scores, reverse=True)


def test_list_gems_rejects_an_unbounded_limit(client):
    """`limit` reaches the database now, so it needs a ceiling - the old
    handler answered limit=100000 by materialising the entire table."""
    assert client.get("/games/gems", params={"limit": 100000}).status_code == 422
    assert client.get("/games/gems", params={"limit": 0}).status_code == 422


def test_list_gems_applies_limit_in_sql(client):
    response = client.get("/games/gems", params={"limit": 1})
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_list_genres_reports_only_genres_with_scored_games(client):
    response = client.get("/genres")
    assert response.status_code == 200
    body = response.json()
    by_value = {row["value"]: row["count"] for row in body}
    assert by_value == {"indie": 2, "simulation": 1}
    # Ordered by count, so the webapp's dropdown leads with the biggest cohort.
    assert [row["value"] for row in body] == ["indie", "simulation"]


def test_list_tags_returns_real_tag_values_with_counts(client):
    """The webapp used to ask for tags through a free-text box, which is a
    spelling test the user loses: SteamSpy's tags are exact-cased strings."""
    response = client.get("/tags")
    assert response.status_code == 200
    by_value = {row["value"]: row["count"] for row in response.json()}
    assert by_value["Roguelike"] == 2
    assert by_value["Pixel Graphics"] == 1


def test_list_tags_scopes_to_a_genre(client):
    response = client.get("/tags", params={"genre": "simulation"})
    assert response.status_code == 200
    # Farm Manager Deluxe is the only simulation game and it has no tags.
    assert response.json() == []


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
    games, less than the 4 total games). Both the filter and the limit live
    in SQL now (`tags @> '["Roguelike"]'` plus LIMIT), which keeps that
    ordering by construction - this test guards against a regression to
    "fetch everything, slice, then filter in Python".
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
