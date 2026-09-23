# Northstar design: the vessel, and watching it fail

> Revised 2026-09-12 after an llm-panel audit (impaired: codex/astra unavailable); findings in the coordinator's memory memo `northstar_panel_audit_2026-09-12.md`.
> Revised again 2026-09-12 after the round-2 panel audit: prediction 1 re-banded on the edge wall, bands hand-written from committed rows (§6), Q4 registers on FREEZE/STARVE/OPAQUE only, the deck's third rule demands first violation inside the registered box, M1 split into M1a0/M1a.
> Revised a third time 2026-09-13 after the round-3 panel (codex and astra answering): the transmission law is declared (sphere-averaged, refracted, §3) and every number in §3-§6 recomputed under it, normal incidence kept as a control row; M1a0 commits ONE spectral table (λ, k, E_AM0, n_ph) that the hand rows and `sim/vessel.py` both integrate on, plus `prereg.yaml`; Q4 registers on FREEZE and OPAQUE only (STARVE cannot be first-violated on the auto path, 0 of 3,900 states); every inequality reads the wall in force, with the four (p, t) modes tabulated (§5); the registered grids, edge rule and load order are written down (§6); the deck test quantifies over each card's whole range and stack (§12).
> Revised a fourth time 2026-09-13 after the round-4 panel (codex, 13 findings, every one confirmed or partially confirmed by an independent verifier, plus 4 the verifier added). Two root classes: **a law declared without its own reflectance is a second declaration** (the shell law fixed `n = 1.31` and then set the reflectance that `n` implies to zero, calling it "consistent with albedo 0"; §3 now states R̄ = 0.0627 and §6 registers a Fresnel sensitivity arm for both predictions, binding included), and **a verifier's scan grid copied into the spec as its own** (round 3's "3,900 / 7,722 states" were the reproduction script's scan sizes; every §4 count is now from the registered 197 × 101 × 3 = 59,691-node grid). Also: `f_photon` declared as a disk average with the interior mixing named as an input (§3); the `f_floor` card struck so §3's "only comparator the deck may move" holds (§12); `prereg.yaml` committed one commit before the calculator, edge-rule ties decided (§6, §8); every BURST cell reads `σ_eff(T_shell)` (§5); the pvlib source pinned to a commit (§6, §8). Responses to all 17 findings at the end of the document.
> Revised a fifth time 2026-09-14 after the round-5 panel (codex, 16 findings, 5 confirmed and 11 partially confirmed by an independent verifier who reproduced every registered digit from the pinned sources, plus 4 the verifier added). Root class: **stating the omitted reflectance hid two more declarations** (the round-4 Fresnel arm wrote "ice→interior, reciprocal, equal", which is true only for a vacuum interior, and scaled `T_eq` by the first-surface `(1 − R̄)`, which is not energy-conserving for a slab and understates the vapour-inner wall's reflectance by 17%): the arm now has three explicit inputs, `optical_law`, `n_interior` {vapour, water} and `thermal_reflectance` {0, slab}, eight rows, and re-read expected outcomes, with P1's σ 0.7 edge under optics alone moving INSIDE the band on the water index and P2 under optics + thermal freezing at 57.1 km, below the band, on the vapour one (§3, §5, §6, §8; that 57.1 km followed a non-conserving balance and is superseded in round 6 by 78.4 km, inside the band). Also: the tie clause bisects every registered line and reports the smallest root (§6); the declared assumptions are a registry table, isothermal shell included (§3); the Question is asked under the declared law (§6); the page prints the slab reflectance of the wall in force, not the first-surface 0.063 (§5); the §4 grid census gets an in-repo producer (§8); the import guard is bidirectional with a file-read half, the regeneration test pins its formatter, the deck's comparator test is semantic (§6, §12); 0.2103 → 0.1931 and the rim 0.2259 → 0.2245 (§3, §4). Responses to all 20 findings at the end of the document.
> Revised a seventh time 2026-09-22 after the round-6 audit (codex, 6 findings): arm (ii)'s thermal balance conserves energy (`T_shell⁴ = (1 − R_slab_sw)·T_eq⁴`, `T_int⁴ = (1 − R_slab_sw + T_sw)·T_eq⁴`) and its four rows are recomputed (P2 water binds OPAQUE again); tie candidates are the lines that change sign in the bracket; a twelfth registry row, `solar_tail_transmission`, and the key `optical_law`; `test_prereg_equals_spec` compares the whole prereg structure; stale M1a0 wording fixed. Responses at the end.

> Drafted 2026-09-12 against `release/1.0.1-rc` (`7ed4414`); revised against `master`
> (`08fac2e`, then `17f08c6`, then `372f941`). Every claim about current code carries a `file:line`. Nothing here edits
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
  without node (`:33-38`), pins fixtures to the md5 of `sim/physiology.py`, `thermal.py` and
  `organism.py` (`:82-99`; the tuple at `:86-90` names those three, so M1b adds `vessel`
  there and in `make_fixtures.py`), and
  runs 9 tests incl. crossovers against the committed CSV (`:155`).
  Fixtures come only from `sim/` public functions (`tools/make_fixtures.py:2-7`).
- **Site build and rail.** `tools/build_site.sh` copies three web files, then both licences and
  `.nojekyll` (`:16-30`) and refuses double-quoted remote `src=` and `<link href=` assets (`:36-40`;
  single-quoted, CSS `url()` and runtime fetches pass). `pages.yml` on master checks out with
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
700 nm, a factor of 701 (`§9:532-540`). A slab of thickness `t` at normal incidence
passes `exp(-k(lambda)·t)`; the shell is not a slab at normal incidence, and the
difference is load-bearing (round-3 audit, astra), so the law is declared here:

**The transmission law (sphere-averaged, refracted).** Distant sun, thin wall
(`t << R`): a ray meets the lit hemisphere at incidence angle `θ` from the local
normal with projected-area weight `2μ dμ` (`μ = cos θ`), refracts into the ice by
Snell, `sin θ' = sin θ / n`, with `n = 1.31` (DECLARED, the sixth declared input), and
crosses the slab path `t / cos θ'`. The REGISTERED law carries no Fresnel reflection.
That is an omission with a known size, not a consistency with `albedo = 0`: the same
`n = 1.31` fixes the unpolarised reflectance at the outer face, `R(normal) = ((n-1)/(n+1))²
= 0.0180`, and its projected-area average over the lit hemisphere, `R̄ = ∫₀¹ 2μ R(μ) dμ =
0.0627`, which is the FIRST-SURFACE reflectance only. The reflectance a thermal balance
must use is the slab's, `R_slab`: the outer face plus every pass back out through the inner
face, and the inner face reflects by the index of what it touches, `n_interior`, a second
declared choice the round-4 text left hidden (round-5 audit). With vapour inside
(`n_interior = 1`, the one reading under which the ice→interior reflectance equals the
air→ice one at the refracted angle) the solar-weighted slab reflectance of the P1 σ 0.7 edge
wall is 0.0752, 104% of the 0.0721 that freezes the shell at 1 AU (below); with liquid water
inside (`n_interior = 1.333`) the inner face reflects 7.6e-5 at normal incidence and the slab
value collapses to the first-surface 0.0628, 87% of the line. The law is kept as declared so
that rounds 2-3's hand-pinned bands stay the registration; the reflectance the law omits is
registered as a named sensitivity arm for both predictions, binding included, with
`n_interior` and the slab reflectance as its explicit inputs (§6, "Fresnel arm"), and the
page prints the slab reflectance of the wall in force beside the 0.072 line (§5). So

`T(k·t) = ∫₀¹ 2μ · exp(-k·t / μ'(μ)) dμ`, `μ'(μ) = sqrt(1 - (1 - μ²) / n²)`,

a function of `k·t` alone, tabulated once and interpolated (log-log, 2,401 nodes from
1e-8 to 1e4). At `k·t = 1` it is 0.3001, against 0.3679 at normal incidence and 0.2194
for straight rays (`2·E₃(1)`); at `k·t` = 0.1 / 0.5 / 2 / 5 it is 0.8857 / 0.5463 /
0.0920 / 0.0030. `tau(lambda, t) = T(k(lambda)·t)` everywhere below. Normal-incidence
`exp(-k·t)` survives as the CONTROL law: `sim/vessel.py` takes the law as an argument,
and §6 carries one control row per prediction computed under it. The thin-wall law omits
O(t/R) effects (chord curvature, total internal reflection at the inner face, multiple
passes); over the registered auto-path domain `t/R ≤ 4.4e-4` at R = 10 km (the σ 0.7 edge
wall, 4.366 m) and the exact-chord recompute moves `tau_sw` from 0.34712 to 0.34711 and the
P1 edge by less than 1e-5 AU, under the 1e-4 AU edge tolerance (§6). Two integrals of
`tau` are the wall:

- `f_photon(t) = ∫₄₀₀⁷⁰⁰ tau(λ,t)·n_ph(λ) dλ / ∫₄₀₀⁷⁰⁰ n_ph(λ) dλ`, the fraction of
  AM0 PAR photons that arrive (`tools/size_par_filter.py:181-186`). This is the
  photon count, not a chlorophyll-weighted rate (`§12:959-963`); it is an upper bound
  on what the organism can use, stated as such on the page. **`f_photon` is the
  projected-disk average**, the total PAR throughput of the lit hemisphere divided by the
  disk area: a point organism at lateral offset `ρ` from the sun line sees only the rays
  that entered at `sin θ = ρ/R`, so its local fraction runs from the normal-incidence value
  at the centre (0.2699 at the P2 wall, t = 55.72 m) to 0.2245 at the rim (0.2259 at ρ/R = 0.99), with the disk
  average 0.2500. The organism is therefore taken to fill the interior, or the interior to
  mix what it receives; that is the seventh declared input, `interior = mixed` (§3
  declared list), and the page carries the alternative `central` (a point organism at the
  centre, which reads the normal-incidence `f_photon` with the shell-law `tau_sw`) as a
  labelled variant: P2 under `central` crosses the 0.25 floor at R = 119.3 km, inside the
  registered band. `tau_sw` is a global energy balance and is the disk average under
  either setting.
- `tau_sw(t) = ∫₂₈₀⁴⁰⁰⁰ tau(λ,t)·E(λ) dλ / ∫ E dλ`, solar-energy-weighted
  (`check_greenhouse_transparency.py:94-96`), band-normalised over 280 to 4000 nm
  (99.05% of TSI 1360.8; the tail outside the band is assumed to transmit like the
  band, the registry row `solar_tail_transmission: band_weighted_tau_sw`). NIR carries 53% of TSI and ice absorbs it (`§13:1021-1025`): at `p*` and
  R = 10 km a pressure wall passes 26 to 34% of solar energy at normal incidence (`tau`
  0.2609 to 0.3429, `§13:1054-1058`) and 25 to 33% under the shell law (0.2516 to
  0.3320); the 16 to 23% (`§13:1036`) belongs to the withdrawn 18 kPa walls.

Both integrals, and every number in §3-§6, are evaluated by trapezoid on ONE grid: ASTM
G173's native wavelength grid, 2,002 rows from 280 to 4000 nm (0.5 nm steps to 400 nm,
1 nm to 1700 nm, then 2 to 5 nm; 301 rows inside PAR), with `k(λ)` interpolated
log-linearly from Warren & Brandt's `m_im` onto it as `check_greenhouse_transparency.py:62-63`
does. That grid is the committed spectral table of M1a0 (§6, §8); the hand rows and
`sim/vessel.py` integrate on the same rows, so a digit that moves between them is a
defect, not a grid choice.

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
albedo)` with the shell-law `tau_sw` (`§13:1040-1046`; the `(N+1)^0.25` form is its `tau = 1` case). The derivation
is a spherical shell radiating from both faces, so `contained_temperature` fixes the
geometry at the sphere's `area_ratio = 4`; the organism's `area_ratio` (`sim/organism.py:35`,
lamina default 2.0) does not enter it, and choosing the vascular class changes the
organism, not the vessel. The shell sits at `T_shell = T_eq` exactly, independent of `tau` (`§17:1459-1460`). That
is the isothermal-shell reading of §13's two-body balance, a declared choice (the registry
below): `§17:1469-1470` also offers a gradient wall whose inner face sits at `T_int`, which
would put the inner face above melting at every node where FREEZE holds, and this spec
excludes it (round-5 audit).

**Vapour pressure at the contained temperature.** Buck: `p_sat(T_C) = 611.21 ·
exp((18.678 - T_C/234.5)·(T_C/(257.14 + T_C)))` (`check_greenhouse_transparency.py:99-100`);
it returns 611.654 Pa at 273.16 K and 882.22 Pa at 5.16 °C against the gate points
611.657 and 882 Pa (q3 spec `:217-220`), so Gate C carries a tolerance (§6).

**Self-consistent pressure, a function.** `p*(r, R, sigma) = p_sat(T_int(t_min(p*)))`,
solved by the damped iteration at `:120-130`, which M1a re-implements with a raise on
iteration exhaustion (the tool's loop, `:123-130`, reports its last iterate silently
after 200 passes; in practice it converges in at most 31, but a residual is a
postcondition, not a habit). At 1 AU and R = 10 km it is 3.453 / 3.002 / 2.607 kPa for
sigma 3.1 / 1.5 / 0.7 MPa at normal incidence (`§13:1054-1058`) and 3.330 / 2.899 /
2.521 kPa under the shell law (walls 5.37 / 9.66 / 18.01 m); as `R -> 0`,
`tau_sw -> 1` and `p*` rises to S1's 18.02 kPa ceiling (`§13:1060-1062`); at the page
default (1 km, 1.10 AU) it is another number, printed live beside the player's `p`.

**The roadmap's closed form, and why it is a control here.**
`R_max = 2·sigma·|ln tau_min| / (k·p)` (`docs/ROADMAP.md:145`, q3 spec `:139`) follows
from `t = pR/(2σ)` and `tau = e^{-kt}` with a scalar `k` and an acceptable `tau_min`.
Its two defects are named in the repo: `k` is not a scalar (`§9:539`) and `tau_min` is
author-declared, "NOT GROUNDED" (q3 spec `:166`). Here `k` becomes the integral above;
`tau_min` does not vanish, it becomes the declared floor `f_floor` of OPAQUE (§4),
disclosed and swept. The closed form survives as two unit-test controls at `k = 0.38623`
and `tau_min = 0.01`, both run under the normal-incidence control law, which is the law
the closed form assumes. (a) A port-regression of §13's mixed row: with `p` taken from
the SPECTRAL fixed point at normal incidence (3453.08 / 3002.39 / 2606.63 Pa) the
closed form gives 21.41 / 11.91 / 6.40 km (`§13:1073-1077`). (b) The scalar limit end
to end: with `tau_sw(t) = e^{-kt}` inside the fixed point too, and `p*` solved at
R = 10 km as the tool does (`R_ORGANISM_M`, `check_greenhouse_transparency.py:35`),
`p*` is 2346.3 / 1581.2 / 1103.6 Pa and `R_max` 31.51 / 22.62 / 15.13 km. A correct
scalar-limit implementation passes (b) and fails (a), so each control names which path
it exercises.

**Declared assumptions, the registry.** Round 5 found the count wrong twice ("seven"
against ten enumerated in §6, with `n_interior` and the shell's temperature profile in
neither list); this table is the list, twelve rows (round 6 added the solar tail), every
row exposed on the page under "declared", and `prereg.yaml` copies it under these keys (§8).

| name                    | registered value                          | role                                                                                      | where it moves                                    |
| ----------------------- | ----------------------------------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------- |
| `t_opt`, `omega`        | 298.15 K, 20 K                            | organism thermal response (`sim/organism.py:37,40`)                                       | page inputs                                       |
| `albedo`, `emissivity`  | 0, 1                                      | shell radiative balance (`Organism` fields `:38-39`, read here as the shell's)            | page inputs; the Fresnel arm replaces `albedo`    |
| `f_floor`               | 0.25                                      | OPAQUE comparator (§4)                                                                    | page input; P2 arms 0.50 / 0.10                   |
| `n`                     | 1.31                                      | ice refractive index, the shell law (§3)                                                  | fixed                                             |
| `interior`              | `mixed`                                   | `f_photon` as a disk average (§3)                                                         | `central` variant row                             |
| shell temperature       | isothermal, `T_shell = T_eq`              | §13 two-body balance; §17's gradient-wall reading excluded (above)                        | fixed                                             |
| dust                    | `none`                                    | magnitude ungroundable, direction pinned downward on `tau`, `T_int`, `p*` (`§15:1287-1297`) | page toggle {none, 0.0087, 0.0548 /m}, DECLARED   |
| `T_freeze`              | 273.15 K                                  | interior freezing point, grounded (pure water); the only comparator the deck may move (§12) | deck                                              |
| `optical_law`           | `shell`: shell law of §3, no reflectance  | the registration                                                                          | control law `normal`; Fresnel arm `shell+fresnel` |
| `n_interior`            | arm only: vapour 1.000 (default), water 1.333 | index of what the inner face touches (§3 above, §6)                                   | arm rows                                          |
| `thermal_reflectance`   | arm only: `0` (registered), `slab`        | `slab`: two-body balance with `R_slab_sw(t)` of the wall in force, `T_shell⁴ = (1 − R_slab_sw)·T_eq⁴`, `T_int⁴ = (1 − R_slab_sw + T_sw)·T_eq⁴` (§6) | arm rows                                          |
| `solar_tail_transmission` | `band_weighted_tau_sw`                  | the 0.95% of TSI outside 280–4000 nm transmits like the band (§3)                          | fixed                                             |

Albedo is not cosmetic: at 1 AU the shell melts at albedo 0 and freezes at 0.0721
(`§17:1501-1502`), and the shell's own slab reflectance under the declared `n` sits on
either side of that line by the inner index (0.0752 with vapour inside, 0.0628 with water,
at the P1 σ 0.7 edge wall; §3 above): the registered `albedo = 0` is a declaration that the
Fresnel arm (§6) relaxes, with the melt door moving from 1.0381 AU to 0.9983 AU (vapour) or
1.0050 AU (water) at that wall. If `albedo > 0` the same `(1 - albedo)` scales `I_wall`;
Beer-Lambert models absorption only (`§17:1505-1509`), which is why the reflectance has to
be carried separately, not why it can be zero. Q4 registers on dust `none`.

## 4. The failure modes, as arithmetic

Each is an inequality evaluated from the inputs; the page prints both sides. There is
no `if failure_type == ...` anywhere; `classify_failure` returns the set of violated
inequalities, in the load order BURST, FREEZE, BOIL, STARVE, OPAQUE, and the first
violated names the picture. Four have grounded comparators (0 for STARVE, `T_freeze`,
`sigma`, `p_sat`); STARVE's inputs include the declared `t_opt` and `omega`; OPAQUE's
comparator itself is declared and says so on its line. `classify_failure(p, t, r, R,
sigma, organism, inputs)` takes `p` and `t` as RESOLVED values; which of them is auto and
which manual is the caller's business (§5).

**On the auto path two lines are equalities, not tests, and a third cannot fire.** With
`t = t_min`, hoop stress equals `sigma` exactly; with `p = p*`, `p` equals `p_sat(T_int)`
to the fixed point's residual (`|Δp| < 1e-6` Pa, `check_greenhouse_transparency.py:127`).
BURST and BOIL therefore hold by construction on the auto path (except BURST's
`sigma(T_shell) = 0` door inside 1.0381 AU, the melt door, below) and are failure modes
of manual gestures only. STARVE holds on the auto path for a different reason: it is never
the first inequality violated. Over the registered grid (§6; r 1.04 to 3.00 AU in 0.01 AU
steps, R 10 m to 1000 km at 20 nodes per decade, three sigmas: 197 × 101 × 3 = 59,691
states, scanned under both laws) STARVE is first-violated 0 times under the shell law
(52,816 FREEZE, 394 OPAQUE, 6,481 HELD) and 0 times at normal incidence (52,668 / 359 /
6,664); every STARVE violation (41,968 shell, 41,796 normal) sits at `T_int < 273.15 K`,
where FREEZE already named the picture, and the smallest STARVE margin with FREEZE holding
is +1.826 µmol under the shell law (σ 0.7, r 1.09 AU, R 794 km, `f_photon` 0.094) and
+1.874 at normal incidence; the grid minimum of `f_photon` on the auto path is 0.0579
(shell) / 0.0667 (normal) while STARVE at 273.15 K needs 0.0007. (Round 3 printed 3,900 and
7,722 states and +1.89: those were the reproduction script's scan sizes and its coarse
minimum, not the registered grid; round-4 audit.) So `binding = STARVE` is a lose-condition that cannot fire, and Q4 does not
register on it; STARVE is displayed as a margin and monitored (§6). Every comparison
carries a stated epsilon (BURST and BOIL: 1e-6 relative; FREEZE: 1e-6 K; STARVE and
OPAQUE: 1e-9 in their units) so a HOLD is never a solver residue, the readout prints the
margin beside each HOLD, and on the auto path it prints BURST's and BOIL's margins as
0 by construction. Because "by construction" hides the construction under test, an
auto-path BURST or BOIL violation is a RUNNER ERROR (exit 2), never a binding, and M1a
keeps a mutation control that must trip it: sizing the wall at `0.99·t_min` at the page
defaults gives hoop stress 707,071 Pa against 700,000 (BURST) and `p_sat(T_int)` 1965.3 Pa
against `p*` 1960.5 (BOIL). Q4 registers on FREEZE and OPAQUE only (§6).

**BURST.** `p·R/(2t) > σ_eff(T_shell)`. `σ_eff` is Petrovic's 0.7 to 3.1 MPa while the
shell is solid, and 0 when `T_shell = T_eq(r) > 273.15 K`, because the wall is then
water, not ice (`§17:1465-1471`: at 1 AU, albedo 0, the coldest part of the wall is
5.16 °C). Two doors, one inequality: too much pressure for the wall you built, or a
distance so close the wall is not a solid. The annulus's inner edge, 1.0381 AU at
albedo 0 (`§17:1480-1486`), falls out of `σ_eff(T_shell) = 0`, not a stored number.
`σ_eff(T_shell)` is what BURST reads in EVERY (p, t) mode (§5's table): the wall-phase
check is part of the inequality, not of the auto path, and on the auto path it is
additionally a PRECONDITION of `t_min`, since with `σ_eff = 0`, `t_min = pR/(2·0)` is
undefined; so a state inside the melt door is BURST in every mode, displayed with
`σ_eff = 0` printed, and lies outside the registered `r` grid, whose lower edge is 1.04 AU
(§6). At 1.00 AU and R = 10 km the other lines all HOLD under the shell law (`T_int`
294.37 K, `f_photon` 0.391, STARVE +9.12; 294.92 K / 0.414 / +9.21 at normal incidence);
the registered pair would read HELD there, which is why the grid does not reach it.

**FREEZE.** `T_int < T_freeze`, `T_freeze` = 273.15 K unless a deck card lowers it
(§12). The 273.15 K / 611.21 Pa pair is a convention, 0.01 K and 0.45 Pa below the triple
point (273.16 K / 611.657 Pa): liquid there is metastable, and taking the triple point as
the freezing line instead moves the P1 σ 0.7 edge from 1.20493 to 1.20482 AU, 1.1e-4 AU,
the size of the edge tolerance (§6). `T_int = (1+tau_sw)^0.25 · T_eq(r)` drops below melting outward: at R = 10 km and
`p = p*` the edge is 1.205 to 1.254 AU across the three sigmas (§6; 1.211 to 1.261 at
normal incidence), 1.468 AU in the `tau = 1` limit of a vanishing wall, where the law
does not enter. The interior frosts.

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
(`compensation_irradiance`, `:126-135`) against 1993.6 µmol of pre-wall PAR at 1.10 AU
(`irradiance(1.10)`, `sim/physiology.py:22-30`), which the 1.400 m default wall passes at
`f_photon` 0.8327 as `I_wall` = 1660.1 µmol, 3.0e-4 of it. There
is no `I_c(T_int)` in the repo; a temperature-consistent threshold is algebraically the
STARVE line itself, not a second inequality.

**OPAQUE.** `f_photon(t) < f_floor` on the wall IN FORCE: `t_min(p*, R)` on the auto
path, the manual `t` otherwise (§5's mode table). On the auto path `t_min = p*R/(2σ)`
rises sublinearly in `R`, since `p*` falls as the wall thickens, and the photon fraction
falls with it. A manual 100 m wall at R = 1 km, 1.10 AU, is OPAQUE (`f_photon` 0.1931; round 4 printed 0.2103, the normal-incidence value)
though `t_min` at its own `p_sat` would pass 0.94; the wall the visitor built is the one
judged. `f_floor` is
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
`f_floor` [0.25], dust floor [none], interior [mixed; `central` labelled variant, §3],
Fresnel [off; `optics` and `optics+thermal` are the §6 arm's two variants, labelled],
`n_interior` [vapour; water, read by the arm only]. Auto is the self-consistent design; manual over- or under-builds.
When `p` goes manual with `t` on auto, `t` freezes at `t_min(p*)` and does not re-track
the manual `p`; otherwise hoop stress would equal `sigma` at every `p` and the BURST
gesture below could never fire.

**The picture.** An SVG cross-section: outer circle radius ∝ `R + t`, inner circle
∝ `R`, wall band at its true ratio `t/R` (clamped to a visible minimum, clamp labelled).
Interior hue from the transmitted PAR spectrum (blue-shift as `t` grows: `tau(λ,t)` at
31 PAR rows), brightness from `f_photon`. Organism: a green disc whose saturation is
`net_carbon_contained / a_max`, grey at zero. Overlays, each keyed to its inequality:
BURST fractures the wall with `p·R/2t` vs `σ_eff(T_shell)` at the break; FREEZE frosts the
interior with `T_int` vs 273.15 K; BOIL dries it with `p` vs `p_sat(T_int)`; STARVE
fades the disc with `net` vs 0; OPAQUE darkens the interior with `f_photon` vs `f_floor`
(labelled declared). No text-transform anywhere (`web/index.html:29-33`).

**The readout panel.** One line per inequality, both sides as numbers with units, HOLDS
or VIOLATED. Below: `p*`, `t_min`, two windows in `r`, labelled: `[r_melt, r_freeze]`
for the current wall HELD FIXED (1.2428 AU at the defaults) and the auto-path edge with
`p*` and `t_min` re-solved at each `r` (1.2805 AU), and the live `R_window` against the
registered floor. Beside the albedo input the panel prints the two lines the declaration
sits between: "shell reflectance from n = 1.31, multi-pass, this wall, `n_interior` as
set: R_slab_sw(t)", computed live (0.0752 at the P1 σ 0.7 edge wall with vapour inside,
0.0628 with water; not applied in the registered law; Fresnel arm §6), and "freezes at 1 AU
above albedo 0.072". The first-surface 0.063 is not printed: it understates the vapour-inner
wall by 17% and puts the ratio to the freeze line on the wrong side of 100% (round-5 audit).

**The four (p, t) modes**, what each inequality reads; `classify_failure` receives the
resolved pair and does not know which mode produced it:

| `p`    | `t`    | resolution                                                                                  | BURST reads                                                                                           | BOIL reads               | FREEZE / STARVE / OPAQUE read |
| ------ | ------ | ------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- | ------------------------ | ----------------------------- |
| auto   | auto   | `p = p*(r, R, σ)`, `t = t_min(p*)`; the design                                              | `p*R/2t_min` vs `σ_eff(T_shell)`: = σ, margin 0, while the shell is solid; BURST inside the melt door | `p*` = `p_sat`, margin 0 | `t_min`                       |
| manual | auto   | `t` FROZEN at `t_min(p*)` of the auto state, does not re-track `p` (else BURST never fires) | `p·R/2t` vs `σ_eff(T_shell)`                                                                          | `p` vs `p_sat(T_int(t))` | the frozen `t`                |
| auto   | manual | `p` re-solved as the fixed point ON THE GIVEN `t`: `p = p_sat(T_int(t))`                    | `p·R/2t` vs `σ_eff(T_shell)`                                                                          | `p` = `p_sat`, margin 0  | the manual `t`                |
| manual | manual | both as given                                                                               | `p·R/2t` vs `σ_eff(T_shell)`                                                                          | `p` vs `p_sat(T_int(t))` | the manual `t`                |

Every BURST cell reads `σ_eff(T_shell)` (§4), never the input `σ`: a manual wall at r = 1.00 AU
has `T_shell = T_eq = 278.311 K > 273.15 K`, so `σ_eff = 0` and the line is BURST at any
`p > 0`, not "5,000 Pa against 700,000 HOLDS". The mode-agnostic invariant M1a tests: for
every (p, t) mode and every `r`, `classify_failure` names BURST whenever `T_shell > 273.15 K`,
with `σ_eff = 0` printed, and the same call with `r` moved outside the melt door and the same
`p`, `t` reads the input `σ` (positive case).

**The first 60 seconds**, at the defaults (1 km, 1.10 AU, 0.7 MPa, auto wall and
pressure). Load: alive; FREEZE, STARVE and OPAQUE HOLD with margins, BURST and BOIL
at margin 0 by construction (§4). Drag `r` inward: at 1.038 AU the wall line turns to
water and BURST fires with `σ_eff = 0`. Drag outward: the interior frosts at the edge
`model.js` prints for this wall; at the defaults `p*` is 1960.5 Pa, `t_min` 1.400 m,
`tau_sw` 0.4331 (shell law; 2033.6 Pa, 1.453 m, 0.4445 at normal incidence, between the
0.625 m row's 0.5086, `§13:1031`, and the 16.1 m row's), `T_int` 290.34 K, and the
auto-path edge (`p*` and `t_min` re-solved at each `r`) is ≈1.28 AU (1.2805; the 1.400 m
wall held fixed freezes at 1.2428 AU, and the page labels which it prints); the page
prints the computed value, not a figure from this spec. Push `p` above `p*` (with `t`
frozen, §5 modes): BURST. Pull `p` below `p_sat`: BOIL. Set `t` manual and thicken it:
the interior goes blue, then OPAQUE at the declared floor (≈56 m), then FREEZE once
`tau_sw` falls under 0.1227 (past ≈233 m at 1.10 AU). Raising `R` alone at 1.10 AU:
`R_window` there is provisionally ≈96 km (§6), so it dies inside the 100 km slider by a
hair; that is why it is printed. STARVE is the one line no gesture reaches at the
defaults (§4); it stays a HOLD with its margin printed (+8.23 µmol at the defaults).

## 6. Pre-registration Q4

**Question.** At self-consistent pressure `p*` and a spectral ice wall sized to the hoop
load (`t = t_min`, so strength is an identity on this path, §4, and BURST is asserted, not
asked), and under the declared law of §3 (whose omitted reflectance moves P1 by up to
0.06 AU, the Fresnel arm below), is there ANY radius `R` at which the interior stays liquid and the wall stays
clear enough to pass the declared photon floor, and at what distance `r` does that
window close?

**Quantities and the registered grids.** `r`: 1.04 to 3.00 AU in 0.01 AU steps, 197
nodes, lower edge above the 1.0381 AU melt door (§4) so every node has a solid wall.
`sigma`: {0.7, 1.5, 3.1} MPa. `R`: 10 m to 1000 km, 20 nodes per decade on a log grid,
101 nodes, wider than the page slider so closure can be found. `R_window(r, sigma)` = the
largest `R` at which FREEZE, STARVE and OPAQUE hold with `p = p*(r, R, sigma)` and `t =
t_min` (BURST and BOIL are asserted, not tested, on this path: a violation is a runner
error, §4); `r_close(R, sigma)` = the largest `r` with the window open at that fixed `R`;
`binding` = the first violated inequality in load order at the edge, named by
`classify_failure`. **Edge rule:** an edge is the root of the binding line's margin,
bracketed by the last HOLD and first VIOLATED grid nodes and refined by bisection to
1e-4 AU in `r` and 0.1% in `R`; grid nodes are for display and for the bracket, never
the reported edge. **Ties (round-5 audit: an edge rule keyed to the node, not the root, could report
an edge past the window's own close; round-6 audit: "bisect every line" is undefined for a
line with no sign change in the bracket):** the bracket is the last all-HOLD node and the first
any-VIOLATED node; the CANDIDATES are the registered lines (FREEZE, OPAQUE) that HOLD at the
lower node and VIOLATE at the upper one, the only lines with a sign change in the bracket;
each candidate's margin is bisected to its root; the edge is the SMALLEST root and `binding`
is that root's line, so the reported edge is where the window closes by its own definition,
never where the load-order line happens to cross; only when two roots fall within one
tolerance of each other does load order decide, and the runner prints both. Roots of other
lines further out (e.g. P2's FREEZE at 532.6 km) are printed as COUNTERFACTUAL, never as the
edge. The rule this replaces bisected the line first in load order at the first violated
node, and was wrong on the case where both lines hold at node k, both are violated at k+1,
and the load-order line's root sits deeper in the bracket than the other's; M1a keeps that
case as a test with a synthetic pair of margins. (On the registered rows no two lines share
a bracket: P2 OPAQUE 95.6 km against FREEZE 532.6 km; the 0.10 arm 777.5 against 532.6 km.
Under the Fresnel optics + thermal arm with vapour inside, FREEZE 78.4 against OPAQUE
102.3 km, different brackets; with water, OPAQUE 109.8 against FREEZE 111.6 km, the closest
pair in the arm, 1.8 km apart, and BOTH inside the one bracket between the 100.0 and
112.2 km nodes: that arm row is the tie clause's live case, and the rule it replaces would
have reported FREEZE at 111.6 km.) If
no node holds, `R_window = 0` and the window is empty. Load order:
BURST, FREEZE, BOIL, STARVE, OPAQUE. A window edge is a curve, so each registration fixes
one axis at a declared value. `binding` is drawn only from FREEZE and OPAQUE: BURST and
BOIL hold by construction at `t = t_min`, `p = p*`, and STARVE is never first-violated
there (§4); none of the three can bind or lose a prediction, and STARVE's margin is
reported at every edge so a run that reaches it is a finding, not a registered loss.

**Where the bands come from.** The bands below are HAND-WRITTEN in this spec from the
committed rows in the table that follows, and `prereg.yaml` copies them verbatim with the
grids, edge rule, tolerances and load order above; `test_prereg_equals_spec` asserts the
WHOLE prereg structure (bands, bindings, grids, edge rule, tolerances, load order, registry,
arm rows) equals a canonical expected structure parsed from this spec's own tables and text,
not two band strings (round-6 audit). **A prereg is never written by the code that checks it:**
`prereg.yaml` is committed ALONE, referencing this spec at its round-6 revision, ONE COMMIT
BEFORE `tools/q4_hand_rows.py` (the hand-row commit is cherry-picked onto the prereg commit,
never merged from its older parent), which is vessel arithmetic (it implements `p*`, `tau_sw`,
`f_photon` and the edge rule) and so cannot share the prereg's commit without erasing the
chronology git is meant to show; M1a's ancestor test (§8) pins that order. The rows are
reproduced in M1a0 by `tools/q4_hand_rows.py`, committed with its output beside the
spec's table. It reads the ONE committed spectral table `sim/spectral_table.csv` (§3: λ,
`k`, `E_AM0`, `n_ph` on ASTM's 2,002-row grid, header carrying the md5 and byte size of
both sources, `ASTMG173.csv` b31870bd… 57,708 B, fetched from pvlib-python at commit
`2d0ed71e1308293b3081979404f8e90f2f2dde1e` (`pvlib/data/ASTMG173.csv`; the file at that
commit hashes to b31870bd…, checked 2026-09-13; `docs/THIRD-PARTY.md:35` is pinned to this
commit, done in M1a0 at `ae56554`), and `iop2008.dat` cf5f76d5…
16,514 B, and the word `trapezoid`) and the existing `sim/thermal.py`,
`sim/physiology.py`, `sim/organism.py` functions; its output repeats both digests. Both
sources are gitignored (`.gitignore:9-10`) and ABSENT from the checkout; the table is
the only input that exists in CI. Three tests keep the rows honest, with their limits
stated: (i) the literal SMELL test, no float literal in `q4_hand_rows.py` equals any value
printed in this section's table, is a smell, not a proof (`0.16 + 0.001`, `float("0.161")`
or a value read from a file evade it); (ii) `test_reproduce_hand_rows` recomputes every
row FROM THE COMMITTED TABLE and matches the printed digits, which proves the rows follow
from the table and CANNOT catch a wrongly generated table, since both consumers share it;
so (iii) `test_regenerate_spectral_table` re-runs the producer on the two sources and
asserts the regenerated table equals the committed one as PARSED VALUES at rtol 1e-12
(`tests/test_spectral_table.py:94-122`; the producer pins its formatter, `%.10e` and `\n`,
but a header- or newline-only difference is not detected by this test, it is out of its
scope; the header md5 is provenance, not the assertion; round-5 and round-6 audits), and it SKIPS,
never passes, when either source is absent (CI), so a green CI run says "rows follow
from table", and only a developer run with the sources says "table follows from
sources". The import guard is BIDIRECTIONAL with a file-read half (round-5 audit: one-way, it left
`sim/vessel.py` free to read the prereg or the hand-row output): `q4_hand_rows.py` imports
nothing from `sim/vessel.py`, `sim/vessel.py` imports nothing from `tools/`, and
`sim/vessel.py` opens neither `prereg.yaml` nor the hand-row output; an M1a test, when that
file exists: an AST walk of both import closures and of every `open` / `read_text` literal,
each direction with a negative case that adds the forbidden edge and must fail. M1a's code computes the same
points and is the object under test, never the source of a band: a computed point outside
its hand band FAILS, it does not re-register. An empty window at every `r` would falsify
both and be the headline finding.

| row                                   | fixed                          | wall at the edge                                                                         | edge                                                        |
| ------------------------------------- | ------------------------------ | ---------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| P1, σ 0.7 MPa                         | R 10 km                        | `p` = p_sat(0 °C) = 611.21 Pa, t 4.366 m, τ_sw 0.3471, f_photon 0.640                    | r 1.2049 AU                                                 |
| P1, σ 1.5 MPa                         | R 10 km                        | 611.21 Pa, t 2.037 m, τ_sw 0.4045, f_photon 0.778                                        | r 1.2303 AU                                                 |
| P1, σ 3.1 MPa                         | R 10 km                        | 611.21 Pa, t 0.986 m, τ_sw 0.4599, f_photon 0.875                                        | r 1.2543 AU                                                 |
| P1 control, normal incidence          | R 10 km, σ 0.7 / 1.5 / 3.1     | same walls, τ_sw 0.3610 / 0.4187 / 0.4741                                                | r 1.2111 / 1.2365 / 1.2605 AU                               |
| P2 OPAQUE, f_floor 0.25               | r 1.10 AU, σ 0.7               | p\* 816.4 Pa, t 55.72 m, τ_sw 0.1908, T_int 277.20 K                                     | R 95.6 km                                                   |
| P2 FREEZE                             | r 1.10 AU, σ 0.7               | p\* = 611.21 Pa, t 232.5 m, τ_sw 0.1227                                                  | R 532.6 km                                                  |
| P2 arms, OPAQUE crossing              | r 1.10 AU, σ 0.7               | f_floor 0.50 / 0.10                                                                      | R 10.6 km / 777.5 km (R_window for 0.10 = 532.6 km, FREEZE) |
| P2 control, normal incidence          | r 1.10 AU, σ 0.7, f_floor 0.25 | p\* 816.6 Pa, t 67.05 m                                                                  | R 114.9 km (FREEZE 642.6 km)                                |
| P2 variant, interior `central`        | r 1.10 AU, σ 0.7, f_floor 0.25 | shell τ_sw, normal-incidence f_photon (§3)                                               | R 119.3 km                                                  |
| P1 Fresnel arm (i), vapour inside     | R 10 km, σ 0.7 / 1.5 / 3.1     | two-interface T, n_interior 1; τ_sw 0.3108 / 0.3621 / 0.4115, f_photon 0.573 / 0.696 / 0.782 | r 1.1886 / 1.2116 / 1.2334 AU                               |
| P1 Fresnel arm (i), water inside      | R 10 km, σ 0.7 / 1.5 / 3.1     | n_interior 1.333; τ_sw 0.3259 / 0.3797 / 0.4316, f_photon 0.601 / 0.730 / 0.821            | r 1.1954 / 1.2194 / 1.2421 AU                               |
| P1 Fresnel arm (ii), vapour inside    | R 10 km, σ 0.7 / 1.5 / 3.1     | as (i) vapour and the two-body balance, T_int⁴ = (1 − R_slab_sw + T_sw)·T_eq⁴, R_slab_sw 0.0752 / 0.0776 / 0.0799; melt door 0.9983 / 0.9971 / 0.9958 AU | r 1.1540 / 1.1766 / 1.1980 AU                    |
| P1 Fresnel arm (ii), water inside     | R 10 km, σ 0.7 / 1.5 / 3.1     | as (i) water and the two-body balance, R_slab_sw 0.0628; melt door 1.0050 AU              | r 1.1668 / 1.1914 / 1.2146 AU                               |
| P2 Fresnel arm (i), vapour inside     | r 1.10 AU, σ 0.7, f_floor 0.25 | OPAQUE: p\* 789.6 Pa, t 42.74 m, τ_sw 0.1827; FREEZE at t 173.0 m                         | OPAQUE R 75.8 km (FREEZE 396.2 km)                          |
| P2 Fresnel arm (i), water inside      | r 1.10 AU, σ 0.7, f_floor 0.25 | OPAQUE: p\* 800.7 Pa, t 48.05 m, τ_sw 0.1861; FREEZE at t 198.0 m                         | OPAQUE R 84.0 km (FREEZE 453.5 km)                          |
| P2 Fresnel arm (ii), vapour inside    | r 1.10 AU, σ 0.7, f_floor 0.25 | FREEZE: p\* 611.21 Pa, t 34.2 m, τ_sw 0.1930, R_slab_sw 0.0703, T_shell 260.57 K; OPAQUE at t 42.74 m | FREEZE R 78.4 km binds before OPAQUE 102.3 km               |
| P2 Fresnel arm (ii), water inside     | r 1.10 AU, σ 0.7, f_floor 0.25 | OPAQUE: p\* 612.9 Pa, t 48.05 m, τ_sw 0.1861, T_int 273.19 K, T_shell 261.09 K; FREEZE at t 48.7 m | OPAQUE R 109.8 km binds before FREEZE 111.6 km (closest pair in the arm, 1.8 km) |

**Registered prediction 1, in `r` at fixed `R = 10 km`, dust none, albedo 0, algal:**
**`r_close(10 km, sigma) ∈ [1.19, 1.27] AU` for every sigma, `binding = FREEZE`.**
Hand reading (rows above): the edge is `(1 + tau_sw)^0.25 · T_eq(r) = 273.15 K` with the
wall evaluated AT the edge, where `p* = p_sat(0 °C) = 611.21 Pa` and `t = 611.21·R/(2σ)`;
with `T_eq(1 AU, 4) = 278.311 K` and the shell law that is 1.2049 / 1.2303 / 1.2543 AU,
and a full fixed-point root-find on `T_int(r) = 273.15 K` returns the same to 4 dp. The
band leaves at least 0.0149 AU on each side of the extreme sigma (0.7 below, 3.1 above).
The normal-incidence control row (1.2111 / 1.2365 / 1.2605 AU) is what `sim/vessel.py`
must return under the control law; it is inside the band too, which is deliberate: the
band tests the vessel, the control row tests the law switch. §13's 1 AU walls (`tau`
0.2609 / 0.3013 / 0.3429, `:1054-1058`) are thicker than the edge wall and would put the
edge nearer the Sun; that reading is wrong because `p*` falls with `r`. At the edge
STARVE holds (+1.98 µmol) and OPAQUE holds (f_photon ≥ 0.640), so FREEZE is the binding.
The 1.1446 AU row (`§17:1482`) is the strong-dust arm (`§15:1291`), excluded by "dust
none", not a widening. Gate A cannot pre-decide it (edges at 275 / 282 K span 1.176 to
1.288 AU). It loses on a computed edge outside [1.19, 1.27] AU for any sigma, or a
binding other than FREEZE. **The page must
also show the `R -> 0` limit: `tau_sw -> 1` and the edge is 1.468 AU (`(1.18921 ·
278.311 / 273.15)²`); STARVE there is still +1.98 µmol.** That is the family's ceiling,
not the registration.

**Registered prediction 2, in `R` at fixed `r = 1.10 AU`, `sigma = 0.7 MPa`, dust none,
`f_floor = 0.25`:** **`R_window ∈ [60, 300] km`, `binding = OPAQUE`.** Hand
reading (rows above): the 0.25 floor is crossed at t = 55.72 m, which at the
self-consistent `p* = 816.4 Pa` is R = 95.6 km; STARVE holds there (+3.11 µmol). FREEZE
at 1.10 AU (`T_eq = 265.36 K`) needs `tau_sw < 0.1227`, reached at t = 232.5 m, which at
`p* = 611.21 Pa` is R = 532.6 km. OPAQUE binds with a factor 5.6 in `R` to spare. The
normal-incidence control row (114.9 km, FREEZE at 642.6 km) is the control-law value.
The red-band closed form, 6.40 km at 1 AU (`§13:1077`), sits far below. This loses two
ways: `R_window` outside [60, 300] km (below 60 km would put the spectral wall near the
scalar it corrects; between 300 and 533 km OPAQUE still binds but the reading is wrong),
or `binding` named FREEZE. The band is conditional on `f_floor = 0.25`: the 0.50 arm is
expected at ≈10.6 km, below the band, and the 0.10 arm's OPAQUE crossing at ≈778 km,
past FREEZE's 532.6 km, so that arm's `R_window` is expected FREEZE-bound at 532.6 km.
Both arms are reported, not registered.

**The Fresnel arm, registered as a sensitivity arm for BOTH predictions (round-4 audit),
its two hidden choices made explicit (round-5 audit).** The registered law is the declared
law of §3, without reflectance: option (a), kept because rounds 2-3 pinned the bands by hand
under it; the omitted reflectance is carried as a named arm with its own expected outcomes,
so Q4 stays falsifiable on the declared law and the arm says what the declaration costs. The
arm has THREE inputs, every one named in `prereg.yaml` and in `sim/vessel.py`'s signature
(§8): `optical_law = shell+fresnel`; `n_interior ∈ {vapour 1.000, water 1.333}`, the index
of what the inner face touches (round 4 wrote "ice→interior at μ′ (reciprocal, equal)",
which is the vapour case and no other: the ice→water reflectance is 7.6e-5 at normal
incidence, and P1's σ 0.7 edge under optics alone moves from 1.1886 AU, outside the band, to
1.1954 AU, inside it, on that one hidden index; vapour is the arm's default because wherever
FREEZE holds the inner face is below 273.15 K and liquid cannot wet it without freezing to
it); and `thermal_reflectance ∈ {0, slab}`, whether the thermal balance carries the slab's
reflectance. Optics: unpolarised
Fresnel at `n = 1.31`, air→ice at `μ` (`R₁`) and ice→interior at `μ'` by `n_interior`
(`R₂`), incoherent multi-pass, `T(k·t) = ∫₀¹ 2μ (1−R₁)(1−R₂) e^{−x} / (1 − R₁R₂ e^{−2x}) dμ`
with `x = k·t/μ'`, and beside it the slab's own reflectance `R_slab(k·t) = ∫₀¹ 2μ (R₁ +
(1−R₁)² R₂ e^{−2x} / (1 − R₁R₂ e^{−2x})) dμ`, which satisfies `R_slab + T = 1` at
`k·t = 0` (round 4's `T_eq·(1−R̄)^¼` did not: `1 − R̄ − T` left 4.3% of the light absorbed by
a non-absorbing slab, and it used the first-surface 0.0627 where the vapour-inner slab
reflects 0.0752 at the P1 wall; an M1a test asserts the identity for both indices). (i)
optics only: the two-interface `T` inside `tau_sw` and `f_photon`, `T_eq` unchanged. (ii)
optics + thermal: (i) and the two-body balance with the slab's solar-weighted reflectance
`R_slab_sw(t)` OF THE WALL IN FORCE (absorptance `A = 1 − R_slab_sw − T_sw`). Interior:
`T_int⁴ = T_sw·T_eq⁴ + T_shell⁴`; shell: `2·T_shell⁴ = A·T_eq⁴ + T_int⁴`. Hence
`T_shell⁴ = (1 − R_slab_sw)·T_eq⁴` and `T_int⁴ = (1 − R_slab_sw + T_sw)·T_eq⁴`, which at
`R_slab_sw = 0` is the registered `(1 + tau_sw)` law (round 5's `(1 − R_slab)(1 + T)` lost
the `R·T` term, round-6 audit). `R_slab_sw` enters the `p*` fixed point because `t` does;
`I_wall` is not scaled again, the (i) transmission already carries both faces. With vapour
inside, `T(1)` is 0.2714 against 0.3001, `R_slab_sw` 0.0752 / 0.0776 / 0.0799 at the three
P1 edge walls, above the 0.0721 freeze line, so under (ii) the melt door sits INSIDE 1 AU
(0.9983 / 0.9971 / 0.9958 AU) and `T_shell` at the P2 FREEZE wall is 260.57 K against
265.36; with water inside, `T(1)` is 0.2842, `R_slab_sw` 0.0628 at every wall (the inner
face adds nothing), the melt door 1.0050 AU and `T_shell(1.10 AU)` 261.09 K. Expected
outcomes, hand-read from the arm rows above: **P1** under (i) vapour 1.1886 / 1.2116 /
1.2334 AU, the σ 0.7 edge OUTSIDE [1.19, 1.27] by 0.0014 AU; (i) water 1.1954 / 1.2194 /
1.2421, all three INSIDE; (ii) vapour 1.1540 / 1.1766 / 1.1980, two of three outside (σ 0.7
and 1.5); (ii) water 1.1668 / 1.1914 / 1.2146, one of three outside (σ 0.7); binding FREEZE
in every row. **P2** under (i) OPAQUE binds at 75.8 km (vapour; FREEZE 396.2) and 84.0 km
(water; FREEZE 453.5), both inside [60, 300]; under (ii) **the binding FLIPS with vapour
inside: FREEZE at 78.4 km (t 34.2 m) before OPAQUE at 102.3 km, `R_window` 78.4 km, inside
the band with the wrong binding; with water inside OPAQUE still binds, at 109.8 km before
FREEZE at 111.6 km, inside the band, the closest pair in the arm (1.8 km, one bracket,
decided by the tie clause).** So the arm is expected to miss prediction 1's band on three
of its four `(n_interior, thermal_reflectance)` combinations (at least one σ each) and to
flip prediction 2's binding on the (ii) vapour row only; a run that reports
the registered rows HELD and the eight arm rows as expected has confirmed the
declaration's cost, not hidden it. The arm rows are reported beside every registered row,
the page carries the arm as a three-way toggle and `n_interior` as a declared input (§5)
and prints `R_slab_sw(t)` of the wall in force beside the 0.072 line, and if M1a's
`sim/vessel.py` returns arm rows off these digits by more than the edge tolerance that is
a defect, as for any control row. Single-pass against multi-pass Fresnel moves P1 by
0.0007 to 0.0009 AU; the registered arm is multi-pass.

**Gates the registration rests on: A and C.** Gate A: `T_eq(1 AU, sphere) ∈ [275, 282]
K` (q3 spec `:211-212`). Gate C: `saturation_pressure` gives 611.657 Pa at 273.16 K
within atol 0.01 Pa (Buck: 611.654), the one MEASURED anchor (the triple point); the
882 Pa at 5.16 °C within atol 0.5 Pa (Buck: 882.22) is a REGRESSION control, not a
second anchor, because the repo computed it from Buck in the first place
(`docs/thermal_premise_retired_2026-09-03.md:48-55`), and it cannot reject the equation,
only a transcription of it. Gate B as the q3 spec wrote it (`:213-216`, a measured
transmission through a stated thickness of ice) has no source in the repo and cannot
fail; it is demoted to an identity test (`transmission_spectrum` at one `k` under the
control law equals `exp(-k·t)`, and under the shell law equals the tabulated `T(k·t)`)
plus the committed-table checks: the table's header carries both source files' md5 and
size, the whole table's own digest is pinned in the test, and CI, where the gitignored
sources are absent by construction, asserts row count 2,002, strictly increasing λ from
280 to 4000 nm, and four pinned `k` rows, 0.00074 /m at 400 nm, 0.05230 at 550, 0.38623
at 680 and 0.52061 at 700 (`bio_grounding:534-537`); endpoints alone let a doubled
interior pass (round-3 audit). Nothing is registered on it. The gates touch the
radiative core and vapour pressure only, not `sigma`, `albedo`, `t_opt`, `omega`,
`f_floor`, which are swept or declared. A failing gate blocks the sweep and exits 2, as
Q2 did (`docs/FINDINGS.md:206-209`).

**Declared, explicit:** `t_opt = 298.15 K`, `omega = 20 K`, `albedo = 0`,
`emissivity = 1`, `f_floor = 0.25`, `n = 1.31`, `interior = mixed`, dust `none`,
`T_freeze = 273.15 K`, isothermal shell, the solar tail outside 280–4000 nm transmitting like
the band, `optical_law = shell`, the shell law of §3 without reflectance (control
law and Fresnel arm reported beside it; the arm's `n_interior` and `thermal_reflectance`
are arm inputs, and §3's registry table is the list); `R_ORGANISM` is swept, not assumed, and prediction 1 names 10 km
only as its fixed point.

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

- **M1a0 (S): the spectral table, the hand rows, the prereg.** Nothing below runs
  without it. Fetch `iop2008.dat` and `ASTMG173.csv` (gitignored, `.gitignore:9-10`,
  absent from the checkout). Extend `tools/extract_ice_k.py` (PAR filter at `:37`,
  `0.40 <= l <= 0.70`; its `--table` flag, `:69-74`, now calls `tools/make_spectral_table.py`)
  to write `sim/spectral_table.csv`: ASTM G173's native
  grid, 2,002 rows, 280 to 4000 nm, columns λ (nm), `k` (/m, log-space interpolation of
  `m_im` as `check_greenhouse_transparency.py:62-63` does, selection window 250 to
  4200 nm), `E_AM0` (W m⁻² nm⁻¹, ASTM column 2), `n_ph` (`E_AM0·λ/(hc)`, relative photon
  weight); provenance header naming both source files with md5 and byte size (§6), the
  quadrature (`trapezoid`) and the producer's commit. A `k`-only table cannot drive
  `tau_sw` or `f_photon` in CI, where the sources are absent (round-3 audit).
  `docs/THIRD-PARTY.md:35` is pinned to the pvlib-python commit
  `2d0ed71e1308293b3081979404f8e90f2f2dde1e` (§6), named in the table header. Commit the
  table checks of §6 (digest, row count, monotone λ, four pinned rows) and
  `test_regenerate_spectral_table` (parsed-value equality at rtol 1e-12 on regeneration from
  the sources; SKIPS when they are absent, §6). (All of this landed at `ae56554`.) Then, in this order and in SEPARATE commits:
  `experiments/q4_vessel/prereg.yaml` ALONE, with both bands, both bindings, the `r` and
  `R` grids, the edge rule with its tie clause and tolerances, the load order, the §3 registry
  of declared values (twelve keys, `optical_law` among them), its control, and the Fresnel arm as eight explicit rows keyed
  by `n_interior × thermal_reflectance`, each with its expected outcome (§6), all copied
  from this spec; then, one commit later (the hand-row commit cherry-picked onto the prereg
  commit), `tools/q4_hand_rows.py` and its output, which
  includes the control rows, the `central` variant row, the eight Fresnel arm rows of §6
  and the §4 grid census (the four counts per law, the min-STARVE-margin node with its
  margin, the grid minimum of `f_photon`; round-5 audit: those numbers had no producer in
  the repo, only a verifier's scratch script). What exists: `test_reproduce_hand_rows` and
  the per-row tests recompute every §6 row (registered, control, variant and arm) from the
  committed table on every run and parse the committed census from the output; the census
  RECOMPUTATION is the separate `test_section4_census`, marked `slow` and deselected by
  default. Acceptance, `pytest -q && pytest -m slow`: every §6 row matches the printed
  digits; the census recomputes; `test_prereg_equals_spec` matches the WHOLE prereg to a
  canonical structure parsed from §3's registry, §6's text and table (not the band strings
  alone); the strict-ancestor test (the prereg's introducing commit is a strict ancestor of
  the commit that introduces `tools/q4_hand_rows.py`; "ancestor of HEAD" is dropped as
  tautological, round-6 audit); the literal smell test, extended to the prereg, passes;
  `test_regenerate_spectral_table` passes with the sources present and reports SKIPPED
  without them.
- **M1a (M): the vessel, in Python.** `sim/vessel.py` (`wall_thickness`, `hoop_stress`,
  `shell_transmission(kt)` with the law as an argument, `transmission_spectrum`,
  `par_photon_fraction`, `solar_transmission`, `saturation_pressure`,
  `contained_temperature(r_au, t, *, optical_law="shell", n_interior=1.000,
  thermal_reflectance="0") -> (T_int, T_shell)`, `self_consistent_pressure(r_au, R, sigma, *,
  optical_law="shell", n_interior=1.000, thermal_reflectance="0")` raising on iteration
  exhaustion (the three arm inputs travel as keyword arguments, and `classify_failure`'s
  `inputs` is a frozen dataclass carrying all twelve registry keys by name),
  `classify_failure(p, t, r, R, sigma, organism, inputs)` reading `σ_eff(T_shell)` in
  every mode, §4), reading `sim/spectral_table.csv`; `Organism.net_carbon_contained`
  beside the existing paths; the §10 same-object test; the two closed-form controls (§3:
  21.41 / 11.91 / 6.40 km mixed, 31.51 / 22.62 / 15.13 km scalar limit), the two
  control-law rows, the `central` variant row and the eight Fresnel arm rows of §6 (three
  arguments, not one toggle: `optical_law ∈ {shell, normal, shell+fresnel}`, `n_interior ∈
  {1.000, 1.333}`, `thermal_reflectance ∈ {0, slab}`; a single `shell+fresnel` value cannot
  express variant (ii), round-5 audit), with `slab_reflectance(kt, n_interior)` beside
  `shell_transmission` and the test `R_slab + T = 1` at `k·t = 0` for both indices; the
  tie-rule test with a synthetic pair of margins whose load-order root sits deeper in the
  bracket (§6); Gate C with its atol and the
  identity test; the import-guard AST test with its negative case (§6); the M1a0
  strict-ancestor test kept, plus `prereg.yaml`'s md5 unchanged, as
  `tests/test_parity_js.py:82-99` pins fixtures; the runner-error test with the `0.99·t_min` mutation control (§4); and
  the mode-agnostic BURST invariant (§5): `classify_failure` names BURST with
  `σ_eff = 0` printed for any (p, t) mode whenever `T_shell > 273.15 K`, with the
  positive case at the same `p`, `t` outside the melt door reading the input `σ`.
  Acceptance: `pytest` green with the new tests; `sim/vessel.py` reproduces every §6 row
  to the printed digits under the shell law, every control row under the control law and
  every arm row under its `(optical_law, n_interior, thermal_reflectance)` triple; no band string is written by `sim/vessel.py`, and
  `prereg.yaml` is untouched since M1a0.
- **M1b (M): the numbers, in the browser.** The port to `web/model.js` with new
  fixture cases and parity tests. Acceptance: on the live page a stranger opens the
  console and `DysonModel.classifyFailure(...)` at the prereg's example inputs returns
  the set the prereg prints; `tests/test_parity_js.py` covers it, with `vessel` added
  to its md5 tuple (`:86-90`) and to `tools/make_fixtures.py`.
- **M2 (M): the verdict.** The seven inputs and the readout panel, no picture.
  Acceptance: at defaults FREEZE, STARVE and OPAQUE HOLD with positive printed margins
  and BURST and BOIL print margin 0 by construction; dragging `r` past the registered
  `r_close` (at `R` = 10 km) flips exactly one line to VIOLATED and it is FREEZE; manual
  `p` above `p*` flips exactly BURST, manual `p` below `p_sat` flips exactly BOIL, and a
  manual `t` of 100 m at the defaults flips exactly OPAQUE (§4).
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

1. **Commit a derived spectral table? Yes, and one table, not a `k` table.** The page
   must work from `file://` with no fetch, and Warren & Brandt's table is "not
   redistributed here" (`docs/FINDINGS.md:259-261`). A 2,002-row table of λ, `k`, `E_AM0`
   and `n_ph` on ASTM's grid is a derived quantity with its producer committed
   (`tools/extract_ice_k.py`); the producer's inputs are gitignored and absent
   (`.gitignore:9-10`), so the derived table is the only thing that can run in CI, and a
   `k`-only table would leave `tau_sw` and `f_photon` nothing to weight by (round 3).
   M1a0's first item, P0.
2. **First load: alive at 1.10 AU.** The first gesture is then a death the visitor
   caused; at 1 AU the wall is already water and the page opens on a corpse.
3. **`p` and `t`: player-set, with `p*` and `t_min` shown.** The only way BURST and
   BOIL are reachable at all: on the auto path they hold by construction (§4), so Q4
   registers on FREEZE and OPAQUE (item 6). Manual `p` freezes an auto `t` at `t_min(p*)`.
4. **Round-2 audit, where the bands come from: the spec, not the code.** Bands are
   hand-written in §6 from committed rows and copied into `prereg.yaml`; M1a's output is
   tested against them.
5. **Round-3 audit, which transmission law: the sphere-averaged, refracted one (§3).**
   Normal-incidence `exp(-k·t)` was an undeclared approximation that moved the
   registered edges by 0.006 to 0.016 AU; it is now the control law, with its own rows.
6. **Round-3 audit, what Q4 registers on: FREEZE and OPAQUE.** STARVE is never
   first-violated on the auto path (0 of 59,691 registered-grid states under either law,
   §4; round 3 wrote 3,900, a reproduction script's scan size) and joins BURST and BOIL
   as a displayed margin; `prereg.yaml` moves to M1a0 so the registration predates the
   code.
7. **Round-4 audit, the reflectance the law omits: registered as an arm, not as the
   law.** `n = 1.31` implies R̄ = 0.0627; the declared law stays the registration (§6,
   option (a)) and the Fresnel arm is expected to miss P1's band and flip P2's binding.
8. **Round-5 audit, the arm's own two hidden choices.** `n_interior` and the slab
   reflectance are the arm's explicit inputs; eight rows; P1 (i) lands inside the band on
   the water index and P2 (ii) freezes below the band on the vapour one (§6); round 6
   corrected the balance: P2 (ii) vapour freezes at 78.4 km, inside the band, wrong binding.

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

**Non-goal.** Gravitropism and microgravity architecture: no panel, no mechanic and no
registered question until NASA GeneLab measurements set the architecture
(`docs/ROADMAP.md:110-112`).
**Inputs and anchors.** Tree mass; head count; element table. Spine item 1: comet
organic-C-rich ~50% by mass, Ca-depleted, P present, K unmeasured
(`docs/ROADMAP.md:95-98`; `docs/prior_art_2026-09-01.md` §3). K, human O2 demand, tissue
stoichiometry and the ~1e12 kg comet mass: all UNGROUNDED, needs a source. Size M.

### Cards inside Q4's page

Two static cards under the readout panel, no new inputs.

- **Shield.** The `p*` wall at 1 AU and 10 km is 5.4 to 18.0 m of ice (§3 shell law;
  5.6 to 18.6 m at normal incidence, `§13:1054-1058`);
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
asserts every row names an input that exists and, SEMANTICALLY rather than by name (round-5
audit: a name test cannot tell a comparator registered as an input from an input), that
the set of comparators {`T_freeze`, `f_floor`, `σ`, `p_sat`, 0} a card's input can move is
exactly {`T_freeze`} for the antifreeze card and empty for every other; a second
asserts every MEASURED row's source resolves to a file:line in this repo. **Third rule:
after any card is played, each registered binding is still FIRST violated at a reachable
auto-path state inside its registered box** (FREEZE: `R` 10 km, `r` in [1.19, 1.27] AU,
every sigma; OPAQUE: `r` 1.10 AU, sigma 0.7 MPa, `R` in [60, 300] km; §6). BURST, BOIL
and STARVE are not registered (§4, §6): the first two stay manual-gesture failures and no
card may remove their manual door; STARVE stays a displayed margin and no card may make it
undisplayable (`r_d` keeps a floor above zero, since `respiration(0, T) = 0`,
`sim/physiology.py:54`). A VIOLATED cell somewhere on the page grid (r to 100 AU, t to
1 km) does not satisfy the rule, because an extreme slider always supplies one. **And
every failure must remain REACHABLE inside the page's slider ranges** (`R` 10 m to
100 km, `r` 0.5 to 100 AU, `t` 0.01 m to 1 km, §5): a card that leaves a line violable
only past the end of a slider has removed it from the page. The number that fixed this
rule: at 1.10 AU and σ 0.7 the auto-path OPAQUE crossing sits inside the 100 km slider
only for `f_floor ≥ 0.2461`; at 0.161 it is at 299.5 km there, 174.0 km even at 1.04 AU,
723.2 km at 1.20 AU and 770.4 km at σ 3.1 / 1.04 AU, nowhere the visitor can drag. **The
per-card test quantifies over the card's whole reach, not one played value:** for a card
that sets a value, that value; for a card that enables a range, BOTH endpoints; for cards
that stack, the maximum playable stack; for each, it runs the auto path across each box
and asserts the named line is the first to flip inside it and still flips inside the
slider ranges. A range whose endpoint fails is CLIPPED at the last passing value and the
clip is printed. **There is no `f_floor` card** (round-4 audit): `f_floor` is OPAQUE's
right-hand side, and §3 names `T_freeze` as the only comparator the deck may move; the
round-3 draft admitted an `f_floor` card reaching 0.161 to 0.293, which contradicted §3
and defined its clips from the very box it was then tested against. `f_floor` stays a
declared input under the assumptions disclosure, swept by Q4's arms, not dealt from the
deck. **Worked failing
example:** antifreeze at `dT_sc = 5 K` moves the R = 10 km FREEZE edge to 1.2631 /
1.2894 / 1.3141 AU for sigma 0.7 / 1.5 / 3.1 (edge wall at `p_sat(-5 °C)` = 421.8 Pa);
two of three leave the box, prediction 1's binding changes, and the card FAILS, even
though FREEZE still violates on the page grid (the `tau = 1` edge moves only to
1.523 AU). **Worked stacking example:** two antifreeze cards at 0.8 K each pass alone
(edges 1.2140 / 1.2395 / 1.2636) and fail together (1.6 K: 1.2231 / 1.2488 / 1.2730, the
sigma 3.1 edge outside 1.27), so the cap below is on the TOTAL.

### Material table (wall rows)

Each row is a `(sigma, k(lambda) or opacity, density, anchor)` tuple the wall-material
input can take. Ice is the only MEASURED row (§3); every other number below is
UNGROUNDED, needs a source, until the CrossRef chain has run. **Every `sigma` or `k` row
must keep OPAQUE first-violated inside prediction 2's box and FREEZE inside prediction
1's, and BURST reachable by the manual `p` gesture** (the third rule): `k` is floored
where the auto-path `f_photon(t_min)` still crosses `f_floor` at an `R` in [60, 300] km
at 1.10 AU; `sigma` is capped where that crossing still occurs before any other line
flips and the R = 10 km FREEZE edge stays inside [1.19, 1.27] AU. A row that cannot
satisfy all three ships DECLARED with its range clipped and the clip printed.

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
`sim/vessel.py` and never an inequality's comparator by the back door: the antifreeze
card moves the interior freezing point `T_freeze` (§3, a material input of the interior
water, default 273.15 K) down by `dT_sc` [0 K default, declared, disclosed], and FREEZE
reads `T_int < T_freeze` as it always does; writing the card as an offset on the 273.15
literal would move the inequality's right-hand side, which the tier rule forbids. The
TOTAL `dT_sc` across every antifreeze card played is capped at 1.3 K: the sigma 3.1 MPa
edge reaches the box top of 1.27 AU at `dT_sc` = 1.343 K (0.7 MPa: 5.57 K; 1.5 MPa:
3.39 K), so at 1.3 K the edges are 1.2197 / 1.2453 / 1.2695 and any larger total fails
the third rule. **The 1.3 K cap is a DECK-TEST CONSTANT**, derived from prediction 1's
box and protecting only the third rule: DECLARED cards are excluded from registered runs
(above), so the cap never touches Q4's registered numbers, and it moves if the box does.
Respiration cards move `r_d` down to a tenth of its value (0.024; the
P2-window STARVE margin moves +3.11 to +3.20), never to zero.

| card                        | stolen from                   | input it moves                                                                                                                            | anchor       |
| --------------------------- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------------ |
| antifreeze proteins         | fish, insects                 | `T_freeze` down by `dT_sc`, 1.3 K total cap across stacked cards; real proteins give a few K, so the card is clipped and the clip printed | DEMONSTRATED |
| reduced dark respiration    | none named                    | `r_d`, down to 0.024, never zero                                                                                                          | DECLARED     |
| Dsup + desiccation proteins | tardigrade                    | the dormancy-vs-radiation budget (§11 ch.4, ch.5)                                                                                         | DEMONSTRATED |
| DNA repair                  | Deinococcus radiodurans       | the same budget, the repair term                                                                                                          | DEMONSTRATED |
| CAM + desert cuticle        | cacti, agaves                 | leaf-scale water loss in vacuum (§11 ch.1)                                                                                                | DEMONSTRATED |
| UV screens                  | Arabidopsis flavonoid mutants | the seed's UV term; note the EXPOSE-E screen mutants did WORSE than wild type                                                             | DEMONSTRATED |
| chemosynthetic symbionts    | tube-worm bacteria            | a dark-side carbon source: O2 banked at perihelion, burned with comet organics at aphelion (§11 ch.3); a redox budget with real inputs    | DECLARED     |
| radiotrophic melanin        | Chernobyl fungi               | a cosmic-ray energy term; the literature claim is contested and the card says so                                                          | DECLARED     |

**One thing plants already do that reads as fiction.** Xylem pulls water at about
-2 MPa, below absolute zero pressure; a tree already operates past vacuum. This goes on
the landing page as the reason a plant, not an animal, is the organism. UNGROUNDED,
needs a source, before it ships.

**Non-goals for the tier.** No genome, no evolution of cards, no cost currency beyond the
carbon budget the model has; a "cost" is carbon or mass charged to the existing inequalities.

**Milestone.** The deck ships after M2 and before M3, as M2b (S): the table, the three
tests, and the badge, with only the antifreeze (`T_freeze` via `dT_sc`) and reduced-respiration (`r_d`)
rows live, since every other row moves an input that does not exist until its chapter
(§11 ch.1, 3, 4, 5); those rows ship with their chapters and the row test runs against
the inputs present at each ship. Bioluminescence moved no input and is dropped. No card may be MEASURED until its number is in `bio_grounding`.

## Round 4 responses

Verified audit table: 13 codex findings + 4 verifier findings, none refuted. Every number
below was recomputed this session (`v4_rev7_fresnel.py`, `v4_gridscan.py` rerun) and
matched the verifier's digits; the registered rows were unchanged.

1. **Disk average reused as local irradiance (MAJOR).** FIXED, §3: `f_photon` is declared
   the projected-disk average; interior mixing is the seventh declared input
   (`interior = mixed`); the `central` variant is a labelled row (P2 119.3 km, in band).
2. **No Fresnel, "consistent with albedo 0" (MAJOR).** FIXED, §3, §5, §6: the phrase is
   gone; R(normal) 0.0180 and R̄ 0.0627 stated; Fresnel arm registered for both
   predictions with expected outcomes (P1 1.1886 / 1.2116 / 1.2334 and 1.1507 / 1.1730 /
   1.1941 AU; P2 OPAQUE 75.8 km, and FREEZE 70.8 km before OPAQUE 104.3 km); the page
   prints 0.063 beside 0.072. Decision (a): the declared law stays the registration.
3. **O(t/R) effects unbounded (NIT).** FIXED, §3: t/R ≤ 4.4e-4, edge shift < 1e-5 AU.
4. **Rows reproduce only with sources outside the checkout (MINOR).** FIXED, §6, §8:
   stated; the regeneration test skips without the sources.
5. **§4 numbers not from the registered grid (MAJOR).** FIXED, §4: 59,691 states,
   STARVE-first 0 / 0, min margin +1.826 / +1.874, f_photon minimum 0.0579 / 0.0667,
   1 AU / 10 km / σ 0.7 = 294.37 K / 0.391 / +9.12, 1993.6 labelled pre-wall with
   I_wall 1660.1.
6. **273.15 K / 611.21 Pa below the triple point (NIT).** FIXED, §4: labelled a
   metastable-liquid convention, edge shift 1.1e-4 AU.
7. **Not reproducible from the checkout; mutable `main` URL (MAJOR).** FIXED, §6, §8:
   pvlib commit `2d0ed71e1308293b3081979404f8e90f2f2dde1e` pinned in the spec and
   scheduled for `docs/THIRD-PARTY.md:35` in M1a0; `test_reproduce_hand_rows` stated to
   be unable to catch a wrong table; `test_regenerate_spectral_table` added, SKIP not
   PASS when sources are absent.
8. **Prereg chronology; edge-rule ties (MINOR).** FIXED, §6, §8: `prereg.yaml` alone,
   one commit before `q4_hand_rows.py`, pinned by the ancestor test; tie clause added.
9. **Mode table prints raw σ (MINOR).** FIXED, §4, §5: every BURST cell reads
   `σ_eff(T_shell)`; r = 1.00 AU worked example; Q4's question no longer asks about
   strength on the path where it is an identity.
10. **Checks that cannot fail (MINOR).** FIXED for the two real ones, §6, §12: the
    no-literal test is renamed a smell test with its evasions named; the `f_floor` clip
    circularity is moot because the card is struck. The three already-disclosed ones
    (Gate B identity, table digest as pin, 882 Pa regression control) are unchanged, as
    the verifier found them disclosed.
11. **`f_floor` card unreachable on the slider; 1.3 K cap load-bearing only for the deck
    (MAJOR).** FIXED, §12: card struck; "reachable inside the slider ranges" added to the
    third rule with the numbers (f_floor ≥ 0.2461 for OPAQUE inside 100 km at 1.10 AU /
    σ 0.7); the cap labelled a deck-test constant.
12. **Sampled citations accurate (NIT).** No change.
13. **Executor could implement σ = 0 only on the auto path (MINOR).** FIXED, §5, §8: the
    mode-agnostic invariant is written in §5 and is an M1a test.
14. **N1, spec contradicts itself on which comparator a card may move (MAJOR).** FIXED,
    §12: the `f_floor` card is struck; §3's rule stands.
15. **N2, Fresnel flips P2's binding (MAJOR).** FIXED, §6: the arm is registered for both
    predictions, binding included; the flip is its expected outcome.
16. **N3, two more stale §4 numbers (MINOR).** FIXED, §4, with finding 5.
17. **N4, verifier's scan sizes copied as the spec's grid (NIT).** FIXED, §4, §10: the
    3,900 / 7,722 are named as the reproduction script's sizes and replaced by the
    registered 59,691; the round-3 banner is left as history.

## Round 5 responses

Verified audit table: 16 codex findings (5 confirmed, 11 partial, none wholly refuted; three
sub-claims refuted) + 4 verifier findings. The verifier reproduced every registered, control
and variant digit from the pinned sources (md5 b31870bd / cf5f76d5); the new arm rows below
were computed this revision (`v5_slab.py`, the verifier's script extended) before they were
written down. The registered rows are unchanged.

1. **"ice→interior, reciprocal, equal" holds only for a vacuum interior (MAJOR).** FIXED,
   §3, §5, §6, §8: `n_interior ∈ {vapour 1.000, water 1.333}` is an explicit arm input with
   vapour as the default and the reason stated; P1 (i) water 1.1954 / 1.2194 / 1.2421 AU, all
   inside the band, is a registered expected outcome beside the vapour row.
2. **`(1−R̄)(1+T)` is not energy-conserving; first-surface R̄ used as the albedo (MAJOR).**
   FIXED, §3, §6: variant (ii) scales `T_eq` by `(1 − R_slab_sw(t))^¼` of the wall in force,
   `R_slab + T = 1` at `k·t = 0` is an M1a test, and the rows are recomputed: P1 (ii) 1.1430 /
   1.1637 / 1.1831 (vapour) and 1.1573 / 1.1805 / 1.2025 (water); P2 (ii) FREEZE 57.1 before
   OPAQUE 108.3 km (vapour, below the band) and 86.0 before 115.6 km (water). SUPERSEDED in
   round 6 (finding 1): that balance lost the `R·T` term; the rows are now §6's. The refuted
   sub-claim (`I_wall` double-counted) is answered in §6: `I_wall` is not scaled again.
3. **Arm digits reproduce (NIT).** No change beyond 1-2.
4. **Question phrased without the law (MINOR).** FIXED, §6: "under the declared law of §3".
5. **Isothermal shell undeclared (MINOR).** FIXED, §3: stated where `T_shell = T_eq` is
   written, §17's gradient-wall reading excluded, a registry row.
6. **"Seven" incomplete (MINOR).** FIXED, §3, §6, §8: the count is gone; a registry table
   with eleven rows is the list and `prereg.yaml` copies it.
7. **`interior = mixed` (NIT).** No change; §3 already names the thermal core as the
   interior water.
8. **Tie rule can report an edge after the window closed (MAJOR).** FIXED, §6, §8: every
   registered line's margin is bisected in the bracket, the smallest root is the edge and its
   line the binding; load order only within one tolerance; the failing case is an M1a test.
9. **Import guard one-way (MINOR).** FIXED, §6: bidirectional, with a file-read half and a
   negative case per direction.
10. **Byte-identity unspecified (MINOR).** FIXED, §6: the producer pins `%.10e` and `\n`;
    the assertion compares parsed values at rtol 1e-12; the md5 is provenance.
11. **Spectral numbers "unreproducible" (NIT).** No change; every one reproduced from the
    pinned sources. The two stale digits found instead are NEW-1 and NEW-2.
12. **Census "does not follow" (NIT).** Refuted by the verifier (STARVE-first 0 with the
    load order entails it; 41,968 / 41,796 reproduced, 0 / 0 at `T_int ≥ 273.15`). No change
    to the numbers; the producer is NEW-3.
13. **Chemosynthesis card defeats OPAQUE; `T_freeze` rename (MINOR).** First half refuted
    (OPAQUE is `f_photon < f_floor`, and every OPAQUE-first cell already has STARVE holding).
    Second half FIXED, §12: the comparator test is semantic, not name-based.
14. **§2 claims (NIT).** Every sampled file:line PASSED; `docs/THIRD-PARTY.md:35` IS the
    `main` URL, so the spec's claim is true and its pin stays an M1a0 task. The one NIT
    FIXED, §2: `build_site.sh` copies three web files, then both licences and `.nojekyll`.
15. **Survivors (NIT).** Folded into 9, 10, 13.
16. **One `shell+fresnel` value for two incompatible variants (MAJOR).** FIXED, §5, §8: three
    arguments (`optical_law`, `n_interior`, `thermal_reflectance`), a three-way page toggle,
    and `prereg.yaml` names the triple on every arm row.
17. **NEW-1, 0.2103 is the normal-incidence value (MINOR).** FIXED, §4: 0.1931, the old digit
    labelled.
18. **NEW-2, rim sampled at ρ/R = 0.99 (NIT).** FIXED, §3: 0.2245 at the rim, 0.2259 at 0.99.
19. **NEW-3, §4 census has no in-repo producer (MINOR).** FIXED, §8: `q4_hand_rows.py`
    prints the census and `test_reproduce_hand_rows` covers it.
20. **NEW-4, first-surface albedo printed where the slab value belongs (MINOR).** FIXED, §5:
    the page prints `R_slab_sw(t)` of the wall in force for the chosen `n_interior`, and the
    reason 0.063 is not printed is stated.

## Round 6 responses

Codex, 6 findings (`~/.cache/llm-panel/runs/dyson-tree-6e0926de3dc8/20260922-205412-2638298/codex.md`); arm digits from `v7_slab.py` (`v7_slab.out`). User approved: fix, then prereg, no further round.

1. **Arm (ii) balance loses transmitted energy (BLOCKER).** FIXED, §3, §6: `T_shell⁴ = (1 − R_slab_sw)·T_eq⁴`, `T_int⁴ = (1 − R_slab_sw + T_sw)·T_eq⁴`; P1 (ii) 1.1540 / 1.1766 / 1.1980 (vapour), 1.1668 / 1.1914 / 1.2146 (water); P2 (ii) vapour FREEZE 78.4 before OPAQUE 102.3 km, water OPAQUE 109.8 before FREEZE 111.6 km.
2. **Tie clause not executable (BLOCKER).** FIXED, §6: candidates are the lines that change sign in the bracket; later roots are counterfactual. The P2 (ii) water row is its live case.
3. **Registry omits the solar tail; key and signature unnamed (MAJOR).** FIXED, §3, §6, §8: twelfth row `solar_tail_transmission`, key `optical_law`, keyword signatures in `sim/vessel.py`.
4. **Prereg guards partial (MAJOR).** FIXED, §6, §8: whole-structure `test_prereg_equals_spec`, "ancestor of HEAD" dropped, `pytest -m slow` in the acceptance, hand rows cherry-picked onto the prereg.
5. **Registered rows and census reproduce (NIT).** No change.
6. **Five stale file:line claims (MINOR).** FIXED, §6, §8: THIRD-PARTY pinned, parsed-value equality, `extract_ice_k.py:37` and `--table`, census test described as it exists.
