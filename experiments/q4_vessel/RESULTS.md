# Q4 results: the vessel, and watching it fail

Written by `experiments/q4_vessel/run.py`; do not edit by hand. Provenance:

```
git_sha=686e7edb0304d9887851dab15044df953cb45ee5
code_dirty=no
prereg_md5=d8707a6607db6d54a006e14af9dcfe79
spectral_table_sha256=2cfea122d9f6f8aae04b3cc53221d67f6d010f94ead1ff39a81a78f4398da0b8
vessel_md5=4eddbbbb4098a09fae1039ca82cbc052
physiology_md5=af16830e7f15c5cf9848c8eb694e99c8
thermal_md5=6b0ecfc0353686a3534939ac9eff9a0e
organism_md5=a5425fa33a97b64be9793a2788778abc
run_md5=04c7a9c54fa237830dd550a2f64e17a4
python=3.13.2
numpy=2.3.5
scipy=1.16.3
written=2026-09-24T01:16:59-04:00
runtime_s=36.2
```

## Verdicts

| prediction | band | measured edge | binding (registered) | verdict |
| --- | --- | --- | --- | --- |
| P1 r_close(10 km, σ) | [1.19, 1.27] AU | σ 0.7: 1.2049 / σ 1.5: 1.2303 / σ 3.1: 1.2543 AU | FREEZE/FREEZE/FREEZE (FREEZE) | **HELD** |
| P2 R_window(1.10 AU, 0.7 MPa) | [60, 300] km | 95.6 km | OPAQUE (OPAQUE) | **HELD** |

Q4_P1=HELD
Q4_P2=HELD

## Gates

| gate | quantity | value | target | passed |
| --- | --- | --- | --- | --- |
| A | T_eq(1 AU, sphere) K | 278.3112 | [275, 282] | True |
| C | p_sat(273.16 K) Pa | 611.6541 | 611.657 +- 0.01 | True |
| C | p_sat(5.16 C) Pa (regression) | 882.2221 | 882 +- 0.5 | True |

## Every edge row beside the prereg's expected value

`within_tol`: |delta| <= prereg edge tolerance (1e-4 AU; 1e-3 x expected in R). `printed`: measured rounded to the prereg's printed digits equals it. STARVE margin at the edge in µmol m⁻² s⁻¹ (monitored, never binding).

| row | config | σ MPa | quantity | measured | expected | delta | within_tol | printed | binding | expected binding | tie | STARVE margin |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| P1 | registered | 0.7 | r_close | 1.204929 AU | 1.2049 | +0.000029 | True | True | FREEZE | FREEZE | False | 1.9816 |
| P1 | registered | 1.5 | r_close | 1.230323 AU | 1.2303 | +0.000023 | True | True | FREEZE | FREEZE | False | 1.9870 |
| P1 | registered | 3.1 | r_close | 1.254335 AU | 1.2543 | +0.000035 | True | True | FREEZE | FREEZE | False | 1.9895 |
| P1.control | control normal | 0.7 | r_close | 1.211114 AU | 1.2111 | +0.000014 | True | True | FREEZE | FREEZE | False | 1.9833 |
| P1.control | control normal | 1.5 | r_close | 1.236544 AU | 1.2365 | +0.000044 | True | True | FREEZE | FREEZE | False | 1.9879 |
| P1.control | control normal | 3.1 | r_close | 1.260455 AU | 1.2605 | -0.000045 | True | True | FREEZE | FREEZE | False | 1.9899 |
| P1.arm0 | arm (i) n_int 1.000 | 0.7 | r_close | 1.188569 AU | 1.1886 | -0.000031 | True | True | FREEZE | FREEZE | False | 1.9784 |
| P1.arm0 | arm (i) n_int 1.000 | 1.5 | r_close | 1.211598 AU | 1.2116 | -0.000002 | True | True | FREEZE | FREEZE | False | 1.9843 |
| P1.arm0 | arm (i) n_int 1.000 | 3.1 | r_close | 1.233407 AU | 1.2334 | +0.000007 | True | True | FREEZE | FREEZE | False | 1.9871 |
| P1.arm1 | arm (i) n_int 1.333 | 0.7 | r_close | 1.195410 AU | 1.1954 | +0.000010 | True | True | FREEZE | FREEZE | False | 1.9798 |
| P1.arm1 | arm (i) n_int 1.333 | 1.5 | r_close | 1.219419 AU | 1.2194 | +0.000019 | True | True | FREEZE | FREEZE | False | 1.9855 |
| P1.arm1 | arm (i) n_int 1.333 | 3.1 | r_close | 1.242135 AU | 1.2421 | +0.000035 | True | True | FREEZE | FREEZE | False | 1.9882 |
| P1.arm2 | arm (ii) n_int 1.000 | 0.7 | r_close | 1.153951 AU | 1.1540 | -0.000049 | True | True | FREEZE | FREEZE | False | 1.9807 |
| P1.arm2 | arm (ii) n_int 1.000 | 1.5 | r_close | 1.176601 AU | 1.1766 | +0.000001 | True | True | FREEZE | FREEZE | False | 1.9863 |
| P1.arm2 | arm (ii) n_int 1.000 | 3.1 | r_close | 1.197990 AU | 1.1980 | -0.000010 | True | True | FREEZE | FREEZE | False | 1.9889 |
| P1.arm3 | arm (ii) n_int 1.333 | 0.7 | r_close | 1.166772 AU | 1.1668 | -0.000028 | True | True | FREEZE | FREEZE | False | 1.9817 |
| P1.arm3 | arm (ii) n_int 1.333 | 1.5 | r_close | 1.191356 AU | 1.1914 | -0.000044 | True | True | FREEZE | FREEZE | False | 1.9871 |
| P1.arm3 | arm (ii) n_int 1.333 | 3.1 | r_close | 1.214595 AU | 1.2146 | -0.000005 | True | True | FREEZE | FREEZE | False | 1.9895 |
| P2 | registered | 0.7 | R_window | 95.5523 km | 95.6 | -0.047667 | True | True | OPAQUE | OPAQUE | False | 3.1094 |
| P2 | registered | 0.7 | FREEZE_root | 532.6245 km | 532.6 | +0.024530 | True | True | OPAQUE |  | False |  |
| P2.control | control normal | 0.7 | R_window | 114.9430 km | 114.9 | +0.042975 | True | True | OPAQUE | OPAQUE | False | 3.1105 |
| P2.control | control normal | 0.7 | FREEZE_root | 642.6248 km | 642.6 | +0.024763 | True | True | OPAQUE |  | False |  |
| P2.central | variant interior central | 0.7 | R_window | 119.2849 km | 119.3 | -0.015137 | True | True | OPAQUE |  | False | 2.9397 |
| P2.ffloor0.50 | f_floor 0.50 | 0.7 | R_window | 10.5843 km |  |  |  |  | OPAQUE |  | False | 5.3873 |
| P2.ffloor0.50 | f_floor 0.50 | 0.7 | OPAQUE_root | 10.5843 km | 10.6 | -0.015749 | False | True | OPAQUE |  | False |  |
| P2.ffloor0.10 | f_floor 0.10 | 0.7 | R_window | 532.6245 km | 532.6 | +0.024530 | True | True | FREEZE | FREEZE | False | 1.8621 |
| P2.ffloor0.10 | f_floor 0.10 | 0.7 | OPAQUE_root | 777.5463 km | 777.5 | +0.046313 | True | True | FREEZE |  | False |  |
| P2.arm4 | arm (i) n_int 1.000 | 0.7 | R_window | 75.7822 km | 75.8 | -0.017773 | True | True | OPAQUE | OPAQUE | False | 2.9554 |
| P2.arm4 | arm (i) n_int 1.000 | 0.7 | FREEZE_root | 396.2470 km | 396.2 | +0.046984 | True | True | OPAQUE |  | False |  |
| P2.arm5 | arm (i) n_int 1.333 | 0.7 | R_window | 84.0151 km | 84.0 | +0.015084 | True | True | OPAQUE | OPAQUE | False | 3.0194 |
| P2.arm5 | arm (i) n_int 1.333 | 0.7 | FREEZE_root | 453.5134 km | 453.5 | +0.013401 | True | True | OPAQUE |  | False |  |
| P2.arm6 | arm (ii) n_int 1.000 | 0.7 | R_window | 78.3890 km | 78.4 | -0.011004 | True | True | FREEZE | FREEZE | False | 1.9461 |
| P2.arm6 | arm (ii) n_int 1.000 | 0.7 | OPAQUE_root | 102.2799 km | 102.3 | -0.020110 | True | True | FREEZE |  | False |  |
| P2.arm7 | arm (ii) n_int 1.333 | 0.7 | R_window | 109.7621 km | 109.8 | -0.037861 | True | True | OPAQUE | OPAQUE | False | 1.9489 |
| P2.arm7 | arm (ii) n_int 1.333 | 0.7 | FREEZE_root | 111.5624 km | 111.6 | -0.037611 | True | True | OPAQUE |  | False |  |

Rows off their expected value by more than the edge tolerance: 1 -- P2.ffloor0.50 σ0.7 OPAQUE_root (-0.015749)
Rows not matching the printed digits: 0
Rows with a binding other than expected: 0

## Census of the registered grid (first violated line, auto path, registered law)

- σ 0.7 MPa: FREEZE 17802, HELD 1922, OPAQUE 173
- σ 1.5 MPa: FREEZE 17602, HELD 2161, OPAQUE 134
- σ 3.1 MPa: FREEZE 17412, HELD 2398, OPAQUE 87

