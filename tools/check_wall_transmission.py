# Companion to check_sigma_k_consistency.py. Section 9's per-thickness transmission figures
# take their WALL THICKNESS from wood (0.625 m at 80 MPa) and their k from ice -- the same
# material mismatch as R_max, in a sentence section 10's first draft had declared unaffected.
# The positive control reproduces the committed 0.6250 m sizing before anything changes.
import signal, sys, math
signal.signal(signal.SIGALRM, lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)))
signal.alarm(60)

def t_wall(p, R, s): return p*R/(2.0*s)
# positive control: reproduce the committed wood-derived sizing
assert abs(t_wall(10e3, 10e3, 80e6) - 0.6250) < 1e-9, "closed form disagrees with the committed 0.6250 m"
print("positive control OK: wood 80 MPa -> 0.6250 m (the committed sizing)\n")

KS = [("400 nm blue", 0.00074), ("550 nm", 0.05230), ("680 nm chl-a red", 0.38623), ("700 nm red", 0.52061)]
print("Section 9 line 488 states, at 'the committed 0.625 m thickness':")
print("  400 nm = 0.9995, 700 nm = 0.7223  -> that thickness is WOOD's (80 MPa).\n")
print(f"{'sigma':28s} {'t (m)':>9s} " + " ".join(f"{l:>14s}" for l,_ in KS))
for lab, s in [("wood 80 MPa (what sec9 used)", 80e6), ("ice 3.1 MPa", 3.1e6), ("ice 1.5 MPa", 1.5e6), ("ice 0.7 MPa", 0.7e6)]:
    t = t_wall(10e3, 10e3, s)
    print(f"{lab:28s} {t:9.3f} " + " ".join(f"{math.exp(-k*t):14.4g}" for _,k in KS))
t = t_wall(10e3, 10e3, 1.5e6)
print(f"\nblue/red contrast at ice-mid t={t:.1f} m: {math.exp(-0.00074*t)/math.exp(-0.52061*t):.3g}x  (sec9 quoted 25.8x at R=100 km)")
print("=> the x701 spread in k is unchanged (no sigma enters it), but every PER-THICKNESS")
print("   transmission number in sec 9 is a wood-thickness number.")
