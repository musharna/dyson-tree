# Recomputes bio_grounding section 9's R_max with an internally consistent wall material.
# Section 9 divided section 7's WOOD tensile strength (80 MPa) by section 9's ICE absorption
# coefficient; no material in this project's grounding has both properties. The positive
# control here reproduces section 9's own published numbers first, so that the only thing
# changing between its table and section 10's is sigma -- without that control, a corrected
# table would be indistinguishable from a differently-wrong one.
import signal, sys, math
signal.signal(signal.SIGALRM, lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)))
signal.alarm(60)

def r_max_km(sigma_pa, p_pa, k_per_m, tau_min=0.01):
    return 2.0*sigma_pa*abs(math.log(tau_min))/(k_per_m*p_pa) / 1000.0

# positive control: reproduce a number section 9 actually published
ctrl = r_max_km(80e6, 10e3, 0.52061)
assert abs(ctrl - 141.0) < 1.0, f"closed form disagrees with section 9's published 141 km: got {ctrl:.1f}"
ctrl2 = r_max_km(80e6, 882.0, 0.00074)
assert abs(ctrl2 - 1.12e6)/1.12e6 < 0.02, f"blue/882Pa control failed: got {ctrl2:.3e}"
print(f"positive control OK: 10 kPa red = {ctrl:.1f} km (published 141), 882 Pa blue = {ctrl2:.3e} km (published 1.12e6)\n")

KS = [("400 nm blue", 0.00074), ("550 nm", 0.05230), ("680 nm chl-a red", 0.38623), ("700 nm red", 0.52061)]
SIGMAS = [("wood MOR median (what sec9 used)", 80e6),
          ("ice, high end", 3.1e6),
          ("ice, mid", 1.5e6),
          ("ice, low end", 0.7e6)]
ASSUMED_R_KM = 10.0

for p_label, p in [("882 Pa (saturation)", 882.0), ("10 kPa (Paul 2004)", 10e3)]:
    print(f"=== p = {p_label} ===")
    print(f"{'sigma':38s} " + " ".join(f"{lab:>18s}" for lab,_ in KS))
    for slab, s in SIGMAS:
        row = " ".join(f"{r_max_km(s,p,k):18.4g}" for _,k in KS)
        print(f"{slab:38s} {row}")
    print(f"{'--- binds at R = 10 km?':38s} " + " ".join(
        f"{('YES' if r_max_km(1.5e6,p,k) < ASSUMED_R_KM else 'no'):>18s}" for _,k in KS) + "   (at ice mid 1.5 MPa)")
    print()
