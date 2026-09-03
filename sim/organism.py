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
from sim.thermal import (
    adapted_optimum,
    equilibrium_temperature,
    temperature_response,
    temperature_response_gaussian,
)


@dataclass(frozen=True)
class Organism:
    cls: str
    a_max: float  # µmol CO2 m⁻² s⁻¹, light-saturated gross assimilation
    k: float  # µmol photons m⁻² s⁻¹, half-saturation irradiance
    r_d: float  # µmol CO2 m⁻² s⁻¹, leaf dark respiration at t_ref
    leaf_mass_ratio: float  # fraction of organism mass that is photosynthetic, (0, 1]
    t_set: float = T_REF_K  # K, tissue temperature set-point (fixed in v1)
    area_ratio: float = 2.0  # radiating area / projected area: 2 lamina, 4 sphere
    t_min: float = 265.15  # K, photosynthesis floor
    t_opt: float = 298.15  # K, response optimum (declared assumption, not grounded)
    emissivity: float = 1.0  # declared assumption
    albedo: float = 0.0  # declared assumption
    omega: float = 20.0  # K, Gaussian width; DECLARED ASSUMPTION, not grounded

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
        if self.omega <= 0:
            raise ValueError(f"omega must be > 0, got {self.omega}")

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

    def net_carbon_at_equilibrium(self, r_au: float, k: float | None = None) -> float:
        """Net carbon for a PASSIVE organism whose temperature follows radiative
        equilibrium at r_au. Both terms move with distance: assimilation is scaled
        by the temperature response, and respiration is evaluated at the
        equilibrium temperature rather than at a fixed set-point.

        net_carbon() is the Q1 path and is deliberately left untouched: making it
        temperature-dependent would change Q1's committed numbers."""
        kk = self.k if k is None else k
        t = equilibrium_temperature(r_au, self.area_ratio, self.emissivity, self.albedo)
        f = temperature_response(t, self.t_min, self.t_opt)
        gross = gross_assimilation(irradiance(r_au), self.a_max, kk) * f
        return gross - respiration(self.r_d, t) / self.leaf_mass_ratio

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
    org: Organism,
    k: float | None = None,
    r_min: float = 0.5,
    r_max: float = 100.0,
    n_grid: int = 400,
) -> float:
    """Distance where whole-organism net carbon crosses zero.

    n_grid is the bracketing grid for the root search. The runner passes the
    pre-registration's declared `sweep.n_grid` so the number reported in
    crossover.csv comes from the grid the pre-registration names, rather than
    from a second, hidden default."""
    return crossover_distance(
        lambda r: org.net_carbon(r, k=k), r_min=r_min, r_max=r_max, n_grid=n_grid
    )


# Presets. a_max and k are stated assumptions (k is swept in the experiment);
# r_d is the calibration knob. Values recorded in experiments/q1_crossover/prereg.yaml.
# area_ratio and t_min are Q2-only fields (net_carbon(), which Q1 uses, reads
# neither); ALGAL declares them explicitly as a sphere with the Pointing et al.
# 2015 algal floor (254.65 K), matching experiments/q2_thermal/prereg.yaml's
# algal preset (area_ratio: 4.0, t_min_grid middle value), rather than
# silently inheriting VASCULAR's lamina defaults.
VASCULAR = Organism("vascular", a_max=10.0, k=100.0, r_d=0.65, leaf_mass_ratio=0.5)
ALGAL = Organism(
    "algal",
    a_max=10.0,
    k=20.0,
    r_d=0.24,
    leaf_mass_ratio=0.8,
    area_ratio=4.0,
    t_min=254.65,
)
PRESETS = {VASCULAR.cls: VASCULAR, ALGAL.cls: ALGAL}
