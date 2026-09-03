#!/usr/bin/env python3
"""Q2b runner: a global thermal gate, a PER-CLASS adaptation gate, then a
distance sweep of the surviving classes, then provenance-stamped CSVs.

The one change from Q2's conventions: Gate B (the adaptation premise) is
evaluated per class rather than all-or-nothing. A class that fails Gate B is
excluded from the sweep entirely -- no row in sweep.csv or limits.csv -- and
its failure is recorded in gates.csv. See gate_thermal/gate_adaptation below.

Exit codes: 0 = Gate A passed AND at least one class passed Gate B (that
class's rows are written); 2 = Gate A failed OR no class passed Gate B
(gates.csv written, sweep.csv and limits.csv removed/absent). Anything else
propagates as an exception.
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
from scipy.optimize import brentq

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from experiments.q2b_adapted.reachability import gate_b_verdict, sign_structure  # noqa: E402
from sim import physiology, thermal  # noqa: E402
from sim.organism import Organism, crossover_distance_for  # noqa: E402
from sim.thermal import adapted_optimum, equilibrium_temperature  # noqa: E402
from sim.thermal import temperature_response_gaussian  # noqa: E402

THERMAL_PATH = REPO_ROOT / "sim" / "thermal.py"
ORGANISM_PATH = REPO_ROOT / "sim" / "organism.py"
PHYSIOLOGY_PATH = REPO_ROOT / "sim" / "physiology.py"


def load_prereg(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def assert_assumptions_match(prereg: dict) -> None:
    """The physical constants a prereg declares must match the code that will
    actually run -- otherwise a drifted constant produces a result that looks
    registered but was not the one the code computed."""
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


def build(name: str, p: dict, a: dict, omega: float) -> Organism:
    """Build an Organism from the PREREG's presets block -- never from
    sim.organism.ALGAL/VASCULAR. The prereg registers algal
    leaf_mass_ratio=1.0 (the grounded unicellular value); the live ALGAL
    preset in sim/organism.py is still 0.8, frozen because it feeds Q1's
    committed numbers. Importing the module preset here would silently
    compute the wrong, unregistered number."""
    r_home_au = float(a["r_home_au"])
    emissivity = float(a["emissivity"])
    albedo = float(a["albedo"])
    t_opt = adapted_optimum(r_home_au, float(p["area_ratio"]), emissivity, albedo)
    return Organism(
        name,
        a_max=float(p["a_max"]),
        k=float(p["k"]),
        r_d=float(p["r_d"]),
        leaf_mass_ratio=float(p["leaf_mass_ratio"]),
        area_ratio=float(p["area_ratio"]),
        t_min=float(p["t_min"]),
        t_opt=t_opt,
        emissivity=emissivity,
        albedo=albedo,
        omega=float(omega),
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


def run_gate_a(prereg: dict) -> tuple[dict, bool]:
    g = prereg["gate_thermal"]
    obs = equilibrium_temperature(float(g["r_au"]), float(g["area_ratio"]))
    lo, hi = (float(x) for x in g["t_eq_k"])
    passed = lo <= obs <= hi
    return {
        "gate": "thermal",
        "cls": "-",
        "detail": f"T_eq at {g['r_au']} AU",
        "observed": f"{obs:.4f}",
        "lo": lo,
        "hi": hi,
        "passed": passed,
    }, passed


def run_gate_b(prereg: dict) -> tuple[list[dict], set]:
    """Per class. Returns (rows, set of class names that PASSED).

    PARAMETER-FREE: the model predicts t_opt from geometry alone, and the
    prediction is compared against the measured optimum. A class that fails
    is excluded from the sweep entirely (handled by the caller); its
    failure is still recorded here so it is disclosed, not silenced."""
    rows, passing = [], set()
    hw = float(prereg["assumptions"]["gate_b_half_width_k"])
    for cls, g in prereg["gate_adaptation"].items():
        p = prereg["presets"][cls]
        pred = adapted_optimum(
            float(prereg["assumptions"]["r_home_au"]),
            float(p["area_ratio"]),
            float(prereg["assumptions"]["emissivity"]),
            float(prereg["assumptions"]["albedo"]),
        )
        ok, lo, hi = gate_b_verdict(pred, [float(x) for x in g["measured_c"]], hw)
        if ok:
            passing.add(cls)
        rows.append(
            {
                "gate": "adaptation",
                "cls": cls,
                "detail": "predicted t_opt (C)",
                "observed": f"{pred - 273.15:.4f}",
                "lo": lo,
                "hi": hi,
                "passed": ok,
            }
        )
    return rows, passing


class UnexpectedSignStructure(ValueError):
    """The net_carbon_adapted curve did not have a shape this selector
    recognizes from Task 3's Step 5 measurement -- either no sign change at
    all (a legitimate, disclosed non-crossing outcome, NOT this exception),
    or exactly one negative->positive transition followed by exactly one
    positive->negative transition (the two-root shape, also legitimate).
    Anything else means the measured shape this selector rests on does not
    hold for these parameters, and must NOT be swallowed into NaN -- that
    would silently misreport (or entirely hide) which root is the outer
    limit. See experiments.q2_thermal.run.UnexpectedSignStructure, the
    pattern this mirrors."""


def outer_carbon_crossover(net_fn, r_min: float, r_max: float, n_grid: int) -> float:
    """Outermost distance where net_carbon_adapted crosses zero, or NaN if
    the curve never crosses at all on the registered window.

    Task 3 measured the sign structure BEFORE this runner was written
    (prereg.yaml curve_shape): algal is [(-1, 1), (1, -1)] at every Ω, but
    vascular is [] (no sign change anywhere on [0.5, 100] AU, including its
    own home distance) at Ω in {10, 15, 20}. An empty transition list is
    therefore a legitimate, disclosed outcome -- "no crossover distance
    exists" -- and is returned as NaN rather than raised. Any OTHER shape
    (not [] and not exactly the two-root pattern) is not one Task 3
    measured, and picking a root anyway would be a guess dressed up as a
    result, so it raises UnexpectedSignStructure instead.
    """
    if r_min <= 0 or r_max <= r_min:
        raise ValueError(f"need 0 < r_min < r_max, got {r_min}, {r_max}")
    transitions = sign_structure(net_fn, r_min, r_max, n_grid)
    if transitions == []:
        return float("nan")
    if transitions != [(-1, 1), (1, -1)]:
        raise UnexpectedSignStructure(
            "unexpected sign structure for net_carbon_adapted on "
            f"[{r_min}, {r_max}] AU: expected [] (no crossing) or exactly "
            "one negative->positive transition (hot inner edge) followed by "
            f"exactly one positive->negative transition (outer limit); got "
            f"{transitions}"
        )
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    i = idx[-1]
    return float(brentq(net_fn, grid[i], grid[i + 1], xtol=1e-6))


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

    a_row, a_passed = run_gate_a(prereg)
    b_rows, passing = run_gate_b(prereg)
    gate_rows = [a_row, *b_rows]
    write_csv(
        args.out / "gates.csv",
        header,
        ["gate", "cls", "detail", "observed", "lo", "hi", "passed"],
        gate_rows,
    )
    for r in gate_rows:
        print(
            f"gate {r['gate']} [{r['cls']}] {r['detail']}: {r['observed']} "
            f"in [{r['lo']}, {r['hi']}] {'pass' if r['passed'] else 'FAIL'}"
        )

    if not a_passed or not passing:
        for stale in ("sweep.csv", "limits.csv"):
            (args.out / stale).unlink(missing_ok=True)
        print("GATE FAILED: no limits reported.")
        print("Do NOT adjust emissivity, albedo or a gate window to pass.")
        print(f"removed any stale sweep.csv/limits.csv from {args.out}")
        return 2

    a = prereg["assumptions"]
    r_home_au = float(a["r_home_au"])
    sw = prereg["sweep"]
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    grid = np.geomspace(r_min, r_max, n_grid)

    sweep_rows, limit_rows = [], []
    for name, p in prereg["presets"].items():
        if name not in passing:
            continue
        for omega in prereg["omega_grid_k"]:
            omega = float(omega)
            org = build(name, p, a, omega)
            t_opt_home = adapted_optimum(
                r_home_au, org.area_ratio, org.emissivity, org.albedo
            )
            for r in grid:
                r = float(r)
                t_eq = equilibrium_temperature(
                    r, org.area_ratio, org.emissivity, org.albedo
                )
                response = temperature_response_gaussian(t_eq, t_opt_home, omega)
                sweep_rows.append(
                    {
                        "class": name,
                        "omega": f"{omega:g}",
                        "r_au": f"{r:.6g}",
                        "t_eq": f"{t_eq:.4f}",
                        "response": f"{response:.6g}",
                        "net_carbon": f"{org.net_carbon_adapted(r, r_home_au):.6g}",
                    }
                )

            # Three single-mechanism distances classify which of light,
            # carbon, or temperature binds -- mirroring Q2's
            # temperature/carbon_fixed_t/carbon_equilibrium min() pattern,
            # relabeled to the registered question's own wording. "carbon"
            # is the actual coupled model (net_carbon_adapted, both light
            # dilution and the Gaussian thermal response) and is the number
            # reported as outer_au; "temperature" and "light" are
            # counterfactual single-mechanism distances used only to decide
            # which constraint is tightest.
            t_home = equilibrium_temperature(
                r_home_au, org.area_ratio, org.emissivity, org.albedo
            )
            thermal_au = r_home_au * (t_home / org.t_min) ** 2
            try:
                light_au = crossover_distance_for(
                    org, r_min=r_min, r_max=r_max, n_grid=n_grid
                )
            except ValueError:
                light_au = float("nan")
            try:
                carbon_au = outer_carbon_crossover(
                    lambda r, org=org: org.net_carbon_adapted(r, r_home_au),
                    r_min=r_min,
                    r_max=r_max,
                    n_grid=n_grid,
                )
            except UnexpectedSignStructure:
                # Must NOT become NaN: see the class docstring above.
                raise
            candidates = {
                "temperature": thermal_au,
                "light": light_au,
                "carbon": carbon_au,
            }
            finite = {k: v for k, v in candidates.items() if np.isfinite(v)}
            binding = min(finite, key=finite.get) if finite else "none_in_window"
            limit_rows.append(
                {
                    "class": name,
                    "omega": f"{omega:g}",
                    "outer_au": f"{carbon_au:.4f}" if np.isfinite(carbon_au) else "nan",
                    "binding": binding,
                }
            )
            print(
                f"limits {name} omega={omega:g}: temperature={thermal_au:.3f} "
                f"light={light_au:.3f} carbon={carbon_au:.3f} -> {binding}"
            )

    write_csv(
        args.out / "sweep.csv",
        header,
        ["class", "omega", "r_au", "t_eq", "response", "net_carbon"],
        sweep_rows,
    )
    write_csv(
        args.out / "limits.csv",
        header,
        ["class", "omega", "outer_au", "binding"],
        limit_rows,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
