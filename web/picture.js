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
    CX = 200,
    MARGIN = 20, // every plate keeps this far inside the picture's edge
    // a plate strip above (and, past two plates, below) the vessel, tall enough for
    // PLATE_LINES lines: BURST's "p·R/2t 700000.0 Pa vs σ_eff(T_shell) 0.0 Pa" needs 5 in a
    // column, whose width holds exactly the 14-character σ_eff(T_shell)
    PLATE_LINES = 5,
    STRIP_H = PLATE_LINES * 19 + 2 * 10 - 2, // lines * LH + 2 * PLATE_PAD - 2, as plateSize
    STRIP_GAP = 12, // strip to the vessel's largest rim
    CY = 20 + STRIP_H + 12 + 148, // MARGIN + STRIP_H + STRIP_GAP + OUT_MAX: never moves
    OUT_MIN = 100, // px at R + t = 10 m
    OUT_MAX = 148, // px at R + t = 101 km
    MIN_BAND_PX = 3,
    FS = 17, // >= 12 px on screen at the page's figure width (smoke asserts it)
    LH = 19,
    PLATE_PAD = 10, // text inset inside a plate
    ORG_R = 34, // the organism disc: one size and one centre in every state
    KEEP_PAD = 3, // units every mark keeps clear of a plate
    WRAP = 20,
    COL_W = (400 - 2 * 20 - 14) / 2; // two plate columns per strip
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
    var w = wmax * FS * 0.64 + 2 * PLATE_PAD,
      h = lines.length * LH + 2 * PLATE_PAD - 2;
    var x0 = anchor === "end" ? x - w : anchor === "middle" ? x - w / 2 : x;
    if (plate)
      el("rect", { x: x0.toFixed(1), y: (y - 2).toFixed(1), width: w.toFixed(1), height: h.toFixed(1),
        rx: 4, fill: "#ffffff", "fill-opacity": 0.92, stroke: FAIL, "stroke-width": 1 }, parent);
    var tx = el("text", { x: x0 + PLATE_PAD, y: y + FS + PLATE_PAD - 6, "font-size": FS, fill: INK }, parent);
    lines.forEach(function (l, i) {
      var a = { x: (x0 + PLATE_PAD).toFixed(1), dy: i ? LH : 0 };
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
    return { w: wmax * FS * 0.64 + 2 * PLATE_PAD, h: lines.length * LH + 2 * PLATE_PAD - 2 };
  }
  // Plates live OUTSIDE the vessel, in a strip above it (slots 0 right, 1 left) and, past two
  // plates, a strip below (2 right, 3 left); BURST takes slot 0, over its crack. Each plate gets
  // the widest wrap that fits its column and the strip. Returns {line: {box, wrap, slot}}.
  function placePlates(names, texts, below0) {
    var order = names.filter(function (n) { return n === "BURST"; })
      .concat(names.filter(function (n) { return n !== "BURST"; }));
    if (order.length > 4) throw new Error("picture: more than four plates: " + order.join(", "));
    var out = {};
    order.forEach(function (n, slot) {
      // alone in its strip, a plate may use the full width; otherwise one column
      var alone = slot < 2 ? order.length === 1 : order.length === 3;
      var maxW = alone ? W - 2 * MARGIN : COL_W;
      var wr = 34, sz = plateSize(texts[n], wr);
      while (wr > 8 && (sz.w > maxW || sz.h > STRIP_H)) sz = plateSize(texts[n], --wr);
      if (sz.w > maxW || sz.h > STRIP_H) throw new Error("picture: plate for " + n + " fits no wrap");
      var right = slot % 2 === 0, top = slot < 2;
      var x0 = right ? W - MARGIN - sz.w : MARGIN;
      var y0 = top ? MARGIN : below0;
      out[n] = { box: { x0: x0, y0: y0, x1: x0 + sz.w, y1: y0 + sz.h }, wrap: wr, top: top, right: right };
    });
    return out;
  }
  // a plate, and a leader from its inner edge to the wound's anchor point (x1,y1 = the anchor)
  function plateWithLeader(g, pl, text, anchor) {
    var b = pl.box;
    label(g, b.x0, b.y0 + 2, "start", text, true, pl.wrap);
    var lx = Math.max(b.x0 + 8, Math.min(b.x1 - 8, anchor[0]));
    var ends = { x1: anchor[0].toFixed(1), y1: anchor[1].toFixed(1), x2: lx.toFixed(1),
      y2: (pl.top ? b.y1 : b.y0).toFixed(1) };
    // a white halo under the leader, so it reads over a dark (OPAQUE) interior too
    el("line", Object.assign({ stroke: "#ffffff", "stroke-width": 6, "data-mark": "leader-halo" }, ends), g);
    el("line", Object.assign({ stroke: FAIL, "stroke-width": 2, "data-mark": "leader" }, ends), g);
    el("circle", { cx: anchor[0].toFixed(1), cy: anchor[1].toFixed(1), r: 4.5, fill: FAIL, stroke: "#ffffff",
      "stroke-width": 2, "data-mark": "anchor" }, g);
  }
  // an interior wound's anchor: between the disc and the wall, toward the plate
  function interiorAnchor(geo, n) {
    var pl = geo.plates[n];
    var ang = (pl.top ? -Math.PI / 2 : Math.PI / 2) + (pl.right ? 1 : -1) * (pl.top ? 0.45 : -0.45);
    return pt((geo.rOrg + geo.ri) / 2, ang);
  }
  function interiorLabel(g, geo, text, n) {
    plateWithLeader(g, geo.plates[n], text, interiorAnchor(geo, n));
  }
  var INTERIOR = { FREEZE: 1, BOIL: 1, STARVE: 1 };
  var ANCHOR_KEEP = 10; // frost and bubbles keep clear of an interior leader's end dot
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
      var clearOf = geo.keep;
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
        segs(g, p, { stroke: FAIL, "stroke-width": 2, "stroke-linecap": "round" }, clearOf);
      });
      plateWithLeader(g, geo.plates.BURST, text, pt(r1 + 26, a));
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
            var q = s + KEEP_PAD + 3; // radius, stroke and a visible gap
            return p[0] + q > R.x0 && p[0] - q < R.x1 && p[1] + q > R.y0 && p[1] - q < R.y1;
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
      // the leader ends on the arc's tip: the f_photon the plate names
      plateWithLeader(g, geo.plates[n], text, pt(rg, -Math.PI / 2 + 2 * Math.PI * f));
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
    // one disc in every state; only an interior too small for it (never in the shots) shrinks it
    var rOrg = Math.min(ORG_R, 0.5 * ri);
    var bad = rep.violated.slice();
    var below0 = CY + OUT_MAX + STRIP_GAP;
    var plates = placePlates(bad, texts, below0);
    var lower = bad.length > 2 ? STRIP_H + STRIP_GAP : 0;
    var CLAMP_Y = CY + 156 + lower;
    var H = CLAMP_Y + 62; // clamp label (2 lines) or gauge key, then the footer
    var geo = { ro: ro, ri: ri, rOrg: rOrg, oy: CY, plates: plates };
    geo.keep = Object.keys(plates).map(function (n) { return plates[n].box; });
    Object.keys(plates).forEach(function (n) {
      if (!INTERIOR[n]) return;
      var a = interiorAnchor(geo, n);
      geo.keep.push({ x0: a[0] - ANCHOR_KEEP, y0: a[1] - ANCHOR_KEEP, x1: a[0] + ANCHOR_KEEP, y1: a[1] + ANCHOR_KEEP });
    });
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
      stroke: net > 0 ? "#2ecc40" : "#8a8a8a", "stroke-width": 3, // bright mid green: reads on navy and on pale
      "fill-opacity": rep.lines.STARVE.violated ? 0.35 : 1,
      "data-saturation": sat.toFixed(4) }, svg);

    if (clamped) {
      var tip = pt(ro, (3 * Math.PI) / 4);
      el("line", { id: "pic-clamp-leader", x1: tip[0].toFixed(1), y1: tip[1].toFixed(1), x2: 40, y2: CLAMP_Y - 4,
        stroke: MUTED, "stroke-width": 1.2 }, svg);
      var ct = el("text", { id: "pic-clamp", x: 16, y: CLAMP_Y + FS, "font-size": FS, fill: FAIL }, svg);
      el("tspan", { x: 16, dy: 0 }, ct, "wall clamped to " + MIN_BAND_PX + " px;");
      el("tspan", { x: 16, dy: LH }, ct,
        " true t/R " + fmtE(t / R) + " would draw " + (ro - riTrue).toFixed(2) + " px");
    }
    // a key for the OPAQUE gauge, bottom left above the footer (the clamp label's place; a
    // wall thin enough to clamp never darkens the interior below the floor)
    if (rep.lines.OPAQUE.violated) {
      var kt = el("text", { id: "pic-key", x: 16, y: H - 6 - 2 * LH, "font-size": FS, fill: MUTED }, svg);
      el("tspan", { x: 16, dy: 0 }, kt, "amber arc: f_photon reaching in;");
      el("tspan", { x: 16, dy: LH }, kt, " white tick: declared floor");
    }
    el("text", { x: 16, y: H - 6, "font-size": FS, fill: MUTED }, svg,
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
