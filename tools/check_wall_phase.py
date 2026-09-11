# Section 17, sweeping the sweep's own output. A section-13-class pairing: the project
# concludes (a) the pressure wall is ICE, taking its tensile strength 0.7-3.1 MPa from
# Petrovic via Hirata, and (b) in the two-body balance of section 13 S7 the shell sits at
# sigma*Ts^4 = A, i.e. Ts = T_eq exactly, independent of tau. No expression contains both.
# Ask what temperature that wall is actually at, and whether ice can be there.
#
# Melting, not sublimation, is the right test for the INNER face: it sees the interior
# pressure (2.2-3.0 kPa), which is above water's triple point (611.657 Pa), so liquid is a
# phase available to it. The melting point of ice Ih only DECREASES with pressure
# (~ -0.0074 K/bar), so 273.15 K is the most generous possible threshold.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(120)
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from sim.thermal import equilibrium_temperature

T_MELT = 273.15  # K, ice Ih at low pressure; the most generous threshold available
T_EQ_1AU = equilibrium_temperature(1.0, area_ratio=4.0)  # algal sphere, the sited case


def shell_and_core(tau: float, t_eq: float) -> tuple[float, float]:
    """Solve section 13's own two-body system for (T_shell, T_core) at transmittance tau.
      core:  tau*A + S_s = S_c
      shell: (1-tau)*A + S_c = 2*S_s      (S = sigma*T^4, A normalised to sigma*t_eq^4)
    """
    a = t_eq**4
    m = np.array([[1.0, -1.0], [-2.0, 1.0]])
    b = np.array([-tau * a, -(1.0 - tau) * a])
    s_s, s_c = np.linalg.solve(m, b)
    return float(s_s ** 0.25), float(s_c ** 0.25)


# --- CONTROL 1: reproduce the project's own published numbers before anything moves.
assert abs(T_EQ_1AU - 273.15 - 5.16) < 0.02, f"C1 FAILED: T_eq {T_EQ_1AU:.3f}"
_, c_tau1 = shell_and_core(1.0, T_EQ_1AU)
assert abs(c_tau1 - 273.15 - 57.82) < 0.05, f"C1 FAILED: tau=1 core {c_tau1 - 273.15:.2f}"
_, c_s7 = shell_and_core(0.3013, T_EQ_1AU)
assert abs(c_s7 - 273.15 - 24.10) < 0.05, f"C1 FAILED: S7 core {c_s7 - 273.15:.2f}"
print("control 1 OK -- reproduces published 5.16 C, tau=1 -> 57.82 C, S7 tau=0.3013 -> 24.10 C")

# --- CONTROL 2: the shell temperature must come out INDEPENDENT of tau and equal to T_eq.
# That is the algebraic content of "add the two equations -> sigma*Ts^4 = A". If this fails,
# the finding below is an artifact of the solver, not of the model.
for ta in (0.0, 0.2156, 0.3013, 0.5, 1.0):
    s, _ = shell_and_core(ta, T_EQ_1AU)
    assert abs(s - T_EQ_1AU) < 1e-9, f"C2 FAILED: tau={ta} gives T_shell {s:.6f}, want {T_EQ_1AU:.6f}"
print(f"control 2 OK -- T_shell = T_eq = {T_EQ_1AU:.2f} K for every tau in [0, 1]\n")

print("=== is the wall ice, at 1 AU, where every number in sections 13-15 was computed? ===")
s, c = shell_and_core(0.3013, T_EQ_1AU)
print(f"  shell (outer, coldest part of the wall): {s:8.2f} K = {s - 273.15:6.2f} C")
print(f"  interior (inner face of the same wall):  {c:8.2f} K = {c - 273.15:6.2f} C")
print(f"  ice Ih melts at:                         {T_MELT:8.2f} K =   0.00 C")
assert s > T_MELT, "the shell is below freezing -- there is no finding here"
print(f"\n  => the COLDEST part of the wall is {s - T_MELT:.2f} K ABOVE the melting point.")
print("     No part of it is ice. A gradient wall is worse, not better: its inner face")
print(f"     sits at the interior temperature, {c - 273.15:.2f} C.\n")

# --- CONTROL 3 (positive control): the predicate must be able to return the other answer,
# or it is not a test. Move outward until the shell freezes and confirm it stops firing.
r_freeze = (T_EQ_1AU / T_MELT) ** 2
s_far, _ = shell_and_core(0.3013, equilibrium_temperature(r_freeze * 1.05, area_ratio=4.0))
assert s_far < T_MELT, "CONTROL 3 FAILED: the melting predicate cannot return 'frozen'"
print(f"control 3 OK -- beyond {r_freeze:.4f} AU the same predicate reports FROZEN\n")

print("=== the annulus in which an ICE vessel holding LIQUID water can exist ===")
print("  inner edge: the shell must be below freezing, else the wall is not a solid")
print("  outer edge: the interior must be above freezing, else there is no liquid to hold\n")
print(f"{'tau':>8} {'inner edge (AU)':>16} {'outer edge (AU)':>16} {'width (AU)':>12} {'1 AU inside?':>13}")
for lab, ta in (("0.2156 (strong dust)", 0.2156), ("0.3013 (S7 mid)", 0.3013), ("0.3429 (S7 strong wall)", 0.3429)):
    inner = (T_EQ_1AU / T_MELT) ** 2
    core_factor = (1.0 + ta) ** 0.25
    outer = (core_factor * T_EQ_1AU / T_MELT) ** 2
    print(f"{lab:>23} {inner:13.4f} {outer:16.4f} {outer - inner:12.4f} {'NO':>13}")
print(f"\n1.0 AU is BELOW every inner edge ({(T_EQ_1AU / T_MELT) ** 2:.4f} AU), so the vessel")
print("modelled throughout sections 13-15 is at a distance where it cannot be solid.")
print(f"For scale, Q2b's algal temperature limit is 1.1945 AU -- the annulus sits INSIDE it.")
# IRON_LAW_OK
# ---------------------------------------------------------------------------
# What the finding COSTS (the section 16 rule: a defect is not priced until its
# consequence is measured). Re-solve section 13's fixed point at the annulus instead
# of at 1 AU. Requires the two spectra in cwd, as check_s3_scattering.py does:
#   curl -sL https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat -o iop2008.dat
#   curl -sL https://raw.githubusercontent.com/pvlib/pvlib-python/main/pvlib/data/ASTMG173.csv -o ASTMG173.csv
import math

rows = []
for line in open("ASTMG173.csv"):
    q = line.strip().split(",")
    if len(q) < 2:
        continue
    try:
        rows.append((float(q[0]), float(q[1])))
    except ValueError:
        pass
assert len(rows) > 1900, "PARSER FAILED on ASTMG173.csv"
lam = np.array([r[0] for r in rows])
irr = np.array([r[1] for r in rows])
ice = []
for line in open("iop2008.dat"):
    q = line.split()
    if len(q) != 3:
        continue
    try:
        ice.append((float(q[0]) * 1000.0, float(q[2])))
    except ValueError:
        pass
assert len(ice) > 400, "PARSER FAILED on iop2008.dat"
il = np.array([r[0] for r in ice])
im = np.array([r[1] for r in ice])
sel = (il >= 250) & (il <= 4200)
k_pure = 4.0 * math.pi * np.exp(np.interp(lam, il[sel], np.log(im[sel]))) / (lam * 1e-9)
TOT = np.trapezoid(irr, lam)
R_ORG = 10e3


def buck_pa(t_c):
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c))) * 100.0


def tau_of(t_m):
    return float(np.trapezoid(np.exp(-k_pure * t_m) * irr, lam) / TOT)


def solve(r_au, sigma):
    """Section 13's damped fixed point p -> t -> tau -> T -> p_sat, at distance r_au."""
    t_eq = equilibrium_temperature(r_au, area_ratio=4.0)
    p = 882.0
    for _ in range(400):
        t_m = p * R_ORG / (2.0 * sigma)
        pn = buck_pa((1.0 + tau_of(t_m)) ** 0.25 * t_eq - 273.15)
        if abs(pn - p) < 1e-7:
            p = pn
            break
        p = 0.5 * p + 0.5 * pn
    t_m = p * R_ORG / (2.0 * sigma)
    ta = tau_of(t_m)
    return p, ta, (1.0 + ta) ** 0.25 * t_eq, t_m


# --- CONTROL 4: at 1 AU this must reproduce section 13 S7's own published fixed point.
p1, ta1, ti1, _ = solve(1.0, 1.5e6)
assert abs(ti1 - 273.15 - 24.10) < 0.15, f"C4 FAILED: 1 AU interior {ti1 - 273.15:.2f} C vs 24.10"
assert abs(p1 / 1000 - 3.002) < 0.05, f"C4 FAILED: 1 AU p {p1 / 1000:.3f} kPa vs 3.002"
print(f"\ncontrol 4 OK -- the solver reproduces S7's own 1 AU fixed point "
      f"({ti1 - 273.15:.2f} C, {p1 / 1000:.3f} kPa)\n")

print("=== section 13's fixed point re-solved INSIDE the annulus (sigma = 1.5 MPa) ===")
# R_max is deliberately NOT reported here. It needs the attenuation coefficient k, and this
# tool has only a spectrum-averaged effective k, while section 13 used a monochromatic one at
# 680 nm. The two differ by ~3x, so printing mine beside section 13's published 11.9 km would
# be an uncontrolled number contradicting a controlled one. The finding does not need it.
print(f"{'r (AU)':>9} {'T_shell':>9} {'tau':>8} {'T_int':>9} {'p_self':>10} {'wall t':>9}  wall phase")
inner_edge = (T_EQ_1AU / T_MELT) ** 2
for r in (1.0, inner_edge, 1.10, 1.1446):
    p, ta, ti, tm = solve(r, 1.5e6)
    ts = equilibrium_temperature(r, area_ratio=4.0)
    if abs(ts - T_MELT) < 1e-6:
        flag = "  at the melting point exactly"
    elif ts > T_MELT:
        flag = "  <- wall MOLTEN"
    else:
        flag = "  solid"
    print(f"{r:9.4f} {ts - 273.15:8.2f}C {ta:8.4f} {ti - 273.15:8.2f}C {p / 1000:9.3f}kPa "
          f"{tm:8.2f}m{flag}")

p_in, ta_in, ti_in, _ = solve(inner_edge, 1.5e6)
assert p_in < p1, "moving to the annulus should LOWER the self-consistent pressure"
assert 882.0 <= p_in <= 10e3, f"p at the annulus left the registered bracket: {p_in:.0f} Pa"
print(f"\n=> Moving to the nearest distance where the wall is actually solid takes p from")
print(f"   {p1 / 1000:.3f} kPa to {p_in / 1000:.3f} kPa -- still INSIDE the registered")
print(f"   [882 Pa, 10 kPa], and DOWNWARD, the same direction dust pushes it (section 15).")
print("   So this finding, like S3's, cannot overturn S7 -- it can only deepen it.")
# IRON_LAW_OK
# ---------------------------------------------------------------------------
# ...AND THE SAME RULE APPLIED ONCE MORE PARTLY REVERSES THE FINDING ABOVE.
# `albedo = 0.0` is declared in sim/thermal.py and used for the SOLAR side of the balance.
# Pair it with Q3's conclusion that the shell is ICE -- a pairing that, like the melting one,
# appears in no expression. A reflective shell absorbs less, runs colder, and freezes sooner.
# The melting finding above is therefore real IN THE MODEL AS WRITTEN, but conditional on a
# declared value that the ice conclusion contradicts. Measure how little albedo it takes.
a_thresh = 1.0 - (T_MELT / T_EQ_1AU) ** 4
assert 0.0 < a_thresh < 0.15, f"threshold albedo {a_thresh:.4f} is outside a sane range"
print("\n=== how robust is the melting finding? the albedo that would undo it ===")
print(f"  T_shell(albedo) = (1 - albedo)^0.25 * {T_EQ_1AU:.2f} K")
print(f"  the shell reaches the melting point at 1 AU when albedo = {a_thresh:.4f} "
      f"({a_thresh * 100:.1f}%)")
print(f"{'albedo':>10} {'T_shell at 1 AU':>17} {'phase at 1 AU':>15}")
for a in (0.0, 0.05, a_thresh, 0.10, 0.30, 0.60):
    ts = (1.0 - a) ** 0.25 * T_EQ_1AU
    print(f"{a:10.4f} {ts - 273.15:14.2f} C {('MOLTEN' if ts > T_MELT + 1e-9 else 'solid'):>15}")
# --- CONTROL 5: the threshold must actually be a threshold in both directions.
assert (1.0 - (a_thresh - 0.02)) ** 0.25 * T_EQ_1AU > T_MELT, "C5 FAILED: below threshold not molten"
assert (1.0 - (a_thresh + 0.02)) ** 0.25 * T_EQ_1AU < T_MELT, "C5 FAILED: above threshold not solid"
print(f"\ncontrol 5 OK -- the predicate flips in BOTH directions across {a_thresh:.4f}\n")
print("So the wall needs to reflect only 7% of incident sunlight to be solid at 1 AU, and")
print("the project's OWN dust model (section 15) gives it a scattering length of 18-116 m")
print("against a wall ~10 m thick -- a wall that scatters is a wall with nonzero albedo.")
print("The Beer-Lambert tau used throughout models pure ABSORPTION and no reflection, which")
print("is exactly consistent with albedo = 0 -- consistently wrong rather than inconsistent.")
print("\n=> BOTH are real pairings. The melting one holds in the model as written; its")
print("   MAGNITUDE is not robust to the albedo one. Neither was ever asked, and both live")
print("   under the SAME section 11 clearance that already missed S7 -- the third thing")
print("   that one bullet has been found to miss.")
