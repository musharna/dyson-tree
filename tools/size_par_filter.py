# Section 11 S2, SIZED -- and section 12 S5, FOUND BY THE ATTEMPT.
#
# S2 recorded that sim/physiology.py delivers PAR as one flat full-spectrum scalar
# (TSI x 0.45 x 4.57) to an organism that section 10 shows must sit behind a blue-pass ice
# wall, but never said HOW BIG the mismatch is. This measures it.
#
# S2's own rule is that two inputs may only be combined once they are SHOWN to describe the
# same object. So this script does not assume the solar spectrum it uses is the one
# physiology.py's scalars came from -- it tries to prove it, by re-deriving PAR_FRACTION and
# PHOTONS_PER_J from the spectrum and comparing them to the live constants.
#
# PHOTONS_PER_J reproduced. PAR_FRACTION did not: the top-of-atmosphere PAR energy fraction
# is 0.388, not the declared 0.45. That pair is in section 11's own "checked and CLEARED"
# list, cleared on the ASSERTION that all three factors describe the top of atmosphere.
# Measuring it was the check that assertion never got. See section 12.
#
# Fetch the two public tables first (neither is redistributed here):
#   curl -sL https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat -o iop2008.dat
#   curl -sL https://raw.githubusercontent.com/pvlib/pvlib-python/main/pvlib/data/ASTMG173.csv -o ASTMG173.csv
# then run this from the directory holding them.
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
from sim.physiology import PAR_FRACTION, PHOTONS_PER_J, TSI_W_M2
from sim.thermal import equilibrium_temperature

H_PLANCK, C_LIGHT, N_AVOGADRO = 6.62607015e-34, 2.99792458e8, 6.02214076e23
PAR_LO, PAR_HI = 400.0, 700.0
R_ORGANISM_M = 10e3  # the radius the project assumes throughout
SOLAR_CONSTANT = 1366.1  # ASTM G173-03's own nominal total

# ---------------------------------------------------------------- solar spectrum
# ASTM G173-03 col 2 = EXTRATERRESTRIAL (AM0) reference spectrum, col 3 = global tilt
# (AM1.5G, i.e. at the SURFACE). Both in W m^-2 nm^-1. Carrying the surface column too is
# what lets the script say which object the declared 0.45 actually resembles.
rows = []
for line in open("ASTMG173.csv"):
    p = line.strip().split(",")
    if len(p) < 3:
        continue
    try:
        rows.append((float(p[0]), float(p[1]), float(p[2])))
    except ValueError:
        pass
assert len(rows) > 1900, (
    f"PARSER FAILED on ASTMG173.csv -- {len(rows)} rows, refusing to report"
)
lam = np.array([r[0] for r in rows])
irr = np.array([r[1] for r in rows])  # AM0
sfc = np.array([r[2] for r in rows])  # AM1.5G
print(f"parsed {len(rows)} spectral rows, {lam.min():.0f}-{lam.max():.0f} nm")

par = (lam >= PAR_LO) & (lam <= PAR_HI)
assert par.sum() > 250, f"too few PAR rows ({par.sum()}) -- refusing to report"
nph = irr * (lam * 1e-9) / (H_PLANCK * C_LIGHT)  # photons s^-1 m^-2 nm^-1

# Each control below was run against a mutant and SEEN TO FAIL for its stated reason -- a
# control never observed failing is not evidence. The mutants, and what each produced:
#   A  feed the AM1.5G surface column where AM0 belongs -> "band integrates to 1000.4 = 0.732"
#   B  denominator = truncated band instead of the solar constant -> "measured 0.3932"
#      (this is the exact bug the first draft of this script shipped)
#   C  drop the nm->m factor in the photon conversion    -> "4553214347.591 umol/J"
#   D  shift the ice wavelength grid by 5 nm             -> "at 550 nm: 0.4727 vs 0.4302"
# --- CONTROL A: the tabulated band recovers the solar constant less its out-of-band tail.
# G173 is truncated at 280-4000 nm, so it returns ~98.7% of 1366.1 W/m2. The residual is real
# UV/IR the table does not carry, NOT a parse error -- assert the ratio, not the total.
total = np.trapezoid(irr, lam)
assert 0.975 < total / SOLAR_CONSTANT < 1.005, (
    f"A FAILED: band integrates to {total:.1f} = {total / SOLAR_CONSTANT:.3f} of {SOLAR_CONSTANT}"
)

# --- CONTROL B: measure the PAR energy fraction at top of atmosphere. PAR_FRACTION is
# declared as a fraction of TSI, so the denominator is the FULL solar constant, not the
# truncated integral (which would inflate it by the missing tail). The assert pins the
# MEASUREMENT; the comparison against the declared constant is a finding, reported below.
par_e_am0 = np.trapezoid(irr[par], lam[par])
toa_frac = par_e_am0 / SOLAR_CONSTANT
assert abs(toa_frac - 0.3879) < 0.004, (
    f"B FAILED: TOA PAR fraction measured {toa_frac:.4f}"
)
sfc_frac = np.trapezoid(sfc[par], lam[par]) / np.trapezoid(sfc, lam)

# --- CONTROL C: re-derive PHOTONS_PER_J over PAR and compare to the LIVE constant
umol_per_j = (np.trapezoid(nph[par], lam[par]) / par_e_am0) / N_AVOGADRO * 1e6
assert abs(umol_per_j - PHOTONS_PER_J) < 0.10, (
    f"C FAILED: spectrum says {umol_per_j:.3f} umol/J, physiology.py declares {PHOTONS_PER_J}"
)

print(
    f"control A OK -- band = {total:.1f} W/m2 = {total / SOLAR_CONSTANT:.4f} of {SOLAR_CONSTANT}"
)
print(
    f"control C OK -- {umol_per_j:.3f} umol/J vs declared PHOTONS_PER_J {PHOTONS_PER_J}\n"
)

print("=== S5: PAR_FRACTION is not a top-of-atmosphere quantity ===")
print(
    f"  measured, AM0 (top of atmosphere)   : {toa_frac:.4f}   <- what irradiance() needs"
)
print(f"  measured, AM1.5G (at the surface)   : {sfc_frac:.4f}")
print(
    f"  declared in physiology.py, 3 preregs: {PAR_FRACTION:.4f}   <- exceeds even the surface value"
)
print(
    f"  => PAR overstated by {PAR_FRACTION / toa_frac:.3f}x at every heliocentric distance."
)
print(
    f"     Flux goes as 1/r^2, so an iso-flux distance moves {math.sqrt(PAR_FRACTION / toa_frac):.4f}x.\n"
)

# ---------------------------------------------------------------- ice absorption
ice = []
for line in open("iop2008.dat"):
    p = line.split()
    if len(p) != 3:
        continue
    try:
        ice.append((float(p[0]) * 1000.0, float(p[2])))  # um -> nm, m_im
    except ValueError:
        pass
assert len(ice) > 400, (
    f"PARSER FAILED on iop2008.dat -- {len(ice)} rows, refusing to report"
)
il = np.array([r[0] for r in ice])
im = np.array([r[1] for r in ice])
sel = (il >= 380) & (il <= 760)
# m_im spans decades across PAR, so interpolate in LOG space -- the physically natural form.
# MEASURED, not assumed: an earlier version of this comment claimed linear interpolation
# "would badly misstate the middle of every 10 nm gap". It does not. Against linear, the
# integrated f_photon moves by <= 0.5% (0.9976/0.9966/0.9952 at t = 29.1/60.1/128.7 m) and
# k at the off-grid 645 nm differs by 0.3%. The table's 10 nm grid is fine enough that this
# choice is NOT load-bearing, and control D cannot see it either -- D probes 400/550/680/700,
# all exactly ON that grid, where both schemes return the tabulated value. D discriminates
# wavelength REGISTRATION (a 5 nm grid shift fails it at 550 nm: 0.4727 vs 0.4302), not
# interpolation scheme. Recorded because the original comment was an unmeasured justification.
k_par = (
    4.0
    * math.pi
    * np.exp(np.interp(lam[par], il[sel], np.log(im[sel])))
    / (lam[par] * 1e-9)
)

# --- CONTROL D: reproduce section 10's committed transmission row (ice 3.1 MPa, t = 16.1 m)
for want_l, want_t in [
    (400.0, 0.9881),
    (550.0, 0.4302),
    (680.0, 1.97e-3),
    (700.0, 2.26e-4),
]:
    got = math.exp(-k_par[np.argmin(np.abs(lam[par] - want_l))] * 16.1)
    assert abs(math.log10(got) - math.log10(want_t)) < 0.02, (
        f"D FAILED at {want_l:.0f} nm: got {got:.4g}, section 10 committed {want_t:.4g}"
    )
print(
    "control D OK -- reproduces section 10's committed ice-3.1-MPa transmission row\n"
)


# ---------------------------------------------------------------- S2: the measurement
def buck_pa(t_c):
    return 6.1121 * math.exp((18.678 - t_c / 234.5) * (t_c / (257.14 + t_c))) * 100.0


t_eq = equilibrium_temperature(1.0, area_ratio=4.0)
P_SELF = buck_pa(t_eq * 2**0.25 - 273.15)  # S1: N=1 shell, ~18.0 kPa


def survey(p, sigma):
    t = (
        p * R_ORGANISM_M / (2.0 * sigma)
    )  # thin-wall hoop stress, the spec's own relation
    tau = np.exp(-k_par * t)
    tp, te = (
        np.trapezoid(tau * nph[par], lam[par]),
        np.trapezoid(tau * irr[par], lam[par]),
    )
    f_ph = tp / np.trapezoid(nph[par], lam[par])
    eff = (tp / te) / N_AVOGADRO * 1e6 if te > 0 else float("nan")
    below = np.where(tau >= 0.5)[0]
    return (
        t,
        f_ph,
        te / par_e_am0,
        eff,
        (lam[par][below[-1]] if len(below) else float("nan")),
    )


print(
    "=== S2, SIZED: PAR reaching a CONTAINED organism, R = 10 km, wall t = p*R/(2*sigma) ==="
)
print(
    "f_photon = fraction of the PAR photons physiology.py assumes arrive that actually do.\n"
)
print(
    f"{'pressure':>36} {'sigma':>7} {'wall t':>9} {'f_photon':>11} {'f_energy':>11} {'umol/J':>8} {'tau=.5':>8}"
)
res = {}
for lab, p in [
    ("882 Pa (bracket floor, UNCONTAINED T)", 882.0),
    ("10 kPa (bracket ceiling, Paul 2004)", 10e3),
    ("18.0 kPa (SELF-CONSISTENT, S1, N=1)", P_SELF),
]:
    for s_mpa in (3.1, 1.5, 0.7):
        t, f_ph, f_en, eu, cut = survey(p, s_mpa * 1e6)
        res[(round(p), s_mpa)] = (f_ph, eu)
        print(
            f"{lab:>36} {s_mpa:6.1f}M {t:8.1f}m {f_ph:11.3e} {f_en:11.3e} {eu:8.2f} {cut:6.0f}nm"
        )

flat = TSI_W_M2 * PAR_FRACTION * PHOTONS_PER_J
print(f"\nphysiology.py asserts irradiance(1.0) = {flat:.1f} umol photons m^-2 s^-1.")
print("Behind a self-consistent ice wall at the SELF-CONSISTENT pressure it is:")
for s_mpa in (3.1, 1.5, 0.7):
    f_ph, eu = res[(round(P_SELF), s_mpa)]
    corrected = TSI_W_M2 * toa_frac * PHOTONS_PER_J * f_ph
    print(
        f"  sigma {s_mpa:3.1f} MPa: {corrected:10.3e} umol m^-2 s^-1 "
        f"-- overstated {flat / corrected:9.3e}x (S5 x{PAR_FRACTION / toa_frac:.2f}, S2 x{1 / f_ph:.3e})"
    )
