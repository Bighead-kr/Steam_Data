from collections.abc import Generator

from fastapi import Depends, FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from tracker.api.schemas import FacetValue, GemResponse
from tracker.config import get_settings
from tracker.db import get_sessionmaker
from tracker.models import Game, GameScore

app = FastAPI(title="Steam Hidden Gems API")

# Public, read-only, unauthenticated API - the Next.js webapp (a different
# origin/port in dev, a different domain once deployed) needs to call it
# directly from the browser. No cookies/credentials are involved, so a
# permissive origin policy carries no meaningful risk here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


def get_session() -> Generator[Session, None, None]:
    session_factory = get_sessionmaker(get_settings().database_url)
    with session_factory() as session:
        yield session


@app.get("/games/gems", response_model=list[GemResponse])
def list_gems(
    genre: str | None = None,
    tag: str | None = None,
    max_price_cents: int | None = None,
    limit: int = Query(20, ge=1, le=200),
    session: Session = Depends(get_session),  # noqa: B008
) -> list[GemResponse]:
    query = (
        select(Game, GameScore)
        .join(GameScore, GameScore.app_id == Game.app_id)
        .where(Game.is_dlc.is_(False))
        # hidden_gem_score ties are common (percentiles over a discrete
        # owners bucket repeat a lot), and Postgres is free to return tied
        # rows in any order - app_id makes paging and screenshots stable.
        .order_by(GameScore.hidden_gem_score.desc(), Game.app_id)
        .limit(limit)
    )
    if genre:
        query = query.where(Game.cohort_genre == genre.lower())
    if max_price_cents is not None:
        # NULL price (a paid game Steam served without price_overview)
        # fails this comparison and drops out, which is the honest answer
        # for a budget filter: we can't claim an unknown price fits.
        query = query.where(Game.price_cents <= max_price_cents)
    if tag:
        # JSONB containment (`tags @> '["Roguelike"]'`), so the filter and
        # the limit are one indexed query instead of "fetch every row, then
        # filter in Python" - that older shape pulled all 9,715 rows out of
        # the database to answer a limit=20 request.
        query = query.where(Game.tags.contains([tag]))

    return [
        GemResponse(
            app_id=game.app_id,
            name=game.name,
            price_cents=game.price_cents,
            genres=game.genres,
            tags=game.tags,
            review_score_pct=game.review_score_pct,
            review_count=game.review_count,
            owners_low=game.owners_low,
            owners_high=game.owners_high,
            quality_pctile=score.quality_pctile,
            exposure_pctile=score.exposure_pctile,
            hidden_gem_score=score.hidden_gem_score,
        )
        for game, score in session.execute(query).all()
    ]


@app.get("/genres", response_model=list[FacetValue])
def list_genres(session: Session = Depends(get_session)) -> list[FacetValue]:  # noqa: B008
    """Cohort genres that actually have scored games behind them.

    The webapp used to hardcode its genre dropdown, which silently went
    stale: two of its options matched a handful of rows or none at all.
    """
    query = (
        select(Game.cohort_genre, func.count().label("n"))
        .join(GameScore, GameScore.app_id == Game.app_id)
        .where(Game.is_dlc.is_(False))
        .group_by(Game.cohort_genre)
        .order_by(desc("n"))
    )
    return [FacetValue(value=value, count=count) for value, count in session.execute(query).all()]


@app.get("/tags", response_model=list[FacetValue])
def list_tags(
    genre: str | None = None,
    limit: int = Query(30, ge=1, le=100),
    session: Session = Depends(get_session),  # noqa: B008
) -> list[FacetValue]:
    """The most common tags among scored games, optionally within a genre.

    Tags are free-form strings from SteamSpy with exact casing ("Roguelike",
    "Co-op"), so a text input can only be guessed at. Serving the real list
    turns the tag filter into a choice instead of a spelling test.
    """
    scored_games = (
        select(Game.tags)
        .join(GameScore, GameScore.app_id == Game.app_id)
        .where(Game.is_dlc.is_(False))
    )
    if genre:
        scored_games = scored_games.where(Game.cohort_genre == genre.lower())

    expanded = select(
        func.jsonb_array_elements_text(scored_games.subquery().c.tags).label("tag")
    ).subquery()
    query = (
        select(expanded.c.tag, func.count().label("n"))
        .group_by(expanded.c.tag)
        .order_by(desc("n"), expanded.c.tag)
        .limit(limit)
    )
    return [FacetValue(value=value, count=count) for value, count in session.execute(query).all()]
