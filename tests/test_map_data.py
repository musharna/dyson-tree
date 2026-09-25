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
    # positive control: recompute 12 cells (incl. a P1-band cell and a NO_DESIGN cell if present) live
    node = shutil.which("node"); assert node, "node required; fails rather than skips"
    out = subprocess.run([node, str(ROOT / "tools" / "make_map.mjs"), "--check", "12"], cwd=ROOT,
                         capture_output=True, text=True, timeout=600)
    assert out.returncode == 0, out.stderr
    res = json.loads(out.stdout)
    assert res["checked"] == 12 and res["mismatches"] == [], res
    assert "HELD" in res["classes_seen"], res   # the sample reached the window
