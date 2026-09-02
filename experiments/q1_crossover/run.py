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
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import physiology  # noqa: E402
from sim.organism import (  # noqa: E402
    PRESETS,
    Organism,
    compensation_irradiance,
    crossover_distance_for,
)

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


# Organism fields the prereg and sim/organism.py must agree on. gate_umol,
# k_grid and predicted_r_star_au are experiment design and have no module
# counterpart, so they are not compared here.
PRESET_FIELDS = ("a_max", "k", "r_d", "leaf_mass_ratio")


def assert_presets_match(prereg: dict) -> None:
    """The runner builds organisms from prereg['presets'] while the calibration
    tests gate sim.organism.PRESETS. Two sources of truth for the same numbers;
    this is what makes them one. A prereg r_d could otherwise drift anywhere
    inside the gate's width with a green suite and a different published r*."""
    p_presets = prereg["presets"]
    if set(p_presets) != set(PRESETS):
        raise ValueError(
            f"prereg presets {sorted(p_presets)} do not match "
            f"sim/organism.py PRESETS {sorted(PRESETS)}"
        )
    t_set = float(prereg["assumptions"]["t_set_k"])
    for name, p in p_presets.items():
        preset = PRESETS[name]
        for field in PRESET_FIELDS:
            if not np.isclose(float(p[field]), getattr(preset, field)):
                raise ValueError(
                    f"prereg preset {name}.{field}={p[field]} does not match "
                    f"sim/organism.py PRESETS[{name!r}].{field}={getattr(preset, field)}"
                )
        if not np.isclose(t_set, preset.t_set):
            raise ValueError(
                f"prereg assumption t_set_k={t_set} does not match "
                f"sim/organism.py PRESETS[{name!r}].t_set={preset.t_set}"
            )


def build(name: str, p: dict, t_set: float) -> Organism:
    return Organism(
        name,
        a_max=p["a_max"],
        k=p["k"],
        r_d=p["r_d"],
        leaf_mass_ratio=p["leaf_mass_ratio"],
        t_set=t_set,
    )


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def git_sha() -> str:
    """HEAD sha, or a loud error carrying git's own stderr. check=True alone
    raises a CalledProcessError whose message is only the exit status."""
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
    """Source hashes alone are not enough: r* comes out of scipy's brentq on a
    numpy grid, so a numeric-stack upgrade can move the number while every md5
    and the git sha stay byte-identical. Record the stack too."""
    sha = git_sha()
    return [
        f"# git_sha={sha}",
        f"# physiology_md5={_md5(PHYSIOLOGY_PATH)}",
        f"# organism_md5={_md5(ORGANISM_PATH)}",
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--prereg", type=Path, default=Path(__file__).with_name("prereg.yaml")
    )
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args(argv)

    prereg = load_prereg(args.prereg)
    assert_assumptions_match(prereg)
    assert_presets_match(prereg)
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
        cal_rows.append(
            {
                "class": name,
                "k": org.k,
                "observed_umol": f"{obs:.4f}",
                "gate_lo": lo,
                "gate_hi": hi,
                "passed": passed,
            }
        )
    write_csv(
        args.out / "calibration.csv",
        header,
        ["class", "k", "observed_umol", "gate_lo", "gate_hi", "passed"],
        cal_rows,
    )
    for r in cal_rows:
        print(
            f"calibration {r['class']}: I_c={r['observed_umol']} gate=[{r['gate_lo']}, {r['gate_hi']}] "
            f"{'pass' if r['passed'] else 'FAIL'}"
        )
    if not all_pass:
        # Not-writing is not enough: --out defaults to the experiment directory,
        # so a previous PASSING run's crossover.csv/sweep.csv are already sitting
        # there and would be read as this run's result under a stale header.
        for stale in ("sweep.csv", "crossover.csv"):
            (args.out / stale).unlink(missing_ok=True)
        print("GATE FAILED: crossover not reported. Fix r_d only, re-register, re-run.")
        print(f"removed any stale sweep.csv/crossover.csv from {args.out}")
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
                sweep_rows.append(
                    {
                        "class": name,
                        "k": k,
                        "r_au": f"{r:.6g}",
                        "net_carbon": f"{org.net_carbon(float(r), k=k):.6g}",
                    }
                )
            r_star = crossover_distance_for(
                org,
                k=k,
                r_min=float(sw["r_min_au"]),
                r_max=float(sw["r_max_au"]),
                n_grid=int(sw["n_grid"]),
            )
            inside = plo <= r_star <= phi
            cross_rows.append(
                {
                    "class": name,
                    "k": k,
                    "r_star_au": f"{r_star:.4f}",
                    "pred_lo": plo,
                    "pred_hi": phi,
                    "inside": inside,
                }
            )
            print(
                f"crossover {name} k={k:g}: r*={r_star:.2f} AU predicted=[{plo:g}, {phi:g}] "
                f"{'inside' if inside else 'OUTSIDE'}"
            )
    write_csv(
        args.out / "sweep.csv", header, ["class", "k", "r_au", "net_carbon"], sweep_rows
    )
    write_csv(
        args.out / "crossover.csv",
        header,
        ["class", "k", "r_star_au", "pred_lo", "pred_hi", "inside"],
        cross_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
