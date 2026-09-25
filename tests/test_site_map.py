"""Task 2 (visual-first): the precomputed first-failure map, drawn on the BUILT page and linked
to the vessel's verdict.

Loads the scripts site/index.html loads into a node `vm` context with a minimal DOM (the same
shape as tests/test_site_picture.py's), drives the controls the way the page does, and reads
back the element tree the page built under #map plus the verdict summary it printed. The
expected classes come from the verdict text and from web/map_data.js, never from mapview.js.

Every negative check has a positive control in the same test. Pixel geometry and the click
wiring in a real browser are tools/smoke_page.py's job. Fails, never skips, without node.
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

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const site = process.argv[2];
const scenarios = JSON.parse(fs.readFileSync(0, "utf8"));
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
function dump(e) {
  return { tag: e.tag, attrs: e.attrs, text: e._text, children: e.children.map(dump) };
}
function run(steps) {
  const els = new Map();
  const timers = [];
  const document = {
    getElementById(id) {
      if (!ids.has(id)) return null;
      if (!els.has(id)) els.set(id, mk(id === "pic" || id === "map" ? "svg" : "div", id));
      return els.get(id);
    },
    createElementNS(ns, tag) { if (ns !== "http://www.w3.org/2000/svg") throw new Error("ns " + ns); return mk(tag, null); },
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
  const map = document.getElementById("map");
  if (!map) throw new Error("no #map in site/index.html");
  return {
    summary: document.getElementById("v-summary").textContent,
    rOut: document.getElementById("v-r-out").textContent,
    map: dump(map),
    grid: ctx.DysonMap.grid,
    classes: ctx.DysonMap.classes,
    slice07: ctx.DysonMap.slices["0.7|algal"],
  };
}
const res = {};
for (const [name, steps] of Object.entries(scenarios)) res[name] = run(steps);
process.stdout.write(JSON.stringify(res));
"""

R10 = {"id": "v-R", "value": "4"}  # log10 m: 10 km
SCENARIOS = {
    "defaults": [],
    # (b) the brief's pair: the registered r_close at 10 km, sigma 0.7, is 1.2049 AU
    "r1.20": [R10, {"id": "v-r", "value": "0.0792"}],
    "r1.21": [R10, {"id": "v-r", "value": "0.0828"}],
    # (b') the same pair at grid-cell centres i = 13 (1.1955 AU) and i = 14 (1.2785 AU)
    "cell13": [R10, {"id": "v-r", "value": "0.0775"}],
    "cell14": [R10, {"id": "v-r", "value": "0.1067"}],
    # (c) slider extremes: the grid corners
    "low": [{"id": "v-R", "value": "1"}, {"id": "v-r", "value": "-0.3011"}],
    "high": [{"id": "v-R", "value": "5"}, {"id": "v-r", "value": "2"}],
    # (d) sigma
    "s15": [{"id": "v-sigma", "value": "1.5"}],
    "vascular": [{"id": "v-org", "value": "vascular"}],
    # (Task 4) off the registered run's inputs: a card, or an advanced input off its default
    "card": [{"id": "deck-0-count", "value": "1"}, {"id": "deck-0-value", "value": "1.3"}],
    "albedo": [{"id": "v-albedo", "value": "0.01"}],
}


def walk(node):
    yield node
    for c in node["children"]:
        yield from walk(c)


def by_id(tree, id_):
    hits = [n for n in walk(tree) if n["attrs"].get("id") == id_]
    assert len(hits) <= 1, (id_, len(hits))
    return hits[0] if hits else None


def need(tree, id_):
    """by_id for a node the test requires: fails with the id instead of returning None."""
    n = by_id(tree, id_)
    assert n is not None, f"no #{id_}"
    return n


def text_of(node):
    return node["text"] + "".join(text_of(c) for c in node["children"])


def cells(tree):
    return [n for n in walk(tree) if n["tag"] == "rect" and "data-cell" in n["attrs"]]


def dot(tree):
    d = by_id(tree, "map-dot")
    assert d is not None, "no #map-dot"
    return d


def cell_under_dot(tree):
    """The cell rect whose drawn box contains the dot's centre (boundary inclusive), found by
    geometry, not by trusting the dot's own data-i/data-j."""
    d = dot(tree)
    x, y = float(d["attrs"]["cx"]), float(d["attrs"]["cy"])
    hits = []
    for c in cells(tree):
        a = c["attrs"]
        x0, y0 = float(a["x"]), float(a["y"])
        x1, y1 = x0 + float(a["width"]), y0 + float(a["height"])
        if x0 - 1e-6 <= x <= x1 + 1e-6 and y0 - 1e-6 <= y <= y1 + 1e-6:
            hits.append(c)
    assert hits, f"no cell contains the dot at ({x}, {y})"
    # on a shared edge both neighbours contain the point; the nearest-cell rule picks the dot's
    want = (d["attrs"]["data-i"], d["attrs"]["data-j"])
    picked = [c for c in hits if (c["attrs"]["data-i"], c["attrs"]["data-j"]) == want]
    assert len(picked) == 1, (
        want,
        [(c["attrs"]["data-i"], c["attrs"]["data-j"]) for c in hits],
    )
    return picked[0]


def verdict_class(summary: str) -> str:
    if summary.startswith("alive: every line holds"):
        return "HELD"
    m = re.match(r"VIOLATED: ([A-Z_]+)", summary)
    assert m, summary
    return m.group(1)


def stored_class(res, i, j):
    return res["classes"][int(res["slice07"][i * res["grid"]["R_log10"][2] + j])]


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
        drv = Path(tmp) / "map.cjs"
        drv.write_text(DRIVER)
        proc = subprocess.run(
            [node, str(drv), str(ROOT / "site")],
            input=json.dumps(SCENARIOS),
            capture_output=True,
            text=True,
            timeout=600,
        )
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


# (a) ------------------------------------------------------------------------------------------
def test_defaults_map_has_80x60_cells_and_the_dot_cell_matches_the_verdict(page):
    r = page["defaults"]
    cs = cells(r["map"])
    assert len(cs) == 80 * 60, len(cs)
    ij = {(int(c["attrs"]["data-i"]), int(c["attrs"]["data-j"])) for c in cs}
    assert ij == {(i, j) for i in range(80) for j in range(60)}
    # every cell's class is the stored one (spot-check the whole 0.7|algal slice)
    bad = [
        (c["attrs"]["data-i"], c["attrs"]["data-j"])
        for c in cs
        if c["attrs"]["data-class"]
        != stored_class(r, int(c["attrs"]["data-i"]), int(c["attrs"]["data-j"]))
    ]
    assert not bad, bad[:5]
    assert r["summary"].startswith("alive: every line holds"), r["summary"]
    under = cell_under_dot(r["map"])
    assert under["attrs"]["data-class"] == verdict_class(r["summary"]) == "HELD"
    # the colour a reader sees is the class colour: same fill as the HELD legend swatch
    sw = by_id(r["map"], "map-key-HELD")
    assert sw is not None and sw["attrs"]["fill"] == under["attrs"]["fill"]


# (b) ------------------------------------------------------------------------------------------
def test_verdict_pair_at_r_close_10km(page):
    a, b = page["r1.20"], page["r1.21"]
    assert a["rOut"] == "1.200 AU" and b["rOut"] == "1.210 AU", (a["rOut"], b["rOut"])
    assert verdict_class(a["summary"]) == "HELD", a["summary"]
    assert verdict_class(b["summary"]) == "FREEZE", b["summary"]
    # r 1.20 AU: the dot's cell and the stored map agree with the verdict
    ca = cell_under_dot(a["map"])
    assert ca["attrs"]["data-class"] == "HELD"
    assert (
        stored_class(a, int(ca["attrs"]["data-i"]), int(ca["attrs"]["data-j"]))
        == "HELD"
    )


def test_dot_carries_the_exact_verdict_class_not_the_cell_class(page):
    """Fix round 1 (F1): one r column is 0.0291 decades, wider than the P1 band, so at r 1.21 AU
    the nearest cell is HELD while the verdict is FREEZE. The dot is the exact design: its class
    and fill are the verdict's; the cell under it keeps the grid's class."""
    a, b = page["r1.20"], page["r1.21"]
    da, db = dot(a["map"]), dot(b["map"])
    assert da["attrs"]["data-class"] == verdict_class(a["summary"]) == "HELD", (da["attrs"], a["summary"])
    assert db["attrs"]["data-class"] == verdict_class(b["summary"]) == "FREEZE", (db["attrs"], b["summary"])
    # the fill a reader sees is the legend's class colour
    for r, d, c in ((a, da, "HELD"), (b, db, "FREEZE")):
        sw = by_id(r["map"], "map-key-" + c)
        assert sw is not None and d["attrs"]["fill"] == sw["attrs"]["fill"], (c, d["attrs"])
    # why the dot needs its own class: the cell under it at 1.21 is still HELD
    assert cell_under_dot(b["map"])["attrs"]["data-class"] == "HELD"
    key = by_id(a["map"], "map-key-note")
    assert key is not None and text_of(key) == "cells: model at cell centres · dot: your exact design"


def test_measured_r_close_is_drawn_on_the_10km_row_per_sigma(page):
    for name, want in (("defaults", "1.2049"), ("s15", "1.2303")):
        m = page[name]["map"]
        tick, lab, band = need(m, "map-rclose"), need(m, "map-rclose-label"), need(m, "map-p1")
        assert tick is not None and lab is not None, name
        assert want in text_of(lab) and "measured" in text_of(lab), text_of(lab)
        bx0, bw = float(band["attrs"]["x"]), float(band["attrs"]["width"])
        x = float(tick["attrs"]["x1"])
        assert bx0 < x < bx0 + bw, (name, x, bx0, bw)  # r_close lies inside the registered band
        # the tick spans the row; the label sits above it, off the row it annotates
        by0 = float(band["attrs"]["y"])
        assert float(tick["attrs"]["y1"]) < by0 and float(tick["attrs"]["y2"]) > by0 + float(band["attrs"]["height"])
        assert float(lab["attrs"]["y"]) + 6 < by0, (lab["attrs"], by0)
    # the tick moves with sigma (1.2303 > 1.2049)
    assert float(need(page["s15"]["map"], "map-rclose")["attrs"]["x1"]) > float(
        need(page["defaults"]["map"], "map-rclose")["attrs"]["x1"])


def test_cell_centre_pair_dot_cell_matches_verdict(page):
    held, frz = page["cell13"], page["cell14"]
    ch, cf = cell_under_dot(held["map"]), cell_under_dot(frz["map"])
    assert (ch["attrs"]["data-i"], ch["attrs"]["data-j"]) == ("13", "44")
    assert (cf["attrs"]["data-i"], cf["attrs"]["data-j"]) == ("14", "44")
    assert ch["attrs"]["data-class"] == verdict_class(held["summary"]) == "HELD", held[
        "summary"
    ]
    assert cf["attrs"]["data-class"] == verdict_class(frz["summary"]) == "FREEZE", frz[
        "summary"
    ]
    assert ch["attrs"]["fill"] != cf["attrs"]["fill"]


# (c) ------------------------------------------------------------------------------------------
def frame(tree):
    f = by_id(tree, "map-frame")
    assert f is not None, "no #map-frame"
    a = f["attrs"]
    return (
        float(a["x"]),
        float(a["y"]),
        float(a["x"]) + float(a["width"]),
        float(a["y"]) + float(a["height"]),
    )


def test_dot_clamps_visibly_to_the_map_edge_at_slider_extremes(page):
    # positive control: at the defaults the dot is strictly inside and not marked
    d0, (x0, y0, x1, y1) = dot(page["defaults"]["map"]), frame(page["defaults"]["map"])
    assert d0["attrs"]["data-clamped"] == "false"
    assert x0 < float(d0["attrs"]["cx"]) < x1 and y0 < float(d0["attrs"]["cy"]) < y1
    assert by_id(page["defaults"]["map"], "map-clamp") is None
    # low corner: r 0.5 AU, R 10 m -> left, bottom
    lo = dot(page["low"]["map"])
    assert lo["attrs"]["data-clamped"] == "true"
    assert (float(lo["attrs"]["cx"]), float(lo["attrs"]["cy"])) == (x0, y1)
    assert by_id(page["low"]["map"], "map-clamp") is not None
    # high corner: r 100 AU, R 100 km -> right, top
    hi = dot(page["high"]["map"])
    assert hi["attrs"]["data-clamped"] == "true"
    assert (float(hi["attrs"]["cx"]), float(hi["attrs"]["cy"])) == (x1, y0)
    assert by_id(page["high"]["map"], "map-clamp") is not None


# (d) ------------------------------------------------------------------------------------------
def test_p2_band_on_sigma_07_only_and_p1_always(page):
    s07, s15 = page["defaults"]["map"], page["s15"]["map"]
    assert by_id(s07, "map-p2") is not None  # positive control
    assert by_id(s15, "map-p2") is None
    for tree in (s07, s15):
        assert by_id(tree, "map-p1") is not None
        assert "[1.19, 1.27] AU" in text_of(by_id(tree, "map-p1-label"))
    assert "[60, 300] km" in text_of(by_id(s07, "map-p2-label"))
    # (fix round 1) off sigma 0.7 the legend says where P2 lives; on sigma 0.7 the band does
    assert by_id(s07, "map-p2-note") is None
    note = by_id(s15, "map-p2-note")
    assert note is not None and text_of(note) == "P2 registered at σ 0.7"


def test_title_names_the_slice_and_the_no_design_key_is_always_present(page):
    t07, t15 = (
        text_of(by_id(page["defaults"]["map"], "map-title")),
        text_of(by_id(page["s15"]["map"], "map-title")),
    )
    assert "σ 0.7 MPa" in t07 and "σ 1.5 MPa" in t15, (t07, t15)
    # the data: organism does not change the map (algal and vascular slices are identical)
    tv = text_of(by_id(page["vascular"]["map"], "map-title"))
    assert "vascular" in tv, tv
    # (Task 5 fix round, N8) the same-map note moved from the title to the legend line
    assert "same map for algal and vascular" in text_of(need(page["vascular"]["map"], "map-legend"))
    for name in ("defaults", "s15"):
        assert by_id(page[name]["map"], "map-key-NO_DESIGN") is not None


# (Task 4) --------------------------------------------------------------------------------------
REGISTERED_LABELS = ("map-p1-label", "map-rclose-label", "map-p2-label")


def test_registered_labels_are_qualified_when_the_design_leaves_the_registered_run(page):
    d = page["defaults"]["map"]
    # positive control: at the registered inputs the labels carry no qualifier and no note
    assert by_id(d, "map-registered-note") is None
    for i in REGISTERED_LABELS:
        assert not text_of(by_id(d, i)).endswith("†"), text_of(by_id(d, i))
    for name in ("card", "albedo"):
        tree = page[name]["map"]
        note = by_id(tree, "map-registered-note")
        assert note is not None and "registered run" in text_of(note) and text_of(note).startswith("†"), name
        for i in REGISTERED_LABELS:  # still visible, and marked
            assert text_of(by_id(tree, i)).endswith(" †"), (name, text_of(by_id(tree, i)))
        # the note sits below the frame, over no cell
        f = need(tree, "map-frame")["attrs"]
        assert float(note["attrs"]["y"]) - 14 > float(f["y"]) + float(f["height"]), (name, note["attrs"], f)


# (Task 5 fix round) ----------------------------------------------------------------------------
OUTCOME = {"HELD": "confirmed", "FAILED": "falsified"}


def q4_results():
    t = (ROOT / "experiments" / "q4_vessel" / "RESULTS.md").read_text()
    got = dict(re.findall(r"^Q4_(P[12])=(HELD|FAILED)$", t, re.M))
    assert set(got) == {"P1", "P2"}, got
    return got


def run_map(site: Path, scenarios: dict) -> dict:
    node = shutil.which("node")
    assert node, "node is required"
    with tempfile.TemporaryDirectory() as tmp:
        drv = Path(tmp) / "map.cjs"
        drv.write_text(DRIVER)
        proc = subprocess.run([node, str(drv), str(site)], input=json.dumps(scenarios),
                              capture_output=True, text=True, timeout=600)
    assert proc.returncode == 0, proc.stderr
    return json.loads(proc.stdout)


def test_registered_labels_name_the_prediction_outcome_never_held(page):
    want = q4_results()
    for name, rc in (("defaults", "1.2049"), ("s15", "1.2303"), ("card", "1.2049")):
        tree = page[name]["map"]
        texts = {i: text_of(need(tree, i)) for i in REGISTERED_LABELS if by_id(tree, i) is not None}
        assert "map-p1-label" in texts, (name, texts)  # positive control: the labels are drawn
        # a registered label never says HELD: that word is the legend's "your design survives"
        assert not [i for i, t in texts.items() if "HELD" in t], (name, texts)
        p1 = texts["map-p1-label"]
        assert p1.startswith("P1 prediction") and "[1.19, 1.27] AU" in p1, p1
        assert f"— {OUTCOME[want['P1']]} ({rc})" in p1, (p1, want)
    p2 = text_of(need(page["defaults"]["map"], "map-p2-label"))
    assert p2.startswith("P2 prediction") and "[60, 300] km" in p2, p2
    assert f"— {OUTCOME[want['P2']]} (95.6 km)" in p2, (p2, want)


def test_registered_outcome_word_follows_the_recorded_result(tmp_path):
    # the word comes from the recorded result, not from the label: flip P1 in a copy of the
    # built page and the label must say the other word
    site = tmp_path / "site"
    shutil.copytree(ROOT / "site", site)
    v = site / "verdict.js"
    src = v.read_text()
    old = 'P1: "HELD",'
    assert src.count(old) == 1, "Q4_RESULT.P1 not found as recorded"
    v.write_text(src.replace(old, 'P1: "FAILED",'))
    flipped = text_of(need(run_map(site, {"d": []})["d"]["map"], "map-p1-label"))
    assert "— falsified (1.2049)" in flipped and "confirmed" not in flipped, flipped


def plate_of(tree, id_):
    """The white plate haloText draws just before a label: its box (x0, y0, x1, y1)."""
    for n in walk(tree):
        ids = [c["attrs"].get("id") for c in n["children"]]
        if id_ in ids:
            k = ids.index(id_)
            assert k > 0 and n["children"][k - 1]["tag"] == "rect", id_
            a = n["children"][k - 1]["attrs"]
            x, y = float(a["x"]), float(a["y"])
            return (x, y, x + float(a["width"]), y + float(a["height"]))
    raise AssertionError(f"no #{id_}")


def marks_box(tree):
    """The union box of the dot's ring and any clamp arrowheads."""
    d = dot(tree)["attrs"]
    cx, cy = float(d["cx"]), float(d["cy"])
    xs, ys = [cx - 9, cx + 9], [cy - 9, cy + 9]
    c = by_id(tree, "map-clamp")
    for p in [n for n in walk(c)] if c else []:
        for pt in p["attrs"].get("points", "").split():
            x, y = map(float, pt.split(","))
            xs.append(x)
            ys.append(y)
    return (min(xs), min(ys), max(xs), max(ys))


def overlap(a, b):
    return a[0] < b[2] and b[0] < a[2] and a[1] < b[3] and b[1] < a[3]


def test_p2_label_never_under_the_dot_at_the_clamped_corner(page):
    hi, d = page["high"]["map"], page["defaults"]["map"]
    assert by_id(hi, "map-clamp") is not None  # the corner case: dot clamped top right
    lab = plate_of(hi, "map-p2-label")
    assert not overlap(lab, marks_box(hi)), (lab, marks_box(hi))
    # the label sits above the frame, so no in-frame dot position can reach it
    assert lab[3] <= frame(hi)[1] - 15, (lab, frame(hi))
    # positive control: the overlap test sees a real overlap (the label against itself)
    assert overlap(lab, lab) and overlap(plate_of(d, "map-p2-label"), plate_of(d, "map-p2-label"))


def test_registered_bands_have_a_thick_outline_and_p2_marks_its_off_map_part(page):
    tree = page["defaults"]["map"]
    x0, y0, x1, y1 = frame(tree)
    for b in ("map-p1", "map-p2"):
        a = need(tree, b)["attrs"]
        assert a.get("stroke") == "#1b1b1b" and float(a.get("stroke-width", 0)) >= 2.5, (b, a)
        h = need(tree, b + "-halo")["attrs"]  # a white under-stroke, so the outline reads on any cell
        assert h.get("stroke") == "#ffffff" and float(h.get("stroke-width", 0)) >= 5, (b, h)
    # P2's band runs to 300 km; the map stops at 100 km: an arrow at the top edge says so
    arrow = need(tree, "map-p2-offmap")
    pts = [tuple(map(float, p.split(","))) for p in arrow["attrs"]["points"].split()]
    p2 = need(tree, "map-p2")["attrs"]
    xc = float(p2["x"]) + float(p2["width"]) / 2
    assert max(y for _, y in pts) <= y0 and min(y for _, y in pts) < y0 - 6, pts
    assert all(abs(x - xc) <= 8 for x, _ in pts), (pts, xc)
    assert by_id(tree, "map-p1-offmap") is None  # control: P1 lies inside the map


def test_order_note_is_always_on_the_map(page):
    import yaml

    order = yaml.safe_load((ROOT / "experiments" / "q4_vessel" / "prereg.yaml").read_text())["load_order"]
    want = " → ".join(order)
    for name in ("defaults", "s15", "card", "high"):
        t = text_of(need(page[name]["map"], "map-order-note"))
        assert want in t and "first to fail" in t, (name, t)


def test_same_map_note_is_in_the_legend_not_the_title(page):
    v = page["vascular"]["map"]
    assert "same map for algal and vascular" not in text_of(need(v, "map-title"))
    assert "same map for algal and vascular" in text_of(need(v, "map-legend"))


# (Task 5 polish) ---------------------------------------------------------------------------------
def test_p2_off_map_note_is_literal_and_clear_of_the_dot(page):
    hi, d = page["high"]["map"], page["defaults"]["map"]
    assert "off map" not in text_of(need(d, "map-p2-label"))
    note = text_of(need(d, "map-p2-offmap-note"))
    assert "continues above" in note and "100 km" in note, note
    for tree in (hi, d):
        box = plate_of(tree, "map-p2-offmap-note")
        assert not overlap(box, marks_box(tree)) and not overlap(box, plate_of(tree, "map-p2-label")), box
        assert box[3] <= frame(tree)[1] - 15, (box, frame(tree))


def test_registered_marks_are_drawn_above_the_dot(page):
    for name in ("r1.21", "defaults"):
        order = [n["attrs"].get("id") for n in walk(page[name]["map"])]
        k = order.index("map-dot")
        assert order.index("map-rclose") > k and order.index("map-p1") > k, (name, k)


def test_p1_band_mark_is_at_least_12_px_tall(page):
    a = need(page["defaults"]["map"], "map-p1")["attrs"]
    assert float(a["height"]) >= 13, a  # 640-unit viewBox renders at ~0.98 px per unit


def test_off_registered_labels_say_registered_run(page):
    for name in ("card", "albedo"):
        for i in REGISTERED_LABELS:
            t = text_of(need(page[name]["map"], i))
            assert t.endswith("· registered run †"), (name, i, t)
    # positive control: at the registered inputs they do not
    for i in REGISTERED_LABELS:
        assert "registered run" not in text_of(need(page["defaults"]["map"], i))


def test_crosshair_runs_under_the_band_labels_and_the_dot_over_them(page):
    # the P1/r_close label plates span the dot's column at the defaults (1 AU): the dashed
    # crosshair must not strike through them, and they must not hide the dot
    for name in ("defaults", "card", "r1.21"):
        nodes = list(walk(page[name]["map"]))
        order = [n["attrs"].get("id") for n in nodes]
        cross = [k for k, n in enumerate(nodes) if n["attrs"].get("data-mark") == "crosshair"]
        assert len(cross) == 2, (name, len(cross))  # positive control: the crosshair is drawn
        lab = min(order.index("map-p1-label"), order.index("map-rclose-label"))
        assert max(cross) < lab < order.index("map-dot"), (name, cross, lab, order.index("map-dot"))


# (Task 5 critic r3) -----------------------------------------------------------------------------
def test_p1_mark_over_the_dot_is_hollow(page):
    for name in ("r1.21", "defaults"):
        tree = page[name]["map"]
        order = [n["attrs"].get("id") for n in walk(tree)]
        box, tick = need(tree, "map-p1")["attrs"], need(tree, "map-rclose")["attrs"]
        # over the dot: stroke only, nothing filled across the dot
        assert box.get("fill") == "none", box
        # the white under-stroke stays under the dot, so it cannot cover the dot's fill
        assert order.index("map-p1-halo") < order.index("map-dot") < order.index("map-p1"), name
        # the tick is drawn outside the box only: a dash, a gap the box's height, a dash
        dash = [float(v) for v in tick.get("stroke-dasharray", "").replace(",", " ").split()]
        assert len(dash) == 3 and dash[1] >= float(box["height"]) - 1e-6, (tick, box["height"])


def test_p1_labels_sit_off_the_held_band(page):
    for name in ("defaults", "s15"):
        tree = page[name]["map"]
        held = [c for c in cells(tree) if c["attrs"]["data-class"] == "HELD"]
        assert held, name  # positive control: the band is there
        for lid in ("map-p1-label", "map-rclose-label"):
            p = plate_of(tree, lid)
            hit = [(c["attrs"]["data-i"], c["attrs"]["data-j"]) for c in held if overlap(p, (
                float(c["attrs"]["x"]), float(c["attrs"]["y"]),
                float(c["attrs"]["x"]) + float(c["attrs"]["width"]), float(c["attrs"]["y"]) + float(c["attrs"]["height"])))]
            assert not hit, (name, lid, p, hit[:5])
