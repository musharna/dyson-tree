// The first-failure map, recomputed off the main thread (visual-first Task 3). The page posts
//   {gen, grid, classes, sigma_Pa, org, inputs}
// where org and inputs are the objects its own verdict path built (web/verdict.js resolve(): the
// preset through DysonDeck.applyOrganism, the inputs through makeVesselInputs). This worker never
// rebuilds them, so it needs no deck.js (which reads the DOM). It answers, level by level,
//   {gen, level: "12×8" | "40×30" | "80×60", slice}   slice: one class digit per cell of the FULL
//                                                     80 × 60 grid, r the outer loop (map_data.js)
//   {gen, progress: {level, done, total}}             while a level is being computed
//   {gen, error}                                      the model raised: shown, never swallowed
// A coarse level samples grid points (12 of the 80 r columns, 8 of the 60 R rows, spread evenly)
// and paints every cell with its nearest sample's class, so it covers the grid's whole extent at
// its own scale. Samples are grid points, so each finer level reuses every cell already computed
// and the 80 × 60 level costs 4800 evaluations in total. Classic script: relative importScripts.
"use strict";
importScripts("spectral_table.js", "model.js");
var M = self.DysonModel;
if (!M) throw new Error("map_worker: DysonModel not loaded");

// COPIED verbatim from tools/make_map.mjs (tests/test_map_worker.py pins the two sources equal)
function mapCell(M, r, R_m, sigma_Pa, org, inputs) {
  try {
    const st = M.autoState(r, R_m, sigma_Pa, M.PRESETS[org] ?? org, inputs ?? M.REGISTERED);
    return st.report.violated[0] ?? "HELD";
  } catch (e) {
    if (e && e.name === "RunnerError") return "NO_DESIGN";
    throw e; // fail loud: any other error is a bug, not a map class
  }
}
const axis = ([lo, hi, n], i) => Math.pow(10, lo + ((hi - lo) * i) / (n - 1));

var LEVELS = [[12, 8], [40, 30], [80, 60]];
var PROGRESS_MS = 250;

// n grid indices spread evenly over 0..N-1, ends included
function samples(n, N) {
  if (!(n >= 2 && n <= N)) throw new RangeError("map_worker: level " + n + " on a grid of " + N);
  var out = [];
  for (var k = 0; k < n; k++) out.push(Math.round((k * (N - 1)) / (n - 1)));
  return out;
}
// for each grid index, the nearest sample (the lower one on a tie)
function nearestSample(s, N) {
  var out = [], k = 0;
  for (var i = 0; i < N; i++) {
    while (k + 1 < s.length && Math.abs(s[k + 1] - i) < Math.abs(s[k] - i)) k++;
    out.push(s[k]);
  }
  return out;
}

// post(msg) receives each message; nLevels (tests) stops after the first nLevels levels
function compute(req, post, nLevels) {
  var G = req.grid, NR = G.r_log10[2], NRR = G.R_log10[2];
  var last = LEVELS[LEVELS.length - 1];
  if (last[0] !== NR || last[1] !== NRR)
    throw new RangeError("map_worker: finest level " + last + " is not the grid " + NR + "×" + NRR);
  var done = new Map(), t = Date.now();
  LEVELS.slice(0, nLevels || LEVELS.length).forEach(function (lv) {
    var name = lv[0] + "×" + lv[1];
    var si = samples(lv[0], NR), sj = samples(lv[1], NRR), todo = [];
    si.forEach(function (i) {
      sj.forEach(function (j) {
        if (!done.has(i * NRR + j)) todo.push([i, j]);
      });
    });
    todo.forEach(function (ij, k) {
      var c = mapCell(M, axis(G.r_log10, ij[0]), axis(G.R_log10, ij[1]), req.sigma_Pa, req.org, req.inputs);
      var ix = req.classes.indexOf(c);
      if (ix < 0) throw new Error("map_worker: unknown class " + c + " at i=" + ij[0] + " j=" + ij[1]);
      done.set(ij[0] * NRR + ij[1], ix);
      if (Date.now() - t >= PROGRESS_MS) {
        t = Date.now();
        post({ gen: req.gen, progress: { level: name, done: k + 1, total: todo.length } });
      }
    });
    var ni = nearestSample(si, NR), nj = nearestSample(sj, NRR), str = "";
    for (var i = 0; i < NR; i++) for (var j = 0; j < NRR; j++) str += done.get(ni[i] * NRR + nj[j]);
    post({ gen: req.gen, level: name, slice: str });
  });
}

self.onmessage = function (ev) {
  var req = ev.data;
  try {
    compute(req, function (m) { self.postMessage(m); });
  } catch (e) {
    self.postMessage({ gen: req.gen, error: String((e && (e.stack || e.message)) || e) });
  }
};
// for tests/test_map_worker.py, which runs this file in node
self.DysonMapWorker = { mapCell: mapCell, axis: axis, compute: compute, samples: samples, LEVELS: LEVELS };
