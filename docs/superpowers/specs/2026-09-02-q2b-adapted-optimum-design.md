# Q2b design — a photosynthetic optimum that is PREDICTED, not fitted

Registered 2026-09-02. Successor to
`docs/superpowers/specs/2026-09-02-q2-thermal-limit-design.md`. Q1's and Q2's
pre-registrations are frozen; nothing here edits either.

## What Q2 left, and why Q2b is not just Q2 with a better curve

Q2 ran, its Gate 2 failed, and no limits were reported. Three things came out of it,
and each shapes this design:

1. **The linear temperature response is falsified.** Grounding `t_opt` afterwards
   (`docs/bio_grounding_2026-09-02.md` §4d) showed cold-climate photoautotrophs have HIGH
   optima — Antarctic mosses 19.0–26.3 °C, cool-grown C3 vascular plants 29.4 °C — while a
   linear ramp needs `t_opt` in [12.0, 13.7] °C to satisfy Körner's rate anchors. No measured
   optimum lies in that window.
2. **Körner's two anchors are retired as a gate here.** Under the June et al. (2004)
   Gaussian AND the grounded cool-grown optimum of 29.4 °C, **no Ω satisfies both anchors** —
   scanned 1–200 °C, none. Three independent sources sit on one side and the anchors on the
   other. They are recorded as a documented conflict, not used as a check. Retiring a gate is
   a real loss and is disclosed as one.
3. **Q2's registered prediction was structurally unsatisfiable** (respiration is positive at
   `t_min`, so carbon always crosses inside the thermal cutoff). A re-registration must
   re-draw the prediction, not only the curve.

## The idea this question rests on

Scafaro et al. (2023) report a photosynthetic optimum of **29.4 °C for cool-grown** and
**32.7 °C for warm-grown** C3 plants across 49 species. The optimum TRACKS the temperature
the tissue grew at. Take that as a mechanism rather than a correlation and the model gains a
prediction it did not have: **an organism's optimum is set by its own equilibrium
temperature at its home distance**, which this model already computes from geometry. `t_opt`
stops being a free parameter.

**Adaptation is to the HABITAT temperature, not the instantaneous one.** If the optimum
tracked tissue temperature at every distance, the response would equal 1 everywhere and
temperature could never limit anything — the model would be degenerate. So `t_opt` is fixed
once, at the home distance, and the organism is then swept outward as its tissue cools away
from an optimum that does not follow.

## Registered question (Q2b)

For a passive organism at radiative equilibrium, adapted at a home distance of 1 AU so that
its photosynthetic optimum equals its tissue temperature there, and with photosynthesis
following the June Gaussian: **at what heliocentric distance does whole-organism net carbon
cross zero, and does the outer limit come from light, carbon, or temperature?**

## Model

New in `sim/thermal.py`, added BESIDE the existing functions — Q2's linear
`temperature_response` is NOT modified, because Q2's committed `gates.csv` must keep
regenerating:

- `temperature_response_gaussian(t, t_opt, omega) -> [0, 1]`
  `exp(-((t - t_opt) / omega) ** 2)`, the form of June, Evans & Farquhar (2004) as quoted
  verbatim in Scafaro et al. (2023): *"J=J(To)e−T−ToΩ2"*, where *"Ω represents the
  temperature difference from To at which J declines to e⁻¹ (0.37) of J(To)."*
  Raises on `omega <= 0` and on `t <= 0`.
- `adapted_optimum(r_home_au, area_ratio, emissivity, albedo) -> K`
  Returns `equilibrium_temperature(r_home_au, ...)`. A one-line function on purpose: it is
  the whole content of the adaptation premise, and giving it a name makes the premise
  greppable and testable rather than inlined.

`Organism` gains `omega: float` (defaulted) and a method
`net_carbon_adapted(r_au, r_home_au, k=None)` beside — never replacing —
`net_carbon_at_equilibrium`.

## The gate: the adaptation premise itself

**Gate A (thermal physics)** — retained from Q2 unchanged: at 1 AU, sphere, ε=1, α=0,
`T_eq` in [275, 282] K.

**Gate B (adaptation premise, PARAMETER-FREE)** — at the home distance the model's predicted
optimum, `T_eq(r_home, class geometry)`, must match that class's measured optimum:

| class | model predicts | measured | source |
| --- | --- | --- | --- |
| algal sphere | 5.16 °C | 5 °C and 7 °C | Colesie et al. 2014, Antarctic soil crusts |
| vascular lamina | 57.82 °C | 29.4 °C | Scafaro et al. 2023, cool-grown C3, 49 spp |

Registered band, stated unambiguously because the algal source reports TWO site values
rather than one: the admissible window is [min(measured) − 5 K, max(measured) + 5 K] per
class. Algal: [0.0, 12.0] °C from sites at 5 and 7 °C. Vascular: [24.4, 34.4] °C from the
single 29.4 °C figure. The ±5 K half-width is a **declared assumption** — no source gives an
adaptation tolerance — and it is wide enough that Gate B's verdicts do not turn on it: the
algal prediction (5.16 °C) sits mid-window and the vascular one (57.82 °C) misses by 23.4 K
even at the window's edge.

**Both outcomes are computed and disclosed here, before the run: the algal class PASSES and
the vascular class FAILS by 28 K.** This is a gate, not a prediction — the reachability
discipline requires knowing in advance what a gate admits, and stating it. What must NOT be
known in advance is the *prediction*, and it is not (below).

The vascular failure is expected and is a finding, not a defect to tune away. The most
likely cause is this model's radiative assumptions rather than the adaptation premise: ε=1
and albedo=0 are declared assumptions, a real leaf reflects roughly half of incident solar,
and this model has no transpirational cooling at all. **Do not adjust emissivity or albedo
to make Gate B pass** — that is fitting a declared assumption to a gate, and it is the
circularity this project has now caught three times.

## Registered prediction

For the class that passes Gate B (algal), with `r_home` = 1 AU: the outer crossover distance
of `net_carbon_adapted`, and which of the three limits binds. **This has not been computed.**
The reachable interval permitted by the gates must be computed and recorded in `prereg.yaml`
before the run, per Q1's and Q2's lesson — Q2 registered a prediction that no parameters
could satisfy, and that must not recur.

## Ω — declared, ungrounded, and swept

June et al. (2004) is closed access; Scafaro quotes the form but not the numeric Ω, and two
open-access sweeps found none. Ω is therefore a **declared assumption** with a sensitivity
arm, registered over the grid **{10, 15, 20, 25, 30} K**, with the crossover reported for
every value. The grid is declared, not cited: it spans the order of magnitude implied by
Ω's definition (the offset at which the rate falls to 1/e) for a curve whose optimum is
~29 °C and which retains measurable activity near 0 °C. Nothing in the literature reached
here pins it, and the prereg must say exactly that. Ω is the parameter
the answer is most sensitive to, and it is the least grounded — that combination is recorded
here rather than buried.

## Out of scope

- Any edit to `experiments/q1_crossover/` or `experiments/q2_thermal/`, both frozen.
- Re-litigating Körner's anchors: retired here, conflict documented, not re-tested.
- Insulation / pressure vessel, still deferred intact.
- Transpirational cooling and a real leaf albedo — named above as the likely cause of Gate
  B's vascular failure, deliberately NOT added, because adding them in the same change that
  tests the premise would confound the test.

## Files

```
sim/thermal.py                       + temperature_response_gaussian, adapted_optimum
sim/organism.py                      + omega field, net_carbon_adapted
experiments/q2b_adapted/prereg.yaml
experiments/q2b_adapted/run.py       gates -> sweep -> report, Q2's conventions
experiments/q2b_adapted/plot.R       sources docs/analysis/theme.R
tests/test_thermal.py                extended
tests/test_q2b_runner.py
```

Runner conventions inherit from Q2 unchanged: gates before any result, exit 2 on gate
failure with stale outputs cleared, provenance header carrying git sha + module md5s +
prereg md5 + numeric stack, and a regeneration test.

**Gate B fails for vascular, so the runner will exit 2 unless the gate is scoped per class.**
The runner MUST evaluate Gate B per class. Q2's gate logic is all-or-nothing; this is the one
place it must change, and the change is narrow:

- Gate A (thermal physics) stays global. If it fails, nothing is reported and the run exits 2.
- Gate B is per class. A class that fails it is **excluded from the sweep entirely** — no
  crossover, no limit, no row in `limits.csv` — and its failure is recorded in `gates.csv`
  with its observed and expected values. A class that passes is swept and reported.
- Exit code 0 if Gate A passed and **at least one** class passed Gate B; exit 2 if Gate A
  failed or **no** class passed Gate B.

So the expected run reports the algal class only, and `limits.csv` will contain no vascular
row. That absence is a result and must be stated in RESULTS.md, not left to be noticed.

## Testing

- Every new assertion is run against the broken state first and the failure recorded.
- Negative assertions carry a positive control in the same test.
- Q1's and Q2's regeneration tests must stay green: editing `sim/organism.py` moves
  `organism_md5`, so both experiments are re-run and their headers re-stamped by the
  code-commit → re-run → header-commit procedure in `experiments/q2_thermal/RESULTS.md` §10.

## Success

Gate A passes; Gate B passes for algal and fails for vascular as disclosed; the algal outer
limit is reported with its binding constraint and its Ω sensitivity; the reachable interval
recorded before the run is compared against the outcome; and Q1's and Q2's committed numbers
are unchanged.
