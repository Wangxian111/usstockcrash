# -*- coding: utf-8 -*-
"""Generate the English build of the crash-radar JS/data assets.

Reads the Chinese originals from <repo>/assets and writes translated copies to
<repo>/en/assets. Every replacement must match exactly once unless the pattern
is listed in MULTI (appears in several places by design).
"""
import re
import sys
from pathlib import Path

ROOT = Path(r"F:\Claudeproject\USStockcrashedOfficial")
SRC = ROOT / "assets"
DST = ROOT / "en" / "assets"
DST.mkdir(parents=True, exist_ok=True)


def apply(text, pairs, label):
    for old, new in pairs:
        n = text.count(old)
        if n == 0:
            raise SystemExit("[MISS] %s: pattern not found:\n%r" % (label, old[:160]))
        text = text.replace(old, new)
    return text


# ---------------------------------------------------------------- backtest.js
BT = [
    # header comment
    ("/* 历史回测页 · 图表与表格渲染 */",
     "/* Backtest page · chart and table rendering */"),

    ('summary.textContent = "查看数据表";',
     'summary.textContent = "View data table";'),

    # banner summary
    ('      s.majorCount + " 次 ≥10% 回撤中，" +\n'
     '      s.early + " 次提前预警、" +\n'
     '      s.partial + " 次部分预警、" +\n'
     '      s.coincident + " 次同步确认、" +\n'
     '      s.missed + " 次未捕捉；2022 年完全没抓到。它更像“相对脆弱度”温度计，而不是时点预测器。";',
     '      "Of " + s.majorCount + " ≥10% drawdowns: " +\n'
     '      s.early + " early warnings, " +\n'
     '      s.partial + " partial warnings, " +\n'
     '      s.coincident + " coincident confirmations, " +\n'
     '      s.missed + " missed; 2022 was a complete miss. It is more a “relative fragility” thermometer than a timing predictor.";'),

    # long conclusion
    ('      "回测窗口 " + D.meta.windowStart + " 至 " + D.meta.windowEnd +\n'
     '      "，共 " + s.majorCount + " 次 ≥10% 回撤。模型只在 2025 年 2–4 月回撤前给出较清晰的提前预警；" +\n'
     '      "2020 年 2 月只有约 10 天的短暂提示；2018 年 Q4 是同步确认；2022 年是完全漏报。" +\n'
     '      "2018 年 1 月的部分预警在峰值前已经回落。注意：这里的“提前/部分预警”按滚动 3 年分位判定；" +\n'
     '      "原始加权分在 2025 年 T-30 为 36.9、2020 年 T-10 为 35.7，都没有达到主站 45 的“关注”阈值。" +\n'
     '      "它更适合回答“现在有多脆弱”，而不是“哪天会跌”。";',
     '      "Backtest window " + D.meta.windowStart + " to " + D.meta.windowEnd +\n'
     '      ", " + s.majorCount + " ≥10% drawdowns in total. The model only gave a fairly clear early warning before the Feb–Apr 2025 drawdown; " +\n'
     '      "Feb 2020 produced just a roughly 10-day brief hint; Q4 2018 was a coincident confirmation; 2022 was a complete miss. " +\n'
     '      "The partial warning in Jan 2018 had already faded before the peak. Note: “early/partial” here is judged on the rolling 3-year percentile; " +\n'
     '      "the raw weighted score was 36.9 at 2025 T-30 and 35.7 at 2020 T-10 — neither reached the main site\'s 45 “watch” threshold. " +\n'
     '      "It answers “how fragile is this now” far better than “when will it fall”.";'),

    # tags
    ('      { text: "2025 提前预警", tone: "warn" },\n'
     '      { text: "2020 约 10 天", tone: "warn" },\n'
     '      { text: "2018Q4 同步确认", tone: "crit" },\n'
     '      { text: "2022 漏报", tone: "crit" },\n'
     '      { text: "2024/2026 小幅回撤", tone: "" }',
     '      { text: "2025 early warning", tone: "warn" },\n'
     '      { text: "2020 ~10 days", tone: "warn" },\n'
     '      { text: "2018Q4 coincident", tone: "crit" },\n'
     '      { text: "2022 missed", tone: "crit" },\n'
     '      { text: "2024/2026 minor dips", tone: "" }'),

    # KPI labels
    ('      { label: "≥10% 回撤", value: s.majorCount, tone: "mid" },\n'
     '      { label: "提前预警", value: s.early, tone: "good" },\n'
     '      { label: "部分预警", value: s.partial, tone: "warn" },\n'
     '      { label: "同步确认", value: s.coincident, tone: "serious" },\n'
     '      { label: "未捕捉", value: s.missed, tone: "crit" },\n'
     '      { label: "事后高位", value: s.falsePositiveCount, tone: "mid" }',
     '      { label: "≥10% drawdowns", value: s.majorCount, tone: "mid" },\n'
     '      { label: "Early warnings", value: s.early, tone: "good" },\n'
     '      { label: "Partial warnings", value: s.partial, tone: "warn" },\n'
     '      { label: "Coincident", value: s.coincident, tone: "serious" },\n'
     '      { label: "Missed", value: s.missed, tone: "crit" },\n'
     '      { label: "Post-crisis highs", value: s.falsePositiveCount, tone: "mid" }'),

    # status tone mapping (keys must match the data labels)
    ('    var tone = label === "提前预警" ? "good"\n'
     '      : label === "部分预警" ? "warn"\n'
     '      : label === "同步确认" ? "serious"\n'
     '      : label === "未捕捉" ? "crit"',
     '    var tone = label === "Early warning" ? "good"\n'
     '      : label === "Partial warning" ? "warn"\n'
     '      : label === "Coincident confirmation" ? "serious"\n'
     '      : label === "Missed" ? "crit"'),

    # epNote
    ('    if (r.label === "提前预警") return "T-30 分位 " + r.pct_t30 + "%，相对高位";\n'
     '    if (r.label === "部分预警") {\n'
     '      if (r.pct_t10 != null && r.pct_t30 != null && r.pct_t10 >= 75 && r.pct_t30 < 65) {\n'
     '        return "T-10 分位 " + r.pct_t10 + "%，约 10 天提前量";\n'
     '      }\n'
     '      return "T-30 分位 " + r.pct_t30 + "%，但 T-10 回落至 " + r.pct_t10 + "%";\n'
     '    }\n'
     '    if (r.label === "同步确认") return "峰值后才升破 80% 分位";\n'
     '    if (r.label === "未捕捉") return "峰值前分位 " + r.pct_t30 + "%，下跌后才抬升";\n'
     '    return "8–10% 回撤，不纳入主统计";',
     '    if (r.label === "Early warning") return "T-30 percentile " + r.pct_t30 + "% — relatively high";\n'
     '    if (r.label === "Partial warning") {\n'
     '      if (r.pct_t10 != null && r.pct_t30 != null && r.pct_t10 >= 75 && r.pct_t30 < 65) {\n'
     '        return "T-10 percentile " + r.pct_t10 + "% — about 10 days of lead";\n'
     '      }\n'
     '      return "T-30 percentile " + r.pct_t30 + "%, but T-10 fell back to " + r.pct_t10 + "%";\n'
     '    }\n'
     '    if (r.label === "Coincident confirmation") return "Crossed the 80th percentile only after the peak";\n'
     '    if (r.label === "Missed") return "Pre-peak percentile " + r.pct_t30 + "% — rose only after the decline";\n'
     '    return "8–10% drawdown, excluded from main statistics";'),

    # sharpNote
    ('    return "T-30 分位 " + (r.pct_t30 == null ? "—" : r.pct_t30 + "%") +',
     '    return "T-30 percentile " + (r.pct_t30 == null ? "—" : r.pct_t30 + "%") +'),
    ('      " · 只跌 " + Math.abs(r.drawdown) + "%";',
     '      " · only " + Math.abs(r.drawdown) + "%";'),

    ('      td.appendChild(statusEl("小幅回撤"));',
     '      td.appendChild(statusEl("Minor drawdown"));'),

    ('      addCell(tr, "分位 ≥" + k + " · 持续 10 日");',
     '      addCell(tr, "Percentile ≥" + k + " · 10-day persistence");'),

    # warning-stat note
    ('        "按分位 ≥80、持续 10 个交易日、未来 6 个月的定义：" +\n'
     '        a80.preCrisis + " 次事前预警，" + a80.hits + " 次命中 ≥10% 回撤，" +\n'
     '        a80.falsePositives + " 次误报，误报率 " + a80.falsePositiveRate + "%。" +\n'
     '        "如果把 8% 也算作大跌：" + b80.hits + " 次命中、" +\n'
     '        b80.falsePositives + " 次误报，误报率 " + b80.falsePositiveRate + "%。";',
     '        "Using percentile ≥80, 10-trading-day persistence, and a 6-month horizon: " +\n'
     '        a80.preCrisis + " advance warnings, " + a80.hits + " hits on ≥10% drawdowns, " +\n'
     '        a80.falsePositives + " false alarms — a " + a80.falsePositiveRate + "% false rate. " +\n'
     '        "Counting 8% as a crash too: " + b80.hits + " hits and " +\n'
     '        b80.falsePositives + " false alarms — a " + b80.falsePositiveRate + "% false rate.";'),

    ('    var labels = { hit: "命中", "false": "误报", post: "事后高位" };',
     '    var labels = { hit: "Hit", "false": "False alarm", post: "Post-crisis high" };'),

    ('      note.textContent = "样本内没有严格意义上的误报。";',
     '      note.textContent = "There are no strict false positives in the sample.";'),

    ('    note.textContent = "这里用 60 作为“高位”阈值（高于主站 45 的关注线），只统计持续 20 个交易日以上的读数，避免把短暂触及关注线也算成误报。按此定义，样本内共有 " + fps.length + " 段高分读数。这些区间发生在已知危机之后，属于危机后的高位读数，不是“事前误报”；样本内没有“事前高分、事后没跌”的严格误报。具体日期见下表。";',
     '    note.textContent = "We use 60 as the “high” threshold (above the main site\'s 45 watch line) and only count readings lasting 20+ trading days, so brief touches of the watch line aren\'t scored as false alarms. Under this definition there are " + fps.length + " high-score spells in the sample. These spells occur after known crises, so they are post-crisis high readings rather than “ex-ante false alarms”; the sample contains no strict “high before, no decline after” false positive. Dates are in the table below.";'),

    ('rows.push({ label: "回撤区间", value: ep.drawdown + "%" });',
     'rows.push({ label: "Drawdown window", value: ep.drawdown + "%" });'),

    ('appendTable(host, ["周", opts.seriesLabel]',
     'appendTable(host, ["Week", opts.seriesLabel]'),

    ('    var labels = { auto: "主题：自动", light: "主题：浅色", dark: "主题：深色" };',
     '    var labels = { auto: "Theme: Auto", light: "Theme: Light", dark: "Theme: Dark" };'),

    # chart options
    ('      thresholdLabel: "关注 45",\n'
     '      color: "var(--s1)",\n'
     '      unit: "",\n'
     '      seriesLabel: "原始风险分",\n'
     '      ariaLabel: "2017 至 2026 年原始风险加权分走势，阴影为重大回撤区间"',
     '      thresholdLabel: "Watch 45",\n'
     '      color: "var(--s1)",\n'
     '      unit: "",\n'
     '      seriesLabel: "Raw risk score",\n'
     '      ariaLabel: "Raw weighted risk score, 2017 to 2026, with major drawdown windows shaded"'),

    ('      thresholdLabel: "相对高位 80",\n'
     '      color: "var(--s2)",\n'
     '      unit: "%",\n'
     '      seriesLabel: "滚动分位",\n'
     '      ariaLabel: "2017 至 2026 年滚动三年风险分位走势，阴影为重大回撤区间"',
     '      thresholdLabel: "Relatively high 80",\n'
     '      color: "var(--s2)",\n'
     '      unit: "%",\n'
     '      seriesLabel: "Rolling percentile",\n'
     '      ariaLabel: "Rolling three-year risk percentile, 2017 to 2026, with major drawdown windows shaded"'),
]

# ------------------------------------------------------------- technical.js
TECH = [
    ("/* 技术分析叠加页 · 表格与价格图 */",
     "/* Technical analysis page · tables and price chart */"),

    ('summary.textContent = "查看数据表";',
     'summary.textContent = "View data table";'),

    ('      "纯技术模型 Top 20% 胜率 " + tech.precision + "%（基准 " + D.nearHighBaseRate + "%），" +\n'
     '      "Top 10% 胜率 " + tech10.precision + "%；但 AUC " + tech.auc + "，" +\n'
     '      "年度中位数 " + s.medianPrecision + "%。叠加基本面后 Top 20% 降到 " + comb.precision + "%。";',
     '      "Pure technical top-20% hit rate " + tech.precision + "% (base rate " + D.nearHighBaseRate + "%), " +\n'
     '      "top-10% hit rate " + tech10.precision + "%; but AUC " + tech.auc + " and " +\n'
     '      "a yearly median of " + s.medianPrecision + "%. Adding fundamentals pulls top 20% down to " + comb.precision + "%.";'),

    ('      "把技术指标单独拿来预测未来 6 个月 ≥10% 回撤，纯技术模型 Top 20% 胜率 " + tech.precision +\n'
     '      "%（基准 " + D.nearHighBaseRate + "%，提升 " + tech.lift + "），Top 10% 胜率 " + tech10.precision +\n'
     '      "%；但 AUC 只有 " + tech.auc + "，年度中位数 " + s.medianPrecision + "%，" +\n'
     '      s.years + " 个可评估年份里只有 " + s.yearsAboveBase + " 年高于基准。" +\n'
     '      "叠加基本面风险分后，Top 20% 胜率反而降到 " + comb.precision + "%，AUC " + comb.auc +\n'
     '      "；原因是基本面风险分在近高点几乎不亮，且它本身在下跌中才升高，对“从当前价再跌 10%”是反向的。" +\n'
     '      "单指标里最有用的是高波动（ATR >80% 分位，胜率 37.1%，但召回只有 8.2%）和周布林挤压（29.9%，召回 21.1%）；" +\n'
     '      "超买 RSI 反而偏多（16.7%，提升 0.74）。结论：技术分析可以作为“不要在高波动/趋势破坏时加仓”的过滤器，" +\n'
     '      "但不能单独作为暴跌择时信号；加上它不会给你一个可靠的全局胜率。";',
     '      "Used on its own to predict ≥10% drawdowns over the next 6 months, the pure technical model has a top-20% hit rate of " + tech.precision +\n'
     '      "% (base rate " + D.nearHighBaseRate + "%, lift " + tech.lift + ") and a top-10% hit rate of " + tech10.precision +\n'
     '      "%; but AUC is only " + tech.auc + " and the yearly median is " + s.medianPrecision + "%, with only " +\n'
     '      s.yearsAboveBase + " of " + s.years + " evaluable years beating the base rate. " +\n'
     '      "Adding the fundamental risk score actually lowers the top-20% hit rate to " + comb.precision + "% (AUC " + comb.auc +\n'
     '      "); the fundamental score barely lights up near highs, and since it rises during declines it is contrarian for “another 10% fall from here.” " +\n'
     '      "The most useful single indicators are high volatility (ATR >80th percentile, 37.1% hit rate but only 8.2% recall) and the weekly Bollinger squeeze (29.9%, 21.1% recall); " +\n'
     '      "an overbought RSI actually leans bullish (16.7%, lift 0.74). Conclusion: technical analysis works as a filter for “don\'t add at high volatility / after trend damage,” " +\n'
     '      "but not as a standalone crash-timing signal; adding it does not give you a reliable overall hit rate.";'),

    ('      { text: "纯技术 Top20 " + tech.precision + "%", tone: "warn" },\n'
     '      { text: "Top10 " + tech10.precision + "%", tone: "warn" },\n'
     '      { text: "AUC " + tech.auc, tone: "crit" },\n'
     '      { text: "叠加后 " + comb.precision + "%", tone: "crit" },\n'
     '      { text: "超买 RSI 反而偏多", tone: "" }',
     '      { text: "Pure technical top20 " + tech.precision + "%", tone: "warn" },\n'
     '      { text: "Top10 " + tech10.precision + "%", tone: "warn" },\n'
     '      { text: "AUC " + tech.auc, tone: "crit" },\n'
     '      { text: "With overlay " + comb.precision + "%", tone: "crit" },\n'
     '      { text: "Overbought RSI leans bullish", tone: "" }'),

    ('      "近高样本基准 " + D.nearHighBaseRate + "%。ATR >80% 分位胜率 37.1% 但召回仅 8.2%；" +\n'
     '      "周布林带宽 <20% 分位胜率 29.9%、召回 21.1%；超买 RSI(14)>70 胜率 16.7%，低于基准。" +\n'
     '      "表中“提升”= 信号胜率 ÷ 基准胜率；召回 = 该信号覆盖了多少未来大跌。";',
     '      "Near-high base rate " + D.nearHighBaseRate + "%. ATR >80th percentile has a 37.1% hit rate but only 8.2% recall; " +\n'
     '      "weekly Bollinger width <20th percentile has a 29.9% hit rate with 21.1% recall; overbought RSI(14)>70 has a 16.7% hit rate, below the base rate. " +\n'
     '      "“Lift” = signal hit rate ÷ base rate; recall = how much of future crashes the signal covers.";'),

    ('      "纯技术模型 Top20 胜率 " + tech.precision + "%（95% CI " +\n'
     '      (tech.precisionCI ? tech.precisionCI[0] + "–" + tech.precisionCI[1] + "%" : "—") +\n'
     '      "），AUC " + tech.auc + "，仅略高于随机。叠加基本面后 AUC " + comb.auc +\n'
     '      "、Top20 胜率 " + comb.precision + "%，没有增益。";',
     '      "Pure technical model top-20% hit rate " + tech.precision + "% (95% CI " +\n'
     '      (tech.precisionCI ? tech.precisionCI[0] + "–" + tech.precisionCI[1] + "%" : "—") +\n'
     '      "), AUC " + tech.auc + " — only slightly better than random. With the fundamental overlay, AUC " + comb.auc +\n'
     '      " and top-20% hit rate " + comb.precision + "%: no gain.";'),

    ('      { label: "近高基准胜率", value: D.nearHighBaseRate + "%", tone: "mid" },\n'
     '      { label: "纯技术 Top 20%", value: m.technical.top20.precision + "%", tone: "good" },\n'
     '      { label: "纯技术 Top 10%", value: m.technical.top10.precision + "%", tone: "good" },\n'
     '      { label: "叠加基本面 Top 20%", value: m.combined.top20.precision + "%", tone: "warn" },\n'
     '      { label: "年度中位数", value: s.medianPrecision + "%", tone: "warn" },\n'
     '      {\n'
     '        label: "高于基准年份",',
     '      { label: "Near-high base rate", value: D.nearHighBaseRate + "%", tone: "mid" },\n'
     '      { label: "Pure technical Top 20%", value: m.technical.top20.precision + "%", tone: "good" },\n'
     '      { label: "Pure technical Top 10%", value: m.technical.top10.precision + "%", tone: "good" },\n'
     '      { label: "With fundamentals Top 20%", value: m.combined.top20.precision + "%", tone: "warn" },\n'
     '      { label: "Yearly median", value: s.medianPrecision + "%", tone: "warn" },\n'
     '      {\n'
     '        label: "Years above base rate",'),

    ('      ["fundamental", "基本面评分"],\n'
     '      ["technical", "纯技术"],\n'
     '      ["combined", "基本面 + 技术"]',
     '      ["fundamental", "Fundamental score"],\n'
     '      ["technical", "Pure technical"],\n'
     '      ["combined", "Fundamental + technical"]'),

    ('      var note = r.skipped ? (r.reason || "跳过") : (r.year === 2026 ? "无正样本，仅作观察" : "");',
     '      var note = r.skipped ? (r.reason || "Skipped") : (r.year === 2026 ? "No positive samples; informational only" : "");'),

    ('      "纯技术 Top20 胜率：" + (parts || "—") + "；中位数 " + D.stability.medianPrecision +\n'
     '      "%，" + D.stability.yearsAboveBase + "/" + D.stability.years +\n'
     '      " 年高于基准。年度波动太大，不能把 pooled " + D.models.technical.top20.precision +\n'
     '      "% 当成稳定胜率。";',
     '      "Pure technical top-20% hit rate: " + (parts || "—") + "; median " + D.stability.medianPrecision +\n'
     '      "%, with " + D.stability.yearsAboveBase + "/" + D.stability.years +\n'
     '      " years above the base rate. Yearly swings are too large to treat the pooled " + D.models.technical.top20.precision +\n'
     '      "% as a stable hit rate.";'),

    ('      "aria-label": "SPY 收盘价与 200 日均线，阴影为回撤超过 10% 的区间"',
     '      "aria-label": "SPY close and its 200-day moving average, with drawdowns beyond 10% shaded"'),

    ('    // 回撤 >=10% 阴影', '    // drawdown >=10% shading'),
    ('    // y 网格', '    // y grid'),
    ('    // x 年标签', '    // x year labels'),
    ('    // 末端标签', '    // end labels'),
    ('    // 十字线', '    // crosshair'),

    ('      "aria-label": "悬停查看 SPY 与 200 日均线"',
     '      "aria-label": "Hover to inspect SPY and its 200-day moving average"'),

    ('        { label: "回撤", value: p.dd == null ? "—" : p.dd + "%" }',
     '        { label: "Drawdown", value: p.dd == null ? "—" : p.dd + "%" }'),

    ('    appendTable(host, ["周", "SPY", "200DMA", "回撤"], data.map(function (p) {',
     '    appendTable(host, ["Week", "SPY", "200DMA", "Drawdown"], data.map(function (p) {'),

    ('    var labels = { auto: "主题：自动", light: "主题：浅色", dark: "主题：深色" };',
     '    var labels = { auto: "Theme: Auto", light: "Theme: Light", dark: "Theme: Dark" };'),
]

# --------------------------------------------------------- backtest-data.js
BTDATA = [
    ('      "HY OAS 免费历史仅 3 年，信用信号使用 HYG/LQD 相对 200 日均线 + 动量的代理。",\n'
     '      "宽度信号使用 RSP/SPY（等权/市值权）相对 200 日均线 + 动量的代理。",\n'
     '      "杠杆/流动性（NFCI）、情绪、结构性风险没有稳定免费历史，未纳入回测；主站模型仍保留这三类信号。",\n'
     '      "月度数据滞后一个月，避免前视偏差。"',
     '      "Free HY OAS history covers only 3 years, so the credit signal uses HYG/LQD versus its 200-day MA plus momentum as a proxy.",\n'
     '      "The breadth signal uses RSP/SPY (equal vs cap weight) versus its 200-day MA plus momentum as a proxy.",\n'
     '      "Leverage/liquidity (NFCI), sentiment, and structural risk have no stable free history and are excluded from the backtest; the main-site model still keeps those three signal families.",\n'
     '      "Monthly data lags one month to avoid look-ahead bias."'),
    ('"label": "部分预警"', '"label": "Partial warning"'),
    ('"label": "同步确认"', '"label": "Coincident confirmation"'),
    ('"label": "小幅回撤"', '"label": "Minor drawdown"'),
    ('"label": "未捕捉"', '"label": "Missed"'),
    ('"label": "提前预警"', '"label": "Early warning"'),
]

# --------------------------------------------------------- technical-data.js
TECHDATA = [
    ('      "目标：未来 126 个交易日内，SPY 从当前价格起算的最大回撤 <= -10%。",\n'
     '      "主分析只保留距高点 5% 以内的样本，模拟“在高位判断下一次大跌”的场景。",\n'
     '      "技术指标基于日线/周线 OHLCV；周线指标按周五收盘对齐到下一交易日。",\n'
     '      "模型使用 purged walk-forward：每年用此前数据训练，训练集末尾剔除 190 天，避免标签重叠。",\n'
     '      "每个测试年按测试年内的预测分位取前 20% / 10% 作为预警，用于回顾性评估；实盘阈值需用训练集确定。",\n'
     '      "样本小、标签重叠，胜率与 AUC 都是探索性结果，不是实盘承诺。"',
     '      "Target: max drawdown of SPY from the current price <= -10% within the next 126 trading days.",\n'
     '      "The main analysis keeps only samples within 5% of the high, simulating the “judge the next crash from a high” scenario.",\n'
     '      "Technical indicators are built from daily/weekly OHLCV; weekly indicators are aligned from Friday closes to the next trading day.",\n'
     '      "The model uses purged walk-forward: each year trains on prior data with the last 190 days of the training set dropped to avoid label overlap.",\n'
     '      "Within each test year, the top 20% / 10% by predicted percentile are flagged as warnings for retrospective evaluation; live thresholds must be set from the training set.",\n'
     '      "Samples are small and labels overlap, so hit rates and AUC are exploratory results, not live promises."'),

    # indicator names
    ('"name": "ATR 分位 > 80%（高波动）"', '"name": "ATR percentile > 80% (high volatility)"'),
    ('"name": "RSI(14) < 40（走弱）"', '"name": "RSI(14) < 40 (weakening)"'),
    ('"name": "周布林带宽 < 20% 分位"', '"name": "Weekly Bollinger width < 20th percentile"'),
    ('"name": "收盘 < 50 日均线"', '"name": "Close < 50-day MA"'),
    ('"name": "日线向下跳空"', '"name": "Gap down (daily)"'),
    ('"name": "日线看跌吞没"', '"name": "Bearish engulfing (daily)"'),
    ('"name": "成交量 > 1.5×20 日均量"', '"name": "Volume > 1.5x 20-day average"'),
    ('"name": "周 MACD 线 < 信号线"', '"name": "Weekly MACD line < signal line"'),
    ('"name": "MACD 线 < 信号线"', '"name": "MACD line < signal line"'),
    ('"name": "布林带宽 < 20% 分位（挤压）"', '"name": "Bollinger width < 20th percentile (squeeze)"'),
    ('"name": "日线外包下跌"', '"name": "Outside-down day (daily)"'),
    ('"name": "RSI(14) > 70（超买）"', '"name": "RSI(14) > 70 (overbought)"'),
    ('"name": "收盘 > 布林上轨"', '"name": "Close > upper Bollinger band"'),
    ('"name": "周 RSI(14) > 70（超买）"', '"name": "Weekly RSI(14) > 70 (overbought)"'),
    ('"name": "50 日均线 < 200 日均线（死叉）"', '"name": "50-day MA < 200-day MA (death cross)"'),
    ('"name": "收盘 < 200 日均线"', '"name": "Close < 200-day MA"'),
    ('"name": "周收盘 < 30 周均线"', '"name": "Weekly close < 30-week MA"'),

    # kinds
    ('"kind": "波动率"', '"kind": "Volatility"'),
    ('"kind": "动量"', '"kind": "Momentum"'),
    ('"kind": "周线"', '"kind": "Weekly"'),
    ('"kind": "趋势"', '"kind": "Trend"'),
    ('"kind": "K 线形态"', '"kind": "Candlestick"'),
    ('"kind": "成交量"', '"kind": "Volume"'),
    ('"kind": "超买"', '"kind": "Overbought"'),

    # skip reasons
    ('"reason": "训练样本不足 300 天"', '"reason": "Training sample under 300 days"'),
    ('"reason": "距高点 5% 以内的样本不足 40 天"', '"reason": "Fewer than 40 days within 5% of the high"'),
]

JOBS = [
    ("backtest.js", BT),
    ("technical.js", TECH),
    ("backtest-data.js", BTDATA),
    ("technical-data.js", TECHDATA),
]

CJK = re.compile(r"[\u4e00-\u9fff]")
failed = False

for name, pairs in JOBS:
    src = SRC / name
    if not src.exists():
        print("[SKIP] missing %s" % src)
        continue
    text = src.read_text(encoding="utf-8")
    try:
        out = apply(text, pairs, name)
    except SystemExit as exc:
        print(exc)
        failed = True
        continue
    dst = DST / name
    dst.write_text(out, encoding="utf-8", newline="\n")
    leftover = [(i + 1, ln.strip()) for i, ln in enumerate(out.splitlines()) if CJK.search(ln)]
    print("[OK] %-20s -> %s  (%d lines, %d with CJK left)"
          % (name, dst.name, len(out.splitlines()), len(leftover)))
    for ln, content in leftover[:15]:
        print("      %d: %s" % (ln, content[:110]))

sys.exit(1 if failed else 0)
