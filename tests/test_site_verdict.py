"""M2 acceptance, on the BUILT page: the seven inputs and the verdict panel (spec §8 M2, §4, §5).

Builds site/ with tools/build_site.sh, then loads the scripts site/index.html loads, in its
order, into a bare node `vm` context with a minimal DOM: `document.getElementById` returns
an element only for an id that site/index.html actually carries, so a control or readout the
page forgot fails here. app.js (the uncontained Q1 plot) is not loaded; it draws SVG.

Each scenario sets controls the way the page does (value, then `input` and `change`
events) and reads back the TEXT the panel prints: status (HOLDS / VIOLATED) and the printed
margin per line. The expected sets come from the spec, not from the page's own model call.

Fails, never skips, without node or bash.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
LINES = ["BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE"]

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const site = process.argv[2];
const scenarios = JSON.parse(fs.readFileSync(0, "utf8"));
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const srcs = [...html.matchAll(/<script src="\.\/([^"]+)"><\/script>/g)].map((m) => m[1]);
const LINES = ["BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE"];
function run(steps) {
  const els = new Map();
  const timers = [];
  const document = {
    getElementById(id) {
      if (!ids.has(id)) return null;
      if (!els.has(id)) {
        const l = {};
        els.set(id, {
          id, value: "", textContent: "", className: "", disabled: false, attrs: {},
          setAttribute(k, v) { this.attrs[k] = String(v); },
          getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
          appendChild(c) { return c; },
          addEventListener(ev, fn) { (l[ev] = l[ev] || []).push(fn); },
          fire(ev) { (l[ev] || []).forEach((fn) => fn({ target: this })); },
        });
      }
      return els.get(id);
    },
    // web/picture.js builds SVG; a detached stub is enough here (tests/test_site_picture.py reads it)
    createElementNS() { const e = { setAttribute() {}, appendChild(c) { return c; }, textContent: "" }; return e; },
  };
  const ctx = { console, document, setTimeout: (fn) => (timers.push(fn), timers.length), clearTimeout: () => {} };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const s of srcs.filter((s) => s !== "app.js"))
    vm.runInContext(fs.readFileSync(path.join(site, s), "utf8"), ctx, { filename: s });
  for (const st of steps) {
    const e = document.getElementById(st.id);
    if (!e) throw new Error("no element #" + st.id);
    e.value = String(st.value);
    e.fire("input");
    e.fire("change");
  }
  while (timers.length) timers.shift()();
  const g = (id) => { const e = document.getElementById(id); if (!e) throw new Error("no #" + id); return e.textContent; };
  const out = { lines: {}, summary: g("v-summary"), live: document.getElementById("v-summary").attrs["aria-live"] || null };
  for (const n of LINES) out.lines[n] = { status: g("v-status-" + n), margin: g("v-margin-" + n), cmp: g("v-cmp-" + n) };
  // visual-first Task 4: the headroom bar per line (null when the page has no such row)
  out.bars = {};
  for (const n of LINES) {
    if (!ids.has("hr-" + n)) { out.bars[n] = null; continue; }
    const q = (s) => (ids.has("hr-" + n + s) ? document.getElementById("hr-" + n + s) : null);
    const f = q("-fill"), c = q("-cap"), v = q("-val");
    out.bars[n] = { attrs: document.getElementById("hr-" + n).attrs, fill: f ? f.attrs : null,
      cap: c ? c.className : null, val: v ? v.textContent : null };
  }
  for (const k of ["v-pstar", "v-tmin", "v-rfixed", "v-rauto", "v-Rwin", "v-Rfloor", "v-rslab", "v-albedo-freeze", "v-error", "deck-status", "deck-0-badge", "deck-1-badge", "deck-0-trait", "deck-1-trait", "deck-0-source"]) out[k] = g(k);
  return out;
}
const res = {};
for (const [name, steps] of Object.entries(scenarios)) res[name] = run(steps);
process.stdout.write(JSON.stringify({ scripts: srcs, res }));
"""

SCENARIOS = {
    "defaults": [],
    # spec §8 M2: drag r past the registered r_close at R = 10 km (P1, sigma 0.7: 1.2049 AU)
    "R10km_r1.20": [{"id": "v-R", "value": "4"}, {"id": "v-r", "value": "0.0792"}],
    "R10km_r1.21": [{"id": "v-R", "value": "4"}, {"id": "v-r", "value": "0.0828"}],
    # manual p above / below p* (1960.5 Pa at the defaults), t frozen at t_min(p*)
    "p_above": [{"id": "v-p-mode", "value": "manual"}, {"id": "v-p", "value": "3.35"}],
    "p_below": [{"id": "v-p-mode", "value": "manual"}, {"id": "v-p", "value": "3.25"}],
    # manual t of 100 m at the defaults, p re-solved on the given wall
    "t_100m": [{"id": "v-t-mode", "value": "manual"}, {"id": "v-t", "value": "2"}],
    # M2b deck (§12): antifreeze 1.3 K at R 10 km moves the sigma 0.7 FREEZE edge to 1.2197
    "afp13_r1.21": [
        {"id": "v-R", "value": "4"},
        {"id": "deck-0-count", "value": "1"},
        {"id": "deck-0-value", "value": "1.3"},
        {"id": "v-r", "value": "0.0828"},
    ],
    "afp13_r1.22": [
        {"id": "v-R", "value": "4"},
        {"id": "deck-0-count", "value": "1"},
        {"id": "deck-0-value", "value": "1.3"},
        {"id": "v-r", "value": "0.0864"},
    ],
    # two 0.8 K cards: 1.6 K total, clipped at 1.3 K and the clip printed
    "afp_2x08": [
        {"id": "v-R", "value": "4"},
        {"id": "deck-0-count", "value": "2"},
        {"id": "deck-0-value", "value": "0.8"},
    ],
    # P2 window (r 1.10, sigma 0.7, R 95.55 km): STARVE +3.11 -> +3.20 with the DECLARED r_d card
    "P2_edge": [{"id": "v-R", "value": "4.98027"}],
    "P2_edge_rd": [{"id": "v-R", "value": "4.98027"}, {"id": "deck-1-count", "value": "1"}],
    # 100 AU: cold respiration is tiny; with the r_d card the deficit falls inside the
    # registered absolute floor (prereg starve_opaque_abs 1e-9) and scores HOLDS
    "r100": [{"id": "v-r", "value": "2"}],
    "r100_rd": [{"id": "v-r", "value": "2"}, {"id": "deck-1-count", "value": "1"}],
    # (Task 4) 0.5 AU: the shell melts, sigma_eff is 0, BURST's headroom runs off the left end
    "r0.5": [{"id": "v-r", "value": "-0.3011"}],
}


def num(text: str) -> float:
    m = re.search(r"[-+−]?\d+(?:\.\d+)?(?:e[-+]?\d+)?", text)
    assert m, f"no number in {text!r}"
    return float(m.group(0).replace("−", "-"))


@pytest.fixture(scope="module")
def page():
    node, bash = shutil.which("node"), shutil.which("bash")
    assert node and bash, (
        "node and bash are required; this test fails rather than skips"
    )
    subprocess.run(
        [bash, str(ROOT / "tools" / "build_site.sh")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=120,
    )
    with tempfile.TemporaryDirectory() as tmp:
        drv = Path(tmp) / "drive.cjs"
        drv.write_text(DRIVER)
        proc = subprocess.run(
            [node, str(drv), str(ROOT / "site")],
            input=json.dumps(SCENARIOS),
            capture_output=True,
            text=True,
            timeout=600,
        )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["scripts"].index("model.js") < out["scripts"].index("verdict.js")
    return out


def violated(r):
    return [n for n in LINES if r["lines"][n]["status"] == "VIOLATED"]


def test_statuses_are_one_of_two_words(page):
    for name, r in page["res"].items():
        for n in LINES:
            assert r["lines"][n]["status"] in ("HOLDS", "VIOLATED"), (
                name,
                n,
                r["lines"][n],
            )


def test_defaults(page):
    r = page["res"]["defaults"]
    assert violated(r) == [], r
    for n in ("FREEZE", "STARVE", "OPAQUE"):
        assert num(r["lines"][n]["margin"]) > 0, (n, r["lines"][n])
    for n in ("BURST", "BOIL"):
        m = r["lines"][n]["margin"]
        assert num(m) == 0.0 and "by construction" in m, (n, m)
    assert abs(num(r["v-pstar"]) - 1960.5) < 0.05, r["v-pstar"]
    assert abs(num(r["v-tmin"]) - 1.400) < 5e-4, r["v-tmin"]
    assert abs(num(r["lines"]["STARVE"]["margin"]) - 8.23) < 5e-3
    # spec §5: the fixed wall freezes at 1.2428 AU, the auto-path edge is 1.2805 AU
    assert "1.2428" in r["v-rfixed"], r["v-rfixed"]
    assert "1.2805" in r["v-rauto"], r["v-rauto"]
    assert r["v-error"] == ""
    assert r["live"] == "polite"
    assert "alive" in r["summary"], r["summary"]


def test_R_window_and_registered_band(page):
    r = page["res"]["defaults"]
    assert 90 < num(r["v-Rwin"]) < 100, r["v-Rwin"]  # ≈96 km provisional (§5)
    prereg = yaml.safe_load((ROOT / "experiments/q4_vessel/prereg.yaml").read_text())
    lo, hi = prereg["predictions"]["P2"]["band_km"]
    assert f"[{lo}, {hi}] km" in r["v-Rfloor"], r["v-Rfloor"]


def test_r_past_registered_r_close_flips_exactly_freeze(page):
    assert violated(page["res"]["R10km_r1.20"]) == []
    assert violated(page["res"]["R10km_r1.21"]) == ["FREEZE"]
    assert "FREEZE" in page["res"]["R10km_r1.21"]["summary"]


def test_manual_p_above_p_star_is_exactly_burst(page):
    assert violated(page["res"]["p_above"]) == ["BURST"]


def test_manual_p_below_p_sat_is_exactly_boil(page):
    assert violated(page["res"]["p_below"]) == ["BOIL"]


def test_manual_t_100m_is_exactly_opaque(page):
    r = page["res"]["t_100m"]
    assert violated(r) == ["OPAQUE"]
    assert "declared" in r["lines"]["OPAQUE"]["cmp"]


def test_slab_reflectance_printed_live(page):
    a = num(page["res"]["defaults"]["v-rslab"])
    b = num(page["res"]["t_100m"]["v-rslab"])
    assert 0 < a < 0.2 and a != b
    assert "0.072" in page["res"]["defaults"]["v-albedo-freeze"]


# ---------------------------------------------------------------- M2b, the deck (§12)
def test_deck_cards_carry_badges_and_sources(page):
    r = page["res"]["defaults"]
    assert (r["deck-0-trait"], r["deck-0-badge"]) == ("antifreeze proteins", "DEMONSTRATED")
    assert (r["deck-1-trait"], r["deck-1-badge"]) == ("reduced dark respiration", "DECLARED")
    assert "10.1038/nbt0997-887" in r["deck-0-source"]
    assert r["deck-status"] == "no card played"


def test_antifreeze_card_moves_t_freeze_and_the_freeze_edge(page):
    base = page["res"]["R10km_r1.21"]
    a, b = page["res"]["afp13_r1.21"], page["res"]["afp13_r1.22"]
    # positive control: without the card r 1.21 AU freezes (edge 1.2049)
    assert violated(base) == ["FREEZE"] and "1.2049" in base["v-rauto"]
    assert violated(a) == [], a["lines"]["FREEZE"]
    assert violated(b) == ["FREEZE"]
    assert "T_freeze 271.850 K" in a["lines"]["FREEZE"]["cmp"], a["lines"]["FREEZE"]["cmp"]
    assert "1.2197" in a["v-rauto"] and "FREEZE binds" in a["v-rauto"], a["v-rauto"]


def test_stacked_antifreeze_is_clipped_and_the_clip_printed(page):
    r = page["res"]["afp_2x08"]
    assert "CLIPPED" in r["deck-status"] and "clipped at 1.3" in r["deck-status"], r["deck-status"]
    assert "T_freeze 271.850 K" in r["lines"]["FREEZE"]["cmp"]
    assert "1.2197" in r["v-rauto"], r["v-rauto"]


def test_declared_respiration_card_allowed_on_page_moves_starve_margin(page):
    a, b = page["res"]["P2_edge"], page["res"]["P2_edge_rd"]
    assert round(num(a["lines"]["STARVE"]["margin"]), 2) == 3.11, a["lines"]["STARVE"]
    assert round(num(b["lines"]["STARVE"]["margin"]), 2) == 3.20, b["lines"]["STARVE"]
    assert b["v-error"] == "" and "DECLARED" in b["deck-status"], b["deck-status"]
    # the card moved r_d, not any comparator: every right-hand side is unchanged
    for n in LINES:
        rhs = lambda r: r["lines"][n]["cmp"].split(" vs ")[1]  # noqa: E731
        assert rhs(a) == rhs(b), n


def test_starve_deficit_inside_the_registered_floor_is_named(page):
    a, b = page["res"]["r100"], page["res"]["r100_rd"]
    # positive control: without the card the 100 AU deficit clears the floor
    assert a["lines"]["STARVE"]["status"] == "VIOLATED", a["lines"]["STARVE"]
    assert "detection floor" not in a["lines"]["STARVE"]["margin"]
    # with it, net is still negative but HOLDS, and the row says why
    assert b["lines"]["STARVE"]["status"] == "HOLDS", b["lines"]["STARVE"]
    assert -1e-9 < num(b["lines"]["STARVE"]["margin"]) < 0, b["lines"]["STARVE"]
    assert "inside the registered detection floor (1e-9)" in b["lines"]["STARVE"]["margin"], b["lines"]["STARVE"]


# The picture must draw anywhere on the sliders, not only in the six shot states: at
# f1761b9 107 of a 150-state grid threw "plate ... fits no wrap" (STARVE from 2 AU out,
# BURST at 0.5 AU and at 1 AU / 100 km). These are the states of each failing class.
SWEEP = {
    f"r{r}_R{R}{c}": [{"id": "v-R", "value": str(R)}]
    + ([{"id": "deck-1-count", "value": "1"}] if c else [])
    + [{"id": "v-r", "value": str(r)}]
    for r, R, c in [
        (-0.3011, 1, ""), (-0.3011, 5, ""), (0, 5, ""), (0.3, 3, ""),
        (1, 3, ""), (1.5, 1, "_rd"), (2, 3, ""), (2, 5, "_rd"),
    ]
}


def test_picture_draws_across_the_slider_range():
    node = shutil.which("node")
    assert node, "node is required; this test fails rather than skips"
    subprocess.run(["bash", str(ROOT / "tools" / "build_site.sh")], cwd=ROOT, check=True,
                   capture_output=True, timeout=120)
    # (visual-first Task 5) the map must draw too: the stub DOM records children here, so the
    # cells #map holds after the state is set can be counted
    kids = ("children: [], appendChild(c) { this.children.push(c); return c; }, "
            "get firstChild() { return this.children[0] || null; }, "
            "removeChild(c) { this.children = this.children.filter((x) => x !== c); return c; }, ")
    patches = [
        ("res[name] = run(steps);",
         "try { res[name] = run(steps); } catch (e) { res[name] = { error: String(e.message) }; }"),
        ("          appendChild(c) { return c; },", "          " + kids),
        ('const e = { setAttribute() {}, appendChild(c) { return c; }, textContent: "" };',
         "const e = { attrs: {}, setAttribute(k, v) { this.attrs[k] = String(v); }, " + kids + 'textContent: "" };'),
        ("  return out;\n",
         "  const walk = (e) => [e].concat((e.children || []).flatMap(walk));\n"
         '  out.mapCells = walk(document.getElementById("map")).filter((e) => e.attrs && "data-cell" in e.attrs).length;\n'
         "  out.mapWant = ctx.DysonMap.grid.r_log10[2] * ctx.DysonMap.grid.R_log10[2];\n"
         '  out.mapGrid = ctx.DysonMap.grid;\n'
         '  const dot = walk(document.getElementById("map")).filter((e) => e.attrs && e.attrs.id === "map-dot");\n'
         "  out.mapDot = dot.map((e) => e.attrs);\n"
         "  return out;\n"),
    ]
    drv_src = DRIVER
    for old, new in patches:
        assert drv_src.count(old) == 1, old
        drv_src = drv_src.replace(old, new)
    with tempfile.TemporaryDirectory() as tmp:
        drv = Path(tmp) / "sweep.cjs"
        drv.write_text(drv_src)
        proc = subprocess.run([node, str(drv), str(ROOT / "site")], input=json.dumps(SWEEP),
                              capture_output=True, text=True, timeout=900)
    assert proc.returncode == 0, proc.stderr
    res = json.loads(proc.stdout)["res"]
    thrown = {k: v["error"] for k, v in res.items() if "error" in v}
    assert not thrown, thrown
    # positive control: these states do fail lines, so plates were actually placed
    assert all(violated(v) for v in res.values()), {k: violated(v) for k, v in res.items()}
    # every state draws the map's cells, one per grid point
    assert all(v["mapWant"] > 0 for v in res.values()), res
    undrawn = {k: (v["mapCells"], v["mapWant"]) for k, v in res.items() if v["mapCells"] != v["mapWant"]}
    assert not undrawn, undrawn
    # drawn for THIS state: one dot, on the cell nearest the slider values the state set (the
    # cells persist between draws, so they alone cannot tell a draw that skipped this state)
    # (grid position in cell units; R 1 km sits on a half-cell tie, so either neighbour is nearest)
    def pos(g, lv):
        return min(g[2] - 1.0, max(0.0, (lv - g[0]) * (g[2] - 1) / (g[1] - g[0])))

    offdot = {}
    for k, v in res.items():
        steps = {st["id"]: float(st["value"]) for st in SWEEP[k]}
        g = v["mapGrid"]
        want = (pos(g["r_log10"], steps["v-r"]), pos(g["R_log10"], steps["v-R"]))
        got = [(d.get("data-i"), d.get("data-j")) for d in v["mapDot"]]
        if len(got) != 1 or any(c is None or abs(int(c) - w) > 0.5 + 1e-6 for c, w in zip(got[0], want)):
            offdot[k] = (got, want)
    assert not offdot, offdot
    # and the five headroom bars, each with a drawn fill
    def barless(v):
        return [n for n in LINES if not (v["bars"][n] and v["bars"][n]["fill"]
                                         and "width:" in v["bars"][n]["fill"].get("style", ""))]
    nobars = {k: barless(v) for k, v in res.items() if barless(v)}
    assert not nobars, nobars


# ---------------------------------------------------------------- visual-first Task 4: headroom bars
def bar(r, n):
    b = r["bars"][n]
    assert b is not None, f"no headroom bar row #hr-{n}"
    return b


def norm(b) -> float:
    return float(b["attrs"]["data-norm"])


def rhs_value(cmp: str) -> float:
    return num(cmp.split(" vs ")[1].split(" ", 1)[1])


def test_five_headroom_bars_carry_the_line_and_its_normaliser(page):
    r = page["res"]["defaults"]
    for n in LINES:
        b = bar(r, n)
        # (data-line is static HTML, which this stub does not parse; smoke_page.py reads it)
        assert b["attrs"].get("title", "").startswith(n + " headroom:"), (n, b["attrs"])
        assert b["fill"] is not None and "width:" in b["fill"].get("style", ""), (n, b["fill"])
    # the normaliser is named in the row's title, so the bar's length is honest
    names = {"BURST": "σ_eff", "FREEZE": "10 K", "BOIL": "p_sat", "STARVE": "a_max", "OPAQUE": "f_floor"}
    for n, want in names.items():
        assert want in bar(r, n)["attrs"].get("title", ""), (n, bar(r, n)["attrs"].get("title"))


def test_headroom_is_the_printed_margin_over_the_named_scale(page):
    from sim.organism import ALGAL

    r = page["res"]["defaults"]
    f = r["lines"]["FREEZE"]
    assert abs(norm(bar(r, "FREEZE")) - num(f["margin"]) / 10.0) < 1e-3, (f, bar(r, "FREEZE"))
    s = r["lines"]["STARVE"]
    assert abs(norm(bar(r, "STARVE")) - num(s["margin"]) / ALGAL.a_max) < 1e-3, (s, bar(r, "STARVE"))
    o = r["lines"]["OPAQUE"]
    assert abs(norm(bar(r, "OPAQUE")) - num(o["margin"]) / rhs_value(o["cmp"])) < 1e-3, (o, bar(r, "OPAQUE"))
    # by construction: BURST and BOIL headroom is the solver residual, ~0
    for n in ("BURST", "BOIL"):
        assert abs(norm(bar(r, n))) < 1e-6, (n, bar(r, n))
    # manual p above p*: BURST's margin over sigma_eff (the printed right side)
    a = page["res"]["p_above"]
    bu = a["lines"]["BURST"]
    assert abs(norm(bar(a, "BURST")) - num(bu["margin"]) / rhs_value(bu["cmp"])) < 1e-3, (bu, bar(a, "BURST"))
    bo = page["res"]["p_below"]["lines"]["BOIL"]
    assert abs(norm(bar(page["res"]["p_below"], "BOIL")) - num(bo["margin"]) / rhs_value(bo["cmp"])) < 1e-3


def test_violated_bar_is_marked_and_the_first_is_the_binding_row(page):
    d, f = page["res"]["defaults"], page["res"]["R10km_r1.21"]
    # positive control: at the defaults no row is marked
    assert [n for n in LINES if bar(d, n)["attrs"].get("data-violated") == "true"] == []
    assert [n for n in LINES if bar(f, n)["attrs"].get("data-violated") == "true"] == ["FREEZE"]
    assert bar(f, "FREEZE")["attrs"].get("data-first") == "true"
    assert norm(bar(f, "FREEZE")) < 0
    # STARVE inside the registered floor: negative headroom, but the line HOLDS, so not marked
    b = bar(page["res"]["r100_rd"], "STARVE")
    assert norm(b) < 0 and b["attrs"].get("data-violated") == "false", b


def test_bar_clamps_at_one_scale_and_says_so(page):
    # positive control: r 1.20 AU at 10 km sits just inside r_close, FREEZE drawn at its true length
    b0 = bar(page["res"]["R10km_r1.20"], "FREEZE")
    assert 0 < norm(b0) < 1, b0
    assert b0["attrs"].get("data-clamped") == "false" and float(b0["attrs"]["data-len"]) == norm(b0), b0
    assert "hr-cap-" not in (b0["cap"] or ""), b0
    # the defaults: FREEZE headroom is past +1 scale (10 K), drawn to the right end, capped there
    b = bar(page["res"]["defaults"], "FREEZE")
    assert norm(b) > 1, b
    assert b["attrs"].get("data-clamped") == "true" and float(b["attrs"]["data-len"]) == 1.0, b
    assert "hr-cap-right" in (b["cap"] or ""), b
    # 100 AU: FREEZE far below, drawn to the left end
    b = bar(page["res"]["r100"], "FREEZE")
    assert norm(b) < -1 and b["attrs"].get("data-violated") == "true", b
    assert b["attrs"].get("data-clamped") == "true" and float(b["attrs"]["data-len"]) == -1.0, b
    assert "hr-cap-left" in (b["cap"] or ""), b
    # 0.5 AU: the wall is water (sigma_eff 0), BURST's headroom is -inf, drawn to the left end
    w = page["res"]["r0.5"]
    assert "the wall is water" in w["lines"]["BURST"]["cmp"], w["lines"]["BURST"]
    b = bar(w, "BURST")
    assert norm(b) < -1 and b["attrs"].get("data-violated") == "true", b
    assert b["attrs"].get("data-clamped") == "true" and float(b["attrs"]["data-len"]) == -1.0, b
    assert "hr-cap-left" in (b["cap"] or ""), b


def test_freeze_bar_title_carries_kelvin_on_both_sides(page):
    # FREEZE's scale is 10 K; the margin it divides is in K too, so both sides say so
    t = bar(page["res"]["defaults"], "FREEZE")["attrs"]["title"]
    assert re.search(r"= [-+−]?\d+(?:\.\d+)? K ÷ 10(?:\.0+)? K = ", t), t
    # positive control: a line in Pa still prints its unit, not K
    assert " Pa ÷ " in bar(page["res"]["defaults"], "BURST")["attrs"]["title"]
