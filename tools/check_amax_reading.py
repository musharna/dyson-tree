# Section 18: S6 has THREE readings, not two -- and section 16 priced the wrong one under
# reading B's name.
#
# Section 13 S6 established that a_max = 10.0 is consumed at three different temperatures:
#   Q1  net_carbon()                no factor at all, tissue at t_set  -> 293.00 K
#   Q2  net_carbon_at_equilibrium() linear ramp, 1.0 at and above t_opt -> 298.15 K (25.00 C)
#   Q2b net_carbon_adapted()        Gaussian, exactly 1.0 AT t_opt      -> the ADAPTED optimum
#                                                                         (278.31 K algal,
#                                                                          330.97 K vascular)
# Section 16 then offered two readings and priced them:
#   reading A -- a_max is the rate at 293 K          (leaves Q1 alone)
#   reading B -- a_max is the PEAK rate at t_opt     (leaves Q2b alone)
# and implemented reading B as a_max = 10.0 * 0.8439 = 8.4394.
#
# That factor is temperature_response(293, 265.15, 298.15) -- Q2's LINEAR ramp evaluated at
# Q2's DECLARED t_opt. It is the correction for the 298.15 K anchor, i.e. a third reading,
# call it C. Reading B's own definition ("the PEAK rate at t_opt", the temperature at which
# the GAUSSIAN equals 1) gives a completely different factor: 0.0272 for vascular at the
# registered omega = 20, a 31x difference from 0.8439.
#
# This tool proves both halves: that section 16's arm reproduces its published number (so the
# arm is correctly identified, not merely alleged), and that true reading B does something
# else entirely -- it removes Q1's compensation point altogether.
#
# Run from anywhere; needs no external data files.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(60)
sys.path.insert(0, "/home/mjarnold/dyson-tree")
from dataclasses import replace

from sim.organism import PRESETS, compensation_irradiance, crossover_distance_for
from sim.physiology import T_REF_K
from sim.thermal import (
    adapted_optimum,
    temperature_response,
    temperature_response_gaussian,
)

V, A = PRESETS["vascular"], PRESETS["algal"]
OMEGA = [10.0, 15.0, 20.0, 25.0, 30.0]  # experiments/q2b_adapted/prereg.yaml:67
T25 = V.t_opt  # 298.15 K -- sim/organism.py:37, "declared assumption, not grounded"
TOPT = {
    "algal": adapted_optimum(1.0, A.area_ratio, A.emissivity, A.albedo),
    "vascular": adapted_optimum(1.0, V.area_ratio, V.emissivity, V.albedo),
}

# --- CONTROL 1 (positive): the UNMODIFIED presets must reproduce Q1's committed numbers.
# A harness that cannot reproduce the baseline cannot be trusted to report a departure from it.
r_reg = crossover_distance_for(V, k=100.0)
ic_reg = compensation_irradiance(V)
assert abs(r_reg - 13.6851) < 1e-3, f"C1 FAILED: registered r* = {r_reg}"
assert abs(ic_reg - 6.9519) < 1e-3, f"C1 FAILED: registered I_c = {ic_reg}"
print(
    f"control 1 OK -- registered presets reproduce r* = {r_reg:.4f} AU, I_c = {ic_reg:.4f}"
)

# --- CONTROL 2 (positive): identify section 16's arm BY REPRODUCING ITS PUBLISHED NUMBER.
# This is the whole claim. If a_max = 8.4394 does not return section 16's 12.3971, then the
# arm is something other than what its source line says and this tool is wrong, not section 16.
f_lin = temperature_response(T_REF_K, V.t_min, T25)
assert abs(f_lin - 0.843939) < 1e-6, f"C2 FAILED: linear ramp gives {f_lin}"
r_c = crossover_distance_for(replace(V, a_max=10.0 * f_lin), k=100.0)
assert abs(r_c - 12.3971) < 1e-3, f"C2 FAILED: got {r_c}, section 16 published 12.3971"
print(f"control 2 OK -- temperature_response(293, {V.t_min}, {T25}) = {f_lin:.6f},")
print(
    f"              and a_max = 10.0 x that = {10.0 * f_lin:.4f} returns r* = {r_c:.4f} AU,"
)
print(
    "              reproducing section 16's 'reading B' figure EXACTLY. The arm is the"
)
print(
    f"              {T25 - 273.15:.2f} C anchor -- Q2's -- not Q2b's adapted optimum.\n"
)

# --- CONTROL 3 (positive): the Gaussian must be exactly 1.0 at its own optimum, else
# "a_max is the PEAK rate at t_opt" does not mean what reading B says it means.
assert abs(temperature_response_gaussian(300.0, 300.0, 20.0) - 1.0) < 1e-12, (
    "C3 FAILED: the Gaussian is not 1.0 at its own optimum"
)

# --- CONTROL 4: the two candidate factors for Q1 must actually DIFFER. If they agreed there
# would be no finding here at all, and this tool should say so rather than dress up a null.
f_gauss_v = temperature_response_gaussian(T_REF_K, TOPT["vascular"], V.omega)
spread = f_lin / f_gauss_v
assert spread > 5.0, f"C4 FAILED: the two readings agree to {spread:.3f}x -- no finding"
print("control 3+4 OK -- Gaussian is 1.0 at t_opt, and the two candidate Q1 factors")
print(
    f"                 differ by {spread:.1f}x ({f_lin:.4f} vs {f_gauss_v:.4f}), so the label matters\n"
)

print("=== The three anchors, and what each implies for Q1's a_max ===")
print(f"{'reading':>52} {'anchor T':>10} {'f(293K)':>9} {'Q1 a_max':>9}")
for lab, t, f in (
    ("A: the rate at 293 K (Q1's own t_set)", T_REF_K, 1.0),
    ("C: the rate at t_opt = 298.15 K = 25 C (Q2, linear)", T25, f_lin),
    (
        "B: the PEAK rate at the adapted t_opt (Q2b, Gaussian)",
        TOPT["vascular"],
        f_gauss_v,
    ),
):
    print(f"{lab:>52} {t - 273.15:9.2f}C {f:9.4f} {10.0 * f:9.4f}")

print(
    "\n=== TRUE reading B applied to Q1: it does not flip a verdict, it removes one ==="
)
print(
    "a_max = 10.0 is the PEAK, so the rate Q1 needs -- at its own 293 K -- is 10.0 * f(293)."
)
print(
    f"{'preset':>9} {'W':>4} {'f(293K)':>9} {'eff a_max':>10} {'resp':>7} {'I_c':>22} {'r*':>14}"
)
for name, org, kk in (("vascular", V, 100.0), ("algal", A, 20.0)):
    for w in OMEGA:
        f = temperature_response_gaussian(T_REF_K, TOPT[name], w)
        o2 = replace(org, a_max=10.0 * f)
        try:
            ic = f"{compensation_irradiance(o2):.4f}"
        except ValueError:
            ic = "NO COMPENSATION POINT"
        try:
            rs = f"{crossover_distance_for(o2, k=kk):.4f} AU"
        except Exception as e:
            rs = type(e).__name__
        print(
            f"{name:>9} {w:4.0f} {f:9.4f} {10.0 * f:10.4f} "
            f"{org.r_d / org.leaf_mass_ratio:7.4f} {ic:>22} {rs:>14}"
        )

# --- CONTROL 5 (positive control on the FAILURE): the no-compensation-point outcome must be
# both REACHABLE and AVOIDABLE. A predicate that can only ever return "broken" is not a check.
try:
    compensation_irradiance(
        replace(
            V,
            a_max=10.0 * temperature_response_gaussian(T_REF_K, TOPT["vascular"], 20.0),
        )
    )
    raise SystemExit(
        "C5 FAILED: vascular at omega=20 should have NO compensation point"
    )
except ValueError:
    pass
compensation_irradiance(replace(V, a_max=10.0))  # must NOT raise
print("\ncontrol 5 OK -- the no-compensation-point failure FIRES for true reading B")
print("              (vascular, omega=20) and does NOT fire for the registered a_max.")

print("\n=== Q2b's a_max correction across the REGISTERED omega sweep ===")
print(
    "Section 16 quoted one number per reading. Omega is swept 10-30, and the correction"
)
print("is a function of it, so one number understates the commitment:\n")
print(
    f"{'reading':>10} {'preset':>9} "
    + " ".join(f"{'W=' + str(int(w)):>12}" for w in OMEGA)
    + f"{'spread':>11}"
)
for lab, tref in (("A (293 K)", T_REF_K), ("C (25 C)", T25)):
    for name in ("algal", "vascular"):
        vals = [
            10.0 / temperature_response_gaussian(tref, TOPT[name], w) for w in OMEGA
        ]
        print(
            f"{lab:>10} {name:>9} "
            + " ".join(f"{v:12.4f}" for v in vals)
            + f"{max(vals) / min(vals):10.1f}x"
        )

# --- CONTROL 6: reproduce section 16's ONE published reading-A figure, a_max = 17.1498.
f_a20 = temperature_response_gaussian(T_REF_K, TOPT["algal"], 20.0)
assert abs(10.0 / f_a20 - 17.1498) < 1e-3, f"C6 FAILED: {10.0 / f_a20}"
print(
    f"\ncontrol 6 OK -- reading A, Q2b algal, omega=20 -> a_max = {10.0 / f_a20:.4f},"
)
print(
    "              matching section 16's published 17.1498. The table above is the same"
)
print("              calculation across the rest of the grid section 16 did not show.")

print("\n=== The asymmetry that decides S6 ===")
print(
    "omega is registered ONLY in experiments/q2b_adapted/prereg.yaml:67 (omega_grid_k)."
)
print("It appears nowhere in q1_crossover/prereg.yaml or q2_thermal/prereg.yaml, and")
print("net_carbon() -- Q1's path -- reads neither omega, area_ratio nor t_opt.")
print(
    "  Readings A and C put the omega-dependent correction on Q2b, which REGISTERED omega."
)
print("  Reading B puts it on Q1, which did not: Q1's headline would then range from")
print("  'no compensation point exists' to r* = 3.92 AU across an unregistered knob.")
