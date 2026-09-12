import pytest

from tracker.scorer import bayesian_quality_score, percentile_rank, score_games


def test_bayesian_quality_score_pulls_low_review_count_toward_cohort_mean():
    # 3 reviews at 100% should land far below 100 once pulled toward a 70% mean.
    score = bayesian_quality_score(
        review_count=3, review_score_pct=100.0, cohort_mean_pct=70.0, prior_strength=50.0
    )
    assert 70.0 < score < 75.0


def test_bayesian_quality_score_barely_moves_high_review_count():
    score = bayesian_quality_score(
        review_count=5000, review_score_pct=95.0, cohort_mean_pct=70.0, prior_strength=50.0
    )
    assert 94.0 < score < 95.0


def test_percentile_rank_basic():
    values = [10.0, 20.0, 30.0, 40.0]
    assert percentile_rank(values, 40.0) == 1.0
    assert percentile_rank(values, 10.0) == 0.25
    assert percentile_rank(values, 25.0) == 0.5


def _game(
    app_id, review_count, review_score_pct, owners_mid, genre="indie", year=2021, is_dlc=False
):
    owners_low = owners_mid - 5000
    owners_high = owners_mid + 5000
    return {
        "app_id": app_id,
        "review_count": review_count,
        "review_score_pct": review_score_pct,
        "owners_low": owners_low,
        "owners_high": owners_high,
        "cohort_genre": genre,
        "cohort_year": year,
        "is_dlc": is_dlc,
    }


def test_score_games_ranks_high_quality_low_exposure_above_popular_mediocre_game():
    games = [
        _game(1, review_count=2000, review_score_pct=97.0, owners_mid=15000),  # hidden gem
        _game(2, review_count=2000, review_score_pct=75.0, owners_mid=500000),  # popular, mediocre
        _game(3, review_count=2000, review_score_pct=85.0, owners_mid=100000),  # middle of pack
    ]
    results = {r["app_id"]: r for r in score_games(games, prior_strength=50.0, min_cohort_size=2)}

    assert results[1]["hidden_gem_score"] > results[3]["hidden_gem_score"]
    assert results[3]["hidden_gem_score"] > results[2]["hidden_gem_score"]


def test_score_games_falls_back_to_genre_only_cohort_when_year_cohort_too_small():
    games = [
        _game(1, review_count=1000, review_score_pct=90.0, owners_mid=10000, year=2020),
        _game(2, review_count=1000, review_score_pct=80.0, owners_mid=10000, year=2021),
        _game(3, review_count=1000, review_score_pct=70.0, owners_mid=10000, year=2022),
    ]
    # min_cohort_size=3: no single year has 3 games, so all fall back to the
    # genre-only cohort of 3 and scoring should not raise.
    results = score_games(games, prior_strength=50.0, min_cohort_size=3)
    assert len(results) == 3


def test_score_games_skips_games_without_review_or_owner_data():
    games = [
        _game(1, review_count=1000, review_score_pct=90.0, owners_mid=10000),
        {
            "app_id": 2,
            "review_count": None,
            "review_score_pct": None,
            "owners_low": None,
            "owners_high": None,
            "cohort_genre": "indie",
            "cohort_year": 2021,
        },
    ]
    results = score_games(games, prior_strength=50.0, min_cohort_size=1)
    assert [r["app_id"] for r in results] == [1]


def test_score_games_skips_games_whose_genre_cohort_is_still_too_small():
    """Percentiles against a cohort of one are noise with a number on it:
    percentile_rank is inclusive-of-self, so the lone game scores quality
    1.0 and exposure 1.0 and the webapp proudly renders "top 1%". Production
    served exactly this for the single game in the "simulation" cohort."""
    games = [
        _game(1, review_count=1000, review_score_pct=90.0, owners_mid=10000, genre="indie"),
        _game(2, review_count=1000, review_score_pct=80.0, owners_mid=20000, genre="indie"),
        _game(3, review_count=145, review_score_pct=73.8, owners_mid=150000, genre="simulation"),
    ]
    results = score_games(games, prior_strength=50.0, min_cohort_size=2)

    assert [r["app_id"] for r in results] == [1, 2]


def test_score_games_excludes_dlc_from_scores_and_from_cohort_statistics():
    """DLC reviews/owners ride on the base game, so a soundtrack in the
    cohort drags every percentile in it."""
    games = [
        _game(1, review_count=1000, review_score_pct=90.0, owners_mid=10000),
        _game(2, review_count=1000, review_score_pct=80.0, owners_mid=20000),
        _game(3, review_count=10, review_score_pct=100.0, owners_mid=30000, is_dlc=True),
    ]
    results = score_games(games, prior_strength=50.0, min_cohort_size=2)
    without_dlc = score_games(games[:2], prior_strength=50.0, min_cohort_size=2)

    assert [r["app_id"] for r in results] == [1, 2]
    assert results == without_dlc


def test_score_games_includes_games_with_zero_review_count():
    # Zero reviews is valid data (not missing); Bayesian formula collapses to cohort mean.
    # This game should be scored, not skipped.
    games = [
        _game(1, review_count=1000, review_score_pct=90.0, owners_mid=10000),
        _game(2, review_count=0, review_score_pct=75.0, owners_mid=10000),  # zero reviews, present data
    ]
    results = score_games(games, prior_strength=50.0, min_cohort_size=1)
    app_ids = [r["app_id"] for r in results]
    assert 2 in app_ids
    # With 0 reviews, Bayesian score should equal cohort mean (~82.5).
    game2_result = next(r for r in results if r["app_id"] == 2)
    assert game2_result["quality_score"] == pytest.approx(82.5, abs=0.1)
