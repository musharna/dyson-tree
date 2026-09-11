// Recompute every quantity in web/fixtures.json with the JS port and print the
// results as JSON on stdout. This script makes NO pass/fail judgement: it
// reports numbers only. tests/test_parity_js.py owns the comparison, so the
// implementation under test never decides whether it agrees with the reference.
//
// Run: node web/parity.mjs [path/to/fixtures.json]

import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

import {
  adaptedOptimum,
  compensationIrradiance,
  crossoverDistanceFor,
  equilibriumTemperature,
  irradiance,
  leafRespiration,
  makeOrganism,
  netCarbon,
  netCarbonAtEquilibrium,
  organismRespiration,
  temperatureResponse,
  temperatureResponseGaussian,
} from "./model.js";

const here = dirname(fileURLToPath(import.meta.url));
const fixturePath = process.argv[2]
  ? resolve(process.argv[2])
  : resolve(here, "fixtures.json");
const fx = JSON.parse(readFileSync(fixturePath, "utf8"));

const grid = fx.grid_au;
const { r_min_au: rMin, r_max_au: rMax, n_grid: nGrid } = fx.registered;

const out = {
  fixture_path: fixturePath,
  fixture_git_sha: fx.provenance.git_sha,
  node: process.version,
  constants: {
    TSI_W_M2: null,
    PAR_FRACTION: null,
    PHOTONS_PER_J: null,
    T_REF_K: null,
    Q10: null,
    SIGMA_W_M2_K4: null,
  },
  cases: {},
  edge_cases: {},
};

// Constants are re-read from the module rather than retyped here.
const mod = await import("./model.js");
for (const name of Object.keys(out.constants)) out.constants[name] = mod[name];

for (const [cls, kase] of Object.entries(fx.cases)) {
  const org = makeOrganism(kase.preset);
  const tEq = grid.map((r) =>
    equilibriumTemperature(r, org.area_ratio, org.emissivity, org.albedo),
  );
  const tOptHome = adaptedOptimum(1.0, org.area_ratio, org.emissivity, org.albedo);
  const perK = {};
  for (const [key, spec] of Object.entries(kase.per_k)) {
    perK[key] = {
      k: spec.k,
      net_carbon: grid.map((r) => netCarbon(org, r, spec.k)),
      compensation_irradiance: compensationIrradiance(org, spec.k),
      crossover_au: crossoverDistanceFor(org, spec.k, rMin, rMax, nGrid),
    };
  }
  out.cases[cls] = {
    leaf_respiration: leafRespiration(org),
    organism_respiration: organismRespiration(org),
    adapted_t_opt_home_1au: tOptHome,
    temperature_response: tEq.map((t) =>
      temperatureResponse(t, org.t_min, org.t_opt),
    ),
    temperature_response_gaussian: tEq.map((t) =>
      temperatureResponseGaussian(t, tOptHome, org.omega),
    ),
    irradiance: grid.map((r) => irradiance(r)),
    equilibrium_temperature: tEq,
    net_carbon_at_equilibrium: grid.map((r) => netCarbonAtEquilibrium(org, r)),
    per_k: perK,
  };
}

for (const edge of fx.edge_cases) {
  const org = makeOrganism(edge.preset);
  if (edge.name === "no_crossover_in_window") {
    out.edge_cases[edge.name] = {
      crossover_au: crossoverDistanceFor(
        org,
        edge.k,
        edge.r_min_au,
        edge.r_max_au,
        edge.n_grid,
      ),
      net_carbon_at_r_max: netCarbon(org, edge.r_max_au, edge.k),
    };
  } else if (edge.name === "compensation_at_respiration_boundary") {
    let raised = null;
    let value = null;
    try {
      value = compensationIrradiance(org);
    } catch (err) {
      raised = err.message;
    }
    out.edge_cases[edge.name] = { raised, value };
  } else if (edge.name === "algal_t_min_floor") {
    out.edge_cases[edge.name] = {
      samples: edge.samples.map((s) => {
        const t = equilibriumTemperature(
          s.r_au,
          org.area_ratio,
          org.emissivity,
          org.albedo,
        );
        return {
          label: s.label,
          r_au: s.r_au,
          t_eq: t,
          temperature_response: temperatureResponse(t, org.t_min, org.t_opt),
          net_carbon_at_equilibrium: netCarbonAtEquilibrium(org, s.r_au),
        };
      }),
    };
  } else {
    throw new Error(`unknown edge case in fixtures: ${edge.name}`);
  }
}

process.stdout.write(JSON.stringify(out));
