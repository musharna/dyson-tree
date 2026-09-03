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
