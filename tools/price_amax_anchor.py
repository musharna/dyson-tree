# Section 16, pricing S6. The SAME registered a_max = 10.0 is multiplied, in the three
# consumption paths of sim/organism.py, by a factor that reaches 1.0 at a DIFFERENT
# temperature in each. This measures those anchor temperatures from the live code and
# prices what re-anchoring all three to one common temperature would cost.
#
# Controls reproduce the project's own published numbers before anything is re-anchored,
# so a wrong answer here cannot be mistaken for a differently-wrong one.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(60)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from sim.organism import PRESETS  # noqa: E402
from sim.physiology import T_REF_K  # noqa: E402
from sim.thermal import (  # noqa: E402
    adapted_optimum,
    temperature_response,
    temperature_response_gaussian,
)

ALG, VAS = PRESETS["algal"], PRESETS["vascular"]

# --- CONTROL 1: the anchors must reproduce the project's own published t_opt values.
t_opt_alg = adapted_optimum(1.0, ALG.area_ratio, ALG.emissivity, ALG.albedo)
t_opt_vas = adapted_optimum(1.0, VAS.area_ratio, VAS.emissivity, VAS.albedo)
assert abs(t_opt_alg - 273.15 - 5.1612) < 0.01, f"C1 FAILED algal {t_opt_alg - 273.15}"
assert abs(t_opt_vas - 273.15 - 57.8196) < 0.01, f"C1 FAILED vasc {t_opt_vas - 273.15}"
# --- CONTROL 2: each response function must actually equal 1.0 at its stated anchor.
assert abs(temperature_response(298.15, 265.15, 298.15) - 1.0) < 1e-12
assert abs(temperature_response_gaussian(t_opt_alg, t_opt_alg, 20.0) - 1.0) < 1e-12
print(f"control 1 OK -- adapted optima reproduce published 5.1612 / 57.8196 C")
print(f"control 2 OK -- both response functions equal 1.0 at their own anchor\n")

print("=== the temperature at which a_max is the TRUE rate, per path ===")
print(f"{'path':>28} {'experiment':>11} {'anchor T (K)':>13} {'anchor T (C)':>13}")
rows = [
    ("net_carbon", "Q1", T_REF_K),  # no f at all; only declared T is t_set = T_REF_K
    ("net_carbon_at_equilibrium", "Q2", 298.15),  # linear ramp reaches 1 at t_opt
    ("net_carbon_adapted [algal]", "Q2b", t_opt_alg),  # gaussian peaks at adapted t_opt
    ("net_carbon_adapted [vasc]", "Q2b", t_opt_vas),
]
for name, exp, t in rows:
    print(f"{name:>28} {exp:>11} {t:13.2f} {t - 273.15:13.2f}")
spread = max(r[2] for r in rows) - min(r[2] for r in rows)
print(f"\nspread between the extreme anchors: {spread:.2f} K")
assert spread > 50.0, f"CONTROL 3 FAILED: spread {spread:.2f} K is not the 52.7 K claimed"
print("control 3 OK -- the spread is real and larger than 50 K\n")

# --- what re-anchoring costs: make every path mean "the rate at 293 K (T_REF_K)".
# Under each path's OWN response function, the rate actually delivered at 293 K is
# a_max * f(293). To make that equal a_max, a_max must be divided by f(293).
print("=== re-anchoring every path to a common 293 K: the a_max each would need ===")
print(f"{'path':>28} {'f(293 K)':>10} {'a_max needed':>13} {'vs 10.0':>9}")
f_q1 = 1.0  # no temperature factor at all
f_q2 = temperature_response(T_REF_K, VAS.t_min, VAS.t_opt)
f_q2b_a = temperature_response_gaussian(T_REF_K, t_opt_alg, ALG.omega)
f_q2b_v = temperature_response_gaussian(T_REF_K, t_opt_vas, VAS.omega)
for name, f in [
    ("net_carbon (Q1)", f_q1),
    ("net_carbon_at_equilibrium (Q2)", f_q2),
    ("net_carbon_adapted [algal]", f_q2b_a),
    ("net_carbon_adapted [vasc]", f_q2b_v),
]:
    need = 10.0 / f
    print(f"{name:>28} {f:10.4f} {need:13.4f} {need / 10.0:8.2f}x")
print("\nThe registered 10.0 is therefore not one quantity. Read as 'the rate at 293 K',")
print("the three paths need a_max spanning 10.0 to " f"{10.0 / min(f_q2, f_q2b_a, f_q2b_v):.2f}" " -- a factor of "
      f"{(1.0 / min(f_q2, f_q2b_a, f_q2b_v)):.2f} between the extremes.")
