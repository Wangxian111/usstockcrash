/* ==========================================================================
   US Stock Crash Radar · 3-Layer Trend Dashboard (home)
   Main layer: 7-condition 3-tier tracking; auxiliary: 6-signal fundamental risk score.
   Data is a 2026-11-18 snapshot, not live quotes.
   ========================================================================== */

"use strict";

const PAGE_DATA = {
  asOf: "2026-11-18",

  layer: {
    score: 6,
    total: 7,
    tier: "Warning",
    tone: "warn",
    confirmed: false,
    volumeRatio: 1.01,
    volumeThreshold: 1.5,
    summary: "6/7 conditions triggered; 30WMA not triggered; volume at 1.01× is below 1.5×, so the confirmation tier is not established.",
    tags: [
      { text: "Below 200DMA", tone: "warn" },
      { text: "Below 50DMA", tone: "warn" },
      { text: "ATR 97th pct", tone: "warn" },
      { text: "MACD weakening", tone: "warn" },
      { text: "RSI 36.6", tone: "mid" },
      { text: "VIX elevated", tone: "warn" }
    ],
    conditions: [
      { name: "Close < 200-day MA", type: "Trend", reading: "−0.3% below 200DMA", percentile: 18, threshold: "Bottom 20%", active: true, note: "Long-term trend broken" },
      { name: "Close < 50-day MA", type: "Trend", reading: "−4.24% below 50DMA", percentile: 7, threshold: "Bottom 20%", active: true, note: "Short-term trend weakening" },
      { name: "RSI(14) bottom 20%", type: "Momentum", reading: "RSI 36.6", percentile: 6, threshold: "Bottom 20%", active: true, note: "Momentum on the weak side" },
      { name: "Weekly close < 30-week MA", type: "Weekly", reading: "+0.29% above 30WMA", percentile: 22, threshold: "Bottom 20%", active: false, note: "Weekly trend intact" },
      { name: "ATR top 20%", type: "Volatility", reading: "ATR 97th percentile", percentile: 97, threshold: "Top 20%", active: true, note: "Volatility elevated" },
      { name: "VIX top 20%", type: "Volatility", reading: "VIX 24.6 (84th pct)", percentile: 84, threshold: "Top 20%", active: true, note: "VIX has reached the high zone" },
      { name: "MACD histogram bottom 20%", type: "Momentum", reading: "MACD hist −0.29% of price", percentile: 15, threshold: "Bottom 20%", active: true, note: "Momentum turning weaker" }
    ]
  },

  auxiliary: {
    score: 27.6,
    band: "Watch",
    tone: "mid",
    pct: 51.2,
    note: "Auxiliary score 27.6 (Watch); the main contribution is valuation at the 99.6th percentile (14.9/15), while credit/breadth/macro are all dark. It diverges from the main layer's 6/7 Warning: the technical layer deteriorated first and the fundamental layer has not confirmed.",
    signals: [
      { name: "Credit", value: 16.7, weight: 25, contribution: 4.2, note: "Credit stress low" },
      { name: "Breadth", value: 0.0, weight: 20, contribution: 0.0, note: "Equal/cap weight not deteriorating" },
      { name: "Valuation", value: 99.6, weight: 15, contribution: 14.9, note: "CAPE extremely high — main driver" },
      { name: "Volatility", value: 47.3, weight: 15, contribution: 7.1, note: "VIX/term structure mid-range" },
      { name: "Rates", value: 26.5, weight: 10, contribution: 2.6, note: "Rate pressure moderate" },
      { name: "Macro", value: 0.0, weight: 15, contribution: 0.0, note: "Unemployment not triggered" },
      { name: "Leverage / liquidity", value: null, weight: null, contribution: null, note: "Not modeled (insufficient free NFCI history)" },
      { name: "Sentiment / flows", value: null, weight: null, contribution: null, note: "Not modeled (no reliable free history)" },
      { name: "Structural risk", value: null, weight: null, contribution: null, note: "Not modeled (hard to quantify)" }
    ]
  },

  profiles: [
    { name: "A Low-frequency, conservative", rule: "≥6/7 conditions", alerts: "17 d/yr", win: "21.5%", recall: "7/9", drawdown: "−6.7%", current: false },
    { name: "B Balanced (current)", rule: "≥5/7 conditions", alerts: "29 d/yr", win: "19.8%", recall: "9/9", drawdown: "−6.0%", current: true },
    { name: "C High-frequency, sensitive", rule: "≥5/11 conditions", alerts: "52 d/yr", win: "13.0%", recall: "9/9", drawdown: "−4.7%", current: false },
    { name: "B + volume confirmation", rule: "≥5/7 + vol >1.5×", alerts: "4 d/yr", win: "45.0%", recall: "8/9", drawdown: "−8.2%", current: false }
  ]
};

const $ = (id) => document.getElementById(id);

function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

function addCell(tr, text, cls) {
  const td = document.createElement("td");
  td.textContent = text;
  if (cls) td.className = cls;
  tr.appendChild(td);
}

const TONE_BORDER = {
  good: "var(--good)",
  warn: "var(--warn)",
  serious: "var(--serious)",
  crit: "var(--crit)",
  mid: "var(--baseline)"
};
const TONE_TEXT = {
  good: "var(--good-text)",
  warn: "var(--warn-text)",
  serious: "var(--serious-text)",
  crit: "var(--crit)",
  mid: "var(--ink-2)"
};

/* ---------------- hero ---------------- */

function currentTier() {
  const L = PAGE_DATA.layer;
  if (L.score >= 5 && L.confirmed) return "confirm";
  if (L.score >= 5) return "warn";
  if (L.score >= 4) return "observe";
  return "calm";
}

function renderLayer() {
  const L = PAGE_DATA.layer;
  $("updTime").textContent = PAGE_DATA.asOf;
  $("bannerDate").textContent = PAGE_DATA.asOf;
  $("layerDate").textContent = PAGE_DATA.asOf;
  $("footerDate").textContent = PAGE_DATA.asOf;

  $("layerTier").textContent = L.tier;
  $("layerTier").style.color = TONE_TEXT[L.tone] || "var(--ink)";
  $("layerScore").textContent = L.score;
  $("layerSub").textContent = L.confirmed
    ? "Volume confirmation: triggered (" + L.volumeRatio.toFixed(2) + "×)"
    : "Volume confirmation: not triggered (" + L.volumeRatio.toFixed(2) + "×)";
  $("layerSummary").textContent = L.summary;

  const hero = $("layerHero");
  if (hero) hero.style.borderLeftColor = TONE_BORDER[L.tone] || "var(--warn)";

  const tier = currentTier();
  document.querySelectorAll(".layer-step").forEach((step) => {
    const key = step.getAttribute("data-tier");
    const active =
      (key === "observe" && L.score >= 4) ||
      (key === "warn" && L.score >= 5) ||
      (key === "confirm" && L.score >= 5 && L.confirmed);
    step.classList.toggle("active", active);
    step.classList.toggle("current", key === tier);
  });

  const tags = $("layerTags");
  clear(tags);
  L.tags.forEach((t) => {
    const span = document.createElement("span");
    span.className = "tag " + (t.tone || "");
    span.textContent = t.text;
    tags.appendChild(span);
  });
}

/* ---------------- KPI ---------------- */

function renderKpis() {
  const L = PAGE_DATA.layer;
  const A = PAGE_DATA.auxiliary;
  const items = [
    { label: "Current tier", value: L.tier, tone: L.tone },
    { label: "Conditions triggered", value: L.score + "/" + L.total, tone: L.tone },
    {
      label: "Volume confirmation" + (L.confirmed ? " (confirmed)" : " (not triggered)"),
      value: L.volumeRatio.toFixed(2) + "×",
      tone: L.confirmed ? "good" : "mid"
    },
    { label: "Auxiliary risk score", value: String(A.score), tone: A.tone },
    { label: "Historical event recall", value: "9/9", tone: "good" },
    { label: "Confirmation day win rate", value: "45.0%", tone: "good" }
  ];
  const host = $("layerKpis");
  clear(host);
  items.forEach((it) => {
    const card = document.createElement("div");
    card.className = "stat";
    const label = document.createElement("div");
    label.className = "stat-label";
    const dot = document.createElement("span");
    dot.className = "dot " + (it.tone || "mid");
    label.appendChild(dot);
    label.appendChild(document.createTextNode(it.label));
    const value = document.createElement("div");
    value.className = "stat-value";
    value.textContent = it.value;
    card.appendChild(label);
    card.appendChild(value);
    host.appendChild(card);
  });
}

/* ---------------- conditions ---------------- */

function renderConditions() {
  const L = PAGE_DATA.layer;
  const tbody = $("conditionRows");
  clear(tbody);

  L.conditions.forEach((c) => {
    const tr = document.createElement("tr");

    addCell(tr, c.name);
    addCell(tr, c.type);
    addCell(tr, c.reading);

    const tdRank = document.createElement("td");
    tdRank.className = "num";
    const bar = document.createElement("span");
    bar.className = "mini-bar";
    const fill = document.createElement("span");
    fill.style.width = Math.max(0, Math.min(100, c.percentile)) + "%";
    fill.style.background = c.active ? "var(--s2)" : "var(--deem)";
    bar.appendChild(fill);
    tdRank.appendChild(bar);
    tdRank.appendChild(document.createTextNode(c.percentile + "%"));
    tr.appendChild(tdRank);

    addCell(tr, c.threshold);

    const tdStatus = document.createElement("td");
    const status = document.createElement("span");
    status.className = "status-tag " + (c.active ? "status-warn" : "status-mid");
    const dot = document.createElement("span");
    dot.className = "dot " + (c.active ? "warn" : "mid");
    status.appendChild(dot);
    status.appendChild(document.createTextNode(c.active ? "Triggered" : "Not triggered"));
    tdStatus.appendChild(status);
    tr.appendChild(tdStatus);

    addCell(tr, c.note, "why");
    tbody.appendChild(tr);
  });

  $("conditionNote").textContent =
    L.score + "/" + L.total + " conditions triggered; the untriggered ones are 200DMA and VIX; " +
    "volume at " + L.volumeRatio.toFixed(2) + "× is " +
    (L.confirmed ? "at or above" : "below") + " 1.5×, so the confirmation tier is " +
    (L.confirmed ? "established." : "not established.");
}

/* ---------------- tiers ---------------- */

function renderTiers() {
  const L = PAGE_DATA.layer;
  const tier = currentTier();
  const cards = [
    {
      key: "observe", title: "Observation", rule: "≥4/7 conditions",
      text: "Start reviewing position sizing, concentration, and leverage; don't chase. Currently " + L.score + "/7 — the observation tier has been passed.",
      active: L.score >= 4
    },
    {
      key: "warn", title: "Warning", rule: "≥5/7 conditions",
      text: "Cut leverage, tighten stops, prepare a staged plan. Currently " + L.score + "/7.",
      active: L.score >= 5
    },
    {
      key: "confirm", title: "Confirmation", rule: "≥5/7 + volume",
      text: "Execute defensive actions; this is not a buy-the-dip signal. Volume currently " + L.volumeRatio.toFixed(2) + "× — unconfirmed.",
      active: L.score >= 5 && L.confirmed
    }
  ];
  const host = $("tierCards");
  clear(host);
  cards.forEach((c) => {
    const card = document.createElement("div");
    card.className = "tier-card" + (c.active ? " active" : "") + (c.key === tier ? " current" : "");
    const h = document.createElement("h3");
    h.textContent = c.title;
    const rule = document.createElement("div");
    rule.className = "rule";
    rule.textContent = c.rule;
    const p = document.createElement("p");
    p.textContent = c.text;
    card.appendChild(h);
    card.appendChild(rule);
    card.appendChild(p);
    if (c.key === tier) {
      const tag = document.createElement("span");
      tag.className = "tag warn";
      tag.textContent = "Current";
      card.appendChild(tag);
    }
    host.appendChild(card);
  });
}

/* ---------------- profiles ---------------- */

function renderProfiles() {
  const tbody = $("profileRows");
  clear(tbody);
  PAGE_DATA.profiles.forEach((p) => {
    const tr = document.createElement("tr");
    const tdName = document.createElement("td");
    tdName.textContent = p.name;
    if (p.current) {
      const tag = document.createElement("span");
      tag.className = "tag warn";
      tag.textContent = " Current";
      tag.style.marginLeft = "6px";
      tdName.appendChild(tag);
    }
    tr.appendChild(tdName);
    addCell(tr, p.rule);
    addCell(tr, p.alerts, "num");
    addCell(tr, p.win, "num");
    addCell(tr, p.recall, "num");
    addCell(tr, p.drawdown, "num");
    tbody.appendChild(tr);
  });
}

/* ---------------- auxiliary ---------------- */

function renderAuxiliary() {
  const A = PAGE_DATA.auxiliary;
  $("auxScore").textContent = A.score.toFixed(1);
  $("auxBand").textContent = A.band + " (" + A.score.toFixed(1) + "/100)";
  $("auxNote").textContent = A.note;

  const marker = $("auxMarker");
  if (marker) marker.style.left = A.score + "%";
  const meter = $("auxMeter");
  if (meter) {
    meter.setAttribute("aria-label", "Auxiliary risk score " + A.score.toFixed(1) + ", in the " + A.band + " zone");
  }

  const tbody = $("auxRows");
  clear(tbody);
  A.signals.forEach((s) => {
    const tr = document.createElement("tr");
    addCell(tr, s.name);
    addCell(tr, s.value == null ? "—" : s.value.toFixed(1), "num");
    addCell(tr, s.weight == null ? "—" : s.weight, "num");
    addCell(tr, s.contribution == null ? "—" : s.contribution.toFixed(1), "num");
    addCell(tr, s.note, "why");
    tbody.appendChild(tr);
  });
}

/* ---------------- theme ---------------- */

function initTheme() {
  const btn = $("themeBtn");
  if (!btn) return;
  const modes = ["auto", "light", "dark"];
  const labels = { auto: "Theme: Auto", light: "Theme: Light", dark: "Theme: Dark" };
  let mode = "auto";

  try {
    const saved = localStorage.getItem("crash-theme");
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
  renderLayer();
  renderKpis();
  renderConditions();
  renderTiers();
  renderProfiles();
  renderAuxiliary();
  initTheme();
}

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
