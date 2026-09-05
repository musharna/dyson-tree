# Dyson tree — ROADMAP

**Canonical for "what phase, what's next".** If a later document supersedes this
one, banner this file and redirect from it in the same commit — a superseding
roadmap that nobody discovers is worse than no roadmap.

## Where this stands

> ⚠️ **READ `docs/thermal_premise_retired_2026-09-03.md` FIRST.** Q2b's Gate B is
> RETIRED as a category error (it compared a vacuum-radiative temperature against
> Earth-thermodynamic optima), and the vapour-pressure argument in that note makes
> the long-deferred PRESSURE VESSEL a precondition for the whole modelling line
> rather than a later extension. Q2b's falsification is unaffected. Nothing is
> retracted; the reading changes.

**Loop A exists and has produced one measured number; Q2 is registered and run,
but its own gate blocked it from producing a second; Q2b (its successor) is
registered and run, and DID produce a limit — for one class, with its own
registered prediction falsified.** Scaffolded 2026-09-01; a carbon-budget model
(loop A, light-only, tissue temperature fixed) lives under `sim/`. Q1 is
registered and run (`experiments/q1_crossover/RESULTS.md`): the vascular
default-k prediction held at 13.69 AU; the algal default-k prediction failed at
67.26 AU against [35, 55]. Q2 (radiative equilibrium + a held-out
temperature-response gate, `experiments/q2_thermal/RESULTS.md`) replaced the
earlier "heating cost" framing; it is registered and run, but Gate 2 (held-out
response anchors) FAILED — the declared `t_opt` of 298.15 K is a mesophyte
optimum while the gate anchors are for cold-adapted tissue. No sweep, no
limits, and no answer to "what binds" were produced; see RESULTS.md for the
implied `t_opt` diagnosis and what would resolve it.

Q2b (`experiments/q2b_adapted/RESULTS.md`) replaced the fitted `t_opt` with one
_predicted_ from geometry (an organism's optimum = its own equilibrium
temperature at a 1 AU home distance), and gated that prediction per class
against independent literature optima instead of fitting it. Gate A passed
(278.3112 K). Gate B passed for **algal** (predicted 5.16 °C vs. measured
5.0–7.0 °C) and **failed for vascular by 28 K** (predicted 57.82 °C vs.
measured 29.4 °C, most likely because this model's `emissivity=1, albedo=0`,
no-transpiration assumptions run a flat lamina far hotter than a real leaf —
not a refutation of the adaptation premise). Vascular was excluded from the
sweep entirely: it has no row in `sweep.csv` or `limits.csv`, only a FAIL row
in `gates.csv`. Algal alone produced an answer: net carbon crosses zero
1.2120–2.5301 AU out (a 2.09× range across the swept, unsourced Ω=10–30 K
grid), and at every Ω the tightest of the three candidate limits is
**temperature** (a fixed 1.1945 AU thermal floor, inside the carbon crossing
at every Ω) — **not** the registered prediction of `carbon`. That prediction
is FALSIFIED, the first registered prediction in this project that was both
falsifiable and actually tested to a verdict.

## The first decision, before anything else

⚠️ **Designer loop or colony loop — build ONE first.** Settled 2026-09-02: A
first — the WHY is on the checklist entry below.

|              | organism designer (A)                 | multi-generational colony (B)         |
| ------------ | ------------------------------------- | ------------------------------------- |
| player verb  | specify a plant against a budget      | steer a population across generations |
| tick         | one design, evaluated                 | many generations                      |
| failure mode | the thing you built cannot stand/live | the colony's economy runs down        |

Both are backed by the same physiology (C), and the failure museum (D) is
supposed to EMERGE from budget arithmetic in either — it is not authored content.
That is the property to protect when choosing.

## The science spine — what has to be real

These are the three places where the sim can be wrong in a way that matters, so
each needs a number and a source before it becomes a mechanic:

1. **Cometary element budget** — organic-C-rich (~50% by mass), refractory
   fraction near-CI-chondritic, Ca-depleted; P present, K unmeasured
   (`docs/prior_art_2026-09-01.md` §3). Element scarcity is NOT a free
   constraint; not modelled in Q1.
2. **Biological pressure vessel** — tensile strength vs wall thickness at ~1 atm.
   A materials problem with a right answer. **Tensile input GROUNDED 2026-09-03**
   (`docs/bio_grounding_2026-09-02.md` §7): wood tension-parallel data are genuinely
   sparse, so the canonical reference's own conservative substitute — modulus of
   rupture, 45-139 MPa across 111 species-rows, median 80 — is what the sizing uses.
   That replaces a _compressive_ 300 MPa proxy and makes the wall 3.75x thicker
   (0.6250 m vs 0.17 m at p=10 kPa, r=10 km).
3. **Light compensation point under 1/r² insolation** — where photosynthesis
   stops paying for the respiration that sustains it, as a function of distance
   from the sun.

**Microgravity architecture is GATED by NASA GeneLab** (15 Arabidopsis
spaceflight experiments) — the architecture follows those measurements rather
than being chosen and then justified.

## Checklist

- [x] Brainstorm the design — 2026-09-02, spec at
      `docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md`
- [x] Settle designer-loop vs colony-loop — A first (2026-09-02). WHY: B needs
      A's budget trusted underneath it; A is the cheapest path to a measured
      answer, and light (spine item 3) turned out to be the binding constraint,
      which A can treat as a swept input.
- [ ] 🔴 **NEXT QUESTION — the pressure vessel, promoted from "out of scope" to
      PRECONDITION (2026-09-03).** An organism at free radiative equilibrium in
      vacuum cannot photosynthesise: water's saturation pressure is 882 Pa at the
      algal sphere's 5.16 C and 18 kPa at the lamina's 57.82 C against ~0 ambient,
      so there is no liquid phase. Q1, Q2 and Q2b all model photosynthesis at a
      vacuum equilibrium temperature, which requires the containment Q1 deferred.
      Open: what containment holds liquid water at distance r; what it costs in
      carbon, mass and absorbed light; and — the one that decides whether the
      existing thermal model survives — does a CONTAINED organism's temperature
      still follow T_eq, or does the vessel set it?
      See `docs/thermal_premise_retired_2026-09-03.md` section 4.
      **SPEC DRAFTED 2026-09-04 —
      `docs/superpowers/specs/2026-09-04-q3-pressure-vessel-design.md`.** The third
      sub-question is ANSWERED analytically and needed no simulation: the vessel sets
      it. For an SW-transparent, IR-opaque wall, `T_interior = (N+1)^0.25 * T_eq`, so
      one shell takes the algal sphere 5.16 C -> 57.82 C and the distance restoring
      the optimum is `sqrt(N+1)`, i.e. 1.0 -> 1.41421 AU. That answer exposed a
      DEGENERACY in the three shipped questions: adding one IR-opaque shell and
      halving `area_ratio` are the SAME operation (identical to 5.7e-14 K), yet
      `sim/thermal.py:28` defines `area_ratio` as pure geometry — so every registered
      4.0 also silently asserted UNCONTAINED, and Q2b's algal band [3.630, 4.311] is
      not a statement about shape alone. Nothing is invalidated; what changes is what
      those questions MEASURED. Q1/Q2/Q2b stay frozen. The spec reframes the
      remaining two sub-questions into one: `R_max = 2*sigma*|ln tau_min|/(k*p)`, the
      radius past which no wall is both strong enough to hold liquid water and clear
      enough to pass light. **BLOCKER CLEARED SAME DAY, AND IT FALSIFIED THAT
      QUESTION — `bio_grounding` §9.** `k` is grounded from Warren & Brandt 2008's
      primary data table (public at atmos.uw.edu even though the paper is paywalled;
      the data was taken, not the paper). Two results: (1) `k` is NOT A SCALAR — it
      spans x701 across PAR, 0.00074 /m at 400 nm to 0.52061 /m at 700 nm, so the
      wall is a SPECTRAL FILTER that strips the red band chlorophyll a uses and
      leaves the blue; a scalar `k` cannot express that, the same root class as the
      `area_ratio` degeneracy above. (2) My declared band [0.1, 5.0] /m was 135x too
      high at the blue end, so `R_max` is 1.3e3-9.9e4 km against an assumed 10 km —
      **strength and transparency DO NOT COLLIDE at any radius worth modelling.**
      Real ice attenuates ~24x harder via dust SCATTERING (Ackermann 2006), still
      leaving R_max >= 1345 km. What binds is wall impurity content, which is not
      groundable for a hypothetical organism and cannot be fixed by finding a better
      PDF. **Q3 needs RE-REGISTERING**: either against mass/carbon cost (framing B,
      no longer moot) or as this falsification with the spectral-filter result as the
      finding. Had the variance decomposition been registered on my band, this would
      have been a retraction instead of a correction.
      **THAT FALSIFICATION IS ITSELF PARTLY WITHDRAWN, 2026-09-04 — `bio_grounding` §10.**
      §9 computed `R_max` from §7's WOOD tensile strength (80 MPa) divided by §9's ICE
      absorption coefficient. No material in the project's grounding has both properties,
      so the quotient describes neither, and it is wrong by ~53x in the direction that
      flattered the conclusion. Ice tensile strength is now grounded at 0.7-3.1 MPa
      (Petrovic 2003 via Hirata 2022, green OA, at one remove). Recomputed consistently,
      **framing A is UNRESOLVED, not falsified: its answer flips inside the registered
      pressure bracket.** At 10 kPa the red band collides at 1.2-7.4 km, BELOW the assumed
      10 km, across the whole grounded sigma range; at the 882 Pa saturation floor it does
      not collide, but the margin is 1.4x, not the "14x to 5 orders of magnitude" §9
      claimed. What decides framing A is `p` and `sigma` — NOT `k`, the input the spec
      blocked on and the only one that got grounded. The spectral-filter result, the 135x
      band error, the `area_ratio` degeneracy and the contained-temperature result all
      stand unaffected. **New rule (§10): a grounded input is not safe merely because it is
      grounded; a PAIR of grounded inputs must be shown to describe the SAME OBJECT before
      they may be combined. Every check in §9 tested one input at a time, and the error
      lived only in the pairing.**
      **PAIRING SWEEP RUN 2026-09-04 — `bio_grounding` §11. Four findings, three of them new
      classes.** ⚠️ **S1: THE REGISTERED PRESSURE BRACKET IS SELF-INCONSISTENT.** `p ∈ [882 Pa,
      10 kPa]` takes its floor from the saturation pressure at the UNCONTAINED temperature —
      but this spec's own settled result is that containment is MANDATORY and the vessel SETS
      the temperature, which raises it. One shell needs **18.02 kPa, 1.8x above the bracket
      top**; two need 78.9 kPa. At the self-consistent 18 kPa, framing A's red-band `R_max` is
      **0.93-4.10 km against an assumed 10 km — it binds decisively.** ⚠️ **S2, and it reaches
      the SHIPPED questions:** `sim/physiology.py` feeds a flat full-spectrum PAR scalar to an
      `a_max` grounded on full-spectrum measurements, but a contained organism sits behind a
      BLUE-PASS wall — Q1/Q2/Q2b model a light field the wall they now require would not
      deliver. Unlike the `area_ratio` degeneracy this would change the NUMBERS. Recorded, NOT
      resolved, and the frozen experiments stay frozen. ⚠️ S3: §9's diffusive-slab caveat
      divides PURE bubble-free ice absorption by DUST-LADEN glacial ice scattering. ✅ S4
      CLOSED: Q2b's adaptation premise had no ledger row and no DOI anywhere in the repo;
      Scafaro 2023 and June 2004 are now verified (29.4/32.7 °C, 49 species and the Ω
      definition all quoted verbatim from the gold-OA text, matching `sim/thermal.py` exactly)
      — the residual is the ORGANISM: a soybean-derived Gaussian and a 49-vascular-C3-species
      result supply the premise applied to a UNICELLULAR alga. **The sweep's own lesson: THE
      UNIT OF VALIDATION IS THE EXPRESSION, NOT THE INPUT — citation checks, the honesty ledger
      and ghostcite all answer YES for both halves of every defect found.**
      **S2 SIZED 2026-09-04 — `bio_grounding` §12 — AND SIZING IT BROKE ONE OF §11's OWN
      CLEARANCES.** ⚠️⚠️ **S5: `PAR_FRACTION = 0.45` IS NOT A TOP-OF-ATMOSPHERE NUMBER.**
      `irradiance()`'s docstring says top-of-atmosphere; the measured AM0 PAR energy fraction
      (ASTM G173-03) is **0.3879**, and 0.45 exceeds even the AM1.5G SURFACE value of 0.4297.
      A 5772 K blackbody independently returns 0.3663. **PAR is overstated 1.160x at every
      distance in Q1, Q2 AND Q2b, unconditionally** — no wall, no Q3 and no re-framing needed
      for it to be wrong; an iso-flux distance threshold moves sqrt(1.160) = 1.077x, ~7% in r.
      All three preregs carry 0.45 as a bare `# assumption` with no source. **§11 had CLEARED
      this exact triple** ("all three describe the solar spectrum at top of atmosphere") — that
      clearance is now WITHDRAWN, and it was produced by reading three labels rather than
      measuring them, which is the failure §11 exists to name. `PHOTONS_PER_J = 4.57` survived
      the same test (re-derived 4.553, 0.4%). **New rule (§12): "THE SAME OBJECT" IS A
      MEASUREMENT, NOT A LABEL — where the object is quantitative, check a pairing by
      RE-DERIVING BOTH INPUTS FROM IT; anything less checks the declarations against each
      other, which they always pass.** ✅ **S2 itself is now sized: a factor, not an order of
      magnitude.** At the self-consistent 18.02 kPa an ice wall is 29-129 m thick and delivers
      **18.7-34.9% of the assumed PAR photons** (50% cutoff at 470-516 nm), so S5+S2 together
      overstate the light field **3.3x-6.2x**. Milder than §10's 2.26e-4 red-band figure
      implies, because MOST PAR PHOTONS ARE NOT IN THE RED BAND — reading a per-wavelength
      extreme as an integrated quantity would have overstated S2 by 4 orders of magnitude.
      Two limits: this is PURE-ICE ABSORPTION ONLY, hence an UPPER BOUND on transmission (S3's
      scattering gap bears directly, ~24x harder), and it is a PHOTON COUNT, not a rate — a
      chlorophyll-weighted figure needs an in vivo action spectrum the project has not
      grounded, and inventing one would manufacture the defect being measured.
      Tool: `tools/size_par_filter.py`, four positive controls.
      **§11's SURVIVING CLEARANCES RE-CHECKED BY MEASUREMENT 2026-09-04 — `bio_grounding` §13.
      THREE OF FOUR DID NOT SURVIVE.** ⚠️⚠️ **S7: THE CONTAINED-TEMPERATURE RESULT
      `T_interior = (N+1)^0.25 * T_eq` ASSUMES AN SW-TRANSPARENT WALL, AND THIS PROJECT'S OWN
      ICE OPTICS FALSIFY THAT.** NIR (700-4000 nm) carries **53% of TSI** and ice absorbs it
      hard, so a pressure-bearing ice wall transmits only **16-23% of SOLAR ENERGY** — it is an
      absorber, not a greenhouse pane. Correct form is **`T_interior = (1+tau)^0.25 * T_eq`**;
      the published formula is the tau=1 special case (positive control: at tau=1 it returns
      57.82 C exactly). tau depends on thickness, thickness on p, p on T, T on tau — a FIXED
      POINT, which is exactly what S1 said a re-registered Q3 must solve. Converged, the
      self-consistent pressure is **2.6-3.5 kPa — INSIDE the registered [882 Pa, 10 kPa]**,
      5.2-6.9x BELOW S1's 18.02 kPa. ⚠️⚠️ **S1'S VERDICT IS THEREFORE WITHDRAWN: THE BRACKET IS
      NOT SELF-INCONSISTENT.** S1's MECHANISM stands (its floor is still p_sat at the
      UNCONTAINED T); its magnitude and verdict do not. Direction is robust — tau is pure-ice
      absorption, so any impurity pushes tau, T and p FURTHER INSIDE the bracket. **Framing A is
      now SPLIT BY ICE STRENGTH**: R_max 21.4 km (3.1 MPa), 11.9 km (1.5), 6.40 km (0.7) — binds
      only at the weak end. ⚠️ **S6: `a_max` HAS NO RECORDED TEMPERATURE.** The Westerband
      deposit has no leaf-temperature column while standardising `Vcmax25` to 25 C in the same
      file; Q1 uses a_max unscaled at 293 K, Q2 as the rate at/above t_opt, Q2b as the PEAK rate
      at a geometry-derived t_opt — three anchors for one number, differing 1.27-8.65x (algal)
      across the registered omega grid. **The rule §13 buys, and it BREAKS §11's own: A PAIRING
      NEED NOT APPEAR IN ANY EXPRESSION.** No line of code contains both halves of S7 — it lives
      between a docstring assumption and a data table two sections away, which is why §§9-12,
      all of which looked at expressions, could not see it. **THE UNIT OF VALIDATION IS
      ULTIMATELY THE OBJECT.** Tools: `check_greenhouse_transparency.py`, `check_amax_anchor.py`.
      **DEGENERACY RE-CHECKED AT A MEASURED tau, 2026-09-04 — `bio_grounding` §14.** The
      "adding one IR-opaque shell == halving `area_ratio`, identical to 5.7e-14 K" claim ABOVE
      ⚠️ **HOLDS ONLY AT tau = 1.** With a measured wall the two operations differ by **31-36 K**
      (halving takes the algal sphere to 57.82 C; a real shell takes it to 21.8-26.5 C).
      ⚠️ **The degeneracy does NOT vanish — it RESCALES:** T depends on `area_ratio/(1+tau)`, so
      a CONTAINED SPHERE presents at an effective `area_ratio` of **2.98-3.17, not 2.0** — the
      confound is real but ~2.7x smaller in temperature than recorded. ⚠️⚠️ **AND A CONTAINED
      SPHERE FALLS ENTIRELY BELOW Q2b's REGISTERED BAND [3.630, 4.311]**; landing inside it
      would need a TRUE `area_ratio` of 4.58-5.79, more extreme than a sphere. So the claim
      "Q2b's algal band is not a statement about shape alone" is **REPLACED**: it IS a statement
      about shape, CONDITIONAL on containment — the two are separable, and were inseparable only
      under tau = 1. ⚠️ **The "two shells need 78.9 kPa" figure is WITHDRAWN** (from 3^0.25*T_eq
      = 93.13 C; at measured tau the interior is 25.67-32.80 C, and shells SATURATE fast because
      each passes only a quarter of what reaches it). **The lesson: A NUMERICAL IDENTITY
      CONFIRMED TO 14 DECIMAL PLACES IS STILL ONLY AS TRUE AS THE PREMISE BOTH SIDES COMPUTE.**
      The 5.7e-14 K agreement measured floating-point arithmetic, not the world — the project's
      oldest root class (a test that cannot fail) reappearing as a VERIFICATION that cannot
      fail. It is now §14's positive control precisely because it never could have been anything
      else. Tool: `tools/check_area_ratio_degeneracy.py`.
- [ ] Ground each science-spine item with a real number and a citation, via
      `bio-grounding`; verify citations per the project's citation chain.
      **2026-09-03 pass: 1 of 2 targets closed.** Spine item 2's tensile input is
      GROUNDED (§7, above). Spine item 3's `I_c` floor is STILL NOT GROUNDED — the
      right paper was identified (Yang 2020, CC-BY gold OA, reports `I_c` for seven
      species) but its tables proved unreachable: Springer redirects to an auth wall,
      the DA MCP finds no fetchable full text, and it is not in EuropePMC. Recorded
      as a failed attempt with the routes tried in
      `docs/bio_grounding_2026-09-02.md` §8, so the next attempt starts elsewhere —
      an interlibrary/PDF copy of that one paper is the shortest path.
      **Started 2026-09-02 for the two parameters the Q1 gate cannot see —
      `docs/bio_grounding_2026-09-02.md`.** `leaf_mass_ratio` is now BOUNDED
      (LMF 0.20-0.80 excluding adult trees, Poorter & Sack 2012), which puts
      vascular r\* in [7.62, 17.79] AU against a registered [12, 22] — the
      grounded range extends BELOW the band rather than confirming it.
      `a_max` CLOSED 2026-09-02 from a CC-0 DATASET (Westerband et al. 2022,
      Dryad, 675 measurements / 530 species / 67 sites) after every paper proved
      paywalled: Asat median 8.75, max 29.52 umol CO2 m-2 s-1. The vascular
      `a_max` = 10.0 sits at the empirical MEDIAN. But the ceiling turned out
      NOT to be the fix — see the algal-gate item below. Spine items other than
      these two are untouched.
- [x] Check the prior-art question — done 2026-09-01, see
      `docs/prior_art_2026-09-01.md`: label-null confirmed (12 exact hits, 1
      mention) AND re-run on the biology (nearest = myco-architecture + BLSS
      crop models). Spine item 1 was rewritten accordingly on 2026-09-02
      (refractory dust near-CI-chondritic, Stephan 2008; P detected, Altwegg
      2016); K remains unmeasured.
- [x] First registered question (Q1, carbon crossover vs distance) —
      `experiments/q1_crossover/prereg.yaml`, results in `RESULTS.md`
- [x] **Algal organism SETTLED 2026-09-02: UNICELLULAR.** Grounding found the
      preset incoherent — its gate source (Richardson et al. 1983) is about
      unicellular microalgae while its `leaf_mass_ratio: 0.8` was justified as
      a THALLUS (a macroalga). Chose unicellular: the gate citation is already
      correct, so the fix costs one number — LMR becomes 1.0 and stops being a
      free parameter, pinned by structure. Algal r\* moves to 75.43 AU, further
      outside Q1's [35, 55]; accepted, since that band is already a reported
      miss and Q2 re-registers. WHY not macroalgal: it needed a new
      compensation-point source AND left LMR free needing its own citation.
      Binding on the NEXT registration — Q1's prereg stays frozen.
      See `docs/bio_grounding_2026-09-02.md` §3.
- [ ] **CONDITIONAL on the pressure-vessel question above — this constrains a
      carbon crossover computed at a FIXED tissue temperature, which the vapour-
      pressure finding shows requires containment. The methodological half is live
      regardless and is the part to carry forward: REGISTER THE BAND IN THE
      QUANTITY THE GATE CAN CHECK.**

      **The algal gate needs a LOWER bound on I_c — and once the organism is
      unicellular that floor is SUFFICIENT.** For lmr = 1.0, r\* = sqrt(C/I_c)
      exactly (C = 2798.4852), verified at 9 (a_max, k) pairs: r\* becomes a
      pure function of the quantity the gate measures, so the gate stops being
      blind and a floor on I_c IS a ceiling on r\*. Exact consequence: the
      existing ceiling I_c <= 1.0 already forces r\* >= 52.9007 AU, so the
      registered [35, 55] band was reachable only over [52.90, 55] —
      **89.5% of it was unreachable before the sweep ran** (worse than the
      60.1% measured at the old lmr = 0.8). Only the floor's VALUE is still
      unsourced: 14C PI compilations structurally cannot supply it (14C
      measures uptake, not respiration; 0.35% of the largest open compilation
      samples the light-limited end). Needs O2-based P-R data on microalgal
      cultures. NEXT REGISTRATION SHOULD REGISTER THE BAND IN I_c, NOT r\*.
      Superseded framing (kept for the record):
      Found 2026-09-02: at the MAXIMUM Asat across 530 species the algal gate
      still PASSES (I_c = 0.1626 <= 1.0) and returns NO crossover inside
      [0.5, 100] AU. A ceiling on `a_max` was necessary but not sufficient —
      the defect is the gate's floor of 0.0, which cannot exclude an
      arbitrarily efficient organism, and efficiency is what pushes r\* past
      the horizon. Fix: take a real microalgal compensation-point floor from
      Richardson, Beardall & Raven 1983, already the algal gate's own source.
      See `docs/bio_grounding_2026-09-02.md` §4. It is uncited, structurally
      invisible to the Q1 calibration gate (which solves against LEAF
      respiration while the answer divides by it), and a lever wide enough to
      decide the verdict on its own — at 0.5 instead of 0.8 the algal r\*
      lands inside its registered band. Q2's heating cost scales with the same
      non-photosynthetic mass fraction, so it inherits the problem.
      `experiments/q1_crossover/RESULTS.md`, "The uncited assumption that sets
      the scale".

- [x] **`t_opt` grounding CLOSED — finding retained, action superseded. The
      literature result below stands on its own and is worth keeping; the "next
      step" it proposed (a concave response + per-class `t_opt`) was BUILT as Q2b,
      whose gate is now retired. The remaining gap it names — no `T_opt` for
      cold-adapted VASCULAR tissue — is moot for gating purposes: gating a
      vacuum-radiative model against terrestrial optima is a category error at any
      level of grounding. See `docs/thermal_premise_retired_2026-09-03.md` §1.**

      **`t_opt` GROUNDED 2026-09-02, and it moved the diagnosis — see
      `docs/bio_grounding_2026-09-02.md` §4d.** Cold-climate photoautotrophs have
      HIGH optima, not low: Antarctic mosses 19.0-26.3 C (ETRmax, six named
      species) and 20-30 C for net CO2 assimilation (Perera-Castro et al. 2020);
      Antarctic lichen soil crusts 5 and 7 C, temperate 17 C (Colesie et al.
      2014). The LINEAR response needs t_opt in [12.0, 13.7] C to satisfy both
      held-out anchors, and NO measured optimum falls in that window - the
      lichens sit below it, the mosses above. **So the functional form is the
      defect, not t_opt**, which is what the spec said Gate 2 would diagnose and
      NOT what I predicted before the run. A re-registered Q2 needs a concave
      response (beta or Arrhenius-with-deactivation) and a per-class t_opt.
      Still ungrounded: T_opt for cold-adapted VASCULAR tissue - both sources
      are non-vascular.

- [x] **Q2 CLOSED 2026-09-03 with no answer, and it will not be reopened in its
      registered form.** Its follow-up ("source `t_opt`, re-register") was done —
      `t_opt` was grounded 2026-09-02 and Q2b WAS that re-registration — and Q2b's
      own gate has since been retired as a category error
      (`docs/thermal_premise_retired_2026-09-03.md`). Left as a record of a gate
      that failed honestly, not as outstanding work — the question was asked and
      the gate blocked the answer.

      Record: `experiments/q2_thermal/prereg.yaml`,
      `run.py`, results in `experiments/q2_thermal/RESULTS.md`. Gate 1
      (thermal physics at 1 AU) passed at 278.31 K. Gate 2 (held-out rate
      anchors for cold-adapted tissue at 5 °C and 0 °C) FAILED both anchors
      (0.3939 vs [0.60, 0.70]; 0.2424 vs [0.30, 0.40]) against the declared
      mesophyte `t_opt` of 298.15 K — no sweep ran, so no limits table and no
      "what binds" answer exist. RESULTS.md computes the `t_opt` band the
      anchors imply ([285.15, 286.82] K) as a diagnosis only, explicitly not
      adopted. Next step: source `t_opt` for cold-adapted tissue from the
      literature and re-register — DONE, and superseded twice; see above. The
      frozen prereg was never tuned to pass, and stays frozen.

- [x] **Q2b registered and run — COMPLETE FOR ONE CLASS, not two.**
      `experiments/q2b_adapted/prereg.yaml`, `run.py`, results in
      `experiments/q2b_adapted/RESULTS.md`. `t_opt` is no longer fitted or a
      declared assumption: it is predicted from geometry (equilibrium
      temperature at the 1 AU home distance) and gated per class against an
      independent literature optimum. Gate A passed (278.3112 K). Gate B
      **passed for algal** (predicted 5.16 °C vs. measured 5.0–7.0 °C,
      Colesie et al. 2014) and **failed for vascular by 28 K** (predicted
      57.82 °C vs. measured 29.4 °C, Scafaro et al. 2023) — most likely this
      model's `emissivity=1, albedo=0`, no-transpiration assumptions running a
      flat lamina too hot, not a refutation of the adaptation premise; those
      assumptions were NOT adjusted to force a pass. Vascular was excluded
      from the sweep: it has no row in `sweep.csv` or `limits.csv`, only its
      Gate B FAIL row in `gates.csv`.

      **The algal pass is NOT robust, and this line stated it unqualified
      until 2026-09-03 — `experiments/q2b_adapted/RESULTS.md` §3 disclosed it
      all along.** Gate B is parameter-free in `t_opt`, but
      `t_opt = T_eq(1 AU, area_ratio)` is _totally_ determined by
      `area_ratio` once `r_home_au`, `emissivity` and `albedo` are fixed: the
      algal window [0.0, 12.0] °C admits only `area_ratio` in [3.630, 4.311]
      — a band 0.681 wide around the registered 4.0. And Colesie's measured
      organisms are lichen-dominated Antarctic soil crusts: flat mats, whose
      radiative geometry is a lamina (`area_ratio` 1-2), not a sphere. At
      `area_ratio=2` — the geometry its own citation is closest to — algal
      predicts 57.82 °C and misses the window's upper edge by 45.82 K,
      against vascular's 23.42 K past its own edge, about 1.8x further out.
      (The "28 K" above is the gap to the measured optimum, a different
      quantity.) So the pass holds only at the registered geometry, and the
      class that passed is the one whose registered geometry LEAST matches
      its own citation. `area_ratio` stays frozen at 4.0 and the window is
      untouched — this is a caveat on the gate that passed, not a re-scoring
      of it. **Algal answered the registered
      question**: net carbon crosses zero at 1.2120–2.5301 AU across the
      swept, unsourced Ω=10–30 K grid (a 2.09× range — low confidence in any
      single number), and the tightest of the three candidate limits is
      **temperature** (a fixed 1.1945 AU floor) at every Ω, not `carbon`.
      **The registered prediction (`predicted_binding_limit.algal: carbon`)
      is FALSIFIED** — the first registered prediction in this project both
      falsifiable and actually tested to a verdict. Körner's rate anchors
      were retired here (no Ω in [1, 200] °C satisfies them jointly with the
      grounded 29.4 °C optimum), not re-used as a gate. Next step, if
      pursued: vascular needs either a transpiration/albedo term added to the
      thermal model (a bigger change than this registration's scope) or a
      re-registration that accepts the 28 K miss and asks a different
      question of that class.
