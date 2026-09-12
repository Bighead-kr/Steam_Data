import os
import subprocess

from sqlalchemy import create_engine, inspect
from testcontainers.postgres import PostgresContainer


def test_alembic_upgrade_creates_expected_tables():
    with PostgresContainer("postgres:16", driver="psycopg") as postgres:
        db_url = postgres.get_connection_url()
        env = {**os.environ, "DATABASE_URL": db_url, "STEAM_API_KEY": "test"}
        subprocess.run(["alembic", "upgrade", "head"], check=True, env=env)

        engine = create_engine(db_url)
        inspector = inspect(engine)
        tables = set(inspector.get_table_names())
        assert {"games_raw", "games", "game_scores", "pipeline_runs"} <= tables

        # The indexes the gems query depends on: ordering by hidden_gem_score,
        # filtering by cohort_genre, and JSONB containment on tags. The ORM
        # declares all three too, so create_all() and alembic agree.
        assert "ix_game_scores_hidden_gem_score" in {
            ix["name"] for ix in inspector.get_indexes("game_scores")
        }
        game_indexes = {ix["name"] for ix in inspector.get_indexes("games")}
        assert {"ix_games_cohort_genre", "ix_games_tags"} <= game_indexes
