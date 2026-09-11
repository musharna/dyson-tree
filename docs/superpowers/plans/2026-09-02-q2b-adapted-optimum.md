# Q2b Adapted-Optimum Implementation Plan

> **Path redaction (2026-09-10, release 1.0).** The local paths in this plan were
> written for one machine. Before the repository was made public the operator's
> home directory and Windows account name were replaced with `~` and
> `<windows-user>`. Only those identifiers changed; every command, claim and
> number in this file is untouched.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine the outer limit for a passive organism whose photosynthetic optimum is predicted from its own equilibrium temperature at a home distance, rather than fitted.

**Architecture:** Two new pure functions in `sim/thermal.py` (a Gaussian temperature response, and the adaptation premise as a named one-liner), one new defaulted field and one new method on `Organism`, and an `experiments/q2b_adapted/` runner that mirrors Q2's conventions with one change: Gate B is evaluated PER CLASS, so a failing class is excluded from the sweep instead of aborting the run.

**Tech Stack:** Python 3, numpy, scipy, PyYAML, pytest; figures in R + ggplot2 sourcing `docs/analysis/theme.R`.

**Spec:** `docs/superpowers/specs/2026-09-02-q2b-adapted-optimum-design.md`

## Global Constraints

- `experiments/q1_crossover/prereg.yaml` and `experiments/q2_thermal/prereg.yaml` are FROZEN. Never edit either. Never edit their CSVs by hand.
- Q1's and Q2's committed CSV BODIES must stay byte-identical. Their regeneration tests are the guard.
- `sim/organism.py::net_carbon` and `::net_carbon_at_equilibrium`, and `sim/thermal.py::temperature_response`, must NOT change behaviour. Q2b adds functions beside them.
- Every new `Organism` field MUST have a default so `VASCULAR` and `ALGAL` construct unchanged.
- **Do NOT adjust `emissivity`, `albedo`, `t_opt`, or any gate window to make a gate pass.** Gate B is expected to FAIL for the vascular class by 28 K; that is a disclosed finding, not a defect. Fitting a declared assumption to a gate is the circularity this project has caught three times.
- Fail loud: out-of-range inputs raise `ValueError` naming the value. No silent fallbacks.
- Never trust a test you have not seen fail: run each new assertion against the broken state and record the observed failure verbatim.
- A negative assertion carries a positive control in the same test.
- Commit messages: conventional-commit style, **no attribution lines, no `Claude-Session:` trailer**.
- Editing `sim/organism.py` moves `organism_md5`, which REDS both Q1's and Q2's regeneration tests. Follow the procedure in `experiments/q2_thermal/RESULTS.md` §10: code commit first, then re-run each experiment, then a header-only commit. Q2's runner still exits 2; that is correct.
- `ruff check .` must gain no new errors (10 pre-existing `E741` in `tests/test_runner.py` are known and out of scope).

---

### Task 1: the Gaussian response and the adaptation premise

**Files:**
- Modify: `sim/thermal.py`
- Test: `tests/test_thermal.py`

**Interfaces:**
- Consumes: `sim.thermal.equilibrium_temperature(r_au, area_ratio, emissivity=1.0, albedo=0.0) -> float`
- Produces: `temperature_response_gaussian(t: float, t_opt: float, omega: float) -> float`; `adapted_optimum(r_home_au: float, area_ratio: float, emissivity: float = 1.0, albedo: float = 0.0) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_thermal.py
import math

from sim.thermal import adapted_optimum, temperature_response_gaussian


def test_gaussian_is_one_at_the_optimum():
    assert temperature_response_gaussian(298.15, t_opt=298.15, omega=20.0) == 1.0


def test_gaussian_falls_to_one_over_e_at_omega_from_the_optimum():
    """Omega is DEFINED as the offset at which the rate falls to e^-1 of its
    peak (June et al. 2004, as quoted in Scafaro et al. 2023). That definition
    is the test."""
    v = temperature_response_gaussian(298.15 + 20.0, t_opt=298.15, omega=20.0)
    assert v == pytest.approx(math.exp(-1.0), rel=1e-12)


def test_gaussian_is_symmetric_about_the_optimum():
    hot = temperature_response_gaussian(298.15 + 12.0, t_opt=298.15, omega=20.0)
    cold = temperature_response_gaussian(298.15 - 12.0, t_opt=298.15, omega=20.0)
    assert hot == pytest.approx(cold, rel=1e-12)
    # and both are strictly below the peak
    assert hot < 1.0


def test_gaussian_narrower_omega_falls_off_faster():
    narrow = temperature_response_gaussian(283.15, t_opt=298.15, omega=10.0)
    wide = temperature_response_gaussian(283.15, t_opt=298.15, omega=30.0)
    assert narrow < wide


def test_gaussian_stays_in_the_unit_interval_far_from_the_optimum():
    for t in (1.0, 100.0, 200.0, 400.0, 600.0):
        v = temperature_response_gaussian(t, t_opt=298.15, omega=20.0)
        assert 0.0 <= v <= 1.0


@pytest.mark.parametrize(
    "kwargs, needle",
    [
        (dict(t=298.15, t_opt=298.15, omega=0.0), "omega"),
        (dict(t=298.15, t_opt=298.15, omega=-5.0), "omega"),
        (dict(t=0.0, t_opt=298.15, omega=20.0), "t"),
        (dict(t=-10.0, t_opt=298.15, omega=20.0), "t"),
    ],
)
def test_gaussian_rejects_out_of_range_inputs(kwargs, needle):
    with pytest.raises(ValueError, match=needle):
        temperature_response_gaussian(**kwargs)
    # positive control in the same test
    assert temperature_response_gaussian(298.15, t_opt=298.15, omega=20.0) == 1.0


def test_adapted_optimum_is_the_equilibrium_temperature_at_the_home_distance():
    """The adaptation premise: the optimum IS the tissue temperature at home.
    Named rather than inlined so the premise is greppable and testable."""
    from sim.thermal import equilibrium_temperature

    for ratio in (2.0, 4.0):
        assert adapted_optimum(1.0, area_ratio=ratio) == pytest.approx(
            equilibrium_temperature(1.0, area_ratio=ratio), rel=1e-12
        )


def test_adapted_optimum_reproduces_the_two_class_predictions():
    """The numbers Gate B is built on. Sphere ~5.16 C, lamina ~57.82 C."""
    assert adapted_optimum(1.0, area_ratio=4.0) - 273.15 == pytest.approx(5.16, abs=0.01)
    assert adapted_optimum(1.0, area_ratio=2.0) - 273.15 == pytest.approx(57.82, abs=0.01)


def test_adapted_optimum_rejects_a_nonpositive_home_distance():
    with pytest.raises(ValueError, match="r_au"):
        adapted_optimum(0.0, area_ratio=4.0)
    assert adapted_optimum(1.0, area_ratio=4.0) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: FAIL — `ImportError: cannot import name 'adapted_optimum'`

- [ ] **Step 3: Write the implementation**

```python
# append to sim/thermal.py
import math


def temperature_response_gaussian(t: float, t_opt: float, omega: float) -> float:
    """Normalized rate multiplier in [0, 1], Gaussian about t_opt.

    The form of June, Evans & Farquhar (2004), as quoted verbatim in Scafaro et
    al. (2023): J = J(To) * exp(-((T - To)/Omega)^2), where "Omega represents the
    temperature difference from To at which J declines to e^-1 (0.37) of J(To)".

    Unlike temperature_response (linear, Q2), this is concave and symmetric: a
    tissue whose optimum is 25 C can still sit well above zero at 5 C, which a
    straight line from t_min to t_opt structurally cannot do. Q2's linear form is
    left in place untouched -- Q2's committed record must keep regenerating.

    There is no t_min here: the Gaussian approaches zero asymptotically rather
    than switching off at a floor. Any hard floor belongs to the caller.
    """
    if omega <= 0:
        raise ValueError(f"omega must be > 0, got {omega}")
    if t <= 0:
        raise ValueError(f"t must be > 0 K, got {t}")
    if t_opt <= 0:
        raise ValueError(f"t_opt must be > 0 K, got {t_opt}")
    return float(math.exp(-(((t - t_opt) / omega) ** 2)))


def adapted_optimum(
    r_home_au: float,
    area_ratio: float,
    emissivity: float = 1.0,
    albedo: float = 0.0,
) -> float:
    """The adaptation premise: an organism's photosynthetic optimum equals its own
    equilibrium temperature at its home distance.

    Scafaro et al. (2023) report the optimum tracking growth temperature (29.4 C
    cool-grown vs 32.7 C warm-grown, 49 C3 species). Taken as a mechanism rather
    than a correlation, t_opt stops being a free parameter and becomes something
    this model PREDICTS from geometry -- which is what makes Gate B able to fail.

    Deliberately a one-liner with a name: the premise is the whole content, and a
    named function is greppable, testable, and mockable in a way an inlined call
    is not.
    """
    return equilibrium_temperature(r_home_au, area_ratio, emissivity, albedo)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: PASS

- [ ] **Step 5: Confirm nothing else moved**

Run: `python3 -m pytest -q` (expect all previously-passing tests still pass) and
`python3 -m ruff check .` (expect only the 10 known `E741` in `tests/test_runner.py`).

- [ ] **Step 6: Commit**

```bash
git add sim/thermal.py tests/test_thermal.py
git commit -m "feat(thermal): Gaussian temperature response and the adaptation premise"
```

---

### Task 2: `net_carbon_adapted` on `Organism`

**Files:**
- Modify: `sim/organism.py`
- Test: `tests/test_organism.py`

**Interfaces:**
- Consumes: `temperature_response_gaussian(t, t_opt, omega)`, `adapted_optimum(r_home_au, area_ratio, emissivity, albedo)`, `equilibrium_temperature(...)`
- Produces: `Organism.omega: float = 20.0`; `Organism.net_carbon_adapted(r_au: float, r_home_au: float, k: float | None = None) -> float`

- [ ] **Step 1: Write the failing tests**

**Import placement matters here.** `tests/test_organism.py` already has a consolidated
top-of-file import block carrying `gross_assimilation`, `irradiance`, `respiration`,
`equilibrium_temperature` and `temperature_response`. Add `adapted_optimum` and
`temperature_response_gaussian` to that EXISTING block at the top of the file. Do NOT
append a fresh `from sim.thermal import ...` mid-file: that produced `E402` plus two
`F811` on this exact file in an earlier round and had to be fixed as a lint regression.

```python
# append to tests/test_organism.py (imports go in the EXISTING top block, not here)


def _algal_adapted():
    return Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65, omega=20.0,
    )


def test_omega_defaults_and_validates():
    o = Organism("x", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)
    assert o.omega == 20.0
    with pytest.raises(ValueError, match="omega"):
        Organism("x", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0, omega=0.0)
    assert Organism("x", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0).omega > 0


def test_net_carbon_adapted_is_at_the_optimum_when_r_equals_r_home():
    """At the home distance the tissue sits exactly at its adapted optimum, so the
    Gaussian returns exactly 1 and assimilation is unscaled."""
    o = _algal_adapted()
    t_home = adapted_optimum(1.0, o.area_ratio, o.emissivity, o.albedo)
    expected = (
        gross_assimilation(irradiance(1.0), o.a_max, o.k) * 1.0
        - respiration(o.r_d, t_home) / o.leaf_mass_ratio
    )
    assert o.net_carbon_adapted(1.0, r_home_au=1.0) == pytest.approx(expected, rel=1e-9)


def test_net_carbon_adapted_pins_every_term_independently():
    """Expected value built from primitives, NOT by calling the method under test.
    This is what discriminates a wrong response argument, a wrong temperature for
    respiration, or a dropped leaf_mass_ratio divisor."""
    o = _algal_adapted()
    r, r_home = 2.0, 1.0
    t = equilibrium_temperature(r, o.area_ratio, o.emissivity, o.albedo)
    t_opt = adapted_optimum(r_home, o.area_ratio, o.emissivity, o.albedo)
    f = temperature_response_gaussian(t, t_opt, o.omega)
    expected = (
        gross_assimilation(irradiance(r), o.a_max, o.k) * f
        - respiration(o.r_d, t) / o.leaf_mass_ratio
    )
    assert o.net_carbon_adapted(r, r_home_au=r_home) == pytest.approx(expected, rel=1e-9)
    # positive control: the value is finite and the terms are not degenerate
    assert 0.0 < f < 1.0


def test_net_carbon_adapted_uses_leaf_mass_ratio():
    whole = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65, omega=20.0,
    ).net_carbon_adapted(1.0, r_home_au=1.0)
    half = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=0.5,
        area_ratio=4.0, t_min=254.65, omega=20.0,
    ).net_carbon_adapted(1.0, r_home_au=1.0)
    assert half < whole


def test_net_carbon_adapted_does_not_disturb_the_q1_or_q2_paths():
    assert VASCULAR.net_carbon(1.0) == pytest.approx(8.3550, abs=1e-4)
    assert ALGAL.net_carbon(1.0) == pytest.approx(9.6290, abs=1e-4)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_organism.py -q`
Expected: FAIL — `TypeError: Organism.__init__() got an unexpected keyword argument 'omega'`

- [ ] **Step 3: Implement**

Extend the import block in `sim/organism.py` to add the two new thermal functions:

```python
from sim.thermal import (
    adapted_optimum,
    equilibrium_temperature,
    temperature_response,
    temperature_response_gaussian,
)
```

Add the field after `albedo`, defaulted:

```python
    omega: float = 20.0  # K, Gaussian width; DECLARED ASSUMPTION, not grounded
```

Append to `__post_init__`:

```python
        if self.omega <= 0:
            raise ValueError(f"omega must be > 0, got {self.omega}")
```

Add this method after `net_carbon_at_equilibrium`. **Do not modify `net_carbon` or `net_carbon_at_equilibrium`.**

```python
    def net_carbon_adapted(
        self, r_au: float, r_home_au: float, k: float | None = None
    ) -> float:
        """Net carbon for a passive organism whose photosynthetic optimum was set
        by its equilibrium temperature at r_home_au, then swept to r_au.

        Adaptation is to the HABITAT temperature, not the instantaneous one: if
        t_opt tracked tissue temperature at every distance the response would be 1
        everywhere and temperature could never limit anything. So t_opt is fixed
        once, at home, and the tissue then cools away from an optimum that does
        not follow.

        net_carbon() (Q1) and net_carbon_at_equilibrium() (Q2) are deliberately
        untouched: both have committed records that must keep regenerating."""
        kk = self.k if k is None else k
        t = equilibrium_temperature(r_au, self.area_ratio, self.emissivity, self.albedo)
        t_opt = adapted_optimum(
            r_home_au, self.area_ratio, self.emissivity, self.albedo
        )
        f = temperature_response_gaussian(t, t_opt, self.omega)
        gross = gross_assimilation(irradiance(r_au), self.a_max, kk) * f
        return gross - respiration(self.r_d, t) / self.leaf_mass_ratio
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_organism.py -q`
Expected: PASS

- [ ] **Step 5: Re-run BOTH prior experiments and re-stamp their headers**

Editing `sim/organism.py` moves `organism_md5`, so Q1's and Q2's regeneration tests are now RED. This is expected. Follow `experiments/q2_thermal/RESULTS.md` §10 exactly:

```bash
git add sim/organism.py tests/test_organism.py
git commit -m "feat(organism): omega field and net_carbon_adapted; Q1 and Q2 paths untouched"
python3 experiments/q1_crossover/run.py   # must exit 0
python3 experiments/q2_thermal/run.py     # must exit 2 -- Q2's gate still fails
```

Then verify NO body value moved, and paste this output into your report:

```bash
for f in calibration.csv sweep.csv crossover.csv; do
  diff <(git show master:experiments/q1_crossover/$f | grep -v '^#') \
       <(grep -v '^#' experiments/q1_crossover/$f) >/dev/null \
    && echo "Q1 $f BODY IDENTICAL" || echo "Q1 $f *** CHANGED ***"
done
diff <(git show HEAD:experiments/q2_thermal/gates.csv | grep -v '^#') \
     <(grep -v '^#' experiments/q2_thermal/gates.csv) >/dev/null \
  && echo "Q2 gates.csv BODY IDENTICAL" || echo "Q2 gates.csv *** CHANGED ***"
git diff --stat experiments/ | tail -5
```

**If any body line moved, STOP and report BLOCKED.** Otherwise commit the header-only change:

```bash
git add experiments/q1_crossover experiments/q2_thermal
git commit -m "chore(exp): regenerate provenance headers after adding net_carbon_adapted"
```

- [ ] **Step 6: Full suite and lint**

Run: `python3 -m pytest -q` and `python3 -m ruff check .`
Expected: all green; ruff shows only the 10 known `E741`.

---

### Task 3: pre-registration, Gate B, and reachability computed first

**Files:**
- Create: `experiments/q2b_adapted/__init__.py`, `experiments/q2b_adapted/prereg.yaml`, `experiments/q2b_adapted/reachability.py`
- Test: `tests/test_q2b_reachability.py`

**Interfaces:**
- Consumes: `adapted_optimum`, `equilibrium_temperature`, `Organism`, `sim.physiology.crossover_distance`
- Produces: `experiments/q2b_adapted/reachability.py::gate_b_verdict(predicted_k: float, measured_c: list[float], half_width_k: float = 5.0) -> tuple[bool, float, float]` returning `(passed, lo_c, hi_c)`; `::sign_structure(net_fn, r_min, r_max, n_grid) -> list[tuple[int, int]]`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_q2b_reachability.py
import pytest

from experiments.q2b_adapted.reachability import gate_b_verdict, sign_structure
from sim.thermal import adapted_optimum


def test_gate_b_window_spans_min_minus_to_max_plus_half_width():
    """The algal source reports TWO site values (5 and 7 C), so the window is
    [min-5, max+5], not +/-5 around a single number."""
    passed, lo, hi = gate_b_verdict(adapted_optimum(1.0, 4.0), [5.0, 7.0], 5.0)
    assert (lo, hi) == pytest.approx((0.0, 12.0))
    assert passed is True


def test_gate_b_fails_for_the_vascular_lamina():
    passed, lo, hi = gate_b_verdict(adapted_optimum(1.0, 2.0), [29.4], 5.0)
    assert (lo, hi) == pytest.approx((24.4, 34.4))
    assert passed is False
    # positive control in the same test: the algal case passes the same function
    assert gate_b_verdict(adapted_optimum(1.0, 4.0), [5.0, 7.0], 5.0)[0] is True


def test_gate_b_rejects_an_empty_measured_list():
    with pytest.raises(ValueError, match="measured"):
        gate_b_verdict(278.31, [], 5.0)
    assert gate_b_verdict(278.31, [5.0], 5.0)[1] == pytest.approx(0.0)


def test_sign_structure_reports_transitions_in_order():
    # monotone decreasing: exactly one positive->negative transition
    assert sign_structure(lambda r: 10.0 - r, 0.5, 100.0, 400) == [(1, -1)]
    # negative -> positive -> negative
    got = sign_structure(lambda r: -((r - 2.0) ** 2) + 1.0, 0.5, 100.0, 400)
    assert got == [(-1, 1), (1, -1)]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_q2b_reachability.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'experiments.q2b_adapted'`

- [ ] **Step 3: Create the package and implement**

```bash
touch experiments/q2b_adapted/__init__.py
```

(`experiments/__init__.py` already exists from Q2. The package path matters: Q2b's runner must be importable as `experiments.q2b_adapted.run`, because `tests/test_runner.py` puts Q1's directory on `sys.path` and does a bare `import run`. Do NOT add a `sys.path.insert` to any Q2b file.)

```python
# experiments/q2b_adapted/reachability.py
"""What the gates admit, and what shape the curve has -- both computed BEFORE
the prediction is registered.

Q1 registered a band of which 89.5% was unreachable. Q2 registered a prediction
no parameters could satisfy. Both were discovered after the run. This module
exists so Q2b's prereg can record the answer in advance."""

from __future__ import annotations

import numpy as np


def gate_b_verdict(
    predicted_k: float, measured_c: list[float], half_width_k: float = 5.0
) -> tuple[bool, float, float]:
    """Gate B: does the model's PREDICTED optimum match the measured one?

    The window is [min(measured) - half_width, max(measured) + half_width] in C,
    because the algal source reports two site values rather than one. half_width
    is a DECLARED ASSUMPTION -- no source gives an adaptation tolerance.

    Returns (passed, lo_c, hi_c)."""
    if not measured_c:
        raise ValueError("measured_c must be a non-empty list of degrees C")
    if half_width_k < 0:
        raise ValueError(f"half_width_k must be >= 0, got {half_width_k}")
    lo = min(measured_c) - half_width_k
    hi = max(measured_c) + half_width_k
    predicted_c = predicted_k - 273.15
    return (lo <= predicted_c <= hi, lo, hi)


def sign_structure(net_fn, r_min: float, r_max: float, n_grid: int) -> list:
    """The ordered sign transitions of net_fn on a log grid.

    Q2's outer-root selector assumes exactly [(-1, 1), (1, -1)] and fails loud on
    anything else. Q2b's curve is Gaussian rather than a linear ramp, so its shape
    is NOT assumed to match -- it is measured here, before the prereg is written."""
    if r_min <= 0 or r_max <= r_min:
        raise ValueError(f"need 0 < r_min < r_max, got {r_min}, {r_max}")
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    return [(int(sign[i]), int(sign[i + 1])) for i in idx]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_q2b_reachability.py -q`
Expected: PASS

- [ ] **Step 5: Measure the curve's shape and the reachable interval BEFORE writing the prereg**

Run this and paste the full output into your report verbatim — the prereg is written FROM it:

```bash
python3 - <<'PY'
from sim.organism import Organism
from sim.thermal import adapted_optimum
from experiments.q2b_adapted.reachability import gate_b_verdict, sign_structure
from sim.physiology import crossover_distance

R_MIN, R_MAX, N = 0.5, 100.0, 200
for cls, ar, tmin, measured in (
    ("algal", 4.0, 254.65, [5.0, 7.0]),
    ("vascular", 2.0, 265.15, [29.4]),
):
    pred = adapted_optimum(1.0, ar)
    ok, lo, hi = gate_b_verdict(pred, measured)
    print(f"{cls}: predicted t_opt = {pred:.4f} K = {pred-273.15:.2f} C, "
          f"window [{lo}, {hi}] C -> GATE B {'PASS' if ok else 'FAIL'}")
    for om in (10.0, 15.0, 20.0, 25.0, 30.0):
        o = Organism(cls, a_max=10.0, k=20.0 if cls=="algal" else 100.0,
                     r_d=0.24 if cls=="algal" else 0.65,
                     leaf_mass_ratio=1.0 if cls=="algal" else 0.5,
                     area_ratio=ar, t_min=tmin, omega=om)
        shape = sign_structure(lambda r: o.net_carbon_adapted(r, 1.0), R_MIN, R_MAX, N)
        try:
            first = crossover_distance(lambda r: o.net_carbon_adapted(r, 1.0),
                                       r_min=R_MIN, r_max=R_MAX, n_grid=N)
            first_s = f"{first:.4f} AU"
        except ValueError as e:
            first_s = f"none ({str(e)[:40]}...)"
        print(f"    omega={om:5.1f}: transitions={shape}  first root={first_s}")
PY
```

**Record the transition structure per Ω.** If it is not `[(-1, 1), (1, -1)]` for every Ω, say so explicitly — Q2's outer-root selector assumes that shape and fails loud otherwise, and Task 4 must handle whatever shape actually occurs rather than assume Q2's.

- [ ] **Step 6: Write the pre-registration**

Create `experiments/q2b_adapted/prereg.yaml`, filling `reachable` and `curve_shape` from Step 5's measured output:

```yaml
# Q2b pre-registration. Written BEFORE run.py produces limits.csv. Do not edit after.
registered: 2026-09-02
question: >
  For a passive organism at radiative equilibrium, adapted at a home distance of
  1 AU so its photosynthetic optimum equals its tissue temperature there, at what
  heliocentric distance does whole-organism net carbon cross zero, and does the
  outer limit come from light, carbon, or temperature?
spec: docs/superpowers/specs/2026-09-02-q2b-adapted-optimum-design.md
grounding: docs/bio_grounding_2026-09-02.md

assumptions:
  tsi_w_m2: 1360.8              # Kopp & Lean 2011, 10.1029/2010GL045777
  par_fraction: 0.45            # assumption
  photons_per_j: 4.57           # assumption
  t_ref_k: 293.0
  q10: 2.0                      # assumption
  sigma_w_m2_k4: 5.670374419e-8 # CODATA, exact by SI definition
  emissivity: 1.0               # DECLARED ASSUMPTION, not grounded
  albedo: 0.0                   # DECLARED ASSUMPTION, not grounded
  r_home_au: 1.0                # the distance the organism is adapted at
  gate_b_half_width_k: 5.0      # DECLARED ASSUMPTION -- no source gives a tolerance

# Gate A: thermal physics, retained from Q2 unchanged.
gate_thermal:
  r_au: 1.0
  area_ratio: 4.0
  t_eq_k: [275.0, 282.0]

# Gate B: the adaptation premise. PARAMETER-FREE -- the model predicts t_opt from
# geometry, and the prediction is compared against measurement.
# Outcomes are COMPUTED AND DISCLOSED here, before the run: algal PASSES,
# vascular FAILS by 28 K. A gate's admissible set must be known in advance; a
# PREDICTION's answer must not, and the prediction below is not.
gate_adaptation:
  algal:
    measured_c: [5.0, 7.0]      # Colesie et al. 2014, Antarctic soil crusts
    predicted_c: 5.16
    expect: pass
  vascular:
    measured_c: [29.4]          # Scafaro et al. 2023, cool-grown C3, 49 species
    predicted_c: 57.82
    expect: fail

# Koerner's rate anchors are RETIRED as a gate here. Under the June Gaussian and
# the grounded 29.4 C optimum, no omega satisfies both (scanned 1-200 C). Recorded
# as a documented conflict, not used as a check. See the spec.

presets:
  algal:
    a_max: 10.0
    k: 20.0
    r_d: 0.24
    leaf_mass_ratio: 1.0        # unicellular: no non-photosynthetic organ
    area_ratio: 4.0             # sphere
    t_min: 254.65               # Pointing et al. 2015 via bio_grounding §1
  vascular:
    a_max: 10.0
    k: 100.0
    r_d: 0.65
    leaf_mass_ratio: 0.5
    area_ratio: 2.0             # flat lamina
    t_min: 265.15

# DECLARED ASSUMPTION, not cited. June et al. 2004 is closed access and two
# open-access sweeps found no numeric omega. Swept because the answer is most
# sensitive to the least grounded parameter.
omega_grid_k: [10.0, 15.0, 20.0, 25.0, 30.0]

sweep:
  r_min_au: 0.5
  r_max_au: 100.0
  n_grid: 200

# Measured in Step 5 BEFORE this file was written.
curve_shape:
  transitions_per_omega: [FILL FROM STEP 5 -- e.g. "[(-1,1),(1,-1)] for all omega"]

reachable:
  note: >
    [FILL FROM STEP 5: the first-root distances per omega per class, and whether a
    root exists at all. A prediction outside this set is not a prediction.]

# NO numeric band is registered, deliberately. Q1 registered a band and 89.5% of it
# was unreachable; Q2 registered a prediction no parameters could satisfy. The fix is
# NOT a band drawn from the Step 5 reachability scan -- a band derived from the scan
# contains the answer by construction and cannot fail. No independent basis for a
# numeric band exists here, so none is invented.
predicted_binding_limit:
  algal: carbon        # the QUALITATIVE prediction, registered; genuinely unknown
predicted_outer_limit_au:
  algal: null          # not registered -- see the note above; the distance is REPORTED
```

**On the `[FILL FROM STEP 5]` markers above:** these are not placeholders in the
plan's sense. They are values that MUST be measured at execution time, by the exact
command in Step 5, and written into the prereg from that output — computing them here
would be computing part of the answer before registering. What is forbidden is an
unspecified TBD; what Step 5 gives is a procedure with a literal command.

- [ ] **Step 7: Commit**

```bash
git add experiments/q2b_adapted tests/test_q2b_reachability.py
git commit -m "exp(q2b): pre-registration with Gate B and curve shape measured first"
```

---

### Task 4: the runner, with Gate B evaluated per class

**Files:**
- Create: `experiments/q2b_adapted/run.py`
- Test: `tests/test_q2b_runner.py`

**Interfaces:**
- Consumes: everything from Tasks 1–3
- Produces: `main(argv: list[str] | None = None) -> int`; CSVs `gates.csv` (`gate,cls,detail,observed,lo,hi,passed`), `sweep.csv` (`class,omega,r_au,t_eq,response,net_carbon`), `limits.csv` (`class,omega,outer_au,binding`)

**The one change from Q2's conventions.** Q2's gate logic is all-or-nothing. Here:
- Gate A (thermal) is GLOBAL. If it fails, nothing is reported and the run exits 2.
- Gate B is PER CLASS. A class that fails is excluded from the sweep entirely — no row in `sweep.csv` or `limits.csv` — and its failure is recorded in `gates.csv`.
- Exit 0 if Gate A passed and **at least one** class passed Gate B; exit 2 if Gate A failed or **no** class passed.
- The expected run therefore reports the algal class only, and `limits.csv` will have no vascular row. **That absence is a result** and Task 5 must state it.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_q2b_runner.py
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

PROVENANCE_KEYS = (
    "# git_sha=", "# thermal_md5=", "# organism_md5=", "# physiology_md5=",
    "# prereg_md5=", "# python=", "# numpy=", "# scipy=", "# written=",
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
    assert not (out / "limits.csv").exists(), "stale limits.csv survived a Gate A failure"


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
        capture_output=True, text=True,
    )
    assert proc.returncode == 2, proc.stderr
    assert (out / "gates.csv").exists()
    assert not (out / "limits.csv").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_q2b_runner.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'experiments.q2b_adapted.run'`

- [ ] **Step 3: Write the runner**

Mirror `experiments/q2_thermal/run.py` — read it first. Reuse verbatim: `load_prereg`, `_md5`, `git_sha`, `write_csv`, and the provenance-header shape. Change only what this task's contract requires. The root selector: Q2's `outer_equilibrium_carbon_crossover` in `experiments/q2_thermal/run.py` is the pattern, including its `UnexpectedSignStructure` guard that must propagate rather than become NaN. **Use the transition structure you MEASURED in Task 3 Step 5** — do not assume Q2's `[(-1,1),(1,-1)]` holds for a Gaussian response; if the measured shape differs, the selector's expected-shape check must encode the measured one and the difference must be reported.

Key structure:

```python
def run_gate_a(prereg: dict) -> tuple[dict, bool]:
    g = prereg["gate_thermal"]
    obs = equilibrium_temperature(float(g["r_au"]), float(g["area_ratio"]))
    lo, hi = (float(x) for x in g["t_eq_k"])
    passed = lo <= obs <= hi
    return {"gate": "thermal", "cls": "-", "detail": f"T_eq at {g['r_au']} AU",
            "observed": f"{obs:.4f}", "lo": lo, "hi": hi, "passed": passed}, passed


def run_gate_b(prereg: dict) -> tuple[list[dict], set]:
    """Per class. Returns (rows, set of class names that PASSED)."""
    rows, passing = [], set()
    hw = float(prereg["assumptions"]["gate_b_half_width_k"])
    for cls, g in prereg["gate_adaptation"].items():
        p = prereg["presets"][cls]
        pred = adapted_optimum(
            float(prereg["assumptions"]["r_home_au"]), float(p["area_ratio"]),
            float(prereg["assumptions"]["emissivity"]),
            float(prereg["assumptions"]["albedo"]),
        )
        ok, lo, hi = gate_b_verdict(pred, [float(x) for x in g["measured_c"]], hw)
        if ok:
            passing.add(cls)
        rows.append({"gate": "adaptation", "cls": cls,
                     "detail": "predicted t_opt (C)", "observed": f"{pred-273.15:.4f}",
                     "lo": lo, "hi": hi, "passed": ok})
    return rows, passing
```

`main()` writes `gates.csv` from Gate A's row plus Gate B's rows, then:

```python
    if not a_passed or not passing:
        for stale in ("sweep.csv", "limits.csv"):
            (args.out / stale).unlink(missing_ok=True)
        print("GATE FAILED: no limits reported.")
        print("Do NOT adjust emissivity, albedo or a gate window to pass.")
        return 2
```

then sweeps only `cls in passing`, over `prereg["omega_grid_k"]`, using
`org.net_carbon_adapted(r, r_home_au)`, and writes `sweep.csv` and `limits.csv`.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_q2b_runner.py -q`
Expected: PASS

- [ ] **Step 5: See the per-class exclusion fail on broken code**

Temporarily change `run_gate_b` to return every class as passing (`passing.add(cls)` unconditionally), confirm `test_real_prereg_run_excludes_the_failing_class_but_still_reports` FAILS with its own message, record it verbatim, restore, confirm green.

- [ ] **Step 6: Full suite, lint, commit**

```bash
python3 -m pytest -q
python3 -m ruff check .
git add experiments/q2b_adapted/run.py tests/test_q2b_runner.py
git commit -m "exp(q2b): runner with per-class adaptation gate"
```

---

### Task 5: run it, plot it, write it up

**Files:**
- Create: `experiments/q2b_adapted/plot.R`, `experiments/q2b_adapted/RESULTS.md`
- Modify: `docs/ROADMAP.md`
- Test: `tests/test_q2b_runner.py` (regeneration test)

- [ ] **Step 1: Run the experiment into the repo directory**

```bash
python3 experiments/q2b_adapted/run.py
echo "exit=$?"
```

Record the exit code and full stdout. Expected: exit 0, algal reported, vascular excluded.

- [ ] **Step 2: Write the plot script**

```r
#!/usr/bin/env Rscript
# Two figures from the Q2b CSVs. One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#")
limits <- read.csv(file.path(in_dir, "limits.csv"), comment.char = "#")
stopifnot(nrow(sweep) > 0, nrow(limits) > 0)
sweep$omega <- factor(sweep$omega)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)

p1 <- ggplot(sweep, aes(r_au, net_carbon, colour = class, linetype = omega)) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_line() +
  scale_x_log10() +
  coord_cartesian(ylim = c(-2, 10)) +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)",
       y = expression(net~carbon~(mu*mol~m^-2~s^-1)),
       linetype = expression(Omega~(K)),
       title = "Q2b: net carbon vs distance, optimum adapted at 1 AU") +
  theme_dyson()
ggsave(file.path(fig_dir, "net_carbon_adapted.png"), p1, width = 8, height = 4.5, dpi = 150)

p2 <- ggplot(limits, aes(omega, outer_au, colour = class)) +
  geom_point(size = 3) + geom_line() +
  scale_colour_dyson() +
  labs(x = expression(Omega~(K)), y = "outer limit (AU)",
       title = "Q2b: sensitivity of the outer limit to the ungrounded Omega") +
  theme_dyson()
ggsave(file.path(fig_dir, "outer_limit_vs_omega.png"), p2, width = 8, height = 4.5, dpi = 150)
cat("wrote", fig_dir, "\n")
```

Run `Rscript experiments/q2b_adapted/plot.R`, confirm both PNGs exist, then **look at them**:

```bash
cp experiments/q2b_adapted/figures/*.png /mnt/c/Users/<windows-user>/Downloads/
cd /mnt/c/Users/<windows-user>/Downloads && cmd.exe /c start "" outer_limit_vs_omega.png
```

Read the PNGs yourself too. A warning-free render is not evidence a layer drew — Q1's prediction band silently vanished under a log axis.

- [ ] **Step 3: Add the regeneration test**

```python
# append to tests/test_q2b_runner.py
def test_committed_q2b_csvs_regenerate_exactly(tmp_path):
    src = REPO / "experiments" / "q2b_adapted"
    if not (src / "gates.csv").exists():
        pytest.skip("Q2b has not been run into the repo directory yet")
    out = tmp_path / "regen"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 0
    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        committed = [x for x in (src / name).read_text().splitlines()
                     if not x.startswith("# git_sha=") and not x.startswith("# written=")]
        fresh = [x for x in (out / name).read_text().splitlines()
                 if not x.startswith("# git_sha=") and not x.startswith("# written=")]
        assert committed == fresh, f"{name} does not regenerate"
```

Tamper with one committed value, confirm it fails, restore, record both.

- [ ] **Step 4: Write `experiments/q2b_adapted/RESULTS.md`**

State, in order: the registered question; Gate A's value and verdict; **Gate B per class, including that vascular failed by 28 K and was therefore excluded — and that its absence from `limits.csv` is a result, not an omission**; the algal outer limit per Ω with its binding constraint; the Ω sensitivity (how much the answer moves across the grid, since Ω is the least grounded parameter); the registered prediction versus the outcome; the reachable interval recorded before the run versus what happened; that Körner's anchors were retired here and why; and the `gates.csv` provenance header verbatim.

Say plainly what the vascular failure most likely means: ε=1, albedo=0 and no transpirational cooling, not a refutation of the adaptation premise. Do NOT adjust those to make it pass.

- [ ] **Step 5: Update `docs/ROADMAP.md` and commit**

Reconcile prose and checklist in the SAME commit. Q2b is complete only if a limit was reported; say exactly what was and was not answered.

```bash
python3 -m pytest -q
git add experiments/q2b_adapted docs/ROADMAP.md
git commit -m "exp(q2b): run the adapted-optimum question; record results"
```
