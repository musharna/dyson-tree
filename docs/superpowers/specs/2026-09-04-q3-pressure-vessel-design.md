# Q3 design — the pressure vessel, and the radius at which transparency and strength collide

> Approved 2026-09-04 on framing A (wall feasibility), with framing C (the `area_ratio`
> degeneracy repair) folded into the pre-registration rather than run as a separate pass.
>
> **⚠️ SUPERSEDED IN PART, 2026-09-04, BY ITS OWN BLOCKER BEING CLEARED — read
> `docs/bio_grounding_2026-09-02.md` §9 BEFORE implementing anything below.** `k` is now
> grounded from Warren & Brandt (2008)'s primary data table, and it falsifies this spec's
> central hypothesis. Two things in this document are now known wrong:
> **(1)** `k` is not a scalar — it spans a factor of 701 across PAR (0.00074 to 0.52061 /m),
> so the wall is a spectral filter and `max_vessel_radius(..., k_per_m, ...)` as specced
> below cannot express it. **(2)** The declared band `k ∈ [0.1, 5.0] /m` was wrong, 135x too
> high at the blue end, and the registered question's premise fails with it: `R_max` is
> 1.3e3–9.9e4 km against an assumed 10 km radius, so **strength and transparency do not
> collide at any radius this project has reason to model.** The title of this spec names a
> collision that does not occur.
>
> What survives intact: the contained-temperature result, the `area_ratio` degeneracy, the
> forced clear-wall architecture, and the refusal to register a prediction on an
> author-chosen band — that refusal is the only reason this is a correction and not a
> retraction. Q3 must be re-registered; §9 states the two candidate framings.
>
> **⚠️⚠️ CORRECTION TO THE CORRECTION, 2026-09-04 (same day) — read `bio_grounding` §10.**
> Point (2) above is WITHDRAWN and the title is REINSTATED. §9 divided §7's WOOD tensile
> strength (80 MPa) by §9's ICE absorption coefficient; no material in this project's
> grounding has both properties, so that `R_max` is wrong by ~53x. With ice strength
> grounded (0.7–3.1 MPa, Petrovic 2003 via Hirata 2022) the collision is real at the top of
> this spec's own registered pressure bracket: **1.2–7.4 km in the red band at 10 kPa,
> BELOW the 10 km radius assumed here**, and 14–62 km at the 882 Pa floor. **This spec's
> title names a collision that DOES occur — the question is which pressure the organism
> must hold.** Point (1), the spectral-filter defect, is unaffected and still fatal to
> `max_vessel_radius(..., k_per_m, ...)` as specced: `k` must become a band, not a scalar.
>
> **⚠️⚠️ THIRD CORRECTION, 2026-09-04 — `bio_grounding` §11 S1 ANSWERS "which pressure".**
> The question the correction above left open is settled by this spec's own contained-temperature
> result. **The registered bracket `p ∈ [882 Pa, 10 kPa]` is self-inconsistent:** its floor is the
> saturation pressure at the UNCONTAINED 5.16 °C, but §37 below settles that containment is
> mandatory and sets the temperature. One IR-opaque shell puts the interior at 57.82 °C, whose
> saturation pressure is **18.02 kPa — 1.8x above this bracket's own ceiling**; two shells need
> 78.9 kPa. **Every pressure in the registered bracket describes an organism with no liquid
> water, which is the condition that promoted this question to a precondition.** At the
> self-consistent 18 kPa the red-band `R_max` is **0.93–4.10 km against the 10 km radius assumed
> here** — so the collision this spec is named for does not merely occur, it binds decisively.
> **A re-registered Q3 must derive `p` from `T_interior`, not declare it.**

## Why this is a precondition and not an extension

Q1 listed the pressure vessel under "Out of scope (v1)" and Q2 and Q2b inherited that
deferral. `docs/thermal_premise_retired_2026-09-03.md` §4 retired the deferral: Q1, Q2 and
Q2b all model photosynthesis proceeding at a vacuum equilibrium temperature, and at that
temperature there is no liquid phase — 882 Pa saturation pressure at the algal sphere's
5.16 °C, ~0 ambient. The carbon arithmetic in those three questions is not wrong; it is
arithmetic about an organism that, as modelled, has no liquid water to run it with.

That doc posed three sub-questions. **The third is already answered, analytically, and it
is answered here rather than by simulation** — see the next section. What remains genuinely
open is the first two, and they collapse into a single quantitative question once the
containment is required to admit light.

## The sub-question that is already settled: the vessel sets the temperature

For a wall transparent in the shortwave and opaque in the thermal IR — the physically
expected case for water or clear ice, which is highly transmissive in PAR and strongly
absorbing beyond ~3 µm — the standard shell balance applies. A thin shell radiates from both
faces, so it emits twice what it absorbs from the interior:

    shell:   sigma*T_i^4 = 2*sigma*T_s^4        ->  T_i = 2^0.25 * T_s
    system:  sigma*T_s^4 = S(1-albedo)/4        ->  T_s = T_eq (the bare value)

Generalising to N such shells:

    T_interior = (N + 1)^0.25 * T_eq            [D]
    r_restore  = sqrt(N + 1)                    [D]   distance restoring the bare optimum

**A contained organism does not follow `T_eq`.** One shell raises the algal sphere from
5.16 °C to 57.82 °C, and restoring the 5.16 °C optimum requires moving from 1.0 AU to
1.41421 AU. This is a bounding idealisation, not a wall model: it assumes a thin,
grey, SW-transparent/IR-opaque shell and neglects conduction. It brackets the effect; it
does not resolve it.

## The degeneracy this exposes in Q1, Q2 and Q2b (framing C, folded in)

Adding one IR-opaque shell and halving the radiating-to-absorbing area ratio are the **same
operation**. A greenhoused sphere (`area_ratio` 4, N=1) and a bare lamina (`area_ratio` 2,
N=0) are the same temperature to 5.7e-14 K — exactly equal for any shared albedo and
emissivity, since both reduce to a factor of 2^0.25.

But `sim/thermal.py:28` defines the parameter as _"radiating area divided by absorbing
(projected) area"_ — pure geometry. So **`area_ratio` has been carrying two physically
distinct claims under one name**, and every registered value of 4.0 silently also asserted
_uncontained_. Consequences that must be stated, not buried:

- Q2b's algal `area_ratio` band [3.630, 4.311] is not a statement about shape alone.
- No result in Q1, Q2 or Q2b is invalidated by this. What changes is what they _measured_:
  a combined geometry-and-containment factor, not a geometric one.
- **Q3's model MUST separate the two**, or its own gate inherits the same degeneracy and
  cannot discriminate the thing it exists to test. This is the project's recurring root
  class — a parameter that cannot distinguish the states it is trusted to specify — and it
  is being caught here before registration rather than after.

Q1, Q2 and Q2b stay frozen. The correction is recorded, not retrofitted.

## Registered question (Q3)

A wall thick enough to hold an internal pressure is also thick enough to attenuate the light
the organism lives on. Thickness rises linearly with organism radius; transmission falls
exponentially with thickness. The two constraints therefore pull in opposite directions and
meet at a finite radius:

**What is the maximum radius of a photosynthetic pressure vessel — the radius beyond which
no wall is simultaneously strong enough to hold liquid water and transparent enough to pass
the light the organism needs — and which of its inputs decides that radius?**

## Model

Both relations are already in the project; neither is new physics.

    thin-wall sphere hoop stress:   sigma = p*R / (2*t)      ->  t = p*R / (2*sigma)
    Beer-Lambert through the wall:  tau   = exp(-k*t)
    require tau >= tau_min          ->      R <= 2*sigma*|ln tau_min| / (k*p)

so

    R_max = 2*sigma*|ln tau_min| / (k*p)        [D]

**Positive control on the closed form:** at p = 10 kPa, R = 10 km, sigma = 80 MPa it returns
t = 0.6250 m, reproducing the sizing already committed in `docs/prior_art_2026-09-01.md` §4
to within 1e-9 m. The new expression is the registered relation rearranged, not a
substitute for it.

New in `sim/`, added BESIDE existing functions — Q1's, Q2's and Q2b's committed `gates.csv`
must keep regenerating unchanged:

- `wall_thickness(p_pa, radius_m, sigma_pa) -> m` — hoop stress, raises on non-positive args.
- `wall_transmission(k_per_m, thickness_m) -> [0, 1]` — Beer-Lambert.
- `max_vessel_radius(sigma_pa, p_pa, k_per_m, tau_min) -> m` — the closed form above.
- `greenhouse_factor(n_shells) -> float` — `(n_shells + 1) ** 0.25`, named so the premise is
  greppable and testable rather than inlined, exactly as `adapted_optimum` was in Q2b.
- `contained_temperature(r_au, area_ratio, n_shells, ...) -> K` —
  `greenhouse_factor(n_shells) * equilibrium_temperature(...)`. **`n_shells` and `area_ratio`
  stay separate arguments** even though they are degenerate in the output. The degeneracy is
  the finding; collapsing them into one parameter would erase it.

## Inputs, and how well each is grounded

| Input                 | Symbol  | Value / band                  | Status                                                                                                                                                                          |
| --------------------- | ------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Wall tensile strength | sigma   | 45 / 80 / 139 MPa             | **GROUNDED** — clear-wood MOR, 111 species-rows, FPL 2010; `bio_grounding` §7                                                                                                   |
| Internal pressure     | p       | 882 Pa – 10 kPa               | **BRACKETED** — floor is saturation pressure at 5.16 °C (physics); upper is Paul 2004's demonstrated-viable 10 kPa                                                              |
| Wall PAR attenuation  | k       | 0.00074–0.52061 /m across PAR | **GROUNDED 2026-09-04** — Warren & Brandt 2008 primary table, 31 PAR rows (`bio_grounding` §9). NOT a scalar: factor-701 spread. Falsifies this spec's premise; see the banner. |
| Minimum transmission  | tau_min | —                             | **NOT GROUNDED** — it is `I_c` / incident PAR, and `I_c` failed to ground on 2026-09-03 (`bio_grounding` §8)                                                                    |

The pressured-wall requirement also forces an architectural conclusion worth stating: at
0.625 m, _pigmented_ tissue transmits `e^-3952` — indistinguishable from zero, calibrated
against a 0.3 mm leaf passing ~15% of PAR. **The wall cannot be pigmented.** The organism is
forced into a clear vessel with photosynthetic tissue strictly inside it.

## The prediction, and the reason it is not registered yet

The obvious registered prediction is a variance decomposition: _which input dominates the
spread in `R_max`?_ A one-at-a-time sweep over the bands above puts `k` first by a wide
margin (x50 across 0.1–5.0 /m, against x11 for p, x3 for sigma, x2 for tau_min).

**That result must not be registered, because I chose it.** `k`'s band is declared by me,
not sourced; widen or narrow it and the ordering changes. A prediction whose answer is set
by the author's choice of band width is a test that cannot fail — the class this project
keeps catching — and registering it would be the same defect in a new costume.

So the pre-registration is **gated on grounding `k` first**:

- `k` must come from measured optical constants for the candidate wall material (clear ice
  is the obvious first target; its PAR absorption coefficients are well measured) via the
  project's citation chain, with the band set by the source's own spread, not by me.
- Only then is the variance decomposition registered, and only then is the `R_max` interval
  computed and disclosed in `prereg.yaml` before the run — per Q1's and Q2's lesson.
- `tau_min` inherits the same rule and is worse off: it needs `I_c`, which is still open.
  Q3 registers pass/fail against the **bounded** `I_c` range rather than a point, so the gate
  reports whether the answer is robust across the whole plausible band. If no band can be
  sourced, `tau_min` is swept and reported per-value, never collapsed to one number.

**Q3 cannot be registered until `k` is grounded.** That is a real blocker, stated as one.

**CLEARED 2026-09-04, same day — and it cost this spec its central hypothesis.** `k` is
grounded in `bio_grounding` §9. The sweep that put `k` first by x50 was run on a band I
declared, and the grounded values sit 135x below my floor at the blue end, so the ordering it
produced was an artifact of my choice. Registering it would have shipped a falsified result
with a pre-registration stamp on it. **This is the strongest argument in the project so far
for the rule that produced it: the refusal to register a prediction whose answer the author
picked is what turned a retraction into a correction.** `tau_min` remains open and still
depends on `I_c`, unchanged from §8.

## Gates

Each must be able to fail against something outside the model.

- **Gate A — thermal physics.** Retained from Q2 and Q2b unchanged: at 1 AU, sphere, eps=1,
  albedo=0, `T_eq` in [275.0, 282.0] K. Fails if the retained radiative core drifts.
- **Gate B — optics.** Beer-Lambert with the grounded `k` must reproduce a _measured_
  transmission through a stated thickness of the cited material, within a tolerance
  registered in advance. Fails if the extracted `k` does not describe the material it came
  from.
- **Gate C — vapour pressure.** The saturation-pressure function must reproduce measured
  values at two independent points (the 273.16 K triple point at 611.657 Pa, and the 5.16 °C
  value the retired-premise doc already quotes). Fails on an incorrect implementation or a
  misread table.

The greenhouse-degeneracy identity (`contained_temperature(4, N=1) == equilibrium(2, N=0)`)
is a **unit test, not a gate**. It can fail on an implementation error, which makes it worth
having, but it checks the algebra against itself and no external measurement — calling it a
gate would overstate what it can detect.

## Out of scope (v1)

- Any edit to `experiments/q1_crossover/`, `experiments/q2_thermal/` or
  `experiments/q2b_adapted/`. All frozen; the degeneracy is recorded against them, not
  retrofitted into them.
- A continuous radiative-transfer treatment of the wall. The N-shell model is discrete and
  grey by choice; it brackets the greenhouse effect rather than resolving it.
- The thermal feedback loop it implies — thicker wall -> more IR-opaque -> hotter interior ->
  higher saturation pressure -> thicker wall. Registered here as an **open question**,
  explicitly not modelled in v1, because the discrete-N model cannot say whether it
  converges.
- Conduction through the wall, and any mechanical failure mode other than hoop tension
  (buckling under external load, creep, fracture toughness).
- The carbon and mass cost of building the vessel — that is framing B, and it is moot until
  this question returns a feasible radius.

## Files

```
sim/thermal.py                      + greenhouse_factor, contained_temperature
sim/vessel.py                       NEW: wall_thickness, wall_transmission, max_vessel_radius
experiments/q3_vessel/prereg.yaml   NEW  (BLOCKED on grounding k)
experiments/q3_vessel/run.py        NEW
experiments/q3_vessel/RESULTS.md    NEW
tests/test_vessel.py                NEW
docs/bio_grounding_2026-09-02.md    + §9 wall PAR attenuation (k)
```

## Testing

Unit tests for each new function including the raise-on-invalid paths; the degeneracy
identity as a unit test; the closed-form positive control against the committed 0.6250 m
sizing; and each gate exercised against a deliberately broken input to confirm it fails for
the stated reason before it is trusted to pass.

## Success

Q3 succeeds if it returns a maximum vessel radius with a stated uncertainty traceable to
grounded inputs, and names which input decides it — or if it establishes that the radius
cannot be bounded without a number the literature does not supply, and says exactly which
number that is.
