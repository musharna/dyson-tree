import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
RUN = REPO / "experiments" / "q2_thermal" / "run.py"
PREREG = REPO / "experiments" / "q2_thermal" / "prereg.yaml"

from experiments.q2_thermal import run  # noqa: E402


def _rows(path):
    lines = [x for x in path.read_text().splitlines() if not x.startswith("#")]
    return lines


def test_gate_thermal_failure_exits_2_and_clears_stale_limits(tmp_path, monkeypatch):
    out = tmp_path / "out"
    out.mkdir()
    # Pre-seed a stale PASSING limits.csv: not-writing is not enough.
    (out / "limits.csv").write_text("# stale\nclass,t_min\nvascular,265.15\n")
    (out / "sweep.csv").write_text("# stale\nclass\nvascular\n")
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]  # impossible band
    p = tmp_path / "bad.yaml"
    p.write_text(yaml.safe_dump(bad))
    assert run.main(["--prereg", str(p), "--out", str(out)]) == 2
    assert not (out / "limits.csv").exists(), (
        "stale limits.csv from a previous passing run survived a gate failure"
    )
    assert not (out / "sweep.csv").exists()
    assert (out / "gates.csv").exists()


def test_assumption_drift_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["sigma_w_m2_k4"] = 1.0
    p = tmp_path / "drift.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="sigma_w_m2_k4"):
        run.main(["--prereg", str(p), "--out", str(tmp_path / "o")])


def test_real_prereg_writes_all_three_csvs_with_provenance(tmp_path):
    out = tmp_path / "ok"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc in (0, 2)
    header = (out / "gates.csv").read_text().splitlines()
    for key in (
        "# git_sha=",
        "# thermal_md5=",
        "# organism_md5=",
        "# prereg_md5=",
        "# python=",
        "# numpy=",
        "# scipy=",
        "# written=",
    ):
        assert any(h.startswith(key) for h in header), key
    if rc == 0:
        prereg = yaml.safe_load(PREREG.read_text())
        n = int(prereg["sweep"]["n_grid"])
        expected = 1 + sum(len(p["t_min_grid"]) * n for p in prereg["presets"].values())
        assert len(_rows(out / "sweep.csv")) == expected, (
            f"sweep.csv has {len(_rows(out / 'sweep.csv'))} lines, "
            f"pre-registration implies {expected} (n_grid={n})"
        )


def test_cli_exits_nonzero_when_a_gate_fails(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]
    p = tmp_path / "bad2.yaml"
    p.write_text(yaml.safe_dump(bad))
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(p), "--out", str(tmp_path / "o2")],
        capture_output=True,
        text=True,
    )
    assert proc.returncode != 0
    assert not (tmp_path / "o2" / "limits.csv").exists()


def test_response_gate_rejects_a_wrong_functional_form(tmp_path, monkeypatch):
    """A flat response of 0.99 is physically absurd -- it says a frozen organism
    photosynthesises at 99% of optimum. Gate 2 must reject it."""
    monkeypatch.setattr(run, "temperature_response", lambda t, t_min, t_opt: 0.99)
    out = tmp_path / "wrong"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 2
    rows = _rows(out / "gates.csv")
    assert any("False" in r for r in rows), "gate 2 accepted a flat 0.99 response"
    assert not (out / "limits.csv").exists()
