# Section 19: reading A REGISTERED -- what it obligates downstream, measured.
#
# S6 is decided: a_max = 10.0 is the assimilation rate at 293 K (Q1's own t_set).
# Section 18 established the choice and eliminated readings B and C; it did NOT
# measure what adopting A does to Q2b's OWN registered output. Section 16 priced
# only Q2b's "light" candidate limit (75.434 -> 99.291 AU, +31.6%) and never asked
# whether the BINDING limit moves, which is the only a_max-sensitive thing Q2b
# registered a prediction about.
#
# Under reading A, Q2b's Gaussian is 1.0 at the ADAPTED optimum, so it consumes
# a_max as the PEAK rate. Reading A says 10.0 is the 293 K rate, so Q2b's peak must
# be scaled UP: a_max_A = 10.0 / f_gauss(293, t_opt_adapted, omega).
#
# This does NOT modify any registered file. It calls the REAL runner's own build()
# and classify_limit() -- section 17's rule: an uncontrolled reimplementation that
# contradicts a controlled published number is evidence about the reimplementation.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(180)
sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from copy import deepcopy
from pathlib import Path

from experiments.q2b_adapted.run import build, classify_limit, load_prereg, run_gate_b
from sim.physiology import T_REF_K
from sim.thermal import adapted_optimum, temperature_response_gaussian

PREREG = Path(__file__).resolve().parents[1] / "experiments/q2b_adapted/prereg.yaml"
pre = load_prereg(PREREG)
a = pre["assumptions"]
sw = pre["sweep"]
R_MIN, R_MAX, N_GRID = float(sw["r_min_au"]), float(sw["r_max_au"]), int(sw["n_grid"])
R_HOME = float(a["r_home_au"])
OMEGA = [float(x) for x in pre["omega_grid_k"]]

# The five rows committed in experiments/q2b_adapted/limits.csv.
SHIPPED = {
    # S5 (2026-09-06) moved these by -0.008% to -0.047%; binding unchanged.
    # Were 1.2120 / 1.3795 / 1.6180 / 1.9723 / 2.5301 at PAR_FRACTION 0.45.
    10.0: (1.2119, "temperature"),
    15.0: (1.3794, "temperature"),
    20.0: (1.6178, "temperature"),
    25.0: (1.9718, "temperature"),
    30.0: (2.5289, "temperature"),
}


def algal_at(a_max: float, omega: float):
    p = deepcopy(pre["presets"]["algal"])
    p["a_max"] = a_max
    org = build("algal", p, a, omega)
    return classify_limit(org, R_HOME, R_MIN, R_MAX, N_GRID)


# --- CONTROL 1 (positive): reproduce the SHIPPED limits.csv from the registered
# a_max. A harness that cannot reproduce the committed baseline cannot be trusted
# to report a departure from it.
for w in OMEGA:
    res = algal_at(10.0, w)
    want_au, want_bind = SHIPPED[w]
    assert abs(res["carbon"] - want_au) < 1e-3, (
        f"C1 FAILED omega={w}: carbon {res['carbon']:.4f}, limits.csv says {want_au}"
    )
    assert res["binding"] == want_bind, (
        f"C1 FAILED omega={w}: binding {res['binding']}, limits.csv says {want_bind}"
    )
print("control 1 OK -- reproduces all 5 committed limits.csv rows from a_max = 10.0")

# --- CONTROL 2 (positive): the reading-A factor reproduces section 18's published
# 17.1498 for algal at omega = 20, so the correction applied below is the one
# section 18 priced and not a fresh invention.
T_OPT = adapted_optimum(
    R_HOME, float(pre["presets"]["algal"]["area_ratio"]),
    float(a["emissivity"]), float(a["albedo"]),
)
f20 = temperature_response_gaussian(T_REF_K, T_OPT, 20.0)
assert abs(10.0 / f20 - 17.1498) < 1e-3, f"C2 FAILED: {10.0 / f20}"
print(f"control 2 OK -- reading-A a_max at omega=20 = {10.0 / f20:.4f} (section 18: 17.1498)")

# --- CONTROL 3: gate B must still EXCLUDE vascular, otherwise reading A's
# 1.82e7 vascular correction would enter Q2b's output and this whole measurement
# would be understating the commitment.
_, passing = run_gate_b(pre)
assert "vascular" not in passing, "C3 FAILED: vascular passed gate B; the 1.82e7 arm is live"
assert "algal" in passing, "C3 FAILED: algal did not pass gate B"
print("control 3 OK -- gate B still excludes vascular, so only algal's factor is live")

# --- CONTROL 4 (positive control on the VERDICT): `binding` must be CAPABLE of
# being something other than "temperature". A predicate that returns one constant
# cannot report that reading A left it alone. Lowering a_max pulls the carbon
# crossover INWARD past the fixed 1.1945 AU thermal floor; it must flip there.
flip = algal_at(3.0, 10.0)
assert flip["binding"] == "carbon", (
    f"C4 FAILED: binding did not flip at a_max=3.0; got {flip['binding']}"
)
print(f"control 4 OK -- binding CAN differ: a_max=3.0, omega=10 -> "
      f"{flip['binding']} (carbon {flip['carbon']:.4f} < temperature {flip['temperature']:.4f})")

print("\n=== Q2b algal under READING A (registered 2026-09-06) ===")
print("temperature is the a_max-INDEPENDENT floor; light and carbon both move outward with a_max.\n")
print(f"{'W':>4} {'a_max_A':>9} {'temperature':>12} {'light':>10} {'carbon':>9} "
      f"{'binding':>12} {'carbon was':>11} {'move':>8}")
rows = []
for w in OMEGA:
    f = temperature_response_gaussian(T_REF_K, T_OPT, w)
    am = 10.0 / f
    res = algal_at(am, w)
    was = SHIPPED[w][0]
    rows.append((w, am, res, was))
    print(f"{w:4.0f} {am:9.4f} {res['temperature']:12.4f} {res['light']:10.3f} "
          f"{res['carbon']:9.4f} {res['binding']:>12} {was:11.4f} "
          f"{100 * (res['carbon'] - was) / was:+7.2f}%")

bindings = {r[2]["binding"] for r in rows}
print(f"\nbinding under reading A, all omega: {bindings}")
print(f"binding as shipped,      all omega: {set(v[1] for v in SHIPPED.values())}")
print("\nThe registered prediction predicted_binding_limit.algal = 'carbon' was already")
print("FALSIFIED by the shipped run (binding = temperature at every omega). Reading A")
print("moves the carbon crossover FURTHER OUT, i.e. further from the thermal floor --")
print("so it cannot rescue that prediction; it widens the margin by which it failed.")
