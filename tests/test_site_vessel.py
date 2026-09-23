"""M1b acceptance, on the BUILT page: `DysonModel.classifyFailure(...)` at the prereg's
registered inputs returns the set the prereg names (spec §8 M1b).

This builds site/ with tools/build_site.sh, then loads the scripts site/index.html
loads, in its order, into a bare node `vm` context (no `module`, no `require`: the
browser path, `window.DysonModel`), and calls classifyFailure there. A page that
forgot to ship or order spectral_table.js fails here, which the parity test (which
`require`s web/model.js) cannot see.

Fails, never skips, without node or bash.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const site = process.argv[2];
const cases = JSON.parse(fs.readFileSync(0, "utf8"));
const html = fs.readFileSync(path.join(site, "index.html"), "utf8");
const srcs = [...html.matchAll(/<script src="\.\/([^"]+)"><\/script>/g)].map((m) => m[1]);
const ctx = { console };
ctx.window = ctx;
vm.createContext(ctx);
const model = srcs.filter((s) => s !== "app.js"); // app.js needs a DOM
for (const s of model) vm.runInContext(fs.readFileSync(path.join(site, s), "utf8"), ctx, { filename: s });
const out = { scripts: srcs, results: [] };
for (const c of cases) {
  ctx.__c = c;
  const rep = vm.runInContext(
    "DysonModel.classifyFailure(__c.p, __c.t, __c.r, __c.R, __c.sigma, DysonModel.ALGAL, __c.inputs)",
    ctx,
  );
  out.results.push({ name: c.name, violated: [...rep.violated], sigma_eff: rep.sigma_eff });
}
process.stdout.write(JSON.stringify(out));
"""


def test_built_page_classify_failure_at_prereg_inputs(tmp_path):
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
    fx = json.loads((ROOT / "web" / "fixtures.json").read_text())
    cases = [
        {
            "name": c["name"],
            **{k: c["args"][k] for k in ("p", "t", "r", "R", "sigma", "inputs")},
        }
        for c in fx["vessel"]["cases"]
        if c["call"] == "prereg_example"
    ]
    assert len(cases) == 8
    drv = tmp_path / "drive.cjs"
    drv.write_text(DRIVER)
    proc = subprocess.run(
        [node, str(drv), str(ROOT / "site")],
        input=json.dumps(cases),
        capture_output=True,
        text=True,
        timeout=300,
    )
    assert proc.returncode == 0, proc.stderr
    out = json.loads(proc.stdout)
    assert out["scripts"].index("spectral_table.js") < out["scripts"].index("model.js")

    prereg = yaml.safe_load(
        (ROOT / "experiments" / "q4_vessel" / "prereg.yaml").read_text()
    )
    binding = {p: [prereg["predictions"][p]["binding"]] for p in ("P1", "P2")}
    for res in out["results"]:
        pred = re.search(r": (P[12]) ", res["name"]).group(1)
        want = [] if "(inside)" in res["name"] else binding[pred]
        assert res["violated"] == want, (
            f"{res['name']}: built page {res['violated']}, want {want}"
        )
        assert res["sigma_eff"] > 0
    # both kinds of answer occurred: the test can fail either way
    assert {tuple(r["violated"]) for r in out["results"]} == {
        (),
        ("FREEZE",),
        ("OPAQUE",),
    }
