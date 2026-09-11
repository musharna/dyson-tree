// Page wiring for the carbon-budget explorer. No framework, no build step, no
// CDN; the plot is hand-drawn SVG. All arithmetic comes from web/model.js --
// nothing is recomputed here, so the page cannot drift from the parity-checked
// port. Classic script (see the note at the top of model.js).
(function () {
  "use strict";

  var M = window.DysonModel;

  // Registered values, copied from experiments/q1_crossover/prereg.yaml. These
  // are PREDICTIONS written before the sweep ran, not results: k_grid is the
  // swept list, predicted_r_star_au the pre-registered band, and `verdict` the
  // published Q1 outcome at the preset's own default k.
  var REGISTERED = {
    vascular: {
      k_grid: [50.0, 100.0, 200.0],
      default_k: 100.0,
      band_au: [12.0, 22.0],
      verdict: "HELD",
    },
    algal: {
      k_grid: [10.0, 20.0, 40.0],
      default_k: 20.0,
      band_au: [35.0, 55.0],
      verdict: "FAILED",
    },
  };

  var R_MIN = 0.5;
  var R_MAX = 100.0;
  var N_GRID = 200; // prereg sweep.n_grid -- the root-finder's bracketing grid
  var CURVE_N = 400; // drawing resolution only

  var SVG_NS = "http://www.w3.org/2000/svg";
  var W = 720;
  var H = 400;
  var PAD = { top: 18, right: 18, bottom: 44, left: 62 };

  var els = {
    preset: document.getElementById("preset"),
    kselect: document.getElementById("kselect"),
    rslider: document.getElementById("rslider"),
    rlabel: document.getElementById("rlabel"),
    plot: document.getElementById("plot"),
    bandswatch: document.getElementById("bandswatch"),
    outR: document.getElementById("out-r"),
    outI: document.getElementById("out-i"),
    outNet: document.getElementById("out-net"),
    outTeq: document.getElementById("out-teq"),
    outXover: document.getElementById("out-xover"),
    outBand: document.getElementById("out-band"),
    outIc: document.getElementById("out-ic"),
  };

  function el(name, attrs, text) {
    var node = document.createElementNS(SVG_NS, name);
    for (var key in attrs) node.setAttribute(key, attrs[key]);
    if (text !== undefined) node.textContent = text;
    return node;
  }

  // Slider position (0..SLIDER_MAX) <-> distance, log-spaced over [R_MIN, R_MAX].
  // 10000 steps so the default 1 AU lands on 1.000, not 1.001.
  var SLIDER_MAX = 10000;

  // The result is QUANTISED to the precision it is displayed at (3 dp). Without
  // this the slider's default position is 0.99987 AU while the label reads
  // "1.000 AU", and every readout beside it -- T_eq, PAR irradiance -- is
  // computed at 0.99987. A reader comparing 330.99 K against the repository's
  // own 330.97 K at 1 AU would be right to call the page wrong. Quantising is
  // also what keeps sliderToR(SLIDER_MAX) from returning 100.00000000000004.
  //
  // The cost, stated rather than hidden: quantising creates small plateaus at
  // the near end, where one slider step (2.6e-4 AU near 0.5 AU) is finer than
  // the 1e-3 AU display grid. Over the 10001 positions there are 8881 distinct
  // distances and the longest run of identical values is 4. That is the price
  // of "the distance shown is the distance used", and it is the right trade:
  // a repeated value is visible and harmless, a hidden mismatch is neither.
  var R_DP = 3;
  function sliderToR(v) {
    var t = Number(v) / SLIDER_MAX;
    var r = Math.exp(Math.log(R_MIN) + t * (Math.log(R_MAX) - Math.log(R_MIN)));
    var q = Math.pow(10, R_DP);
    return Math.min(R_MAX, Math.max(R_MIN, Math.round(r * q) / q));
  }
  function rToSlider(r) {
    var t = (Math.log(r) - Math.log(R_MIN)) / (Math.log(R_MAX) - Math.log(R_MIN));
    return Math.round(t * SLIDER_MAX);
  }

  function state() {
    var cls = els.preset.value;
    return {
      cls: cls,
      org: M.PRESETS[cls],
      reg: REGISTERED[cls],
      k: Number(els.kselect.value),
      r: sliderToR(els.rslider.value),
    };
  }

  function xScale(r) {
    var t = (Math.log(r) - Math.log(R_MIN)) / (Math.log(R_MAX) - Math.log(R_MIN));
    return PAD.left + t * (W - PAD.left - PAD.right);
  }

  function makeYScale(lo, hi) {
    return function (y) {
      var t = (y - lo) / (hi - lo);
      return H - PAD.bottom - t * (H - PAD.top - PAD.bottom);
    };
  }

  function drawPlot(s) {
    var svg = els.plot;
    while (svg.firstChild) svg.removeChild(svg.firstChild);

    // Hatch pattern for the pre-registered band: deliberately unlike any
    // result mark on this plot. A prediction must never read as a measurement.
    var defs = el("defs", {});
    var pat = el("pattern", {
      id: "bandhatch",
      width: "8",
      height: "8",
      patternUnits: "userSpaceOnUse",
      patternTransform: "rotate(45)",
    });
    pat.appendChild(el("rect", { width: "8", height: "8", fill: "none" }));
    pat.appendChild(
      el("line", { x1: "0", y1: "0", x2: "0", y2: "8", stroke: "#8a8378", "stroke-width": "2", opacity: "0.45" })
    );
    defs.appendChild(pat);
    svg.appendChild(defs);

    var pts = [];
    var lo = Infinity;
    var hi = -Infinity;
    for (var i = 0; i < CURVE_N; i += 1) {
      var t = i / (CURVE_N - 1);
      var r = Math.exp(Math.log(R_MIN) + t * (Math.log(R_MAX) - Math.log(R_MIN)));
      var y = M.netCarbon(s.org, r, s.k);
      pts.push([r, y]);
      if (y < lo) lo = y;
      if (y > hi) hi = y;
    }
    var span = hi - lo || 1;
    lo -= 0.06 * span;
    hi += 0.06 * span;
    if (lo > 0) lo = -0.05 * hi; // zero is always on the plot: it is the verdict line
    var yScale = makeYScale(lo, hi);

    // Pre-registered band, drawn first so results sit on top of it.
    var bx0 = xScale(Math.max(R_MIN, s.reg.band_au[0]));
    var bx1 = xScale(Math.min(R_MAX, s.reg.band_au[1]));
    svg.appendChild(
      el("rect", {
        x: bx0,
        y: PAD.top,
        width: Math.max(0, bx1 - bx0),
        height: H - PAD.top - PAD.bottom,
        fill: "url(#bandhatch)",
        stroke: "#8a8378",
        "stroke-dasharray": "4 3",
        "stroke-width": "1",
      })
    );
    svg.appendChild(
      el(
        "text",
        {
          x: (bx0 + bx1) / 2,
          y: PAD.top + 14,
          "text-anchor": "middle",
          "font-size": "11",
          fill: "#6b655c",
        },
        "pre-registered " + (s.reg.verdict === "HELD" ? "(HELD)" : "(FAILED)")
      )
    );

    // Axes.
    var ticks = [0.5, 1, 2, 5, 10, 20, 50, 100];
    ticks.forEach(function (tick) {
      var x = xScale(tick);
      svg.appendChild(
        el("line", { x1: x, y1: H - PAD.bottom, x2: x, y2: H - PAD.bottom + 5, stroke: "#9a948b" })
      );
      svg.appendChild(
        el("text", { x: x, y: H - PAD.bottom + 18, "text-anchor": "middle", "font-size": "11", fill: "#5d5d5d" }, String(tick))
      );
    });
    svg.appendChild(
      el("text", { x: (PAD.left + W - PAD.right) / 2, y: H - 8, "text-anchor": "middle", "font-size": "12", fill: "#5d5d5d" }, "heliocentric distance (AU, log scale)")
    );

    var yTicks = [];
    var step = Math.pow(10, Math.round(Math.log10((hi - lo) / 4)) );
    for (var v = Math.ceil(lo / step) * step; v <= hi; v += step) yTicks.push(v);
    yTicks.forEach(function (v) {
      var y = yScale(v);
      svg.appendChild(el("line", { x1: PAD.left - 5, y1: y, x2: PAD.left, y2: y, stroke: "#9a948b" }));
      svg.appendChild(
        el("text", { x: PAD.left - 8, y: y + 4, "text-anchor": "end", "font-size": "11", fill: "#5d5d5d" }, v.toFixed(Math.abs(step) < 1 ? 1 : 0))
      );
    });
    svg.appendChild(
      el("text", { x: 14, y: (PAD.top + H - PAD.bottom) / 2, "font-size": "12", fill: "#5d5d5d", transform: "rotate(-90 14 " + (PAD.top + H - PAD.bottom) / 2 + ")", "text-anchor": "middle" }, "net carbon (µmol CO₂ m⁻² s⁻¹)")
    );

    // Zero line: the break-even the whole question is about.
    var y0 = yScale(0);
    svg.appendChild(el("line", { x1: PAD.left, y1: y0, x2: W - PAD.right, y2: y0, stroke: "#1b1b1b", "stroke-width": "1", "stroke-dasharray": "2 3" }));
    // "break-even" sits at the LEFT end of the zero line: the right end is where
    // every crossover lands, and its label collided with them.
    svg.appendChild(el("text", { x: PAD.left + 4, y: y0 - 5, "text-anchor": "start", "font-size": "11", fill: "#1b1b1b" }, "break-even"));

    // The curve.
    var d = pts
      .map(function (p, i) {
        return (i === 0 ? "M" : "L") + xScale(p[0]).toFixed(2) + " " + yScale(p[1]).toFixed(2);
      })
      .join(" ");
    svg.appendChild(el("path", { d: d, fill: "none", stroke: "#1f5c8b", "stroke-width": "2" }));

    // Measured crossovers for every registered k of this class: results, drawn
    // as solid dots -- a mark the bands never use.
    // Labels are staggered onto two rows in x order. At k=50/100/200 the three
    // crossovers land within ~90px of each other and a single row runs them
    // into an unreadable blob.
    var marks = [];
    s.reg.k_grid.forEach(function (k) {
      var xo = M.crossoverDistanceFor(s.org, k, R_MIN, R_MAX, N_GRID);
      if (xo === null) return;
      marks.push({ k: k, xo: xo, cx: xScale(xo) });
    });
    marks.sort(function (a, b) { return a.cx - b.cx; });
    marks.forEach(function (m, i) {
      var isCurrent = m.k === s.k;
      svg.appendChild(
        el("circle", {
          cx: m.cx,
          cy: y0,
          r: isCurrent ? 5 : 3.5,
          fill: "#b4432f",
          stroke: "#faf8f4",
          "stroke-width": "1",
        })
      );
      // "model output" rides on the point itself rather than floating in a
      // corner, where it collided with the band caption in the algal view.
      var text = "k=" + m.k + " · " + m.xo.toFixed(2) + " AU";
      if (isCurrent) text += " (model output)";
      // Anchor at the edges so a label near x=720 cannot be clipped away.
      var anchor = "middle";
      if (m.cx > W - PAD.right - 70) anchor = "end";
      else if (m.cx < PAD.left + 70) anchor = "start";
      svg.appendChild(
        el(
          "text",
          {
            class: "xover-label",
            x: m.cx,
            // Three rows, one label each: at k=50/100/200 the crossovers are
            // ~42px apart on a log axis and the labels are ~90-200px wide, so
            // two rows still ran them into each other. ABOVE the zero line, not
            // below: below it there are only ~16px before the x-axis tick
            // numbers in the algal view, and the labels sat on top of them.
            y: y0 - 12 - (i % 3) * 17,
            "text-anchor": anchor,
            "font-size": "11",
            fill: "#b4432f",
            "font-weight": isCurrent ? "600" : "400",
          },
          text
        )
      );
    });

    // The selected distance.
    var xr = xScale(s.r);
    var netAtR = M.netCarbon(s.org, s.r, s.k);
    svg.appendChild(el("line", { x1: xr, y1: PAD.top, x2: xr, y2: H - PAD.bottom, stroke: "#1f5c8b", "stroke-width": "1", "stroke-dasharray": "3 3", opacity: "0.7" }));
    svg.appendChild(el("circle", { id: "marker", cx: xr, cy: yScale(netAtR), r: 4.5, fill: "#1f5c8b" }));
  }

  function render() {
    var s = state();

    els.rlabel.textContent = s.r.toFixed(R_DP) + " AU";

    var xover = M.crossoverDistanceFor(s.org, s.k, R_MIN, R_MAX, N_GRID);
    var inBand = xover !== null && xover >= s.reg.band_au[0] && xover <= s.reg.band_au[1];

    els.outR.textContent = s.r.toFixed(R_DP) + " AU";
    els.outI.textContent = M.irradiance(s.r).toFixed(2) + " µmol photons m⁻² s⁻¹";
    var net = M.netCarbon(s.org, s.r, s.k);
    els.outNet.textContent =
      net.toFixed(4) + " µmol CO₂ m⁻² s⁻¹ — " + (net > 0 ? "above break-even" : "below break-even");
    var teq = M.equilibriumTemperature(s.r, s.org.area_ratio, s.org.emissivity, s.org.albedo);
    els.outTeq.textContent = teq.toFixed(2) + " K (" + (teq - 273.15).toFixed(2) + " °C)";

    if (xover === null) {
      els.outXover.textContent = "no crossover in range (0.5–100 AU)";
    } else {
      els.outXover.textContent = xover.toFixed(4) + " AU";
    }
    els.outBand.innerHTML = "";
    var bandText =
      "[" + s.reg.band_au[0] + ", " + s.reg.band_au[1] + "] AU — " +
      (xover === null ? "no value to compare" : inBand ? "inside" : "OUTSIDE");
    var span = document.createElement("span");
    span.className = inBand ? "verdict-held" : "verdict-failed";
    span.textContent = bandText;
    els.outBand.appendChild(span);
    var note = document.createElement("span");
    note.style.color = "var(--muted)";
    note.textContent =
      " · registered before the run; the class verdict at its default k=" +
      s.reg.default_k + " was " + s.reg.verdict;
    els.outBand.appendChild(note);

    els.outIc.textContent =
      M.compensationIrradiance(s.org, s.k).toFixed(4) + " µmol photons m⁻² s⁻¹";

    drawPlot(s);
  }

  function fillKOptions() {
    var cls = els.preset.value;
    var reg = REGISTERED[cls];
    els.kselect.innerHTML = "";
    reg.k_grid.forEach(function (k) {
      var opt = document.createElement("option");
      opt.value = String(k);
      opt.textContent = k === reg.default_k ? k + " (registered default)" : String(k);
      if (k === reg.default_k) opt.selected = true;
      els.kselect.appendChild(opt);
    });
  }

  els.preset.addEventListener("change", function () {
    fillKOptions();
    render();
  });
  els.kselect.addEventListener("change", render);
  els.rslider.addEventListener("input", render);

  els.bandswatch.style.background =
    "repeating-linear-gradient(45deg, #8a8378 0 2px, transparent 2px 6px)";

  fillKOptions();
  els.rslider.value = String(rToSlider(1.0));
  render();
})();
