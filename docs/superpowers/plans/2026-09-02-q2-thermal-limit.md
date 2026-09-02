# Q2 Thermal Limit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether light, carbon, or temperature sets the outer limit for a passive organism at radiative equilibrium, and at what heliocentric distance.

**Architecture:** A new pure-function module `sim/thermal.py` (equilibrium temperature, temperature response) plus five defaulted fields on the existing frozen `Organism` and one new method beside `net_carbon`. Q1's carbon-only path is not touched. A `experiments/q2_thermal/` runner mirrors Q1's conventions exactly: two gates before any distance is reported, exit 2 on gate failure with stale outputs cleared, provenance-stamped CSVs.

**Tech Stack:** Python 3, numpy, scipy, PyYAML, pytest; figures in R + ggplot2 sourcing `docs/analysis/theme.R`.

**Spec:** `docs/superpowers/specs/2026-09-02-q2-thermal-limit-design.md`

## Global Constraints

- `experiments/q1_crossover/prereg.yaml` is FROZEN. Never edit it.
- Q1's committed CSV bodies must stay byte-identical. `tests/test_runner.py::test_committed_csvs_regenerate_exactly` is the guard and must stay green throughout.
- `sim/organism.py::Organism.net_carbon` must NOT change behaviour. Q2 adds `net_carbon_at_equilibrium` beside it.
- Every new `Organism` field MUST have a default, so `VASCULAR` and `ALGAL` construct unchanged.
- Fail loud: no silent fallbacks, no swallowed exceptions. Out-of-range inputs raise `ValueError` naming the value, matching `sim/physiology.py`.
- Never trust a test you have not seen fail: run each new assertion against the broken state and record the observed failure message in your report.
- A negative assertion carries a positive control in the same test.
- Plots are R + ggplot2 sourcing `docs/analysis/theme.R`. Never matplotlib, never inline restyling.
- Commit messages: conventional-commit style, no attribution lines, no `Claude-Session:` trailer.
- Stefan–Boltzmann constant is exactly `5.670374419e-8` W m⁻² K⁻⁴ (CODATA, exact by SI definition).
- **Do NOT tune `t_opt` to make Gate 2 pass.** If Gate 2 fails, report the failure and the implied `t_opt`. The spec names an ungrounded `t_opt` as the first suspect; tuning it until the gate passes is the exact circularity this gate exists to prevent.

---

### Task 1: `equilibrium_temperature`

**Files:**
- Create: `sim/thermal.py`
- Test: `tests/test_thermal.py`

**Interfaces:**
- Consumes: `sim.physiology.TSI_W_M2` (float, 1360.8)
- Produces: `SIGMA_W_M2_K4: float`; `equilibrium_temperature(r_au: float, area_ratio: float, emissivity: float = 1.0, albedo: float = 0.0) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_thermal.py
import pytest

from sim.thermal import SIGMA_W_M2_K4, equilibrium_temperature


def test_sphere_at_1_au_matches_blackbody_value():
    # area_ratio 4 = sphere: absorbs over pi r^2, radiates over 4 pi r^2.
    t = equilibrium_temperature(1.0, area_ratio=4.0)
    assert t == pytest.approx(278.31, abs=0.05)


def test_lamina_at_1_au_is_hotter_than_sphere():
    # A flat lamina radiates from 2 faces, not 4, so it runs hotter.
    lamina = equilibrium_temperature(1.0, area_ratio=2.0)
    sphere = equilibrium_temperature(1.0, area_ratio=4.0)
    assert lamina > sphere
    assert lamina == pytest.approx(330.97, abs=0.05)


def test_inverse_square_root_scaling():
    # S ~ 1/r^2 and T ~ S^(1/4), so T ~ r^-1/2: quadrupling r halves T.
    t1 = equilibrium_temperature(1.0, area_ratio=4.0)
    t4 = equilibrium_temperature(4.0, area_ratio=4.0)
    assert t4 == pytest.approx(t1 / 2.0, rel=1e-12)


def test_albedo_and_emissivity_lower_and_raise_temperature():
    base = equilibrium_temperature(1.0, area_ratio=4.0)
    # Reflecting 30% of the light must cool it.
    assert equilibrium_temperature(1.0, area_ratio=4.0, albedo=0.3) < base
    # A poorer emitter must run hotter for the same absorbed power.
    assert equilibrium_temperature(1.0, area_ratio=4.0, emissivity=0.5) > base


def test_sigma_is_the_codata_value():
    assert SIGMA_W_M2_K4 == 5.670374419e-8


@pytest.mark.parametrize(
    "kwargs, needle",
    [
        (dict(r_au=0.0, area_ratio=4.0), "r_au"),
        (dict(r_au=-1.0, area_ratio=4.0), "r_au"),
        (dict(r_au=1.0, area_ratio=0.0), "area_ratio"),
        (dict(r_au=1.0, area_ratio=4.0, emissivity=0.0), "emissivity"),
        (dict(r_au=1.0, area_ratio=4.0, emissivity=1.5), "emissivity"),
        (dict(r_au=1.0, area_ratio=4.0, albedo=-0.1), "albedo"),
        (dict(r_au=1.0, area_ratio=4.0, albedo=1.0), "albedo"),
    ],
)
def test_out_of_range_inputs_raise_naming_the_value(kwargs, needle):
    with pytest.raises(ValueError, match=needle):
        equilibrium_temperature(**kwargs)
    # positive control: the legitimate call in the same test still works
    assert equilibrium_temperature(1.0, area_ratio=4.0) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'sim.thermal'`

- [ ] **Step 3: Write the implementation**

```python
# sim/thermal.py
"""Radiative equilibrium temperature and the temperature response of photosynthesis.

Units: temperature in K; distance in AU; irradiance in W m⁻². All functions are
stateless. Out-of-range inputs raise ValueError naming the value.

Kept separate from sim/physiology.py, which is about light and carbon. This module
is the thermal domain introduced by Q2.
"""

from __future__ import annotations

from sim.physiology import TSI_W_M2

# CODATA / exact by the SI definition of the kelvin.
SIGMA_W_M2_K4 = 5.670374419e-8


def equilibrium_temperature(
    r_au: float,
    area_ratio: float,
    emissivity: float = 1.0,
    albedo: float = 0.0,
) -> float:
    """Radiative equilibrium temperature of a passive body at r_au.

    area_ratio is radiating area divided by absorbing (projected) area: 2 for a
    flat lamina that absorbs on one face and radiates from both, 4 for a sphere
    that absorbs over its cross-section and radiates over its whole surface.

    Absorbed = S(1-albedo) per unit projected area; emitted = area_ratio *
    emissivity * sigma * T^4 per unit projected area. Setting them equal:
    """
    if r_au <= 0:
        raise ValueError(f"r_au must be > 0, got {r_au}")
    if area_ratio <= 0:
        raise ValueError(f"area_ratio must be > 0, got {area_ratio}")
    if not (0 < emissivity <= 1):
        raise ValueError(f"emissivity must be in (0, 1], got {emissivity}")
    if not (0 <= albedo < 1):
        raise ValueError(f"albedo must be in [0, 1), got {albedo}")
    s = TSI_W_M2 / r_au**2
    return float((s * (1 - albedo) / (area_ratio * emissivity * SIGMA_W_M2_K4)) ** 0.25)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: PASS (all tests)

- [ ] **Step 5: Confirm the full suite is still green**

Run: `python3 -m pytest -q`
Expected: PASS — 39 pre-existing tests plus the new ones.

- [ ] **Step 6: Commit**

```bash
git add sim/thermal.py tests/test_thermal.py
git commit -m "feat(thermal): radiative equilibrium temperature"
```

---

### Task 2: `temperature_response` and the held-out gate

**Files:**
- Modify: `sim/thermal.py`
- Test: `tests/test_thermal.py`

**Interfaces:**
- Consumes: nothing new
- Produces: `temperature_response(t: float, t_min: float, t_opt: float) -> float` returning a multiplier in `[0.0, 1.0]`

**Why this shape:** the response is parameterized ONLY by `t_min` and `t_opt`. The literature anchors (60–70% of maximum at 5 °C, 30–40% at 0 °C) are HELD OUT and used only by the runner's Gate 2. Fitting the curve through those anchors and then checking it against them would be a test that cannot fail.

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_thermal.py
from sim.thermal import temperature_response


def test_response_is_zero_at_and_below_t_min():
    assert temperature_response(265.15, t_min=265.15, t_opt=298.15) == 0.0
    assert temperature_response(200.0, t_min=265.15, t_opt=298.15) == 0.0


def test_response_is_one_at_and_above_t_opt():
    assert temperature_response(298.15, t_min=265.15, t_opt=298.15) == 1.0
    assert temperature_response(310.0, t_min=265.15, t_opt=298.15) == 1.0


def test_response_is_linear_between_the_two_endpoints():
    # midpoint of [265.15, 298.15] is 281.65
    assert temperature_response(281.65, t_min=265.15, t_opt=298.15) == pytest.approx(0.5)


def test_response_is_monotonic_in_temperature():
    prev = -1.0
    for t in range(260, 305):
        v = temperature_response(float(t), t_min=265.15, t_opt=298.15)
        assert v >= prev
        prev = v


def test_response_rejects_t_opt_not_above_t_min():
    with pytest.raises(ValueError, match="t_opt"):
        temperature_response(280.0, t_min=298.15, t_opt=265.15)
    # positive control
    assert temperature_response(280.0, t_min=265.15, t_opt=298.15) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: FAIL — `ImportError: cannot import name 'temperature_response'`

- [ ] **Step 3: Write the implementation**

```python
# append to sim/thermal.py
def temperature_response(t: float, t_min: float, t_opt: float) -> float:
    """Normalized rate multiplier in [0, 1] for photosynthesis at temperature t.

    Linear from 0 at t_min to 1 at t_opt, flat above t_opt. Parameterized ONLY by
    t_min and t_opt: the literature rate anchors at 5 °C and 0 °C are deliberately
    NOT used here so the runner can hold them out as an independent gate. A curve
    fitted through the anchors could not fail a check against those same anchors.
    """
    if t_opt <= t_min:
        raise ValueError(f"t_opt must be > t_min, got t_opt={t_opt}, t_min={t_min}")
    if t <= t_min:
        return 0.0
    if t >= t_opt:
        return 1.0
    return float((t - t_min) / (t_opt - t_min))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_thermal.py -q`
Expected: PASS

- [ ] **Step 5: Record what the held-out anchors say about this form — do NOT tune**

Run this and paste the output into your task report verbatim:

```bash
python3 - <<'PY'
from sim.thermal import temperature_response
for t_opt in (298.15, 288.15, 286.15):
    f5 = temperature_response(278.15, 265.15, t_opt)   # 5 C
    f0 = temperature_response(273.15, 265.15, t_opt)   # 0 C
    print(f"t_opt={t_opt:7.2f}  f(5C)={f5:.4f} (gate 0.60-0.70)  f(0C)={f0:.4f} (gate 0.30-0.40)")
PY
```

This is diagnostic only. It tells the reviewer whether the declared `t_opt` of 298.15 K can satisfy Gate 2. **Do not change `t_opt` in any file on the strength of this output** — the prereg declares it, Gate 2 judges it, and the runner reports the verdict. Changing it here to make a later gate pass is the circularity the spec forbids.

- [ ] **Step 6: Run the full suite and commit**

```bash
python3 -m pytest -q
git add sim/thermal.py tests/test_thermal.py
git commit -m "feat(thermal): temperature response, parameterized only by t_min and t_opt"
```

---

### Task 3: extend `Organism` without disturbing Q1

**Files:**
- Modify: `sim/organism.py:21-60`
- Test: `tests/test_organism.py`

**Interfaces:**
- Consumes: `sim.thermal.equilibrium_temperature`, `sim.thermal.temperature_response`
- Produces: `Organism` with new defaulted fields `area_ratio: float = 2.0`, `t_min: float = 265.15`, `t_opt: float = 298.15`, `emissivity: float = 1.0`, `albedo: float = 0.0`; and `Organism.net_carbon_at_equilibrium(r_au: float, k: float | None = None) -> float`

- [ ] **Step 1: Write the failing tests**

```python
# append to tests/test_organism.py
from sim.organism import ALGAL, VASCULAR, Organism
from sim.thermal import equilibrium_temperature


def test_q1_presets_still_construct_with_unchanged_carbon_values():
    # The new fields are defaulted, so the Q1 presets are untouched.
    assert VASCULAR.net_carbon(1.0) == pytest.approx(9.2981, abs=1e-4)
    assert ALGAL.net_carbon(1.0) == pytest.approx(9.6290, abs=1e-4)


def test_new_fields_have_defaults():
    o = Organism("x", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)
    assert o.area_ratio == 2.0
    assert o.t_min == 265.15
    assert o.t_opt == 298.15
    assert o.emissivity == 1.0
    assert o.albedo == 0.0


def test_equilibrium_net_carbon_uses_the_equilibrium_temperature():
    # At 1 AU a sphere sits at ~278.3 K, which is above t_min for the algal floor
    # but below t_opt, so the response multiplier is strictly between 0 and 1.
    o = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65,
    )
    t = equilibrium_temperature(1.0, area_ratio=4.0)
    assert 254.65 < t < 298.15
    # Temperature-scaled assimilation must be strictly below the unscaled Q1 value.
    assert o.net_carbon_at_equilibrium(1.0) < o.net_carbon(1.0)


def test_equilibrium_net_carbon_is_negative_below_t_min():
    # Far enough out that T < t_min: assimilation is switched off entirely and
    # only respiration remains, so net carbon must be strictly negative.
    o = Organism(
        "algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0,
        area_ratio=4.0, t_min=254.65,
    )
    far = 100.0
    assert equilibrium_temperature(far, area_ratio=4.0) < 254.65
    assert o.net_carbon_at_equilibrium(far) < 0
    # positive control: near in, it is positive
    assert o.net_carbon_at_equilibrium(1.0) > 0


@pytest.mark.parametrize(
    "field, value",
    [("area_ratio", 0.0), ("emissivity", 1.5), ("albedo", 1.0), ("t_min", -1.0)],
)
def test_new_fields_validate(field, value):
    kwargs = dict(a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)
    kwargs[field] = value
    with pytest.raises(ValueError, match=field):
        Organism("x", **kwargs)
    # positive control
    assert Organism("x", **dict(a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=1.0)).a_max == 10.0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_organism.py -q`
Expected: FAIL — `TypeError: Organism.__init__() got an unexpected keyword argument 'area_ratio'`

- [ ] **Step 3: Add the fields, validation, and the new method**

In `sim/organism.py`, extend the import block at line 12 to add the thermal functions:

```python
from sim.thermal import equilibrium_temperature, temperature_response
```

Add these fields to the `Organism` dataclass immediately after `t_set` (line 28), keeping every one defaulted:

```python
    area_ratio: float = 2.0  # radiating area / projected area: 2 lamina, 4 sphere
    t_min: float = 265.15  # K, photosynthesis floor
    t_opt: float = 298.15  # K, response optimum (declared assumption, not grounded)
    emissivity: float = 1.0  # declared assumption
    albedo: float = 0.0  # declared assumption
```

Append to `__post_init__`:

```python
        if self.area_ratio <= 0:
            raise ValueError(f"area_ratio must be > 0, got {self.area_ratio}")
        if not (0 < self.emissivity <= 1):
            raise ValueError(f"emissivity must be in (0, 1], got {self.emissivity}")
        if not (0 <= self.albedo < 1):
            raise ValueError(f"albedo must be in [0, 1), got {self.albedo}")
        if self.t_min <= 0:
            raise ValueError(f"t_min must be > 0 K, got {self.t_min}")
        if self.t_opt <= self.t_min:
            raise ValueError(
                f"t_opt must be > t_min, got t_opt={self.t_opt}, t_min={self.t_min}"
            )
```

Add this method after `net_carbon` (after line 60). **Do not modify `net_carbon` itself.**

```python
    def net_carbon_at_equilibrium(self, r_au: float, k: float | None = None) -> float:
        """Net carbon for a PASSIVE organism whose temperature follows radiative
        equilibrium at r_au. Both terms move with distance: assimilation is scaled
        by the temperature response, and respiration is evaluated at the
        equilibrium temperature rather than at a fixed set-point.

        net_carbon() is the Q1 path and is deliberately left untouched: making it
        temperature-dependent would change Q1's committed numbers."""
        kk = self.k if k is None else k
        t = equilibrium_temperature(
            r_au, self.area_ratio, self.emissivity, self.albedo
        )
        f = temperature_response(t, self.t_min, self.t_opt)
        gross = gross_assimilation(irradiance(r_au), self.a_max, kk) * f
        return gross - respiration(self.r_d, t) / self.leaf_mass_ratio
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_organism.py -q`
Expected: PASS

- [ ] **Step 5: Prove Q1 is byte-identical — this is the cross-question guard**

Run: `python3 -m pytest tests/test_runner.py::test_committed_csvs_regenerate_exactly -v`
Expected: PASS. If this fails, extending `Organism` has perturbed Q1's committed numbers; stop and report rather than regenerating the CSVs.

Then confirm directly:

```bash
for f in calibration.csv sweep.csv crossover.csv; do
  diff <(git show HEAD:experiments/q1_crossover/$f | grep -v '^#') \
       <(grep -v '^#' experiments/q1_crossover/$f) >/dev/null \
    && echo "$f BODY IDENTICAL" || echo "$f *** CHANGED ***"
done
```

Expected: all three `BODY IDENTICAL`.

- [ ] **Step 6: Run the full suite and commit**

```bash
python3 -m pytest -q
git add sim/organism.py tests/test_organism.py
git commit -m "feat(organism): thermal fields and equilibrium net carbon, Q1 path untouched"
```

---

### Task 4: the pre-registration, with reachability computed before the run

**Files:**
- Create: `experiments/q2_thermal/prereg.yaml`
- Create: `experiments/q2_thermal/reachability.py`
- Test: `tests/test_q2_reachability.py`

**Interfaces:**
- Consumes: `sim.thermal.equilibrium_temperature`, `sim.organism.Organism`
- Produces: `experiments/q2_thermal/reachability.py::thermal_cutoff_au(t_min: float, area_ratio: float, emissivity: float = 1.0, albedo: float = 0.0) -> float`

**Why a separate step:** Q1's review found that 96.2% of its vascular band was pre-satisfied by its gate and 89.5% of its algal band was unreachable — both discovered after the run. The reachable interval goes into the prereg BEFORE anything is registered.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_q2_reachability.py
import pytest

from experiments.q2_thermal.reachability import thermal_cutoff_au
from sim.thermal import equilibrium_temperature


def test_cutoff_is_where_equilibrium_temperature_equals_t_min():
    r = thermal_cutoff_au(t_min=254.65, area_ratio=4.0)
    assert equilibrium_temperature(r, area_ratio=4.0) == pytest.approx(254.65, rel=1e-9)


def test_colder_floor_pushes_the_cutoff_further_out():
    warm = thermal_cutoff_au(t_min=268.15, area_ratio=2.0)
    cold = thermal_cutoff_au(t_min=254.65, area_ratio=2.0)
    assert cold > warm


def test_cutoff_rejects_a_nonpositive_floor():
    with pytest.raises(ValueError, match="t_min"):
        thermal_cutoff_au(t_min=0.0, area_ratio=4.0)
    # positive control
    assert thermal_cutoff_au(t_min=254.65, area_ratio=4.0) > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python3 -m pytest tests/test_q2_reachability.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'experiments.q2_thermal.reachability'`

- [ ] **Step 3: Write the implementation**

First create BOTH package markers — this is not optional:

```bash
touch experiments/__init__.py experiments/q2_thermal/__init__.py
```

**Why:** `tests/test_runner.py` puts `experiments/q1_crossover/` on `sys.path` and does a
bare `import run`. If Q2's runner were imported the same way, two different modules would
both be named `run` in one pytest session and whichever imported first would win. Importing
Q2's as `experiments.q2_thermal.run` gives it a distinct fully-qualified name, so the two
coexist. `pyproject.toml` already sets `pythonpath = ["."]`, so the repo root is importable.
Do not add a `sys.path.insert` to the Q2 test.

Then:

```python
# experiments/q2_thermal/reachability.py
"""Where the gates permit an outcome to land, computed BEFORE registering a band.

Q1 registered bands without this and found afterwards that 96.2% of one band was
pre-satisfied by its gate and 89.5% of the other was unreachable."""

from __future__ import annotations

from sim.physiology import TSI_W_M2
from sim.thermal import SIGMA_W_M2_K4


def thermal_cutoff_au(
    t_min: float, area_ratio: float, emissivity: float = 1.0, albedo: float = 0.0
) -> float:
    """Distance at which equilibrium temperature falls to t_min.

    Closed form: T(r) = T(1 AU) / sqrt(r), so r = (T(1 AU) / t_min)^2."""
    if t_min <= 0:
        raise ValueError(f"t_min must be > 0 K, got {t_min}")
    if area_ratio <= 0:
        raise ValueError(f"area_ratio must be > 0, got {area_ratio}")
    t_1au = (
        TSI_W_M2 * (1 - albedo) / (area_ratio * emissivity * SIGMA_W_M2_K4)
    ) ** 0.25
    return float((t_1au / t_min) ** 2)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python3 -m pytest tests/test_q2_reachability.py -q`
Expected: PASS

- [ ] **Step 5: Compute the reachable intervals for the prereg**

```bash
python3 - <<'PY'
from experiments.q2_thermal.reachability import thermal_cutoff_au
for cls, ratio, floors in (
    ("vascular", 2.0, (265.15, 266.65, 268.15)),
    ("algal", 4.0, (252.15, 254.65, 257.15)),
):
    rs = [thermal_cutoff_au(t, ratio) for t in floors]
    print(f"{cls}: t_min {floors} -> thermal cutoff {[round(r,4) for r in rs]} AU")
PY
```

Confirm the printed values match the `reachable_thermal_cutoff_au` block already filled in
below (vascular 1.5581 / 1.5406 / 1.5234; algal 1.2183 / 1.1945 / 1.1714). **If they differ,
stop and report** — a mismatch means the code and the plan disagree about the physics, and
the prereg must not be written from a value nobody reproduced.

- [ ] **Step 6: Write the pre-registration**

Create `experiments/q2_thermal/prereg.yaml`, substituting the intervals you just computed into `reachable_thermal_cutoff_au`:

```yaml
# Q2 pre-registration. Written BEFORE run.py produces limits.csv. Do not edit after.
registered: 2026-09-02
question: >
  For a passive organism at radiative equilibrium, with photosynthetic rate following
  an empirically-anchored temperature response rather than an extrapolated Q10, what
  sets the outer limit -- light, carbon, or temperature -- and at what distance?
spec: docs/superpowers/specs/2026-09-02-q2-thermal-limit-design.md
grounding: docs/bio_grounding_2026-09-02.md

# Must match sim/physiology.py and sim/thermal.py; run.py refuses to run on mismatch.
assumptions:
  tsi_w_m2: 1360.8          # Kopp & Lean 2011, 10.1029/2010GL045777
  par_fraction: 0.45        # assumption
  photons_per_j: 4.57       # assumption
  t_ref_k: 293.0
  q10: 2.0                  # assumption
  sigma_w_m2_k4: 5.670374419e-8   # CODATA, exact by SI definition
  t_opt_k: 298.15           # DECLARED ASSUMPTION, NOT GROUNDED. Gate 2 judges it.
  emissivity: 1.0           # declared assumption
  albedo: 0.0               # declared assumption

# Gate 1: thermal physics at 1 AU, sphere, emissivity 1, albedo 0.
gate_thermal:
  r_au: 1.0
  area_ratio: 4.0
  t_eq_k: [275.0, 282.0]    # brackets the standard blackbody value 278.3 K

# Gate 2: HELD OUT from the fit. temperature_response is parameterized only by
# t_min and t_opt; these two anchors are never used to build it.
# Pointing et al. 2015, 10.3389/fpls.2015.00692, quoting Koerner 2003b:
# "Cold adapted photosynthetic tissue in vascular plants reaches 60-70% of
#  maximum rates at 5 C and 30-40% at 0 C".
gate_response:
  t_min_k: 265.15           # the vascular floor used for the gate check
  anchors:
    - {t_k: 278.15, lo: 0.60, hi: 0.70}   # 5 C
    - {t_k: 273.15, lo: 0.30, hi: 0.40}   # 0 C

presets:
  vascular:
    a_max: 10.0
    k: 100.0
    r_d: 0.65
    leaf_mass_ratio: 0.5
    area_ratio: 2.0         # flat lamina: absorbs one face, radiates two
    # Koerner 2003a via Pointing et al. 2015: chloroplasts freeze at -5 to -8 C.
    t_min_grid: [265.15, 266.65, 268.15]
  algal:
    a_max: 10.0
    k: 20.0
    r_d: 0.24
    leaf_mass_ratio: 1.0    # unicellular: no non-photosynthetic organ (2026-09-02)
    area_ratio: 4.0         # sphere: absorbs cross-section, radiates whole surface
    # Pointing et al. 2015: net photosynthesis measured to -18.5 C. The source gives
    # ONE value, not a range; the +/- 2.5 K spread is a DECLARED ASSUMPTION.
    t_min_grid: [252.15, 254.65, 257.15]

sweep:
  r_min_au: 0.5
  r_max_au: 100.0
  n_grid: 200

# Computed BEFORE registering, from reachability.py. A band the gates cannot reach
# is not a prediction.
reachable_thermal_cutoff_au:
  # Computed from reachability.py before registering; each entry pairs with the
  # same index of that class's t_min_grid.
  vascular: [1.5581, 1.5406, 1.5234]
  algal: [1.2183, 1.1945, 1.1714]

# The registered prediction.
predicted_binding_limit:
  vascular: temperature
  algal: temperature
```

- [ ] **Step 7: Commit**

```bash
git add experiments/q2_thermal/ tests/test_q2_reachability.py
git commit -m "exp(q2): pre-registration with reachability computed before the run"
```

---

### Task 5: the runner

**Files:**
- Create: `experiments/q2_thermal/run.py`
- Test: `tests/test_q2_runner.py`

**Interfaces:**
- Consumes: everything from Tasks 1–4
- Produces: `main(argv: list[str] | None = None) -> int`; CSVs `gates.csv` (`gate,detail,observed,lo,hi,passed`), `sweep.csv` (`class,t_min,r_au,t_eq,response,net_carbon`), `limits.csv` (`class,t_min,thermal_au,carbon_fixed_t_au,carbon_equilibrium_au,binding`)

**Mirror Q1's runner exactly** (`experiments/q1_crossover/run.py`): gates before any limit is reported, exit 2 on gate failure, stale outputs unlinked before that exit, provenance header on every CSV.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_q2_runner.py
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
    for key in ("# git_sha=", "# thermal_md5=", "# organism_md5=", "# prereg_md5=",
                "# python=", "# numpy=", "# scipy=", "# written="):
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
        capture_output=True, text=True,
    )
    assert proc.returncode != 0
    assert not (tmp_path / "o2" / "limits.csv").exists()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_q2_runner.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'experiments.q2_thermal.run'`

- [ ] **Step 3: Write the runner**

```python
#!/usr/bin/env python3
"""Q2 runner: two gates, then a distance sweep, then provenance-stamped CSVs.

Exit codes: 0 = both gates passed and limits written; 2 = a gate failed
(gates.csv written, sweep.csv and limits.csv removed). Anything else raises.
"""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import platform
import subprocess
import sys
from pathlib import Path

import numpy as np
import scipy
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import physiology, thermal  # noqa: E402
from sim.organism import Organism, crossover_distance_for  # noqa: E402
from sim.physiology import crossover_distance  # noqa: E402
from sim.thermal import equilibrium_temperature, temperature_response  # noqa: E402

THERMAL_PATH = REPO_ROOT / "sim" / "thermal.py"
ORGANISM_PATH = REPO_ROOT / "sim" / "organism.py"
PHYSIOLOGY_PATH = REPO_ROOT / "sim" / "physiology.py"


def load_prereg(path: Path) -> dict:
    with open(path) as fh:
        return yaml.safe_load(fh)


def assert_assumptions_match(prereg: dict) -> None:
    a = prereg["assumptions"]
    pairs = {
        "tsi_w_m2": physiology.TSI_W_M2,
        "par_fraction": physiology.PAR_FRACTION,
        "photons_per_j": physiology.PHOTONS_PER_J,
        "t_ref_k": physiology.T_REF_K,
        "q10": physiology.Q10,
        "sigma_w_m2_k4": thermal.SIGMA_W_M2_K4,
    }
    for key, code_value in pairs.items():
        if not np.isclose(a[key], code_value):
            raise ValueError(
                f"prereg assumption {key}={a[key]} does not match code {key}={code_value}"
            )


def build(name: str, p: dict, a: dict, t_min: float) -> Organism:
    return Organism(
        name,
        a_max=p["a_max"],
        k=p["k"],
        r_d=p["r_d"],
        leaf_mass_ratio=p["leaf_mass_ratio"],
        area_ratio=p["area_ratio"],
        t_min=t_min,
        t_opt=float(a["t_opt_k"]),
        emissivity=float(a["emissivity"]),
        albedo=float(a["albedo"]),
    )


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def git_sha() -> str:
    proc = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, capture_output=True, text=True
    )
    if proc.returncode != 0:
        raise RuntimeError(
            f"git rev-parse HEAD failed in {REPO_ROOT} "
            f"(exit {proc.returncode}): {proc.stderr.strip() or '<no stderr>'}"
        )
    return proc.stdout.strip()


def provenance_lines(prereg_path: Path) -> list[str]:
    return [
        f"# git_sha={git_sha()}",
        f"# thermal_md5={_md5(THERMAL_PATH)}",
        f"# organism_md5={_md5(ORGANISM_PATH)}",
        f"# physiology_md5={_md5(PHYSIOLOGY_PATH)}",
        f"# prereg_md5={_md5(prereg_path)}",
        f"# python={platform.python_version()}",
        f"# numpy={np.__version__}",
        f"# scipy={scipy.__version__}",
        f"# written={dt.datetime.now().astimezone().isoformat(timespec='seconds')}",
    ]


def write_csv(path: Path, header: list[str], fieldnames: list[str], rows: list[dict]) -> None:
    with open(path, "w", newline="") as fh:
        for line in header:
            fh.write(line + "\n")
        w = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow(r)


def run_gates(prereg: dict) -> tuple[list[dict], bool]:
    """Gate 1 = thermal physics. Gate 2 = the HELD-OUT response anchors."""
    rows, ok = [], True
    g1 = prereg["gate_thermal"]
    obs = equilibrium_temperature(float(g1["r_au"]), float(g1["area_ratio"]))
    lo, hi = (float(x) for x in g1["t_eq_k"])
    passed = lo <= obs <= hi
    ok &= passed
    rows.append({"gate": "thermal", "detail": f"T_eq at {g1['r_au']} AU",
                 "observed": f"{obs:.4f}", "lo": lo, "hi": hi, "passed": passed})

    g2 = prereg["gate_response"]
    t_min = float(g2["t_min_k"])
    t_opt = float(prereg["assumptions"]["t_opt_k"])
    for anchor in g2["anchors"]:
        t = float(anchor["t_k"])
        obs = temperature_response(t, t_min, t_opt)
        lo, hi = float(anchor["lo"]), float(anchor["hi"])
        passed = lo <= obs <= hi
        ok &= passed
        rows.append({"gate": "response", "detail": f"f(T={t} K)",
                     "observed": f"{obs:.4f}", "lo": lo, "hi": hi, "passed": passed})
    return rows, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prereg", type=Path, default=Path(__file__).with_name("prereg.yaml"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args(argv)

    prereg = load_prereg(args.prereg)
    assert_assumptions_match(prereg)
    args.out.mkdir(parents=True, exist_ok=True)
    header = provenance_lines(args.prereg)

    gate_rows, all_pass = run_gates(prereg)
    write_csv(args.out / "gates.csv", header,
              ["gate", "detail", "observed", "lo", "hi", "passed"], gate_rows)
    for r in gate_rows:
        print(f"gate {r['gate']} {r['detail']}: {r['observed']} "
              f"in [{r['lo']}, {r['hi']}] {'pass' if r['passed'] else 'FAIL'}")
    if not all_pass:
        for stale in ("sweep.csv", "limits.csv"):
            (args.out / stale).unlink(missing_ok=True)
        print("GATE FAILED: limits not reported.")
        print("Do NOT tune t_opt to pass. Report the failure and the implied t_opt.")
        print(f"removed any stale sweep.csv/limits.csv from {args.out}")
        return 2

    a = prereg["assumptions"]
    sw = prereg["sweep"]
    r_min, r_max, n_grid = float(sw["r_min_au"]), float(sw["r_max_au"]), int(sw["n_grid"])
    grid = np.geomspace(r_min, r_max, n_grid)
    sweep_rows, limit_rows = [], []
    for name, p in prereg["presets"].items():
        for t_min in p["t_min_grid"]:
            t_min = float(t_min)
            org = build(name, p, a, t_min)
            for r in grid:
                r = float(r)
                t_eq = equilibrium_temperature(r, org.area_ratio, org.emissivity, org.albedo)
                sweep_rows.append({
                    "class": name, "t_min": t_min, "r_au": f"{r:.6g}",
                    "t_eq": f"{t_eq:.4f}",
                    "response": f"{temperature_response(t_eq, org.t_min, org.t_opt):.6g}",
                    "net_carbon": f"{org.net_carbon_at_equilibrium(r):.6g}",
                })
            t_1au = equilibrium_temperature(1.0, org.area_ratio, org.emissivity, org.albedo)
            thermal_au = (t_1au / t_min) ** 2
            try:
                carbon_fixed = crossover_distance_for(org, r_min=r_min, r_max=r_max, n_grid=n_grid)
            except ValueError:
                carbon_fixed = float("nan")
            try:
                carbon_eq = crossover_distance(
                    org.net_carbon_at_equilibrium, r_min=r_min, r_max=r_max, n_grid=n_grid
                )
            except ValueError:
                carbon_eq = float("nan")
            candidates = {"temperature": thermal_au, "carbon_fixed_t": carbon_fixed,
                          "carbon_equilibrium": carbon_eq}
            finite = {k: v for k, v in candidates.items() if np.isfinite(v)}
            binding = min(finite, key=finite.get) if finite else "none_in_window"
            limit_rows.append({
                "class": name, "t_min": t_min, "thermal_au": f"{thermal_au:.4f}",
                "carbon_fixed_t_au": f"{carbon_fixed:.4f}",
                "carbon_equilibrium_au": f"{carbon_eq:.4f}", "binding": binding,
            })
            print(f"limits {name} t_min={t_min:g}: thermal={thermal_au:.3f} "
                  f"carbon_fixedT={carbon_fixed:.3f} carbon_eq={carbon_eq:.3f} -> {binding}")
    write_csv(args.out / "sweep.csv", header,
              ["class", "t_min", "r_au", "t_eq", "response", "net_carbon"], sweep_rows)
    write_csv(args.out / "limits.csv", header,
              ["class", "t_min", "thermal_au", "carbon_fixed_t_au",
               "carbon_equilibrium_au", "binding"], limit_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_q2_runner.py -q`
Expected: PASS

- [ ] **Step 5a: See Gate 2 reject a deliberately wrong response function**

The spec requires this: a gate that has never been seen to fail is not evidence. Add:

```python
# append to tests/test_q2_runner.py
def test_response_gate_rejects_a_wrong_functional_form(tmp_path, monkeypatch):
    """A flat response of 0.99 is physically absurd -- it says a frozen organism
    photosynthesises at 99% of optimum. Gate 2 must reject it."""
    monkeypatch.setattr(run, "temperature_response", lambda t, t_min, t_opt: 0.99)
    out = tmp_path / "wrong"
    assert run.main(["--prereg", str(PREREG), "--out", str(out)]) == 2
    rows = _rows(out / "gates.csv")
    assert any("False" in r for r in rows), "gate 2 accepted a flat 0.99 response"
    assert not (out / "limits.csv").exists()
```

Run it, confirm it passes (i.e. the gate does reject), and record the `gates.csv` rows it
produced. Then confirm the positive direction: with the real function, the same anchors are
evaluated rather than skipped.

- [ ] **Step 5b: See the stale-CSV assertion fail on unfixed code**

Temporarily comment out the two `unlink` lines in `main`, run
`python3 -m pytest tests/test_q2_runner.py::test_gate_thermal_failure_exits_2_and_clears_stale_limits -q`,
and record the failure message. Then restore the lines and confirm the test passes again. Report both.

- [ ] **Step 6: Run the full suite and commit**

```bash
python3 -m pytest -q
git add experiments/q2_thermal/run.py tests/test_q2_runner.py
git commit -m "exp(q2): gated runner for the thermal limit"
```

---

### Task 6: run it, plot it, write it up

**Files:**
- Create: `experiments/q2_thermal/plot.R`
- Create: `experiments/q2_thermal/RESULTS.md`
- Modify: `docs/ROADMAP.md`

**Interfaces:**
- Consumes: the CSVs from Task 5

- [ ] **Step 1: Run the experiment into the repo directory**

```bash
python3 experiments/q2_thermal/run.py
echo "exit=$?"
```

Record the exit code and the full stdout. **If a gate failed (exit 2), that is a legitimate outcome — do NOT tune `t_opt` or any prereg value.** Record which anchor failed and what `t_opt` would have been needed, and continue to Step 5 to write it up as the result.

- [ ] **Step 2: Write the plot script (only if Step 1 exited 0)**

```r
#!/usr/bin/env Rscript
# Two figures from the Q2 CSVs. One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#")
limits <- read.csv(file.path(in_dir, "limits.csv"), comment.char = "#")
stopifnot(nrow(sweep) > 0, nrow(limits) > 0)
sweep$t_min <- factor(sweep$t_min)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)

# Figure 1: equilibrium temperature vs distance, with each class's floor
floors <- unique(limits[, c("class", "t_min")])
p1 <- ggplot(sweep, aes(r_au, t_eq, colour = class, linetype = t_min)) +
  geom_line() +
  geom_hline(data = floors, aes(yintercept = t_min, colour = class),
             linetype = "dotted", show.legend = FALSE) +
  scale_x_log10() +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)", y = "equilibrium temperature (K)",
       linetype = expression(T[min]~(K)),
       title = "Q2: equilibrium temperature vs distance; dotted = photosynthesis floor") +
  theme_dyson()
ggsave(file.path(fig_dir, "temperature_vs_distance.png"), p1, width = 8, height = 4.5, dpi = 150)

# Figure 2: where each limit falls, per class
long <- reshape(limits[, c("class", "t_min", "thermal_au", "carbon_equilibrium_au")],
                direction = "long", varying = c("thermal_au", "carbon_equilibrium_au"),
                v.names = "distance_au", timevar = "limit",
                times = c("temperature", "carbon"), idvar = c("class", "t_min"))
p2 <- ggplot(long, aes(distance_au, interaction(class, t_min), colour = class, shape = limit)) +
  geom_point(size = 3, na.rm = TRUE) +
  scale_x_log10() +
  scale_colour_dyson() +
  labs(x = "distance (AU, log)", y = "class and floor",
       title = "Q2: which limit binds first") +
  theme_dyson()
ggsave(file.path(fig_dir, "which_limit_binds.png"), p2, width = 8, height = 4.5, dpi = 150)
cat("wrote", fig_dir, "\n")
```

Run: `Rscript experiments/q2_thermal/plot.R` and confirm both PNGs exist.

- [ ] **Step 3: Look at both figures before claiming they are correct**

Copy them where the user can see them and open once:

```bash
cp experiments/q2_thermal/figures/*.png /mnt/c/Users/a2b32/Downloads/
cd /mnt/c/Users/a2b32/Downloads && cmd.exe /c start "" which_limit_binds.png
```

Read the PNGs yourself too. A warning-free render is not evidence a layer drew: Q1's prediction band silently vanished under a log axis and the implementer called the warning harmless without looking.

- [ ] **Step 4: Add the Q2 regeneration test**

```python
# append to tests/test_q2_runner.py
def test_committed_q2_csvs_regenerate_exactly(tmp_path):
    """The committed record must be what the committed code produces."""
    src = REPO / "experiments" / "q2_thermal"
    if not (src / "gates.csv").exists():
        pytest.skip("Q2 has not been run into the repo directory yet")
    out = tmp_path / "regen"
    run.main(["--prereg", str(PREREG), "--out", str(out)])
    for name in ("gates.csv", "sweep.csv", "limits.csv"):
        if not (src / name).exists():
            continue
        committed = [x for x in (src / name).read_text().splitlines()
                     if not x.startswith("# git_sha=") and not x.startswith("# written=")]
        fresh = [x for x in (out / name).read_text().splitlines()
                 if not x.startswith("# git_sha=") and not x.startswith("# written=")]
        assert committed == fresh, f"{name} does not regenerate"
```

Run: `python3 -m pytest tests/test_q2_runner.py -q`. Then tamper with one committed value, confirm the test fails, restore, and record both.

- [ ] **Step 5: Write `experiments/q2_thermal/RESULTS.md`**

Report, in this order: which gates passed and their observed values; **if Gate 2 failed, say so plainly and give the `t_opt` the anchors imply, without changing anything**; the limits table per class and floor; which limit binds; how the registered prediction (`temperature` for both classes) fared; and the reachable intervals from the prereg against the outcome. Copy the provenance header from `limits.csv` verbatim. State the [0.5, 100] AU solve window and flag any value near its edge.

- [ ] **Step 6: Update `docs/ROADMAP.md` and commit**

Tick the Q2 line, point it at `experiments/q2_thermal/RESULTS.md`, and reconcile the "Where this stands" prose in the same commit — Q1's review found the roadmap contradicting itself twice because prose and checklist were updated separately.

```bash
python3 -m pytest -q
git add experiments/q2_thermal/ docs/ROADMAP.md
git commit -m "exp(q2): run the registered thermal-limit question; record results"
```
