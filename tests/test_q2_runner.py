import csv
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
from sim.organism import Organism  # noqa: E402
from sim.physiology import crossover_distance  # noqa: E402
from sim.thermal import equilibrium_temperature, temperature_response  # noqa: E402


def _dict_rows(path):
    """CSV rows as dicts, provenance-comment lines stripped."""
    lines = [ln for ln in path.read_text().splitlines() if not ln.startswith("#")]
    return list(csv.DictReader(lines))


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


def test_outer_equilibrium_carbon_crossover_pins_the_outer_root_not_the_inner():
    """net_carbon_at_equilibrium is NOT monotone: it runs negative (hot inner
    edge, respiration explodes) -> positive -> negative (cold outer edge) on
    the registered window. sim.physiology.crossover_distance -- correct for
    Q1's monotone net_carbon -- returns the FIRST sign change, which here is
    the wrong, too-hot INNER root. This pins the algal class's outer root at
    its middle registered t_min (254.65 K) to the value verified independently
    against the traced net-carbon values at r=0.5/1.0/1.2 AU (-246.06 / +5.31 /
    -0.016): a selector that returned the inner root instead would land near
    ~0.6-0.7 AU, not ~1.19 AU, and would fail this assertion."""
    prereg = yaml.safe_load(PREREG.read_text())
    a = prereg["assumptions"]
    p = prereg["presets"]["algal"]
    t_min = float(p["t_min_grid"][1])
    assert t_min == pytest.approx(254.65)
    org = run.build("algal", p, a, t_min)
    sw = prereg["sweep"]
    r_min, r_max, n_grid = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    outer = run.outer_equilibrium_carbon_crossover(
        org.net_carbon_at_equilibrium, r_min, r_max, n_grid
    )
    assert outer == pytest.approx(1.19377, abs=1e-4)
    # The wrongly-selected inner root (hot edge) sits well below 1 AU -- the
    # traced net carbon is already positive at 1.0 AU (+5.31), so a selector
    # that grabbed the first sign change instead of the last would report
    # something less than 1.0, not ~1.19.
    assert outer > 1.0


def test_outer_equilibrium_carbon_crossover_rejects_an_unexpected_sign_shape():
    """A monotone-decreasing curve (Q1-shaped: one sign change, not the
    negative->positive->negative shape this selector assumes) must not be
    silently handed a root -- it must fail loud."""
    with pytest.raises(ValueError, match="unexpected sign structure"):
        run.outer_equilibrium_carbon_crossover(
            lambda r: 10.0 - r, r_min=0.5, r_max=100.0, n_grid=400
        )


def test_shape_violation_propagates_instead_of_becoming_a_false_temperature_verdict(
    tmp_path, monkeypatch
):
    """A violated sign-structure assumption must abort the run, not turn into NaN.

    The guard in outer_equilibrium_carbon_crossover is worthless if main()
    swallows it: a NaN carbon_equilibrium drops out of `candidates`, so
    `binding` falls through to "temperature" -- and the run then exits 0
    reporting a CONFIRMATION of the registered prediction, produced by an
    assumption that did not hold. That is strictly worse than crashing.

    Gate 2 fails on the real prereg, so the sweep is never reached; widen only
    the anchors in an in-memory copy to get there, then force a Q1-shaped
    (monotone) curve so the structure check fires.
    """
    prereg = yaml.safe_load(PREREG.read_text())
    for anchor in prereg["gate_response"]["anchors"]:
        anchor["lo"], anchor["hi"] = 0.0, 1.0
    path = tmp_path / "allpass_shape.yaml"
    path.write_text(yaml.safe_dump(prereg))

    # Monotone decreasing: one sign change, not the assumed two.
    monkeypatch.setattr(
        run.Organism, "net_carbon_at_equilibrium", lambda self, r, k=None: 10.0 - r
    )
    out = tmp_path / "shape"
    with pytest.raises(run.UnexpectedSignStructure, match="unexpected sign structure"):
        run.main(["--prereg", str(path), "--out", str(out)])
    assert not (out / "limits.csv").exists(), (
        "a limits.csv was written despite a violated structural assumption"
    )
    # Positive control: the same widened prereg with the REAL curve reaches the
    # sweep and exits 0, so the failure above is the shape, not the widening.
    out_ok = tmp_path / "shape_ok"
    monkeypatch.undo()
    assert run.main(["--prereg", str(path), "--out", str(out_ok)]) == 0
    assert (out_ok / "limits.csv").exists()


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


def test_gate_thermal_alone_fails_the_run(tmp_path):
    """test_gate_thermal_failure_exits_2_and_clears_stale_limits above breaks
    gate 1 while gate 2 is left at its real, already-failing anchors -- so
    rc == 2 is over-determined and cannot tell correct `ok &= passed`
    accumulation from a deleted gate-1 accumulation (gate 2 alone would still
    force rc == 2). Here gate 2's anchors are widened to pass (in-memory copy
    only -- prereg.yaml itself stays frozen) so gate 1 is the SOLE failure:
    deleting `ok &= passed` for gate 1 would leave `ok` following gate 2 only,
    which now passes, and the run would wrongly exit 0."""
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]  # impossible band
    for anchor in bad["gate_response"]["anchors"]:
        anchor["lo"], anchor["hi"] = 0.0, 1.0
    p = tmp_path / "gate1_only.yaml"
    p.write_text(yaml.safe_dump(bad))
    out = tmp_path / "gate1_only_out"

    assert run.main(["--prereg", str(p), "--out", str(out)]) == 2
    rows = _rows(out / "gates.csv")[1:]  # drop the CSV header row
    thermal_rows = [r for r in rows if r.startswith("thermal,")]
    assert thermal_rows and thermal_rows[0].split(",")[-1] == "False", (
        f"expected the thermal gate to be the failing row: {thermal_rows}"
    )
    response_rows = [r for r in rows if r.startswith("response,")]
    assert response_rows and all(r.split(",")[-1] == "True" for r in response_rows), (
        f"positive control failed: response gate should pass here: {response_rows}"
    )
    assert not (out / "limits.csv").exists()


def test_assumption_drift_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["sigma_w_m2_k4"] = 1.0
    p = tmp_path / "drift.yaml"
    p.write_text(yaml.safe_dump(bad))
    with pytest.raises(ValueError, match="sigma_w_m2_k4"):
        run.main(["--prereg", str(p), "--out", str(tmp_path / "o")])


def test_real_prereg_gate_failure_writes_gates_csv_with_provenance(tmp_path):
    """Against the real, frozen prereg, gate 2 always fails, so rc == 0 never
    happens here (that path -- writing sweep.csv/limits.csv -- is exercised by
    test_synthetic_all_pass_prereg_exercises_the_rc0_path instead, on a widened
    in-memory copy). This test's name used to promise all three CSVs while
    only ever checking one, with a dead `if rc == 0:` branch that never ran."""
    out = tmp_path / "ok"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc == 2
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


def test_cli_exits_nonzero_when_a_gate_fails(tmp_path):
    """`proc.returncode != 0` is also satisfied by exit 1 from an unhandled
    traceback -- e.g. a RuntimeError raised right after load_prereg -- which
    is a completely broken runner, not the documented gate-failure contract
    (the module docstring: 0 = both gates passed, 2 = a gate failed). Assert
    the exact documented code and that gates.csv actually got written, which
    an unhandled exception before run_gates() would not produce."""
    bad = yaml.safe_load(PREREG.read_text())
    bad["gate_thermal"]["t_eq_k"] = [1000.0, 2000.0]
    p = tmp_path / "bad2.yaml"
    p.write_text(yaml.safe_dump(bad))
    out = tmp_path / "o2"
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(p), "--out", str(out)],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 2, (
        f"expected the documented gate-failure code 2, got {proc.returncode}\n"
        f"stderr: {proc.stderr}"
    )
    assert (out / "gates.csv").exists()
    assert not (out / "limits.csv").exists()


def test_response_gate_rejects_a_wrong_functional_form(tmp_path, monkeypatch):
    """A flat response of 0.99 is physically absurd -- it says a frozen organism
    photosynthesises at 99% of optimum. Gate 2 must reject it.

    Against the real, frozen prereg, Gate 2 already fails on its own (mesophyte
    t_opt vs cold-adapted anchors) and already emits `False` rows -- so
    `rc == 2` and `any("False" in r for r in rows)` hold identically whether
    or not the monkeypatch takes effect. Assert the recorded `observed` value
    is the patched 0.9900 (proving the substitution actually ran) AND that
    the thermal gate row is True (the positive control: only the response
    gate is broken here, not thermal physics)."""
    monkeypatch.setattr(run, "temperature_response", lambda t, t_min, t_opt: 0.99)
    out = tmp_path / "wrong"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 2
    rows = _rows(out / "gates.csv")[1:]  # drop the CSV header row
    response_rows = [r for r in rows if r.startswith("response,")]
    assert response_rows, f"no response gate rows in {rows}"
    for r in response_rows:
        fields = r.split(",")
        assert fields[2] == "0.9900", f"patch did not take effect: {r}"
        assert fields[-1] == "False", f"gate 2 accepted a flat 0.99 response: {r}"
    thermal_rows = [r for r in rows if r.startswith("thermal,")]
    assert thermal_rows and thermal_rows[0].split(",")[-1] == "True", (
        f"positive control failed: thermal gate did not pass: {thermal_rows}"
    )
    assert not (out / "limits.csv").exists()


def test_synthetic_all_pass_prereg_exercises_the_rc0_path(tmp_path):
    """Against the real, frozen prereg, gate 2 always fails (mesophyte t_opt vs
    cold-adapted anchors), so `rc == 0` never happens in
    test_real_prereg_gate_failure_writes_only_gates_csv, and sweep.csv/limits.csv
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

    # --- value assertions -----------------------------------------------
    # Everything above checks provenance keys, row counts, and the header
    # line -- none of it pins a single number or a `binding` verdict. Four
    # mutants each pass this whole test 77/77 unnoticed: build() hardcoding
    # t_min=265.15 instead of the swept value, `binding = max(...)` instead
    # of `min(...)`, sweep.csv's t_eq column emitting a constant "300.0000",
    # and gate 1's `ok &= passed` deleted (the last is covered by
    # test_gate_thermal_alone_fails_the_run instead). The checks below
    # recompute expected numbers from the documented primitives directly --
    # never by calling back into run.py's own sweep/selection code -- so they
    # cannot pass just because run.py agrees with itself.
    a = prereg["assumptions"]
    sweep_dicts = _dict_rows(out / "sweep.csv")
    limits_dicts = _dict_rows(out / "limits.csv")

    from collections import defaultdict

    by_key = defaultdict(list)
    for row in sweep_dicts:
        by_key[(row["class"], row["t_min"])].append(row)

    for (cls, t_min_str), rows_for_key in by_key.items():
        preset = prereg["presets"][cls]
        t_min = float(t_min_str)
        # Pick a row where the response is neither saturated at 0 (T <= t_min)
        # nor at 1 (T >= t_opt) -- those two flats are exactly where a
        # hardcoded t_min could coincidentally still match, since f(T)=1 for
        # T >= t_opt regardless of which t_min was used to build the curve.
        mid_rows = [r for r in rows_for_key if 0.05 < float(r["response"]) < 0.95]
        assert mid_rows, (
            f"{cls}/{t_min_str}: no sweep row in the response's linear zone"
        )
        row = mid_rows[len(mid_rows) // 2]
        r_au = float(row["r_au"])
        t_eq_expected = equilibrium_temperature(
            r_au,
            float(preset["area_ratio"]),
            float(a["emissivity"]),
            float(a["albedo"]),
        )
        # t_eq: kills a constant "300.0000" column outright.
        assert float(row["t_eq"]) == pytest.approx(t_eq_expected, abs=1e-3), (
            f"{cls}/{t_min_str} r={r_au}: t_eq {row['t_eq']} != independently "
            f"computed {t_eq_expected:.4f}"
        )
        # response computed against the SWEPT t_min (not whatever build() may
        # have hardcoded internally) -- this is the one that catches build()
        # silently ignoring its t_min argument, since the two organism
        # classes are built from a different t_min at each grid point.
        response_expected = temperature_response(
            t_eq_expected, t_min, float(a["t_opt_k"])
        )
        assert float(row["response"]) == pytest.approx(response_expected, rel=1e-4), (
            f"{cls}/{t_min_str} r={r_au}: response {row['response']} != "
            f"independently computed {response_expected:.6g} for t_min={t_min}"
        )

    # thermal_au must differ across a class's three registered t_min values --
    # a build() that hardcoded t_min for the Organism would still leave
    # thermal_au varying today (it is computed from the loop's own t_min, not
    # org.t_min), but this pins the observable directly rather than assuming
    # that wiring, and would catch a future refactor that routed thermal_au
    # through org.t_min instead.
    for cls in ("vascular", "algal"):
        vals = {r["thermal_au"] for r in limits_dicts if r["class"] == cls}
        assert len(vals) == 3, (
            f"{cls}: expected 3 distinct thermal_au values across t_min_grid, "
            f"got {vals}"
        )

    # binding, hand-derived independently for one row (vascular, t_min=265.15):
    # each of the three candidate distances is recomputed from primitives
    # (Organism, crossover_distance, outer_equilibrium_carbon_crossover), then
    # `min()` is applied here in the test, separately from run.py's own
    # candidates/min() call -- this is what a binding=max() mutant fails.
    preset = prereg["presets"]["vascular"]
    t_min_check = float(preset["t_min_grid"][0])
    org_check = Organism(
        "vascular",
        a_max=preset["a_max"],
        k=preset["k"],
        r_d=preset["r_d"],
        leaf_mass_ratio=preset["leaf_mass_ratio"],
        area_ratio=preset["area_ratio"],
        t_min=t_min_check,
        t_opt=float(a["t_opt_k"]),
        emissivity=float(a["emissivity"]),
        albedo=float(a["albedo"]),
    )
    sw = prereg["sweep"]
    r_min, r_max, ng = (
        float(sw["r_min_au"]),
        float(sw["r_max_au"]),
        int(sw["n_grid"]),
    )
    t_1au = equilibrium_temperature(
        1.0, org_check.area_ratio, org_check.emissivity, org_check.albedo
    )
    thermal_expected = (t_1au / t_min_check) ** 2
    carbon_fixed_expected = crossover_distance(
        org_check.net_carbon, r_min=r_min, r_max=r_max, n_grid=ng
    )
    carbon_eq_expected = run.outer_equilibrium_carbon_crossover(
        org_check.net_carbon_at_equilibrium, r_min, r_max, ng
    )
    candidates_expected = {
        "temperature": thermal_expected,
        "carbon_fixed_t": carbon_fixed_expected,
        "carbon_equilibrium": carbon_eq_expected,
    }
    binding_expected = min(candidates_expected, key=candidates_expected.get)

    row = next(
        r
        for r in limits_dicts
        if r["class"] == "vascular" and float(r["t_min"]) == t_min_check
    )
    assert row["binding"] == binding_expected, (
        f"binding {row['binding']} != hand-derived {binding_expected} "
        f"(candidates={candidates_expected})"
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


def test_committed_q2_csvs_regenerate_exactly(tmp_path):
    """The committed record must be what the committed code produces. This
    also asserts the branch's headline claim -- "the registered run exits
    2" -- which nothing else in this suite states against the real prereg
    directly (test_real_prereg_gate_failure_writes_gates_csv_with_provenance
    covers the same fact, but a regeneration test asserting nothing about the
    return code, only that byte content matches, is silent on the one thing
    the committed CSVs are evidence FOR)."""
    src = REPO / "experiments" / "q2_thermal"
    if not (src / "gates.csv").exists():
        pytest.skip("Q2 has not been run into the repo directory yet")
    out = tmp_path / "regen"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc == 2, "the registered Q2 run is expected to exit 2 (gate 2 fails)"
    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        if not (src / name).exists():
            continue
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
