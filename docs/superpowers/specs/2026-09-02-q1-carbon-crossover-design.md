# Q1 design — carbon-budget crossover distance for a single Dyson-tree organism

Date: 2026-09-02. Status: approved in brainstorm, awaiting spec review.
Grounding: `docs/prior_art_2026-09-01.md` (all numbers below cite it).

## Decisions recorded

| Decision | Choice | Why |
|---|---|---|
| Purpose | Research sim with a registered question | Roadmap requires pre-registration before any runner; failure museum must emerge, not be authored |
| Light floor | Heliocentric distance is the swept independent variable | The survey made light the binding constraint; sweeping it turns a design bet into a measurement |
| Loop | A: single organism, evaluated | B (colony) needs A's budget trusted underneath it; A is the cheapest path to a measured answer |
| Budget scope | Carbon only | One balance, one crossover; pressure and elements enter after calibration passes |
| Success | Reproduce ground truth at 1 AU, then report crossover | A crossover with no calibration gate is a number that cannot be wrong |
| Stack | Python + numpy + pytest; plots R + ggplot2 | Matches other bio-sims and repo layout; house plotting rule |
| Approach | Light-response compensation model, tissue T fixed | Every parameter sourced but one; deferred heating cost is the declared v2 |

## Registered question (Q1)

For a single organism of photosystem class C, with tissue temperature held at a set-point, at what heliocentric distance r* does whole-organism net carbon assimilation cross zero?

**Pre-registered predictions:** vascular r* in [12, 22] AU; algal r* in [35, 55] AU.

**Calibration gate (must pass before r* is reported):** at 1 AU, leaf-level compensation irradiance in [5.3, 9.0] µmol m⁻² s⁻¹ for VASCULAR (Craine & Reich 2005, 10.1111/j.1469-8137.2005.01420.x) and < 1.0 µmol m⁻² s⁻¹ for ALGAL (Richardson 1983, 10.1111/j.1469-8137.1983.tb03422.x).

**Declared v2 (not built here):** carbon cost of holding tissue temperature against radiative loss to space, giving a second crossover.

## Model

Pure functions, no state, no time axis.

- `irradiance(r_au) -> µmol m⁻² s⁻¹`: `TSI / r² × PAR_FRACTION × PHOTONS_PER_J`. TSI = 1360.8 W m⁻² (Kopp & Lean 2011, 10.1029/2010GL045777). PAR_FRACTION = 0.45 and PHOTONS_PER_J = 4.57 are named assumptions, not literals.
- `gross_assimilation(I, A_max, K) -> µmol m⁻² s⁻¹`: rectangular hyperbola `A_max · I / (I + K)`. K (half-saturation) is the one unsourced parameter and is swept, not fixed.
- `respiration(R_d, T, T_ref, Q10) -> µmol m⁻² s⁻¹ (per unit photosynthetic area)`: `R_d · Q10^((T − T_ref)/10)`. T is a fixed set-point in v1 (assumed 293 K), so light is the only distance-varying input. Q10 = 2.0 stated as assumption.
- `Organism`: dataclass `{cls, A_max, K, R_d, leaf_mass_ratio, T_set}`. `net_carbon(r) = gross(irradiance(r)) − respiration / leaf_mass_ratio`. Non-photosynthetic mass respires at the same mass-specific rate but does not assimilate; `leaf_mass_ratio` is what converts a leaf-level LCP into a whole-organism one.
- `compensation_irradiance(org)`: solves `gross(I) = respiration` for I analytically (`I_c = K·R/(A_max − R)`); raises if `R ≥ A_max`.
- `crossover_distance(org)`: root of `net_carbon(r) = 0` in r on a log grid 0.5–100 AU via Brent; raises if no sign change on the grid.

Presets: `VASCULAR` and `ALGAL`, each calibrated by choosing `R_d` so compensation lands near 7 and 0.5 µmol respectively at the default K. Calibration touches only `R_d`, never the light physics. Chosen values are written into the pre-registration file before the sweep runs.

## Data flow

Input: `experiments/q1_crossover/prereg.yaml` — presets, gate ranges, predicted r* ranges, K sensitivity grid, assumptions (PAR_FRACTION, PHOTONS_PER_J, T_set, Q10).

Runner `experiments/q1_crossover/run.py`, in order:

1. **Calibration gate.** Compute compensation irradiance per preset. Write `calibration.csv` (class, observed, gate_lo, gate_hi, pass). On any fail: print the numbers, exit non-zero, do not write crossover output.
2. **Sweep.** For each preset × K in grid: evaluate net carbon on the log grid, root-find r*. Write `sweep.csv` (class, K, r_au, net_carbon; long format) and `crossover.csv` (class, K, r_star, pred_lo, pred_hi, inside).
3. **Provenance.** Every CSV starts with `#` header lines: git SHA, md5 of `sim/physiology.py`, md5 of `prereg.yaml`, ISO timestamp.

Plots: `experiments/q1_crossover/plot.R`, sourcing `docs/analysis/theme.R` (created here as the house theme). Reads CSVs only. Two figures, one graph each: net carbon vs distance per class (K as linetype), and r* vs K per class with the predicted band.

## Testing

`tests/` under pytest, split by what each can fail on:

- **Physics identities:** `irradiance(1) ≈ 2000` under the stated assumptions; `irradiance(10) == irradiance(1)/100`. Guard refactors.
- **Calibration:** each preset's compensation irradiance inside its gate. The scientific test.
- **Controls, in the same test as the healthy path:** `R_d = 0` ⇒ compensation 0 and no crossover (raises); `R_d × 2` ⇒ r* strictly inward of baseline. Asserted alongside the baseline passing, per the negative-needs-a-positive-control rule.
- **Runner:** a failing preset ⇒ exit non-zero and `crossover.csv` absent; real presets ⇒ both CSVs exist with provenance header.

## Error handling

Fail loud, nothing defaulted. Out-of-range parameters (negative rates, `leaf_mass_ratio ∉ (0,1]`, `r ≤ 0`) raise with the offending value. Root-finder raises on no sign change. Runner exits non-zero on gate failure.

## Out of scope (v1)

Temperature varying with distance; heating cost (v2); pressure vessel; element stoichiometry; population, inheritance, or any time axis; any play surface.

## Files

```
sim/physiology.py            irradiance, gross_assimilation, respiration, compensation_irradiance, crossover_distance
sim/organism.py              Organism dataclass, VASCULAR, ALGAL presets
experiments/q1_crossover/    prereg.yaml, run.py, plot.R, (outputs: calibration.csv, sweep.csv, crossover.csv)
docs/analysis/theme.R        house ggplot2 theme, sourced by every plot script
tests/test_physiology.py, tests/test_calibration.py, tests/test_runner.py
```
