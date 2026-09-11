#!/usr/bin/env python3
"""Reproduce `curve_shape.transitions_per_omega` from `q2b_adapted/prereg.yaml`.

That block records the sign structure of `net_carbon_adapted` for every
(class, omega) on the registered [0.5, 100] AU grid. It was measured in Task 3
BEFORE the runner was written, and the prereg cites an internal working note for
the command -- a file that is not in this repository, so until now the table had
no committed way to check it.

`tests/test_q2b_runner.py` exercises the same branches, but deliberately with
SYNTHETIC closures (an always-negative curve, a three-root curve) rather than the
real classes and omegas, because the real runner never reaches them: vascular is
excluded at Gate B and algal always produces exactly two roots. So the tests pin
the selector's behaviour, not this table's contents. This script pins the table.

It changes nothing. It recomputes the sign structure the same way
`outer_carbon_crossover` does -- same grid, same `np.sign` product test -- and
compares it against what the prereg registered. The prereg is not rewritten; a
mismatch is reported as a failure here.

    python3 tools/check_q2b_curve_shape.py

Exit 0 if every registered shape reproduces, 1 otherwise.
"""

from __future__ import annotations

import signal
import sys
from pathlib import Path

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(600)

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

import numpy as np  # noqa: E402

from experiments.q2b_adapted.run import build, load_prereg  # noqa: E402

PREREG = REPO_ROOT / "experiments/q2b_adapted/prereg.yaml"


def transitions_for(net_fn, r_min: float, r_max: float, n_grid: int) -> list[list[int]]:
    """The sign-change list, computed exactly as `outer_carbon_crossover` does."""
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    return [[int(sign[i]), int(sign[i + 1])] for i in idx]


def main() -> int:
    pre = load_prereg(PREREG)
    a = pre["assumptions"]
    sw = pre["sweep"]
    r_home = float(a["r_home_au"])
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    registered = pre["curve_shape"]["transitions_per_omega"]

    failures = []
    print(f"{'class':9} {'omega':>6}  {'registered':>26}  {'recomputed':>26}  verdict")
    for cls, per_omega in registered.items():
        for omega_s, want in per_omega.items():
            omega = float(omega_s)
            org = build(cls, pre["presets"][cls], a, omega)
            got = transitions_for(
                lambda r: org.net_carbon_adapted(r, r_home), r_min, r_max, n_grid
            )
            ok = got == [list(t) for t in want]
            if not ok:
                failures.append((cls, omega_s, want, got))
            print(
                f"{cls:9} {omega_s:>6}  {str(want):>26}  {str(got):>26}  "
                f"{'OK' if ok else 'MISMATCH'}"
            )

    # A positive control on the checker itself: the comparison must be capable of
    # reporting a mismatch. Both registered shapes are present in the table above
    # (algal's two-root shape and vascular's empty one), so a checker that always
    # said OK would be visible here as an impossible unanimity across two
    # genuinely different shapes.
    shapes = {str(v) for per in registered.values() for v in per.values()}
    assert len(shapes) > 1, (
        "control FAILED: the registered table holds only one distinct shape, so "
        "agreeing with it is not evidence of anything"
    )

    if failures:
        print(f"\nFAILED: {len(failures)} registered shape(s) do not reproduce.")
        for cls, omega_s, want, got in failures:
            print(f"  {cls} omega={omega_s}: registered {want}, recomputed {got}")
        return 1

    print(
        f"\nOK -- all {sum(len(p) for p in registered.values())} registered shapes "
        f"reproduce, across {len(shapes)} distinct shapes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
