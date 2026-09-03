# Q2b: what limits range from the Sun for an organism whose optimum is PREDICTED, not fitted?

## 1. Registered question

From `prereg.yaml` (registered 2026-09-02, spec
`docs/superpowers/specs/2026-09-02-q2b-adapted-optimum-design.md`):

> For a passive organism at radiative equilibrium, adapted at a home distance of 1 AU
> so its photosynthetic optimum equals its tissue temperature there, at what
> heliocentric distance does whole-organism net carbon cross zero, and does the outer
> limit come from light, carbon, or temperature?

`python3 experiments/q2b_adapted/run.py` exited **0**. Full stdout:

```
gate thermal [-] T_eq at 1.0 AU: 278.3112 in [275.0, 282.0] pass
gate adaptation [algal] predicted t_opt (C): 5.1612 in [0.0, 12.0] pass
gate adaptation [vascular] predicted t_opt (C): 57.8196 in [24.4, 34.4] FAIL
limits algal omega=10: temperature=1.194 light=75.434 carbon=1.212 -> temperature
limits algal omega=15: temperature=1.194 light=75.434 carbon=1.380 -> temperature
limits algal omega=20: temperature=1.194 light=75.434 carbon=1.618 -> temperature
limits algal omega=25: temperature=1.194 light=75.434 carbon=1.972 -> temperature
limits algal omega=30: temperature=1.194 light=75.434 carbon=2.530 -> temperature
```

Exit 0 means Gate A passed and at least one class passed Gate B — not that every
class was answered. Only `algal` was.

## 2. Gate A (thermal physics, unchanged from Q2)

**PASS.** Equilibrium temperature of a sphere at 1 AU (area ratio 4, emissivity 1,
albedo 0) is 278.3112 K, inside the registered [275.0, 282.0] K bracket.

## 3. Gate B (the adaptation premise) — per class, parameter-free

Gate B has no fitted parameters: the model predicts `t_opt` from geometry alone
(`adapted_optimum(r_home_au, area_ratio, emissivity, albedo)`) and compares it to a
measured optimum from an independent literature source. The window is
`[min(measured) − 5 K, max(measured) + 5 K]` (`gate_b_half_width_k`, a declared,
uncited tolerance).

| class    | predicted t_opt | measured                                                 | window          | verdict  |
| -------- | --------------- | -------------------------------------------------------- | --------------- | -------- |
| algal    | 5.1612 °C       | 5.0–7.0 °C (Colesie et al. 2014, Antarctic soil crusts)  | [0.0, 12.0] °C  | **PASS** |
| vascular | 57.8196 °C      | 29.4 °C (Scafaro et al. 2023, cool-grown C3, 49 species) | [24.4, 34.4] °C | **FAIL** |

**Vascular fails by 28 K** (57.8196 − 29.4 = 28.4196 °C, ≈28 K over the measured
value; 23.4 °C outside the gate window's upper edge). Because Gate B is evaluated
per class rather than all-or-nothing, this failure does **not** abort the run — it
excludes vascular from everything downstream and is recorded in `gates.csv`.
**Vascular therefore has no row anywhere in `sweep.csv` or `limits.csv` — its only
appearance in this experiment's output is the FAIL row in `gates.csv`. That absence
is itself a result, not an omission: it says the geometry-only prediction of a
vascular optimum is wrong by 28 K, not that no vascular optimum exists.**

**What the vascular failure most likely means.** The model's geometry-only
prediction uses the same declared assumptions as Q2 and Q1: emissivity = 1,
albedo = 0, and no transpirational cooling. A flat lamina (area_ratio = 2, the
vascular preset) with those assumptions runs far hotter at equilibrium than a real
leaf, which loses heat by transpiration and reflects some incident light — both of
which this model omits by design. The 28 K overshoot is consistent with exactly
that missing cooling, not with a refutation of the adaptation premise itself (which
the algal class passed cleanly at the registered `area_ratio=4.0` — not, as an
earlier draft of this section claimed, because algal life is straightforwardly
"closer to a true blackbody sphere": see the geometry caveat immediately below,
which withdraws that claim). **These assumptions are not adjusted here to make
vascular pass** — `emissivity`, `albedo`, and the absence of a transpiration term
are frozen in `prereg.yaml`.

**The one passing gate rests on an undisclosed sensitivity to `area_ratio`, with
more leverage than the parameters this section already disclosed.** Gate B is
parameter-free in `t_opt` — the model predicts it rather than fitting it — but
`t_opt = T_eq(1 AU, area_ratio)` is _totally_ determined by `area_ratio` once
`r_home_au`, `emissivity`, and `albedo` are fixed. Recomputed directly against
`sim.thermal.equilibrium_temperature`: the algal gate window `[0.0, 12.0] °C`
admits `area_ratio ∈ [3.630, 4.311]` and nothing outside that band —
`area_ratio=3` predicts 25.91 °C, `area_ratio=2` predicts 57.8196 °C (the
identical formula at the identical `area_ratio` as the vascular class, hence the
identical number), and `area_ratio=1` predicts 120.44 °C. The registered
`area_ratio=4.0` sits inside a band only 0.681 wide. Worse, the measured side of
this gate — Colesie et al. (2014) — is **lichen-dominated Antarctic biological
soil crusts**: flat mats growing on the ground, whose radiative geometry sits
close to a lamina (`area_ratio` 1–2), not a sphere (4). Modelled at
`area_ratio=2`, the geometry its own measurement is closest to, the algal class
predicts 57.8196 °C — 45.82 K above the window's upper edge (12.0 °C) — missing
Gate B on the same footing vascular does — 45.82 K past the window edge against
vascular's 23.42 K, so about 1.8x further out, not the same margin — and for the same
underlying reason: no transpirational cooling, no reflectance, and no hard
temperature floor built into the assimilation term. This is a caveat on the one
gate that passed, not a re-scoring of it: `area_ratio` stays frozen at its
registered value of 4.0, and Gate B's window is not touched here. Ω gets a whole
section below (§5); this deserves comparable weight, which is why it is recorded
here rather than left as an unremarked number in a gates.csv column no one names.

## 4. The algal outer limit, per Ω, and its binding constraint

From `limits.csv` (all rows are `class=algal`; vascular has none):

| Ω (K) | outer_au (net carbon crossover) | binding     |
| ----- | ------------------------------- | ----------- |
| 10    | 1.2120                          | temperature |
| 15    | 1.3795                          | temperature |
| 20    | 1.6180                          | temperature |
| 25    | 1.9723                          | temperature |
| 30    | 2.5301                          | temperature |

Two different numbers matter here and should not be conflated. `outer_au` is the
distance at which the full coupled model (`net_carbon_adapted`, the Gaussian
temperature response applied to the actual carbon budget) itself crosses zero —
this is the number that moves with Ω. `binding` is a separate, three-way diagnostic
(`classify_limit`) that also computes a pure light-only crossover (75.434 AU,
constant — it doesn't depend on temperature or Ω at all). **This is not Q1's
committed algal value** (67.2623 AU, `experiments/q1_crossover/crossover.csv`):
Q1 froze `leaf_mass_ratio=0.8`, while this prereg registers the grounded
unicellular value `leaf_mass_ratio=1.0` (§ presets), and `crossover_distance_for`
moves with that divisor — the two numbers differ because the input differs, not
because either run computed the light-only crossover wrong. A pure
thermal floor (the distance at which equilibrium temperature falls to the class's
absolute survival floor `t_min`, **1.1945 AU, also constant across Ω**, since it
depends only on geometry and `t_min`, never on the Gaussian response or Ω). At every
Ω in the grid, **the thermal floor (1.1945 AU) sits closer to the Sun than the
model's own carbon crossover (1.2120–2.5301 AU)** — meaning the absolute cold limit
binds before the Gaussian-response-based carbon crossing has even happened. That is
why `binding = temperature` at all five Ω: temperature is the tightest of the three
candidates, not carbon, even though the reported `outer_au` in each row is the
carbon crossing distance the registered question actually asked for.

## 5. Ω sensitivity — the least-grounded parameter in this design

`omega_grid_k` is explicitly a **declared, uncited assumption** in `prereg.yaml`:
"June et al. (2004) is closed access and two open-access sweeps found no numeric
Ω... Swept because the answer is most sensitive to the least grounded parameter."
That sensitivity is visible directly in the outer-carbon-root column above: it runs
**1.2120 AU at Ω=10 up to 2.5301 AU at Ω=30** — a factor of **2.09×**, more than a
doubling, across a 5-point linear grid in an unsourced parameter. The thermal-floor
candidate (1.1945 AU) is, by construction, insensitive to Ω, so the _binding
answer_ ("temperature") is stable across the whole grid — but the _distance at
which the full model's own net carbon crosses zero_ is not, and it is that second
number, not the binding label, that is closest to what "at what heliocentric
distance" in the registered question is asking for. **Confidence in a single
numeric outer limit for algal life should be low**: doubling the carbon-crossing
distance by moving Ω over a range with no independent source to narrow it means the
reported number is closer to a demonstration that the model is well-posed than to a
settled physical answer.

## 6. Registered prediction versus outcome — FALSIFIED

`prereg.yaml`:

```yaml
predicted_binding_limit:
  algal: carbon # the QUALITATIVE prediction, registered; genuinely unknown
```

**Observed: `binding = temperature` for algal at every one of the five registered Ω
(10, 15, 20, 25, 30).** The registered prediction was carbon; the model computed
temperature, unanimously, across the whole swept parameter. This is a genuine
falsification, not a near-miss or a labeling ambiguity — it is also, as far as this
project's record goes, **the first registered prediction here that was both
falsifiable (a real "carbon" candidate existed and could have won) and actually
tested (the run completed and reported a verdict)**, unlike Q1's unreachable band
or Q2's structurally-unsatisfiable prediction. It is reported here as a failed
prediction, not softened, and `prereg.yaml` is not edited to match the outcome.

**Why `carbon` was the registered prediction, and what losing to a fixed floor
shows.** `net_carbon_adapted` — the function this design added — carries no hard
temperature floor of its own: unlike Q2's `temperature_response` (0 below
`t_min`, a switch), `temperature_response_gaussian` only decays asymptotically
toward zero as habitat temperature departs from the adapted optimum. The
belief behind that label — **reconstructed here after the fact, because the
pre-registration recorded `predicted_binding_limit.algal: carbon` with no
rationale attached** — was that the mechanism this experiment actually built — an
organism's assimilation fading out as its Gaussian response detunes from a
`t_opt` fixed at home — would be the thing that finally drove net
carbon through zero, since nothing else in the modeled carbon budget has a
cutoff of its own. Nothing in the frozen prereg states this; it is the reasoning
as best it can be reconstructed, and a reader should treat it as such. That
belief was wrong: `classify_limit`'s three-way candidate
set also includes `temperature`, a floor with no dependence on the Gaussian
machinery at all — `thermal_au = r_home_au * (T_eq(r_home_au)/t_min)**2`, the
distance at which passive equilibrium temperature alone reaches the class's
absolute survival floor `t_min` (254.65 K for algal, Pointing et al. 2015 via
`docs/bio_grounding_2026-09-02.md` §1). That candidate sits at a fixed 1.1945 AU
regardless of Ω because none of its three inputs — `r_home_au`, the geometry
that sets `T_eq(r_home_au)`, and `t_min` — is a function of Ω; Ω enters the
model only through `temperature_response_gaussian`, which does not appear
anywhere in `thermal_au`'s formula. The carbon crossover, by contrast, is
literally the distance at which the Gaussian-scaled assimilation term falls
below respiration, so widening Ω (a flatter, slower-decaying response) directly
pushes that crossing further out — exactly the 1.2120→2.5301 AU spread §5
documents. The falsification therefore shows something about the model, not
just about a label: the sophisticated part of this design — the adapted optimum
and its Gaussian width — never gets the chance to be the acting constraint,
because a much older, Ω-independent number (an absolute cold floor carried over
from Q2's `t_min` gate) is always reached first. The adaptation machinery this
experiment built is real and correctly computed; it is simply not the thing
that ends up limiting range in this model.

## 7. Reachable interval, recorded before the run, versus what happened

`prereg.yaml`'s `reachable.note`, computed and written **before** this run
(Task 3, reproduced verbatim):

> algal: a first root (net carbon crossing from negative to positive moving outward
> from the inner edge) exists for every omega in the grid, and moves INWARD as
> omega widens: 0.8787 AU (omega=10) -> 0.8376 -> 0.8052 -> 0.7794 -> 0.7587 AU
> (omega=30). Narrower omega pushes the reachable zone further out...
>
> vascular: for omega in {10, 15, 20}, net carbon is negative across the WHOLE
> swept range [0.5, 100] AU -- there is no distance, including the 1 AU home
> distance itself, at which this organism's adapted parameters produce positive
> net carbon... Only at the two widest scanned omegas (25, 30) does a root
> reappear, at 1.0840 AU (omega=25) and 1.0705 AU (omega=30)...

**The prereg's mechanism claim above is wrong, and it stays wrong because the
file is frozen.** `T_eq(1 AU, area_ratio=2)` **is** 57.82 °C — identical to the
vascular preset's own predicted `t_opt`, not "~5–8 °C" below it; the "~5–8 °C"
figure belongs to the _algal_ sphere's equilibrium temperature, not vascular's.
The Gaussian response at vascular's own home distance is therefore exactly 1.0,
its maximum, not a small fraction of it. The real reason the lamina is
carbon-negative at its own optimum is Q10, not a mismatched response: at
`t_home = 330.97 K` (57.8196 °C), `Q10**((330.97−293)/10) = 13.8995`, so
`respiration/leaf_mass_ratio = 0.65 * 13.8995 / 0.5 = 18.0694` against gross
assimilation of `9.6550`, giving `net = 9.6550 − 18.0694 = −8.4144` — temperature-
scaled respiration outruns a saturating assimilation term even where the
response curve sits at its peak. The companion claim, "narrower omega pushes the
reachable zone further out," is also backwards: a narrower Gaussian raises the
inner (hot-side) root from 0.7587 to 0.8787 AU — moving it OUTWARD, away from the
Sun, which is the opposite of what the note's
own numbers show (0.8787 AU at Ω=10 down to 0.7587 AU at Ω=30) — and pulls the
outer root inward too (§4–5: 1.2120 AU at Ω=10 versus 2.5301 AU at Ω=30).
Narrowing Ω shrinks the reachable zone from both ends; it does not push it
outward.

That note describes the **inner** root (the first, hot-side crossing into positive
net carbon) and vascular's viability, computed from `curve_shape` alone — it does
not commit to an outer-limit number, deliberately: "NO numeric band is registered...
No independent basis for a numeric band exists here, so none is invented." What
actually happened matches the disclosed curve shape exactly: algal produced the
two-root `[(-1,1),(1,-1)]` pattern at every Ω and reported an outer root
(§4 above); vascular never reached the sweep at all, because it was excluded at
Gate B before `curve_shape` or the reachable interval mattered — Gate B, not the
reachability of a root, is what determined vascular's fate.

## 8. Körner's anchors, retired

Q2's held-out gate used Körner's rate anchors (60–70% of maximum at 5 °C, 30–40% at
0 °C) to test a linear temperature response and failed. Q2b does not re-use them as
a gate. `prereg.yaml`, verbatim:

> Koerner's rate anchors are RETIRED as a gate here. Under the June Gaussian and the
> grounded 29.4 C optimum, no omega satisfies both (scanned 1-200 C). Recorded as a
> documented conflict, not used as a check. See the spec.

The design spec confirms this was checked, not assumed: scanning Ω from 1–200 °C
under the June et al. (2004) Gaussian form and the grounded 29.4 °C vascular
optimum, **no Ω satisfies both Körner anchors simultaneously**. Three independent
sources (the Gaussian functional form, the grounded optimum, and Körner's anchors)
do not agree, so retaining Körner's anchors as a pass/fail gate here would have
meant gating on a check the model's own inputs cannot jointly satisfy — a real loss
of a held-out check, disclosed rather than silently dropped.

## 9. Provenance (verbatim from `limits.csv`)

```
# git_sha=a68bf0c46e2dc34d4c504ac9954453dca91f272f
# thermal_md5=6b0ecfc0353686a3534939ac9eff9a0e
# organism_md5=8882eac48ee3e4932e643650e75e0732
# physiology_md5=adacb668ea4f79b428ca0155381da220
# prereg_md5=774bef761dc2ce02d87540a528b1d876
# python=3.13.2
# numpy=2.3.5
# scipy=1.16.3
# written=2026-09-03T00:51:36-04:00
```

## 10. Figures

`Rscript experiments/q2b_adapted/plot.R` produced two PNGs under
`experiments/q2b_adapted/figures/`, rendered with no warnings and visually
confirmed (not just assumed from the clean render):

- `net_carbon_adapted.png`: net carbon vs. log distance, one line per Ω, algal
  only (no vascular series exists to plot). All five Ω curves peak near 1 AU (the
  home distance, by construction) at ~9.8 µmol m⁻² s⁻¹, and widen visibly as Ω
  increases — the widest (Ω=30) curve's outer tail extends furthest right, matching
  the 2.5301 AU outer root; the narrowest (Ω=10) curve's tail is the tightest,
  matching 1.2120 AU. The legend correctly lists only `algal`. A dashed vertical
  line at 1.1945 AU, labeled "binding thermal floor," marks the distance this run
  actually found limiting — it sits inside every curve's positive region, near the
  peak. It is NOT far short of the curves' zero-crossings: the omega=10 curve
  crosses at 1.2120 AU, only 0.0175 AU (1.5%) beyond the floor, and the two are
  visually coincident on the figure. The label
  overlaps the curves near the peak (a consequence of the log x-axis compressing
  everything near 1 AU) but is legible and not clipped.
- `outer_limit_vs_omega.png`: net-carbon crossover (AU) vs. Ω, five points
  connected by a line, rising monotonically and convexly from 1.212 AU to
  2.530 AU. Legend shows only `algal`. A dashed horizontal line at 1.1945 AU,
  labeled "binding thermal floor (1.1945 AU)," sits below every one of the five
  points — visually showing that the plotted quantity (the carbon crossover,
  what moves with Ω) is not the outer limit this run reported (temperature, flat
  at the dashed line). Retitled from "sensitivity of the outer limit to Omega"
  to "sensitivity of the net-carbon crossover to Omega," since `outer_au` was
  never the binding limit at any swept Ω.

Both figures were copied to the Windows Downloads folder and opened once
(`net_carbon_adapted.png`) to avoid multiple pop-ups; both PNGs were then read
directly and inspected — no layer is missing, no text is clipped, no data is
absent from either that should be present, and the new reference lines drew on
both (verified visually, not just assumed from the clean, warning-free render).

## 11. Regeneration test

`tests/test_q2b_runner.py::test_committed_q2b_csvs_regenerate_exactly` re-runs
`run.py` into a temp directory and diffs each committed CSV body (excluding the
`git_sha` and `written` provenance lines) against the committed copy. It passed
against the real committed CSVs. Tampering with one committed value
(`experiments/q2b_adapted/limits.csv`, `algal,10,1.2120,temperature` →
`algal,10,9.9999,temperature`) made it fail for the stated reason:

```
E           AssertionError: limits.csv does not regenerate
E           assert ['# thermal_m...y=2.3.5', ...] == ['# thermal_m...y=2.3.5', ...]
E
E             At index 8 diff: 'algal,10,9.9999,temperature' != 'algal,10,1.2120,temperature'
E             Use -v to get more diff
```

The value was restored (`diff` against the pre-tamper backup confirmed byte-identical)
and the test passes again.

## 12. Suite and lint

`python3 -m pytest -q`: **117 passed** at the run recorded above (§1). A
subsequent fix wave (findings A–H, this document's §3/§4/§6/§7 corrections,
`plot.R`'s relabeling, and new tests pinning `net_carbon_adapted`'s
`leaf_mass_ratio` divisor and `outer_carbon_crossover`'s/`classify_limit`'s
three previously-unguarded branches) added 5 tests with no change to any
committed CSV, prereg, or the numbers in §1's stdout: **122 passed**.
`ruff check .`: **10 errors**, all pre-existing `E741` (ambiguous variable
name `l`) in `tests/test_runner.py` — no new errors introduced by this task
or the fix wave.
