# Dyson tree — ROADMAP

**Canonical for "what phase, what's next".** If a later document supersedes this
one, banner this file and redirect from it in the same commit — a superseding
roadmap that nobody discovers is worse than no roadmap.

## Where this stands

**Loop A exists and has produced one measured number; Q2 is registered and run,
but its own gate blocked it from producing a second.** Scaffolded 2026-09-01; a
carbon-budget model (loop A, light-only, tissue temperature fixed) lives under
`sim/`. Q1 is registered and run (`experiments/q1_crossover/RESULTS.md`): the
vascular default-k prediction held at 13.69 AU; the algal default-k prediction
failed at 67.26 AU against [35, 55]. Q2 (radiative equilibrium + a held-out
temperature-response gate, `experiments/q2_thermal/RESULTS.md`) replaced the
earlier "heating cost" framing; it is registered and run, but Gate 2 (held-out
response anchors) FAILED — the declared `t_opt` of 298.15 K is a mesophyte
optimum while the gate anchors are for cold-adapted tissue. No sweep, no
limits, and no answer to "what binds" were produced; see RESULTS.md for the
implied `t_opt` diagnosis and what would resolve it.

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
   A materials problem with a right answer.
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
- [ ] Ground each science-spine item with a real number and a citation, via
      `bio-grounding`; verify citations per the project's citation chain.
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
- [ ] **The algal gate needs a LOWER bound on I_c — and once the organism is
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
- [ ] **Q2 registered and run, but NOT complete — the question was asked and
      the gate blocked the answer.** `experiments/q2_thermal/prereg.yaml`,
      `run.py`, results in `experiments/q2_thermal/RESULTS.md`. Gate 1
      (thermal physics at 1 AU) passed at 278.31 K. Gate 2 (held-out rate
      anchors for cold-adapted tissue at 5 °C and 0 °C) FAILED both anchors
      (0.3939 vs [0.60, 0.70]; 0.2424 vs [0.30, 0.40]) against the declared
      mesophyte `t_opt` of 298.15 K — no sweep ran, so no limits table and no
      "what binds" answer exist. RESULTS.md computes the `t_opt` band the
      anchors imply ([285.15, 286.82] K) as a diagnosis only, explicitly not
      adopted. Next step: source `t_opt` for cold-adapted tissue from the
      literature and re-register; do not tune the frozen prereg to pass.
