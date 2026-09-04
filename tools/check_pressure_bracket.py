# Section 11 S1: the Q3 spec registers p in [882 Pa, 10 kPa], but that floor is the saturation
# pressure at the UNCONTAINED equilibrium temperature -- and the same spec settles that
# containment is mandatory and RAISES the temperature. This recomputes the pressure the wall
# must actually hold. Positive controls reproduce the roadmap's own published 5.16 C/882 Pa and
# 57.82 C/18 kPa from the live sim.thermal code before anything moves, so a wrong answer here
# cannot be mistaken for a differently-wrong one.
import signal, sys, math
signal.signal(signal.SIGALRM, lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)))
signal.alarm(60)
sys.path.insert(0, "/home/mjarnold/dyson-tree")
from sim.thermal import equilibrium_temperature

def buck_pa(t_c):                      # saturation vapour pressure over water
    return 6.1121*math.exp((18.678 - t_c/234.5)*(t_c/(257.14+t_c)))*100.0

# --- positive controls: reproduce the roadmap's OWN published numbers ---
t_un = equilibrium_temperature(1.0, area_ratio=4.0) - 273.15          # algal sphere, UNCONTAINED
assert abs(t_un - 5.16) < 0.02, f"uncontained T control failed: {t_un:.3f} vs published 5.16 C"
p_un = buck_pa(t_un)
assert abs(p_un - 882) < 3, f"882 Pa control failed: {p_un:.1f}"
t_c1 = (equilibrium_temperature(1.0, area_ratio=4.0) * (1+1)**0.25) - 273.15   # + one IR-opaque shell
assert abs(t_c1 - 57.82) < 0.05, f"contained T control failed: {t_c1:.3f} vs published 57.82 C"
p_c1 = buck_pa(t_c1)
assert abs(p_c1/1000 - 18.0) < 0.2, f"18 kPa control failed: {p_c1/1000:.2f}"
print(f"controls OK -- uncontained {t_un:.2f} C -> {p_un:.0f} Pa (published 882);")
print(f"             contained N=1 {t_c1:.2f} C -> {p_c1/1000:.1f} kPa (published 18)\n")

print("The registered bracket is p in [882 Pa, 10 kPa]. Its FLOOR is the saturation")
print("pressure at the UNCONTAINED temperature -- but Q3 established containment is")
print("MANDATORY, and containment RAISES the temperature.\n")
print(f"{'N shells':>8} {'T_int (C)':>10} {'p_sat req (kPa)':>16} {'in bracket?':>13}")
for N in range(0, 4):
    t = equilibrium_temperature(1.0, area_ratio=4.0)*(N+1)**0.25 - 273.15
    p = buck_pa(t)
    print(f"{N:8d} {t:10.2f} {p/1000:16.3f} {('YES' if 882 <= p <= 10e3 else 'NO -- ABOVE TOP'):>13}")

print("\nR_max (km) in the red band at the SELF-CONSISTENT pressure, tau_min=0.01:")
def r_max_km(s, p, k): return 2.0*s*abs(math.log(0.01))/(k*p)/1000.0
for lab, p in [("882 Pa (bracket floor, UNCONTAINED T)", p_un), ("10 kPa (bracket top)", 10e3),
               ("18.0 kPa (SELF-CONSISTENT, N=1)", p_c1)]:
    lo, hi = r_max_km(0.7e6, p, 0.38623), r_max_km(3.1e6, p, 0.38623)
    print(f"  {lab:40s} {lo:8.2f} - {hi:7.2f} km   {'BINDS at 10 km' if hi < 10 else 'does not bind'}")
