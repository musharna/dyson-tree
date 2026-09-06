import numpy as np
import pytest

from sim.physiology import (
    PAR_FRACTION,
    PHOTONS_PER_J,
    TSI_W_M2,
    gross_assimilation,
    irradiance,
    respiration,
)


def test_irradiance_at_1_au_matches_stated_assumptions():
    # 1360.8 * 0.3879 * 4.57 = 2412.3 (top-of-atmosphere PAR photon flux).
    # PAR_FRACTION was 0.45 until 2026-09-06; S5 corrected it to the MEASURED
    # AM0 400-700 nm fraction. See docs/bio_grounding_2026-09-02.md sections 12 and 20.
    assert irradiance(1.0) == pytest.approx(TSI_W_M2 * PAR_FRACTION * PHOTONS_PER_J)
    assert irradiance(1.0) == pytest.approx(2412.3, rel=1e-3)


def test_irradiance_inverse_square():
    assert irradiance(10.0) == pytest.approx(irradiance(1.0) / 100.0)


def test_irradiance_accepts_arrays():
    r = np.array([1.0, 2.0, 4.0])
    out = irradiance(r)
    assert out.shape == (3,)
    assert out[1] == pytest.approx(out[0] / 4.0)


def test_irradiance_rejects_nonpositive_distance():
    with pytest.raises(ValueError, match="r_au"):
        irradiance(0.0)
    with pytest.raises(ValueError, match="r_au"):
        irradiance(np.array([1.0, -1.0]))


def test_gross_assimilation_is_rectangular_hyperbola():
    # at I = k, assimilation is half of a_max
    assert gross_assimilation(100.0, a_max=10.0, k=100.0) == pytest.approx(5.0)
    assert gross_assimilation(0.0, a_max=10.0, k=100.0) == 0.0
    # saturates toward a_max
    assert gross_assimilation(1e9, a_max=10.0, k=100.0) == pytest.approx(10.0, rel=1e-6)


def test_gross_assimilation_rejects_bad_params():
    with pytest.raises(ValueError, match="a_max"):
        gross_assimilation(10.0, a_max=0.0, k=100.0)
    with pytest.raises(ValueError, match="k"):
        gross_assimilation(10.0, a_max=10.0, k=-1.0)
    with pytest.raises(ValueError, match="irradiance"):
        gross_assimilation(-5.0, a_max=10.0, k=100.0)


def test_respiration_q10():
    assert respiration(1.0, t=293.0) == pytest.approx(1.0)
    assert respiration(1.0, t=303.0) == pytest.approx(2.0)
    assert respiration(1.0, t=283.0) == pytest.approx(0.5)
    assert respiration(0.0, t=293.0) == 0.0


def test_respiration_rejects_bad_params():
    with pytest.raises(ValueError, match="r_d"):
        respiration(-0.1, t=293.0)
    with pytest.raises(ValueError, match="t must"):
        respiration(1.0, t=0.0)
