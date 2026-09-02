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
| r\* values in §2 and §3 | computed live this session against `sim/`, positive-control checked |

## 6. What this changes for Q2

- Registering `leaf_mass_ratio` with a band, not a point, and taking the band from
  Poorter & Sack (2012) rather than from an inline comment.
- Deciding the algal organism **before** registering: unicellular (LMR pinned at 1.0,
  gate already correct) or macroalgal (LMR free, gate must be re-sourced).
- **Give the algal gate a lower bound on I_c.** §4 shows a ceiling on `a_max` does not fix
  it: the gate passes at the 530-species maximum and still returns no crossover. A gate
  with no floor cannot exclude an arbitrarily efficient organism.
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
- **Westerband A C (2022).** Australia-wide photosynthetic trait dataset. Dryad. [10.5061/dryad.j9kd51cgr](https://doi.org/10.5061/dryad.j9kd51cgr) — CC-0 dataset. ghostcite returns tier U (not in CrossRef); Dryad DOIs are registered with DataCite, and DataCite confirms first creator Westerband, publicationYear 2022, publisher Dryad.
