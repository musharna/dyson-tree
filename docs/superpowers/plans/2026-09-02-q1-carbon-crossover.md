# Q1 Carbon-Budget Crossover Implementation Plan

> **Path redaction (2026-09-10, release 1.0).** The local paths in this plan were
> written for one machine. Before the repository was made public the operator's
> home directory and Windows account name were replaced with `~` and
> `<windows-user>`. Only those identifiers changed; every command, claim and
> number in this file is untouched.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a pure-function carbon-budget model of one Dyson-tree organism, gate it on published 1 AU compensation irradiance, then sweep heliocentric distance to measure where net carbon crosses zero per photosystem class.

**Architecture:** Three layers: `sim/physiology.py` (pure physics/biology functions, numpy-aware), `sim/organism.py` (frozen dataclass + two calibrated presets + compensation solver), and `experiments/q1_crossover/` (pre-registration YAML, runner that gates then sweeps and writes provenance-stamped CSVs, R plots that read only CSVs). No state, no time axis.

**Tech Stack:** Python 3.13 (conda base at `~/miniconda3/bin/python3`), numpy 2.3, scipy 1.16 (`brentq`), PyYAML, pytest 9. Plots: R 4.3.3 + ggplot2 4.0.2 via `/usr/bin/Rscript`.

**Spec:** `docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md` (read it first; grounding numbers in `docs/prior_art_2026-09-01.md`).

## Global Constraints

- All work in `~/dyson-tree` on `master`. Run commands from the repo root.
- Every commit message ends with the line `Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M`.
- Fail loud: no try/except that defaults, no clamping. Out-of-range inputs raise `ValueError` naming the offending value.
- Units: irradiance in µmol photons m⁻² s⁻¹; assimilation and respiration in µmol CO₂ m⁻² s⁻¹ per unit photosynthetic area; temperature in K; distance in AU.
- Constants: TSI = 1360.8 W m⁻²; PAR_FRACTION = 0.45; PHOTONS_PER_J = 4.57; T_ref = 293.0 K; Q10 = 2.0. `irradiance(1.0)` = 1360.8 × 0.45 × 4.57 = 2798.5 (top-of-atmosphere, NOT 2000).
- Calibration gates: VASCULAR compensation in [5.3, 9.0]; ALGAL in [0.0, 1.0]. Pre-registered r*: VASCULAR [12, 22] AU; ALGAL [35, 55] AU. **Do not change presets, gates, or predictions after the sweep has been run. If the prediction fails, report the failure.**
- Calibration touches only `r_d`. Never touch light physics or `a_max`/`k` to make a gate pass.
- Plots: R + ggplot2 only, one graph per figure, every plot script sources `docs/analysis/theme.R`.
- Runtime is seconds; no jobd needed.

---

## File structure

| File | Responsibility |
|---|---|
| `pyproject.toml` | pytest config: `pythonpath = ["."]` so `import sim` works |
| `.gitignore` | add `__pycache__/`, `.pytest_cache/` |
| `sim/__init__.py` | empty |
| `sim/physiology.py` | `irradiance`, `gross_assimilation`, `respiration`, `crossover_distance` (takes a callable) |
| `sim/organism.py` | `Organism` dataclass, `compensation_irradiance`, `crossover_distance_for`, `VASCULAR`, `ALGAL` |
| `tests/test_physiology.py` | physics identities + range errors |
| `tests/test_organism.py` | calibration gates + compensation controls |
| `tests/test_crossover.py` | crossover controls (R_d=0 raises; 2×R_d moves inward) |
| `tests/test_runner.py` | gate failure ⇒ exit 2 and no crossover.csv; real prereg ⇒ both CSVs with provenance |
| `experiments/q1_crossover/prereg.yaml` | the registered question, presets, gates, predictions, sweep grid |
| `experiments/q1_crossover/run.py` | gate → sweep → CSVs with provenance header |
| `docs/analysis/theme.R` | house ggplot2 theme + palette |
| `experiments/q1_crossover/plot.R` | two figures from CSVs |
| `experiments/q1_crossover/RESULTS.md` | numbers copied from CSVs, pass/fail verbatim |
| `docs/ROADMAP.md` | tick items, rewrite spine item 1 |

---

### Task 1: Physics functions

**Files:**
- Create: `pyproject.toml`, `sim/__init__.py`, `sim/physiology.py`
- Modify: `.gitignore`
- Test: `tests/test_physiology.py`

**Interfaces:**
- Produces: `irradiance(r_au, tsi=1360.8, par_fraction=0.45, photons_per_j=4.57) -> float|ndarray`; `gross_assimilation(i, a_max, k) -> float|ndarray`; `respiration(r_d, t, t_ref=293.0, q10=2.0) -> float`; module constants `TSI_W_M2`, `PAR_FRACTION`, `PHOTONS_PER_J`, `T_REF_K`, `Q10`.

- [ ] **Step 1: Create config files**

`pyproject.toml`:
```toml
[tool.pytest.ini_options]
pythonpath = ["."]
testpaths = ["tests"]
```

Append to `.gitignore`:
```
__pycache__/
.pytest_cache/
```

Create empty `sim/__init__.py` (`touch sim/__init__.py`). Delete `sim/.gitkeep` and `tests/.gitkeep` (`git rm -q sim/.gitkeep tests/.gitkeep`).

- [ ] **Step 2: Write the failing tests**

`tests/test_physiology.py`:
```python
import numpy as np
import pytest

from sim.physiology import (
    PAR_FRACTION, PHOTONS_PER_J, TSI_W_M2,
    gross_assimilation, irradiance, respiration,
)


def test_irradiance_at_1_au_matches_stated_assumptions():
    # 1360.8 * 0.45 * 4.57 = 2798.5 (top-of-atmosphere PAR photon flux)
    assert irradiance(1.0) == pytest.approx(TSI_W_M2 * PAR_FRACTION * PHOTONS_PER_J)
    assert irradiance(1.0) == pytest.approx(2798.5, rel=1e-3)


def test_irradiance_inverse_square():
    assert irradiance(10.0) == pytest.approx(irradiance(1.0) / 100.0)


def test_irradiance_accepts_arrays():
    r = np.array([1.0, 2.0, 4.0])
    out = irradiance(r)
    assert out.shape == (3,)
    assert out[1] == pytest.approx(out[0] / 4.0)


def test_irradiance_rejects_nonpositive_distance():
    with pytest.raises(ValueError, match="r_au"):
        irradiance(0.0)
    with pytest.raises(ValueError, match="r_au"):
        irradiance(np.array([1.0, -1.0]))


def test_gross_assimilation_is_rectangular_hyperbola():
    # at I = k, assimilation is half of a_max
    assert gross_assimilation(100.0, a_max=10.0, k=100.0) == pytest.approx(5.0)
    assert gross_assimilation(0.0, a_max=10.0, k=100.0) == 0.0
    # saturates toward a_max
    assert gross_assimilation(1e9, a_max=10.0, k=100.0) == pytest.approx(10.0, rel=1e-6)


def test_gross_assimilation_rejects_bad_params():
    with pytest.raises(ValueError, match="a_max"):
        gross_assimilation(10.0, a_max=0.0, k=100.0)
    with pytest.raises(ValueError, match="k"):
        gross_assimilation(10.0, a_max=10.0, k=-1.0)
    with pytest.raises(ValueError, match="irradiance"):
        gross_assimilation(-5.0, a_max=10.0, k=100.0)


def test_respiration_q10():
    assert respiration(1.0, t=293.0) == pytest.approx(1.0)
    assert respiration(1.0, t=303.0) == pytest.approx(2.0)
    assert respiration(1.0, t=283.0) == pytest.approx(0.5)
    assert respiration(0.0, t=293.0) == 0.0


def test_respiration_rejects_bad_params():
    with pytest.raises(ValueError, match="r_d"):
        respiration(-0.1, t=293.0)
    with pytest.raises(ValueError, match="t must"):
        respiration(1.0, t=0.0)
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_physiology.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'sim.physiology'`

- [ ] **Step 4: Write the implementation**

`sim/physiology.py`:
```python
"""Pure physics and physiology functions for the Q1 carbon-budget model.

Units: irradiance in µmol photons m⁻² s⁻¹; assimilation/respiration in
µmol CO₂ m⁻² s⁻¹ per unit photosynthetic area; temperature in K; distance in AU.
All functions are stateless. Out-of-range inputs raise ValueError naming the value.
"""
from __future__ import annotations

import numpy as np
from scipy.optimize import brentq

# Kopp & Lean 2011, doi:10.1029/2010GL045777 (2008 solar minimum)
TSI_W_M2 = 1360.8
# Assumptions, declared in experiments/q1_crossover/prereg.yaml
PAR_FRACTION = 0.45      # fraction of TSI in 400-700 nm
PHOTONS_PER_J = 4.57     # µmol photons per J of PAR
T_REF_K = 293.0
Q10 = 2.0


def irradiance(r_au, tsi=TSI_W_M2, par_fraction=PAR_FRACTION, photons_per_j=PHOTONS_PER_J):
    """PAR photon flux at heliocentric distance r_au, top-of-atmosphere, 1/r²."""
    r = np.asarray(r_au, dtype=float)
    if np.any(r <= 0):
        raise ValueError(f"r_au must be > 0, got {r_au}")
    out = tsi / r**2 * par_fraction * photons_per_j
    return float(out) if out.ndim == 0 else out


def gross_assimilation(i, a_max, k):
    """Rectangular hyperbola: a_max * I / (I + k)."""
    if a_max <= 0:
        raise ValueError(f"a_max must be > 0, got {a_max}")
    if k <= 0:
        raise ValueError(f"k must be > 0, got {k}")
    ii = np.asarray(i, dtype=float)
    if np.any(ii < 0):
        raise ValueError(f"irradiance must be >= 0, got {i}")
    out = a_max * ii / (ii + k)
    return float(out) if out.ndim == 0 else out


def respiration(r_d, t, t_ref=T_REF_K, q10=Q10):
    """Dark respiration with Q10 temperature dependence."""
    if r_d < 0:
        raise ValueError(f"r_d must be >= 0, got {r_d}")
    if t <= 0:
        raise ValueError(f"t must be > 0 K, got {t}")
    if q10 <= 0:
        raise ValueError(f"q10 must be > 0, got {q10}")
    return r_d * q10 ** ((t - t_ref) / 10.0)


def crossover_distance(net_fn, r_min=0.5, r_max=100.0, n_grid=400):
    """Distance in AU where net_fn(r) crosses zero. Brent root on the first
    sign change of a log-spaced grid. Raises if there is no sign change."""
    if r_min <= 0 or r_max <= r_min:
        raise ValueError(f"need 0 < r_min < r_max, got {r_min}, {r_max}")
    grid = np.geomspace(r_min, r_max, n_grid)
    vals = np.array([net_fn(float(r)) for r in grid])
    sign = np.sign(vals)
    idx = np.where(sign[:-1] * sign[1:] < 0)[0]
    if len(idx) == 0:
        raise ValueError(
            f"no sign change of net carbon on [{r_min}, {r_max}] AU: "
            f"min={vals.min():.4g}, max={vals.max():.4g}"
        )
    i = idx[0]
    return float(brentq(net_fn, grid[i], grid[i + 1], xtol=1e-6))
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_physiology.py -v`
Expected: 8 passed

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml .gitignore sim/__init__.py sim/physiology.py tests/test_physiology.py
git rm -q --cached sim/.gitkeep tests/.gitkeep 2>/dev/null; rm -f sim/.gitkeep tests/.gitkeep
git commit -m "feat(sim): physics functions with identity tests

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```

---

### Task 2: Organism, compensation irradiance, calibrated presets

**Files:**
- Create: `sim/organism.py`
- Test: `tests/test_organism.py`

**Interfaces:**
- Consumes: `sim.physiology.irradiance`, `gross_assimilation`, `respiration`, `T_REF_K`.
- Produces: `Organism(cls: str, a_max: float, k: float, r_d: float, leaf_mass_ratio: float, t_set: float = 293.0)` frozen dataclass with methods `leaf_respiration() -> float`, `organism_respiration() -> float`, `net_carbon(r_au, k=None) -> float`; module function `compensation_irradiance(org, k=None) -> float`; presets `VASCULAR`, `ALGAL`; `PRESETS: dict[str, Organism]`.

- [ ] **Step 1: Write the failing tests**

`tests/test_organism.py`:
```python
import pytest

from sim.organism import ALGAL, PRESETS, VASCULAR, Organism, compensation_irradiance
from sim.physiology import irradiance


# --- calibration gates (the scientific tests) -------------------------------

def test_vascular_compensation_inside_craine_reich_gate():
    # Craine & Reich 2005, doi:10.1111/j.1469-8137.2005.01420.x: LSMs 5.3, 8.1, 9.0
    ic = compensation_irradiance(VASCULAR)
    assert 5.3 <= ic <= 9.0, ic


def test_algal_compensation_below_richardson_floor():
    # Richardson 1983, doi:10.1111/j.1469-8137.1983.tb03422.x: growth < 1 µE
    ic = compensation_irradiance(ALGAL)
    assert 0.0 < ic < 1.0, ic


# --- analytic identity -------------------------------------------------------

def test_compensation_is_where_gross_equals_leaf_respiration():
    org = Organism("x", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
    ic = compensation_irradiance(org)
    from sim.physiology import gross_assimilation
    assert gross_assimilation(ic, org.a_max, org.k) == pytest.approx(org.leaf_respiration())
    # closed form K*R/(A_max-R)
    assert ic == pytest.approx(100.0 * 0.65 / (10.0 - 0.65))


# --- controls: healthy path and broken path asserted together ---------------

def test_zero_respiration_gives_zero_compensation_while_baseline_is_positive():
    base = compensation_irradiance(VASCULAR)
    assert base > 0
    dead = Organism("v0", a_max=VASCULAR.a_max, k=VASCULAR.k, r_d=0.0,
                    leaf_mass_ratio=VASCULAR.leaf_mass_ratio)
    assert compensation_irradiance(dead) == 0.0


def test_doubling_respiration_raises_compensation():
    base = compensation_irradiance(VASCULAR)
    hot = Organism("v2", a_max=VASCULAR.a_max, k=VASCULAR.k, r_d=2 * VASCULAR.r_d,
                   leaf_mass_ratio=VASCULAR.leaf_mass_ratio)
    assert compensation_irradiance(hot) > base


def test_respiration_at_or_above_a_max_raises():
    org = Organism("x", a_max=1.0, k=10.0, r_d=1.0, leaf_mass_ratio=1.0)
    with pytest.raises(ValueError, match="a_max"):
        compensation_irradiance(org)


# --- whole-organism net carbon ----------------------------------------------

def test_net_carbon_positive_at_1_au_for_both_presets():
    assert VASCULAR.net_carbon(1.0) > 0
    assert ALGAL.net_carbon(1.0) > 0


def test_net_carbon_uses_leaf_mass_ratio():
    whole = Organism("w", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=1.0)
    half = Organism("h", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
    assert half.organism_respiration() == pytest.approx(2 * whole.organism_respiration())
    assert half.net_carbon(1.0) < whole.net_carbon(1.0)


def test_net_carbon_k_override():
    i1 = irradiance(1.0)
    assert VASCULAR.net_carbon(1.0, k=VASCULAR.k) == pytest.approx(VASCULAR.net_carbon(1.0))
    # larger k => less assimilation at the same light
    assert VASCULAR.net_carbon(1.0, k=2 * VASCULAR.k) < VASCULAR.net_carbon(1.0)


def test_organism_validates_ranges():
    with pytest.raises(ValueError, match="leaf_mass_ratio"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.0)
    with pytest.raises(ValueError, match="leaf_mass_ratio"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=1.5)
    with pytest.raises(ValueError, match="a_max"):
        Organism("x", a_max=-1.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.5)
    with pytest.raises(ValueError, match="t_set"):
        Organism("x", a_max=10.0, k=100.0, r_d=0.5, leaf_mass_ratio=0.5, t_set=-5.0)


def test_presets_registry():
    assert set(PRESETS) == {"vascular", "algal"}
    assert PRESETS["vascular"] is VASCULAR
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_organism.py -v`
Expected: collection error, `ModuleNotFoundError: No module named 'sim.organism'`

- [ ] **Step 3: Write the implementation**

`sim/organism.py`:
```python
"""One organism's parameters and its carbon balance at a heliocentric distance.

Calibration rule (spec): presets are calibrated ONLY through r_d so that leaf-level
compensation irradiance lands inside the published gate at the default k.
Never adjust a_max, k, or light physics to pass a gate.
"""
from __future__ import annotations

from dataclasses import dataclass

from sim.physiology import (
    T_REF_K, crossover_distance, gross_assimilation, irradiance, respiration,
)


@dataclass(frozen=True)
class Organism:
    cls: str
    a_max: float            # µmol CO2 m⁻² s⁻¹, light-saturated gross assimilation
    k: float                # µmol photons m⁻² s⁻¹, half-saturation irradiance
    r_d: float              # µmol CO2 m⁻² s⁻¹, leaf dark respiration at t_ref
    leaf_mass_ratio: float  # fraction of organism mass that is photosynthetic, (0, 1]
    t_set: float = T_REF_K  # K, tissue temperature set-point (fixed in v1)

    def __post_init__(self):
        if self.a_max <= 0:
            raise ValueError(f"a_max must be > 0, got {self.a_max}")
        if self.k <= 0:
            raise ValueError(f"k must be > 0, got {self.k}")
        if self.r_d < 0:
            raise ValueError(f"r_d must be >= 0, got {self.r_d}")
        if not (0 < self.leaf_mass_ratio <= 1):
            raise ValueError(f"leaf_mass_ratio must be in (0, 1], got {self.leaf_mass_ratio}")
        if self.t_set <= 0:
            raise ValueError(f"t_set must be > 0 K, got {self.t_set}")

    def leaf_respiration(self) -> float:
        """Dark respiration per unit photosynthetic area at t_set."""
        return respiration(self.r_d, self.t_set)

    def organism_respiration(self) -> float:
        """Whole-organism respiration expressed per unit photosynthetic area.
        Non-photosynthetic mass respires at the same mass-specific rate but
        does not assimilate, so dividing by leaf_mass_ratio scales it up."""
        return self.leaf_respiration() / self.leaf_mass_ratio

    def net_carbon(self, r_au: float, k: float | None = None) -> float:
        """Net carbon per unit photosynthetic area at distance r_au."""
        kk = self.k if k is None else k
        return gross_assimilation(irradiance(r_au), self.a_max, kk) - self.organism_respiration()


def compensation_irradiance(org: Organism, k: float | None = None) -> float:
    """Leaf-level compensation irradiance: gross(I) = leaf respiration.
    Closed form of a_max*I/(I+k) = R  ->  I = k*R/(a_max - R)."""
    r = org.leaf_respiration()
    kk = org.k if k is None else k
    if r >= org.a_max:
        raise ValueError(f"leaf respiration {r} >= a_max {org.a_max}: no compensation point")
    return kk * r / (org.a_max - r)


def crossover_distance_for(org: Organism, k: float | None = None,
                           r_min: float = 0.5, r_max: float = 100.0) -> float:
    """Distance where whole-organism net carbon crosses zero."""
    return crossover_distance(lambda r: org.net_carbon(r, k=k), r_min=r_min, r_max=r_max)


# Presets. a_max and k are stated assumptions (k is swept in the experiment);
# r_d is the calibration knob. Values recorded in experiments/q1_crossover/prereg.yaml.
VASCULAR = Organism("vascular", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
ALGAL = Organism("algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=0.8)
PRESETS = {VASCULAR.cls: VASCULAR, ALGAL.cls: ALGAL}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest tests/test_organism.py -v`
Expected: 11 passed. If a calibration gate fails, the ONLY permitted change is `r_d` of that preset; recompute with `I_c = k*r_d/(a_max - r_d)` and record the new value in Task 4's `prereg.yaml`.

- [ ] **Step 5: Commit**

```bash
git add sim/organism.py tests/test_organism.py
git commit -m "feat(sim): Organism dataclass, compensation solver, calibrated presets

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```

---

### Task 3: Crossover controls

**Files:**
- Test: `tests/test_crossover.py`

**Interfaces:**
- Consumes: `sim.organism.VASCULAR`, `ALGAL`, `Organism`, `crossover_distance_for`; `sim.physiology.crossover_distance`.
- Produces: nothing new; this task proves the root-finder can fail for the stated reasons.

- [ ] **Step 1: Write the tests**

`tests/test_crossover.py`:
```python
import pytest

from sim.organism import ALGAL, VASCULAR, Organism, crossover_distance_for
from sim.physiology import crossover_distance


def _with_rd(org, r_d):
    return Organism(org.cls, a_max=org.a_max, k=org.k, r_d=r_d,
                    leaf_mass_ratio=org.leaf_mass_ratio, t_set=org.t_set)


def test_crossover_exists_and_net_is_zero_there():
    for org in (VASCULAR, ALGAL):
        r_star = crossover_distance_for(org)
        assert 0.5 < r_star < 100.0
        assert org.net_carbon(r_star) == pytest.approx(0.0, abs=1e-6)
        # sign check either side
        assert org.net_carbon(r_star * 0.9) > 0
        assert org.net_carbon(r_star * 1.1) < 0


def test_zero_respiration_has_no_crossover_while_baseline_does():
    assert crossover_distance_for(VASCULAR) > 0          # positive control
    with pytest.raises(ValueError, match="no sign change"):
        crossover_distance_for(_with_rd(VASCULAR, 0.0))   # negative


def test_doubling_respiration_moves_crossover_inward():
    base = crossover_distance_for(VASCULAR)
    hot = crossover_distance_for(_with_rd(VASCULAR, 2 * VASCULAR.r_d))
    assert hot < base


def test_larger_k_moves_crossover_inward():
    base = crossover_distance_for(VASCULAR)
    assert crossover_distance_for(VASCULAR, k=2 * VASCULAR.k) < base
    assert crossover_distance_for(VASCULAR, k=0.5 * VASCULAR.k) > base


def test_generic_root_finder_on_known_function():
    # net = 4 - r  => root at 4
    assert crossover_distance(lambda r: 4.0 - r, r_min=0.5, r_max=100.0) == pytest.approx(4.0, abs=1e-5)
    with pytest.raises(ValueError, match="no sign change"):
        crossover_distance(lambda r: 1.0, r_min=0.5, r_max=100.0)
    with pytest.raises(ValueError, match="r_min"):
        crossover_distance(lambda r: 4.0 - r, r_min=10.0, r_max=1.0)
```

- [ ] **Step 2: Run tests to verify they pass** (this task only adds tests over Task 1-2 code; if any fails, the earlier task's code is wrong, fix there)

Run: `python3 -m pytest tests/ -v`
Expected: 24 passed

- [ ] **Step 3: Commit**

```bash
git add tests/test_crossover.py
git commit -m "test(sim): crossover controls (no-respiration raises, 2x R_d inward, k sensitivity)

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```

---

### Task 4: Pre-registration file and runner

**Files:**
- Create: `experiments/q1_crossover/prereg.yaml`, `experiments/q1_crossover/run.py`
- Delete: `experiments/.gitkeep`
- Test: `tests/test_runner.py`

**Interfaces:**
- Consumes: `sim.organism.Organism`, `compensation_irradiance`, `crossover_distance_for`; `sim.physiology` constants.
- Produces: `run.main(argv: list[str] | None) -> int` (0 pass, 2 gate fail); CSVs `calibration.csv`, `sweep.csv`, `crossover.csv` in `--out` dir, each starting with `#`-prefixed provenance lines. Column names: calibration `class,k,observed_umol,gate_lo,gate_hi,passed`; sweep `class,k,r_au,net_carbon`; crossover `class,k,r_star_au,pred_lo,pred_hi,inside`.

- [ ] **Step 1: Write the pre-registration file**

`experiments/q1_crossover/prereg.yaml`:
```yaml
# Q1 pre-registration. Written BEFORE the sweep runs. Do not edit after run.py has produced crossover.csv.
registered: 2026-09-02
question: >
  For a single organism of photosystem class C, with tissue temperature held at a
  set-point, at what heliocentric distance r* does whole-organism net carbon
  assimilation cross zero?
spec: docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md
grounding: docs/prior_art_2026-09-01.md

# Must match sim/physiology.py constants; run.py refuses to run on mismatch.
assumptions:
  tsi_w_m2: 1360.8        # Kopp & Lean 2011, 10.1029/2010GL045777
  par_fraction: 0.45      # assumption
  photons_per_j: 4.57     # assumption
  t_ref_k: 293.0
  q10: 2.0                # assumption
  t_set_k: 293.0          # v1: tissue temperature fixed; heating cost is v2

presets:
  vascular:
    a_max: 10.0
    k: 100.0
    r_d: 0.65               # calibration knob; gives I_c = 100*0.65/9.35 = 6.95
    leaf_mass_ratio: 0.5    # assumption: half the mass is photosynthetic
    gate_umol: [5.3, 9.0]   # Craine & Reich 2005, 10.1111/j.1469-8137.2005.01420.x
    k_grid: [50.0, 100.0, 200.0]
    predicted_r_star_au: [12.0, 22.0]
  algal:
    a_max: 10.0
    k: 20.0
    r_d: 0.24               # calibration knob; gives I_c = 20*0.24/9.76 = 0.49
    leaf_mass_ratio: 0.8    # assumption: thallus mostly photosynthetic
    gate_umol: [0.0, 1.0]   # Richardson 1983, 10.1111/j.1469-8137.1983.tb03422.x
    k_grid: [10.0, 20.0, 40.0]
    predicted_r_star_au: [35.0, 55.0]

sweep:
  r_min_au: 0.5
  r_max_au: 100.0
  n_grid: 200
```

Note: if Task 2 changed an `r_d`, put the changed value here now, before any run.

- [ ] **Step 2: Write the failing runner tests**

`tests/test_runner.py`:
```python
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


def test_gate_failure_exits_2_and_writes_no_crossover(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"]["vascular"]["r_d"] = 3.0   # I_c = 100*3/7 = 42.9, outside [5.3, 9.0]
    bad_path = tmp_path / "prereg_bad.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    out = tmp_path / "out_bad"
    rc = run.main(["--prereg", str(bad_path), "--out", str(out)])
    assert rc == 2
    assert (out / "calibration.csv").exists()
    assert not (out / "crossover.csv").exists()
    assert not (out / "sweep.csv").exists()
    _, body = _read_header_and_rows(out / "calibration.csv")
    assert any(",False" in l for l in body[1:])


def test_real_prereg_passes_and_writes_all_csvs_with_provenance(tmp_path):
    out = tmp_path / "out_ok"
    rc = run.main(["--prereg", str(PREREG), "--out", str(out)])
    assert rc == 0
    for name in ("calibration.csv", "sweep.csv", "crossover.csv"):
        header, body = _read_header_and_rows(out / name)
        assert any(l.startswith("# git_sha=") for l in header), name
        assert any(l.startswith("# physiology_md5=") for l in header), name
        assert any(l.startswith("# prereg_md5=") for l in header), name
        assert len(body) >= 2, name
    _, cross = _read_header_and_rows(out / "crossover.csv")
    assert cross[0] == "class,k,r_star_au,pred_lo,pred_hi,inside"
    assert len(cross) == 1 + 3 + 3   # header + 3 k values per preset


def test_assumption_mismatch_refuses_to_run(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["assumptions"]["par_fraction"] = 0.5
    bad_path = tmp_path / "prereg_drift.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    import pytest
    with pytest.raises(ValueError, match="par_fraction"):
        run.main(["--prereg", str(bad_path), "--out", str(tmp_path / "o")])


def test_cli_exit_code_on_gate_failure(tmp_path):
    bad = yaml.safe_load(PREREG.read_text())
    bad["presets"]["algal"]["r_d"] = 5.0
    bad_path = tmp_path / "p.yaml"
    bad_path.write_text(yaml.safe_dump(bad))
    proc = subprocess.run(
        [sys.executable, str(RUN), "--prereg", str(bad_path), "--out", str(tmp_path / "o")],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 2, proc.stdout + proc.stderr
    assert "GATE FAILED" in proc.stdout
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python3 -m pytest tests/test_runner.py -v`
Expected: collection error `ModuleNotFoundError: No module named 'run'`

- [ ] **Step 4: Write the runner**

`experiments/q1_crossover/run.py`:
```python
#!/usr/bin/env python3
"""Q1 runner: calibration gate, then distance sweep, then provenance-stamped CSVs.

Exit codes: 0 = gate passed and sweep written; 2 = gate failed (calibration.csv
written, nothing else). Any other error propagates as an exception.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import subprocess
import sys
from pathlib import Path

import numpy as np
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from sim import physiology  # noqa: E402
from sim.organism import Organism, compensation_irradiance, crossover_distance_for  # noqa: E402

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
    }
    for key, code_value in pairs.items():
        if not np.isclose(a[key], code_value):
            raise ValueError(
                f"prereg assumption {key}={a[key]} does not match sim/physiology.py {key}={code_value}"
            )


def build(name: str, p: dict, t_set: float) -> Organism:
    return Organism(name, a_max=p["a_max"], k=p["k"], r_d=p["r_d"],
                    leaf_mass_ratio=p["leaf_mass_ratio"], t_set=t_set)


def _md5(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()


def provenance_lines(prereg_path: Path) -> list[str]:
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
                         capture_output=True, text=True).stdout.strip()
    return [
        f"# git_sha={sha}",
        f"# physiology_md5={_md5(PHYSIOLOGY_PATH)}",
        f"# prereg_md5={_md5(prereg_path)}",
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


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--prereg", type=Path, default=Path(__file__).with_name("prereg.yaml"))
    ap.add_argument("--out", type=Path, default=Path(__file__).parent)
    args = ap.parse_args(argv)

    prereg = load_prereg(args.prereg)
    assert_assumptions_match(prereg)
    t_set = float(prereg["assumptions"]["t_set_k"])
    args.out.mkdir(parents=True, exist_ok=True)
    header = provenance_lines(args.prereg)

    # 1. calibration gate at default k
    cal_rows, all_pass = [], True
    orgs: dict[str, Organism] = {}
    for name, p in prereg["presets"].items():
        org = build(name, p, t_set)
        orgs[name] = org
        obs = compensation_irradiance(org)
        lo, hi = (float(x) for x in p["gate_umol"])
        passed = lo <= obs <= hi
        all_pass &= passed
        cal_rows.append({"class": name, "k": org.k, "observed_umol": f"{obs:.4f}",
                         "gate_lo": lo, "gate_hi": hi, "passed": passed})
    write_csv(args.out / "calibration.csv", header,
              ["class", "k", "observed_umol", "gate_lo", "gate_hi", "passed"], cal_rows)
    for r in cal_rows:
        print(f"calibration {r['class']}: I_c={r['observed_umol']} gate=[{r['gate_lo']}, {r['gate_hi']}] "
              f"{'pass' if r['passed'] else 'FAIL'}")
    if not all_pass:
        print("GATE FAILED: crossover not reported. Fix r_d only, re-register, re-run.")
        return 2

    # 2. sweep
    sw = prereg["sweep"]
    grid = np.geomspace(float(sw["r_min_au"]), float(sw["r_max_au"]), int(sw["n_grid"]))
    sweep_rows, cross_rows = [], []
    for name, p in prereg["presets"].items():
        org = orgs[name]
        plo, phi = (float(x) for x in p["predicted_r_star_au"])
        for k in p["k_grid"]:
            k = float(k)
            for r in grid:
                sweep_rows.append({"class": name, "k": k, "r_au": f"{r:.6g}",
                                   "net_carbon": f"{org.net_carbon(float(r), k=k):.6g}"})
            r_star = crossover_distance_for(org, k=k, r_min=float(sw["r_min_au"]), r_max=float(sw["r_max_au"]))
            inside = plo <= r_star <= phi
            cross_rows.append({"class": name, "k": k, "r_star_au": f"{r_star:.4f}",
                               "pred_lo": plo, "pred_hi": phi, "inside": inside})
            print(f"crossover {name} k={k:g}: r*={r_star:.2f} AU predicted=[{plo:g}, {phi:g}] "
                  f"{'inside' if inside else 'OUTSIDE'}")
    write_csv(args.out / "sweep.csv", header, ["class", "k", "r_au", "net_carbon"], sweep_rows)
    write_csv(args.out / "crossover.csv", header,
              ["class", "k", "r_star_au", "pred_lo", "pred_hi", "inside"], cross_rows)
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

Then: `chmod +x experiments/q1_crossover/run.py; git rm -q experiments/.gitkeep`

- [ ] **Step 5: Run tests to verify they pass**

Run: `python3 -m pytest tests/ -v`
Expected: 28 passed

- [ ] **Step 6: Commit (prereg + runner + tests; NO CSV outputs yet)**

```bash
git add experiments/q1_crossover/prereg.yaml experiments/q1_crossover/run.py tests/test_runner.py
git commit -m "feat(q1): pre-registration and gated sweep runner with provenance headers

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```

---

### Task 5: House theme and plots

**Files:**
- Create: `docs/analysis/theme.R`, `experiments/q1_crossover/plot.R`
- Test: shell check that `Rscript plot.R` exits 0 and produces two PNGs (no pytest for R)

**Interfaces:**
- Consumes: `sweep.csv` (`class,k,r_au,net_carbon`) and `crossover.csv` (`class,k,r_star_au,pred_lo,pred_hi,inside`) with `#` comment headers.
- Produces: `experiments/q1_crossover/figures/net_carbon_vs_distance.png`, `experiments/q1_crossover/figures/crossover_vs_k.png`; `theme_dyson()`, `scale_colour_dyson()` for future scripts.

- [ ] **Step 1: Write the house theme**

`docs/analysis/theme.R`:
```r
# House ggplot2 theme for dyson-tree. EVERY plot script sources this file.
# Restyle here, never inline in a plot script.
suppressPackageStartupMessages(library(ggplot2))

palette_dyson <- c(vascular = "#2E7D32", algal = "#1565C0")

theme_dyson <- function(base_size = 12) {
  theme_minimal(base_size = base_size) +
    theme(
      panel.grid.minor = element_blank(),
      plot.title.position = "plot",
      legend.position = "bottom",
      strip.text = element_text(face = "bold")
    )
}

scale_colour_dyson <- function(...) scale_colour_manual(values = palette_dyson, ...)
scale_fill_dyson <- function(...) scale_fill_manual(values = palette_dyson, ...)
```

- [ ] **Step 2: Write the plot script**

`experiments/q1_crossover/plot.R`:
```r
#!/usr/bin/env Rscript
# Two figures from the Q1 CSVs. One graph per figure. Reads CSVs only.
args <- commandArgs(trailingOnly = TRUE)
here <- normalizePath(dirname(sub("--file=", "", grep("--file=", commandArgs(), value = TRUE))))
in_dir <- if (length(args) >= 1) args[1] else here
repo <- normalizePath(file.path(here, "..", ".."))
source(file.path(repo, "docs", "analysis", "theme.R"))

sweep <- read.csv(file.path(in_dir, "sweep.csv"), comment.char = "#")
cross <- read.csv(file.path(in_dir, "crossover.csv"), comment.char = "#")
stopifnot(nrow(sweep) > 0, nrow(cross) > 0)
sweep$k <- factor(sweep$k)
cross$k <- as.numeric(cross$k)
fig_dir <- file.path(in_dir, "figures")
dir.create(fig_dir, showWarnings = FALSE)

# Figure 1: net carbon vs distance, per class, k as linetype
p1 <- ggplot(sweep, aes(r_au, net_carbon, colour = class, linetype = k)) +
  geom_hline(yintercept = 0, colour = "grey40") +
  geom_line() +
  scale_x_log10() +
  coord_cartesian(ylim = c(-2, 5)) +
  scale_colour_dyson() +
  labs(x = "heliocentric distance (AU, log)",
       y = expression(net~carbon~(mu*mol~m^-2~s^-1)),
       linetype = "k (half-saturation)",
       title = "Q1: whole-organism net carbon vs distance") +
  theme_dyson()
ggsave(file.path(fig_dir, "net_carbon_vs_distance.png"), p1, width = 6, height = 4, dpi = 150)

# Figure 2: crossover distance vs k, with the pre-registered band per class
band <- unique(cross[, c("class", "pred_lo", "pred_hi")])
p2 <- ggplot() +
  geom_rect(data = band, aes(xmin = -Inf, xmax = Inf, ymin = pred_lo, ymax = pred_hi, fill = class), alpha = 0.15) +
  geom_point(data = cross, aes(k, r_star_au, colour = class), size = 2.5) +
  geom_line(data = cross, aes(k, r_star_au, colour = class)) +
  scale_x_log10() +
  scale_colour_dyson() + scale_fill_dyson() +
  labs(x = "k, half-saturation irradiance (log)", y = "crossover distance r* (AU)",
       title = "Q1: crossover distance vs k; band = pre-registered prediction") +
  theme_dyson()
ggsave(file.path(fig_dir, "crossover_vs_k.png"), p2, width = 6, height = 4, dpi = 150)
cat("wrote", fig_dir, "\n")
```

- [ ] **Step 3: Produce test CSVs in a temp dir and run the plot script against them**

```bash
python3 experiments/q1_crossover/run.py --out ~/scratch/q1_plotcheck && \
Rscript experiments/q1_crossover/plot.R ~/scratch/q1_plotcheck && \
ls -la ~/scratch/q1_plotcheck/figures/
```
Expected: exit 0, two PNGs listed. If R errors on `expression(...)` axis label, replace with the plain string `"net carbon (umol m-2 s-1)"`.

- [ ] **Step 4: Open the figures for the user** (the user cannot see inline images)

```bash
cp ~/scratch/q1_plotcheck/figures/*.png /mnt/c/Users/<windows-user>/Downloads/ && \
cmd.exe /c start /mnt/c/Users/<windows-user>/Downloads/net_carbon_vs_distance.png
```

- [ ] **Step 5: Commit**

```bash
git add docs/analysis/theme.R experiments/q1_crossover/plot.R
git commit -m "feat(q1): house ggplot2 theme and two-figure plot script

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```

---

### Task 6: Run the registered experiment, record results, update roadmap

**Files:**
- Create: `experiments/q1_crossover/calibration.csv`, `sweep.csv`, `crossover.csv`, `figures/*.png`, `experiments/q1_crossover/RESULTS.md`
- Modify: `docs/ROADMAP.md` (spine item 1 text; three checklist items)

**Interfaces:**
- Consumes: everything above.
- Produces: the measured answer to Q1, committed with provenance.

- [ ] **Step 1: Confirm the tree is clean and the prereg is committed BEFORE running**

```bash
git status --porcelain   # must be empty
git log --oneline -1 -- experiments/q1_crossover/prereg.yaml   # must show a commit
```

- [ ] **Step 2: Run the experiment in place and the plots**

```bash
python3 experiments/q1_crossover/run.py && Rscript experiments/q1_crossover/plot.R
echo "exit=$?"; head -6 experiments/q1_crossover/crossover.csv
```
Expected: exit 0, calibration lines both `pass`, six crossover lines. **If the gate fails, stop and report; do not edit anything to make it pass.**

- [ ] **Step 3: Write RESULTS.md from the CSVs (copy numbers, do not retype from memory)**

`experiments/q1_crossover/RESULTS.md` skeleton; fill every `<...>` from `calibration.csv` and `crossover.csv`:
```markdown
# Q1 results — <date from CSV header>

Provenance: git_sha=<from header>, physiology_md5=<from header>, prereg_md5=<from header>.

## Calibration gate

| class | k | observed I_c (µmol) | gate | pass |
|---|---|---|---|---|
| vascular | 100 | <observed> | [5.3, 9.0] | <True/False> |
| algal | 20 | <observed> | [0.0, 1.0] | <True/False> |

## Crossover distance r* (AU) vs pre-registered prediction

| class | k | r* | predicted | inside |
|---|---|---|---|---|
| vascular | 50 | <r*> | [12, 22] | <> |
| vascular | 100 | <r*> | [12, 22] | <> |
| vascular | 200 | <r*> | [12, 22] | <> |
| algal | 10 | <r*> | [35, 55] | <> |
| algal | 20 | <r*> | [35, 55] | <> |
| algal | 40 | <r*> | [35, 55] | <> |

## Verdict

State, per class, whether the default-k prediction held, verbatim from the `inside` column. State which k values fall outside the band. No re-tuning was performed after the run.

## Figures

- `figures/net_carbon_vs_distance.png`
- `figures/crossover_vs_k.png`

## What this does and does not show

Light-only, tissue temperature fixed at 293 K. The heating cost (v2) can only move r* inward. Pressure and element budgets are not modelled.
```

- [ ] **Step 4: Open both figures for the user**

```bash
cp experiments/q1_crossover/figures/*.png /mnt/c/Users/<windows-user>/Downloads/ && \
cmd.exe /c start /mnt/c/Users/<windows-user>/Downloads/crossover_vs_k.png
```

- [ ] **Step 5: Update the roadmap** (Iron Law: `cat docs/ROADMAP.md` first; the strings below are from the live file at commit 9772d9e)

Replace spine item 1:
```
1. **Cometary element budget** — CHON-rich, P/K/metal-poor. The scarce elements
   are the design constraint; get the composition from a real measurement, not
   from a plausible-sounding ratio.
```
with:
```
1. **Cometary element budget** — organic-C-rich (~50% by mass), refractory
   fraction near-CI-chondritic, Ca-depleted; P present, K unmeasured
   (`docs/prior_art_2026-09-01.md` §3). Element scarcity is NOT a free
   constraint; not modelled in Q1.
```

Replace checklist lines:
```
- [ ] Brainstorm the design (`superpowers:brainstorming`, then `deep-sim-design`)
- [ ] Settle designer-loop vs colony-loop and record WHY
```
with:
```
- [x] Brainstorm the design — 2026-09-02, spec at
      `docs/superpowers/specs/2026-09-02-q1-carbon-crossover-design.md`
- [x] Settle designer-loop vs colony-loop — A first (2026-09-02). WHY: B needs
      A's budget trusted underneath it; A is the cheapest path to a measured
      answer, and light (spine item 3) turned out to be the binding constraint,
      which A can treat as a swept input.
```
and:
```
- [ ] First registered question + pre-registration, before any runner exists
```
with:
```
- [x] First registered question (Q1, carbon crossover vs distance) —
      `experiments/q1_crossover/prereg.yaml`, results in `RESULTS.md`
- [ ] Q2 (declared): carbon cost of holding tissue temperature against
      radiative loss; second crossover
```
Leave the `bio-grounding` line unticked: spine items 1 and 2 are grounded in the survey but only item 3 has a number in a model.

- [ ] **Step 6: Run the full suite one last time, then commit everything**

```bash
python3 -m pytest tests/ -q
git add experiments/q1_crossover/ docs/ROADMAP.md
git commit -m "exp(q1): run registered carbon-crossover sweep; record results; roadmap

Claude-Session: https://claude.ai/code/session_01JCjkg29wRHsrygFNa2Q68M"
```
Expected: 28 passed; commit lands. Do not push unless asked.

---

## Self-review (done at plan-writing time)

- **Spec coverage:** irradiance/gross/respiration/Organism/compensation/crossover → Tasks 1-2; presets calibrated via r_d → Task 2; gate-then-sweep runner with provenance and exit-2 → Task 4; K sweep → prereg `k_grid` + runner; theme.R + two one-graph figures → Task 5; tests split by what they can fail on, controls paired with positive path → Tasks 1-4; fail-loud errors → every function; out-of-scope list → RESULTS.md closing section. Gap: none found.
- **Placeholders:** RESULTS.md `<...>` slots are deliberate copy-from-CSV fields, not plan placeholders.
- **Type consistency:** `Organism(cls, a_max, k, r_d, leaf_mass_ratio, t_set)` used identically in Tasks 2, 3, 4; `compensation_irradiance(org, k=None)`; `crossover_distance_for(org, k=None, r_min, r_max)`; `crossover_distance(net_fn, r_min, r_max, n_grid)`; `run.main(argv) -> int`; CSV columns identical between Task 4 runner, Task 4 tests, and Task 5 plot.R.
