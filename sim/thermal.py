"""Radiative equilibrium temperature and the temperature response of photosynthesis.

Units: temperature in K; distance in AU; irradiance in W m⁻². All functions are
stateless. Out-of-range inputs raise ValueError naming the value.

Kept separate from sim/physiology.py, which is about light and carbon. This module
is the thermal domain introduced by Q2.
"""

from __future__ import annotations

from sim.physiology import TSI_W_M2

# CODATA / exact by the SI definition of the kelvin.
SIGMA_W_M2_K4 = 5.670374419e-8


def equilibrium_temperature(
    r_au: float,
    area_ratio: float,
    emissivity: float = 1.0,
    albedo: float = 0.0,
) -> float:
    """Radiative equilibrium temperature of a passive body at r_au.

    area_ratio is radiating area divided by absorbing (projected) area: 2 for a
    flat lamina that absorbs on one face and radiates from both, 4 for a sphere
    that absorbs over its cross-section and radiates over its whole surface.

    Absorbed = S(1-albedo) per unit projected area; emitted = area_ratio *
    emissivity * sigma * T^4 per unit projected area. Setting them equal:
    """
    if r_au <= 0:
        raise ValueError(f"r_au must be > 0, got {r_au}")
    if area_ratio <= 0:
        raise ValueError(f"area_ratio must be > 0, got {area_ratio}")
    if not (0 < emissivity <= 1):
        raise ValueError(f"emissivity must be in (0, 1], got {emissivity}")
    if not (0 <= albedo < 1):
        raise ValueError(f"albedo must be in [0, 1), got {albedo}")
    s = TSI_W_M2 / r_au**2
    return float((s * (1 - albedo) / (area_ratio * emissivity * SIGMA_W_M2_K4)) ** 0.25)


def temperature_response(t: float, t_min: float, t_opt: float) -> float:
    """Normalized rate multiplier in [0, 1] for photosynthesis at temperature t.

    Linear from 0 at t_min to 1 at t_opt, flat above t_opt. Parameterized ONLY by
    t_min and t_opt: the literature rate anchors at 5 °C and 0 °C are deliberately
    NOT used here so the runner can hold them out as an independent gate. A curve
    fitted through the anchors could not fail a check against those same anchors.
    """
    if t_opt <= t_min:
        raise ValueError(f"t_opt must be > t_min, got t_opt={t_opt}, t_min={t_min}")
    if t <= t_min:
        return 0.0
    if t >= t_opt:
        return 1.0
    return float((t - t_min) / (t_opt - t_min))
