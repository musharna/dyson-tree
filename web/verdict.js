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
  var MV = window.DysonMapView; // web/mapview.js: the precomputed first-failure map
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
  // P1 is r_close at R = 10 km (prereg P1); the map draws both registered bands from here
  MV.setBands({
    P1: { band_au: Q4_RESULT.P1_band_au, R_km: 10, verdict: Q4_RESULT.P1,
      r_close_au: Q4_RESULT.r_close_au, sigma_MPa: Q4_RESULT.sigma_MPa },
    P2: { band_km: P2.band_km, r_au: P2.r_au, sigma_MPa: P2.sigma_MPa, verdict: Q4_RESULT.P2,
      measured_km: Q4_RESULT.R_window_km.toFixed(1) },
    order: M.LOAD_ORDER, // the model's check order: a map cell names the first line to fail
  });
  // the <details> inputs: a change here moves the model off the precomputed map's inputs
  var ADVANCED = ["v-albedo", "v-emissivity", "v-topt", "v-omega", "v-ffloor", "v-dust", "v-interior",
    "v-fresnel", "v-ninterior"];

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
      // STARVE's right side is the constant 0, named once, not "0 0.000 <unit>"
      (name === "STARVE" ? rhsName : rhsName + " " + withUnit(fmt(L.rhs, d), u));
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
    /* a deficit smaller than the registered absolute floor (prereg
     * starve_opaque_abs 1e-9) scores HOLDS; far out, cold respiration is that
     * small, so say the organism is still losing carbon */
    if (name === "STARVE" && L.margin < 0 && !L.violated)
      margin +=
        " — net is negative but inside the registered detection floor (" +
        fmt(M.EPS_STARVE_OPAQUE, 0) +
        "), so this line scores HOLDS";
    return {
      cmp: cmp,
      margin: margin,
      status: L.violated ? "VIOLATED" : "HOLDS",
    };
  }

  // The headroom bars (visual-first Task 4). Each bar is the line's printed margin divided by that
  // line's own scale, so five lines in different units share one axis. The scales are the model's
  // own numbers for this design: σ_eff and p_sat are the right sides BURST and BOIL compare against,
  // f_floor is OPAQUE's right side, a_max is the organism's (after any card). FREEZE has no model
  // output of its size, so it uses FREEZE_SCALE_K, a display scale named by the task brief; the row's
  // title says which scale each bar uses. Bars are clamped to ±1 scale and the clamp is marked.
  var FREEZE_SCALE_K = 10;
  function barScale(name, L, res) {
    if (name === "BURST") return { v: L.rhs, name: "σ_eff(T_shell)", unit: "Pa" };
    if (name === "FREEZE") return { v: FREEZE_SCALE_K, name: "10 K (a display scale, not a model output)", unit: "K" };
    if (name === "BOIL") return { v: L.rhs, name: "p_sat(T_int)", unit: "Pa" };
    if (name === "STARVE") return { v: res.org.a_max, name: "a_max (the organism's)", unit: "µmol m⁻² s⁻¹" };
    if (name === "OPAQUE") return { v: L.rhs, name: "f_floor (declared)", unit: "" };
    throw new RangeError("headroom: no scale for line " + name);
  }
  function pct(x) {
    return (Math.round(x * 1e4) / 100) + "%";
  }
  function drawBar(name, L, res, first) {
    var sc = barScale(name, L, res);
    var q = L.margin / sc.v; // ±Infinity when the scale is 0 (σ_eff of a water wall), NaN if 0/0
    var row = $("hr-" + name), fill = $("hr-" + name + "-fill"), cap = $("hr-" + name + "-cap");
    var val = $("hr-" + name + "-val");
    var scaleText = "bar = margin ÷ " + sc.name + " = " + withUnit(fmt(L.margin, 3), sc.unit) + " ÷ " +
      withUnit(fmt(sc.v, 3), sc.unit);
    if (isNaN(q)) {
      // 0 ÷ 0: no length can be drawn; said, not hidden
      row.setAttribute("data-norm", "NaN");
      row.setAttribute("data-len", "0");
      row.setAttribute("data-clamped", "false");
      fill.setAttribute("style", "left:50%;width:0%");
      cap.className = "hr-cap";
      val.textContent = "no scale";
      scaleText += ": the scale is 0, so the bar has no length";
    } else {
      var len = Math.max(-1, Math.min(1, q)), clamped = len !== q;
      row.setAttribute("data-norm", String(q));
      row.setAttribute("data-len", String(len));
      row.setAttribute("data-clamped", clamped ? "true" : "false");
      fill.setAttribute("style", len >= 0
        ? "left:50%;width:" + pct(len / 2)
        : "left:" + pct(0.5 + len / 2) + ";width:" + pct(-len / 2));
      cap.className = clamped ? "hr-cap " + (len > 0 ? "hr-cap-right" : "hr-cap-left") : "hr-cap";
      cap.textContent = clamped ? (len > 0 ? "›" : "‹") : "";
      val.textContent = res.byConstruction[name]
        ? "0, auto"
        : !isFinite(q) ? (q > 0 ? "+∞" : "−∞") : (q >= 0 ? "+" : "−") + fmt(Math.abs(q), 2);
      scaleText += " = " + (isFinite(q) ? fmt(q, 3) : String(q)) +
        (clamped ? "; drawn clamped at " + (len > 0 ? "+1" : "−1") + " scale" : "");
    }
    row.setAttribute("data-violated", L.violated ? "true" : "false");
    row.setAttribute("data-first", first ? "true" : "false");
    row.setAttribute("title", name + " headroom: " + scaleText);
    $("hr-" + name + "-scale").textContent = scaleText;
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
      $("v-summary").className = "vsummary verdict-failed";
      current = null;
      $("headroom").setAttribute("data-error", "true"); // the bars are the last good design's
      PIC.blank("the model raised");
      mapModelError(s);
      return;
    }
    $("v-error").textContent = "";
    $("headroom").setAttribute("data-error", "false");
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
      // the wound prints the panel's both sides; a " — " explanation stays in the panel
      texts[n] = tx.cmp.split(" — ")[0];
      $("v-cmp-" + n).textContent = tx.cmp;
      $("v-margin-" + n).textContent = tx.margin;
      var st = $("v-status-" + n);
      st.textContent = tx.status;
      st.className = "hr-status " + (tx.status === "HOLDS" ? "verdict-held" : "verdict-failed");
      drawBar(n, res.report.lines[n], res, bad.length > 0 && bad[0] === n);
    });
    $("v-summary").textContent = bad.length
      ? "VIOLATED: " + bad.join(", ") + " — drawn: " + bad[0] + " (first to fail)"
      : "alive: every line holds";
    $("v-summary").className = "vsummary " + (bad.length ? "verdict-failed" : "verdict-held");

    $("v-tR").textContent = (res.t / s.R).toExponential(3);
    PIC.draw(res, texts);
    drawMap(s, bad.length ? bad[0] : "HELD", res);

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
      " km, OPAQUE: prediction " +
      (Q4_RESULT.P2 === "HELD" ? "confirmed" : "falsified");

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

  // The map's source. The precomputed slice (web/map_data.js) is the auto design at the page's
  // default inputs, so it applies iff no card is played and every advanced input is at its
  // default. Otherwise a Web Worker (web/map_worker.js) recomputes the slice with the organism and
  // inputs this page's resolve() built, level by level (12×8, 40×30, 80×60); until the first
  // level lands the precomputed slice is drawn greyed and labelled not current.
  // Manual p/t does not change the map: it is the map of the AUTO design, labelled as such, and
  // the dot carries the exact (manual) verdict.
  // Every change of the map's inputs bumps mapGen; a worker message from an older gen is dropped.
  var MAP_DEBOUNCE_MS = 250;
  var MAP_FINAL = "80×60";
  var map = { gen: 0, key: null, live: null, progress: null, error: null, worker: null, timer: null, last: null };

  function stopWorker() {
    if (map.timer !== null) clearTimeout(map.timer);
    map.timer = null;
    if (map.worker) map.worker.terminate();
    map.worker = null;
  }
  function startWorker(gen, req) {
    map.timer = null;
    if (gen !== map.gen) return;
    if (typeof Worker === "undefined") {
      map.error = "this browser has no Web Worker";
      return redrawMap();
    }
    var w;
    try {
      w = new Worker("map_worker.js");
    } catch (err) {
      var fileUrl = typeof location !== "undefined" && location.protocol === "file:";
      map.error = fileUrl
        ? "browsers refuse workers on file:// pages; serve this folder over http"
        : "the browser refused the worker: " + (err && err.message ? err.message : err);
      return redrawMap();
    }
    map.worker = w;
    w.onmessage = function (ev) { onMapMessage(ev.data); };
    w.onerror = function (ev) {
      if (gen !== map.gen) return;
      map.error = "worker error: " + ((ev && ev.message) || "the worker script failed to load");
      stopWorker();
      redrawMap();
    };
    req.gen = gen;
    w.postMessage(req);
  }
  function onMapMessage(d) {
    if (!d || d.gen !== map.gen) return; // a result for inputs the page no longer shows
    if (d.error) {
      map.error = "the model raised in the worker: " + String(d.error).split("\n")[0];
      stopWorker();
    } else if (d.progress) {
      map.progress = d.progress;
    } else {
      var D = window.DysonMap, n = D.grid.r_log10[2] * D.grid.R_log10[2];
      if (typeof d.slice !== "string" || d.slice.length !== n)
        throw new Error("map worker: level " + d.level + " slice is not " + n + " cells");
      map.live = { level: d.level, slice: d.slice };
      map.progress = null;
      if (d.level === MAP_FINAL) stopWorker();
    }
    redrawMap();
  }
  function redrawMap() {
    if (map.last) drawMap(map.last[0], map.last[1], map.last[2]);
  }
  function spaced(level) {
    return String(level).replace("×", " × ");
  }

  // The model raised: no verdict for the current inputs. Stop and orphan any worker (its late
  // messages carry an old gen), forget the key so the next good design starts afresh, and draw
  // the last cells greyed with a dot that names no class. s: the inputs read, or undefined if
  // reading them raised (the dot then stays where the last good design put it).
  function mapModelError(s) {
    stopWorker();
    map.gen += 1;
    map.key = null;
    map.live = map.progress = map.error = null;
    var at = s || (map.last && map.last[0]);
    if (!at) return;
    var state = mapState(at, null);
    state.source = { kind: "stale", lines: ["no verdict: the model raised", "greyed: the last map, not current"] };
    MV.draw($("map"), state, null);
  }
  function mapState(s, verdict) {
    return {
      verdict: verdict,
      r: s.r,
      R: s.R,
      sigma_MPa: Number($("v-sigma").value),
      org: s.org,
      cardsPlayed: s.deck.played.length,
      advancedChanged: ADVANCED.some(function (id) {
        return $(id).value !== DEFAULTS[id];
      }),
      manualPT: s.pMode !== "auto" || s.tMode !== "auto",
    };
  }
  // verdict: the class the summary names (first violated line, or HELD) at the exact design
  function drawMap(s, verdict, res) {
    map.last = [s, verdict, res];
    var state = mapState(s, verdict);
    var k = $("v-sigma").value + "|" + state.org;
    var pre = window.DysonMap.slices[k];
    if (typeof pre !== "string") throw new Error("map: no precomputed slice " + k);
    var applies = state.cardsPlayed === 0 && !state.advancedChanged;
    var key = applies ? "precomputed|" + k : JSON.stringify([s.sigma, res.org, res.inp]);
    if (key !== map.key) {
      map.key = key;
      map.gen += 1;
      map.live = map.progress = map.error = null;
      stopWorker();
      if (!applies) {
        var D = window.DysonMap;
        map.timer = setTimeout(startWorker.bind(null, map.gen, {
          grid: D.grid, classes: D.classes, sigma_Pa: s.sigma, org: res.org, inputs: res.inp,
        }), MAP_DEBOUNCE_MS);
      }
    }
    var slice = pre;
    if (applies) {
      state.source = { kind: "precomputed" };
    } else if (map.live) {
      var p = map.progress;
      state.source = {
        kind: "live",
        level: map.live.level,
        provisional: map.live.level !== MAP_FINAL, // a coarse preview, drawn as such
        status: map.live.level === MAP_FINAL
          ? "recomputed for your design (" + spaced(MAP_FINAL) + ")"
          : "your design, " + spaced(map.live.level) + " preview" +
            (p ? " · computing " + spaced(p.level) + ": " + Math.floor((100 * p.done) / p.total) + "%" : ""),
      };
      slice = map.live.slice;
    } else {
      state.source = map.error
        ? { kind: "stale", lines: ["live recompute unavailable", map.error,
          "greyed: the precomputed map, not current"] }
        : { kind: "stale", lines: ["recomputing for your design…" +
          (map.progress ? " " + Math.floor((100 * map.progress.done) / map.progress.total) + "%" : ""),
          "greyed: the precomputed map, not current"] };
    }
    MV.draw($("map"), state, slice);
  }
  // A click or drag on the map sets r and R, snapped to each slider's own step grid, and fires
  // the events a slider gesture fires (input while dragging, change on release).
  MV.onPick(function (rLog, RLog, phase) {
    [["v-r", rLog], ["v-R", RLog]].forEach(function (p) {
      var e = $(p[0]);
      var min = Number(e.getAttribute("min")), max = Number(e.getAttribute("max")),
        step = Number(e.getAttribute("step"));
      if (!(isFinite(min) && isFinite(max) && step > 0))
        throw new Error("map pick: #" + p[0] + " has no min/max/step");
      var v = min + Math.round((p[1] - min) / step) * step;
      e.value = Math.max(min, Math.min(max, v)).toFixed(4);
    });
    ["v-r", "v-R"].forEach(function (id) {
      $(id).dispatchEvent(new Event(phase, { bubbles: true }));
    });
  });

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
    // text >= 12 px rendered at the page width (smoke asserts it); dot labels sit in a column
    // right of the band, so none straddles a band edge
    var FS = 13, X0 = 1.1, X1 = 1.35, L = 24, Rt = 300, TOP = 34, ROW = 26, BOT = TOP + 12 + 3 * ROW;
    svg.setAttribute("viewBox", "0 0 400 " + (BOT + 52));
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
    mk("text", { id: "q4-band-label", x: (x(b[0]) + x(b[1])) / 2, y: TOP - 9, "text-anchor": "middle",
      "font-size": FS, fill: "#6b655c" }, "pre-registered [" + b[0] + ", " + b[1] + "] AU (" + Q4_RESULT.P1 + ") — registered run");
    var LX = Math.max(Rt, x(b[1])) + 10; // the label column
    Q4_RESULT.r_close_au.forEach(function (r, i) {
      var y = TOP + 6 + ROW / 2 + i * ROW;
      mk("line", { x1: x(r) + 5, y1: y, x2: LX - 4, y2: y, stroke: "#b5b0a6", "stroke-dasharray": "2 3" });
      mk("circle", { "data-mark": "q4-measured", cx: x(r), cy: y, r: 4.5, fill: "#1565C0" });
      mk("text", { x: LX, y: y + 4.5, "font-size": FS, fill: "#1f1f1f" },
        "σ " + Q4_RESULT.sigma_MPa[i] + ": " + r.toFixed(4));
    });
    mk("line", { x1: L, y1: BOT, x2: Rt, y2: BOT, stroke: "#9a948b" });
    [1.1, 1.15, 1.2, 1.25, 1.3, 1.35].forEach(function (t) {
      mk("line", { x1: x(t), y1: BOT, x2: x(t), y2: BOT + 4, stroke: "#9a948b" });
      mk("text", { x: x(t), y: BOT + 19, "text-anchor": "middle", "font-size": FS, fill: "#5d5d5d" },
        t.toFixed(2));
    });
    mk("text", { x: 4, y: BOT + 42, "font-size": FS, fill: "#5d5d5d" },
      "r (AU): measured r_close; σ in MPa");
    var v = $("q4-verdict");
    v.textContent = "P1 " + Q4_RESULT.P1 + " (registered run, binding FREEZE) · P2 " + Q4_RESULT.P2 +
      " (registered run, R_window " + Q4_RESULT.R_window_km.toFixed(1) + " km, OPAQUE)";
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
