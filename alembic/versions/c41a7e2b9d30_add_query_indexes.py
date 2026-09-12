"""add indexes for the gems query

The webapp's only hot query orders every scored game by hidden_gem_score and
filters on cohort_genre and tags. Until now all three were answered by a
sequential scan over the whole table because the API pulled every matching
row into Python before slicing; now that the limit and the tag filter are
pushed into SQL, these indexes are what make that cheap.

Revision ID: c41a7e2b9d30
Revises: bb0cdd887d52
Create Date: 2026-09-12 14:05:00.000000

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'c41a7e2b9d30'
down_revision: str | Sequence[str] | None = 'bb0cdd887d52'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # A plain btree serves the DESC order too - Postgres scans it backwards.
    op.create_index("ix_game_scores_hidden_gem_score", "game_scores", ["hidden_gem_score"])
    op.create_index("ix_games_cohort_genre", "games", ["cohort_genre"])
    # GIN is the index type that answers JSONB containment (`tags @> ...`),
    # which is how the tag filter is expressed.
    op.create_index(
        "ix_games_tags",
        "games",
        ["tags"],
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_games_tags", table_name="games")
    op.drop_index("ix_games_cohort_genre", table_name="games")
    op.drop_index("ix_game_scores_hidden_gem_score", table_name="game_scores")
