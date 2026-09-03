import math
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
import yaml

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
RUN = REPO / "experiments" / "q2b_adapted" / "run.py"
PREREG = REPO / "experiments" / "q2b_adapted" / "prereg.yaml"

from experiments.q2b_adapted import run  # noqa: E402
from sim.organism import Organism  # noqa: E402
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


# --- outer_carbon_crossover / classify_limit: unguarded branches -----------
#
# All three of outer_carbon_crossover's disclosed branches survive the suite
# above unchanged: nan->0.0, the shape guard->False, and dropping
# "none_in_window" all still pass 117 tests, because the real prereg never
# exercises them -- vascular is excluded at Gate B and algal always produces
# exactly two roots. These tests use synthetic net_fn closures (not routed
# through a real class/omega) so the three disclosed, non-real-data shapes
# are each actually reached.


def test_outer_carbon_crossover_all_negative_returns_nan():
    """A curve that never crosses zero: the registered "no crossover exists"
    outcome (prereg.yaml curve_shape, vascular at omega in {10,15,20}).
    Mutant this guards: `return float("nan")` -> `return 0.0`."""
    always_negative = lambda r: -1.0 - 0.01 * r  # noqa: E731
    result = run.outer_carbon_crossover(always_negative, 0.5, 100.0, 50)
    assert math.isnan(result)


def test_outer_carbon_crossover_three_root_curve_raises_not_swallowed():
    """A shape Task 3 never measured (three sign changes, not the registered
    [] or [(-1,1),(1,-1)]) must raise UnexpectedSignStructure rather than
    silently picking a root or returning NaN. Mutant this guards: the shape
    guard `if transitions != [(-1, 1), (1, -1)]:` -> `if False:`, which would
    let this net_fn fall through to `idx[-1]` and return a number instead of
    raising."""

    def three_root(r):
        if r < 2.0:
            return -1.0
        if r < 5.0:
            return 1.0
        if r < 20.0:
            return -1.0
        return 1.0

    with pytest.raises(run.UnexpectedSignStructure, match="unexpected sign structure"):
        run.outer_carbon_crossover(three_root, 0.5, 100.0, 60)


def test_outer_carbon_crossover_two_root_shape_still_returns_the_outer_root():
    """Positive control for the two tests above: the registered two-root
    shape must still work, so a guard that rejects everything is not what is
    passing the negative cases."""

    def two_root(r):
        return -1.0 if (r < 1.0 or r > 10.0) else 1.0

    result = run.outer_carbon_crossover(two_root, 0.5, 100.0, 60)
    assert 9.0 < result < 11.0


def _degenerate_organism() -> Organism:
    """An organism whose respiration swamps assimilation everywhere on the
    registered sweep window, so BOTH net_carbon (light) and net_carbon_adapted
    (carbon) are negative at every grid point -- verified directly: the
    maximum of net_carbon_adapted over the sweep grid is ~-1e-6, never
    positive. r_d=100 against a_max=10 (leaf_mass_ratio=1) makes
    organism_respiration alone exceed a_max, the ceiling gross_assimilation
    can ever reach."""
    return Organism(
        "degenerate",
        a_max=10.0,
        k=20.0,
        r_d=100.0,
        leaf_mass_ratio=1.0,
        area_ratio=4.0,
        t_min=254.65,
        omega=20.0,
    )


def test_classify_limit_all_nonfinite_candidates_reports_none_in_window():
    """The three-way selection must degrade to "none_in_window" when nothing
    is finite, rather than raising (e.g. min() on an empty dict). Mutant this
    guards: `min(finite, key=finite.get) if finite else "none_in_window"` ->
    `min(finite, key=finite.get)` (dropping the empty-dict fallback), which
    raises ValueError instead of returning the disclosed sentinel.

    thermal_au is a closed-form (r_home_au * (T_eq/t_min)**2) that cannot go
    non-finite for any valid Organism, so equilibrium_temperature -- the one
    function classify_limit calls to build it -- is monkeypatched to return
    NaN for the duration of this test only, and restored in a finally block.
    light_au and carbon_au go NaN on their own via the degenerate organism
    above (no monkeypatching needed for those two)."""
    org = _degenerate_organism()
    original = run.equilibrium_temperature
    run.equilibrium_temperature = lambda *a, **k: float("nan")
    try:
        result = run.classify_limit(org, 1.0, 0.5, 100.0, 50)
    finally:
        run.equilibrium_temperature = original
    assert run.equilibrium_temperature is original, (
        "equilibrium_temperature not restored"
    )
    assert not np.isfinite(result["temperature"])
    assert not np.isfinite(result["light"])
    assert not np.isfinite(result["carbon"])
    assert result["binding"] == "none_in_window"
