import math

import pytest

from sim.thermal import (
    SIGMA_W_M2_K4,
    adapted_optimum,
    equilibrium_temperature,
    temperature_response,
    temperature_response_gaussian,
)


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


def test_response_is_zero_at_and_below_t_min():
    assert temperature_response(265.15, t_min=265.15, t_opt=298.15) == 0.0
    assert temperature_response(200.0, t_min=265.15, t_opt=298.15) == 0.0


def test_response_is_one_at_and_above_t_opt():
    assert temperature_response(298.15, t_min=265.15, t_opt=298.15) == 1.0
    assert temperature_response(310.0, t_min=265.15, t_opt=298.15) == 1.0


def test_response_is_linear_between_the_two_endpoints():
    # midpoint of [265.15, 298.15] is 281.65
    assert temperature_response(281.65, t_min=265.15, t_opt=298.15) == pytest.approx(
        0.5
    )


def test_response_is_monotonic_in_temperature():
    prev = -1.0
    for t in range(260, 305):
        v = temperature_response(float(t), t_min=265.15, t_opt=298.15)
        assert v >= prev
        prev = v


def test_response_rejects_t_opt_not_above_t_min():
    with pytest.raises(ValueError, match="t_opt"):
        temperature_response(280.0, t_min=298.15, t_opt=265.15)
    # positive control
    assert temperature_response(280.0, t_min=265.15, t_opt=298.15) > 0


def test_gaussian_is_one_at_the_optimum():
    assert temperature_response_gaussian(298.15, t_opt=298.15, omega=20.0) == 1.0


def test_gaussian_falls_to_one_over_e_at_omega_from_the_optimum():
    """Omega is DEFINED as the offset at which the rate falls to e^-1 of its
    peak (June et al. 2004, as quoted in Scafaro et al. 2023). That definition
    is the test."""
    v = temperature_response_gaussian(298.15 + 20.0, t_opt=298.15, omega=20.0)
    assert v == pytest.approx(math.exp(-1.0), rel=1e-12)


def test_gaussian_is_symmetric_about_the_optimum():
    hot = temperature_response_gaussian(298.15 + 12.0, t_opt=298.15, omega=20.0)
    cold = temperature_response_gaussian(298.15 - 12.0, t_opt=298.15, omega=20.0)
    assert hot == pytest.approx(cold, rel=1e-12)
    # and both are strictly below the peak
    assert hot < 1.0


def test_gaussian_narrower_omega_falls_off_faster():
    narrow = temperature_response_gaussian(283.15, t_opt=298.15, omega=10.0)
    wide = temperature_response_gaussian(283.15, t_opt=298.15, omega=30.0)
    assert narrow < wide


def test_gaussian_stays_in_the_unit_interval_far_from_the_optimum():
    for t in (1.0, 100.0, 200.0, 400.0, 600.0):
        v = temperature_response_gaussian(t, t_opt=298.15, omega=20.0)
        assert 0.0 <= v <= 1.0


@pytest.mark.parametrize(
    "kwargs, needle",
    [
        (dict(t=298.15, t_opt=298.15, omega=0.0), "omega"),
        (dict(t=298.15, t_opt=298.15, omega=-5.0), "omega"),
        (dict(t=0.0, t_opt=298.15, omega=20.0), "t"),
        (dict(t=-10.0, t_opt=298.15, omega=20.0), "t"),
    ],
)
def test_gaussian_rejects_out_of_range_inputs(kwargs, needle):
    with pytest.raises(ValueError, match=needle):
        temperature_response_gaussian(**kwargs)
    # positive control in the same test
    assert temperature_response_gaussian(298.15, t_opt=298.15, omega=20.0) == 1.0


def test_adapted_optimum_is_the_equilibrium_temperature_at_the_home_distance():
    """The adaptation premise: the optimum IS the tissue temperature at home.
    Named rather than inlined so the premise is greppable and testable."""
    from sim.thermal import equilibrium_temperature

    for ratio in (2.0, 4.0):
        assert adapted_optimum(1.0, area_ratio=ratio) == pytest.approx(
            equilibrium_temperature(1.0, area_ratio=ratio), rel=1e-12
        )


def test_adapted_optimum_reproduces_the_two_class_predictions():
    """The numbers Gate B is built on. Sphere ~5.16 C, lamina ~57.82 C."""
    assert adapted_optimum(1.0, area_ratio=4.0) - 273.15 == pytest.approx(
        5.16, abs=0.01
    )
    assert adapted_optimum(1.0, area_ratio=2.0) - 273.15 == pytest.approx(
        57.82, abs=0.01
    )


def test_adapted_optimum_rejects_a_nonpositive_home_distance():
    with pytest.raises(ValueError, match="r_au"):
        adapted_optimum(0.0, area_ratio=4.0)
    assert adapted_optimum(1.0, area_ratio=4.0) > 0
