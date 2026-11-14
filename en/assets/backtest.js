/* Backtest page · chart and table rendering */
(function () {
  "use strict";

  var D = (typeof BACKTEST_DATA !== "undefined") ? BACKTEST_DATA : null;
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

  function fmt(n) {
    return Number(n).toLocaleString("en-US", { maximumFractionDigits: 1 });
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

  /* ---------------- table view ---------------- */

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
    var s = D.summary;
    $("btAsOf").textContent = D.meta.windowEnd;

    $("btBannerText").textContent =
      "Of " + s.majorCount + " ≥10% drawdowns: " +
      s.early + " early warnings, " +
      s.partial + " partial warnings, " +
      s.coincident + " coincident confirmations, " +
      s.missed + " missed; 2022 was a complete miss. It is more a “relative fragility” thermometer than a timing predictor.";

    $("btConclusion").textContent =
      "Backtest window " + D.meta.windowStart + " to " + D.meta.windowEnd +
      ", " + s.majorCount + " ≥10% drawdowns in total. The model only gave a fairly clear early warning before the Feb–Apr 2025 drawdown; " +
      "Feb 2020 produced just a roughly 10-day brief hint; Q4 2018 was a coincident confirmation; 2022 was a complete miss. " +
      "The partial warning in Jan 2018 had already faded before the peak. Note: “early/partial” here is judged on the rolling 3-year percentile; " +
      "the raw weighted score was 36.9 at 2025 T-30 and 35.7 at 2020 T-10 — neither reached the main site's 45 “watch” threshold. " +
      "It answers “how fragile is this now” far better than “when will it fall”.";

    var tags = [
      { text: "2025 early warning", tone: "warn" },
      { text: "2020 ~10 days", tone: "warn" },
      { text: "2018Q4 coincident", tone: "crit" },
      { text: "2022 missed", tone: "crit" },
      { text: "2024/2026 minor dips", tone: "" }
    ];
    var host = $("btTags");
    clear(host);
    tags.forEach(function (t) {
      var span = document.createElement("span");
      span.className = "tag " + (t.tone || "");
      span.textContent = t.text;
      host.appendChild(span);
    });
  }

  function renderKpis() {
    var s = D.summary;
    var items = [
      { label: "≥10% drawdowns", value: s.majorCount, tone: "mid" },
      { label: "Early warnings", value: s.early, tone: "good" },
      { label: "Partial warnings", value: s.partial, tone: "warn" },
      { label: "Coincident", value: s.coincident, tone: "serious" },
      { label: "Missed", value: s.missed, tone: "crit" },
      { label: "Post-crisis highs", value: s.falsePositiveCount, tone: "mid" }
    ];
    var host = $("btKpis");
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

  /* ---------------- episodes ---------------- */

  function addCell(tr, text, cls) {
    var td = document.createElement("td");
    td.textContent = text;
    if (cls) td.className = cls;
    tr.appendChild(td);
  }

  function statusEl(label) {
    var tone = label === "Early warning" ? "good"
      : label === "Partial warning" ? "warn"
      : label === "Coincident confirmation" ? "serious"
      : label === "Missed" ? "crit"
      : "mid";
    var span = document.createElement("span");
    span.className = "status-tag status-" + tone;
    var dot = document.createElement("span");
    dot.className = "dot " + tone;
    span.appendChild(dot);
    span.appendChild(document.createTextNode(label));
    return span;
  }

  function epNote(r) {
    if (r.label === "Early warning") return "T-30 percentile " + r.pct_t30 + "% — relatively high";
    if (r.label === "Partial warning") {
      if (r.pct_t10 != null && r.pct_t30 != null && r.pct_t10 >= 75 && r.pct_t30 < 65) {
        return "T-10 percentile " + r.pct_t10 + "% — about 10 days of lead";
      }
      return "T-30 percentile " + r.pct_t30 + "%, but T-10 fell back to " + r.pct_t10 + "%";
    }
    if (r.label === "Coincident confirmation") return "Crossed the 80th percentile only after the peak";
    if (r.label === "Missed") return "Pre-peak percentile " + r.pct_t30 + "% — rose only after the decline";
    return "8–10% drawdown, excluded from main statistics";
  }

  function sharpNote(r) {
    return "T-30 percentile " + (r.pct_t30 == null ? "—" : r.pct_t30 + "%") +
      " / T-10 " + (r.pct_t10 == null ? "—" : r.pct_t10 + "%") +
      " · only " + Math.abs(r.drawdown) + "%";
  }

  function renderEpisodes() {
    var major = $("btMajorRows");
    clear(major);
    D.episodes.filter(function (r) { return r.major; }).forEach(function (r) {
      var tr = document.createElement("tr");
      addCell(tr, r.peak);
      addCell(tr, r.trough);
      addCell(tr, r.drawdown + "%", "num");
      addCell(tr, r.score_t30 == null ? "—" : r.score_t30, "num");
      addCell(tr, r.score_t10 == null ? "—" : r.score_t10, "num");
      addCell(tr, r.pct_t30 == null ? "—" : r.pct_t30 + "%", "num");
      addCell(tr, r.pct_t10 == null ? "—" : r.pct_t10 + "%", "num");
      var td = document.createElement("td");
      td.appendChild(statusEl(r.label));
      tr.appendChild(td);
      addCell(tr, epNote(r), "why");
      major.appendChild(tr);
    });

    var sharp = $("btSharpRows");
    clear(sharp);
    D.episodes.filter(function (r) { return !r.major; }).forEach(function (r) {
      var tr = document.createElement("tr");
      addCell(tr, r.peak);
      addCell(tr, r.trough);
      addCell(tr, r.drawdown + "%", "num");
      addCell(tr, r.pct_t30 == null ? "—" : r.pct_t30 + "%", "num");
      addCell(tr, r.pct_t10 == null ? "—" : r.pct_t10 + "%", "num");
      var td = document.createElement("td");
      td.appendChild(statusEl("Minor drawdown"));
      tr.appendChild(td);
      addCell(tr, sharpNote(r), "why");
      sharp.appendChild(tr);
    });
  }

  function renderWarningStats() {
    var tbody = $("btWarnRows");
    clear(tbody);
    var s10 = D.warningStats || {};
    var s8 = D.warningStats8 || {};

    ["75", "80", "85"].forEach(function (k) {
      var a = s10[k];
      var b = s8[k];
      if (!a || !b) return;
      var tr = document.createElement("tr");
      addCell(tr, "Percentile ≥" + k + " · 10-day persistence");
      addCell(tr, a.preCrisis, "num");
      addCell(tr, a.hits, "num");
      addCell(tr, a.falsePositives, "num");
      addCell(tr, a.falsePositiveRate + "%", "num");
      addCell(tr, b.hits, "num");
      addCell(tr, b.falsePositives, "num");
      addCell(tr, b.falsePositiveRate + "%", "num");
      addCell(tr, a.postCrisis, "num");
      tbody.appendChild(tr);
    });

    var a80 = s10["80"];
    var b80 = s8["80"];
    if (a80 && b80) {
      $("btWarnNote").textContent =
        "Using percentile ≥80, 10-trading-day persistence, and a 6-month horizon: " +
        a80.preCrisis + " advance warnings, " + a80.hits + " hits on ≥10% drawdowns, " +
        a80.falsePositives + " false alarms — a " + a80.falsePositiveRate + "% false rate. " +
        "Counting 8% as a crash too: " + b80.hits + " hits and " +
        b80.falsePositives + " false alarms — a " + b80.falsePositiveRate + "% false rate.";
    }

    var detail = $("btWarnDetailRows");
    clear(detail);
    var rows = (s10["80"] && s10["80"].rows) || [];
    var labels = { hit: "Hit", "false": "False alarm", post: "Post-crisis high" };
    rows.forEach(function (r) {
      var tr = document.createElement("tr");
      addCell(tr, r.start);
      addCell(tr, r.end);
      addCell(tr, r.max_pct == null ? "—" : r.max_pct + "%", "num");
      addCell(tr, r.dd_at_start + "%", "num");
      addCell(tr, r.forward_6m_dd + "%", "num");
      var td = document.createElement("td");
      var tone = r.outcome === "hit" ? "good" : r.outcome === "false" ? "crit" : "mid";
      var span = document.createElement("span");
      span.className = "status-tag status-" + tone;
      var dot = document.createElement("span");
      dot.className = "dot " + tone;
      span.appendChild(dot);
      span.appendChild(document.createTextNode(labels[r.outcome] || r.outcome));
      td.appendChild(span);
      tr.appendChild(td);
      detail.appendChild(tr);
    });
  }

  function renderFalsePositives() {
    var tbody = $("btFpRows");
    clear(tbody);
    var fps = D.falsePositives || [];
    var note = $("btFpNote");

    if (!fps.length) {
      note.textContent = "There are no strict false positives in the sample.";
      return;
    }

    note.textContent = "We use 60 as the “high” threshold (above the main site's 45 watch line) and only count readings lasting 20+ trading days, so brief touches of the watch line aren't scored as false alarms. Under this definition there are " + fps.length + " high-score spells in the sample. These spells occur after known crises, so they are post-crisis high readings rather than “ex-ante false alarms”; the sample contains no strict “high before, no decline after” false positive. Dates are in the table below.";

    fps.forEach(function (fp) {
      var tr = document.createElement("tr");
      addCell(tr, fp.start);
      addCell(tr, fp.end);
      addCell(tr, fp.trading_days, "num");
      addCell(tr, fp.max_score, "num");
      addCell(tr, fp.forward_6m_return + "%", "num");
      tbody.appendChild(tr);
    });
  }

  /* ---------------- chart ---------------- */

  function scoreChart(host, opts) {
    var data = opts.data;
    if (!data || !data.length) return;

    var W = 1000;
    var H = 340;
    var m = { t: 24, r: 80, b: 44, l: 48 };
    var plotW = W - m.l - m.r;
    var plotH = H - m.t - m.b;
    var unit = opts.unit || "";

    var x = function (i) { return m.l + (i / (data.length - 1)) * plotW; };
    var y = function (v) { return m.t + plotH - (v / 100) * plotH; };

    var s = el("svg", {
      viewBox: "0 0 " + W + " " + H,
      role: "img",
      "aria-label": opts.ariaLabel
    });

    for (var v = 0; v <= 100; v += 20) {
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
      }, v + unit));
    }

    (opts.episodes || []).filter(function (e) { return e.major; }).forEach(function (e) {
      var a = data.findIndex(function (p) { return p.d >= e.peak; });
      if (a < 0) a = 0;
      var b = data.findIndex(function (p) { return p.d > e.trough; });
      if (b < 0) b = data.length - 1;
      else b = Math.max(a, b - 1);
      var x1 = x(a);
      var x2 = x(b);
      s.appendChild(el("rect", {
        x: x1, y: m.t,
        width: Math.max(2, x2 - x1), height: plotH,
        fill: "rgba(208,59,59,0.08)"
      }));
    });

    var ty = y(opts.threshold);
    s.appendChild(el("line", {
      x1: m.l, x2: W - m.r, y1: ty, y2: ty,
      stroke: "var(--crit)", "stroke-width": 1.5, opacity: 0.75
    }));
    s.appendChild(el("text", {
      x: W - m.r + 6, y: ty + 4,
      fill: "var(--crit)", "font-size": 10.5, "font-weight": 600
    }, opts.thresholdLabel));

    var prevYear = null;
    data.forEach(function (p, i) {
      var yr = p.d.slice(0, 4);
      if (prevYear !== null && yr !== prevYear) {
        s.appendChild(el("text", {
          x: x(i), y: m.t + plotH + 24,
          "text-anchor": "middle",
          fill: "var(--muted)",
          "font-size": 10.5
        }, yr));
      }
      prevYear = yr;
    });
    var d = data.map(function (p, i) {
      return (i ? "L" : "M") + x(i).toFixed(1) + "," + y(p.v).toFixed(1);
    }).join(" ");
    s.appendChild(el("path", {
      d: d,
      fill: "none",
      stroke: opts.color,
      "stroke-width": 2,
      "stroke-linejoin": "round",
      "stroke-linecap": "round"
    }));

    var last = data[data.length - 1];
    s.appendChild(el("circle", {
      cx: x(data.length - 1), cy: y(last.v), r: 4.5,
      fill: opts.color, stroke: "var(--surface-1)", "stroke-width": 2
    }));
    s.appendChild(el("text", {
      x: x(data.length - 1) + 8, y: y(last.v) + 4,
      fill: "var(--ink)", "font-size": 12, "font-weight": 650
    }, last.v + unit));

    var cross = el("g", { opacity: 0 });
    var vline = el("line", {
      x1: 0, x2: 0, y1: m.t, y2: m.t + plotH,
      stroke: "var(--baseline)", "stroke-width": 1
    });
    var hdot = el("circle", {
      r: 4, fill: opts.color,
      stroke: "var(--surface-1)", "stroke-width": 2
    });
    cross.appendChild(vline);
    cross.appendChild(hdot);
    s.appendChild(cross);

    var overlay = el("rect", {
      x: m.l, y: m.t,
      width: plotW, height: plotH,
      fill: "transparent",
      tabindex: 0,
      role: "button",
      "aria-label": opts.ariaLabel
    });

    function nearest(ev) {
      var rect = s.getBoundingClientRect();
      var px = ((ev.clientX - rect.left) / rect.width) * W;
      return Math.max(0, Math.min(data.length - 1, Math.round(((px - m.l) / plotW) * (data.length - 1))));
    }

    function showAt(i, ev) {
      var p = data[i];
      var cx = x(i);
      var cy = y(p.v);
      vline.setAttribute("x1", cx);
      vline.setAttribute("x2", cx);
      hdot.setAttribute("cx", cx);
      hdot.setAttribute("cy", cy);
      cross.setAttribute("opacity", "1");

      var ep = (opts.episodes || []).find(function (e) {
        return e.major && p.d >= e.peak && p.d <= e.trough;
      });
      var rows = [{ label: opts.seriesLabel, value: p.v + unit, color: opts.color }];
      if (ep) rows.push({ label: "Drawdown window", value: ep.drawdown + "%" });
      ttShow(ev, p.d, rows);
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
    appendTable(host, ["Week", opts.seriesLabel], data.map(function (p) {
      return [p.d, p.v + unit];
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

    function apply(m) {
      if (m === "auto") delete document.documentElement.dataset.theme;
      else document.documentElement.dataset.theme = m;
      btn.textContent = labels[m];
      try { localStorage.setItem("crash-theme", m); } catch (e) {}
    }

    btn.addEventListener("click", function () {
      mode = modes[(modes.indexOf(mode) + 1) % modes.length];
      apply(mode);
    });

    apply(mode);
  }

  /* ---------------- init ---------------- */

  function init() {
    renderText();
    renderKpis();
    renderEpisodes();
    renderWarningStats();
    renderFalsePositives();

    scoreChart($("btChartRaw"), {
      data: D.series,
      episodes: D.episodes,
      threshold: 45,
      thresholdLabel: "Watch 45",
      color: "var(--s1)",
      unit: "",
      seriesLabel: "Raw risk score",
      ariaLabel: "Raw weighted risk score, 2017 to 2026, with major drawdown windows shaded"
    });

    scoreChart($("btChartPct"), {
      data: D.seriesPct,
      episodes: D.episodes,
      threshold: 80,
      thresholdLabel: "Relatively high 80",
      color: "var(--s2)",
      unit: "%",
      seriesLabel: "Rolling percentile",
      ariaLabel: "Rolling three-year risk percentile, 2017 to 2026, with major drawdown windows shaded"
    });

    initTheme();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
