// The vessel's cross-section (northstar M3, spec §5 "The picture", §9 risk 3). Classic script.
//
// Drawing only: every quantity drawn is a DysonModel output handed over by verdict.js (the
// resolved t and R, the report's lines, T_int, f_photon, the organism's a_max) or the model's
// own transmission spectrum. The only numbers this file owns are pixel constants.
//
//   outer circle ∝ R + t (log-mapped so 10 m to 100 km fits one box; see OUT_MIN/OUT_MAX)
//   inner circle = outer · R / (R + t), so band / inner = t / R exactly, unless the band
//     would be under MIN_BAND_PX, when it is clamped and the clamp is labelled
//   interior hue: the transmitted PAR photon spectrum τ(λ,t)·n_ph(λ) at 31 rows (400..700 nm
//     every 10 nm) mapped to RGB; brightness from f_photon
//   organism: a disc, saturation = net_carbon_contained / a_max, grey at or below 0
//   one overlay per VIOLATED line, the panel's both-sides text printed beside the wound
(function () {
  "use strict";

  var M = window.DysonModel;
  if (!M) throw new Error("picture: DysonModel not loaded");
  var NS = "http://www.w3.org/2000/svg";
  var W = 420,
    CX = 210,
    CY = 200,
    OUT_MIN = 80, // px at R + t = 10 m
    OUT_MAX = 170, // px at R + t = 101 km
    MIN_BAND_PX = 3,
    LABEL_Y0 = 396,
    LABEL_DY = 32;
  var BG = "#faf8f4";

  function el(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) {
      e.setAttribute(k, attrs[k]);
    });
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }

  // Visible-spectrum approximation (Bruton 1996, piecewise-linear); drawing, not physics.
  function wavelengthRGB(l) {
    var r = 0,
      g = 0,
      b = 0;
    if (l < 440) {
      r = (440 - l) / 60;
      b = 1;
    } else if (l < 490) {
      g = (l - 440) / 50;
      b = 1;
    } else if (l < 510) {
      g = 1;
      b = (510 - l) / 20;
    } else if (l < 580) {
      r = (l - 510) / 70;
      g = 1;
    } else if (l < 645) {
      r = 1;
      g = (645 - l) / 65;
    } else r = 1;
    var f = l < 420 ? 0.3 + (0.7 * (l - 380)) / 40 : l > 700 ? 0.3 : 1;
    return [r * f, g * f, b * f];
  }

  var rows = null;
  function parRows() {
    if (rows) return rows;
    var T = M.spectralTable();
    var idx = [];
    for (var i = 0; i < T.parLam.length; i++)
      if (T.parLam[i] % 10 === 0) idx.push(i);
    if (idx.length !== 31)
      throw new Error("picture: expected 31 PAR rows, got " + idx.length);
    rows = {
      lam: idx.map(function (i) {
        return T.parLam[i];
      }),
      k: Float64Array.from(idx, function (i) {
        return T.parK[i];
      }),
      nph: idx.map(function (i) {
        return T.parN[i];
      }),
    };
    return rows;
  }

  function interiorColour(res) {
    var P = parRows();
    var tau = M.transmissionSpectrum(res.t, {
      k: P.k,
      optical_law: res.inp.optical_law,
      n_interior: res.inp.n_interior,
    });
    var c = [0, 0, 0];
    for (var i = 0; i < P.lam.length; i++) {
      var w = tau[i] * P.nph[i];
      var q = wavelengthRGB(P.lam[i]);
      c[0] += w * q[0];
      c[1] += w * q[1];
      c[2] += w * q[2];
    }
    var mx = Math.max(c[0], c[1], c[2]);
    var v = Math.max(0, Math.min(1, res.report.f_photon)); // brightness = f_photon
    return c.map(function (x) {
      // a pale tint of the transmitted colour, scaled by f_photon
      var chroma = mx > 0 ? x / mx : 0;
      return Math.round(255 * v * (0.55 + 0.45 * chroma));
    });
  }

  function outerRadius(R, t) {
    var x = (Math.log10(R + t) - 1) / (Math.log10(101000) - 1);
    return OUT_MIN + (OUT_MAX - OUT_MIN) * Math.max(0, Math.min(1, x));
  }

  function fmtE(x) {
    return x.toExponential(2);
  }

  function label(parent, x, y, anchor, text) {
    // both sides on two lines, split at " vs " so the concatenated text is the panel's
    var cut = text.indexOf(" vs ");
    var tx = el(
      "text",
      {
        x: x,
        y: y,
        "text-anchor": anchor,
        "font-size": 11,
        fill: "#1b1b1b",
      },
      parent,
    );
    el("tspan", { x: x, dy: 0 }, tx, cut < 0 ? text : text.slice(0, cut));
    if (cut >= 0) el("tspan", { x: x, dy: 13 }, tx, text.slice(cut));
    return tx;
  }

  var DRAW = {
    // fracture across the wall at the upper right; the break is where the numbers sit
    BURST: function (g, geo, text) {
      var a = -Math.PI / 4;
      var pts = [];
      var r0 = geo.ri - 10,
        r1 = geo.ro + 10;
      for (var i = 0; i <= 6; i++) {
        var rr = r0 + ((r1 - r0) * i) / 6;
        var j = (i % 2 ? 1 : -1) * 0.05;
        pts.push(
          (CX + rr * Math.cos(a + j)).toFixed(1) +
            "," +
            (CY + rr * Math.sin(a + j)).toFixed(1),
        );
      }
      el(
        "polyline",
        { points: pts.join(" "), fill: "none", stroke: BG, "stroke-width": 6 },
        g,
      );
      el(
        "polyline",
        {
          points: pts.join(" "),
          fill: "none",
          stroke: "#8a3b2a",
          "stroke-width": 2,
        },
        g,
      );
      var ex = CX + (r1 + 4) * Math.cos(a),
        ey = CY + (r1 + 4) * Math.sin(a);
      label(g, Math.min(W - 4, ex + 4), Math.max(14, ey - 16), "end", text);
    },
    // frost over the interior
    FREEZE: function (g, geo, text, slot) {
      el(
        "circle",
        { cx: CX, cy: CY, r: geo.ri, fill: "#ffffff", "fill-opacity": 0.55 },
        g,
      );
      for (var i = 0; i < 9; i++) {
        var a = (i * 2 * Math.PI) / 9,
          rr = geo.ri * (0.55 + 0.3 * (i % 2));
        var x = CX + rr * Math.cos(a),
          y = CY + rr * Math.sin(a),
          s = Math.max(3, geo.ri * 0.08);
        for (var k = 0; k < 3; k++) {
          var b = (k * Math.PI) / 3;
          el(
            "line",
            {
              x1: (x - s * Math.cos(b)).toFixed(1),
              y1: (y - s * Math.sin(b)).toFixed(1),
              x2: (x + s * Math.cos(b)).toFixed(1),
              y2: (y + s * Math.sin(b)).toFixed(1),
              stroke: "#7aa7c7",
              "stroke-width": 1.2,
            },
            g,
          );
        }
      }
      label(g, CX, LABEL_Y0 + slot * LABEL_DY, "middle", text);
    },
    // dried: the interior goes to a cracked tan
    BOIL: function (g, geo, text, slot) {
      el(
        "circle",
        { cx: CX, cy: CY, r: geo.ri, fill: "#b89a64", "fill-opacity": 0.7 },
        g,
      );
      for (var i = 0; i < 7; i++) {
        var a = (i * 2 * Math.PI) / 7 + 0.3;
        el(
          "path",
          {
            d:
              "M" +
              CX +
              "," +
              CY +
              " L" +
              (CX + geo.ri * 0.5 * Math.cos(a + 0.15)).toFixed(1) +
              "," +
              (CY + geo.ri * 0.5 * Math.sin(a + 0.15)).toFixed(1) +
              " L" +
              (CX + geo.ri * 0.95 * Math.cos(a)).toFixed(1) +
              "," +
              (CY + geo.ri * 0.95 * Math.sin(a)).toFixed(1),
            fill: "none",
            stroke: "#6b5431",
            "stroke-width": 1,
          },
          g,
        );
      }
      label(g, CX, LABEL_Y0 + slot * LABEL_DY, "middle", text);
    },
    // the disc fades
    STARVE: function (g, geo, text, slot) {
      el(
        "circle",
        { cx: CX, cy: CY, r: geo.rOrg, fill: BG, "fill-opacity": 0.7 },
        g,
      );
      el(
        "circle",
        {
          cx: CX,
          cy: CY,
          r: geo.rOrg,
          fill: "none",
          stroke: "#5d5d5d",
          "stroke-dasharray": "3 3",
        },
        g,
      );
      label(g, CX, LABEL_Y0 + slot * LABEL_DY, "middle", text);
    },
    // the interior darkens under its own wall
    OPAQUE: function (g, geo, text, slot) {
      el(
        "circle",
        { cx: CX, cy: CY, r: geo.ri, fill: "#000000", "fill-opacity": 0.6 },
        g,
      );
      label(g, CX, LABEL_Y0 + slot * LABEL_DY, "middle", text);
    },
  };

  function clear(svg) {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
  }

  // res: verdict.js's resolved state; texts: the panel's both-sides string per line.
  function draw(res, texts) {
    var svg = document.getElementById("pic");
    if (!svg) throw new Error("picture: missing #pic");
    clear(svg);
    var R = res.s.R,
      t = res.t,
      rep = res.report;
    var ro = outerRadius(R, t);
    var riTrue = (ro * R) / (R + t);
    var clamped = ro - riTrue < MIN_BAND_PX;
    var ri = clamped ? ro - MIN_BAND_PX : riTrue;
    var rOrg = Math.max(4, 0.3 * ri);
    var geo = { ro: ro, ri: ri, rOrg: rOrg };
    var bad = rep.violated.slice();
    var lowSlots = bad.filter(function (n) {
      return n !== "BURST";
    }).length;
    var H = LABEL_Y0 + Math.max(1, lowSlots) * LABEL_DY + 4;
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);

    el("title", {}, svg, "Cross-section of the vessel");
    el(
      "desc",
      {},
      svg,
      "Ice sphere, radius R " +
        (R >= 1000 ? (R / 1000).toFixed(3) + " km" : R.toFixed(1) + " m") +
        ", wall t " +
        t.toPrecision(4) +
        " m, t/R " +
        fmtE(t / R) +
        (clamped ? " (wall drawn at a " + MIN_BAND_PX + " px minimum)" : "") +
        "; f_photon " +
        rep.f_photon.toFixed(3) +
        "; " +
        (bad.length ? "violated: " + bad.join(", ") : "every line holds") +
        ".",
    );

    var rgb = interiorColour(res);
    el(
      "circle",
      { id: "pic-outer", cx: CX, cy: CY, r: ro.toFixed(4), fill: "#b9d3e3" },
      svg,
    );
    el(
      "circle",
      {
        id: "pic-inner",
        cx: CX,
        cy: CY,
        r: ri.toFixed(4),
        fill: "rgb(" + rgb[0] + ", " + rgb[1] + ", " + rgb[2] + ")",
      },
      svg,
    );
    var sat = Math.max(0, Math.min(1, rep.lines.STARVE.lhs / res.org.a_max));
    el(
      "circle",
      {
        id: "pic-organism",
        cx: CX,
        cy: CY,
        r: rOrg.toFixed(2),
        fill: "hsl(120, " + (100 * sat).toFixed(1) + "%, 32%)",
        "data-saturation": sat.toFixed(4),
      },
      svg,
    );

    el(
      "text",
      { x: 6, y: 16, "font-size": 11, fill: "#5d5d5d" },
      svg,
      "t/R " + fmtE(t / R) + " · drawn size log-scaled in R + t",
    );
    if (clamped)
      el(
        "text",
        { id: "pic-clamp", x: 6, y: 30, "font-size": 11, fill: "#8a3b2a" },
        svg,
        "wall clamped to " +
          MIN_BAND_PX +
          " px; at true t/R " +
          fmtE(t / R) +
          " it would be " +
          (ro - riTrue).toFixed(2) +
          " px",
      );

    var g = el("g", { id: "pic-overlays" }, svg);
    var slot = 0;
    bad.forEach(function (n) {
      var fn = DRAW[n];
      if (!fn) throw new Error("picture: no overlay for line " + n);
      var og = el("g", { id: "pic-ov-" + n, "data-line": n }, g);
      fn(og, geo, texts[n], n === "BURST" ? 0 : slot++);
    });
  }

  function blank(msg) {
    var svg = document.getElementById("pic");
    if (!svg) return;
    clear(svg);
    el("title", {}, svg, "Cross-section of the vessel");
    el("desc", {}, svg, "No picture: " + msg);
  }

  window.DysonPicture = { draw: draw, blank: blank, MIN_BAND_PX: MIN_BAND_PX };
})();
