# Northstar design: the vessel, and watching it fail

> Revised 2026-09-12 after an llm-panel audit (impaired: codex/astra unavailable); findings in the coordinator's memory memo `northstar_panel_audit_2026-09-12.md`.
> Revised again 2026-09-12 after the round-2 panel audit: prediction 1 re-banded on the edge wall, bands hand-written from committed rows (§6), Q4 registers on FREEZE/STARVE/OPAQUE only, the deck's third rule demands first violation inside the registered box, M1 split into M1a0/M1a.

> Drafted 2026-09-12 against `release/1.0.1-rc` (`7ed4414`); revised against `master`
> (`08fac2e`). Every claim about current code carries a `file:line`. Nothing here edits
> a frozen pre-registration.
> Supersedes the modelling direction of `2026-09-04-q3-pressure-vessel-design.md`
> (whose four correction banners are the input to §3 below); does not supersede
> `docs/ROADMAP.md`, which must be bannered to point here in the same commit that
> starts M1a. §§1-10 are Act One (Q4, the vessel, watching it fail); §11 is the story
> order after Q4 as the user set it on 2026-09-12, and §7 defers to it by chapter.

## 1. Northstar

A visitor sees a cross-section of a sealed, transparent sphere with a green organism
inside it, at a distance from the Sun they can drag, and the sphere is either alive or
it is bursting, freezing, boiling dry, starving, or going dark under its own wall. They
change one input (radius, wall, pressure, distance, organism) and the picture changes
state, with the number that killed it printed beside the wound. Nothing is authored:
every failure is an inequality between quantities the repository grounds, or one
declared and disclosed as such, and the visitor can read both sides.

## 2. What exists today that this reuses

What is true now: the live page is an uncontained organism at a fixed tissue
temperature (`web/index.html:128-132`), with a class dropdown, a `k` dropdown and a
log-spaced distance slider (`web/index.html:77-91`, `web/app.js:62-89`), driving one
net-carbon curve (`web/app.js:114-284`). The page itself says "No pressure vessel" and
"No spectral wall" (`web/index.html:130-135`). The model has no tree: `Organism` is a
frozen dataclass of 11 numeric fields plus `cls` (`sim/organism.py:27-40`), two presets
(`:163-173`).

Reused as-is, no edits:

- **Light in.** `irradiance(r_au)` is `TSI / r² × PAR_FRACTION × PHOTONS_PER_J`
  (`sim/physiology.py:22-30`), TSI 1360.8 (`:14`), PAR fraction 0.3879 measured AM0
  (`:16`). `gross_assimilation(i, a_max, k)` (`:33-43`), `respiration(r_d, t)`, Q10 (`:46-54`).
- **Thermal core.** `equilibrium_temperature(r_au, area_ratio, emissivity, albedo)`
  (`sim/thermal.py:20-46`; `area_ratio` is pure geometry, `:28-30`);
  `temperature_response_gaussian(t, t_opt, omega)` (`:65-86`), the June 2004 form.
- **Organism.** `Organism` fields incl. `area_ratio` (2.0 lamina default, `:35`; ALGAL
  declares 4.0, `:170`), `t_opt` "declared assumption, not grounded" (`:37`), `omega`
  "DECLARED ASSUMPTION" (`:40`), `emissivity`/`albedo` declared (`:38-39`).
  `compensation_irradiance(org)` is evaluated at `t_set` = 293 K (`:126-135`, via
  `leaf_respiration` `:70-72`): no temperature argument, no distance term. `net_carbon`,
  `net_carbon_at_equilibrium`, `net_carbon_adapted` stay untouched (`:80-123`).
- **The r slider.** `R_MIN 0.5`, `R_MAX 100` AU (`web/app.js:29-30`); quantised to 3 dp
  so "the distance shown is the distance used" (`:66-85`). Kept verbatim.
- **Parity.** `web/model.js` is a classic script exporting `DysonModel` for the browser
  and `module.exports` for node (`web/model.js:9-13, 267-271`); each function names its
  `sim/` lines (`:22, :32, :59`). `tests/test_parity_js.py` fails rather than skips
  without node (`:33-38`), pins fixtures to the md5 of each `sim/*.py` (`:82-99`), and
  runs 9 tests incl. crossovers against the committed CSV (`:155`).
  Fixtures come only from `sim/` public functions (`tools/make_fixtures.py:2-7`).
- **Site build and rail.** `tools/build_site.sh` copies an allowlist of three files
  (`:16-19`) and refuses remote assets (`:36-40`). `pages.yml` on master checks out with
  `fetch-depth: 0` (`:34`), pins python 3.13.2 (`:42`), runs pytest incl. parity before
  upload (`:45-51`), then `build_site.sh` (`:52-53`). `pyproject.toml:24-25` discovers
  `sim*` and `experiments*` only, so `sim/vessel.py` and `experiments/q4_vessel/` are
  packaged without edits; `web/` is not a package. CSV `git_sha` must be a reachable
  ancestor of HEAD (`tests/test_derived_csvs.py:198-221`): regenerate CSVs and fixtures
  last, never amend after. M1a starts from `master`.
- **Vessel arithmetic already computed in `tools/`, not in `sim/`:** Buck saturation
  pressure (`tools/check_greenhouse_transparency.py:99-100`), solar-weighted wall
  transmission `tau_sw(t)` (`:94-96`), the damped fixed point `p -> t -> tau -> T ->
p_sat` (`:120-130`), and the PAR photon fraction behind a wall
  (`tools/size_par_filter.py:177-195`). The tools open `iop2008.dat` and `ASTMG173.csv`
  (`tools/extract_ice_k.py:10`, `check_greenhouse_transparency.py:38`), gitignored
  (`.gitignore:9-10`) and absent from this checkout, so today they cannot run. M1a moves
  the arithmetic into `sim/` with tests; the tools become positive controls, not sources.

## 3. The vessel model

What would be true: one sphere, one wall, one organism inside, five inequalities. The
arithmetic below has no new physics; every symbol is already grounded in this repo or
is declared and disclosed as an input.

**Geometry and load.** Thin-wall sphere of internal radius `R` (m), wall thickness `t`
(m), internal pressure `p` (Pa) against ~0 ambient. Hoop stress
`sigma_hoop = p·R / (2·t)` (q3 spec `:133`; `docs/prior_art_2026-09-01.md:58`).
The wall that just holds `p` is `t_min = p·R / (2·sigma)`. The hoop formula is thin-wall;
the sliders reach `t/R = 100` (R 10 m, manual t 1 km), so the BURST line prints a validity
flag whenever `t/R >= 0.1` and the page states the formula is outside its domain there.

**Wall material.** The wall must be clear: pigmented tissue at 0.625 m passes
`e^-3952` (q3 spec `:168-171`). The only clear material with both a grounded strength
and grounded optics is pure water ice: tensile `sigma` **0.7 to 3.1 MPa** (Petrovic
2003 via Hirata 2022, `bio_grounding` §10 `:613-615`, grounded at one remove) and
absorption `k(lambda) = 4·pi·m_im/lambda` from Warren & Brandt 2008 (`§9:519-537`);
`sigma` is a page input, default 0.7 MPa (the weak end), swept in Q4. The wood MOR
**80 MPa median** (§7 `:456-462`) is NOT a wall input:
pairing wood strength with ice optics is the ~53x error §10 records (`:596-608`), and
the rule "a pair of grounded inputs must describe the same object" (`:689-690`) is a
test in M1a, not a comment; it asserts by material id, not citation string, with a
positive case (`sigma_ice`, `k_ice`) that passes and a negative case (`sigma_wood`,
`k_ice`) that fails. Wood remains only a labelled counterfactual with its own
`k`, UNGROUNDED, needs a source, and so is not on the page.

**Spectral wall, not a scalar.** `k` spans 0.00074 /m at 400 nm to 0.52061 /m at
700 nm, a factor of 701 (`§9:532-540`). Transmission through thickness `t` is
`tau(lambda, t) = exp(-k(lambda)·t)`. Two integrals of it are the wall:

- `f_photon(t) = ∫₄₀₀⁷⁰⁰ tau(λ,t)·n_ph(λ) dλ / ∫₄₀₀⁷⁰⁰ n_ph(λ) dλ`, the fraction of
  AM0 PAR photons that arrive (`tools/size_par_filter.py:181-186`). This is the
  photon count, not a chlorophyll-weighted rate (`§12:959-963`); it is an upper bound
  on what the organism can use, stated as such on the page.
- `tau_sw(t) = ∫₂₈₀⁴⁰⁰⁰ tau(λ,t)·E(λ) dλ / ∫ E dλ`, solar-energy-weighted
  (`check_greenhouse_transparency.py:94-96`). NIR carries 53% of TSI and ice absorbs
  it (`§13:1021-1025`): at `p*` and R = 10 km a pressure wall passes 26 to 34% of solar
  energy (`tau` 0.2609 to 0.3429, `§13:1054-1058`); the 16 to 23% (`§13:1036`) belongs
  to the withdrawn 18 kPa walls.

**The coupling that closes S2.** Today `irradiance(r)` feeds an unfiltered scalar to an
organism the vessel finding requires to sit behind a blue-pass wall
(`docs/FINDINGS.md:428-433`). The closure is one line: `I_wall(r, t) = (1 - albedo) ·
irradiance(r) · f_photon(t)`, fed to `gross_assimilation` in a new
`Organism.net_carbon_contained` placed BESIDE the three existing paths, which do not
change. `1/r²` stays inside `irradiance` (`sim/physiology.py:29`); the wall factor is
distance-independent by construction, which keeps the two separable on the page;
`(1 - albedo)` enters linearly, as on the absorbed side of `equilibrium_temperature`
(`sim/thermal.py:46`).

**Contained temperature.** `T_int = (1 + tau_sw(t))^0.25 · T_eq(r, area_ratio, eps,
albedo)` (`§13:1040-1046`; the `(N+1)^0.25` form is its `tau = 1` case). The derivation
is a spherical shell radiating from both faces, so `contained_temperature` fixes the
geometry at the sphere's `area_ratio = 4`; the organism's `area_ratio` (`sim/organism.py:35`,
lamina default 2.0) does not enter it, and choosing the vascular class changes the
organism, not the vessel. The shell sits at `T_shell = T_eq` exactly, independent of `tau` (`§17:1459-1460`).

**Vapour pressure at the contained temperature.** Buck: `p_sat(T_C) = 611.21 ·
exp((18.678 - T_C/234.5)·(T_C/(257.14 + T_C)))` (`check_greenhouse_transparency.py:99-100`);
it returns 611.654 Pa at 273.16 K and 882.22 Pa at 5.16 °C against the gate points
611.657 and 882 Pa (q3 spec `:217-220`), so Gate C carries a tolerance (§6).

**Self-consistent pressure, a function.** `p*(r, R, sigma) = p_sat(T_int(t_min(p*)))`,
solved by the damped iteration at `:120-130`. At 1 AU and R = 10 km it is 3.453 /
3.002 / 2.607 kPa for sigma 3.1 / 1.5 / 0.7 MPa (`§13:1054-1058`); as `R -> 0`,
`tau_sw -> 1` and `p*` rises to S1's 18.02 kPa ceiling (`§13:1060-1062`); at the page
default (1 km, 1.10 AU) it is another number, printed live beside the player's `p`.

**The roadmap's closed form, and why it is a control here.**
`R_max = 2·sigma·|ln tau_min| / (k·p)` (`docs/ROADMAP.md:145`, q3 spec `:139`) follows
from `t = pR/(2σ)` and `tau = e^{-kt}` with a scalar `k` and an acceptable `tau_min`.
Its two defects are named in the repo: `k` is not a scalar (`§9:539`) and `tau_min` is
author-declared, "NOT GROUNDED" (q3 spec `:166`). Here `k` becomes the integral above;
`tau_min` does not vanish, it becomes the declared floor `f_floor` of OPAQUE (§4),
disclosed and swept. The closed form survives as two unit-test controls at `k = 0.38623`
and `tau_min = 0.01`. (a) A port-regression of §13's mixed row: with `p` taken from the
SPECTRAL fixed point (3453.08 / 3002.39 / 2606.63 Pa) the closed form gives 21.41 /
11.91 / 6.40 km (`§13:1073-1077`). (b) The scalar limit end to end: with `tau_sw(t) =
e^{-kt}` inside the fixed point too, `p*` is 2346 / 1581 / 1104 Pa and `R_max` 31.51 /
22.62 / 15.13 km. A correct scalar-limit implementation passes (b) and fails (a), so
each control names which path it exercises.

**Declared assumptions, five, all exposed as inputs:** `t_opt` and `omega`
(`sim/organism.py:37,40`); `albedo` and `emissivity` (also `Organism` fields, `:38-39`,
read here as the shell's); `f_floor` (§4). Albedo is not cosmetic: at 1 AU the shell
melts at albedo 0 and freezes at 0.0721 (`§17:1501-1502`); if `albedo > 0` the same
`(1 - albedo)` scales `I_wall`, since Beer-Lambert models absorption only and is
consistent with `albedo = 0` (`§17:1505-1509`). Dust: magnitude ungroundable, direction
pinned downward on `tau`, `T_int`, `p*` (`§15:1287-1297`); the page carries a `dust
floor` toggle {none, 0.0087, 0.0548 /m} labelled DECLARED; Q4 registers on `none`.

## 4. The failure modes, as arithmetic

Each is an inequality evaluated from the inputs; the page prints both sides. There is
no `if failure_type == ...` anywhere; `classify_failure` returns the set of violated
inequalities and the first in load order names the picture. Four compare grounded
quantities; OPAQUE compares one to a declared floor and says so on its line.

**On the auto path two lines are equalities, not tests.** With `t = t_min`, hoop stress
equals `sigma` exactly; with `p = p*`, `p` equals `p_sat(T_int)` to the fixed point's
residual (`|Δp| < 1e-6` Pa, `check_greenhouse_transparency.py:127`). BURST and BOIL
therefore hold by construction on the auto path (except BURST's `sigma(T_shell) = 0`
door inside 1.0381 AU) and are failure modes of manual gestures only. Every comparison
carries a stated epsilon (BURST and BOIL: 1e-6 relative; FREEZE: 1e-6 K; STARVE and
OPAQUE: 1e-9 in their units) so a HOLD is never a solver residue, the readout prints the
margin beside each HOLD, and on the auto path it prints BURST's and BOIL's margins as
0 by construction. Q4 registers on FREEZE, STARVE and OPAQUE only (§6).

**BURST.** `p·R/(2t) > sigma(T_shell)`. `sigma` is Petrovic's 0.7 to 3.1 MPa while the
shell is solid, and 0 when `T_shell = T_eq(r) > 273.15 K`, because the wall is then
water, not ice (`§17:1465-1471`: at 1 AU, albedo 0, the coldest part of the wall is
5.16 °C). Two doors, one inequality: too much pressure for the wall you built, or a
distance so close the wall is not a solid. The annulus's inner edge, 1.0381 AU at
albedo 0 (`§17:1480-1486`), falls out of `sigma(T_shell) = 0`, not a stored number.

**FREEZE.** `T_int < 273.15 K`. `T_int = (1+tau_sw)^0.25 · T_eq(r)` drops below melting
outward: at R = 10 km and `p = p*` the edge is 1.211 to 1.261 AU across the three sigmas
(§6), 1.468 AU in the `tau = 1` limit of a vanishing wall. The interior frosts.

**BOIL.** `p < p_sat(T_int)`. The player holds less than the vapour pressure at the
contained temperature and the water leaves as gas; this is the vessel's premise, no liquid phase in vacuum
(`docs/thermal_premise_retired_2026-09-03.md:46-60`). Same family as FREEZE (no liquid
phase), but its own line, its own cue (the interior dries, no frost) and its own door,
the `p` slider.

**STARVE.** `net_carbon_contained(r, t) < 0`, where gross is
`gross_assimilation(I_wall, a_max, k) · temperature_response_gaussian(T_int, t_opt,
omega)` and respiration is `respiration(r_d, T_int) / leaf_mass_ratio`: a new path
beside `net_carbon_adapted` (`sim/organism.py:102-123`), with `T_eq` replaced by
`T_int`, `irradiance` by `I_wall`, and `t_opt` a declared field, not `adapted_optimum`.
Because `f_photon` is a photon count that over-credits the surviving blue band
(`§12:959-963`), STARVE fires later than it should; the page says so under the readout.
At the defaults it is far from firing: ALGAL's `I_c` is 0.492 µmol
(`compensation_irradiance`, `:126-135`) against 1993.6 µmol at 1.10 AU, 2.5e-4. There
is no `I_c(T_int)` in the repo; a temperature-consistent threshold is algebraically the
STARVE line itself, not a second inequality.

**OPAQUE.** `f_photon(t_min(R)) < f_floor`, a predicate on the wall alone: `t_min =
pR/(2σ)` rises linearly in `R` and the photon fraction falls with it. `f_floor` is
DECLARED, default 0.25, printed on its line as "declared floor" with the reason beside
it: 24.3% is the thickest wall the repo has sized at a non-withdrawn pressure (71.4 m,
10 kPa, 0.7 MPa, `§12:935`; the 128.7 m row at `:938` is the withdrawn 18.02 kPa); Q4 registers on 0.25 and reports {0.10, 0.50} as sensitivity arms. This is
the bind the roadmap sweeps at 0.93 to 4.10 km against an assumed 10 km
(`docs/ROADMAP.md:187`; `§11:750`), computed with a red-band scalar `k` and the
since-withdrawn 18 kPa. §12's table (`:928-938`) gives 24 to 44% at 10 km on its 10 kPa
rows (`:933-935`), so at `p*` (2.6 to 3.5 kPa, thinner walls) the spectral wall is
expected to bind well above the red-band radius; §6 registers that.

## 5. The player loop, one screen

What the visitor sees: left, a cross-section; right, seven inputs and one verdict
panel. The existing curve and readouts move below, unchanged, as "the uncontained model".

**Goal on the glass.** Q4's question is printed on the page: at the current `r` and
`sigma`, the live `R_window` (the largest `R` at which every line HOLDS) is drawn beside
the registered floor from `prereg.yaml`, provisional until M4 labels it HELD or FAILED.
The visitor's job is to find the largest sphere that lives.

**Inputs** (all sliders, values printed; defaults in brackets): vessel radius `R`
[1 km, log 10 m to 100 km]; wall thickness `t` [auto = `t_min`, or manual, log 0.01 m
to 1 km]; internal pressure `p` [auto = `p*`, or manual]; distance `r` [1.10 AU, the
existing slider]; ice tensile strength `sigma` [0.7 MPa; 0.7, 1.5, 3.1]; organism class
[algal]; wall material [ice, the only grounded option]. Under a "declared assumptions"
disclosure: `albedo` [0.0], `emissivity` [1.0], `t_opt` [298.15 K], `omega` [20 K],
`f_floor` [0.25], dust floor [none]. Auto is the self-consistent design; manual over- or under-builds.
When `p` goes manual with `t` on auto, `t` freezes at `t_min(p*)` and does not re-track
the manual `p`; otherwise hoop stress would equal `sigma` at every `p` and the BURST
gesture below could never fire.

**The picture.** An SVG cross-section: outer circle radius ∝ `R + t`, inner circle
∝ `R`, wall band at its true ratio `t/R` (clamped to a visible minimum, clamp labelled).
Interior hue from the transmitted PAR spectrum (blue-shift as `t` grows: `tau(λ,t)` at
31 PAR rows), brightness from `f_photon`. Organism: a green disc whose saturation is
`net_carbon_contained / a_max`, grey at zero. Overlays, each keyed to its inequality:
BURST fractures the wall with `p·R/2t` vs `sigma` at the break; FREEZE frosts the
interior with `T_int` vs 273.15 K; BOIL dries it with `p` vs `p_sat(T_int)`; STARVE
fades the disc with `net` vs 0; OPAQUE darkens the interior with `f_photon` vs `f_floor`
(labelled declared). No text-transform anywhere (`web/index.html:29-33`).

**The readout panel.** One line per inequality, both sides as numbers with units, HOLDS
or VIOLATED. Below: `p*`, `t_min`, the window `[r_melt, r_freeze]` for the current wall,
and the live `R_window` against the registered floor.

**The first 60 seconds**, at the defaults (1 km, 1.10 AU, 0.7 MPa, auto wall and
pressure). Load: alive; FREEZE, STARVE and OPAQUE HOLD with margins, BURST and BOIL
at margin 0 by construction (§4). Drag `r` inward: at 1.038 AU the wall line turns to
water and BURST fires with `sigma = 0`. Drag outward: the interior frosts at the edge
`model.js` prints for this wall; at the defaults `p*` is 2033.6 Pa, `t_min` 1.453 m,
`tau_sw` 0.4445 (between the 0.625 m row's 0.5086, `§13:1031`, and the 16.1 m row's),
and the edge for that self-consistent wall is ≈1.29 AU (1.2863); the page prints the
computed value, not a figure from this spec. Push `p` above `p*` (with `t` frozen, §5
inputs): BURST. Pull `p` below `p_sat`: BOIL. Set `t` manual and thicken it: the
interior goes blue, then OPAQUE at the declared floor (≈67 m), then FREEZE once
`tau_sw` falls under 0.1227 (past ≈281 m at 1.10 AU). Raising `R` alone at 1.10 AU:
`R_window` there is provisionally ≈115 km (§6), so it may or may not die inside the
100 km slider; that is why it is printed. STARVE is the one line no gesture reaches at the defaults (§4); it
stays a HOLD and the sweep asks whether any registered `(r, R, sigma)` reaches it.

## 6. Pre-registration Q4

**Question.** At self-consistent pressure `p*` and a spectral ice wall, is there ANY
radius `R` at which the vessel is strong enough to hold liquid water and clear enough
to pass the declared photon floor, and at what distance `r` does that window close?

**Quantities.** For each `r` on the registered grid, each `sigma` in {0.7, 1.5,
3.1} MPa, and `R` on a log grid from 10 m to 1000 km (wider than the page slider, so
closure can be found): `R_window(r, sigma)` = the largest `R` at which all five
inequalities of §4 hold with `p = p*(r, R, sigma)` and `t = t_min`; `r_close(R, sigma)`
= the largest `r` with the window open at that fixed `R`; `binding` = the inequality
that closes it, named by `classify_failure`. A window edge is a curve, so each
registration fixes one axis at a declared value. `binding` is drawn only
from FREEZE, STARVE and OPAQUE: BURST and BOIL hold by construction at `t = t_min`,
`p = p*` (§4) and can neither bind nor lose a prediction.

**Where the bands come from.** The bands below are HAND-WRITTEN in this spec from the
committed rows in the table that follows, and `prereg.yaml` copies them verbatim; a test
asserts the prereg's band strings equal this section's. The rows are reproduced in M1a0 by
`tools/q4_hand_rows.py`, committed with its output beside the spec's table; it uses the
`tools/` loaders (`check_greenhouse_transparency.py:38-63`, `size_par_filter.py:135-150`)
and the existing `sim/thermal.py`, `sim/physiology.py`, `sim/organism.py` functions, and
imports nothing from `sim/vessel.py`. M1a's code computes the same points and is the
object under test, never the source of a band: a computed point outside its hand band
FAILS, it does not re-register. An empty window at every `r` would falsify both and be
the headline finding.

| row | fixed | wall at the edge | edge |
| --- | --- | --- | --- |
| P1, σ 0.7 MPa | R 10 km | `p` = p_sat(0 °C) = 611.21 Pa, t 4.366 m, τ_sw 0.3610, f_photon 0.676 | r 1.2111 AU |
| P1, σ 1.5 MPa | R 10 km | 611.21 Pa, t 2.037 m, τ_sw 0.4187, f_photon 0.807 | r 1.2365 AU |
| P1, σ 3.1 MPa | R 10 km | 611.21 Pa, t 0.986 m, τ_sw 0.4741, f_photon 0.894 | r 1.2605 AU |
| P2 OPAQUE, f_floor 0.25 | r 1.10 AU, σ 0.7 | p* 816.6 Pa, t 67.05 m, T_int 277.21 K | R 114.9 km |
| P2 FREEZE | r 1.10 AU, σ 0.7 | p* = 611.21 Pa, t 280.6 m, τ_sw 0.1227 | R 642.6 km |
| P2 arms | r 1.10 AU, σ 0.7 | f_floor 0.50 / 0.10 | R 12.7 km / 935.1 km |

**Registered prediction 1, in `r` at fixed `R = 10 km`, dust none, albedo 0, algal:**
**`r_close(10 km, sigma) ∈ [1.20, 1.27] AU` for every sigma, `binding = FREEZE`.**
Hand reading (rows above): the edge is `(1 + tau_sw)^0.25 · T_eq(r) = 273.15 K` with the
wall evaluated AT the edge, where `p* = p_sat(0 °C) = 611.21 Pa` and `t = 611.21·R/(2σ)`;
with `T_eq(1 AU, 4) = 278.311 K` that is 1.2111 / 1.2365 / 1.2605 AU, and a full
fixed-point root-find on `T_int(r) = 273.15 K` returns the same to 4 dp. §13's 1 AU walls
(`tau` 0.2609 / 0.3013 / 0.3429, `:1054-1058`) are thicker than the edge wall and would put
the edge at 1.166 / 1.184 / 1.203 AU; that reading is wrong because `p*` falls with `r`.
At the edge STARVE holds (+1.98 µmol) and OPAQUE holds (f_photon ≥ 0.676), so FREEZE is
the binding. The 1.1446 AU row (`§17:1482`) is the strong-dust arm (`§15:1291`), excluded
by "dust none", not a widening. Gate A cannot pre-decide it (edges at 275 / 282 K span
1.138 to 1.309 AU). It loses on a computed edge outside [1.20, 1.27] AU for any sigma, or
a binding other than FREEZE. **The page must
also show the `R -> 0` limit: `tau_sw -> 1` and the edge is 1.468 AU (`(1.18921 ·
278.311 / 273.15)²`); STARVE there is still +1.98 µmol.** That is the family's ceiling,
not the registration.

**Registered prediction 2, in `R` at fixed `r = 1.10 AU`, `sigma = 0.7 MPa`, dust none,
`f_floor = 0.25`:** **`R_window ∈ [60, 300] km`, `binding = OPAQUE`.** Hand
reading (rows above): the 0.25 floor is crossed at t = 67.05 m, which at the
self-consistent `p* = 816.6 Pa` is R = 114.9 km; STARVE holds there (+3.11 µmol).
FREEZE at 1.10 AU (`T_eq = 265.36 K`) needs `tau_sw < 0.1227`, reached at t = 280.6 m
(§13's 128.7 m row, `tau` 0.1598, `:1034`, is not yet there), which at `p* = 611.21 Pa`
is R = 642.6 km. OPAQUE binds with a factor 5.6 in `R` to spare. The red-band closed
form, 6.40 km at 1 AU (`§13:1077`), sits far below. This loses two ways: `R_window`
outside [60, 300] km (below 60 km would put the spectral wall near the scalar it
corrects; between 300 and 643 km OPAQUE still binds but the reading is wrong), or
`binding` named STARVE or FREEZE. The band is conditional on `f_floor = 0.25`: the 0.50
arm is expected at ≈12.7 km, below the band, and the 0.10 arm at ≈935 km, past FREEZE's
642.6 km, so that arm is expected FREEZE-bound. Both arms are reported, not registered.

**Gates the registration rests on: A and C.** Gate A: `T_eq(1 AU, sphere) ∈ [275, 282]
K` (q3 spec `:211-212`). Gate C: `saturation_pressure` gives 611.657 Pa at 273.16 K
within atol 0.01 Pa (Buck: 611.654) and 882 Pa at 5.16 °C within atol 0.5 Pa (Buck:
882.22) (q3 spec `:217-220`). Gate B as the q3 spec wrote it (`:213-216`, a measured
transmission through a stated thickness of ice) has no source in the repo and cannot
fail; it is demoted to a unit test (`transmission_spectrum` at one `k` equals
`exp(-k·t)`; the committed `k(λ)` table carries its source file's md5 and size in its
header, and CI, where the gitignored source is absent by construction, asserts the
table's internal invariants: row count, endpoints 0.00074 /m at 400 nm and 0.52061 /m at
700 nm, strictly increasing λ) and nothing is registered on it. The gates touch the
radiative core and vapour pressure only, not `sigma`, `albedo`, `t_opt`, `omega`,
`f_floor`, which are swept or declared. A failing gate blocks the sweep and exits 2, as
Q2 did (`docs/FINDINGS.md:206-209`).

**Declared, explicit:** `t_opt = 298.15 K`, `omega = 20 K`, `albedo = 0`,
`emissivity = 1`, `f_floor = 0.25`, dust `none`; `R_ORGANISM` is swept, not assumed,
and prediction 1 names 10 km only as its fixed point.

## 7. Non-goals for this arc

- Colony loop (B): needs A's budget trusted first (`docs/ROADMAP.md:118-121`).
- Growth over time: one design, evaluated; a tick would need a mass budget nobody has.
  Stays out until §11 chapter 3 integrates carbon over an orbit.
- Orbit mechanics: DEFERRED to §11 chapter 3, which replaces the `r` slider with
  (perihelion, aphelion, period).
- 3D: the cross-section carries every quantity; a third dimension is decoration.
- Elements budget: DEFERRED to §11 chapter 6; spine item 1 is ungrounded for K
  (`docs/ROADMAP.md:95-98`) and would enter here as a sixth authored constraint.
- Wood or pigmented walls: `k` for wood is UNGROUNDED; the §10 pairing rule forbids it.
  Scattering magnitude: direction pinned only (`§15:1293-1297`); shipped as a toggle.
- Chlorophyll action spectrum: not grounded; inventing one manufactures S2's defect.
- A temperature-consistent compensation irradiance: it is the STARVE line (§4).
  Buckling, creep, conduction, shell stacking: q3 spec `:227-241` keeps them out.

## 8. Milestones

- **M1a0 (S): the table and the hand rows.** Nothing below runs without it. Fetch
  `iop2008.dat` and `ASTMG173.csv` (gitignored, `.gitignore:9-10`, absent from the
  checkout). Extend `tools/extract_ice_k.py`, which today filters PAR only
  (`:21`, `0.40<=l<=0.70`), to also write a coarse NIR grid to 4000 nm by the log-space
  interpolation `check_greenhouse_transparency.py:63` already uses (250 to 4200 nm);
  commit the derived `k(λ)` table (31 PAR rows plus the NIR grid) under `sim/` with a
  provenance header naming the Warren & Brandt file, its md5 and size (§10 Q1), and the
  Gate B invariant test. Commit `tools/q4_hand_rows.py` and its output (§6). Acceptance:
  the output reproduces §6's rows to the printed digits.
- **M1a (M): the vessel, in Python.** `sim/vessel.py` (`wall_thickness`, `hoop_stress`,
  `transmission_spectrum`, `par_photon_fraction`, `solar_transmission`,
  `saturation_pressure`, `contained_temperature`, `self_consistent_pressure`,
  `classify_failure`), `Organism.net_carbon_contained` beside the existing paths, the
  §10 same-object test, the two closed-form controls (§3: 21.41 / 11.91 / 6.40 km mixed,
  31.51 / 22.62 / 15.13 km scalar limit), Gate C with its atol, the Gate B unit test, and
  `experiments/q4_vessel/prereg.yaml` with both bands and bindings copied verbatim from
  §6. Acceptance: `pytest` green with the new tests; the prereg-equals-spec band test
  passes; `prereg.yaml` names two bands and two bindings the sweep has not been run
  against, and no band string is written by `sim/vessel.py`.
- **M1b (M): the numbers, in the browser.** The port to `web/model.js` with new
  fixture cases and parity tests. Acceptance: on the live page a stranger opens the
  console and `DysonModel.classifyFailure(...)` at the prereg's example inputs returns
  the set the prereg prints; `tests/test_parity_js.py` covers it.
- **M2 (M): the verdict.** The seven inputs and the readout panel, no picture.
  Acceptance: at defaults FREEZE, STARVE and OPAQUE HOLD with positive printed margins
  and BURST and BOIL print margin 0 by construction; dragging `r` past the registered
  `r_close` (at `R` = 10 km) flips exactly one line to VIOLATED and it is FREEZE.
- **M3 (L): the picture.** The cross-section, driven only by `model.js` outputs.
  Acceptance: at an unclamped check state (R 1 km, manual t 50 m, `t/R` = 0.050) the drawn
  wall band's pixel thickness divided by the inner radius equals `t/R` from the readout to
  2 dp; at the defaults (`t/R` = 1.45e-3) the clamp is active and the clamp label is
  asserted present instead; `smoke_page.py` measures both from the DOM.
- **M4 (M): the run.** `run.py`, `RESULTS.md`, `sweep.csv` with provenance headers,
  FINDINGS §5, the `r_close` band drawn hatched as Q1's is (`web/app.js:118-119`).
  Acceptance: the page shows the hatched prediction beside the measured `r_close`,
  labelled HELD or FAILED, and the README's opening paragraph counts four questions.

## 9. Risks: three ways this becomes another parameter plotter

1. **The verdict becomes a label on a curve.** Guard: M2 ships before any plot; the
   panel has no x-axis; `classify_failure` is the only source of the words
   BURST/FREEZE/BOIL/STARVE/OPAQUE and a test asserts they appear nowhere else in `web/`.
2. **Author-chosen thresholds creep back in** (a safety factor, a "viable" pressure).
   Guard: `sim/vessel.py` may contain no numeric threshold except 273.15, 611.657 and
   sourced material constants; a test greps for literals and every one must carry a
   `# source:` on its line. `f_floor` is not a literal there: it is an argument with no
   default, supplied by the page and by `prereg.yaml`.
3. **The picture corrects the label, not the value** (the 1.0 lesson: a page that read
   1.000 AU and evaluated 0.99987). Guard: every drawn geometry is read back from the
   DOM by `smoke_page.py` against `fixtures.json`; M3 passes only through an independent
   visual critic, not the author's read.

## 10. Answered 2026-09-12

1. **Commit a derived `k(λ)` table? Yes.** The page must work from `file://` with no
   fetch, and Warren & Brandt's table is "not redistributed here"
   (`docs/FINDINGS.md:259-261`). A 31-row PAR plus coarse NIR table is a derived
   quantity with its producer committed (`tools/extract_ice_k.py`); the producer's
   inputs are gitignored and absent (`.gitignore:9-10`), so the derived table is the
   only thing that can run in CI. M1a's first item, P0.
2. **First load: alive at 1.10 AU.** The first gesture is then a death the visitor
   caused; at 1 AU the wall is already water and the page opens on a corpse.
3. **`p` and `t`: player-set, with `p*` and `t_min` shown.** The only way BURST and
   BOIL are reachable at all: on the auto path they hold by construction (§4), so Q4
   registers on FREEZE, STARVE and OPAQUE. Manual `p` freezes an auto `t` at `t_min(p*)`.
4. **Round-2 audit, where the bands come from: the spec, not the code.** Bands are
   hand-written in §6 from committed rows and copied into `prereg.yaml`; M1a's output is
   tested against them.

## 11. The story after Q4

Story order set by the user on 2026-09-12. §§1-10 are Act One. Chapters 2 and 3 add one
registered question each and chapter 6 adds two, phrased so a gate can check them, and
reuse §4; chapters 1 and 4, and chapter 5's `m_seed` question, are display-only until
their anchors are grounded. Sizes: S < 1 week, M 1-3 weeks, L > 3 weeks. "UNGROUNDED, needs a
source" means the number stays off the page until grounded.

### Chapter 1. The scale ladder: who needs a vessel at all (display, not registered)

**Seen.** The Q4 sphere shrinks on a log ladder from 100 km to 10 µm with a seed, a
lichen thallus, a tardigrade and a plant cell drawn beside it at true scale. At the
small end the wall band vanishes because the organism's own wall holds the pressure; at
the large end it is metres of ice. Dyson's original drawing (foliage outside in vacuum,
habitat inside) tops the ladder with each leaf redrawn as a sealed vessel at leaf scale,
the only reading under which it holds air.

**Status.** Display only, no registered question: every anchor it needs (cell turgor
0.5-1 MPa, cell-wall strength, cuticle thickness, vacuum survival of seeds, lichens and
tardigrades) is UNGROUNDED, needs a source, and a question with zero grounded anchors
cannot be registered. The ladder draws the hoop equation (§3; q3 spec `:133`) at every
rung with own-wall numbers labelled DECLARED. If chapter 4's EXPOSE papers ground the
lichen rung, "at what `R_free` does `t_min` first exceed the wall a cell supplies for
free" can be registered then. Size S.

### Chapter 2. Mirror leaves and stacked shells (Act 2: moving the window outward)

**Seen.** A petal mirror of player-set area unfolds around the sphere and the interior
brightens; a shell count adds concentric ice rings and the interior warms while going
bluer and darker with each ring. Dragging `r` out to 2 AU and 5 AU, the visitor watches
which combination keeps the interior liquid and the disc green, and at what ring count
the disc greys because no PAR survives the stack.

**Question.** For `r` in {2, 5} AU and `sigma` in {0.7, 1.5, 3.1} MPa, what is the
smallest (shell count `N`, mirror ratio `M`) pair under which all five inequalities of
§4 hold at `p = p*`, and what `N_dark(r)` first drives `f_photon^N` below `f_floor`
with `M` at its mass-feasible maximum?

**Inputs and anchors.** Mirror ratio `M` [1, log to 10^4]; shell count `N` [0 to 5];
mirror areal mass (declared) charged into the hoop load of the wall carrying it.
Incident PAR scales `1/r²` (`sim/physiology.py:29`); the compensation irradiance does
not move with `r` (`sim/organism.py:126-135` has no distance term), so 5 AU needs 25x
the mirror and 40 AU 1,600x to restore the 1 AU flux; `I_wall = M · (1 - albedo) ·
irradiance(r) · f_photon(t)` extends §3's closure. Shells: `bio_grounding` §14
`:1149-1158` puts one real shell at 21.8 to 26.5 °C against the uncontained 5.16 °C,
+16.6 to +21.3 K per shell at measured `tau`; the +31 to +36 K there (`:1158`) is the
GAP between a real shell and the halved-`area_ratio` identity, not a shell's warming.
`:1196-1200` shows the stack saturating (5.16, 21.8, 25.7, 26.7 °C at `tau = 0.26`),
each shell passing a quarter of what reaches it; PAR loss goes as `f_photon(t)^N`.
Mirror areal mass and reflectance: UNGROUNDED, needs a source. Both sliders feed the
same inequalities; no new failure word is authored. Size M.

**Variant, comet as vessel.** Grow inside the comet: crust is the wall, thickness free,
transparency the only constraint, the trunk a light pipe from a surface window. BURST
drops out, OPAQUE is the whole game. Light-pipe loss per metre: UNGROUNDED, needs a source.

**Variant, how many trees make a Dyson sphere.** Leaf area to intercept 1% of solar
output, as a count of Q4 vessels at the current `R`. A flourish from TSI
(`sim/physiology.py:14`) and `4·pi·r²`; no registered question.

### Chapter 3. The orbit is the calendar

**Seen.** The `r` slider becomes an ellipse with perihelion `q`, aphelion `Q` and period
drawn to scale, and a clock runs. The sphere thaws through perihelion, frosts and greys
through aphelion, and a carbon integral fills or drains beside it. The tree lives if the
integral is positive after one lap, even though the instant readout says FREEZE for most
of the year.

**Question.** For the Q4 default vessel, which `(q, Q)` pairs on a registered grid give
`∫ net_carbon_contained(r(t), t_wall) dt >= 0` over one period, with respiration times a
dormancy fraction `d = 0.10` whenever `T_int < 273.15 K`, and does the closing `Q`
exceed the fixed-`r` `r_close` band of §6 by more than `d` accounts for?

**Inputs and anchors.** `q`, `Q` (AU); the dormancy fraction `d`, FROZEN at 0.10 for
the registration, DECLARED on the page, 0.05 and 0.20 reported as sensitivity arms; a
tick, the first in the repo. `r(t)` from Kepler's equation, stateless; the integrand is
§4 STARVE per tick with `1/r²` inside `irradiance` (`sim/physiology.py:29`). Dormancy
through aphelion (resurrection plants, seed dormancy) is the biology; the dormant rate
is UNGROUNDED, needs a source, which is why `d` is frozen and disclosed rather than
fitted. §7 defers growth-over-time and orbit mechanics here.

**Variant, albedo as an evolvable trait.** §17 `:1497-1502` has the shell melting at
albedo 0 and freezing at 0.0721 at 1 AU. Let albedo respond to `T_shell` over the orbit
(frost forms, frost sublimes) so the sphere self-regulates or runs away; the same
`(1 - albedo)` factor scales `I_wall` per §3. Size L.

### Chapter 4. The seed as the spaceship (Act 3; display, not registered)

**Seen.** A pod on the outer wall dehisces and seeds drift off the comet at walking
pace (escape velocity from a ~1e12 kg body is ~1 m/s). A transit bar counts centuries to
the next comet at Oort-cloud spacing while a DNA-damage meter climbs and an ice-coat
slider slows it. Arrival draws germination or a dead seed with the dose printed.

**Status.** Display only. The one measured quantity is EXPOSE-E's binary endpoint (seeds
germinated after 558 days outside the ISS); dose attenuation in ice and the
damage-to-viability curve are UNGROUNDED, so a damage-rate question cannot be registered.
**Candidate question, once both are grounded:** at a transit time of centuries, what
ice-coat thickness `d_coat` holds accumulated dose to at most the EXPOSE-E exposure the
seeds survived, and does any `d_coat` under 1 m do it?

**Inputs and anchors.** Transit time; ice-coat thickness `d_coat`; dose rate behind
`d_coat` (the dormancy-vs-radiation budget). Arabidopsis and tobacco seeds germinated
after 558 days outside the ISS on EXPOSE-E: Tepfer and Leach 2017, Astrobiology,
10.1089/ast.2015.1457; Tepfer, Zalar and Leach 2012, 10.1089/ast.2011.0744; both: verify
via CrossRef before citing in-repo. Escape velocity ~1 m/s from `sqrt(2GM/R)` at ~1e12
kg, comet mass UNGROUNDED, needs a source; so are dose attenuation in ice and the
damage-to-viability curve. Size M.

### Chapter 5. Seed bootstrapping, and what the seed carries

**Seen.** A seed lands on bare ice with its carbon reserve drawn as a shrinking bar. It
absorbs sunlight, melts a pocket (334 kJ/kg latent heat) and starts the first wall; the
bar drains as it builds. Either the vessel closes first and the Q4 page appears, or the
bar hits zero and the seedling frosts over.

**Question (display-only until seed reserve carbon and startup respiration are
grounded).** Is there a seed reserve mass `m_seed` for which the startup budget closes
(absorbed sunlight over the startup time melts the water the first `t_min` wall needs
before the reserve is spent), and what is the smallest such `m_seed` at 1.10 AU?

**Inputs and anchors.** Seed reserve mass; seed absorptance; startup time. Latent heat
of fusion 334 kJ/kg; `irradiance(r)` (`sim/physiology.py:22-30`); `t_min` and `p*` from
§3. Seed reserve carbon per mass and startup respiration: UNGROUNDED, needs a source.
Alongside, a grounding table (not a mechanic) of carried traits: UV screens (Tepfer's
UV-screen mutants did WORSE than wild type; same two papers, verify via CrossRef), DNA
repair, desiccation proteins, anti-freeze coat, each row source-or-UNGROUNDED. Size M.

### Chapter 6. Element budget and air per person

**Seen.** Two panels. A mass slider grows the tree against a ~1e12 kg comet and one
element bar empties first with its name printed. A head count at 1 AU and 5 AU shows the
leaf area each person needs behind the wall's `f_photon`, Dyson's stated purpose.

**Questions.** (a) With the comet's element fractions, which element runs out first and
at what tree mass `m_limit`, as a fraction of comet mass? (b) What leaf area per human
`A_air(r, t)` balances one person's O2 demand at 1 AU and 5 AU behind `f_photon(t)`, and
by what factor does the wall raise it?

**Non-goal.** Gravitropism: no panel, no mechanic and no registered question until NASA
GeneLab measurements set the architecture (`docs/ROADMAP.md:110-112`).
**Inputs and anchors.** Tree mass; head count; element table. Spine item 1: comet
organic-C-rich ~50% by mass, Ca-depleted, P present, K unmeasured
(`docs/ROADMAP.md:95-98`; `docs/prior_art_2026-09-01.md` §3). K, human O2 demand, tissue
stoichiometry and the ~1e12 kg comet mass: all UNGROUNDED, needs a source. Size M.

### Cards inside Q4's page

Two static cards under the readout panel, no new inputs.
- **Shield.** The `p*` wall at 1 AU and 10 km is 5.6 to 18.6 m of ice (`§13:1054-1058`);
  about 1 m of water stops most solar protons, so shielding may come free with the
  wall. The 1 m figure is UNGROUNDED, needs a source; the thickness is §3's `t_min`.
- **Treeship falsified.** Absorbed photon pressure at 1 AU is TSI/c = 1360.8 / 2.998e8
  = 4.54 µN/m² (`sim/physiology.py:14`). On 1 km² of leaf, 4.5 N; on a ~1e12 kg comet,
  4.5e-12 m/s², nine orders below the Sun's 5.9e-3 m/s² pull at 1 AU, and a year of it
  is 1.4e-4 m/s against a ~1 m/s escape velocity. It does not fly. The only propulsion
  a plant has is shading one side of its comet to bias outgassing, and that is
  speculative. Comet mass UNGROUNDED, needs a source.

## 12. The speculative tier: a gene deck and a material table

User ruling 2026-09-12: the story may step into science fiction, on one condition that
keeps the model honest. **A card moves an input. A card never moves an inequality.**
The five failures of §4 stay the judge; the visitor chooses what the organism is made of.

**Seen.** Beside the design inputs, a deck. Each card names an organism, the trait,
the input it moves, its cost, and an anchor badge: MEASURED (a number with a source in
this repo), DEMONSTRATED (done in a lab, source outside the repo, verified before it is
cited), or DECLARED (fantasy, labelled as such). Playing a card changes a slider's value
or range; the picture and the five lines respond as to any other input. A DECLARED card
cannot be played in a registered run; the sweep refuses it, the page allows it.

**The rule, as tests.** `sim/vessel.py` and `classify_failure` do not import the deck.
The deck is a data table (`web/deck.json`, mirrored in `sim/deck.py` for parity) whose
every row is `{organism, trait, input, delta_or_range, cost, anchor, source}`; a test
asserts every row names an input that exists and no row names an inequality; a second
asserts every MEASURED row's source resolves to a file:line in this repo. **Third rule:
after any card is played, each registered binding is still FIRST violated at a reachable
auto-path state inside its registered box** (FREEZE: `R` 10 km, `r` in [1.20, 1.27] AU,
every sigma; OPAQUE: `r` 1.10 AU, sigma 0.7 MPa, `R` in [60, 300] km; §6), and STARVE
still takes both HOLD and VIOLATED on the page grid (no auto-path state in either box
violates STARVE, so it cannot be held to first violation). BURST and BOIL hold by
construction on the auto path (§4) and stay manual-gesture failures; no card may remove
their manual door. A VIOLATED cell somewhere on the page grid (r to 100 AU, t to 1 km)
does not satisfy the rule, because an extreme slider always supplies one. The per-card
test plays each card, runs the auto path across each box, and asserts the named line is
the first to flip inside it. **Worked failing example:** antifreeze at `dT_sc = 5 K`
moves the R = 10 km FREEZE edge to 1.2696 / 1.2958 / 1.3203 AU for sigma 0.7 / 1.5 / 3.1
(edge wall at `p_sat(-5 °C)` = 421.8 Pa); two of three leave the box, prediction 1's
binding changes, and the card FAILS, even though FREEZE still violates on the page grid
(the `tau = 1` edge moves only to 1.523 AU). Zero respiration fails the STARVE clause,
since `respiration(0, T) = 0` (`sim/physiology.py:54`).

### Material table (wall rows)

Each row is a `(sigma, k(lambda) or opacity, density, anchor)` tuple the wall-material
input can take. Ice is the only MEASURED row (§3); every other number below is
UNGROUNDED, needs a source, until the CrossRef chain has run. **Every `sigma` or `k` row
must keep OPAQUE first-violated inside prediction 2's box and BURST reachable by the
manual `p` gesture** (the third rule): `k` is floored where the auto-path
`f_photon(t_min)` still crosses `f_floor` at an `R` in [60, 300] km at 1.10 AU; `sigma`
is capped where that crossing still occurs before any other line flips. A row that cannot
satisfy both ships DECLARED with its range clipped and the clip printed.

| material          | organism it is stolen from | what it does to the lines                                                                                                                                                           | anchor       |
| ----------------- | -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| water ice         | the comet                  | the §3 baseline                                                                                                                                                                     | MEASURED     |
| nacre             | mollusc shell              | ~100 MPa tensile, ~30x ice, so BURST retreats (clipped so it can still fire); opaque, so OPAQUE fires unless paired with an ice window or the comet-as-vessel light pipe (§11 ch.2) | DEMONSTRATED |
| biogenic silica   | diatom frustule            | grown glass, clear in the visible and strong; the one row that can open the window in both directions at once, and so the row the third rule watches closest                        | DEMONSTRATED |
| spider silk       | spidroin in tobacco/potato | ~1 GPa tensile; not a wall, a tether: in zero g structure is tension, so mirrors and leaves hang on silk (§11 ch.2)                                                                 | DEMONSTRATED |
| magnetite         | chiton radula              | hardest biomaterial; armour, not a vessel; a row for micrometeorite pitting once that is a failure mode                                                                             | DEMONSTRATED |
| nickel-laden wood | hyperaccumulator trees     | metal in tissue is real (sap ~25% Ni in one species); metal as a structural wall is not, and the card says so                                                                       | DECLARED     |

### Gene cards (organism rows)

Ordered from most to least grounded. Each moves one named input, never a literal in
`sim/vessel.py`: the antifreeze card leaves 273.15 alone and moves a supercooling offset
input `dT_sc` [0 K default, declared, disclosed] that FREEZE reads as `T_int < 273.15 -
dT_sc`, capped at 0.8 K: the sigma 3.1 MPa edge reaches the box top of 1.27 AU at
`dT_sc` = 0.819 K (0.7 MPa: 5.04 K; 1.5 MPa: 2.86 K), so any larger value fails the third
rule. Respiration cards move `r_d` within a floor above zero (third rule).

| card                        | stolen from                   | input it moves                                                                                                                         | anchor       |
| --------------------------- | ----------------------------- | -------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| antifreeze proteins         | fish, insects                 | `dT_sc`, up to the 0.8 K cap; real proteins give a few K, so the card is clipped and the clip printed                                  | DEMONSTRATED |
| reduced dark respiration    | none named                    | `r_d`, down to a floor above zero                                                                                                      | DECLARED     |
| Dsup + desiccation proteins | tardigrade                    | the dormancy-vs-radiation budget (§11 ch.4, ch.5)                                                                                      | DEMONSTRATED |
| DNA repair                  | Deinococcus radiodurans       | the same budget, the repair term                                                                                                       | DEMONSTRATED |
| CAM + desert cuticle        | cacti, agaves                 | leaf-scale water loss in vacuum (§11 ch.1)                                                                                             | DEMONSTRATED |
| UV screens                  | Arabidopsis flavonoid mutants | the seed's UV term; note the EXPOSE-E screen mutants did WORSE than wild type                                                          | DEMONSTRATED |
| chemosynthetic symbionts    | tube-worm bacteria            | a dark-side carbon source: O2 banked at perihelion, burned with comet organics at aphelion (§11 ch.3); a redox budget with real inputs | DECLARED     |
| radiotrophic melanin        | Chernobyl fungi               | a cosmic-ray energy term; the literature claim is contested and the card says so                                                       | DECLARED     |

**One thing plants already do that reads as fiction.** Xylem pulls water at about
-2 MPa, below absolute zero pressure; a tree already operates past vacuum. This goes on
the landing page as the reason a plant, not an animal, is the organism. UNGROUNDED,
needs a source, before it ships.

**Non-goals for the tier.** No genome, no evolution of cards, no cost currency beyond the
carbon budget the model has; a "cost" is carbon or mass charged to the existing inequalities.

**Milestone.** The deck ships after M2 and before M3, as M2b (S): the table, the three
tests, and the badge, with only the antifreeze (`dT_sc`) and reduced-respiration (`r_d`)
rows live, since every other row moves an input that does not exist until its chapter
(§11 ch.1, 3, 4, 5); those rows ship with their chapters and the row test runs against
the inputs present at each ship. Bioluminescence moved no input and is dropped. No card may be MEASURED until its number is in `bio_grounding`.
