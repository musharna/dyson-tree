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

    panel = page.locator("aside.isnot")
    check(panel.is_visible(), f"[{label}] 'What this is / is not' panel is visible")
    ptext = panel.inner_text()
    for phrase in ("pressure vessel", "spectral wall", "category error", "falsified"):
        check(phrase in ptext, f"[{label}] limitations panel mentions '{phrase}'")

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

    page.select_option("#preset", "vascular")
    check(page.locator("#plot path").count() >= 1, f"[{label}] vascular curve is drawn")


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
