// The first-failure map (visual-first Task 2): distance r × radius R, one cell per grid point of
// web/map_data.js (tools/make_map.mjs), coloured by the first line the auto design violates there,
// with the registered P1/P2 bands and the current design dot. Classic script.
//
// Drawing only: every cell class is the precomputed model output; the colours are the picture's
// own marks (web/picture.js PALETTE). The only numbers this file owns are pixel constants.
//
//   x = log10 r over the grid's range, y = log10 R (labelled in km), larger R upward
//   cell (i, j) is centred on grid point (i, j) and clipped at the map edge, so the frame spans
//     exactly the grid's range and the slider extremes sit on the frame, never off it
//   the dot is the exact (r, R) the verdict evaluates; "the cell under the dot" is the nearest
//     grid point (cellAt), which is what the reader sees: its rect contains the dot
(function () {
  "use strict";

  var D = window.DysonMap;
  if (!D) throw new Error("mapview: DysonMap (web/map_data.js) not loaded");
  var PIC = window.DysonPicture;
  if (!PIC || !PIC.PALETTE) throw new Error("mapview: DysonPicture.PALETTE (web/picture.js) not loaded");
  var PAL = PIC.PALETTE;
  var GR = D.grid.r_log10, GRR = D.grid.R_log10;
  var NR = GR[2], NRR = GRR[2];
  D.classes.forEach(function (c) {
    if (!(c in PAL)) throw new Error("mapview: no palette colour for class " + c);
  });

  var NS = "http://www.w3.org/2000/svg";
  var W = 640,
    L = 64, // frame left: y tick labels and the rotated axis title sit left of it
    T = 112, // frame top: title, status line (live recompute), P2 label, P2 off-map note
    STATUS_Y = 44, // baseline of the recompute status, above the frame, never over the cells
    P2_Y = 68, // baseline of the P2 label
    P2_NOTE_Y = 90, // baseline of the P2 off-map note: its plate ends 16 px above the frame, clear of any dot mark
    PW = 540,
    PH = 405, // 80 × 60 cells at 6.75 px square
    FS = 14, // >= 12 px on screen at the page's map width (smoke asserts it)
    KEY_ROW = 22,
    EDGE_TOL = 5e-4, // decades: r is read rounded to 0.001 AU, so 0.500 AU is 7e-5 inside the grid
    INK = "#1b1b1b",
    MUTED = "#5d5d5d",
    AXIS = "#9a948b",
    BAND = "#8a8378";
  var LABEL = {
    HELD: "HELD (every line holds)",
    BURST: "BURST",
    FREEZE: "FREEZE",
    BOIL: "BOIL",
    STARVE: "STARVE",
    OPAQUE: "OPAQUE",
    NO_DESIGN: "no design (solver found none)",
  };

  function el(tag, attrs, parent, text) {
    var e = document.createElementNS(NS, tag);
    Object.keys(attrs || {}).forEach(function (k) {
      e.setAttribute(k, attrs[k]);
    });
    if (text !== undefined) e.textContent = text;
    if (parent) parent.appendChild(e);
    return e;
  }
  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }
  function lg(v) {
    return Math.log(v) / Math.LN10;
  }
  function clampN(v, lo, hi) {
    return Math.max(lo, Math.min(hi, v));
  }
  var X = function (lr) { return L + ((lr - GR[0]) / (GR[1] - GR[0])) * PW; };
  var Y = function (lR) { return T + PH - ((lR - GRR[0]) / (GRR[1] - GRR[0])) * PH; };
  var DX = (GR[1] - GR[0]) / (NR - 1), DY = (GRR[1] - GRR[0]) / (NRR - 1);

  // nearest grid point in log space, clamped to the grid
  function nearest(g, lv) {
    return clampN(Math.round(((lv - g[0]) * (g[2] - 1)) / (g[1] - g[0])), 0, g[2] - 1);
  }
  function cellAt(r_au, R_m) {
    return { i: nearest(GR, lg(r_au)), j: nearest(GRR, lg(R_m)) };
  }
  function classOf(slice, i, j) {
    var c = D.classes[Number(slice.charAt(i * NRR + j))];
    if (!c) throw new Error("mapview: slice has no class at i=" + i + " j=" + j);
    return c;
  }
  function fillOf(c) {
    return c === "NO_DESIGN" ? "url(#map-hatch-nd)" : PAL[c];
  }

  var bands = null; // set once by verdict.js (it owns the registered values)
  var pickFns = [];
  var built = null; // {svg, key, layers}

  function defs(svg) {
    var d = el("defs", {}, svg);
    function hatch(id, colour, opacity, bg) {
      var p = el("pattern", { id: id, width: 6, height: 6, patternUnits: "userSpaceOnUse",
        patternTransform: "rotate(45)" }, d);
      if (bg) el("rect", { width: 6, height: 6, fill: bg }, p);
      el("line", { x1: 0, y1: 0, x2: 0, y2: 6, stroke: colour, "stroke-width": 2, opacity: opacity }, p);
    }
    hatch("map-hatch-nd", PAL.NO_DESIGN, 1, "#faf8f4");
    hatch("map-hatch-band", "#ffffff", 0.8, null);
    hatch("map-hatch-prov", "#ffffff", 0.6, null); // over a coarse preview: provisional
    var f = el("filter", { id: "map-desat" }, d);
    el("feColorMatrix", { type: "saturate", values: 0.3 }, f);
  }
  // a registered result as a prediction outcome; the legend's HELD means "your design survives"
  function outcome(v) {
    var o = { HELD: "confirmed", FAILED: "falsified" }[v];
    if (!o) throw new Error("mapview: registered result is neither HELD nor FAILED (" + v + ")");
    return o;
  }

  function axes(svg) {
    var g = el("g", { id: "map-axes" }, svg);
    [0.5, 1, 2, 5, 10, 20, 50, 100].forEach(function (r) {
      var x = X(lg(r));
      el("line", { x1: x, y1: T + PH, x2: x, y2: T + PH + 5, stroke: AXIS }, g);
      el("text", { x: x, y: T + PH + 20, "text-anchor": "middle", "font-size": FS, fill: MUTED }, g, String(r));
    });
    el("text", { x: L + PW / 2, y: T + PH + 40, "text-anchor": "middle", "font-size": FS, fill: MUTED }, g,
      "distance r (AU, log scale)");
    [[1, "0.01"], [2, "0.1"], [3, "1"], [4, "10"], [5, "100"]].forEach(function (t) {
      var y = Y(t[0]);
      el("line", { x1: L - 5, y1: y, x2: L, y2: y, stroke: AXIS }, g);
      el("text", { x: L - 8, y: y + 5, "text-anchor": "end", "font-size": FS, fill: MUTED }, g, t[1]);
    });
    el("text", { x: 16, y: T + PH / 2, "text-anchor": "middle", "font-size": FS, fill: MUTED,
      transform: "rotate(-90 16 " + (T + PH / 2) + ")" }, g, "vessel radius R (km, log scale)");
  }

  function drawCells(g, slice) {
    for (var i = 0; i < NR; i++) {
      var xa = Math.max(L, X(GR[0] + (i - 0.5) * DX)), xb = Math.min(L + PW, X(GR[0] + (i + 0.5) * DX));
      for (var j = 0; j < NRR; j++) {
        var ya = Math.max(T, Y(GRR[0] + (j + 0.5) * DY)), yb = Math.min(T + PH, Y(GRR[0] + (j - 0.5) * DY));
        var c = classOf(slice, i, j);
        el("rect", { x: xa, y: ya, width: xb - xa, height: yb - ya, fill: fillOf(c),
          "data-cell": "", "data-i": i, "data-j": j, "data-class": c }, g);
      }
    }
  }

  // text width estimate for layout only (sans-serif averages under 0.6 em per character)
  function textW(t) {
    return t.length * FS * 0.6;
  }
  // a flowing key: each entry as wide as its label, wrapping inside the frame's width
  // off the registered run (a card played, or a declared assumption off its default): the P1/P2 and
  // r_close labels stay, marked †, and the key says they are the registered run's, not this design's
  function offRegistered(state) {
    return state.cardsPlayed > 0 || !!state.advancedChanged;
  }
  function legend(g, slice, y0, sigma_MPa, off, same) {
    var present = D.classes.filter(function (c) {
      return c === "NO_DESIGN" || slice === null || slice.indexOf(String(D.classes.indexOf(c))) >= 0;
    });
    var x = L, y = y0, rows = 1;
    present.forEach(function (c) {
      var w = 24 + textW(LABEL[c]) + 22;
      if (x > L && x + w > L + PW) {
        x = L;
        y += KEY_ROW;
        rows++;
      }
      el("rect", { id: "map-key-" + c, x: x, y: y - 11, width: 18, height: 12, fill: fillOf(c),
        stroke: AXIS, "stroke-width": 0.8 }, g);
      el("text", { x: x + 24, y: y, "font-size": FS, fill: INK }, g, LABEL[c]);
      x += w;
    });
    y += KEY_ROW;
    rows++;
    el("text", { id: "map-key-note", x: L, y: y, "font-size": FS, fill: INK }, g,
      "cells: model at cell centres · dot: your exact design");
    if (same) {
      y += KEY_ROW;
      rows++;
      el("text", { id: "map-same-note", x: L, y: y, "font-size": FS, fill: MUTED }, g,
        "same map for algal and vascular at this σ");
    }
    // the order the lines are checked in: a cell names only the first to fail
    if (!bands || !bands.order) throw new Error("mapview: line order not set (verdict.js passes LOAD_ORDER)");
    var ord = el("text", { id: "map-order-note", x: L, y: y + KEY_ROW, "font-size": FS, fill: INK }, g);
    wrap("checked in order: " + bands.order.join(" → ") + "; the map shows the first to fail", PW).forEach(
      function (piece, n) {
        el("tspan", { x: L, dy: n ? KEY_ROW : 0 }, ord, piece);
        y += KEY_ROW;
        rows++;
      });
    if (bands && Math.abs(sigma_MPa - bands.P2.sigma_MPa) > 1e-9) {
      y += KEY_ROW;
      rows++;
      el("text", { id: "map-p2-note", x: L, y: y, "font-size": FS, fill: INK }, g,
        "P2 registered at σ " + bands.P2.sigma_MPa);
    }
    if (off) {
      y += KEY_ROW;
      rows++;
      haloText(g, { id: "map-registered-note", x: L + 4, y: y },
        "† labels: the registered run (no cards, default inputs)");
    }
    return rows;
  }
  // a label on a white plate, so it reads over any cell colour
  function haloText(parent, attrs, text) {
    var w = textW(text) + 8, mid = attrs["text-anchor"] === "middle";
    var x0 = mid ? attrs.x - w / 2 : attrs.x - 4;
    el("rect", { x: x0, y: attrs.y - FS, width: w, height: FS + 6, rx: 3, fill: "#ffffff", "fill-opacity": 0.9 },
      parent);
    return el("text", Object.assign({ "font-size": FS, fill: INK }, attrs), parent, text);
  }

  // a registered band: a white under-stroke, then a solid ink outline, so it reads on any cell colour
  function outline(g, id, box) {
    el("rect", Object.assign({ id: id + "-halo", fill: "none", stroke: "#ffffff", "stroke-width": 6 }, box), g);
    el("rect", Object.assign({ id: id, fill: "url(#map-hatch-band)", stroke: INK, "stroke-width": 2.5 }, box), g);
  }
  // g: the band layer; labels: over the dot's crosshair, under the dot; top: over the dot, so the
  // registered marks stay visible where the dot sits on them
  function drawBands(g, labels, top, sigma_MPa, off) {
    var dag = off ? " · registered run †" : "";
    if (!bands) throw new Error("mapview: bands not set (verdict.js calls DysonMapView.setBands)");
    var p1 = bands.P1;
    var x0 = X(lg(p1.band_au[0])), x1 = X(lg(p1.band_au[1]));
    var yc = Y(lg(p1.R_km * 1000));
    var h = Math.max(PH / (NRR - 1), 16); // the row, drawn at least 16 tall so the mark reads as a box
    outline(top, "map-p1", { x: x0, y: yc - h / 2, width: x1 - x0, height: h });
    // the measured edge for this slice's sigma (the committed Q4 run), a tick across the row
    var k = -1;
    p1.sigma_MPa.forEach(function (s, n) { if (Math.abs(s - sigma_MPa) < 1e-9) k = n; });
    if (k < 0) throw new Error("mapview: no measured r_close for sigma " + sigma_MPa);
    var xr = X(lg(p1.r_close_au[k]));
    var ly = yc - h / 2 - 30, lx = L + 8; // label plates: above the row, from the frame's left edge
    el("line", { x1: xr, y1: yc - h / 2 - 9, x2: xr, y2: yc + h / 2 + 9, stroke: "#ffffff", "stroke-width": 6 }, top);
    el("line", { id: "map-rclose", x1: xr, y1: yc - h / 2 - 9, x2: xr, y2: yc + h / 2 + 9, stroke: INK,
      "stroke-width": 3 }, top);
    el("line", { x1: xr, y1: yc - h / 2 - 9, x2: xr, y2: ly + 6, stroke: INK, "stroke-width": 1.2 }, g);
    haloText(labels, { id: "map-rclose-label", x: lx, y: ly },
      "measured r_close " + p1.r_close_au[k].toFixed(4) + " AU (σ " + sigma_MPa + ")" + dag);
    haloText(labels, { id: "map-p1-label", x: lx, y: ly - FS - 8 },
      "P1 prediction [" + p1.band_au[0] + ", " + p1.band_au[1] + "] AU — " + outcome(p1.verdict) +
        " (" + p1.r_close_au[k].toFixed(4) + ")" + dag);
    var p2 = bands.P2;
    if (Math.abs(sigma_MPa - p2.sigma_MPa) > 1e-9) return;
    var xc = X(lg(p2.r_au)), w = PW / (NR - 1);
    var bot = Y(lg(p2.band_km[0] * 1000));
    var yt = Math.max(T, Y(lg(p2.band_km[1] * 1000)));
    outline(g, "map-p2", { x: xc - w / 2, y: yt, width: w, height: bot - yt });
    var clipped = p2.band_km[1] * 1000 > Math.pow(10, GRR[1]);
    if (clipped) {
      // the band runs above the map's top edge: an arrow out of the frame at its column
      var m = el("polygon", { id: "map-p2-offmap", fill: INK, stroke: "#ffffff", "stroke-width": 1,
        points: [[xc, T - 13], [xc - 6, T - 3], [xc + 6, T - 3]].map(function (q) { return q.join(","); }).join(" ") }, g);
      el("title", {}, m, "P2 band continues to " + p2.band_km[1] + " km, above the map's " +
        Math.pow(10, GRR[1] - 3) + " km top");
      haloText(g, { id: "map-p2-offmap-note", x: xc + 12, y: P2_NOTE_Y },
        "↑ band continues above the map's " + Math.pow(10, GRR[1] - 3) + " km top");
    }
    haloText(g, { id: "map-p2-label", x: 8, y: P2_Y },
      "P2 prediction R_window ∈ [" + p2.band_km[0] + ", " + p2.band_km[1] + "] km" +
        " — " + outcome(p2.verdict) + " (" + p2.measured_km + " km)" + dag);
  }

  // cross: the crosshair layer, under the band labels; g: the dot's layer, over them
  function drawDot(g, cross, state, slice) {
    var lr = lg(state.r), lR = lg(state.R);
    var loX = lr <= GR[0] + EDGE_TOL, hiX = lr >= GR[1] - EDGE_TOL;
    var loY = lR <= GRR[0] + EDGE_TOL, hiY = lR >= GRR[1] - EDGE_TOL;
    var cx = loX ? L : hiX ? L + PW : X(lr);
    var cy = loY ? T + PH : hiY ? T : Y(lR);
    var clamped = loX || hiX || loY || hiY;
    var c = cellAt(state.r, state.R);
    el("line", { x1: L, y1: cy, x2: L + PW, y2: cy, stroke: INK, "stroke-opacity": 0.55, "stroke-width": 1,
      "stroke-dasharray": "4 3", "data-mark": "crosshair" }, cross);
    el("line", { x1: cx, y1: T, x2: cx, y2: T + PH, stroke: INK, "stroke-opacity": 0.55, "stroke-width": 1,
      "stroke-dasharray": "4 3", "data-mark": "crosshair" }, cross);
    if (!(state.verdict in PAL)) throw new Error("mapview: dot has no verdict class (" + state.verdict + ")");
    // the dot is the exact design: filled with the verdict's class, ringed dark over white so it
    // reads on any cell colour; the nearest cell's class is kept apart as data-cell-class
    el("circle", { cx: cx, cy: cy, r: 9, fill: INK, "data-mark": "dot-ring" }, g);
    el("circle", { id: "map-dot", cx: cx, cy: cy, r: 6.5, fill: fillOf(state.verdict), stroke: "#ffffff",
      "stroke-width": 2, "data-i": c.i, "data-j": c.j, "data-class": state.verdict,
      "data-cell-class": slice === null ? "" : classOf(slice, c.i, c.j),
      "data-clamped": clamped ? "true" : "false" }, g);
    if (!clamped) return;
    // an outward arrowhead just outside each edge the dot is pinned to
    var m = el("g", { id: "map-clamp", "data-mark": "clamp" }, g);
    el("title", {}, m, "the design sits on the edge of the precomputed grid");
    var tri = function (x, y, dx, dy) {
      var px = -dy, py = dx; // perpendicular
      var pts = [[x + dx * 12, y + dy * 12], [x + dx * 3 + px * 6, y + dy * 3 + py * 6],
        [x + dx * 3 - px * 6, y + dy * 3 - py * 6]];
      el("polygon", { points: pts.map(function (p) { return p[0].toFixed(1) + "," + p[1].toFixed(1); }).join(" "),
        fill: INK }, m);
    };
    if (loX) tri(L - 2, cy, -1, 0);
    if (hiX) tri(L + PW + 2, cy, 1, 0);
    if (loY) tri(cx, T + PH + 2, 0, 1);
    if (hiY) tri(cx, T - 2, 0, -1);
  }

  // the data: at this sigma the algal and vascular precomputed slices are identical
  function sameMap(state) {
    var s = String(state.sigma_MPa);
    return sourceOf(state).kind === "precomputed" && D.slices[s + "|algal"] === D.slices[s + "|vascular"];
  }
  function titleText(state) {
    return "First line to fail · σ " + String(state.sigma_MPa) + " MPa · " + state.org +
      (sourceOf(state).kind === "live" ? " · your design" : "");
  }
  // state.source (verdict.js): {kind: "precomputed"} (the default), {kind: "stale", lines} (the
  // precomputed slice drawn greyed while the worker recomputes), {kind: "live", level, status}
  function sourceOf(state) {
    return state.source || { kind: "precomputed" };
  }
  // split a status line into pieces that fit the frame's width (text width is estimated)
  function wrap(t, maxW) {
    var out = [], line = "";
    String(t).split(" ").forEach(function (w) {
      var next = line ? line + " " + w : w;
      if (line && textW(next) + 8 > maxW) {
        out.push(line);
        line = w;
      } else line = next;
    });
    if (line) out.push(line);
    return out;
  }
  // the source's labels, redrawn with the dot on every draw (progress text changes often)
  function drawStatus(g, state, stale) {
    var src = sourceOf(state);
    if (stale) {
      var lines = src.lines || ["recomputing…"];
      var rows = [];
      lines.forEach(function (t, n) {
        wrap(t, PW - 24).forEach(function (piece) {
          rows.push({ t: piece, id: n === 0 ? "map-recomputing" : n === lines.length - 1 ? "map-stale-note" : null });
        });
      });
      // the progress line sits above the frame; the notes about the greyed cells stay on them
      var head = rows.filter(function (o) { return o.id === "map-recomputing"; }).length;
      var y0 = T + PH / 2 - ((rows.length - head - 1) * KEY_ROW) / 2;
      rows.forEach(function (row, n) {
        var a = n < head ? { x: 8 + (n ? 12 : 0), y: STATUS_Y + n * KEY_ROW, "data-state": "recomputing" }
          : { x: L + PW / 2, y: y0 + (n - head) * KEY_ROW, "text-anchor": "middle", "data-state": "recomputing" };
        // a line that wraps keeps its id on its first piece only
        if (row.id && !rows.slice(0, n).some(function (o) { return o.id === row.id; })) a.id = row.id;
        else if (row.id) a["data-part-of"] = row.id;
        haloText(g, a, row.t);
      });
    } else if (src.kind === "live") {
      haloText(g, { id: "map-live-status", x: 8, y: STATUS_Y, "data-level": src.level }, src.status);
    }
    if (state.manualPT)
      haloText(g, { id: "map-manual-note", x: L + 8, y: T + PH - 8 },
        "map shows the auto-designed vessel; your manual p/t is the dot");
  }

  function build(svg, state, slice) {
    clear(svg);
    var H0 = T + PH + 64;
    var layers = {};
    el("title", {}, svg, "First-failure map: distance against vessel radius");
    defs(svg);
    layers.title = el("text", { id: "map-title", x: 4, y: 20, "font-size": FS, fill: INK, "font-weight": 600 }, svg,
      titleText(state));
    layers.cells = el("g", { id: "map-cells", "shape-rendering": "crispEdges" }, svg);
    if (slice !== null) drawCells(layers.cells, slice);
    var prov = sourceOf(state).kind === "live" && !!sourceOf(state).provisional;
    layers.cells.setAttribute("data-provisional", prov ? "true" : "false");
    if (prov) {
      // a coarse preview: desaturated and hatched, so it is not read as the recomputed map
      layers.cells.setAttribute("filter", "url(#map-desat)");
      el("rect", { id: "map-provisional", x: L, y: T, width: PW, height: PH, fill: "url(#map-hatch-prov)",
        "pointer-events": "none" }, svg);
    }
    el("rect", { id: "map-frame", x: L, y: T, width: PW, height: PH, fill: "none", stroke: AXIS }, svg);
    axes(svg);
    var off = offRegistered(state);
    var rows = legend(el("g", { id: "map-legend" }, svg), slice, H0, state.sigma_MPa, off, sameMap(state));
    layers.bands = el("g", { id: "map-bands" }, svg);
    layers.cross = el("g", { id: "map-cross" }, svg);
    layers.labels = el("g", { id: "map-band-labels" }, svg);
    layers.over = el("g", { id: "map-over" }, svg);
    layers.top = el("g", { id: "map-top" }, svg);
    drawBands(layers.bands, layers.labels, layers.top, state.sigma_MPa, off);
    el("rect", { id: "map-hit", x: L, y: T, width: PW, height: PH, fill: "transparent",
      style: "cursor: crosshair" }, svg);
    svg.setAttribute("viewBox", "0 0 " + W + " " + (H0 + (rows - 1) * KEY_ROW + 12));
    return layers;
  }

  // client px -> viewBox units
  function toView(svg, ev) {
    var b = svg.getBoundingClientRect(), vb = svg.viewBox.baseVal;
    return [((ev.clientX - b.left) * vb.width) / b.width, ((ev.clientY - b.top) * vb.height) / b.height];
  }
  // viewBox units -> (log10 r, log10 R), clamped to the frame
  function toLog(v) {
    var x = clampN(v[0], L, L + PW), y = clampN(v[1], T, T + PH);
    return [GR[0] + ((x - L) / PW) * (GR[1] - GR[0]), GRR[0] + ((T + PH - y) / PH) * (GRR[1] - GRR[0])];
  }
  // wired once per svg: a press inside the frame starts a pick; a drag may leave the frame and
  // is clamped to its edge
  var wired = [];
  function wire(svg) {
    if (wired.indexOf(svg) >= 0) return;
    wired.push(svg);
    var dragging = false;
    function fire(ev, phase) {
      var v = toLog(toView(svg, ev));
      pickFns.forEach(function (fn) { fn(v[0], v[1], phase); });
    }
    svg.addEventListener("pointerdown", function (ev) {
      var v = toView(svg, ev);
      if (v[0] < L || v[0] > L + PW || v[1] < T || v[1] > T + PH) return;
      dragging = true;
      if (svg.setPointerCapture) svg.setPointerCapture(ev.pointerId);
      fire(ev, "input");
    });
    svg.addEventListener("pointermove", function (ev) {
      if (dragging) fire(ev, "input");
    });
    svg.addEventListener("pointerup", function (ev) {
      if (!dragging) return;
      dragging = false;
      fire(ev, "change");
    });
    svg.addEventListener("pointercancel", function () {
      dragging = false;
    });
  }

  // slice: the class string to draw (precomputed, or a worker level painted over the full grid),
  // or null (no cells known: the last cells stay). A null slice or state.source.kind "stale" is
  // NOT current: the cells are greyed, labelled, and the dot does not vouch for their class.
  function draw(svg, state, slice) {
    var src = sourceOf(state), stale = slice === null || src.kind === "stale";
    var key = String(state.sigma_MPa) + "|" + stale + "|" + offRegistered(state) + "|" + !!src.provisional + "|" +
      state.org + "|" + src.kind + "|" +
      (slice === null ? "null" : slice);
    if (!built || built.svg !== svg || built.key !== key) {
      var dim = slice === null && built && built.svg === svg ? built.lastSlice : null;
      var layers = build(svg, state, slice === null ? dim : slice);
      wire(svg);
      built = { svg: svg, key: key, layers: layers, lastSlice: slice === null ? dim : slice };
      if (stale) layers.cells.setAttribute("opacity", "0.35");
    }
    built.layers.cells.setAttribute("data-source", stale ? "stale" : src.kind === "live" ? src.level : "precomputed");
    built.layers.title.textContent = titleText(state);
    clear(built.layers.over);
    clear(built.layers.cross);
    drawDot(built.layers.over, built.layers.cross, state, stale ? null : slice);
    drawStatus(built.layers.over, state, stale);
  }

  window.DysonMapView = {
    draw: draw,
    cellAt: cellAt,
    onPick: function (fn) { pickFns.push(fn); },
    setBands: function (b) { bands = b; },
  };
})();
