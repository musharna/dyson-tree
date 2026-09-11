# Dyson tree

**Can a tree grow in space?** This repository builds the smallest honest carbon
budget for one photosynthetic organism at a distance `r` from the Sun — light in,
respiration out — registers what it expects before each run, and reports what
happened. Three questions were registered and run; **exactly one of their
predictions held.** One missed its band, one was falsified outright, and one was
never tested because its own held-out gate failed. A fourth question was specified
and then falsified before registration: it asked for a single attenuation
coefficient for a wall whose absorption spans a factor of 701 across PAR, which is
a quantity that cannot exist. The falsifications are the result worth reading.

- **Explore the model in your browser:** <https://musharna.github.io/dyson-tree/>
  — pick a photosystem class, a distance and a half-saturation constant, and watch
  net carbon cross zero. The pre-registered bands are drawn beside the measured
  crossovers, marked as predictions rather than results.
- **Read the findings:** **[`docs/FINDINGS.md`](docs/FINDINGS.md)** — falsifications
  first, each with its number, the file it lives in, and the command that produces it.

Licence: code (`sim/ tools/ tests/ web/ experiments/**/*.py`) is **MIT**;
documents, figures, results and pre-registrations (`docs/**`,
`experiments/**/{RESULTS.md,prereg.yaml,*.csv,figures}`) are **CC-BY-4.0**. See
`LICENSE`, `LICENSE-docs`, `docs/THIRD-PARTY.md` and `CITATION.cff`.

## Run it

```bash
git clone https://github.com/musharna/dyson-tree && cd dyson-tree
python3 -m venv .venv && . .venv/bin/activate
pip install -e '.[dev]'
python -m pytest -q          # 139 passed
tools/build_site.sh          # build the published page into site/
```

**Python 3.13.2 exactly**, not just 3.13. The committed CSVs carry a provenance
header that records the interpreter, and the regenerate-exactly guards diff every
header line except `git_sha` and `written` — so on any other 3.13.x patch release
**six tests fail on the `# python=` line alone**, with identical data. That is the
guard working as designed, not a broken checkout; the failure message shows a
one-line diff.

Optional, for the parts beyond the test suite:

| For                                        | You need                    |
| ------------------------------------------ | --------------------------- |
| the 9 JS parity tests (`test_parity_js`)   | **Node ≥ 18**               |
| `python3 tools/smoke_page.py` (147 checks) | **Playwright + Chromium**   |
| the figures (`plot.R`)                     | **R 4.3.3 + ggplot2 4.0.2** |

Then the registered runs and the derived tables:

```bash
python3 experiments/q1_crossover/run.py    # exits 0
python3 experiments/q2_thermal/run.py      # exits 2 -- the gate fails, by design
python3 experiments/q2b_adapted/run.py     # exits 0
python3 tools/derive_q2b_candidates.py     # the two classify_limit tables
python3 tools/derive_q2b_floor_response.py # the response at the thermal floor
python3 tools/derive_q1_reachability.py    # the gate-reachability scan
git status --porcelain experiments/        # headers move; the data rows do not
```

Every registered question ships a pre-registration written before its runner, a
calibration gate that must pass before any result is reported, and CSVs carrying a
provenance header (git sha, source md5s, numeric-stack versions).
`tests/test_runner.py::test_committed_csvs_regenerate_exactly` re-runs the
experiment and diffs it against what is committed, so the record cannot drift away
from the code that claims to produce it. `tests/test_derived_csvs.py` does the same
for the `tools/derive_*.py` tables.

## Layout

    docs/         ROADMAP.md is canonical for "what phase, what's next";
                  FINDINGS.md is the result; dated design notes live here too
    sim/          the model itself
    experiments/  one directory per registered question: prereg.yaml (written
                  before the run), run.py, RESULTS.md and the committed CSVs
    tests/        guards; every claim the model makes should have one
    tools/        probes, derivations, one-off measurement scripts
    web/          the static explorer (no build step, no CDN, no dependency)

`docs/ROADMAP.md` stays canonical for "what phase, what's next";
`docs/RELEASE-1.0.md` is the release evidence log and
`docs/RELEASE-1.0.1.md` the one for this release.

---

# Design record

Everything below is the design history — the brief this was built against and the
decisions taken along the way. It is kept because the reasoning is the point, but
nothing below is needed to run the code or read the result.

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

- Brainstorm and write a spec before any new mechanic — Q1 went through that and
  the spec is the binding authority for what the runner does.
- Decide what to simulate individually versus as a field, and what the observer
  actually perturbs, before writing the model.
- Ground every borrowed biological mechanism in a real number and a source before it
  becomes a load-bearing design primitive. The science spine above is exactly the kind of thing that
  degrades into flavour text if it is not checked against real numbers.
  `leaf_mass_ratio` is the standing example: uncited, invisible to the
  calibration gate, and wide enough on its own to decide whether Q1's algal
  prediction lands inside its registered band (`RESULTS.md` records `a_max` as
  the second such parameter, and the one the algal gate constrains least).

The prior-art question was checked on 2026-09-01 —
`docs/prior_art_2026-09-01.md`, re-run on the biology rather than only the
name — and is no longer open.
