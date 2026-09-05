# Bio-grounding: `leaf_mass_ratio` and `a_max`

Run 2026-09-02 via the `bio-grounding` ritual, against the parameters the Q1 final
review identified as loose: the two the calibration gate cannot observe. Q1's
`prereg.yaml` is frozen — **nothing here edits it.** This document constrains the
*next* registration.

Every citation below passed `ghostcite` 0.5.2 (deterministic CrossRef byline + year +
retraction gate), in two runs: 5 refs then 1 more, 0 findings after correction. Two
corrections the gate forced, both wrong-year: Poorter *New Phytologist* is CrossRef
2011 (not the commonly-cited 2012 print issue), and Poorter & Sack *Frontiers* is
2012 (I had first written 2011, conflating the two adjacent Poorter papers). Every number was computed against live `sim/`
code this session, with a positive control asserting the restored constants reproduce
the committed r\* values (67.2623 algal / 13.6851 vascular).

## 1. What the gate citations actually describe

The two gate sources resolve to specific organisms, and this matters more than it looks:

| class | gate source | organism the source is about |
| --- | --- | --- |
| vascular | Craine & Reich 2005 | *"Leaf-level light compensation points in shade-tolerant woody **seedlings**"* |
| algal | Richardson, Beardall & Raven 1983 | *"Adaptation of **unicellular** algae to irradiance: an analysis of strategies"* |

Richardson et al.'s own abstract: *"Analysis of data in the literature relating to
**microalgal** adaptations to different photon flux densities indicates that different
algal classes have significantly different light requirements for growth and
photosynthesis."* The paper is resolved to algal *classes* — dinoflagellates,
blue-green algae, diatoms.

**⚠️ The algal preset's `leaf_mass_ratio` does not describe the organism its own gate
describes.** `prereg.yaml` justifies `leaf_mass_ratio: 0.8` as
`# assumption: thallus mostly photosynthetic`. A *thallus* is a macroalga. The gate
that admits the value is calibrated on *unicellular* microalgae. Two different
organisms are being averaged into one preset.

## 2. `leaf_mass_ratio`, vascular — GROUNDED (bounded, not pinned)

> *"This is especially the case if the various fractions of the plant have values
> between 0.20 and 0.80. Adult trees exempted, most LMF and RMF values are within that
> range (see Poorter et al., 2012)."*
> — Poorter & Sack 2012, *Front. Plant Sci.* 3:259, §"Non-normality of fraction values"

Species-resolved instance from the same paper (*Deschampsia flexuosa*, final harvest):

> *"At the final harvest, LMF was 0.46 for the high-nutrient plants, and 0.31 for the
> low-nutrient plants"*

**Rule extracted:** LMF ∈ [0.20, 0.80] for anything that is not an adult tree; a woody
seedling sits inside that interval, and nutrient status alone moves a single species
across 0.31–0.46.

**Verdict on the current value:** `leaf_mass_ratio: 0.5` for the vascular preset is
**inside the cited range** and close to the well-fed *D. flexuosa* value. It is
defensible. What was missing was never the value — it was the *bound*.

**Consequence of the bound (computed):** with the gate held and LMF swept across its
cited range, vascular r\* is

| LMF | I_c (gate) | r\* |
| --- | --- | --- |
| 0.20 | 6.9519 | 7.6238 AU |
| 0.50 | 6.9519 | 13.6851 AU |
| 0.80 | 6.9519 | 17.7889 AU |

so the *literature-admissible* r\* interval is **[7.62, 17.79] AU** against a registered
band of [12, 22]. Grounding the parameter does **not** rescue the band — it extends the
reachable set *below* it. The gate reads 6.9519 at all three, unchanged.

## 3. `leaf_mass_ratio`, algal — the value is WRONG FOR THE ORGANISM

For a unicellular alga there is no non-photosynthetic *organ*. `leaf_mass_ratio` is
defined in this model as the fraction of organism mass that is photosynthetic tissue,
and the whole cell is that tissue, so **LMR = 1.0** by the model's own definition — not
0.8, and not for the reason the comment gives.

**Consequence (computed):** algal r\* moves 67.2623 → **75.4338 AU**, i.e. *further*
outside the registered [35, 55], with the gate reading an unchanged I_c = 0.4918.

Two coherent repairs exist, and they are a genuine fork for Q2:

1. **Keep the unicellular organism** (matching the gate source): set LMR = 1.0, and the
   parameter stops being free at all — it is pinned by the organism's structure.
2. **Keep the thallus** (a macroalga): then the *gate* is wrong, because Richardson et
   al. 1983 does not calibrate macroalgae, and a macroalgal compensation-point source is
   needed instead.

What is not defensible is the present combination, which takes the gate from organism 1
and the mass ratio from organism 2.

### DECIDED 2026-09-02: option 1 — the algal class is UNICELLULAR

Chosen because it is the only repair that costs one number. The gate citation
(Richardson, Beardall & Raven 1983) is already correct for a unicellular alga, so nothing
needs re-sourcing; `leaf_mass_ratio` becomes 1.0 and **stops being a free parameter**,
pinned by the organism's structure rather than by an assumption. Option 2 would have
required a new macroalgal compensation-point source *and* left LMR free needing its own
thallus-fraction citation.

Consequence, accepted deliberately: algal r\* moves to 75.4338 AU, *further* from Q1's
registered [35, 55]. This does not make the miss worse in any meaningful sense — Q1's band
is already reported as missed, and Q2 re-registers. Fixing the organism makes the miss
**interpretable** (the model overshoots for a coherent organism) instead of ambiguous (the
model overshoots for a chimera of two organisms).

**Binding on the next registration, not on Q1.** `experiments/q1_crossover/prereg.yaml`
stays frozen; Q1's committed numbers stand as run.

## 4. `a_max` upper bound — RESOLVED from data (and the ceiling turns out not to be the fix)

Closed 2026-09-02 by going to a **dataset** instead of a paper, via the data-aggregator.
Papers were all paywalled; the underlying measurements are CC-0.

**Source:** Westerband et al. (2022), *Australia-wide photosynthetic trait dataset*, Dryad,
[10.5061/dryad.j9kd51cgr](https://doi.org/10.5061/dryad.j9kd51cgr), CC-0. Authors include
Ian Wright and Owen Atkin. Column definition, verbatim from the deposit's README:

> *"Asat_area_micromol_m2.s: Light-saturated rate of photosynthesis at ambient CO2. Units
> are micromol of CO2 per meters squared per second."*

Those are exactly this model's `a_max` units. Computed from the deposit
(675 non-null measurements, 530 species, 67 sites):

| statistic | Asat, µmol CO₂ m⁻² s⁻¹ |
| --- | --- |
| min | 1.023 |
| median | 8.748 |
| p90 | 16.409 |
| p95 | 18.804 |
| p99 | 23.892 |
| **max** | **29.516** |
| mean | 9.566 |

**Unit honesty:** Asat is *net* light-saturated assimilation; this model's `a_max` is
*gross*. Gross = net + leaf respiration, so the comparable gross values are Asat + `r_d`.

**Result 1 — the vascular `a_max` = 10.0 is well grounded.** The empirical median gives a
gross `a_max` of 9.398 and r\* = 13.2032 AU, against the registered value's 13.6851 AU. The
preset sits essentially at the median of 530 species.

**Result 2 — the vascular gate was already doing the bounding.** No extra ceiling is needed
there: at the p90 value the gate *fails* (I_c = 3.9612, below the 5.3 floor). A two-sided
gate excludes high `a_max` on its own.

**Result 3 — and this is the one that matters — the empirical ceiling does NOT close the
algal hole.** At the observed **maximum across all 530 species**:

| Asat | gross `a_max` | I_c | algal gate | algal r\* |
| --- | --- | --- | --- | --- |
| median 8.748 | 8.988 | 0.5487 | **passes** | 63.6569 AU |
| p90 16.409 | 16.649 | 0.2925 | **passes** | 87.3236 AU |
| p99 23.892 | 24.132 | 0.2009 | **passes** | **no crossover in [0.5, 100] AU** |
| max 29.516 | 29.756 | 0.1626 | **passes** | **no crossover in [0.5, 100] AU** |

So the missing ceiling was **necessary but not sufficient**. Even the most productive leaf
ever measured in this 530-species survey passes the algal gate and yields no answer inside
the search window. **The defect is the algal gate's one-sidedness — its lower bound of
I_c = 0.0 — not the absence of an `a_max` ceiling.** A gate with no floor cannot exclude an
arbitrarily efficient organism, and efficiency is exactly what pushes r\* past the horizon.

**Fix that follows:** give the algal gate a real lower bound from microalgal compensation-
point data. Richardson, Beardall & Raven 1983 — already the algal gate's source — is a
survey of microalgal light requirements and is the natural place to get it.

**Scope caveat, stated plainly:** this dataset is *vascular* Australian plants. It bounds
the vascular class directly; it does **not** measure microalgae. It is used above only as a
deliberately generous borrowed ceiling, and the argument is *a fortiori* — if even a
vascular maximum fails to constrain the algal gate, a microalgal ceiling will not either.
A microalgal `a_max` ceiling is still unsourced.

## 4b. The decided organism turns the algal gate from blind into COMPLETE

Filed on 2026-09-02 as "the algal gate needs a lower bound on I_c." Working that item
produced something stronger, and it is exact rather than numerical.

**With `leaf_mass_ratio` = 1.0 — which the unicellular decision (§3) pins it to —**

$$r^* = \sqrt{C / I_c}, \qquad C = \text{TSI} \times \text{par\_fraction} \times \text{photons\_per\_j} = 2798.4852$$

Derivation: `I_c = k·r_d/(a_max − r_d)` gives `a_max/r_d − 1 = k/I_c`, and
`r* = sqrt(C/k · (a_max·lmr/r_d − 1))` with `lmr = 1` collapses to `sqrt(C/k · k/I_c)`.
The `k` cancels. Verified numerically against the live solver at 9 combinations of
`a_max` ∈ {5, 10, 25} × `k` ∈ {10, 20, 40} — every one matched to < 1e-3, including the
three that correctly predicted r\* beyond the 100 AU window.

**What this means.** For a unicellular organism, r\* is a pure function of the compensation
irradiance — the *exact quantity the gate measures*. The §2/C2 blindness does not merely
shrink; it **disappears**. The gate stops being a guard that cannot observe its referent
and becomes a complete observer of it. `a_max` and `k` still matter, but only through I_c,
so bounding I_c bounds r\* completely.

**So the filed fix was right, and the reason is stronger than the one filed.** A floor on
I_c maps one-to-one onto a ceiling on r\*:

| floor on I_c | implied ceiling on r\* |
| --- | --- |
| 0.05 | 236.58 AU |
| 0.1 | 167.29 AU |
| 0.2 | 118.29 AU |
| 0.5 | 74.81 AU |

**And it sharpens §1's headline finding into an exact statement.** The gate's existing
ceiling I_c ≤ 1.0 already implies **r\* ≥ 52.9007 AU**. The registered band [35, 55] AU
corresponds to I_c ∈ [0.9251, 2.2845]. Intersecting, the band is reachable only for
I_c ∈ [0.9251, 1.0] — **7.5% of the gate's own admissible interval, covering just
[52.90, 55] AU, or 10.5% of the band's width.** For the organism now decided, **89.5% of
the registered algal band was unreachable before the sweep ran** — worse than the 60.1%
measured at the old `leaf_mass_ratio` of 0.8.

Q1's algal result (I_c = 0.4918 → r\* = 75.4338 AU at lmr = 1.0) sits exactly on this curve.

**What is still missing is only the floor's VALUE.** The structure is settled; the number
is not. See §4c.

## 4c. Why the obvious dataset cannot supply that floor

Searched for microalgal compensation-irradiance data the same way §4 was closed. The
largest relevant open deposit is Amirian et al. (2026), *A Compilation of Marine
Photosynthesis–Irradiance Data from ¹⁴C Incubation Experiments*, Zenodo
[10.5281/zenodo.21908199](https://doi.org/10.5281/zenodo.21908199), CC-BY-4.0 —
111,209 measurements. It is the right organism (marine phytoplankton) and the wrong
instrument, for a structural reason worth recording:

- Only **164 of 111,209** rows (0.15%) have a negative photosynthesis rate, and only
  **6 of 39** report groups bracket zero — so a compensation point can be interpolated
  almost nowhere in it.
- Its own `dataType` labels are `photoinhibition` (64,167), `light-saturated` (46,656),
  `light-limited` (386). **0.35% of the compilation samples the light-limited end** — the
  end where a compensation point lives.

The cause is methodological: **¹⁴C incubation measures carbon uptake, not respiration**,
and a compensation point is exactly where uptake balances respiration. No amount of ¹⁴C
data yields one. The floor needs O₂-based P–R measurements on microalgal cultures, which a
second targeted search did not surface as an open dataset.

**Status: the gate's structure is now understood exactly (§4b); its floor value remains
unsourced.** Recorded so the next attempt does not re-mine ¹⁴C compilations.

## 4d. `t_opt` — grounded, and it says the FUNCTIONAL FORM is wrong, not the parameter

Q2's Gate 2 failed and its RESULTS.md §6 asked for a `t_opt` sourced for cold-adapted
tissue from somewhere other than the two anchors that gate it. Done here. The answer
inverts the diagnosis I recorded before Q2 ran.

**What I predicted:** that 298.15 K (25 °C) was a mesophyte optimum and a cold-adapted
organism would want a LOWER one. **What the literature says:** cold-climate
photoautotrophs have HIGH optima.

> *"The optimum temperature for both net assimilation of CO2 and photoprotective heat
> dissipation of three East Antarctic species was 20–30°C"*
> — Perera-Castro et al. 2020, *Front. Plant Sci.* 11:1178, abstract

> *"Polytrichastrum alpinum, which is associated with polar and alpine habitats, showed
> the highest optimum temperature (26.3 ± 0.7°C)"* — ibid., Results

Table 2 of that paper gives T_opt of ETRmax across six named Antarctic moss species
(*Bryum pseudotriquetrum*, *Ceratodon purpureus*, *Chorisodontium aciphyllum*,
*Polytrichastrum alpinum*, *Sanionia uncinata*, *Schistidium antarctici*) spanning
**19.0 ± 0.9 °C to 26.3 ± 0.7 °C**. The paper's title states the point: *"Antarctic Mosses
Have High Temperature Optima for Photosynthesis Despite Cold Climate."* The mechanism it
gives is one this model shares — tissue runs hotter than air:

> *"Antarctic mosses, however, can have canopy temperatures well above air temperature.
> At midday, canopy temperatures can exceed 15°C"* — ibid., abstract

A second, independent source disagrees, and the disagreement is real rather than noise:

> *"Optimal temperature for NP of BSC was 5 °C at Site Darwin, 7 °C at Site Garwood and
> 17 °C at Site Homburg."*
> — Colesie et al. 2014, *ISME J* 8:2104, on lichen-dominated biological soil crusts
> (Darwin and Garwood Antarctic; Homburg a moderate German site)

So measured optima for cold-climate photoautotrophs run **5–7 °C for Antarctic lichen
crusts** and **19–30 °C for Antarctic mosses**. Organism matters more than climate does.

### The decisive comparison

Under the LINEAR response Q2 implements, with `t_min` = 265.15 K, satisfying both held-out
anchors requires:

| anchor | admissible `t_opt` |
| --- | --- |
| 60–70% at 5 °C | [10.6, 13.7] °C |
| 30–40% at 0 °C | [12.0, 18.7] °C |
| **intersection** | **[12.0, 13.7] °C** |

**No measured value above falls in that window.** The lichen crusts sit below it (5, 7 °C),
the mosses above it (19–30 °C), and even the temperate crust (17 °C) misses. The window is
bracketed from both sides and contains nothing.

**Conclusion: the linear response is the defect, not `t_opt`.** A real temperature-response
curve is concave — it rises steeply out of the cold and flattens toward a broad optimum —
so a tissue whose optimum is 25 °C can still be at 60–70% of maximum at 5 °C. A straight
line from `t_min` to `t_opt` cannot do that: it forces the rate at 5 °C to be a fixed
fraction of the distance to the optimum. This is exactly what the spec said Gate 2 would
diagnose — *"if a curve pinned at its endpoints does not independently land in both
windows, the gate fails and the functional form is wrong"* — and it is NOT what I predicted
the failure would mean.

**Correction of the record:** Q2's `RESULTS.md` §5 attributes the gate failure to a
mesophyte-vs-cold-adapted `t_opt` mismatch. On this grounding that attribution is wrong in
direction: 298.15 K is *inside* the measured moss range (20–30 °C for net assimilation).
The implied band in its §4 ([285.15, 286.82] K) is not a corrected `t_opt` — it is the
window a linear form would need, and no organism measured here has an optimum there.

### What Q3 / a re-registered Q2 should do

1. Replace the linear response with a concave form — a beta or Arrhenius-with-deactivation
   curve — parameterized by `t_min`, `t_opt` and a shape parameter fitted to neither anchor.
2. Register `t_opt` **per class** from measurement, not one value for both: the lichen
   /algal class near 5–7 °C, a moss-like or vascular class near 20–26 °C. Both are cited
   above; neither is vascular, which remains the gap (see below).
3. Keep the two anchors held out. They have now done real work twice — first failing the
   gate, then falsifying my explanation of why.

**Still ungrounded:** a measured T_opt for cold-adapted VASCULAR tissue. Both sources above
are non-vascular (bryophyte, lichen). Körner's vascular rate anchors remain the only
vascular-specific temperature data in this project, and they cannot be used to set `t_opt`
without the circularity Gate 2 exists to prevent.

## 5. Honesty ledger (which layer each claim sits on)

| claim | status |
| --- | --- |
| Gate sources describe woody seedlings / unicellular microalgae | **real-mechanism-backed** — verified against both papers' own titles and abstract |
| LMF ∈ [0.20, 0.80] excluding adult trees | **real-mechanism-backed** — verbatim, ghostcite-clean |
| *D. flexuosa* LMF 0.31–0.46 | **real-mechanism-backed** — verbatim, species-resolved |
| Vascular LMR = 0.5 is defensible | **real-mechanism-backed** — inside the cited range |
| Unicellular alga ⇒ LMR = 1.0 | **plausible, definitional — NOT a measured value.** It follows from the model's definition plus the absence of a non-photosynthetic organ. No paper was read that reports a microalgal "leaf mass ratio", because the quantity is not normally defined for a single cell. Treat as a structural argument, not an observation. |
| Algal LMR = 0.8 "thallus mostly photosynthetic" | **convenient fiction** — the organism it invokes is not the organism the gate calibrates |
| `a_max` ceiling, vascular | **real-data-backed** — computed from 675 CC-0 measurements, 530 species (§4) |
| Vascular `a_max` = 10.0 is defensible | **real-data-backed** — sits at the empirical median |
| Empirical ceiling does not close the algal gate | **real-data-backed** — computed live; gate passes at the 530-species maximum |
| `a_max` ceiling, *microalgal* | **unresolved** — the dataset is vascular; borrowed a fortiori only (§4) |
| Cold-climate photoautotrophs have HIGH T_opt (19–30 °C mosses; 5–7 °C lichen crusts) | **real-mechanism-backed** — verbatim, species- and site-resolved, both refs ghostcite-clean (§4d) |
| The LINEAR response, not `t_opt`, is what fails Gate 2 | **derived** — the anchors' admissible window is [12.0, 13.7] °C and no measured optimum lies in it (§4d) |
| T_opt for cold-adapted VASCULAR tissue | **unresolved** — both sources are bryophyte/lichen (§4d) |
| r\* = sqrt(C / I_c) for a unicellular organism | **derived + numerically verified** — algebraic identity, checked at 9 (a_max, k) pairs against the live solver (§4b) |
| Gate ceiling I_c<=1.0 implies r\* >= 52.9007 AU | **derived** — direct consequence of the identity (§4b) |
| 89.5% of the algal band unreachable at lmr=1.0 | **derived** — exact, supersedes the 60.1% measured at lmr=0.8 (§4b) |
| Microalgal I_c floor VALUE | **unresolved** — 14C data structurally cannot supply it (§4c) |
| r\* values in §2 and §3 | computed live this session against `sim/`, positive-control checked |
| Tensile data for wood are sparse in the literature | **real-mechanism-backed** — the canonical reference states it in its own property definition (§7) |
| MOR is the accepted conservative substitute for tensile strength | **real-mechanism-backed** — verbatim, and the error direction is stated (§7) |
| Clear-wood MOR 45–139 MPa, median 80 | **real-data-backed** — extracted from 111 species-rows of the metric strength tables (§7) |
| Wall thickness 0.36–1.11 m, median 0.625 m | **derived** — the doc's own thin-wall relation at the MOR range (§7) |
| A comet organism's tissue is wood-like | **convenient fiction** — nothing grounds this; §7 grounds the number, not the analogy |
| Microalgal I_c floor VALUE (2nd attempt) | **STILL unresolved** — the right paper was found and is CC-BY, but publisher-blocked (§8) |
| I_c = R_d/alpha with a hard ceiling on alpha | **plausible, MY OWN derivation, source NOT verified** — a lead for the next pass, not a grounding (§8) |
| Ice PAR absorption coefficient 0.00074–0.52061 /m | **real-data-backed** — computed from Warren & Brandt's own published table, 31 rows in 400–700 nm (§9) |
| A single scalar `k` describes the wall | **FALSE, and the spec assumed it** — k spans a factor of 701 across PAR; the wall is a spectral filter, not an attenuator (§9) |
| My declared band k ∈ [0.1, 5.0] /m | **WRONG — 2 orders too high at the blue end.** Had the variance decomposition been registered on it, the grounded data would have falsified it (§9) |
| Scattering, not absorption, sets attenuation in real ice | **real-data-backed** — transport length 10–100 m vs absorption 100–400 m at 400 nm (§9) |
| Diffusion length L_d = sqrt(l_abs·l_tr/3) | **derived, standard radiative transfer** — the formula is textbook; its application to this geometry is mine and unvalidated (§9) |
| Wall transparency limits organism radius | **WITHDRAWN by §10** — §9's R_max paired WOOD's sigma with ICE's k. Recomputed consistently the status is **UNRESOLVED**: it binds at 10 kPa (1.2–7.4 km), not at 882 Pa (§10) |
| Ice tensile strength 0.7–3.1 MPa | **real-data-backed, AT ONE REMOVE** — verbatim from Hirata et al. 2022 (green OA) quoting Petrovic 2003 (closed); Petrovic's byline verified via CrossRef + OpenAlex, but the paper was not read (§10) |
| §9's R_max values (sigma = 80 MPa) | **WRONG BY ~53x** — 80 MPa is §7's clear-wood MOR; the k it divides is pure ice. No material has both (§10) |
| Strength and transparency do not collide at any modelled radius | **RETRACTED** — at 10 kPa a consistent ice wall collides at 1.2–7.4 km, below the assumed 10 km, across the whole grounded sigma range (§10) |
| Framing A's answer is decided by k | **FALSE** — k was the input that got grounded, but p and sigma are what flip the answer inside the registered bracket (§10) |
| Registered pressure bracket p ∈ [882 Pa, 10 kPa] | **SELF-INCONSISTENT** — its floor is p_sat at the UNCONTAINED temperature, but containment is mandatory and raises T; N=1 needs 18.02 kPa, 1.8x ABOVE the bracket top (§11 S1) |
| Flat PAR scalar combined with full-spectrum `a_max`, for a CONTAINED organism | **OPEN MISMATCH, and it reaches Q1/Q2/Q2b** — the wall is a blue-pass filter, so the light field and the photosynthetic parameters describe different spectra (§11 S2) |
| L_d combining Warren & Brandt with Ackermann | **MATERIAL MISMATCH** — pure bubble-free ice absorption against dust-laden glacial ice scattering; the ledger flagged the formula, not its two objects (§11 S3) |
| Scafaro 2023 / June 2004 numbers used by `sim/thermal.py` | **real-data-backed** — 29.4/32.7 °C, 49 species and the Ω definition all verified VERBATIM against the gold-OA primary text; the code docstrings match exactly (§11 S4) |
| Adaptation premise applied to the ALGAL preset | **organism mismatch** — a whole-leaf Rubisco-deactivation result from 49 vascular C3 land plants, its Gaussian form derived on SOYBEAN LEAVES, supplying the thermal premise for a unicellular alga (§11 S4) |
| `PAR_FRACTION = 0.45` used in a top-of-atmosphere function | **WRONG OBJECT** — the measured AM0 PAR energy fraction is **0.3879**; 0.45 exceeds even the AM1.5G *surface* value (0.4297). PAR overstated 1.160x in Q1/Q2/Q2b, unconditionally (§12 S5) |
| §11's clearance of `TSI x PAR_FRACTION x PHOTONS_PER_J` | **FALSE CLEAR, WITHDRAWN** — cleared by reading three labels that all said "top of atmosphere". Measuring showed one of them is not (§12 S5) |
| `PHOTONS_PER_J = 4.57` | **real-data-backed** — re-derived as 4.553 umol/J from the ASTM G173-03 AM0 spectrum over 400-700 nm; 0.4% agreement (§12 control C) |
| Size of S2 behind a self-consistent ice wall | **BOUNDED BELOW, not resolved** — 18.7-34.9% of assumed PAR photons survive at the self-consistent 18.02 kPa; 3.3-6.2x total overstatement with S5. Pure-ice absorption only, so an UPPER BOUND on transmission (§12) |
| `a_max`'s measurement temperature | **NOT RECORDED IN THE SOURCE** — the Westerband deposit has no leaf-temperature column, while standardising `Vcmax25` to 25 C in the same file. Q1/Q2/Q2b then assume THREE DIFFERENT anchors for it; the readings differ 1.27-8.65x (algal) (§13 S6) |
| §11's clearance of `respiration(r_d, t)` | **WITHDRAWN** — cleared the respiration side; nothing asked what temperature the ASSIMILATION side's grounded `a_max` describes (§13 S6) |
| `T_interior = (N+1)^0.25 * T_eq` | **PREMISE FALSIFIED BY THIS PROJECT'S OWN OPTICS** — it assumes an SW-TRANSPARENT wall; a pressure-bearing ice wall transmits only 16-23% of solar energy (NIR is 53% of TSI and ice absorbs it). Correct form is `(1+tau)^0.25 * T_eq`; the published formula is the tau=1 case (§13 S7) |
| S1's "the registered pressure bracket is self-inconsistent" | **WITHDRAWN** — S1 assumed tau=1. Solved as a fixed point the self-consistent p is **2.6-3.5 kPa, INSIDE [882 Pa, 10 kPa]**, 5.2-6.9x below S1's 18.02 kPa. S1's MECHANISM stands; its magnitude and verdict do not (§13 S7) |
| Framing A (strength vs transparency collide at R = 10 km) | **SPLIT BY ICE STRENGTH** — at the self-consistent pressure R_max is 21.4 km (3.1 MPa), 11.9 km (1.5), 6.40 km (0.7). Binds only at the weak end (§13 S7) |
| §12's use of G173's 1366.1 normalisation with the project's 1360.8 TSI | **CHECKED, TRANSFERABLE** — the PAR fraction is dimensionless, a property of spectral SHAPE not scale; residual <= 0.39%, 41x smaller than S5. Stated rather than waved through (§13) |
| "One IR-opaque shell == halving `area_ratio`, identical to 5.7e-14 K" | **TRUE ONLY AT tau = 1** — with a measured wall the two differ by **31-36 K**. The 5.7e-14 K agreement compared two expressions computing the SAME ASSUMPTION (§14) |
| S5 and S6 as INDEPENDENT deferred defects | **NOT INDEPENDENT** — each alone leaves all six Q1 verdicts standing; TOGETHER (S5 + S6 reading B) vascular k=100 falls to r*=11.51, OUTSIDE the registered [12, 22]. The effects compose multiplicatively (§16). ⚠️ **THAT ARM IS READING C, NOT B** — §18 S10 |
| The ICE wall's own temperature | **S8: MOLTEN AT 1 AU** — section 13's two-body balance puts the shell at `Ts = T_eq` exactly, independent of tau: **5.16 C**, with the interior face at 24.10 C. Ice melts at 0 C, and that threshold only DROPS with pressure. No part of the wall is ice where sections 13-15 computed every number (§17) |
| Where an ice vessel holding liquid water CAN exist | **A 0.11-0.16 AU ANNULUS, AND 1 AU IS OUTSIDE IT** — inner edge 1.0381 AU (tau-independent), outer edge 1.1446-1.2030 AU. Q2b's algal temperature limit, 1.1945 AU, sits just beyond it. Re-solving the fixed point at the inner edge takes p 3.002 -> 2.287 kPa: inside the bracket, DOWNWARD, the third effect to point that way (§17) |
| `albedo = 0.0` paired with a wall concluded to be ICE | **S9, AND IT PARTLY REVERSES S8** — the shell reaches the melting point at 1 AU at albedo **0.0721**; at 0.10 it is -2.07 C. S8 holds in the model as written and its MAGNITUDE does not survive S9. Not internally inconsistent: Beer-Lambert models pure absorption, matching albedo=0 — consistently wrong, which is why no single-expression check could see it (§17) |
| §11's clearance of `equilibrium_temperature` | **HAS NOW MISSED THREE THINGS** — S7, S8 and S9, while remaining literally accurate. A clearance true about the EXPRESSION says nothing about the OBJECT; the bullet cannot be made more correct, only replaced by a different question (§17) |
| `PHOTONS_PER_J` applied behind the blue-pass wall | **CHECKED AND CLEAN** — `size_par_filter.py` computes photon- and energy-weighted transmission separately and applies the photon-weighted fraction to a photon-weighted flux. The obvious next instance of §12's failure is not present (§17) |
| Q1's "the vascular default-k prediction HELD" | **CONDITIONAL ON THE S6 DECISION** — survives S5 + reading A (12.7058, inside); fails S5 + reading B (11.5100, misses the floor by 4.1%). The registration choice decides the published verdict (§16). ⚠️ **THE CHOICE IS A-vs-C; B IS INELIGIBLE** (§18) |
| S5's reach into Q2 | **NONE** — Q2 exits 2 at a purely thermal gate before any PAR-dependent code runs; unchanged in every digit. Q2b's `gates.csv` is byte-identical and its binding limit stays `temperature` at every omega (§16) |
| `a_max`'s three anchors, sized | **52.66 K SPREAD** — 293.00 K (Q1), 298.15 K (Q2), 278.31 K (Q2b algal), 330.97 K (Q2b vascular). Re-anchored to a common 293 K the paths need `a_max` 10.0 to 367.53; the 36.75x extreme is inside the vascular class Gate B already FAILED, so the live factor is algal's 1.71x (§16) |
| §16's "reading B" arm | **S10: IT IS NOT READING B** — the factor is `temperature_response(293, 265.15, 298.15)` = 0.8439, Q2's LINEAR ramp at Q2's DECLARED 25.00 °C `t_opt`. Reading B's own definition (the PEAK of Q2b's Gaussian at the ADAPTED optimum) gives 0.0272 — **31.0×** apart. Confirmed by reproducing §16's published 12.3971 exactly from `a_max = 8.4394`. Every number §16 published from the arm is right; the name is wrong (§18) |
| True reading B applied to Q1 | **S11: INELIGIBLE — IT REMOVES THE RESULT, NOT THE VERDICT** — at Ω ∈ {10, 15, 20} the vascular organism has **no compensation point at any irradiance**; at Ω ∈ {25, 30} `I_c` is 187.92 and 47.61 against a gate ceiling of **9.0**. `net_carbon()` reads neither Ω, `area_ratio` nor `t_opt`, so applying B imports three objects Q1 does not have (§18) |
| The criterion that eliminates reading B | **WHERE THE CORRECTION LANDS, NOT HOW BIG IT IS** — Ω is registered only in `q2b_adapted/prereg.yaml:67`, zero occurrences in Q1's and Q2's. A reading that makes a registered result depend on an unregistered parameter is a **re-registration**, not a reading. Size alone would have picked the same answer for the wrong reason (§18) |
| §16's one-number-per-reading Q2b corrections | **EACH IS A FUNCTION OF Ω** — reading A algal spans 86.5049 (Ω=10) to 12.7091 (Ω=30), a **6.8×** spread; reading C algal spans **33.1×**. §16's published 17.1498 is reproduced exactly, and is the Ω=20 cell of that row (§18) |
| `a_max`'s measurement temperature, after §18 | **STILL NOT GROUNDED** — §18 narrows which internally consistent reading may be adopted; it does not recover the anchor. §13's "not recorded in the source" stands. Open route: the deposit's `Vcmax25` was derived from `Asat` by the one-point method, which passes through a leaf-temperature term, so the anchor may be recoverable by inversion. **NOT ATTEMPTED** — Dryad file downloads now 401 without a bearer token and the public routes return a WAF challenge; no workaround attempted (§18) |
| Q2b's preset source vs `sim/organism.py` | **UNGUARDED, AND THEY DIFFER** — Q1 runs `assert_presets_match`; Q2b has no equivalent. `leaf_mass_ratio` is 0.8 in `organism.py` and 1.0 in Q2b's prereg. The difference is deliberate and commented, but the name `algal` denotes two organisms and only one experiment would notice (§16) |
| The `area_ratio` degeneracy | **REAL BUT RESCALED, ~2.7x smaller** — T depends on `area_ratio/(1+tau)`, so a contained sphere presents at effective 2.98-3.17, not 2.0 (§14) |
| "Q2b's algal band is not a statement about shape alone" | **REPLACED** — the band [3.630, 4.311] is a statement about shape CONDITIONAL on containment: a contained sphere presents BELOW its floor, and landing inside it would need a true `area_ratio` of 4.58-5.79, more extreme than a sphere (§14) |
| "Two shells need 78.9 kPa" | **WITHDRAWN** — from `3^0.25*T_eq` = 93.13 C; at measured tau the interior is 25.67-32.80 C. Same falsified transparency premise that took S1's 18.02 kPa (§14) |
| §11 S3 ("pure ice absorption divided by dusty ice scattering") | **WITHDRAWN — S3 IS FALSE.** §9's `L_d` uses Ackermann's OWN absorption AND scattering; 18.3-115.5 m reproduces exactly from them, S3's attribution gives 67.0-211.8 m (§15) |
| §10's "the scattering caveat is unaffected" | **FALSE** — `R_max` is linear in sigma there too. With ice sigma: 11.8-330 km, not 1345-8508 km. Conclusion survives, margin collapses 134x -> 1.2x (§15) |
| Dust's effect on section 13's tau | **DIRECTION PINNED, magnitude still ungrounded** — a DECLARED dust floor from Ackermann's diffusion lengths gives tau 0.216-0.282 and p 2.21-2.81 kPa, always INSIDE the bracket and always DOWNWARD. S3 cannot overturn S7, only deepen it (§15) |
| A comet organism's wall is ice | **convenient fiction** — §9 grounds ice, not the identification |
| Antarctic dust loading bounds an organism's wall impurities | **convenient fiction** — no connection whatsoever; used only to show scattering CAN dominate (§9) |

## 6. What this changes for Q2

- Registering `leaf_mass_ratio` with a band, not a point, and taking the band from
  Poorter & Sack (2012) rather than from an inline comment.
- Deciding the algal organism **before** registering: unicellular (LMR pinned at 1.0,
  gate already correct) or macroalgal (LMR free, gate must be re-sourced).
- **Give the algal gate a lower bound on I_c** — confirmed as the right lever, and §4b now
  shows why it is *sufficient*: once the organism is unicellular, r\* = sqrt(C/I_c), so a
  floor on I_c is exactly a ceiling on r\*. Only the floor's value is still unsourced (§4c).
- **Register the algal band in I_c, not in r\*.** They are interchangeable for a unicellular
  organism, and I_c is the quantity the gate can actually check — which would have made the
  [35, 55] AU band's 89.5% unreachability visible at registration time rather than after.
- **Register the gate's reachable r\* interval alongside the predicted band.** A band the
  gate cannot reach is not a prediction — §2 shows the grounded parameter range and the
  registered band only partly overlap.

## 7. Wood tensile strength — GROUNDED, and it makes the wall 3.75x thicker

**Trigger.** `docs/prior_art_2026-09-01.md` §4 flags "**unknown:** a quotable bulk *tensile*
strength for wood", and its derived sizing leans on Gibson's *compressive* 300 MPa (densest
palm) as an order-of-magnitude proxy. Q3 cannot report a wall thickness that rests on a
compressive number.

**The gap is real, not a search failure.** The canonical engineering reference says so in
its own definition of the property: "Relatively few data are available on the tensile
strength of various species". Its species tables (5-3a/5-4a/5-5a) carry modulus of rupture,
compression parallel and perpendicular, shear parallel, and tension **perpendicular** — and
no tension-**parallel** column at all. So §4's `unknown` was correctly flagged.

**What the reference supplies instead is a RULE, and the rule is what to port:**

> "In the absence of sufficient tension test data, modulus of rupture values are sometimes
> substituted for tensile strength of small, clear, straight-grained pieces of wood."

> "The modulus of rupture is considered to be a low or conservative estimate of tensile
> strength for clear specimens (this is not true for lumber)."

The direction of the error is stated, and it is the safe direction for a pressure vessel:
MOR **under**-estimates tensile strength, so a wall sized from MOR is too thick, never too
thin. That is what makes it usable as a substitute rather than merely a related number.

**Values.** MOR at 12% moisture content, extracted from the metric strength tables,
n = 111 species-rows. Wall thickness from the doc's own thin-wall relation, sigma*t = p*r/2
= 5e7 N/m at p = 10 kPa, r = 10 km:

| statistic | MOR (MPa) | wall thickness t |
| --- | --- | --- |
| min | 45 | 1.1111 m |
| 10th pct | 59 | 0.8475 m |
| **median** | **80** | **0.6250 m** |
| 90th pct | 117 | 0.4274 m |
| max | 139 | 0.3597 m |
| *(current doc proxy: Gibson compressive)* | *300* | *0.1667 m* |

**Consequence: the registered sizing is optimistic by 3.75x at the median.** 0.17 m of "the
strongest tissue" becomes 0.625 m of median clear wood, and 1.11 m at the weakest species in
the table. The qualitative claim in §4 — that this is metres of parenchyma-grade material,
not a thin skin — survives and strengthens.

**Where this stops.** MOR is measured on clear, straight-grained, defect-free Earth-grown
specimens at 12% MC. Nothing here establishes that a comet organism's tissue is wood, and a
vessel wall is loaded very differently from a bending test-piece. This grounds the NUMBER the
sizing needs; it does not license the analogy that the organism is made of oak.

## 8. Microalgal I_c floor — NOT GROUNDED this pass. Recorded as a failed attempt.

The second target of this pass was the floor on `I_c` that §4b/§4c show is exactly a ceiling
on r\*. **It was not obtained.** What was tried, so the next attempt does not repeat it:

- **Yang X (2020)**, "Quantifying photosynthetic performance of phytoplankton based on
  photosynthesis-irradiance response models" (10.1186/s12302-020-00306-9) is the right paper:
  seven phytoplankton species, four P-I models, and it reports the light compensation point
  `I_c` explicitly. It is CC-BY gold OA. **The values are in the tables, and the tables were
  not reachable**: springeropen redirects to a Springer IdP auth wall, the DA MCP reports no
  fetchable open-access full text, and the record is not in EuropePMC. The abstract gives
  only the ordering (*Platymonas subcordiformis* < *Dunaliella salina* / *Isochrysis
  galbana*), not the numbers.
- Abstract-scoped searches for numeric compensation irradiances returned nothing usable;
  these values live in tables, which OpenAlex does not index.

**A better structural route, flagged as UNVERIFIED reasoning, not a result.** On the linear
low-light limb, P_net = alpha*I - R_d, so `I_c = R_d / alpha` by definition. alpha has a hard
physical ceiling — the Z-scheme needs a minimum number of photons per O2 — so a floor on
`I_c` follows from a floor on maintenance respiration, which cannot be zero for a living
cell. If that holds, the registerable quantity is a respiration floor plus a physical
constant, neither of which is a fitted parameter. **This is my own derivation. The photon
requirement was NOT verified against a source this pass** (the OA copies of the two reviews
that state it were also publisher-blocked), so it is recorded here as a lead, not a
grounding. Do not cite it until the constant is quoted from a real source.

## 9. Wall PAR attenuation `k` — GROUNDED, and it FALSIFIES the constraint it was meant to set

> **⚠️ PARTIALLY WITHDRAWN 2026-09-04 by §10, same day.** The `R_max` numbers below pair
> §7's WOOD tensile strength (80 MPa) with this section's ICE absorption coefficient. No
> material in this project's grounding has both properties. With an internally consistent
> ice wall the constraint DOES bind at the top of the registered pressure bracket. **Read §10
> before citing anything in the "constraint does not bind" paragraph.** Everything else in
> §9 — the x701 spectral spread, the 135x band error, the scattering caveat — is unaffected.
>
> ⚠️⚠️ **CORRECTED 2026-09-05 by §15: 'the scattering caveat' IS affected.** `R_max` is LINEAR
> in sigma there too. With ice sigma its `R_max` is 11.8–330 km, not 1345–8508 km — the
> conclusion survives but the margin collapses from 134x to 1.2x. Second wrong item in this
> one banner.

This was the blocker the Q3 spec named: `k` could not be declared by me, because a
one-at-a-time sweep made `k` dominate `R_max` by x50 and I had chosen its band. Grounding it
changed the answer, which is the point of having refused to register it.

**Source and route.** Warren & Brandt (2008), 10.1029/2007JD009744, is the standard
compilation of ice optical constants; it is closed access, but its abstract states *"Tables of
the revised optical constants are available on a website"* `[Q]`, and that site
(`atmos.uw.edu/ice_optical_constants/`) serves the primary table as
`IOP_2008_ASCIItable.dat` under HTTP 200 to plain curl. **The paywall was routed around by
taking the data, not the paper** — the same move that closed §7 via the public-domain Wood
Handbook. Column meanings were read off the host page rather than assumed: *"column 1:
wavelength (microns) column 2: m re column 3: m im"* `[Q]`. 486 of 487 lines parsed; 31 rows
lie in PAR. The parse count is asserted in the extraction script, because §8's lesson was
that a parser reporting a confident partial result is the failure mode here.

**The number.** Absorption coefficient `k_abs = 4*pi*m_im/lambda`:

| lambda | m_im | k_abs (1/m) | absorption length |
| --- | --- | --- | --- |
| 400 nm | 2.365e-11 | 0.00074 | 1345.9 m |
| 550 nm | 2.289e-09 | 0.05230 | 19.1 m |
| 680 nm (chl-a red peak) | 2.090e-08 | 0.38623 | 2.6 m |
| 700 nm | 2.900e-08 | 0.52061 | 1.9 m |

**`k` is not a scalar, and the spec was wrong to treat it as one.** Across PAR it spans a
factor of **701**. A single `k` cannot represent this wall: it is a spectral filter. At the
committed 0.625 m thickness the wall passes 0.9995 at 400 nm and 0.7223 at 700 nm; by 6.25 m
(R = 100 km) that is 0.9954 against 0.0386, a blue/red ratio of 25.8. **A thick clear wall
does not dim the interior so much as redden-strip it** — it removes the red band chlorophyll a
uses most and leaves the blue Soret band. That is a real, grounded architectural consequence,
and the scalar-`k` model in the spec cannot express it. Same root class as the `area_ratio`
degeneracy the spec itself caught: a parameter that cannot represent what it is trusted for.

**My declared band was wrong, in the direction that flattered the question.** The spec
declared `k` in [0.1, 5.0] /m. The grounded blue end is **0.00074 /m — 135x smaller than my
floor.** Registering the variance decomposition on my band would have produced a result the
data falsifies. The refusal to register was correct, and it is the only reason this is a
grounding rather than a retraction.

**The constraint does not bind.** `[WITHDRAWN 2026-09-04 — §10: this sigma is WOOD's and
this k is ICE's. With a consistent ice wall the constraint DOES bind at 10 kPa.]` With
grounded `k` at sigma = 80 MPa and tau_min = 0.01:

| p | blue end | red end |
| --- | --- | --- |
| 882 Pa (saturation) | 1.12e6 km | 1605 km |
| 10 kPa (Paul 2004) | 9.92e4 km | 141 km |

Against an assumed organism radius of 10 km, the transparency ceiling is **14x to 5 orders of
magnitude too high to matter.** PAR-integrated transmission (flat weighting, DECLARED
assumption) does not fall to 0.5 until R = 213.6 km at 10 kPa. **Framing A's hypothesis — that
strength and transparency collide at a finite, interesting radius — is FALSIFIED for pure
ice.** The collision exists, but it sits far outside any radius the project has reason to model.

**What actually binds is scattering, and it is not groundable for this organism.** The above
is absorption in pure bubble-free ice — a best case. Ackermann et al. (2006),
10.1029/2005JD006687, measured deep South Pole ice in situ: at 400 nm the effective (transport)
scattering length is 10–100 m against an absorption length of 100–400 m, with strong forward
scattering, and below 1450 m *there are no bubbles* — the residual scattering is dust. Treating
the wall as a diffusive slab (`L_d = sqrt(l_abs*l_tr/3)`, standard, but applied here by me and
not validated against a measurement) gives a diffusion length of 18–116 m, i.e. **real ice
attenuates roughly 24x more strongly than pure-ice absorption alone**, dropping `R_max` at
400 nm to 1345–4146 km. Still far above 10 km.

So the honest state is: **the wall's transparency is set by its impurity content, not by ice
physics, and nothing grounds the impurity content of a hypothetical organism's wall.**
Antarctic dust loading is used above only to show that scattering CAN dominate absorption; it
says nothing about biology. This is a real residual gap, and unlike §8's it cannot be closed by
finding a better PDF — no measurement of this quantity exists, because the object does not.

**Consequence for Q3.** The registered question as specced asks for a radius the transparency
constraint does not set. Q3 must either be re-registered against the constraint that does bind
(mass and carbon cost — framing B, previously deferred as moot pending this answer, and no
longer moot), or be registered as the falsification above with the spectral-filtering result as
its finding. That decision belongs to the next pass, not to this grounding.

## 10. The sigma that produced §9's falsification is WOOD's and the k is ICE's — no wall is both

**Trigger.** Re-reading §9 while scoping Q3's re-registration, to check which constraint
framing B would be inheriting as already-settled.

**The defect.** §9 computes `R_max` "*with grounded `k` at sigma = 80 MPa*". 80 MPa is §7's
median clear-wood modulus of rupture, extracted from 111 species-rows of the Wood Handbook.
`k` is Warren & Brandt's absorption coefficient for pure bubble-free ice. So

```
R_max = 2*sigma*|ln tau_min| / (k*p)
```

was evaluated for a material simultaneously as strong as clear oak and as transparent as
bubble-free ice. **Nothing in this project's grounding supplies such a material.** The two
inputs describe two different substances and the quotient is a property of neither. This is
not a rounding concern: it is a factor of ~53 on the load-bearing quantity, in the direction
that flatters the conclusion §9 drew.

**Grounding sigma for the material `k` actually describes.** Petrovic (2003) is the canonical
review and is closed access. Its value is quoted verbatim by a peer-reviewed, green-OA paper:

> "The tensile strength of non-porous pure water ice varies from 0.7 to 3.1 MPa, depending on
> the temperature, strain rate, and minor components (Petrovic, 2003)." `[Q]`
> — Hirata et al. (2022), *Icarus*, 10.1016/j.icarus.2022.114919

Petrovic's byline was verified independently via CrossRef and OpenAlex (J. J. Petrovic,
*J. Mater. Sci.* **38**:1–6, 2003, 619 citations), and Hirata et al.'s reference entry matches
that metadata exactly. **The value is grounded AT ONE REMOVE**: quoted from a public paper
that cites the closed original. Petrovic was not read directly. Recorded at that layer, not
higher.

The materials now agree: Warren & Brandt's `k` is pure bubble-free ice, Petrovic's range is
non-porous pure water ice. Same substance, for the first time in this calculation.

**Recomputed.** Positive control first — the closed form reproduces §9's own published
numbers (141.5 km against its 141 at 10 kPa/700 nm; 1.129e6 against its 1.12e6 at
882 Pa/400 nm), so sigma is the only thing that changes below. `tau_min` = 0.01 throughout.

| p | band | §9's value (sigma = 80 MPa, WOOD) | grounded ice (sigma = 0.7–3.1 MPa) | binds at R = 10 km? |
| --- | --- | --- | --- | --- |
| 882 Pa | 400 nm | 1.13e6 km | 9878 – 43750 km | no |
| 882 Pa | 550 nm | 1.60e4 km | 140 – 619 km | no |
| 882 Pa | 680 nm (chl-a red peak) | 2163 km | 18.9 – 83.8 km | no — margin 1.9x |
| 882 Pa | 700 nm | 1605 km | 14.0 – 62.2 km | no — **margin 1.4x** |
| 10 kPa | 400 nm | 9.96e4 km | 871 – 3858 km | no |
| 10 kPa | 550 nm | 1409 km | 12.3 – 54.6 km | no — margin 1.2x |
| 10 kPa | 680 nm (chl-a red peak) | 191 km | 1.67 – 7.39 km | **YES** |
| 10 kPa | 700 nm | 141 km | 1.24 – 5.48 km | **YES** |

**Framing A is not falsified. Its answer flips inside the project's own declared input
bracket.** The Q3 spec registers `p` as bracketed 882 Pa – 10 kPa (saturation floor to Paul
2004's demonstrated-viable hypobaric pressure). At the top of that bracket, an internally
consistent ice wall collides with transparency in the red band at **1.2–7.4 km — below the
10 km radius the project assumes** — across the entire grounded ice-strength range. At the
bottom of the bracket it does not collide, but the margin at the weak end is **1.4x, not the
"14x to 5 orders of magnitude" §9 claims.**

So the honest status of framing A is **UNRESOLVED, not falsified**, and what decides it is
`p` and `sigma` — not `k`, the input the spec blocked on and the one that was actually
grounded first.

**What §10 does not touch — CORRECTED, same pass.** The ×701 *spread* stands: it is a property
of `k` across wavelength and no sigma enters it. But this section's first draft claimed the
spectral-filter result stood "unchanged", and **that overclaimed.** §9's PER-THICKNESS
transmission figures — *"at the committed 0.625 m thickness the wall passes 0.9995 at 400 nm and
0.7223 at 700 nm"* — take their thickness from WOOD (0.625 m at 80 MPa) and their `k` from ICE.
Same defect, same section, one sentence I had just declared safe. Recomputed at 10 kPa / 10 km
with a consistent ice wall (positive control: the closed form returns the committed 0.6250 m at
80 MPa before anything changes):

| sigma | wall t | 400 nm | 550 nm | 680 nm | 700 nm |
| --- | --- | --- | --- | --- | --- |
| wood 80 MPa (§9's) | 0.625 m | 0.9995 | 0.9678 | 0.7855 | 0.7223 |
| ice 3.1 MPa | 16.1 m | 0.9881 | 0.4302 | 1.97e-3 | 2.26e-4 |
| ice 1.5 MPa | 33.3 m | 0.9756 | 0.1749 | 2.56e-6 | 2.91e-8 |
| ice 0.7 MPa | 71.4 m | 0.9485 | 2.39e-2 | 1.04e-12 | 7.08e-17 |

**The conclusion survives and gets far stronger; every number supporting it changes.** A
consistent ice wall is not a mild reddening filter — it is a **blue-pass filter that is opaque
in the red**, blue/red contrast 3.4e7 at ice-mid against §9's quoted 25.8. Chlorophyll a's Q
band is not attenuated, it is *gone*; only the Soret band survives. The rest of §10 — the
`R_max` correction, the 135x band error, the `area_ratio` degeneracy, the contained-temperature
result — is unaffected.

**This was found by applying §10's own rule to the rest of the document, and it is the third
instance of the class in one section.** Recorded because the rule caught a case its own author
had explicitly cleared one paragraph earlier: **naming a defect class does not exempt the
sentence that names it.** The 135x band error stands. The
`area_ratio` degeneracy stands. The contained-temperature result (`T_interior =
(N+1)^0.25 * T_eq`) stands. What is withdrawn is one sentence: that strength and transparency
do not collide at any radius worth modelling.

**Root class, and the rule this buys.** §9 and the Q3 spec each caught *a parameter that
cannot represent what it is trusted for* — the scalar `k`, and `area_ratio` carrying two jobs.
§10 is the same class one level up: two parameters that each faithfully represent a real
material, combined into a quotient that represents none. The rule:

> **A grounded input is not safe merely because it is grounded. A pair of grounded inputs
> must be shown to describe the same object before they may be combined.**

Grounding `sigma` (§7) and grounding `k` (§9) were each correct work. The defect was created
by putting them in one equation, and it survived because both halves had citations. **Every
check in §9 was a check on one input at a time, and the error lived only in the pairing** —
which is why none of them could see it.

## 11. The pairing sweep — applying §10's rule to the whole project

**Trigger.** §10 produced a rule; a rule's first job is to be applied to everything the author
already wrote. §10 found one mismatched pair by accident and its own first draft cleared a
sentence that had the same defect (see §10's correction). This is the deliberate sweep.

**Method.** Inventory every sourced number in `sim/`, the three `prereg.yaml` files and §§1–10,
recording for each **the object it describes** — not just its value and citation. Then take
every expression that combines two or more of them and ask whether those objects are the same
material, the same organism, the same spectrum, the same condition.

### Findings

**S1 (NEW, and it is the sharpest thing in this document). The registered pressure bracket is
computed from a temperature that the project's own settled result says cannot occur.**

> ⚠️⚠️ **VERDICT WITHDRAWN 2026-09-04 by §13 S7, same day.** Everything below assumes
> `T_interior = 2^0.25 · T_eq`, i.e. a fully SW-TRANSPARENT wall. The project's own ice optics
> falsify that premise: a pressure-bearing wall transmits 16–23% of solar energy. Solved as a
> fixed point, the self-consistent pressure is **2.6–3.5 kPa — INSIDE the registered bracket**,
> not 18.02 kPa above it. **S1's MECHANISM stands** (the floor is still `p_sat` at the
> uncontained temperature); **its magnitude and its verdict do not.** Read §13 S7 before citing
> any number below.

Q3's spec registers `p ∈ [882 Pa, 10 kPa]`. The floor is the saturation pressure at 5.16 °C —
the algal sphere's **uncontained** equilibrium temperature. But §37 of that same spec settles
that containment is mandatory and that **the vessel sets the temperature**,
`T_interior = (N+1)^0.25 · T_eq`. Containment therefore *raises* the temperature, and
saturation pressure is superexponential in it:

| N shells | T_interior | p_sat required | inside the registered bracket? |
| --- | --- | --- | --- |
| 0 (uncontained — cannot photosynthesise) | 5.16 °C | 882 Pa | yes, and it is the floor |
| **1** | **57.82 °C** | **18.02 kPa** | **NO — 1.8x above the top** |
| 2 | 93.13 °C | 78.90 kPa | no — 7.9x above |
| 3 | 120.44 °C | 200.7 kPa | no — 20x above |

Positive control: both endpoints reproduce the roadmap's own published figures (5.16 °C → 882 Pa;
57.82 °C → 18 kPa) from the live `sim.thermal` code and the Buck equation, before anything moves.

**The bracket cannot contain its own premise.** Every pressure in it describes an organism that
is not contained, and an organism that is not contained has no liquid water — which is the
finding that promoted Q3 to a precondition in the first place. This is not a mismatch between
two *sources*; it is a mismatch between a registered input and a result the project derived
after registering it. **Same class, new mechanism: the pair here is a number and a conclusion,
not two citations.**

Consequence for framing A, at the self-consistent pressure (red band, grounded ice sigma):

| p | R_max, 680 nm | binds at R = 10 km? |
| --- | --- | --- |
| 882 Pa — bracket floor, uncontained T | 18.9 – 83.8 km | no |
| 10 kPa — bracket top | 1.67 – 7.39 km | yes |
| **18.0 kPa — self-consistent, N = 1** | **0.93 – 4.10 km** | **yes, decisively** |

**S2 (NEW, and it reaches the three SHIPPED questions, not just Q3). Full-spectrum
photosynthetic parameters are combined with what §9/§10 show is a spectrally filtered light
field.** `sim/physiology.py:29` computes PAR as one flat scalar, `TSI × 0.45 × 4.57` — all three
factors describing the **unfiltered solar spectrum** — and feeds it to `gross_assimilation`
alongside `a_max`, grounded in §4 from 530 species measured under **full-spectrum light**. For an
uncontained organism the pair is consistent. For a contained one it is not: a consistent ice wall
is a blue-pass filter that removes chlorophyll a's red Q band entirely (§10, corrected). Q1, Q2
and Q2b all model photosynthesis at a light field the wall they now require would not deliver.

Unlike the `area_ratio` degeneracy — which changed what those questions *measured* while leaving
every number standing — this one would change the numbers. **NOT resolved here, and NOT a reason
to touch the frozen experiments.** Recorded as the largest known open pairing.

**S3 (NEW). Pure ice absorption is divided by dusty ice scattering.**

> ⚠️⚠️ **WITHDRAWN 2026-09-05 by §15 — S3 IS FALSE.** §9's `L_d` is object-matched: BOTH lengths
> are Ackermann's. 18.3–115.5 m reproduces exactly from his own 100–400 m x 10–100 m, while
> S3's attribution would give 67.0–211.8 m. The sweep inferred the pairing from the prose
> around the formula instead of the arithmetic that produced the number. The paragraph DOES
> contain a defect, but a different one — its `R_max` figures are wood's sigma (§15).
 §9's diffusive-slab caveat
combines Warren & Brandt's **pure, bubble-free** ice absorption with Ackermann's **dust-laden
deep South Pole glacial** ice transport length. Both are ice; they are not the same ice — the
Ackermann paper's own point is that below 1450 m the bubbles are gone and the residual scattering
*is* the dust. The ledger already flags the formula as applied-by-me-and-unvalidated; it did not
flag that its two inputs describe different materials.

**S4 (NEW, now CLOSED by this sweep). Q2b's adaptation premise had no ledger row and no DOI
anywhere in the repository.** `sim/thermal.py` attributes the Gaussian form and the acclimation
result to "June, Evans & Farquhar (2004), as quoted verbatim in Scafaro et al. (2023)", and
`experiments/q2b_adapted/prereg.yaml:40` uses `measured_c: [29.4]` as Gate B's anchor — but
neither §5's honesty ledger nor this document's reference list mentioned either paper, and no DOI
for either appeared anywhere in the project. The sweep resolved and verified both from the gold-OA
primary text:

> "the Topt of Ac was 29.4 °C for cool and 32.7 °C for warm grown plants" `[Q]`
> "temperature response curves of 49 species previously published" `[Q]`
> "Ω is the difference in temperature from To at which J declines to e−1 (0.37) J(To)" `[Q]`

All three match `sim/thermal.py`'s docstrings, including the Ω definition word for word — the
code was right and the ledger simply never covered it. **The remaining mismatch is the organism:**
a whole-leaf, Rubisco-deactivation result from 49 vascular C3 land plants supplies the thermal
premise that `adapted_optimum` applies to the **unicellular** algal preset (§3 decided that class
is a single cell). Same class as §4's `a_max` borrow, and now ledgered as such.

### Pairs checked and CLEARED

- `TSI × PAR_FRACTION × PHOTONS_PER_J` — all three describe the solar spectrum at top of
  atmosphere; mutually consistent. (All three are *declared*, and S2 is about what happens to
  them behind a wall — but as a pair, they agree.)
  - ⚠️⚠️ **WITHDRAWN 2026-09-04 by §12, same day — THIS CLEARANCE WAS FALSE.** The measured
    top-of-atmosphere PAR energy fraction is **0.3879**, not 0.45. This bullet cleared the pair
    by reading its three labels instead of measuring them, which is the failure §11 exists to
    name. See §12 S5.
- `equilibrium_temperature` — one grounded input (TSI) against exact constants and declared
  emissivity/albedo. No two-source pair exists to mismatch.
  - ⚠️ **TRUE AS STATED, AND IT MISSED §13 S7.** Narrowly correct — TSI is the only sourced
    input. But the pair that mattered was never inside this function: it is between its
    greenhouse premise and the ice optics two sections away, and no expression contains both.
  - ⚠️⚠️ **AND IT MISSED TWO MORE — §17 S8 AND S9. THREE FINDINGS UNDER ONE STILL-ACCURATE
    BULLET.** S8: the shell this function returns sits at `T_eq` = 5.16 °C, and the wall is
    ICE, which melts at 0 °C. S9: its declared `albedo = 0` is paired with that same ice
    conclusion, and 7.2% albedo would reverse S8. **A clearance that is true about the
    EXPRESSION says nothing about the OBJECT.** This bullet cannot be made more correct — it
    has to be replaced by a different question: *what does this function assume about the
    world, and does anything else the project believes contradict it?*
- `respiration(r_d, t)` — `r_d` is labelled a calibration knob in all three preregs, not a
  sourced value, so no pairing arises. `Q10 = 2.0` and `T_REF_K = 293` are declared.
  - ⚠️⚠️ **WITHDRAWN 2026-09-04 by §13 S6.** This examined the RESPIRATION side and never asked
    what temperature the ASSIMILATION side's grounded `a_max` describes. The source records
    none, and Q1/Q2/Q2b each assume a different one.
- `a_max` vascular→algal, algal `leaf_mass_ratio`, `t_opt` from bryophyte/lichen sources —
  already recorded in §§3, 4, 4b and 4d. Re-confirmed, not re-litigated.

### What the sweep says about the rule that generated it

Three of the four findings are pairings the project's existing checks could not have caught,
because **every one of those checks validates a single input.** Citation verification asks "is
this source real"; the honesty ledger asks "what layer does this claim sit on"; ghostcite asks
"is this byline right". All three answer yes for both halves of every defect found here.

**The unit of validation has to be the EXPRESSION, not the input.** A number is not true or
false on its own — it is true *of an object*, and combining two numbers silently asserts their
objects are the same one. That assertion is never written down, so nothing checks it.

S1 sharpens this further: its two halves are a registered input and a later derived conclusion.
So the rule generalises past citations — **anything a model combines carries an unstated claim
that the things combined describe the same world, including a project's own past and present
selves.**

## 12. S2 sized — and `PAR_FRACTION` is a surface number inside a top-of-atmosphere function

**Trigger.** §11 recorded S2 — a flat full-spectrum PAR scalar feeding a full-spectrum `a_max`
for an organism §10 shows must sit behind a blue-pass wall — as "the largest known open
pairing", but never gave its size. This pass measures it. `tools/size_par_filter.py`.

**Method, and the discipline it had to satisfy.** Sizing S2 means combining
`sim/physiology.py`'s scalars with a solar spectrum. _That is itself a pairing_, and §10's rule
forbids assuming the spectrum I picked is the one those scalars describe. So the script tries
to **prove** the match before using it. Four controls run before any result:

- **A.** ASTM G173-03's AM0 column integrates to 1347.9 W/m², **0.9867** of its own nominal
  1366.1 — the residual is real UV/IR outside the table's 280–4000 nm span. The control
  therefore asserts the _ratio_, not the total; an assert on the total would have read a
  correct table as a parse failure.
- **B.** Re-derive the PAR energy fraction at top of atmosphere. **This is the control that
  failed**, and it is S5 below.
- **C.** Re-derive µmol photons per J of PAR: **4.553** against the declared
  `PHOTONS_PER_J = 4.57`. Passes at 0.4%.
- **D.** Reproduce §10's committed ice transmission row (0.9881 / 0.4302 / 1.97e-3 / 2.26e-4 at
  t = 16.1 m) from an independent log-space interpolation of the same Warren & Brandt table.
  Passes. This pins the ice side, so a wrong answer below cannot be blamed on the optics.

**Every control was then run against a mutant and seen to fail for its stated reason**, because
a control never observed failing is not evidence — the project's own doctrine, applied to the
instrument that produced this section. A: feed the AM1.5G surface column where AM0 belongs →
*"band integrates to 1000.4 = 0.732"*. B: use the truncated band as denominator instead of the
solar constant → *"measured 0.3932"* — **this is the exact bug the first draft of the script
shipped**, and control B caught it before it reached this page. C: drop the nm→m factor →
*"4553214347.591 umol/J"*. D: shift the ice wavelength grid 5 nm → *"at 550 nm: 0.4727 vs
0.4302"*.

**One mutant survived, and it convicted a comment rather than a number.** Replacing the
log-space interpolation of `m_im` with linear interpolation changed nothing D could see —
because D probes 400/550/680/700 nm, all of which sit *exactly on* the ice table's 10 nm grid,
where both schemes return the tabulated value. **D discriminates wavelength registration, not
interpolation scheme.** Measuring the difference directly showed why that is harmless here: the
two schemes move the integrated result by ≤ 0.5% and differ by 0.3% at the off-grid 645 nm. But
the code comment had *asserted* that linear interpolation "would badly misstate the middle of
every 10 nm gap" — an unmeasured justification, and false. The number was right; the reason
given for it was invented. Corrected in place, and recorded here because **it is S5's own
failure mode in miniature: a label asserting a property that no one measured.**

### S5 (NEW). The PAR fraction is 0.388 at the top of the atmosphere. The project declares 0.45.

| quantity                                                        | value      |
| --------------------------------------------------------------- | ---------- |
| measured, ASTM G173-03 **AM0 (top of atmosphere)**              | **0.3879** |
| measured, ASTM G173-03 AM1.5G (at the surface)                  | 0.4297     |
| independent check, 5772 K blackbody                             | 0.3663     |
| **declared** in `sim/physiology.py` and all three `prereg.yaml` | **0.4500** |

`irradiance()`'s own docstring says _"top-of-atmosphere"_. The fraction it multiplies TSI by is
not a top-of-atmosphere fraction — it exceeds even the terrestrial AM1.5G value. **PAR is
overstated by 1.160× at every heliocentric distance, in every one of the three shipped
questions.** Flux goes as 1/r², so an iso-flux distance threshold moves by √1.160 = **1.077×**,
about 7% in r to first order.

Where 0.45 came from is not recorded: all three preregs carry it as a bare `# assumption` with
no source. It is close to the textbook "PAR is ~45% of solar radiation" figure, which is a
statement about _surface_ radiation. That provenance is a guess and is recorded as one. The
measurement is not a guess.

**This is the sharpest instance of the project's own root class, because §11 cleared it.** The
pair sits in §11's _"Pairs checked and CLEARED"_ list, cleared one commit ago with:

> `TSI × PAR_FRACTION × PHOTONS_PER_J` — all three describe the solar spectrum at top of
> atmosphere; mutually consistent.

That clearance was produced by reading three declarations and observing that they all _said_
top of atmosphere. Two of them meant it. **§11 cleared this pair using exactly the reasoning
§11 was written to condemn: it validated the labels, one at a time.** The check that would have
caught it is the one this pass ran — re-derive each scalar from the spectrum it claims to
describe — which is just the check that grounds an input, applied to the pairing instead.

> **The rule: "the same object" is a measurement, not a label.** Two inputs agreeing about
> which object they describe is a claim of theirs, not evidence for it. Where the object is
> quantitative, a pairing is checked by re-deriving both inputs _from_ it. Anything less
> checks the declarations against each other, which they will always pass.

### S2, sized

Wall thickness from the spec's own thin-wall relation `t = p·R/(2σ)` at R = 10 km; transmission
`exp(−k(λ)·t)` with §9's grounded pure-ice `k`; integrated against the AM0 **photon** spectrum
over 400–700 nm.

| p                                     | σ           | wall t      | PAR photons delivered | τ = 0.5 at |
| ------------------------------------- | ----------- | ----------- | --------------------- | ---------- |
| 882 Pa (bracket floor, uncontained T) | 3.1 MPa     | 1.4 m       | 85.5%                 | 696 nm     |
| 882 Pa                                | 1.5 MPa     | 2.9 m       | 74.8%                 | 638 nm     |
| 882 Pa                                | 0.7 MPa     | 6.3 m       | 60.6%                 | 593 nm     |
| 10 kPa (bracket ceiling)              | 3.1 MPa     | 16.1 m      | 43.7%                 | 540 nm     |
| 10 kPa                                | 1.5 MPa     | 33.3 m      | 33.1%                 | 511 nm     |
| 10 kPa                                | 0.7 MPa     | 71.4 m      | 24.3%                 | 487 nm     |
| **18.02 kPa (self-consistent, S1)**   | **3.1 MPa** | **29.1 m**  | **34.9%**             | **516 nm** |
| **18.02 kPa**                         | **1.5 MPa** | **60.1 m**  | **26.2%**             | **492 nm** |
| **18.02 kPa**                         | **0.7 MPa** | **128.7 m** | **18.7%**             | **470 nm** |

**S2 is real, but it is a factor and not an order of magnitude: 2.9–5.3× at the self-consistent
pressure.** Combined with S5's 1.16×, `irradiance(1.0)`'s 2798.5 µmol m⁻² s⁻¹ becomes
**450–840 — overstated 3.3× to 6.2×.**

That is far milder than §10's per-wavelength figures suggest, and the reason is worth stating
plainly: **§10's alarming numbers are red-band transmissions, and most PAR photons are not in
the red band.** Integrated over PAR the blue end carries the count, and the blue end is nearly
transparent. So the _spectrum_ is mutilated — the 50% cutoff sits at 470–516 nm, putting
everything redward of green beyond reach — while the _photon count_ falls only ~3–5×. Reading
§10's 2.26e-4 as the size of S2 would have overstated it by four orders of magnitude. **A
per-wavelength extreme is not an integrated quantity**, which is the same category error as
treating `k` as a scalar (§9), one level up.

**Two things this measurement does NOT license.**

1. **It is an upper bound on transmission, not an estimate of it.** This is absorption in pure
   bubble-free ice. §11 S3 — pure-ice absorption divided by dusty-ice scattering — bears
   directly here, and §9's own scattering caveat put real ice at roughly **24× stronger**
   attenuation. **3.3–6.2× is a floor on the error, not its size.**
2. **It is a photon count, not a photosynthetic rate.** `a_max` was measured under full-spectrum
   light, and the surviving band excludes chlorophyll a's Q band entirely. A
   chlorophyll-weighted figure would be worse, possibly much worse — but producing one requires
   an _in vivo_ action spectrum this project has not grounded, and inventing one would
   manufacture the very defect this section is about. Bounded below; not resolved.

**Consequence.** Q1, Q2 and Q2b each contain a light field overstated **1.16× unconditionally**
(S5), and **3.3–6.2× if the organism is contained** (S5 + S2) — and §10 makes containment
mandatory. The two are not equivalent in standing: S2 depends on the vessel and is bounded
below, while **S5 is a defect in the shipped questions exactly as registered.** It needs no
wall, no Q3 and no re-framing to be wrong. Whether that triggers re-registration is a decision
for the next pass, not for this grounding.
## 13. Re-checking §11's surviving clearances by measurement — and the greenhouse premise fails

**Trigger.** §12 withdrew one of the four entries in §11's _"Pairs checked and CLEARED"_ list
after measuring it. Three were still standing, cleared the same way — by reading labels. This
pass measures them, and audits §12's own pairings by the rule §12 itself introduced.

### S6 (NEW). `a_max` has no recorded temperature, and the three questions assume three different ones.

§4 grounded `a_max` from Westerband et al. (2022)'s `Asat` column and was careful about the
unit question — _"Asat is net; this model's `a_max` is gross"_ — but never asked **what
temperature that rate describes.** The deposit does not say. It has no leaf-temperature column
at all, while carrying **`Vcmax25_micromol.m2.s`** — explicitly standardised to 25 °C — in the
same 35-column file. The authors standardised where they meant to; `Asat` is an as-measured
field quantity whose leaf temperature was not deposited. (The 675 Asat rows carry site climate
only: MAT median 18.5 °C, max-temp median 24.6 °C.)

So the anchor is unrecoverable from the source — and each shipped question supplies a different
one implicitly:

| question                       | how `a_max` is consumed                                                           | anchor it implies             |
| ------------------------------ | --------------------------------------------------------------------------------- | ----------------------------- |
| Q1 `net_carbon`                | `gross_assimilation(...)`, **no temperature factor**, tissue at `t_set = T_REF_K` | the rate at **293.0 K**       |
| Q2 `net_carbon_at_equilibrium` | `× temperature_response(...)`, which is 1.0 **at and above** `t_opt`              | the rate at `t_opt` or hotter |
| Q2b `net_carbon_adapted`       | `× temperature_response_gaussian(...)`, exactly 1.0 **at** `t_opt`                | the **peak** rate, at `t_opt` |

The same registered `a_max = 10.0` cannot be all three unless `t_opt = 293 K`, and it is not —
Q2b _derives_ `t_opt` from geometry via `adapted_optimum`. Sized with the project's **own**
Gaussian, so no new object is imported to measure the gap:

| preset   | `t_opt`  | ΔT from 293 K | Ω=10   | Ω=15   | Ω=20   | Ω=25   | Ω=30   |
| -------- | -------- | ------------- | ------ | ------ | ------ | ------ | ------ |
| algal    | 5.16 °C  | +14.69 K      | 0.1156 | 0.3833 | 0.5831 | 0.7081 | 0.7868 |
| vascular | 57.82 °C | −37.97 K      | 0.0000 | 0.0016 | 0.0272 | 0.0996 | 0.2015 |

**The two readings of one number differ by 1.27×–8.65× (algal) and 4.96×–1.8e6× (vascular)
across the registered Ω grid.** Neither is checkable against the source. The disagreement is
_internal_ and provable from the code alone. `tools/check_amax_anchor.py`.

§11 cleared this pair by examining the **respiration** side (_"`r_d` is a calibration knob, so
no pairing arises"_) and never asking what temperature the **assimilation** side's grounded
number describes. Note also that `r_d` being a calibration knob partly _masks_ the defect in
Q1's gate — `I_c = k·r_d/(a_max − r_d)` was tuned to hit a target — while leaving `r*` exposed.

### S7 (NEW, and it withdraws part of S1). The contained-temperature result assumes a wall the project's own optics say cannot exist.

`T_interior = (N+1)^0.25 · T_eq` is derived for an **SW-transparent, IR-opaque** wall. §12
measured that same wall passing 2.26e-4 in the red. The thermal model and the optical model
describe **the same wall** and disagree about it — and the disagreement is far worse than PAR
suggests, because **PAR is not where the energy is**:

| band                 | fraction of TSI |
| -------------------- | --------------- |
| UV, 280–400 nm       | 0.0763          |
| PAR, 400–700 nm      | 0.3932          |
| **NIR, 700–4000 nm** | **0.5305**      |

Ice absorbs the near-infrared hard. Solar-energy-weighted transmittance of a pure-ice wall:

| wall t         | τ (solar energy) | `T_interior` if the premise is corrected |
| -------------- | ---------------- | ---------------------------------------- |
| 0.625 m (§9's) | 0.5086           | 35.29 °C                                 |
| 16.1 m         | 0.2699           | 22.29 °C                                 |
| 29.1 m         | 0.2345           | 20.21 °C                                 |
| 128.7 m        | 0.1598           | 15.67 °C                                 |

**A pressure-bearing ice wall transmits 16–23% of the solar energy. It is not a greenhouse
pane; it is an absorber.** Redoing the shell balance without assuming transparency — same
idealisation as the original derivation, one assumption changed:

```
core:   tau*A + sigma*Ts^4 = sigma*Tc^4
shell:  (1-tau)*A + sigma*Tc^4 = 2*sigma*Ts^4
add  ->  sigma*Ts^4 = A     =>     T_interior = (1 + tau)^0.25 * T_eq
```

**The project's formula is the τ = 1 special case.** Positive control: at τ = 1 the
generalisation returns 57.82 °C exactly, the roadmap's own published number — a generalisation
that cannot reproduce what it generalises is not one.

**And τ depends on thickness, thickness on pressure, pressure on temperature, temperature on τ.
That is a fixed point** — solving it is precisely what §11 S1 said a re-registered Q3 must do,
derive `p` from `T_interior` rather than declare it. Converged:

| σ       | wall t  | τ      | `T_interior` | self-consistent `p` | in [882 Pa, 10 kPa]? |
| ------- | ------- | ------ | ------------ | ------------------- | -------------------- |
| 3.1 MPa | 5.57 m  | 0.3429 | 26.45 °C     | **3.453 kPa**       | **YES — inside**     |
| 1.5 MPa | 10.01 m | 0.3013 | 24.10 °C     | **3.002 kPa**       | **YES — inside**     |
| 0.7 MPa | 18.62 m | 0.2609 | 21.77 °C     | **2.607 kPa**       | **YES — inside**     |

**S1's conclusion is withdrawn. The registered pressure bracket is NOT self-inconsistent.** S1
computed 18.02 kPa — 1.8× above the bracket ceiling — from `T_interior = 2^0.25 · T_eq`, i.e.
by assuming τ = 1, the very assumption the optics falsify. The self-consistent pressure is
**2.6–3.5 kPa, comfortably inside the registered bracket**, 5.2×–6.9× below S1's figure.

What of S1 _stands_ is its mechanism: the bracket's floor is still `p_sat` at the _uncontained_
temperature, and containment still raises it. What falls is the magnitude and therefore the
verdict. And the direction is robust — τ above is **pure-ice absorption**, so any real
impurity or scattering (§11 S3) pushes τ down, `T_interior` down, and `p` further _inside_ the
bracket, never out of it.

Framing A moves again, and this time it lands somewhere honest:

| σ       | self-consistent p | `R_max` (red) | binds at R = 10 km? |
| ------- | ----------------- | ------------- | ------------------- |
| 3.1 MPa | 3.453 kPa         | 21.41 km      | no                  |
| 1.5 MPa | 3.002 kPa         | 11.91 km      | no                  |
| 0.7 MPa | 2.607 kPa         | 6.40 km       | **YES**             |

**Framing A is split by ice strength** — it binds only at the weak end of Petrovic's range.
Not §9's falsification, not S1's decisive binding. `tools/check_greenhouse_transparency.py`.

Note in passing: the corrected `T_interior` of 21.8–26.5 °C sits very close to the 293.0 K that
Q1 declares as its tissue set-point, and very far from the 5.16 °C `adapted_optimum` hands Q2b.
S6 and S7 are the same wound seen from two sides.

### §12's own pairings, audited by §12's rule

`1360.8` appears **nowhere** in this document. §12 derived the PAR fraction against ASTM
G173-03's 1366.1 W/m² normalisation and then applied it to Kopp & Lean's 1360.8 W/m² TSI,
without saying why that is allowed. Checked: the fraction is **dimensionless — a property of
spectral shape, not scale** — so it transfers, and the residual if the two normalisations
disagreed in shape at all is ≤ **0.39%**, against S5's 16.0%. **41× smaller, real, now stated,
and not load-bearing.** Recorded rather than waved through, because "not load-bearing" is a
measurement too.

### Clearance status after this pass

| §11 clearance                                                         | status                                                                                                                                                                                                                       |
| --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `TSI × PAR_FRACTION × PHOTONS_PER_J`                                  | **WITHDRAWN** by §12 (S5)                                                                                                                                                                                                    |
| `respiration(r_d, t)`                                                 | **WITHDRAWN** — cleared the respiration side; the assimilation side's anchor was never asked (S6)                                                                                                                            |
| `equilibrium_temperature` — _"no two-source pair exists to mismatch"_ | **TRUE AS STATED, AND IT MISSED S7.** Narrowly correct: TSI is the only sourced input. But the pair that mattered was never inside that function — it is between its greenhouse premise and the ice optics two sections away |
| `a_max` vascular→algal, algal LMR, `t_opt` provenance                 | stands — re-confirmed, and S6 is a _different_ axis of the same input (temperature, not organism)                                                                                                                            |

**All four clearances have now been examined by measurement. Three did not survive.**

### The rule this buys, and it breaks §11's own formulation

§11 said _the unit of validation is the expression, not the input._ **S7 is not in any
expression.** No line of code multiplies τ by the greenhouse factor; nothing imports
`sim.thermal` and the ice table together. The contradiction lives between a **docstring
assumption in one module and a data table in another section**, and an expression-level check —
however rigorous — cannot see it, because the two halves never meet in one.

> **A pairing need not appear in any expression. Two models can describe the same object
> incompatibly with no single line of code containing both.** The unit of validation is
> ultimately neither the input nor the expression but **the OBJECT**: every model that
> describes a thing is making claims about it, and those claims must be made to agree
> explicitly, because nothing in the code will ever bring them face to face.

That is why S7 survived §9, §10, §11 and §12 — every one of which was looking at expressions.
It was found only by asking what `equilibrium_temperature`'s _clearance_ had not looked at, and
the clearance was **true as written**.

## 14. The `area_ratio` degeneracy re-checked at a τ someone measured

**Trigger.** §13 S7 replaced `T_interior = (N+1)^0.25 · T_eq` with `(1+τ)^0.25 · T_eq`. The
roadmap's `area_ratio` degeneracy — _"adding one IR-opaque shell and halving `area_ratio` are
the SAME operation (identical to 5.7e-14 K)"_ — is stated in terms of that superseded law. It
is the symmetric case S7's own data already settles, so it gets checked rather than assumed.

**Method.** Solve the N-shell radiative system for arbitrary τ instead of assuming
transparency, shells IR-opaque and radiating from both faces:

```
shell 1:  (1-tau)*A             + S_2                = 2*S_1
shell i:  (1-tau)*tau^(i-1)*A   + S_{i-1} + S_{i+1}  = 2*S_i
shell N:  (1-tau)*tau^(N-1)*A   + S_{N-1} + S_core   = 2*S_N
core:      tau^N * A            + S_N                = S_core
```

**Controls.** At τ = 1 the solver returns exactly `(N+1)·A` for N = 0…5 — the project's own
law — and one shell then equals halving `area_ratio` to **5.7e-14 K**, reproducing the
roadmap's published residue digit for digit. Mutants confirm both controls discriminate:
detaching the innermost shell from the core gives 1.0 where 2 is required, and letting shells
radiate from one face makes the system **singular**, which is the correct response to an
energy balance that cannot be satisfied.

### Result 1 — the identity holds only at τ = 1.

| wall      | τ      | `T` with one shell | gap vs halving `area_ratio` |
| --------- | ------ | ------------------ | --------------------------- |
| σ 3.1 MPa | 0.3429 | 26.45 °C           | **−31.37 K**                |
| σ 1.5 MPa | 0.3013 | 24.10 °C           | **−33.72 K**                |
| σ 0.7 MPa | 0.2609 | 21.77 °C           | **−36.05 K**                |

Halving `area_ratio` takes the algal sphere from 5.16 °C to 57.82 °C. A _real_ shell takes it
to 21.8–26.5 °C. **The two operations differ by 31–36 K, not by 5.7e-14 K.**

### Result 2 — but the degeneracy does not vanish. It rescales.

```
T = ( S*(1+tau) / (area_ratio * sigma) )^0.25
```

`area_ratio` and `(1+τ)` enter **only as a ratio**, so the degenerate quantity is
`area_ratio/(1+τ)` — an _effective_ `area_ratio`. Containment does not stop masquerading as
shape; it masquerades as **less** shape than was claimed:

| wall                          | τ      | effective `area_ratio` |
| ----------------------------- | ------ | ---------------------- |
| σ 3.1 MPa                     | 0.3429 | 2.979                  |
| σ 0.7 MPa                     | 0.2609 | 3.172                  |
| _τ = 1 (the roadmap's claim)_ | 1.0000 | _2.000_                |

So a registered `4.0` still carries a claim about containment — but the claim is "τ ≈ 0", and
a contained sphere presents as ≈ 3.0–3.2, not as 2.0. **The confound is real and about 2.7×
smaller in temperature than recorded.**

### Result 3 — and a contained sphere falls outside Q2b's registered band entirely.

Q2b registers the algal band as **[3.630, 4.311]**. A contained sphere presents at
**2.979–3.172 — wholly below its floor.** Inverting: for a contained organism to present
_inside_ that band, its true `area_ratio` would have to be **[4.577, 5.789]**. A sphere is
4.0 and a face-on lamina is 2.0, so the entire band would demand a body **more extreme than a
sphere** — elongated or flattened and seen near edge-on.

This _replaces_ rather than confirms the roadmap's reading. The claim on record is that Q2b's
band "is not a statement about shape alone". Corrected: **the band is a statement about shape,
conditional on containment — and no contained sphere can produce a value in it.** Containment
and shape are separable after all; they were only inseparable under τ = 1.

### Result 4 — the N = 2 figure inherits the same falsified premise.

The roadmap quotes _"two shells need 78.9 kPa"_ from `3^0.25 · T_eq` = 93.13 °C. At measured τ
that interior is **25.67–32.80 °C**, not 93.13 °C. The 78.9 kPa figure is withdrawn on exactly
the ground that took S1's 18.02 kPa: it assumes a transparency the optics deny. Note the shape
of the corrected column — with real τ the shells saturate fast (5.16 → 21.8 → 25.7 → 26.7 °C
at τ = 0.26), because each shell only passes a quarter of what reaches it. **Stacking shells
is a far weaker lever than the transparent model implies.**

### The lesson, and it is the project's oldest root class wearing a new coat

The degeneracy was verified **numerically, to fourteen decimal places**. That is what made it
look airtight, and it is exactly why it went unchallenged through §§9–13. But the check
compared `(N+1)^0.25 · T_eq` against `T_eq` at half the `area_ratio` — **two expressions
computing the same assumption.** Agreement to 5.7e-14 K measured floating-point arithmetic, not
the world.

> **A numerical identity confirmed to fourteen decimal places is still only as true as the
> premise both sides compute.** An agreement that tight is evidence the two expressions share
> an assumption, not evidence the assumption is right — and the tighter it is, the more
> completely it hides that.

This is the project's oldest root class — _a test that cannot fail_ — reappearing as a
_verification_ that cannot fail. §11 already named the pattern for inputs and §13 for models;
here it is for identities. The 5.7e-14 K is now this document's positive control **precisely
because** it never could have been anything else.

## 15. S3 closed — by disproving it

**Trigger.** S3 was the last unresolved finding of the §11 sweep, and §13/§14 made it
load-bearing: τ drives every number in §§12–14, and S3 was the reason τ was only an upper
bound. Closing it meant either finding a matched-object pair or stating the bound honestly.

**It needed neither, because S3 is false.**

### The attribution S3 asserted is checkable by arithmetic, and it fails

S3 claims §9's diffusive-slab caveat _"combines Warren & Brandt's pure, bubble-free ice
absorption with Ackermann's dust-laden deep South Pole glacial ice transport length."_ But §9
quotes **both** lengths from Ackermann — _"the effective (transport) scattering length is
10–100 m against an absorption length of 100–400 m"_ — so the claim is testable against the
published number. `L_d = sqrt(l_abs·l_tr/3)`:

| hypothesis                      | inputs                  | `L_d`              | matches §9's published 18–116 m? |
| ------------------------------- | ----------------------- | ------------------ | -------------------------------- |
| **Ackermann's own two lengths** | 100–400 m × 10–100 m    | **18.3 – 115.5 m** | **yes, exactly**                 |
| S3's attribution                | W&B 1345.9 m × 10–100 m | 67.0 – 211.8 m     | no — 3.7× off at the low end     |

**§9's `L_d` is object-matched.** Both lengths are Ackermann's, measured on the same ice in the
same experiment, and the number §9 published could only have come from that pair. S3 misread
the attribution — §9's _neighbouring sentence_ compares the result against pure-ice absorption,
and the sweep took that comparison for the formula's input.

**S3 is withdrawn.** Recorded rather than quietly deleted, because a sweep that produces a
false positive is telling you something about the sweep: **§11 read the paragraph and inferred
the pairing from the prose around the formula rather than from the arithmetic that produced the
number.** It was label-reading — the very failure §12 later named — committed one section
earlier than §12 found it, and against a formula rather than a constant.

### But the paragraph is not clean, and §10 cleared it by name

`R_max = 2σ·|ln τ_min|·L_d/p` is **linear in σ**, and §9 evaluated it at **80 MPa — the wood
figure**. §10's withdrawal banner reads:

> Everything else in §9 — the ×701 spectral spread, the 135× band error, **the scattering
> caveat** — is unaffected.

Two of those three are genuinely σ-independent. The scattering caveat is not:

| σ                     | `R_max` at `L_d` = 18.3 m | at `L_d` = 115.5 m |
| --------------------- | ------------------------- | ------------------ |
| 80 MPa (wood — §9's)  | 1345.3 km                 | 8508.1 km          |
| 3.1 MPa (ice, strong) | 52.1 km                   | 329.7 km           |
| 1.5 MPa (ice, mid)    | 25.2 km                   | 159.5 km           |
| 0.7 MPa (ice, weak)   | **11.8 km**               | 74.4 km            |

The conclusion — _"still far above 10 km"_ — survives, but the **margin collapses from 134× to
1.2×**. (The 1345.3 km reproduces §9's published 1345 km at σ = 80 MPa, p = 10 kPa,
`L_d` = 18.3 m, which confirms the wood σ is what generated those figures.)

**This is the third sentence §10 cleared that was not clean**, and the second in that one
banner — after _"the spectral-filter result stands unchanged"_, corrected in the same pass that
wrote it. §10's rule was right and §10's own application of it kept failing in the same
direction: **the clearing sentence is written last, when the author is most confident and least
willing to re-derive.**

### What dust actually does to τ — S3's real consequence

The reason S3 mattered was never the attribution; it was that §§12–14's τ is pure-ice
absorption and therefore an upper bound. So: model dust as a wavelength-independent attenuation
floor set by Ackermann's own diffusion lengths — **a DECLARED model, not a measurement**,
defensible only because ice's own absorption swamps dust everywhere except the blue window,
which is exactly where the floor bites. Re-solving §13's fixed point at σ = 1.5 MPa:

| dust floor                    | τ (solar) | `T_interior` | self-consistent `p` |
| ----------------------------- | --------- | ------------ | ------------------- |
| none (§13's pure ice)         | 0.3013    | 24.10 °C     | 3.002 kPa           |
| 1/115.5 m = 0.0087 /m (weak)  | 0.2820    | 22.99 °C     | 2.809 kPa           |
| 1/18.3 m = 0.0548 /m (strong) | 0.2156    | 19.08 °C     | **2.209 kPa**       |

**Every dust level keeps `p` inside the registered [882 Pa, 10 kPa] and pushes it downward** —
the direction §13 predicted from the structure alone. **S3 cannot overturn S7; it can only
deepen it.** That is the honest closure: the residual gap §9 called ungroundable is still
ungroundable _in magnitude_, but its **direction is now pinned**, and the conclusion that
depends on it is monotone in the unknown. A bound whose sign is known does not need its value.

### Tells

**A false positive in a sweep is a finding about the sweep.** S3 cost nothing to disprove and
would have cost a great deal to act on — the "matched pair" it demanded already existed in the
cited paper. Before hunting for a missing input, check whether the number you are questioning
already reproduces from inputs you have.

**A mutation that silently fails to apply is indistinguishable from a control that cannot
fail.** The first attempt to mutate control B printed nothing, which reads exactly like a
non-discriminating control. The `sed` had matched nothing: the formatter had wrapped the target
assignment across two lines. The conclusion drawn from it happened to be correct — the original
control B, which asserted `not (near_lo and near_hi)`, genuinely could not fire under any
single-value change — but **the evidence for that conclusion was invalid, and being right by
luck is not being right.** Assert that the mutant differs from the original, not merely that
the run said something.

## 16. S5 and S6 priced — neither moves a verdict alone, and together they move Q1's

**Trigger.** S5 (`PAR_FRACTION` overstated 1.160×) and S6 (`a_max` anchored at three
different temperatures) are both defects in SHIPPED, pre-registered questions, and both were
deferred as registration decisions. A registration decision made without knowing what it costs
is not a decision. This measures the cost. **Nothing registered was modified**: every run below
executes the real runners against a `git archive HEAD` copy in a scratch tree.

### The harness reproduces before it is trusted

The pristine copy re-runs all three experiments and returns **all six committed CSVs
byte-identical on their data lines** (`calibration`, `crossover`, `sweep` for Q1;
`gates`, `limits`, `sweep` for Q2b), with published stdout reproduced verbatim. A one-digit
mutation (`5.1612 → 5.1613`) makes the comparator report DIFFERS, so it is a comparator and
not a rubber stamp.

### S5 alone: every number moves, no verdict moves

`r*` scales as **exactly `sqrt(par_fraction)`** — measured ratio 0.928440 against
`sqrt(0.3879/0.45)`, agreeing to **3e-06** across all six cases (a 1% perturbation of one value
trips that check). Q1's calibration gate is **untouched**: `I_c = k·r_d/(a_max − r_d)` contains
no light term.

| case           | `r*` at 0.45 | at 0.3879 | band     | verdict     |
| -------------- | ------------ | --------- | -------- | ----------- |
| vascular k=50  | 19.3537      | 17.9688   | [12, 22] | inside      |
| vascular k=100 | 13.6851      | 12.7058   | [12, 22] | inside      |
| vascular k=200 | 9.6769       | 8.9844    | [12, 22] | OUTSIDE     |
| algal k=10     | 95.1233      | 88.3162   | [35, 55] | OUTSIDE     |
| algal k=20     | 67.2623      | 62.4490   | [35, 55] | OUTSIDE     |
| algal k=40     | 47.5616      | 44.1581   | [35, 55] | inside      |

**All six verdicts are unchanged.** Q2 is unchanged in every digit — it exits 2 at the
temperature-response gate, which is purely thermal, so S5 never reaches it. Q2b's `gates.csv`
is byte-identical and its binding limit stays `temperature` at every Ω; only the fourth decimal
of `outer_au` moves (max 2.5301 → 2.5289, **0.05%**).

Solving `r*(par) = r*₀·sqrt(par/0.45)` for each band edge gives the PAR value at which each
verdict would flip. The nearest is **vascular k=100 at par = 0.3460** — the measured 0.3879
clears it by 12%, and the 5772 K blackbody estimate (0.3663) still clears it.

### S6 alone: the anchors, measured from the live code

The same registered `a_max = 10.0` is multiplied by a factor reaching 1.0 at a **different
temperature in each path**:

| path                        | experiment | anchor T   |
| --------------------------- | ---------- | ---------- |
| `net_carbon`                | Q1         | 293.00 K (19.85 °C) — no factor at all; the only declared temperature is `t_set` |
| `net_carbon_at_equilibrium` | Q2         | 298.15 K (25.00 °C) — the linear ramp reaches 1 at `t_opt` |
| `net_carbon_adapted` algal  | Q2b        | 278.31 K (5.16 °C) — the Gaussian peaks at the ADAPTED optimum |
| `net_carbon_adapted` vasc   | Q2b        | 330.97 K (57.82 °C) |

**Spread: 52.66 K.** Read as "the rate at 293 K", the paths need `a_max` from 10.0 to 367.53 —
a factor of **36.75×**. That extreme belongs entirely to the vascular class Gate B already
FAILED, so the live figure is the algal **1.71×**.

Two readings, each self-consistent, each leaving a different experiment alone:

- **Reading A — `a_max` is the rate at 293 K.** Q1 is already correct. Q2b algal needs
  `a_max = 17.1498`; its light limit moves 75.434 → 99.291 AU (**+31.6%**), carbon limits +3.8%
  at Ω=30. Binding stays `temperature` at every Ω.
- **Reading B — `a_max` is the peak rate at `t_opt`.** Q2b is already correct (its Gaussian
  peaks at 1). Q1 needs `a_max = 10.0 × f(293) = 8.4394`; every `r*` falls 9.4% (k=100: 13.6851 → 12.3971) and
  `I_c` rises 6.9519 → **8.3447 against a gate ceiling of 9.0** — headroom cut from 2.05 to
  0.66, a 3× reduction. All six verdicts still hold.
  - ⚠️⚠️ **THIS ARM IS NOT READING B — §18 S10.** The factor `f(293)` used here is
    `temperature_response(293, 265.15, 298.15)` (`tools/price_registered_corrections.py:122`),
    Q2's LINEAR ramp at Q2's DECLARED `t_opt` = 25.00 °C. Reading B as defined one line above —
    the PEAK of Q2b's GAUSSIAN at the ADAPTED optimum — gives 0.0272, not 0.8439, a **31.0×**
    difference. Every number in this bullet is correct; they price a **third** reading (C).
    True reading B removes Q1's compensation point entirely at Ω ∈ {10, 15, 20} and is
    **ineligible** (§18 S11). The A-vs-B framing below should be read as **A-vs-C**.

### Together: Q1's headline verdict flips

The two corrections **compose multiplicatively** (11.5100 predicted from the single effects
against 11.5100 measured):

| | vascular k=100 `r*` | band [12, 22] |
| --------- | -------- | ------- |
| as registered | 13.6851 | inside |
| S5 only | 12.7058 | inside |
| S6 reading B only | 12.3971 | inside |
| **both** | **11.5100** | **OUTSIDE — misses the floor by 0.49 AU (4.1%)** |

Q1's `RESULTS.md` records that *"For the vascular class the default-k (k=100) prediction
HELD."* Under S5 plus reading B it does not. Under S5 plus **reading A** it does (12.7058).

> **The S6 decision determines whether Q1's headline survives S5.** These were filed as two
> independent defects and deferred separately. They are not independent: each is individually
> harmless to every registered verdict, and their product is not. Fixing them one at a time —
> in either order — would have shown two clean bills of health and then a flip that appeared to
> come from nowhere.

### What this cost to learn, and two tells

**A defect that changes no verdict is not thereby cheap, and a pair of them is not twice one.**
The project's habit has been to size defects one at a time. S5 and S6 are the first pair
measured jointly, and the joint result is the only one that moves anything.

**The mutation-that-did-not-apply tell fired again, in a new disguise.** Re-anchoring the algal
`a_max` in `sim/organism.py` changed nothing, and the run printed a full, plausible table —
because Q2b builds its organisms from `prereg.yaml`, not from `PRESETS`. The edit had applied
perfectly to a file the code path never reads. §15 caught this as a `sed` that matched nothing;
here the write succeeded and the *object* was wrong. **Asserting that the edit applied is not
enough — the assertion must be that the edit applied to the thing under test.**

**A guard that exists in one experiment and not its sibling.** Q1 runs
`assert_presets_match`, comparing `prereg.yaml`'s presets against `sim/organism.py`. **Q2b has
no such check**, and the two sources do in fact differ: `leaf_mass_ratio` is 0.8 in
`organism.py` and 1.0 in Q2b's prereg (documented there as *"unicellular: no non-photosynthetic
organ"*). The divergence is deliberate and commented, so this is not a defect in the value — it
is that the name `algal` denotes two different organisms across two experiments, and only one
of them has a guard that would notice.

## 17. The sweep re-run under the rules it produced — and two pairings in its own output

**Trigger.** §11 is the origin of every S-finding, and it is now the one artifact in this
project whose error rate has been *measured*: of its four clearances, **three did not survive**
re-checking (§§12, 13); of its findings, **S1 and S3 were both withdrawn** (§§13, 15). Roughly
50% error in both directions — from a sweep run before a single one of the five rules that
followed it existed. It has also never been applied to §§11–16, i.e. to its own output.

**Method.** Rather than re-list pairs, apply each rule that §11 lacked, and extend the scope to
the sections and tools §11 predates.

### The §12 rule (measure, don't read the label) — applied, and it CLEARS

**`PHOTONS_PER_J` behind the wall.** §12 caught `PAR_FRACTION` being a surface number inside a
top-of-atmosphere function. The same failure one level down would be using the *unfiltered*
4.57 µmol/J to convert a *filtered* energy flux — a blue-pass wall raises the mean photon
energy, so µmol/J must fall. **`tools/size_par_filter.py` does not make this error.** It
computes photon- and energy-weighted transmission separately (`f_ph`, `f_en`), reports µmol/J
behind the wall as its own column, and applies the photon-weighted fraction to a
photon-weighted incident flux. Recorded as **checked and clean** — §15's rule says a sweep's
false positive is a finding about the sweep, and the way to avoid producing one is to check
whether the suspect number already reproduces correctly from inputs in hand.

### The §13 rule (the unit is the OBJECT) — S8, and it is about the wall's phase

Two conclusions of this project, in no shared expression:

- the pressure wall is **ice**, its tensile strength 0.7–3.1 MPa taken from Petrovic via Hirata;
- in §13's own two-body balance, adding the two equations gives `σ·Ts⁴ = A`, so the shell sits
  at **`Ts = T_eq` exactly, independent of τ** (verified for τ ∈ [0, 1] to 1e-9).

Nothing ever asked what temperature that ice is at. At 1 AU, where every number in §§13–15 was
computed:

| | temperature |
| --- | --- |
| shell — the **coldest** part of the wall | 278.31 K = **5.16 °C** |
| interior — the inner face of that same wall | 297.25 K = 24.10 °C |
| ice Ih, melting point (the most generous threshold available) | 273.15 K = 0.00 °C |

**No part of the wall is ice.** The coldest part is 5.16 K above melting, and a gradient wall is
worse rather than better — its inner face sits at 24.10 °C. Melting, not sublimation, is the
right test for the inner face: it sees the interior pressure (2.2–3.0 kPa), which is above
water's triple point (611.657 Pa), so liquid is a phase available to it. The melting point of
ice Ih only *decreases* with pressure, so 273.15 K is the most forgiving line that can be drawn.

**The vessel has a habitable annulus, and 1 AU is not in it.** The shell must be below freezing
for the wall to be solid; the interior must be above freezing for there to be liquid to hold:

| τ | inner edge | outer edge | width | contains 1 AU? |
| --- | --- | --- | --- | --- |
| 0.2156 (strong dust) | 1.0381 AU | 1.1446 AU | 0.1065 AU | **no** |
| 0.3013 (§13 mid) | 1.0381 AU | 1.1843 AU | 0.1461 AU | **no** |
| 0.3429 (§13 strong wall) | 1.0381 AU | 1.2030 AU | 0.1649 AU | **no** |

The inner edge is τ-independent (it is a statement about the shell, and the shell is at `T_eq`
whatever τ does). For scale, **Q2b's algal temperature limit is 1.1945 AU** — the annulus sits
just inside it.

**Priced, per §16.** Re-solving §13's fixed point at the inner edge takes the self-consistent
pressure from **3.002 kPa to 2.287 kPa** — still inside the registered [882 Pa, 10 kPa], and
**downward**, the same direction dust pushes it. So S8, like S3's real consequence, **cannot
overturn S7; it can only deepen it.** Third independent effect now found pointing the same way.

### The same rule once more — S9, which partly REVERSES S8

`albedo = 0.0` is declared in `sim/thermal.py` and used for the solar side of the balance.
Paired with "the shell is ice" — again, no expression contains both — a reflective shell absorbs
less, runs colder, and freezes sooner. **How little albedo undoes S8:**

`T_shell(a) = (1 − a)^0.25 · 278.31 K`, so the shell reaches the melting point at 1 AU at
**albedo = 0.0721 — 7.2%.** At 10% it is −2.07 °C; at a snow-like 0.6, −51.82 °C. The predicate
flips in both directions across that threshold.

Note what is **not** wrong here: the Beer-Lambert `τ = exp(−k·t)` used throughout models pure
absorption with no reflection, which is exactly consistent with `albedo = 0`. The model is
**consistently wrong rather than internally inconsistent** — which is precisely why no
single-expression check could see it, and why §11 cleared `equilibrium_temperature` by
observing, correctly, that it has only one sourced input.

> **S8 holds in the model as written. Its magnitude does not survive S9.** Both are real
> pairings; neither was ever asked; and applying §16's rule to *findings* rather than to
> defects, they interact — the first is conditional on the second.

### The bullet that has now missed three things

§11's clearance of `equilibrium_temperature` reads: *"one grounded input (TSI) against exact
constants and declared emissivity/albedo. No two-source pair exists to mismatch."* §13 already
banner-corrected it as **true as stated, and it missed S7**. It also missed **S8** and **S9**.
Three findings under one bullet that was, and remains, literally accurate.

**A clearance that is true about the expression says nothing about the object.** "No two-source
pair exists" is a claim about what is *written in the function*. Every one of S7, S8 and S9 is a
pairing between something in that function and something concluded elsewhere in the project.
The bullet cannot be rewritten to be more correct; it has to be replaced by a different
question — *what does this function assume about the world, and does anything else the project
believes contradict it?*

### Scope, stated rather than implied

This pass applied the §12, §13 and §16 rules to the Q3 thermal chain and to `size_par_filter`.
It did **not** re-sweep §§1–8's biological groundings, and it spot-checked rather than swept the
122-test suite for §14-class tautologies (`tests/test_thermal.py:131–143` is a good sign — it
explicitly discriminates a Gaussian from a Laplace that would pass every tangent-point check).
Those remain unswept, and saying so is cheaper than implying coverage that was not achieved.

### A tell, from getting it wrong inside this section

The first version of `tools/check_wall_phase.py` printed an `R_max` column giving 38.4 km at
σ = 1.5 MPa, beside §13's published 11.9 km. The gap was mine: §13 used a monochromatic `k` at
680 nm and I had used a spectrum-averaged effective `k`. The number was removed rather than
explained, because the finding does not need it.

> **An uncontrolled reimplementation that contradicts a controlled published number is not
> evidence of a discrepancy — it is evidence of an uncontrolled reimplementation.** The
> temptation is to report it as a fourth finding. Every control in this section exists to make
> that distinction, and the one quantity with no control attached was the one that looked most
> like a discovery.

## 18. S6 resolved — there are three readings, and §16 priced the wrong one under reading B's name

**Trigger.** S6 was deferred as a registration decision between two readings of `a_max`, and
§16 priced both so the decision could be made knowing its cost. A choice between two options
is not a choice if one is ineligible, and is not a choice at all if the two priced arms were
the same option. This pass re-derives the readings from the live code before the decision is
taken. `tools/check_amax_reading.py`, six controls, three of them positive.

### S10 (NEW). §16's "reading B" arm computes a third reading, not reading B.

§16 defines reading B as _"`a_max` is the peak rate at `t_opt`"_ — the temperature at which
Q2b's **Gaussian** equals 1, which is the **adapted** optimum that `adapted_optimum()` derives
from geometry. It then implements the arm as `a_max = 10.0 × f(293) = 8.4394`, where
`tools/price_registered_corrections.py:122` records the factor as
`temperature_response(293, 265.15, 298.15)`.

That is Q2's **linear ramp** evaluated at Q2's **declared** `t_opt` — the 25.00 °C anchor,
which §13's own table lists as a *separate row* from Q2b's. Measured against the live code:

|                                            reading | anchor T | `f(293 K)` | Q1 `a_max` |
| -------------------------------------------------- | -------- | ---------- | ---------- |
| **A** — the rate at 293 K (Q1's own `t_set`)        | 19.85 °C | 1.0000     | 10.0000    |
| **C** — the rate at `t_opt` = 298.15 K (Q2, linear) | 25.00 °C | 0.8439     | **8.4394** |
| **B** — the PEAK rate at the adapted `t_opt` (Q2b, Gaussian) | 57.82 °C | 0.0272 | **0.2721** |

**The two candidate factors for Q1 differ by 31.0×.** The identification is not an allegation:
feeding `a_max = 8.4394` to the live `crossover_distance_for` returns **12.3971 AU**,
reproducing §16's published "reading B" figure exactly (control 2). §16 priced reading **C**.

This matters because §16's headline rests on that arm: *"the S6 decision determines whether
Q1's headline survives S5."* The statement stands — 11.5100 AU is still outside [12, 22] — but
what it is conditional on is the **A-versus-C** decision. Reading B was never priced.

### S11 (NEW). True reading B is not well-defined for Q1, and where it is defined it removes Q1's result rather than moving it.

`net_carbon()` — Q1's path — reads **neither `omega`, `area_ratio`, nor `t_opt`**
(`sim/organism.py:80–86`, and the preset comment at `sim/organism.py:158` says so outright:
_"area_ratio and t_min are Q2-only fields (net_carbon(), which Q1 uses, reads neither)"_).
Applying reading B to Q1 therefore requires importing the Gaussian, the adapted optimum, and
Ω — three objects Q1 does not have. Carried through anyway:

| preset   | Ω  | `f(293 K)` | eff. `a_max` | respiration | `I_c`                 | `r*`       |
| -------- | -- | ---------- | ------------ | ----------- | --------------------- | ---------- |
| vascular | 10 | 0.0000     | 0.0000       | 1.3000      | NO COMPENSATION POINT | — |
| vascular | 15 | 0.0016     | 0.0165       | 1.3000      | NO COMPENSATION POINT | — |
| vascular | 20 | 0.0272     | 0.2721       | 1.3000      | NO COMPENSATION POINT | — |
| vascular | 25 | 0.0996     | 0.9959       | 1.3000      | 187.9236              | no root |
| vascular | 30 | 0.2015     | 2.0152       | 1.3000      | 47.6131               | 3.9237 AU |
| algal    | 20 | 0.5831     | 5.8310       | 0.3000      | 0.8585                | 50.7909 AU |

**At three of the five registered Ω the vascular organism has no compensation point at all** —
gross assimilation cannot reach whole-organism respiration at *any* irradiance, so `r*` does not
exist to be inside or outside a band. At the two widest Ω it exists but `I_c` is 47.6 and 187.9
against a **gate ceiling of 9.0**. Under reading B Q1's vascular result is not flipped; it is
annihilated, at every Ω the project registered.

Positive control on that failure (control 5): the no-compensation-point outcome **fires** for
true reading B at Ω = 20 and **does not fire** for the registered `a_max`. A predicate that
could only ever return "broken" would not be evidence of anything.

Note what reading B does to the *algal* class, which is the class Gate B did not fail: `r*` at
k = 20 moves 67.2623 → **50.7909 AU**, from outside the registered [35, 55] to inside it. The
reading that destroys the vascular question repairs the algal verdict. Neither effect is a
reason to adopt or reject it; both are recorded because a reading that only ever looked bad
would be suspiciously easy to dismiss.

### The correction §16 quoted as one number is a function of Ω

Q2b's `a_max` correction under readings A and C, across the registered
`omega_grid_k: [10, 15, 20, 25, 30]` (`experiments/q2b_adapted/prereg.yaml:67`):

| reading   | preset   | Ω=10        | Ω=15      | Ω=20     | Ω=25     | Ω=30    | spread     |
| --------- | -------- | ----------- | --------- | -------- | -------- | ------- | ---------- |
| A (293 K) | algal    | 86.5049     | 26.0893   | 17.1498  | 14.1230  | 12.7091 | 6.8×       |
| A (293 K) | vascular | 1.82e7      | 6063.90   | 367.5343 | 100.4132 | 49.6236 | 3.7e5×     |
| C (25 °C) | algal    | 512.0259    | 57.5023   | 26.7500  | 18.7710  | 15.4854 | 33.1×      |
| C (25 °C) | vascular | 4.76e5      | 1199.69   | 147.7328 | 56.0358  | 33.0954 | 1.4e4×     |

§16 published the single value **17.1498** for reading A — reproduced here exactly (control 6),
and visible now as the Ω = 20 cell of a row spanning 6.8×. One number per reading understated
what each reading commits the project to.

### The asymmetry that decides S6

Ω is registered **only** in Q2b (`omega_grid_k`); it occurs zero times in
`q1_crossover/prereg.yaml` and `q2_thermal/prereg.yaml`, and `sim/organism.py:40` flags it as a
_"DECLARED ASSUMPTION, not grounded"_.

- **Readings A and C** put the Ω-dependent correction on **Q2b**, the experiment that registered
  and swept Ω. Its answer already varies with Ω by design.
- **Reading B** puts it on **Q1**, which did not. Q1's published headline would become a
  function of a knob Q1 never registered, ranging from *"no compensation point exists"* to
  3.9237 AU.

> **A reading of a grounded input that makes a registered result depend on an unregistered
> parameter is not a reading of that input — it is a re-registration of the experiment.** This
> is the criterion that eliminates B, and it is a property of where each correction *lands*,
> not of how large it is. Size alone would have picked the same answer here for the wrong
> reason; the algal column, where B is neither largest nor worst, is what separates the two.

**So S6 is a choice between A and C, and B is ineligible.** Between the survivors:

| | Q1 | Q2 | Q2b | Q1 headline under S5 |
| --- | --- | --- | --- | --- |
| **A** — rate at 293 K | unchanged | needs correction | needs correction, 6.8× Ω-spread (algal) | **12.7058, inside [12, 22] — HOLDS** |
| **C** — rate at 25 °C | 10.0 → 8.4394 | unchanged | needs correction, 33.1× Ω-spread (algal) | **11.5100, outside — FAILS by 4.1%** |

**Recommendation: reading A.** Three measured reasons, none of them that it is the verdict-
preserving option. (1) Its Q2b Ω-spread is 6.8× against C's 33.1× — the smaller commitment to an
ungrounded parameter. (2) Its anchor, 293 K, is the only one of the three that the code
*declares* rather than infers: `t_set = T_REF_K` is written into `sim/organism.py:34` as Q1's
tissue set-point, whereas C's 298.15 K is carried by a field the same file labels *"declared
assumption, not grounded"*. (3) It requires changing no shipped number in the experiment whose
result is being defended, which keeps the correction and the verdict from being decided by the
same edit.

That third reason is also the honest weakness of the recommendation, and it is recorded rather
than argued away: **reading A is the option under which Q1's headline survives, and I am
recommending it.** The first two reasons stand on their own — they were measured before the
verdict table was assembled, and reason (1) is visible in the algal column where the verdict
does not appear at all — but the coincidence is real and a reader should weigh it.

### What is still NOT measured: the anchor itself

None of this recovers what temperature Westerband et al.'s `Asat` was actually measured at. It
narrows which *internally consistent* reading the project may adopt; it does not make the
anchor grounded. §13's verdict — **not recorded in the source** — stands unchanged.

One route to grounding it does now look open, and it was not visible to §13. The deposit's
methods state that _"Vcmax was estimated via the one-point method when it was not provided from
A-ci curves"_, and the deposit carries **`Vcmax25`** alongside `Asat` and `Ci:Ca`. The one-point
method converts an as-measured rate to a 25 °C standard **through a leaf-temperature term**, so
the measurement temperature is implicitly encoded in the relationship between the two deposited
columns and may be recoverable by inversion. That would replace the whole A-versus-C choice with
a measurement.

**Not attempted this pass:** Dryad's file endpoints now require a bearer token
(`/api/v2/files/*/download` → 401) and the public routes return an AWS WAF challenge (403). The
deposit metadata is public and was read; the data file was not obtained, and no attempt was made
to work around the bot protection. Recorded as the open route, not as a result.

### A tell

§16 named two readings, defined them correctly in prose, and then implemented one of them as the
other. The arm was not sloppy — it was *labelled*, and the label was checked against the prose
rather than against the factor. Every number §16 published from that arm is correct; what was
wrong was which question they answer.

> **A correctly computed arm under the wrong name is invisible to every check that compares
> results to results.** §16's arm reproduced its baseline, composed multiplicatively with S5
> exactly as predicted, and passed a mutation check. All of that is true of the reading it
> actually computed. Nothing in the section compared the *factor* to the *definition* — and the
> definition was three lines above it.

This is the same shape as §15's "a mutation that silently fails to apply is indistinguishable
from a control that cannot fail" and §16's own "the assertion must be that the edit applied to
the thing under test", one level up: here the edit applied to the right file, the arithmetic was
right, and the **name** was the thing that did not describe the object.

## References (all ghostcite-clean, 0 findings)

- **Kopp G (2011).** A new, lower value of total solar irradiance: Evidence and climate significance. *Geophysical Research Letters.* [10.1029/2010GL045777](https://doi.org/10.1029/2010GL045777)
- **Craine J M (2005).** Leaf-level light compensation points in shade-tolerant woody seedlings. *New Phytologist.* [10.1111/j.1469-8137.2005.01420.x](https://doi.org/10.1111/j.1469-8137.2005.01420.x)
- **Richardson K (1983).** Adaptation of unicellular algae to irradiance: an analysis of strategies. *New Phytologist.* [10.1111/j.1469-8137.1983.tb03422.x](https://doi.org/10.1111/j.1469-8137.1983.tb03422.x)
- **Poorter H (2011).** Biomass allocation to leaves, stems and roots: meta-analyses of interspecific variation and environmental control. *New Phytologist* 193:30–50. [10.1111/j.1469-8137.2011.03952.x](https://doi.org/10.1111/j.1469-8137.2011.03952.x) — CrossRef issues this 2011-11-15 (print issue 2012-01); cited here as 2011 because the deterministic gate compares against the CrossRef `issued` year.
- **Poorter H (2012).** Pitfalls and possibilities in the analysis of biomass allocation patterns in plants. *Frontiers in Plant Science* 3:259. [10.3389/fpls.2012.00259](https://doi.org/10.3389/fpls.2012.00259)
- **Wright I J (2004).** The worldwide leaf economics spectrum. *Nature.* [10.1038/nature02403](https://doi.org/10.1038/nature02403) — cited for context only; its area-based values were not reachable, so §4 uses a dataset instead.
- **Perera-Castro A V (2020).** It Is Hot in the Sun: Antarctic Mosses Have High Temperature Optima for Photosynthesis Despite Cold Climate. *Frontiers in Plant Science* 11:1178. [10.3389/fpls.2020.01178](https://doi.org/10.3389/fpls.2020.01178) — gold OA; ghostcite clean.
- **Colesie C (2014).** Habitat stress initiates changes in composition, CO2 gas exchange and C-allocation as life traits in biological soil crusts. *The ISME Journal.* [10.1038/ismej.2014.47](https://doi.org/10.1038/ismej.2014.47) — green OA (PMC4184013); ghostcite clean.
- **Amirian M (2026).** A Compilation of Marine Photosynthesis–Irradiance Data from 14C Incubation Experiments. Zenodo. [10.5281/zenodo.21908199](https://doi.org/10.5281/zenodo.21908199) — CC-BY-4.0 dataset; used as a NEGATIVE result (§4c).
- **Westerband A C (2022).** Australia-wide photosynthetic trait dataset. Dryad. [10.5061/dryad.j9kd51cgr](https://doi.org/10.5061/dryad.j9kd51cgr) — CC-0 dataset. ghostcite returns tier U (not in CrossRef); Dryad DOIs are registered with DataCite, and DataCite confirms first creator Westerband, publicationYear 2022, publisher Dryad.
- **Forest Products Laboratory (2010).** Wood Handbook — Wood as an Engineering Material. Centennial Edition. General Technical Report FPL-GTR-190. Madison, WI: U.S. Department of Agriculture, Forest Service, Forest Products Laboratory. 508 p. — public domain (U.S. government work); no DOI, so not ghostcite-checkable. Identity verified from the PDF's own embedded metadata (title, author "USDA Forest Service", and a full self-citation in the subject field). Used in §7.
- **Yang X (2020).** Quantifying photosynthetic performance of phytoplankton based on photosynthesis–irradiance response models. *Environmental Sciences Europe.* [10.1186/s12302-020-00306-9](https://doi.org/10.1186/s12302-020-00306-9) — CC-BY gold OA; cited in §8 as a NEGATIVE result (correct paper, full text unreachable). Byline confirmed via OpenAlex: first author Xiaolong Yang, 2020.
- **ASTM G173-03.** Standard Tables for Reference Solar Spectral Irradiances. ASTM International. — supplies §12's AM0 (extraterrestrial) and AM1.5G (surface) columns. The standard is paywalled and `nrel.gov`, its usual public host, was unreachable this session; the tabulation was taken from the pvlib-python repository's redistributed copy (`pvlib/data/ASTMG173.csv`, BSD-3-Clause), 2002 rows, 280-4000 nm. **Verified by physics rather than by byline**, since a data table has no byline to check: the AM0 column integrates to 0.9867 of the 1366.1 W/m2 solar constant it declares (residual = the out-of-band tail), its PAR photon conversion reproduces this project's own `PHOTONS_PER_J` to 0.4%, and a 5772 K blackbody independently returns a PAR energy fraction of 0.3663 against the table's 0.3879.
- **Warren S G (2008).** Optical constants of ice from the ultraviolet to the microwave: A revised compilation. *Journal of Geophysical Research: Atmospheres* 113:D14220. [10.1029/2007JD009744](https://doi.org/10.1029/2007JD009744) — closed access; the PRIMARY DATA TABLE is public at `atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat` and is what §9 uses. Byline confirmed via OpenAlex: first author Stephen G. Warren, 2008, 1285 citations.
- **Ackermann M (2006).** Optical properties of deep glacial ice at the South Pole. *Journal of Geophysical Research: Atmospheres* 111:D13203. [10.1029/2005JD006687](https://doi.org/10.1029/2005JD006687) — bronze OA; IceCube collaboration, 117 authors. Byline confirmed via OpenAlex: first author M. Ackermann, 2006, 539 citations. Used in §9 for the scattering caveat.
- **Petrovic J J (2003).** Review: Mechanical properties of ice and snow. *Journal of Materials Science* 38:1–6. [10.1023/A:1021134128038](https://doi.org/10.1023/A:1021134128038) — closed access; NOT read directly. Byline and pagination confirmed independently via CrossRef and OpenAlex (619 citations). Its tensile-strength range reaches §10 quoted verbatim through Hirata et al. 2022.
- **Scafaro A P (2023).** Rubisco deactivation and chloroplast electron transport rates co-limit photosynthesis above optimal leaf temperature in terrestrial plants. *Nature Communications* 14. [10.1038/s41467-023-38496-4](https://doi.org/10.1038/s41467-023-38496-4) — gold OA, full text read this pass. Supplies Q2b's 29.4/32.7 °C anchors, the 49-species count and the Ω definition, all quoted verbatim in §11 S4. Byline verified via OpenAlex (129 citations); co-authors Evans and Farquhar match `sim/thermal.py`'s attribution.
- **June T (2004).** A simple new equation for the reversible temperature dependence of photosynthetic electron transport: a study on soybean leaf. *Functional Plant Biology* 31:275–283. [10.1071/fp03250](https://doi.org/10.1071/fp03250) — closed access, NOT read directly; reaches this project through Scafaro 2023's verbatim quotation, at one remove. Byline verified via OpenAlex (June, Evans, Farquhar; 212 citations). **Derived on soybean leaves** — noted because §11 S4 turns on the organism.
- **Hirata N (2022).** Disruption of Saturn's ring particles by thermal stress. *Icarus* 114919. [10.1016/j.icarus.2022.114919](https://doi.org/10.1016/j.icarus.2022.114919) — green OA (Kobe University repository); full text read. Supplies §10's verbatim quotation of Petrovic's 0.7–3.1 MPa, and its reference entry for Petrovic matches CrossRef exactly.
