# Section 14: the roadmap states as settled that "adding one IR-opaque shell and halving
# area_ratio are the SAME operation (identical to 5.7e-14 K)", and concludes that every
# registered area_ratio = 4.0 "silently asserted UNCONTAINED".
#
# That identity holds only because both operations multiply T by 2^0.25. Section 13 S7 showed
# a real ice shell multiplies by (1+tau)^0.25, tau ~ 0.26-0.34. So the claim needs re-checking
# at the tau it was never tested at -- the symmetric case S7's own data already settles.
#
# Solves the N-shell radiative system for arbitrary tau rather than assuming transparency:
#   shell 1:      (1-tau)*A            + S_2           = 2*S_1
#   shell i:      (1-tau)*tau^(i-1)*A  + S_{i-1} + S_{i+1} = 2*S_i
#   shell N:      (1-tau)*tau^(N-1)*A  + S_{N-1} + S_core  = 2*S_N
#   core:          tau^N * A           + S_N              = S_core
# where S = sigma*T^4. Positive control: at tau = 1 this must return (N+1)*A for the core,
# i.e. the project's own (N+1)^0.25 law, for every N.
import signal
import sys

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)),
)
signal.alarm(60)
import numpy as np

sys.path.insert(0, str(__import__("pathlib").Path(__file__).resolve().parents[1]))
from sim.thermal import equilibrium_temperature


def core_factor(n_shells: int, tau: float) -> float:
    """S_core / A for n_shells IR-opaque shells each of SW transmittance tau."""
    if n_shells == 0:
        return 1.0
    n = n_shells
    m = np.zeros((n + 1, n + 1))
    b = np.zeros(n + 1)
    for i in range(1, n + 1):  # rows 0..n-1 are shells 1..n
        r = i - 1
        m[r, r] = -2.0
        if i > 1:
            m[r, r - 1] = 1.0
        if i < n:
            m[r, r + 1] = 1.0
        else:
            m[r, n] = 1.0  # innermost shell sees the core
        b[r] = -(1.0 - tau) * tau ** (i - 1)
    m[n, n] = -1.0
    m[n, n - 1] = 1.0
    b[n] = -(tau**n)
    return float(np.linalg.solve(m, b)[n])


# --- CONTROL 1: at tau = 1 the solver must reproduce the project's own (N+1) law exactly
for n in range(0, 6):
    got = core_factor(n, 1.0)
    assert abs(got - (n + 1)) < 1e-10, (
        f"CONTROL 1 FAILED: N={n} tau=1 gives {got}, want {n + 1}"
    )
# --- CONTROL 2: at tau = 1, one shell must equal halving area_ratio, to the roadmap's own 5.7e-14 K
t_shell = equilibrium_temperature(1.0, 4.0) * core_factor(1, 1.0) ** 0.25
t_half = equilibrium_temperature(1.0, 2.0)
assert abs(t_shell - t_half) < 1e-12, f"CONTROL 2 FAILED: {t_shell} vs {t_half}"
print("control 1 OK -- tau=1 reproduces (N+1) for N=0..5")
print(
    f"control 2 OK -- at tau=1, one shell == halving area_ratio to {abs(t_shell - t_half):.1e} K"
)
print("              (the roadmap's published residue is 5.7e-14 K -- same identity)\n")

T4 = equilibrium_temperature(1.0, 4.0)
TAUS = [
    ("sigma 3.1 MPa wall", 0.3429),
    ("sigma 1.5 MPa wall", 0.3013),
    ("sigma 0.7 MPa wall", 0.2609),
]

print("=== is one real shell still the same operation as halving area_ratio? ===")
print(f"algal sphere, area_ratio 4.0, T_eq = {T4 - 273.15:.2f} C")
print(f"halving area_ratio to 2.0        -> {t_half - 273.15:.2f} C\n")
print(f"{'wall':>20} {'tau':>7} {'T with 1 shell':>16} {'gap vs halving':>16}")
for lab, ta in TAUS:
    t = T4 * core_factor(1, ta) ** 0.25
    print(f"{lab:>20} {ta:7.4f} {t - 273.15:13.2f} C {t - t_half:13.2f} K")

print("\n=== but the degeneracy does not vanish -- it RESCALES ===")
print(
    "T = (S*(1+tau) / (area_ratio*sigma))^0.25, so area_ratio and (1+tau) enter ONLY as a"
)
print(
    "ratio. The degenerate quantity is area_ratio/(1+tau) -- an EFFECTIVE area_ratio:\n"
)
print(
    f"{'wall':>20} {'tau':>7} {'effective area_ratio':>21} {'vs Q2b band [3.630, 4.311]':>28}"
)
for lab, ta in TAUS:
    eff = 4.0 / (1.0 + ta)
    where = (
        "INSIDE"
        if 3.630 <= eff <= 4.311
        else ("BELOW the floor" if eff < 3.630 else "ABOVE")
    )
    print(f"{lab:>20} {ta:7.4f} {eff:21.4f} {where:>28}")
print(
    f"{'tau = 1 (the claim)':>20} {1.0:7.4f} {4.0 / 2.0:21.4f} {'BELOW the floor':>28}"
)

print("\n=== N shells, real tau, against the (N+1)^0.25 law the roadmap uses ===")
print(f"{'N':>3} {'(N+1)^0.25 law':>16} {'tau=0.2609':>12} {'tau=0.3429':>12}")
for n in range(0, 4):
    a = T4 * (n + 1) ** 0.25 - 273.15
    b_ = T4 * core_factor(n, 0.2609) ** 0.25 - 273.15
    c = T4 * core_factor(n, 0.3429) ** 0.25 - 273.15
    print(f"{n:3d} {a:13.2f} C {b_:9.2f} C {c:9.2f} C")

# --- the inverse question: what TRUE shape would a CONTAINED organism need in order to
# present inside Q2b's registered band? true = effective * (1 + tau).
print("\n=== inverse: true area_ratio a CONTAINED organism needs to land in Q2b's band ===")
lo_t = 3.630 * (1.0 + min(t for _, t in TAUS))
hi_t = 4.311 * (1.0 + max(t for _, t in TAUS))
print(f"  band [3.630, 4.311] requires TRUE area_ratio in [{lo_t:.3f}, {hi_t:.3f}]")
print(f"  a sphere is 4.0 and a face-on lamina is 2.0, so the whole band demands a body")
print(f"  MORE extreme than a sphere -- elongated or flattened, seen near edge-on.")
print(f"  A CONTAINED SPHERE presents at {4.0 / (1 + max(t for _, t in TAUS)):.3f}-"
      f"{4.0 / (1 + min(t for _, t in TAUS)):.3f}, entirely BELOW the band floor of 3.630.")

print("\n=== what the roadmap's N=2 figure inherits ===")
print("  The roadmap quotes 'two shells need 78.9 kPa' from T = 3^0.25*T_eq = 93.13 C.")
print(f"  At real tau that interior is {T4 * core_factor(2, 0.2609) ** 0.25 - 273.15:.2f}-"
      f"{T4 * core_factor(2, 0.3429) ** 0.25 - 273.15:.2f} C, not 93.13 C, so the 78.9 kPa")
print("  figure inherits the same falsified transparency premise as S1's 18.02 kPa did.")
