# Q1 results — 2026-09-02

Provenance: git_sha=809f935d66241855572763969255ff4c0b17f8c7, physiology_md5=eeddc3a10b1f0060010b1641814fe06d, organism_md5=4342263e4e2de18d1663733d3c58cd23, prereg_md5=58e2bd03c17b8c8c50e41b92f30ae82e, written=2026-09-02T12:47:59-04:00.

## Calibration gate

| class    | k   | observed I_c (µmol) | gate       | pass |
| -------- | --- | ------------------- | ---------- | ---- |
| vascular | 100 | 6.9519              | [5.3, 9.0] | True |
| algal    | 20  | 0.4918              | [0.0, 1.0] | True |

## Crossover distance r\* (AU) vs pre-registered prediction

| class    | k   | r\*     | predicted | inside |
| -------- | --- | ------- | --------- | ------ |
| vascular | 50  | 19.3537 | [12, 22]  | True   |
| vascular | 100 | 13.6851 | [12, 22]  | True   |
| vascular | 200 | 9.6769  | [12, 22]  | False  |
| algal    | 10  | 95.1233 | [35, 55]  | False  |
| algal    | 20  | 67.2623 | [35, 55]  | False  |
| algal    | 40  | 47.5616 | [35, 55]  | True   |

## Verdict

The calibration gate passed for both presets (vascular I_c=6.9519 in [5.3, 9.0]; algal I_c=0.4918 in [0.0, 1.0]). For the vascular class the default-k (k=100) prediction HELD: `inside` is True at r*=13.6851 AU, and it is also True at k=50 (r*=19.3537 AU); it is False at k=200 (r*=9.6769 AU), which falls below the pre-registered [12, 22] band. For the algal class the default-k (k=20) prediction FAILED: `inside` is False at r*=67.2623 AU, above the pre-registered [35, 55] band, and False again at k=10 (r*=95.1233 AU); only k=40 (r*=47.5616 AU) is True. So three of six swept k values fall outside their band: vascular k=200, algal k=10, and algal k=20. No re-tuning was performed after the run — no preset, gate, or prediction was edited once the sweep had been executed.

## Figures

- `figures/net_carbon_vs_distance.png`
- `figures/crossover_vs_k.png`

## What this does and does not show

Light-only, tissue temperature fixed at 293 K. The heating cost (v2) can only move r\* inward. Pressure and element budgets are not modelled.
