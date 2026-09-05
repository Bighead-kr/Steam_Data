from collections.abc import Generator

from fastapi import Depends, FastAPI
from sqlalchemy import select
from sqlalchemy.orm import Session

from tracker.api.schemas import GemResponse
from tracker.config import get_settings
from tracker.db import get_sessionmaker
from tracker.models import Game, GameScore

app = FastAPI(title="Steam Hidden Gems API")


def get_session() -> Generator[Session, None, None]:
    session_factory = get_sessionmaker(get_settings().database_url)
    with session_factory() as session:
        yield session


@app.get("/games/gems", response_model=list[GemResponse])
def list_gems(
    genre: str | None = None,
    tag: str | None = None,
    max_price_cents: int | None = None,
    limit: int = 20,
    session: Session = Depends(get_session),  # noqa: B008
) -> list[GemResponse]:
    query = (
        select(Game, GameScore)
        .join(GameScore, GameScore.app_id == Game.app_id)
        .order_by(GameScore.hidden_gem_score.desc())
    )
    if genre:
        query = query.where(Game.cohort_genre == genre.lower())
    if max_price_cents is not None:
        query = query.where(Game.price_cents <= max_price_cents)

    rows = session.execute(query).all()
    results = [
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
        for game, score in rows
    ]

    if tag:
        results = [r for r in results if tag in r.tags]

    return results[:limit]
