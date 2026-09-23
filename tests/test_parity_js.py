"""The JS port in web/model.js must agree with the Python model.

web/parity.mjs recomputes every quantity in web/fixtures.json with the JS port
and prints raw numbers. All comparison happens HERE: the implementation under
test never reports its own verdict.

If `node` is missing this test FAILS rather than skips. A skipped parity check
is a parity check that cannot fail, and the whole point of this file is that the
browser page cannot drift from the Python the repo's results came from.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "web" / "fixtures.json"
PARITY = ROOT / "web" / "parity.mjs"


@pytest.fixture(scope="module")
def fx() -> dict:
    return json.loads(FIXTURES.read_text())


@pytest.fixture(scope="module")
def js(fx) -> dict:
    node = shutil.which("node")
    assert node, (
        "node is required for the JS parity check and was not found on PATH. "
        "This test fails rather than skips on purpose: a skipped parity check "
        "cannot fail, and web/model.js would then be free to drift from sim/."
    )
    proc = subprocess.run(
        [node, str(PARITY)], capture_output=True, text=True, timeout=300
    )
    assert proc.returncode == 0, f"node web/parity.mjs failed:\n{proc.stderr}"
    return json.loads(proc.stdout)


def tol_for(fx: dict, quantity: str) -> tuple[float, float]:
    t = fx["tolerances"][quantity]
    return float(t["rtol"]), float(t["atol"])


def check(fx, quantity, label, ref, got):
    """abs_err <= atol + rtol*|ref|, with the tolerance read from the fixture."""
    rtol, atol = tol_for(fx, quantity)
    assert got is not None, f"{quantity} [{label}]: JS returned null, Python has {ref}"
    err = abs(got - ref)
    limit = atol + rtol * abs(ref)
    assert err <= limit, (
        f"{quantity} [{label}]: |{got!r} - {ref!r}| = {err:.6g} > "
        f"{limit:.6g} (rtol={rtol:g}, atol={atol:g})"
    )


def check_series(fx, quantity, label, refs, gots):
    assert len(gots) == len(refs), f"{quantity} [{label}]: length {len(gots)} != {len(refs)}"
    rtol, atol = tol_for(fx, quantity)
    worst = (-1.0, None)
    for i, (ref, got) in enumerate(zip(refs, gots)):
        assert got is not None, f"{quantity} [{label}] index {i}: JS returned null"
        err = abs(got - ref)
        limit = atol + rtol * abs(ref)
        if err - limit > worst[0]:
            worst = (err - limit, (i, ref, got, err, limit))
    assert worst[1] is not None, f"{quantity} [{label}]: empty series"
    i, ref, got, err, limit = worst[1]
    assert err <= limit, (
        f"{quantity} [{label}] index {i} (r={fx['grid_au'][i]:.6g} AU): "
        f"|{got!r} - {ref!r}| = {err:.6g} > {limit:.6g} "
        f"(rtol={rtol:g}, atol={atol:g})"
    )


def test_fixture_provenance_matches_this_tree(fx):
    """The fixtures must describe THIS model, not an older one."""
    import hashlib

    for mod, key in (
        ("physiology", "physiology_md5"),
        ("thermal", "thermal_md5"),
        ("organism", "organism_md5"),
        ("vessel", "vessel_md5"),
    ):
        live = hashlib.md5((ROOT / "sim" / f"{mod}.py").read_bytes()).hexdigest()
        assert live == fx["provenance"][key], (
            f"sim/{mod}.py has changed since web/fixtures.json was generated. "
            f"Re-run `python3 tools/make_fixtures.py` and commit the result."
        )
    prereg = hashlib.md5(
        (ROOT / "experiments" / "q1_crossover" / "prereg.yaml").read_bytes()
    ).hexdigest()
    assert prereg == fx["provenance"]["prereg_md5"]
    q4 = hashlib.md5(
        (ROOT / "experiments" / "q4_vessel" / "prereg.yaml").read_bytes()
    ).hexdigest()
    assert q4 == fx["provenance"]["prereg_q4_md5"] == "d8707a6607db6d54a006e14af9dcfe79"
    table = hashlib.md5((ROOT / "sim" / "spectral_table.csv").read_bytes()).hexdigest()
    assert table == fx["provenance"]["spectral_table_md5"]


def test_js_constants_match(fx, js):
    for name, ref in fx["constants"].items():
        assert js["constants"][name] == ref, f"constant {name}: JS {js['constants'][name]} != Python {ref}"


def test_js_scalars_match(fx, js):
    for cls, kase in fx["cases"].items():
        got = js["cases"][cls]
        for quantity in (
            "leaf_respiration",
            "organism_respiration",
            "adapted_t_opt_home_1au",
        ):
            check(fx, quantity if quantity in fx["tolerances"] else "irradiance",
                  f"{cls}.{quantity}", kase[quantity], got[quantity])


def test_js_series_match(fx, js):
    for cls, kase in fx["cases"].items():
        got = js["cases"][cls]
        for quantity in (
            "irradiance",
            "equilibrium_temperature",
            "temperature_response",
            "temperature_response_gaussian",
            "net_carbon_at_equilibrium",
        ):
            check_series(fx, quantity, cls, kase[quantity], got[quantity])


def test_js_per_k_match(fx, js):
    for cls, kase in fx["cases"].items():
        for key, spec in kase["per_k"].items():
            got = js["cases"][cls]["per_k"][key]
            label = f"{cls} k={spec['k']:g}"
            assert got["k"] == spec["k"]
            check_series(fx, "net_carbon", label, spec["net_carbon"], got["net_carbon"])
            check(
                fx,
                "compensation_irradiance",
                label,
                spec["compensation_irradiance"],
                got["compensation_irradiance"],
            )
            if spec["crossover_au"] is None:
                assert got["crossover_au"] is None, (
                    f"{label}: Python has no crossover, JS returned "
                    f"{got['crossover_au']}"
                )
            else:
                check(fx, "crossover_au", label, spec["crossover_au"], got["crossover_au"])


def test_js_crossovers_match_the_committed_experiment(fx, js):
    """Positive control: the parity numbers are the ones in crossover.csv.

    Without this, model.js and fixtures.json could agree perfectly with each
    other while both disagreeing with the result the repository published.
    """
    import csv

    rows = [
        r
        for r in csv.DictReader(
            line
            for line in (ROOT / "experiments" / "q1_crossover" / "crossover.csv")
            .read_text()
            .splitlines()
            if not line.startswith("#")
        )
    ]
    assert rows, "crossover.csv had no data rows"
    for row in rows:
        cls, k = row["class"], float(row["k"])
        got = js["cases"][cls]["per_k"][repr(k)]["crossover_au"]
        published = float(row["r_star_au"])
        assert abs(got - published) <= 5e-5, (
            f"{cls} k={k:g}: JS r*={got} disagrees with the committed "
            f"crossover.csv value {published} (which is rounded to 4 dp)"
        )


def test_js_edge_case_no_crossover_is_null(fx, js):
    ref = next(e for e in fx["edge_cases"] if e["name"] == "no_crossover_in_window")
    got = js["edge_cases"]["no_crossover_in_window"]
    assert ref["expect"] == "null"
    assert got["crossover_au"] is None, (
        "Python raises 'no sign change' here; JS must report null rather than "
        f"extrapolate, got {got['crossover_au']}"
    )
    check(
        fx,
        "net_carbon",
        "edge no_crossover @ r_max",
        ref["net_carbon_at_r_max"],
        got["net_carbon_at_r_max"],
    )


def test_js_edge_case_compensation_boundary_raises(fx, js):
    ref = next(
        e
        for e in fx["edge_cases"]
        if e["name"] == "compensation_at_respiration_boundary"
    )
    got = js["edge_cases"]["compensation_at_respiration_boundary"]
    assert ref["expect"] == "error"
    assert got["value"] is None, f"JS returned a value at the boundary: {got['value']}"
    assert got["raised"], "JS did not raise at leaf respiration == a_max"
    assert "no compensation point" in got["raised"]


def test_js_edge_case_t_min_floor(fx, js):
    ref = next(e for e in fx["edge_cases"] if e["name"] == "algal_t_min_floor")
    got = js["edge_cases"]["algal_t_min_floor"]["samples"]
    assert [s["label"] for s in got] == [s["label"] for s in ref["samples"]]
    for r, g in zip(ref["samples"], got):
        label = f"t_min floor {r['label']}"
        check(fx, "equilibrium_temperature", label, r["t_eq"], g["t_eq"])
        check(
            fx,
            "temperature_response",
            label,
            r["temperature_response"],
            g["temperature_response"],
        )
        check(
            fx,
            "net_carbon_at_equilibrium",
            label,
            r["net_carbon_at_equilibrium"],
            g["net_carbon_at_equilibrium"],
        )
    at_floor = next(s for s in got if s["label"] == "at_floor")
    assert at_floor["temperature_response"] == 0.0, (
        "the response must be exactly 0 at t_min, not merely small"
    )
    outside = next(s for s in got if s["label"] == "outside")
    assert outside["temperature_response"] == 0.0, (
        "below t_min the response must be CLAMPED to 0. An unclamped linear "
        "ramp returns a negative number here, which would turn the gross term "
        "of net carbon negative. This is the assertion the floor case exists "
        "for; note it does NOT discriminate `t < t_min` from `t <= t_min` -- "
        "at t == t_min the ramp evaluates to 0 under either spelling."
    )


# ---------------------------------------------------------------- the vessel (M1b)
def _cmp(fx, tol, path, ref, got, errs):
    """Walk the expected structure; numbers within the case's tolerance, the rest exact."""
    if isinstance(ref, bool) or ref is None or isinstance(ref, str):
        if got != ref:
            errs.append(f"{path}: JS {got!r} != Python {ref!r}")
    elif isinstance(ref, (int, float)):
        if not isinstance(got, (int, float)) or isinstance(got, bool):
            errs.append(f"{path}: JS {got!r} is not a number (Python {ref!r})")
            return
        rtol, atol = tol_for(fx, tol)
        if abs(got - ref) > atol + rtol * abs(ref):
            errs.append(
                f"{path}: |{got!r} - {ref!r}| = {abs(got - ref):.6g} > "
                f"{atol + rtol * abs(ref):.6g} ({tol})"
            )
    elif isinstance(ref, list):
        if not isinstance(got, list) or len(got) != len(ref):
            errs.append(f"{path}: JS {got!r} vs Python list of {len(ref)}")
            return
        for i, (r, g) in enumerate(zip(ref, got)):
            _cmp(fx, tol, f"{path}[{i}]", r, g, errs)
    elif isinstance(ref, dict):
        if not isinstance(got, dict) or set(got) != set(ref):
            errs.append(
                f"{path}: keys JS {sorted(got) if isinstance(got, dict) else got!r}"
                f" != Python {sorted(ref)}"
            )
            return
        for k in ref:
            _cmp(fx, tol, f"{path}.{k}", ref[k], got[k], errs)
    else:
        raise TypeError(f"{path}: unhandled fixture type {type(ref)}")


def _vessel_errors(fx, js, pred=lambda c: True):
    got = {c["name"]: c["got"] for c in js["vessel"]["cases"]}
    errs = []
    n = 0
    for case in fx["vessel"]["cases"]:
        if not pred(case):
            continue
        n += 1
        assert case["name"] in got, f"JS did not replay vessel case {case['name']!r}"
        _cmp(fx, case["tol"], case["name"], case["expect"], got[case["name"]], errs)
    assert n > 0, "predicate selected no vessel case: a test that cannot fail"
    return errs


VESSEL_CALLS = (
    "shell_transmission",
    "slab_reflectance",
    "optics_at_t",
    "saturation_pressure",
    "self_consistent_pressure",
    "closed_form_control",
    "auto_state",
    "classify",
    "check_auto_path",
    "convergence_error",
    "same_object",
    "find_edge_linear",
    "r_close",
    "r_window",
    "prereg_example",
)


@pytest.mark.parametrize("call", VESSEL_CALLS)
def test_js_vessel_matches(fx, js, call):
    errs = _vessel_errors(fx, js, lambda c: c["call"] == call)
    assert not errs, f"{len(errs)} vessel mismatches:\n" + "\n".join(errs[:20])


def test_js_vessel_every_case_replayed(fx, js):
    assert {c["call"] for c in fx["vessel"]["cases"]} == set(VESSEL_CALLS)
    assert [c["name"] for c in js["vessel"]["cases"]] == [
        c["name"] for c in fx["vessel"]["cases"]
    ]


def test_js_vessel_grids_and_table(fx, js):
    assert js["vessel"]["grid_r_au"] == fx["vessel"]["grid_r_au"]
    errs = []
    _cmp(fx, "vessel_closed", "grid_r_m", fx["vessel"]["grid_r_m"], js["vessel"]["grid_r_m"], errs)
    assert not errs, errs
    import hashlib

    data = "".join(
        ln
        for ln in (ROOT / "sim" / "spectral_table.csv").read_text().splitlines(keepends=True)
        if not ln.startswith("#")
    )
    assert js["vessel"]["spectral_table_sha256"] == hashlib.sha256(data.encode()).hexdigest()


def test_spectral_table_js_is_generated_from_the_csv():
    import importlib.util

    spec = importlib.util.spec_from_file_location("msj", ROOT / "tools" / "make_spectral_js.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert (ROOT / "web" / "spectral_table.js").read_text() == mod.render(), (
        "web/spectral_table.js is stale: run `python3 tools/make_spectral_js.py`"
    )


def test_prereg_example_sets(fx, js):
    """M1b acceptance (spec §8): at the prereg's registered inputs, either side of each
    registered edge, classifyFailure returns the empty set inside the window and the
    registered binding outside it (P1 FREEZE at every sigma, P2 OPAQUE)."""
    import yaml

    prereg = yaml.safe_load(
        (ROOT / "experiments" / "q4_vessel" / "prereg.yaml").read_text()
    )
    want = {"P1": [prereg["predictions"]["P1"]["binding"]], "P2": [prereg["predictions"]["P2"]["binding"]]}
    got = {c["name"]: c["got"] for c in js["vessel"]["cases"]}
    seen = 0
    for case in fx["vessel"]["cases"]:
        if case["call"] != "prereg_example":
            continue
        seen += 1
        pred = case["name"].split(": ")[1][:2]
        expected = [] if "(inside)" in case["name"] else want[pred]
        assert got[case["name"]]["report"]["violated"] == expected, case["name"]
        assert case["expect"]["report"]["violated"] == expected, case["name"]
    assert seen == 8


def test_vessel_case_names_are_unique(fx):
    names = [c["name"] for c in fx["vessel"]["cases"]]
    assert len(names) == len(set(names)), "duplicate vessel case names shadow each other"
