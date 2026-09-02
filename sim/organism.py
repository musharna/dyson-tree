"""One organism's parameters and its carbon balance at a heliocentric distance.

Calibration rule (spec): presets are calibrated ONLY through r_d so that leaf-level
compensation irradiance lands inside the published gate at the default k.
Never adjust a_max, k, or light physics to pass a gate.
"""

from __future__ import annotations

from dataclasses import dataclass

from sim.physiology import (
    T_REF_K,
    crossover_distance,
    gross_assimilation,
    irradiance,
    respiration,
)


@dataclass(frozen=True)
class Organism:
    cls: str
    a_max: float  # µmol CO2 m⁻² s⁻¹, light-saturated gross assimilation
    k: float  # µmol photons m⁻² s⁻¹, half-saturation irradiance
    r_d: float  # µmol CO2 m⁻² s⁻¹, leaf dark respiration at t_ref
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
            raise ValueError(
                f"leaf_mass_ratio must be in (0, 1], got {self.leaf_mass_ratio}"
            )
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
        return (
            gross_assimilation(irradiance(r_au), self.a_max, kk)
            - self.organism_respiration()
        )


def compensation_irradiance(org: Organism, k: float | None = None) -> float:
    """Leaf-level compensation irradiance: gross(I) = leaf respiration.
    Closed form of a_max*I/(I+k) = R  ->  I = k*R/(a_max - R)."""
    r = org.leaf_respiration()
    kk = org.k if k is None else k
    if r >= org.a_max:
        raise ValueError(
            f"leaf respiration {r} >= a_max {org.a_max}: no compensation point"
        )
    return kk * r / (org.a_max - r)


def crossover_distance_for(
    org: Organism, k: float | None = None, r_min: float = 0.5, r_max: float = 100.0
) -> float:
    """Distance where whole-organism net carbon crosses zero."""
    return crossover_distance(
        lambda r: org.net_carbon(r, k=k), r_min=r_min, r_max=r_max
    )


# Presets. a_max and k are stated assumptions (k is swept in the experiment);
# r_d is the calibration knob. Values recorded in experiments/q1_crossover/prereg.yaml.
VASCULAR = Organism("vascular", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
ALGAL = Organism("algal", a_max=10.0, k=20.0, r_d=0.24, leaf_mass_ratio=0.8)
PRESETS = {VASCULAR.cls: VASCULAR, ALGAL.cls: ALGAL}
