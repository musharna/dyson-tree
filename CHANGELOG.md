# Changelog

All notable changes to this project are documented here. This file was created
at the 1.0.0 release and backfills one line per registered question.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.0] — 2026-09-10

### Added

- **Browser explorer** (`web/`, published to <https://musharna.github.io/dyson-tree/>):
  a single page running a JS port of the carbon-budget model. Preset, distance
  and half-saturation `k` in; net-carbon curve, crossover, equilibrium
  temperature and compensation irradiance out. No build step, no CDN, no
  dependency. Pre-registered bands are drawn as hatched predictions, never in the
  style of a result.
- **`web/fixtures.json` + `tests/test_parity_js.py`** — the JS port is pinned to
  the Python model per quantity, with declared tolerances, three edge cases, and
  a positive control against the committed `crossover.csv`.
- **`docs/FINDINGS.md`** — the falsifications, first, for a reader who has never
  seen this repository.
- **`docs/RELEASE-1.0.md`** — stage-by-stage release evidence.
- `LICENSE` (MIT), `LICENSE-docs` (CC-BY-4.0), `CITATION.cff`,
  `docs/THIRD-PARTY.md`, `docs/dois.txt`, this changelog, and a GitHub Pages
  workflow.

### Changed

- Superseded numbers in `experiments/q1_crossover/RESULTS.md`,
  `experiments/q2b_adapted/RESULTS.md` and `docs/ROADMAP.md` are now bannered
  with their current values. Per this repository's convention, superseded claims
  are bannered, never rewritten.

## Registered questions, backfilled

### Q3 — the pressure vessel — specified 2026-09-04, PREMISE FALSIFIED

Spec at `docs/superpowers/specs/2026-09-04-q3-pressure-vessel-design.md`. Never
reached pre-registration. Answered analytically: an IR-opaque shell sets the
interior temperature at `(N+1)^0.25 · T_eq`, and adding a shell is
indistinguishable from halving `area_ratio`. Its central input — a scalar wall
attenuation `k` — does not exist: grounded against Warren & Brandt 2008, PAR
absorption spans a factor of 701, so the wall is a spectral filter. Needs
re-registering.

### Q2b — adapted optimum — registered 2026-09-02, run, PREDICTION FALSIFIED

`experiments/q2b_adapted/`. Predicted that carbon binds the outer limit. It does
not: temperature binds at every Ω, at a hard 1.1945 AU floor. Only the algal
class was answered; the gate that excluded the vascular class was later retired
as a category error (`docs/thermal_premise_retired_2026-09-03.md`), which does
not affect the falsification.

### Q2 — thermal limit — registered 2026-09-02, run, GATE FAILED

`experiments/q2_thermal/`. The held-out response anchors were missed by roughly a
factor of two, the runner exited 2, and no limits were reported. `t_opt` was not
tuned to make it pass; Q2b was registered as a successor instead.

### Q1 — carbon crossover — registered 2026-09-02, run, ONE OF TWO PREDICTIONS HELD

`experiments/q1_crossover/`. Vascular held at 12.7058 AU inside [12, 22];
algal failed at 62.4490 AU against [35, 55]. `RESULTS.md` also records how much
of each prediction the calibration gate had already decided: 96.2% of the
gate-admissible range produces a vascular hit, and 60.1% of the algal band was
unreachable before the sweep ran.

### S5 — PAR fraction corrected — 2026-09-06

`PAR_FRACTION` 0.45 → 0.3879 (measured AM0 400–700 nm fraction of TSI). Applies
unconditionally to Q1, Q2 and Q2b. Every crossover distance scales by
`sqrt(0.3879/0.45) = 0.928487`; every compensation irradiance is unchanged
(irradiances do not depend on the PAR fraction); **no verdict moved.**

[1.0.0]: https://github.com/musharna/dyson-tree/releases/tag/v1.0.0
