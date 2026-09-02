"""Where the gates permit an outcome to land, computed BEFORE registering a band.

Q1 registered bands without this and found afterwards that 96.2% of one band was
pre-satisfied by its gate and 89.5% of the other was unreachable."""

from __future__ import annotations

from sim.physiology import TSI_W_M2
from sim.thermal import SIGMA_W_M2_K4


def thermal_cutoff_au(
    t_min: float, area_ratio: float, emissivity: float = 1.0, albedo: float = 0.0
) -> float:
    """Distance at which equilibrium temperature falls to t_min.

    Closed form: T(r) = T(1 AU) / sqrt(r), so r = (T(1 AU) / t_min)^2."""
    if t_min <= 0:
        raise ValueError(f"t_min must be > 0 K, got {t_min}")
    if area_ratio <= 0:
        raise ValueError(f"area_ratio must be > 0, got {area_ratio}")
    t_1au = (
        TSI_W_M2 * (1 - albedo) / (area_ratio * emissivity * SIGMA_W_M2_K4)
    ) ** 0.25
    return float((t_1au / t_min) ** 2)
