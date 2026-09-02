import subprocess
import sys
from pathlib import Path

import yaml

REPO = Path(__file__).resolve().parents[1]
RUN = REPO / "experiments" / "q1_crossover" / "run.py"
PREREG = REPO / "experiments" / "q1_crossover" / "prereg.yaml"

sys.path.insert(0, str(RUN.parent))
import run  # noqa: E402


def _read_header_and_rows(path: Path):
    lines = path.read_text().splitlines()
    header = [l for l in lines if l.startswith("#")]
    body = [l for l in lines if not l.startswith("#")]
    return header, body


def test_gate_failure_exits_2_and_writes_no_crossover(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"]["vascular"]["r_d"] = 3.0   # I_c = 100*3/7 = 42.9, outside [5.3, 9.0]
    bad_path = tmp_path / "prereg_bad.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    out = tmp_path / "out_bad"
    rc = run.main(["--prereg", str(bad_path), "--out", str(out)])
    assert rc == 2
    assert (out / "calibration.csv").exists()
    assert not (out / "crossover.csv").exists()
    assert not (out / "sweep.csv").exists()
    _, body = _read_header_and_rows(out / "calibration.csv")
    assert any(",False" in l for l in body[1:])


def test_real_prereg_passes_and_writes_all_csvs_with_provenance(tmp_path):
    out = tmp_path / "out_ok"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc == 0
    for name in ("calibration.csv", "sweep.csv", "crossover.csv"):
        header, body = _read_header_and_rows(out / name)
        assert any(l.startswith("# git_sha=") for l in header), name
        assert any(l.startswith("# physiology_md5=") for l in header), name
        assert any(l.startswith("# prereg_md5=") for l in header), name
        assert len(body) >= 2, name
    _, cross = _read_header_and_rows(out / "crossover.csv")
    assert cross[0] == "class,k,r_star_au,pred_lo,pred_hi,inside"
    assert len(cross) == 1 + 3 + 3   # header + 3 k values per preset


def test_assumption_mismatch_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["par_fraction"] = 0.5
    bad_path = tmp_path / "prereg_drift.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    import pytest
    with pytest.raises(ValueError, match="par_fraction"):
        run.main(["--prereg", str(bad_path), "--out", str(tmp_path / "o")])


def test_cli_exit_code_on_gate_failure(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"]["algal"]["r_d"] = 5.0
    bad_path = tmp_path / "p.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(bad_path), "--out", str(tmp_path / "o")],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "GATE FAILED" in proc.stdout
