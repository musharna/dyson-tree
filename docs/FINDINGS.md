# Findings

**Can a tree grow in space?** This repository asks that question the way you would
ask it of a crop: build the smallest honest carbon budget for one photosynthetic
organism at a distance `r` from the Sun, write down what you expect BEFORE running
it, and then report what happened — including when what happened was that the
prediction was wrong.

**Four questions were registered and run (Q1, Q2, Q2b, Q4); one more (Q3) was
specified, and its premise was falsified before it could be registered.** Of the
registered predictions three held — Q1's vascular crossover, judged as the
repository judges them, at each class's registered default `k`, and both of Q4's
vessel edges (§5). Q1's algal
prediction missed its band, Q2b's prediction was falsified outright **for the
algal class — the only class that run answered, and whether it generalises is
open** (§1), and Q2's was never tested at all because Q2's own held-out gate
failed and the runner refused to report. That is the headline, and it is the reason this repository is worth
reading. A model that only ever confirmed its author would tell you nothing.

**Every number this page reports as a result names the file it lives in and the
command that produces it.** The three registered runners write theirs; the result
figures no runner emits — the Q2b candidate tables, the response at the thermal
floor, the Q1 gate-reachability scan — are each written to a committed CSV by a
`tools/derive_*.py` script from committed inputs, and `tests/test_derived_csvs.py`
checks that they still regenerate.

Two kinds of number on this page are **not** in a CSV, and are marked here rather
than left to look like an oversight:

- **Q3's figures.** Q3 was answered analytically and has no runner. They are read
  off a cited primary source or computed in the `tools/check_*.py` scripts, and
  its section names the documents that carry the working.
- **A few one-off diagnostics quoted inside an argument** rather than reported as
  results — the vascular net carbon at home (−8.47), the crust-at-ratio-1
  temperature (120.44 °C), the four Q2 miss ratios. Each names the model function
  or the committed CSV it comes from at the point it is used, which is enough to
  recompute it, but no committed file holds the number itself.

---

## What was falsified

### 1. Carbon does not set the outer limit. Temperature does — for the algal class. (Q2b)

**Registered prediction:** for an organism whose photosynthetic optimum is
_predicted from its own geometry_ rather than fitted, carbon balance binds first —
the organism runs out of light-limited carbon before anything else stops it.

**Result: FALSIFIED.** Temperature binds at every width of the response curve
that was swept:

| class | Ω (K) | temperature candidate | light candidate | carbon candidate | binding         |
| ----- | ----- | --------------------- | --------------- | ---------------- | --------------- |
| algal | 10    | 1.1945 AU             | 70.04 AU        | 1.2119 AU        | **temperature** |
| algal | 15    | 1.1945 AU             | 70.04 AU        | 1.3794 AU        | **temperature** |
| algal | 20    | 1.1945 AU             | 70.04 AU        | 1.6178 AU        | **temperature** |
| algal | 25    | 1.1945 AU             | 70.04 AU        | 1.9718 AU        | **temperature** |
| algal | 30    | 1.1945 AU             | 70.04 AU        | 2.5289 AU        | **temperature** |

Every row is the **algal** class — the only class the run answered. Why, and what
that costs the claim, is two subsections down.

These are three **separately computed candidate distances**, and the run reports
whichever is smallest. The temperature candidate is a fixed **1.1945 AU** — the
distance at which equilibrium temperature reaches the algal floor (254.65 K,
Pointing et al. 2015). It depends only on geometry and `t_min`, never on Ω or on
the response curve, which is why it is identical down the column. It is tighter
than the carbon crossing at every Ω, and light — the constraint the whole project
started from — is outside by a factor of nearly sixty.

**What this does not say.** It does not say the modelled rate switches off past
1.1945 AU. Q2b's carbon path (`Organism.net_carbon_adapted`) uses the Gaussian
response, whose own docstring is explicit that _"there is no t_min here: the
Gaussian approaches zero asymptotically rather than switching off at a floor"_ —
at 1.1945 AU and Ω = 10 the response is 0.0037, not 0, and net carbon is still
+0.0197. Carbon does cross zero, at the 1.2119 AU in the table. The finding is a
comparison of candidate distances, not a cut-off: the temperature limit simply
arrives first. `experiments/q2b_adapted/RESULTS.md` states this carefully and is
the authority if this summary and it ever disagree.

Those two figures live in `experiments/q2b_adapted/floor_response.csv`
(`python3 tools/derive_q2b_floor_response.py`). It carries two rows, because the
distance above is quoted rounded: at the literal 1.1945 AU the response is
0.003697 and net carbon +0.019725, and at the full-precision thermal floor
(1.194466 AU) they are 0.003703 and +0.019783. Both round to the 0.0037 and
+0.0197 printed here, and the gap is rounding of the input distance.

- Lives in: `experiments/q2b_adapted/limits.csv` (the carbon candidate, as
  `outer_au`) and `experiments/q2b_adapted/candidates.csv` (all three
  candidates, the two tables on this page), written up in
  `experiments/q2b_adapted/RESULTS.md`
- Command: `python3 experiments/q2b_adapted/run.py` (exits 0), then
  `python3 tools/derive_q2b_candidates.py`
- Produced by the code whose commit the file's own `git_sha` header names
  (identical across every committed CSV) — see _A note on the CSV provenance headers_ below
  for the 1.0.0 header defect this replaced

**Only one of the two organism classes was answered at all**, and the gate that
decided which is _itself retired_. Q2b gated its adaptation premise per class by
comparing a model-predicted optimum against a measured one: the algal class
"passed" (5.1612 °C predicted against 5.0–7.0 °C measured, Colesie et al. 2014),
the vascular class failed by 28 K (57.8196 °C predicted against 29.4 °C measured,
Scafaro et al. 2023) and was excluded from everything downstream — it has no row in
`sweep.csv` or `limits.csv`, only a FAIL row in `gates.csv`.

**That gate could not have been informative either way**, and the reason is
recorded in `docs/thermal_premise_retired_2026-09-03.md`: it compared a
_vacuum-radiative_ temperature against _Earth-thermodynamic_ optima. Terrestrial
tissue temperature is set by radiation **plus** conduction, convection and
evaporation — Earth's own blackbody equilibrium is −18 °C against a +15 °C mean
surface, and that 33 K gap is the missing physics. Under honest geometry every
class fails its window (`sim.thermal.equilibrium_temperature` at 1 AU: crust mat
at ratio 1 → 120.44 °C, the same crust
at ratio 2 → 57.82 °C, vascular lamina at ratio 2 → 57.82 °C); the single pass came
from modelling a flat soil crust as a **sphere** (ratio 4 → 5.16 °C), the geometry
that note disowns — a coincidence, not a signal. This is a design
error in Q2b's spec, not a property of the organisms — and it supersedes the
"a flat lamina runs hotter than a real leaf" explanation still printed in
`experiments/q2b_adapted/RESULTS.md`.

**How far the falsification survives that retirement — stated precisely, because
the answer is not "entirely".** Within the algal class it is untouched: it
compared the thermal floor against the carbon crossing, both computed inside the
model, and temperature won at every Ω whether or not Gate B meant anything.

**But the retired gate is what made the result a clean sweep.** Running Q2b's own
`classify_limit` on the vascular class — the class Gate B excluded — gives:

| Ω   | temperature | light   | carbon                  | binding     |
| --- | ----------- | ------- | ----------------------- | ----------- |
| 10  | 1.5581      | 12.7058 | _no crossing in window_ | temperature |
| 15  | 1.5581      | 12.7058 | _no crossing in window_ | temperature |
| 20  | 1.5581      | 12.7058 | _no crossing in window_ | temperature |
| 25  | 1.5581      | 12.7058 | **1.2060**              | **carbon**  |
| 30  | 1.5581      | 12.7058 | **1.3920**              | **carbon**  |

These rows are in `experiments/q2b_adapted/candidates.csv`, flagged
`in_limits_csv = no (gate B excluded)`. They exist only there: the runner writes
no vascular row to `sweep.csv` or `limits.csv`, and that exclusion is registered
and stays. Computing them changes nothing the runner reported —
`tools/derive_q2b_candidates.py` asserts Gate B still passes algal only before it
writes anything.

So the registered prediction — carbon binds — **would have held for vascular at
Ω = 25 and Ω = 30.** "Temperature binds at every Ω" is true of the class that was
answered, and the gate that excluded the other class has since been retired as
uninformative. Read plainly: **the falsification stands for the algal class, and
whether it generalises is open.**

Two things keep that from being a quiet retraction. The exclusion was registered
in advance — the prereg carries `expect: fail` for vascular — so the run did what
it said it would do. And the three Ω where vascular still reports `temperature`
are not evidence for temperature at all: at Ω ∈ {10, 15, 20} the vascular carbon
candidate is not a number, because **net carbon is negative across the entire
[0.5, 100] AU grid** — the organism never breaks even anywhere on the swept range.
(Its net carbon at the 1 AU home is −8.47 — `Organism.net_carbon_adapted(1.0, 1.0)`
on the prereg's vascular preset; no committed CSV holds it, because the class has
no row in `sweep.csv` — but that figure is Ω-independent and so
does not by itself distinguish these three Ω from the two where carbon does cross.) `classify_limit` records that as `nan`, and
`min()` drops it. The prereg discloses this shape in advance
(`experiments/q2b_adapted/prereg.yaml`, `curve_shape`). So of the five vascular
rows, two say carbon binds and three describe an organism that is never viable —
neither group supports "temperature binds".

### 2. The algal range prediction missed by 7.45 AU, in the wrong direction (Q1)

**Registered prediction:** the algal crossover — the distance where whole-organism
net carbon reaches zero — falls in **[35, 55] AU**.

**Result: FALSIFIED at the registered default `k = 20`: r\* = 62.4490 AU**, above
the band, and wrong again at `k = 10` (88.3162 AU). Only `k = 40` (44.1581 AU)
lands inside. Three of the six swept `k` values fall outside their band:

| class    | k   | r\* (AU)    | registered band | inside  |
| -------- | --- | ----------- | --------------- | ------- |
| vascular | 50  | 17.9688     | [12, 22]        | yes     |
| vascular | 100 | **12.7058** | [12, 22]        | **yes** |
| vascular | 200 | 8.9844      | [12, 22]        | no      |
| algal    | 10  | 88.3162     | [35, 55]        | no      |
| algal    | 20  | **62.4490** | [35, 55]        | **no**  |
| algal    | 40  | 44.1581     | [35, 55]        | yes     |

- Lives in: `experiments/q1_crossover/crossover.csv`
- Command: `python3 experiments/q1_crossover/run.py` (exits 0)
- Produced by the code whose commit the file's own `git_sha` header names
  (identical across every committed CSV) (see _A note on the CSV provenance headers_)

### 3. Q2 produced no answer, and the reason is the finding

Q2 asked what sets the outer limit once photosynthesis follows an
empirically-anchored temperature response instead of an extrapolated Q10. It never
got to answer: **its own held-out gate failed and the run refused to report
limits.**

| anchor            | observed response | required window | verdict |
| ----------------- | ----------------- | --------------- | ------- |
| f(278.15 K, 5 °C) | 0.3939            | [0.60, 0.70]    | FAIL    |
| f(273.15 K, 0 °C) | 0.2424            | [0.30, 0.40]    | FAIL    |

The temperature response was parameterised only by `t_min` and `t_opt`; the two
literature rate anchors were deliberately held out so they could not be fitted to.
They were then missed **by factors of 1.2–1.8×** — 0.3939 falls short of its
[0.60, 0.70] window by 1.52× at the near edge and 1.78× at the far one, and
0.2424 falls short of [0.30, 0.40] by 1.24× and 1.65× — because the declared
`t_opt = 298.15 K` is a mesophyte optimum while the anchors describe cold-adapted
tissue. (Earlier drafts of this page said "roughly a factor of two", which
overstates every one of those four ratios.) The runner exits **2**, writes no `limits.csv`, and prints
`Do NOT tune t_opt to pass`. That instruction was followed: Q2 stands as a failed
gate, and Q2b was registered as a separate successor question rather than Q2 being
quietly re-tuned until it passed.

- Lives in: `experiments/q2_thermal/gates.csv` and `RESULTS.md`
- Command: `python3 experiments/q2_thermal/run.py` (exits **2**, by design)
- Produced by the code whose commit the file's own `git_sha` header names
  (identical across every committed CSV) (see _A note on the CSV provenance headers_)

### 4. The wall is a spectral filter, not an attenuator — so the vessel is unbuilt (Q3)

Q1, Q2 and Q2b all model photosynthesis at a _vacuum_ equilibrium temperature.
Water's saturation pressure at those temperatures is 882 Pa (algal sphere, 5.16 °C)
and 18 kPa (lamina, 57.82 °C) against ~0 ambient, so **there is no liquid phase** —
every one of those questions silently assumed a containment vessel that was never
modelled. Q3 was **specified** to design it — and never reached
pre-registration, because the work of specifying it falsified its own premise
first (see the headline above, and `CHANGELOG.md`). Two results came out of that
specification, and both changed what the earlier questions mean:

**(a) The vessel sets the temperature; the organism does not.** This is the
settled part, and the sub-result that answered it — "does a contained organism's
temperature still follow `T_eq`?" — is _no_: the wall does.

The _formula_ first given for it has since been superseded by this project's own
optics, and it is quoted here with that correction attached. For a
**shortwave-transparent**, IR-opaque wall of `N` shells,
`T_interior = (N + 1)^0.25 · T_eq`, with `sqrt(N + 1)` the distance restoring the
bare optimum — one shell taking the algal sphere from 5.16 °C to 57.82 °C, 1.0 AU
to 1.41421 AU. **But a pressure-bearing ice wall is not shortwave-transparent**: it
transmits only 16–23% of solar energy, because NIR is 53% of TSI and ice absorbs
it. The correct form is `(1 + τ)^0.25 · T_eq`, and the familiar one is its τ = 1
case (`docs/bio_grounding_2026-09-02.md` §13 S7). At the measured τ (0.26–0.34) one
shell gives **21.8–26.5 °C, not 57.82 °C**. (From the unrounded τ = 0.2609–0.3429
of `bio_grounding` §13; the rounded 0.26–0.34 printed here gives 21.72–26.29 °C.)

The same correction reaches the degeneracy. "Adding one IR-opaque shell and
halving `area_ratio` are the same operation, identical to 5.7 × 10⁻¹⁴ K" is **true
only at τ = 1** — at a measured τ the two differ by 31–36 K (§14). That agreement
compared two expressions computing the same assumption. What survives is the
qualitative point, and it is the one that matters here: `sim/thermal.py` defines
`area_ratio` as pure geometry, so every registered `area_ratio` silently asserted
_uncontained_.

**(b) A scalar attenuation coefficient for the wall is a category error.** Grounded
against Warren & Brandt's 2008 primary ice optical-constants table, the PAR
absorption coefficient spans **a factor of 701** — 0.00074 /m at 400 nm to
0.52061 /m at 700 nm. (The ratio is taken from the unrounded coefficients,
`4π·m_im/λ` at the table's own `m_im` of 2.365 × 10⁻¹¹ and 2.900 × 10⁻⁸, giving
700.69 → 701. Dividing the two 5-dp figures printed here instead gives 703.5;
the difference is the rounding in this line, not in the result. Producer:
`tools/extract_ice_k.py`, which asserts its parse count — it needs the source
table fetched first, per the curl in its header, as the table is third-party and
not redistributed here. Working: `docs/bio_grounding_2026-09-02.md` §9.) An ice wall is a blue-pass filter that strips exactly the red
band chlorophyll _a_ uses. One number cannot express that, which is why **no vessel
is modelled in this release** and why the explorer offers no wall-thickness input.

The wall's load-bearing verdict — whether strength and transparency ever collide at
a radius worth modelling — is **UNRESOLVED, not settled**: the first answer was
computed by dividing wood's tensile strength by ice's absorption coefficient, two
grounded numbers that describe no single material, and it was wrong by ~53× in the
direction that flattered the conclusion. Recomputed consistently, the answer flips
inside the registered pressure bracket.

- Lives in: `docs/superpowers/specs/2026-09-04-q3-pressure-vessel-design.md` and
  `docs/bio_grounding_2026-09-02.md` §§9–12
- Answered analytically; no runner
- Answered at `1d9cea5` (the S5 commit); released in `v1.0.0` = `4d4d8a7`

---

## What holds

### 5. The vessel has a window, and both registered edges held (Q4)

Q4 asked whether any sphere of ice, sized to hold its own self-consistent vapour
pressure, keeps its interior liquid and still passes the declared photon floor, and
where that window closes. Both predictions were written by hand into
`experiments/q4_vessel/prereg.yaml` (md5 `d8707a66…`, committed alone at `ab1030e`)
before any runner existed, and both **held**:

| prediction | band | measured | binding | verdict |
| --- | --- | --- | --- | --- |
| P1 `r_close(10 km, σ)` | [1.19, 1.27] AU | 1.2049 / 1.2303 / 1.2543 AU (σ 0.7 / 1.5 / 3.1 MPa) | FREEZE ×3 | **HELD** |
| P2 `R_window(1.10 AU, 0.7 MPa)` | [60, 300] km | 95.55 km (FREEZE counterfactual 532.6 km) | OPAQUE | **HELD** |

Gates A (T_eq 278.31 K) and C (611.654 Pa at the triple point; 882.22 Pa regression)
passed. BURST and BOIL held on the auto path at all 59,691 grid nodes (a violation
would have been exit 2). The control law, the `central` variant, both `f_floor` arms and
all eight Fresnel-arm rows reproduce the prereg's printed digits with the expected
binding in every row, including the two the prereg flagged: the (ii)-vapour row
flips P2's binding to FREEZE (78.39 km, OPAQUE 102.28 km), and the (ii)-water row puts
OPAQUE (109.76 km) and FREEZE (111.56 km) in one bracket, decided by the smallest root.
One row sits outside the prereg's edge tolerance as written: the `f_floor` 0.50
OPAQUE crossing, 10.584 km against the printed 10.6 km, a delta of −0.016 km against a
tolerance of 1e-3 × 10.6 = 0.011 km. The prereg prints that row to 0.1 km, coarser than
its own tolerance, so the row matches its printed digits and misses the tolerance; it
is an unregistered arm and moves no verdict. The census of the grid (first violated:
FREEZE 52,816, OPAQUE 394, STARVE 0, HELD 6,481) equals `tools/q4_hand_rows.out`.

What the pass means, and does not: under the declared shell law without reflectance,
the vessel lives only in a thin band between the ice-melt door (1.038 AU) and about
1.2 AU at 10 km, and the Fresnel arm moves P1's σ 0.7 edge outside the band on three
of its four combinations, exactly as registered. The declaration carries that cost.

- Lives in: `experiments/q4_vessel/RESULTS.md`, `edges.csv`, `sweep.csv`; figures in
  `experiments/q4_vessel/figures/`
- Produced by: `python3 experiments/q4_vessel/run.py` (exits 0, ~40 s on 3 workers)

**The vascular crossover prediction held.** At the registered default `k = 100`,
r\* = **12.7058 AU**, inside the pre-registered [12, 22] AU. The calibration gate
passed for both classes: vascular compensation irradiance 6.9519 µmol m⁻² s⁻¹ in
[5.3, 9.0], algal 0.4918 in [0.0, 1.0]
(`experiments/q1_crossover/calibration.csv`).

**That hit carries less information than the algal miss does**, and the repository
says so. The calibration gate constrains `r_d` at 1 AU, and r\* follows from `r_d`
— so the two are not independent: some of each registered band was already decided
before the sweep ran. `experiments/q1_crossover/RESULTS.md` works this out under
_"How much of each prediction the gate had already decided"_, **but its numbers are
pre-S5**, and unlike the crossovers they cannot be recovered by rescaling: the
bands are fixed while the reachable interval shrank by 7.16%, which moves the
percentages non-linearly. Recomputed against the release code:

|                                                           | RESULTS.md (pre-S5) | release code          |
| --------------------------------------------------------- | ------------------- | --------------------- |
| vascular reachable r\*                                    | [11.89, 15.81] AU   | **[11.04, 14.68] AU** |
| share of gate-admissible `r_d` giving r\* inside [12, 22] | 96.2%               | **66.4%**             |
| algal floor on r\*                                        | 47.02 AU            | **43.65 AU**          |
| share of [35, 55] unreachable                             | 60.1%               | **43.3%**             |

The reading softens but does not reverse. Two-thirds of the gate-admissible
vascular range still lands inside the registered band, so the vascular hit remains
substantially pre-decided — it is no longer "close to forced". On the algal side
**43.3% of the registered band was unreachable before the sweep ran**, so the miss
still carries more information than the hit does.

- Lives in: `experiments/q1_crossover/reachability.csv`, which carries these four
  figures at full precision (11.043318 / 14.680400 / 66.4143% / 43.654467 /
  43.2723%) together with the gate-admissible `r_d` intervals they come from
- Command: `python3 tools/derive_q1_reachability.py`
- Method: invert the calibration gate for the `r_d` interval a gate-passing
  organism could have had, then evaluate `crossover_distance_for(n_grid=200)` —
  the prereg's own declared grid — across it, holding every other registered
  value fixed. The share is solved for, not counted off a grid: the one wrong
  digit in this table's history (43.66 for 43.65) came from a `linspace` scan
  whose points never landed on the endpoint.
- Control: the scan reproduces r\*(`r_d`=0.65, k=100) = 12.7058 and
  r\*(`r_d`=0.24, k=20) = 62.4490, matching `crossover.csv` exactly. The script
  asserts this before writing.

**A 1.16× error in the PAR fraction was found and corrected, and no verdict moved.**
`PAR_FRACTION` was 0.45, an unsourced assumption that exceeds even the AM1.5G
_surface_ value; the measured AM0 400–700 nm fraction of TSI is **0.3879**. The
correction (S5) applies unconditionally to Q1, Q2 and Q2b. Because r\* is a
_distance_ it scales as exactly `sqrt(0.3879/0.45) = 0.9284396`, while the
compensation irradiance is an _irradiance_ and does not depend on PAR at all — so
`calibration.csv` and both `gates.csv` are unchanged to the byte, every r\* moved
by 7.16%, and **all six Q1 verdicts and all five Q2b verdicts stand as they were**.

---

## A provenance note: older prose predates that correction

The committed CSVs are current. **Some committed prose is not**, and it is
labelled rather than rewritten, per this repository's convention of bannering
superseded claims instead of editing them away:

- `experiments/q1_crossover/RESULTS.md` quotes the pre-S5 crossovers
  (13.6851 / 19.3537 / 9.6769 / 95.1233 / 67.2623 / 47.5616 AU). Multiply any of
  them by 0.9284396 to get the current value (the last digit can differ by one:
  the pre-S5 figures are themselves rounded to 4 dp). No verdict in that table changes.
- `experiments/q2b_adapted/RESULTS.md` pastes a pre-S5 run's stdout, in which the
  light limit reads 75.434 AU; it is now 70.036 AU. It was never binding either way.
- `docs/ROADMAP.md`'s summary paragraph quotes 13.69 and 67.26 AU.

### A note on the CSV provenance headers

**Repaired in 1.0.1 — this section now records a closed defect.** Through 1.0.0
every committed CSV carried a provenance header whose **`git_sha` line named a
commit whose code cannot produce the file**. `crossover.csv` said
`git_sha=fc6ba42…`, but `git show fc6ba42:sim/physiology.py` still has
`PAR_FRACTION = 0.45` and would produce 13.6851 AU, not the 12.7058 in the file.
The cause: the runners were re-run with the S5 edit in the working tree while
`HEAD` was still at the parent commit, and `git_sha()` records `HEAD`, not the
tree it ran against. The other half of the header was already correct — the
`physiology_md5`, `organism_md5` and `prereg_md5` lines described the files as they
actually were (`af16830e…` is `sim/physiology.py` at `1d9cea5`, not at `fc6ba42`) —
so the header was internally contradictory, and the md5s resolved it.

For 1.0.1 all three runners were re-run under Python 3.13.2 with numpy 2.3.5 /
scipy 1.16.3, and the regenerated CSVs committed. Every committed CSV now carries
the **same** `git_sha`, naming the commit the runners actually executed at, so
**reproduce from the commit the header names**.

**The data came back byte-identical.** Against 1.0.0, the entire diff in every
file is provenance:

| files                                   | changed lines | which                              |
| --------------------------------------- | ------------- | ---------------------------------- |
| the three Q1 CSVs, and Q2's `gates.csv` | 2 each        | `git_sha`, `written`               |
| the three Q2b CSVs                      | 3 each        | `git_sha`, `written`, `prereg_md5` |

Not a data row among them. The Q2b files carry one extra line because
`experiments/q2b_adapted/prereg.yaml` gained a **comment block** in this release
(the fix for a citation pointing at an unshipped working note), which moves the
file's md5 without changing a single registered value. `physiology_md5`,
`organism_md5` and `thermal_md5` did not move anywhere.

Two residues, stated rather than hidden:

- **A CSV cannot name the commit that contains it**, because committing it changes
  that commit's SHA. `git_sha` names the code the runner _executed_; nothing under
  `sim/` changes between that commit and the release, so the named tree does
  reproduce the file.
- **That SHA has to stay reachable.** Regenerating a CSV and then amending or
  rebasing the commit it named orphans it — the SHA resolves in the one working
  clone and nowhere else, which is worse than naming the wrong commit. This
  happened once during 1.0.1 and was caught by review, not by the suite: the
  regenerate-exactly guards exclude the `git_sha` line by design, so they are
  structurally blind to it. `tests/test_derived_csvs.py::test_provenance_sha_is_a_real_reachable_commit`
  now asserts every committed CSV's `git_sha` is a commit object and an ancestor
  of `HEAD`. The working rule: **regenerate the CSVs last, once the commit shape
  is settled.**

**The check behind that claim:** re-running all three runners regenerates every
committed CSV with **byte-identical data** — only the provenance header (its
`git_sha` and timestamp) moves. Verified by hand on 2026-09-10 and again on
2026-09-11 during the re-run above, and continuously by
`tests/test_runner.py::test_committed_csvs_regenerate_exactly`, which re-runs Q1
into a temp directory and diffs every line except those two against what is
committed. The commands are in _Reproduce_ below.

---

## Still open

From the unchecked items in `docs/ROADMAP.md`'s checklist. The first is quoted
verbatim; the second and third are abridged, and the roadmap is the authority:

- 🔴 **NEXT QUESTION — the pressure vessel, promoted from "out of scope" to
  PRECONDITION (2026-09-03).** _"An organism at free radiative equilibrium in
  vacuum cannot photosynthesise… Open: what containment holds liquid water at
  distance r; what it costs in carbon, mass and absorbed light; and — the one that
  decides whether the existing thermal model survives — does a CONTAINED organism's
  temperature still follow T_eq, or does the vessel set it?"_ The third
  sub-question is answered (the vessel sets it); the first two are not.
- **Ground each science-spine item with a real number and a citation.** One of two
  targets closed. The algal compensation-irradiance floor is **still not grounded**
  — the right paper was identified but its tables proved unreachable, and the failed
  routes are recorded in `docs/bio_grounding_2026-09-02.md` §8 so the next attempt
  starts elsewhere.
- **CONDITIONAL on the pressure-vessel question — register the band in the quantity
  the gate can check.** The algal gate needs a _lower_ bound on `I_c`; with a
  unicellular organism (`leaf_mass_ratio = 1.0`) that floor is sufficient, because
  `r* = sqrt(C / I_c)` exactly and a floor on `I_c` becomes a ceiling on `r*`.

One more open item is recorded here rather than in the checklist, because it
reaches the shipped questions: **S2 — `sim/physiology.py` delivers a flat,
unattenuated top-of-atmosphere PAR scalar to an organism that the pressure-vessel
finding requires to sit behind a blue-pass wall.** S5 removed a 1.16× error from
that number; the remaining overstatement is a further 1.2× to 5×10⁵× depending on
wall thickness, and it is untouched. The frozen experiments stay frozen.

---

## Reproduce

```bash
git clone https://github.com/musharna/dyson-tree && cd dyson-tree
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'          # python 3.13.2 exactly; numpy 2.3.5, scipy 1.16.3, PyYAML 6.0.3
python -m pytest -q              # 149 passed

python3 experiments/q1_crossover/run.py    # exits 0
python3 experiments/q2_thermal/run.py      # exits 2 -- the gate fails, by design
python3 experiments/q2b_adapted/run.py     # exits 0
python3 experiments/q4_vessel/run.py       # exits 0
python3 tools/derive_q2b_candidates.py     # the two classify_limit tables
python3 tools/derive_q2b_floor_response.py # the response at the thermal floor
python3 tools/derive_q1_reachability.py    # the gate-reachability scan
git status --porcelain experiments/        # headers move; `git diff` on the data rows is empty

python3 tools/make_fixtures.py   # regenerate web/fixtures.json from the Python model
tools/build_site.sh              # build the published page into site/
python3 tools/smoke_page.py      # headless browser checks (needs playwright + chromium)
```

**Python 3.13.2 exactly**, not just 3.13: the committed CSVs record the
interpreter in their provenance header, and the regenerate-exactly guards diff
every header line except `git_sha` and `written` — so on any other 3.13.x patch
release six tests fail on the `# python=` line alone, with identical data.

The browser explorer at <https://musharna.github.io/dyson-tree/> runs a port of the
same model (`web/model.js`). It is pinned to the Python by `web/fixtures.json`
through `tests/test_parity_js.py`, whose crossover values are checked against
`experiments/q1_crossover/crossover.csv` itself — so the page cannot show a number
the repository's own committed results do not.

The figures are R + ggplot2: `Rscript experiments/q1_crossover/plot.R`,
`Rscript experiments/q2b_adapted/plot.R`, `Rscript experiments/q4_vessel/plot.R`.

Code is MIT; documents and figures are CC-BY-4.0. See `LICENSE`, `LICENSE-docs`
and `docs/THIRD-PARTY.md`.
