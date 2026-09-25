# Dyson page visual-first rebuild — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild `web/index.html`'s vessel section around a large distance × radius "which line fails first" map linked to the vessel picture, so a reader gets the test and the result at a glance.

**Architecture:** An offline node tool computes the map on a log grid with the page's own `web/model.js` (`autoState`), for each σ × organism with no cards, and writes `web/map_data.js` with provenance. `web/mapview.js` draws it as SVG with the registered P1/P2 bands and the current design dot; clicking sets the r/R sliders. When a deck card or an advanced input makes the precomputed slice not apply, a Web Worker (`web/map_worker.js`) recomputes progressively (coarse → fine) with the same pure function. The five-line table becomes headroom bars; deck cards become tokens; prose moves into `<details>`.

**Tech Stack:** plain JS (no framework, no build step beyond `tools/build_site.sh`), SVG, Web Worker, pytest + node drivers, Playwright smoke (`tools/smoke_page.py`).

**Spec:** grill ledger `~/.claude/projects/-home-mjarnold/memory/grill_visual_redesign_dyson_pollen_2026-09-25.md` (decisions Q1–Q7, A1–A16).

## Global Constraints

- No change to any model number, verdict rule, prereg, or `web/model.js` math (A2, A8). JS↔Python parity stays 1e-15.
- Every visual encodes only model output (A4); a map cell's colour is `autoState(...).report.violated[0]` or `HELD`, or the explicit class `NO_DESIGN` when `autoState` throws `RunnerError` — never interpolated, never guessed.
- Pre-registered bands (P1 [1.19, 1.27] AU at R 10 km; P2 [60, 300] km at r 1.10 AU, σ 0.7) and every DECLARED label stay always visible (Q2 premise).
- Keep every existing element id that tests read (`v-status-*`, `v-margin-*`, `v-cmp-*`, `v-summary`, `v-rauto`, `v-Rwin`, `deck-*`, `pic-*`, `q4-band`); restyle them, don't remove them.
- Plain SVG/Canvas + Web Worker only; all assets relative (build_site.sh rejects remote assets).
- Leak-guard: no `/home/mjarnold` or `/mnt/c/Users/a2b32` in tracked files.
- Headless browsers: default Playwright launch only (software rendering); never `--enable-gpu`/d3d12 on this laptop (memory `laptop_tdr_0x116_wsl_webgl_2026-09-25`).
- Every new test is seen failing for its stated reason before its fix; every negative check carries a positive control.
- Visual output passes an independent critic agent before merge (A3); plus the blind 10-second before/after test (Q2).

## Review Focus

1. **Map cell where the auto design throws** (auto-path BURST/BOIL) — must render as `NO_DESIGN` with its own legend entry, never as a failure class; test in Task 1.
2. **Current design outside the grid** (slider extremes r 0.5 / 100 AU, R 10 m / 100 km are the grid corners) — dot clamps visibly to the edge with a marker, not silently off-map; test in Task 2.
3. **A card played mid-recompute, then removed** — the stale worker result must never paint over the precomputed slice; test in Task 3 (generation counter).
4. **Advanced inputs changed** (f_floor, emissivity, Fresnel…) — precomputed slice no longer applies; map must say so and recompute, never show the no-card slice as if current; test in Task 3.
5. **Slider-range sweep** — every new picture (map, bars) draws in all states of `test_picture_draws_across_the_slider_range`; extend it in Task 5.

---

### Task 1: Offline map precompute with provenance

**Files:**
- Create: `tools/make_map.mjs`
- Create (generated, committed): `web/map_data.js`
- Test: `tests/test_map_data.py`

**Interfaces:**
- Produces: `window.DysonMap = { grid: {r_log10: [lo, hi, n], R_log10: [lo, hi, n]}, classes: ["HELD","BURST","FREEZE","BOIL","STARVE","OPAQUE","NO_DESIGN"], slices: {"<sigma_MPa>|<org>": "<string of n_r*n_R class indices, row-major r outer>"}, provenance: {git_sha, model_js_sha256, spectral_table_js_sha256, written, runtime_s} }`
- Produces: `export function mapCell(M, r, R_m, sigma_Pa, org, inputs)` returning a class name (shared by Task 3's worker).

Grid: `r_log10` = [-0.3011, 2, 80] (the v-r slider range), `R_log10` = [1, 5, 60] (v-R slider, metres), σ ∈ {0.7, 1.5, 3.1} MPa, org ∈ {algal, vascular}. Cost measured 2026-09-25: 44 ms/cell ⇒ 28,800 cells ≈ 21 min — run via `heavy-run` or jobd, not bare bash.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_map_data.py
import hashlib, json, re, shutil, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]

def load():
    src = (ROOT / "web" / "map_data.js").read_text()
    m = re.search(r"window\.DysonMap = (\{.*\});\s*$", src, re.S)
    assert m, "web/map_data.js has no window.DysonMap literal"
    return json.loads(m.group(1))

def test_provenance_pins_the_model_that_made_it():
    d = load()
    for f, key in (("model.js", "model_js_sha256"), ("spectral_table.js", "spectral_table_js_sha256")):
        assert hashlib.sha256((ROOT / "web" / f).read_bytes()).hexdigest() == d["provenance"][key], f
    anc = subprocess.run(["git", "merge-base", "--is-ancestor", d["provenance"]["git_sha"], "HEAD"], cwd=ROOT)
    assert anc.returncode == 0, "map git_sha is not an ancestor of HEAD"

def test_every_slice_is_complete_and_uses_known_classes():
    d = load(); nr = d["grid"]["r_log10"][2]; nR = d["grid"]["R_log10"][2]
    assert set(d["slices"]) == {f"{s}|{o}" for s in ("0.7", "1.5", "3.1") for o in ("algal", "vascular")}
    for k, s in d["slices"].items():
        assert len(s) == nr * nR, k
        assert set(s) <= set(str(i) for i in range(len(d["classes"]))), k

def test_sampled_cells_equal_the_live_model():
    # positive control: recompute 12 cells (incl. a P1-band cell and a NO_DESIGN cell if present) live
    node = shutil.which("node"); assert node, "node required; fails rather than skips"
    out = subprocess.run([node, str(ROOT / "tools" / "make_map.mjs"), "--check", "12"], cwd=ROOT,
                         capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checked"] == 12 and res["mismatches"] == [], res
    assert "HELD" in res["classes_seen"], res   # the sample reached the window
```

- [ ] **Step 2: Run it — expect FAIL** (`web/map_data.js` missing): `python -m pytest -q tests/test_map_data.py`

- [ ] **Step 3: Implement `tools/make_map.mjs`**

```js
// tools/make_map.mjs — the distance × radius first-failure map, computed with the page's own
// web/model.js so the map and the live verdict cannot disagree. Usage:
//   node tools/make_map.mjs              → writes web/map_data.js (≈21 min; run under heavy-run)
//   node tools/make_map.mjs --check N    → recompute N cells live, compare to web/map_data.js, print JSON
import fs from "node:fs"; import vm from "node:vm"; import crypto from "node:crypto";
import { execSync } from "node:child_process";
const W = new URL("../web/", import.meta.url);
const GRID = { r_log10: [-0.3011, 2, 80], R_log10: [1, 5, 60] };
const SIGMAS = ["0.7", "1.5", "3.1"], ORGS = ["algal", "vascular"];
const CLASSES = ["HELD", "BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE", "NO_DESIGN"];
export function loadModel() {
  const ctx = { console }; ctx.window = ctx; vm.createContext(ctx);
  for (const f of ["spectral_table.js", "model.js"]) vm.runInContext(fs.readFileSync(new URL(f, W), "utf8"), ctx);
  return ctx.DysonModel;
}
export function mapCell(M, r, R_m, sigma_Pa, org, inputs) {
  try {
    const st = M.autoState(r, R_m, sigma_Pa, M.PRESETS[org] ?? org, inputs ?? M.REGISTERED);
    return st.report.violated[0] ?? "HELD";
  } catch (e) {
    if (e && e.name === "RunnerError") return "NO_DESIGN";
    throw e; // fail loud: any other error is a bug, not a map class
  }
}
export const axis = ([lo, hi, n], i) => Math.pow(10, lo + ((hi - lo) * i) / (n - 1));
```

Then `main()`: build every slice row-major (r outer, R inner) into a string of class indices; write `web/map_data.js` as `// GENERATED by tools/make_map.mjs; do not edit.\nwindow.DysonMap = <JSON>;\n` with provenance (`git rev-parse HEAD`, sha256 of `web/model.js` and `web/spectral_table.js`, ISO time, runtime). `--check N`: pick N cells deterministically (every ⌊total/N⌋-th cell across all slices, plus the cell nearest r 1.20 AU / R 10 km σ 0.7 algal), recompute, print `{checked, mismatches, classes_seen}`. Confirm `M.autoState`, `M.PRESETS`, `M.REGISTERED` are in the API (`web/model.js:1022-1062`); if `REGISTERED` or `autoState` is not exported, add them to the `API` object only — no math change.

- [ ] **Step 4: Generate** — `HEAVY_RUN_MEM=4G heavy-run node tools/make_map.mjs` (commit first so `git_sha` is an ancestor; re-stamp after rebases as in M4).
- [ ] **Step 5: Run the test — expect PASS.** Then seen-failing control: flip one character of one slice in `web/map_data.js`, confirm `test_sampled_cells_equal_the_live_model` or the sha test fails for that reason, restore.
- [ ] **Step 6: Add `map_data.js` to `tools/build_site.sh`'s copy list and a `<script src="./map_data.js">` before `verdict.js`; commit.**

### Task 2: Map view linked to the vessel

**Files:**
- Create: `web/mapview.js`
- Modify: `web/index.html` (vessel section grid), `web/verdict.js` (call `MapView.draw` on each render; wire click → sliders)
- Test: `tests/test_site_map.py` (node driver like `tests/test_site_verdict.py`'s `DRIVER`), `tools/smoke_page.py` (new checks)

**Interfaces:**
- Consumes: `window.DysonMap`, `mapCell` class names (Task 1).
- Produces: `window.DysonMapView = { draw(svg, state, slice), cellAt(r_au, R_m) -> {i, j}, onPick(fn) }` where `state = {r, R, sigma_MPa, org, cardsPlayed, advancedChanged}` and `slice` is a class string or `null` (recomputing).

Draw: SVG `#map`, x = log r (AU), y = log R (km labels), one rect per cell coloured by class using the failure palette already used by the picture (`web/picture.js` FAIL colours; FREEZE blue, OPAQUE dark grey, HELD green, NO_DESIGN hatched light grey with its own legend entry). Overlay: P1 band (x 1.19–1.27 AU at R 10 km row), P2 band (y 60–300 km at r 1.10 AU, drawn only on σ 0.7 slices), and the current design dot with crosshair. Click/drag on the map sets `#v-r` and `#v-R` values (snapped to their step grid, as in `610ed8f`) and fires `input`/`change`.

- [ ] **Step 1: failing tests** — in `tests/test_site_map.py`: (a) at defaults the `#map` has 80×60 cells and the cell under the dot has the class the verdict summary names (`HELD` ↔ "alive: every line holds"); (b) positive/negative pair: at R 10 km, r 1.21 AU (σ 0.7) the dot's cell is FREEZE and the verdict names FREEZE; at r 1.20 it is HELD; (c) the dot at slider extremes sits on the map edge (`data-clamped="true"`); (d) the P2 band element exists on σ 0.7 and not on σ 1.5.
- [ ] **Step 2: run — expect FAIL (no `#map`).**
- [ ] **Step 3: implement `web/mapview.js` + layout** (map ~60% width left, vessel right, headroom strip under vessel — Task 4 fills it).
- [ ] **Step 4: tests PASS; smoke additions**: map visible, text ≥ 12 px, click at a HELD cell turns the summary to "alive", click at a FREEZE cell turns it to FREEZE (real browser, both directions). Seen failing with the click handler disabled.
- [ ] **Step 5: commit.**

### Task 3: Live recompute in a worker when cards or advanced inputs change

**Files:**
- Create: `web/map_worker.js`
- Modify: `web/verdict.js` (decide precomputed vs worker; generation counter), `tools/build_site.sh`
- Test: `tests/test_map_worker.py`

**Interfaces:**
- Consumes: `mapCell` logic — the worker `importScripts("spectral_table.js", "model.js", "deck.js")` and evaluates the same function body (copy `mapCell` verbatim into `web/map_worker.js` and add a test asserting the two function sources are identical after whitespace normalisation, so they cannot drift).
- Produces: worker messages `{gen, level, slice}` where `level` ∈ {12×8, 40×30, 80×60}; page ignores any `gen` older than the latest request.

Rule: precomputed slice applies iff no card played AND every advanced input equals its default (`web/verdict.js` DEFAULTS). Otherwise the map shows a "recomputing for your design" label, greys the precomputed slice, and paints worker levels as they arrive.

- [ ] **Step 1: failing tests** — (a) worker function source == `tools/make_map.mjs` `mapCell` source; (b) driving the worker's compute in node for the no-card case at 12×8 equals the precomputed slice subsampled at the same cells (positive control); (c) with antifreeze 1.3 K at σ 0.7 algal, the cell r 1.21 AU / R 10 km flips FREEZE → HELD (the M2b-registered shift to 1.2197); (d) stale-result rule: post gen 1 (card on), then gen 2 (card off) — a late gen-1 message is ignored and the precomputed slice stays.
- [ ] **Step 2–4: FAIL → implement → PASS; commit.**

### Task 4: Headroom bars, card tokens, collapsible prose

**Files:**
- Modify: `web/index.html`, `web/verdict.js` (`lineText` output feeds bars; ids kept), `web/deck.js` (token markup), CSS in `web/index.html`
- Test: `tests/test_site_verdict.py` (existing assertions must keep passing unchanged), `tools/smoke_page.py`

Bars: one row per line in load order; bar length = margin normalised by that line's scale (BURST σ_eff, FREEZE 10 K, BOIL p_sat, STARVE a_max, OPAQUE f_floor) — state the normaliser in the row's title so the length is honest; binding/violated row highlighted; the existing `v-cmp-*`/`v-margin-*` text stays in the row (visible on hover/focus and to screen readers). Tokens: badge + trait + one-line effect; source/cost/cap inside `<details>`. Prose ("what this is / is not", declared assumptions, provenance) into `<details>`; P1/P2 bands and DECLARED badges stay outside any `<details>`.

- [ ] **Step 1: failing smoke checks** — bars exist for 5 lines, violated bar carries `data-violated`, DECLARED badge visible without opening anything, the bands' labels visible without interaction.
- [ ] **Step 2–4: FAIL → implement → PASS (existing 321 pytest + smoke unchanged); commit.**

### Task 5: Range sweep, blind test, critic, merge

**Files:**
- Modify: `tests/test_site_verdict.py` (`SWEEP` states also assert `#map` drawn and 5 bars present)
- Create: `docs/superpowers/briefs/2026-09-25-visual-blind-test.md` (the before/after answers)

- [ ] **Step 1:** extend the sweep test; seen failing by breaking `MapView.draw` for one state.
- [ ] **Step 2:** full `pytest -q`, rebuild, `python tools/smoke_page.py` — all green.
- [ ] **Step 3: blind 10-second test** — screenshot today's live page and the new build at 1400×900 (viewport only, as a reader's first 10 s). Give each to a separate fresh critic agent with only: "In one sentence each: what is being tested, and what is the current result?" Record both answers verbatim in the brief. Pass = the new page's answer names the test (where the vessel works) and the result (HELD / what fails) correctly, and the old page's does not do better.
- [ ] **Step 4:** independent visual critic rounds on the full page and on 4 states (defaults, FREEZE, card played + recomputing, map clamped at an extreme) until PASS.
- [ ] **Step 5:** merge to master, push, CI green, live Chromium check at 100 AU and with a card played; memory audit entry.
