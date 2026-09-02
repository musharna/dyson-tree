import pytest

from sim.organism import ALGAL, PRESETS, VASCULAR, Organism, compensation_irradiance


# --- calibration gates (the scientific tests) -------------------------------


def test_vascular_compensation_inside_craine_reich_gate():
    # Craine & Reich 2005, doi:10.1111/j.1469-8137.2005.01420.x: LSMs 5.3, 8.1, 9.0
    ic = compensation_irradiance(VASCULAR)
    assert 5.3 <= ic <= 9.0, ic


def test_algal_compensation_below_richardson_floor():
    # Richardson 1983, doi:10.1111/j.1469-8137.1983.tb03422.x: growth < 1 µE
    ic = compensation_irradiance(ALGAL)
    assert 0.0 < ic < 1.0, ic


# --- analytic identity -------------------------------------------------------


def test_compensation_is_where_gross_equals_leaf_respiration():
    org = Organism("x", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
    ic = compensation_irradiance(org)
    from sim.physiology import gross_assimilation

    assert gross_assimilation(ic, org.a_max, org.k) == pytest.approx(
        org.leaf_respiration()
    )
    # closed form K*R/(A_max-R)
    assert ic == pytest.approx(100.0 * 0.65 / (10.0 - 0.65))


# --- controls: healthy path and broken path asserted together ---------------


def test_zero_respiration_gives_zero_compensation_while_baseline_is_positive():
    base = compensation_irradiance(VASCULAR)
    assert base > 0
    dead = Organism(
        "v0",
        a_max=VASCULAR.a_max,
        k=VASCULAR.k,
        r_d=0.0,
        leaf_mass_ratio=VASCULAR.leaf_mass_ratio,
    )
    assert compensation_irradiance(dead) == 0.0


def test_doubling_respiration_raises_compensation():
    base = compensation_irradiance(VASCULAR)
    hot = Organism(
        "v2",
        a_max=VASCULAR.a_max,
        k=VASCULAR.k,
        r_d=2 * VASCULAR.r_d,
        leaf_mass_ratio=VASCULAR.leaf_mass_ratio,
    )
    assert compensation_irradiance(hot) > base


def test_respiration_at_or_above_a_max_raises():
    org = Organism("x", a_max=1.0, k=10.0, r_d=1.0, leaf_mass_ratio=1.0)
    with pytest.raises(ValueError, match="a_max"):
        compensation_irradiance(org)


# --- whole-organism net carbon ----------------------------------------------


def test_net_carbon_positive_at_1_au_for_both_presets():
    assert VASCULAR.net_carbon(1.0) > 0
    assert ALGAL.net_carbon(1.0) > 0


def test_net_carbon_uses_leaf_mass_ratio():
    whole = Organism("w", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=1.0)
    half = Organism("h", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
    assert half.organism_respiration() == pytest.approx(
        2 * whole.organism_respiration()
    )
    assert half.net_carbon(1.0) < whole.net_carbon(1.0)


def test_net_carbon_k_override():
    assert VASCULAR.net_carbon(1.0, k=VASCULAR.k) == pytest.approx(
        VASCULAR.net_carbon(1.0)
    )
    # larger k => less assimilation at the same light
    assert VASCULAR.net_carbon(1.0, k=2 * VASCULAR.k) < VASCULAR.net_carbon(1.0)


def test_organism_validates_ranges():
    with pytest.raises(ValueError, match="leaf_mass_ratio"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.0)
    with pytest.raises(ValueError, match="leaf_mass_ratio"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=1.5)
    with pytest.raises(ValueError, match="a_max"):
        Organism("x", a_max=-1.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.5)
    with pytest.raises(ValueError, match="t_set"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.5, t_set=-5.0)


def test_presets_registry():
    assert set(PRESETS) == {"vascular", "algal"}
    assert PRESETS["vascular"] is VASCULAR


from sim.organism import ALGAL, VASCULAR, Organism
from sim.thermal import equilibrium_temperature


def test_q1_presets_still_construct_with_unchanged_carbon_values():
    # The new fields are defaulted, so the Q1 presets are untouched.
    assert VASCULAR.net_carbon(1.0) == pytest.approx(8.3550, abs=1e-4)
    assert ALGAL.net_carbon(1.0) == pytest.approx(9.6290, abs=1e-4)


def test_new_fields_have_defaults():
    o = Organism("x", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)
    assert o.area_ratio == 2.0
    assert o.t_min == 265.15
    assert o.t_opt == 298.15
    assert o.emissivity == 1.0
    assert o.albedo == 0.0


def test_equilibrium_net_carbon_uses_the_equilibrium_temperature():
    # At 1 AU a sphere sits at ~278.3 K, which is above t_min for the algal floor
    # but below t_opt, so the response multiplier is strictly between 0 and 1.
    o = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65,
    )
    t = equilibrium_temperature(1.0, area_ratio=4.0)
    assert 254.65 < t < 298.15
    # Temperature-scaled assimilation must be strictly below the unscaled Q1 value.
    assert o.net_carbon_at_equilibrium(1.0) < o.net_carbon(1.0)


def test_equilibrium_net_carbon_is_negative_below_t_min():
    # Far enough out that T < t_min: assimilation is switched off entirely and
    # only respiration remains, so net carbon must be strictly negative.
    o = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65,
    )
    far = 100.0
    assert equilibrium_temperature(far, area_ratio=4.0) < 254.65
    assert o.net_carbon_at_equilibrium(far) < 0
    # positive control: near in, it is positive
    assert o.net_carbon_at_equilibrium(1.0) > 0


@pytest.mark.parametrize(
    "field, value",
    [("area_ratio", 0.0), ("emissivity", 1.5), ("albedo", 1.0), ("t_min", -1.0)],
)
def test_new_fields_validate(field, value):
    kwargs = dict(a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)
    kwargs[field] = value
    with pytest.raises(ValueError, match=field):
        Organism("x", **kwargs)
    # positive control
    assert Organism("x", **dict(a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)).a_max == 10.0
