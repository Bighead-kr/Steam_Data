import pytest

from tracker.collector import CollectorNotImplementedError, collect_games


def test_collect_games_raises_not_implemented_in_phase_a():
    with pytest.raises(CollectorNotImplementedError, match="Phase B"):
        collect_games(genres=["indie", "roguelike"])
