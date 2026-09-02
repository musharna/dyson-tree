# Dyson tree

A sim-zoo design track. **Loop A exists and has produced one measured number.**
Scaffolded 2026-09-01; the design was run on 2026-09-02
(`docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md`), and a
carbon-budget model — loop A, light-only, tissue temperature fixed — lives
under `sim/`. Q1 is registered and run: the vascular default-k prediction held
at 13.69 AU, the algal default-k prediction failed at 67.26 AU against
[35, 55]. Read the result and its caveats in
**`experiments/q1_crossover/RESULTS.md`**; `docs/ROADMAP.md` stays canonical for
"what phase, what's next". Q2 (heating cost) is declared, not built. Tracked as
task #10.

## The brief, as filed

In-depth iterative design. **Organism designer (A) + multi-generational colony
(B)**, backed by real physiology (C); a **failure museum (D)** emerges from
budget arithmetic rather than being authored.

**Science spine** — the three things that have to be real for any of it to mean
anything:

- **cometary element budget** — CHON-rich, P/K/metal-poor. What you can build is
  set by what a comet actually contains, and the scarce elements are the
  interesting constraint.
- **biological pressure vessel** — tensile strength against wall thickness at
  ~1 atm. This is a materials problem with a right answer, not a dial.
- **light compensation point under 1/r² insolation** — where photosynthesis stops
  paying for the respiration that sustains it, as a function of distance.

**Microgravity architecture is gated by NASA GeneLab** (15 Arabidopsis
spaceflight experiments). Gated means: the architecture follows the measurements,
not the other way round.

## ✅ The open decision, now settled

**The designer and the colony economy are TWO LOOPS. Build one first.** They have
different tick rates, different player verbs and different failure modes, and a
design that tries to be both at once usually ends up being neither. Settled
2026-09-02: **A first.** B needs A's budget trusted underneath it, A is the
cheapest path to a measured answer, and light (spine item 3) turned out to be
the binding constraint, which A can treat as a swept input. See
`docs/ROADMAP.md` for the reasoning of record.

## Before adding to the model

The design track is the work and the code is downstream of it, so keep the
order:

- `superpowers:brainstorming` before any new mechanic — Q1 went through it and
  the spec is the binding authority for what the runner does.
- `deep-sim-design` for what to simulate individually versus as a field, and for
  what the observer actually perturbs.
- `bio-grounding` before any borrowed biological mechanism becomes a load-bearing
  design primitive. The science spine above is exactly the kind of thing that
  degrades into flavour text if it is not checked against real numbers.
  `leaf_mass_ratio` is the standing example: uncited, invisible to the
  calibration gate, and wide enough on its own to decide whether Q1's algal
  prediction lands inside its registered band (`RESULTS.md` records `a_max` as
  the second such parameter, and the one the algal gate constrains least).

Every registered question ships a pre-registration written before its runner,
a calibration gate that must pass before any result is reported, and CSVs
carrying a provenance header (git sha, source md5s, numeric-stack versions).
`tests/test_runner.py::test_committed_csvs_regenerate_exactly` re-runs the
experiment and diffs it against what is committed, so the record cannot drift
away from the code that claims to produce it.

The prior-art question was checked on 2026-09-01 —
`docs/prior_art_2026-09-01.md`, re-run on the biology rather than only the
name — and is no longer open.

## Layout

Mirrors `_pm/`, which is the sibling project furthest along:

    docs/         ROADMAP.md is canonical for "what phase, what's next";
                  pre-registrations and results live here, dated
    sim/          the model itself
    experiments/  runners that ask one registered question each
    tests/        guards; every claim the model makes should have one
    tools/        probes, gradients, one-off measurement scripts
    _scratch/     untracked working area
