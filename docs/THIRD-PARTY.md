# Third-party material

This repository redistributes no third-party data file. Every external table
below is FETCHED by the tool that uses it, from the address recorded in that
tool's header comment, and is left untracked. That is deliberate: a fetch
command in the source is reproducible and carries no redistribution question.

## Ice optical constants — Warren & Brandt (2008)

- **Used by:** `tools/extract_ice_k.py` (and, at one remove,
  `tools/check_wall_phase.py`, `tools/check_s3_scattering.py`,
  `tools/size_par_filter.py`), grounding `docs/bio_grounding_2026-09-02.md` §9.
- **File:** `IOP_2008_ASCIItable.dat`, 487 lines, fetched from
  <https://atmos.uw.edu/ice_optical_constants/IOP_2008_ASCIItable.dat>
- **Citation:** Warren, S. G., and R. E. Brandt (2008), Optical constants of ice
  from the ultraviolet to the microwave: A revised compilation,
  *J. Geophys. Res.*, 113, D14220, doi:10.1029/2007JD009744.
- **Terms, as found on the host page** (<https://atmos.uw.edu/ice_optical_constants/>,
  read 2026-09-10): the page carries **no licence, no copyright notice, no
  permission statement and no citation request**. It gives the reference above, a
  funding acknowledgment ("This research was supported by the National Science
  Foundation under grants ANT-00-03826 and OPP-06-36993"), a description of the
  data set and its wavelength-by-wavelength provenance, and the download link.
  That is the whole of what the page says. Because it grants no redistribution
  rights, none are assumed: the file is fetched by the tool, not vendored here.
  The paper itself is paywalled; **the data table is what was used, and the paper
  was not.**

## Reference solar spectra — ASTM G173-03

- **Used by:** `tools/check_greenhouse_transparency.py`,
  `tools/check_s3_scattering.py`, `tools/size_par_filter.py`, grounding the
  `PAR_FRACTION = 0.3879` correction in `docs/bio_grounding_2026-09-02.md` §12.
- **File:** `ASTMG173.csv`, fetched from the pvlib-python project at
  <https://raw.githubusercontent.com/pvlib/pvlib-python/2d0ed71e1308293b3081979404f8e90f2f2dde1e/pvlib/data/ASTMG173.csv>
- **Citation:** ASTM G173-03(2020), *Standard Tables for Reference Solar
  Spectral Irradiances: Direct Normal and Hemispherical on 37° Tilted Surface*,
  ASTM International. The underlying reference spectra are distributed by NREL.
- **Terms:** pvlib-python is BSD-3-Clause licensed; the tabulated reference
  spectra it ships originate with NREL/ASTM. The ASTM standard document itself
  is copyrighted and is NOT included here.

## Wood Handbook figures — Forest Products Laboratory (2010)

- **Used by:** `docs/bio_grounding_2026-09-02.md` §7 (modulus-of-rupture values
  across 111 species-rows) and `docs/prior_art_2026-09-01.md`.
- **Citation:** Forest Products Laboratory (2010), *Wood Handbook — Wood as an
  Engineering Material*, Centennial Edition, General Technical Report
  FPL-GTR-190, Madison, WI: U.S. Department of Agriculture, Forest Service,
  Forest Products Laboratory, 508 p.
- **Terms:** **Public domain** as a work of the U.S. federal government. It has
  no DOI and so is not ghostcite-checkable; its identity was verified from the
  PDF's own embedded metadata (title, author "USDA Forest Service", and a full
  self-citation in the subject field).

## Ice tensile strength — Petrovic (2003), via Hirata (2022)

- **Used by:** `docs/bio_grounding_2026-09-02.md` §10.
- **Terms:** Reached through a green open-access copy at one remove; the value
  (0.7–3.1 MPa) is quoted, the source document is not redistributed.

## Software dependencies

`numpy` (BSD-3-Clause), `scipy` (BSD-3-Clause), `PyYAML` (MIT), `pytest` (MIT),
`ruff` (MIT), and — for `tools/smoke_page.py` only — `playwright` (Apache-2.0).
The published page (`site/`) bundles **no** third-party code: the plot is
hand-drawn SVG, there is no framework, no build step and no CDN request.
