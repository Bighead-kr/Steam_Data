from pydantic import BaseModel


class FacetValue(BaseModel):
    """One selectable filter value plus how many scored games carry it."""

    value: str
    count: int


class GemResponse(BaseModel):
    app_id: int
    name: str
    price_cents: int | None
    genres: list[str]
    tags: list[str]
    review_score_pct: float | None
    review_count: int | None
    owners_low: int | None
    owners_high: int | None
    quality_pctile: float
    exposure_pctile: float
    hidden_gem_score: float
