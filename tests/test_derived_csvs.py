"""The derived CSVs under experiments/ must regenerate from the committed code.

`tests/test_runner.py::test_committed_csvs_regenerate_exactly` makes that promise
for the three registered runners. These files are the same promise for the three
derivation tools: every number `docs/FINDINGS.md` prints has a committed producer,
and this is what keeps that true rather than true-on-the-day-it-was-written.

The tools carry their own positive controls -- each one refuses to write a file
unless it first reproduces the committed baseline it is extending (limits.csv's
carbon column, crossover.csv's two registered r*). Those controls run here too,
because these tests invoke the tools' real `main()`. What the tests add is the
diff against what is checked in.
"""

from __future__ import annotations

import csv
import difflib
import importlib.util
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "tools"))

# git_sha and written move on every run by design; everything else -- the data
# rows, the derived_by line, and every source md5 -- must not.
VOLATILE = ("# git_sha=", "# written=")

# (tool module, committed artifact)
DERIVATIONS = [
    ("derive_q2b_candidates", "experiments/q2b_adapted/candidates.csv"),
    ("derive_q2b_floor_response", "experiments/q2b_adapted/floor_response.csv"),
    ("derive_q1_reachability", "experiments/q1_crossover/reachability.csv"),
]


def load_tool(name: str):
    """Import a tools/*.py by path. tools/ is not a package -- setuptools is
    configured to ship only sim* and experiments* -- so there is nothing to
    import normally."""
    spec = importlib.util.spec_from_file_location(name, REPO / "tools" / f"{name}.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def stable(path: Path) -> list[str]:
    return [
        line for line in path.read_text().splitlines() if not line.startswith(VOLATILE)
    ]


@pytest.mark.parametrize("tool_name,artifact", DERIVATIONS)
def test_derived_csv_regenerates_exactly(tool_name, artifact, tmp_path):
    tool = load_tool(tool_name)
    out = tmp_path / Path(artifact).name
    assert tool.main(["--out", str(out)]) == 0

    committed = REPO / artifact
    want, got = stable(committed), stable(out)
    if want != got:
        diff = "\n".join(
            list(
                difflib.unified_diff(
                    want,
                    got,
                    fromfile=f"committed/{artifact}",
                    tofile=f"rerun/{artifact}",
                    lineterm="",
                )
            )[:40]
        )
        raise AssertionError(
            f"{artifact} does not regenerate from the current code. Re-run "
            f"python3 tools/{tool_name}.py and commit, or explain the "
            f"numeric change:\n{diff}"
        )


@pytest.mark.parametrize("_tool_name,artifact", DERIVATIONS)
def test_derived_csv_header_names_its_producer(_tool_name, artifact):
    """A derived file must be distinguishable from a runner's output at a
    glance, and must say what it was computed from. Without `derived_by` a
    reader finding candidates.csv beside limits.csv has no way to tell which
    one the registered runner wrote."""
    lines = (REPO / artifact).read_text().splitlines()
    header = [ln for ln in lines if ln.startswith("#")]
    keys = [ln.split("=", 1)[0] for ln in header]

    assert "# derived_by" in keys, f"{artifact} header does not name its producer"
    assert "# git_sha" in keys, f"{artifact} header does not name a commit"
    assert any(ln.startswith("# source=") for ln in header), (
        f"{artifact} header names no source input"
    )

    producer = next(ln for ln in header if ln.startswith("# derived_by="))
    script = REPO / producer.split("=", 1)[1]
    assert script.is_file(), (
        f"{artifact} names a producer that is not committed: {script}"
    )

    # Every source it claims to have read must exist and still hash the same --
    # a stale md5 means the artifact predates its own input.
    from derive_provenance import md5

    for ln in (ln for ln in header if ln.startswith("# source=")):
        rel, claimed = ln.removeprefix("# source=").split(" md5=")
        src = REPO / rel
        assert src.is_file(), f"{artifact} names a missing source: {rel}"
        assert md5(src) == claimed, (
            f"{artifact} was derived from a stale {rel}: header says {claimed}, "
            f"the committed file hashes to {md5(src)}. Re-run its producer."
        )


def read_rows(artifact: str) -> list[dict]:
    lines = [
        ln
        for ln in (REPO / artifact).read_text().splitlines()
        if not ln.startswith("#")
    ]
    return list(csv.DictReader(lines))


def test_candidates_csv_agrees_with_committed_limits_csv():
    """candidates.csv adds the temperature and light columns that limits.csv
    never held. The column the two DO share -- the carbon candidate, which the
    runner reports as outer_au -- has to agree, or the new file is describing a
    different run than the registered one."""
    limits = {r["omega"]: r for r in read_rows("experiments/q2b_adapted/limits.csv")}
    assert limits, "limits.csv has no rows"

    for row in read_rows("experiments/q2b_adapted/candidates.csv"):
        if row["in_limits_csv"] != "yes":
            continue
        committed = limits[row["omega"]]
        assert row["class"] == committed["class"]
        assert float(row["carbon_au"]) == pytest.approx(
            float(committed["outer_au"]), abs=5e-5
        ), f"omega={row['omega']}: candidates.csv carbon disagrees with limits.csv"
        assert row["binding"] == committed["binding"]


def test_candidates_csv_holds_the_vascular_rows_the_runner_excludes():
    """Gate B keeps vascular out of limits.csv, and that exclusion is registered
    and must stay. The vascular rows therefore exist ONLY here, labelled -- which
    is the whole reason FINDINGS' second table had no artifact."""
    rows = read_rows("experiments/q2b_adapted/candidates.csv")
    vascular = [r for r in rows if r["class"] == "vascular"]
    assert len(vascular) == 5, "expected five vascular omega rows"
    assert all(r["in_limits_csv"].startswith("no") for r in vascular), (
        "vascular rows must be labelled as absent from limits.csv"
    )
    assert not any(
        r["class"] == "vascular"
        for r in read_rows("experiments/q2b_adapted/limits.csv")
    ), "gate B's exclusion of vascular from limits.csv has been broken"

    # The point of the table: the registered prediction WOULD have held here.
    carbon_bound = {r["omega"] for r in vascular if r["binding"] == "carbon"}
    assert carbon_bound == {"25", "30"}, (
        f"FINDINGS says vascular binds on carbon at omega 25 and 30; got {carbon_bound}"
    )
