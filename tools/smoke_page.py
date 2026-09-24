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
                   for (let i = 0; i < 40; i++) { s.value = (1.05 + i * 0.005).toFixed(3);
                     const t0 = performance.now(); s.dispatchEvent(new Event('input'));
                     void document.getElementById('v-status-FREEZE').textContent;
                     out.push(performance.now() - t0); }
                   out.sort((a, b) => a - b);
                   return {median: out[20], max: out[39]}; }"""
    )
    notes.append(f"NOTE  [{label}] r-drag input-to-readout latency: median {lat['median']:.1f} ms, max {lat['max']:.1f} ms (40 inputs)")
    check(lat["max"] < 100, f"[{label}] r-drag input-to-readout under 100 ms (max {lat['max']:.1f} ms)")

    reload()
    set_range("#v-R", 4)
    set_range("#v-r", 1.20)
    check(violated() == [], f"[{label}] R 10 km, r 1.20 AU: all hold, got {violated()}")
    set_range("#v-r", 1.21)
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
    set_range("#v-r", 1.21)
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
