# Executor brief: M1a0, the ready half (spectral table + hand rows + tests). NO prereg.

Repo `/home/<user>/dyson-tree`, master `25c5f37`. Authority: the spec
`docs/superpowers/specs/2026-09-12-northstar-design.md` — §3 (vessel model, registry table
:232-258), §4 (failure modes, census :278-310), §6 (pre-registration, rows :520-536, table checks
:620-646), §8 M1a0 (:665-695). Read those sections fresh before writing anything; the spec wins
over this brief wherever they differ.

## Scope (this half only)
1. `tools/extract_ice_k.py` → extended (or a new `tools/make_spectral_table.py` that it calls) to
   write `sim/spectral_table.csv`: ASTM G173 native grid, 2,002 rows, 280–4000 nm; columns
   `lambda_nm, k_per_m, E_AM0, n_ph`; `k` by log-space interpolation of `m_im` as
   `tools/check_greenhouse_transparency.py:62-63` does (selection window 250–4200 nm);
   `E_AM0` = ASTM column 2; `n_ph = E_AM0·λ/(hc)`; provenance header with both sources' md5 +
   byte size, the word `trapezoid`, the producer's commit, and the pvlib commit
   `2d0ed71e1308293b3081979404f8e90f2f2dde1e`. Formatter pinned: `%.10e`, `\n` line ends.
2. Sources (gitignored, fetch to repo root; NEVER `git add` them):
   `curl -sL https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat -o iop2008.dat`
   `curl -sL https://raw.githubusercontent.com/pvlib/pvlib-python/2d0ed71e1308293b3081979404f8e90f2f2dde1e/pvlib/data/ASTMG173.csv -o ASTMG173.csv`
   Expected: ASTMG173.csv md5 starts `b31870bd`, 57,708 B; iop2008.dat md5 starts `cf5f76d5`,
   16,514 B. If either differs, STOP and report — do not proceed on a different source.
3. `docs/THIRD-PARTY.md:35`: the mutable `main` URL → the pinned commit URL.
4. Tests (`tests/test_spectral_table.py`): table digest pinned; row count 2,002; strictly
   increasing λ 280→4000; four pinned `k` rows 0.00074 /m @400 nm, 0.05230 @550, 0.38623 @680,
   0.52061 @700 (tolerance: the spec's printed digits); `test_regenerate_spectral_table` re-runs
   the producer and compares PARSED values at rtol 1e-12, SKIPS (pytest.skip, never pass) when
   either source is absent.
5. `tools/q4_hand_rows.py` + committed output `tools/q4_hand_rows.out`: reproduces EVERY §6 row
   (registered P1 ×3, P1 normal control, P2 OPAQUE/FREEZE, P2 arms 0.50/0.10, P2 normal control,
   P2 `central` variant, the EIGHT Fresnel arm rows keyed by `n_interior × thermal_reflectance`)
   and the §4 census (four counts per law over the 197×101×3 = 59,691 grid, STARVE-first 0/0,
   min STARVE margin +1.826 / +1.874 µmol at its node, grid minimum f_photon 0.0579 / 0.0667,
   1 AU/10 km/σ 0.7 → 294.37 K / 0.391 / +9.12). Reads ONLY `sim/spectral_table.csv` + existing
   `sim/thermal.py`, `sim/physiology.py`, `sim/organism.py`. Imports nothing from `sim/vessel.py`
   (does not exist yet — do NOT create it; that is M1a).
6. `tests/test_hand_rows.py`: `test_reproduce_hand_rows` recomputes every row + the census from the
   committed table and matches the spec's printed digits; the literal SMELL test (no float literal
   in `q4_hand_rows.py` equals a printed table value).
7. NOT in scope: `experiments/q4_vessel/prereg.yaml` (HELD by the user until a further audit),
   `sim/vessel.py`, `web/`. Do not create them.

## Physics reference (verified scratch, read-only, for cross-checking your numbers)
`/home/<user>/.claude/jobs/<job>/tmp/v5-dyson/v5_slab.py` (+ `v5_slab.out`): the slab
reflectance `R_slab(kt)` integral, solar weighting, the eight arm rows. `v5_physics.py`/`.out` and
`v5_gridscan.py`/`.out`: P1/P2 rows, census. These are the verifier's scripts that produced the
spec's digits; your `q4_hand_rows.py` must reproduce them independently from the table (you may
read them; you may not copy printed values into your code).

## Rules
- Branch `m1a0-table` off master; small commits; NO push; no attribution lines in commits.
- TDD: write each test, see it FAIL for the stated reason, then make it pass. Report the failing
  output in your final report for at least the four-pinned-rows test and the smell test.
- Every inline python gets `signal.alarm(...)`. Grid census may take minutes — fine, but run it
  once and cache the result in the `.out`.
- Run `pytest -q` at the end; it must be green (149 existing + yours).
- Stay inside `/home/<user>/dyson-tree`. Do not touch any other repo or the memory dir.
- Final report: commits (hashes + one line each), every numeric row with spec-vs-computed
  side by side, test counts, anything that did NOT reproduce (say so plainly; do not fudge a
  digit to make it match — a mismatch is a finding).
