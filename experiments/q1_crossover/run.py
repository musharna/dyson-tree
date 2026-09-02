#!/usr/bin/env python3
"""Q1 runner: calibration gate, then distance sweep, then provenance-stamped CSVs.

Exit codes: 0 = gate passed and sweep written; 2 = gate failed (calibration.csv
written, nothing else). Any other error propagates as an exception.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import physiology  # noqa: E402
from sim.organism import Organism, compensation_irradiance, crossover_distance_for  # noqa: E402

PHYSIOLOGY_PATH = REPO_ROOT / "sim" / "physiology.py"
ORGANISM_PATH = REPO_ROOT / "sim" / "organism.py"


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
    }
    for key, code_value in pairs.items():
        if not np.isclose(a[key], code_value):
            raise ValueError(
                f"prereg assumption {key}={a[key]} does not match sim/physiology.py {key}={code_value}"
            )


def build(name: str, p: dict, t_set: float) -> Organism:
    return Organism(name, a_max=p["a_max"], k=p["k"], r_d=p["r_d"],
                    leaf_mass_ratio=p["leaf_mass_ratio"], t_set=t_set)


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def provenance_lines(prereg_path: Path) -> list[str]:
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
                         capture_output=True, text=True).stdout.strip()
    return [
        f"# git_sha={sha}",
        f"# physiology_md5={_md5(PHYSIOLOGY_PATH)}",
        f"# organism_md5={_md5(ORGANISM_PATH)}",
        f"# prereg_md5={_md5(prereg_path)}",
        f"# written={dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]


def write_csv(path: Path, header: list[str], fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as fh:
        for line in header:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prereg", type=Path, default=Path(__file__).with_name("prereg.yaml"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args(argv)

    prereg = load_prereg(args.prereg)
    assert_assumptions_match(prereg)
    t_set = float(prereg["assumptions"]["t_set_k"])
    args.out.mkdir(parents=True, exist_ok=True)
    header = provenance_lines(args.prereg)

    # 1. calibration gate at default k
    cal_rows, all_pass = [], True
    orgs: dict[str, Organism] = {}
    for name, p in prereg["presets"].items():
        org = build(name, p, t_set)
        orgs[name] = org
        obs = compensation_irradiance(org)
        lo, hi = (float(x) for x in p["gate_umol"])
        passed = lo <= obs <= hi
        all_pass &= passed
        cal_rows.append({"class": name, "k": org.k, "observed_umol": f"{obs:.4f}",
                         "gate_lo": lo, "gate_hi": hi, "passed": passed})
    write_csv(args.out / "calibration.csv", header,
              ["class", "k", "observed_umol", "gate_lo", "gate_hi", "passed"], cal_rows)
    for r in cal_rows:
        print(f"calibration {r['class']}: I_c={r['observed_umol']} gate=[{r['gate_lo']}, {r['gate_hi']}] "
              f"{'pass' if r['passed'] else 'FAIL'}")
    if not all_pass:
        print("GATE FAILED: crossover not reported. Fix r_d only, re-register, re-run.")
        return 2

    # 2. sweep
    sw = prereg["sweep"]
    grid = np.geomspace(float(sw["r_min_au"]), float(sw["r_max_au"]), int(sw["n_grid"]))
    sweep_rows, cross_rows = [], []
    for name, p in prereg["presets"].items():
        org = orgs[name]
        plo, phi = (float(x) for x in p["predicted_r_star_au"])
        for k in p["k_grid"]:
            k = float(k)
            for r in grid:
                sweep_rows.append({"class": name, "k": k, "r_au": f"{r:.6g}",
                                   "net_carbon": f"{org.net_carbon(float(r), k=k):.6g}"})
            r_star = crossover_distance_for(org, k=k, r_min=float(sw["r_min_au"]), r_max=float(sw["r_max_au"]))
            inside = plo <= r_star <= phi
            cross_rows.append({"class": name, "k": k, "r_star_au": f"{r_star:.4f}",
                               "pred_lo": plo, "pred_hi": phi, "inside": inside})
            print(f"crossover {name} k={k:g}: r*={r_star:.2f} AU predicted=[{plo:g}, {phi:g}] "
                  f"{'inside' if inside else 'OUTSIDE'}")
    write_csv(args.out / "sweep.csv", header, ["class", "k", "r_au", "net_carbon"], sweep_rows)
    write_csv(args.out / "crossover.csv", header,
              ["class", "k", "r_star_au", "pred_lo", "pred_hi", "inside"], cross_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
