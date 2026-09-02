# Dyson tree — ROADMAP

**Canonical for "what phase, what's next".** If a later document supersedes this
one, banner this file and redirect from it in the same commit — a superseding
roadmap that nobody discovers is worse than no roadmap.

## Where this stands

**Loop A exists and has produced one measured number.** Scaffolded 2026-09-01; a
carbon-budget model (loop A, light-only, tissue temperature fixed) lives under
`sim/`. Q1 is registered and run (`experiments/q1_crossover/RESULTS.md`): the
vascular default-k prediction held at 13.69 AU; the algal default-k prediction
failed at 67.26 AU against [35, 55]. Q2 (heating cost) is declared, not built.

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
      `a_max` has NO ceiling yet: every candidate source was paywalled, so no
      number was recorded. Spine items other than these two are untouched.
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
      See `docs/bio_grounding_2026-09-02.md` §3. It is uncited, structurally
      invisible to the Q1 calibration gate (which solves against LEAF
      respiration while the answer divides by it), and a lever wide enough to
      decide the verdict on its own — at 0.5 instead of 0.8 the algal r\*
      lands inside its registered band. Q2's heating cost scales with the same
      non-photosynthetic mass fraction, so it inherits the problem.
      `experiments/q1_crossover/RESULTS.md`, "The uncited assumption that sets
      the scale".
- [ ] Q2 (declared): carbon cost of holding tissue temperature against
      radiative loss; second crossover
