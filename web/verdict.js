// The vessel's verdict panel (northstar M2, spec §4, §5): seven inputs, one line per
// inequality. All arithmetic is DysonModel's (web/model.js); this file resolves the
// (p, t) mode (§5's table), calls the model and prints. Classic script, like app.js.
//
// Speed: classifyFailure and the fixed point are milliseconds, so the five lines update on
// every input. The two edge searches (rClose, rWindow) cost ~0.5-2.5 s each; they run
// debounced after input stops, and are cached on the inputs they actually depend on
// (rClose ignores r, rWindow ignores R).
(function () {
  "use strict";

  var M = window.DysonModel;
  var $ = function (id) {
    var e = document.getElementById(id);
    if (!e) throw new Error("verdict panel: missing #" + id);
    return e;
  };

  // Registered P2 band, copied from experiments/q4_vessel/prereg.yaml (tests pin it).
  var P2 = { band_km: [60, 300], r_au: 1.1, sigma_MPa: 0.7 };
  var EDGE_DEBOUNCE_MS = 300;

  // Control defaults (§5). Log sliders carry log10 of the value.
  var DEFAULTS = {
    "v-R": "3", // log10 m: 1 km
    "v-t-mode": "auto",
    "v-t": "0", // log10 m, used when manual
    "v-p-mode": "auto",
    "v-p": "3", // log10 Pa, used when manual
    "v-r": "1.10",
    "v-sigma": "0.7",
    "v-org": "algal",
    "v-wall": "ice",
    "v-albedo": String(M.VESSEL_DEFAULTS.albedo),
    "v-emissivity": String(M.VESSEL_DEFAULTS.emissivity),
    "v-topt": String(M.VESSEL_DEFAULTS.t_opt_K),
    "v-omega": String(M.VESSEL_DEFAULTS.omega_K),
    "v-ffloor": String(M.VESSEL_DEFAULTS.f_floor),
    "v-dust": "none",
    "v-interior": "mixed",
    "v-fresnel": "off",
    "v-ninterior": "vapour",
  };
  var FRESNEL = {
    off: { optical_law: "shell", thermal_reflectance: "0" },
    optics: { optical_law: "shell+fresnel", thermal_reflectance: "0" },
    "optics+thermal": {
      optical_law: "shell+fresnel",
      thermal_reflectance: "slab",
    },
  };
  var UNITS = {
    BURST: "Pa",
    FREEZE: "K",
    BOIL: "Pa",
    STARVE: "µmol m⁻² s⁻¹",
    OPAQUE: "",
  };

  function fmt(x, d) {
    if (!isFinite(x)) return String(x);
    var a = Math.abs(x);
    if (a !== 0 && (a >= 1e6 || a < 1e-3))
      return x.toExponential(d === undefined ? 3 : d);
    return x.toFixed(d === undefined ? 3 : d);
  }
  function signed(x, d) {
    return (x >= 0 ? "+" : "−") + fmt(Math.abs(x), d);
  }
  function withUnit(s, u) {
    return u ? s + " " + u : s;
  }

  function read() {
    var v = function (id) {
      return $(id).value;
    };
    var fr = FRESNEL[v("v-fresnel")];
    if (!fr) throw new RangeError("unknown Fresnel setting " + v("v-fresnel"));
    return {
      R: Math.pow(10, Number(v("v-R"))),
      r: Math.round(Number(v("v-r")) * 1000) / 1000,
      sigma: Number(v("v-sigma")) * 1e6,
      org: v("v-org"),
      wall: v("v-wall"),
      tMode: v("v-t-mode"),
      t: Math.pow(10, Number(v("v-t"))),
      pMode: v("v-p-mode"),
      p: Math.pow(10, Number(v("v-p"))),
      inputs: {
        albedo: Number(v("v-albedo")),
        emissivity: Number(v("v-emissivity")),
        t_opt_K: Number(v("v-topt")),
        omega_K: Number(v("v-omega")),
        f_floor: Number(v("v-ffloor")),
        dust: v("v-dust"),
        interior: v("v-interior"),
        optical_law: fr.optical_law,
        thermal_reflectance: fr.thermal_reflectance,
        n_interior: M.N_INTERIOR[v("v-ninterior")],
      },
    };
  }

  // §5's four (p, t) modes. classifyFailure gets the resolved pair only.
  function resolve(s) {
    var inp = M.makeVesselInputs(s.inputs);
    var org = M.PRESETS[s.org];
    if (!org) throw new RangeError("unknown organism class " + s.org);
    if (s.wall !== M.WALL_MATERIAL)
      throw new RangeError("wall material " + s.wall + " is not grounded");
    var th = {
      optical_law: inp.optical_law,
      n_interior: inp.n_interior,
      thermal_reflectance: inp.thermal_reflectance,
      albedo: inp.albedo,
      emissivity: inp.emissivity,
    };
    var pStar = M.selfConsistentPressure(s.r, s.R, s.sigma, th);
    var tMin = M.wallThickness(pStar, s.R, s.sigma);
    var p, t, report;
    var pAuto = s.pMode === "auto";
    var tAuto = s.tMode === "auto";
    // t on auto is t_min(p*) and does NOT re-track a manual p (§5).
    t = tAuto ? tMin : s.t;
    if (pAuto)
      p = tAuto
        ? pStar
        : M.saturationPressure(M.containedTemperature(s.r, t, th)[0]);
    else p = s.p;
    if (pAuto && tAuto)
      report = M.checkAutoPath(p, t, s.r, s.R, s.sigma, org, inp);
    else report = M.classifyFailure(p, t, s.r, s.R, s.sigma, org, inp);
    return {
      s: s,
      inp: inp,
      org: org,
      th: th,
      pStar: pStar,
      tMin: tMin,
      p: p,
      t: t,
      report: report,
      byConstruction: {
        BURST: pAuto && tAuto && report.sigma_eff > 0,
        BOIL: pAuto,
      },
    };
  }

  function lineText(name, L, res) {
    var u = UNITS[name];
    var cmp,
      lhsName,
      rhsName,
      d = 3;
    if (name === "BURST") {
      lhsName = "p·R/2t";
      rhsName = "σ_eff(T_shell)";
      d = 1;
    } else if (name === "FREEZE") {
      lhsName = "T_int";
      rhsName = "T_freeze";
    } else if (name === "BOIL") {
      lhsName = "p";
      rhsName = "p_sat(T_int)";
      d = 2;
    } else if (name === "STARVE") {
      lhsName = "net carbon";
      rhsName = "0";
    } else {
      lhsName = "f_photon";
      rhsName = "f_floor (declared floor)";
      d = 4;
    }
    cmp =
      lhsName +
      " " +
      withUnit(fmt(L.lhs, d), u) +
      " vs " +
      rhsName +
      " " +
      withUnit(fmt(L.rhs, d), u);
    if (name === "BURST" && res.report.sigma_eff === 0)
      cmp +=
        " — the wall is water (T_shell " +
        fmt(res.report.T_shell, 2) +
        " K > 273.15 K)";
    var margin = res.byConstruction[name]
      ? withUnit("0", u) +
        " (by construction; solver residual " +
        fmt(L.margin, 2) +
        ")"
      : withUnit(signed(L.margin, d), u);
    return {
      cmp: cmp,
      margin: margin,
      status: L.violated ? "VIOLATED" : "HOLDS",
    };
  }

  // [r_melt, r_freeze] for the current wall held fixed. T_int and T_shell both scale as
  // T_eq(r) ∝ r^-1/2 at a fixed wall (containedTemperature: (1 - R_s + τ)^¼·T_eq, τ and R_s
  // independent of r), so each edge is r·(T/T_threshold)² from the model's own temperatures.
  function fixedWallWindow(res) {
    var r = res.s.r;
    var rMelt = r * Math.pow(res.report.T_shell / M.T_ICE_MELT_K, 2);
    var rFreeze = r * Math.pow(res.report.T_int / res.inp.T_freeze_K, 2);
    return [rMelt, rFreeze];
  }

  var edgeCache = {};
  var edgeTimer = null;
  var current = null;

  function edgeKey(kind, res) {
    var s = res.s;
    return JSON.stringify([
      kind,
      kind === "rClose" ? s.R : s.r,
      s.sigma,
      s.org,
      s.inputs,
    ]);
  }
  function edge(kind, res) {
    var k = edgeKey(kind, res);
    if (!(k in edgeCache)) {
      try {
        edgeCache[k] =
          kind === "rClose"
            ? M.rClose(res.s.R, res.s.sigma, res.org, res.inp)
            : M.rWindow(res.s.r, res.s.sigma, res.org, res.inp);
      } catch (err) {
        edgeCache[k] = {
          error: String(err && err.message ? err.message : err),
        };
      }
    }
    return edgeCache[k];
  }
  function edgeText(e, unit, scale, d) {
    if (e.error) return "no edge: " + e.error;
    if (e.binding === null) return "0 (no node holds)";
    return (
      fmt(e.edge / scale, d) +
      " " +
      unit +
      " (" +
      e.binding +
      " binds" +
      (e.tie ? ", tie" : "") +
      ")"
    );
  }
  function renderEdges() {
    edgeTimer = null;
    var res = current;
    if (!res) return;
    var t0 = Date.now();
    $("v-rauto").textContent = edgeText(edge("rClose", res), "AU", 1, 4);
    $("v-Rwin").textContent = edgeText(edge("rWindow", res), "km", 1000, 1);
    $("v-edge-ms").textContent = String(Date.now() - t0);
  }

  function render() {
    var s, res;
    try {
      s = read();
      res = resolve(s);
    } catch (err) {
      $("v-error").textContent =
        "model error: " + (err && err.message ? err.message : err);
      $("v-summary").textContent =
        "no verdict: the model raised (see the error line)";
      current = null;
      return;
    }
    $("v-error").textContent = "";
    current = res;
    $("v-R-out").textContent =
      s.R >= 1000 ? fmt(s.R / 1000, 3) + " km" : fmt(s.R, 1) + " m";
    $("v-r-out").textContent = s.r.toFixed(3) + " AU";
    $("v-t-out").textContent =
      s.tMode === "auto" ? "auto: " + fmt(res.t, 3) + " m" : fmt(s.t, 3) + " m";
    $("v-p-out").textContent =
      s.pMode === "auto"
        ? "auto: " + fmt(res.p, 1) + " Pa"
        : fmt(s.p, 1) + " Pa";
    $("v-t").disabled = s.tMode === "auto";
    $("v-p").disabled = s.pMode === "auto";

    var bad = res.report.violated;
    M.LOAD_ORDER.forEach(function (n) {
      var tx = lineText(n, res.report.lines[n], res);
      $("v-cmp-" + n).textContent = tx.cmp;
      $("v-margin-" + n).textContent = tx.margin;
      var st = $("v-status-" + n);
      st.textContent = tx.status;
      st.className = tx.status === "HOLDS" ? "verdict-held" : "verdict-failed";
    });
    $("v-summary").textContent = bad.length
      ? "VIOLATED: " + bad.join(", ") + " — the picture is " + bad[0]
      : "alive: every line holds";

    $("v-pstar").textContent = fmt(res.pStar, 1) + " Pa";
    $("v-tmin").textContent = fmt(res.tMin, 3) + " m";
    var w = fixedWallWindow(res);
    $("v-rfixed").textContent =
      "[" +
      w[0].toFixed(4) +
      ", " +
      w[1].toFixed(4) +
      "] AU (this " +
      fmt(res.t, 3) +
      " m wall held fixed)";
    $("v-rslab").textContent = fmt(
      M.solarSlabReflectance(res.t, res.inp.n_interior),
      4,
    );
    var tEq1 = M.equilibriumTemperature(
      1.0,
      M.SPHERE_AREA_RATIO,
      res.inp.emissivity,
      0.0,
    );
    $("v-albedo-freeze").textContent =
      "freezes at 1 AU above albedo " +
      (1 - Math.pow(res.inp.T_freeze_K / tEq1, 4)).toFixed(3);
    $("v-Rfloor").textContent =
      "registered band (P2, r " +
      P2.r_au.toFixed(2) +
      " AU, σ " +
      P2.sigma_MPa +
      " MPa): [" +
      P2.band_km[0] +
      ", " +
      P2.band_km[1] +
      "] km — provisional until M4";

    var pending =
      !(edgeKey("rClose", res) in edgeCache) ||
      !(edgeKey("rWindow", res) in edgeCache);
    if (pending) {
      $("v-rauto").textContent = "computing…";
      $("v-Rwin").textContent = "computing…";
      if (edgeTimer !== null) clearTimeout(edgeTimer);
      edgeTimer = setTimeout(renderEdges, EDGE_DEBOUNCE_MS);
    } else {
      renderEdges();
    }
  }

  Object.keys(DEFAULTS).forEach(function (id) {
    $(id).value = DEFAULTS[id];
  });
  // Going manual starts from the auto value, so the gesture begins at the design.
  function seedManual(modeId, sliderId, key) {
    $(modeId).addEventListener("change", function () {
      if ($(modeId).value === "manual" && current)
        $(sliderId).value = String(Math.log10(current[key]).toFixed(4));
    });
  }
  seedManual("v-t-mode", "v-t", "tMin");
  seedManual("v-p-mode", "v-p", "pStar");
  Object.keys(DEFAULTS).forEach(function (id) {
    $(id).addEventListener("input", render);
    $(id).addEventListener("change", render);
  });
  $("v-summary").setAttribute("aria-live", "polite");

  window.DysonVerdict = { resolve: resolve, read: read, render: render };
  render();
})();
