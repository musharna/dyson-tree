#!/usr/bin/env python3
"""Derive the gate-reachability scan that FINDINGS' "What holds" section reports
and no committed file held.

FINDINGS argues that Q1's vascular hit carries less information than the algal
miss, because the calibration gate constrains `r_d` and r* follows from `r_d` --
so part of each registered band was already decided before the sweep ran. The
four release-code figures it tabulates (`docs/FINDINGS.md`, "What holds";
`CHANGELOG.md` 1.0.0) were:

    vascular reachable r*                      [11.04, 14.68] AU
    share of gate-admissible r_d giving a hit  66.4%
    algal floor on r*                          43.65 AU
    share of [35, 55] unreachable              43.3%

They existed only as prose. This script writes them to
`experiments/q1_crossover/reachability.csv`.

Method, exactly as FINDINGS states it: invert the calibration gate to get the
interval of `r_d` a gate-passing organism could have had, then evaluate
`crossover_distance_for(n_grid=200)` -- the prereg's own declared grid -- across
it, holding every other registered value fixed.

`compensation_irradiance` is monotone increasing in `r_d` and r* is monotone
decreasing in it, so each interval endpoint maps to the opposite endpoint of the
reachable r* interval, and the share is found by solving for the `r_d` at which
r* crosses the band edge rather than by counting grid points. That matters: the
one wrong digit in this table's history (43.66 for 43.65, `docs/RELEASE-1.0.md`
Stage 6 round 2) came from a `linspace` scan whose grid never landed on the
endpoint.

It is NOT a measurement and changes nothing that was measured. It calls the Q1
runner's own `build()` and the model's own `compensation_irradiance` and
`crossover_distance_for`, on the committed prereg.

    python3 tools/derive_q1_reachability.py

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

from scipy.optimize import brentq  # noqa: E402

from derive_provenance import derived_header, write_derived_csv  # noqa: E402

from experiments.q1_crossover.run import build, load_prereg  # noqa: E402
from sim.organism import (  # noqa: E402
    compensation_irradiance,
    crossover_distance_for,
)
from sim.physiology import respiration  # noqa: E402

PREREG = REPO_ROOT / "experiments/q1_crossover/prereg.yaml"
CROSSOVER = REPO_ROOT / "experiments/q1_crossover/crossover.csv"
OUT = REPO_ROOT / "experiments/q1_crossover/reachability.csv"

# crossover.csv's rows at each class's registered default k. The positive
# control: a scan that cannot reproduce the committed sweep at the registered
# `r_d` is not scanning the same model the sweep did. FINDINGS names exactly
# this check.
CONTROL_RSTAR = {"vascular": (100.0, 12.7058), "algal": (20.0, 62.4490)}

# What FINDINGS reports, held out so the derivation has something to disagree
# with. (floor_au, ceiling_au_or_None, share_pct, share_kind)
FINDINGS_TABLE = {
    "vascular": (11.04, 14.68, 66.4, "inside"),
    "algal": (43.65, None, 43.3, "unreachable"),
}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    # --out exists so the regenerate-exactly test can write the Q1 reachability scan
    # into a temp directory and diff it against what is committed,
    # without clobbering the committed file to run the check.
    ap.add_argument("--out", type=Path, default=OUT)
    out = ap.parse_args(argv).out
    pre = load_prereg(PREREG)
    a = pre["assumptions"]
    sw = pre["sweep"]
    t_set = float(a["t_set_k"])
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )

    def org(cls: str, r_d: float):
        p = dict(pre["presets"][cls])
        p["r_d"] = r_d
        return build(cls, p, t_set)

    def i_c(cls: str, r_d: float, k: float) -> float:
        return compensation_irradiance(org(cls, r_d), k=k)

    def r_star(cls: str, r_d: float, k: float) -> float:
        return crossover_distance_for(
            org(cls, r_d), k=k, r_min=r_min, r_max=r_max, n_grid=n_grid
        )

    # --- CONTROL 1 (positive): reproduce crossover.csv at the registered r_d.
    for cls, (k, want) in CONTROL_RSTAR.items():
        got = r_star(cls, float(pre["presets"][cls]["r_d"]), k)
        assert abs(got - want) < 1e-4, (
            f"C1 FAILED {cls}: r* = {got:.4f}, crossover.csv says {want}"
        )
    print("control 1 OK -- reproduces crossover.csv at both registered defaults")

    rows = []
    for cls, (k, _) in CONTROL_RSTAR.items():
        p = pre["presets"][cls]
        ic_lo, ic_hi = (float(x) for x in p["gate_umol"])
        band_lo, band_hi = (float(x) for x in p["predicted_r_star_au"])
        a_max = float(p["a_max"])

        # r_d ceiling: there is no compensation point once leaf respiration
        # reaches a_max, so the inversion must bracket strictly below it.
        r_d_cap = float(
            brentq(lambda rd: respiration(rd, t_set) - a_max * 0.999999, 1e-12, 1e6)
        )

        def invert_gate(target: float) -> float:
            """The r_d at which compensation irradiance equals `target`. A gate
            floor of 0 admits r_d = 0 exactly (no respiration, no compensation
            point to exceed), which brentq cannot bracket."""
            if target <= 0:
                return 0.0
            return float(
                brentq(
                    lambda rd: i_c(cls, rd, k) - target,
                    1e-15,
                    r_d_cap,
                    xtol=1e-15,
                )
            )

        r_d_lo, r_d_hi = invert_gate(ic_lo), invert_gate(ic_hi)

        # --- CONTROL 2 (positive): the inversion round-trips through the gate.
        assert abs(i_c(cls, r_d_hi, k) - ic_hi) < 1e-9, f"C2 FAILED {cls} upper gate"
        if r_d_lo > 0:
            assert abs(i_c(cls, r_d_lo, k) - ic_lo) < 1e-9, (
                f"C2 FAILED {cls} lower gate"
            )

        # Monotonicity: more respiration -> nearer crossover. r_d_hi gives the floor.
        r_star_floor = r_star(cls, r_d_hi, k)
        r_star_ceiling = r_star(cls, r_d_lo, k) if r_d_lo > 0 else math.inf

        # --- CONTROL 3: that monotonicity is asserted, not assumed.
        assert r_star_floor < r_star_ceiling, (
            f"C3 FAILED {cls}: r* is not decreasing in r_d "
            f"({r_star_floor} at r_d={r_d_hi}, {r_star_ceiling} at r_d={r_d_lo})"
        )

        if math.isfinite(r_star_ceiling):
            # Share of the gate-admissible r_d interval landing inside the band.
            # Here the whole reachable interval sits below the band ceiling, so
            # the only binding edge is the floor; solve for where r* crosses it.
            r_d_at_band = float(
                brentq(
                    lambda rd: r_star(cls, rd, k) - band_lo,
                    r_d_lo,
                    r_d_hi,
                    xtol=1e-13,
                )
            )
            share = 100.0 * (r_d_at_band - r_d_lo) / (r_d_hi - r_d_lo)
            share_kind = "inside"
            ceiling_s = f"{r_star_ceiling:.4f}"
        else:
            # No gate-passing r_d reaches below the floor, so everything from the
            # band's lower edge up to that floor was unreachable before the sweep.
            share = 100.0 * (r_star_floor - band_lo) / (band_hi - band_lo)
            share_kind = "unreachable"
            ceiling_s = ""

        # --- CONTROL 4 (the claim): check against what FINDINGS prints.
        want_floor, want_ceiling, want_share, want_kind = FINDINGS_TABLE[cls]
        assert share_kind == want_kind, f"C4 FAILED {cls}: share kind {share_kind}"
        assert abs(round(r_star_floor, 2) - want_floor) < 1e-9, (
            f"C4 FAILED {cls}: floor {r_star_floor:.6f} != FINDINGS' {want_floor}"
        )
        if want_ceiling is not None:
            assert abs(round(r_star_ceiling, 2) - want_ceiling) < 1e-9, (
                f"C4 FAILED {cls}: ceiling {r_star_ceiling:.6f} != {want_ceiling}"
            )
        assert abs(round(share, 1) - want_share) < 1e-9, (
            f"C4 FAILED {cls}: share {share:.4f}% != FINDINGS' {want_share}%"
        )

        rows.append(
            {
                "class": cls,
                "k": f"{k:g}",
                "gate_ic_lo": f"{ic_lo:g}",
                "gate_ic_hi": f"{ic_hi:g}",
                "r_d_lo": f"{r_d_lo:.6f}",
                "r_d_hi": f"{r_d_hi:.6f}",
                "r_star_floor_au": f"{r_star_floor:.6f}",
                "r_star_ceiling_au": ceiling_s,
                "band_lo_au": f"{band_lo:g}",
                "band_hi_au": f"{band_hi:g}",
                "share_pct": f"{share:.4f}",
                "share_of": share_kind,
            }
        )
    print("control 2 OK -- the gate inversion round-trips to the declared I_c")
    print("control 3 OK -- r* confirmed monotone decreasing in r_d for both classes")
    print("control 4 OK -- reproduces all four figures FINDINGS reports")

    write_derived_csv(
        out,
        derived_header(__file__, [PREREG, CROSSOVER]),
        [
            "class",
            "k",
            "gate_ic_lo",
            "gate_ic_hi",
            "r_d_lo",
            "r_d_hi",
            "r_star_floor_au",
            "r_star_ceiling_au",
            "band_lo_au",
            "band_hi_au",
            "share_pct",
            "share_of",
        ],
        rows,
    )
    print(f"\nwrote {out} ({len(rows)} rows)")
    for r in rows:
        reach = (
            f"[{r['r_star_floor_au']}, {r['r_star_ceiling_au']}]"
            if r["r_star_ceiling_au"]
            else f"[{r['r_star_floor_au']}, inf)"
        )
        print(
            f"  {r['class']:9} r_d in [{r['r_d_lo']}, {r['r_d_hi']}]  "
            f"reachable r* = {reach} AU  "
            f"{r['share_pct']}% {r['share_of']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
