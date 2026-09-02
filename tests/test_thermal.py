import pytest

from sim.thermal import SIGMA_W_M2_K4, equilibrium_temperature


def test_sphere_at_1_au_matches_blackbody_value():
    # area_ratio 4 = sphere: absorbs over pi r^2, radiates over 4 pi r^2.
    t = equilibrium_temperature(1.0, area_ratio=4.0)
    assert t == pytest.approx(278.31, abs=0.05)


def test_lamina_at_1_au_is_hotter_than_sphere():
    # A flat lamina radiates from 2 faces, not 4, so it runs hotter.
    lamina = equilibrium_temperature(1.0, area_ratio=2.0)
    sphere = equilibrium_temperature(1.0, area_ratio=4.0)
    assert lamina > sphere
    assert lamina == pytest.approx(330.97, abs=0.05)


def test_inverse_square_root_scaling():
    # S ~ 1/r^2 and T ~ S^(1/4), so T ~ r^-1/2: quadrupling r halves T.
    t1 = equilibrium_temperature(1.0, area_ratio=4.0)
    t4 = equilibrium_temperature(4.0, area_ratio=4.0)
    assert t4 == pytest.approx(t1 / 2.0, rel=1e-12)


def test_albedo_and_emissivity_lower_and_raise_temperature():
    base = equilibrium_temperature(1.0, area_ratio=4.0)
    # Reflecting 30% of the light must cool it.
    assert equilibrium_temperature(1.0, area_ratio=4.0, albedo=0.3) < base
    # A poorer emitter must run hotter for the same absorbed power.
    assert equilibrium_temperature(1.0, area_ratio=4.0, emissivity=0.5) > base


def test_sigma_is_the_codata_value():
    assert SIGMA_W_M2_K4 == 5.670374419e-8


@pytest.mark.parametrize(
    "kwargs, needle",
    [
        (dict(r_au=0.0, area_ratio=4.0), "r_au"),
        (dict(r_au=-1.0, area_ratio=4.0), "r_au"),
        (dict(r_au=1.0, area_ratio=0.0), "area_ratio"),
        (dict(r_au=1.0, area_ratio=4.0, emissivity=0.0), "emissivity"),
        (dict(r_au=1.0, area_ratio=4.0, emissivity=1.5), "emissivity"),
        (dict(r_au=1.0, area_ratio=4.0, albedo=-0.1), "albedo"),
        (dict(r_au=1.0, area_ratio=4.0, albedo=1.0), "albedo"),
    ],
)
def test_out_of_range_inputs_raise_naming_the_value(kwargs, needle):
    with pytest.raises(ValueError, match=needle):
        equilibrium_temperature(**kwargs)
    # positive control: the legitimate call in the same test still works
    assert equilibrium_temperature(1.0, area_ratio=4.0) > 0
