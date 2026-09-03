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
for both classes) was never tested.** Any figure or number for "which limit binds
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
# git_sha=821df11b06ef4c40918b48697fc71751d79feda1
# thermal_md5=95b021360a70a5b4b0e16e643fa98500
# organism_md5=153da4cac9084fee3514e33e153b42f4
# physiology_md5=adacb668ea4f79b428ca0155381da220
# prereg_md5=f68949559939193a48a092546c638726
# python=3.13.2
# numpy=2.3.5
# scipy=1.16.3
# written=2026-09-02T20:12:34-04:00
```
