# Dyson tree — ROADMAP

**Canonical for "what phase, what's next".** If a later document supersedes this
one, banner this file and redirect from it in the same commit — a superseding
roadmap that nobody discovers is worse than no roadmap.

## Where this stands

**Nothing is designed yet.** The directory was scaffolded 2026-09-01 so
development could start; no model exists, no question is registered, no number
has been measured.

## The first decision, before anything else

⚠️ **Designer loop or colony loop — build ONE first.** Filed as the open flag on
task #10 and still open.

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

1. **Cometary element budget** — CHON-rich, P/K/metal-poor. The scarce elements
   are the design constraint; get the composition from a real measurement, not
   from a plausible-sounding ratio.
2. **Biological pressure vessel** — tensile strength vs wall thickness at ~1 atm.
   A materials problem with a right answer.
3. **Light compensation point under 1/r² insolation** — where photosynthesis
   stops paying for the respiration that sustains it, as a function of distance
   from the sun.

**Microgravity architecture is GATED by NASA GeneLab** (15 Arabidopsis
spaceflight experiments) — the architecture follows those measurements rather
than being chosen and then justified.

## Not yet done

- [ ] Brainstorm the design (`superpowers:brainstorming`, then `deep-sim-design`)
- [ ] Settle designer-loop vs colony-loop and record WHY
- [ ] Ground each science-spine item with a real number and a citation, via
      `bio-grounding`; verify citations per the project's citation chain
- [ ] Check the prior-art question — the existing scouting note flags that a
      previous search probed the NAME rather than the biology, so the null is
      not established
- [ ] First registered question + pre-registration, before any runner exists
