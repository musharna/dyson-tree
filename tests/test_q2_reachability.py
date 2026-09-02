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
