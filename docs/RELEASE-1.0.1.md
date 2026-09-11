# Release 1.0.1 — evidence log

> ℹ️ **This is a release evidence log, not a findings document.** It records what
> was run and what it printed for the 1.0.1 release. It is not the authority on
> any result — that is [`docs/FINDINGS.md`](FINDINGS.md).

Executed against `docs/superpowers/specs/2026-09-11-v1.0.1-plan.md`, a 13-item
punch list from the post-ship review panel, verified by the coordinator against
the released tree at `4d4d8a7`. Commands are pasted with their real output.

**Branch:** `release/1.0.1-rc`, cut from `c239801` (= `origin/master`).
**RC SHA:** `a734813`.

| commit    | contents                                                        |
| --------- | --------------------------------------------------------------- |
| `09a820a` | items 1–5, 10 — derived artifacts, scoped claims, re-run        |
| `a734813` | items 6–9, 11–13 — README, licences, prereg citation, changelog |

## The scope rule this release was held to

> You MAY correct statements, add committed scripts that reproduce an
> already-reported number from committed data, re-run the three experiment
> runners **only** to refresh their provenance headers, fix docs/metadata/links.
> You MAY NOT change `sim/`, presets, constants, pre-registrations, or add inputs
> to the explorer. **A fix changes what is SAID, never what was MEASURED.**

**Held.** `git diff c239801..a734813 --stat -- sim/` is empty. No preset, constant
or registered prediction was touched. The one pre-registration edit is a comment
block in `experiments/q2b_adapted/prereg.yaml` (item 9), which the plan
explicitly directs; no registered value in it changed.

**Every CSV data row is byte-identical to 1.0.0.** Verified by stripping comments
and diffing each committed CSV against its `HEAD` version:

```
$ for f in $(git ls-files 'experiments/**/*.csv'); do
    diff -q <(git show <1.0.0>:"$f" | grep -v '^#') <(grep -v '^#' "$f") >/dev/null \
      || echo "DATA CHANGED: $f"
  done
(no output)
```

## Environment

```
python   3.13.2
numpy    2.3.5
scipy    1.16.3
PyYAML   6.0.3
pytest   9.1.1
node     v18.19.1
gitleaks 8.30.1
ghostcite 0.5.2
```

## Item 5 first — the ordering constraint the plan did not state

Item 1 derives CSVs **from** the experiment CSVs item 5 rewrites, so deriving
first would have baked pre-re-run provenance (`source=… md5=…`) into the new
artifacts. Item 5 was executed first.

All three runners were re-run at `c239801` under the environment above:

```
$ python3 experiments/q1_crossover/run.py     # exit 0
$ python3 experiments/q2_thermal/run.py       # exit 2, by design -- the gate fails
$ python3 experiments/q2b_adapted/run.py      # exit 0
```

The plan's stop condition was "if any data row differs, STOP and hand back". No
data row differed:

```
$ git diff --stat
 experiments/q1_crossover/calibration.csv | 4 ++--
 experiments/q1_crossover/crossover.csv   | 4 ++--
 experiments/q1_crossover/sweep.csv       | 4 ++--
 experiments/q2_thermal/gates.csv         | 4 ++--
 experiments/q2b_adapted/gates.csv        | 4 ++--
 experiments/q2b_adapted/limits.csv       | 4 ++--
 experiments/q2b_adapted/sweep.csv        | 4 ++--
 7 files changed, 14 insertions(+), 14 deletions(-)
```

Two lines per file, both provenance: `git_sha` and `written`. `sweep.csv` alone
is 1200 data rows and contributed none of them.

**One residue, stated rather than hidden.** A CSV cannot name the commit that
contains it, because committing it changes that commit's SHA. `git_sha` names the
code the runner _executed_; nothing under `sim/` changes between that commit and
this one, so the named tree does reproduce the file. That is recorded in FINDINGS'
_A note on the CSV provenance headers_, which now describes a closed defect.

## Item 1 — the four sets of numbers that had no producer

Three derivation tools, each of which **refuses to write a file unless it first
reproduces the committed baseline it is extending**:

| tool                                 | writes                                    | positive controls                                                                                                                                          |
| ------------------------------------ | ----------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `tools/derive_q2b_candidates.py`     | `q2b_adapted/candidates.csv` (10 rows)    | reproduces all 5 `limits.csv` carbon/binding rows; reproduces FINDINGS' vascular table; `binding` is shown to vary; Gate B still passes algal only         |
| `tools/derive_q2b_floor_response.py` | `q2b_adapted/floor_response.csv` (2 rows) | `t_eq` at the floor equals `t_min`; FINDINGS' figures hold at the printed distance; reproduces RELEASE-1.0's round-2 values; response is strictly positive |
| `tools/derive_q1_reachability.py`    | `q1_crossover/reachability.csv` (2 rows)  | reproduces `crossover.csv` at both registered defaults; the gate inversion round-trips; monotonicity asserted, not assumed                                 |

All call the runners' own `build()` / `classify_limit()` / `crossover_distance_for`
rather than reimplementing them.

```
$ python3 tools/derive_q1_reachability.py
control 1 OK -- reproduces crossover.csv at both registered defaults
control 2 OK -- the gate inversion round-trips to the declared I_c
control 3 OK -- r* confirmed monotone decreasing in r_d for both classes
control 4 OK -- reproduces all four figures FINDINGS reports

wrote experiments/q1_crossover/reachability.csv (2 rows)
  vascular  r_d in [0.503324, 0.825688]  reachable r* = [11.043318, 14.6804] AU  66.4143% inside
  algal     r_d in [0.000000, 0.476190]  reachable r* = [43.654467, inf) AU  43.2723% unreachable
```

Every derived header names its producer, its commit, and every source with that
source's md5:

```
# derived_by=tools/derive_q2b_candidates.py
# git_sha=09a820a9659607410e4c37ffc2d6b4ab320831b2
# source=experiments/q2b_adapted/prereg.yaml md5=a7d25919e942f6bdc2894e16f1311c90
# source=experiments/q2b_adapted/limits.csv md5=34ef649b638c5e3fe227141207173fc2
# python=3.13.2 / numpy=2.3.5 / scipy=1.16.3 / written=…
```

### One thing the controls caught that the plan had not

FINDINGS says net carbon at the thermal floor is **+0.0197**. At the
**full-precision** floor (1.194466 AU) it is +0.019783 — **0.0198** at 4 dp. At
the **1.1945 AU FINDINGS actually prints**, it is +0.019725 → 0.0197. FINDINGS is
correct as written; the difference is rounding of the input distance, and it also
explains why `docs/RELEASE-1.0.md`'s round-2 re-review quotes 0.003697 / +0.019725
where a floor-evaluated check gives 0.003703 / +0.019783. `floor_response.csv`
carries **both rows** so this is checkable rather than a thing to take on trust.

### FINDINGS' opening rule

The rule "every number names the file it lives in and the command that produces
it" was still not literally true after the above, because **Q3 was answered
analytically and has no runner**. Per the plan's instruction, the sentence was
softened to state what is true: it holds for every computed number, and Q3 is
named as the exception.

## Items 2–4, 6–13 — per-item disposition

| #   | Item                                        | Disposition                                                                                                                                          |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Q2b candidates + 3 other unsourced numbers  | **Done.** 3 tools, 3 CSVs, 8 new tests. FINDINGS' rule softened re Q3.                                                                               |
| 2   | Scope the falsification to the algal class  | **Done.** `web/index.html`, `CHANGELOG.md`, `thermal_premise_retired` — the last by inline marker, per that file's banner-don't-rewrite rule.        |
| 3   | Inline `⚠️ superseded` markers              | **Done.** ROADMAP ×2; q2b `RESULTS.md` §4 table ×5, plus 75.434 and 67.2623; CHANGELOG's `(N+1)^0.25`. The q2b banner now covers the whole §4 table. |
| 4   | FINDINGS:181 "Q3 was registered"            | **Done.** Now "specified", consistent with the page's own headline.                                                                                  |
| 5   | Provenance re-run                           | **Done.** Byte-identical; see above.                                                                                                                 |
| 6   | README install/test/build block             | **Done.** Run-it block, versions, design history below the fold, Layout corrected, `_scratch/` removed.                                              |
| 7   | FINDINGS `python >= 3.13` → `3.13.2`        | **Done**, with the measured reason and the 139 count.                                                                                                |
| 8   | Licence partition / LICENSE note / CITATION | **Done.** `prereg.yaml` added to the README partition; LICENSE note added; CITATION declares both licences, schema-validated.                        |
| 9   | q2b prereg cites an unshipped note          | **Done, and upgraded** — see below.                                                                                                                  |
| 10  | "factor of two" / "factor of 701"           | **Done**, and 701 was found to be CORRECT — see below.                                                                                               |
| 11  | RELEASE-1.0 `_pm/` defect + banner          | **Done.** Both occurrences annotated; banner added. Verified `grep -n "_pm/" README.md` returns nothing.                                             |
| 12  | `docs/superpowers/plans/README.md`          | **Done.**                                                                                                                                            |
| 13  | CHANGELOG `[1.0.1]`                         | **Done.**                                                                                                                                            |

### Item 9 — "find the command or say none exists"

Neither. The command did not exist, so one was written:
`tools/check_q2b_curve_shape.py` recomputes the sign structure for all ten
(class, omega) pairs exactly as `outer_carbon_crossover` does and compares it to
the registered `curve_shape` block.

```
$ python3 tools/check_q2b_curve_shape.py
…
OK -- all 10 registered shapes reproduce, across 2 distinct shapes
```

This was worth doing because the existing tests in `tests/test_q2b_runner.py`
cover those branches with **synthetic** closures — they pin the selector's
behaviour, not the registered table's contents.

**It was seen to fail.** Run against a prereg copy with vascular Ω = 15 altered
from `[]` to the two-root shape, it reports
`vascular omega=15.0: registered [[-1, 1], [1, -1]], recomputed []` and exits 1.

**A coupling the guards caught before I did.** Adding the comment to `prereg.yaml`
changes its md5, which the CSV provenance headers record — so five tests went red
immediately. The q2b runner and the two q2b derivations were re-run; no data row
changed.

### Item 10 — the factor of 701 is correct and was kept

The plan read it as derived from the two 5-dp figures printed beside it
(0.52061 / 0.00074 = 703.5). It is not. From the unrounded coefficients,
`4π·m_im/λ` at `m_im` = 2.365 × 10⁻¹¹ and 2.900 × 10⁻⁸:

```
$ python3 -c "import math; kmin=4*math.pi*2.365e-11/0.400e-6; \
              kmax=4*math.pi*2.900e-08/0.700e-6; print(kmax/kmin)"
700.6946541830263
```

→ 701. So the plan's first branch applied: the source is quoted rather than the
number changed, and FINDINGS now names `tools/extract_ice_k.py` and explains the
703.5 discrepancy.

The "factor of two" half was a real overstatement and was fixed. All four miss
ratios: 0.3939 vs [0.60, 0.70] → 1.52× / 1.78×; 0.2424 vs [0.30, 0.40] → 1.24× /
1.65×. Written as **1.2–1.8× with the ratios**, in FINDINGS and in CHANGELOG. The
plan suggested "up to ~1.7×", which would understate the 1.78×; the exact range
is used instead.

## Acceptance

### Tests — 139 passed (131 + 8 new)

```
$ python -m pytest -q
139 passed in 2.16s
```

`tests/test_derived_csvs.py` adds regenerate-exactly guards for the three derived
CSVs, plus producer-named and source-md5-not-stale checks.

**The new guards were seen to fail**, each on a separate mutation of
`candidates.csv`, and each caught by two independent assertions:

| mutation                  | result                                            |
| ------------------------- | ------------------------------------------------- |
| a carbon digit flipped    | 2 failed — regenerate + agrees-with-`limits.csv`  |
| a source md5 made stale   | 2 failed — regenerate + header-names-its-producer |
| the vascular rows dropped | 2 failed — regenerate + holds-the-vascular-rows   |

### The Python 3.13.2 pin — measured, not asserted

Simulated by patching `platform.python_version` at runtime, leaving every
committed file untouched:

```
$ python3 -c "import platform, pytest, sys
platform.python_version = lambda: '3.13.9'
sys.exit(pytest.main(['-q','--no-header']))"
6 failed, 133 passed
```

Three runner regenerate tests and three derived ones, all on the `# python=`
line, with identical data. **The plan said "three tests"; that was correct before
this release added the derived CSVs.** README and FINDINGS say six.

### Site and smoke — 147/147

```
$ tools/build_site.sh          # exit 0
$ python3 tools/smoke_page.py
147 passed, 0 failed
```

### Citations — `docs/dois.txt` unchanged, ghostcite clean

Regenerating the file from `docs/` + `README.md` yields the same 69 DOIs, none
added, none removed — this release cites no new work.

```
$ ghostcite --format doi docs/dois.txt
ghostcite: 69 entries, 69 with DOIs
  retractions: Retraction Watch snapshot 2026-07-14 (71059 rows)
  ? U  L68  10.5061/dryad.j9kd51cgr   →  DOI not in CrossRef but resolves at doi.org
  ? U  L69  10.5281/zenodo.21908199   →  DOI not in CrossRef but resolves at doi.org
  2 U
```

Zero ghost citations, zero retractions. The two `U` rows are a Dryad dataset and
a Zenodo deposit — registered with DataCite, not CrossRef — the same two, for the
same reason, as at 1.0.0 (`docs/RELEASE-1.0.md:363`).

### Secrets and machine paths — clean

```
$ gitleaks git --redact -v .        # 101 commits scanned, no leaks found
$ gitleaks dir --redact -v site/    # no leaks found
$ git grep -n -I -E "/home/|-home-|a2b32|mjarnold|C:\\Users" -- .
docs/superpowers/specs/2026-09-11-v1.0.1-plan.md:93   (the acceptance rule quoting those literals)
$ grep -rn -E "/home/|-home-|a2b32|mjarnold" site/
(no output)
```

The only hit is the plan file quoting the patterns as its own rule text. No
machine path, no account name, in the tree or in the built site.

## For the coordinator

1. **`docs/superpowers/specs/2026-09-11-v1.0.1-plan.md` is an internal executor
   brief and is committed on `master`.** For 1.0 the equivalent was deliberately
   removed before release (`2ac9bb4`, "docs: remove the internal executor
   brief"). The same call is open here, and it is yours — removing it was not in
   this release's scope allowlist. It contains no secret and no machine path.
2. **The page's FINDINGS link still points at `blob/master`.** Unchanged from
   1.0.0 and correct after merge.
3. **Carried forward from 1.0.0, unfixed and still the owner's call:** the home
   path and Windows account name in ~17 commits of _git history_. Working-tree
   redactions cannot reach them; `gitleaks` finds no credential. Recommendation
   at 1.0.0 was accept-and-flip.
4. `CITATION.cff` now says `version: 1.0.1` and `date-released: 2026-09-11`. If
   the tag slips, that date needs updating with it.

**Executor stops here.** No merge, no tag, no release, no visibility change.
