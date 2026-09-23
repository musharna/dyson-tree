"""M1a: `sim/vessel.py` against the §3-§6 rows (northstar design §8, M1a bullet).

The expected digits come from TWO places, both outside `sim/`: the spec's printed text
(typed here, as test data) and `tools/q4_hand_rows.out`, the committed hand-row record
(parsed here). `sim/vessel.py` may read neither; the import guard below holds that.
A match is `round(got, printed_places) == printed`: the tolerance IS the printed digits.
"""

from __future__ import annotations

import ast
import hashlib
import math
import re
from pathlib import Path

import pytest

from sim import vessel as V
from sim.organism import ALGAL, compensation_irradiance
from sim.physiology import irradiance

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tools" / "q4_hand_rows.out"
PREREG = ROOT / "experiments" / "q4_vessel" / "prereg.yaml"
VESSEL_SRC = ROOT / "sim" / "vessel.py"
CALC_SRC = ROOT / "tools" / "q4_hand_rows.py"
PREREG_MD5 = "d8707a6607db6d54a006e14af9dcfe79"  # at M1a0 (509dfac)

SIGMAS = V.SIGMAS_PA
R_P1 = 10e3
R_P2_AU, SIGMA_P2 = 1.10, 0.7e6


def _places(s: str) -> int:
    return len(s.split(".")[1]) if "." in s else 0


def match(got: float, printed: str) -> bool:
    return round(got, _places(printed)) == float(printed)


def check(got, printed, what):
    assert match(got, printed), f"{what}: vessel {got!r} vs printed {printed}"


# ---------------------------------------------------------------- the .out, parsed
LAW_KEYS = {
    "registered, shell law": ("shell", 1.0, "0"),
    "control, normal incidence": ("normal", 1.0, "0"),
    "arm (i) vapour": ("shell+fresnel", 1.0, "0"),
    "arm (i) water": ("shell+fresnel", 1.333, "0"),
    "arm (ii) vapour": ("shell+fresnel", 1.0, "slab"),
    "arm (ii) water": ("shell+fresnel", 1.333, "slab"),
}


def _law_of(label: str):
    for key, triple in LAW_KEYS.items():
        if key in label:
            return key, triple
    raise KeyError(label)


def _parse_out():
    text = OUT.read_text()
    p1, p2 = {}, {}
    cur = None
    for ln in text.splitlines():
        m = re.match(r"^  (P[12]) (.+)$", ln)
        if m and ("registered" in ln or "control" in ln or "arm (" in ln):
            cur = (m.group(1), _law_of(m.group(2))[0])
            (p1 if cur[0] == "P1" else p2)[cur[1]] = []
            continue
        if cur and cur[0] == "P1":
            m = re.match(
                r"^\s+sigma (\S+) MPa: p (\S+) Pa  t (\S+) m  tau_sw (\S+)  f_photon (\S+)"
                r"  R_slab_sw (\S+)  melt door (\S+) AU  edge (\S+) AU",
                ln,
            )
            if m:
                p1[cur[1]].append(
                    dict(zip("sigma p t tau fph rslab door edge".split(), m.groups()))
                )
        if cur and cur[0] == "P2":
            m = re.match(
                r"^\s+OPAQUE R (\S+) km: p\* (\S+) Pa  t (\S+) m  tau_sw (\S+)"
                r"  T_int (\S+) K  T_shell (\S+) K  R_slab_sw (\S+)  STARVE (\S+)",
                ln,
            )
            if m:
                p2[cur[1]].append(
                    dict(zip("R p t tau tint tshell rslab starve".split(), m.groups()))
                )
            m = re.match(
                r"^\s+FREEZE R (\S+) km: p\* (\S+) Pa  t (\S+) m  tau_sw (\S+)"
                r"  T_shell (\S+) K  R_slab_sw (\S+)",
                ln,
            )
            if m:
                p2[cur[1]].append(
                    dict(zip("R p t tau tshell rslab".split(), m.groups()))
                )
            m = re.match(r"^\s+R_window (\S+) km, binding (\w+)", ln)
            if m:
                p2[cur[1]].append({"window": m.group(1), "binding": m.group(2)})
    floors = {
        f: (a, b, c)
        for f, a, b, c in re.findall(
            r"P2 arm f_floor (\S+): OPAQUE crossing R (\S+) km;\s+R_window (\S+) km \((\w+)\)",
            text,
        )
    }
    central = re.search(r"interior `central`.*: R (\S+) km", text).group(1)
    ref = dict(
        re.findall(
            r"^  (shell|normal): (T_int \S+ K  f_photon \S+  STARVE \S+) umol",
            text,
            re.M,
        )
    )
    starve_edge = re.search(
        r"STARVE margin at the sigma 0.7 edge: (\S+) umol", text
    ).group(1)
    consts = {
        "T_eq": re.search(r"T_eq\(1 AU, area_ratio 4\) = (\S+) K", text).group(1),
        "door": re.search(r"melt door, albedo 0: (\S+) AU", text).group(1),
        "T1_shell": re.search(r"T_shell law T\(1\) = (\S+);", text).group(1),
        "T1_vap": re.search(r"multi-pass T\(1\): vapour (\S+)", text).group(1),
        "T1_wat": re.search(r"multi-pass T\(1\): vapour \S+  water (\S+)", text).group(
            1
        ),
        "ceiling": re.search(r"tau=1 ceiling edge: (\S+) AU", text).group(1),
    }
    return p1, p2, floors, central, ref, starve_edge, consts


P1_OUT, P2_OUT, FLOORS_OUT, CENTRAL_OUT, REF_OUT, STARVE_EDGE_OUT, CONSTS_OUT = (
    _parse_out()
)


def test_out_parsed_completely():
    """The parser saw every row: 6 laws x 3 sigmas for P1, 6 laws x 3 lines for P2."""
    assert sorted(P1_OUT) == sorted(LAW_KEYS) and all(
        len(v) == 3 for v in P1_OUT.values()
    )
    assert sorted(P2_OUT) == sorted(LAW_KEYS) and all(
        len(v) == 3 for v in P2_OUT.values()
    )
    assert set(FLOORS_OUT) == {"0.50", "0.10"} and set(REF_OUT) == {"shell", "normal"}


def inputs_for(law_key, **kw):
    law, n_int, thermal = LAW_KEYS[law_key]
    return V.VesselInputs(
        optical_law=law, n_interior=n_int, thermal_reflectance=thermal, **kw
    )


# ---------------------------------------------------------------- §3 the laws
def test_shell_law_values():
    check(V.shell_transmission(1.0), CONSTS_OUT["T1_shell"], "T(1) shell")
    check(V.shell_transmission(1.0), "0.3001", "T(1) spec")
    for kt, printed in (
        (0.1, "0.8857"),
        (0.5, "0.5463"),
        (2.0, "0.0920"),
        (5.0, "0.0030"),
    ):
        check(V.shell_transmission(kt), printed, f"T({kt})")
    check(V.shell_transmission(1.0, "normal"), "0.3679", "e^-1")
    check(
        V.shell_transmission(1.0, "shell+fresnel", 1.0),
        CONSTS_OUT["T1_vap"],
        "T(1) vap",
    )
    check(
        V.shell_transmission(1.0, "shell+fresnel", 1.333),
        CONSTS_OUT["T1_wat"],
        "T(1) wat",
    )


@pytest.mark.parametrize("n_int", [1.000, 1.333])
def test_slab_reflectance_plus_transmission_is_one_at_zero_depth(n_int):
    total = V.slab_reflectance(0.0, n_int) + V.shell_transmission(
        0.0, "shell+fresnel", n_int
    )
    assert abs(total - 1.0) < 1e-6, f"n_interior {n_int}: R_slab + T = {total!r}"
    # positive control: an absorbing slab does NOT sum to 1
    thick = V.slab_reflectance(1.0, n_int) + V.shell_transmission(
        1.0, "shell+fresnel", n_int
    )
    assert thick < 0.5


def test_gate_b_identity():
    """Gate B demoted to identity: one k under each law equals the law itself."""
    k, t = 0.38623, 3.0
    assert V.transmission_spectrum(t, k=[k], optical_law="normal")[0] == pytest.approx(
        math.exp(-k * t), rel=1e-15
    )
    assert V.transmission_spectrum(t, k=[k], optical_law="shell")[
        0
    ] == V.shell_transmission(k * t)


def test_gate_a_and_c():
    t_eq = V.equilibrium_temperature(1.0, V.SPHERE_AREA_RATIO)
    assert 275 <= t_eq <= 282
    check(t_eq, CONSTS_OUT["T_eq"], "T_eq(1 AU)")
    assert abs(V.saturation_pressure(273.16) - 611.657) <= 0.01
    assert abs(V.saturation_pressure(273.15 + 5.16) - 882.0) <= 0.5
    check(V.saturation_pressure(273.16), "611.654", "Buck at the triple point")


def test_same_object():
    """§3/§10: a strength and an optics input must describe one material, by id."""
    assert V.assert_same_object("sigma_ice", "k_ice") == "ice"
    with pytest.raises(ValueError, match="different objects"):
        V.assert_same_object("sigma_wood", "k_ice")
    assert V.WALL_INPUTS == ("sigma_ice", "k_ice") and V.WALL_MATERIAL == "ice"


def test_registry_keys_equal_prereg():
    import dataclasses

    import yaml

    reg = yaml.safe_load(PREREG.read_text())["registry"]
    assert [f.name for f in dataclasses.fields(V.VesselInputs)] == list(reg)
    d = V.REGISTERED
    assert (d.t_opt_K, d.omega_K, d.albedo, d.emissivity, d.f_floor, d.n) == (
        reg["t_opt_K"],
        reg["omega_K"],
        reg["albedo"],
        reg["emissivity"],
        reg["f_floor"],
        reg["n"],
    )
    assert (d.interior, d.dust, d.T_freeze_K, d.optical_law) == (
        reg["interior"],
        reg["dust"],
        reg["T_freeze_K"],
        reg["optical_law"],
    )
    assert d.n_interior == reg["n_interior"]["vapour"]
    assert d.thermal_reflectance == reg["thermal_reflectance"]["registered"]


def test_self_consistent_pressure_at_1au():
    """§3: 3.330 / 2.899 / 2.521 kPa (walls 5.37 / 9.66 / 18.01 m) shell; 3453.08 /
    3002.39 / 2606.63 Pa normal incidence."""
    shell = [("3.330", "5.37"), ("2.899", "9.66"), ("2.521", "18.01")]
    normal = ["3453.08", "3002.39", "2606.63"]
    for s, (kpa, wall), npa in zip(sorted(SIGMAS, reverse=True), shell, normal):
        p = V.self_consistent_pressure(1.0, R_P1, s)
        check(p / 1e3, kpa, f"p* shell sigma {s}")
        check(V.wall_thickness(p, R_P1, s), wall, f"t_min shell sigma {s}")
        check(
            V.self_consistent_pressure(1.0, R_P1, s, optical_law="normal"),
            npa,
            "p* normal",
        )


def test_fixed_point_raises_on_exhaustion():
    with pytest.raises(V.ConvergenceError, match="did not converge"):
        V.self_consistent_pressure(1.10, 1e3, 0.7e6, max_iter=3)


def test_closed_form_controls():
    """§3: (a) mixed port-regression, (b) scalar limit end to end; each names its path."""
    k, tau_min = 0.38623, 0.01
    order = (3.1e6, 1.5e6, 0.7e6)
    mixed = {3.1e6: "21.41", 1.5e6: "11.91", 0.7e6: "6.40"}
    scalar_p = {3.1e6: "2346.3", 1.5e6: "1581.2", 0.7e6: "1103.6"}
    scalar_r = {3.1e6: "31.51", 1.5e6: "22.62", 0.7e6: "15.13"}
    for s in order:
        p_mixed = V.self_consistent_pressure(1.0, R_P1, s, optical_law="normal")
        check(
            V.closed_form_r_max(s, p_mixed, k, tau_min) / 1e3,
            mixed[s],
            f"(a) sigma {s}",
        )
        p_scalar = V.self_consistent_pressure(1.0, R_P1, s, scalar_k=k)
        check(p_scalar, scalar_p[s], f"(b) p* sigma {s}")
        r_scalar = V.closed_form_r_max(s, p_scalar, k, tau_min)
        check(r_scalar / 1e3, scalar_r[s], f"(b) R_max sigma {s}")
        # the scalar-limit path fails (a): each control names which path it exercises
        assert not match(r_scalar / 1e3, mixed[s])


def test_page_defaults():
    """§4/§5 at 1 km, 1.10 AU, 0.7 MPa: p* 1960.5, t_min 1.400, tau_sw 0.4331, T_int
    290.34, f_photon 0.8327, I_wall 1660.1, STARVE +8.23; normal 2033.6 / 1.453 / 0.4445."""
    p, t, rep = V.auto_state(1.10, 1e3, 0.7e6, ALGAL)
    check(p, "1960.5", "p*")
    check(t, "1.400", "t_min")
    check(V.solar_transmission(t), "0.4331", "tau_sw")
    check(rep.T_int, "290.34", "T_int")
    check(rep.f_photon, "0.8327", "f_photon")
    check(irradiance(1.10) * rep.f_photon, "1660.1", "I_wall")
    check(irradiance(1.10), "1993.6", "pre-wall PAR")
    check(rep.lines["STARVE"].margin, "8.23", "STARVE")
    check(compensation_irradiance(ALGAL), "0.492", "I_c")
    assert rep.violated == ()
    assert rep.lines["BURST"].margin == pytest.approx(0.0, abs=1e-6 * 0.7e6)
    pn, tn, _ = V.auto_state(
        1.10, 1e3, 0.7e6, ALGAL, V.VesselInputs(optical_law="normal")
    )
    check(pn, "2033.6", "p* normal")
    check(tn, "1.453", "t_min normal")
    check(V.solar_transmission(tn, optical_law="normal"), "0.4445", "tau_sw normal")


def test_manual_100m_wall_is_opaque():
    """§4: a manual 100 m wall at R = 1 km, 1.10 AU reads f_photon 0.1931, OPAQUE."""
    t = 100.0
    t_int, _ = V.contained_temperature(1.10, t)
    rep = V.classify_failure(V.saturation_pressure(t_int), t, 1.10, 1e3, 0.7e6, ALGAL)
    check(rep.f_photon, "0.1931", "f_photon")
    assert "OPAQUE" in rep.violated


def test_net_carbon_contained_on_organism():
    t = 1.4
    t_int, _ = V.contained_temperature(1.10, t)
    f = V.par_photon_fraction(t)
    assert ALGAL.net_carbon_contained(1.10, t) == V.net_carbon_contained(
        ALGAL, 1.10, t_int, f
    )
    # the existing paths are untouched: a different number from the uncontained model
    assert ALGAL.net_carbon_contained(1.10, t) != ALGAL.net_carbon_adapted(1.10, 1.0)


# ---------------------------------------------------------------- §6 P1 rows
@pytest.mark.parametrize("law_key", sorted(LAW_KEYS))
def test_p1_rows(law_key):
    inp = inputs_for(law_key)
    for i, s in enumerate(SIGMAS):
        row = P1_OUT[law_key][i]
        e = V.r_close(R_P1, s, ALGAL, inp)
        tag = f"P1 {law_key} sigma {row['sigma']}"
        assert e.binding == "FREEZE", f"{tag}: binding {e.binding}"
        check(e.edge, row["edge"], f"{tag} edge")
        p, t, rep = V.auto_state(e.edge, R_P1, s, ALGAL, inp)
        check(p, row["p"], f"{tag} p*")
        check(t, row["t"], f"{tag} t")
        check(V.solar_transmission(t, **inp.optics()), row["tau"], f"{tag} tau_sw")
        check(rep.f_photon, row["fph"], f"{tag} f_photon")
        rs = (
            V.solar_slab_reflectance(t, inp.n_interior)
            if inp.thermal_reflectance == "slab"
            else 0.0
        )
        check(rs, row["rslab"], f"{tag} R_slab_sw")
        door = (
            rep.T_shell / V.T_ICE_MELT_K
        ) ** 2 * e.edge  # T_shell ∝ r^-1/2 at fixed t
        check(door, row["door"], f"{tag} melt door")
        assert "OPAQUE" not in rep.violated and "STARVE" not in rep.violated
        if law_key == "registered, shell law" and i == 0:
            check(rep.lines["STARVE"].margin, STARVE_EDGE_OUT, "STARVE at the P1 edge")


def test_melt_door_falls_out_of_sigma_eff():
    """§4: 1.0381 AU is where σ_eff(T_shell) goes to 0, not a stored number."""
    t = 4.366
    lo, hi = 1.0, 1.1
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        rep = V.classify_failure(611.21, t, mid, R_P1, 0.7e6, ALGAL)
        lo, hi = (lo, mid) if rep.sigma_eff > 0 else (mid, hi)
    check(hi, CONSTS_OUT["door"], "melt door")


def test_tau_one_ceiling():
    check(
        (2**0.25 * V.equilibrium_temperature(1.0, 4) / 273.15) ** 2,
        CONSTS_OUT["ceiling"],
        "ceiling",
    )


# ---------------------------------------------------------------- §6 P2 rows
@pytest.mark.parametrize("law_key", sorted(LAW_KEYS))
def test_p2_rows(law_key):
    inp = inputs_for(law_key)
    opaque, freeze, window = P2_OUT[law_key]
    e = V.r_window(R_P2_AU, SIGMA_P2, ALGAL, inp)
    tag = f"P2 {law_key}"
    assert e.binding == window["binding"], f"{tag}: binding {e.binding}"
    check(e.edge / 1e3, window["window"], f"{tag} R_window")
    r_op = e.roots.get("OPAQUE", e.counterfactual.get("OPAQUE"))
    r_fr = e.roots.get("FREEZE", e.counterfactual.get("FREEZE"))
    check(r_op / 1e3, opaque["R"], f"{tag} OPAQUE R")
    check(r_fr / 1e3, freeze["R"], f"{tag} FREEZE R")
    for row, R in ((opaque, r_op), (freeze, r_fr)):
        p, t, rep = V.auto_state(R_P2_AU, R, SIGMA_P2, ALGAL, inp)
        check(p, row["p"], f"{tag} p* at {row['R']} km")
        check(t, row["t"], f"{tag} t at {row['R']} km")
        check(V.solar_transmission(t, **inp.optics()), row["tau"], f"{tag} tau_sw")
        check(rep.T_shell, row["tshell"], f"{tag} T_shell")
        rs = (
            V.solar_slab_reflectance(t, inp.n_interior)
            if inp.thermal_reflectance == "slab"
            else 0.0
        )
        check(rs, row["rslab"], f"{tag} R_slab_sw")
        if "tint" in row:
            check(rep.T_int, row["tint"], f"{tag} T_int")
            check(rep.lines["STARVE"].margin, row["starve"], f"{tag} STARVE")


def test_p2_arm_ii_water_is_the_tie_clause_live_case():
    """§6: OPAQUE 109.8 and FREEZE 111.6 km share the 100.0-112.2 km bracket."""
    e = V.r_window(R_P2_AU, SIGMA_P2, ALGAL, inputs_for("arm (ii) water"))
    assert set(e.roots) == {"OPAQUE", "FREEZE"}
    check(e.bracket[0] / 1e3, "100.0", "bracket lo")
    check(e.bracket[1] / 1e3, "112.2", "bracket hi")
    assert e.binding == "OPAQUE" and not e.tie


@pytest.mark.parametrize("floor", ["0.50", "0.10"])
def test_p2_f_floor_arms(floor):
    crossing, window, binding = FLOORS_OUT[floor]
    e = V.r_window(R_P2_AU, SIGMA_P2, ALGAL, V.VesselInputs(f_floor=float(floor)))
    assert e.binding == binding
    check(e.edge / 1e3, window, f"f_floor {floor} R_window")
    r_op = e.roots.get("OPAQUE", e.counterfactual.get("OPAQUE"))
    check(r_op / 1e3, crossing, f"f_floor {floor} OPAQUE crossing")


def test_p2_central_variant():
    e = V.r_window(R_P2_AU, SIGMA_P2, ALGAL, V.VesselInputs(interior="central"))
    assert e.binding == "OPAQUE"
    check(e.edge / 1e3, CENTRAL_OUT, "central")


@pytest.mark.parametrize("law", ["shell", "normal"])
def test_section4_reference_state(law):
    tint, fph, starve = re.match(
        r"T_int (\S+) K  f_photon (\S+)  STARVE (\S+)", REF_OUT[law]
    ).groups()
    _, _, rep = V.auto_state(1.0, R_P1, 0.7e6, ALGAL, V.VesselInputs(optical_law=law))
    check(rep.T_int, tint, f"{law} T_int")
    check(rep.f_photon, fph, f"{law} f_photon")
    check(rep.lines["STARVE"].margin, starve, f"{law} STARVE")
    # §4: at 1.00 AU the other lines all HOLD; the wall is water, so BURST alone fires
    assert rep.violated == ("BURST",) and rep.sigma_eff == 0.0


# ---------------------------------------------------------------- §6 tie rule
def test_tie_rule_smallest_root_not_load_order():
    """Both lines hold at node k and violate at k+1; the load-order line (FREEZE) has its
    root DEEPER in the bracket than OPAQUE's. The edge is OPAQUE's root, the smaller."""
    nodes = [1.0, 2.0, 3.0]

    def margins(x):
        return {"FREEZE": 2.8 - x, "STARVE": 1.0, "OPAQUE": 2.2 - x}

    e = V.find_edge(
        nodes,
        margins,
        tie_tol=lambda a, b: abs(a - b) <= 1e-4,
        refine_width=lambda lo, hi: 1e-9,
    )
    assert e.bracket == (2.0, 3.0)
    assert e.binding == "OPAQUE", f"binding {e.binding} at {e.roots}"
    assert e.edge == pytest.approx(2.2, abs=1e-8)
    assert e.roots["FREEZE"] == pytest.approx(2.8, abs=1e-8)
    assert not e.tie
    # within one tolerance, load order decides and both roots are returned
    t = V.find_edge(
        nodes,
        lambda x: {"FREEZE": 2.20005 - x, "STARVE": 1.0, "OPAQUE": 2.2 - x},
        tie_tol=lambda a, b: abs(a - b) <= 1e-4,
        refine_width=lambda lo, hi: 1e-9,
    )
    assert t.tie and t.binding == "FREEZE" and set(t.roots) == {"FREEZE", "OPAQUE"}


def test_edge_rule_empty_window():
    e = V.find_edge(
        [1.0, 2.0],
        lambda x: {"FREEZE": -1.0, "STARVE": 1.0, "OPAQUE": 1.0},
        tie_tol=lambda a, b: False,
        refine_width=lambda lo, hi: 1e-9,
    )
    assert e.edge == 0.0 and e.binding is None


# ---------------------------------------------------------------- §4 runner error
def test_runner_error_mutation_control():
    """§4: sizing the wall at 0.99·t_min at the page defaults trips BURST (707,071 vs
    700,000 Pa) and BOIL (p_sat(T_int) 1965.3 vs p* 1960.5): a RunnerError, exit 2."""
    p = V.self_consistent_pressure(1.10, 1e3, 0.7e6)
    t = 0.99 * V.wall_thickness(p, 1e3, 0.7e6)
    rep = V.classify_failure(p, t, 1.10, 1e3, 0.7e6, ALGAL)
    check(rep.lines["BURST"].lhs, "707071", "hoop at 0.99 t_min")
    check(rep.lines["BOIL"].rhs, "1965.3", "p_sat at 0.99 t_min")
    check(p, "1960.5", "p*")
    with pytest.raises(V.RunnerError, match="BURST/BOIL") as exc:
        V.check_auto_path(p, t, 1.10, 1e3, 0.7e6, ALGAL)
    assert exc.value.exit_code == 2
    # positive control: the unmutated wall passes the same check
    V.check_auto_path(p, V.wall_thickness(p, 1e3, 0.7e6), 1.10, 1e3, 0.7e6, ALGAL)


# ---------------------------------------------------------------- §5 BURST invariant
def _mode_pairs(r_in, R, sigma):
    """Resolved (p, t) of each (p, t) mode, built at a solid-wall state (1.10 AU)."""
    p_auto = V.self_consistent_pressure(1.10, R, sigma)
    t_auto = V.wall_thickness(p_auto, R, sigma)
    t_manual = 10.0
    t_int, _ = V.contained_temperature(r_in, t_manual)
    return {
        "auto/auto": (p_auto, t_auto),
        "manual/auto": (5000.0, t_auto),
        "auto/manual": (V.saturation_pressure(t_int), t_manual),
        "manual/manual": (5000.0, t_manual),
    }


@pytest.mark.parametrize("r_in", [0.5, 0.9, 1.0, 1.03])
def test_burst_invariant_every_mode(r_in):
    """§5: whenever T_shell > 273.15 K, BURST names the picture with σ_eff = 0 in every
    mode; the same (p, t) with r outside the melt door reads the input σ."""
    R, sigma = 1e3, 0.7e6
    for mode, (p, t) in _mode_pairs(r_in, R, sigma).items():
        rep = V.classify_failure(p, t, r_in, R, sigma, ALGAL)
        assert rep.T_shell > 273.15
        assert rep.sigma_eff == 0.0, f"{mode} r={r_in}: sigma_eff {rep.sigma_eff}"
        assert rep.lines["BURST"].rhs == 0.0
        assert rep.first == "BURST", f"{mode} r={r_in}: first {rep.first}"
        out = V.classify_failure(p, t, 1.10, R, sigma, ALGAL)
        assert out.T_shell < 273.15 and out.sigma_eff == sigma
        assert out.lines["BURST"].rhs == sigma


def test_burst_invariant_under_arm_ii_door():
    """Arm (ii) moves the door inside 1 AU (0.9983 AU, vapour): 0.99 AU is BURST, 1.00 is not."""
    inp = inputs_for("arm (ii) vapour")
    t = 4.366
    assert V.classify_failure(611.21, t, 0.99, R_P1, 0.7e6, ALGAL, inp).sigma_eff == 0.0
    assert (
        V.classify_failure(611.21, t, 1.00, R_P1, 0.7e6, ALGAL, inp).sigma_eff == 0.7e6
    )


# ---------------------------------------------------------------- §6 import guard
FORBIDDEN_FILES = ("prereg.yaml", "q4_hand_rows")
BAND_PATTERNS = (r"1\.19\s*,\s*1\.27", r"\b60\s*,\s*300\b", r"\bband\b")


def _imports(tree):
    out = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            out |= {a.name for a in node.names}
        elif isinstance(node, ast.ImportFrom):
            out.add(node.module or "")
        elif (
            isinstance(node, ast.Call) and getattr(node.func, "id", "") == "__import__"
        ):
            out |= {a.value for a in node.args if isinstance(a, ast.Constant)}
    return out


def _closure(path):
    """Import closure over this repo's modules, starting from one file."""
    seen, todo, mods = set(), [path], set()
    while todo:
        p = todo.pop()
        if p in seen:
            continue
        seen.add(p)
        for m in _imports(ast.parse(p.read_text())):
            mods.add(m)
            cand = ROOT / (m.replace(".", "/") + ".py")
            if cand.exists():
                todo.append(cand)
    return mods, seen


def _string_literals(tree):
    return [
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    ]


def vessel_violations(src: str) -> list[str]:
    tree = ast.parse(src)
    bad = [m for m in _imports(tree) if m.startswith("tools") or "q4_hand_rows" in m]
    for s in _string_literals(tree):
        if any(f in s for f in FORBIDDEN_FILES):
            bad.append(f"file literal {s!r}")
    for n in ast.walk(tree):
        if isinstance(n, ast.Call):
            name = getattr(n.func, "id", getattr(n.func, "attr", ""))
            if name in ("open", "read_text", "read_bytes", "safe_load", "load"):
                for a in ast.walk(n):
                    if (
                        isinstance(a, ast.Constant)
                        and isinstance(a.value, str)
                        and any(f in a.value for f in FORBIDDEN_FILES)
                    ):
                        bad.append(f"{name}({a.value!r})")
    return bad


def band_strings(src: str) -> list[str]:
    tree = ast.parse(src)
    code_strings = [s for s in _string_literals(tree)]
    # module/function docstrings describe; they are not written output
    docs = {
        ast.get_docstring(n, clean=False)
        for n in ast.walk(tree)
        if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef))
    }
    return [
        s
        for s in code_strings
        if s not in docs and any(re.search(p, s) for p in BAND_PATTERNS)
    ]


def calc_violations(src: str) -> list[str]:
    return [m for m in _imports(ast.parse(src)) if "vessel" in m]


def test_import_guard_vessel():
    mods, files = _closure(VESSEL_SRC)
    assert not [m for m in mods if m.startswith("tools")], mods
    for f in files:
        assert vessel_violations(f.read_text()) == [], f
    assert band_strings(VESSEL_SRC.read_text()) == []


def test_import_guard_vessel_negative_cases():
    base = VESSEL_SRC.read_text()
    for edge in (
        "\nimport tools.q4_hand_rows\n",
        "\nfrom tools import q4_hand_rows\n",
        "\n_X = open('experiments/q4_vessel/prereg.yaml').read()\n",
        "\n_Y = (ROOT / 'tools' / 'q4_hand_rows.out').read_text()\n",
    ):
        assert vessel_violations(base + edge), f"guard missed {edge!r}"
    assert band_strings(base + "\n_B = 'R_window in [60, 300] km'\n")
    assert band_strings(base + "\n_B = f'{1.19, 1.27}'\n") or band_strings(
        base + "\n_B = 'r_close in [1.19, 1.27] AU'\n"
    )


def test_import_guard_calculator():
    mods, _ = _closure(CALC_SRC)
    assert not [m for m in mods if "vessel" in m], mods
    base = CALC_SRC.read_text()
    assert calc_violations(base) == []
    assert calc_violations(base + "\nfrom sim.vessel import shell_transmission\n")
    assert calc_violations(base + "\nimport sim.vessel\n")


def test_prereg_untouched_since_m1a0():
    assert hashlib.md5(PREREG.read_bytes()).hexdigest() == PREREG_MD5
