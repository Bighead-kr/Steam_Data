from __future__ import annotations

from collections import defaultdict
from statistics import mean


def bayesian_quality_score(
    review_count: int, review_score_pct: float, cohort_mean_pct: float, prior_strength: float
) -> float:
    """Shrink a game's review score toward its cohort's mean, weighted by
    how many reviews back it up (fewer reviews -> more shrinkage)."""
    return (review_count * review_score_pct + prior_strength * cohort_mean_pct) / (
        review_count + prior_strength
    )


def percentile_rank(values: list[float], target: float) -> float:
    """Fraction of `values` at or below `target`, as 0..1. Empty -> 0.0."""
    if not values:
        return 0.0
    at_or_below = sum(1 for v in values if v <= target)
    return at_or_below / len(values)


def _is_scoreable(game: dict) -> bool:
    return (
        game.get("review_count") is not None
        and game.get("review_score_pct") is not None
        and game.get("owners_low") is not None
        and game.get("owners_high") is not None
    )


def score_games(
    games: list[dict], prior_strength: float, min_cohort_size: int
) -> list[dict]:
    """Score games on quality-vs-exposure within a (genre, year) cohort,
    falling back to a genre-only cohort when the (genre, year) cohort is
    smaller than `min_cohort_size`.

    Games missing review or owner data are skipped (insufficient data).
    """
    scoreable = [g for g in games if _is_scoreable(g)]

    fine_groups: dict[tuple[str, int], list[dict]] = defaultdict(list)
    coarse_groups: dict[str, list[dict]] = defaultdict(list)
    for g in scoreable:
        fine_groups[(g["cohort_genre"], g["cohort_year"])].append(g)
        coarse_groups[g["cohort_genre"]].append(g)

    results = []
    for g in scoreable:
        fine_key = (g["cohort_genre"], g["cohort_year"])
        cohort = (
            fine_groups[fine_key]
            if len(fine_groups[fine_key]) >= min_cohort_size
            else coarse_groups[g["cohort_genre"]]
        )

        cohort_mean_pct = mean(c["review_score_pct"] for c in cohort)
        quality_score = bayesian_quality_score(
            g["review_count"], g["review_score_pct"], cohort_mean_pct, prior_strength
        )
        cohort_quality_scores = [
            bayesian_quality_score(
                c["review_count"], c["review_score_pct"], cohort_mean_pct, prior_strength
            )
            for c in cohort
        ]
        cohort_owners_mid = [(c["owners_low"] + c["owners_high"]) / 2 for c in cohort]
        owners_mid = (g["owners_low"] + g["owners_high"]) / 2

        quality_pctile = percentile_rank(cohort_quality_scores, quality_score)
        exposure_pctile = percentile_rank(cohort_owners_mid, owners_mid)

        results.append(
            {
                "app_id": g["app_id"],
                "quality_score": quality_score,
                "quality_pctile": quality_pctile,
                "exposure_pctile": exposure_pctile,
                "hidden_gem_score": quality_pctile - exposure_pctile,
            }
        )
    return results
