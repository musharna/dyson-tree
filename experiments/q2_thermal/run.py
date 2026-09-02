#!/usr/bin/env python3
"""Q2 runner: two gates, then a distance sweep, then provenance-stamped CSVs.

Exit codes: 0 = both gates passed and limits written; 2 = a gate failed
(gates.csv written, sweep.csv and limits.csv removed). Anything else raises.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import physiology, thermal  # noqa: E402
from sim.organism import Organism, crossover_distance_for  # noqa: E402
from sim.physiology import crossover_distance  # noqa: E402
from sim.thermal import equilibrium_temperature, temperature_response  # noqa: E402

THERMAL_PATH = REPO_ROOT / "sim" / "thermal.py"
ORGANISM_PATH = REPO_ROOT / "sim" / "organism.py"
PHYSIOLOGY_PATH = REPO_ROOT / "sim" / "physiology.py"


def load_prereg(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def assert_assumptions_match(prereg: dict) -> None:
    a = prereg["assumptions"]
    pairs = {
        "tsi_w_m2": physiology.TSI_W_M2,
        "par_fraction": physiology.PAR_FRACTION,
        "photons_per_j": physiology.PHOTONS_PER_J,
        "t_ref_k": physiology.T_REF_K,
        "q10": physiology.Q10,
        "sigma_w_m2_k4": thermal.SIGMA_W_M2_K4,
    }
    for key, code_value in pairs.items():
        if not np.isclose(a[key], code_value):
            raise ValueError(
                f"prereg assumption {key}={a[key]} does not match code {key}={code_value}"
            )


def build(name: str, p: dict, a: dict, t_min: float) -> Organism:
    return Organism(
        name,
        a_max=p["a_max"],
        k=p["k"],
        r_d=p["r_d"],
        leaf_mass_ratio=p["leaf_mass_ratio"],
        area_ratio=p["area_ratio"],
        t_min=t_min,
        t_opt=float(a["t_opt_k"]),
        emissivity=float(a["emissivity"]),
        albedo=float(a["albedo"]),
    )


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git rev-parse HEAD failed in {REPO_ROOT} "
            f"(exit {proc.returncode}): {proc.stderr.strip() or '<no stderr>'}"
        )
    return proc.stdout.strip()


def provenance_lines(prereg_path: Path) -> list[str]:
    return [
        f"# git_sha={git_sha()}",
        f"# thermal_md5={_md5(THERMAL_PATH)}",
        f"# organism_md5={_md5(ORGANISM_PATH)}",
        f"# physiology_md5={_md5(PHYSIOLOGY_PATH)}",
        f"# prereg_md5={_md5(prereg_path)}",
        f"# python={platform.python_version()}",
        f"# numpy={np.__version__}",
        f"# scipy={scipy.__version__}",
        f"# written={dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]


def write_csv(
    path: Path, header: list[str], fieldnames: list[str], rows: list[dict]
) -> None:
    with open(path, "w", newline="") as fh:
        for line in header:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run_gates(prereg: dict) -> tuple[list[dict], bool]:
    """Gate 1 = thermal physics. Gate 2 = the HELD-OUT response anchors."""
    rows, ok = [], True
    g1 = prereg["gate_thermal"]
    obs = equilibrium_temperature(float(g1["r_au"]), float(g1["area_ratio"]))
    lo, hi = (float(x) for x in g1["t_eq_k"])
    passed = lo <= obs <= hi
    ok &= passed
    rows.append(
        {
            "gate": "thermal",
            "detail": f"T_eq at {g1['r_au']} AU",
            "observed": f"{obs:.4f}",
            "lo": lo,
            "hi": hi,
            "passed": passed,
        }
    )

    g2 = prereg["gate_response"]
    t_min = float(g2["t_min_k"])
    t_opt = float(prereg["assumptions"]["t_opt_k"])
    for anchor in g2["anchors"]:
        t = float(anchor["t_k"])
        obs = temperature_response(t, t_min, t_opt)
        lo, hi = float(anchor["lo"]), float(anchor["hi"])
        passed = lo <= obs <= hi
        ok &= passed
        rows.append(
            {
                "gate": "response",
                "detail": f"f(T={t} K)",
                "observed": f"{obs:.4f}",
                "lo": lo,
                "hi": hi,
                "passed": passed,
            }
        )
    return rows, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prereg", type=Path, default=Path(__file__).with_name("prereg.yaml")
    )
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args(argv)

    prereg = load_prereg(args.prereg)
    assert_assumptions_match(prereg)
    args.out.mkdir(parents=True, exist_ok=True)
    header = provenance_lines(args.prereg)

    gate_rows, all_pass = run_gates(prereg)
    write_csv(
        args.out / "gates.csv",
        header,
        ["gate", "detail", "observed", "lo", "hi", "passed"],
        gate_rows,
    )
    for r in gate_rows:
        print(
            f"gate {r['gate']} {r['detail']}: {r['observed']} "
            f"in [{r['lo']}, {r['hi']}] {'pass' if r['passed'] else 'FAIL'}"
        )
    if not all_pass:
        for stale in ("sweep.csv", "limits.csv"):
            (args.out / stale).unlink(missing_ok=True)
        print("GATE FAILED: limits not reported.")
        print("Do NOT tune t_opt to pass. Report the failure and the implied t_opt.")
        print(f"removed any stale sweep.csv/limits.csv from {args.out}")
        return 2

    a = prereg["assumptions"]
    sw = prereg["sweep"]
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    grid = np.geomspace(r_min, r_max, n_grid)
    sweep_rows, limit_rows = [], []
    for name, p in prereg["presets"].items():
        for t_min in p["t_min_grid"]:
            t_min = float(t_min)
            org = build(name, p, a, t_min)
            for r in grid:
                r = float(r)
                t_eq = equilibrium_temperature(
                    r, org.area_ratio, org.emissivity, org.albedo
                )
                sweep_rows.append(
                    {
                        "class": name,
                        "t_min": t_min,
                        "r_au": f"{r:.6g}",
                        "t_eq": f"{t_eq:.4f}",
                        "response": f"{temperature_response(t_eq, org.t_min, org.t_opt):.6g}",
                        "net_carbon": f"{org.net_carbon_at_equilibrium(r):.6g}",
                    }
                )
            t_1au = equilibrium_temperature(
                1.0, org.area_ratio, org.emissivity, org.albedo
            )
            thermal_au = (t_1au / t_min) ** 2
            try:
                carbon_fixed = crossover_distance_for(
                    org, r_min=r_min, r_max=r_max, n_grid=n_grid
                )
            except ValueError:
                carbon_fixed = float("nan")
            try:
                carbon_eq = crossover_distance(
                    org.net_carbon_at_equilibrium,
                    r_min=r_min,
                    r_max=r_max,
                    n_grid=n_grid,
                )
            except ValueError:
                carbon_eq = float("nan")
            candidates = {
                "temperature": thermal_au,
                "carbon_fixed_t": carbon_fixed,
                "carbon_equilibrium": carbon_eq,
            }
            finite = {k: v for k, v in candidates.items() if np.isfinite(v)}
            binding = min(finite, key=finite.get) if finite else "none_in_window"
            limit_rows.append(
                {
                    "class": name,
                    "t_min": t_min,
                    "thermal_au": f"{thermal_au:.4f}",
                    "carbon_fixed_t_au": f"{carbon_fixed:.4f}",
                    "carbon_equilibrium_au": f"{carbon_eq:.4f}",
                    "binding": binding,
                }
            )
            print(
                f"limits {name} t_min={t_min:g}: thermal={thermal_au:.3f} "
                f"carbon_fixedT={carbon_fixed:.3f} carbon_eq={carbon_eq:.3f} -> {binding}"
            )
    write_csv(
        args.out / "sweep.csv",
        header,
        ["class", "t_min", "r_au", "t_eq", "response", "net_carbon"],
        sweep_rows,
    )
    write_csv(
        args.out / "limits.csv",
        header,
        [
            "class",
            "t_min",
            "thermal_au",
            "carbon_fixed_t_au",
            "carbon_equilibrium_au",
            "binding",
        ],
        limit_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
