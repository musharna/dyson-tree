# Q2: what limits range from the Sun for a passive organism at radiative equilibrium?

## 1. Registered question

From `prereg.yaml` (registered 2026-09-02, spec `docs/superpowers/specs/2026-09-02-q2-thermal-limit-design.md`):

> For a passive organism at radiative equilibrium, with photosynthetic rate following
> an empirically-anchored temperature response rather than an extrapolated Q10, what
> sets the outer limit -- light, carbon, or temperature -- and at what distance?

Registered prediction: `temperature` binds first for both the `vascular` and `algal` classes.

## 2. Gate results

`python3 experiments/q2_thermal/run.py` exited **2**. Full stdout:

```
gate thermal T_eq at 1.0 AU: 278.3112 in [275.0, 282.0] pass
gate response f(T=278.15 K): 0.3939 in [0.6, 0.7] FAIL
gate response f(T=273.15 K): 0.2424 in [0.3, 0.4] FAIL
GATE FAILED: limits not reported.
Do NOT tune t_opt to pass. Report the failure and the implied t_opt.
removed any stale sweep.csv/limits.csv from /home/mjarnold/dyson-tree/experiments/q2_thermal
```

**Gate 1 (thermal physics, `gate_thermal`)**: PASS. Equilibrium temperature of a sphere
at 1 AU (area ratio 4, emissivity 1, albedo 0) is 278.3112 K, inside the registered
[275.0, 282.0] K bracket around the standard blackbody value.

**Gate 2 (held-out response anchors, `gate_response`)**: FAIL, both anchors.
`temperature_response(t, t_min=265.15, t_opt=298.15)` is a linear ramp from 0 at
`t_min` to 1 at `t_opt` (`sim/thermal.py:45-59`), parameterized only by `t_min` and
`t_opt` — the anchors are never used to fit it, so they are a genuine held-out check.

| anchor            | observed | required window | verdict |
| ----------------- | -------- | --------------- | ------- |
| f(278.15 K, 5 °C) | 0.3939   | [0.60, 0.70]    | FAIL    |
| f(273.15 K, 0 °C) | 0.2424   | [0.30, 0.40]    | FAIL    |

## 3. No limits reported

`sweep.csv` and `limits.csv` were not written — `run.py` removed any stale copies of
both and exited before the distance sweep. The gate is the precondition for reporting
a binding limit; it did not pass, so **no distance sweep ran, no limits table exists,
no binding-limit classification exists, and the registered prediction (`temperature`
for both classes) was never tested.** It is also, as §9 shows, unsatisfiable: the run could not have confirmed it even had the gates passed. Any figure or number for "which limit binds
first" would be fabricated — none is reported here.

## 4. What `t_opt` the anchors imply (diagnosis, not an adopted value)

Both anchors use the same linear form as the sim: `f(t) = (t - t_min) / (t_opt - t_min)`
for `t_min < t <= t_opt`, with `t_min = 265.15 K` fixed by the gate.

Solving each anchor's window for `t_opt`:

- 5 °C anchor: `f(278.15) ∈ [0.60, 0.70]` → `t_opt - 265.15 = 13.00 / f` →
  `t_opt ∈ [265.15 + 13.00/0.70, 265.15 + 13.00/0.60] = [283.72, 286.82]` K
- 0 °C anchor: `f(273.15) ∈ [0.30, 0.40]` → `t_opt - 265.15 = 8.00 / f` →
  `t_opt ∈ [265.15 + 8.00/0.40, 265.15 + 8.00/0.30] = [285.15, 291.82]` K

Intersection (the `t_opt` band that satisfies **both** windows simultaneously):

```
t_opt ∈ [285.15, 286.82] K   (12.0 – 13.7 °C)
```

This is a diagnosis of what the two literature anchors are consistent with under the
declared linear form — **it is not being adopted.** Setting `t_opt` to this band to
pass the gate would be exactly the circularity the held-out design exists to prevent:
a curve fitted through its own check anchors cannot fail against them.

## 5. Likely root cause

The declared `t_opt_k: 298.15` (25 °C) in `prereg.yaml` is flagged in the file itself
as a "DECLARED ASSUMPTION, NOT GROUNDED" — a generic mesophyte thermal optimum. The
gate anchors, by contrast, are specifically for **cold-adapted photosynthetic tissue**
(Pointing et al. 2015, 10.3389/fpls.2015.00692, quoting Koerner 2003b: "Cold adapted
photosynthetic tissue in vascular plants reaches 60-70% of maximum rates at 5 °C and
30-40% at 0 °C"). A cold-adapted optimum sits well below a mesophyte optimum, so a
linear ramp anchored at 298.15 K under-predicts the response at 5 °C and 0 °C by a
wide margin (observed 0.39 vs. required 0.60-0.70; 0.24 vs. 0.30-0.40) — consistent
with the implied band of 285.15-286.82 K computed above, ~11-13 K below 298.15 K.

## 6. What would resolve it honestly

Source a `t_opt` for cold-adapted photosynthetic tissue from the literature (not the
band in §4, which was derived from the same two anchors used to gate it), then
register a new pre-registration with that value and re-run. The gate anchors
themselves are not in question; the mismatch is between a mesophyte `t_opt` and
cold-adapted response data.

## 7. Reachable intervals from the prereg (untested)

`prereg.yaml` records, under `reachable_thermal_cutoff_au`, intervals computed by
`reachability.py` **before registration** — a band the gates could not reach would
not have been a valid prediction to register in the first place:

```yaml
reachable_thermal_cutoff_au:
  vascular: [1.5581, 1.5406, 1.5234]
  algal: [1.2183, 1.1945, 1.1714]
```

These pair index-for-index with each class's `t_min_grid` in `prereg.yaml`
(vascular: [265.15, 266.65, 268.15] K; algal: [252.15, 254.65, 257.15] K). Because
Gate 2 failed, the distance sweep never ran, so these intervals remain **untested
against actual output** — they describe what was reachable under the frozen
assumptions, not what the sweep produced.

The registered sweep window was `[0.5, 100.0]` AU (`sweep.r_min_au` /
`sweep.r_max_au` in `prereg.yaml`); no swept value exists to check against that edge
since the sweep did not run.

## 8. Provenance (verbatim from `gates.csv`)

```
# git_sha=e2301116935d84f649ef3ae7107eef2f3d7dd0d6
# thermal_md5=e69a7c818f4499e12fd17b6e91b34b96
# organism_md5=df699a13442e8794d226cf58c8408345
# physiology_md5=adacb668ea4f79b428ca0155381da220
# prereg_md5=f68949559939193a48a092546c638726
# python=3.13.2
# numpy=2.3.5
# scipy=1.16.3
# written=2026-09-02T20:38:39-04:00
```

## 9. A second registration defect, found by a code review (disclosed, not corrected)

`prereg.yaml` is frozen; the two problems below are defects **in the registration
itself**, not in the runner. They are reported here because they were found while
implementing a post-review fix wave, not fixed there, because fixing them would mean
editing a frozen file.

**9.1 The registered prediction (`temperature` for both classes) could not have been
satisfied by any parameters.** Respiration is strictly positive at `t_min`
(`respiration(r_d, t_min) > 0` for any `r_d > 0`), so net carbon at radiative
equilibrium goes negative _before_ the temperature response reaches zero: the outer
root of `net_carbon_at_equilibrium` always sits strictly inside the pure thermal
cutoff `r = (T_eq(1 AU) / t_min)^2`. This is not a coincidence of the two rows quoted
in the fix-wave review — it holds for **all six** registered `(class, t_min)` pairs,
recomputed here directly from `outer_equilibrium_carbon_crossover` (the corrected
selector; see the runner's `git log`) and `reachability.thermal_cutoff_au`:

| class    | t_min (K) | outer carbon root (AU) | thermal cutoff (AU) | carbon − thermal | as % of thermal |
| -------- | --------- | ---------------------- | ------------------- | ---------------- | --------------- |
| vascular | 265.15    | 1.54978                | 1.55809             | −0.0083 AU       | −0.5334%        |
| vascular | 266.65    | 1.53195                | 1.54061             | −0.0087 AU       | −0.5622%        |
| vascular | 268.15    | 1.51441                | 1.52342             | −0.0090 AU       | −0.5914%        |
| algal    | 252.15    | 1.21763                | 1.21827             | −0.0006 AU       | −0.0524%        |
| algal    | 254.65    | 1.19377                | 1.19447             | −0.0007 AU       | −0.0583%        |
| algal    | 257.15    | 1.17060                | 1.17135             | −0.0008 AU       | −0.0647%        |

Carbon binds before temperature in every one of the six rows the prereg registers.
`binding = min(...)` over `{temperature, carbon_fixed_t, carbon_equilibrium}` can
therefore never return `"temperature"` under any admissible sweep of `t_min` inside
the registered grids — the registration predicted an outcome its own model structure
cannot produce, for any parameters, not just the ones that happened to be swept.

**9.2 `"light"` has no representative in the runner and can never be reported.** The
registered question asks what sets the outer limit — _"light, carbon, or
temperature"_ — but `run.py`'s `candidates` dict has exactly three keys:
`temperature`, `carbon_fixed_t`, `carbon_equilibrium`. No candidate stands for a
light-driven limit (irradiance falling below some floor independent of temperature or
carbon balance), so `binding` can only ever read as `"temperature"` or one of the two
carbon variants. A third of the registered question's answer space was never wired up.

**9.3 The substantive finding these two defects point to.** Combined with §9.1's
table, the model as built says: **for a passive organism at radiative equilibrium,
the carbon limit and the thermal limit are effectively the same limit** — they
coincide to within 0.04%–0.6% of the distance across every registered `(class,
t_min)` pair, with carbon always binding first, by a margin an order of magnitude
smaller than the separation the design doc argued would make the three-way question
falsifiable (`docs/superpowers/specs/2026-09-02-q2-thermal-limit-design.md`: _"The
three candidate limits are separated by an order of magnitude"_). That separation
does not hold once carbon is evaluated at the equilibrium temperature rather than
fixed T — respiration and assimilation both collapse in the same narrow band just
above `t_min`, so the two limits close in on each other instead of separating. The
registered three-way question is degenerate for this model: it was built in a way
that makes `"carbon"` the only reachable answer, `"temperature"` an answer the model
can approach but never actually produce, and `"light"` an answer the model cannot
express at all.

**This is disclosed here, not corrected**, because `prereg.yaml` is a frozen
pre-registration — see hard constraint 1 of the fix wave that produced this section.
Resolving it means a new registration with a candidate set that actually spans
`{light, carbon, temperature}` and a design-time reachability check (as
`reachability.py`'s own docstring argues) confirming `"temperature"` is a reachable
outcome before the question is asked again.

## 10. Re-running after a change to `sim/organism.py` or `sim/thermal.py`

Both Q1 and Q2 hash `sim/organism.py` into their CSV provenance headers (Q1 also
hashes `sim/physiology.py`; Q2 also hashes `sim/thermal.py`). A change to any of
those files moves the corresponding `*_md5` line in every committed CSV under
`experiments/q1_crossover/` and `experiments/q2_thermal/`, which fails
`test_committed_csvs_regenerate_exactly` (Q1) and
`test_committed_q2_csvs_regenerate_exactly` (Q2) until the CSVs are regenerated —
this is expected, not a bug, and the two tests going red together is exactly the
tripwire they exist for.

The procedure, in order (used for the `ALGAL` geometry fix and the `thermal.py`
docstring completion in this fix wave):

1. **Commit the source change on its own** — no CSV files in the same commit. Both
   regeneration tests will be RED at this commit; that is expected and should be
   noted in the commit message so a `git bisect` doesn't mistake it for a break.
2. **Re-run both experiments**: `python3 experiments/q1_crossover/run.py` (must exit 0) and `python3 experiments/q2_thermal/run.py` (must exit 2 — Gate 2 fails on the
   frozen prereg and is expected to keep failing; a change that makes it exit 0
   without an intentional, disclosed prereg change is itself a bug — see hard
   constraint 2 above it).
3. **Verify the CSV bodies, not just that the commands ran.** For Q1, diff each
   committed CSV against `master` with comment lines stripped (the exact command is
   in this repo's fix-wave instructions and in `test_runner.py`); the three bodies
   must be byte-identical. For Q2, diff `gates.csv`'s body (comment lines stripped)
   against the pre-regeneration commit; it must be unchanged. If any body line moved,
   **stop** — a source change that alters `net_carbon()`'s registered numbers (Q1) or
   the gate verdicts (Q2) is a different, much bigger change than a provenance-header
   refresh, and needs its own review, not a silent CSV update.
4. **Commit the header-only CSV updates as a separate commit**, once step 3 confirms
   only provenance lines (`git_sha`, `*_md5`, `written`) changed.
