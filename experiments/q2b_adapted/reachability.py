"""What the gates admit, and what shape the curve has -- both computed BEFORE
the prediction is registered.

Q1 registered a band of which 89.5% was unreachable. Q2 registered a prediction
no parameters could satisfy. Both were discovered after the run. This module
exists so Q2b's prereg can record the answer in advance."""

from __future__ import annotations

import numpy as np


def gate_b_verdict(
    predicted_k: float, measured_c: list[float], half_width_k: float = 5.0
) -> tuple[bool, float, float]:
    """Gate B: does the model's PREDICTED optimum match the measured one?

    The window is [min(measured) - half_width, max(measured) + half_width] in C,
    because the algal source reports two site values rather than one. half_width
    is a DECLARED ASSUMPTION -- no source gives an adaptation tolerance.

    Returns (passed, lo_c, hi_c)."""
    if not measured_c:
        raise ValueError("measured_c must be a non-empty list of degrees C")
    if half_width_k < 0:
        raise ValueError(f"half_width_k must be >= 0, got {half_width_k}")
    lo = min(measured_c) - half_width_k
    hi = max(measured_c) + half_width_k
    predicted_c = predicted_k - 273.15
    return (lo <= predicted_c <= hi, lo, hi)


def sign_structure(net_fn, r_min: float, r_max: float, n_grid: int) -> list:
    """The ordered sign transitions of net_fn on a log grid.

    Q2's outer-root selector assumes exactly [(-1, 1), (1, -1)] and fails loud on
    anything else. Q2b's curve is Gaussian rather than a linear ramp, so its shape
    is NOT assumed to match -- it is measured here, before the prereg is written."""
    if r_min <= 0 or r_max <= r_min:
        raise ValueError(f"need 0 < r_min < r_max, got {r_min}, {r_max}")
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    return [(int(sign[i]), int(sign[i + 1])) for i in idx]
