# Executor brief: dyson M2, the verdict (inputs + readout panel, no picture).

Repo `/home/<user>/dyson-tree`, master `ae449d6`. Authority: spec §8 M2 bullet
(`docs/superpowers/specs/2026-09-12-northstar-design.md`, "M2 (M): the verdict"), §4 (lines, margins,
modes), §5 (defaults, (p, t) modes, page prints R_slab_sw live), §6. Read fresh; spec wins.

- The seven inputs and the readout panel on the page, driven ONLY by `DysonModel` (web/model.js, M1b):
  each line FREEZE / STARVE / OPAQUE / BURST / BOIL with HOLD/VIOLATED and its printed margin; manual
  p and t modes per §5.
- Acceptance (node test driving the built page + real-browser smoke): defaults → FREEZE, STARVE, OPAQUE
  HOLD with positive margins, BURST and BOIL margin 0 by construction; drag r past the registered r_close
  at R = 10 km → exactly one line flips, FREEZE; manual p > p* → exactly BURST; manual p < p_sat →
  exactly BOIL; manual t = 100 m at defaults → exactly OPAQUE.
- Speed: M1b measured rClose/rWindow at 1–4 s per call in JS. The panel must stay responsive on input
  (no edge search on every slider tick — debounce or compute edges only where the spec requires them);
  report measured input-to-readout latency in Chromium.
- Branch `m2-verdict`; no push/merge; no attribution; prereg md5 d8707a66 unchanged; tests seen failing
  first; `pytest -q`, `-m slow`, `tools/smoke_page.py` green; keep a11y (labels, live region).
  Final report: SHAs, counts, latency, the five acceptance readouts, mismatches.
