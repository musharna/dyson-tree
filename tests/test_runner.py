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


def test_prereg_presets_match_module_presets():
    """The runner builds organisms from prereg['presets']; tests/test_organism.py
    gates sim.organism.PRESETS. Nothing else ties the two together, so a prereg
    r_d could drift inside the gate's width with a fully green suite."""
    run.assert_presets_match(yaml.safe_load(PREREG.read_text()))


def test_preset_drift_refuses_to_run():
    import pytest

    for field, value in (
        ("r_d", 0.30),
        ("a_max", 11.0),
        ("k", 25.0),
        ("leaf_mass_ratio", 0.7),
    ):
        drift = yaml.safe_load(PREREG.read_text())
        drift["presets"]["algal"][field] = value
        with pytest.raises(ValueError, match=field):
            run.assert_presets_match(drift)


def test_preset_drift_refuses_to_run_end_to_end(tmp_path):
    import pytest

    drift = yaml.safe_load(PREREG.read_text())
    # inside the algal gate [0, 1] (I_c = 20*0.30/9.70 = 0.62), so the gate
    # cannot catch it, but it moves the published r*
    drift["presets"]["algal"]["r_d"] = 0.30
    p = tmp_path / "drift.yaml"
    p.write_text(yaml.safe_dump(drift))
    with pytest.raises(ValueError, match="r_d"):
        run.main(["--prereg", str(p), "--out", str(tmp_path / "o")])
    assert not (tmp_path / "o" / "crossover.csv").exists()


def test_unknown_preset_name_refuses_to_run():
    import pytest

    drift = yaml.safe_load(PREREG.read_text())
    drift["presets"]["kelp"] = dict(drift["presets"]["algal"])
    with pytest.raises(ValueError, match="kelp"):
        run.assert_presets_match(drift)


def test_git_sha_failure_carries_git_stderr(tmp_path, monkeypatch):
    import pytest

    monkeypatch.setattr(run, "REPO_ROOT", tmp_path)  # not a git repo
    with pytest.raises(RuntimeError, match="not a git repository"):
        run.git_sha()


def _failing_gate_prereg(tmp_path, name, monkeypatch, r_d, stem):
    """Re-register a preset so its 1 AU compensation irradiance misses the gate.
    assert_presets_match now forbids prereg-only drift, so this edits BOTH
    sources the way a real re-registration would: prereg.yaml and PRESETS."""
    from sim.organism import Organism

    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"][name]["r_d"] = r_d
    monkeypatch.setitem(
        run.PRESETS,
        name,
        Organism(
            name,
            a_max=bad["presets"][name]["a_max"],
            k=bad["presets"][name]["k"],
            r_d=r_d,
            leaf_mass_ratio=bad["presets"][name]["leaf_mass_ratio"],
        ),
    )
    path = tmp_path / stem
    path.write_text(yaml.safe_dump(bad))
    return path


def test_gate_failure_exits_2_and_clears_stale_crossover(tmp_path, monkeypatch):
    """A failing gate must leave no crossover output — including output a
    PREVIOUS passing run already wrote into the same directory. The default
    --out is the experiment directory itself, so the stale-file case is the
    normal invocation, not an edge case."""
    # I_c = 100*3/7 = 42.9, outside [5.3, 9.0]
    bad_path = _failing_gate_prereg(
        tmp_path, "vascular", monkeypatch, 3.0, "prereg_bad.yaml"
    )
    out = tmp_path / "out_bad"
    out.mkdir()
    # pre-seed the artefacts of an earlier PASSING run
    for name in ("sweep.csv", "crossover.csv"):
        (out / name).write_text(
            (REPO / "experiments" / "q1_crossover" / name).read_text()
        )
    rc = run.main(["--prereg", str(bad_path), "--out", str(out)])
    assert rc == 2
    assert (out / "calibration.csv").exists()
    assert not (out / "crossover.csv").exists(), (
        "stale crossover.csv from a previous passing run survived a gate failure"
    )
    assert not (out / "sweep.csv").exists(), (
        "stale sweep.csv from a previous passing run survived a gate failure"
    )
    _, body = _read_header_and_rows(out / "calibration.csv")
    assert any(",False" in l for l in body[1:])


def test_gate_failure_in_a_virgin_directory_writes_no_crossover(tmp_path, monkeypatch):
    bad_path = _failing_gate_prereg(
        tmp_path, "vascular", monkeypatch, 3.0, "prereg_bad2.yaml"
    )
    out = tmp_path / "out_virgin"
    assert run.main(["--prereg", str(bad_path), "--out", str(out)]) == 2
    assert (out / "calibration.csv").exists()
    assert not (out / "crossover.csv").exists()
    assert not (out / "sweep.csv").exists()


def test_real_prereg_passes_and_writes_all_csvs_with_provenance(tmp_path):
    out = tmp_path / "out_ok"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc == 0
    for name in ("calibration.csv", "sweep.csv", "crossover.csv"):
        header, body = _read_header_and_rows(out / name)
        assert any(l.startswith("# git_sha=") for l in header), name
        assert any(l.startswith("# physiology_md5=") for l in header), name
        assert any(l.startswith("# organism_md5=") for l in header), name
        assert any(l.startswith("# prereg_md5=") for l in header), name
        assert any(l.startswith("# python=") for l in header), name
        assert any(l.startswith("# numpy=") for l in header), name
        assert any(l.startswith("# scipy=") for l in header), name
        assert len(body) >= 2, name
    # calibration.csv is one row per preset; `>= 2` cannot fail on a runner
    # that silently drops a class, which is the whole point of the gate.
    _, calib = _read_header_and_rows(out / "calibration.csv")
    assert calib[0] == "class,k,observed_umol,gate_lo,gate_hi,passed"
    assert len(calib) == 1 + len(yaml.safe_load(PREREG.read_text())["presets"])
    _, cross = _read_header_and_rows(out / "crossover.csv")
    assert cross[0] == "class,k,r_star_au,pred_lo,pred_hi,inside"
    assert len(cross) == 1 + 3 + 3  # header + 3 k values per preset

    # sweep.csv is the only place the pre-registration's declared n_grid is
    # observable. `>= 2` passed on a sweep that emitted one row per series.
    prereg = yaml.safe_load(PREREG.read_text())
    n_grid = int(prereg["sweep"]["n_grid"])
    expected = 1 + sum(  # column header + one row per (preset, k, grid point)
        len(p["k_grid"]) * n_grid for p in prereg["presets"].values()
    )
    _, sweep = _read_header_and_rows(out / "sweep.csv")
    assert sweep[0] == "class,k,r_au,net_carbon"
    assert len(sweep) == expected, (
        f"sweep.csv has {len(sweep)} lines, pre-registration implies {expected} "
        f"(n_grid={n_grid})"
    )


def test_committed_csvs_regenerate_exactly(tmp_path):
    """The branch's whole thesis: the committed record is what this code
    produces. Re-run and diff against what is checked in. git_sha and written
    are the only lines allowed to move — everything else, body and provenance,
    must match, so a source or numeric-stack change that is not followed by a
    re-run fails here."""
    import difflib

    volatile = ("# git_sha=", "# written=")
    out = tmp_path / "regen"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 0
    for name in ("calibration.csv", "sweep.csv", "crossover.csv"):
        committed = REPO / "experiments" / "q1_crossover" / name

        def stable(path):
            return [
                line
                for line in path.read_text().splitlines()
                if not line.startswith(volatile)
            ]

        want, got = stable(committed), stable(out / name)
        if want != got:
            diff = "\n".join(
                list(
                    difflib.unified_diff(
                        want,
                        got,
                        fromfile=f"committed/{name}",
                        tofile=f"rerun/{name}",
                        lineterm="",
                    )
                )[:40]
            )
            raise AssertionError(
                f"{name} does not regenerate from the current code. Re-run "
                f"experiments/q1_crossover/run.py and commit, or explain the "
                f"numeric change:\n{diff}"
            )


def test_runner_passes_prereg_n_grid_to_the_root_search(tmp_path, monkeypatch):
    """prereg declares one n_grid. It used to govern only sweep.csv's
    resolution while the root bracket used a hidden default of 400."""
    prereg = yaml.safe_load(PREREG.read_text())
    declared = int(prereg["sweep"]["n_grid"])
    seen = []
    real = run.crossover_distance_for

    def spy(org, **kw):
        seen.append(kw.get("n_grid"))
        return real(org, **kw)

    monkeypatch.setattr(run, "crossover_distance_for", spy)
    assert run.main(["--prereg", str(PREREG), "--out", str(tmp_path / "o")]) == 0
    assert seen and set(seen) == {declared}, seen


def test_assumption_mismatch_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["par_fraction"] = 0.5
    bad_path = tmp_path / "prereg_drift.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    import pytest

    with pytest.raises(ValueError, match="par_fraction"):
        run.main(["--prereg", str(bad_path), "--out", str(tmp_path / "o")])


def test_cli_exit_code_on_gate_failure(tmp_path):
    """Out-of-process: the real CLI, not main() in this interpreter. Both
    sources are re-registered together (prereg.yaml and PRESETS), because
    prereg-only drift is now refused before the gate is ever reached."""
    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"]["algal"]["r_d"] = 5.0  # I_c = 20*5/5 = 20, outside [0, 1]
    bad_path = tmp_path / "p.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    driver = tmp_path / "driver.py"
    driver.write_text(
        "import sys\n"
        f"sys.path.insert(0, {str(RUN.parent)!r})\n"
        "import run\n"
        "from sim.organism import ALGAL, Organism\n"
        "run.PRESETS['algal'] = Organism('algal', a_max=ALGAL.a_max, k=ALGAL.k,\n"
        "                                r_d=5.0, leaf_mass_ratio=ALGAL.leaf_mass_ratio)\n"
        "sys.exit(run.main(sys.argv[1:]))\n"
    )
    proc = subprocess.run(
        [
            sys.executable,
            str(driver),
            "--prereg",
            str(bad_path),
            "--out",
            str(tmp_path / "o"),
        ],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "GATE FAILED" in proc.stdout


def test_cli_exit_code_is_nonzero_on_preset_drift(tmp_path):
    """The real CLI, prereg-only drift: refused loudly before any output."""
    drift = yaml.safe_load(PREREG.read_text())
    drift["presets"]["algal"]["r_d"] = 0.30
    p = tmp_path / "drift_cli.yaml"
    p.write_text(yaml.safe_dump(drift))
    out = tmp_path / "o"
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(p), "--out", str(out)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode != 0
    assert "does not match" in proc.stderr and "r_d" in proc.stderr, proc.stderr
    assert not (out / "crossover.csv").exists()
