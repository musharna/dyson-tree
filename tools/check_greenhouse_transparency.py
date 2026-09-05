# Section 13 S7: the contained-temperature result T_interior = (N+1)^0.25 * T_eq assumes an
# SW-TRANSPARENT, IR-opaque wall. Section 12's own optics say that wall is not SW-transparent:
# NIR carries 53% of TSI and ice absorbs it hard, so a pressure-bearing wall passes only a
# fifth of the solar energy. The thermal model and the optical model describe the same wall
# and disagree about it -- section 12's rule, applied across two models instead of two numbers.
#
# Redo the shell balance WITHOUT assuming transparency. Per unit area, shell transmittance tau:
#   core:  tau*A + sigma*Ts^4 = sigma*Tc^4
#   shell: (1-tau)*A + sigma*Tc^4 = 2*sigma*Ts^4
#   add -> sigma*Ts^4 = A, so sigma*Tc^4 = (1+tau)*A  =>  T_interior = (1+tau)^0.25 * T_eq
# The project's formula is the tau = 1 special case. Same idealization as the original
# derivation (grey, IR-opaque, radiative only) -- this changes ONE assumption, not the model.
#
# tau depends on wall thickness, thickness on pressure, pressure on temperature, temperature
# on tau: a FIXED POINT. Solving it is exactly what section 11 S1 said a re-registered Q3
# must do -- derive p from T_interior instead of declaring it.
#
# Fetch first (neither table is redistributed here):
#   curl -sL https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat -o iop2008.dat
#   curl -sL https://raw.githubusercontent.com/pvlib/pvlib-python/main/pvlib/data/ASTMG173.csv -o ASTMG173.csv
import signal
import sys
import math

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(60)
import numpy as np

sys.path.insert(0, "/home/mjarnold/dyson-tree")
from sim.thermal import equilibrium_temperature

R_ORGANISM_M = 10e3

rows = []
for line in open("ASTMG173.csv"):
    p = line.strip().split(",")
    if len(p) < 2:
        continue
    try:
        rows.append((float(p[0]), float(p[1])))
    except ValueError:
        pass
assert len(rows) > 1900, f"PARSER FAILED on ASTMG173.csv -- {len(rows)} rows"
lam = np.array([r[0] for r in rows])
irr = np.array([r[1] for r in rows])

ice = []
for line in open("iop2008.dat"):
    p = line.split()
    if len(p) != 3:
        continue
    try:
        ice.append((float(p[0]) * 1000.0, float(p[2])))
    except ValueError:
        pass
assert len(ice) > 400, f"PARSER FAILED on iop2008.dat -- {len(ice)} rows"
il = np.array([r[0] for r in ice])
im = np.array([r[1] for r in ice])
sel = (il >= 250) & (il <= 4200)
k_all = 4.0 * math.pi * np.exp(np.interp(lam, il[sel], np.log(im[sel]))) / (lam * 1e-9)
TOT = np.trapezoid(irr, lam)

# --- CONTROL 1: the band splits the way section 13 reports (NIR is the majority of TSI)
fr = {}
for lo, hi, nm in [(280, 400, "UV"), (400, 700, "PAR"), (700, 4000, "NIR")]:
    b = (lam >= lo) & (lam <= hi)
    fr[nm] = np.trapezoid(irr[b], lam[b]) / TOT
assert abs(fr["NIR"] - 0.5305) < 0.004, (
    f"CONTROL 1 FAILED: NIR fraction {fr['NIR']:.4f}"
)
assert abs(fr["PAR"] - 0.3932) < 0.004, (
    f"CONTROL 1 FAILED: PAR fraction {fr['PAR']:.4f}"
)

# --- CONTROL 2: tau = 1 must reproduce the project's OWN published contained temperature.
# If the generalisation cannot return the number it generalises, it is not a generalisation.
T_EQ_ALGAL = equilibrium_temperature(1.0, area_ratio=4.0)
assert abs(T_EQ_ALGAL - 273.15 - 5.16) < 0.02, (
    f"CONTROL 2 FAILED: T_eq {T_EQ_ALGAL:.3f}"
)
t_shell_transparent = (1.0 + 1.0) ** 0.25 * T_EQ_ALGAL - 273.15
assert abs(t_shell_transparent - 57.82) < 0.05, (
    f"CONTROL 2 FAILED: tau=1 gives {t_shell_transparent:.2f} C, published 57.82"
)
print(
    f"control 1 OK -- UV {fr['UV']:.4f} / PAR {fr['PAR']:.4f} / NIR {fr['NIR']:.4f} of TSI"
)
print("control 2 OK -- tau=1 reproduces the published 57.82 C exactly\n")


def tau_sw(t_m):
    """Solar-energy-weighted transmittance of a pure-ice wall of thickness t_m."""
    return float(np.trapezoid(np.exp(-k_all * t_m) * irr, lam) / TOT)


def buck_pa(t_c):
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c))) * 100.0


print(
    "=== S7: the greenhouse premise against the wall the optics actually describe ==="
)
print(
    f"{'wall t':>9} {'tau_SW':>8} {'T_int (1+tau)^.25':>19} {'vs published 57.82 C':>21}"
)
for t_m in (0.625, 16.1, 29.1, 60.1, 128.7):
    ta = tau_sw(t_m)
    ti = (1.0 + ta) ** 0.25 * T_EQ_ALGAL - 273.15
    print(f"{t_m:8.1f}m {ta:8.4f} {ti:16.2f} C {ti - 57.82:19.2f} C")

print("\n=== the FIXED POINT: p -> t -> tau -> T -> p_sat, iterated to convergence ===")
print("(section 11 S1's requirement: derive p from T_interior instead of declaring it)")
print(
    f"\n{'sigma':>8} {'wall t':>10} {'tau_SW':>8} {'T_int':>9} {'p_self':>11} {'in [882 Pa, 10 kPa]?':>22}"
)
out = {}
for s_mpa in (3.1, 1.5, 0.7):
    sigma = s_mpa * 1e6
    p = 882.0  # start at the registered floor
    for _ in range(200):
        t_m = p * R_ORGANISM_M / (2.0 * sigma)
        ti_k = (1.0 + tau_sw(t_m)) ** 0.25 * T_EQ_ALGAL
        p_new = buck_pa(ti_k - 273.15)
        if abs(p_new - p) < 1e-6:
            p = p_new
            break
        p = 0.5 * p + 0.5 * p_new  # damped, the map is stiff in tau
    t_m = p * R_ORGANISM_M / (2.0 * sigma)
    ta = tau_sw(t_m)
    ti = (1.0 + ta) ** 0.25 * T_EQ_ALGAL - 273.15
    out[s_mpa] = (t_m, ta, ti, p)
    ok = "YES -- inside" if 882 <= p <= 10e3 else "NO"
    print(
        f"{s_mpa:7.1f}M {t_m:9.2f}m {ta:8.4f} {ti:8.2f}C {p / 1000:10.3f}kPa {ok:>22}"
    )

print("\nAgainst section 11 S1, which assumed a fully SW-transparent wall:")
print(
    "  S1: N=1 -> T_int 57.82 C -> p_sat 18.02 kPa -> 1.8x ABOVE the registered ceiling."
)
for s_mpa in (3.1, 1.5, 0.7):
    t_m, ta, ti, p = out[s_mpa]
    print(
        f"  sigma {s_mpa:3.1f} MPa: T_int {ti:5.2f} C -> p {p / 1000:6.3f} kPa "
        f"-- {18020 / p:5.2f}x LOWER than S1's figure"
    )

# --- and what that does to framing A, the question the whole Q3 arc is about ---
print("\n=== framing A at the SELF-CONSISTENT pressure (red band, k = 0.38623 /m) ===")
print("R_max = 2*sigma*|ln tau_min|/(k*p), tau_min = 0.01, against the assumed R = 10 km:")
K_RED, TAU_MIN = 0.38623, 0.01
for s_mpa in (3.1, 1.5, 0.7):
    t_m, ta, ti, p = out[s_mpa]
    rk = 2.0 * (s_mpa * 1e6) * abs(math.log(TAU_MIN)) / (K_RED * p) / 1000.0
    print(
        f"  sigma {s_mpa:3.1f} MPa, p {p / 1000:6.3f} kPa -> R_max {rk:8.2f} km"
        f"   {'BINDS at 10 km' if rk < 10 else 'does not bind'}"
    )
print("\nS1 reported 0.93-4.10 km (BINDS decisively) from its 18.02 kPa. At the")
print("self-consistent pressure the answer is SPLIT BY ICE STRENGTH -- which is the honest")
print("state of framing A, and it is neither section 9's falsification nor S1's binding.")
