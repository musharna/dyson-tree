# Changelog

All notable changes to this project are documented here. This file was created
at the 1.0.0 release and backfills one line per registered question.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

## [1.0.1] — 2026-09-11

A documentation and provenance release, from a post-ship review panel's findings.
**No measured value changed.** `sim/`, every preset, every constant and every
registered prediction are untouched; the committed experiment data is
byte-identical to 1.0.0. What changed is what the repository _says_ about it.

### Fixed

- **CSV provenance headers named a commit whose code cannot produce them.** Every
  header said `git_sha=fc6ba42`, whose `PAR_FRACTION` is still 0.45 and which
  would produce 13.6851 AU rather than the committed 12.7058. All three runners
  were re-run at the 1.0.1 branch point under Python 3.13.2 and the CSVs
  re-committed: **the data came back byte-identical**, the whole diff being
  `git_sha` and `written`, two lines per file. Documented in 1.0.0 as
  unrepairable-within-scope; repaired here.
- **Four sets of numbers in `docs/FINDINGS.md` had no committed producer.** The
  Q2b temperature and light candidates (1.1945 / 70.04 AU) lived in no file —
  `limits.csv` holds only the carbon candidate — and neither did the vascular
  `classify_limit` table, the Gaussian response at the thermal floor, or the
  gate-reachability scan. Each now has one; see _Added_ below.
- **The Q2b falsification was stated unscoped** in `web/index.html`, this file and
  `docs/thermal_premise_retired_2026-09-03.md`. It holds **for the algal class**,
  the only class the run answered; the retired Gate B readmits vascular, where
  carbon binds at Ω = 25 and 30 — where the registered prediction would have held.
- **`docs/FINDINGS.md` said Q3 "was registered".** It was _specified_; its premise
  was falsified before it could be registered, as the same page's headline says.
- **"Missed by roughly a factor of two"** overstated all four of Q2's miss ratios
  (1.24×, 1.52×, 1.65×, 1.78×). Now stated as 1.2–1.8× with the ratios, here and
  in FINDINGS.
- **Stale numbers far from their banner** now carry an inline
  `⚠️ superseded → <value> (S5)` marker at the number itself: `docs/ROADMAP.md`'s
  two Q1 crossovers, and in `experiments/q2b_adapted/RESULTS.md` the light limit,
  the Q1 comparison value, and the whole pre-S5 `outer_au` column of its §4 table —
  which its banner had not covered, naming only the light limit.
- **`(N+1)^0.25 · T_eq` was quoted here without its τ = 1 qualifier.** The general
  form is `(1 + τ)^0.25 · T_eq`; at a pressure-bearing ice wall's measured
  τ = 0.26–0.34 one shell gives 21.8–26.5 °C, not 57.82 °C.
- **The licence partition omitted `experiments/**/prereg.yaml`** in `README.md`,
which `LICENSE-docs` includes.
- **`docs/RELEASE-1.0.md` listed a defect that had already been fixed** before the
  release flip (`README.md` referencing `_pm/`). Both occurrences are annotated.

### Added

- **`tools/derive_q2b_candidates.py`** → `experiments/q2b_adapted/candidates.csv`:
  all three candidate distances per class and Ω, including the vascular rows Gate B
  keeps out of `limits.csv`, labelled as such.
- **`tools/derive_q2b_floor_response.py`** →
  `experiments/q2b_adapted/floor_response.csv`: the Gaussian response and net
  carbon at the thermal floor. Two rows on purpose — FINDINGS' +0.0197 holds at
  the 1.1945 AU it prints, while the full-precision floor gives +0.019783
  (0.0198 at 4 dp); the gap is rounding of the input distance.
- **`tools/derive_q1_reachability.py`** →
  `experiments/q1_crossover/reachability.csv`: the gate-reachability scan
  (66.4143% / 43.2723% / [11.043318, 14.680400] AU / 43.654467 AU).
- **`tools/check_q2b_curve_shape.py`** — reproduces the `curve_shape` table
  registered in `q2b_adapted/prereg.yaml`, which had cited an internal working
  note that is not in this repository. The existing tests cover those branches
  with synthetic curves, so they pinned the selector, not the table.
- **`tests/test_derived_csvs.py`** — regenerate-exactly guards for the three
  derived CSVs, plus checks that each header names its producer and that no
  source md5 has gone stale. 8 tests; 131 → 139.
- **`README.md` now has a "Run it" block** — install, test and build, with the
  version requirements stated: Python **3.13.2 exactly** (on any other 3.13.x
  patch six tests fail on the `# python=` header line alone, with identical
  data), Node ≥ 18 for the 9 parity tests, Playwright + Chromium for
  `tools/smoke_page.py`, R 4.3.3 + ggplot2 4.0.2 for the figures. The design
  history moved below the fold under "Design record".
- **`docs/superpowers/plans/README.md`** — what those files are, and that the
  tool names in them are the author's private tooling.
- **`docs/RELEASE-1.0.1.md`** — this release's evidence log. `docs/RELEASE-1.0.md`
  gains a banner saying it is an evidence log, not a findings document.

### Changed

- `docs/FINDINGS.md`'s rule "every number names the file it lives in and the
  command that produces it" now says what is actually true: it holds for every
  computed number, and Q3 — answered analytically, with no runner — is named as
  the exception rather than left as a false universal.
- The **factor of 701** for ice PAR absorption is **kept, and sourced**. It is
  correct: it comes from the unrounded coefficients (700.69), not from dividing
  the two 5-dp figures printed beside it (which give 703.5). FINDINGS now says so
  and names `tools/extract_ice_k.py`.
- `LICENSE` gains a one-line note pointing at `LICENSE-docs` for the
  documentation partition; `CITATION.cff` declares both licences and is validated
  against the CFF 1.2.0 schema.

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
interior temperature at `(N+1)^0.25 · T_eq` ⚠️ _that form holds only at **τ = 1**
(a shortwave-transparent wall); the general form is `(1 + τ)^0.25 · T_eq`, and a
pressure-bearing ice wall measures τ = 0.26–0.34, giving 21.8–26.5 °C for one
shell rather than 57.82 °C — see `docs/FINDINGS.md` and
`docs/bio_grounding_2026-09-02.md` §13 S7_, and adding a shell is
indistinguishable from halving `area_ratio` ⚠️ _also τ = 1 only; at the measured
τ the two differ by 31–36 K (§14)_. Its central input — a scalar wall
attenuation `k` — does not exist: grounded against Warren & Brandt 2008, PAR
absorption spans a factor of 701, so the wall is a spectral filter. Needs
re-registering.

### Q2b — adapted optimum — registered 2026-09-02, run, PREDICTION FALSIFIED

`experiments/q2b_adapted/`. Predicted that carbon binds the outer limit. It does
not: temperature binds at every Ω, at a hard 1.1945 AU floor — **for the algal
class, the only class the run answered**. The gate that excluded the vascular
class was later retired as a category error
(`docs/thermal_premise_retired_2026-09-03.md`). That retirement leaves the algal
falsification intact — it compared two quantities both computed inside the model
— but it readmits the vascular class, where the same `classify_limit` gives
carbon as the binding limit at Ω = 25 and 30, i.e. where the registered
prediction would have HELD. The falsification stands for algal; whether it
generalises is open. See `docs/FINDINGS.md` and
`experiments/q2b_adapted/candidates.csv`.

### Q2 — thermal limit — registered 2026-09-02, run, GATE FAILED

`experiments/q2_thermal/`. The held-out response anchors were missed by factors
of 1.2–1.8× (see `docs/FINDINGS.md` for the four ratios), the runner exited 2,
and no limits were reported. `t_opt` was not
tuned to make it pass; Q2b was registered as a successor instead.

### Q1 — carbon crossover — registered 2026-09-02, run, ONE OF TWO PREDICTIONS HELD

`experiments/q1_crossover/`. Vascular held at 12.7058 AU inside [12, 22];
algal failed at 62.4490 AU against [35, 55]. `RESULTS.md` also records how much
of each prediction the calibration gate had already decided. Those percentages
are pre-S5 and do not rescale (the bands are fixed while the reachable interval
shrank 7.16%); recomputed at the release code, **66.4%** of the gate-admissible
vascular range produces a hit and **43.3%** of the algal band was unreachable
before the sweep ran. See `docs/FINDINGS.md`, "What holds". Since 1.0.1 those
figures live in `experiments/q1_crossover/reachability.csv`
(`python3 tools/derive_q1_reachability.py`).

### S5 — PAR fraction corrected — 2026-09-06

`PAR_FRACTION` 0.45 → 0.3879 (measured AM0 400–700 nm fraction of TSI). Applies
unconditionally to Q1, Q2 and Q2b. Every crossover distance scales by
`sqrt(0.3879/0.45) = 0.9284396`; every compensation irradiance is unchanged
(irradiances do not depend on the PAR fraction); **no verdict moved.**

[1.0.1]: https://github.com/musharna/dyson-tree/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/musharna/dyson-tree/releases/tag/v1.0.0
