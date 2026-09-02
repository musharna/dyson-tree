"""Pure physics and physiology functions for the Q1 carbon-budget model.

Units: irradiance in µmol photons m⁻² s⁻¹; assimilation/respiration in
µmol CO₂ m⁻² s⁻¹ per unit photosynthetic area; temperature in K; distance in AU.
All functions are stateless. Out-of-range inputs raise ValueError naming the value.
"""

from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

# Kopp & Lean 2011, doi:10.1029/2010GL045777 (2008 solar minimum)
TSI_W_M2 = 1360.8
# Assumptions, declared in experiments/q1_crossover/prereg.yaml
PAR_FRACTION = 0.45  # fraction of TSI in 400-700 nm
PHOTONS_PER_J = 4.57  # µmol photons per J of PAR
T_REF_K = 293.0
Q10 = 2.0


def irradiance(
    r_au, tsi=TSI_W_M2, par_fraction=PAR_FRACTION, photons_per_j=PHOTONS_PER_J
):
    """PAR photon flux at heliocentric distance r_au, top-of-atmosphere, 1/r²."""
    r = np.asarray(r_au, dtype=float)
    if np.any(r <= 0):
        raise ValueError(f"r_au must be > 0, got {r_au}")
    out = tsi / r**2 * par_fraction * photons_per_j
    return float(out) if out.ndim == 0 else out


def gross_assimilation(i, a_max, k):
    """Rectangular hyperbola: a_max * I / (I + k)."""
    if a_max <= 0:
        raise ValueError(f"a_max must be > 0, got {a_max}")
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    ii = np.asarray(i, dtype=float)
    if np.any(ii < 0):
        raise ValueError(f"irradiance must be >= 0, got {i}")
    out = a_max * ii / (ii + k)
    return float(out) if out.ndim == 0 else out


def respiration(r_d, t, t_ref=T_REF_K, q10=Q10):
    """Dark respiration with Q10 temperature dependence."""
    if r_d < 0:
        raise ValueError(f"r_d must be >= 0, got {r_d}")
    if t <= 0:
        raise ValueError(f"t must be > 0 K, got {t}")
    if q10 <= 0:
        raise ValueError(f"q10 must be > 0, got {q10}")
    return r_d * q10 ** ((t - t_ref) / 10.0)


def crossover_distance(net_fn, r_min=0.5, r_max=100.0, n_grid=400):
    """Distance in AU where net_fn(r) crosses zero. Brent root on the first
    sign change of a log-spaced grid. Raises if there is no sign change."""
    if r_min <= 0 or r_max <= r_min:
        raise ValueError(f"need 0 < r_min < r_max, got {r_min}, {r_max}")
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    if len(idx) == 0:
        raise ValueError(
            f"no sign change of net carbon on [{r_min}, {r_max}] AU: "
            f"min={vals.min():.4g}, max={vals.max():.4g}"
        )
    i = idx[0]
    return float(brentq(net_fn, grid[i], grid[i + 1], xtol=1e-6))
