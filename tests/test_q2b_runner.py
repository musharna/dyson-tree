import subprocess
import sys
from pathlib import Path

import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
RUN = REPO / "experiments" / "q2b_adapted" / "run.py"
PREREG = REPO / "experiments" / "q2b_adapted" / "prereg.yaml"

from experiments.q2b_adapted import run  # noqa: E402
from sim.thermal import equilibrium_temperature  # noqa: E402

PROVENANCE_KEYS = (
    "# git_sha=",
    "# thermal_md5=",
    "# organism_md5=",
    "# physiology_md5=",
    "# prereg_md5=",
    "# python=",
    "# numpy=",
    "# scipy=",
    "# written=",
)


def _rows(path):
    return [x for x in path.read_text().splitlines() if not x.startswith("#")]


def test_real_prereg_run_excludes_the_failing_class_but_still_reports(tmp_path):
    """Gate B fails for vascular and passes for algal. The run must NOT abort:
    it reports algal and records the vascular failure."""
    out = tmp_path / "real"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 0
    gates = _rows(out / "gates.csv")
    assert any("vascular" in g and "False" in g for g in gates)
    assert any("algal" in g and "True" in g for g in gates)
    limits = _rows(out / "limits.csv")
    assert all("vascular" not in row for row in limits[1:]), (
        "a vascular row was reported despite that class failing Gate B"
    )
    assert any("algal" in row for row in limits[1:])
    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        header = (out / name).read_text().splitlines()
        for key in PROVENANCE_KEYS:
            assert any(h.startswith(key) for h in header), f"{name} missing {key}"


def test_gate_a_failure_aborts_everything(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]
    p = tmp_path / "bad_a.yaml"
    p.write_text(yaml.safe_dump(bad))
    out = tmp_path / "outa"
    out.mkdir()
    (out / "limits.csv").write_text("# stale\nclass\nalgal\n")
    assert run.main(["--prereg", str(p), "--out", str(out)]) == 2
    assert not (out / "limits.csv").exists(), (
        "stale limits.csv survived a Gate A failure"
    )
    assert not (out / "sweep.csv").exists(), "stale sweep.csv survived a Gate A failure"


def test_exit_2_when_no_class_passes_gate_b(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    for cls in bad["gate_adaptation"]:
        bad["gate_adaptation"][cls]["measured_c"] = [-100.0]
    p = tmp_path / "nob.yaml"
    p.write_text(yaml.safe_dump(bad))
    assert run.main(["--prereg", str(p), "--out", str(tmp_path / "outb")]) == 2


def test_sweep_row_count_matches_the_prereg_for_passing_classes_only(tmp_path):
    out = tmp_path / "rows"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 0
    prereg = yaml.safe_load(PREREG.read_text())
    n = int(prereg["sweep"]["n_grid"])
    n_omega = len(prereg["omega_grid_k"])
    n_pass = sum(
        1 for c, g in prereg["gate_adaptation"].items() if g["expect"] == "pass"
    )
    expected = 1 + n_pass * n_omega * n
    assert len(_rows(out / "sweep.csv")) == expected, (
        f"sweep.csv has {len(_rows(out / 'sweep.csv'))} lines, prereg implies {expected}"
    )


def test_assumption_drift_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["sigma_w_m2_k4"] = 1.0
    p = tmp_path / "drift.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="sigma_w_m2_k4"):
        run.main(["--prereg", str(p), "--out", str(tmp_path / "o")])


def test_cli_exit_code_is_2_on_gate_a_failure(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]
    p = tmp_path / "cli.yaml"
    p.write_text(yaml.safe_dump(bad))
    out = tmp_path / "cliout"
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(p), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2, proc.stderr
    assert (out / "gates.csv").exists()
    assert not (out / "limits.csv").exists()
    assert not (out / "sweep.csv").exists()


def test_algal_thermal_au_and_binding_are_pinned_against_the_real_prereg():
    """Guards the two regressions a reviewer reproduced by hand: taking the
    inner root instead of the outer one in outer_carbon_crossover, and
    inverting the min() in classify_limit's binding selection. None of the
    structural tests above would catch either -- they check row counts,
    exclusion, and exit codes, never a specific outer_au or binding value.

    The expected thermal_au is computed here from sim.thermal.equilibrium_temperature
    and the prereg's own t_min directly -- NOT by calling run.classify_limit or
    run.build and trusting their internal formula -- so this is an independent
    check, not a tautology."""
    prereg = yaml.safe_load(PREREG.read_text())
    p = prereg["presets"]["algal"]
    a = prereg["assumptions"]
    r_home_au = float(a["r_home_au"])
    sw = prereg["sweep"]
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )

    t_home_independent = equilibrium_temperature(
        r_home_au, float(p["area_ratio"]), float(a["emissivity"]), float(a["albedo"])
    )
    expected_thermal_au = r_home_au * (t_home_independent / float(p["t_min"])) ** 2
    assert expected_thermal_au == pytest.approx(1.1945, abs=1e-4)

    # Measured via the real run in Task 4's report; pinned here so a
    # regression that swaps idx[-1] for idx[0] (the too-hot inner root,
    # ~0.76-0.88 AU per Task 3's Step 5) or min() for max() (which would
    # pick "light", ~75 AU) is caught.
    expected_outer_au = {
        10.0: 1.2120,
        15.0: 1.3795,
        20.0: 1.6180,
        25.0: 1.9723,
        30.0: 2.5301,
    }
    for omega, exp_outer in expected_outer_au.items():
        org = run.build("algal", p, a, omega)
        result = run.classify_limit(org, r_home_au, r_min, r_max, n_grid)
        assert result["temperature"] == pytest.approx(expected_thermal_au, rel=1e-6)
        assert result["carbon"] == pytest.approx(exp_outer, abs=5e-4)
        assert result["binding"] == "temperature"


def test_committed_q2b_csvs_regenerate_exactly(tmp_path):
    src = REPO / "experiments" / "q2b_adapted"
    if not (src / "gates.csv").exists():
        pytest.skip("Q2b has not been run into the repo directory yet")
    out = tmp_path / "regen"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 0
    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        committed = [
            x
            for x in (src / name).read_text().splitlines()
            if not x.startswith("# git_sha=") and not x.startswith("# written=")
        ]
        fresh = [
            x
            for x in (out / name).read_text().splitlines()
            if not x.startswith("# git_sha=") and not x.startswith("# written=")
        ]
        assert committed == fresh, f"{name} does not regenerate"
