# Extracts PAR absorption coefficients from Warren & Brandt 2008's public data table.
# Fetch first:  curl -sL https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat -o iop2008.dat
# Grounds bio_grounding_2026-09-02.md section 9. Asserts the parse count -- a partial
# parse reporting a confident result is the failure mode this file exists to prevent.
import signal, sys, math
signal.signal(signal.SIGALRM, lambda *_: (sys.stderr.write("aborting: walltime guard\n"), sys.exit(2)))
signal.alarm(60)

rows=[]
for line in open('iop2008.dat'):
    p=line.split()
    if len(p)!=3: continue
    try: rows.append((float(p[0]),float(p[1]),float(p[2])))
    except ValueError: pass
print(f"parsed {len(rows)} rows of 487 lines")
assert len(rows) > 400, "PARSER FAILED -- refusing to report on a partial table"

def k_abs(lam_um, m_im):           # absorption coefficient, 1/m
    return 4.0*math.pi*m_im/(lam_um*1e-6)

par=[(l,n,m) for (l,n,m) in rows if 0.40<=l<=0.70]
print(f"PAR rows (0.40-0.70 um): {len(par)}")
assert par, "no PAR rows -- refusing to report"

print("\n=== grounded k over PAR (Warren & Brandt 2008, IOP_2008_ASCIItable.dat) ===")
print(f"{'lambda_nm':>10} {'m_im':>12} {'k_abs 1/m':>12} {'abs.len m':>11}")
for l,n,m in par:
    k=k_abs(l,m)
    print(f"{l*1000:10.1f} {m:12.3e} {k:12.5f} {1.0/k:11.2f}")

ks=[k_abs(l,m) for l,n,m in par]
kmin,kmax=min(ks),max(ks)
print(f"\nPAR range: k_abs {kmin:.5f} - {kmax:.5f} /m   (spread x{kmax/kmin:.0f})")
print(f"absorption length {1/kmax:.2f} m (red end) to {1/kmin:.1f} m (blue end)")

# R_max = 2*sigma*|ln tau_min| / (k*p)
def r_max(sig,p,k,tau): return 2*sig*abs(math.log(tau))/(k*p)
print("\n=== R_max with GROUNDED k (sigma=80 MPa median, tau_min=0.01) ===")
for pname,p in [("saturation 882 Pa",882.0),("Paul 2004 10 kPa",10e3)]:
    for kn,k in [("blue end",kmin),("red end",kmax)]:
        R=r_max(80e6,p,k,0.01)/1000
        print(f"  p={pname:20s} {kn:9s} k={k:8.5f} /m -> R_max = {R:12.1f} km")

print("\n=== spectral filtering: transmission through the 0.625 m committed wall ===")
for l,n,m in par:
    k=k_abs(l,m)
    print(f"  {l*1000:6.1f} nm  tau = {math.exp(-k*0.625):.4f}")
