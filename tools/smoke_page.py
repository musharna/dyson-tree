#!/usr/bin/env python3
"""Headless browser smoke test for site/ — the artifact that gets published.

Checks the SHIPPED directory, not web/, because site/ is what GitHub Pages
serves. Runs the page twice: once from `file://` and once from an http subpath
(`/dyson-tree/`), because Pages serves this project from a subpath and a page
that only works at a server root would 404 there.

Displayed numbers are compared against web/fixtures.json — the same reference
the Python/JS parity test uses — so the page is pinned to the Python model, not
merely to itself.

Fails loudly if playwright or its chromium build is missing; it never skips.

Run: python3 tools/smoke_page.py
"""

from __future__ import annotations

import http.server
import json
import re
import signal
import socketserver
import sys
import threading
from pathlib import Path

signal.signal(
    signal.SIGALRM,
    lambda *_: (sys.stderr.write("aborting: walltime guard (300s)\n"), sys.exit(2)),
)
signal.alarm(300)

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
FIXTURES = json.loads((ROOT / "web" / "fixtures.json").read_text())
SUBPATH = "dyson-tree"

failures: list[str] = []
notes: list[str] = []


def check(ok: bool, msg: str) -> None:
    (notes if ok else failures).append(("PASS  " if ok else "FAIL  ") + msg)


def tol(quantity: str) -> tuple[float, float]:
    t = FIXTURES["tolerances"][quantity]
    return float(t["rtol"]), float(t["atol"])


def number_in(text: str) -> float:
    m = re.search(r"-?\d+\.\d+", text)
    assert m, f"no number in {text!r}"
    return float(m.group(0))


def serve(directory: Path):
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(  # noqa: E731
        *a, directory=str(directory), **kw
    )
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, httpd.server_address[1]


def check_plot_geometry(page, label: str) -> None:
    """No two plot labels overlap, and none falls outside the viewBox.

    Measured with getBoundingClientRect, NOT getBBox: getBBox reports geometry
    BEFORE the element's own transform, so the rotated y-axis title measured as
    sitting at x=-77 and read as both off-canvas and overlapping a tick label.
    Client rects are what the reader sees, converted back to viewBox units.

    Called once per preset. Two earlier versions of this check were weaker in
    ways that passed a broken page: a fixed 62px x-threshold (labels ~90-200px
    wide ran together anyway), and running only before the preset was switched,
    so the algal layout -- whose crossover labels sat on the x-axis tick
    numbers -- was never measured at all.
    """
    boxes = page.eval_on_selector_all(
        "#plot text",
        """els => {
             const svg = document.getElementById("plot");
             const vb = svg.viewBox.baseVal;
             const s = svg.getBoundingClientRect();
             const sx = vb.width / s.width, sy = vb.height / s.height;
             return els.map(e => { const b = e.getBoundingClientRect();
               return {x: (b.left - s.left) * sx, y: (b.top - s.top) * sy,
                       w: b.width * sx, h: b.height * sy, t: e.textContent}; });
           }""",
    )
    labels = [b for b in boxes if b["t"].startswith("k=")]
    check(len(labels) == 3, f"[{label}] all three registered-k crossovers are labelled, got {len(labels)}")

    def overlaps(a, b, pad=1.0):
        return (
            a["x"] < b["x"] + b["w"] + pad
            and b["x"] < a["x"] + a["w"] + pad
            and a["y"] < b["y"] + b["h"] + pad
            and b["y"] < a["y"] + a["h"] + pad
        )

    collide = [
        f"{a['t']!r} x {b['t']!r}"
        for i, a in enumerate(boxes)
        for b in boxes[i + 1 :]
        if overlaps(a, b)
    ]
    check(not collide, f"[{label}] no two plot labels overlap: {collide}")

    VIEW_W, VIEW_H = 720.0, 400.0
    outside = [
        f"{b['t']!r} at x={b['x']:.1f}..{b['x'] + b['w']:.1f} y={b['y']:.1f}..{b['y'] + b['h']:.1f}"
        for b in boxes
        if b["x"] < 0 or b["x"] + b["w"] > VIEW_W or b["y"] < 0 or b["y"] + b["h"] > VIEW_H
    ]
    check(not outside, f"[{label}] every plot label is inside the 720x400 viewBox: {outside}")

    check(
        any("model output" in b["t"] for b in boxes),
        f"[{label}] the measured crossover is labelled 'model output' on the plot itself",
    )


def exercise(page, label: str) -> None:
    """Every assertion that does not depend on how the page was loaded."""
    check(page.locator("#preset").input_value() == "vascular", f"[{label}] default preset is vascular")
    check(page.locator("#kselect").input_value() == "100", f"[{label}] default k is the registered 100")

    ref = FIXTURES["cases"]["vascular"]["per_k"]["100.0"]["crossover_au"]
    shown = number_in(page.locator("#out-xover").inner_text())
    rtol, atol = tol("crossover_au")
    ok = abs(shown - ref) <= max(atol + rtol * abs(ref), 5e-5)
    check(ok, f"[{label}] displayed r* {shown} matches fixture {ref} (displayed to 4 dp)")

    ic_ref = FIXTURES["cases"]["vascular"]["per_k"]["100.0"]["compensation_irradiance"]
    ic_shown = number_in(page.locator("#out-ic").inner_text())
    check(abs(ic_shown - ic_ref) <= 5e-5, f"[{label}] displayed I_c {ic_shown} matches fixture {ic_ref}")

    check("inside" in page.locator("#out-band").inner_text(), f"[{label}] vascular k=100 reported inside its band")

    # The distance the page DISPLAYS must be the distance it EVALUATED. The
    # slider maps an integer position through a log scale, so the default
    # position landed at 0.99987 AU while the label said "1.000 AU" -- and
    # T_eq and the irradiance beside it were computed at 0.99987, disagreeing
    # with this repository's own published T_eq at 1 AU in the second decimal.
    # Nothing here caught it: the earlier version of this file checked only
    # #out-xover and #out-ic, and neither depends on the slider.
    consts = FIXTURES["constants"]

    def expect_at(r_au, area_ratio):
        par = consts["TSI_W_M2"] / (r_au * r_au) * consts["PAR_FRACTION"] * consts["PHOTONS_PER_J"]
        s_flux = consts["TSI_W_M2"] / (r_au * r_au)
        t_eq = (s_flux / (area_ratio * 1.0 * consts["SIGMA_W_M2_K4"])) ** 0.25
        return par, t_eq

    def net_carbon_at(r_au, preset, k):
        """Closed form of Organism.net_carbon, from the fixture's own preset."""
        i = consts["TSI_W_M2"] / (r_au * r_au) * consts["PAR_FRACTION"] * consts["PHOTONS_PER_J"]
        gross = preset["a_max"] * i / (i + k)
        return gross - preset["r_d"] / preset["leaf_mass_ratio"]

    def check_readouts_agree_with_displayed_distance(tag, cls):
        preset = FIXTURES["cases"][cls]["preset"]
        area_ratio = preset["area_ratio"]
        k = float(page.locator("#kselect").input_value())
        r_shown = number_in(page.locator("#out-r").inner_text())
        par_shown = number_in(page.locator("#out-i").inner_text())
        teq_shown = number_in(page.locator("#out-teq").inner_text())
        par_want, teq_want = expect_at(r_shown, area_ratio)

        # The slider's own label must agree with the readout it drives. Without
        # this, hard-coding #rlabel to a constant leaves every assertion green
        # while the control lies at every position.
        check(
            page.locator("#rlabel").inner_text().strip() == page.locator("#out-r").inner_text().strip(),
            f"[{label}] {tag}: slider label {page.locator('#rlabel').inner_text()!r} must match "
            f"the readout {page.locator('#out-r').inner_text()!r}",
        )

        # Net carbon, recomputed from the fixture preset rather than trusted.
        net_shown = number_in(page.locator("#out-net").inner_text())
        net_want = net_carbon_at(r_shown, preset, k)
        check(
            abs(net_shown - net_want) <= 5e-4,
            f"[{label}] {tag}: net carbon {net_shown} must match {net_want:.4f} at the "
            f"displayed distance {r_shown}, k={k:g}",
        )

        # I_c depends on the SELECTED k, so it is re-checked on every view rather
        # than once for the default.
        ic_shown = number_in(page.locator("#out-ic").inner_text())
        ic_want = k * preset["r_d"] / (preset["a_max"] - preset["r_d"])
        check(
            abs(ic_shown - ic_want) <= 5e-4,
            f"[{label}] {tag}: I_c {ic_shown} must match {ic_want:.4f} for {cls} k={k:g}",
        )
        check(
            abs(par_shown - par_want) <= 5e-3,
            f"[{label}] {tag}: PAR {par_shown} must match {par_want:.4f}, the value at the "
            f"DISPLAYED distance {r_shown}",
        )
        check(
            abs(teq_shown - teq_want) <= 5e-3,
            f"[{label}] {tag}: T_eq {teq_shown} must match {teq_want:.4f}, the value at the "
            f"DISPLAYED distance {r_shown}",
        )

    check_readouts_agree_with_displayed_distance("default", "vascular")

    # The marked point must sit where the axis says that distance is. At exactly
    # 1.000 AU the marker's x must equal the x of the "1" tick label -- a
    # cross-check inside the page, so a marker drawn at the wrong distance
    # cannot pass by merely having moved.
    marker_cx = float(page.locator("#marker").get_attribute("cx"))
    tick_x = page.eval_on_selector_all(
        "#plot text",
        """els => { const t = els.find(e => e.textContent === "1");
                    return t ? Number(t.getAttribute("x")) : null; }""",
    )
    check(
        tick_x is not None and abs(marker_cx - tick_x) <= 0.5,
        f"[{label}] at 1.000 AU the plot marker (x={marker_cx}) sits on the '1' tick "
        f"(x={tick_x})",
    )

    # ...and at the default the distance must be exactly 1 AU, where this
    # repository publishes T_eq in two gates.csv files and in the fixtures.
    r_default = number_in(page.locator("#out-r").inner_text())
    check(r_default == 1.0, f"[{label}] the default distance is exactly 1.000 AU, got {r_default}")
    teq_default = number_in(page.locator("#out-teq").inner_text())
    teq_ref = FIXTURES["cases"]["vascular"]["adapted_t_opt_home_1au"]
    check(
        abs(teq_default - teq_ref) <= 5e-3,
        f"[{label}] vascular T_eq at 1 AU is {teq_default}, fixtures say {teq_ref}",
    )

    panel = page.locator("aside.isnot")
    check(panel.is_visible(), f"[{label}] 'What this is / is not' panel is visible")
    ptext = panel.inner_text()
    for phrase in ("pressure vessel", "spectral wall", "category error", "falsified"):
        check(phrase in ptext, f"[{label}] limitations panel mentions '{phrase}'")

    body_all = page.locator("body").inner_text()
    check("Jaret Arnold" in body_all, f"[{label}] the page names its copyright holder")
    check("MIT" in body_all and "CC BY 4.0" in body_all, f"[{label}] the page states both licences")

    # ...and the licence links must RESOLVE. Naming a licence the reader cannot
    # open is the same defect as not naming one: dropping the copy step from
    # tools/build_site.sh ships two 404s and is otherwise invisible.
    for sel, want in (('a[href="./LICENSE"]', "MIT License"),
                      ('a[href="./LICENSE-docs"]', "Creative Commons")):
        href = page.locator(sel).first.get_attribute("href")
        target = (SITE / href.replace("./", "")).resolve()
        ok = target.is_file() and want in target.read_text()
        check(ok, f"[{label}] {href} resolves inside site/ and is the {want} text")

    legend = page.locator(".legend").inner_text()
    check(
        "pre-registered band (Q1) — vascular: HELD · algal: FAILED" in legend,
        f"[{label}] legend carries the exact registered-band text",
    )
    check("model output" in legend, f"[{label}] legend labels the model output")

    # The micro sign trap: `text-transform: uppercase` maps U+00B5 MICRO SIGN to
    # U+039C GREEK CAPITAL MU, which renders as a Latin M -- so a correct DOM and
    # a correct test on the DOM can both be green while the page shows the reader
    # "MMOL", off by a factor of 1000. Assert on the RENDERED text.
    body_text = page.locator("body").inner_text()
    mu = "\u039c"
    check(mu not in body_text, f"[{label}] no rendered text contains GREEK CAPITAL MU (uppercased micro sign)")
    klabel = page.locator('label[for="kselect"]').inner_text()
    check("µmol" in klabel, f"[{label}] the k label renders a micro sign, got {klabel!r}")

    check_plot_geometry(page, label + " vascular")

    # -- moving the slider changes the marked value --
    before_r = page.locator("#out-r").inner_text()
    before_marker = page.locator("#marker").get_attribute("cx")
    page.locator("#rslider").fill("7000")
    page.locator("#rslider").dispatch_event("input")
    after_r = page.locator("#out-r").inner_text()
    after_marker = page.locator("#marker").get_attribute("cx")
    check(before_r != after_r, f"[{label}] slider changes the reported distance ({before_r} -> {after_r})")
    check(before_marker != after_marker, f"[{label}] slider moves the plot marker ({before_marker} -> {after_marker})")
    net_far = number_in(page.locator("#out-net").inner_text())
    check(net_far < 0, f"[{label}] far from the Sun net carbon is negative, got {net_far}")
    check_readouts_agree_with_displayed_distance("slider moved", "vascular")
    page.locator("#rslider").fill("10000")
    page.locator("#rslider").dispatch_event("input")
    r_max_shown = number_in(page.locator("#out-r").inner_text())
    check(r_max_shown == 100.0, f"[{label}] the slider maximum is exactly 100.000 AU, got {r_max_shown}")
    check_readouts_agree_with_displayed_distance("slider at maximum", "vascular")
    check_plot_geometry(page, label + " vascular, slider moved")
    page.locator("#rslider").fill("1308")
    page.locator("#rslider").dispatch_event("input")

    # -- both presets render --
    page.select_option("#preset", "algal")
    ks = page.locator("#kselect option").all_inner_texts()
    check(
        [k.split(" ")[0] for k in ks] == ["10", "20", "40"],
        f"[{label}] algal offers exactly the registered k grid, got {ks}",
    )
    algal_ref = FIXTURES["cases"]["algal"]["per_k"]["20.0"]["crossover_au"]
    algal_shown = number_in(page.locator("#out-xover").inner_text())
    check(
        abs(algal_shown - algal_ref) <= 5e-5,
        f"[{label}] algal k=20 displayed r* {algal_shown} matches fixture {algal_ref}",
    )
    check(
        "OUTSIDE" in page.locator("#out-band").inner_text(),
        f"[{label}] algal k=20 is reported OUTSIDE its pre-registered band",
    )
    check(page.locator("#plot path").count() >= 1, f"[{label}] algal curve is drawn")
    check_readouts_agree_with_displayed_distance("algal", "algal")
    algal_teq = number_in(page.locator("#out-teq").inner_text())
    algal_teq_ref = FIXTURES["cases"]["algal"]["adapted_t_opt_home_1au"]
    check(
        abs(algal_teq - algal_teq_ref) <= 5e-3,
        f"[{label}] algal T_eq at 1 AU is {algal_teq}, fixtures (and both gates.csv) say "
        f"{algal_teq_ref}",
    )
    check_plot_geometry(page, label + " algal")

    # -- a non-default k still agrees with the fixture --
    page.select_option("#kselect", "40")
    k40_ref = FIXTURES["cases"]["algal"]["per_k"]["40.0"]["crossover_au"]
    k40_shown = number_in(page.locator("#out-xover").inner_text())
    check(
        abs(k40_shown - k40_ref) <= 5e-5,
        f"[{label}] algal k=40 displayed r* {k40_shown} matches fixture {k40_ref}",
    )
    check(
        "inside" in page.locator("#out-band").inner_text(),
        f"[{label}] algal k=40 is reported inside the band (the one k that was)",
    )
    check_readouts_agree_with_displayed_distance("algal k=40", "algal")

    page.select_option("#preset", "vascular")
    check(page.locator("#plot path").count() >= 1, f"[{label}] vascular curve is drawn")


VLINES = ("BURST", "FREEZE", "BOIL", "STARVE", "OPAQUE")


def exercise_vessel(page, label: str) -> None:
    """M2: the verdict panel in a real browser (spec §8 M2, §5), plus input latency."""

    def settle():
        page.wait_for_function(
            "() => !['v-rauto','v-Rwin'].some(i => document.getElementById(i).textContent.includes('computing'))",
            timeout=60000,
        )

    def violated():
        return [n for n in VLINES if page.locator(f"#v-status-{n}").inner_text().strip() == "VIOLATED"]

    def set_range(sel, value):
        page.locator(sel).fill(str(value))
        page.locator(sel).dispatch_event("input")

    def reload():
        page.reload(wait_until="load")
        settle()

    settle()
    check(violated() == [], f"[{label}] vessel defaults: every line HOLDS, got {violated()}")
    for n in ("FREEZE", "STARVE", "OPAQUE"):
        m = page.locator(f"#v-margin-{n}").inner_text()
        check(number_in(m.replace("−", "-")) > 0 and m.startswith("+"), f"[{label}] default {n} margin positive: {m!r}")
    for n in ("BURST", "BOIL"):
        m = page.locator(f"#v-margin-{n}").inner_text()
        check(m.startswith("0 ") and "by construction" in m, f"[{label}] default {n} margin 0 by construction: {m!r}")
    rauto = page.locator("#v-rauto").inner_text()
    check("1.2805" in rauto, f"[{label}] auto-path edge in r at the defaults is 1.2805 AU: {rauto!r}")
    rwin = page.locator("#v-Rwin").inner_text()
    notes.append(f"NOTE  [{label}] defaults: R_window {rwin}; r edges {rauto}; "
                 f"edge compute {page.locator('#v-edge-ms').inner_text()} ms")
    check(page.locator("#v-summary").get_attribute("aria-live") == "polite", f"[{label}] verdict summary is a polite live region")
    unlabelled = page.eval_on_selector_all(
        "#vessel input, #vessel select",
        "els => els.filter(e => !(e.labels && e.labels.length) && !e.getAttribute('aria-label')).map(e => e.id)",
    )
    check(not unlabelled, f"[{label}] every vessel control has a label: {unlabelled}")

    # input-to-readout latency: dragging r, the five lines are recomputed synchronously
    lat = page.evaluate(
        """() => { const s = document.getElementById('v-r'); const out = [];
                   for (let i = 0; i < 40; i++) { s.value = Math.log10(1.05 + i * 0.005).toFixed(4);
                     const t0 = performance.now(); s.dispatchEvent(new Event('input'));
                     void document.getElementById('v-status-FREEZE').textContent;
                     out.push(performance.now() - t0); }
                   out.sort((a, b) => a - b);
                   return {median: out[20], max: out[39]}; }"""
    )
    notes.append(f"NOTE  [{label}] r-drag input-to-readout latency: median {lat['median']:.1f} ms, max {lat['max']:.1f} ms (40 inputs)")
    check(lat["max"] < 100, f"[{label}] r-drag input-to-readout under 100 ms (max {lat['max']:.1f} ms)")

    # spec §5: the distance slider spans 0.5 to 100 AU (the M2 page stopped at 0.9 to 3)
    reload()
    for end, want in (("min", "0.500 AU"), ("max", "100.000 AU")):
        lim = page.locator("#v-r").get_attribute(end)
        set_range("#v-r", lim)
        settle()
        got = page.locator("#v-r-out").inner_text().strip()
        err = page.locator("#v-error").inner_text().strip()
        check(got == want and not err, f"[{label}] r slider {end} reads {want} with no error (got {got!r}, error {err!r})")

    reload()
    set_range("#v-R", 4)
    set_range("#v-r", 0.0792)
    check(violated() == [], f"[{label}] R 10 km, r 1.20 AU: all hold, got {violated()}")
    set_range("#v-r", 0.0828)
    check(violated() == ["FREEZE"], f"[{label}] R 10 km, r 1.21 AU (past r_close 1.2049): exactly FREEZE, got {violated()}")

    reload()
    page.select_option("#v-p-mode", "manual")
    set_range("#v-p", 3.35)
    check(violated() == ["BURST"], f"[{label}] manual p 2239 Pa > p*: exactly BURST, got {violated()}")
    set_range("#v-p", 3.25)
    check(violated() == ["BOIL"], f"[{label}] manual p 1778 Pa < p_sat: exactly BOIL, got {violated()}")

    reload()
    page.select_option("#v-t-mode", "manual")
    set_range("#v-t", 2)
    check(violated() == ["OPAQUE"], f"[{label}] manual t 100 m: exactly OPAQUE, got {violated()}")
    check(page.locator("#v-t-out").inner_text().startswith("100.000 m"), f"[{label}] t label reads 100 m: {page.locator('#v-t-out').inner_text()!r}")
    settle()
    reload()

    # M2b: the deck (§12). Badges render; playing antifreeze 1.3 K moves the R 10 km edge.
    check(page.locator("#deck-0-badge").inner_text() == "DEMONSTRATED", f"[{label}] antifreeze badge DEMONSTRATED")
    check(page.locator("#deck-1-badge").inner_text() == "DECLARED", f"[{label}] respiration badge DECLARED")
    check(page.locator("#deck-0-count option").count() == 4, f"[{label}] antifreeze stacks 0-3 cards")
    set_range("#v-R", 4)
    set_range("#v-r", 0.0828)
    check(violated() == ["FREEZE"], f"[{label}] deck: no card, R 10 km, r 1.21: FREEZE, got {violated()}")
    page.select_option("#deck-0-count", "1")
    set_range("#deck-0-value", 1.3)
    check(violated() == [], f"[{label}] deck: antifreeze 1.3 K, r 1.21: all hold, got {violated()}")
    settle()
    rauto = page.locator("#v-rauto").inner_text()
    check("1.2197" in rauto, f"[{label}] deck: antifreeze 1.3 K edge 1.2197 AU: {rauto!r}")
    page.select_option("#deck-0-count", "2")
    set_range("#deck-0-value", 0.8)
    st = page.locator("#deck-status").inner_text()
    check("CLIPPED" in st and "1.3" in st, f"[{label}] deck: 2 x 0.8 K clipped at 1.3, printed: {st!r}")
    check(page.locator("#deck-status").get_attribute("aria-live") == "polite", f"[{label}] deck status is a polite live region")
    settle()
    reload()

SHOTS = ROOT / "docs" / "m3_shots"


def exercise_picture(page, label: str, shoot: bool) -> None:
    """M3: the cross-section, measured from the RENDERED DOM (spec §8 M3, §9 risk 3)."""

    def settle():
        page.wait_for_function(
            "() => !['v-rauto','v-Rwin'].some(i => document.getElementById(i).textContent.includes('computing'))",
            timeout=60000,
        )

    def set_range(sel, value):
        page.locator(sel).fill(str(value))
        page.locator(sel).dispatch_event("input")

    def violated():
        return [n for n in VLINES if page.locator(f"#v-status-{n}").inner_text().strip() == "VIOLATED"]

    def geom():
        # client rects of the two circles, in CSS px: what the reader sees
        return page.evaluate(
            """() => { const o = document.getElementById('pic-outer').getBoundingClientRect();
                       const i = document.getElementById('pic-inner').getBoundingClientRect();
                       return {ro: o.width / 2, ri: i.width / 2}; }"""
        )

    def overlays():
        return sorted(page.eval_on_selector_all("#pic-overlays > g", "els => els.map(e => e.dataset.line)"))

    def shot(name):
        settle()
        busy = "computing" in page.locator("#vessel").inner_text()
        check(not busy, f"[{label}] shot {name}: taken after the panel finished computing")
        if shoot:
            SHOTS.mkdir(parents=True, exist_ok=True)
            page.locator("#vessel").screenshot(path=str(SHOTS / f"{name}.png"))

    def reload():
        page.reload(wait_until="load")
        settle()

    discs = []  # (cx, cy, r) of the organism disc per measured state: must never move or resize

    def measure(tag, line=None):
        """Critic round 1: text size, wound anchoring, rim clearance, disc colour, clamp leader."""
        m = page.evaluate(
            """(line) => { const svg = document.getElementById('pic');
              svg.scrollIntoView({block: 'center'});
              const s = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal, k = s.width / vb.width;
              const o = document.getElementById('pic-outer').getBoundingClientRect();
              const i = document.getElementById('pic-inner').getBoundingClientRect();
              const C = {x: o.left + o.width / 2, y: o.top + o.height / 2, ro: o.width / 2, ri: i.width / 2};
              const rect = (b) => ({l: b.left, r: b.right, t: b.top, b: b.bottom});
              const fonts = [...svg.querySelectorAll('text')].map(t =>
                ({t: t.textContent.slice(0, 30), px: parseFloat(getComputedStyle(t).fontSize) * k}));
              const org = document.getElementById('pic-organism'), ob = org.getBoundingClientRect();
              const top = document.elementFromPoint(ob.left + ob.width / 2, ob.top + ob.height / 2);
              const lab = line ? [...document.querySelectorAll('#pic-ov-' + line + ' text')].map(t => rect(t.getBoundingClientRect())) : [];
              const cl = document.getElementById('pic-clamp');
              const lead = document.getElementById('pic-clamp-leader');
              let leadEnd = null;
              if (lead) { const b = lead.getBoundingClientRect(); leadEnd = [rect(b)]; }
              return {C, fonts, fill: getComputedStyle(org).fill, topId: top ? top.id : null,
                      lab, clamp: cl ? rect(cl.getBoundingClientRect()) : null, leadEnd,
                      inner: getComputedStyle(document.getElementById('pic-inner')).fill,
                      amax: DysonModel.PRESETS[document.getElementById('v-org').value].a_max}; }""",
            line,
        )
        C = m["C"]
        small = [f for f in m["fonts"] if f["px"] < 12]
        check(not small, f"[{label}] {tag}: every picture text >= 12 px effective: {small}")

        def dist_rect(b):  # centre-to-rectangle nearest distance
            dx = max(b["l"] - C["x"], 0, C["x"] - b["r"])
            dy = max(b["t"] - C["y"], 0, C["y"] - b["b"])
            return (dx * dx + dy * dy) ** 0.5

        if line == "BURST":
            near = min(dist_rect(b) for b in m["lab"])
            check(near > C["ro"] + 2, f"[{label}] {tag}: fracture label clear of the rim (nearest {near:.1f} px, rim {C['ro']:.1f} px)")
        elif line in ("FREEZE", "BOIL", "OPAQUE"):
            # critic round 3: the plate may sit outside the vessel; it is anchored to the wound by
            # a leader from its edge whose far end lies inside the interior
            ends = page.evaluate(
                """(line) => [...document.querySelectorAll('#pic-ov-' + line + ' [data-mark=leader]')].map(l => {
                     const svg = document.getElementById('pic'), pt = svg.createSVGPoint();
                     pt.x = parseFloat(l.getAttribute('x1')); pt.y = parseFloat(l.getAttribute('y1'));
                     const q = pt.matrixTransform(svg.getScreenCTM()); return [q.x, q.y]; })""",  # getScreenCTM is viewport space, as getBoundingClientRect
                line,
            )
            d_in = [((x - C["x"]) ** 2 + (y - C["y"]) ** 2) ** 0.5 for x, y in ends]
            check(bool(d_in) and all(d < C["ri"] for d in d_in),
                  f"[{label}] {tag}: killing number anchored to the interior wound by a leader ending inside (ends at {[round(d, 1) for d in d_in]} px, ri {C['ri']:.1f})")
        rgb = [int(x) for x in re.findall(r"\d+", m["fill"])[:3]]
        mx, mn = max(rgb) / 255, min(rgb) / 255
        lum = (mx + mn) / 2
        sat = 0 if mx == mn else (mx - mn) / (1 - abs(2 * lum - 1))
        net = number_in(page.locator("#v-cmp-STARVE").inner_text())
        want = max(0.0, min(1.0, net / m["amax"]))
        check(m["topId"] == "pic-organism" and abs(sat - want) < 0.02,
              f"[{label}] {tag}: disc on top ({m['topId']}) with saturation {sat:.3f} = net/a_max {want:.3f}")
        if m["clamp"] is not None:
            d = dist_rect(m["clamp"]) - C["ro"]
            ok = m["leadEnd"] is not None and d < 60
            check(ok, f"[{label}] {tag}: clamp label beside the band ({d:.1f} px off the rim) with a leader")
        return m


    def overlap_check(tag):
        """Critic round 2: no overlay mark or leader crosses a label plate; plates clear the disc."""
        g = page.evaluate(
            """() => { const svg = document.getElementById('pic'); const n = (e, a) => parseFloat(e.getAttribute(a));
              const plates = [...svg.querySelectorAll('#pic-overlays rect')].map(r => ({owner: r.parentNode.id,
                x0: n(r,'x'), y0: n(r,'y'), x1: n(r,'x') + n(r,'width'), y1: n(r,'y') + n(r,'height')}));
              const segs = [];
              const add = (e, pts) => { for (let i = 1; i < pts.length; i++) segs.push({id: (e.id || e.parentNode.id) + ':' + e.tagName, a: pts[i-1], b: pts[i], sw: parseFloat(getComputedStyle(e).strokeWidth) || 0}); };
              svg.querySelectorAll('#pic-overlays line, #pic-clamp-leader').forEach(e =>
                add(e, [[n(e,'x1'), n(e,'y1')], [n(e,'x2'), n(e,'y2')]]));
              svg.querySelectorAll('#pic-overlays polyline').forEach(e =>
                add(e, e.getAttribute('points').trim().split(/\\s+/).map(p => p.split(',').map(Number))));
              const rings = [...svg.querySelectorAll('#pic-overlays circle')].filter(c => c.getAttribute('fill') === 'none')
                .map(c => ({id: c.parentNode.id + ':ring', cx: n(c,'cx'), cy: n(c,'cy'), r: n(c,'r')}));
              const o = document.getElementById('pic-organism'), inn = document.getElementById('pic-inner');
              const vb = svg.viewBox.baseVal;
              return {plates, segs, rings, disc: {cx: n(o,'cx'), cy: n(o,'cy'), r: n(o,'r')},
                      inner: {cx: n(inn,'cx'), cy: n(inn,'cy'), r: n(inn,'r')},
                      outer: (() => { const e = document.getElementById('pic-outer');
                        return {cx: n(e,'cx'), cy: n(e,'cy'), r: n(e,'r'), sw: parseFloat(e.getAttribute('stroke-width')) || 0}; })(), vb: {w: vb.width, h: vb.height}}; }"""
        )

        def seg_hits(a, b, R):
            # Liang-Barsky clip of segment ab against rect R shrunk by 1 unit (a leader may touch the edge)
            x0, y0, x1, y1 = R["x0"] + 1, R["y0"] + 1, R["x1"] - 1, R["y1"] - 1
            dx, dy = b[0] - a[0], b[1] - a[1]
            t0, t1 = 0.0, 1.0
            for p_, q_ in ((-dx, a[0] - x0), (dx, x1 - a[0]), (-dy, a[1] - y0), (dy, y1 - a[1])):
                if p_ == 0:
                    if q_ < 0:
                        return False
                else:
                    t = q_ / p_
                    if p_ < 0:
                        t0 = max(t0, t)
                    else:
                        t1 = min(t1, t)
            return t0 <= t1

        def ring_hits(c, R):
            nx = min(max(c["cx"], R["x0"]), R["x1"]) - c["cx"]
            ny = min(max(c["cy"], R["y0"]), R["y1"]) - c["cy"]
            near = (nx * nx + ny * ny) ** 0.5
            far = max(((x - c["cx"]) ** 2 + (y - c["cy"]) ** 2) ** 0.5 for x in (R["x0"], R["x1"]) for y in (R["y0"], R["y1"]))
            return near <= c["r"] <= far

        hits = [f"{s_['id']} x plate {R['owner']}" for R in g["plates"] for s_ in g["segs"] if seg_hits(s_["a"], s_["b"], R)]
        hits += [f"{c['id']} x plate {R['owner']}" for R in g["plates"] for c in g["rings"] if ring_hits(c, R)]
        check(not hits, f"[{label}] {tag}: no overlay mark or leader crosses a label plate: {sorted(set(hits))[:6]}")
        # polish item 7: every plate keeps a margin inside the picture's edge
        for R in g["plates"]:
            m_ = min(R["x0"], R["y0"], g["vb"]["w"] - R["x1"], g["vb"]["h"] - R["y1"])
            check(m_ >= 8, f"[{label}] {tag}: plate {R['owner']} keeps >= 8 units inside the picture edge ({m_:.1f})")
        # polish item 6: a plate never overlaps the wall band: wholly inside the interior, or
        # wholly outside the rim (incl. its outline)
        I, O = g["inner"], g["outer"]
        for R in g["plates"]:
            far = max(((x - I["cx"]) ** 2 + (y - I["cy"]) ** 2) ** 0.5 for x in (R["x0"], R["x1"]) for y in (R["y0"], R["y1"]))
            nx = min(max(O["cx"], R["x0"]), R["x1"]) - O["cx"]
            ny = min(max(O["cy"], R["y0"]), R["y1"]) - O["cy"]
            near = (nx * nx + ny * ny) ** 0.5
            check(far <= I["r"] - 3 or near >= O["r"] + O["sw"] / 2 + 3,
                  f"[{label}] {tag}: plate {R['owner']} clear of the wall band (inner corner reach {far:.1f} vs interior {I['r']:.1f}; nearest {near:.1f} vs rim {O['r']:.1f})")
        # critic round 2: interior shows between the disc (incl. its stroke) and the wall band's
        # inner edge, measured on RENDERED px
        w = page.evaluate(
            """() => { const svg = document.getElementById('pic'), k = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
              const o = document.getElementById('pic-organism'), i = document.getElementById('pic-inner');
              const ob = o.getBoundingClientRect(), ib = i.getBoundingClientRect();
              const sw = parseFloat(getComputedStyle(o).strokeWidth) * k;
              const dx = (ob.left + ob.right) / 2 - (ib.left + ib.right) / 2, dy = (ob.top + ob.bottom) / 2 - (ib.top + ib.bottom) / 2;
              return {gap: ib.width / 2 - (Math.hypot(dx, dy) + ob.width / 2 + sw / 2), k}; }"""
        )
        check(w["gap"] >= 10, f"[{label}] {tag}: disc (with stroke) clears the wall band by {w['gap']:.1f} rendered px >= 10")
        # critic round 3: marks keep >= 6 rendered px from every plate; a leader (a segment with
        # an endpoint on a plate's boundary) is the one mark allowed to meet it
        k_ = page.evaluate("() => { const s = document.getElementById('pic'); return s.getBoundingClientRect().width / s.viewBox.baseVal.width; }")

        def on_edge(q, R):
            inx, iny = R["x0"] - 0.6 <= q[0] <= R["x1"] + 0.6, R["y0"] - 0.6 <= q[1] <= R["y1"] + 0.6
            return inx and iny and min(abs(q[0] - R["x0"]), abs(q[0] - R["x1"]), abs(q[1] - R["y0"]), abs(q[1] - R["y1"])) <= 0.6

        def seg_rect_dist(a, b, R):
            best = float("inf")
            for i in range(41):
                t = i / 40
                x, y = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
                dx = max(R["x0"] - x, 0, x - R["x1"])
                dy = max(R["y0"] - y, 0, y - R["y1"])
                best = min(best, (dx * dx + dy * dy) ** 0.5)
            return best

        near_ = []
        for R in g["plates"]:
            for s_ in g["segs"]:
                if s_["id"].startswith("pic-clamp") or on_edge(s_["a"], R) or on_edge(s_["b"], R):
                    continue
                dd = (seg_rect_dist(s_["a"], s_["b"], R) - s_["sw"] / 2) * k_  # to the stroke's edge
                if dd < 6:
                    near_.append(f"{s_['id']} {dd:.1f}px from plate {R['owner']}")
        check(not near_, f"[{label}] {tag}: every mark keeps >= 6 px from every plate: {near_[:4]}")
        d = g["disc"]
        discs.append((tag, round(d["cx"], 2), round(d["cy"], 2), round(d["r"], 2)))
        for R in g["plates"]:
            if R["owner"] == "pic-ov-BURST":
                continue
            nx = min(max(d["cx"], R["x0"]), R["x1"]) - d["cx"]
            ny = min(max(d["cy"], R["y0"]), R["y1"]) - d["cy"]
            gap = (nx * nx + ny * ny) ** 0.5 - d["r"]
            check(gap >= 3, f"[{label}] {tag}: plate {R['owner']} clears the disc by {gap:.1f} >= 3 units")

    def hatch_contrast():
        m = page.evaluate(
            """() => { const g = document.getElementById('pic-ov-OPAQUE');
              const cs = (e, p) => getComputedStyle(e)[p];
              const hatch = [...g.querySelectorAll('line:not([data-mark^=leader])')].map(l => ({c: cs(l, 'stroke'), a: parseFloat(cs(l, 'strokeOpacity'))}));
              const veil = g.querySelector('[data-mark=veil]');
              return {hatch, inner: cs(document.getElementById('pic-inner'), 'fill'),
                      veil: veil ? {c: cs(veil, 'fill'), a: parseFloat(cs(veil, 'fillOpacity'))} : null}; }"""
        )

        def rgb(s_):
            return [int(x) / 255 for x in re.findall(r"\d+", s_)[:3]]

        def over(top, a, base):
            return [a * t + (1 - a) * b for t, b in zip(top, base)]

        def lum(c):
            lin = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
            return 0.2126 * lin[0] + 0.7152 * lin[1] + 0.0722 * lin[2]

        under = rgb(m["inner"])
        if m["veil"]:
            under = over(rgb(m["veil"]["c"]), m["veil"]["a"], under)
        diffs = [abs(lum(over(rgb(h["c"]), h["a"], under)) - lum(under)) for h in m["hatch"]]
        check(bool(diffs) and min(diffs) >= 0.15,
              f"[{label}] OPAQUE hatch contrasts with the fill under it: min luminance difference {min(diffs) if diffs else None} (>= 0.15)")

    reload()
    tr = float(page.locator("#v-tR").inner_text())
    g = geom()
    check(abs(tr - 1.400e-3) < 5e-7, f"[{label}] picture defaults: readout t/R {tr:.3e} is t_min 1.400 m / 1 km (spec §8 prints 1.45e-3, the normal-incidence t_min)")
    clamp = page.locator("#pic-clamp")
    check(clamp.count() == 1 and clamp.is_visible() and "clamped" in clamp.text_content(),
          f"[{label}] picture defaults: clamp label present and visible")
    band = g["ro"] - g["ri"]
    notes.append(f"NOTE  [{label}] defaults drawn band {band:.3f} px on inner {g['ri']:.2f} px "
                 f"(ratio {band / g['ri']:.4f} vs true t/R {tr:.3e})")
    check(overlays() == [], f"[{label}] picture defaults: no overlay, got {overlays()}")
    measure("defaults")
    overlap_check("defaults")
    shot("01_defaults_clamped")

    # input -> picture latency: the picture is redrawn synchronously with the lines
    lat = page.evaluate(
        """() => { const s = document.getElementById('v-r'); const out = [];
                   for (let i = 0; i < 40; i++) { s.value = Math.log10(1.05 + i * 0.005).toFixed(4);
                     const t0 = performance.now(); s.dispatchEvent(new Event('input'));
                     void document.getElementById('pic-inner').getBoundingClientRect();
                     out.push(performance.now() - t0); }
                   out.sort((a, b) => a - b); return {median: out[20], max: out[39]}; }"""
    )
    notes.append(f"NOTE  [{label}] r-drag input-to-picture latency (layout forced): median {lat['median']:.1f} ms, max {lat['max']:.1f} ms")
    check(lat["max"] < 100, f"[{label}] input-to-picture under 100 ms (max {lat['max']:.1f} ms)")

    reload()
    page.select_option("#v-t-mode", "manual")
    set_range("#v-t", "1.699")  # 50.003 m (the slider step is 1e-4)
    tr = float(page.locator("#v-tR").inner_text())
    g = geom()
    ratio = (g["ro"] - g["ri"]) / g["ri"]
    notes.append(f"NOTE  [{label}] unclamped R 1 km t 50 m: drawn band/inner {ratio:.5f} (ro {g['ro']:.3f}, ri {g['ri']:.3f} px) vs readout t/R {tr:.5f}")
    check(round(tr, 3) == 0.050 and round(ratio, 2) == round(tr, 2),
          f"[{label}] unclamped: drawn band/inner {ratio:.4f} equals readout t/R {tr:.4f} to 2 dp")
    check(page.locator("#pic-clamp").count() == 0, f"[{label}] unclamped: no clamp label")
    m2 = measure("unclamped")
    overlap_check("unclamped")
    rgb2 = [int(x) for x in re.findall(r"\d+", m2["inner"])[:3]]
    check(rgb2[2] == max(rgb2) and rgb2[2] - min(rgb2) >= 40 and max(rgb2) >= 120,
          f"[{label}] unclamped (alive, f_photon above the floor): interior visibly blue and not crushed, {rgb2}")
    shot("02_unclamped_t50m")
    settle()

    gestures = [
        ("03_freeze", "FREEZE", lambda: (set_range("#v-R", 4), set_range("#v-r", 0.0828))),
        ("04_burst", "BURST", lambda: (page.select_option("#v-p-mode", "manual"), set_range("#v-p", 3.35))),
        ("05_boil", "BOIL", lambda: (page.select_option("#v-p-mode", "manual"), set_range("#v-p", 3.25))),
        ("06_opaque", "OPAQUE", lambda: (page.select_option("#v-t-mode", "manual"), set_range("#v-t", 2))),
    ]
    for name, line, act in gestures:
        reload()
        act()
        v, ov = violated(), overlays()
        check(v == [line] and ov == [line], f"[{label}] gesture {line}: violated {v}, overlays {ov} (want exactly [{line}])")
        cmp = page.locator(f"#v-cmp-{line}").inner_text().split(" — ")[0]
        lab = page.locator(f"#pic-ov-{line}").text_content()
        check(cmp in lab, f"[{label}] gesture {line}: wound prints the panel's both sides {cmp!r}")
        box = page.evaluate(
            f"""() => {{ const s = document.getElementById('pic').getBoundingClientRect();
                        return [...document.querySelectorAll('#pic-ov-{line} text')].map(t => {{ const b = t.getBoundingClientRect();
                          return b.left >= s.left - 0.5 && b.right <= s.right + 0.5 && b.top >= s.top - 0.5 && b.bottom <= s.bottom + 0.5; }}); }}"""
        )
        check(box and all(box), f"[{label}] gesture {line}: wound label inside the picture {box}")
        measure(line, line)
        overlap_check(line)
        if line == "OPAQUE":
            hatch_contrast()
        if line == "OPAQUE":
            marks = page.eval_on_selector_all("#pic-ov-OPAQUE [data-mark]", "els => els.map(e => e.dataset.mark)")
            check("veil" in marks and "floor-ring" in marks, f"[{label}] OPAQUE has its own veil and floor ring, not luminance only: {marks}")
        shot(name)
        settle()
    reload()
    geo_ = sorted({d[1:] for d in discs})
    check(len(discs) == 6 and len(geo_) == 1,
          f"[{label}] organism disc (cx, cy, r) identical in all six states: {discs}")



def exercise_q4_band(page, label: str) -> None:
    """M4: the r_close band hatched as Q1's is, the measured edges beside it, HELD/FAILED."""
    import re as _re

    results = (ROOT / "experiments" / "q4_vessel" / "RESULTS.md").read_text()
    want = dict(_re.findall(r"^Q4_(P[12])=(HELD|FAILED)$", results, _re.M))
    m = page.evaluate(
        """() => { const r = document.getElementById('q4-band-rect');
                  const pat = document.getElementById('q4hatch');
                  const dots = [...document.querySelectorAll('#q4-band [data-mark=q4-measured]')];
                  const rb = r.getBoundingClientRect();
                  return { fill: r.getAttribute('fill'), pat: !!pat, w: rb.width, h: rb.height,
                    label: document.getElementById('q4-band-label').textContent,
                    verdict: document.getElementById('q4-verdict').textContent,
                    dots: dots.map(d => { const b = d.getBoundingClientRect(); return {x: (b.left + b.right) / 2, w: b.width}; }),
                    x0: rb.left, x1: rb.right }; }"""
    )
    check(m["fill"] == "url(#q4hatch)" and m["pat"], f"[{label}] Q4 band is hatched: {m['fill']}")
    check(m["w"] > 20 and m["h"] > 20, f"[{label}] Q4 band is drawn: {m['w']:.0f}x{m['h']:.0f}px")
    check(len(m["dots"]) == 3 and all(d["w"] > 0 for d in m["dots"]), f"[{label}] three measured r_close marks")
    check(f"({want.get('P1')})" in m["label"], f"[{label}] Q4 band label {m['label']!r} carries RESULTS.md P1 {want.get('P1')}")
    check(f"P1 {want.get('P1')}" in m["verdict"] and f"P2 {want.get('P2')}" in m["verdict"],
          f"[{label}] Q4 verdict line {m['verdict']!r} matches RESULTS.md {want}")
    inside = [m["x0"] <= d["x"] <= m["x1"] for d in m["dots"]]
    check(inside == [True] * 3 if want.get("P1") == "HELD" else not all(inside),
          f"[{label}] measured marks sit where the verdict says relative to the band: {inside}")
    # critic round 5: every text >= 12 rendered px; no text straddles the band's left/right edge
    t = page.evaluate(
        """() => { const svg = document.getElementById('q4-band'); svg.scrollIntoView({block: 'center'});
                  const k = svg.getBoundingClientRect().width / svg.viewBox.baseVal.width;
                  const rb = document.getElementById('q4-band-rect').getBoundingClientRect();
                  return { x0: rb.left, x1: rb.right, y0: rb.top, y1: rb.bottom, texts: [...svg.querySelectorAll('text')].map(e => {
                    const b = e.getBoundingClientRect();
                    return {t: e.textContent.slice(0, 24), px: parseFloat(getComputedStyle(e).fontSize) * k, l: b.left, r: b.right, t0: b.top, t1: b.bottom}; }) }; }"""
    )
    small = [(x["t"], round(x["px"], 1)) for x in t["texts"] if x["px"] < 12]
    check(t["texts"] and not small, f"[{label}] Q4 band: every text >= 12 px rendered: {small}")
    cross = [x["t"] for x in t["texts"] if any(x["l"] + 2 < e < x["r"] - 2 for e in (t["x0"], t["x1"]))
             and x["t1"] > t["y0"] and x["t0"] < t["y1"]]  # text beside the band, not the title/axis
    check(not cross, f"[{label}] Q4 band: no label runs across a band edge: {cross}")


def main() -> int:
    assert SITE.is_dir(), "site/ not built — run tools/build_site.sh first"
    from playwright.sync_api import sync_playwright

    import shutil
    import tempfile

    tmp = Path(tempfile.mkdtemp(prefix="dt-smoke-"))
    shutil.copytree(SITE, tmp / SUBPATH)
    httpd, port = serve(tmp)
    http_url = f"http://127.0.0.1:{port}/{SUBPATH}/"
    file_url = (SITE / "index.html").as_uri()

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        for label, url in (("http subpath", http_url), ("file://", file_url)):
            console: list[str] = []
            page = browser.new_page()
            page.on(
                "console",
                lambda m, c=console: c.append(f"{m.type}: {m.text}")
                if m.type in ("error", "warning")
                else None,
            )
            page.on("pageerror", lambda e, c=console: c.append(f"pageerror: {e}"))
            failed_requests: list[str] = []
            page.on(
                "requestfailed",
                lambda r, f=failed_requests: f.append(f"{r.url} {r.failure}"),
            )
            resp = page.goto(url, wait_until="load")
            if url.startswith("http"):
                check(
                    resp is not None and resp.status == 200,
                    f"[{label}] HTTP {resp.status if resp else 'no response'}",
                )
            check(not failed_requests, f"[{label}] no failed requests: {failed_requests}")
            check(not console, f"[{label}] zero console errors/warnings: {console}")
            check(
                page.title() == "Dyson tree — carbon-budget explorer",
                f"[{label}] title renders",
            )
            exercise(page, label)
            exercise_vessel(page, label)
            exercise_q4_band(page, label)
            exercise_picture(page, label, shoot=url.startswith("http"))
            page.close()
        browser.close()
    httpd.shutdown()
    shutil.rmtree(tmp, ignore_errors=True)

    for line in notes:
        print(line)
    for line in failures:
        print(line)
    print(f"\n{len(notes)} passed, {len(failures)} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
