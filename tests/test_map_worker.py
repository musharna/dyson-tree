"""Task 3 (visual-first): the live map recompute in a Web Worker (web/map_worker.js).

Two node harnesses, both over the BUILT site/ (tools/build_site.sh), so a worker the build forgot
to copy, or an importScripts name that does not exist beside it, fails here:

  * WORKER: runs site/map_worker.js in a node `vm` context the way a browser worker runs it
    (a global `self`, `importScripts` resolving names relative to the worker file, `postMessage`),
    and calls the worker's own compute and mapCell.
  * PAGE: runs the page's scripts in a `vm` context with the fake DOM of tests/test_site_map.py
    and a fake `Worker` that records what the page posts and lets the test deliver messages back.

Every negative check has a positive control in the same test. Fails, never skips, without node.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

# ------------------------------------------------------------------------------------------------
COMMON = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const site = process.argv[2];
function loadWorker() {
  const posted = [];
  const ctx = { console };
  ctx.self = ctx;
  ctx.postMessage = (m) => posted.push(structuredClone(m));
  ctx.importScripts = (...names) => names.forEach((n) => {
    if (n.includes("/")) throw new Error("importScripts: not a sibling name " + n);
    vm.runInContext(fs.readFileSync(path.join(site, n), "utf8"), ctx, { filename: n });
  });
  vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(site, "map_worker.js"), "utf8"), ctx, { filename: "map_worker.js" });
  return { ctx, posted };
}
function loadMapData() {
  const ctx = {}; ctx.window = ctx; vm.createContext(ctx);
  vm.runInContext(fs.readFileSync(path.join(site, "map_data.js"), "utf8"), ctx);
  return ctx.DysonMap;
}
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const srcs = [...html.matchAll(/<script src="\.\/([^"]+)"><\/script>/g)].map((m) => m[1]);
function mk(tag, id) {
  const l = {};
  return {
    tag, id, value: "", _text: "", className: "", disabled: false, attrs: {}, children: [], parentNode: null, style: {},
    get textContent() { return this._text + this.children.map((c) => c.textContent).join(""); },
    set textContent(v) { this._text = String(v); this.children = []; },
    setAttribute(k, v) { this.attrs[k] = String(v); if (k === "id") this.id = String(v); },
    getAttribute(k) { return k in this.attrs ? this.attrs[k] : null; },
    removeAttribute(k) { delete this.attrs[k]; },
    appendChild(c) { c.parentNode = this; this.children.push(c); return c; },
    removeChild(c) { this.children = this.children.filter((x) => x !== c); c.parentNode = null; return c; },
    get firstChild() { return this.children[0] || null; },
    addEventListener(ev, fn) { (l[ev] = l[ev] || []).push(fn); },
    fire(ev) { (l[ev] || []).forEach((fn) => fn({ target: this })); },
  };
}
function dump(e) { return { tag: e.tag, attrs: e.attrs, text: e._text, children: e.children.map(dump) }; }
// the page, with a fake Worker; withWorker false leaves `Worker` undefined, as an old browser would
function loadPage(withWorker) {
  const els = new Map(), timers = [], workers = [];
  const document = {
    getElementById(id) {
      if (!ids.has(id)) return null;
      if (!els.has(id)) els.set(id, mk(id === "pic" || id === "map" ? "svg" : "div", id));
      return els.get(id);
    },
    createElementNS(ns, tag) { if (ns !== "http://www.w3.org/2000/svg") throw new Error("ns " + ns); return mk(tag, null); },
  };
  class FakeWorker {
    constructor(url) { this.url = url; this.posted = []; this.terminated = false; workers.push(this); }
    postMessage(m) { this.posted.push(structuredClone(m)); }
    terminate() { this.terminated = true; }
  }
  const ctx = { console, document, setTimeout: (fn) => (timers.push(fn), timers.length), clearTimeout: () => {} };
  if (withWorker) ctx.Worker = FakeWorker;
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const s of srcs.filter((s) => s !== "app.js"))
    vm.runInContext(fs.readFileSync(path.join(site, s), "utf8"), ctx, { filename: s });
  const flush = () => { while (timers.length) timers.shift()(); };
  const set = (id, value) => {
    const e = document.getElementById(id);
    if (!e) throw new Error("no element #" + id);
    e.value = String(value); e.fire("input"); e.fire("change");
  };
  // deliver a message to a worker the page made, the way a browser does
  const deliver = (w, data) => w.onmessage({ data });
  return { ctx, document, workers, flush, set, deliver, map: () => dump(document.getElementById("map")) };
}
"""


def run_node(script: str, payload: dict | None = None, timeout: int = 600) -> dict:
    assert NODE and shutil.which("bash"), (
        "node and bash are required; this test fails rather than skips"
    )
    with tempfile.TemporaryDirectory() as tmp:
        drv = Path(tmp) / "drv.cjs"
        drv.write_text(COMMON + script)
        proc = subprocess.run(
            [NODE, str(drv), str(ROOT / "site")],
            input=json.dumps(payload or {}),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    assert proc.returncode == 0, proc.stderr[-4000:]
    return json.loads(proc.stdout)


@pytest.fixture(scope="module", autouse=True)
def built_site():
    assert shutil.which("bash"), "bash is required"
    subprocess.run(
        ["bash", str(ROOT / "tools" / "build_site.sh")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        timeout=120,
    )


def walk(node):
    yield node
    for c in node["children"]:
        yield from walk(c)


def by_id(tree, id_):
    hits = [n for n in walk(tree) if n["attrs"].get("id") == id_]
    assert len(hits) <= 1, (id_, len(hits))
    return hits[0] if hits else None


def text_of(node):
    return node["text"] + "".join(text_of(c) for c in node["children"])


def cell_classes(tree):
    return {
        (int(n["attrs"]["data-i"]), int(n["attrs"]["data-j"])): n["attrs"]["data-class"]
        for n in walk(tree)
        if n["tag"] == "rect" and "data-cell" in n["attrs"]
    }


# (a) --------------------------------------------------------------------------------------------
def fn_source(text: str, name: str) -> str:
    """The `function <name>(...) {...}` text, brace-matched, whitespace-normalised; `export ` dropped."""
    m = re.search(r"(?:export\s+)?function\s+" + name + r"\s*\(", text)
    assert m, f"no function {name}"
    start = text.index("function", m.start())
    depth, i = 0, text.index("{", start)
    while True:
        ch = text[i]
        depth += ch == "{"
        depth -= ch == "}"
        i += 1
        if depth == 0:
            break
    return re.sub(r"\s+", " ", text[start:i]).strip()


def test_worker_mapcell_is_make_map_mapcell_verbatim():
    ref = (ROOT / "tools" / "make_map.mjs").read_text()
    wk = (ROOT / "web" / "map_worker.js").read_text()
    a, b = fn_source(ref, "mapCell"), fn_source(wk, "mapCell")
    assert a == b, f"\nmake_map.mjs: {a}\nmap_worker.js: {b}"
    # the grid axis the worker places cells with is make_map's too
    ax = lambda t: re.sub(r"\s+", " ", re.search(r"const axis = [^\n]+", t).group(0))  # noqa: E731
    assert ax(ref).replace("export ", "") == ax(wk), (ax(ref), ax(wk))
    # positive control: the normaliser does see a one-token drift
    assert fn_source(wk.replace('"HELD"', '"HOLD"'), "mapCell") != a


# (b) --------------------------------------------------------------------------------------------
NO_CARD = r"""
const D = loadMapData();
const P = loadPage(true);
const V = P.ctx.DysonVerdict, res = V.resolve(V.read());
// the page-built objects, exactly as a worker request would carry them (structured clone)
const req = structuredClone({ gen: 7, grid: D.grid, classes: D.classes, sigma_Pa: 0.7e6, org: res.org, inputs: res.inp });
const W = loadWorker();
const t0 = Date.now();
W.ctx.DysonMapWorker.compute(req, (m) => W.posted.push(m), 1);  // the first level only
const lvl = W.posted.filter((m) => m.slice !== undefined);
const NR = D.grid.r_log10[2], NRR = D.grid.R_log10[2];
// the grid's own cell centres: a spread plus the P1-band cell (r 1.20 AU, R 10 km)
const near = (g, v) => Math.round(((Math.log10(v) - g[0]) * (g[2] - 1)) / (g[1] - g[0]));
const cellsIJ = [[near(D.grid.r_log10, 1.2), near(D.grid.R_log10, 1e4)], [14, 44]];
for (let k = 0; k < 14; k++) cellsIJ.push([(k * 37 + 5) % NR, (k * 23 + 3) % NRR]);
const ax = W.ctx.DysonMapWorker.axis, M = W.ctx.DysonModel;
const cells = cellsIJ.map(([i, j]) => ({ i, j,
  live: W.ctx.DysonMapWorker.mapCell(M, ax(D.grid.r_log10, i), ax(D.grid.R_log10, j), req.sigma_Pa, req.org, req.inputs),
  stored: D.classes[Number(D.slices["0.7|algal"][i * NRR + j])] }));
process.stdout.write(JSON.stringify({ levels: lvl, cells, NR, NRR, stored: D.slices["0.7|algal"],
  samples: W.ctx.DysonMapWorker.samples(12, NR), samplesR: W.ctx.DysonMapWorker.samples(8, NRR), ms: Date.now() - t0 }));
"""


def test_worker_matches_the_precomputed_slice_with_no_card():
    r = run_node(NO_CARD)
    NR, NRR, stored = r["NR"], r["NRR"], r["stored"]
    # the worker's own function at the 80 x 60 grid's cell centres equals the stored map
    bad = [c for c in r["cells"] if c["live"] != c["stored"]]
    assert len(r["cells"]) >= 12 and not bad, bad
    p1 = r["cells"][0]
    assert (p1["i"], p1["j"]) == (13, 44) and p1["live"] == "HELD", p1
    # positive control: the sample is not one class, and FREEZE sits in it (cell 14, 44)
    assert len({c["stored"] for c in r["cells"]}) >= 3, r["cells"]
    assert r["cells"][1]["stored"] == "FREEZE" == r["cells"][1]["live"]
    # the 12 x 8 level: one message, the full 80 x 60 extent, its sample cells equal the stored map
    (lv,) = r["levels"]
    assert lv["gen"] == 7 and lv["level"] == "12×8" and len(lv["slice"]) == NR * NRR
    si, sj = r["samples"], r["samplesR"]
    assert (
        (len(si), len(sj)) == (12, 8)
        and si[0] == 0
        and si[-1] == NR - 1
        and sj[-1] == NRR - 1
    )
    mism = [
        (i, j)
        for i in si
        for j in sj
        if lv["slice"][i * NRR + j] != stored[i * NRR + j]
    ]
    assert not mism, mism

    # and it paints the whole extent at its own scale: every cell takes its nearest sample's class
    def nearest(v, s):
        return min(s, key=lambda x: (abs(x - v), x))

    off = [
        (i, j)
        for i in range(NR)
        for j in range(NRR)
        if lv["slice"][i * NRR + j] != stored[nearest(i, si) * NRR + nearest(j, sj)]
    ]
    assert not off, off[:5]


# (c) --------------------------------------------------------------------------------------------
CARD = r"""
const P = loadPage(true);
const V = P.ctx.DysonVerdict;
const base = V.resolve(V.read());
P.set("deck-0-count", 1); P.set("deck-0-value", 1.3);
P.flush();
const res = V.resolve(V.read());
const w = P.workers[P.workers.length - 1];
const req = w ? w.posted[w.posted.length - 1] : null;
const W = loadWorker(), M = W.ctx.DysonModel, cell = W.ctx.DysonMapWorker.mapCell;
const at = (o, r) => cell(M, r, 1e4, 0.7e6, o.org, o.inputs);
process.stdout.write(JSON.stringify({
  url: w && w.url, req, pageOrg: res.org, pageInp: res.inp, baseInp: base.inp,
  noCard121: at({ org: base.org, inputs: base.inp }, 1.21),
  card121: req && at(req, 1.21), card1225: req && at(req, 1.225), card120: req && at(req, 1.20),
}));
"""


def test_antifreeze_card_flips_the_1_21_au_cell_through_the_page_built_request():
    r = run_node(CARD)
    assert r["url"] == "map_worker.js", r[
        "url"
    ]  # relative: works under an http subpath
    req = r["req"]
    assert req is not None, "playing a card posted nothing to a worker"
    # the worker gets the page's own organism and inputs, not a rebuild
    assert req["org"] == r["pageOrg"] and req["inputs"] == r["pageInp"]
    assert (
        req["inputs"]["T_freeze_K"] == pytest.approx(273.15 - 1.3)
        and r["baseInp"]["T_freeze_K"] == 273.15
    )
    assert req["sigma_Pa"] == 0.7e6
    # the M2b-registered shift: r_close 1.2049 -> 1.2197 AU at R 10 km, sigma 0.7, algal
    assert (
        r["noCard121"] == "FREEZE"
    )  # positive control: without the card 1.21 AU freezes
    assert r["card121"] == "HELD"
    assert (
        r["card1225"] == "FREEZE" and r["card120"] == "HELD"
    )  # the new edge lies in (1.21, 1.225)


# (d) --------------------------------------------------------------------------------------------
GENS = r"""
const P = loadPage(true);
const out = {};
out.defaults = P.map(); out.nWorkers0 = P.workers.length;
P.set("deck-0-count", 1); P.set("deck-0-value", 1.3); P.flush();
const w1 = P.workers[P.workers.length - 1], g1 = w1.posted[0].gen;
out.stale = P.map();
P.set("deck-0-count", 0); P.flush();                 // gen 2: the card is off, precomputed applies
out.w1terminated = w1.terminated; out.nWorkersAfterOff = P.workers.length;
const N = w1.posted[0].grid.r_log10[2] * w1.posted[0].grid.R_log10[2];
P.deliver(w1, { gen: g1, level: "12×8", slice: "5".repeat(N) });   // late gen-1 result
out.afterLate = P.map();
P.set("deck-0-count", 1); P.flush();                 // gen 3: card on again
const w3 = P.workers[P.workers.length - 1], g3 = w3.posted[0].gen;
out.gens = [g1, g3];
P.deliver(w3, { gen: g1, level: "12×8", slice: "5".repeat(N) });   // stale while recomputing
out.staleWhileLive = P.map();
P.deliver(w3, { gen: g3, level: "12×8", slice: "5".repeat(N) });   // positive control: current gen
P.deliver(w3, { gen: g3, progress: { level: "40×30", done: 300, total: 1104 } });  // worker order
out.live = P.map();
P.deliver(w3, { gen: g3, level: "80×60", slice: "2".repeat(N) });
out.final = P.map(); out.w3terminated = w3.terminated;
out.stored = P.ctx.DysonMap.slices["0.7|algal"]; out.classes = P.ctx.DysonMap.classes;
// manual p mode with no card: the precomputed map, labelled
const Q = loadPage(true);
Q.set("v-p-mode", "manual"); Q.flush();
out.manual = Q.map(); out.manualWorkers = Q.workers.length;
// an advanced input moves off its default: recompute
const A = loadPage(true);
A.set("v-albedo", "0.1"); A.flush();
out.advWorkers = A.workers.length; out.advReq = A.workers.length ? A.workers[0].posted[0] : null;
out.adv = A.map();
// no Worker in this browser: the map says so and stays greyed, never shown as current
const Z = loadPage(false);
Z.set("deck-0-count", 1); Z.flush();
out.noWorker = Z.map();
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def gens():
    return run_node(GENS)


def stored_map(g):
    NRR = 60
    return {
        (i, j): g["classes"][int(g["stored"][i * NRR + j])]
        for i in range(80)
        for j in range(60)
    }


def source(tree):
    return by_id(tree, "map-cells")["attrs"].get("data-source")


def test_stale_generation_is_dropped_and_precomputed_stays(gens):
    g, want = gens, stored_map(gens)
    assert g["nWorkers0"] == 0  # defaults: no worker at all
    assert g["w1terminated"] and g["nWorkersAfterOff"] == 1
    # card off, then the late gen-1 result arrives: ignored, the precomputed slice stays, current
    assert cell_classes(g["afterLate"]) == want
    assert (
        source(g["afterLate"]) == "precomputed"
        and by_id(g["afterLate"], "map-recomputing") is None
    )
    # a stale gen while recomputing is ignored too: still the greyed precomputed map
    assert g["gens"][1] > g["gens"][0]
    assert (
        source(g["staleWhileLive"]) == "stale"
        and cell_classes(g["staleWhileLive"]) == want
    )
    # positive control: the current gen's message paints, over the whole grid
    live = cell_classes(g["live"])
    assert len(live) == 4800 and set(live.values()) == {"OPAQUE"}
    assert source(g["live"]) == "12×8" and by_id(g["live"], "map-recomputing") is None
    st = by_id(g["live"], "map-live-status")
    assert (
        st is not None
        and "12 × 8" in text_of(st)
        and "40 × 30" in text_of(st)
        and "27%" in text_of(st)
    ), text_of(st)
    assert (
        set(cell_classes(g["final"]).values()) == {"FREEZE"}
        and source(g["final"]) == "80×60"
    )
    assert (
        "80 × 60" in text_of(by_id(g["final"], "map-live-status")) and g["w3terminated"]
    )


def test_precomputed_is_greyed_and_labelled_not_current_while_recomputing(gens):
    d, s = gens["defaults"], gens["stale"]
    # positive control: at the defaults the precomputed map is current, not dimmed, no label
    assert (
        source(d) == "precomputed"
        and by_id(d, "map-cells")["attrs"].get("opacity") is None
    )
    assert by_id(d, "map-recomputing") is None and by_id(d, "map-live-status") is None
    assert cell_classes(s) == stored_map(gens)
    assert (
        source(s) == "stale" and by_id(s, "map-cells")["attrs"].get("opacity") == "0.35"
    )
    rc = by_id(s, "map-recomputing")
    assert rc is not None and "recomputing for your design" in text_of(rc), (
        rc and text_of(rc)
    )
    note = by_id(s, "map-stale-note")
    assert note is not None and "not current" in text_of(note)
    # the dot does not vouch for a cell class that is not current
    assert by_id(s, "map-dot")["attrs"]["data-cell-class"] == ""
    assert by_id(d, "map-dot")["attrs"]["data-cell-class"] == "HELD"
    assert "same map for algal and vascular" not in text_of(by_id(s, "map-title"))


def test_manual_pt_keeps_the_precomputed_map_with_a_label(gens):
    m, d = gens["manual"], gens["defaults"]
    assert gens["manualWorkers"] == 0
    assert source(m) == "precomputed" and cell_classes(m) == stored_map(gens)
    lab = by_id(m, "map-manual-note")
    assert (
        lab is not None
        and text_of(lab)
        == "map shows the auto-designed vessel; your manual p/t is the dot"
    )
    assert by_id(d, "map-manual-note") is None  # positive control: auto p/t, no label


def test_advanced_input_off_default_recomputes(gens):
    assert gens["advWorkers"] == 1 and gens["advReq"]["inputs"]["albedo"] == 0.1
    assert (
        source(gens["adv"]) == "stale"
        and by_id(gens["adv"], "map-recomputing") is not None
    )


def test_no_worker_says_so_and_never_shows_the_map_as_current(gens):
    z = gens["noWorker"]
    assert (
        source(z) == "stale" and by_id(z, "map-cells")["attrs"].get("opacity") == "0.35"
    )
    txt = (
        text_of(by_id(z, "map-recomputing")) + " " + text_of(by_id(z, "map-stale-note"))
    )
    assert "unavailable" in txt and "not current" in txt, txt
