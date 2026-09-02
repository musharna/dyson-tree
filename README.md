# Dyson tree

A sim-zoo design track. **Scaffolded 2026-09-01; the design has NOT been done
yet** — this directory exists so development can start, not because anything is
settled. Tracked as task #10.

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

## ⚠️ The open decision, flagged at filing and still open

**The designer and the colony economy are TWO LOOPS. Build one first.** They have
different tick rates, different player verbs and different failure modes, and a
design that tries to be both at once usually ends up being neither. Nothing here
commits to which one goes first — that is the first thing the design track has
to settle.

## Before writing code here

Run the design properly rather than starting from whatever is easiest to
implement:

- `superpowers:brainstorming` before any implementation — the design track is the
  work, and the code is downstream of it.
- `deep-sim-design` for what to simulate individually versus as a field, and for
  what the observer actually perturbs.
- `bio-grounding` before any borrowed biological mechanism becomes a load-bearing
  design primitive. The science spine above is exactly the kind of thing that
  degrades into flavour text if it is not checked against real numbers.

⚠️ Prior scouting exists and is a **hypothesis, not state** — re-verify before
building on it: `~/.claude/projects/-home-mjarnold/memory/bio_sim_candidates_grounded_2026-07-31.md`
carries a note that a Dyson-tree literature truth exists but that the search
probed the NAME rather than the biology. Treat that as "the prior art question is
open", not as a finished review.

## Layout

Mirrors `_pm/`, which is the sibling project furthest along:

    docs/         ROADMAP.md is canonical for "what phase, what's next";
                  pre-registrations and results live here, dated
    sim/          the model itself
    experiments/  runners that ask one registered question each
    tests/        guards; every claim the model makes should have one
    tools/        probes, gradients, one-off measurement scripts
    _scratch/     untracked working area
