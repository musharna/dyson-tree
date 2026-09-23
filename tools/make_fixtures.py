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
    adapted_optimum,
    equilibrium_temperature,
    temperature_response,
    temperature_response_gaussian,
)

ROOT = Path(__file__).resolve().parents[1]
PREREG = ROOT / "experiments" / "q1_crossover" / "prereg.yaml"
OUT = ROOT / "web" / "fixtures.json"
PREREG_Q4 = ROOT / "experiments" / "q4_vessel" / "prereg.yaml"

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


# ---------------------------------------------------------------- the vessel (M1b)
# Every number below comes from sim/vessel.py through its public functions. The
# cases are the §6 rows (P1, P2, both controls, the six law triples, the f_floor
# arms, `central`), both §3 closed-form controls, the page defaults, the §4
# mutation control, BURST inside the melt door in every (p, t) mode with its
# positive case outside, a low-pressure state (p* ~0.12 Pa at 2.82 AU, where the
# fixed point's 1e-9·p residual term is the one that holds BOIL), the §6 tie rule
# on synthetic margins, and the prereg's registered inputs either side of each
# registered edge. web/parity.mjs replays each case by its `call`.

LAW_TRIPLES = {
    "shell": {},
    "normal": {"optical_law": "normal"},
    "arm_i_vapour": {"optical_law": "shell+fresnel", "n_interior": 1.0},
    "arm_i_water": {"optical_law": "shell+fresnel", "n_interior": 1.333},
    "arm_ii_vapour": {
        "optical_law": "shell+fresnel",
        "n_interior": 1.0,
        "thermal_reflectance": "slab",
    },
    "arm_ii_water": {
        "optical_law": "shell+fresnel",
        "n_interior": 1.333,
        "thermal_reflectance": "slab",
    },
}


def report_to_dict(rep) -> dict:
    return {
        "violated": list(rep.violated),
        "first": rep.first,
        "sigma_eff": rep.sigma_eff,
        "T_int": rep.T_int,
        "T_shell": rep.T_shell,
        "f_photon": rep.f_photon,
        "thin_wall_valid": bool(rep.thin_wall_valid),
        "lines": {
            n: {
                "lhs": ln.lhs,
                "rhs": ln.rhs,
                "margin": ln.margin,
                "violated": bool(ln.violated),
            }
            for n, ln in rep.lines.items()
        },
    }


def edge_to_dict(e) -> dict:
    return {
        "edge": e.edge,
        "binding": e.binding,
        "roots": dict(e.roots),
        "tie": bool(e.tie),
        "bracket": list(e.bracket) if e.bracket else None,
        "counterfactual": dict(e.counterfactual),
    }


def vessel_block() -> dict:
    from sim import vessel as V
    from sim.organism import ALGAL

    cases = []

    def add(name, call, args, tol, expect):
        cases.append(
            {"name": name, "call": call, "args": args, "tol": tol, "expect": expect}
        )

    kts = [0.0, 1e-9, 1e-6, 0.01, 0.1, 0.5, 1.0, 2.0, 5.0, 20.0, 1e3, 2e4]
    for law, n_int in (
        ("shell", 1.0),
        ("normal", 1.0),
        ("shell+fresnel", 1.0),
        ("shell+fresnel", 1.333),
    ):
        add(
            f"law {law} n_interior {n_int}",
            "shell_transmission",
            {"kt": kts, "optical_law": law, "n_interior": n_int},
            "vessel_closed",
            {"T": [V.shell_transmission(k, law, n_int) for k in kts]},
        )
    for n_int in (1.0, 1.333):
        add(
            f"slab reflectance n_interior {n_int}",
            "slab_reflectance",
            {"kt": kts[:-1], "n_interior": n_int},
            "vessel_closed",
            {"R": [V.slab_reflectance(k, n_int) for k in kts[:-1]]},
        )
    ts = [0.0, 0.5, 1.4, 4.366, 34.2, 55.72, 100.0, 232.5, 1000.0]
    for key, kw in LAW_TRIPLES.items():
        inp = V.VesselInputs(**kw)
        exp = {
            "tau_sw": [V.solar_transmission(t, **inp.optics()) for t in ts],
            "f_photon": [
                V.par_photon_fraction(t, **inp.optics(), interior="mixed") for t in ts
            ],
        }
        if inp.optical_law == "shell":
            exp["f_photon_central"] = [
                V.par_photon_fraction(t, interior="central") for t in ts
            ]
        if inp.optical_law == "shell+fresnel":
            exp["R_slab_sw"] = [V.solar_slab_reflectance(t, inp.n_interior) for t in ts]
        tc = [V.contained_temperature(r, t, **inp.thermal()) for r in (1.0, 1.1, 2.0) for t in ts]
        exp["T_int"] = [a for a, _ in tc]
        exp["T_shell"] = [b for _, b in tc]
        add(f"optics {key}", "optics_at_t", {"t": ts, "inputs": kw}, "vessel_closed", exp)
    temps = [180.0, 200.0, 250.0, 273.15, 273.16, 278.31, 290.0, 300.0]
    add(
        "saturation pressure (Buck)",
        "saturation_pressure",
        {"T": temps},
        "vessel_closed",
        {"p": [V.saturation_pressure(t) for t in temps]},
    )

    # §3 self-consistent pressure at 1 AU, R 10 km, both laws; the closed-form controls
    for s in V.SIGMAS_PA:
        for law in ("shell", "normal"):
            add(
                f"p* 1 AU R 10 km sigma {s:g} {law}",
                "self_consistent_pressure",
                {"r": 1.0, "R": 1e4, "sigma": s, "kw": {"optical_law": law}},
                "vessel_state",
                {"p": V.self_consistent_pressure(1.0, 1e4, s, optical_law=law)},
            )
        k, tau_min = 0.38623, 0.01
        p_mixed = V.self_consistent_pressure(1.0, 1e4, s, optical_law="normal")
        add(
            f"closed-form control (a) mixed, sigma {s:g}",
            "closed_form_control",
            {"r": 1.0, "R": 1e4, "sigma": s, "k": k, "tau_min": tau_min,
             "kw": {"optical_law": "normal"}},
            "vessel_state",
            {"p": p_mixed, "R_max": V.closed_form_r_max(s, p_mixed, k, tau_min)},
        )
        p_scalar = V.self_consistent_pressure(1.0, 1e4, s, scalar_k=k)
        add(
            f"closed-form control (b) scalar limit, sigma {s:g}",
            "closed_form_control",
            {"r": 1.0, "R": 1e4, "sigma": s, "k": k, "tau_min": tau_min,
             "kw": {"scalar_k": k}},
            "vessel_state",
            {"p": p_scalar, "R_max": V.closed_form_r_max(s, p_scalar, k, tau_min)},
        )

    def auto(name, r, R, sigma, kw=None):
        p, t, rep = V.auto_state(r, R, sigma, ALGAL, V.VesselInputs(**(kw or {})))
        add(
            name,
            "auto_state",
            {"r": r, "R": R, "sigma": sigma, "inputs": kw or {}},
            "vessel_state",
            {"p": p, "t": t, "report": report_to_dict(rep)},
        )

    auto("page defaults (1.10 AU, 1 km, 0.7 MPa)", 1.10, 1e3, 0.7e6)
    auto("page defaults, normal incidence", 1.10, 1e3, 0.7e6, {"optical_law": "normal"})
    for key, kw in LAW_TRIPLES.items():
        auto(f"§4 reference state 1.00 AU R 10 km {key} (BURST inside the melt door)",
             1.0, 1e4, 0.7e6, kw)
    auto("low pressure: p* ~0.12 Pa at 2.82 AU, R 10 km", 2.82, 1e4, 0.7e6)
    auto("low pressure: 2.82 AU, R 10 m", 2.82, 10.0, 0.7e6)

    def classify(name, p, t, r, R, sigma, kw=None):
        rep = V.classify_failure(p, t, r, R, sigma, ALGAL, V.VesselInputs(**(kw or {})))
        add(
            name,
            "classify",
            {"p": p, "t": t, "r": r, "R": R, "sigma": sigma, "inputs": kw or {}},
            "vessel_state",
            report_to_dict(rep),
        )

    t100 = 100.0
    ti, _ = V.contained_temperature(1.10, t100)
    classify("manual 100 m wall, R 1 km, 1.10 AU (OPAQUE)", V.saturation_pressure(ti),
             t100, 1.10, 1e3, 0.7e6)
    # BURST inside the melt door, every (p, t) mode, and its positive case outside
    R, s = 1e3, 0.7e6
    p_auto = V.self_consistent_pressure(1.10, R, s)
    t_auto = V.wall_thickness(p_auto, R, s)
    for r_in in (0.5, 0.9, 1.0, 1.03):
        ti, _ = V.contained_temperature(r_in, 10.0)
        modes = {
            "auto/auto": (p_auto, t_auto),
            "manual/auto": (5000.0, t_auto),
            "auto/manual": (V.saturation_pressure(ti), 10.0),
            "manual/manual": (5000.0, 10.0),
        }
        for mode, (p, t) in modes.items():
            classify(f"BURST inside melt door r {r_in} {mode}", p, t, r_in, R, s)
            classify(f"BURST positive case: the r {r_in} {mode} (p, t) at r 1.10 (reads input sigma)", p, t, 1.10, R, s)
    classify("arm (ii) vapour door: 0.99 AU inside", 611.21, 4.366, 0.99, 1e4, 0.7e6,
             LAW_TRIPLES["arm_ii_vapour"])
    classify("arm (ii) vapour door: 1.00 AU outside", 611.21, 4.366, 1.00, 1e4, 0.7e6,
             LAW_TRIPLES["arm_ii_vapour"])
    classify("thin-wall flag: t/R = 100", 611.21, 1000.0, 1.10, 10.0, 0.7e6)

    # §4 mutation control: 0.99·t_min at the page defaults is a RunnerError
    t99 = 0.99 * t_auto
    try:
        V.check_auto_path(p_auto, t99, 1.10, R, s, ALGAL)
        raise AssertionError("0.99 t_min did not trip the runner error")
    except V.RunnerError as exc:
        add("runner error: 0.99 t_min at the page defaults", "check_auto_path",
            {"p": p_auto, "t": t99, "r": 1.10, "R": R, "sigma": s, "inputs": {}},
            "vessel_state",
            {"raised": "RunnerError", "exit_code": exc.exit_code,
             "report": report_to_dict(V.classify_failure(p_auto, t99, 1.10, R, s, ALGAL))})
    add("runner error positive control: t_min passes", "check_auto_path",
        {"p": p_auto, "t": t_auto, "r": 1.10, "R": R, "sigma": s, "inputs": {}},
        "vessel_state",
        {"raised": None, "exit_code": None,
         "report": report_to_dict(V.check_auto_path(p_auto, t_auto, 1.10, R, s, ALGAL))})
    try:
        V.self_consistent_pressure(1.10, 1e3, 0.7e6, max_iter=3)
        raise AssertionError("expected ConvergenceError")
    except V.ConvergenceError:
        add("fixed point exhausts in 3 passes", "convergence_error",
            {"r": 1.10, "R": 1e3, "sigma": 0.7e6, "max_iter": 3}, "vessel_closed",
            {"raised": "ConvergenceError"})
    add("same object: sigma_ice + k_ice", "same_object", {"ids": ["sigma_ice", "k_ice"]},
        "vessel_closed", {"material": V.assert_same_object("sigma_ice", "k_ice"), "raised": False})
    add("same object: sigma_wood + k_ice is refused", "same_object",
        {"ids": ["sigma_wood", "k_ice"]}, "vessel_closed", {"material": None, "raised": True})

    # §6 tie rule on synthetic linear margins, margin = c0 + c1·x
    for nm, lines, nodes in (
        ("smallest root, not load order",
         {"FREEZE": [2.8, -1.0], "STARVE": [1.0, 0.0], "OPAQUE": [2.2, -1.0]}, [1.0, 2.0, 3.0]),
        ("within one tolerance: load order decides",
         {"FREEZE": [2.20005, -1.0], "STARVE": [1.0, 0.0], "OPAQUE": [2.2, -1.0]}, [1.0, 2.0, 3.0]),
        ("empty window", {"FREEZE": [-1.0, 0.0], "STARVE": [1.0, 0.0], "OPAQUE": [1.0, 0.0]},
         [1.0, 2.0]),
    ):
        e = V.find_edge(
            nodes,
            lambda x, L=lines: {k: c0 + c1 * x for k, (c0, c1) in L.items()},
            tie_tol=lambda a, b: abs(a - b) <= 1e-4,
            refine_width=lambda lo, hi: 1e-9,
        )
        add(f"tie rule: {nm}", "find_edge_linear",
            {"nodes": nodes, "lines": lines, "tie_tol": 1e-4, "refine_width": 1e-9},
            "vessel_closed", edge_to_dict(e))

    # §6 rows: P1 r_close at R 10 km, P2 R_window at 1.10 AU, every law triple
    for key, kw in LAW_TRIPLES.items():
        inp = V.VesselInputs(**kw)
        for s in V.SIGMAS_PA:
            add(f"§6 P1 {key} sigma {s:g}", "r_close",
                {"R": 1e4, "sigma": s, "inputs": kw}, "edge_r_au",
                edge_to_dict(V.r_close(1e4, s, ALGAL, inp)))
        add(f"§6 P2 {key}", "r_window", {"r": 1.10, "sigma": 0.7e6, "inputs": kw},
            "edge_R_m", edge_to_dict(V.r_window(1.10, 0.7e6, ALGAL, inp)))
    for kw in ({"f_floor": 0.50}, {"f_floor": 0.10}, {"interior": "central"}):
        add(f"§6 P2 variant {kw}", "r_window", {"r": 1.10, "sigma": 0.7e6, "inputs": kw},
            "edge_R_m", edge_to_dict(V.r_window(1.10, 0.7e6, ALGAL, V.VesselInputs(**kw))))

    # The prereg's registered inputs (experiments/q4_vessel/prereg.yaml `predictions`,
    # `registered_rows`), either side of each registered edge: inside the window
    # classify_failure returns the empty set, outside it returns the registered binding.
    prereg = yaml.safe_load(PREREG_Q4.read_text())
    rows = prereg["registered_rows"]
    examples = []
    for s_mpa, edge in zip(prereg["predictions"]["P1"]["sigma_MPa"], rows["P1_edge_au"]):
        for side, r in (("inside", edge - 0.001), ("outside", edge + 0.001)):
            examples.append((f"P1 sigma {s_mpa} MPa, R 10 km, r {r:.4f} AU ({side})",
                             r, 10e3, s_mpa * 1e6, {}))
    p2 = prereg["predictions"]["P2"]
    for side, R in (("inside", rows["P2"]["R_km"] * 1e3 * 0.99),
                    ("outside", rows["P2"]["R_km"] * 1e3 * 1.01)):
        examples.append((f"P2 r {p2['fixed']['r_au']} AU, sigma {p2['fixed']['sigma_MPa']} MPa,"
                         f" R {R / 1e3:.2f} km ({side})", p2["fixed"]["r_au"], R,
                         p2["fixed"]["sigma_MPa"] * 1e6, {"f_floor": p2["fixed"]["f_floor"]}))
    for name, r, R, s, kw in examples:
        p, t, rep = V.auto_state(r, R, s, ALGAL, V.VesselInputs(**kw))
        add(f"prereg example: {name}", "prereg_example",
            {"p": p, "t": t, "r": r, "R": R, "sigma": s, "inputs": kw},
            "vessel_state", {"p": p, "t": t, "report": report_to_dict(rep)})

    return {
        "organism": "algal",
        "grid_r_au": [float(x) for x in V.GRID_R_AU],
        "grid_r_m": [float(x) for x in V.GRID_R_M],
        "cases": cases,
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
        t_eq = [
            equilibrium_temperature(float(r), org.area_ratio, org.emissivity, org.albedo)
            for r in grid
        ]
        # Every function the JS port contains gets a fixture. thermal.py is
        # ported whole (the ship plan says so), so its two Q2/Q2b response
        # forms are sampled here even though the page plots neither -- a
        # ported function with no fixture is a test that cannot fail.
        t_opt_home = adapted_optimum(1.0, org.area_ratio, org.emissivity, org.albedo)
        cases[cls] = {
            "preset": org_to_dict(org),
            "leaf_respiration": org.leaf_respiration(),
            "organism_respiration": org.organism_respiration(),
            "adapted_t_opt_home_1au": t_opt_home,
            "temperature_response": [
                temperature_response(t, org.t_min, org.t_opt) for t in t_eq
            ],
            "temperature_response_gaussian": [
                temperature_response_gaussian(t, t_opt_home, org.omega) for t in t_eq
            ],
            "irradiance": [irradiance(float(r)) for r in grid],
            "equilibrium_temperature": [
                t for t in t_eq
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
    # distance where T_eq == t_min exactly and one step either side.
    #
    # What this does NOT discriminate: `t < t_min` vs `t <= t_min` in the guard.
    # At t == t_min the ramp evaluates to (t - t_min)/(t_opt - t_min) = 0
    # anyway, so both spellings return exactly 0 and the sample cannot tell
    # them apart. What it DOES pin is that the clamp exists at all -- the
    # `outside` sample sits below the floor, where an unclamped ramp goes
    # NEGATIVE -- and that net carbon steps down across the floor (gross
    # vanishes while respiration continues).
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
            f"{r_floor:.6f} AU; temperature_response is 0 at and below it. "
            "The `outside` sample is below the floor, where a ramp with no "
            "clamp would return a NEGATIVE response -- that is what this "
            "case discriminates. It does not distinguish `<` from `<=`: at "
            "t == t_min the ramp is 0 either way.",
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
            # `git describe`, not the branch name: a branch name (M1a recorded
            # "m1a-vessel") stops naming anything once the branch is merged or deleted.
            "git_describe": git("describe", "--tags", "--always", "--dirty"),
            "worktree_dirty": bool(git("status", "--porcelain")),
            "generator": "tools/make_fixtures.py",
            "physiology_md5": md5(ROOT / "sim" / "physiology.py"),
            "thermal_md5": md5(ROOT / "sim" / "thermal.py"),
            "organism_md5": md5(ROOT / "sim" / "organism.py"),
            "vessel_md5": md5(ROOT / "sim" / "vessel.py"),
            "spectral_table_md5": md5(ROOT / "sim" / "spectral_table.csv"),
            "prereg_q4_md5": md5(PREREG_Q4),
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
            "adapted_t_opt_home_1au": {"rtol": 1e-9, "atol": 0.0, "why": "closed form"},
            "temperature_response_gaussian": {
                "rtol": 1e-9,
                "atol": 1e-15,
                "why": "closed form; underflows to exact 0 far from t_opt, where "
                "a relative bound has no meaning",
            },
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
            "vessel_closed": {
                "rtol": 1e-9,
                "atol": 1e-12,
                "why": "vessel quantities with no iteration: quadratures and "
                "interpolations on the same table, same grid, same order; only "
                "summation order and libm differ",
            },
            "vessel_state": {
                "rtol": 1e-8,
                "atol": 1e-6,
                "why": "downstream of the p* fixed point, whose stop rule is "
                "|dp| < min(1e-6 Pa, 1e-9 p): one extra pass on either side moves p "
                "by up to that residual, and BURST/BOIL margins on the auto path are "
                "differences of equal terms (0 by construction), so atol 1e-6 in "
                "their units (Pa)",
            },
            "edge_r_au": {
                "rtol": 0.0,
                "atol": 1e-7,
                "why": "bisected root, refine width 1e-8 AU (EDGE_TOL_R_AU·1e-4): "
                "ten widths",
            },
            "edge_R_m": {
                "rtol": 1e-6,
                "atol": 0.0,
                "why": "bisected root, refine width 1e-7·lo (EDGE_TOL_R_REL·1e-4): "
                "ten widths",
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
        "vessel": vessel_block(),
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
    print(f"  vessel cases: {len(doc['vessel']['cases'])}")
    # Unused-import guard: these are re-exported into the fixture's contract via
    # the constants block and the checks above; naming them here keeps linters
    # from stripping the imports the doc depends on.
    assert gross_assimilation(100.0, 10.0, 100.0) > 0
    assert respiration(1.0, T_REF_K) == 1.0
    assert Q10 == 2.0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
