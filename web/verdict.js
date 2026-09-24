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
  var DECK = window.DysonDeck; // web/deck.js: the played cards' inputs
  var PIC = window.DysonPicture; // web/picture.js: the cross-section, drawn from res
  var $ = function (id) {
    var e = document.getElementById(id);
    if (!e) throw new Error("verdict panel: missing #" + id);
    return e;
  };

  // Registered P2 band, copied from experiments/q4_vessel/prereg.yaml (tests pin it).
  var P2 = { band_km: [60, 300], r_au: 1.1, sigma_MPa: 0.7 };
  var EDGE_DEBOUNCE_MS = 300;

  // The committed Q4 run (experiments/q4_vessel/RESULTS.md, edges.csv), COPIED here, never
  // recomputed on the page; tests/test_q4_runner.py pins these to RESULTS.md.
  var Q4_RESULT = {
    P1: "HELD",
    P2: "HELD",
    P1_band_au: [1.19, 1.27],
    sigma_MPa: [0.7, 1.5, 3.1],
    r_close_au: [1.2049, 1.2303, 1.2543],
    R_window_km: 95.6,
  };

  // Control defaults (§5). Log sliders carry log10 of the value.
  var DEFAULTS = {
    "v-R": "3", // log10 m: 1 km
    "v-t-mode": "auto",
    "v-t": "0", // log10 m, used when manual
    "v-p-mode": "auto",
    "v-p": "3", // log10 Pa, used when manual
    "v-r": "0.0414", // log10 AU on the 1e-4 grid from -0.3011: 1.100 AU (§5 range 0.5 to 100 AU)
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
    var deck = DECK.effect();
    if (!fr) throw new RangeError("unknown Fresnel setting " + v("v-fresnel"));
    return {
      R: Math.pow(10, Number(v("v-R"))),
      r: Math.round(Math.pow(10, Number(v("v-r"))) * 1000) / 1000,
      sigma: Number(v("v-sigma")) * 1e6,
      org: v("v-org"),
      wall: v("v-wall"),
      tMode: v("v-t-mode"),
      t: Math.pow(10, Number(v("v-t"))),
      pMode: v("v-p-mode"),
      p: Math.pow(10, Number(v("v-p"))),
      // a played card moves an input (T_freeze_K here), never the inequality (§12)
      inputs: Object.assign({
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
      }, deck.inputs),
      deck: deck,
    };
  }

  // §5's four (p, t) modes. classifyFailure gets the resolved pair only.
  function resolve(s) {
    var inp = M.makeVesselInputs(s.inputs);
    var org = M.PRESETS[s.org];
    if (!org) throw new RangeError("unknown organism class " + s.org);
    org = DECK.applyOrganism(org, s.deck);
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
      s.deck.organism,
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
      PIC.blank("the model raised");
      return;
    }
    $("v-error").textContent = "";
    DECK.status(s.deck);
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
    var texts = {};
    M.LOAD_ORDER.forEach(function (n) {
      var tx = lineText(n, res.report.lines[n], res);
      texts[n] = tx.cmp;
      $("v-cmp-" + n).textContent = tx.cmp;
      $("v-margin-" + n).textContent = tx.margin;
      var st = $("v-status-" + n);
      st.textContent = tx.status;
      st.className = tx.status === "HOLDS" ? "verdict-held" : "verdict-failed";
    });
    $("v-summary").textContent = bad.length
      ? "VIOLATED: " + bad.join(", ") + " — the picture is " + bad[0]
      : "alive: every line holds";

    $("v-tR").textContent = (res.t / s.R).toExponential(3);
    PIC.draw(res, texts);

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
      "] km — measured " +
      Q4_RESULT.R_window_km.toFixed(1) +
      " km, OPAQUE: " +
      Q4_RESULT.P2;

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

  // Q4 P1: the registered band drawn hatched as Q1's is (web/app.js), the measured r_close
  // beside it. Drawn once: it is a record of the run, not a function of the inputs.
  function drawQ4Band() {
    var svg = $("q4-band");
    var NS = "http://www.w3.org/2000/svg";
    function mk(name, attrs, text) {
      var n = document.createElementNS(NS, name);
      for (var k in attrs) n.setAttribute(k, attrs[k]);
      if (text !== undefined) n.textContent = text;
      svg.appendChild(n);
      return n;
    }
    var X0 = 1.1, X1 = 1.35, L = 30, Rt = 385, TOP = 22, BOT = 88;
    var x = function (r) { return L + ((r - X0) / (X1 - X0)) * (Rt - L); };
    var defs = mk("defs", {});
    var pat = document.createElementNS(NS, "pattern");
    [["id", "q4hatch"], ["width", "8"], ["height", "8"], ["patternUnits", "userSpaceOnUse"],
     ["patternTransform", "rotate(45)"]].forEach(function (kv) { pat.setAttribute(kv[0], kv[1]); });
    var ln = document.createElementNS(NS, "line");
    [["x1", "0"], ["y1", "0"], ["x2", "0"], ["y2", "8"], ["stroke", "#8a8378"],
     ["stroke-width", "2"], ["opacity", "0.45"]].forEach(function (kv) { ln.setAttribute(kv[0], kv[1]); });
    pat.appendChild(ln);
    defs.appendChild(pat);
    var b = Q4_RESULT.P1_band_au;
    mk("rect", { id: "q4-band-rect", x: x(b[0]), y: TOP, width: x(b[1]) - x(b[0]), height: BOT - TOP,
      fill: "url(#q4hatch)", stroke: "#8a8378", "stroke-dasharray": "4 3", "stroke-width": "1" });
    mk("text", { id: "q4-band-label", x: (x(b[0]) + x(b[1])) / 2, y: TOP - 6, "text-anchor": "middle",
      "font-size": "11", fill: "#6b655c" }, "pre-registered [" + b[0] + ", " + b[1] + "] AU (" + Q4_RESULT.P1 + ")");
    Q4_RESULT.r_close_au.forEach(function (r, i) {
      var y = TOP + 14 + i * 20;
      mk("circle", { "data-mark": "q4-measured", cx: x(r), cy: y, r: 4, fill: "#1565C0" });
      mk("text", { x: x(r) + 8, y: y + 4, "font-size": "11", fill: "#1f1f1f" },
        "σ " + Q4_RESULT.sigma_MPa[i] + " MPa: " + r.toFixed(4) + " AU");
    });
    mk("line", { x1: L, y1: BOT, x2: Rt, y2: BOT, stroke: "#9a948b" });
    [1.1, 1.15, 1.2, 1.25, 1.3, 1.35].forEach(function (t) {
      mk("line", { x1: x(t), y1: BOT, x2: x(t), y2: BOT + 4, stroke: "#9a948b" });
      mk("text", { x: x(t), y: BOT + 16, "text-anchor": "middle", "font-size": "10", fill: "#5d5d5d" },
        t.toFixed(2));
    });
    mk("text", { x: (L + Rt) / 2, y: BOT + 30, "text-anchor": "middle", "font-size": "11", fill: "#5d5d5d" },
      "r (AU): measured r_close, model output");
    var v = $("q4-verdict");
    v.textContent = "P1 " + Q4_RESULT.P1 + " (binding FREEZE) · P2 " + Q4_RESULT.P2 +
      " (R_window " + Q4_RESULT.R_window_km.toFixed(1) + " km, OPAQUE)";
    v.className = Q4_RESULT.P1 === "HELD" ? "verdict-held" : "verdict-failed";
  }
  drawQ4Band();

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
  Object.keys(DEFAULTS)
    .concat(DECK.controlIds)
    .forEach(function (id) {
    $(id).addEventListener("input", render);
    $(id).addEventListener("change", render);
  });
  $("v-summary").setAttribute("aria-live", "polite");

  window.DysonVerdict = { resolve: resolve, read: read, render: render, Q4_RESULT: Q4_RESULT };
  render();
})();
