#!/usr/bin/env python3
"""Generate web/fixtures.json from the PYTHON model at this commit.

The JS port in web/model.js is checked against this file by
tests/test_parity_js.py. Nothing here recomputes the model: every number
comes from sim/ via the same public functions the experiments call, so a
fixture can never encode a second, hidden implementation.

Contents are driven by the registered values, read from
experiments/q1_crossover/prereg.yaml -- k grids, n_grid and the solve
window are never retyped here.

Run: python3 tools/make_fixtures.py
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import scipy
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sim.organism import (  # noqa: E402
    PRESETS,
    Organism,
    compensation_irradiance,
    crossover_distance_for,
)
from sim.physiology import (  # noqa: E402
    PAR_FRACTION,
    PHOTONS_PER_J,
    Q10,
    T_REF_K,
    TSI_W_M2,
    gross_assimilation,
    irradiance,
    respiration,
)
from sim.thermal import (  # noqa: E402
    SIGMA_W_M2_K4,
    equilibrium_temperature,
    temperature_response,
)

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "experiments" / "q1_crossover" / "prereg.yaml"
OUT = ROOT / "web" / "fixtures.json"

# Display grid: linear in AU across the whole solve window, per the ship plan.
# Deliberately NOT the log-spaced bracketing grid the root-finder uses -- a
# parity check that reused the solver's own grid would sample exactly the
# points the solver is most accurate at.
GRID_N = 400


def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def git(*args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
    ).stdout.strip()


def org_to_dict(org: Organism) -> dict:
    return {
        "cls": org.cls,
        "a_max": org.a_max,
        "k": org.k,
        "r_d": org.r_d,
        "leaf_mass_ratio": org.leaf_mass_ratio,
        "t_set": org.t_set,
        "area_ratio": org.area_ratio,
        "t_min": org.t_min,
        "t_opt": org.t_opt,
        "emissivity": org.emissivity,
        "albedo": org.albedo,
        "omega": org.omega,
    }


def main() -> int:
    prereg = yaml.safe_load(PREREG.read_text())
    sweep = prereg["sweep"]
    r_min, r_max, n_grid = sweep["r_min_au"], sweep["r_max_au"], sweep["n_grid"]
    k_grids = {cls: prereg["presets"][cls]["k_grid"] for cls in PRESETS}

    grid = np.linspace(r_min, r_max, GRID_N)

    cases: dict[str, dict] = {}
    for cls, org in PRESETS.items():
        per_k = {}
        for k in k_grids[cls]:
            try:
                xover = crossover_distance_for(
                    org, k=k, r_min=r_min, r_max=r_max, n_grid=n_grid
                )
            except ValueError:
                xover = None
            per_k[repr(float(k))] = {
                "k": float(k),
                "net_carbon": [org.net_carbon(float(r), k=k) for r in grid],
                "compensation_irradiance": compensation_irradiance(org, k=k),
                "crossover_au": xover,
            }
        cases[cls] = {
            "preset": org_to_dict(org),
            "leaf_respiration": org.leaf_respiration(),
            "organism_respiration": org.organism_respiration(),
            "irradiance": [irradiance(float(r)) for r in grid],
            "equilibrium_temperature": [
                equilibrium_temperature(
                    float(r), org.area_ratio, org.emissivity, org.albedo
                )
                for r in grid
            ],
            "net_carbon_at_equilibrium": [
                org.net_carbon_at_equilibrium(float(r)) for r in grid
            ],
            "per_k": per_k,
        }

    # ---- edge cases, all inside the model's own domain ----
    edges = []

    # (1) No crossover inside [0.5, 100] AU. The algal preset at k below the
    # registered grid puts the root past r_max: net carbon never changes sign
    # in the window, and crossover_distance_for RAISES rather than returning a
    # number. The JS port must report null here, not extrapolate.
    algal = PRESETS["algal"]
    k_no_root = 5.0
    try:
        crossover_distance_for(algal, k=k_no_root, r_min=r_min, r_max=r_max, n_grid=n_grid)
        raise AssertionError(f"expected no sign change for algal k={k_no_root}")
    except ValueError as exc:
        edges.append(
            {
                "name": "no_crossover_in_window",
                "why": "algal at k=5 (below the registered grid): the root lies "
                "beyond r_max, so there is no sign change in [0.5, 100] AU",
                "preset": org_to_dict(algal),
                "k": k_no_root,
                "r_min_au": r_min,
                "r_max_au": r_max,
                "n_grid": n_grid,
                "expect": "null",
                "python_error": str(exc),
                "net_carbon_at_r_max": algal.net_carbon(r_max, k=k_no_root),
            }
        )

    # (2) The ValueError boundary of compensation_irradiance: leaf respiration
    # >= a_max means the rectangular hyperbola never reaches respiration, so
    # there is no compensation point at any irradiance. t_set == T_REF_K, so
    # leaf respiration is exactly r_d and the boundary is r_d == a_max.
    boundary = Organism(
        "vascular", a_max=10.0, k=100.0, r_d=10.0, leaf_mass_ratio=0.5
    )
    try:
        compensation_irradiance(boundary)
        raise AssertionError("expected ValueError at r_d == a_max")
    except ValueError as exc:
        edges.append(
            {
                "name": "compensation_at_respiration_boundary",
                "why": "r_d == a_max == 10.0 with t_set == t_ref, so leaf "
                "respiration equals a_max exactly: no compensation point",
                "preset": org_to_dict(boundary),
                "expect": "error",
                "python_error": str(exc),
            }
        )

    # (3) The algal t_min floor (254.65 K, Pointing et al. 2015): the Q2 linear
    # response switches off AT the floor, not asymptotically. Sampled at the
    # distance where T_eq == t_min exactly and one step either side, so a port
    # that used `<` where Python uses `<=` is caught.
    t_floor = algal.t_min
    s_at_floor = (
        algal.area_ratio * algal.emissivity * SIGMA_W_M2_K4 * t_floor**4
    ) / (1 - algal.albedo)
    r_floor = (TSI_W_M2 / s_at_floor) ** 0.5
    samples = []
    for label, r in (
        ("inside", r_floor * 0.999),
        ("at_floor", r_floor),
        ("outside", r_floor * 1.001),
    ):
        t = equilibrium_temperature(
            float(r), algal.area_ratio, algal.emissivity, algal.albedo
        )
        samples.append(
            {
                "label": label,
                "r_au": float(r),
                "t_eq": t,
                "temperature_response": temperature_response(
                    t, algal.t_min, algal.t_opt
                ),
                "net_carbon_at_equilibrium": algal.net_carbon_at_equilibrium(float(r)),
            }
        )
    edges.append(
        {
            "name": "algal_t_min_floor",
            "why": "T_eq crosses the algal t_min floor (254.65 K) at r="
            f"{r_floor:.6f} AU; temperature_response is 0 at and below it",
            "preset": org_to_dict(algal),
            "t_min": t_floor,
            "r_floor_au": float(r_floor),
            "samples": samples,
        }
    )

    doc = {
        "_comment": "Generated by tools/make_fixtures.py from the Python model. "
        "Do not hand-edit. Regenerate and re-commit if sim/ changes.",
        "provenance": {
            "git_sha": git("rev-parse", "HEAD"),
            "git_describe": git("rev-parse", "--abbrev-ref", "HEAD"),
            "worktree_dirty": bool(git("status", "--porcelain")),
            "generator": "tools/make_fixtures.py",
            "physiology_md5": md5(ROOT / "sim" / "physiology.py"),
            "thermal_md5": md5(ROOT / "sim" / "thermal.py"),
            "organism_md5": md5(ROOT / "sim" / "organism.py"),
            "prereg_md5": md5(PREREG),
            "python": sys.version.split()[0],
            "numpy": np.__version__,
            "scipy": scipy.__version__,
            "written": datetime.now(timezone.utc).astimezone().isoformat(),
        },
        "constants": {
            "TSI_W_M2": TSI_W_M2,
            "PAR_FRACTION": PAR_FRACTION,
            "PHOTONS_PER_J": PHOTONS_PER_J,
            "T_REF_K": T_REF_K,
            "Q10": Q10,
            "SIGMA_W_M2_K4": SIGMA_W_M2_K4,
        },
        "registered": {
            "source": "experiments/q1_crossover/prereg.yaml",
            "r_min_au": r_min,
            "r_max_au": r_max,
            "n_grid": n_grid,
            "k_grid": k_grids,
            "predicted_r_star_au": {
                cls: prereg["presets"][cls]["predicted_r_star_au"] for cls in PRESETS
            },
            "gate_umol": {cls: prereg["presets"][cls]["gate_umol"] for cls in PRESETS},
        },
        "tolerances": {
            "_form": "abs_err <= atol + rtol * |ref|",
            "irradiance": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "gross_assimilation": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "respiration": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "leaf_respiration": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "organism_respiration": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "equilibrium_temperature": {
                "rtol": 1e-9,
                "atol": 0.0,
                "why": "closed form",
            },
            "compensation_irradiance": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "temperature_response": {
                "rtol": 1e-9,
                "atol": 1e-15,
                "why": "closed form, but the ramp returns exact 0 below t_min "
                "where a relative bound has no meaning",
            },
            "net_carbon": {
                "rtol": 1e-9,
                "atol": 1e-12,
                "why": "closed form, but it is a DIFFERENCE that passes through "
                "zero at the crossover: near the root |ref| is ~1e-17 and a pure "
                "relative bound would demand bit-exact cancellation between two "
                "O(1) terms. 1e-12 umol CO2 m-2 s-1 is ~1e-13 of the values at "
                "either end of the grid.",
            },
            "net_carbon_at_equilibrium": {
                "rtol": 1e-9,
                "atol": 1e-12,
                "why": "same difference-through-zero reason as net_carbon",
            },
            "crossover_au": {
                "rtol": 1e-6,
                "atol": 1e-6,
                "why": "bracketed root; the JS port bisects where Python uses "
                "scipy brentq with xtol=1e-6, so agreement is bounded by the "
                "solver tolerance, not by float precision",
            },
        },
        "grid_au": [float(r) for r in grid],
        "cases": cases,
        "edge_cases": edges,
    }

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, indent=1) + "\n")
    print(f"wrote {OUT.relative_to(ROOT)}  ({OUT.stat().st_size} bytes)")
    print(f"  git_sha={doc['provenance']['git_sha']}")
    for cls in cases:
        ks = ", ".join(
            f"k={c['k']:g}:{'null' if c['crossover_au'] is None else format(c['crossover_au'], '.4f')}"
            for c in cases[cls]["per_k"].values()
        )
        print(f"  {cls}: {ks}")
    print(f"  edge cases: {', '.join(e['name'] for e in edges)}")
    # Unused-import guard: these are re-exported into the fixture's contract via
    # the constants block and the checks above; naming them here keeps linters
    # from stripping the imports the doc depends on.
    assert gross_assimilation(100.0, 10.0, 100.0) > 0
    assert respiration(1.0, T_REF_K) == 1.0
    assert Q10 == 2.0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
