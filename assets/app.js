/* ==========================================================================
   美股暴跌预警 · 三层趋势雷达（首页）
   主层：7 条件三层跟踪；辅助：6 信号基本面风险分。
   数据为 2026-11-24 快照，非实时行情。
   ========================================================================== */

"use strict";

const PAGE_DATA = {
  asOf: "2026-11-24",

  layer: {
    score: 7,
    total: 7,
    tier: "警告层",
    tone: "warn",
    confirmed: false,
    volumeRatio: 1.02,
    volumeThreshold: 1.5,
    summary: "7/7 条件全部触发；放量 1.02× 低于 1.5×，确认层未成立。",
    tags: [
      { text: "200DMA 下方", tone: "warn" },
      { text: "50DMA 下方", tone: "warn" },
      { text: "周线 30WMA 下方", tone: "warn" },
      { text: "ATR 100% 分位", tone: "warn" },
      { text: "MACD 走弱", tone: "warn" },
      { text: "RSI 40.5", tone: "mid" },
      { text: "VIX 高位", tone: "warn" }
    ],
    conditions: [
      { name: "收盘 < 200 日均线", type: "趋势", reading: "低于 200DMA −1.9%", percentile: 14, threshold: "后 20% 分位", active: true, note: "长期趋势已破坏" },
      { name: "收盘 < 50 日均线", type: "趋势", reading: "低于 50DMA −5.25%", percentile: 5, threshold: "后 20% 分位", active: true, note: "短期趋势走弱" },
      { name: "RSI(14) 后 20%", type: "动量", reading: "RSI 40.5", percentile: 11, threshold: "后 20% 分位", active: true, note: "动量偏弱" },
      { name: "周收盘 < 30 周均线", type: "周线", reading: "低于 30WMA −8.20%", percentile: 5, threshold: "后 20% 分位", active: true, note: "周线趋势走弱" },
      { name: "ATR 前 20%", type: "波动率", reading: "ATR 100% 分位", percentile: 100, threshold: "前 20% 分位", active: true, note: "波动率处于高位" },
      { name: "VIX 前 20%", type: "波动率", reading: "VIX 26.4（88% 分位）", percentile: 88, threshold: "前 20% 分位", active: true, note: "VIX 进入高位" },
      { name: "MACD 柱后 20%", type: "动量", reading: "MACD 柱 −0.49%/价格", percentile: 7, threshold: "后 20% 分位", active: true, note: "动量转弱" }
    ]
  },

  auxiliary: {
    score: 31.4,
    band: "观察",
    tone: "mid",
    pct: 72.4,
    note: "辅助分 31.4（观察），主要贡献来自估值 99.6 分位（14.9/15），信用/宽度/利率/宏观都未亮。与主层 7/7 警告出现分歧：技术层先恶化，基本面层尚未确认。",
    signals: [
      { name: "信用", value: 24.1, weight: 25, contribution: 6.0, note: "信用压力低" },
      { name: "宽度", value: 0.0, weight: 20, contribution: 0.0, note: "等权/市值权未恶化" },
      { name: "估值", value: 99.6, weight: 15, contribution: 14.9, note: "CAPE 极高，主要贡献" },
      { name: "波动率", value: 52.7, weight: 15, contribution: 7.9, note: "VIX/期限结构中位" },
      { name: "利率", value: 22.5, weight: 10, contribution: 2.2, note: "实际利率/曲线温和" },
      { name: "宏观", value: 0.0, weight: 15, contribution: 0.0, note: "失业率未触发" },
      { name: "杠杆/流动性", value: null, weight: null, contribution: null, note: "未建模（NFCI 免费历史不足）" },
      { name: "情绪/资金", value: null, weight: null, contribution: null, note: "未建模（无可靠免费历史）" },
      { name: "结构性风险", value: null, weight: null, contribution: null, note: "未建模（难以量化）" }
    ]
  },

  profiles: [
    { name: "A 低频保守", rule: "7 条件 ≥6/7", alerts: "17 天/年", win: "21.5%", recall: "7/9", drawdown: "−6.7%", current: false },
    { name: "B 均衡（当前）", rule: "7 条件 ≥5/7", alerts: "29 天/年", win: "19.8%", recall: "9/9", drawdown: "−6.0%", current: true },
    { name: "C 高频灵敏", rule: "11 条件 ≥5/11", alerts: "52 天/年", win: "13.0%", recall: "9/9", drawdown: "−4.7%", current: false },
    { name: "B + 放量确认", rule: "≥5/7 + 量 >1.5×", alerts: "4 天/年", win: "45.0%", recall: "8/9", drawdown: "−8.2%", current: false }
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
    ? "放量确认：已触发（" + L.volumeRatio.toFixed(2) + "×）"
    : "放量确认：未触发（" + L.volumeRatio.toFixed(2) + "×）";
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
    { label: "当前层级", value: L.tier, tone: L.tone },
    { label: "触发条件", value: L.score + "/" + L.total, tone: L.tone },
    {
      label: "放量确认" + (L.confirmed ? "（已确认）" : "（未触发）"),
      value: L.volumeRatio.toFixed(2) + "×",
      tone: L.confirmed ? "good" : "mid"
    },
    { label: "辅助风险分", value: String(A.score), tone: A.tone },
    { label: "历史事件召回", value: "9/9", tone: "good" },
    { label: "确认层日胜率", value: "45.0%", tone: "good" }
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
    status.appendChild(document.createTextNode(c.active ? "触发" : "未触发"));
    tdStatus.appendChild(status);
    tr.appendChild(tdStatus);

    addCell(tr, c.note, "why");
    tbody.appendChild(tr);
  });

  $("conditionNote").textContent =
    L.score + "/" + L.total + " 条件触发；未触发的是 200DMA 与 VIX；" +
    "放量 " + L.volumeRatio.toFixed(2) + "× " +
    (L.confirmed ? "已达到" : "低于") + " 1.5×，确认层" +
    (L.confirmed ? "成立。" : "未成立。");
}

/* ---------------- tiers ---------------- */

function renderTiers() {
  const L = PAGE_DATA.layer;
  const tier = currentTier();
  const cards = [
    {
      key: "observe", title: "观察层", rule: "条件 ≥4/7",
      text: "开始检查仓位、集中度和杠杆；不要追高。当前 " + L.score + "/7，已越过观察层。",
      active: L.score >= 4
    },
    {
      key: "warn", title: "警告层", rule: "条件 ≥5/7",
      text: "降低杠杆、收紧止损、准备分批计划。当前 " + L.score + "/7。",
      active: L.score >= 5
    },
    {
      key: "confirm", title: "确认层", rule: "≥5/7 + 放量",
      text: "执行防守动作；不是抄底信号。当前放量 " + L.volumeRatio.toFixed(2) + "×，未确认。",
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
      tag.textContent = "当前";
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
      tag.textContent = " 当前";
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
  $("auxBand").textContent = A.band + "（" + A.score.toFixed(1) + "/100）";
  $("auxNote").textContent = A.note;

  const marker = $("auxMarker");
  if (marker) marker.style.left = A.score + "%";
  const meter = $("auxMeter");
  if (meter) {
    meter.setAttribute("aria-label", "辅助风险分 " + A.score.toFixed(1) + "，处于" + A.band + "区间");
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
  const labels = { auto: "主题：自动", light: "主题：浅色", dark: "主题：深色" };
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
