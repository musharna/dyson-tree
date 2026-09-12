# Northstar design: the vessel, and watching it fail

> Drafted 2026-09-12 against `release/1.0.1-rc` (HEAD `7ed4414`). Every claim about
> current code carries a `file:line`. Nothing here edits a frozen pre-registration.
> Supersedes the modelling direction of `2026-09-04-q3-pressure-vessel-design.md`
> (whose four correction banners are the input to §3 below); does not supersede
> `docs/ROADMAP.md`, which must be bannered to point here in the same commit that
> starts M1. §§1-10 are Act One (Q4, the vessel, watching it fail); §11 is the story
> order after Q4 as the user set it on 2026-09-12, and §7 defers to it by chapter.

## 1. Northstar

A visitor sees a cross-section of a sealed, transparent sphere with a green organism
inside it, at a distance from the Sun they can drag, and the sphere is either alive or
it is bursting, freezing, starving, or going dark under its own wall. They change one
input (radius, wall, pressure, distance, organism) and the picture changes state,
with the number that killed it printed beside the wound. Nothing on the page is
authored: every failure is an inequality between two quantities the repository already
grounds, and the visitor can read both sides.

## 2. What exists today that this reuses

What is true now: the live page is an uncontained organism at a fixed tissue
temperature (`web/index.html:128-132`), with a class dropdown, a `k` dropdown and a
log-spaced distance slider (`web/index.html:77-91`, `web/app.js:62-89`), driving one
net-carbon curve (`web/app.js:114-284`). The page itself says "No pressure vessel" and
"No spectral wall" (`web/index.html:130-135`). The model has no tree: `sim/organism.py`
is a frozen dataclass of 11 scalars (`sim/organism.py:27-40`) with two presets
(`sim/organism.py:163-173`).

Reused as-is, no edits:

- **Light in.** `irradiance(r_au)` is `TSI / r² × PAR_FRACTION × PHOTONS_PER_J`
  (`sim/physiology.py:22-30`), TSI 1360.8 (`:14`), PAR fraction 0.3879 measured AM0
  (`:16`). `gross_assimilation(i, a_max, k)` (`:33-43`), `respiration(r_d, t)` with
  Q10 (`:46-54`).
- **Thermal core.** `equilibrium_temperature(r_au, area_ratio, emissivity, albedo)`
  (`sim/thermal.py:20-46`; `area_ratio` is pure geometry, `:28-30`).
  `temperature_response_gaussian(t, t_opt, omega)` (`:65-86`), the June 2004 form.
- **Organism.** `Organism` fields incl. `t_opt` "declared assumption, not grounded"
  (`sim/organism.py:37`), `omega` "DECLARED ASSUMPTION" (`:40`), `albedo`/`emissivity`
  declared (`:38-39`). `compensation_irradiance` (`:126-135`). `net_carbon`,
  `net_carbon_at_equilibrium`, `net_carbon_adapted` stay untouched (`:80-123`); each
  guards a committed record.
- **The r slider.** `R_MIN 0.5`, `R_MAX 100` AU (`web/app.js:29-30`); quantised to 3 dp
  so "the distance shown is the distance used" (`web/app.js:66-85`). Kept verbatim.
- **Parity.** `web/model.js` is a classic script exporting `DysonModel` for the browser
  and `module.exports` for node (`web/model.js:9-13, 267-271`); each function names its
  `sim/` lines (`:22, :32, :59`). `tests/test_parity_js.py` fails rather than skips
  without node (`:33-38`), pins fixtures to the md5 of each `sim/*.py`
  (`:82-99`), and runs 9 tests incl. crossovers against the committed CSV (`:155`).
  Fixtures come only from `sim/` public functions (`tools/make_fixtures.py:2-7`).
- **Site build and rail.** `tools/build_site.sh` copies an allowlist of three files
  (`:16-19`) and refuses remote assets (`:36-40`). `pages.yml` pins python 3.13.2
  (`:36`), runs pytest incl. parity before upload (`:43-45`), then `build_site.sh`
  (`:47`). `pyproject.toml:24-25` discovers `sim*` and `experiments*` only, so a new
  `sim/vessel.py` and `experiments/q4_vessel/` are packaged without edits; `web/` is
  not a package and stays that way. CSV `git_sha` must be a reachable ancestor of HEAD
  (`tests/test_derived_csvs.py:198-221`): regenerate CSVs and fixtures last, never
  amend after. That guard needs the ancestors present in CI: `origin/master` (632d8ba,
  one commit past this branch) sets `fetch-depth: 0` on the checkout (`pages.yml:34`
  there); this branch does not yet have it. M1 starts from `origin/master`.
- **Vessel arithmetic already computed in `tools/`, not in `sim/`:** Buck saturation
  pressure (`tools/check_greenhouse_transparency.py:99-100`), solar-weighted wall
  transmission `tau_sw(t)` (`:94-96`), the damped fixed point `p -> t -> tau -> T ->
p_sat` (`:120-130`), and the PAR photon fraction behind a wall
  (`tools/size_par_filter.py:177-195`). M1 moves these into `sim/` with tests; the
  tools become positive controls, not sources.

## 3. The vessel model

What would be true: one sphere, one wall, one organism inside, four inequalities. The
arithmetic below has no new physics; every symbol is already grounded in this repo.

**Geometry and load.** Thin-wall sphere of internal radius `R` (m), wall thickness `t`
(m), internal pressure `p` (Pa) against ~0 ambient. Hoop stress
`sigma_hoop = p·R / (2·t)` (q3 spec `:133`; `docs/prior_art_2026-09-01.md:58`).
The wall that just holds `p` is `t_min = p·R / (2·sigma)`.

**Wall material.** The wall must be clear: pigmented tissue at 0.625 m passes
`e^-3952` (q3 spec `:168-171`). The only clear material with both a grounded strength
and grounded optics is pure water ice: tensile `sigma` **0.7 to 3.1 MPa** (Petrovic
2003 via Hirata 2022, `bio_grounding` §10 `:613-615`, grounded at one remove) and
absorption `k(lambda) = 4·pi·m_im/lambda` from Warren & Brandt 2008 (`§9:519-537`).
The wood MOR **80 MPa median** (§7 `:456-462`) is NOT a wall input: pairing wood
strength with ice optics is the ~53x error §10 records (`:596-608`), and the rule
"a pair of grounded inputs must describe the same object" (`:689-690`) is a test in M1,
not a comment. Wood remains available only as a labelled counterfactual with its own
`k`, which is UNGROUNDED, needs a source, and so is not on the page.

**Spectral wall, not a scalar.** `k` spans 0.00074 /m at 400 nm to 0.52061 /m at
700 nm, a factor of 701 (`§9:532-540`). Transmission through thickness `t` is
`tau(lambda, t) = exp(-k(lambda)·t)`. Two integrals of it are the wall:

- `f_photon(t) = ∫₄₀₀⁷⁰⁰ tau(λ,t)·n_ph(λ) dλ / ∫₄₀₀⁷⁰⁰ n_ph(λ) dλ`, the fraction of
  AM0 PAR photons that arrive (`tools/size_par_filter.py:181-186`). This is the
  photon count, not a chlorophyll-weighted rate (`§12:959-963`); it is an upper bound
  on what the organism can use, stated as such on the page.
- `tau_sw(t) = ∫₂₈₀⁴⁰⁰⁰ tau(λ,t)·E(λ) dλ / ∫ E dλ`, solar-energy-weighted
  (`check_greenhouse_transparency.py:94-96`). NIR carries 53% of TSI and ice absorbs
  it (`§13:1021-1025`), so a pressure wall passes 16 to 23% of solar energy.

**The coupling that closes S2.** Today `irradiance(r)` feeds an unfiltered scalar to an
organism the vessel finding requires to sit behind a blue-pass wall
(`docs/FINDINGS.md:428-433`). The closure is one line:
`I_wall(r, t) = irradiance(r) · f_photon(t)`, fed to `gross_assimilation` in a new
`Organism.net_carbon_contained` placed BESIDE the three existing paths, which do not
change. `1/r²` stays inside `irradiance` (`sim/physiology.py:29`); the wall factor is
distance-independent by construction, which is what makes the two separable on the
page.

**Contained temperature.** `T_int = (1 + tau_sw(t))^0.25 · T_eq(r, 4, eps, albedo)`
(`§13:1040-1046`; the `(N+1)^0.25` form is its `tau = 1` case). The shell sits at
`T_shell = T_eq` exactly, independent of `tau` (`§17:1459-1460`).

**Vapour pressure at the contained temperature.** Buck: `p_sat(T_C) = 611.21 ·
exp((18.678 - T_C/234.5)·(T_C/(257.14 + T_C)))`
(`tools/check_greenhouse_transparency.py:99-100`); gate points 611.657 Pa at 273.16 K
and 882 Pa at 5.16 °C (q3 spec `:217-220`).

**Self-consistent pressure.** `p* = p_sat(T_int(t(p*)))`, solved by the damped
iteration at `:120-130`. At 1 AU, R = 10 km: 3.453 / 3.002 / 2.607 kPa for sigma 3.1 /
1.5 / 0.7 MPa (`§13:1054-1058`). The page shows `p*` beside whatever `p` the player
sets.

**The roadmap's closed form, and why it is a control here.**
`R_max = 2·sigma·|ln tau_min| / (k·p)` (`docs/ROADMAP.md:140`, q3 spec `:139`):
`sigma` tensile strength (Pa), `p` internal pressure (Pa), `k` a single absorption
coefficient (1/m), `tau_min` the smallest acceptable transmission. It follows from
`t = pR/(2σ)` and `tau = e^{-kt}`. Its two defects are named in the repo: `k` is not a
scalar (`§9:539`) and `tau_min` is author-declared, "NOT GROUNDED" (q3 spec `:166`).
In this design both disappear: `k` becomes the integral above, and `tau_min` becomes
`I_c / irradiance(r)` with `I_c` the organism's own compensation irradiance
(`sim/organism.py:126-135`), so the threshold is the organism's, not the author's.
The closed form survives as a unit-test control: at monochromatic `k = 0.38623` and
`tau_min = 0.01` the spectral code must reproduce 21.41 / 11.91 / 6.40 km
(`§13:1073-1077`).

**Declared assumptions, four, all exposed as inputs:** `t_opt` and `omega` (organism,
`sim/organism.py:37,40`); `albedo` and `emissivity` (vessel, `:38-39`). Albedo is not
cosmetic: at 1 AU the shell melts at albedo 0 and freezes at 0.0721 (`§17:1501-1502`).
If `albedo > 0` the same factor must scale `I_wall`, since Beer-Lambert as used models
absorption only and is consistent with `albedo = 0` (`§17:1505-1509`). Dust: the
magnitude is ungroundable but the direction is pinned downward on `tau`, `T_int`, `p*`
(`§15:1287-1297`); the page carries a `dust floor` toggle {none, 0.0087, 0.0548 /m}
labelled DECLARED, and Q4 registers on `none` with the others as sensitivity arms.

## 4. The four failure modes, as arithmetic

Each is an inequality evaluated from the inputs. The page prints both sides. There is
no `if failure_type == ...` authored anywhere; `classify_failure` returns the set of
violated inequalities and the first one in load order names the picture.

**BURST.** `p·R/(2t) > sigma(T_shell)`. `sigma` is Petrovic's 0.7 to 3.1 MPa while the
shell is solid, and 0 when `T_shell = T_eq(r) > 273.15 K`, because the wall is then
water, not ice (`§17:1465-1471`: at 1 AU, albedo 0, the coldest part of the wall is
5.16 °C). So BURST has two doors and one inequality: too much pressure for the wall you
built, or a distance so close the wall is not a solid. The inner edge of the habitable
annulus, 1.0381 AU at albedo 0 (`§17:1480-1486`), falls out of `sigma(T_shell) = 0`,
not from a stored number.

**FREEZE.** Liquid water requires `273.15 K < T_int` and `p >= p_sat(T_int)`. The
first fails outward: `T_int = (1+tau_sw)^0.25 · T_eq(r)` drops below melting at
1.14 to 1.20 AU depending on `tau_sw` (`§17:1480-1484`). The second fails when the
player holds less than `p*`: the water boils off at the contained temperature. Both
are the same readout, "no liquid phase", with the violated side printed. FREEZE is what
promoted the vessel to a precondition (`docs/thermal_premise_retired_2026-09-03.md:46-60`).

**STARVE.** `net_carbon_contained(r, t) < 0`, where gross is
`gross_assimilation(I_wall, a_max, k) · temperature_response_gaussian(T_int, t_opt,
omega)` and respiration is `respiration(r_d, T_int) / leaf_mass_ratio`. This is the
Q2b path (`sim/organism.py:102-123`) with `T_eq` replaced by `T_int` and `irradiance`
replaced by `I_wall`. Because `f_photon` is a photon count that over-credits the
surviving blue band (`§12:959-963`), STARVE fires later than it should; the page says
so under the readout.

**CRUSH / OPAQUE.** The wall that holds `p` at radius `R` is `t_min = pR/(2σ)`, rising
linearly in `R`; `f_photon(t_min)` falls with it. At the radius where
`irradiance(r)·f_photon(t_min(R)) < I_c(T_int)` the vessel is too thick to feed what
it contains, and no thinner wall holds. This is the bind the roadmap sweeps at 0.93 to
4.10 km against an assumed 10 km (`docs/ROADMAP.md:182`; `§11:750`), computed with a
red-band scalar `k` and the since-withdrawn 18 kPa. Nobody has run it with the spectral
wall at `p*`; §12's table (`:928-938`) says the photon count at 10 km is 24 to 44%, so
the spectral answer is expected to sit well above the red-band one. That expectation
is what Q4 registers, in §6.

## 5. The player loop, one screen

What the visitor sees: left, a cross-section; right, six inputs and one verdict panel.
The existing curve and its readouts move below, unchanged, as "the uncontained model".

**Inputs** (all sliders, values printed; defaults in brackets): vessel radius `R`
[1 km, log 10 m to 100 km]; wall thickness `t` [auto = `t_min`, or manual]; internal
pressure `p` [auto = `p*`, or manual]; distance `r` [1.10 AU, the existing slider];
organism class [algal]; wall material [ice, the only grounded option]. Under a
"declared assumptions" disclosure: `albedo` [0.0], `emissivity` [1.0], `t_opt`
[298.15 K], `omega` [20 K], dust floor [none]. Auto modes are the self-consistent
design; manual is how the visitor over- or under-builds.

**The picture.** An SVG cross-section: outer circle radius ∝ `R + t`, inner circle
∝ `R`, wall band drawn at its true thickness ratio `t/R` (clamped to a visible
minimum with the clamp labelled). Interior fill hue from the transmitted PAR spectrum
(blue-shift as `t` grows: `tau(λ,t)` sampled at 31 PAR rows), brightness from
`f_photon`. Organism: a green disc whose saturation is `net_carbon_contained / a_max`,
grey at zero. State overlays, each keyed to its inequality: BURST draws the wall
fractured with `p·R/2t` vs `sigma` printed at the break; FREEZE frosts the interior
with `T_int` vs 273.15 K; STARVE fades the disc with `net` vs 0; OPAQUE darkens the
interior with `I_wall` vs `I_c`. No text-transform anywhere (`web/index.html:29-33`).

**The readout panel.** One line per inequality, both sides as numbers with units, and
the word HOLDS or VIOLATED. Below: `p*` and `t_min` for the current design, and the
distance window `[r_melt, r_freeze]` for the current wall.

**The first 60 seconds.** Load: alive, at 1.10 AU, 1 km, ice, auto wall and pressure;
the panel reads four HOLDS. Drag `r` inward: at 1.038 AU the wall line turns to water
and BURST fires with `sigma = 0`. Drag outward: at ~1.18 AU the interior frosts. Drag
`R` up at 1.10 AU: the wall band thickens, the interior goes blue then dark, the disc
greys, STARVE then OPAQUE. Push `p` above `p*`: BURST. The visitor has now seen all
four deaths from four gestures and every one had a number on it.

## 6. Pre-registration Q4

**Question.** At self-consistent pressure `p*` and a spectral ice wall, is there ANY
radius `R` at which the vessel is simultaneously strong enough to hold liquid water and
clear enough to pass compensation-point PAR, and at what distance `r` does that window
close?

**Quantities.** For each `r` on the registered grid and each `sigma` in {0.7, 1.5,
3.1} MPa, `R_window(r)` = the largest `R` at which all four inequalities of §4 hold with
`p = p*(r, R)` and `t = t_min`. `r_close` = the largest `r` with `R_window > 0`;
`binding(r)` = the inequality that closes it, as Q2b's `classify_limit` names its
binding limit.

**Registered predictions, in quantities the gates can check** (`docs/ROADMAP.md:482-500`).
Gate A pins `T_eq` (q3 spec `:211-212`), so a band in `r_close` is a band Gate A
reaches directly: the outer edge is `T_int = 273.15 K`, pressure-free. The provisional
band is the envelope of the repo's own annulus table, 1.1446 to 1.2030 AU at albedo 0
(`§17:1480-1484`), widened by the dust arms downward and by no author choice upward:
**`r_close ∈ [1.10, 1.21] AU`, `binding(r_close) = FREEZE`, for algal at albedo 0.**
Second prediction, in `R`: **`R_window(1.10 AU) >= 6 km at sigma = 0.7 MPa`**, i.e.
the spectral wall does not bind below the red-band 6.40 km (`§13:1077`); this one is
reached by Gate B (optics) and is the sensitive one. The registered numbers are
COMPUTED by M1's code and written into `prereg.yaml` before the sweep, per Q1's rule
(q3 spec `:189-190`); the figures above are provisional readings of existing tables and
are not the registration.

**What falsifies.** `r_close` outside the band; `binding` at `r_close` being STARVE or
OPAQUE rather than FREEZE; `R_window(1.10 AU)` below 6 km at any grounded sigma;
or an empty window at every `r`, which would be the headline finding.

**What the gates may constrain.** Gate A: `T_eq(1 AU, sphere) ∈ [275, 282] K`. Gate B:
Beer-Lambert with the extracted `k` reproduces a measured transmission through a
stated thickness of ice: UNGROUNDED, needs a source (q3 spec `:213-216` names the gate
without one). Gate C: Buck at 273.16 K and 5.16 °C. The gates constrain optics and
vapour pressure only; they do not touch `sigma`, `albedo`, `t_opt`, `omega`, which are
swept or declared and disclosed. A gate that fails blocks the sweep and exits 2, as Q2
did (`docs/FINDINGS.md:206-209`).

**Declared, explicit:** `t_opt = 298.15 K`, `omega = 20 K`, `albedo = 0`,
`emissivity = 1`, dust `none`; `R_ORGANISM` is no longer assumed at 10 km, it is swept.

## 7. Non-goals for this arc

- Colony loop (B): needs A's budget trusted first (`docs/ROADMAP.md:113-116`).
- Growth over time: one design, evaluated; a tick would need a mass budget nobody has.
  Stays out until §11 chapter 3 needs a tick to integrate carbon over an orbit.
- Orbit mechanics: DEFERRED to §11 chapter 3, not excluded. In this arc `r` is a
  slider; chapter 3 replaces it with (perihelion, aphelion, period).
- 3D: the cross-section carries every quantity; a third dimension is decoration.
- Elements budget: DEFERRED to §11 chapter 6. Spine item 1 is ungrounded for K
  (`docs/ROADMAP.md:90-93`); in this arc it would enter as a fifth authored constraint.
- Wood or pigmented walls: `k` for wood is UNGROUNDED; the §10 pairing rule forbids it.
- Scattering magnitude: direction pinned only (`§15:1293-1297`); shipped as a toggle.
- Chlorophyll action spectrum: not grounded; inventing one manufactures S2's defect.
- Buckling, creep, conduction, shell stacking: q3 spec `:227-241` keeps them out.

## 8. Milestones

- **M1 (M): the numbers.** `sim/vessel.py` (`wall_thickness`, `hoop_stress`,
  `transmission_spectrum`, `par_photon_fraction`, `solar_transmission`,
  `saturation_pressure`, `contained_temperature`, `self_consistent_pressure`,
  `classify_failure`), `Organism.net_carbon_contained` beside the existing paths, the
  §10 same-object test, the closed-form control, ported to `web/model.js` with new
  fixture cases and parity tests, `experiments/q4_vessel/prereg.yaml` registered.
  Acceptance: on the live page a stranger opens the console and
  `DysonModel.classifyFailure(...)` at the prereg's example inputs returns the set the
  prereg prints; `tests/test_parity_js.py` covers it.
- **M2 (M): the verdict.** The six inputs and the readout panel, no picture.
  Acceptance: at defaults the panel shows four HOLDS; dragging `r` past the registered
  `r_close` flips exactly one line to VIOLATED and it is FREEZE.
- **M3 (L): the picture.** The cross-section, driven only by `model.js` outputs.
  Acceptance: the drawn wall band's pixel thickness divided by the inner radius equals
  `t/R` from the readout to 2 dp, and `smoke_page.py` measures it from the DOM.
- **M4 (M): the run.** `run.py`, `RESULTS.md`, `sweep.csv` with provenance headers,
  FINDINGS §5, the `r_close` band drawn hatched as Q1's is (`web/app.js:118-119`).
  Acceptance: the page shows the hatched prediction beside the measured `r_close`
  labelled HELD or FAILED, and the README's opening paragraph counts four questions.

## 9. Risks: three ways this becomes another parameter plotter

1. **The verdict becomes a label on a curve.** Guard: M2 ships before any plot; the
   verdict panel has no x-axis; `classify_failure` is the only source of the words
   BURST/FREEZE/STARVE/OPAQUE and a test asserts they appear nowhere else in `web/`.
2. **Author-chosen thresholds creep back in** (`tau_min`, a safety factor, a "viable"
   pressure). Guard: `sim/vessel.py` may contain no numeric threshold except 273.15,
   611.657 and sourced material constants; a test greps for literals and every one must
   carry a `# source:` on its line.
3. **The picture corrects the label, not the value** (the 1.0 lesson: a page that read
   1.000 AU and evaluated 0.99987). Guard: every drawn geometry is read back from the
   DOM by `smoke_page.py` against `fixtures.json`, and M3 passes only through an
   independent visual critic, not the author's read.

## 10. Open questions for the user

1. The wall optics need `k(λ)` on the page, and the page must work from `file://` with
   no fetch. The repo's rule is that Warren & Brandt's table is "not redistributed here"
   (`docs/FINDINGS.md:259-261`). Commit a derived 31-row PAR + coarse NIR `k` table under
   `sim/` with its extraction script as provenance? Recommended: yes, it is a derived
   quantity with the producer committed (`tools/extract_ice_k.py`).
2. First load: alive at 1.10 AU (recommended, so the first gesture is a death the
   visitor caused) or at 1 AU, where the wall is already water?
3. `p` and `t`: player-set with `p*` and `t_min` shown (recommended, it is the only way
   BURST is reachable by hand) or always self-consistent?

## 11. The story after Q4

Story order set by the user on 2026-09-12. §§1-10 are Act One. Each chapter adds one
registered question (chapter 6 adds three), phrased so a gate can check it, and reuses
the four inequalities of §4. Sizes: S < 1 week, M 1-3 weeks, L > 3 weeks. "UNGROUNDED,
needs a source" means the number stays off the page until `bio_grounding` carries it.

### Chapter 1. The scale ladder: who needs a vessel at all

**Seen.** The Q4 sphere shrinks on a log ladder from 100 km to 10 µm with a seed, a
lichen thallus, a tardigrade and a plant cell drawn beside it at true scale. At the
small end the wall band vanishes because the organism's own wall holds the pressure; at
the large end it is metres of ice. Dyson's original drawing (foliage outside in vacuum,
habitat inside) tops the ladder with each leaf redrawn as a sealed vessel at leaf scale,
the only reading under which it holds air.

**Question.** At what internal radius `R_free` does `t_min = p·R/(2·sigma)` first exceed
the wall a cell or cuticle supplies for free, for `p` in {0.5, 1} MPa turgor against a
cell wall and `p*` against ice, and does `R_free` fall below the smallest `R` the Q4
page draws?

**Inputs and anchors.** Ladder class {cell, seed, lichen, tardigrade, leaf, Q4 vessel},
each with an "own wall" thickness and strength. The same hoop equation (§3; q3 spec
`:133`) at every rung. Cell turgor 0.5-1 MPa, cell-wall strength, cuticle thickness, and
vacuum survival of seeds, lichens and tardigrades: all UNGROUNDED, needs a source
(chapter 4's EXPOSE papers are the natural anchor). Size S.

**Variant, lichen as the grounded organism class.** Lichen survived 18 months on EXPOSE;
once sourced it is the one rung with a measured, not declared, desiccation tolerance.
UNGROUNDED until sourced.

### Chapter 2. Mirror leaves and stacked shells (Act 2: moving the window outward)

**Seen.** A petal mirror of player-set area unfolds around the sphere and the interior
brightens; a shell count adds concentric ice rings and the interior warms while going
bluer and darker with each ring. Dragging `r` out to 2 AU and 5 AU, the visitor watches
which combination keeps the interior liquid and the disc green, and at what ring count
the disc greys because no PAR survives the stack.

**Question.** For `r` in {2, 5} AU and `sigma` in {0.7, 1.5, 3.1} MPa, what is the
smallest (shell count `N`, mirror ratio `M`) pair under which all four inequalities of
§4 hold at `p = p*`, and what `N_dark(r)` first drives `I_wall` below `I_c` with `M` at
its mass-feasible maximum?

**Inputs and anchors.** Mirror ratio `M` [1, log to 10^4]; shell count `N` [0 to 5];
mirror areal mass (declared) charged into the hoop load of the wall carrying it.
Compensation irradiance scales `1/r²` (`sim/physiology.py:25-29`;
`sim/organism.py:126-135`), so 5 AU needs 25x and 40 AU 1,600x; `I_wall = M ·
irradiance(r) · f_photon(t)` extends §3's closure. Shells: `bio_grounding` §14
`:1150-1158` puts one extra IR-opaque shell at +31 to +36 K at measured `tau`, and
`:1195-1200` shows the stack saturating (5.16, 21.8, 25.7, 26.7 °C at `tau = 0.26`)
since each shell passes a quarter of what reaches it; PAR loss goes as `f_photon(t)^N`.
Mirror areal mass and reflectance: UNGROUNDED, needs a source. Both sliders feed the
same four inequalities; no new failure word is authored. Size M.

**Variant, comet as vessel.** Grow inside the comet: crust is the wall, thickness is free,
transparency the only constraint, the trunk a light pipe from a surface window. BURST
drops out and OPAQUE is the whole game. Light-pipe loss per metre: UNGROUNDED, needs a
source.

**Variant, how many trees make a Dyson sphere.** Leaf area to intercept 1% of solar
output, printed as a count of Q4 vessels at the current `R`. A flourish from TSI
(`sim/physiology.py:14`) and `4·pi·r²`; no registered question.

### Chapter 3. The orbit is the calendar

**Seen.** The `r` slider becomes an ellipse with perihelion `q`, aphelion `Q` and period
drawn to scale, and a clock runs. The sphere thaws through perihelion, frosts and greys
through aphelion, and a carbon integral fills or drains beside it. The tree lives if the
integral is positive after one lap, even though the instant readout says FREEZE for most
of the year.

**Question.** For the Q4 default vessel, which `(q, Q)` pairs on a registered grid give
`∫ net_carbon_contained(r(t), t_wall) dt >= 0` over one period, and does the closing
`Q` exceed the fixed-`r` `r_close` band of §6 by more than the dormancy respiration
fraction accounts for?

**Inputs and anchors.** `q`, `Q` (AU); a dormancy respiration fraction applied when
`T_int < 273.15 K` [declared, disclosed]; a tick, the first in the repo. `r(t)` from
Kepler's equation, stateless; the integrand is §4 STARVE per tick with `1/r²` inside
`irradiance` (`sim/physiology.py:29`). Dormancy through aphelion (resurrection plants,
seed dormancy) is the biology; the dormant respiration rate is UNGROUNDED, needs a
source. §7 defers growth-over-time and orbit mechanics here.

**Variant, albedo as an evolvable trait.** §17 `:1497-1501` has the shell melting at
albedo 0 and freezing at 0.0721 at 1 AU. Instead of declaring it, let albedo respond to
`T_shell` over the orbit (frost forms, frost sublimes) so the sphere self-regulates or
runs away; the same `(1-a)^0.25` factor scales `I_wall` per §3. Size L.

### Chapter 4. The seed as the spaceship (Act 3)

**Seen.** A pod on the outer wall dehisces and seeds drift off the comet at walking
pace, since escape velocity from a ~1e12 kg body is ~1 m/s. A transit bar counts
centuries to the next comet at Oort-cloud spacing while a DNA-damage meter climbs and an
ice-coat slider slows it. Arrival draws germination or a dead seed with the dose printed.

**Question.** At a registered transit time of centuries and the measured vacuum plus
radiation damage rate, what ice-coat thickness `d_coat` holds accumulated DNA damage
below the germination-loss threshold, and does any `d_coat` under 1 m do it?

**Inputs and anchors.** Transit time; ice-coat thickness `d_coat`; dose rate behind
`d_coat` (the dormancy-vs-radiation budget). Arabidopsis and tobacco seeds germinated
after 558 days outside the ISS on EXPOSE-E: Tepfer and Leach 2017, Astrobiology,
10.1089/ast.2015.1457; Tepfer, Zalar and Leach 2012, 10.1089/ast.2011.0744; both: verify
via CrossRef before citing in-repo. Escape velocity ~1 m/s from `sqrt(2GM/R)` at ~1e12
kg, comet mass UNGROUNDED, needs a source. Dose attenuation in ice and the
damage-to-viability curve: UNGROUNDED, needs a source. Size M.

### Chapter 5. Seed bootstrapping, and what the seed carries

**Seen.** A seed lands on bare ice with its carbon reserve drawn as a shrinking bar. It
absorbs sunlight, melts a pocket (334 kJ/kg latent heat) and starts the first wall; the
bar drains as it builds. Either the vessel closes before the bar empties and the Q4 page
appears, or the bar hits zero and the seedling frosts over.

**Question.** Is there a seed reserve mass `m_seed` for which the startup budget closes
(absorbed sunlight over the startup time melts the water the first `t_min` wall needs
before the reserve is spent), and what is the smallest such `m_seed` at 1.10 AU?

**Inputs and anchors.** Seed reserve mass; seed absorptance; startup time. Latent heat
of fusion 334 kJ/kg; `irradiance(r)` (`sim/physiology.py:22-30`); `t_min` and `p*` from
§3. Seed reserve carbon per mass and startup respiration: UNGROUNDED, needs a source.
Alongside, a grounding table (not a mechanic) of carried traits: UV screens (Tepfer's
UV-screen mutants did WORSE than wild type; from the same two papers, verify via
CrossRef), DNA repair, desiccation proteins, anti-freeze coat, each row
source-or-UNGROUNDED. The lichen variant of chapter 1 may sit here instead. Size M.

### Chapter 6. Element budget, air per person, gravitropism

**Seen.** Three panels. A mass slider grows the tree against a ~1e12 kg comet and one
element bar empties first with its name printed. A head count at 1 AU and 5 AU shows the
leaf area each person needs behind the wall's `f_photon`, Dyson's stated purpose. A
gravitropism panel stays greyed: "gated on NASA GeneLab".

**Questions.** (a) With the comet's element fractions, which element runs out first and
at what tree mass `m_limit`, as a fraction of comet mass? (b) What leaf area per human
`A_air(r, t)` balances one person's O2 demand at 1 AU and 5 AU behind `f_photon(t)`, and
by what factor does the wall raise it? (c) No mechanic and no registered question for
gravitropism until GeneLab measurements set the architecture (`docs/ROADMAP.md:110-112`).

**Inputs and anchors.** Tree mass; head count; element table. Spine item 1: comet
organic-C-rich ~50% by mass, Ca-depleted, P present, K unmeasured
(`docs/ROADMAP.md:94-98`; `docs/prior_art_2026-09-01.md` §3); K is UNGROUNDED, needs a
source. Human O2 demand and tissue stoichiometry: UNGROUNDED, needs a source. Comet mass
~1e12 kg: UNGROUNDED, needs a source. Size M.

### Cards inside Q4's page

Two static cards under the readout panel, no new inputs.

- **Shield.** The `p*` wall is already 5.6 to 18.6 m of ice at the swept sigmas; about
  1 m of water stops most solar protons, so shielding may come free with the pressure
  wall. The 1 m figure is UNGROUNDED, needs a source; the thickness is §3's `t_min`.
- **Treeship falsified.** Photon pressure ~9 µN/m² at 1 AU on a km² leaf gives ~9 N; on
  a ~1e12 kg comet that is ~1e-14 m/s². It does not fly, by ~14 orders of magnitude. The
  only propulsion a plant has is shading one side of its comet to bias outgassing, and
  that is speculative. Photon pressure is TSI/c (`sim/physiology.py:14`); comet mass
  UNGROUNDED, needs a source.

## 12. The speculative tier: a gene deck and a material table

User ruling 2026-09-12: the story may step into science fiction, on one condition that
keeps the model honest. **A card moves an input. A card never moves an inequality.**
The four failures of §4 stay the judge; what the visitor chooses is what the organism
is made of and what it stole from whom.

**Seen.** Beside the design inputs, a deck. Each card names an organism, the trait,
the input it moves, its cost, and a coloured anchor badge: MEASURED (a number with a
source in this repo), DEMONSTRATED (done in a lab, source outside the repo, verified
before it is cited), or DECLARED (fantasy, labelled as such on the card). Playing a
card changes a slider's value or range; the picture and the four lines respond as they
would to any other input. A DECLARED card cannot be played in a registered run; the
sweep refuses it, the page allows it.

**The rule, as a test.** `sim/vessel.py` and `classify_failure` do not import the deck.
The deck is a data table (`web/deck.json`, mirrored in `sim/deck.py` for parity) whose
every row is `{organism, trait, input, delta_or_range, cost, anchor, source}`; a test
asserts every row names an input that exists and no row names an inequality, and a
second test asserts every MEASURED row's source resolves to a file:line in this repo.

### Material table (wall rows)

Each row is a `(sigma, k(lambda) or opacity, density, anchor)` tuple the wall-material
input can take. Ice is the only MEASURED row today (§3). The rest are DEMONSTRATED or
DECLARED until sourced, and every number below is UNGROUNDED, needs a source, until
the CrossRef chain in the citation rule has run.

| material          | organism it is stolen from | what it does to the four lines                          | anchor       |
| ----------------- | -------------------------- | ------------------------------------------------------- | ------------ |
| water ice         | the comet                  | the §3 baseline                                         | MEASURED     |
| nacre             | mollusc shell              | ~100 MPa tensile, ~30x ice, so BURST retreats; opaque, so OPAQUE fires unless paired with an ice window or the comet-as-vessel light pipe (§11 ch.2) | DEMONSTRATED |
| biogenic silica   | diatom frustule            | grown glass, clear in the visible and strong; the one row that can open the window in both directions at once | DEMONSTRATED |
| spider silk       | spidroin in tobacco/potato | ~1 GPa tensile; not a wall, a tether: in zero g structure is tension, so mirrors and leaves hang on silk (§11 ch.2) | DEMONSTRATED |
| magnetite         | chiton radula              | hardest biomaterial; armour, not a vessel; a row for micrometeorite pitting once that is a failure mode | DEMONSTRATED |
| nickel-laden wood | hyperaccumulator trees     | metal in tissue is real (sap ~25% Ni in one species); metal as a structural wall is not, and the card says so | DECLARED     |

### Gene cards (organism rows)

Ordered from most to least grounded. Each moves one named input.

| card                       | stolen from                   | input it moves                                          | anchor       |
| -------------------------- | ----------------------------- | ------------------------------------------------------- | ------------ |
| antifreeze proteins        | fish, insects                 | the FREEZE threshold, by a few K of supercooling        | DEMONSTRATED |
| Dsup + desiccation proteins| tardigrade                    | the dormancy-vs-radiation budget (§11 ch.4, ch.5)       | DEMONSTRATED |
| DNA repair                 | Deinococcus radiodurans       | the same budget, the repair term                        | DEMONSTRATED |
| CAM + desert cuticle       | cacti, agaves                 | leaf-scale water loss in vacuum (§11 ch.1)              | DEMONSTRATED |
| UV screens                 | Arabidopsis flavonoid mutants | the seed's UV term; note the EXPOSE-E screen mutants did WORSE than wild type | DEMONSTRATED |
| chemosynthetic symbionts   | tube-worm bacteria            | a dark-side carbon source: O2 banked at perihelion, burned with comet organics at aphelion (§11 ch.3); a redox budget with real inputs | DECLARED |
| radiotrophic melanin       | Chernobyl fungi               | a cosmic-ray energy term; the literature claim is contested and the card says so | DECLARED |
| bioluminescence            | fungal luciferin plants       | nothing; a flourish for the aphelion picture            | DECLARED     |

**One thing plants already do that reads as fiction.** Xylem pulls water at about
-2 MPa, below absolute zero pressure; a tree is already a hydraulic system that
operates past vacuum. This goes on the landing page as the reason a plant, and not an
animal, is the organism for this story. UNGROUNDED, needs a source, before it ships.

**Non-goals for the tier.** No genome, no evolution of cards, no cost currency beyond
the carbon budget the model already has; a card's "cost" is carbon or mass charged to
the existing inequalities, never a new score.

**Milestone.** The deck ships after M2 (the verdict panel) and before M3 (the picture),
as M2b (S): the table, the two tests, and the badge. No card may be MEASURED until its
number is in `bio_grounding` with a section number.
