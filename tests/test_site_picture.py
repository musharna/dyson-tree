"""M3 acceptance, on the BUILT page: the cross-section picture (spec §5 "The picture", §8 M3, §9 risk 3).

Loads the scripts site/index.html loads into a node `vm` context with a minimal DOM that
supports createElementNS/appendChild, drives the controls the way the page does, and reads
the picture back as the element tree the page built under #pic (attributes and text), never
from picture.js's intent. Pixel geometry in a real browser is tools/smoke_page.py's job.

Every assertion is paired with a positive control in the same test (a state where the thing
must appear, beside the state where it must not). Fails, never skips, without node or bash.
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
LINES = ["BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE"]

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const site = process.argv[2];
const scenarios = JSON.parse(fs.readFileSync(0, "utf8"));
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const ids = new Set([...html.matchAll(/\sid="([^"]+)"/g)].map((m) => m[1]));
const srcs = [...html.matchAll(/<script src="\.\/([^"]+)"><\/script>/g)].map((m) => m[1]);
const LINES = ["BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE"];
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
      if (!els.has(id)) els.set(id, mk(id === "pic" ? "svg" : "div", id));
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
  const g = (id) => { const e = document.getElementById(id); if (!e) throw new Error("no #" + id); return e.textContent; };
  const out = { lines: {}, tR: g("v-tR"), pic: dump(document.getElementById("pic")) };
  for (const n of LINES) out.lines[n] = { status: g("v-status-" + n), cmp: g("v-cmp-" + n) };
  return out;
}
const res = {};
for (const [name, steps] of Object.entries(scenarios)) res[name] = run(steps);
process.stdout.write(JSON.stringify(res));
"""

T50 = "1.69897"  # log10(50 m)
SCENARIOS = {
    "defaults": [],
    "t50": [{"id": "v-t-mode", "value": "manual"}, {"id": "v-t", "value": T50}],
    "freeze": [{"id": "v-R", "value": "4"}, {"id": "v-r", "value": "0.0828"}],
    "burst": [{"id": "v-p-mode", "value": "manual"}, {"id": "v-p", "value": "3.35"}],
    "boil": [{"id": "v-p-mode", "value": "manual"}, {"id": "v-p", "value": "3.25"}],
    "opaque": [{"id": "v-t-mode", "value": "manual"}, {"id": "v-t", "value": "2"}],
    "P2_edge": [{"id": "v-R", "value": "4.98027"}],
    # (Task 5 fix round) the far corner: r 100 AU, R 100 km, where the true band is far below 1 px
    "far": [{"id": "v-R", "value": "5"}, {"id": "v-r", "value": "2"}],
}
GESTURE = {"freeze": "FREEZE", "burst": "BURST", "boil": "BOIL", "opaque": "OPAQUE"}


def walk(node):
    yield node
    for c in node["children"]:
        yield from walk(c)


def by_id(pic, id_):
    hits = [n for n in walk(pic) if n["attrs"].get("id") == id_]
    assert len(hits) <= 1, (id_, len(hits))
    return hits[0] if hits else None


def text_of(node):
    return node["text"] + "".join(text_of(c) for c in node["children"])


def overlays(pic):
    g = by_id(pic, "pic-overlays")
    assert g is not None, "no #pic-overlays group"
    return sorted(c["attrs"]["data-line"] for c in g["children"])


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
    return json.loads(proc.stdout)


def radii(pic):
    o, i = by_id(pic, "pic-outer"), by_id(pic, "pic-inner")
    assert o is not None and i is not None, "outer/inner circles missing"
    return float(o["attrs"]["r"]), float(i["attrs"]["r"])


def test_unclamped_band_ratio_equals_readout_t_over_R(page):
    r = page["t50"]
    tR = num(r["tR"])
    assert round(tR, 3) == 0.050, r["tR"]
    ro, ri = radii(r["pic"])
    assert round((ro - ri) / ri, 2) == round(tR, 2), (ro, ri, tR)
    assert by_id(r["pic"], "pic-clamp") is None, (
        "clamp label shown on an unclamped wall"
    )
    # positive control: at the defaults the true band would be sub-pixel, so the drawn
    # ratio must NOT equal t/R there and the clamp label must be present
    d = page["defaults"]
    ro_d, ri_d = radii(d["pic"])
    assert abs((ro_d - ri_d) / ri_d - num(d["tR"])) > 1e-3


def test_defaults_clamp_is_active_and_labelled(page):
    d = page["defaults"]
    # spec §8 prints 1.45e-3 (normal-incidence t_min 1.453 m); the shell-law page has t_min 1.400 m
    assert abs(num(d["tR"]) - 1.400e-3) < 5e-7, d["tR"]
    clamp = by_id(d["pic"], "pic-clamp")
    assert clamp is not None, "no clamp label at the defaults"
    t = text_of(clamp)
    assert "clamped" in t and "1.4" in t, t
    # positive control: the same label is absent at the unclamped state
    assert by_id(page["t50"]["pic"], "pic-clamp") is None


@pytest.mark.parametrize("gesture", sorted(GESTURE))
def test_each_overlay_appears_exactly_when_its_line_is_violated(page, gesture):
    d = page["defaults"]
    assert overlays(d["pic"]) == [], overlays(d["pic"])
    r = page[gesture]
    violated = [n for n in LINES if r["lines"][n]["status"] == "VIOLATED"]
    assert violated == [GESTURE[gesture]], violated
    assert overlays(r["pic"]) == violated
    # the number that killed it is printed beside the wound, and it is the panel's number
    g = by_id(r["pic"], "pic-ov-" + GESTURE[gesture])
    label = text_of(g)
    cmp = r["lines"][GESTURE[gesture]]["cmp"].split(" — ")[0]
    assert cmp and cmp in label, (label, cmp)
    # and no other overlay carries a label
    others = [n for n in LINES if n != GESTURE[gesture] and by_id(r["pic"], "pic-ov-" + n)]
    assert others == [], others


def test_organism_saturation_tracks_net_over_amax(page):
    def sat(r):
        disc = by_id(r["pic"], "pic-organism")
        assert disc is not None
        return float(disc["attrs"]["data-saturation"])

    d, e = page["defaults"], page["P2_edge"]
    # net 8.23 and 3.11 µmol at a_max 10: saturation is net / a_max
    assert sat(d) == pytest.approx(0.823, abs=2e-3)
    assert sat(e) == pytest.approx(0.311, abs=2e-3)


def test_interior_blue_shifts_as_the_wall_thickens(page):
    def rgb(r):
        n = by_id(r["pic"], "pic-inner")
        assert n is not None, "no #pic-inner"
        fill = n["attrs"]["fill"]
        m = re.fullmatch(r"rgb\((\d+), (\d+), (\d+)\)", fill)
        assert m, fill
        return [int(x) for x in m.groups()]

    thin, thick = rgb(page["defaults"]), rgb(page["opaque"])
    # blue's share of the colour rises and the interior darkens (f_photon falls)
    assert thick[2] / sum(thick) > thin[2] / sum(thin) + 0.02, (thin, thick)
    assert sum(thick) < sum(thin), (thin, thick)


def test_svg_is_accessible(page):
    pic = page["defaults"]["pic"]
    kids = [c["tag"] for c in pic["children"]]
    assert "title" in kids and "desc" in kids, kids
    desc = text_of(next(c for c in pic["children"] if c["tag"] == "desc"))
    assert "t/R" in desc, desc


# (Task 5 fix round) the clamp note is a drawing note, not a verdict: neutral grey, and a size
# far below a pixel is said as such, never as "0.00 px"
def test_clamp_note_is_neutral_and_says_sub_pixel_honestly(page):
    d, far = by_id(page["defaults"]["pic"], "pic-clamp"), by_id(page["far"]["pic"], "pic-clamp")
    assert d is not None and far is not None
    assert d["attrs"].get("fill") == "#5d5d5d", d["attrs"]
    # positive control: at the defaults the true band is a printable fraction of a pixel
    assert re.search(r"would draw 0\.\d\d px", text_of(d)), text_of(d)
    t = text_of(far)
    assert "would draw ≪ 1 px" in t and "0.00 px" not in t, t


def test_clamp_note_prints_t_over_r_once_and_quietly(page):
    # (Task 5 polish) the clamp note carries t/R; the footer does not repeat it; note at 13 px
    for name in ("defaults", "far"):
        pic = page[name]["pic"]
        t = " ".join(text_of(n) for n in walk(pic) if n["tag"] == "text")  # what is drawn, not <title>
        clamp = by_id(pic, "pic-clamp")
        assert clamp is not None, name
        m = re.search(r"t/R (\d\.\d\de-?\d+)", text_of(clamp))
        assert m, text_of(clamp)
        assert t.count("t/R " + m.group(1)) == 1, (name, t.count("t/R " + m.group(1)))
        assert clamp["attrs"].get("font-size") == "13", name
    # positive control: unclamped, the footer still prints t/R
    assert "t/R " in text_of(page["t50"]["pic"])
