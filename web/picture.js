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
  var W = 400,
    H = 440,
    CX = 200,
    CY = 222,
    OUT_MIN = 100, // px at R + t = 10 m
    OUT_MAX = 148, // px at R + t = 101 km
    MIN_BAND_PX = 3,
    FS = 17, // >= 12 px on screen at the page's figure width (smoke asserts it)
    LH = 19,
    PLATE_GAP = 10, // units between the organism disc and a plate
    KEEP_PAD = 3, // units every mark keeps clear of a plate
    WRAP = 20,
    MARGIN = 12, // every plate keeps this far inside the picture's edge
    FIT_PAD = 14, // interior plates keep this far inside the wall (the OPAQUE gauge runs there)
    CLAMP_Y = 378;
  var NS = "http://www.w3.org/2000/svg";
  var BG = "#faf8f4",
    INK = "#1b1b1b",
    RIM = "#3d6f8e", // outer-circle outline: the vessel edge against the page
    MUTED = "#5d5d5d",
    FAIL = "#8a3b2a";

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
    // brightness: a monotone map of the model's f_photon (sqrt, so the declared floor 0.25
    // sits at mid-dark 0.5 and an alive interior above it is visibly brighter)
    var v = Math.sqrt(Math.max(0, Math.min(1, res.report.f_photon)));
    return c.map(function (x) {
      var chroma = mx > 0 ? x / mx : 0; // hue of the transmitted PAR photon spectrum
      return Math.round(255 * v * (0.2 + 0.8 * chroma));
    });
  }

  function outerRadius(R, t) {
    var x = (Math.log10(R + t) - 1) / (Math.log10(101000) - 1);
    return OUT_MIN + (OUT_MAX - OUT_MIN) * Math.max(0, Math.min(1, x));
  }

  function fmtE(x) {
    return x.toExponential(2);
  }
  function pt(r, a) {
    return [CX + r * Math.cos(a), CY + r * Math.sin(a)];
  }
  function P2(p) {
    return p[0].toFixed(1) + "," + p[1].toFixed(1);
  }

  // Break text into lines of <= WRAP chars at spaces; each later line keeps its leading
  // space, so the concatenated textContent is exactly the input (the panel's string).
  function wrap(text, n) {
    n = n || WRAP;
    var out = [],
      cur = "";
    text.split(/(?= )/).forEach(function (w) {
      if (cur && (cur + w).length > n) {
        out.push(cur);
        cur = w;
      } else cur += w;
    });
    if (cur) out.push(cur);
    return out;
  }

  // The killing text: first line (the violated side) bold in the failure colour.
  // (x, y) is the top-left for anchor "start", top-right for "end", top-centre for "middle".
  function label(parent, x, y, anchor, text, plate, n) {
    var lines = wrap(text, n);
    var wmax = Math.max.apply(null, lines.map(function (l) { return l.trim().length; }));
    var w = wmax * FS * 0.64 + 10,
      h = lines.length * LH + 6;
    var x0 = anchor === "end" ? x - w : anchor === "middle" ? x - w / 2 : x;
    if (plate)
      el("rect", { x: x0.toFixed(1), y: (y - 2).toFixed(1), width: w.toFixed(1), height: h.toFixed(1),
        rx: 4, fill: "#ffffff", "fill-opacity": 0.92, stroke: FAIL, "stroke-width": 1 }, parent);
    var tx = el("text", { x: x0 + 5, y: y + FS - 1, "font-size": FS, fill: INK }, parent);
    lines.forEach(function (l, i) {
      var a = { x: (x0 + 5).toFixed(1), dy: i ? LH : 0 };
      if (i === 0) {
        a["font-weight"] = 700;
        a.fill = FAIL;
      }
      el("tspan", a, tx, l);
    });
    return { x0: x0, y0: y - 2, w: w, h: h };
  }

  // plate size for a text, before anything is drawn (marks are clipped around it)
  function plateSize(text, n) {
    var lines = wrap(text, n);
    var wmax = Math.max.apply(null, lines.map(function (l) { return l.trim().length; }));
    return { w: wmax * FS * 0.64 + 10, h: lines.length * LH + 6 };
  }
  // Interior plates: one stack, centred on x, inside the interior clear of the wall band by
  // FIT_PAD. The disc stays at the centre when the stack fits above it; otherwise the stack
  // rises as high as the widest plate's corners allow and the disc moves down beneath it.
  // Returns {boxes: {line: box}, oy: disc centre y}.
  function layoutInterior(ri, rOrg, names, texts) {
    if (!names.length) return { boxes: {}, oy: CY, wrap: WRAP };
    var rf = ri - FIT_PAD, best = null;
    // the widest wrap whose stack and disc both fit; narrower wraps trade width for height
    for (var n = WRAP; n >= 10 && !(best && best.fits); n--) best = stackAt(n);
    return best;

    function stackAt(n) {
      var sz = names.map(function (k) { return plateSize(texts[k], n); });
      var Hs = sz.reduce(function (a, z) { return a + z.h; }, 0) + 6 * (sz.length - 1);
      var Ws = Math.max.apply(null, sz.map(function (z) { return z.w; }));
      var a = rf > Ws / 2 ? Math.sqrt(rf * rf - (Ws * Ws) / 4) : 0; // highest top the corners allow
      var centred = rOrg + PLATE_GAP + Hs; // top height above centre with the disc left centred
      var top, oy;
      if (centred <= a) {
        top = CY - centred;
        oy = CY;
      } else {
        top = CY - a;
        oy = top + Hs + PLATE_GAP + rOrg;
      }
      var bot = top + Hs - CY; // stack bottom below centre
      var fits = Ws / 2 < rf && Math.hypot(Ws / 2, bot) <= rf && oy + rOrg <= CY + ri - 4;
      var boxes = {}, y = top;
      names.forEach(function (k, i) {
        boxes[k] = { x0: CX - sz[i].w / 2, y0: y, x1: CX + sz[i].w / 2, y1: y + sz[i].h };
        y += sz[i].h + 6;
      });
      return { boxes: boxes, oy: oy, wrap: n, fits: fits };
    }
  }
  function interiorLabel(g, geo, text, n) {
    var b = geo.boxes[n];
    label(g, CX, b.y0 + 2, "middle", text, true, geo.wrap);
  }
  // the parts of segment ab outside every keep-out rect (padded), for marks near a plate
  function outside(a, b, rects) {
    var pieces = [[a, b]];
    rects.forEach(function (R) {
      var next = [];
      pieces.forEach(function (sg) {
        var p = sg[0], q = sg[1], dx = q[0] - p[0], dy = q[1] - p[1], t0 = 0, t1 = 1, ok = true;
        [[-dx, p[0] - (R.x0 - KEEP_PAD)], [dx, R.x1 + KEEP_PAD - p[0]],
         [-dy, p[1] - (R.y0 - KEEP_PAD)], [dy, R.y1 + KEEP_PAD - p[1]]].forEach(function (c) {
          if (!ok) return;
          if (c[0] === 0) { if (c[1] < 0) ok = false; return; }
          var t = c[1] / c[0];
          if (c[0] < 0) t0 = Math.max(t0, t); else t1 = Math.min(t1, t);
        });
        if (!ok || t0 > t1) { next.push(sg); return; }
        var at = function (t) { return [p[0] + dx * t, p[1] + dy * t]; };
        if (t0 > 1e-6) next.push([p, at(t0)]);
        if (t1 < 1 - 1e-6) next.push([at(t1), q]);
      });
      pieces = next;
    });
    return pieces;
  }
  function segs(g, pts, attrs, rects) {
    for (var i = 1; i < pts.length; i++)
      outside(pts[i - 1], pts[i], rects).forEach(function (sg) {
        var a = Object.assign({ x1: sg[0][0].toFixed(1), y1: sg[0][1].toFixed(1),
          x2: sg[1][0].toFixed(1), y2: sg[1][1].toFixed(1) }, attrs);
        el("line", a, g);
      });
  }
  function ring(g, r, attrs, rects) {
    var pts = [];
    for (var i = 0; i <= 96; i++) pts.push(pt(r, (i * 2 * Math.PI) / 96));
    segs(g, pts, attrs, rects);
  }

  var DRAW = {
    // a gap through the whole wall band at the upper right, cracks radiating from it, and
    // the killing numbers outside the rim on a leader
    BURST: function (g, geo, text) {
      var a = -0.9,
        da = 0.05;
      var r0 = geo.ri - 1,
        r1 = geo.ro + 1;
      el("path", {
        d: "M" + P2(pt(r0, a - da)) + " L" + P2(pt(r1, a - da * 1.6)) + " L" + P2(pt(r1, a + da * 1.6)) +
          " L" + P2(pt(r0, a + da)) + " Z",
        fill: BG, "data-mark": "gap",
      }, g);
      [[-1, 0.6], [1, 0.6], [-1, -0.5], [1, -0.5], [0, 1], [0, -0.9]].forEach(function (c) {
        var side = a + c[0] * da * 1.3,
          out = c[1] > 0;
        var p = [pt(out ? r1 : r0, side)];
        var steps = 3,
          len = 16 + 10 * Math.abs(c[1]);
        for (var i = 1; i <= steps; i++) {
          var rr = (out ? r1 : r0) + (out ? 1 : -1) * (len * i) / steps;
          p.push(pt(rr, side + c[0] * 0.06 * i + (i % 2 ? 0.03 : -0.03)));
        }
        segs(g, p, { stroke: FAIL, "stroke-width": 2, "stroke-linecap": "round" }, geo.keep);
      });
      var b = label(g, W - MARGIN, MARGIN, "end", text, true);
      var from = pt(r1 + 26, a);
      el("line", { x1: P2(from).split(",")[0], y1: P2(from).split(",")[1],
        x2: (b.x0 + b.w / 2).toFixed(1), y2: (b.y0 + b.h).toFixed(1), stroke: FAIL, "stroke-width": 1.5 }, g);
    },
    // frost at the wall, inward to the disc's edge: it never covers the organism
    FREEZE: function (g, geo, text, n) {
      var inner = geo.rOrg + 4;
      el("path", {
        d: "M" + (CX - geo.ri) + "," + CY + " a" + geo.ri + "," + geo.ri + " 0 1,0 " + 2 * geo.ri + ",0 a" +
          geo.ri + "," + geo.ri + " 0 1,0 " + -2 * geo.ri + ",0 Z M" + (CX - inner) + "," + geo.oy + " a" + inner + "," +
          inner + " 0 1,1 " + 2 * inner + ",0 a" + inner + "," + inner + " 0 1,1 " + -2 * inner + ",0 Z",
        fill: "#ffffff", "fill-opacity": 0.6, "fill-rule": "evenodd", "data-mark": "frost",
      }, g);
      for (var i = 0; i < 12; i++) {
        var p = pt(geo.ri * (0.72 + 0.16 * (i % 2)), (i * 2 * Math.PI) / 12 + 0.2),
          s = Math.max(4, geo.ri * 0.07);
        var near = geo.keep.some(function (R) {
          return p[0] + s + KEEP_PAD > R.x0 && p[0] - s - KEEP_PAD < R.x1 && p[1] + s + KEEP_PAD > R.y0 && p[1] - s - KEEP_PAD < R.y1;
        });
        if (near) continue;
        for (var k = 0; k < 3; k++) {
          var bb = (k * Math.PI) / 3;
          el("line", { x1: (p[0] - s * Math.cos(bb)).toFixed(1), y1: (p[1] - s * Math.sin(bb)).toFixed(1),
            x2: (p[0] + s * Math.cos(bb)).toFixed(1), y2: (p[1] + s * Math.sin(bb)).toFixed(1),
            stroke: "#5f8fb3", "stroke-width": 1.5 }, g);
        }
      }
      interiorLabel(g, geo, text, n);
    },
    // boiling off: a warm vapour haze with rising bubbles (round, open marks: nothing here
    // reads as a crack, which is BURST's mark)
    BOIL: function (g, geo, text, n) {
      el("circle", { cx: CX, cy: CY, r: geo.ri, fill: "#f3e3c4", "fill-opacity": 0.7, "data-mark": "vapour" }, g);
      var bg = el("g", { "data-mark": "bubbles" }, g);
      for (var i = 0; i < 26; i++) {
        var a = i * 2.39996, // golden-angle scatter over the interior
          rr = geo.ri * (0.25 + 0.68 * Math.sqrt(((i * 7) % 26) / 25)),
          p = pt(rr, a),
          s = 3 + (i % 4) * 2;
        var clear = Math.hypot(p[0] - CX, p[1] - CY) + s < geo.ri - 2 &&
          Math.hypot(p[0] - CX, p[1] - geo.oy) > geo.rOrg + s + 4 &&
          !geo.keep.some(function (R) {
            return p[0] + s + KEEP_PAD > R.x0 && p[0] - s - KEEP_PAD < R.x1 && p[1] + s + KEEP_PAD > R.y0 && p[1] - s - KEEP_PAD < R.y1;
          });
        if (clear)
          el("circle", { cx: p[0].toFixed(1), cy: p[1].toFixed(1), r: s, fill: "none", stroke: "#b5651d",
            "stroke-width": 1.8 }, bg);
      }
      interiorLabel(g, geo, text, n);
    },
    // the disc fades (draw() lowers its opacity); a dashed ring marks it
    STARVE: function (g, geo, text, n) {
      el("circle", { cx: CX, cy: geo.oy, r: geo.rOrg + 5, fill: "none", stroke: FAIL, "stroke-dasharray": "4 3",
        "stroke-width": 1.5, "data-mark": "fade-ring" }, g);
      interiorLabel(g, geo, text, n);
    },
    // under its own wall: a veil, and a light gauge just inside the wall: the amber arc runs
    // clockwise from 12 o'clock for f_photon of the turn, the white tick stands at the declared
    // f_floor; the arc stopping short of the tick is the failure
    OPAQUE: function (g, geo, text, n, rep) {
      el("circle", { cx: CX, cy: CY, r: geo.ri, fill: "#000000", "fill-opacity": 0.35, "data-mark": "veil" }, g);
      var rg = geo.ri - 7,
        f = Math.max(0, Math.min(1, rep.lines.OPAQUE.lhs)),
        ff = Math.max(0, Math.min(1, rep.lines.OPAQUE.rhs));
      var arc = function (f0, f1) {
        var pts = [], k = Math.max(2, Math.ceil((f1 - f0) * 96));
        for (var i = 0; i <= k; i++) pts.push(pt(rg, -Math.PI / 2 + 2 * Math.PI * (f0 + ((f1 - f0) * i) / k)));
        return pts;
      };
      var gg = el("g", { "data-mark": "light-gauge" }, g);
      segs(gg, arc(0, 1), { stroke: "#d8d2c4", "stroke-opacity": 0.75, "stroke-width": 2 }, geo.keep);
      segs(gg, arc(0, f), { stroke: "#ffb000", "stroke-width": 6, "stroke-linecap": "butt" }, geo.keep);
      var fr = el("g", { "data-mark": "floor-ring" }, g);
      var af = -Math.PI / 2 + 2 * Math.PI * ff;
      segs(fr, [pt(rg - 9, af), pt(rg + 5, af)], { stroke: "#ffffff", "stroke-width": 3 }, geo.keep);
      interiorLabel(g, geo, text, n);
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
    var rOrg = Math.max(6, 0.28 * ri);
    var bad = rep.violated.slice();
    var lay = layoutInterior(ri, rOrg, bad.filter(function (n) { return n !== "BURST"; }), texts);
    var geo = { ro: ro, ri: ri, rOrg: rOrg, oy: lay.oy, boxes: lay.boxes, wrap: lay.wrap };
    geo.keep = Object.keys(lay.boxes).map(function (n) { return lay.boxes[n]; });
    svg.setAttribute("viewBox", "0 0 " + W + " " + H);

    el("title", {}, svg, "Cross-section of the vessel");
    el("desc", {}, svg,
      "Ice sphere, radius R " + (R >= 1000 ? (R / 1000).toFixed(3) + " km" : R.toFixed(1) + " m") +
        ", wall t " + t.toPrecision(4) + " m, t/R " + fmtE(t / R) +
        (clamped ? " (wall drawn at a " + MIN_BAND_PX + " px minimum)" : "") +
        "; f_photon " + rep.f_photon.toFixed(3) +
        "; " + (bad.length ? "violated: " + bad.join(", ") : "every line holds") + ".");

    var rgb = interiorColour(res);
    el("circle", { id: "pic-outer", cx: CX, cy: CY, r: ro.toFixed(4), fill: "#b9d3e3", stroke: RIM,
      "stroke-width": 1.5 }, svg);
    el("circle", { id: "pic-inner", cx: CX, cy: CY, r: ri.toFixed(4),
      fill: "rgb(" + rgb[0] + ", " + rgb[1] + ", " + rgb[2] + ")" }, svg);

    // overlays sit under the organism, so no mark recolours the disc
    var g = el("g", { id: "pic-overlays" }, svg);
    bad.forEach(function (n) {
      var fn = DRAW[n];
      if (!fn) throw new Error("picture: no overlay for line " + n);
      var og = el("g", { id: "pic-ov-" + n, "data-line": n }, g);
      fn(og, geo, texts[n], n, rep);
    });

    var net = rep.lines.STARVE.lhs;
    var sat = Math.max(0, Math.min(1, net / res.org.a_max));
    el("circle", { id: "pic-organism", cx: CX, cy: geo.oy.toFixed(2), r: rOrg.toFixed(2),
      fill: "hsl(120, " + (100 * sat).toFixed(1) + "%, 32%)",
      stroke: net > 0 ? "#1f7a1f" : "#8a8a8a", "stroke-width": 2.5,
      "fill-opacity": rep.lines.STARVE.violated ? 0.35 : 1,
      "data-saturation": sat.toFixed(4) }, svg);

    if (clamped) {
      var tip = pt(ro, (3 * Math.PI) / 4);
      el("line", { id: "pic-clamp-leader", x1: tip[0].toFixed(1), y1: tip[1].toFixed(1), x2: 40, y2: CLAMP_Y - 4,
        stroke: MUTED, "stroke-width": 1.2 }, svg);
      var ct = el("text", { id: "pic-clamp", x: 6, y: CLAMP_Y + FS, "font-size": FS, fill: FAIL }, svg);
      el("tspan", { x: 6, dy: 0 }, ct, "wall clamped to " + MIN_BAND_PX + " px;");
      el("tspan", { x: 6, dy: LH }, ct,
        " true t/R " + fmtE(t / R) + " would draw " + (ro - riTrue).toFixed(2) + " px");
    }
    el("text", { x: 6, y: H - 6, "font-size": FS, fill: MUTED }, svg,
      "t/R " + fmtE(t / R) + " · size log-scaled in R + t");
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
