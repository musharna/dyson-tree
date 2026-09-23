"""The Q4 pre-registration against the spec it copies, and against git's chronology.

`test_prereg_equals_spec` builds the WHOLE expected prereg structure from the spec's
own text and tables (§3 registry, §6 bands, grids, edge rule, tolerances, load order,
row table) and compares it to `prereg.yaml` section by section (round-6 audit: two
band strings let a wrong binding, grid, registry entry, tie rule or arm row pass).
`test_prereg_precedes_hand_rows` asserts the commit that introduced the prereg is a
STRICT ancestor of the commit that introduced `tools/q4_hand_rows.py` ("ancestor of
HEAD" is dropped as tautological). Each has a planted negative control.
"""

import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
SPEC = ROOT / "docs" / "superpowers" / "specs" / "2026-09-12-northstar-design.md"
PREREG = ROOT / "experiments" / "q4_vessel" / "prereg.yaml"
CALC = "tools/q4_hand_rows.py"
SPEC_REL = "docs/superpowers/specs/2026-09-12-northstar-design.md"
PREREG_REL = "experiments/q4_vessel/prereg.yaml"


def _git(*args):
    return subprocess.run(
        ["git", *args], cwd=ROOT, capture_output=True, text=True, check=False
    )


def _spec():
    return SPEC.read_text()


def _flat(text):
    return re.sub(r"\s+", " ", text)


def _nums(cell):
    return [float(x) for x in re.findall(r"\d+\.\d+|\d+", cell)]


def _table_rows(text, header_start):
    """Rows of the markdown table whose header line starts with `header_start`."""
    lines = text.splitlines()
    i = next(k for k, ln in enumerate(lines) if ln.startswith(header_start))
    rows = []
    for ln in lines[i + 2 :]:
        if not ln.startswith("|"):
            break
        rows.append([c.strip() for c in ln.strip().strip("|").split("|")])
    return rows


# ---------------------------------------------------------------- expected, from the spec
def _registry(text):
    rows = {r[0]: r[1] for r in _table_rows(text, "| name ")}
    assert len(rows) == 12, f"§3 registry has {len(rows)} rows, spec says twelve"
    tick = lambda c: re.search(r"`([^`]+)`", c).group(1)  # noqa: E731
    t_opt, omega = _nums(rows["`t_opt`, `omega`"])
    albedo, emis = _nums(rows["`albedo`, `emissivity`"])
    ni = rows["`n_interior`"]
    tr = rows["`thermal_reflectance`"]
    return {
        "t_opt_K": t_opt,
        "omega_K": omega,
        "albedo": albedo,
        "emissivity": emis,
        "f_floor": _nums(rows["`f_floor`"])[0],
        "n": _nums(rows["`n`"])[0],
        "interior": tick(rows["`interior`"]),
        "shell_temperature": rows["shell temperature"].split(",")[0],
        "dust": tick(rows["dust"]),
        "T_freeze_K": _nums(rows["`T_freeze`"])[0],
        "optical_law": tick(rows["`optical_law`"]),
        "n_interior": {
            "arm_only": ni.startswith("arm only"),
            "vapour": float(re.search(r"vapour (\d\.\d+)", ni).group(1)),
            "water": float(re.search(r"water (\d\.\d+)", ni).group(1)),
            "default": re.search(r"(\w+) [\d.]+ \(default\)", ni).group(1),
        },
        "thermal_reflectance": {
            "arm_only": tr.startswith("arm only"),
            "registered": re.search(r"`(\w+)` \(registered\)", tr).group(1),
            "arm": re.findall(r"`(\w+)`", tr)[-1],
        },
        "solar_tail_transmission": tick(rows["`solar_tail_transmission`"]),
    }


def _crossings(cell):
    """{'OPAQUE': km, 'FREEZE': km} from an edge cell, in either phrasing."""
    return {
        line: float(v)
        for line, v in re.findall(r"(OPAQUE|FREEZE)(?: R)? (\d+\.\d+) km", cell)
    }


def _rows(text):
    rows = {r[0]: r for r in _table_rows(text, "| row ")}
    edge = {k: r[3] for k, r in rows.items()}
    p1_reg = [_nums(edge[f"P1, σ {s} MPa"])[0] for s in ("0.7", "1.5", "3.1")]
    registered = {
        "P1_edge_au": p1_reg,
        "P2": {
            "R_km": _nums(edge["P2 OPAQUE, f_floor 0.25"])[0],
            "binding": "OPAQUE",
            "FREEZE_km": _nums(edge["P2 FREEZE"])[0],
        },
    }
    ctl_p2 = _nums(edge["P2 control, normal incidence"])
    control = {
        "optical_law": "normal",
        "P1_edge_au": _nums(edge["P1 control, normal incidence"]),
        "P2": {
            "R_km": ctl_p2[0],
            "binding": "OPAQUE" if ctl_p2[0] < ctl_p2[1] else "FREEZE",
            "FREEZE_km": ctl_p2[1],
        },
    }
    arms = _nums(edge["P2 arms, OPAQUE crossing"])  # 10.6, 777.5, 0.10, 532.6
    variants = {
        "interior_central": {
            "P2_R_km": _nums(edge["P2 variant, interior `central`"])[0]
        },
        "P2_f_floor_arms": {
            "0.50": {"OPAQUE_km": arms[0]},
            "0.10": {
                "OPAQUE_km": arms[1],
                "R_window_km": arms[3],
                "binding": "FREEZE" if arms[3] < arms[1] else "OPAQUE",
            },
        },
    }
    assert "binding FREEZE in every row" in _flat(text), "P1 arm binding not stated"
    fresnel = []
    for pred in ("P1", "P2"):
        for variant, tr in (("i", "0"), ("ii", "slab")):
            for inside, n_int in (("vapour", 1.000), ("water", 1.333)):
                cell = edge[f"{pred} Fresnel arm ({variant}), {inside} inside"]
                row = {
                    "optical_law": "shell+fresnel",
                    "n_interior": n_int,
                    "thermal_reflectance": tr,
                    "prediction": pred,
                }
                if pred == "P1":
                    row |= {"edge_au": _nums(cell), "binding": "FREEZE"}
                else:
                    c = _crossings(cell)
                    bind = min(c, key=c.get)
                    other = max(c, key=c.get)
                    row |= {
                        "R_window_km": c[bind],
                        "binding": bind,
                        "other_km": c[other],
                    }
                fresnel.append(row)
    # the prereg lists (i) then (ii) per prediction, vapour then water
    return registered, control, variants, fresnel


def _expected(text):
    flat = _flat(text)
    m1 = re.search(
        r"`r_close\(10 km, sigma\) ∈ \[([\d.]+), ([\d.]+)\] AU` for every sigma, `binding = (\w+)`",
        flat,
    )
    m2 = re.search(r"`R_window ∈ \[(\d+), (\d+)\] km`, `binding = (\w+)`", flat)
    mr = re.search(
        r"`r`: ([\d.]+) to ([\d.]+) AU in ([\d.]+) AU steps, (\d+) nodes", flat
    )
    ms = re.search(r"`sigma`: \{([\d., ]+)\} MPa", flat)
    mR = re.search(
        r"`R`: (\d+) m to (\d+) km, (\d+) nodes per decade on a (\w+) grid, (\d+) nodes",
        flat,
    )
    mt = re.search(r"bisection to (1e-\d) AU in `r` and ([\d.]+)% in `R`", flat)
    me = re.search(
        r"BURST and BOIL: (1e-\d) relative; FREEZE: (1e-\d) K; STARVE and OPAQUE: (1e-\d)",
        flat,
    )
    mfp = re.search(r"\(`\|Δp\| < (1e-\d)` Pa", flat)
    mgc = re.search(
        r"611\.657 Pa at 273\.16 K within atol ([\d.]+) Pa.*?882 Pa at 5\.16 °C within atol ([\d.]+) Pa",
        flat,
    )
    mlo = re.search(r"Load order: ((?:\w+, ){4}\w+)\.", flat)
    for m, what in [
        (m1, "P1 band"),
        (m2, "P2 band"),
        (mr, "r grid"),
        (ms, "sigma"),
        (mR, "R grid"),
        (mt, "edge tol"),
        (me, "epsilons"),
        (mfp, "fixed point"),
        (mgc, "gate C"),
        (mlo, "load order"),
    ]:
        assert m, f"spec no longer states the {what} in the parsed form"
    sig = [float(x) for x in ms.group(1).split(",")]
    registered, control, variants, fresnel = _rows(text)

    # edge rule: each prereg value is keyed to the spec phrase that states it.
    edge_phrases = {
        "root_of": (
            "binding line's margin",
            "an edge is the root of the binding line's margin",
        ),
        "bracket": (
            "last all-HOLD node, first any-VIOLATED node",
            "the bracket is the last all-HOLD node and the first any-VIOLATED node",
        ),
        "candidates": (
            "registered lines that HOLD at the lower node and VIOLATE at the upper node",
            "the CANDIDATES are the registered lines (FREEZE, OPAQUE) that HOLD at the lower node and VIOLATE at the upper one",
        ),
        "refine": ("bisection", "each candidate's margin is bisected to its root"),
        "edge": (
            "smallest candidate root; binding = that root's line",
            "the edge is the SMALLEST root and `binding` is that root's line",
        ),
        "tie": (
            "roots within one tolerance -> load order decides, both printed",
            "only when two roots fall within one tolerance of each other does load order decide, and the runner prints both",
        ),
        "later_roots": (
            "printed as counterfactual, never the edge",
            "are printed as COUNTERFACTUAL, never as the edge",
        ),
        "empty": ("no node holds -> R_window = 0", "no node holds, `R_window = 0`"),
        "grid_nodes": (
            "display and bracket only, never the reported edge",
            "grid nodes are for display and for the bracket, never the reported edge",
        ),
    }
    for key, (_, phrase) in edge_phrases.items():
        assert phrase in flat, f"edge rule '{key}': spec phrase gone: {phrase!r}"

    spec_commit = _git("log", "-1", "--format=%h", "--abbrev=7", _introducing_commit(PREREG_REL), "--", SPEC_REL).stdout.strip()
    return {
        "predictions": {
            "P1": {
                "axis": "r",
                "fixed": {"R_km": 10, "dust": "none", "albedo": 0, "organism": "algal"},
                "sigma_MPa": sig,
                "band_au": [float(m1.group(1)), float(m1.group(2))],
                "band": f"r_close(10 km, sigma) in [{m1.group(1)}, {m1.group(2)}] AU for every sigma",
                "binding": m1.group(3),
            },
            "P2": {
                "axis": "R",
                "fixed": {
                    "r_au": 1.10,
                    "sigma_MPa": 0.7,
                    "dust": "none",
                    "f_floor": 0.25,
                },
                "band_km": [int(m2.group(1)), int(m2.group(2))],
                "band": f"R_window in [{m2.group(1)}, {m2.group(2)}] km",
                "binding": m2.group(3),
            },
        },
        "grids": {
            "r_au": {
                "start": float(mr.group(1)),
                "stop": float(mr.group(2)),
                "step": float(mr.group(3)),
                "nodes": int(mr.group(4)),
            },
            "sigma_MPa": sig,
            "R_m": {
                "start": int(mR.group(1)),
                "stop": float(mR.group(2)) * 1e3,
                "per_decade": int(mR.group(3)),
                "spacing": mR.group(4),
                "nodes": int(mR.group(5)),
            },
        },
        "load_order": mlo.group(1).split(", "),
        "binding_lines": ["FREEZE", "OPAQUE"],
        "asserted_not_tested": ["BURST", "BOIL"],
        "monitored": ["STARVE"],
        "edge_rule": {k: v for k, (v, _) in edge_phrases.items()},
        "tolerances": {
            "edge_r_au": float(mt.group(1)),
            "edge_R_rel": float(mt.group(2)) / 100,
            "burst_boil_rel": float(me.group(1)),
            "freeze_K": float(me.group(2)),
            "starve_opaque_abs": float(me.group(3)),
            "fixed_point_dp_Pa": float(mfp.group(1)),
            "gate_C_triple_point_Pa": float(mgc.group(1)),
            "gate_C_regression_Pa": float(mgc.group(2)),
        },
        "registry": _registry(text),
        "control": control,
        "variants": variants,
        "registered_rows": registered,
        "fresnel_arm": fresnel,
        "_spec_commit": spec_commit,
    }


def _mismatches(prereg, text):
    exp = _expected(text)
    spec_commit = exp.pop("_spec_commit")
    bad = []
    extra = set(prereg) - set(exp) - {"spec", "spectral_table", "gates"}
    if extra:
        bad.append(f"prereg sections the spec does not define: {sorted(extra)}")
    for key, want in exp.items():
        if prereg.get(key) != want:
            bad.append(f"{key}: prereg {prereg.get(key)!r}\n   spec   {want!r}")
    s = prereg.get("spec", {})
    if s.get("path") != SPEC_REL:
        bad.append(f"spec.path {s.get('path')!r}")
    if str(s.get("commit")) != spec_commit:
        bad.append(f"spec.commit {s.get('commit')!r} vs last spec commit {spec_commit}")
    flat = _flat(text)
    g = prereg.get("gates", {})
    if (
        "[275, 282]" not in g.get("A", "")
        or "Gate A: `T_eq(1 AU, sphere) ∈ [275, 282] K`" not in flat
    ):
        bad.append("gates.A")
    if "611.657" not in g.get("C", "") or "882" not in g.get("C", ""):
        bad.append("gates.C")
    return bad


def _table_meta():
    src = (ROOT / "tests" / "test_spectral_table.py").read_text()
    digest = re.search(r'TABLE_DIGEST = "([0-9a-f]{64})"', src).group(1)
    return digest


# ---------------------------------------------------------------- tests
def test_prereg_equals_spec():
    prereg = yaml.safe_load(PREREG.read_text())
    bad = _mismatches(prereg, _spec())
    assert not bad, "prereg.yaml differs from the spec:\n" + "\n".join(bad)


def test_prereg_spectral_table_block():
    st = yaml.safe_load(PREREG.read_text())["spectral_table"]
    text = _flat(_spec())
    assert st["data_sha256"] == _table_meta()
    assert st["rows"] == 2002 and "2,002 rows from 280 to 4000 nm" in text
    assert st["quadrature"] == "trapezoid"
    header = (ROOT / "sim" / "spectral_table.csv").read_text().split("lambda_nm")[0]
    for name, meta in st["sources"].items():
        assert f"{name}  md5 {meta['md5']}  size {meta['bytes']} B" in header, name
        assert meta["md5"][:8] + "…" in text, f"spec does not print {name}'s md5"


@pytest.mark.parametrize(
    "plant",
    [
        "old_arm_ii_edge",
        "old_tie_rule",
        "wrong_binding",
        "wrong_grid",
        "dropped_registry_row",
    ],
)
def test_prereg_equals_spec_can_fail(plant):
    """Negative controls: each planted defect must be caught; the unplanted prereg
    must pass inside the same test (positive control)."""
    text = _spec()
    good = yaml.safe_load(PREREG.read_text())
    assert not _mismatches(good, text)
    bad = yaml.safe_load(PREREG.read_text())
    if plant == "old_arm_ii_edge":
        bad["fresnel_arm"][2]["edge_au"][0] = 1.1430
    elif plant == "old_tie_rule":
        bad["edge_rule"]["candidates"] = (
            "every registered line, bisected inside the bracket"
        )
    elif plant == "wrong_binding":
        bad["predictions"]["P2"]["binding"] = "FREEZE"
    elif plant == "wrong_grid":
        bad["grids"]["R_m"]["per_decade"] = 10
    elif plant == "dropped_registry_row":
        del bad["registry"]["solar_tail_transmission"]
    assert _mismatches(bad, text), f"planted {plant} was not caught"


def _introducing_commit(path):
    out = _git("log", "--diff-filter=A", "--format=%H", "--", path).stdout.split()
    assert len(out) == 1, f"{path}: introduced by {len(out)} commits: {out}"
    return out[0]


def _strictly_before(a, b):
    return a != b and _git("merge-base", "--is-ancestor", a, b).returncode == 0


def test_prereg_precedes_hand_rows():
    """§6/§8: the prereg's introducing commit is a STRICT ancestor of the calculator's."""
    pre = _introducing_commit(PREREG_REL)
    calc = _introducing_commit(CALC)
    assert _strictly_before(pre, calc), (
        f"prereg {pre[:7]} is not strictly before {calc[:7]}"
    )
    # swapped order and self-comparison must both read False (the check can fail)
    assert not _strictly_before(calc, pre)
    assert not _strictly_before(pre, pre)
    # the prereg's commit touched nothing else (committed ALONE)
    files = _git("show", "--name-only", "--format=", pre).stdout.split()
    assert files == [PREREG_REL], f"prereg commit also touched {files}"
