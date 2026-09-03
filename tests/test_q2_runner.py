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


def _header(path):
    return [x for x in path.read_text().splitlines() if x.startswith("#")]


PROVENANCE_KEYS = (
    "# git_sha=",
    "# thermal_md5=",
    "# organism_md5=",
    "# prereg_md5=",
    "# python=",
    "# numpy=",
    "# scipy=",
    "# written=",
)


def test_gate_thermal_failure_exits_2_and_clears_stale_limits(tmp_path):
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


def test_synthetic_all_pass_prereg_exercises_the_rc0_path(tmp_path):
    """Against the real, frozen prereg, gate 2 always fails (mesophyte t_opt vs
    cold-adapted anchors), so `rc == 0` never happens in
    test_real_prereg_writes_all_three_csvs_with_provenance and sweep.csv/limits.csv
    get zero automated coverage from it. Widen ONLY gate_response's anchor windows
    on an in-memory copy -- never prereg.yaml itself, which stays frozen and its
    registered verdict stays exactly what it is -- so both gates pass here, and
    assert what that dead branch was meant to assert."""
    good = yaml.safe_load(PREREG.read_text())
    for anchor in good["gate_response"]["anchors"]:
        anchor["lo"], anchor["hi"] = 0.0, 1.0
    p = tmp_path / "allpass.yaml"
    p.write_text(yaml.safe_dump(good))
    out = tmp_path / "allpass_out"

    rc = run.main(["--prereg", str(p), "--out", str(out)])
    assert rc == 0

    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        header = _header(out / name)
        for key in PROVENANCE_KEYS:
            assert any(h.startswith(key) for h in header), f"{name} missing {key}"

    prereg = yaml.safe_load(PREREG.read_text())
    n = int(prereg["sweep"]["n_grid"])
    presets = prereg["presets"].values()

    sweep_rows = _rows(out / "sweep.csv")
    expected_sweep = 1 + sum(len(pr["t_min_grid"]) * n for pr in presets)
    assert len(sweep_rows) == expected_sweep, (
        f"sweep.csv has {len(sweep_rows)} lines, prereg implies {expected_sweep} "
        f"(n_grid={n})"
    )

    limits_rows = _rows(out / "limits.csv")
    assert limits_rows[0] == (
        "class,t_min,thermal_au,carbon_fixed_t_au,carbon_equilibrium_au,binding"
    )
    expected_limits = 1 + sum(len(pr["t_min_grid"]) for pr in presets)
    assert len(limits_rows) == expected_limits, (
        f"limits.csv has {len(limits_rows)} lines, prereg implies {expected_limits} "
        "(one row per class,t_min pair, plus header)"
    )


def test_partial_gate_response_failure_still_exits_2(tmp_path):
    """Exactly one response anchor passes and the other fails. Both anchors failing
    identically (the flat-0.99 test above) cannot distinguish correct `ok &= passed`
    accumulation from a last-wins bug that only remembers the final anchor; this can."""
    mixed = yaml.safe_load(PREREG.read_text())
    anchors = mixed["gate_response"]["anchors"]
    # anchors[0] (5 C) is left narrow -> fails against the real ~0.394 response.
    # anchors[1] (0 C) is widened -> passes against the real ~0.242 response.
    anchors[1]["lo"], anchors[1]["hi"] = 0.0, 1.0
    p = tmp_path / "mixed.yaml"
    p.write_text(yaml.safe_dump(mixed))
    out = tmp_path / "mixed_out"

    assert run.main(["--prereg", str(p), "--out", str(out)]) == 2
    rows = _rows(out / "gates.csv")[1:]  # drop the CSV header row
    assert len(rows) == 3, (
        f"expected 3 gate rows (thermal + 2 anchors), got {len(rows)}"
    )
    assert sum("False" in r for r in rows) == 1, "expected exactly one failing gate row"
    assert sum("True" in r for r in rows) == 2, (
        "expected the thermal gate and the widened anchor to pass"
    )
    assert not (out / "limits.csv").exists()
