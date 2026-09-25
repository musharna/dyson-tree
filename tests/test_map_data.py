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
    # positive control: recompute 12 cells live (the P1-band cell nearest r 1.20 AU / R 10 km σ 0.7 algal,
    # plus a stride across all slices). The grid has no NO_DESIGN cell, so that class is covered by
    # test_mapCell_classifies_stub_outcomes below, not here.
    node = shutil.which("node"); assert node, "node required; fails rather than skips"
    out = subprocess.run([node, str(ROOT / "tools" / "make_map.mjs"), "--check", "12"], cwd=ROOT,
                         capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checked"] == 12 and res["mismatches"] == [], res
    assert "HELD" in res["classes_seen"], res   # the sample reached the window


MAPCELL_PROBE = r"""
const { loadModel, mapCell } = await import(process.argv[1]);
const M = loadModel();
const stub = (f) => ({ ...M, autoState: f });
const out = {};
out.runner = mapCell(stub(() => { throw new M.RunnerError("no design"); }), 1, 1e4, 0.7e6, "algal");
try { mapCell(stub(() => { throw new Error("plain bug"); }), 1, 1e4, 0.7e6, "algal"); out.plain = "swallowed"; }
catch (e) { out.plain = "rethrown:" + e.message; }
out.held = mapCell(stub(() => ({ report: { violated: [] } })), 1, 1e4, 0.7e6, "algal");
out.freeze = mapCell(stub(() => ({ report: { violated: ["FREEZE", "BURST"] } })), 1, 1e4, 0.7e6, "algal");
console.log(JSON.stringify(out));
"""

def test_mapCell_classifies_stub_outcomes():
    # unit test of mapCell's error mapping, independent of whether any grid cell throws
    node = shutil.which("node"); assert node, "node required; fails rather than skips"
    out = subprocess.run([node, "--input-type=module", "-e", MAPCELL_PROBE,
                          (ROOT / "tools" / "make_map.mjs").as_uri()], cwd=ROOT,
                         capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["runner"] == "NO_DESIGN", res
    assert res["plain"] == "rethrown:plain bug", res
    # positive controls: the non-throwing path still classifies
    assert res["held"] == "HELD" and res["freeze"] == "FREEZE", res
