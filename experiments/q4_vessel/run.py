#!/usr/bin/env python3
"""Q4 runner (northstar M4): gates A and C, then the registered grid, then the edges.

Authority: experiments/q4_vessel/prereg.yaml (frozen, md5 d8707a66...) and spec §6.
This file reads the prereg; it never writes it and never adjusts a band, grid, tolerance
or edge rule. It imports sim/vessel.py (and the sim modules vessel itself uses), never
sim/deck.py or tools/.

Exit codes: 0 = gates passed, sweep and edges written; 2 = a gate failed, or an auto-path
BURST/BOIL violation (a runner error, §4), or the prereg does not match the code's
constants -- in every exit-2 case NOTHING is written and stale outputs are removed.

Outputs (all with the same provenance header): sweep.csv (the registered 197 x 101 x 3
grid under the registered law), edges.csv (P1 per sigma, P2, the control law, the
`central` variant, the f_floor arms and every Fresnel-arm row, each beside the prereg's
expected value), RESULTS.md (verdicts).

Comparison rule against the prereg's expected rows, fixed BEFORE the run: `delta` =
measured - expected; `within_tol` = |delta| <= the prereg's edge tolerance (edge_r_au, or
edge_R_rel x expected); `matches_printed` = measured rounded to the digits the prereg
prints (4 dp AU, 0.1 km) equals the printed value. Both are reported; neither moves a
verdict. Verdicts on P1/P2 read the measured edge against the band, unrounded, inclusive.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import math
import platform
import subprocess
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import vessel as V  # noqa: E402
from sim.organism import ALGAL  # noqa: E402
from sim.thermal import equilibrium_temperature  # noqa: E402

HERE = Path(__file__).resolve().parent
PREREG_MD5_PREFIX = "d8707a66"
MAX_WORKERS = 3
OUTPUTS = ("sweep.csv", "edges.csv", "RESULTS.md")
CODE_PATHS = {
    "vessel_md5": REPO_ROOT / "sim" / "vessel.py",
    "physiology_md5": REPO_ROOT / "sim" / "physiology.py",
    "thermal_md5": REPO_ROOT / "sim" / "thermal.py",
    "organism_md5": REPO_ROOT / "sim" / "organism.py",
    "run_md5": Path(__file__).resolve(),
}


class PreregMismatch(RuntimeError):
    pass


# ---------------------------------------------------------------- provenance
def md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def table_sha256() -> str:
    data = "".join(
        ln
        for ln in V.TABLE_PATH.read_text().splitlines(keepends=True)
        if not ln.startswith("#")
    )
    return hashlib.sha256(data.encode()).hexdigest()


def git(*args) -> str:
    proc = subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"git {' '.join(args)} failed (exit {proc.returncode}): "
            f"{proc.stderr.strip() or '<no stderr>'}"
        )
    return proc.stdout.strip()


def provenance_lines(prereg_path: Path) -> list[str]:
    import scipy

    lines = [f"# git_sha={git('rev-parse', 'HEAD')}"]
    dirty = git(
        "status",
        "--porcelain",
        "--",
        "sim",
        "experiments/q4_vessel/run.py",
        "experiments/q4_vessel/prereg.yaml",
    )
    lines.append(f"# code_dirty={'yes' if dirty else 'no'}")
    lines.append(f"# prereg_md5={md5(prereg_path)}")
    lines.append(f"# spectral_table_sha256={table_sha256()}")
    for key, path in CODE_PATHS.items():
        lines.append(f"# {key}={md5(path)}")
    lines += [
        f"# python={platform.python_version()}",
        f"# numpy={np.__version__}",
        f"# scipy={scipy.__version__}",
        f"# written={dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]
    return lines


# ---------------------------------------------------------------- prereg vs code
def registered_grids(prereg: dict):
    g = prereg["grids"]
    r = g["r_au"]
    r_nodes = np.round(
        np.arange(float(r["start"]), float(r["stop"]) + 1e-9, float(r["step"])), 2
    )
    R = g["R_m"]
    decades = math.log10(float(R["stop"])) - math.log10(float(R["start"]))
    R_nodes = np.logspace(
        math.log10(float(R["start"])),
        math.log10(float(R["stop"])),
        int(round(decades * int(R["per_decade"]))) + 1,
    )
    if len(r_nodes) != int(r["nodes"]) or len(R_nodes) != int(R["nodes"]):
        raise PreregMismatch(
            f"grid node counts {len(r_nodes)}/{len(R_nodes)} != prereg "
            f"{r['nodes']}/{R['nodes']}"
        )
    sig = [float(s) * 1e6 for s in g["sigma_MPa"]]
    return r_nodes, R_nodes, sig


def assert_prereg_matches_code(prereg: dict, prereg_path: Path) -> None:
    """The runner uses sim/vessel.py's constants; each must equal the prereg's."""
    got = md5(prereg_path)
    if not got.startswith(PREREG_MD5_PREFIX):
        raise PreregMismatch(
            f"prereg md5 {got} is not the registered {PREREG_MD5_PREFIX}..."
        )
    r_nodes, R_nodes, sig = registered_grids(prereg)
    if not np.array_equal(r_nodes, V.GRID_R_AU):
        raise PreregMismatch("prereg r grid != sim.vessel.GRID_R_AU")
    if not np.allclose(R_nodes, V.GRID_R_M, rtol=1e-12, atol=0):
        raise PreregMismatch("prereg R grid != sim.vessel.GRID_R_M")
    if tuple(sig) != tuple(V.SIGMAS_PA):
        raise PreregMismatch(f"prereg sigmas {sig} != sim.vessel.SIGMAS_PA")
    tol = prereg["tolerances"]
    pairs = {
        "edge_r_au": V.EDGE_TOL_R_AU,
        "edge_R_rel": V.EDGE_TOL_R_REL,
        "burst_boil_rel": V.EPS_BURST_BOIL_REL,
        "freeze_K": V.EPS_FREEZE_K,
        "starve_opaque_abs": V.EPS_STARVE_OPAQUE,
        "fixed_point_dp_Pa": V.FIXED_POINT_DP_PA,
    }
    for k, v in pairs.items():
        if float(tol[k]) != v:
            raise PreregMismatch(f"tolerance {k}: prereg {tol[k]} != code {v}")
    if tuple(prereg["load_order"]) != V.LOAD_ORDER:
        raise PreregMismatch("load order differs")
    if tuple(prereg["binding_lines"]) != V.BINDING_LINES:
        raise PreregMismatch("binding lines differ")
    reg = prereg["registry"]
    R0 = V.REGISTERED
    checks = {
        "t_opt_K": R0.t_opt_K,
        "omega_K": R0.omega_K,
        "albedo": R0.albedo,
        "emissivity": R0.emissivity,
        "f_floor": R0.f_floor,
        "n": R0.n,
        "T_freeze_K": R0.T_freeze_K,
    }
    for k, v in checks.items():
        if float(reg[k]) != v:
            raise PreregMismatch(f"registry {k}: prereg {reg[k]} != code {v}")
    for k in (
        "interior",
        "shell_temperature",
        "dust",
        "optical_law",
        "solar_tail_transmission",
    ):
        if str(reg[k]) != str(getattr(R0, k)):
            raise PreregMismatch(
                f"registry {k}: prereg {reg[k]} != code {getattr(R0, k)}"
            )
    if float(reg["n_interior"][reg["n_interior"]["default"]]) != R0.n_interior:
        raise PreregMismatch("registry n_interior default differs")
    if str(reg["thermal_reflectance"]["registered"]) != R0.thermal_reflectance:
        raise PreregMismatch("registry thermal_reflectance differs")
    st = prereg["spectral_table"]
    if table_sha256() != st["data_sha256"]:
        raise PreregMismatch("spectral table sha256 != prereg data_sha256")
    if len(V.LAMBDA_NM) != int(st["rows"]):
        raise PreregMismatch("spectral table row count differs")


# ---------------------------------------------------------------- gates
def gates(prereg: dict) -> list[dict]:
    tol = prereg["tolerances"]
    t_eq = equilibrium_temperature(1.0, V.SPHERE_AREA_RATIO)
    p_tp = V.saturation_pressure(273.16)
    p_reg = V.saturation_pressure(273.15 + 5.16)
    return [
        {
            "gate": "A",
            "quantity": "T_eq(1 AU, sphere) K",
            "value": t_eq,
            "target": "[275, 282]",
            "passed": 275.0 <= t_eq <= 282.0,
        },
        {
            "gate": "C",
            "quantity": "p_sat(273.16 K) Pa",
            "value": p_tp,
            "target": f"611.657 +- {tol['gate_C_triple_point_Pa']}",
            "passed": abs(p_tp - 611.657) <= float(tol["gate_C_triple_point_Pa"]),
        },
        {
            "gate": "C",
            "quantity": "p_sat(5.16 C) Pa (regression)",
            "value": p_reg,
            "target": f"882 +- {tol['gate_C_regression_Pa']}",
            "passed": abs(p_reg - 882.0) <= float(tol["gate_C_regression_Pa"]),
        },
    ]


# ---------------------------------------------------------------- the sweep
def _sweep_sigma(args):
    sigma, r_nodes, R_nodes = args
    rows = []
    for r in r_nodes:
        p0 = None
        for R in R_nodes:
            p, t, rep = V.auto_state(float(r), float(R), sigma, ALGAL, p0=p0)
            p0 = p
            if rep.first in ("BURST", "BOIL"):
                raise V.RunnerError(
                    f"auto path names {rep.first} at r={r} R={R} sigma={sigma}"
                )
            L = rep.lines
            rows.append(
                {
                    "sigma_MPa": f"{sigma / 1e6:g}",
                    "r_au": f"{r:.2f}",
                    "R_m": f"{R:.6g}",
                    "p_star_Pa": f"{p:.6f}",
                    "t_m": f"{t:.6g}",
                    "T_int_K": f"{rep.T_int:.6f}",
                    "T_shell_K": f"{rep.T_shell:.6f}",
                    "f_photon": f"{rep.f_photon:.6g}",
                    "margin_BURST_Pa": f"{L['BURST'].margin:.6g}",
                    "margin_FREEZE_K": f"{L['FREEZE'].margin:.6g}",
                    "margin_BOIL_Pa": f"{L['BOIL'].margin:.6g}",
                    "margin_STARVE_umol": f"{L['STARVE'].margin:.6g}",
                    "margin_OPAQUE": f"{L['OPAQUE'].margin:.6g}",
                    "first_violated": rep.first or "HELD",
                }
            )
    return rows


SWEEP_FIELDS = [
    "sigma_MPa",
    "r_au",
    "R_m",
    "p_star_Pa",
    "t_m",
    "T_int_K",
    "T_shell_K",
    "f_photon",
    "margin_BURST_Pa",
    "margin_FREEZE_K",
    "margin_BOIL_Pa",
    "margin_STARVE_umol",
    "margin_OPAQUE",
    "first_violated",
]


# ---------------------------------------------------------------- the edges
EDGE_FIELDS = [
    "row",
    "prediction",
    "config",
    "optical_law",
    "n_interior",
    "thermal_reflectance",
    "interior",
    "f_floor",
    "sigma_MPa",
    "fixed",
    "quantity",
    "line",
    "unit",
    "measured",
    "expected",
    "delta",
    "tolerance",
    "within_tol",
    "matches_printed",
    "binding",
    "expected_binding",
    "binding_ok",
    "tie",
    "bracket_lo",
    "bracket_hi",
    "roots",
    "counterfactual",
    "starve_margin_at_edge",
    "band_lo",
    "band_hi",
    "in_band",
]


def _inputs(cfg: dict) -> V.VesselInputs:
    return V.VesselInputs(**cfg)


def _line_root(edge: V.Edge, line: str):
    if line in edge.roots:
        return edge.roots[line]
    return edge.counterfactual.get(line, float("nan"))


def _fmt_map(d, scale, dp):
    return ";".join(f"{k}={v / scale:.{dp}f}" for k, v in d.items())


def compute_edges(prereg: dict, r_nodes, R_nodes, sigmas):
    tol = prereg["tolerances"]
    tol_r = float(tol["edge_r_au"])
    tol_R = float(tol["edge_R_rel"])
    P1, P2 = prereg["predictions"]["P1"], prereg["predictions"]["P2"]
    R_fix = float(P1["fixed"]["R_km"]) * 1e3
    r_fix = float(P2["fixed"]["r_au"])
    sig_p2 = float(P2["fixed"]["sigma_MPa"]) * 1e6
    p1_lo, p1_hi = (float(x) for x in P1["band_au"])
    p2_lo, p2_hi = (float(x) for x in P2["band_km"])
    rows = []

    def base(row, pred, config, cfg, sigma, fixed):
        inp = _inputs(cfg)
        return {
            "row": row,
            "prediction": pred,
            "config": config,
            "optical_law": inp.optical_law,
            "n_interior": f"{inp.n_interior:.3f}",
            "thermal_reflectance": inp.thermal_reflectance,
            "interior": inp.interior,
            "f_floor": f"{inp.f_floor:g}",
            "sigma_MPa": f"{sigma / 1e6:g}",
            "fixed": fixed,
        }

    def compare(rec, measured, expected, unit):
        rec["measured"] = f"{measured:.6f}" if unit == "AU" else f"{measured / 1e3:.4f}"
        if expected is None:
            for k in (
                "expected",
                "delta",
                "tolerance",
                "within_tol",
                "matches_printed",
            ):
                rec[k] = ""
            return
        m = measured if unit == "AU" else measured / 1e3
        t = tol_r if unit == "AU" else tol_R * expected
        dp = 4 if unit == "AU" else 1
        rec["expected"] = f"{expected:.{dp}f}"
        rec["delta"] = f"{m - expected:+.6f}"
        rec["tolerance"] = f"{t:.6g}"
        rec["within_tol"] = bool(abs(m - expected) <= t) if math.isfinite(m) else False
        rec["matches_printed"] = (
            bool(round(m, dp) == round(expected, dp)) if math.isfinite(m) else False
        )

    def edge_meta(rec, e, scale, dp, starve):
        rec["tie"] = e.tie
        rec["bracket_lo"] = (
            "" if e.bracket is None else f"{e.bracket[0] / scale:.{dp}f}"
        )
        rec["bracket_hi"] = (
            "" if e.bracket is None else f"{e.bracket[1] / scale:.{dp}f}"
        )
        rec["roots"] = _fmt_map(e.roots, scale, dp + 2)
        rec["counterfactual"] = _fmt_map(e.counterfactual, scale, dp + 2)
        rec["starve_margin_at_edge"] = "" if starve is None else f"{starve:.4f}"

    def starve_at(r, R, sigma, inp):
        return V.auto_state(r, R, sigma, ALGAL, inp)[2].lines["STARVE"].margin

    # ---- P1-shaped rows: edge in r at R = 10 km, per sigma
    p1_cfgs = [
        (
            "P1",
            "registered",
            {},
            prereg["registered_rows"]["P1_edge_au"],
            "FREEZE",
            True,
        ),
        (
            "P1.control",
            "control normal",
            {"optical_law": prereg["control"]["optical_law"]},
            prereg["control"]["P1_edge_au"],
            None,
            False,
        ),
    ]
    for i, arm in enumerate(prereg["fresnel_arm"]):
        if arm["prediction"] != "P1":
            continue
        cfg = {
            "optical_law": arm["optical_law"],
            "n_interior": float(arm["n_interior"]),
            "thermal_reflectance": str(arm["thermal_reflectance"]),
        }
        name = f"arm {'(i)' if cfg['thermal_reflectance'] == '0' else '(ii)'} n_int {cfg['n_interior']:.3f}"
        p1_cfgs.append((f"P1.arm{i}", name, cfg, arm["edge_au"], arm["binding"], False))
    for row, config, cfg, expected, exp_bind, registered in p1_cfgs:
        inp = _inputs(cfg)
        for sigma, exp_edge in zip(sigmas, expected):
            e = V.r_close(R_fix, sigma, ALGAL, inp, nodes=r_nodes)
            rec = base(row, "P1", config, cfg, sigma, f"R={R_fix / 1e3:g} km")
            rec.update(
                quantity="r_close",
                line=e.binding or "",
                unit="AU",
                binding=e.binding or "EMPTY",
                expected_binding=exp_bind or P1["binding"],
            )
            compare(rec, e.edge, float(exp_edge), "AU")
            rec["binding_ok"] = rec["binding"] == rec["expected_binding"]
            edge_meta(
                rec,
                e,
                1.0,
                4,
                starve_at(e.edge, R_fix, sigma, inp) if e.binding else None,
            )
            rec["band_lo"], rec["band_hi"] = p1_lo, p1_hi
            rec["in_band"] = p1_lo <= e.edge <= p1_hi
            rows.append(rec)

    # ---- P2-shaped rows: window in R at r = 1.10 AU, sigma 0.7
    ctl = prereg["control"]["P2"]
    reg = prereg["registered_rows"]["P2"]
    var = prereg["variants"]
    ff = var["P2_f_floor_arms"]
    # (row, config, cfg, expected R_window km, expected binding, {line: expected km})
    p2_cfgs = [
        (
            "P2",
            "registered",
            {},
            reg["R_km"],
            reg["binding"],
            {"FREEZE": reg["FREEZE_km"]},
        ),
        (
            "P2.control",
            "control normal",
            {"optical_law": prereg["control"]["optical_law"]},
            ctl["R_km"],
            ctl["binding"],
            {"FREEZE": ctl["FREEZE_km"]},
        ),
        (
            "P2.central",
            "variant interior central",
            {"interior": "central"},
            var["interior_central"]["P2_R_km"],
            None,
            {},
        ),
        (
            "P2.ffloor0.50",
            "f_floor 0.50",
            {"f_floor": 0.50},
            None,
            None,
            {"OPAQUE": ff["0.50"]["OPAQUE_km"]},
        ),
        (
            "P2.ffloor0.10",
            "f_floor 0.10",
            {"f_floor": 0.10},
            ff["0.10"]["R_window_km"],
            ff["0.10"]["binding"],
            {"OPAQUE": ff["0.10"]["OPAQUE_km"]},
        ),
    ]
    for i, arm in enumerate(prereg["fresnel_arm"]):
        if arm["prediction"] != "P2":
            continue
        cfg = {
            "optical_law": arm["optical_law"],
            "n_interior": float(arm["n_interior"]),
            "thermal_reflectance": str(arm["thermal_reflectance"]),
        }
        name = f"arm {'(i)' if cfg['thermal_reflectance'] == '0' else '(ii)'} n_int {cfg['n_interior']:.3f}"
        other = "FREEZE" if arm["binding"] == "OPAQUE" else "OPAQUE"
        p2_cfgs.append(
            (
                f"P2.arm{i}",
                name,
                cfg,
                arm["R_window_km"],
                arm["binding"],
                {other: arm["other_km"]},
            )
        )
    for row, config, cfg, exp_R, exp_bind, others in p2_cfgs:
        inp = _inputs(cfg)
        e = V.r_window(r_fix, sig_p2, ALGAL, inp, nodes=R_nodes)
        starve = starve_at(r_fix, e.edge, sig_p2, inp) if e.binding else None
        rec = base(row, "P2", config, cfg, sig_p2, f"r={r_fix:g} AU")
        rec.update(
            quantity="R_window",
            line=e.binding or "",
            unit="km",
            binding=e.binding or "EMPTY",
            expected_binding=exp_bind or "",
        )
        compare(rec, e.edge, None if exp_R is None else float(exp_R), "km")
        rec["binding_ok"] = (rec["binding"] == exp_bind) if exp_bind else ""
        edge_meta(rec, e, 1e3, 1, starve)
        if row == "P2":
            rec["band_lo"], rec["band_hi"] = p2_lo, p2_hi
            rec["in_band"] = p2_lo <= e.edge / 1e3 <= p2_hi
        else:
            rec["band_lo"] = rec["band_hi"] = rec["in_band"] = ""
        rows.append(rec)
        for line, exp_km in others.items():
            sub = base(row, "P2", config, cfg, sig_p2, f"r={r_fix:g} AU")
            sub.update(
                quantity=f"{line}_root",
                line=line,
                unit="km",
                binding=e.binding or "EMPTY",
                expected_binding="",
                binding_ok="",
            )
            compare(sub, _line_root(e, line), float(exp_km), "km")
            edge_meta(sub, e, 1e3, 1, None)
            sub["band_lo"] = sub["band_hi"] = sub["in_band"] = ""
            rows.append(sub)
    return rows


def verdicts(rows, prereg):
    p1 = [r for r in rows if r["row"] == "P1"]
    p2 = [r for r in rows if r["row"] == "P2" and r["quantity"] == "R_window"]
    b1 = prereg["predictions"]["P1"]["binding"]
    b2 = prereg["predictions"]["P2"]["binding"]
    v1 = all(r["in_band"] and r["binding"] == b1 for r in p1) and len(p1) == 3
    v2 = len(p2) == 1 and p2[0]["in_band"] and p2[0]["binding"] == b2
    return {"P1": "HELD" if v1 else "FAILED", "P2": "HELD" if v2 else "FAILED"}


# ---------------------------------------------------------------- writing
def write_csv(path: Path, header, fields, rows):
    with open(path, "w", newline="") as fh:
        for ln in header:
            fh.write(ln + "\n")
        w = csv.DictWriter(fh, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def census(sweep_rows):
    out = {}
    for s in sorted({r["sigma_MPa"] for r in sweep_rows}, key=float):
        c = {}
        for r in sweep_rows:
            if r["sigma_MPa"] == s:
                c[r["first_violated"]] = c.get(r["first_violated"], 0) + 1
        out[s] = c
    return out


def write_results(path, header, gate_rows, rows, v, cen, runtime_s, prereg):
    P1, P2 = prereg["predictions"]["P1"], prereg["predictions"]["P2"]
    L = ["# Q4 results: the vessel, and watching it fail", ""]
    L.append(
        "Written by `experiments/q4_vessel/run.py`; do not edit by hand. Provenance:"
    )
    L.append("")
    L.append("```")
    L += [h.lstrip("# ") for h in header]
    L.append(f"runtime_s={runtime_s:.1f}")
    L.append("```")
    L.append("")
    L.append("## Verdicts")
    L.append("")
    L.append("| prediction | band | measured edge | binding (registered) | verdict |")
    L.append("| --- | --- | --- | --- | --- |")
    p1 = [r for r in rows if r["row"] == "P1"]
    meas = " / ".join(f"σ {r['sigma_MPa']}: {float(r['measured']):.4f}" for r in p1)
    binds = "/".join(r["binding"] for r in p1)
    L.append(
        f"| P1 r_close(10 km, σ) | [{P1['band_au'][0]}, {P1['band_au'][1]}] AU | "
        f"{meas} AU | {binds} ({P1['binding']}) | **{v['P1']}** |"
    )
    p2 = next(r for r in rows if r["row"] == "P2" and r["quantity"] == "R_window")
    L.append(
        f"| P2 R_window(1.10 AU, 0.7 MPa) | [{P2['band_km'][0]}, {P2['band_km'][1]}] km | "
        f"{float(p2['measured']):.1f} km | {p2['binding']} ({P2['binding']}) | **{v['P2']}** |"
    )
    L.append("")
    L.append(f"Q4_P1={v['P1']}")
    L.append(f"Q4_P2={v['P2']}")
    L.append("")
    L.append("## Gates")
    L.append("")
    L.append("| gate | quantity | value | target | passed |")
    L.append("| --- | --- | --- | --- | --- |")
    for g in gate_rows:
        L.append(
            f"| {g['gate']} | {g['quantity']} | {g['value']:.4f} | {g['target']} | {g['passed']} |"
        )
    L.append("")
    L.append("## Every edge row beside the prereg's expected value")
    L.append("")
    L.append(
        "`within_tol`: |delta| <= prereg edge tolerance (1e-4 AU; 1e-3 x expected in R). "
        "`printed`: measured rounded to the prereg's printed digits equals it. "
        "STARVE margin at the edge in µmol m⁻² s⁻¹ (monitored, never binding)."
    )
    L.append("")
    L.append(
        "| row | config | σ MPa | quantity | measured | expected | delta | within_tol | printed | binding | expected binding | tie | STARVE margin |"
    )
    L.append(
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |"
    )
    for r in rows:
        L.append(
            f"| {r['row']} | {r['config']} | {r['sigma_MPa']} | {r['quantity']} | "
            f"{r['measured']} {r['unit']} | {r['expected']} | {r['delta']} | {r['within_tol']} | "
            f"{r['matches_printed']} | {r['binding']} | {r['expected_binding']} | {r['tie']} | "
            f"{r['starve_margin_at_edge']} |"
        )
    off = [r for r in rows if r["within_tol"] is False]
    unprinted = [r for r in rows if r["matches_printed"] is False]
    badbind = [r for r in rows if r["binding_ok"] is False]
    L.append("")
    L.append(
        f"Rows off their expected value by more than the edge tolerance: {len(off)}"
        + (
            ""
            if not off
            else " -- "
            + ", ".join(
                f"{r['row']} σ{r['sigma_MPa']} {r['quantity']} ({r['delta']})"
                for r in off
            )
        )
    )
    L.append(
        f"Rows not matching the printed digits: {len(unprinted)}"
        + (
            ""
            if not unprinted
            else " -- "
            + ", ".join(
                f"{r['row']} σ{r['sigma_MPa']} {r['quantity']}" for r in unprinted
            )
        )
    )
    L.append(
        f"Rows with a binding other than expected: {len(badbind)}"
        + (
            ""
            if not badbind
            else " -- " + ", ".join(f"{r['row']} σ{r['sigma_MPa']}" for r in badbind)
        )
    )
    L.append("")
    L.append(
        "## Census of the registered grid (first violated line, auto path, registered law)"
    )
    L.append("")
    for s, c in cen.items():
        L.append(f"- σ {s} MPa: " + ", ".join(f"{k} {n}" for k, n in sorted(c.items())))
    L.append("")
    path.write_text("\n".join(L) + "\n")


def remove_stale(out: Path):
    for name in OUTPUTS:
        (out / name).unlink(missing_ok=True)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prereg", type=Path, default=HERE / "prereg.yaml")
    ap.add_argument("--out", type=Path, default=HERE)
    ap.add_argument("--workers", type=int, default=MAX_WORKERS)
    args = ap.parse_args(argv)
    workers = max(1, min(args.workers, MAX_WORKERS))
    t0 = time.time()

    prereg = yaml.safe_load(args.prereg.read_text())
    args.out.mkdir(parents=True, exist_ok=True)
    try:
        assert_prereg_matches_code(prereg, args.prereg)
    except PreregMismatch as err:
        remove_stale(args.out)
        print(f"PREREG MISMATCH: {err}. Nothing written.", file=sys.stderr)
        return 2

    gate_rows = gates(prereg)
    for g in gate_rows:
        print(
            f"gate {g['gate']} {g['quantity']}: {g['value']:.4f} target {g['target']} "
            f"{'pass' if g['passed'] else 'FAIL'}"
        )
    if not all(g["passed"] for g in gate_rows):
        remove_stale(args.out)
        print("GATE FAILED: sweep blocked, nothing written.", file=sys.stderr)
        return 2

    header = provenance_lines(args.prereg)
    r_nodes, R_nodes, sigmas = registered_grids(prereg)
    try:
        jobs = [(s, r_nodes, R_nodes) for s in sigmas]
        if workers == 1:
            parts = [_sweep_sigma(j) for j in jobs]
        else:
            with Pool(min(workers, len(sigmas))) as pool:
                parts = pool.map(_sweep_sigma, jobs)
        sweep_rows = [r for part in parts for r in part]
        print(f"sweep: {len(sweep_rows)} states in {time.time() - t0:.1f} s")
        rows = compute_edges(prereg, r_nodes, R_nodes, sigmas)
    except V.RunnerError as err:
        remove_stale(args.out)
        print(
            f"RUNNER ERROR (auto-path BURST/BOIL): {err}. Nothing written.",
            file=sys.stderr,
        )
        return 2

    v = verdicts(rows, prereg)
    runtime = time.time() - t0
    write_csv(args.out / "sweep.csv", header, SWEEP_FIELDS, sweep_rows)
    write_csv(args.out / "edges.csv", header, EDGE_FIELDS, rows)
    write_results(
        args.out / "RESULTS.md",
        header,
        gate_rows,
        rows,
        v,
        census(sweep_rows),
        runtime,
        prereg,
    )
    for r in rows:
        print(
            f"{r['row']:<14} σ{r['sigma_MPa']:<4} {r['quantity']:<12} {r['measured']:>12} "
            f"exp {r['expected']:>9} Δ {r['delta']:>10} tol {r['within_tol']!s:<5} "
            f"bind {r['binding']}/{r['expected_binding']}"
        )
    print(f"P1 {v['P1']}  P2 {v['P2']}  runtime {runtime:.1f} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
