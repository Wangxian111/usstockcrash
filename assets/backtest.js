/* 历史回测页 · 图表与表格渲染 */
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
    summary.textContent = "查看数据表";
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
      s.majorCount + " 次 ≥10% 回撤中，" +
      s.early + " 次提前预警、" +
      s.partial + " 次部分预警、" +
      s.coincident + " 次同步确认、" +
      s.missed + " 次未捕捉；2022 年完全没抓到。它更像“相对脆弱度”温度计，而不是时点预测器。";

    $("btConclusion").textContent =
      "回测窗口 " + D.meta.windowStart + " 至 " + D.meta.windowEnd +
      "，共 " + s.majorCount + " 次 ≥10% 回撤。模型只在 2025 年 2–4 月回撤前给出较清晰的提前预警；" +
      "2020 年 2 月只有约 10 天的短暂提示；2018 年 Q4 是同步确认；2022 年是完全漏报。" +
      "2018 年 1 月的部分预警在峰值前已经回落。注意：这里的“提前/部分预警”按滚动 3 年分位判定；" +
      "原始加权分在 2025 年 T-30 为 36.9、2020 年 T-10 为 35.7，都没有达到主站 45 的“关注”阈值。" +
      "它更适合回答“现在有多脆弱”，而不是“哪天会跌”。";

    var tags = [
      { text: "2025 提前预警", tone: "warn" },
      { text: "2020 约 10 天", tone: "warn" },
      { text: "2018Q4 同步确认", tone: "crit" },
      { text: "2022 漏报", tone: "crit" },
      { text: "2024/2026 小幅回撤", tone: "" }
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
      { label: "≥10% 回撤", value: s.majorCount, tone: "mid" },
      { label: "提前预警", value: s.early, tone: "good" },
      { label: "部分预警", value: s.partial, tone: "warn" },
      { label: "同步确认", value: s.coincident, tone: "serious" },
      { label: "未捕捉", value: s.missed, tone: "crit" },
      { label: "事后高位", value: s.falsePositiveCount, tone: "mid" }
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
    var tone = label === "提前预警" ? "good"
      : label === "部分预警" ? "warn"
      : label === "同步确认" ? "serious"
      : label === "未捕捉" ? "crit"
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
    if (r.label === "提前预警") return "T-30 分位 " + r.pct_t30 + "%，相对高位";
    if (r.label === "部分预警") {
      if (r.pct_t10 != null && r.pct_t30 != null && r.pct_t10 >= 75 && r.pct_t30 < 65) {
        return "T-10 分位 " + r.pct_t10 + "%，约 10 天提前量";
      }
      return "T-30 分位 " + r.pct_t30 + "%，但 T-10 回落至 " + r.pct_t10 + "%";
    }
    if (r.label === "同步确认") return "峰值后才升破 80% 分位";
    if (r.label === "未捕捉") return "峰值前分位 " + r.pct_t30 + "%，下跌后才抬升";
    return "8–10% 回撤，不纳入主统计";
  }

  function sharpNote(r) {
    return "T-30 分位 " + (r.pct_t30 == null ? "—" : r.pct_t30 + "%") +
      " / T-10 " + (r.pct_t10 == null ? "—" : r.pct_t10 + "%") +
      " · 只跌 " + Math.abs(r.drawdown) + "%";
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
      td.appendChild(statusEl("小幅回撤"));
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
      addCell(tr, "分位 ≥" + k + " · 持续 10 日");
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
        "按分位 ≥80、持续 10 个交易日、未来 6 个月的定义：" +
        a80.preCrisis + " 次事前预警，" + a80.hits + " 次命中 ≥10% 回撤，" +
        a80.falsePositives + " 次误报，误报率 " + a80.falsePositiveRate + "%。" +
        "如果把 8% 也算作大跌：" + b80.hits + " 次命中、" +
        b80.falsePositives + " 次误报，误报率 " + b80.falsePositiveRate + "%。";
    }

    var detail = $("btWarnDetailRows");
    clear(detail);
    var rows = (s10["80"] && s10["80"].rows) || [];
    var labels = { hit: "命中", "false": "误报", post: "事后高位" };
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
      note.textContent = "样本内没有严格意义上的误报。";
      return;
    }

    note.textContent = "这里用 60 作为“高位”阈值（高于主站 45 的关注线），只统计持续 20 个交易日以上的读数，避免把短暂触及关注线也算成误报。按此定义，样本内共有 " + fps.length + " 段高分读数。这些区间发生在已知危机之后，属于危机后的高位读数，不是“事前误报”；样本内没有“事前高分、事后没跌”的严格误报。具体日期见下表。";

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
      if (ep) rows.push({ label: "回撤区间", value: ep.drawdown + "%" });
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
    appendTable(host, ["周", opts.seriesLabel], data.map(function (p) {
      return [p.d, p.v + unit];
    }));
  }

  /* ---------------- theme ---------------- */

  function initTheme() {
    var btn = $("themeBtn");
    if (!btn) return;
    var modes = ["auto", "light", "dark"];
    var labels = { auto: "主题：自动", light: "主题：浅色", dark: "主题：深色" };
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
      thresholdLabel: "关注 45",
      color: "var(--s1)",
      unit: "",
      seriesLabel: "原始风险分",
      ariaLabel: "2017 至 2026 年原始风险加权分走势，阴影为重大回撤区间"
    });

    scoreChart($("btChartPct"), {
      data: D.seriesPct,
      episodes: D.episodes,
      threshold: 80,
      thresholdLabel: "相对高位 80",
      color: "var(--s2)",
      unit: "%",
      seriesLabel: "滚动分位",
      ariaLabel: "2017 至 2026 年滚动三年风险分位走势，阴影为重大回撤区间"
    });

    initTheme();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
