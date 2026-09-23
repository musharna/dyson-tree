"""The §6 hand rows and the §4 census, recomputed from the committed table.

WHAT THIS CAN AND CANNOT CATCH (§6, stated in the spec itself): it recomputes every
row FROM `sim/spectral_table.csv` and matches the spec's printed digits, which proves
the rows follow from the table. It CANNOT catch a wrongly generated table, because
`tools/q4_hand_rows.py` and this test share it. That is
`tests/test_spectral_table.py::test_regenerate_spectral_table`'s job.

The second guard is the literal SMELL test: no float literal in `q4_hand_rows.py`
equals a value the spec's §6 table PRINTS AS A RESULT. It is a smell, not a proof --
`0.16 + 0.001`, `float("0.161")` or a value read from a file all evade it.
"""

from __future__ import annotations

import ast
import importlib.util
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CALC = ROOT / "tools" / "q4_hand_rows.py"
OUT = ROOT / "tools" / "q4_hand_rows.out"


@pytest.fixture(scope="module")
def q4():
    spec = importlib.util.spec_from_file_location("q4_hand_rows", CALC)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# ---------------------------------------------------------------------------
# §6, the rows. Each tuple is (sigma index, spec's printed digits).
# ---------------------------------------------------------------------------

# P1: law key -> per-sigma (t_m, tau_sw, f_photon, edge_au), spec §6 :520-536.
P1_SPEC = {
    "shell": [
        (4.366, 0.3471, 0.640, 1.2049),
        (2.037, 0.4045, 0.778, 1.2303),
        (0.986, 0.4599, 0.875, 1.2543),
    ],
    "normal": [
        (4.366, 0.3610, None, 1.2111),
        (2.037, 0.4187, None, 1.2365),
        (0.986, 0.4741, None, 1.2605),
    ],
    "arm_i_vapour": [
        (4.366, 0.3108, 0.573, 1.1886),
        (2.037, 0.3621, 0.696, 1.2116),
        (0.986, 0.4115, 0.782, 1.2334),
    ],
    "arm_i_water": [
        (4.366, 0.3259, 0.601, 1.1954),
        (2.037, 0.3797, 0.730, 1.2194),
        (0.986, 0.4316, 0.821, 1.2421),
    ],
    "arm_ii_vapour": [
        (4.366, 0.3108, 0.573, 1.1540),
        (2.037, 0.3621, 0.696, 1.1766),
        (0.986, 0.4115, 0.782, 1.1980),
    ],
    "arm_ii_water": [
        (4.366, 0.3259, 0.601, 1.1668),
        (2.037, 0.3797, 0.730, 1.1914),
        (0.986, 0.4316, 0.821, 1.2146),
    ],
}

# §6 arm (ii) also prints the wall's slab reflectance and the melt door.
P1_ARM_II_SPEC = {
    "arm_ii_vapour": [(0.0752, 0.9983), (0.0776, 0.9971), (0.0799, 0.9958)],
    "arm_ii_water": [(0.0628, 1.0050), (0.0628, 1.0050), (0.0628, 1.0050)],
}

# P2: law key -> (OPAQUE R km, p* Pa, t m, tau_sw, T_int K, FREEZE R km, binding)
P2_SPEC = {
    "shell": (95.6, 816.4, 55.72, 0.1908, 277.20, 532.6, "OPAQUE"),
    "normal": (114.9, 816.6, 67.05, None, None, 642.6, "OPAQUE"),
    "arm_i_vapour": (75.8, 789.6, 42.74, 0.1827, None, 396.2, "OPAQUE"),
    "arm_i_water": (84.0, 800.7, 48.05, 0.1861, None, 453.5, "OPAQUE"),
    "arm_ii_vapour": (102.3, None, 42.74, 0.1827, None, 78.4, "FREEZE"),
    "arm_ii_water": (109.8, 612.9, 48.05, 0.1861, 273.19, 111.6, "OPAQUE"),
}

# §6 arm (ii) FREEZE walls (round 6, conserving balance): t, tau_sw, R_slab_sw, T_shell.
# The water row prints only the FREEZE wall's t (it binds OPAQUE); its R_slab_sw is the
# 0.0628 every water wall carries and T_shell 261.09 K as printed; tau_sw unprinted.
P2_ARM_II_FREEZE_SPEC = {
    "arm_ii_vapour": (34.2, 0.1930, 0.0703, 260.57),
    "arm_ii_water": (48.7, None, 0.0628, 261.09),
}

P2_FLOOR_ARM_SPEC = {0.50: 10.6, 0.10: 777.5}
P2_CENTRAL_SPEC = 119.3
P2_FREEZE_PSTAR_PA = 611.21
P2_FREEZE_TAU_SHELL = 0.1227
P2_FREEZE_T_M_SHELL = 232.5

# §4: law -> (FREEZE, STARVE, OPAQUE, HELD, min margin, node, min f_photon)
CENSUS_SPEC = {
    "shell": (52816, 0, 394, 6481, 1.826, (0.7, 1.09, 794.0, 0.094), 0.0579),
    "normal": (52668, 0, 359, 6664, 1.874, None, 0.0667),
}
REF_STATE_SPEC = {"shell": (294.37, 0.391, 9.12), "normal": (294.92, 0.414, 9.21)}


def _laws(q4):
    return {
        "shell": (q4.TAU_SHELL, q4.FPH_SHELL, None),
        "normal": (q4.TAU_NORMAL, q4.FPH_NORMAL, None),
        "arm_i_vapour": (q4.TAU_FVAP, q4.FPH_FVAP, None),
        "arm_i_water": (q4.TAU_FWAT, q4.FPH_FWAT, None),
        "arm_ii_vapour": (q4.TAU_FVAP, q4.FPH_FVAP, q4.R_SLAB_VAPOUR),
        "arm_ii_water": (q4.TAU_FWAT, q4.FPH_FWAT, q4.R_SLAB_WATER),
    }


def _digits(x: float) -> int:
    """Places printed after the point, so the tolerance IS the spec's printed digits."""
    s = f"{x!r}"
    return len(s.split(".")[1]) if "." in s else 0


def _matches(got: float, spec: float) -> bool:
    return round(got, _digits(spec)) == spec


@pytest.mark.parametrize("law", sorted(P1_SPEC))
def test_p1_rows(q4, law):
    tau_fn, fph_fn, rs_fn = _laws(q4)[law]
    for i, sigma in enumerate(q4.SIGMAS_PA):
        t, tau, edge, door = q4.p1_edge(sigma, tau_fn, rs_fn)
        t_spec, tau_spec, fph_spec, edge_spec = P1_SPEC[law][i]
        assert _matches(t, t_spec), f"{law} sigma{i}: t {t:.3f} vs {t_spec}"
        assert _matches(tau, tau_spec), (
            f"{law} sigma{i}: tau_sw {tau:.4f} vs {tau_spec}"
        )
        assert _matches(edge, edge_spec), (
            f"{law} sigma{i}: edge {edge:.4f} vs {edge_spec}"
        )
        if fph_spec is not None:
            fph = fph_fn(t)
            assert _matches(fph, fph_spec), (
                f"{law} sigma{i}: f_photon {fph:.3f} vs {fph_spec}"
            )
        # the closed-form edge and the full fixed-point root-find agree to 4 dp
        root = q4.p1_edge_rootfind(sigma, tau_fn, rs_fn)
        assert round(root, 4) == round(edge, 4), (
            f"{law} sigma{i}: root {root} vs {edge}"
        )


@pytest.mark.parametrize("law", sorted(P1_ARM_II_SPEC))
def test_p1_arm_ii_slab_and_door(q4, law):
    tau_fn, _, rs_fn = _laws(q4)[law]
    for i, sigma in enumerate(q4.SIGMAS_PA):
        t, _, _, door = q4.p1_edge(sigma, tau_fn, rs_fn)
        rsl_spec, door_spec = P1_ARM_II_SPEC[law][i]
        rsl = rs_fn(t)
        assert _matches(rsl, rsl_spec), (
            f"{law} sigma{i}: R_slab_sw {rsl:.4f} vs {rsl_spec}"
        )
        assert _matches(door, door_spec), (
            f"{law} sigma{i}: melt door {door:.4f} vs {door_spec}"
        )


@pytest.mark.parametrize("law", sorted(P2_SPEC))
def test_p2_rows(q4, law):
    tau_fn, fph_fn, rs_fn = _laws(q4)[law]
    r_op = q4.p2_crossing(tau_fn, fph_fn, rs_fn, mode="OPAQUE")
    r_fr = q4.p2_crossing(tau_fn, fph_fn, rs_fn, mode="FREEZE")
    po, to, tauo, tio, _, _ = q4.p2_state(r_op, tau_fn, fph_fn, rs_fn)
    op_spec, p_spec, t_spec, tau_spec, tint_spec, fr_spec, binding_spec = P2_SPEC[law]

    assert _matches(r_op / 1e3, op_spec), (
        f"{law}: OPAQUE R {r_op / 1e3:.1f} vs {op_spec}"
    )
    assert _matches(r_fr / 1e3, fr_spec), (
        f"{law}: FREEZE R {r_fr / 1e3:.1f} vs {fr_spec}"
    )
    assert _matches(to, t_spec), f"{law}: t {to:.2f} vs {t_spec}"
    if p_spec is not None:
        assert _matches(po, p_spec), f"{law}: p* {po:.1f} vs {p_spec}"
    if tau_spec is not None:
        assert _matches(tauo, tau_spec), f"{law}: tau_sw {tauo:.4f} vs {tau_spec}"
    if tint_spec is not None:
        assert _matches(tio, tint_spec), f"{law}: T_int {tio:.2f} vs {tint_spec}"
    binding = "OPAQUE" if r_op < r_fr else "FREEZE"
    assert binding == binding_spec, f"{law}: binding {binding} vs {binding_spec}"


def test_p2_registered_freeze_wall(q4):
    """The registered FREEZE row's wall: p* = p_sat(0 C), t 232.5 m, tau_sw 0.1227."""
    r_fr = q4.p2_crossing(q4.TAU_SHELL, q4.FPH_SHELL, None, mode="FREEZE")
    p, t, tau, _, _, _ = q4.p2_state(r_fr, q4.TAU_SHELL, q4.FPH_SHELL, None)
    assert _matches(p, P2_FREEZE_PSTAR_PA), f"p* {p:.2f}"
    assert _matches(t, P2_FREEZE_T_M_SHELL), f"t {t:.1f}"
    assert _matches(tau, P2_FREEZE_TAU_SHELL), f"tau_sw {tau:.4f}"


@pytest.mark.parametrize("law", sorted(P2_ARM_II_FREEZE_SPEC))
def test_p2_arm_ii_freeze_wall(q4, law):
    tau_fn, fph_fn, rs_fn = _laws(q4)[law]
    r_fr = q4.p2_crossing(tau_fn, fph_fn, rs_fn, mode="FREEZE")
    _, t, tau, _, _, t_shell = q4.p2_state(r_fr, tau_fn, fph_fn, rs_fn)
    t_spec, tau_spec, rsl_spec, tshell_spec = P2_ARM_II_FREEZE_SPEC[law]
    assert _matches(t, t_spec), f"{law}: t {t:.1f} vs {t_spec}"
    if tau_spec is not None:
        assert _matches(tau, tau_spec), f"{law}: tau_sw {tau:.4f} vs {tau_spec}"
    assert _matches(rs_fn(t), rsl_spec), (
        f"{law}: R_slab_sw {rs_fn(t):.4f} vs {rsl_spec}"
    )
    assert _matches(t_shell, tshell_spec), (
        f"{law}: T_shell {t_shell:.2f} vs {tshell_spec}"
    )


@pytest.mark.parametrize("floor", sorted(P2_FLOOR_ARM_SPEC))
def test_p2_f_floor_arms(q4, floor):
    r_op = q4.p2_crossing(q4.TAU_SHELL, q4.FPH_SHELL, None, floor=floor, mode="OPAQUE")
    assert _matches(r_op / 1e3, P2_FLOOR_ARM_SPEC[floor])


def test_p2_f_floor_010_window_is_the_freeze_edge(q4):
    """§6: 'R_window for 0.10 = 532.6 km, FREEZE' -- the OPAQUE crossing is past it."""
    r_op = q4.p2_crossing(q4.TAU_SHELL, q4.FPH_SHELL, None, floor=0.10, mode="OPAQUE")
    r_fr = q4.p2_crossing(q4.TAU_SHELL, q4.FPH_SHELL, None, mode="FREEZE")
    assert r_fr < r_op
    assert _matches(r_fr / 1e3, P2_SPEC["shell"][5])


def test_p2_central_variant(q4):
    from scipy.optimize import brentq

    r = brentq(
        lambda rr: (
            q4.FPH_NORMAL(q4.p2_state(rr, q4.TAU_SHELL, q4.FPH_SHELL)[1]) - q4.F_FLOOR
        ),
        1e2,
        5e6,
        xtol=0.1,
    )
    assert _matches(r / 1e3, P2_CENTRAL_SPEC), (
        f"central {r / 1e3:.1f} vs {P2_CENTRAL_SPEC}"
    )


@pytest.mark.parametrize("law", sorted(REF_STATE_SPEC))
def test_section4_reference_state(q4, law):
    """§4: at 1 AU, R = 10 km the other lines HOLD -- 294.37 K / 0.391 / +9.12."""
    tau_fn, fph_fn, _ = _laws(q4)[law]
    _, t, _, t_int, _ = q4.fixed_point(1.0, q4.R_FIXED_M, q4.SIGMAS_PA[0], tau_fn)
    fp = fph_fn(t)
    margin = q4.net_carbon(1.0, t_int, fp)
    tint_spec, fp_spec, margin_spec = REF_STATE_SPEC[law]
    assert _matches(t_int, tint_spec), f"{law}: T_int {t_int:.2f} vs {tint_spec}"
    assert _matches(fp, fp_spec), f"{law}: f_photon {fp:.3f} vs {fp_spec}"
    assert _matches(margin, margin_spec), (
        f"{law}: STARVE {margin:+.2f} vs {margin_spec}"
    )


def test_section4_starve_floor(q4):
    """§4: STARVE at 273.15 K needs f_photon 0.0007, far under the grid minimum."""
    from sim.physiology import irradiance, respiration
    from sim.thermal import temperature_response_gaussian

    o = q4.ORG
    r_over = (
        respiration(o.r_d, q4.T_FREEZE)
        / o.leaf_mass_ratio
        / temperature_response_gaussian(q4.T_FREEZE, q4.T_OPT, q4.OMEGA)
    )
    i_need = o.k * r_over / (o.a_max - r_over)
    f_need = i_need / irradiance((2**0.25 * q4.T_EQ_1AU / q4.T_FREEZE) ** 2)
    assert round(f_need, 4) == 0.0007, f"f_photon needed {f_need:.5f}"
    assert f_need < CENSUS_SPEC["shell"][6]


def test_grid_shape(q4):
    assert len(q4.GRID_R_AU) == 197
    assert len(q4.GRID_R_M) == 101
    assert len(q4.GRID_R_AU) * len(q4.GRID_R_M) * len(q4.SIGMAS_PA) == 59691
    assert q4.GRID_R_AU[0] == 1.04 and q4.GRID_R_AU[-1] == 3.00
    assert q4.GRID_R_M[0] == 10.0 and q4.GRID_R_M[-1] == 1e6


@pytest.mark.slow
@pytest.mark.parametrize("law", sorted(CENSUS_SPEC))
def test_section4_census(q4, law):
    """The 59,691-node scan. Minutes, so it is opt-in: `pytest -m slow`.

    `test_committed_output_matches_the_census` is the always-on half: it asserts the
    committed `.out` carries these same numbers, so a census that drifted would have
    to drift in BOTH the code and the checked-in record to pass unnoticed.
    """
    tau_fn, fph_fn, _ = _laws(q4)[law]
    tf, ff = q4.tabulate_in_t(tau_fn, fph_fn)
    counts, _, n_warm, margin, node, min_fp = q4.census(tf, ff)
    fr, st, op, held, margin_spec, node_spec, minfp_spec = CENSUS_SPEC[law]
    assert (counts["FREEZE"], counts["STARVE"], counts["OPAQUE"], counts["HELD"]) == (
        fr,
        st,
        op,
        held,
    )
    assert n_warm == 0, "a STARVE violation with FREEZE holding would be a finding"
    assert _matches(margin, margin_spec), f"{law}: min STARVE margin {margin:+.4f}"
    assert _matches(min_fp, minfp_spec), f"{law}: min f_photon {min_fp:.4f}"
    if node_spec is not None:
        assert (round(node[0], 1), round(node[1], 2)) == node_spec[:2]


def test_committed_output_matches_the_census():
    """The committed `.out` carries the §4 counts the spec prints."""
    assert OUT.exists(), "tools/q4_hand_rows.out is not committed"
    text = OUT.read_text()
    for law, (fr, st, op, held, margin, _, min_fp) in CENSUS_SPEC.items():
        m = re.search(
            rf"^  {law}: first-violated FREEZE (\d+)\s+STARVE (\d+)\s+OPAQUE (\d+)\s+HELD (\d+)",
            text,
            re.M,
        )
        assert m, f"no census line for {law} in the committed output"
        assert tuple(int(g) for g in m.groups()) == (fr, st, op, held), (
            f"{law}: committed output has {m.groups()}, spec {(fr, st, op, held)}"
        )
        tail = text[m.end() :]
        got_margin = float(
            re.search(
                r"min STARVE margin with FREEZE holding ([-+][\d.]+) umol", tail
            ).group(1)
        )
        got_fp = float(re.search(r"grid minimum f_photon ([\d.]+)", tail).group(1))
        assert _matches(got_margin, margin), (
            f"{law}: committed output's min STARVE margin {got_margin:+.4f},"
            f" spec {margin:+.3f}"
        )
        assert _matches(got_fp, min_fp), (
            f"{law}: committed output's min f_photon {got_fp:.4f}, spec {min_fp:.4f}"
        )


# ---------------------------------------------------------------------------
# The literal smell test.
# ---------------------------------------------------------------------------

# The §6 table's RESULTS: every value it prints that the calculator must DERIVE.
# The declared INPUTS of the "fixed" column (sigma 0.7 / 1.5 / 3.1 MPa, R 10 km,
# r 1.10 AU, f_floor 0.25 / 0.50 / 0.10) are excluded -- a registration types its
# inputs, and a test that forbade them would forbid the registration. The smell
# this catches is a hard-coded ANSWER.
FORBIDDEN_LITERALS = {
    # P1 walls, tau_sw, f_photon, edges (all six laws)
    611.21,
    4.366,
    0.3471,
    0.640,
    1.2049,
    2.037,
    0.4045,
    0.778,
    1.2303,
    0.986,
    0.4599,
    0.875,
    1.2543,
    0.3610,
    0.4187,
    0.4741,
    1.2111,
    1.2365,
    1.2605,
    0.3108,
    0.573,
    1.1886,
    0.3621,
    0.696,
    1.2116,
    0.4115,
    0.782,
    1.2334,
    0.3259,
    0.601,
    1.1954,
    0.3797,
    0.730,
    1.2194,
    0.4316,
    0.821,
    1.2421,
    1.1540,
    1.1766,
    1.1980,
    1.1668,
    1.1914,
    1.2146,
    0.0752,
    0.0776,
    0.0799,
    0.0628,
    0.9983,
    0.9971,
    0.9958,
    1.0050,
    # P2
    816.4,
    55.72,
    0.1908,
    277.20,
    95.6,
    232.5,
    0.1227,
    532.6,
    10.6,
    777.5,
    816.6,
    67.05,
    114.9,
    642.6,
    119.3,
    789.6,
    42.74,
    0.1827,
    75.8,
    396.2,
    173.0,
    800.7,
    48.05,
    0.1861,
    84.0,
    453.5,
    198.0,
    34.2,
    0.1930,
    0.0703,
    260.57,
    78.4,
    102.3,
    612.9,
    273.19,
    261.09,
    48.7,
    109.8,
    111.6,
    # §4 census and reference state
    52816.0,
    394.0,
    6481.0,
    52668.0,
    359.0,
    6664.0,
    1.826,
    1.874,
    0.0579,
    0.0667,
    294.37,
    0.391,
    9.12,
}


def test_no_printed_table_value_is_a_literal():
    """A smell, not a proof: `0.16 + 0.001` or a value read from a file evade it."""
    tree = ast.parse(CALC.read_text())
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            if (
                not isinstance(node.value, bool)
                and float(node.value) in FORBIDDEN_LITERALS
            ):
                hits.append((node.lineno, node.value))
    assert not hits, "a §6 result is hard-coded in tools/q4_hand_rows.py: " + ", ".join(
        f"line {ln}: {v!r}" for ln, v in hits
    )


def test_smell_test_can_fail(tmp_path):
    """Positive control: the smell test must trip on a planted literal.

    An assertion that has never been seen to fail is not a check. This plants
    `1.2049` -- P1's registered sigma 0.7 edge -- into a copy of the calculator and
    asserts the same AST walk finds it.
    """
    planted = tmp_path / "planted.py"
    planted.write_text(CALC.read_text() + "\n_PLANTED_EDGE = 1.2049\n")
    tree = ast.parse(planted.read_text())
    hits = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, float)
        and n.value in FORBIDDEN_LITERALS
    ]
    assert hits == [1.2049], f"planted literal not caught: {hits}"


def test_imports_nothing_from_sim_vessel():
    """§6's import guard, this half: the calculator must not touch sim/vessel.py."""
    src = CALC.read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                assert "vessel" not in a.name, f"imports {a.name}"
        elif isinstance(node, ast.ImportFrom):
            assert "vessel" not in (node.module or ""), f"imports from {node.module}"
    # M1a's version of this guard is bidirectional and walks both import closures,
    # with a negative case per direction; it cannot be written until sim/vessel.py
    # exists. What is testable today is the half that does: this file's own imports,
    # plus the fact that the module it must not read is not yet in the tree.
    assert not (ROOT / "sim" / "vessel.py").exists(), (
        "sim/vessel.py now exists -- replace this with M1a's bidirectional AST guard"
    )
    planted = ast.parse(src + "\nfrom sim.vessel import wall_thickness\n")
    caught = [
        n.module
        for n in ast.walk(planted)
        if isinstance(n, ast.ImportFrom) and "vessel" in (n.module or "")
    ]
    assert caught == ["sim.vessel"], "the guard cannot see the edge it forbids"


def test_reads_only_the_spectral_table():
    """Every file the calculator opens is the one committed table."""
    tree = ast.parse(CALC.read_text())
    literals = [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and (
            n.value.endswith(".csv")
            or n.value.endswith(".yaml")
            or n.value.endswith(".out")
        )
    ]
    assert literals == ["spectral_table.csv"], f"opens {literals}"


def test_output_is_committed_and_current(q4):
    """The `.out` beside the calculator is the record; its digest must be the table's."""
    text = OUT.read_text()
    assert q4.table_digest() in text, "committed output was produced from another table"
    assert "b31870bd3500b58414100af7e4b0e04c" in text
    assert "cf5f76d58a31aa5f994fa038c390a856" in text
    assert "trapezoid" in text


# IRON_LAW_OK


def test_reproduce_hand_rows(q4):
    """§8's named acceptance: every §6 row and the §4 reference state, in one test.

    The parametrized tests above are the same checks split so a failure names the
    row; this is the single assertion the spec's acceptance clause asks for. The
    59,691-node census half is `test_section4_census` (marked `slow`) with
    `test_committed_output_matches_the_census` as its always-on record check.
    """
    for law in P1_SPEC:
        test_p1_rows(q4, law)
    for law in P1_ARM_II_SPEC:
        test_p1_arm_ii_slab_and_door(q4, law)
    for law in P2_SPEC:
        test_p2_rows(q4, law)
    for law in P2_ARM_II_FREEZE_SPEC:
        test_p2_arm_ii_freeze_wall(q4, law)
    for floor in P2_FLOOR_ARM_SPEC:
        test_p2_f_floor_arms(q4, floor)
    test_p2_registered_freeze_wall(q4)
    test_p2_f_floor_010_window_is_the_freeze_edge(q4)
    test_p2_central_variant(q4)
    for law in REF_STATE_SPEC:
        test_section4_reference_state(q4, law)
    test_section4_starve_floor(q4)


# ---------------------------------------------------------------------------
# The smell test covers the prereg: every result the prereg freezes is forbidden.
# ---------------------------------------------------------------------------
PREREG = ROOT / "experiments" / "q4_vessel" / "prereg.yaml"
PREREG_RESULT_SECTIONS = ("registered_rows", "control", "variants", "fresnel_arm")


def _prereg_results(prereg):
    """Every float the prereg records as a RESULT (inputs like n_interior excluded)."""
    out = set()

    def walk(x, key=None):
        if isinstance(x, dict):
            for k, v in x.items():
                walk(v, k)
        elif isinstance(x, list):
            for v in x:
                walk(v, key)
        elif isinstance(x, float) and key not in ("n_interior",):
            out.add(x)

    for sec in PREREG_RESULT_SECTIONS:
        walk(prereg[sec])
    return out


def _uncovered(prereg):
    return sorted(_prereg_results(prereg) - FORBIDDEN_LITERALS)


def test_smell_test_covers_the_prereg():
    import yaml

    prereg = yaml.safe_load(PREREG.read_text())
    assert _prereg_results(prereg), "parsed no results from the prereg"
    missing = _uncovered(prereg)
    assert not missing, f"prereg results the smell test does not forbid: {missing}"
    # negative control: a prereg result outside the forbidden set must be reported
    prereg["fresnel_arm"][2]["edge_au"][0] = 1.1430
    assert _uncovered(prereg) == [1.143], "coverage check cannot see a new result"
