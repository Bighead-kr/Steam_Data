from __future__ import annotations

import datetime as dt

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class GameRaw(Base):
    __tablename__ = "games_raw"

    app_id: Mapped[int] = mapped_column(primary_key=True)
    raw_json: Mapped[dict] = mapped_column(JSONB)
    fetched_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class Game(Base):
    __tablename__ = "games"

    app_id: Mapped[int] = mapped_column(ForeignKey("games_raw.app_id"), primary_key=True)
    name: Mapped[str]
    genres: Mapped[list[str]] = mapped_column(JSONB)
    tags: Mapped[list[str]] = mapped_column(JSONB)
    release_date: Mapped[dt.date | None]
    price_cents: Mapped[int | None]
    is_dlc: Mapped[bool]
    review_score_pct: Mapped[float | None]
    review_count: Mapped[int | None]
    owners_low: Mapped[int | None]
    owners_high: Mapped[int | None]
    avg_playtime_min: Mapped[int | None]
    cohort_genre: Mapped[str]
    cohort_year: Mapped[int]


class GameScore(Base):
    __tablename__ = "game_scores"

    app_id: Mapped[int] = mapped_column(ForeignKey("games.app_id"), primary_key=True)
    quality_score: Mapped[float]
    quality_pctile: Mapped[float]
    exposure_pctile: Mapped[float]
    hidden_gem_score: Mapped[float]
    computed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )


class PipelineRun(Base):
    __tablename__ = "pipeline_runs"

    run_id: Mapped[str] = mapped_column(primary_key=True)
    started_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str]
    games_collected: Mapped[int]
    games_new: Mapped[int]
    notes: Mapped[str | None]
