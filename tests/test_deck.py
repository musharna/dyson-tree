"""M2b: the gene deck's three rules (northstar design §12).

1. every row names an input that exists, and the set of comparators {T_freeze, f_floor,
   σ, p_sat, 0} its card can move is, SEMANTICALLY (measured on classify_failure's own
   right-hand sides, not by name), exactly {T_freeze} for antifreeze and empty otherwise;
2. every MEASURED row's source resolves to a file:line in this repo;
3. over each card's whole reach (both endpoints, max stack) FREEZE is still first violated
   inside prediction 1's box and OPAQUE inside prediction 2's, both inside the page's
   slider ranges; BURST/BOIL manual doors intact; STARVE margin still displayed.

Each test carries a deliberately bad fixture it must reject AND the live rows (or a good
fixture) it must accept, so a broken checker cannot read as a pass.
"""

from __future__ import annotations

import ast
import copy
import json
import math
import re
from functools import lru_cache
from pathlib import Path

import pytest

from sim import deck as D
from sim import vessel as V
from sim.organism import ALGAL

ROOT = Path(__file__).resolve().parents[1]
DECK_JSON = ROOT / "web" / "deck.json"
DECK_SRC = ROOT / "sim" / "deck.py"
VESSEL_SRC = ROOT / "sim" / "vessel.py"

# §12 / §6 boxes (test data typed from the spec, not read by sim/)
FREEZE_BOX = {"R": 10e3, "r": (1.19, 1.27)}
OPAQUE_BOX = {"r": 1.10, "sigma": 0.7e6, "R": (60e3, 300e3)}
# §5 page slider ranges
SLIDER_R_M = (10.0, 100e3)
SLIDER_r_AU = (0.5, 100.0)

AFP = D.row_by_trait("antifreeze proteins")
RD = D.row_by_trait("reduced dark respiration")


def fixture(row, **dor):
    r = copy.deepcopy(row)
    r["delta_or_range"].update(dor)
    return r


# ---------------------------------------------------------------- the table
def test_rows_mirror_web_deck_json():
    js = json.loads(DECK_JSON.read_text())
    assert js == json.loads(json.dumps(list(D.ROWS)))
    for row in js:
        assert tuple(row) == D.ROW_KEYS, row
        assert row["anchor"] in D.ANCHORS
    # only the two live rows ship in M2b; no f_floor card
    assert [r["trait"] for r in js] == [
        "antifreeze proteins",
        "reduced dark respiration",
    ]
    assert not [r for r in js if r["input"] == "f_floor"]
    # the parity check can fail: one changed digit is caught
    bad = json.loads(DECK_JSON.read_text())
    bad[0]["delta_or_range"]["total_cap"] = 1.31
    assert bad != json.loads(json.dumps(list(D.ROWS)))


# ---------------------------------------------------------------- import guard
def _imports(tree):
    out = set()
    for n in ast.walk(tree):
        if isinstance(n, ast.Import):
            out |= {a.name for a in n.names}
        elif isinstance(n, ast.ImportFrom):
            out.add(n.module or "")
            out |= {f"{n.module}.{a.name}" for a in n.names}
    return out


def _closure(src_text):
    seen, todo, mods = set(), [ast.parse(src_text)], set()
    while todo:
        for m in _imports(todo.pop()):
            if m in mods:
                continue
            mods.add(m)
            cand = ROOT / (m.replace(".", "/") + ".py")
            if cand.exists() and cand not in seen:
                seen.add(cand)
                todo.append(ast.parse(cand.read_text()))
    return mods


def deck_violations(src: str) -> list[str]:
    bad = [m for m in _closure(src) if m in ("sim.deck", "deck") or m.endswith(".deck")]
    tree = ast.parse(src)
    bad += [
        f"literal {n.value!r}"
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and "deck" in n.value
    ]
    for fn in ast.walk(tree):
        if isinstance(fn, ast.FunctionDef) and fn.name == "classify_failure":
            bad += [
                f"classify_failure names {n.id}"
                for n in ast.walk(fn)
                if isinstance(n, ast.Name) and "deck" in n.id.lower()
            ]
    return bad


def test_vessel_does_not_import_the_deck():
    base = VESSEL_SRC.read_text()
    assert deck_violations(base) == []
    for edge in (
        "\nimport sim.deck\n",
        "\nfrom sim import deck\n",
        "\nfrom sim.deck import ROWS\n",
        "\n_J = open('web/deck.json').read()\n",
    ):
        assert deck_violations(base + edge), f"guard missed {edge!r}"
    injected = base.replace(
        "    t_int, t_shell = contained_temperature(r, t, **inputs.thermal())",
        "    t_int, t_shell = contained_temperature(r, t, **inputs.thermal())\n"
        "    _ = DECK_ROWS",
        1,
    )
    assert injected != base, "injection anchor not found in classify_failure"
    assert deck_violations(injected), "guard missed a deck name inside classify_failure"


def test_deck_imports_vessel_one_way_only():
    # the other direction: the deck may use the vessel's input dataclass, never its
    # classifier, so no card can compute a verdict of its own
    tree = ast.parse(DECK_SRC.read_text())
    names = {
        a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) for a in n.names
    }
    assert "classify_failure" not in names and "find_edge" not in names, names
    bad = ast.parse(
        DECK_SRC.read_text() + "\nfrom sim.vessel import classify_failure\n"
    )
    names = {
        a.name for n in ast.walk(bad) if isinstance(n, ast.ImportFrom) for a in n.names
    }
    assert "classify_failure" in names


# ---------------------------------------------------------------- rule 1
COMPARATOR = {
    "BURST": "σ",
    "FREEZE": "T_freeze",
    "BOIL": "p_sat",
    "STARVE": "0",
    "OPAQUE": "f_floor",
}


def _probe_states():
    """Resolved (p, t, r, R, sigma) states the comparators are read at: P1 and P2."""
    out = []
    for r, R, s in ((1.20, 10e3, 0.7e6), (1.10, 95e3, 0.7e6), (1.10, 1e3, 3.1e6)):
        p, t, _ = V.auto_state(r, R, s, ALGAL)
        out.append((p, t, r, R, s))
    return out


def comparators_moved(row) -> set[str]:
    """Which lines' right-hand sides move when the card is played over its reach."""
    moved = set()
    for tot in D.reach(row):
        inp, org = D.apply(row, tot, V.REGISTERED, ALGAL)
        for st in _probe_states():
            a = V.classify_failure(*st, ALGAL, V.REGISTERED)
            b = V.classify_failure(*st, org, inp)
            for ln, c in COMPARATOR.items():
                if not math.isclose(
                    a.lines[ln].rhs, b.lines[ln].rhs, rel_tol=1e-12, abs_tol=0
                ):
                    moved.add(c)
    return moved


def rule1_failures(row) -> list[str]:
    if not D.input_exists(row):
        return [f"{row['trait']}: input {row['input']!r} does not exist"]
    want = {"T_freeze"} if row["trait"] == "antifreeze proteins" else set()
    got = comparators_moved(row)
    return (
        []
        if got == want
        else [f"{row['trait']}: moves comparators {got}, allowed {want}"]
    )


def test_rule1_inputs_exist_and_comparators_are_semantic():
    # positive control: the live rows
    for row in D.ROWS:
        assert rule1_failures(row) == [], rule1_failures(row)
    assert comparators_moved(AFP) == {"T_freeze"}
    assert comparators_moved(RD) == set()
    # bad fixtures, each rejected for its reason
    ghost = dict(copy.deepcopy(RD), input="leaf_armour")
    assert "does not exist" in rule1_failures(ghost)[0]
    # an f_floor card: a real input that IS a comparator; a name test on "T_freeze" misses it
    ffl = dict(copy.deepcopy(RD), input="f_floor", trait="brighter chloroplasts")
    ffl["delta_or_range"].update(op="subtract", range=[0.0, 0.1])
    assert "{'f_floor'}" in rule1_failures(ffl)[0]
    # an antifreeze row wired to a non-comparator input moves nothing: also rejected
    afp_wrong = dict(copy.deepcopy(AFP), input="t_opt_K")
    assert "moves comparators set()" in rule1_failures(afp_wrong)[0]


# ---------------------------------------------------------------- rule 2
SRC_RE = re.compile(r"^([\w./-]+\.\w+):(\d+)$")


def resolves(source: str) -> bool:
    m = SRC_RE.match(source.strip())
    if not m:
        return False
    path = (ROOT / m.group(1)).resolve()
    if ROOT not in path.parents or not path.is_file():
        return False
    lines = path.read_text().splitlines()
    n = int(m.group(2))
    return 1 <= n <= len(lines) and lines[n - 1].strip() != ""


def rule2_failures(rows) -> list[str]:
    return [
        f"{r['trait']}: MEASURED source {r['source']!r} does not resolve"
        for r in rows
        if r["anchor"] == "MEASURED" and not resolves(r["source"])
    ]


def test_rule2_measured_sources_resolve():
    assert rule2_failures(D.ROWS) == []  # no MEASURED row ships in M2b
    good = dict(copy.deepcopy(RD), anchor="MEASURED", source="sim/physiology.py:54")
    assert rule2_failures([good]) == []
    for src in (
        "sim/physiology.py:99999",
        "sim/nope.py:3",
        "doi:10.1038/nbt0997-887",
        "sim/physiology.py",
        # exists but outside the repo on any checkout layout (CI checks out
        # into .../dyson-tree/dyson-tree, where ../dyson-tree/ is the repo itself)
        "../../../../../../../../etc/passwd:1",
    ):
        bad = dict(copy.deepcopy(RD), anchor="MEASURED", source=src)
        assert rule2_failures([bad]), f"accepted {src!r}"
    # DEMONSTRATED rows carry a DOI (checked by CrossRef before commit, §12)
    for r in D.ROWS:
        if r["anchor"] == "DEMONSTRATED":
            assert r["source"].startswith("doi:10."), r


# ---------------------------------------------------------------- rule 3
@lru_cache(maxsize=None)
def _freeze_edges(T_freeze_K: float, r_d: float):
    inp = V.VesselInputs(T_freeze_K=T_freeze_K)
    org = ALGAL.__class__(**{**ALGAL.__dict__, "r_d": r_d})
    return tuple(V.r_close(FREEZE_BOX["R"], s, org, inp) for s in V.SIGMAS_PA)


@lru_cache(maxsize=None)
def _opaque_edge(T_freeze_K: float, r_d: float):
    inp = V.VesselInputs(T_freeze_K=T_freeze_K)
    org = ALGAL.__class__(**{**ALGAL.__dict__, "r_d": r_d})
    e = V.r_window(OPAQUE_BOX["r"], OPAQUE_BOX["sigma"], org, inp)
    return e, V.auto_state(OPAQUE_BOX["r"], e.edge, OPAQUE_BOX["sigma"], org, inp)


def reach_state(row, tot):
    inp, org = D.apply(row, tot, V.REGISTERED, ALGAL)
    # the deck moves only these two inputs in M2b; any other move is rule 1's failure
    assert inp == V.VesselInputs(T_freeze_K=inp.T_freeze_K)
    return inp, org


def rule3_failures(row) -> list[str]:
    out = []
    for tot in D.reach(row):
        inp, org = reach_state(row, tot)
        tag = f"{row['trait']} at {tot:g}"
        if not org.r_d > 0:
            out.append(f"{tag}: r_d {org.r_d} leaves STARVE undisplayable")
            continue
        for s, e in zip(V.SIGMAS_PA, _freeze_edges(inp.T_freeze_K, org.r_d)):
            lo, hi = FREEZE_BOX["r"]
            if e.binding != "FREEZE" or not lo <= e.edge <= hi:
                out.append(
                    f"{tag}: sigma {s / 1e6:g} FREEZE edge {e.edge:.4f} AU binding {e.binding}"
                )
            if not SLIDER_r_AU[0] <= e.edge <= SLIDER_r_AU[1]:
                out.append(f"{tag}: FREEZE edge {e.edge:.4f} AU outside the r slider")
        e, (p, t, rep) = _opaque_edge(inp.T_freeze_K, org.r_d)
        lo, hi = OPAQUE_BOX["R"]
        if e.binding != "OPAQUE" or not lo <= e.edge <= hi:
            out.append(
                f"{tag}: OPAQUE R_window {e.edge / 1e3:.1f} km binding {e.binding}"
            )
        if not SLIDER_R_M[0] <= e.edge <= SLIDER_R_M[1]:
            out.append(f"{tag}: OPAQUE edge {e.edge / 1e3:.1f} km outside the R slider")
        # STARVE still a displayed, finite margin at the P2 edge, and violable on the page
        if not math.isfinite(rep.lines["STARVE"].margin):
            out.append(f"{tag}: STARVE margin not finite")
        # the hot end of the sliders: r 0.5 AU behind the thinnest wall (t 0.01 m)
        hot = V.classify_failure(
            p, 0.01, SLIDER_r_AU[0], e.edge, OPAQUE_BOX["sigma"], org, inp
        )
        if not hot.lines["STARVE"].violated:
            out.append(f"{tag}: STARVE unreachable at r {SLIDER_r_AU[0]} AU, t 0.01 m")
        # BURST and BOIL manual doors at the P2 edge state
        R = e.edge
        if (
            not V.classify_failure(
                1.1 * p, t, OPAQUE_BOX["r"], R, OPAQUE_BOX["sigma"], org, inp
            )
            .lines["BURST"]
            .violated
        ):
            out.append(f"{tag}: BURST manual door closed")
        psat = V.saturation_pressure(rep.T_int)
        if (
            not V.classify_failure(
                0.9 * psat, t, OPAQUE_BOX["r"], R, OPAQUE_BOX["sigma"], org, inp
            )
            .lines["BOIL"]
            .violated
        ):
            out.append(f"{tag}: BOIL manual door closed")
    return out


def _edges(T_freeze_K, r_d=ALGAL.r_d):
    return [round(e.edge, 4) for e in _freeze_edges(T_freeze_K, r_d)]


def test_rule3_third_rule_over_each_cards_reach():
    # positive control: the live rows, over their whole reach
    assert D.reach(AFP) == [0.0, 1.3]
    assert D.reach(RD) == [0.1]
    for row in D.ROWS:
        assert rule3_failures(row) == [], rule3_failures(row)
    # the spec's worked numbers (§12)
    assert _edges(273.15 - 1.3) == [1.2197, 1.2453, 1.2695]
    rd = D.apply(RD, 0.1, V.REGISTERED, ALGAL)[1].r_d
    assert rd == pytest.approx(0.024)
    m0 = _opaque_edge(273.15, ALGAL.r_d)[1][2].lines["STARVE"].margin
    m1 = _opaque_edge(273.15, rd)[1][2].lines["STARVE"].margin
    assert (round(m0, 2), round(m1, 2)) == (3.11, 3.20)
    # bad fixture 1: the unclipped antifreeze card, 5 K
    unclipped = fixture(AFP, total_cap=None, max_stack=1)
    f = rule3_failures(unclipped)
    assert _edges(273.15 - 5.0) == [1.2631, 1.2894, 1.3141]
    # two of three leave the box (sigma 0.7 at 1.2631 is still inside it)
    assert f == [
        "antifreeze proteins at 5: sigma 1.5 FREEZE edge 1.2894 AU binding FREEZE",
        "antifreeze proteins at 5: sigma 3.1 FREEZE edge 1.3141 AU binding FREEZE",
    ], f
    # bad fixture 2: 0.8 K passes alone, fails stacked twice (the cap is on the TOTAL)
    alone = fixture(AFP, range=[0.0, 0.8], total_cap=None, max_stack=1)
    assert rule3_failures(alone) == []
    assert _edges(273.15 - 0.8) == [1.2140, 1.2395, 1.2636]
    twice = fixture(AFP, range=[0.0, 0.8], total_cap=None, max_stack=2)
    f = rule3_failures(twice)
    assert _edges(273.15 - 1.6) == [1.2231, 1.2488, 1.2730]
    assert f == [
        "antifreeze proteins at 1.6: sigma 3.1 FREEZE edge 1.2730 AU binding FREEZE"
    ], f
    # bad fixture 3: respiration to zero
    zero = fixture(RD, range=[0.0, 0.0])
    assert rule3_failures(zero) == [
        "reduced dark respiration at 0: r_d 0.0 leaves STARVE undisplayable"
    ]


@pytest.mark.slow
def test_rule3_cap_is_where_the_sigma_31_edge_leaves_the_box():
    """§12: the sigma 3.1 MPa edge reaches 1.27 AU at dT_sc = 1.343 K; the 1.3 K cap is below it."""

    def top(dT):
        return (
            V.r_close(
                FREEZE_BOX["R"], 3.1e6, ALGAL, V.VesselInputs(T_freeze_K=273.15 - dT)
            ).edge
            - 1.27
        )

    lo, hi = 1.3, 1.6
    assert top(lo) < 0 < top(hi)
    while hi - lo > 1e-4:
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if top(mid) < 0 else (lo, mid)
    assert round(0.5 * (lo + hi), 3) == 1.343
    assert AFP["delta_or_range"]["total_cap"] <= 0.5 * (lo + hi)


def test_declared_card_refused_in_registered_run():
    with pytest.raises(D.DeclaredInRegisteredRun):
        D.play(
            {"reduced dark respiration": [0.1]}, V.REGISTERED, ALGAL, registered=True
        )
    # positive controls: the page (unregistered) allows it; DEMONSTRATED plays registered
    inp, org, _ = D.play(
        {"reduced dark respiration": [0.1]}, V.REGISTERED, ALGAL, registered=False
    )
    assert org.r_d == pytest.approx(0.024)
    inp, org, clips = D.play(
        {"antifreeze proteins": [0.8, 0.8]}, V.REGISTERED, ALGAL, registered=True
    )
    assert inp.T_freeze_K == pytest.approx(273.15 - 1.3)
    assert clips == ["antifreeze proteins: total 1.6 K clipped at 1.3"]
