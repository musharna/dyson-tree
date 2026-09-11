#!/usr/bin/env python3
"""Derive the three candidate outer distances, per class and per omega, that
`docs/FINDINGS.md` tabulates twice -- and that no committed file held.

FINDINGS reports two tables built from Q2b's `classify_limit`:

  * the ALGAL table ("Carbon does not set the outer limit. Temperature does"),
    whose temperature (1.1945 AU) and light (70.04 AU) columns appear in no
    committed artifact. `experiments/q2b_adapted/limits.csv` carries only
    `class,omega,outer_au,binding` -- `outer_au` is the CARBON candidate, so
    the two columns the falsification actually turns on were unreproducible
    from the repository.
  * the VASCULAR table, showing that the registered prediction would have held
    at omega = 25 and 30 for the class Gate B excluded. The runner writes no
    vascular row anywhere, by design, so that table had no artifact either.

This script writes both into `experiments/q2b_adapted/candidates.csv`.

It is NOT a measurement and changes nothing that was measured. It calls the
runner's own `build()` and `classify_limit()` on the committed prereg -- not a
reimplementation -- so the only thing it can report is what the registered code
already computes. Running the vascular rows is exactly what FINDINGS describes
doing ("Running Q2b's own classify_limit on the vascular class"); Gate B's
exclusion of vascular from `sweep.csv` and `limits.csv` is untouched.

    python3 tools/derive_q2b_candidates.py

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

import math  # noqa: E402

from derive_provenance import derived_header, write_derived_csv  # noqa: E402

from experiments.q2b_adapted.run import (  # noqa: E402
    build,
    classify_limit,
    load_prereg,
    run_gate_b,
)

PREREG = REPO_ROOT / "experiments/q2b_adapted/prereg.yaml"
LIMITS = REPO_ROOT / "experiments/q2b_adapted/limits.csv"
OUT = REPO_ROOT / "experiments/q2b_adapted/candidates.csv"

# The carbon candidate and binding verdict of every row the runner committed to
# limits.csv. This is the positive control: a derivation that cannot reproduce
# the committed baseline cannot be trusted to report the columns that baseline
# does not contain.
SHIPPED = {
    10.0: (1.2119, "temperature"),
    15.0: (1.3794, "temperature"),
    20.0: (1.6178, "temperature"),
    25.0: (1.9718, "temperature"),
    30.0: (2.5289, "temperature"),
}

# The vascular rows as FINDINGS prints them. Held out the same way: if the
# derivation disagrees here, FINDINGS is wrong or this script is, and either way
# nothing should be written.
FINDINGS_VASCULAR = {
    10.0: (1.5581, 12.7058, None, "temperature"),
    15.0: (1.5581, 12.7058, None, "temperature"),
    20.0: (1.5581, 12.7058, None, "temperature"),
    25.0: (1.5581, 12.7058, 1.2060, "carbon"),
    30.0: (1.5581, 12.7058, 1.3920, "carbon"),
}


def fmt(x: float) -> str:
    """4 dp, or the empty string for a candidate that does not exist. NaN means
    'no crossing anywhere on the registered window' -- a disclosed outcome, not
    a failure -- and writing it as an empty cell keeps a reader from reading it
    as a number that happened to be zero."""
    return "" if math.isnan(x) else f"{x:.4f}"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # --out exists so the regenerate-exactly test can write the Q2b candidate table
    # into a temp directory and diff it against what is committed,
    # without clobbering the committed file to run the check.
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    pre = load_prereg(PREREG)
    a = pre["assumptions"]
    sw = pre["sweep"]
    r_home = float(a["r_home_au"])
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    omegas = [float(w) for w in pre["omega_grid_k"]]

    results = {
        (cls, w): classify_limit(
            build(cls, pre["presets"][cls], a, w), r_home, r_min, r_max, n_grid
        )
        for cls in pre["presets"]
        for w in omegas
    }

    # --- CONTROL 1 (positive): reproduce every committed limits.csv row.
    for w in omegas:
        want_au, want_bind = SHIPPED[w]
        got = results[("algal", w)]
        assert abs(got["carbon"] - want_au) < 1e-4, (
            f"C1 FAILED omega={w}: carbon {got['carbon']:.4f}, limits.csv says {want_au}"
        )
        assert got["binding"] == want_bind, (
            f"C1 FAILED omega={w}: binding {got['binding']}, limits.csv says {want_bind}"
        )
    print("control 1 OK -- reproduces all 5 committed limits.csv carbon/binding rows")

    # --- CONTROL 2 (positive): reproduce FINDINGS' vascular table digit for digit.
    for w, (t_au, l_au, c_au, bind) in FINDINGS_VASCULAR.items():
        got = results[("vascular", w)]
        assert abs(got["temperature"] - t_au) < 1e-4, f"C2 FAILED omega={w} temperature"
        assert abs(got["light"] - l_au) < 1e-4, f"C2 FAILED omega={w} light"
        if c_au is None:
            assert math.isnan(got["carbon"]), (
                f"C2 FAILED omega={w}: carbon {got['carbon']}, FINDINGS says no crossing"
            )
        else:
            assert abs(got["carbon"] - c_au) < 1e-4, (
                f"C2 FAILED omega={w}: carbon {got['carbon']:.4f}, FINDINGS says {c_au}"
            )
        assert got["binding"] == bind, f"C2 FAILED omega={w} binding"
    print("control 2 OK -- reproduces FINDINGS' vascular classify_limit table")

    # --- CONTROL 3 (negative result needs a positive control): `binding` must be
    # capable of reporting something other than "temperature", or the algal
    # table's unanimity is a property of the predicate rather than of the model.
    # The vascular rows supply that directly -- two of them say "carbon".
    bindings = {r["binding"] for r in results.values()}
    assert "carbon" in bindings and "temperature" in bindings, (
        f"C3 FAILED: binding took only the values {bindings}; a predicate that "
        "cannot vary cannot evidence the falsification"
    )
    print(f"control 3 OK -- binding varies across the table: {sorted(bindings)}")

    # --- CONTROL 4: Gate B's verdict is unchanged by this script. The vascular
    # rows below are computed for the record, NOT smuggled into the run.
    _, passing = run_gate_b(pre)
    assert passing == {"algal"}, f"C4 FAILED: gate B passing set is {passing}"
    print("control 4 OK -- gate B still passes algal only; no runner output changes")

    rows = [
        {
            "class": cls,
            "omega": f"{w:g}",
            "temperature_au": fmt(results[(cls, w)]["temperature"]),
            "light_au": fmt(results[(cls, w)]["light"]),
            "carbon_au": fmt(results[(cls, w)]["carbon"]),
            "binding": results[(cls, w)]["binding"],
            "in_limits_csv": "yes" if cls in passing else "no (gate B excluded)",
        }
        for cls in pre["presets"]
        for w in omegas
    ]

    write_derived_csv(
        out,
        derived_header(__file__, [PREREG, LIMITS]),
        [
            "class",
            "omega",
            "temperature_au",
            "light_au",
            "carbon_au",
            "binding",
            "in_limits_csv",
        ],
        rows,
    )
    print(f"\nwrote {out} ({len(rows)} rows)")
    for r in rows:
        print(
            f"  {r['class']:9} omega={r['omega']:>2}  "
            f"temperature={r['temperature_au']:>7}  light={r['light_au']:>7}  "
            f"carbon={r['carbon_au'] or '(no crossing)':>13}  -> {r['binding']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
