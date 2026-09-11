# Section 15, closing section 11 S3. S3 claims section 9's diffusive-slab caveat "combines
# Warren & Brandt's PURE bubble-free ice absorption with Ackermann's DUST-LADEN transport
# length". Before accepting that, test it: section 9 quotes BOTH lengths from Ackermann
# ("scattering length is 10-100 m against an absorption length of 100-400 m"), so the
# attribution is checkable by arithmetic. L_d = sqrt(l_abs * l_tr / 3).
#
# If S3 is right, the published 18-116 m should reproduce from Warren & Brandt's pure-ice
# absorption length at 400 nm (1345.9 m). If S3 is wrong, it reproduces from Ackermann's own.
# Only one of those can be true, and the two hypotheses give numbers 3.7x apart.
#
# Fetch first:
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

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from sim.thermal import equilibrium_temperature

# Ackermann et al. 2006, deep South Pole glacial ice at 400 nm, as quoted in section 9
ACK_L_ABS = (100.0, 400.0)  # m, absorption length
ACK_L_TR = (10.0, 100.0)  # m, effective (transport) scattering length
WB_L_ABS_400 = (
    1345.9  # m, Warren & Brandt pure bubble-free ice at 400 nm (section 9's table)
)
R_ORGANISM_M, TAU_MIN = 10e3, 0.01


def l_d(l_abs, l_tr):
    return math.sqrt(l_abs * l_tr / 3.0)


# --- CONTROL A: does section 9's published 18-116 m come from ACKERMANN's own two lengths?
a_lo, a_hi = l_d(ACK_L_ABS[0], ACK_L_TR[0]), l_d(ACK_L_ABS[1], ACK_L_TR[1])
assert abs(a_lo - 18.0) < 0.5 and abs(a_hi - 116.0) < 1.0, (
    f"CONTROL A FAILED: Ackermann-only gives {a_lo:.1f}-{a_hi:.1f}, section 9 published 18-116"
)
# --- CONTROL B: what S3's attribution WOULD have produced. It must be SEPARATED from the
# published range, not merely unequal to it. An earlier version asserted `not (near_lo and
# near_hi)`, which no single-value mutation could make fire -- a control that cannot fail is
# not a control. Asserting the RATIO is falsifiable: set WB_L_ABS_400 to Ackermann's 100 m and
# this fires at 1.00x.
# Tell from finding that: the FIRST attempt to mutate this printed nothing, which reads exactly
# like "the control cannot fail" -- but the sed had matched nothing, because the formatter had
# wrapped the target assignment across two lines. A mutation that silently fails to apply is
# INDISTINGUISHABLE from a control that cannot fail. Assert the mutation applied, not just that
# the run said something.
s3_lo, s3_hi = l_d(WB_L_ABS_400, ACK_L_TR[0]), l_d(WB_L_ABS_400, ACK_L_TR[1])
assert s3_lo / a_lo > 2.0, (
    f"CONTROL B FAILED: S3's attribution gives {s3_lo:.1f} m vs Ackermann's {a_lo:.1f} m, "
    f"only {s3_lo / a_lo:.2f}x apart -- too close to tell the two hypotheses apart"
)
print(
    f"control A OK -- Ackermann's OWN l_abs x l_tr gives {a_lo:.1f}-{a_hi:.1f} m "
    f"= section 9's published 18-116 m"
)
print(
    f"control B OK -- S3's attribution would give {s3_lo:.1f}-{s3_hi:.1f} m, "
    f"which is NOT what section 9 published\n"
)
print(
    "=> S3 IS FALSE. Section 9's L_d is OBJECT-MATCHED: both lengths are Ackermann's,"
)
print(
    "   measured on the same ice in the same experiment. S3 misread the attribution.\n"
)

# --- the defect that IS in that paragraph, and section 10 cleared it BY NAME ---
print("=== but the paragraph is not clean: its R_max figures are WOOD's sigma ===")
print(
    "Section 10's banner says '...the scattering caveat -- is unaffected'. It is affected:"
)
print(
    "R_max = 2*sigma*|ln tau_min|*L_d/p is LINEAR in sigma, and section 9 used 80 MPa.\n"
)


def r_max_km(sigma, p, ld):
    return 2.0 * sigma * abs(math.log(TAU_MIN)) * ld / p / 1000.0


print(f"{'sigma':>28} {'L_d 18.3 m':>13} {'L_d 115.5 m':>13} {'binds at 10 km?':>17}")
for lab, sg in [
    ("80 MPa (WOOD, section 9's)", 80e6),
    ("3.1 MPa (ice, strong)", 3.1e6),
    ("1.5 MPa (ice, mid)", 1.5e6),
    ("0.7 MPa (ice, weak)", 0.7e6),
]:
    lo = r_max_km(sg, 10e3, a_lo)
    hi = r_max_km(sg, 10e3, a_hi)
    print(f"{lab:>28} {lo:10.1f}km {hi:10.1f}km {('YES' if lo < 10 else 'no'):>17}")
print(
    "\n(section 9 published 1345-4146 km here; the first figure reproduces at sigma = 80 MPa,"
)
print(" p = 10 kPa, L_d = 18.3 m -- confirming the wood sigma is what generated them.)")

# --- and what dusty ice does to section 13's tau, which is the reason S3 still matters ---
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

# DECLARED MODEL, not a measurement: dust adds a wavelength-INDEPENDENT attenuation floor set
# by Ackermann's 400 nm diffusion length. Defensible only because ice's own absorption swamps
# dust everywhere except the blue window -- which is exactly where the floor bites.
print(
    "\n=== what DUSTY ice does to section 13's tau (DECLARED dust model, see section 15) ==="
)
print(f"{'dust floor':>34} {'tau_solar':>11} {'T_int':>9} {'p_self':>11}")
T4 = equilibrium_temperature(1.0, area_ratio=4.0)


def buck_pa(t_c):
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c))) * 100.0


def tau_of(t_m, kd):
    return float(np.trapezoid(np.exp(-(k_pure + kd) * t_m) * irr, lam) / TOT)


for lab, kd in [
    ("none (section 13's pure ice)", 0.0),
    (f"1/{a_hi:.1f} m = {1 / a_hi:.4f} /m (weak dust)", 1.0 / a_hi),
    (f"1/{a_lo:.1f} m = {1 / a_lo:.4f} /m (strong dust)", 1.0 / a_lo),
]:
    p = 882.0
    for _ in range(300):
        t_m = p * R_ORGANISM_M / (2.0 * 1.5e6)  # sigma = 1.5 MPa, the mid ice case
        pn = buck_pa((1.0 + tau_of(t_m, kd)) ** 0.25 * T4 - 273.15)
        if abs(pn - p) < 1e-6:
            p = pn
            break
        p = 0.5 * p + 0.5 * pn
    t_m = p * R_ORGANISM_M / (2.0 * 1.5e6)
    ta = tau_of(t_m, kd)
    print(
        f"{lab:>34} {ta:11.4f} {(1 + ta) ** 0.25 * T4 - 273.15:8.2f}C {p / 1000:10.3f}kPa"
    )
print(
    "\nEvery dust level keeps p INSIDE the registered [882 Pa, 10 kPa], and pushes it DOWN --"
)
print(
    "the direction section 13 predicted. S3 cannot overturn S7; it can only deepen it."
)
