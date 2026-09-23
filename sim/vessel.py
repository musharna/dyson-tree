"""The vessel: one sphere, one ice wall, one organism inside (northstar design §3-§6, M1a).

Units: pressure Pa; lengths m; distance AU; temperature K; photon flux µmol m⁻² s⁻¹.

INPUT. `sim/spectral_table.csv` only (λ, k, E_AM0, n_ph on ASTM G173's 2,002-row grid).
This module never opens the pre-registration or the hand-row output and imports nothing
from `tools/`: it is the object under test, never the source of a band (§6). The import
guard in `tests/test_vessel.py` walks this file's AST to hold that.

THE LAWS (§3). A transmission law is a function of k·t alone:
  shell           T(kt) = ∫₀¹ 2μ exp(-kt/μ') dμ,  μ' = sqrt(1 - (1-μ²)/n²)   (registered)
  normal          T(kt) = exp(-kt)                                           (control)
  shell+fresnel   T(kt) = ∫₀¹ 2μ (1-R₁)(1-R₂) e^{-x} / (1 - R₁R₂e^{-2x}) dμ, x = kt/μ'
                  with R₁ air→ice at μ, R₂ ice→interior at μ' by n_interior    (arm)
Each is tabulated once on 2,401 log-spaced k·t nodes (1e-8 to 1e4) and interpolated
log-log. Spectral averages are trapezoids on the table's own rows.

THE THERMAL BALANCE. Registered (thermal_reflectance "0"): T_shell = T_eq,
T_int = (1 + τ_sw)^¼ T_eq. Arm (ii) (thermal_reflectance "slab"): the conserving
two-body balance, T_shell⁴ = (1 - R_slab_sw) T_eq⁴, T_int⁴ = (1 - R_slab_sw + τ_sw) T_eq⁴.
T_eq is the sphere's (area_ratio 4), not the organism's.
"""

from __future__ import annotations

import csv
import io
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

from sim.physiology import gross_assimilation, irradiance, respiration
from sim.thermal import equilibrium_temperature, temperature_response_gaussian

TABLE_PATH = Path(__file__).resolve().parent / "spectral_table.csv"

# ---------------------------------------------------------------- declared constants
N_ICE = 1.31  # §3 registry `n`
N_INTERIOR = {"vapour": 1.000, "water": 1.333}  # §3 registry `n_interior`, arm only
SPHERE_AREA_RATIO = (
    4.0  # the vessel's geometry; the organism's area_ratio does not enter
)
T_ICE_MELT_K = 273.15  # the wall's own phase line (σ_eff door), not the deck's T_freeze
PAR_NM = (400.0, 700.0)
THIN_WALL_LIMIT = 0.1  # t/R at and above which hoop stress is outside its domain (§3)

# §4 comparison epsilons and §6 edge tolerances
EPS_BURST_BOIL_REL = 1e-6
EPS_FREEZE_K = 1e-6
EPS_STARVE_OPAQUE = 1e-9
FIXED_POINT_DP_PA = 1e-6
FIXED_POINT_MAX_ITER = 1000
EDGE_TOL_R_AU = 1e-4
EDGE_TOL_R_REL = 1e-3

LOAD_ORDER = ("BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE")
BINDING_LINES = ("FREEZE", "OPAQUE")
WINDOW_LINES = ("FREEZE", "STARVE", "OPAQUE")

OPTICAL_LAWS = ("shell", "normal", "shell+fresnel")
THERMAL_REFLECTANCES = ("0", "slab")

# quadrature for the tabulated laws (§3)
_N_MU = 4001
_KT = np.logspace(-8.0, 4.0, 2401)
_LOG_KT = np.log(_KT)


class RunnerError(RuntimeError):
    """An auto-path BURST or BOIL violation: the construction under test broke (exit 2)."""

    exit_code = 2


class ConvergenceError(RuntimeError):
    """The self-consistent pressure iteration exhausted its passes."""


# ---------------------------------------------------------------- §10 same object
@dataclass(frozen=True)
class GroundedInput:
    id: str
    material: str
    quantity: str


GROUNDED_INPUTS = {
    "sigma_ice": GroundedInput("sigma_ice", "ice", "tensile strength"),
    "k_ice": GroundedInput("k_ice", "ice", "absorption coefficient"),
    "sigma_wood": GroundedInput("sigma_wood", "wood", "modulus of rupture"),
}


def assert_same_object(*input_ids: str) -> str:
    """A pair of grounded inputs must describe the same object (§3, §10), by material id."""
    mats = {GROUNDED_INPUTS[i].material for i in input_ids}
    if len(mats) != 1:
        raise ValueError(
            f"grounded inputs {input_ids} describe different objects: {sorted(mats)}"
        )
    return mats.pop()


WALL_INPUTS = ("sigma_ice", "k_ice")
WALL_MATERIAL = assert_same_object(*WALL_INPUTS)


# ---------------------------------------------------------------- the table
def _load_table(path: Path = TABLE_PATH):
    text = path.read_text()
    body = "".join(
        ln for ln in text.splitlines(keepends=True) if not ln.startswith("#")
    )
    rows = list(csv.DictReader(io.StringIO(body)))
    cols = {
        name: np.array([float(r[name]) for r in rows])
        for name in ("lambda_nm", "k_per_m", "E_AM0", "n_ph")
    }
    if len(rows) != 2002:
        raise ValueError(f"{path}: expected 2002 rows, got {len(rows)}")
    return cols


_T = _load_table()
LAMBDA_NM = _T["lambda_nm"]
K_PER_M = _T["k_per_m"]
E_AM0 = _T["E_AM0"]
N_PH = _T["n_ph"]
_PAR = (LAMBDA_NM >= PAR_NM[0]) & (LAMBDA_NM <= PAR_NM[1])
_E_TOT = float(np.trapezoid(E_AM0, LAMBDA_NM))
_NPH_TOT = float(np.trapezoid(N_PH[_PAR], LAMBDA_NM[_PAR]))


# ---------------------------------------------------------------- mechanics
def wall_thickness(p: float, R: float, sigma: float) -> float:
    """t_min = p·R / (2σ): the thin-wall sphere that just holds p."""
    if sigma <= 0:
        raise ValueError(f"sigma must be > 0 (a molten wall has no t_min), got {sigma}")
    if p < 0 or R <= 0:
        raise ValueError(f"need p >= 0 and R > 0, got p={p}, R={R}")
    return p * R / (2.0 * sigma)


def hoop_stress(p: float, R: float, t: float) -> float:
    """σ_hoop = p·R / (2t)."""
    if t <= 0 or R <= 0:
        raise ValueError(f"need t > 0 and R > 0, got t={t}, R={R}")
    return p * R / (2.0 * t)


# ---------------------------------------------------------------- optics
_MU = np.linspace(0.0, 1.0, _N_MU)[1:]


def _mu_prime(mu):
    return np.sqrt(1.0 - (1.0 - mu**2) / N_ICE**2)


_MUP = _mu_prime(_MU)


def _fresnel(mu, n1, n2):
    """Unpolarised reflectance, medium n1 at cos θ = mu meeting medium n2."""
    arg = 1.0 - (n1 / n2) ** 2 * (1.0 - mu**2)
    mu2 = np.sqrt(np.maximum(arg, 0.0))
    rs = (n1 * mu - n2 * mu2) / (n1 * mu + n2 * mu2)
    rp = (n2 * mu - n1 * mu2) / (n2 * mu + n1 * mu2)
    return np.where(arg <= 0, 1.0, 0.5 * (rs**2 + rp**2))


def _check_n_interior(n_interior: float) -> float:
    if not any(math.isclose(n_interior, v, abs_tol=1e-12) for v in N_INTERIOR.values()):
        raise ValueError(
            f"n_interior must be one of {sorted(N_INTERIOR.values())}, got {n_interior}"
        )
    return float(n_interior)


@lru_cache(maxsize=None)
def _faces(n_interior: float):
    r1 = _fresnel(_MU, 1.0, N_ICE)
    r2 = _fresnel(_MUP, N_ICE, n_interior)
    return r1, r2


@lru_cache(maxsize=None)
def _exp_kt():
    return np.exp(-np.outer(_KT, 1.0 / _MUP))


@lru_cache(maxsize=None)
def _law_table(optical_law: str, n_interior: float):
    """(values on _KT, value at k·t -> 0) for a tabulated law."""
    e = _exp_kt()
    if optical_law == "shell":
        vals = np.trapezoid(2 * _MU * e, _MU, axis=1)
        return vals, 1.0
    if optical_law == "shell+fresnel":
        r1, r2 = _faces(n_interior)
        vals = np.trapezoid(
            2 * _MU * (1 - r1) * (1 - r2) * e / (1 - r1 * r2 * e**2), _MU, axis=1
        )
        return vals, float(vals[0])
    raise ValueError(f"no tabulated law {optical_law!r}")


def _check_law(optical_law: str):
    if optical_law not in OPTICAL_LAWS:
        raise ValueError(
            f"optical_law must be one of {OPTICAL_LAWS}, got {optical_law!r}"
        )


def shell_transmission(kt, optical_law: str = "shell", n_interior: float = 1.000):
    """Transmission of the wall at optical depth k·t under the given law (§3, §6)."""
    _check_law(optical_law)
    kt_arr = np.atleast_1d(np.asarray(kt, dtype=float))
    if np.any(kt_arr < 0):
        raise ValueError(f"k·t must be >= 0, got {kt}")
    if optical_law == "normal":
        out = np.exp(-kt_arr)
    else:
        vals, at_zero = _law_table(optical_law, _check_n_interior(n_interior))
        out = np.empty_like(kt_arr)
        lo, hi = kt_arr < _KT[0], kt_arr > _KT[-1]
        mid = ~lo & ~hi
        out[lo] = at_zero
        out[hi] = 0.0
        out[mid] = np.exp(
            np.interp(np.log(kt_arr[mid]), _LOG_KT, np.log(np.maximum(vals, 1e-300)))
        )
    return float(out[0]) if np.ndim(kt) == 0 else out


def slab_reflectance(kt: float, n_interior: float = 1.000) -> float:
    """Whole-slab reflectance at optical depth k·t, incoherent multi-pass (§6).

    R_slab = ∫₀¹ 2μ (R₁ + (1-R₁)² R₂ e^{-2x} / (1 - R₁R₂e^{-2x})) dμ, x = kt/μ'.
    Satisfies R_slab + T = 1 at k·t = 0."""
    if kt < 0:
        raise ValueError(f"k·t must be >= 0, got {kt}")
    r1, r2 = _faces(_check_n_interior(n_interior))
    e2 = np.exp(-2.0 * kt / _MUP)
    return float(
        np.trapezoid(2 * _MU * (r1 + (1 - r1) ** 2 * r2 * e2 / (1 - r1 * r2 * e2)), _MU)
    )


@lru_cache(maxsize=None)
def _slab_table(n_interior: float):
    r1, r2 = _faces(n_interior)
    e2 = _exp_kt() ** 2
    return np.trapezoid(
        2 * _MU * (r1 + (1 - r1) ** 2 * r2 * e2 / (1 - r1 * r2 * e2)), _MU, axis=1
    )


def solar_slab_reflectance(t: float, n_interior: float = 1.000) -> float:
    """R_slab_sw(t): the wall's slab reflectance weighted by E_AM0 over 280-4000 nm."""
    vals = _slab_table(_check_n_interior(n_interior))
    kt = np.clip(K_PER_M * t, _KT[0], _KT[-1])
    return float(
        np.trapezoid(np.interp(np.log(kt), _LOG_KT, vals) * E_AM0, LAMBDA_NM) / _E_TOT
    )


def transmission_spectrum(
    t: float, *, k=None, optical_law: str = "shell", n_interior: float = 1.000
):
    """τ(λ, t) = T(k(λ)·t) on the table's rows, or at the given k."""
    if t < 0:
        raise ValueError(f"t must be >= 0, got {t}")
    kk = K_PER_M if k is None else k
    return shell_transmission(np.asarray(kk, dtype=float) * t, optical_law, n_interior)


def solar_transmission(
    t: float,
    *,
    optical_law: str = "shell",
    n_interior: float = 1.000,
    scalar_k: float | None = None,
) -> float:
    """τ_sw(t), solar-energy-weighted over 280-4000 nm (band-normalised, §3).

    scalar_k replaces the spectrum with exp(-k·t): the §3 closed-form control (b) only."""
    if scalar_k is not None:
        return math.exp(-scalar_k * t)
    tau = transmission_spectrum(t, optical_law=optical_law, n_interior=n_interior)
    return float(np.trapezoid(tau * E_AM0, LAMBDA_NM) / _E_TOT)


def par_photon_fraction(
    t: float,
    *,
    optical_law: str = "shell",
    n_interior: float = 1.000,
    interior: str = "mixed",
) -> float:
    """f_photon(t), the fraction of AM0 PAR photons (400-700 nm) that arrive (§3).

    interior "mixed" is the projected-disk average under the law in force; "central" is a
    point organism at the centre, which reads the normal-incidence fraction (shell law only).
    """
    if interior == "central":
        if optical_law != "shell":
            raise ValueError("interior 'central' is defined under the shell law only")
        optical_law = "normal"
    elif interior != "mixed":
        raise ValueError(f"interior must be 'mixed' or 'central', got {interior!r}")
    tau = transmission_spectrum(
        t, k=K_PER_M[_PAR], optical_law=optical_law, n_interior=n_interior
    )
    return float(np.trapezoid(tau * N_PH[_PAR], LAMBDA_NM[_PAR]) / _NPH_TOT)


# ---------------------------------------------------------------- thermodynamics
def saturation_pressure(t_k: float) -> float:
    """Buck (1981) over liquid water, Pa, at temperature t_k in K."""
    tc = t_k - 273.15
    return 611.21 * math.exp((18.678 - tc / 234.5) * (tc / (257.14 + tc)))


def _check_thermal(thermal_reflectance: str):
    if thermal_reflectance not in THERMAL_REFLECTANCES:
        raise ValueError(
            f"thermal_reflectance must be one of {THERMAL_REFLECTANCES},"
            f" got {thermal_reflectance!r}"
        )
    return thermal_reflectance


def contained_temperature(
    r_au: float,
    t: float,
    *,
    optical_law: str = "shell",
    n_interior: float = 1.000,
    thermal_reflectance: str = "0",
    albedo: float = 0.0,
    emissivity: float = 1.0,
    scalar_k: float | None = None,
) -> tuple[float, float]:
    """(T_int, T_shell) of the vessel behind a wall of thickness t at r_au (§3, §6)."""
    _check_thermal(thermal_reflectance)
    t_eq = equilibrium_temperature(r_au, SPHERE_AREA_RATIO, emissivity, albedo)
    tau = solar_transmission(
        t, optical_law=optical_law, n_interior=n_interior, scalar_k=scalar_k
    )
    if thermal_reflectance == "slab":
        if optical_law != "shell+fresnel":
            raise ValueError(
                "thermal_reflectance 'slab' needs optical_law 'shell+fresnel'"
            )
        rs = solar_slab_reflectance(t, n_interior)
    else:
        rs = 0.0
    return (1.0 - rs + tau) ** 0.25 * t_eq, (1.0 - rs) ** 0.25 * t_eq


def self_consistent_pressure(
    r_au: float,
    R: float,
    sigma: float,
    *,
    optical_law: str = "shell",
    n_interior: float = 1.000,
    thermal_reflectance: str = "0",
    albedo: float = 0.0,
    emissivity: float = 1.0,
    scalar_k: float | None = None,
    p0: float | None = None,
    tol: float = FIXED_POINT_DP_PA,
    max_iter: int = FIXED_POINT_MAX_ITER,
) -> float:
    """p* = p_sat(T_int(t_min(p*))), damped 50/50 iteration; raises on exhaustion."""
    p = 2.0 * saturation_pressure(273.15) if p0 is None else p0
    for _ in range(max_iter):
        t = wall_thickness(p, R, sigma)
        t_int, _ = contained_temperature(
            r_au,
            t,
            optical_law=optical_law,
            n_interior=n_interior,
            thermal_reflectance=thermal_reflectance,
            albedo=albedo,
            emissivity=emissivity,
            scalar_k=scalar_k,
        )
        p_new = saturation_pressure(t_int)
        # 1e-6 Pa is the registered residual; below ~1 Pa it is looser than BOIL's
        # 1e-6 relative epsilon, so the residual is also held under 1e-9 relative.
        if abs(p_new - p) < min(tol, 1e-9 * p_new):
            return p_new
        p = 0.5 * (p + p_new)
    raise ConvergenceError(
        f"p* did not converge in {max_iter} passes at r={r_au} AU, R={R} m,"
        f" sigma={sigma} Pa, law={optical_law}: last p={p!r}, |dp|={abs(p_new - p)!r}"
    )


def closed_form_r_max(sigma: float, p: float, k: float, tau_min: float) -> float:
    """The roadmap's R_max = 2σ|ln τ_min| / (k·p), a CONTROL (§3), in m."""
    return 2.0 * sigma * abs(math.log(tau_min)) / (k * p)


# ---------------------------------------------------------------- the registry
@dataclass(frozen=True)
class VesselInputs:
    """The §3 registry: every declared input, by the registry's key names."""

    t_opt_K: float = 298.15
    omega_K: float = 20.0
    albedo: float = 0.0
    emissivity: float = 1.0
    f_floor: float = 0.25
    n: float = N_ICE
    interior: str = "mixed"
    shell_temperature: str = "isothermal"
    dust: str = "none"
    T_freeze_K: float = 273.15
    optical_law: str = "shell"
    n_interior: float = N_INTERIOR["vapour"]
    thermal_reflectance: str = "0"
    solar_tail_transmission: str = "band_weighted_tau_sw"

    def __post_init__(self):
        _check_law(self.optical_law)
        _check_n_interior(self.n_interior)
        _check_thermal(self.thermal_reflectance)
        if self.n != N_ICE:
            raise ValueError(f"n is fixed at {N_ICE} (§3 registry), got {self.n}")
        if self.shell_temperature != "isothermal":
            raise ValueError("shell_temperature is fixed 'isothermal' (§3 registry)")
        if self.solar_tail_transmission != "band_weighted_tau_sw":
            raise ValueError("solar_tail_transmission is fixed (§3 registry)")
        if self.dust != "none":
            raise NotImplementedError(
                f"dust {self.dust!r}: M1a implements the registered 'none' only"
            )
        if self.interior not in ("mixed", "central"):
            raise ValueError(
                f"interior must be 'mixed' or 'central', got {self.interior!r}"
            )
        if self.thermal_reflectance == "slab" and self.optical_law != "shell+fresnel":
            raise ValueError(
                "thermal_reflectance 'slab' needs optical_law 'shell+fresnel'"
            )

    def optics(self) -> dict:
        return {"optical_law": self.optical_law, "n_interior": self.n_interior}

    def thermal(self) -> dict:
        return {
            **self.optics(),
            "thermal_reflectance": self.thermal_reflectance,
            "albedo": self.albedo,
            "emissivity": self.emissivity,
        }


REGISTERED = VesselInputs()


# ---------------------------------------------------------------- the five lines
@dataclass(frozen=True)
class Line:
    name: str
    lhs: float
    rhs: float
    margin: float  # > 0 HOLDS by that much; < -eps VIOLATED
    violated: bool


@dataclass(frozen=True)
class FailureReport:
    lines: dict  # name -> Line, in load order
    violated: tuple  # names, load order
    sigma_eff: float
    T_int: float
    T_shell: float
    f_photon: float
    thin_wall_valid: bool
    extra: dict = field(default_factory=dict)

    @property
    def first(self) -> str | None:
        return self.violated[0] if self.violated else None


def net_carbon_contained(
    organism,
    r_au: float,
    t_int: float,
    f_photon: float,
    inputs: VesselInputs = REGISTERED,
) -> float:
    """STARVE's left side: gross at I_wall and T_int minus respiration at T_int (§4)."""
    i_wall = (1.0 - inputs.albedo) * irradiance(r_au) * f_photon
    gross = gross_assimilation(i_wall, organism.a_max, organism.k)
    gross *= temperature_response_gaussian(t_int, inputs.t_opt_K, inputs.omega_K)
    return gross - respiration(organism.r_d, t_int) / organism.leaf_mass_ratio


def classify_failure(p, t, r, R, sigma, organism, inputs: VesselInputs = REGISTERED):
    """The set of violated inequalities at a RESOLVED (p, t), in load order (§4).

    BURST reads σ_eff(T_shell) in every mode: 0 when the shell is above 273.15 K."""
    t_int, t_shell = contained_temperature(r, t, **inputs.thermal())
    f_ph = par_photon_fraction(t, **inputs.optics(), interior=inputs.interior)
    sigma_eff = 0.0 if t_shell > T_ICE_MELT_K else sigma
    hoop = hoop_stress(p, R, t)
    p_sat = saturation_pressure(t_int)
    net = net_carbon_contained(organism, r, t_int, f_ph, inputs)

    def line(name, lhs, rhs, margin, eps):
        return Line(name, lhs, rhs, margin, margin < -eps)

    lines = {
        "BURST": line(
            "BURST",
            hoop,
            sigma_eff,
            sigma_eff - hoop,
            EPS_BURST_BOIL_REL * max(sigma_eff, hoop),
        ),
        "FREEZE": line(
            "FREEZE", t_int, inputs.T_freeze_K, t_int - inputs.T_freeze_K, EPS_FREEZE_K
        ),
        "BOIL": line("BOIL", p, p_sat, p - p_sat, EPS_BURST_BOIL_REL * p_sat),
        "STARVE": line("STARVE", net, 0.0, net, EPS_STARVE_OPAQUE),
        "OPAQUE": line(
            "OPAQUE", f_ph, inputs.f_floor, f_ph - inputs.f_floor, EPS_STARVE_OPAQUE
        ),
    }
    return FailureReport(
        lines=lines,
        violated=tuple(n for n in LOAD_ORDER if lines[n].violated),
        sigma_eff=sigma_eff,
        T_int=t_int,
        T_shell=t_shell,
        f_photon=f_ph,
        thin_wall_valid=t / R < THIN_WALL_LIMIT,
    )


def check_auto_path(p, t, r, R, sigma, organism, inputs: VesselInputs = REGISTERED):
    """Classify an auto-path state; BURST or BOIL violated there is a RunnerError (§4).

    The one exception is BURST through the melt door (σ_eff = 0): that is the inequality
    firing, not the construction breaking, and it is returned as BURST."""
    rep = classify_failure(p, t, r, R, sigma, organism, inputs)
    bad = [n for n in ("BURST", "BOIL") if rep.lines[n].violated]
    if rep.sigma_eff == 0.0 and "BURST" in bad:
        bad.remove("BURST")
    if bad:
        detail = "; ".join(
            f"{n}: {rep.lines[n].lhs:.6g} vs {rep.lines[n].rhs:.6g}" for n in bad
        )
        raise RunnerError(
            f"auto-path {'/'.join(bad)} violated at r={r} AU, R={R} m, sigma={sigma} Pa,"
            f" p={p:.6g} Pa, t={t:.6g} m: {detail}"
        )
    return rep


def auto_state(r, R, sigma, organism, inputs: VesselInputs = REGISTERED, p0=None):
    """The design: p = p*(r, R, σ), t = t_min(p*) at the input σ; returns (p, t, report).

    Inside the melt door the report names BURST with σ_eff = 0 printed (§4); the wall
    t_min(p*) there is the one the input σ would size, shown for display only."""
    p = self_consistent_pressure(r, R, sigma, **inputs.thermal(), p0=p0)
    t = wall_thickness(p, R, sigma)
    return p, t, check_auto_path(p, t, r, R, sigma, organism, inputs)


# ---------------------------------------------------------------- the edge rule (§6)
@dataclass(frozen=True)
class Edge:
    edge: float  # 0.0 when the window is empty
    binding: str | None
    roots: dict  # candidate line -> root inside the bracket
    tie: bool
    bracket: tuple | None
    counterfactual: dict  # later roots of registered lines, never the edge


def _bisect(fn, lo, hi, width):
    f_lo = fn(lo)
    for _ in range(200):
        if hi - lo <= width:
            break
        mid = 0.5 * (lo + hi)
        f_mid = fn(mid)
        if (f_mid >= 0) == (f_lo >= 0):
            lo, f_lo = mid, f_mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def find_edge(
    nodes,
    margins,
    *,
    window_lines=WINDOW_LINES,
    binding_lines=BINDING_LINES,
    eps=None,
    tie_tol,
    refine_width,
):
    """§6's edge rule on a node grid.

    margins(x) -> {line: margin}, positive holds. The bracket is the last all-HOLD node and
    the first any-VIOLATED node; candidates are binding lines that hold at the lower node and
    violate at the upper; each candidate's margin is bisected to its root; the edge is the
    SMALLEST root and `binding` its line; within tie_tol(a, b) load order decides.
    Roots of other binding lines at later nodes are returned as counterfactual."""
    eps = eps or {
        "FREEZE": EPS_FREEZE_K,
        "STARVE": EPS_STARVE_OPAQUE,
        "OPAQUE": EPS_STARVE_OPAQUE,
    }
    cache = {}

    def at(i):
        if i not in cache:
            cache[i] = margins(nodes[i])
        return cache[i]

    def viol(m, ln):
        return m[ln] < -eps.get(ln, 0.0)

    def root(ln, lo, hi):
        return _bisect(lambda x: margins(x)[ln], lo, hi, refine_width(lo, hi))

    first_bad = None
    for i in range(len(nodes)):
        if any(viol(at(i), ln) for ln in window_lines):
            first_bad = i
            break
    if first_bad is None:
        raise ValueError("no node violates: the window does not close on this grid")
    if first_bad == 0:
        return Edge(0.0, None, {}, False, None, {})
    lo, hi = nodes[first_bad - 1], nodes[first_bad]
    m_lo, m_hi = at(first_bad - 1), at(first_bad)
    cands = [ln for ln in binding_lines if not viol(m_lo, ln) and viol(m_hi, ln)]
    if not cands:
        others = [ln for ln in window_lines if viol(m_hi, ln)]
        raise RuntimeError(
            f"window closes at node {hi} on {others}, none of them a binding line: a finding"
        )
    roots = {ln: root(ln, lo, hi) for ln in cands}
    smallest = min(roots.values())
    tied = [ln for ln in LOAD_ORDER if ln in roots and tie_tol(roots[ln], smallest)]
    binding = tied[0]
    counterfactual = {}
    for ln in binding_lines:
        if ln in roots:
            continue
        for j in range(first_bad, len(nodes)):
            if viol(at(j), ln):
                if not viol(at(j - 1), ln):
                    counterfactual[ln] = root(ln, nodes[j - 1], nodes[j])
                break
    return Edge(roots[binding], binding, roots, len(tied) > 1, (lo, hi), counterfactual)


GRID_R_AU = np.round(np.arange(1.04, 3.00 + 1e-9, 0.01), 2)
GRID_R_M = np.logspace(1.0, 6.0, 101)
SIGMAS_PA = (0.7e6, 1.5e6, 3.1e6)


def _window_margins(organism, inputs, fn_state):
    def margins(x):
        rep = fn_state(x)
        return {ln: rep.lines[ln].margin for ln in WINDOW_LINES}

    return margins


def r_close(R, sigma, organism, inputs: VesselInputs = REGISTERED, nodes=GRID_R_AU):
    """The largest r with the window open at fixed R (§6), bisected to below 1e-4 AU."""
    margins = _window_margins(
        organism, inputs, lambda r: auto_state(float(r), R, sigma, organism, inputs)[2]
    )
    return find_edge(
        [float(x) for x in nodes],
        margins,
        tie_tol=lambda a, b: abs(a - b) <= EDGE_TOL_R_AU,
        refine_width=lambda lo, hi: EDGE_TOL_R_AU * 1e-4,
    )


def r_window(r, sigma, organism, inputs: VesselInputs = REGISTERED, nodes=GRID_R_M):
    """The largest R with the window open at fixed r (§6), bisected to below 0.1%."""
    margins = _window_margins(
        organism, inputs, lambda R: auto_state(r, float(R), sigma, organism, inputs)[2]
    )
    return find_edge(
        [float(x) for x in nodes],
        margins,
        tie_tol=lambda a, b: abs(a - b) <= EDGE_TOL_R_REL * min(a, b),
        refine_width=lambda lo, hi: EDGE_TOL_R_REL * 1e-4 * lo,
    )
