"""M4: the Q4 runner and its committed results (spec §6, §8 M4).

The provenance test checks the committed RESULTS.md / edges.csv / sweep.csv were written
from the committed prereg (md5 d8707a66...) and from the code as it stands now; the page
test checks web/verdict.js carries the HELD/FAILED label RESULTS.md records. Each has its
negative control inside the same test.
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import subprocess
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[1]
Q4 = ROOT / "experiments" / "q4_vessel"
PREREG = Q4 / "prereg.yaml"
OUTPUTS = ("RESULTS.md", "edges.csv", "sweep.csv")

_spec = importlib.util.spec_from_file_location("q4_run", Q4 / "run.py")
q4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(q4)


def _md5(p: Path) -> str:
    return hashlib.md5(p.read_bytes()).hexdigest()


def header_of(text: str) -> dict:
    out = {}
    for ln in text.splitlines():
        m = re.match(r"^#?\s*(\w+)=(\S+)\s*$", ln)
        if m:
            out.setdefault(m.group(1), m.group(2))
    return out


def provenance_problems(text: str) -> list[str]:
    """Every way a results header can fail to come from the committed prereg and code."""
    h = header_of(text)
    bad = []
    if h.get("prereg_md5") != _md5(PREREG):
        bad.append(f"prereg_md5 {h.get('prereg_md5')} != {_md5(PREREG)}")
    if not str(h.get("prereg_md5", "")).startswith("d8707a66"):
        bad.append("prereg_md5 is not the registered d8707a66...")
    for key, path in q4.CODE_PATHS.items():
        if h.get(key) != _md5(path):
            bad.append(f"{key} {h.get(key)} != current {_md5(path)}")
    if (
        h.get("spectral_table_sha256")
        != yaml.safe_load(PREREG.read_text())["spectral_table"]["data_sha256"]
    ):
        bad.append("spectral_table_sha256 differs from the prereg")
    if h.get("code_dirty") != "no":
        bad.append(f"code_dirty={h.get('code_dirty')}")
    sha = h.get("git_sha", "")
    anc = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"], cwd=ROOT
    ).returncode
    if anc != 0:
        bad.append(f"git_sha {sha} is not an ancestor of HEAD")
    return bad


@pytest.mark.parametrize("name", OUTPUTS)
def test_results_come_from_committed_prereg_and_code(name):
    text = (Q4 / name).read_text()
    assert provenance_problems(text) == []
    # negative control: the same file with its prereg md5 or vessel md5 altered must fail
    h = header_of(text)
    for key in ("prereg_md5", "vessel_md5"):
        tampered = text.replace(f"{key}={h[key]}", f"{key}={'0' * 32}", 1)
        assert tampered != text
        assert any(key in p for p in provenance_problems(tampered)), key


def results_verdicts(text: str) -> dict:
    return dict(re.findall(r"^Q4_(P[12])=(HELD|FAILED)$", text, re.M))


def page_q4(js: str) -> dict:
    m = re.search(r"var Q4_RESULT = (\{.*?\});", js, re.S)
    assert m, "web/verdict.js carries no Q4_RESULT"
    body = m.group(1)
    out = dict(re.findall(r"(P[12]): \"(HELD|FAILED)\"", body))
    out["r_close"] = [
        float(x)
        for x in re.search(r"r_close_au: \[([^\]]*)\]", body).group(1).split(",")
    ]
    out["R_window"] = float(re.search(r"R_window_km: ([\d.]+)", body).group(1))
    return out


def test_page_label_matches_results():
    text = (Q4 / "RESULTS.md").read_text()
    js = (ROOT / "web" / "verdict.js").read_text()
    res, page = results_verdicts(text), page_q4(js)
    assert set(res) == {"P1", "P2"}
    assert page["P1"] == res["P1"] and page["P2"] == res["P2"]
    edges = (Q4 / "edges.csv").read_text().splitlines()
    rows = [
        ln.split(",") for ln in edges if ln.startswith("P1,") or ln.startswith("P2,")
    ]
    p1 = [float(r[13]) for r in rows if r[0] == "P1"]
    p2 = [float(r[13]) for r in rows if r[0] == "P2" and r[10] == "R_window"]
    assert [round(x, 4) for x in p1] == page["r_close"]
    assert round(p2[0], 1) == page["R_window"]
    # negative control: a page whose label is flipped must not match
    flip = {"HELD": "FAILED", "FAILED": "HELD"}[res["P1"]]
    js2 = js.replace(f'P1: "{res["P1"]}"', f'P1: "{flip}"', 1)
    assert page_q4(js2)["P1"] != res["P1"]


def test_gate_failure_exits_2_and_writes_nothing(tmp_path, monkeypatch):
    # positive control: the real gates pass
    assert all(g["passed"] for g in q4.gates(yaml.safe_load(PREREG.read_text())))
    for n in OUTPUTS:
        (tmp_path / n).write_text("stale")
    real = q4.V.saturation_pressure
    monkeypatch.setattr(q4.V, "saturation_pressure", lambda t: real(t) + 0.02)
    assert q4.main(["--out", str(tmp_path), "--workers", "1"]) == 2
    assert not any((tmp_path / n).exists() for n in OUTPUTS)


def test_prereg_drift_exits_2(tmp_path):
    prereg = yaml.safe_load(PREREG.read_text())
    q4.assert_prereg_matches_code(prereg, PREREG)  # positive control
    prereg["predictions"]["P1"]["band_au"] = [1.18, 1.27]
    p = tmp_path / "prereg.yaml"
    p.write_text(yaml.safe_dump(prereg))
    assert (
        q4.main(["--prereg", str(p), "--out", str(tmp_path / "o"), "--workers", "1"])
        == 2
    )
    assert not (tmp_path / "o" / "RESULTS.md").exists()


def test_runner_error_exits_2(tmp_path, monkeypatch):
    def boom(*a, **k):
        raise q4.V.RunnerError("auto-path BOIL violated (injected)")

    monkeypatch.setattr(q4.V, "auto_state", boom)
    assert q4.main(["--out", str(tmp_path), "--workers", "1"]) == 2
    assert not (tmp_path / "sweep.csv").exists()


@pytest.mark.slow
def test_rerun_reproduces_committed_edges(tmp_path):
    assert q4.main(["--out", str(tmp_path)]) == 0
    strip = lambda t: [ln for ln in t.splitlines() if not ln.startswith("#")]  # noqa: E731
    assert strip((tmp_path / "edges.csv").read_text()) == strip(
        (Q4 / "edges.csv").read_text()
    )
