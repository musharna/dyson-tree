// The gene deck (northstar M2b, spec §12). A card moves an input; it never moves an
// inequality. The table is web/deck.json (mirrored by sim/deck.py, parity-tested), loaded as
// window.DysonDeckRows by deck_rows.js, which tools/build_site.sh writes from deck.json.
// This file only resolves which inputs the played cards move and by how much; verdict.js
// hands them to DysonModel like any other input. Classic script, like verdict.js.
(function () {
  "use strict";

  var M = window.DysonModel;
  var ROWS = window.DysonDeckRows;
  if (!M) throw new Error("deck: DysonModel not loaded");
  if (!ROWS || !ROWS.length) throw new Error("deck: DysonDeckRows not loaded");
  var $ = function (id) {
    var e = document.getElementById(id);
    if (!e) throw new Error("deck: missing #" + id);
    return e;
  };
  if (document.getElementById("deck-" + ROWS.length))
    throw new Error("deck: more card slots than rows");

  function rangeText(d) {
    var lo = d.range[0],
      hi = d.range[1];
    var u = d.unit ? " " + d.unit : "";
    var verb = d.op === "subtract" ? "down by " : "times ";
    var s =
      lo === hi
        ? verb + lo + u
        : verb + d.param + " in [" + lo + ", " + hi + "]" + u;
    s += "; up to " + d.max_stack + " card" + (d.max_stack > 1 ? "s" : "");
    if (d.total_cap !== null) s += ", TOTAL capped at " + d.total_cap + u;
    return s + ". " + d.clip_note;
  }

  ROWS.forEach(function (row, i) {
    var d = row.delta_or_range;
    $("deck-" + i + "-trait").textContent = row.trait;
    $("deck-" + i + "-organism").textContent = row.organism;
    $("deck-" + i + "-input").textContent = row.input;
    $("deck-" + i + "-delta").textContent = rangeText(d);
    $("deck-" + i + "-cost").textContent = row.cost;
    $("deck-" + i + "-source").textContent = row.source;
    var b = $("deck-" + i + "-badge");
    b.textContent = row.anchor;
    b.className = "badge badge-" + row.anchor;
    var c = $("deck-" + i + "-count");
    var opts = [];
    for (var k = 0; k <= d.max_stack; k++) opts.push(k);
    if (
      c.options !== undefined &&
      typeof document.createElement === "function"
    ) {
      opts.forEach(function (k) {
        var o = document.createElement("option");
        o.value = String(k);
        o.textContent = k === 0 ? "not played" : k + " played";
        c.appendChild(o);
      });
    }
    c.value = "0";
    var v = $("deck-" + i + "-value");
    v.min = String(d.range[0]);
    v.max = String(d.range[1]);
    v.step = "0.01";
    v.value = String(
      d.range[1] === d.range[0] ? d.range[0] : Math.min(d.range[1], 0.8),
    );
    v.disabled = d.range[0] === d.range[1];
    $("deck-" + i + "-value-label").textContent =
      d.param + (d.unit ? " (" + d.unit + ")" : "") + " per card";
  });

  // sim/deck.py:total
  function total(row, values) {
    var d = row.delta_or_range;
    if (values.length > d.max_stack)
      throw new RangeError(
        row.trait + ": " + values.length + " cards, max_stack " + d.max_stack,
      );
    values.forEach(function (v) {
      if (!(v >= d.range[0] && v <= d.range[1]))
        throw new RangeError(
          row.trait +
            ": " +
            v +
            " outside the card range [" +
            d.range[0] +
            ", " +
            d.range[1] +
            "]",
        );
    });
    var tot;
    if (d.op === "subtract")
      tot = values.reduce(function (a, b) {
        return a + b;
      }, 0);
    else if (d.op === "scale")
      tot = values.reduce(function (a, b) {
        return a * b;
      }, 1);
    else throw new RangeError("unknown op " + d.op);
    if (d.total_cap !== null && tot > d.total_cap)
      return {
        total: d.total_cap,
        clip:
          row.trait +
          ": total " +
          tot +
          " " +
          d.unit +
          " clipped at " +
          d.total_cap,
      };
    return { total: tot, clip: null };
  }

  // sim/deck.py:apply, over the page's defaults: {inputs: {...}, organism: {field: factor|delta}}
  function effect() {
    var inputs = {},
      organism = [],
      clips = [],
      played = [];
    ROWS.forEach(function (row, i) {
      var n = Number($("deck-" + i + "-count").value);
      if (!n) return;
      var per = Number($("deck-" + i + "-value").value);
      var values = [];
      for (var k = 0; k < n; k++) values.push(per);
      var t = total(row, values);
      if (t.clip) clips.push(t.clip);
      played.push(row.trait + " ×" + n + " (" + row.anchor + ")");
      var op = row.delta_or_range.op;
      if (row.input in M.VESSEL_DEFAULTS) {
        var base = M.VESSEL_DEFAULTS[row.input];
        inputs[row.input] = op === "subtract" ? base - t.total : base * t.total;
      } else if (row.input in M.ALGAL) {
        organism.push({ field: row.input, op: op, total: t.total });
      } else {
        throw new RangeError(
          row.trait + ": input " + row.input + " does not exist",
        );
      }
    });
    return { inputs: inputs, organism: organism, clips: clips, played: played };
  }

  function applyOrganism(org, eff) {
    if (!eff.organism.length) return org;
    var f = Object.assign({}, org);
    eff.organism.forEach(function (m) {
      f[m.field] =
        m.op === "subtract" ? f[m.field] - m.total : f[m.field] * m.total;
    });
    return M.makeOrganism(f);
  }

  function status(eff) {
    $("deck-status").textContent = eff.played.length
      ? "played: " +
        eff.played.join(", ") +
        (eff.clips.length ? " — CLIPPED: " + eff.clips.join("; ") : "")
      : "no card played";
  }

  var controlIds = [];
  ROWS.forEach(function (_, i) {
    controlIds.push("deck-" + i + "-count", "deck-" + i + "-value");
  });

  window.DysonDeck = {
    rows: ROWS,
    total: total,
    effect: effect,
    applyOrganism: applyOrganism,
    status: status,
    controlIds: controlIds,
  };
})();
