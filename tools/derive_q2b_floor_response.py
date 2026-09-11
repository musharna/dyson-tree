#!/usr/bin/env python3
"""Derive the two numbers behind FINDINGS' "What this does not say" paragraph.

FINDINGS states that the temperature limit is a comparison of candidate
distances and NOT a cut-off: "at 1.1945 AU and omega = 10 the response is
0.0037, not 0, and net carbon is still +0.0197". That is the sentence keeping
the falsification from being over-read, and neither number lived in a committed
file.

Both are written to `experiments/q2b_adapted/floor_response.csv`.

Two rows, deliberately, because the distance is quoted rounded. Evaluated at
the full-precision thermal floor (1.194466... AU) the response is 0.003703 and
net carbon +0.019783; evaluated at the literal 1.1945 AU that FINDINGS prints,
they are 0.003697 and +0.019725 -- the figures `docs/RELEASE-1.0.md`'s round-2
re-review quotes. The two agree to every digit FINDINGS actually claims (0.0037
and +0.0197), and the gap is rounding of the INPUT distance, not a disagreement
about the model. Committing both rows is what makes that checkable instead of
something a reader has to take on trust.

It is NOT a measurement. It calls the runner's own `build()` and
`classify_limit()` and the model's own `net_carbon_adapted`, on the committed
prereg.

    python3 tools/derive_q2b_floor_response.py

Exit 0 on success. Any control failure raises rather than writing a file.
"""

from __future__ import annotations

import argparse
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
sys.path.insert(0, str(REPO_ROOT / "tools"))

from derive_provenance import derived_header, write_derived_csv  # noqa: E402

from experiments.q2b_adapted.run import (  # noqa: E402
    build,
    classify_limit,
    load_prereg,
)
from sim.thermal import (  # noqa: E402
    adapted_optimum,
    equilibrium_temperature,
    temperature_response_gaussian,
)

PREREG = REPO_ROOT / "experiments/q2b_adapted/prereg.yaml"
OUT = REPO_ROOT / "experiments/q2b_adapted/floor_response.csv"

OMEGA = 10.0  # the omega FINDINGS quotes
FINDINGS_ROUNDED = (0.0037, 0.0197)  # response, net carbon -- as printed
RELEASE_AT_ROUNDED_R = (0.003697, 0.019725)  # RELEASE round-2, at r = 1.1945 exactly


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # --out exists so the regenerate-exactly test can write the Q2b floor-response rows
    # into a temp directory and diff it against what is committed,
    # without clobbering the committed file to run the check.
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    pre = load_prereg(PREREG)
    a = pre["assumptions"]
    sw = pre["sweep"]
    r_home = float(a["r_home_au"])
    org = build("algal", pre["presets"]["algal"], a, OMEGA)

    floor = classify_limit(
        org,
        r_home,
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )["temperature"]
    t_opt = adapted_optimum(r_home, org.area_ratio, org.emissivity, org.albedo)

    def at(r: float) -> dict:
        t_eq = equilibrium_temperature(r, org.area_ratio, org.emissivity, org.albedo)
        return {
            "r_au": r,
            "t_eq_k": t_eq,
            "response": temperature_response_gaussian(t_eq, t_opt, OMEGA),
            "net_carbon": org.net_carbon_adapted(r, r_home),
        }

    exact, rounded = at(floor), at(1.1945)

    # --- CONTROL 1 (positive): the full-precision floor is where equilibrium
    # temperature equals the class's grounded t_min. If it is not, the distance
    # this whole file is about is not the thermal floor.
    assert abs(exact["t_eq_k"] - org.t_min) < 1e-6, (
        f"C1 FAILED: t_eq at the floor is {exact['t_eq_k']}, t_min is {org.t_min}"
    )
    print(f"control 1 OK -- t_eq at the floor = t_min = {org.t_min} K")

    # --- CONTROL 2 (positive): FINDINGS quotes both figures AT the distance it
    # prints, so that is the row its claim has to be checked against.
    assert round(rounded["response"], 4) == FINDINGS_ROUNDED[0], (
        f"C2 FAILED: response {rounded['response']:.6f} at r = 1.1945 does not "
        f"round to FINDINGS' {FINDINGS_ROUNDED[0]}"
    )
    assert round(rounded["net_carbon"], 4) == FINDINGS_ROUNDED[1], (
        f"C2 FAILED: net carbon {rounded['net_carbon']:.6f} at r = 1.1945 does "
        f"not round to FINDINGS' {FINDINGS_ROUNDED[1]}"
    )
    print("control 2 OK -- at the printed 1.1945 AU, FINDINGS' 0.0037 / +0.0197 hold")

    # --- CONTROL 2b: at the FULL-PRECISION floor the response still rounds to
    # 0.0037, but net carbon is 0.019783 -- 0.0198 at 4 dp, not 0.0197. Pinned
    # rather than smoothed over: the two distances must stay close enough that
    # rounding the input explains the gap (equal at 3 dp), and FINDINGS' figure
    # must keep being read as "at the distance printed", not "at the floor".
    assert round(exact["response"], 4) == FINDINGS_ROUNDED[0], (
        f"C2b FAILED: response at the exact floor is {exact['response']:.6f}"
    )
    assert round(exact["net_carbon"], 3) == round(FINDINGS_ROUNDED[1], 3), (
        f"C2b FAILED: net carbon at the exact floor is {exact['net_carbon']:.6f}, "
        f"which disagrees with FINDINGS' {FINDINGS_ROUNDED[1]} at 3 dp -- more "
        "than rounding the input distance explains"
    )
    print(
        f"control 2b OK -- at the exact floor net carbon is "
        f"{exact['net_carbon']:.6f} (0.0198 at 4 dp), equal to 3 dp; the "
        "difference is the rounded input distance"
    )

    # --- CONTROL 3 (positive): the rounded-distance evaluation reproduces the
    # figures RELEASE's round-2 re-review published, which is what identifies the
    # 4th-digit gap as rounding of the input rather than a model disagreement.
    assert abs(rounded["response"] - RELEASE_AT_ROUNDED_R[0]) < 5e-7, (
        f"C3 FAILED: response {rounded['response']:.6f} != RELEASE "
        f"{RELEASE_AT_ROUNDED_R[0]}"
    )
    assert abs(rounded["net_carbon"] - RELEASE_AT_ROUNDED_R[1]) < 5e-7, (
        f"C3 FAILED: net carbon {rounded['net_carbon']:.6f} != RELEASE "
        f"{RELEASE_AT_ROUNDED_R[1]}"
    )
    print(
        "control 3 OK -- at r = 1.1945 exactly, reproduces RELEASE's 0.003697 / +0.019725"
    )

    # --- CONTROL 4 (the point of the paragraph): the response must be strictly
    # positive here. An assertion that it is "small" would pass on a response
    # that had switched off, which is the exact misreading this file exists to
    # foreclose.
    assert exact["response"] > 0 and exact["net_carbon"] > 0, (
        f"C4 FAILED: response {exact['response']} / net carbon "
        f"{exact['net_carbon']} -- the 'not a cut-off' claim does not hold"
    )
    print(
        "control 4 OK -- response and net carbon are both strictly positive at the floor"
    )

    rows = [
        {
            "evaluated_at": label,
            "omega": f"{OMEGA:g}",
            "r_au": f"{row['r_au']:.6f}",
            "t_eq_k": f"{row['t_eq_k']:.6f}",
            "gaussian_response": f"{row['response']:.6f}",
            "net_carbon": f"{row['net_carbon']:+.6f}",
        }
        for label, row in (
            ("thermal floor (full precision)", exact),
            ("1.1945 AU (as printed in FINDINGS)", rounded),
        )
    ]

    write_derived_csv(
        out,
        derived_header(__file__, [PREREG]),
        ["evaluated_at", "omega", "r_au", "t_eq_k", "gaussian_response", "net_carbon"],
        rows,
    )
    print(f"\nwrote {out} ({len(rows)} rows)")
    for r in rows:
        print(
            f"  {r['evaluated_at']:36} r={r['r_au']}  "
            f"response={r['gaussian_response']}  net_carbon={r['net_carbon']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
