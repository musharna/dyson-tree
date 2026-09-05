# Section 13 S6: section 4 grounds a_max from Westerband 2022's Asat column, handling the
# net-vs-gross unit question carefully -- and never asking WHAT TEMPERATURE that rate describes.
#
# The deposit does not say. It has no leaf-temperature column at all, while carrying
# "Vcmax25_micromol.m2.s" -- explicitly standardised to 25 C -- in the same 35-column file.
# The authors standardised where they meant to; Asat is an as-measured field quantity whose
# leaf temperature was not deposited.
#
# So the anchor is unknowable from the source, and the three shipped questions each supply a
# DIFFERENT one implicitly:
#   Q1  net_carbon()               gross_assimilation(...) with NO temperature factor, tissue
#                                  held at t_set = T_REF_K = 293.0 K -> a_max is the rate at 20 C
#   Q2  net_carbon_at_equilibrium() gross * temperature_response(...) which is 1.0 AT AND ABOVE
#                                  t_opt -> a_max is the rate at t_opt or hotter
#   Q2b net_carbon_adapted()       gross * temperature_response_gaussian(...) which is exactly
#                                  1.0 AT t_opt -> a_max is the PEAK rate, at t_opt
# The same preset value a_max = 10.0 cannot be all three unless t_opt = 293 K. It is not:
# Q2b DERIVES t_opt from geometry via adapted_optimum().
#
# This measures the disagreement using the project's OWN Gaussian -- no new object is
# imported to size it, which is the whole point of section 12's rule.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(60)
sys.path.insert(0, "/home/mjarnold/dyson-tree")
from sim.physiology import T_REF_K
from sim.thermal import adapted_optimum, temperature_response_gaussian

# registered in experiments/q2b_adapted/prereg.yaml
OMEGA_GRID = [10.0, 15.0, 20.0, 25.0, 30.0]
PRESETS = {"algal": 4.0, "vascular": 2.0}  # name -> area_ratio
R_HOME_AU = 1.0

# --- CONTROL: adapted_optimum must reproduce the roadmap's own published temperatures
t_alg = adapted_optimum(R_HOME_AU, PRESETS["algal"]) - 273.15
t_vas = adapted_optimum(R_HOME_AU, PRESETS["vascular"]) - 273.15
assert abs(t_alg - 5.16) < 0.02, (
    f"CONTROL FAILED: algal t_opt {t_alg:.3f} C, published 5.16"
)
assert abs(t_vas - 57.82) < 0.05, (
    f"CONTROL FAILED: vascular t_opt {t_vas:.3f} C, published 57.82"
)
assert abs(temperature_response_gaussian(300.0, 300.0, 20.0) - 1.0) < 1e-12, (
    "CONTROL FAILED: the Gaussian is not 1.0 at its own optimum"
)
print(
    "control OK -- adapted_optimum reproduces 5.16 C (algal) and 57.82 C (vascular),"
)
print(
    "              and the Gaussian is exactly 1.0 at t_opt, so a_max IS the peak rate\n"
)

print(
    "Q1 uses a_max UNSCALED with tissue at t_set = "
    f"{T_REF_K:.1f} K ({T_REF_K - 273.15:.1f} C)."
)
print("Q2b uses a_max as the PEAK rate at a t_opt it derives from geometry.")
print(
    "Under Q2b's own Gaussian, the rate at Q1's 293.0 K is this fraction of the peak:\n"
)
print(
    f"{'preset':>10} {'t_opt':>9} {'dT from 293 K':>15} "
    + "".join(f"{'W=' + str(int(w)):>10}" for w in OMEGA_GRID)
)
for name, ar in PRESETS.items():
    t_opt = adapted_optimum(R_HOME_AU, ar)
    cells = "".join(
        f"{temperature_response_gaussian(T_REF_K, t_opt, w):10.4f}" for w in OMEGA_GRID
    )
    print(f"{name:>10} {t_opt - 273.15:8.2f}C {T_REF_K - t_opt:14.2f}K {cells}")

print("\nSo the SAME registered a_max = 10.0 is read two ways that differ by:")
for name, ar in PRESETS.items():
    t_opt = adapted_optimum(R_HOME_AU, ar)
    fs = [temperature_response_gaussian(T_REF_K, t_opt, w) for w in OMEGA_GRID]
    print(
        f"  {name:>9}: {1 / max(fs):.2f}x to {1 / min(fs):.4g}x across the registered omega grid"
    )

print("\nNeither reading is checkable against the source: the deposit records no leaf")
print(
    "temperature for Asat. The disagreement is INTERNAL and provable from the code alone."
)
