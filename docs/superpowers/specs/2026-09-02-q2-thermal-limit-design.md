# Q2 design — the thermal limit, and which constraint actually binds

Registered 2026-09-02. Successor to
`docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md`.
Q1's `prereg.yaml` is frozen; nothing here edits it.

## Why Q2 is not the question that was declared

Q1 declared a v2: *"carbon cost of holding tissue temperature against radiative loss to
space, giving a second crossover."* A design-time feasibility check killed it, and the
result is worth more than the question was.

**Holding 293 K in vacuum costs 179x (flat lamina) to 358x (sphere) the organism's entire
photosynthetic capacity — at 1 AU, in full sunlight.** Radiative loss is
`ratio * sigma * T^4` = 836 W m-2 (lamina) or 1672 W m-2 (sphere); at ~467 kJ per mol C
that is 1790 / 3580 umol C m-2 s-1 against an `a_max` of 10. A heated organism has no
positive carbon balance anywhere, so there is no second crossover to find.

The passive alternative has no crossover either, for the opposite reason: respiration is
exponential in temperature while assimilation falls as 1/r^2, so a cooling organism's
respiration collapses to ~1e-7 by 10 AU while gross assimilation is still 5.8. Net carbon
stays positive past 100 AU.

**The real finding is what that implies for Q1.** A passive organism reaches 273 K at
1.04 AU (sphere) to 1.47 AU (lamina). Q1's crossovers sit at 13.69 and 75.43 AU — **10 to
70x beyond the point where the organism is frozen solid.** Every Q1 answer lives in a
regime where its own Q10 law and its implicit liquid-water assumption are invalid.
**Q1 measured a limit that never binds.** That correction is part of this spec's output.

## Registered question (Q2)

For a single organism of photosystem class C at radiative equilibrium with distance — no
heating, temperature free to fall — and with photosynthetic rate following an
empirically-anchored temperature response rather than a Q10 extrapolated ~200 K beyond
anything that measured it: **what sets the outer limit — light, carbon, or temperature —
and at what heliocentric distance?**

The three candidate limits are separated by an order of magnitude, so the answer is
falsifiable in a way Q1's band was not.

**Deliberately NOT registered:** the pure thermal cutoff `r = (T_eq(1 AU) / T_min)^2`. It
is a closed form, it was computed during design (1.19 AU algal, 1.52-1.56 AU vascular),
and registering a known answer is theatre. What is registered is which limit binds and
where, once the rate declines continuously instead of switching off.

## Grounding

All quotes verbatim from Pointing et al. (2015), *Biogeography of photoautotrophs in the
high polar biome*, Front. Plant Sci. 6:692, doi:10.3389/fpls.2015.00692 (gold OA;
ghostcite 0.5.2 clean, 0 findings).

**Algal / lichenised floor.** *"even the capacity of some species to gain positive net
photosynthesis at sub-0 temperatures, for example as low as -18.5°C for the Antarctic
lichen Neuropogon acromelanus (Lange and Kappen, 2013) in the laboratory and similar
values reported in the field for Usnea sphacelata and Umbilicaria aprina (Kappen, 1989;
Schroeter et al., 1994)."* => T_min = 254.65 K. A lichen photobiont is a chlorophyte, so
this is the right organism for the algal class.

**Vascular floor.** *"the theoretical lower thermal limit for plastid-mediated
photosynthesis occurs where chloroplasts freeze at -5 to -8°C (Körner, 2003a)"*
=> T_min in [265.15, 268.15] K.

**Rate anchors (these replace Q10).** *"Cold adapted photosynthetic tissue in vascular
plants reaches 60-70% of maximum rates at 5°C and 30-40% at 0°C, when growth is 0
(Körner, 2003b)."*

Attributions inside those quotes (Lange & Kappen; Körner 2003a/b; Kappen 1989; Schroeter
et al. 1994) are reported **as cited by Pointing et al.** and are NOT independently
verified here. Only Pointing et al. 2015 passed the citation gate. Do not promote an
inner attribution to a first-party citation without re-verifying it.

## Model

Pure functions, no state, no time axis. New module `sim/thermal.py`.

- `equilibrium_temperature(r_au, area_ratio, emissivity, albedo) -> K`
  `T = (TSI / r_au^2 * (1 - albedo) / (area_ratio * emissivity * sigma)) ** 0.25`,
  sigma = 5.670374419e-8 W m-2 K-4. Raises on r_au <= 0, area_ratio <= 0,
  emissivity outside (0, 1], albedo outside [0, 1).
- `temperature_response(t, t_min, t_opt) -> [0, 1]`
  Normalized rate multiplier. **Parameterized ONLY by t_min and t_opt** — see the gate.
  Zero at or below t_min, 1 at t_opt.
  `t_opt` is a **declared assumption, not grounded**: 298.15 K (25°C) for both classes,
  flagged in the prereg alongside emissivity and albedo. It is the second of the two
  free parameters of the held-out gate, so if the gate fails, an ungrounded `t_opt` is
  the first suspect and must be reported as such rather than tuned until the gate passes.
- `Organism` gains `area_ratio: float = 2.0` and `t_min: float = 265.15`, both defaulted
  so the Q1 presets construct unchanged.
- **`net_carbon` is NOT modified.** Q2 adds a separate method,
  `net_carbon_at_equilibrium(r_au, ...)`, computing
  `gross_assimilation(irradiance(r), a_max, k) * temperature_response(T(r), ...) -
   organism_respiration(T(r))`.

  *Self-review caught this as a contradiction in the first draft:* making `net_carbon`
  temperature-dependent would change Q1's committed numbers, which this same spec requires
  to be unchanged. The two requirements cannot both hold on one function. Q1's carbon-only
  path stays byte-identical; Q2 is a new entry point beside it. This also keeps the two
  registered questions independently re-runnable, which the provenance headers assume.

Geometry per class, from the organism decisions already made: vascular = flat lamina,
absorbs on one face and radiates from both, `area_ratio = 2`. Algal = sphere (the
unicellular decision of 2026-09-02), absorbs over its cross-section and radiates over its
whole surface, `area_ratio = 4`.

## Calibration gates (both must pass before any distance is reported)

**Gate 1 — thermal physics.** At 1 AU with emissivity 1 and albedo 0, the sphere
(`area_ratio = 4`) must give `T_eq` in **[275, 282] K**, bracketing the standard
solar-system blackbody value of 278.3 K. A sign error or a factor-of-4 geometry slip
fails it.

**Gate 2 — the temperature response, held-out.** `temperature_response` must return
**0.60-0.70 at 5°C (278.15 K)** and **0.30-0.40 at 0°C (273.15 K)**, per the Körner
anchors quoted above.

**Gate 2 must not be circular, and this is a hard requirement.** The response curve is
fitted using ONLY `t_min` and `t_opt`. The 5°C and 0°C values are HELD OUT and used
solely as the gate. Building the curve through those anchors and then checking it against
them would be a test that cannot fail — the defect the Q1 review caught twice. If a curve
pinned at its endpoints does not independently land in both windows, **the gate fails and
the functional form is wrong**; that is a real outcome, not a fitting problem to be tuned
away.

## Swept axis

`t_min` across its cited range. Vascular: [265.15, 268.15] K — the -5 to -8°C span, which
the source states as a range. Algal: the source gives a **single** value, -18.5°C, not a
range, so the sweep is the three points {252.15, 254.65, 257.15} K, i.e. the cited value
plus or minus 2.5 K. **That spread is a declared assumption, not a cited uncertainty**, and
the prereg must say so — the source reports one number and inventing an interval around it
would be fabricating precision the literature does not offer. Distance remains the
independent variable.

Unlike Q1 — where `k` was swept but invisible to the gate, producing a band that could not
be falsified — **`t_min` is the gated quantity.** Sweeping it cannot produce an
unfalsifiable band.

## Reachability, computed BEFORE registering

The prereg must record, alongside each predicted band, the interval of outcomes the gates
actually permit. Q1's review found that 96.2% of its vascular band was pre-satisfied by
its gate and 89.5% of its algal band was unreachable — both discovered after the run.
This is that lesson applied at registration time. A predicted band that the gates cannot
reach is not a prediction and must be re-drawn before the run.

## Declared assumptions, not gated

`emissivity` and `albedo`. A real leaf's solar absorptance is far from 1 and shifts `T_eq`
materially. They get a sensitivity arm and an explicit flag rather than an invented
citation. Also uncited: the ~467 kJ per mol C used in the motivation above; it is a
textbook heat of combustion and is used only for an order-of-magnitude argument that does
not enter the model.

## Out of scope

- **The heating-cost arm.** Recorded above as a result; not built.
- **Insulation / pressure vessel.** The genuinely open engineering question — how much
  insulation keeps the organism liquid at distance r — is deferred INTACT to a later
  question rather than half-answered here.
- Time axis, population, inheritance, element stoichiometry, any play surface.

## Files

```
sim/thermal.py                    equilibrium_temperature, temperature_response
sim/organism.py                   + area_ratio, t_min (defaulted); T-dependent net_carbon
experiments/q2_thermal/prereg.yaml
experiments/q2_thermal/run.py     gate -> sweep -> report, provenance headers
experiments/q2_thermal/plot.R     sources docs/analysis/theme.R
tests/test_thermal.py
tests/test_q2_runner.py
```

Runner conventions inherit from Q1 unchanged: gate before report, exit 2 on gate failure,
clear stale outputs before that exit, provenance header carrying git sha + md5 of each
source module + the prereg + the numeric stack.

## Testing

- **Gate 2 is run against a deliberately wrong functional form first**, to confirm it can
  fail, and the observed failure is recorded. No gate ships unseen-failing.
- Every negative assertion carries a positive control in the same test.
- **Q1's `test_committed_csvs_regenerate_exactly` runs unchanged as the cross-question
  guard.** Extending `Organism` must not perturb Q1's committed numbers; if it does, that
  test fails loudly rather than silently rewriting the record.
- A regeneration test for Q2's own CSVs, mirroring Q1's.

## Success

Both gates pass; the sweep reports which of light, carbon, or temperature binds first per
class, with the distance; the reachability intervals recorded in the prereg are compared
against the outcome; and Q1's committed numbers are unchanged.
