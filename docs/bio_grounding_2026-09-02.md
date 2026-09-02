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

## 4. `a_max` upper bound — UNRESOLVED THIS SESSION

The final review showed the algal gate is one-sided (I_c ≤ 1.0) and so places **no upper
bound on `a_max`**: `a_max` = 20 passes at I_c = 0.2429 giving r\* = 95.86 AU, and
`a_max` = 30 passes at I_c = 0.1613 with no crossover anywhere inside [0.5, 100] AU.
A literature ceiling is therefore load-bearing.

**I could not obtain one.** Attempted and blocked: Wright et al. 2004 (*Nature* — auth
redirect), Poorter et al. 2011 and 2015 (*New Phytologist* — HTTP 403, bronze/hybrid OA
is publisher-side only, no repository copy, absent from Unpaywall/EuropePMC),
Markesteijn & Poorter 2009 (*J. Ecol.* — 403, no green copy found), the CSIRO trait
handbook (redirect), De Kauwe et al. 2015 (*New Phytologist* — 403). Two further OA-
filtered OpenAlex sweeps returned nothing carrying area-based A_max ranges.

**Status: no number, and therefore no claim.** Not "roughly 30" — that would be exactly
the recall-shaped assertion this project's citation rule exists to prevent. The bound
stays open until a reachable source supplies it.

## 5. Honesty ledger (which layer each claim sits on)

| claim | status |
| --- | --- |
| Gate sources describe woody seedlings / unicellular microalgae | **real-mechanism-backed** — verified against both papers' own titles and abstract |
| LMF ∈ [0.20, 0.80] excluding adult trees | **real-mechanism-backed** — verbatim, ghostcite-clean |
| *D. flexuosa* LMF 0.31–0.46 | **real-mechanism-backed** — verbatim, species-resolved |
| Vascular LMR = 0.5 is defensible | **real-mechanism-backed** — inside the cited range |
| Unicellular alga ⇒ LMR = 1.0 | **plausible, definitional — NOT a measured value.** It follows from the model's definition plus the absence of a non-photosynthetic organ. No paper was read that reports a microalgal "leaf mass ratio", because the quantity is not normally defined for a single cell. Treat as a structural argument, not an observation. |
| Algal LMR = 0.8 "thallus mostly photosynthetic" | **convenient fiction** — the organism it invokes is not the organism the gate calibrates |
| `a_max` upper bound | **unresolved** — see §4; no source reached |
| r\* values in §2 and §3 | computed live this session against `sim/`, positive-control checked |

## 6. What this changes for Q2

- Registering `leaf_mass_ratio` with a band, not a point, and taking the band from
  Poorter & Sack (2012) rather than from an inline comment.
- Deciding the algal organism **before** registering: unicellular (LMR pinned at 1.0,
  gate already correct) or macroalgal (LMR free, gate must be re-sourced).
- `a_max` still needs a ceiling, or the one-sided algal gate keeps admitting organisms
  for which the experiment has no answer.
- **Register the gate's reachable r\* interval alongside the predicted band.** A band the
  gate cannot reach is not a prediction — §2 shows the grounded parameter range and the
  registered band only partly overlap.

## References (all ghostcite-clean, 0 findings)

- **Kopp G (2011).** A new, lower value of total solar irradiance: Evidence and climate significance. *Geophysical Research Letters.* [10.1029/2010GL045777](https://doi.org/10.1029/2010GL045777)
- **Craine J M (2005).** Leaf-level light compensation points in shade-tolerant woody seedlings. *New Phytologist.* [10.1111/j.1469-8137.2005.01420.x](https://doi.org/10.1111/j.1469-8137.2005.01420.x)
- **Richardson K (1983).** Adaptation of unicellular algae to irradiance: an analysis of strategies. *New Phytologist.* [10.1111/j.1469-8137.1983.tb03422.x](https://doi.org/10.1111/j.1469-8137.1983.tb03422.x)
- **Poorter H (2011).** Biomass allocation to leaves, stems and roots: meta-analyses of interspecific variation and environmental control. *New Phytologist* 193:30–50. [10.1111/j.1469-8137.2011.03952.x](https://doi.org/10.1111/j.1469-8137.2011.03952.x) — CrossRef issues this 2011-11-15 (print issue 2012-01); cited here as 2011 because the deterministic gate compares against the CrossRef `issued` year.
- **Poorter H (2012).** Pitfalls and possibilities in the analysis of biomass allocation patterns in plants. *Frontiers in Plant Science* 3:259. [10.3389/fpls.2012.00259](https://doi.org/10.3389/fpls.2012.00259)
- **Wright I J (2004).** The worldwide leaf economics spectrum. *Nature.* [10.1038/nature02403](https://doi.org/10.1038/nature02403) — cited for context only; its area-based values were not reachable (§4).
