# 美股暴跌预警 · US Crash Radar

复用 `F:\Claudeproject\GoldWebsite` 的设计系统（数据看板、卡片、KPI、图表、主题切换、零依赖）搭建的独立静态站点。

## 运行

直接用浏览器打开 `index.html`，无需构建、无需安装依赖。

```text
F:\Claudeproject\USStockcrashedOfficial\index.html
```

## 自动更新

`.github/workflows/daily-update.yml` 每天北京时间 08:00（UTC 00:00）自动运行：

1. 重新抓取行情与宏观数据（`REFRESH_DATA=1`；单个数据源失败时回退到 `data/raw/` 缓存，不会整体失败）；
2. 依次运行 `build_backtest.py` → `build_technical.py` → `build_site.py` → `build_en.py`；
3. 有变更时提交并推送，然后请求 GitHub Pages 重新构建。

- 非交易日数据不变，任务正常结束，不会产生空提交。
- 手动触发：仓库 Actions → **Daily data update** → **Run workflow**。
- GitHub 的 cron 在整点可能有几分钟到半小时的排队延迟，属于平台行为。
- 若行情数据超过 7 天未更新，任务会给出 warning 提示上游数据源异常。

## 目录

```text
USStockcrashedOfficial/
├─ index.html              # 三层趋势雷达首页
├─ backtest.html           # 2017–2026 历史回测页
├─ technical.html          # 技术分析叠加页
├─ en/                     # 英文版（面向海外流量与赞助）
│  ├─ index.html
│  ├─ backtest.html
│  ├─ technical.html
│  └─ assets/              # 英文版 JS 与数据（由 scripts/build_en.py 生成）
├─ assets/
│  ├─ site.css             # 设计令牌与组件样式（复用 GoldWebsite 调色板）
│  ├─ app.js               # 主站数据、评分渲染、图表、主题切换
│  ├─ backtest.js          # 回测页图表与表格
│  ├─ backtest-data.js     # 回测结果（由脚本生成）
│  ├─ technical.js         # 技术分析页图表与表格
│  ├─ technical-data.js    # 技术分析结果（由脚本生成）
│  └─ favicon.svg
├─ data/
│  ├─ snapshot.json        # 旧版九信号示例快照（新首页未使用）
│  ├─ backtest.json        # 回测结果（供其他工具读取）
│  ├─ backtest_score_daily.csv  # 日频评分（技术分析输入）
│  ├─ technical.json       # 技术分析结果
│  └─ raw/                 # 回测原始数据缓存（自动生成）
├─ scripts/
│  ├─ build_backtest.py    # 回测数据构建脚本
│  ├─ build_technical.py   # 技术分析构建脚本
│  ├─ build_site.py        # 重算首页 PAGE_DATA（7 条件 + 辅助分）
│  └─ build_en.py          # 生成英文版 assets（文案替换，不重新计算数据）
├─ .github/workflows/
│  └─ daily-update.yml     # 每天北京时间 08:00 自动更新并发布
└─ README.md
```

## 英文版（en/）

`en/` 是同一套数据的英文界面，面向海外流量：默认入口 `https://wangxian111.github.io/usstockcrash/en/`。

- **页面一一对应**：`en/index.html`、`en/backtest.html`、`en/technical.html`。
- **共用资源**：CSS、favicon 走 `../assets/`；JS 与数据在 `en/assets/`（英文文案）。
- **语言切换**：中文页右上角 `EN` 按钮，英文页右上角 `中文`。
- **hreflang**：六个页面都带 `en` / `zh-CN` / `x-default` 互指标签，便于搜索引擎分流。
- **数据不重复计算**：`en/assets/backtest-data.js`、`technical-data.js` 由 `scripts/build_en.py` 从中文版做纯文案替换生成。

更新数据后的正确顺序：

```powershell
python scripts\build_backtest.py
python scripts\build_technical.py
python scripts\build_site.py      # 重算中英文首页 PAGE_DATA 与结论段落
python scripts\build_en.py        # 重新生成 en/assets/*.js
```

`build_en.py` 会校验每条替换是否命中；若中文源改了措辞导致未命中，脚本会报 `[MISS]` 并退出，不会静默漏译。

### 打赏按钮（暂未启用）

GitHub Sponsors 与 Ko-fi 账户尚未开通，因此英文页目前**没有**打赏按钮，避免死链。
样式已在三个英文页的 `<style>` 中预留（`.sponsor-btn`）。账户开通后，在英文页 masthead 的 `Theme: Auto` 按钮前插入：

```html
<a class="ghost-btn sponsor-btn" href="https://ko-fi.com/你的handle" target="_blank" rel="noopener" style="text-decoration:none">♥ Support</a>
<a class="ghost-btn" href="https://github.com/sponsors/Wangxian111" target="_blank" rel="noopener" style="text-decoration:none">★ Sponsor</a>
```

页脚可再补一句引导（英文页 footer 已有位置，可加在 `Page navigation` 之前）：

```html
<span style="display:block;margin-top:8px">
  If this radar helps you, consider
  <a href="https://ko-fi.com/你的handle" target="_blank" rel="noopener" style="color:#ea4aaa">buying me a coffee</a>.
</span>
```


## 页面内容

首页现在以**三层趋势跟踪为主**，原九信号基本面风险分降为辅助背景。

- **三层总览**：当前层级（观察/警告/确认）、5/7 条件、放量确认状态、三层阶梯。
- **七条件跟踪**：收盘<200DMA、收盘<50DMA、RSI 后 20%、周收盘<30WMA、ATR 前 20%、VIX 前 20%、MACD 柱后 20%；逐项显示当前读数、分位、阈值、触发状态。
- **层级动作**：观察层（≥4/7）、警告层（≥5/7）、确认层（≥5/7+放量）分别对应的风险动作。
- **历史验证**：A 低频保守 / B 均衡（当前）/ C 高频灵敏 / B+放量确认 的胜率、召回、触发回撤。
- **辅助风险分**：6 个可回测信号（信用、宽度、估值、波动率、利率、宏观）的分数、权重、贡献；3 个未建模信号单列。首页快照由 `scripts/build_site.py` 按最新数据重算。
- **方法与风险预算**：主层公式、历史边界、仓位与现金约束。
- **研究页面**：`backtest.html`（危机明细、假阳性）、`technical.html`（单指标、三种组合、暴跌频率、技术分析）。

## 历史回测（2017–2026）

`backtest.html` 用 6 个可计算信号回测主站评分在最近几次 ≥10% 回撤前的表现。

### 结果摘要

- 5 次 ≥10% 回撤：1 次提前预警（2025）、2 次部分预警（2018-01、2020-02）、1 次同步确认（2018Q4）、1 次未捕捉（2022）。
- 2020 年只有约 10 天的短暂提示；2022 年完全漏报。
- 注意：这里的“提前/部分预警”按滚动 3 年分位判定；原始加权分在 2025 年 T-30 为 36.9、2020 年 T-10 为 35.7，均低于主站 45 的“关注”线。
- 按“分位 ≥80 持续 10 个交易日”定义：9 次事前预警，3 次命中 ≥10% 回撤，6 次误报（误报率 67%）；若把 8% 也算大跌，5 次误报（56%）。
- 2022 漏报原因：峰值前只有估值信号亮（99），信用 8、波动率 14、利率 0、宏观 0；模型偏信用/流动性，缺少通胀与美联储政策预期。
- 唯一的“原始分 ≥60”区间发生在 2020 年 3–4 月，即 COVID 暴跌之后，不是事前误报。
- 结论：它更像“相对脆弱度”温度计，而不是时点预测器。

### 回测口径

- 窗口：2017-05 至 2026-11（行情数据从 2016-11 开始）。
- 信号：信用（HYG/LQD 代理）25、宽度（RSP/SPY 代理）20、估值（CAPE）15、波动率（VIX/VIX3M）15、宏观（失业率 Sahm 思路）15、利率（10Y TIPS + 2s10s）10。
- 杠杆/流动性（NFCI）、情绪、结构性风险没有稳定免费历史，未纳入回测；主站模型仍保留。
- 分位：滚动 3 年（756 个交易日）分位，避免使用未来数据。
- 判定：T-30 分位 ≥80 或 T-10 ≥80 且 T-30 ≥65 为提前预警；T-30 ≥65 或 T-10 ≥75 为部分预警；峰值后 10 日内分位 ≥80 为同步确认；其余为未捕捉。
- 8–10% 回撤单独列出，不参与主统计。

### 重新生成回测

```bash
pip install -r scripts/requirements.txt
python scripts/build_backtest.py
```

脚本会拉取/读取 `data/raw/` 缓存，生成 `data/backtest.json` 和 `assets/backtest-data.js`。

数据源：Nasdaq API（SPY/RSP/HYG/LQD）、CBOE（VIX/VIX3M）、美国财政部（名义/实际收益率）、DBnomics/OECD（美国月度失业率）、multpl.com（Shiller CAPE）。

**注意：**回测是历史模拟，不是实盘策略；样本只有 5 次 ≥10% 回撤，统计意义有限；代理信号与真实 HY OAS、真实市场宽度、NFCI 有差异。

## 技术分析叠加（2017–2026）

`technical.html` 用日线/周线 OHLCV 检验技术指标对“未来 6 个月 ≥10% 回撤”的预测力。

### 结果摘要

- 近高样本（距高点 5% 以内）基准胜率 22.8%。
- 纯技术模型 Top 20% 胜率 30.9%（95% CI 24.1–38.7%），Top 10% 42.9%，但 AUC 0.522，仅略高于随机。
- 年度极不稳定：2021 0%、2024 40.8%、2025 65.9%、2026 0%（无正样本）；中位数 20.4%，4 个可评估年份里 2 年高于基准。
- 叠加基本面后 Top 20% 胜率反而降到 27.0%，AUC 0.482；基本面风险分在近高点几乎不亮，且对“从当前价再跌”是反向的。
- 单指标：ATR >80% 分位胜率 37.1%（召回仅 8.2%）；周布林带宽 <20% 分位 29.9%（召回 21.1%）；超买 RSI(14)>70 胜率 16.7%，低于基准。
- 结论：技术分析只能做弱过滤/确认，不是可靠的暴跌择时信号。

### 三种组合（2 周 8% 暴跌）

- **A 低频保守**：7 条件 ≥6/7；约 17 个预警日/年；日胜率 21.5%；事件召回 7/9；中位触发在峰值后 19 日、回撤 −6.7%。
- **B 均衡（推荐）**：7 条件 ≥5/7；约 29 个预警日/年；日胜率 19.8%；事件召回 9/9；中位触发在峰值后 17 日、回撤 −6.0%。
- **C 高频灵敏**：11 条件 ≥5/11；约 52 个预警日/年；日胜率 13.0%；事件召回 9/9；中位触发在峰值后 17 日、回撤 −4.7%。
- **关键限制**：0/9 在峰值前触发；三套都是趋势确认/防守减仓工具，不是顶部预测器；结果为样本内筛查，未做独立特征选择外样本，胜率应打折看待。

### 运行

```bash
python scripts/build_backtest.py      # 生成 data/backtest_score_daily.csv
python scripts/build_technical.py     # 生成 data/technical.json + assets/technical-data.js
```

### 口径与局限

- 目标：未来 126 个交易日内，SPY 从当前收盘价起算的最大回撤 ≤ −10%。
- 主分析只保留距历史高点 5% 以内的样本，模拟“在高位判断下一次大跌”。
- 模型：L2 逻辑回归，class_weight=balanced；purged walk-forward，每年训练集末尾剔除 190 天，避免标签重叠。
- 预警：每个测试年按预测分位取前 20% / 10%，用于回顾性评估；实盘阈值需用训练集确定。
- 样本小、标签高度重叠，AUC 与胜率都是探索性结果；不是交易策略。

## 更新数据

当前首页使用 `assets/app.js` 顶部的 `PAGE_DATA` 内嵌快照，保证 `file://` 直接打开也能运行（浏览器对本地 `fetch` 有 CORS 限制）。

`scripts/build_site.py` 会读取最新行情与 `data/backtest_score_daily.csv`，自动重写：

- `PAGE_DATA.layer`：7 个条件的当前读数、分位、`active`、层级、放量与摘要；
- `PAGE_DATA.auxiliary`：6 个信号的读数、权重、贡献与说明；
- `asOf` 以及中英文首页「辅助分的定位」结论段落。

因此日常更新不需要手工改数，运行上面的四步脚本或等定时任务即可。

### 主层口径

7 个条件：

- 趋势：收盘 <200 日均线、收盘 <50 日均线、周收盘 <30 周均线。
- 动量：RSI(14) 后 20%、MACD 柱后 20%。
- 波动率：ATR 前 20%、VIX 前 20%。

分位 = 扩展窗口（至少 252 个交易日）百分位；低分位条件取后 20%，高分位条件取前 20%。

| 层级 | 条件 |
|---|---|
| 观察层 | 7 个条件中 ≥4 个触发 |
| 警告层 | ≥5 个触发 |
| 确认层 | ≥5 个触发 + 成交量 >1.5×20 日均量 |

### 辅助分口径

```text
辅助分 = Σ（信号读数 × 权重）÷ 100
权重：信用 25 · 宽度 20 · 估值 15 · 波动率 15 · 宏观 15 · 利率 10
```

区间：0–24 平静，25–44 观察，45–64 关注，65–84 警戒，85–100 危机。  
辅助分的当前读数与主要贡献由 `scripts/build_site.py` 自动写入首页；杠杆/流动性、情绪、结构性风险未建模。

### 区间

| 分数 | 状态 |
|---|---|
| 0–24 | 平静 |
| 25–44 | 观察 |
| 45–64 | 关注 |
| 65–84 | 警戒 |
| 85–100 | 危机 |

## 设计系统复用说明

- 调色板与设计令牌来自 GoldWebsite 的 `goldsite` 页面（dataviz 调色板实例）。
- 组件模式复用：masthead、card、KPI stat、driver bar、charts-grid、data table、tooltip、theme toggle。
- 图表为手写 SVG，无第三方依赖；每张图都带悬停提示和“查看数据表”折叠表。
- 主题支持自动 / 浅色 / 深色，选择会写入 `localStorage`。

## 免责声明

本项目仅用于研究与教育，不构成投资建议、要约或招揽。页面中的读数为示例数据，不是实时行情；历史涨跌幅为近似值，不代表未来收益。投资涉及风险，可能损失全部本金。
