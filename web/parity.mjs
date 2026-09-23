// Recompute every quantity in web/fixtures.json with the JS port and print the
// results as JSON on stdout. This script makes NO pass/fail judgement: it
// reports numbers only. tests/test_parity_js.py owns the comparison, so the
// implementation under test never decides whether it agrees with the reference.
//
// Run: node web/parity.mjs [path/to/fixtures.json]

import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

// model.js is a classic script (it must load from file:// in a browser, where
// ES modules are refused), so node reaches it through require, not import.
const require = createRequire(import.meta.url);
const model = require("./model.js");
const {
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
} = model;

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
for (const name of Object.keys(out.constants)) out.constants[name] = model[name];

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

// ---- the vessel (sim/vessel.py): replay every fixture case by its `call` ----
const V = model;
const ALGAL_V = model.ALGAL;
const reportOut = (rep) => ({
  violated: [...rep.violated],
  first: rep.first,
  sigma_eff: rep.sigma_eff,
  T_int: rep.T_int,
  T_shell: rep.T_shell,
  f_photon: rep.f_photon,
  thin_wall_valid: rep.thin_wall_valid,
  lines: Object.fromEntries(
    Object.entries(rep.lines).map(([n, l]) => [
      n,
      { lhs: l.lhs, rhs: l.rhs, margin: l.margin, violated: l.violated },
    ]),
  ),
});
const edgeOut = (e) => ({
  edge: e.edge,
  binding: e.binding,
  roots: e.roots,
  tie: e.tie,
  bracket: e.bracket,
  counterfactual: e.counterfactual,
});
const RS = [1.0, 1.1, 2.0];

function replay(c) {
  const a = c.args;
  switch (c.call) {
    case "shell_transmission":
      return { T: a.kt.map((k) => V.shellTransmission(k, a.optical_law, a.n_interior)) };
    case "slab_reflectance":
      return { R: a.kt.map((k) => V.slabReflectance(k, a.n_interior)) };
    case "optics_at_t": {
      const inp = V.makeVesselInputs(a.inputs);
      const op = { optical_law: inp.optical_law, n_interior: inp.n_interior };
      const th = { ...op, thermal_reflectance: inp.thermal_reflectance, albedo: inp.albedo, emissivity: inp.emissivity };
      const out = {
        tau_sw: a.t.map((t) => V.solarTransmission(t, op)),
        f_photon: a.t.map((t) => V.parPhotonFraction(t, { ...op, interior: "mixed" })),
      };
      if (inp.optical_law === "shell")
        out.f_photon_central = a.t.map((t) => V.parPhotonFraction(t, { interior: "central" }));
      if (inp.optical_law === "shell+fresnel")
        out.R_slab_sw = a.t.map((t) => V.solarSlabReflectance(t, inp.n_interior));
      const tc = RS.flatMap((r) => a.t.map((t) => V.containedTemperature(r, t, th)));
      out.T_int = tc.map((x) => x[0]);
      out.T_shell = tc.map((x) => x[1]);
      return out;
    }
    case "saturation_pressure":
      return { p: a.T.map((t) => V.saturationPressure(t)) };
    case "self_consistent_pressure":
      return { p: V.selfConsistentPressure(a.r, a.R, a.sigma, a.kw) };
    case "closed_form_control": {
      const p = V.selfConsistentPressure(a.r, a.R, a.sigma, a.kw);
      return { p, R_max: V.closedFormRMax(a.sigma, p, a.k, a.tau_min) };
    }
    case "auto_state":
    case "prereg_example": {
      const s = V.autoState(a.r, a.R, a.sigma, ALGAL_V, a.inputs);
      return { p: s.p, t: s.t, report: reportOut(s.report) };
    }
    case "classify":
      return reportOut(V.classifyFailure(a.p, a.t, a.r, a.R, a.sigma, ALGAL_V, a.inputs));
    case "check_auto_path": {
      const rep = V.classifyFailure(a.p, a.t, a.r, a.R, a.sigma, ALGAL_V, a.inputs);
      try {
        V.checkAutoPath(a.p, a.t, a.r, a.R, a.sigma, ALGAL_V, a.inputs);
        return { raised: null, exit_code: null, report: reportOut(rep) };
      } catch (err) {
        if (!(err instanceof V.RunnerError)) throw err;
        return { raised: err.name, exit_code: err.exit_code, report: reportOut(rep) };
      }
    }
    case "convergence_error":
      try {
        V.selfConsistentPressure(a.r, a.R, a.sigma, { max_iter: a.max_iter });
        return { raised: null };
      } catch (err) {
        if (!(err instanceof V.ConvergenceError)) throw err;
        return { raised: err.name };
      }
    case "same_object":
      try {
        return { material: V.assertSameObject(...a.ids), raised: false };
      } catch (err) {
        return { material: null, raised: true };
      }
    case "find_edge_linear":
      return edgeOut(
        V.findEdge(
          a.nodes,
          (x) => Object.fromEntries(Object.entries(a.lines).map(([k, [c0, c1]]) => [k, c0 + c1 * x])),
          { tie_tol: (p, q) => Math.abs(p - q) <= a.tie_tol, refine_width: () => a.refine_width },
        ),
      );
    case "r_close":
      return edgeOut(V.rClose(a.R, a.sigma, ALGAL_V, a.inputs));
    case "r_window":
      return edgeOut(V.rWindow(a.r, a.sigma, ALGAL_V, a.inputs));
    default:
      throw new Error(`unknown vessel case call in fixtures: ${c.call}`);
  }
}

out.vessel = {
  grid_r_au: [...V.GRID_R_AU],
  grid_r_m: [...V.GRID_R_M],
  spectral_table_sha256: V.spectralTable().data_sha256,
  cases: fx.vessel.cases.map((c) => ({ name: c.name, got: replay(c) })),
};

process.stdout.write(JSON.stringify(out));
