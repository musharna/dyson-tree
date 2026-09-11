# Q1 results — 2026-09-02

> ⚠️ **SUPERSEDED NUMBERS, SAME VERDICTS (2026-09-06, S5).** `PAR_FRACTION` was
> corrected from an unsourced 0.45 to the measured AM0 value 0.3879, so every
> crossover in this file is 1.0770x too large. Multiply by
> `sqrt(0.3879/0.45) = 0.928487`: 19.3537 -> 17.9688, **13.6851 -> 12.7058**,
> 9.6769 -> 8.9844, 95.1233 -> 88.3162, **67.2623 -> 62.4490**, 47.5616 ->
> 44.1581. The compensation irradiances (6.9519, 0.4918) do NOT move — `I_c` is
> an irradiance and is PAR-independent — and **no `inside` verdict changes**.
> `crossover.csv` in this directory is current; this prose is not, and is
> bannered rather than rewritten per the project's convention. See
> `docs/bio_grounding_2026-09-02.md` §20 and `docs/FINDINGS.md`.


Provenance (matches the header of the committed CSVs):
git_sha=54740719e96900b1165970e1182b090689014f9a,
physiology_md5=adacb668ea4f79b428ca0155381da220,
organism_md5=a68658c3a9a7f30449aaba6389f33586,
prereg_md5=58e2bd03c17b8c8c50e41b92f30ae82e,
python=3.13.2, numpy=2.3.5, scipy=1.16.3,
written=2026-09-02T15:26:36-04:00.

Every value below was first produced at git_sha=809f935 on 2026-09-02T12:47:59
and is byte-identical after the re-run above; only the provenance header moved.
Nothing was re-tuned after the sweep: no preset, gate, prediction or model
constant has been edited since the run.

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

## How much of each prediction the gate had already decided

The calibration gate constrains `r_d` at 1 AU; r\* follows from `r_d`. So the
two are not independent, and the verdicts above read differently once you know
what range of r\* a gate-passing organism could have produced at all. Holding
every other registered value fixed and scanning `r_d` against each gate:

| class    | gate I_c   | gate-admissible `r_d` | reachable r\*     | registered band |
| -------- | ---------- | --------------------- | ----------------- | --------------- |
| vascular | [5.3, 9.0] | [0.5033, 0.8257]      | [11.89, 15.81] AU | [12, 22]        |
| algal    | [0.0, 1.0] | [0.0000, 0.4762]      | [47.02, ∞) AU     | [35, 55]        |

Read plainly:

- **The vascular band was largely pre-satisfied by the gate.** 96.2% of the
  gate-admissible `r_d` interval produces an r\* inside [12, 22]; only the
  sliver giving r\* in [11.89, 12) could have missed. The default-k "hit" was
  close to forced.
- **The algal band was only partly reachable.** No gate-passing `r_d` can put
  r\* below 47.02 AU, so 60.1% of the registered [35, 55] band — everything
  from 35 to 47.02 — was unreachable before the sweep ran. The upper end of
  the interval is unbounded: as `r_d` → 0 the compensation point goes to zero
  and r\* diverges. Below `r_d` = 0.1104 there is no crossover inside the
  [0.5, 100] AU solve window at all, so a gate-passing algal organism in that
  range would have produced no answer rather than a wrong one. The vascular
  gate has no such region: its floor is `r_d` = 0.5033, well above the 0.0140
  at which vascular r\* would leave the window, so every gate-passing vascular
  organism yields an answer somewhere in [11.89, 15.81] AU.

This does not soften the misses; a miss is still a miss. It says the vascular
hit carries much less information than the algal miss does.

## The uncited assumption that sets the scale

`compensation_irradiance` solves against **leaf** respiration, while
`net_carbon` divides by `leaf_mass_ratio`. The gate therefore constrains `r_d`
while the answer is set by `r_d / leaf_mass_ratio`, and the denominator is
structurally invisible to the gate. Algal preset, `r_d` fixed at its registered
0.24:

| leaf_mass_ratio  | I_c (µmol) | gate | r\* (AU) |
| ---------------- | ---------- | ---- | -------- |
| 0.2              | 0.4918     | PASS | 32.03    |
| 0.5              | 0.4918     | PASS | 52.68    |
| 0.8 (registered) | 0.4918     | PASS | 67.26    |
| 1.0              | 0.4918     | PASS | 75.43    |

I_c is identical to four decimal places across a 2.35× swing in r\*. The
vascular preset behaves the same way: I_c = 6.9519 at every value, r\* = 7.62,
13.69, 17.79, 20.06 AU for the same four ratios.

The consequence is sharp. **At `leaf_mass_ratio` = 0.5 the algal r\* is 52.68
AU, inside the registered [35, 55] band.** The algal prediction was carried out
of its band by an assumption no measurement in this experiment can see.

`leaf_mass_ratio` carries no citation — `prereg.yaml` marks it
`# assumption: thallus mostly photosynthetic`. It is not the only uncited
parameter (`par_fraction`, `photons_per_j` and `q10` are also bare
`# assumption`, and `a_max` and `k` carry no comment at all), and its
per-unit sensitivity is not exceptional: d ln r\*/d ln `leaf_mass_ratio` is
0.515 (algal) and 0.575 (vascular), against exactly 0.500 for `par_fraction`
and `photons_per_j`, which enter as √. What matters is not the elasticity but
how wide a range the parameter is free to occupy. Over the 0.2–1.0 span tabled
above, `leaf_mass_ratio` moves algal r\* by 2.35× and vascular r\* by 2.63×;
a comparable 0.40–0.50 excursion in `par_fraction` moves algal r\* only from
63.42 to 70.90 AU and vascular r\* from 12.90 to 14.43 AU.

`leaf_mass_ratio` is not, however, the widest freedom the gate leaves open.
`a_max` enters r\* through the same product `a_max`·`leaf_mass_ratio`/`r_d`, so
its elasticity is identical by construction (0.515 algal, 0.575 vascular), and
it is one of the two parameters carrying no comment at all. What differs is how
far each gate constrains it. The vascular gate is two-sided and confines `a_max`
to [7.87, 12.91], an r\* span of 11.89–15.81 AU (1.33×) — narrower than
`leaf_mass_ratio`'s 2.63×, so for the vascular class `leaf_mass_ratio` is
indeed the wider of the two. The algal gate is one-sided (I_c ≤ 1.0) and so
places no upper bound on `a_max` whatsoever: `a_max` = 20 passes the gate at
I_c = 0.2429 and gives r\* = 95.86 AU, and `a_max` = 30 passes at I_c = 0.1613
with no crossover anywhere inside the [0.5, 100] AU window. For the algal class
— the one whose prediction failed — `a_max` is the wider freedom, not
`leaf_mass_ratio`.

So the gate leaves two uncited parameters loose and reports on neither, and for
the failing class the one it constrains least is not the one this section began
with.

Gating `leaf_mass_ratio` against a real leaf-mass-ratio / thallus-fraction
source is a prerequisite for Q2, whose heating cost scales with the same
non-photosynthetic mass fraction.

## The solve window, and how close the algal result came to leaving it

r\* is searched on **[0.5, 100] AU** (`prereg.yaml`, `sweep.r_min_au` /
`r_max_au`). Anything outside that window is not reported: `crossover_distance`
raises rather than extrapolating, and the runner has no fallback.

Algal k=10 gives r\* = 95.1233 AU — 95.1% of the ceiling. One more step down
the k sweep would have aborted the whole run: at algal k=8 the solver raises

    no sign change of net carbon on [0.5, 100.0] AU: min=0.03799, max=9.693

Net carbon is still positive at 100 AU, so there is no crossover to report
inside the window. Failing loud there is the intended behaviour; the point is
that the reported algal numbers sit near the edge of the region where this
experiment can answer at all, and the k sweep stopped one step short of it.

## Figures

- `figures/net_carbon_vs_distance.png`
- `figures/crossover_vs_k.png`

## What this does and does not show

Light-only, tissue temperature fixed at 293 K. The heating cost (v2) can only move r\* inward. Pressure and element budgets are not modelled.
