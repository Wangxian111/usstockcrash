/* Technical analysis page · tables and price chart */
(function () {
  "use strict";

  var D = (typeof TECHNICAL_DATA !== "undefined") ? TECHNICAL_DATA : null;
  if (!D) return;

  var NS = "http://www.w3.org/2000/svg";
  var $ = function (id) { return document.getElementById(id); };
  var tt = $("tt");

  function el(tag, attrs, text) {
    var node = document.createElementNS(NS, tag);
    if (attrs) {
      for (var key in attrs) {
        if (Object.prototype.hasOwnProperty.call(attrs, key) && attrs[key] !== undefined && attrs[key] !== null) {
          node.setAttribute(key, attrs[key]);
        }
      }
    }
    if (text !== undefined && text !== null) node.textContent = text;
    return node;
  }

  function clear(node) {
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function addCell(tr, text, cls) {
    var td = document.createElement("td");
    td.textContent = text;
    if (cls) td.className = cls;
    tr.appendChild(td);
  }

  function pct(v) {
    return v == null ? "—" : v + "%";
  }

  function ci(v) {
    if (!v || v[0] == null || v[1] == null) return "";
    return " (" + v[0] + "–" + v[1] + "%)";
  }

  /* ---------------- tooltip ---------------- */

  function ttMove(ev) {
    var cx, cy;
    if (ev && typeof ev.clientX === "number" && ev.clientX !== 0) {
      cx = ev.clientX;
      cy = ev.clientY;
    } else if (ev && ev.currentTarget) {
      var r = ev.currentTarget.getBoundingClientRect();
      cx = r.left + r.width / 2;
      cy = r.top;
    } else {
      return;
    }
    var w = tt.offsetWidth;
    var h = tt.offsetHeight;
    var x = cx + 14;
    var y = cy + 14;
    if (x + w > window.innerWidth - 8) x = cx - w - 12;
    if (y + h > window.innerHeight - 8) y = cy - h - 12;
    if (x < 8) x = 8;
    if (y < 8) y = 8;
    tt.style.left = x + "px";
    tt.style.top = y + "px";
  }

  function ttShow(ev, title, rows) {
    clear(tt);
    var t = document.createElement("div");
    t.className = "tt-title";
    t.textContent = title;
    tt.appendChild(t);
    rows.forEach(function (r) {
      var row = document.createElement("div");
      row.className = "tt-row";
      var n = document.createElement("span");
      n.className = "n";
      if (r.color) {
        var key = document.createElement("i");
        key.className = "key";
        key.style.background = r.color;
        n.appendChild(key);
      }
      n.appendChild(document.createTextNode(r.label));
      var v = document.createElement("span");
      v.className = "v";
      v.textContent = r.value;
      row.appendChild(n);
      row.appendChild(v);
      tt.appendChild(row);
    });
    tt.style.display = "block";
    ttMove(ev);
  }

  function ttHide() {
    tt.style.display = "none";
  }

  function appendTable(host, headers, rows) {
    var details = document.createElement("details");
    details.className = "data-table";
    var summary = document.createElement("summary");
    summary.textContent = "View data table";
    details.appendChild(summary);

    var wrap = document.createElement("div");
    wrap.className = "tblwrap";
    var table = document.createElement("table");
    table.className = "data";

    var thead = document.createElement("thead");
    var trh = document.createElement("tr");
    headers.forEach(function (h) {
      var th = document.createElement("th");
      th.textContent = h;
      trh.appendChild(th);
    });
    thead.appendChild(trh);
    table.appendChild(thead);

    var tbody = document.createElement("tbody");
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      r.forEach(function (c) {
        var td = document.createElement("td");
        td.textContent = c;
        tr.appendChild(td);
      });
      tbody.appendChild(tr);
    });
    table.appendChild(tbody);
    wrap.appendChild(table);
    details.appendChild(wrap);
    host.parentNode.appendChild(details);
  }

  /* ---------------- text / KPI ---------------- */

  function renderText() {
    var m = D.models;
    var s = D.stability;
    var tech = m.technical.top20;
    var tech10 = m.technical.top10;
    var comb = m.combined.top20;

    $("techAsOf").textContent = D.meta.windowEnd;
    $("techBaseRate").textContent = D.nearHighBaseRate + "%";

    $("techBannerText").textContent =
      "Pure technical top-20% hit rate " + tech.precision + "% (base rate " + D.nearHighBaseRate + "%), " +
      "top-10% hit rate " + tech10.precision + "%; but AUC " + tech.auc + " and " +
      "a yearly median of " + s.medianPrecision + "%. Adding fundamentals pulls top 20% down to " + comb.precision + "%.";

    $("techConclusion").textContent =
      "Used on its own to predict ≥10% drawdowns over the next 6 months, the pure technical model has a top-20% hit rate of " + tech.precision +
      "% (base rate " + D.nearHighBaseRate + "%, lift " + tech.lift + ") and a top-10% hit rate of " + tech10.precision +
      "%; but AUC is only " + tech.auc + " and the yearly median is " + s.medianPrecision + "%, with only " +
      s.yearsAboveBase + " of " + s.years + " evaluable years beating the base rate. " +
      "Adding the fundamental risk score actually lowers the top-20% hit rate to " + comb.precision + "% (AUC " + comb.auc +
      "); the fundamental score barely lights up near highs, and since it rises during declines it is contrarian for “another 10% fall from here.” " +
      "The most useful single indicators are high volatility (ATR >80th percentile, 37.1% hit rate but only 8.2% recall) and the weekly Bollinger squeeze (29.9%, 21.1% recall); " +
      "an overbought RSI actually leans bullish (16.7%, lift 0.74). Conclusion: technical analysis works as a filter for “don't add at high volatility / after trend damage,” " +
      "but not as a standalone crash-timing signal; adding it does not give you a reliable overall hit rate.";

    var tags = [
      { text: "Pure technical top20 " + tech.precision + "%", tone: "warn" },
      { text: "Top10 " + tech10.precision + "%", tone: "warn" },
      { text: "AUC " + tech.auc, tone: "crit" },
      { text: "With overlay " + comb.precision + "%", tone: "crit" },
      { text: "Overbought RSI leans bullish", tone: "" }
    ];
    var host = $("techTags");
    clear(host);
    tags.forEach(function (t) {
      var span = document.createElement("span");
      span.className = "tag " + (t.tone || "");
      span.textContent = t.text;
      host.appendChild(span);
    });

    $("techIndicatorNote").textContent =
      "Near-high base rate " + D.nearHighBaseRate + "%. ATR >80th percentile has a 37.1% hit rate but only 8.2% recall; " +
      "weekly Bollinger width <20th percentile has a 29.9% hit rate with 21.1% recall; overbought RSI(14)>70 has a 16.7% hit rate, below the base rate. " +
      "“Lift” = signal hit rate ÷ base rate; recall = how much of future crashes the signal covers.";

    $("techModelNote").textContent =
      "Pure technical model top-20% hit rate " + tech.precision + "% (95% CI " +
      (tech.precisionCI ? tech.precisionCI[0] + "–" + tech.precisionCI[1] + "%" : "—") +
      "), AUC " + tech.auc + " — only slightly better than random. With the fundamental overlay, AUC " + comb.auc +
      " and top-20% hit rate " + comb.precision + "%: no gain.";
  }

  function renderKpis() {
    var m = D.models;
    var s = D.stability;
    var items = [
      { label: "Near-high base rate", value: D.nearHighBaseRate + "%", tone: "mid" },
      { label: "Pure technical Top 20%", value: m.technical.top20.precision + "%", tone: "good" },
      { label: "Pure technical Top 10%", value: m.technical.top10.precision + "%", tone: "good" },
      { label: "With fundamentals Top 20%", value: m.combined.top20.precision + "%", tone: "warn" },
      { label: "Yearly median", value: s.medianPrecision + "%", tone: "warn" },
      {
        label: "Years above base rate",
        value: s.yearsAboveBase + "/" + s.years,
        tone: s.yearsAboveBase >= s.years / 2 ? "mid" : "crit"
      }
    ];
    var host = $("techKpis");
    clear(host);
    items.forEach(function (it) {
      var card = document.createElement("div");
      card.className = "stat";
      var label = document.createElement("div");
      label.className = "stat-label";
      var dot = document.createElement("span");
      dot.className = "dot " + it.tone;
      label.appendChild(dot);
      label.appendChild(document.createTextNode(it.label));
      var value = document.createElement("div");
      value.className = "stat-value";
      value.textContent = it.value;
      card.appendChild(label);
      card.appendChild(value);
      host.appendChild(card);
    });
  }

  /* ---------------- tables ---------------- */

  function renderIndicatorTable(tbody, rows) {
    clear(tbody);
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      addCell(tr, r.name);
      addCell(tr, r.kind);
      addCell(tr, r.signalDays, "num");
      addCell(tr, pct(r.precision), "num");
      addCell(tr, r.lift == null ? "—" : r.lift.toFixed(2), "num");
      addCell(tr, pct(r.recall), "num");
      addCell(tr, pct(r.fpr), "num");
      addCell(tr, pct(r.avgFwdDd), "num");
      tbody.appendChild(tr);
    });
  }

  function renderModels() {
    var body = $("techModelRows");
    clear(body);
    var order = [
      ["fundamental", "Fundamental score"],
      ["technical", "Pure technical"],
      ["combined", "Fundamental + technical"]
    ];
    order.forEach(function (item) {
      var m = D.models[item[0]];
      if (!m) return;
      var a = m.top20;
      var b = m.top10;
      var tr = document.createElement("tr");
      addCell(tr, item[1]);
      addCell(tr, pct(a.precision) + ci(a.precisionCI), "num");
      addCell(tr, pct(b.precision), "num");
      addCell(tr, a.auc == null ? "—" : a.auc, "num");
      addCell(tr, pct(a.recall), "num");
      addCell(tr, pct(a.fpr), "num");
      addCell(tr, a.lift == null ? "—" : a.lift, "num");
      body.appendChild(tr);
    });
  }

  function renderYearly() {
    var body = $("techYearlyRows");
    clear(body);
    (D.yearly || []).forEach(function (r) {
      var tr = document.createElement("tr");
      addCell(tr, r.year);
      addCell(tr, r.testDays == null ? "—" : r.testDays, "num");
      addCell(tr, pct(r.baseRate), "num");
      addCell(tr, r.skipped ? "—" : pct(r.technical_precision20), "num");
      addCell(tr, r.skipped ? "—" : (r.technical_auc == null ? "—" : r.technical_auc), "num");
      addCell(tr, r.skipped ? "—" : pct(r.fundamental_precision20), "num");
      addCell(tr, r.skipped ? "—" : pct(r.combined_precision20), "num");
      var note = r.skipped ? (r.reason || "Skipped") : (r.year === 2026 ? "No positive samples; informational only" : "");
      addCell(tr, note, "why");
      body.appendChild(tr);
    });

    var techRows = (D.yearly || []).filter(function (r) {
      return !r.skipped && r.technical_precision20 != null;
    });
    var parts = techRows.map(function (r) {
      return r.year + " " + r.technical_precision20 + "%";
    }).join("、");
    $("techStabilityNote").textContent =
      "Pure technical top-20% hit rate: " + (parts || "—") + "; median " + D.stability.medianPrecision +
      "%, with " + D.stability.yearsAboveBase + "/" + D.stability.years +
      " years above the base rate. Yearly swings are too large to treat the pooled " + D.models.technical.top20.precision +
      "% as a stable hit rate.";
  }

  /* ---------------- price chart ---------------- */

  function priceChart(host, data) {
    if (!data || !data.length) return;
    var W = 1000;
    var H = 340;
    var m = { t: 24, r: 90, b: 44, l: 56 };
    var plotW = W - m.l - m.r;
    var plotH = H - m.t - m.b;
    var vals = [];
    data.forEach(function (p) {
      if (p.close != null) vals.push(p.close);
      if (p.sma200 != null) vals.push(p.sma200);
    });
    var lo = Math.min.apply(null, vals);
    var hi = Math.max.apply(null, vals);
    var pad = (hi - lo) * 0.06 || 10;
    lo -= pad;
    hi += pad;

    var x = function (i) { return m.l + (i / (data.length - 1)) * plotW; };
    var y = function (v) { return m.t + plotH - ((v - lo) / (hi - lo)) * plotH; };

    var s = el("svg", {
      viewBox: "0 0 " + W + " " + H,
      role: "img",
      "aria-label": "SPY close and its 200-day moving average, with drawdowns beyond 10% shaded"
    });

    // drawdown >=10% shading
    var runStart = null;
    for (var i = 0; i < data.length; i++) {
      var inDD = data[i].dd != null && data[i].dd <= -10;
      if (inDD && runStart === null) runStart = i;
      if (!inDD && runStart !== null) {
        s.appendChild(el("rect", {
          x: x(runStart), y: m.t,
          width: Math.max(2, x(i) - x(runStart)), height: plotH,
          fill: "rgba(208,59,59,0.08)"
        }));
        runStart = null;
      }
    }
    if (runStart !== null) {
      s.appendChild(el("rect", {
        x: x(runStart), y: m.t,
        width: Math.max(2, x(data.length - 1) - x(runStart)), height: plotH,
        fill: "rgba(208,59,59,0.08)"
      }));
    }

    // y grid
    for (var t = 0; t <= 4; t++) {
      var v = lo + (hi - lo) * t / 4;
      var yy = y(v);
      s.appendChild(el("line", {
        x1: m.l, x2: W - m.r, y1: yy, y2: yy,
        stroke: "var(--grid)", "stroke-width": 1
      }));
      s.appendChild(el("text", {
        x: m.l - 9, y: yy + 4,
        "text-anchor": "end",
        fill: "var(--muted)",
        "font-size": 10.5,
        style: "font-variant-numeric: tabular-nums"
      }, Math.round(v)));
    }

    // x year labels
    var prevYear = null;
    data.forEach(function (p, idx) {
      var yr = p.d.slice(0, 4);
      if (prevYear !== null && yr !== prevYear) {
        s.appendChild(el("text", {
          x: x(idx), y: m.t + plotH + 24,
          "text-anchor": "middle",
          fill: "var(--muted)",
          "font-size": 10.5
        }, yr));
      }
      prevYear = yr;
    });

    function line(key, color) {
      var pts = data.map(function (p, idx) {
        return p[key] == null ? null : [x(idx), y(p[key])];
      }).filter(Boolean);
      if (!pts.length) return;
      var d = pts.map(function (p, idx) {
        return (idx ? "L" : "M") + p[0].toFixed(1) + "," + p[1].toFixed(1);
      }).join(" ");
      s.appendChild(el("path", {
        d: d, fill: "none", stroke: color,
        "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round"
      }));
    }
    line("close", "var(--s1)");
    line("sma200", "var(--s2)");

    // end labels
    var last = data[data.length - 1];
    if (last.close != null) {
      s.appendChild(el("text", {
        x: x(data.length - 1) + 8, y: y(last.close) + 4,
        fill: "var(--ink)", "font-size": 11, "font-weight": 650
      }, "SPY " + last.close.toFixed(0)));
    }
    if (last.sma200 != null) {
      s.appendChild(el("text", {
        x: x(data.length - 1) + 8, y: y(last.sma200) + 4,
        fill: "var(--s2)", "font-size": 11, "font-weight": 650
      }, "200D " + last.sma200.toFixed(0)));
    }

    // crosshair
    var cross = el("g", { opacity: 0 });
    var vline = el("line", {
      x1: 0, x2: 0, y1: m.t, y2: m.t + plotH,
      stroke: "var(--baseline)", "stroke-width": 1
    });
    cross.appendChild(vline);
    s.appendChild(cross);

    var overlay = el("rect", {
      x: m.l, y: m.t, width: plotW, height: plotH,
      fill: "transparent", tabindex: 0, role: "button",
      "aria-label": "Hover to inspect SPY and its 200-day moving average"
    });

    function nearest(ev) {
      var rect = s.getBoundingClientRect();
      var px = ((ev.clientX - rect.left) / rect.width) * W;
      return Math.max(0, Math.min(data.length - 1, Math.round(((px - m.l) / plotW) * (data.length - 1))));
    }

    function showAt(idx, ev) {
      var p = data[idx];
      var cx = x(idx);
      vline.setAttribute("x1", cx);
      vline.setAttribute("x2", cx);
      cross.setAttribute("opacity", "1");
      ttShow(ev, p.d, [
        { label: "SPY", value: p.close == null ? "—" : p.close.toFixed(2), color: "var(--s1)" },
        { label: "200DMA", value: p.sma200 == null ? "—" : p.sma200.toFixed(2), color: "var(--s2)" },
        { label: "Drawdown", value: p.dd == null ? "—" : p.dd + "%" }
      ]);
    }

    overlay.addEventListener("pointermove", function (ev) { showAt(nearest(ev), ev); });
    overlay.addEventListener("pointerleave", function () {
      cross.setAttribute("opacity", "0");
      ttHide();
    });
    overlay.addEventListener("focus", function (ev) { showAt(data.length - 1, ev); });
    overlay.addEventListener("blur", function () {
      cross.setAttribute("opacity", "0");
      ttHide();
    });
    s.appendChild(overlay);

    host.appendChild(s);
    appendTable(host, ["Week", "SPY", "200DMA", "Drawdown"], data.map(function (p) {
      return [
        p.d,
        p.close == null ? "—" : p.close.toFixed(2),
        p.sma200 == null ? "—" : p.sma200.toFixed(2),
        p.dd == null ? "—" : p.dd + "%"
      ];
    }));
  }

  /* ---------------- theme ---------------- */

  function initTheme() {
    var btn = $("themeBtn");
    if (!btn) return;
    var modes = ["auto", "light", "dark"];
    var labels = { auto: "Theme: Auto", light: "Theme: Light", dark: "Theme: Dark" };
    var mode = "auto";
    try {
      var saved = localStorage.getItem("crash-theme");
      if (modes.indexOf(saved) !== -1) mode = saved;
    } catch (e) {}
    function apply(modeName) {
      if (modeName === "auto") delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = modeName;
      btn.textContent = labels[modeName];
      try { localStorage.setItem("crash-theme", modeName); } catch (e) {}
    }
    btn.addEventListener("click", function () {
      mode = modes[(modes.indexOf(mode) + 1) % modes.length];
      apply(mode);
    });
    apply(mode);
  }

  function init() {
    renderText();
    renderKpis();
    renderIndicatorTable($("techIndicatorRows"), D.indicators || []);
    renderIndicatorTable($("techAllRows"), D.indicatorsAll || []);
    renderModels();
    renderYearly();
    priceChart($("techChart"), D.series || []);
    initTheme();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
