"""Reproduces every hand row of the northstar design's §6 table and the §4 census.

The spec's rows were hand-read from a verifier's scratch scripts that lived outside
this repository (round-5 audit). This file is their in-repo producer: it recomputes
the registered rows, the two control rows, the `central` variant, the eight Fresnel
arm rows keyed by `n_interior` x `thermal_reflectance`, and the §4 grid census, and
prints each beside nothing at all -- the comparison against the spec's printed digits
is `tests/test_hand_rows.py`'s job, so that no value printed in §6 is a literal here.

INPUTS. `sim/spectral_table.csv` (the one committed spectral basis: lambda, k, E_AM0,
n_ph on ASTM G173's 2,002-row grid) and the existing `sim.thermal`, `sim.physiology`,
`sim.organism`. Nothing else. In particular this file imports NOTHING from
`sim/vessel.py`, which does not exist yet and is M1a's object under test: a calculator
that imported the thing it calibrates would be checking the code against itself.

THE ARITHMETIC, in the order the spec derives it.
  k(lambda), E_AM0(lambda), n_ph(lambda)    read from the table
  tau_sw(t)   = int T(k(l) t) E_AM0 dl / int E_AM0 dl          (trapezoid, 280-4000 nm)
  f_photon(t) = int T(k(l) t) n_ph dl / int n_ph dl            (trapezoid, 400-700 nm)
  T_shell(kt) = int_0^1 2 mu exp(-kt/mu') dmu                  the declared shell law
  T_norm(kt)  = exp(-kt)                                       the control law
  T_fresnel   = int_0^1 2 mu (1-R1)(1-R2) e / (1 - R1 R2 e^2) dmu    the arm, multi-pass
  t_min       = p R / (2 sigma)      hoop stress at the wall
  T_int       = (1 + tau_sw(t))^0.25 * T_shell_temp(r)
  p*          solves p = p_sat(T_int(p)) by damped iteration (Buck)
  arm (ii)    T_shell_temp(r) = T_eq(r) * (1 - R_slab_sw(t))^0.25 of the wall in force

Run: `python tools/q4_hand_rows.py` (writes stdout; the committed `.out` beside it is
the checked-in record). `--no-census` skips the 59,691-node grid, which takes minutes.
"""

import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(3600)

import csv
import hashlib
import io
import math
from pathlib import Path

import numpy as np
from scipy.optimize import brentq

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from sim.organism import ALGAL
from sim.physiology import gross_assimilation, irradiance, respiration
from sim.thermal import equilibrium_temperature, temperature_response_gaussian

TABLE = ROOT / "sim" / "spectral_table.csv"

# ---------------------------------------------------------------- declared inputs
# The §3 registry, verbatim. These are INPUTS: they are typed here because the
# registration types them, and the literal smell test excludes exactly this block.
N_ICE = 1.31  # ice refractive index, the shell law
N_VAPOUR = 1.0  # arm: index of what the inner face touches, vapour
N_WATER = 1.333  # arm: liquid water
T_OPT = 298.15  # organism thermal optimum, K
OMEGA = 20.0  # Gaussian width, K
T_FREEZE = 273.15  # interior freezing point, K
AREA_RATIO = 4.0  # sphere
SIGMAS_PA = (0.7e6, 1.5e6, 3.1e6)
R_FIXED_M = 10e3  # prediction 1's fixed radius
R_P2_AU = 1.10  # prediction 2's fixed distance
SIGMA_P2_PA = 0.7e6
F_FLOOR = 0.25  # OPAQUE comparator, declared
F_FLOOR_ARMS = (0.50, 0.10)
PAR_LO_NM, PAR_HI_NM = 400.0, 700.0

# quadrature grids
N_MU = 4001
KT_DECADES = (-8, 4)
N_KT = 2401
N_KT_SLAB = 241


# ---------------------------------------------------------------- the table
def load_table(path=TABLE):
    text = path.read_text()
    data = "".join(
        ln for ln in text.splitlines(keepends=True) if not ln.startswith("#")
    )
    rows = list(csv.DictReader(io.StringIO(data)))
    lam = np.array([float(r["lambda_nm"]) for r in rows])
    k = np.array([float(r["k_per_m"]) for r in rows])
    e_am0 = np.array([float(r["E_AM0"]) for r in rows])
    n_ph = np.array([float(r["n_ph"]) for r in rows])
    assert len(lam) == 2002, f"spectral table has {len(lam)} rows"
    header = [ln for ln in text.splitlines() if ln.startswith("#")]
    return lam, k, e_am0, n_ph, header


LAM, K_ALL, E_AM0, N_PH, HEADER = load_table()
PAR = (LAM >= PAR_LO_NM) & (LAM <= PAR_HI_NM)
K_PAR = K_ALL[PAR]
E_TOT = np.trapezoid(E_AM0, LAM)
NPH_TOT = np.trapezoid(N_PH[PAR], LAM[PAR])

# ---------------------------------------------------------------- the laws
MU = np.linspace(0.0, 1.0, N_MU)[1:]


def mu_prime(mu, n=N_ICE):
    """Snell: cosine of the refracted ray inside ice for an external cos mu."""
    return np.sqrt(1.0 - (1.0 - mu**2) / n**2)


MUP = mu_prime(MU)
KT = np.logspace(KT_DECADES[0], KT_DECADES[1], N_KT)
EXP_KT = np.exp(-np.outer(KT, 1.0 / MUP))  # e^{-kt/mu'} over (kt, mu)


def tabulate_kt(values, at_zero):
    """Log-log interpolator in kt for a transmission law sampled on KT."""
    log_v = np.log(np.maximum(values, 1e-300))
    log_kt = np.log(KT)

    def law(kt):
        kt = np.atleast_1d(np.asarray(kt, float))
        out = np.empty_like(kt)
        lo, hi = kt < KT[0], kt > KT[-1]
        mid = ~lo & ~hi
        out[lo] = at_zero
        out[hi] = 0.0
        out[mid] = np.exp(np.interp(np.log(kt[mid]), log_kt, log_v))
        return out

    return law


def fresnel(mu, n1, n2):
    """Unpolarised reflectance, medium n1 at cos(theta)=mu meeting n2."""
    s2 = 1.0 - mu**2
    arg = 1.0 - (n1 / n2) ** 2 * s2
    mu2 = np.sqrt(np.maximum(arg, 0.0))
    rs = (n1 * mu - n2 * mu2) / (n1 * mu + n2 * mu2)
    rp = (n2 * mu - n1 * mu2) / (n2 * mu + n1 * mu2)
    return np.where(arg <= 0, 1.0, 0.5 * (rs**2 + rp**2))


R_OUT = fresnel(MU, N_VAPOUR, N_ICE)  # vacuum -> ice, outer face
R_IN_VAPOUR = fresnel(MUP, N_ICE, N_VAPOUR)  # ice -> vapour, inner face
R_IN_WATER = fresnel(MUP, N_ICE, N_WATER)  # ice -> liquid water, inner face


def _multi_pass_T(r1, r2):
    return np.trapezoid(
        2 * MU * (1 - r1) * (1 - r2) * EXP_KT / (1 - r1 * r2 * EXP_KT**2), MU, axis=1
    )


T_SHELL = tabulate_kt(np.trapezoid(2 * MU * EXP_KT, MU, axis=1), 1.0)


def T_NORMAL(kt):
    return np.exp(-np.atleast_1d(np.asarray(kt, float)))


_v_vap = _multi_pass_T(R_OUT, R_IN_VAPOUR)
_v_wat = _multi_pass_T(R_OUT, R_IN_WATER)
T_FRESNEL_VAPOUR = tabulate_kt(_v_vap, _v_vap[0])
T_FRESNEL_WATER = tabulate_kt(_v_wat, _v_wat[0])


def slab_reflectance(r2, kt):
    """Whole-slab reflectance at optical depth kt; R_slab + T = 1 at kt = 0."""
    e = np.exp(-kt / MUP)
    return float(
        np.trapezoid(
            2 * MU * (R_OUT + (1 - R_OUT) ** 2 * r2 * e**2 / (1 - R_OUT * r2 * e**2)),
            MU,
        )
    )


def solar_weighted_slab_R(r2):
    grid = np.logspace(KT_DECADES[0], KT_DECADES[1], N_KT_SLAB)
    vals = np.array([slab_reflectance(r2, kt) for kt in grid])
    log_grid = np.log(grid)

    def rs(t):
        kt = np.clip(K_ALL * t, grid[0], grid[-1])
        return float(
            np.trapezoid(np.interp(np.log(kt), log_grid, vals) * E_AM0, LAM) / E_TOT
        )

    return rs


R_SLAB_VAPOUR = solar_weighted_slab_R(R_IN_VAPOUR)
R_SLAB_WATER = solar_weighted_slab_R(R_IN_WATER)


# ---------------------------------------------------------------- spectral averages
def tau_sw_of(law):
    return lambda t: float(np.trapezoid(law(K_ALL * t) * E_AM0, LAM) / E_TOT)


def f_photon_of(law):
    return lambda t: float(np.trapezoid(law(K_PAR * t) * N_PH[PAR], LAM[PAR]) / NPH_TOT)


TAU_SHELL, FPH_SHELL = tau_sw_of(T_SHELL), f_photon_of(T_SHELL)
TAU_NORMAL, FPH_NORMAL = tau_sw_of(T_NORMAL), f_photon_of(T_NORMAL)
TAU_FVAP, FPH_FVAP = tau_sw_of(T_FRESNEL_VAPOUR), f_photon_of(T_FRESNEL_VAPOUR)
TAU_FWAT, FPH_FWAT = tau_sw_of(T_FRESNEL_WATER), f_photon_of(T_FRESNEL_WATER)


# ---------------------------------------------------------------- thermodynamics
def saturation_pressure_pa(t_celsius):
    """Buck (1981) over liquid water, Pa."""
    return (
        6.1121
        * math.exp((18.678 - t_celsius / 234.5) * (t_celsius / (257.14 + t_celsius)))
        * 100.0
    )


def t_eq(r_au):
    return equilibrium_temperature(r_au, area_ratio=AREA_RATIO)


T_EQ_1AU = t_eq(1.0)
P_EDGE_PA = saturation_pressure_pa(0.0)  # the edge wall's pressure, p_sat(0 C)

ORG = ALGAL


def net_carbon(r_au, t_int, f_photon):
    return (
        gross_assimilation(irradiance(r_au) * f_photon, ORG.a_max, ORG.k)
        * temperature_response_gaussian(t_int, T_OPT, OMEGA)
        - respiration(ORG.r_d, t_int) / ORG.leaf_mass_ratio
    )


def shell_temperature(r_au, t_m, r_slab_fn=None):
    """T the shell radiates at: T_eq, or T_eq*(1-R_slab_sw(t))^0.25 under arm (ii)."""
    if r_slab_fn is None:
        return t_eq(r_au)
    return t_eq(r_au) * (1.0 - r_slab_fn(t_m)) ** 0.25


def fixed_point(r_au, r_m, sigma_pa, tau_fn, r_slab_fn=None, p0=None, tol=1e-7):
    """p* = p_sat(T_int(p*)) with t = pR/(2 sigma) inside the loop. Damped 50/50."""
    p = P_EDGE_PA * 2.0 if p0 is None else p0
    for _ in range(5000):
        t = p * r_m / (2.0 * sigma_pa)
        t_int = (1.0 + tau_fn(t)) ** 0.25 * shell_temperature(r_au, t, r_slab_fn)
        p_new = saturation_pressure_pa(t_int - T_FREEZE)
        if abs(p_new - p) < tol:
            p = p_new
            break
        p = 0.5 * (p + p_new)
    else:
        raise RuntimeError("self-consistent pressure did not converge")
    t = p * r_m / (2.0 * sigma_pa)
    t_shell = shell_temperature(r_au, t, r_slab_fn)
    return p, t, tau_fn(t), (1.0 + tau_fn(t)) ** 0.25 * t_shell, t_shell


# ---------------------------------------------------------------- the rows
def p1_edge(sigma_pa, tau_fn, r_slab_fn=None):
    """Closed form: T_int(r) = T_freeze with the wall evaluated AT the edge."""
    t = P_EDGE_PA * R_FIXED_M / (2.0 * sigma_pa)
    t_shell_1au = (
        T_EQ_1AU if r_slab_fn is None else T_EQ_1AU * (1.0 - r_slab_fn(t)) ** 0.25
    )
    door = (t_shell_1au / T_FREEZE) ** 2
    return t, tau_fn(t), door * math.sqrt(1.0 + tau_fn(t)), door


def p1_edge_rootfind(sigma_pa, tau_fn, r_slab_fn=None):
    lo = 0.95 if r_slab_fn is not None else 1.0
    return brentq(
        lambda rr: (
            fixed_point(rr, R_FIXED_M, sigma_pa, tau_fn, r_slab_fn)[3] - T_FREEZE
        ),
        lo,
        1.45,
        xtol=1e-7,
    )


def p2_state(r_m, tau_fn, fph_fn, r_slab_fn=None):
    p, t, tau, t_int, t_shell = fixed_point(
        R_P2_AU, r_m, SIGMA_P2_PA, tau_fn, r_slab_fn
    )
    return p, t, tau, t_int, fph_fn(t), t_shell


def p2_crossing(tau_fn, fph_fn, r_slab_fn=None, floor=F_FLOOR, mode="OPAQUE"):
    idx = 4 if mode == "OPAQUE" else 3
    target = floor if mode == "OPAQUE" else T_FREEZE
    return brentq(
        lambda rr: p2_state(rr, tau_fn, fph_fn, r_slab_fn)[idx] - target,
        1e2,
        5e6,
        xtol=0.1,
    )


# ---------------------------------------------------------------- the §4 census
GRID_R_AU = np.round(np.arange(1.04, 3.00 + 1e-9, 0.01), 2)
GRID_R_M = np.logspace(1, 6, 101)  # 10 m to 1000 km, 20 nodes per decade
GRID_T_M = np.logspace(-4, 5, 3601)


def tabulate_in_t(tau_fn, fph_fn):
    """Log-log interpolators in t: 59,691 states x 2 laws needs them."""
    ta = np.array([tau_fn(t) for t in GRID_T_M])
    fp = np.array([fph_fn(t) for t in GRID_T_M])
    lt = np.log(GRID_T_M)
    lta, lfp = np.log(np.maximum(ta, 1e-300)), np.log(np.maximum(fp, 1e-300))
    return (
        lambda t: float(np.exp(np.interp(math.log(t), lt, lta))),
        lambda t: float(np.exp(np.interp(math.log(t), lt, lfp))),
    )


def census(tau_fn, fph_fn):
    """Load order BURST, FREEZE, BOIL, STARVE, OPAQUE; BURST and BOIL hold by
    construction on the auto path, so the first violated is among the other three."""
    counts = {"FREEZE": 0, "STARVE": 0, "OPAQUE": 0, "HELD": 0}
    starve_violations = 0
    starve_violations_warm = 0
    min_margin, min_node = float("inf"), None
    min_f_photon = float("inf")
    for sigma in SIGMAS_PA:
        for r_au in GRID_R_AU:
            p0 = None
            for r_m in GRID_R_M:
                p, t, _, t_int, _ = fixed_point(
                    float(r_au), float(r_m), sigma, tau_fn, p0=p0
                )
                p0 = p
                fp = fph_fn(t)
                margin = net_carbon(float(r_au), t_int, fp)
                if t_int < T_FREEZE:
                    first = "FREEZE"
                elif margin < 0:
                    first = "STARVE"
                elif fp < F_FLOOR:
                    first = "OPAQUE"
                else:
                    first = "HELD"
                counts[first] += 1
                if margin < 0:
                    starve_violations += 1
                    if t_int >= T_FREEZE:
                        starve_violations_warm += 1
                if t_int >= T_FREEZE and margin < min_margin:
                    min_margin = margin
                    min_node = (sigma / 1e6, float(r_au), r_m / 1e3, t_int, fp)
                min_f_photon = min(min_f_photon, fp)
    return (
        counts,
        starve_violations,
        starve_violations_warm,
        min_margin,
        min_node,
        min_f_photon,
    )


# ---------------------------------------------------------------- report
def main(argv):
    out = []
    w = out.append

    w("=== provenance: the one input table ===")
    for line in HEADER:
        if "source:" in line or "quadrature" in line or "producer_commit" in line:
            w("  " + line.lstrip("# ").rstrip())
    w(f"  table sha256 (data rows): {table_digest()}")
    w(f"  rows {len(LAM)}, {LAM[0]:.0f} to {LAM[-1]:.0f} nm; PAR rows {int(PAR.sum())}")

    w("")
    w("=== §3 constants ===")
    w(f"  T_eq(1 AU, area_ratio {AREA_RATIO:.0f}) = {T_EQ_1AU:.6f} K")
    w(f"  p_sat(0 C) = {P_EDGE_PA:.5f} Pa   [the edge wall's pressure]")
    w(f"  melt door, albedo 0: {(T_EQ_1AU / T_FREEZE) ** 2:.5f} AU")
    w(f"  freeze-line albedo at 1 AU: {1 - (T_FREEZE / T_EQ_1AU) ** 4:.5f}")
    w(
        f"  T_shell law T(1) = {float(T_SHELL(1.0)[0]):.5f}; control e^-1 = {math.exp(-1):.5f}"
    )
    w(
        f"  Fresnel multi-pass T(1): vapour {float(T_FRESNEL_VAPOUR(1.0)[0]):.5f}"
        f"  water {float(T_FRESNEL_WATER(1.0)[0]):.5f}"
    )
    w(
        f"  R_slab at kt->0: vapour {slab_reflectance(R_IN_VAPOUR, 1e-8):.6f}"
        f"  water {slab_reflectance(R_IN_WATER, 1e-8):.6f}"
    )
    w(
        f"  tau=1 ceiling edge: {(2**0.25 * T_EQ_1AU / T_FREEZE) ** 2:.4f} AU"
        f"  (STARVE {net_carbon((2**0.25 * T_EQ_1AU / T_FREEZE) ** 2, T_FREEZE, 1.0):+.2f})"
    )

    # ---- P1: registered, control, arm
    w("")
    w("=== §6 P1, edge in r at R = 10 km, dust none, albedo 0, algal ===")
    p1_laws = (
        ("P1 registered, shell law", TAU_SHELL, FPH_SHELL, None),
        ("P1 control, normal incidence", TAU_NORMAL, FPH_NORMAL, None),
        (
            "P1 arm (i) vapour  n_int 1.000, thermal_reflectance 0",
            TAU_FVAP,
            FPH_FVAP,
            None,
        ),
        (
            "P1 arm (i) water   n_int 1.333, thermal_reflectance 0",
            TAU_FWAT,
            FPH_FWAT,
            None,
        ),
        (
            "P1 arm (ii) vapour n_int 1.000, thermal_reflectance slab",
            TAU_FVAP,
            FPH_FVAP,
            R_SLAB_VAPOUR,
        ),
        (
            "P1 arm (ii) water  n_int 1.333, thermal_reflectance slab",
            TAU_FWAT,
            FPH_FWAT,
            R_SLAB_WATER,
        ),
    )
    for label, tau_fn, fph_fn, rs_fn in p1_laws:
        w(f"  {label}")
        for sigma in SIGMAS_PA:
            t, tau, edge, door = p1_edge(sigma, tau_fn, rs_fn)
            root = p1_edge_rootfind(sigma, tau_fn, rs_fn)
            rsl = rs_fn(t) if rs_fn else 0.0
            w(
                f"    sigma {sigma / 1e6:.1f} MPa: p {P_EDGE_PA:.2f} Pa  t {t:.3f} m"
                f"  tau_sw {tau:.4f}  f_photon {fph_fn(t):.3f}"
                f"  R_slab_sw {rsl:.4f}  melt door {door:.4f} AU"
                f"  edge {edge:.4f} AU (root {root:.4f})"
            )
    t_e, _, _, _ = p1_edge(SIGMAS_PA[0], TAU_SHELL)
    w(
        f"  STARVE margin at the sigma {SIGMAS_PA[0] / 1e6:.1f} edge:"
        f" {net_carbon(p1_edge(SIGMAS_PA[0], TAU_SHELL)[2], T_FREEZE, FPH_SHELL(t_e)):+.2f} umol"
    )

    # ---- P2
    w("")
    w(
        f"=== §6 P2, window in R at r = {R_P2_AU:.2f} AU, sigma {SIGMA_P2_PA / 1e6:.1f} MPa,"
        f" f_floor {F_FLOOR:.2f} ==="
    )
    p2_laws = (
        ("P2 registered, shell law", TAU_SHELL, FPH_SHELL, None),
        ("P2 control, normal incidence", TAU_NORMAL, FPH_NORMAL, None),
        (
            "P2 arm (i) vapour  n_int 1.000, thermal_reflectance 0",
            TAU_FVAP,
            FPH_FVAP,
            None,
        ),
        (
            "P2 arm (i) water   n_int 1.333, thermal_reflectance 0",
            TAU_FWAT,
            FPH_FWAT,
            None,
        ),
        (
            "P2 arm (ii) vapour n_int 1.000, thermal_reflectance slab",
            TAU_FVAP,
            FPH_FVAP,
            R_SLAB_VAPOUR,
        ),
        (
            "P2 arm (ii) water  n_int 1.333, thermal_reflectance slab",
            TAU_FWAT,
            FPH_FWAT,
            R_SLAB_WATER,
        ),
    )
    for label, tau_fn, fph_fn, rs_fn in p2_laws:
        r_op = p2_crossing(tau_fn, fph_fn, rs_fn, mode="OPAQUE")
        r_fr = p2_crossing(tau_fn, fph_fn, rs_fn, mode="FREEZE")
        po, to, tauo, tio, fpo, tso = p2_state(r_op, tau_fn, fph_fn, rs_fn)
        pf, tf, tauf, tif, fpf, tsf = p2_state(r_fr, tau_fn, fph_fn, rs_fn)
        binding = "OPAQUE" if r_op < r_fr else "FREEZE"
        w(f"  {label}")
        w(
            f"    OPAQUE R {r_op / 1e3:.1f} km: p* {po:.1f} Pa  t {to:.2f} m"
            f"  tau_sw {tauo:.4f}  T_int {tio:.2f} K  T_shell {tso:.2f} K"
            f"  R_slab_sw {(rs_fn(to) if rs_fn else 0.0):.4f}"
            f"  STARVE {net_carbon(R_P2_AU, tio, fpo):+.2f}"
        )
        w(
            f"    FREEZE R {r_fr / 1e3:.1f} km: p* {pf:.2f} Pa  t {tf:.1f} m"
            f"  tau_sw {tauf:.4f}  T_shell {tsf:.2f} K"
            f"  R_slab_sw {(rs_fn(tf) if rs_fn else 0.0):.4f}"
        )
        w(f"    R_window {min(r_op, r_fr) / 1e3:.1f} km, binding {binding}")
    for floor in F_FLOOR_ARMS:
        r_op = p2_crossing(TAU_SHELL, FPH_SHELL, None, floor=floor, mode="OPAQUE")
        r_fr = p2_crossing(TAU_SHELL, FPH_SHELL, None, mode="FREEZE")
        w(
            f"  P2 arm f_floor {floor:.2f}: OPAQUE crossing R {r_op / 1e3:.1f} km;"
            f"  R_window {min(r_op, r_fr) / 1e3:.1f} km"
            f" ({'OPAQUE' if r_op < r_fr else 'FREEZE'})"
        )
    r_central = brentq(
        lambda rr: FPH_NORMAL(p2_state(rr, TAU_SHELL, FPH_SHELL)[1]) - F_FLOOR,
        1e2,
        5e6,
        xtol=0.1,
    )
    w(
        f"  P2 variant, interior `central` (shell tau_sw, normal-incidence f_photon):"
        f" R {r_central / 1e3:.1f} km"
    )

    # ---- §4 census
    w("")
    w("=== §4 census over the registered grid ===")
    w(
        f"  grid {len(GRID_R_AU)} x {len(GRID_R_M)} x {len(SIGMAS_PA)}"
        f" = {len(GRID_R_AU) * len(GRID_R_M) * len(SIGMAS_PA)} states"
    )
    if "--no-census" in argv:
        w("  SKIPPED (--no-census)")
    else:
        for law, tau_fn, fph_fn in (
            ("shell", TAU_SHELL, FPH_SHELL),
            ("normal", TAU_NORMAL, FPH_NORMAL),
        ):
            tf, ff = tabulate_in_t(tau_fn, fph_fn)
            counts, nS, nS_warm, margin, node, min_fp = census(tf, ff)
            w(
                f"  {law}: first-violated FREEZE {counts['FREEZE']}"
                f"  STARVE {counts['STARVE']}  OPAQUE {counts['OPAQUE']}"
                f"  HELD {counts['HELD']}  (sum {sum(counts.values())})"
            )
            w(
                f"    STARVE violated anywhere {nS}, of which with T_int >= T_freeze: {nS_warm}"
            )
            w(
                f"    min STARVE margin with FREEZE holding {margin:+.4f} umol at"
                f" sigma {node[0]:.1f} MPa, r {node[1]:.2f} AU, R {node[2]:.1f} km,"
                f" T_int {node[3]:.4f} K, f_photon {node[4]:.4f}"
            )
            w(f"    grid minimum f_photon {min_fp:.4f}")

    # ---- the §4 reference state
    w("")
    w("=== §4 reference state: 1 AU, R = 10 km, sigma 0.7 MPa ===")
    for law, tau_fn, fph_fn in (
        ("shell", TAU_SHELL, FPH_SHELL),
        ("normal", TAU_NORMAL, FPH_NORMAL),
    ):
        p, t, tau, t_int, _ = fixed_point(1.0, R_FIXED_M, SIGMAS_PA[0], tau_fn)
        fp = fph_fn(t)
        w(
            f"  {law}: T_int {t_int:.2f} K  f_photon {fp:.3f}"
            f"  STARVE {net_carbon(1.0, t_int, fp):+.2f} umol"
        )

    text = "\n".join(out) + "\n"
    sys.stdout.write(text)
    return 0


def table_digest():
    data = "".join(
        ln
        for ln in TABLE.read_text().splitlines(keepends=True)
        if not ln.startswith("#")
    )
    return hashlib.sha256(data.encode()).hexdigest()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
