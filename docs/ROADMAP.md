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

## Not yet done

- [x] Brainstorm the design — 2026-09-02, spec at
      `docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md`
- [x] Settle designer-loop vs colony-loop — A first (2026-09-02). WHY: B needs
      A's budget trusted underneath it; A is the cheapest path to a measured
      answer, and light (spine item 3) turned out to be the binding constraint,
      which A can treat as a swept input.
- [ ] Ground each science-spine item with a real number and a citation, via
      `bio-grounding`; verify citations per the project's citation chain
- [x] Check the prior-art question — done 2026-09-01, see
      `docs/prior_art_2026-09-01.md`: label-null confirmed (12 exact hits, 1
      mention) AND re-run on the biology (nearest = myco-architecture + BLSS
      crop models). Spine item 1 was rewritten accordingly on 2026-09-02
      (refractory dust near-CI-chondritic, Stephan 2008; P detected, Altwegg
      2016); K remains unmeasured.
- [x] First registered question (Q1, carbon crossover vs distance) —
      `experiments/q1_crossover/prereg.yaml`, results in `RESULTS.md`
- [ ] Q2 (declared): carbon cost of holding tissue temperature against
      radiative loss; second crossover
