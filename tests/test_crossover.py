import pytest

from sim.organism import ALGAL, VASCULAR, Organism, crossover_distance_for
from sim.physiology import crossover_distance


def _with_rd(org, r_d):
    return Organism(
        org.cls,
        a_max=org.a_max,
        k=org.k,
        r_d=r_d,
        leaf_mass_ratio=org.leaf_mass_ratio,
        t_set=org.t_set,
    )


def test_crossover_exists_and_net_is_zero_there():
    for org in (VASCULAR, ALGAL):
        r_star = crossover_distance_for(org)
        assert 0.5 < r_star < 100.0
        assert org.net_carbon(r_star) == pytest.approx(0.0, abs=1e-6)
        # sign check either side
        assert org.net_carbon(r_star * 0.9) > 0
        assert org.net_carbon(r_star * 1.1) < 0


def test_zero_respiration_has_no_crossover_while_baseline_does():
    assert crossover_distance_for(VASCULAR) > 0  # positive control
    with pytest.raises(ValueError, match="no sign change"):
        crossover_distance_for(_with_rd(VASCULAR, 0.0))  # negative


def test_doubling_respiration_moves_crossover_inward():
    base = crossover_distance_for(VASCULAR)
    hot = crossover_distance_for(_with_rd(VASCULAR, 2 * VASCULAR.r_d))
    assert hot < base


def test_larger_k_moves_crossover_inward():
    base = crossover_distance_for(VASCULAR)
    assert crossover_distance_for(VASCULAR, k=2 * VASCULAR.k) < base
    assert crossover_distance_for(VASCULAR, k=0.5 * VASCULAR.k) > base


def test_n_grid_is_load_bearing_for_the_bracket():
    """Positive + negative control that n_grid actually selects the bracket:
    a narrow negative window a coarse grid steps straight over."""

    def net(r):
        return -1.0 if 40.0 < r < 41.0 else 1.0

    with pytest.raises(ValueError, match="no sign change"):
        crossover_distance(net, r_min=0.5, r_max=100.0, n_grid=10)
    assert 39.0 < crossover_distance(net, r_min=0.5, r_max=100.0, n_grid=4000) < 42.0


def test_crossover_distance_for_forwards_n_grid(monkeypatch):
    """The pre-registration declares one n_grid; it must reach the root search,
    not just the sweep CSV's resolution."""
    import sim.organism as om

    real = om.crossover_distance
    seen = {}

    def spy(fn, r_min, r_max, n_grid):
        seen["n_grid"] = n_grid
        return real(fn, r_min=r_min, r_max=r_max, n_grid=n_grid)

    monkeypatch.setattr(om, "crossover_distance", spy)
    crossover_distance_for(VASCULAR, n_grid=37)
    assert seen["n_grid"] == 37


def test_generic_root_finder_on_known_function():
    # net = 4 - r  => root at 4
    assert crossover_distance(
        lambda r: 4.0 - r, r_min=0.5, r_max=100.0
    ) == pytest.approx(4.0, abs=1e-5)
    with pytest.raises(ValueError, match="no sign change"):
        crossover_distance(lambda r: 1.0, r_min=0.5, r_max=100.0)
    with pytest.raises(ValueError, match="r_min"):
        crossover_distance(lambda r: 4.0 - r, r_min=10.0, r_max=1.0)
