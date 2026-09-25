"""Deck stacking parity: web/deck.js (run in node) must stack cards exactly as sim/deck.py.

Pattern of tests/test_parity_js.py: node runs the implementation under test and prints raw
results; every comparison happens HERE. Fails, never skips, without node.

The page is never a registered run, so it plays the DECLARED card; the Python side is
compared with registered=False, and the same combination is asserted refused by Python with
registered=True in the same test (the refusal and the page's allowance, side by side).
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from sim import deck as D
from sim import vessel as V
from sim.organism import ALGAL

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
AFP, RD = "antifreeze proteins", "reduced dark respiration"

# {trait: (cards played, value per card)}: the page plays n copies of ONE value per row
COMBOS: dict[str, dict[str, tuple[int, float]]] = {
    "afp x1 0.8": {AFP: (1, 0.8)},
    "afp x1 0.0": {AFP: (1, 0.0)},
    "afp x1 1.3 (at the cap)": {AFP: (1, 1.3)},
    "afp x1 5.0 (clipped)": {AFP: (1, 5.0)},
    "afp x2 0.8 (clipped)": {AFP: (2, 0.8)},
    "afp x3 0.4": {AFP: (3, 0.4)},
    "afp x3 0.45 (clipped)": {AFP: (3, 0.45)},
    "rd x1 0.1 (DECLARED)": {RD: (1, 0.1)},
    "afp x2 0.5 + rd x1": {AFP: (2, 0.5), RD: (1, 0.1)},
    "afp x3 5.0 + rd x1": {AFP: (3, 5.0), RD: (1, 0.1)},
    "none": {},
    # both sides must refuse these
    "afp x4 (over max_stack)": {AFP: (4, 0.1)},
    "afp x1 6.0 (outside range)": {AFP: (1, 6.0)},
    "rd x1 0.5 (outside range)": {RD: (1, 0.5)},
}

DRIVER = r"""
const fs = require("fs"), vm = require("vm"), path = require("path");
const web = process.argv[1];  // node -e: argv[1] is the first extra argument
const combos = JSON.parse(fs.readFileSync(0, "utf8"));
const rows = JSON.parse(fs.readFileSync(path.join(web, "deck.json"), "utf8"));
function run(combo) {
  const els = new Map();
  const document = {
    getElementById(id) {
      if (id === "deck-" + rows.length) return null;
      if (!els.has(id)) els.set(id, { id, value: "", textContent: "", className: "" });
      return els.get(id);
    },
  };
  const ctx = { console, document, DysonDeckRows: rows };
  ctx.window = ctx;
  vm.createContext(ctx);
  for (const s of ["model.js", "deck.js"])
    vm.runInContext(fs.readFileSync(path.join(web, s), "utf8"), ctx, { filename: s });
  const M = ctx.DysonModel, K = ctx.DysonDeck;
  rows.forEach((r, i) => {
    const c = combo[r.trait];
    document.getElementById("deck-" + i + "-count").value = String(c ? c[0] : 0);
    if (c) document.getElementById("deck-" + i + "-value").value = String(c[1]);
  });
  let eff;
  try { eff = K.effect(); } catch (e) { return { error: e.name + ": " + e.message }; }
  const org = K.applyOrganism(M.ALGAL, eff);
  return { T_freeze_K: "T_freeze_K" in eff.inputs ? eff.inputs.T_freeze_K : M.VESSEL_DEFAULTS.T_freeze_K,
           r_d: org.r_d, clips: eff.clips };
}
const out = {};
for (const [k, v] of Object.entries(combos)) out[k] = run(v);
process.stdout.write(JSON.stringify(out));
"""


@pytest.fixture(scope="module")
def js() -> dict:
    node = shutil.which("node")
    assert node, "node is required for the deck parity check (fails rather than skips)"
    proc = subprocess.run(
        [node, "-e", DRIVER, str(WEB)],
        input=json.dumps(
            {k: {t: list(c) for t, c in v.items()} for k, v in COMBOS.items()}
        ),
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert proc.returncode == 0, f"deck driver failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


def py(combo: dict[str, tuple[int, float]], registered: bool) -> dict:
    plays = {t: [v] * n for t, (n, v) in combo.items()}
    try:
        inp, org, clips = D.play(plays, V.REGISTERED, ALGAL, registered=registered)
    except D.DeclaredInRegisteredRun:
        raise
    except ValueError as e:
        return {"error": str(e)}
    return {"T_freeze_K": inp.T_freeze_K, "r_d": org.r_d, "clips": clips}


def test_every_combination_is_exercised(js):
    # every card singly, stacks, the DECLARED card, and refusals are all in the set
    assert set(js) == set(COMBOS)
    for row in D.ROWS:
        assert any(set(c) == {row["trait"]} for c in COMBOS.values()), row["trait"]
    assert any(len(c) == 2 for c in COMBOS.values())
    assert any("error" in r for r in js.values()) and any(
        "error" not in r for r in js.values()
    )


@pytest.mark.parametrize("name", list(COMBOS))
def test_js_stacking_equals_python(js, name):
    combo, got = COMBOS[name], js[name]
    want = py(combo, registered=False)
    if "error" in want:
        assert "error" in got, (
            f"{name}: Python refuses ({want['error']}), JS gave {got}"
        )
        return
    assert "error" not in got, (
        f"{name}: JS refused ({got['error']}), Python gave {want}"
    )
    # exact equality: both sides do the same float operations in the same order
    assert got["T_freeze_K"] == want["T_freeze_K"], (name, got, want)
    assert got["r_d"] == want["r_d"], (name, got, want)
    assert got["clips"] == want["clips"], (name, got, want)
    # the refused-in-registered-runs card: the page plays it; Python refuses it registered
    if RD in combo:
        with pytest.raises(D.DeclaredInRegisteredRun):
            py(combo, registered=True)
    else:
        assert py(combo, registered=True) == want
