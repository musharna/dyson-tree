import pytest

from experiments.q2_thermal.reachability import thermal_cutoff_au
from sim.thermal import equilibrium_temperature


def test_cutoff_is_where_equilibrium_temperature_equals_t_min():
    r = thermal_cutoff_au(t_min=254.65, area_ratio=4.0)
    assert equilibrium_temperature(r, area_ratio=4.0) == pytest.approx(254.65, rel=1e-9)


def test_colder_floor_pushes_the_cutoff_further_out():
    warm = thermal_cutoff_au(t_min=268.15, area_ratio=2.0)
    cold = thermal_cutoff_au(t_min=254.65, area_ratio=2.0)
    assert cold > warm


def test_cutoff_rejects_a_nonpositive_floor():
    with pytest.raises(ValueError, match="t_min"):
        thermal_cutoff_au(t_min=0.0, area_ratio=4.0)
    # positive control
    assert thermal_cutoff_au(t_min=254.65, area_ratio=4.0) > 0


def test_cutoff_actually_uses_area_ratio():
    """None of the tests above vary area_ratio while holding t_min fixed, so a
    hardcoded area_ratio=4.0 inside thermal_cutoff_au would pass all three:
    the first test happens to pass area_ratio=4.0 anyway, and the other two
    never compare across area_ratio at all. This is the only artifact whose
    output is quoted as evidence inside the frozen prereg.yaml
    (reachable_thermal_cutoff_au) and re-quoted in RESULTS.md, so a
    proven-blind suite here is a real gap."""
    lamina = thermal_cutoff_au(t_min=265.15, area_ratio=2.0)
    sphere = thermal_cutoff_au(t_min=265.15, area_ratio=4.0)
    assert lamina != sphere
