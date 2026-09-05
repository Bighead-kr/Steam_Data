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
        tables = set(inspect(engine).get_table_names())
        assert {"games_raw", "games", "game_scores", "pipeline_runs"} <= tables
