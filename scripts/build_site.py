#!/usr/bin/env python3
"""
首页快照构建
--------------------------------------------------------------------------
读取 data/raw/ 与 data/backtest_score_daily.csv 的最新数据，重算首页
PAGE_DATA（7 条件主层 + 6 信号辅助分），并就地改写：

  assets/app.js      中文首页快照
  en/assets/app.js   英文首页快照
  index.html         辅助分结论段落
  en/index.html      辅助分结论段落

口径与 README 一致：
  - 趋势/动量/周线/VIX 分位：扩展窗口（至少 252 个交易日）百分位
  - ATR 分位：滚动 252 日百分位（与 build_technical 一致）
  - 辅助分：build_backtest.py 输出的日频评分（5 日均值平滑）
"""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
sys.path.insert(0, str(ROOT / "scripts"))

from build_technical import build_indicators  # noqa: E402

MIN_HISTORY = 252


# ---------------------------------------------------------------- 数据加载

def load_raw_prices(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
                errors="coerce",
            )
    return df.dropna(subset=["date"]).sort_values("date").set_index("date")


def load_cboe(name: str) -> pd.Series:
    df = pd.read_csv(RAW / f"cboe_{name}.csv")
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
    return df.dropna(subset=["DATE"]).set_index("DATE")["CLOSE"].sort_index()


def expanding_pct(s: pd.Series) -> pd.Series:
    return s.expanding(min_periods=MIN_HISTORY).rank(pct=True)


def fmt_signed(x: float, dp: int = 2) -> str:
    return f"{x * 100:+.{dp}f}%".replace("-", "−")


def pct_int(x: float) -> int:
    return int(round(float(x) * 100))


def join_and(items: list[str], sep: str = "、", conj: str = " 与 ") -> str:
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    return sep.join(items[:-1]) + conj + items[-1]


# ---------------------------------------------------------------- 计算快照

def compute_snapshot() -> dict:
    spy = load_raw_prices(RAW / "nasdaq_SPY.csv")
    ind = build_indicators(spy)
    vix_all = load_cboe("VIX")
    vix = vix_all.reindex(spy.index).ffill()

    daily = pd.read_csv(
        ROOT / "data" / "backtest_score_daily.csv", parse_dates=["date"]
    ).set_index("date").sort_index()

    # 以行情和评分都有数据的最后一天为准
    common = spy.index.intersection(daily.dropna(subset=["score"]).index)
    asof = common[-1]
    row = ind.loc[asof]
    daily_row = daily.loc[asof]

    dist200 = float(row["dist200"])
    dist50 = float(row["dist50"])
    rsi14 = float(row["rsi14"])
    w_dist30 = float(row["w_dist30"])
    atr_rank = float(row["atr_rank"])
    macd_norm = float(row["macd_hist_norm"])
    vol_ratio = float(row["vol_ratio"])
    vix_now = float(vix.loc[asof])

    pct = {
        "dist200": float(expanding_pct(ind["dist200"]).loc[asof]),
        "dist50": float(expanding_pct(ind["dist50"]).loc[asof]),
        "rsi": float(expanding_pct(ind["rsi14"]).loc[asof]),
        "w_dist30": float(expanding_pct(ind["w_dist30"]).loc[asof]),
        "macd": float(expanding_pct(ind["macd_hist_norm"]).loc[asof]),
        "vix": float(expanding_pct(vix).loc[asof]),
        "atr": atr_rank,
    }

    conditions = [
        ("200", dist200 < 0),
        ("50", dist50 < 0),
        ("rsi", pct["rsi"] <= 0.20),
        ("week", w_dist30 < 0),
        ("atr", atr_rank > 0.80),
        ("vix", pct["vix"] > 0.80),
        ("macd", pct["macd"] <= 0.20),
    ]
    active = {k: v for k, v in conditions}
    score = sum(1 for v in active.values() if v)
    confirmed = vol_ratio > 1.5  # 放量条件本身是否触发；确认层还要求 score >= 5

    signals = ["credit", "breadth", "valuation", "volatility", "rates", "macro"]
    weights = {"credit": 25, "breadth": 20, "valuation": 15, "volatility": 15, "rates": 10, "macro": 15}
    sig_vals = {k: round(float(daily_row[k]) * 100, 1) for k in signals}
    contributions = {k: round(sig_vals[k] * weights[k] / 100, 1) for k in signals}
    aux_score = round(float(daily_row["score"]), 1)
    aux_pct = round(float(daily_row["score_pct"]), 1) if pd.notna(daily_row["score_pct"]) else None

    return {
        "asOf": asof.strftime("%Y-%m-%d"),
        "dist200": dist200,
        "dist50": dist50,
        "rsi14": rsi14,
        "w_dist30": w_dist30,
        "atr_rank": atr_rank,
        "macd_norm": macd_norm,
        "vol_ratio": round(vol_ratio, 2),
        "vix_now": vix_now,
        "pct": {k: pct_int(v) for k, v in pct.items()},
        "active": active,
        "score": score,
        "confirmed": confirmed,
        "sig": sig_vals,
        "contrib": contributions,
        "weights": weights,
        "aux_score": aux_score,
        "aux_pct": aux_pct,
    }


# ---------------------------------------------------------------- 文案

ZH_TIER = {"calm": "平静", "observe": "观察层", "warn": "警告层", "confirm": "确认层"}
EN_TIER = {"calm": "Calm", "observe": "Observation", "warn": "Warning", "confirm": "Confirmation"}
ZH_TIER_SHORT = {"calm": "平静", "observe": "观察", "warn": "警告", "confirm": "确认"}

ZH_BANDS = [  # (上限, 名称, tone)
    (25, "平静", "good"),
    (45, "观察", "mid"),
    (65, "关注", "warn"),
    (85, "警戒", "serious"),
    (101, "危机", "crit"),
]
EN_BANDS = [
    (25, "Calm", "good"),
    (45, "Watch", "mid"),
    (65, "Alert", "warn"),
    (85, "Severe", "serious"),
    (101, "Crisis", "crit"),
]


def band_for(score: float, bands):
    for cap, name, tone in bands:
        if score < cap:
            return name, tone
    return bands[-1][1], bands[-1][2]


def tier_key(s: dict) -> str:
    if s["score"] >= 5 and s["confirmed"]:
        return "confirm"
    if s["score"] >= 5:
        return "warn"
    if s["score"] == 4:
        return "observe"
    return "calm"


def divergence(s: dict, band: str) -> str:
    """返回 divergence 类型：tech_first / fundamental_first / aligned"""
    main_warn = s["score"] >= 5
    aux_low = band in ("平静", "观察", "Watch", "Calm")
    aux_high = band in ("关注", "警戒", "危机", "Alert", "Severe", "Crisis")
    if main_warn and aux_low:
        return "tech_first"
    if (not main_warn) and aux_high:
        return "fundamental_first"
    return "aligned"


def zh_conditions(s: dict) -> list[dict]:
    a = s["active"]
    p = s["pct"]
    return [
        {
            "name": "收盘 < 200 日均线", "type": "趋势",
            "reading": f"{'低于' if s['dist200'] < 0 else '高于'} 200DMA {fmt_signed(s['dist200'], 1)}",
            "percentile": p["dist200"], "threshold": "后 20% 分位", "active": a["200"],
            "note": "长期趋势已破坏" if a["200"] else "长期趋势尚未破坏",
        },
        {
            "name": "收盘 < 50 日均线", "type": "趋势",
            "reading": f"{'低于' if s['dist50'] < 0 else '高于'} 50DMA {fmt_signed(s['dist50'], 2)}",
            "percentile": p["dist50"], "threshold": "后 20% 分位", "active": a["50"],
            "note": "短期趋势走弱" if a["50"] else "短期趋势仍在",
        },
        {
            "name": "RSI(14) 后 20%", "type": "动量",
            "reading": f"RSI {s['rsi14']:.1f}",
            "percentile": p["rsi"], "threshold": "后 20% 分位", "active": a["rsi"],
            "note": "动量偏弱" if a["rsi"] else "动量中性",
        },
        {
            "name": "周收盘 < 30 周均线", "type": "周线",
            "reading": f"{'低于' if s['w_dist30'] < 0 else '高于'} 30WMA {fmt_signed(s['w_dist30'], 2)}",
            "percentile": p["w_dist30"], "threshold": "后 20% 分位", "active": a["week"],
            "note": "周线趋势走弱" if a["week"] else "周线趋势完好",
        },
        {
            "name": "ATR 前 20%", "type": "波动率",
            "reading": f"ATR {p['atr']}% 分位",
            "percentile": p["atr"], "threshold": "前 20% 分位", "active": a["atr"],
            "note": "波动率处于高位" if a["atr"] else "波动率正常",
        },
        {
            "name": "VIX 前 20%", "type": "波动率",
            "reading": f"VIX {s['vix_now']:.1f}（{p['vix']}% 分位）",
            "percentile": p["vix"], "threshold": "前 20% 分位", "active": a["vix"],
            "note": "VIX 进入高位" if a["vix"] else "VIX 尚未进入高位",
        },
        {
            "name": "MACD 柱后 20%", "type": "动量",
            "reading": f"MACD 柱 {fmt_signed(s['macd_norm'], 2)}/价格",
            "percentile": p["macd"], "threshold": "后 20% 分位", "active": a["macd"],
            "note": "动量转弱" if a["macd"] else "动量未转弱",
        },
    ]


def en_conditions(s: dict) -> list[dict]:
    a = s["active"]
    p = s["pct"]
    return [
        {
            "name": "Close < 200-day MA", "type": "Trend",
            "reading": f"{fmt_signed(s['dist200'], 1)} {'below' if s['dist200'] < 0 else 'above'} 200DMA",
            "percentile": p["dist200"], "threshold": "Bottom 20%", "active": a["200"],
            "note": "Long-term trend broken" if a["200"] else "Long-term trend not yet broken",
        },
        {
            "name": "Close < 50-day MA", "type": "Trend",
            "reading": f"{fmt_signed(s['dist50'], 2)} {'below' if s['dist50'] < 0 else 'above'} 50DMA",
            "percentile": p["dist50"], "threshold": "Bottom 20%", "active": a["50"],
            "note": "Short-term trend weakening" if a["50"] else "Short-term trend intact",
        },
        {
            "name": "RSI(14) bottom 20%", "type": "Momentum",
            "reading": f"RSI {s['rsi14']:.1f}",
            "percentile": p["rsi"], "threshold": "Bottom 20%", "active": a["rsi"],
            "note": "Momentum on the weak side" if a["rsi"] else "Momentum neutral",
        },
        {
            "name": "Weekly close < 30-week MA", "type": "Weekly",
            "reading": f"{fmt_signed(s['w_dist30'], 2)} {'below' if s['w_dist30'] < 0 else 'above'} 30WMA",
            "percentile": p["w_dist30"], "threshold": "Bottom 20%", "active": a["week"],
            "note": "Weekly trend weakening" if a["week"] else "Weekly trend intact",
        },
        {
            "name": "ATR top 20%", "type": "Volatility",
            "reading": f"ATR {p['atr']}th percentile",
            "percentile": p["atr"], "threshold": "Top 20%", "active": a["atr"],
            "note": "Volatility elevated" if a["atr"] else "Volatility normal",
        },
        {
            "name": "VIX top 20%", "type": "Volatility",
            "reading": f"VIX {s['vix_now']:.1f} ({p['vix']}th pct)",
            "percentile": p["vix"], "threshold": "Top 20%", "active": a["vix"],
            "note": "VIX has reached the high zone" if a["vix"] else "VIX has not reached the high zone",
        },
        {
            "name": "MACD histogram bottom 20%", "type": "Momentum",
            "reading": f"MACD hist {fmt_signed(s['macd_norm'], 2)} of price",
            "percentile": p["macd"], "threshold": "Bottom 20%", "active": a["macd"],
            "note": "Momentum turning weaker" if a["macd"] else "Momentum not weakening",
        },
    ]


def zh_signal_note(name: str, v: float) -> str:
    if v < 25:
        return {
            "credit": "信用压力低", "breadth": "等权/市值权未恶化", "valuation": "估值相对正常",
            "volatility": "波动率低位", "rates": "实际利率/曲线温和", "macro": "失业率未触发",
        }[name]
    if v < 55:
        return {
            "credit": "信用压力中等", "breadth": "宽度一般", "valuation": "CAPE 偏高",
            "volatility": "VIX/期限结构中位", "rates": "利率压力中等", "macro": "失业率温和上升",
        }[name]
    return {
        "credit": "信用压力偏高", "breadth": "宽度走弱", "valuation": "CAPE 极高，主要贡献",
        "volatility": "波动率偏高", "rates": "利率压力偏高", "macro": "失业率明显上升",
    }[name]


def en_signal_note(name: str, v: float) -> str:
    if v < 25:
        return {
            "credit": "Credit stress low", "breadth": "Equal/cap weight not deteriorating",
            "valuation": "Valuation relatively normal", "volatility": "Volatility low",
            "rates": "Real rates/curve benign", "macro": "Unemployment not triggered",
        }[name]
    if v < 55:
        return {
            "credit": "Credit stress moderate", "breadth": "Breadth mixed",
            "valuation": "CAPE elevated", "volatility": "VIX/term structure mid-range",
            "rates": "Rate pressure moderate", "macro": "Unemployment rising moderately",
        }[name]
    return {
        "credit": "Credit stress elevated", "breadth": "Breadth deteriorating",
        "valuation": "CAPE extremely high — main driver", "volatility": "Volatility elevated",
        "rates": "Rate pressure elevated", "macro": "Unemployment rising sharply",
    }[name]


ZH_SIGNAL_NAMES = {
    "credit": "信用", "breadth": "宽度", "valuation": "估值",
    "volatility": "波动率", "rates": "利率", "macro": "宏观",
}
EN_SIGNAL_NAMES = {
    "credit": "Credit", "breadth": "Breadth", "valuation": "Valuation",
    "volatility": "Volatility", "rates": "Rates", "macro": "Macro",
}


def build_page_data(s: dict, lang: str) -> dict:
    if lang == "zh":
        tk = tier_key(s)
        tier = ZH_TIER[tk]
        tone = {"calm": "good", "observe": "mid", "warn": "warn", "confirm": "crit"}[tk]
        band, band_tone = band_for(s["aux_score"], ZH_BANDS)
        conditions = zh_conditions(s)
        tags = []
        if s["active"]["200"]:
            tags.append({"text": "200DMA 下方", "tone": "warn"})
        if s["active"]["50"]:
            tags.append({"text": "50DMA 下方", "tone": "warn"})
        if s["active"]["week"]:
            tags.append({"text": "周线 30WMA 下方", "tone": "warn"})
        if s["active"]["atr"]:
            tags.append({"text": f"ATR {s['pct']['atr']}% 分位", "tone": "warn"})
        if s["active"]["macd"]:
            tags.append({"text": "MACD 走弱", "tone": "warn"})
        tags.append({"text": f"RSI {s['rsi14']:.1f}", "tone": "mid"})
        tags.append({"text": "VIX 高位" if s["active"]["vix"] else "VIX 未确认",
                     "tone": "warn" if s["active"]["vix"] else ""})

        missing = []
        short = {"200": "200DMA", "50": "50DMA", "rsi": "RSI",
                 "week": "30WMA", "atr": "ATR", "vix": "VIX", "macd": "MACD"}
        for k in ["200", "50", "rsi", "week", "atr", "vix", "macd"]:
            if not s["active"][k]:
                missing.append(short[k])
        if missing:
            summary = f"{s['score']}/7 条件触发；{join_and(missing)} 未触发；"
        else:
            summary = "7/7 条件全部触发；"
        confirm_tier = s["score"] >= 5 and s["confirmed"]
        summary += (f"放量 {s['vol_ratio']:.2f}× "
                    f"{'高于' if s['confirmed'] else '低于'} 1.5×，"
                    f"确认层{'成立' if confirm_tier else '未成立'}。")

        top = max(s["sig"], key=lambda k: s["contrib"][k])
        low = [ZH_SIGNAL_NAMES[k] for k in s["sig"] if s["sig"][k] < 25 and k != top]
        aux_note = (f"辅助分 {s['aux_score']}（{band}），主要贡献来自"
                    f"{ZH_SIGNAL_NAMES[top]} {s['sig'][top]} 分位"
                    f"（{s['contrib'][top]}/{s['weights'][top]}）")
        if low:
            aux_note += f"，{'/'.join(low)}都未亮"
        div = divergence(s, band)
        aux_note += f"。与主层 {s['score']}/7 {ZH_TIER_SHORT[tk]}"
        if div == "tech_first":
            aux_note += "出现分歧：技术层先恶化，基本面层尚未确认。"
        elif div == "fundamental_first":
            aux_note += "出现分歧：基本面风险高于技术层。"
        else:
            aux_note += "方向一致。"

        signal_rows = [
            {"name": ZH_SIGNAL_NAMES[k], "value": s["sig"][k], "weight": s["weights"][k],
             "contribution": s["contrib"][k], "note": zh_signal_note(k, s["sig"][k])}
            for k in ["credit", "breadth", "valuation", "volatility", "rates", "macro"]
        ]
        signal_rows += [
            {"name": "杠杆/流动性", "value": None, "weight": None, "contribution": None,
             "note": "未建模（NFCI 免费历史不足）"},
            {"name": "情绪/资金", "value": None, "weight": None, "contribution": None,
             "note": "未建模（无可靠免费历史）"},
            {"name": "结构性风险", "value": None, "weight": None, "contribution": None,
             "note": "未建模（难以量化）"},
        ]
        profiles = [
            {"name": "A 低频保守", "rule": "7 条件 ≥6/7", "alerts": "17 天/年",
             "win": "21.5%", "recall": "7/9", "drawdown": "−6.7%", "current": False},
            {"name": "B 均衡（当前）", "rule": "7 条件 ≥5/7", "alerts": "29 天/年",
             "win": "19.8%", "recall": "9/9", "drawdown": "−6.0%", "current": True},
            {"name": "C 高频灵敏", "rule": "11 条件 ≥5/11", "alerts": "52 天/年",
             "win": "13.0%", "recall": "9/9", "drawdown": "−4.7%", "current": False},
            {"name": "B + 放量确认", "rule": "≥5/7 + 量 >1.5×", "alerts": "4 天/年",
             "win": "45.0%", "recall": "8/9", "drawdown": "−8.2%", "current": False},
        ]
    else:
        tk = tier_key(s)
        tier = EN_TIER[tk]
        tone = {"calm": "good", "observe": "mid", "warn": "warn", "confirm": "crit"}[tk]
        band, band_tone = band_for(s["aux_score"], EN_BANDS)
        conditions = en_conditions(s)
        tags = []
        if s["active"]["200"]:
            tags.append({"text": "Below 200DMA", "tone": "warn"})
        if s["active"]["50"]:
            tags.append({"text": "Below 50DMA", "tone": "warn"})
        if s["active"]["week"]:
            tags.append({"text": "Below 30WMA (weekly)", "tone": "warn"})
        if s["active"]["atr"]:
            tags.append({"text": f"ATR {s['pct']['atr']}th pct", "tone": "warn"})
        if s["active"]["macd"]:
            tags.append({"text": "MACD weakening", "tone": "warn"})
        tags.append({"text": f"RSI {s['rsi14']:.1f}", "tone": "mid"})
        tags.append({"text": "VIX elevated" if s["active"]["vix"] else "VIX unconfirmed",
                     "tone": "warn" if s["active"]["vix"] else ""})

        missing = []
        short = {"200": "200DMA", "50": "50DMA", "rsi": "RSI",
                 "week": "30WMA", "atr": "ATR", "vix": "VIX", "macd": "MACD"}
        for k in ["200", "50", "rsi", "week", "atr", "vix", "macd"]:
            if not s["active"][k]:
                missing.append(short[k])
        if missing:
            summary = f"{s['score']}/7 conditions triggered; {join_and(missing, ', ', ' and ')} not triggered; "
        else:
            summary = "All 7 conditions triggered; "
        confirm_tier = s["score"] >= 5 and s["confirmed"]
        summary += (f"volume at {s['vol_ratio']:.2f}× is "
                    f"{'above' if s['confirmed'] else 'below'} 1.5×, so the confirmation tier is "
                    f"{'established' if confirm_tier else 'not established'}.")

        top = max(s["sig"], key=lambda k: s["contrib"][k])
        low = [EN_SIGNAL_NAMES[k].lower() for k in s["sig"] if s["sig"][k] < 25 and k != top]
        aux_note = (f"Auxiliary score {s['aux_score']} ({band}); the main contribution is "
                    f"{EN_SIGNAL_NAMES[top].lower()} at the {s['sig'][top]}th percentile "
                    f"({s['contrib'][top]}/{s['weights'][top]})")
        if low:
            aux_note += f", while {'/'.join(low)} are all dark"
        div = divergence(s, band)
        aux_note += f". It {'diverges from' if div != 'aligned' else 'aligns with'} the main layer's {s['score']}/7 {tier}"
        if div == "tech_first":
            aux_note += ": the technical layer deteriorated first and the fundamental layer has not confirmed."
        elif div == "fundamental_first":
            aux_note += ": fundamental risk is running ahead of the technical layer."
        else:
            aux_note += "."

        signal_rows = [
            {"name": EN_SIGNAL_NAMES[k], "value": s["sig"][k], "weight": s["weights"][k],
             "contribution": s["contrib"][k], "note": en_signal_note(k, s["sig"][k])}
            for k in ["credit", "breadth", "valuation", "volatility", "rates", "macro"]
        ]
        signal_rows += [
            {"name": "Leverage / liquidity", "value": None, "weight": None, "contribution": None,
             "note": "Not modeled (insufficient free NFCI history)"},
            {"name": "Sentiment / flows", "value": None, "weight": None, "contribution": None,
             "note": "Not modeled (no reliable free history)"},
            {"name": "Structural risk", "value": None, "weight": None, "contribution": None,
             "note": "Not modeled (hard to quantify)"},
        ]
        profiles = [
            {"name": "A Low-frequency, conservative", "rule": "≥6/7 conditions", "alerts": "17 d/yr",
             "win": "21.5%", "recall": "7/9", "drawdown": "−6.7%", "current": False},
            {"name": "B Balanced (current)", "rule": "≥5/7 conditions", "alerts": "29 d/yr",
             "win": "19.8%", "recall": "9/9", "drawdown": "−6.0%", "current": True},
            {"name": "C High-frequency, sensitive", "rule": "≥5/11 conditions", "alerts": "52 d/yr",
             "win": "13.0%", "recall": "9/9", "drawdown": "−4.7%", "current": False},
            {"name": "B + volume confirmation", "rule": "≥5/7 + vol >1.5×", "alerts": "4 d/yr",
             "win": "45.0%", "recall": "8/9", "drawdown": "−8.2%", "current": False},
        ]

    auxiliary = {
        "score": s["aux_score"],
        "band": band,
        "tone": band_tone,
        "pct": s["aux_pct"],
        "note": aux_note,
        "signals": signal_rows,
    }

    return {
        "asOf": s["asOf"],
        "layer": {
            "score": s["score"],
            "total": 7,
            "tier": tier,
            "tone": tone,
            "confirmed": s["confirmed"],
            "volumeRatio": s["vol_ratio"],
            "volumeThreshold": 1.5,
            "summary": summary,
            "tags": tags,
            "conditions": conditions,
        },
        "auxiliary": auxiliary,
        "profiles": profiles,
    }


# ---------------------------------------------------------------- 写文件

PAGE_RE = re.compile(r"const PAGE_DATA = \{.*?\n\};", re.S)


def _js_scalar(v):
    if v is None:
        return "null"
    if v is True:
        return "true"
    if v is False:
        return "false"
    if isinstance(v, str):
        return json.dumps(v, ensure_ascii=False)
    return json.dumps(v, ensure_ascii=False)


def _is_flat(d) -> bool:
    return isinstance(d, dict) and all(not isinstance(v, (dict, list)) for v in d.values())


def _inline(d) -> str:
    return "{ " + ", ".join(f"{k}: {_js_scalar(v)}" for k, v in d.items()) + " }"


def js_literal(obj, level: int = 0) -> str:
    """输出与现有 app.js 风格一致的 JS 字面量：扁平对象单行，其余逐行缩进。"""
    pad = "  " * level
    if isinstance(obj, dict):
        if _is_flat(obj):
            return _inline(obj)
        lines = []
        for k, v in obj.items():
            lines.append(f"{pad}  {k}: {js_literal(v, level + 1)}")
        body = "{\n" + ",\n".join(lines) + "\n" + pad + "}"
        if level == 0:
            for key in ("layer", "auxiliary", "profiles"):
                body = body.replace(f"\n  {key}:", f"\n\n  {key}:")
        return body
    if isinstance(obj, list):
        if not obj:
            return "[]"
        items = [f"{pad}  {js_literal(x, level + 1)}" for x in obj]
        return "[\n" + ",\n".join(items) + "\n" + pad + "]"
    return _js_scalar(obj)


def patch_app_js(path: Path, data: dict) -> None:
    text = path.read_text(encoding="utf-8")
    block = "const PAGE_DATA = " + js_literal(data) + ";"
    text, n = PAGE_RE.subn(lambda _m: block, text)
    if n != 1:
        raise SystemExit(f"[FAIL] {path}: PAGE_DATA 块匹配到 {n} 处（期望 1）")
    text = re.sub(r"数据为 \d{4}-\d{2}-\d{2} 快照", f"数据为 {data['asOf']} 快照", text)
    text = re.sub(r"Data is a \d{4}-\d{2}-\d{2} snapshot", f"Data is a {data['asOf']} snapshot", text)
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {path.relative_to(ROOT)}  asOf={data['asOf']}  "
          f"layer={data['layer']['score']}/7 {data['layer']['tier']}  "
          f"aux={data['auxiliary']['score']}({data['auxiliary']['band']})")


def patch_html(path: Path, s: dict, lang: str) -> None:
    text = path.read_text(encoding="utf-8")
    tk = tier_key(s)
    band, _ = band_for(s["aux_score"], ZH_BANDS if lang == "zh" else EN_BANDS)
    div = divergence(s, band)
    if lang == "zh":
        if div == "aligned":
            sent = "方向一致"
        elif div == "tech_first":
            sent = "出现分歧，说明技术层先恶化、基本面层尚未确认"
        else:
            sent = "出现分歧，说明基本面风险高于技术层"
        li = (f"<li><b>辅助分的定位：</b>估值/信用/宏观是慢变量；当前辅助分 "
              f"{s['aux_score']}（{band}），与主层 {s['score']}/7 "
              f"{ZH_TIER_SHORT[tk]}{sent}。</li>")
        pattern = re.compile(r"<li><b>辅助分的定位：</b>.*?</li>", re.S)
    else:
        if div == "aligned":
            sent = "aligns with"
        elif div == "tech_first":
            sent = ("disagrees with")
        else:
            sent = "disagrees with"
        tail = ""
        if div == "tech_first":
            tail = ", meaning the technical layer deteriorated first while fundamentals have not confirmed"
        elif div == "fundamental_first":
            tail = ", meaning fundamental risk is running ahead of the technical layer"
        li = (f"<li><b>Auxiliary score's role:</b> valuation/credit/macro are slow variables; "
              f"the current auxiliary score of {s['aux_score']} ({band}) {sent} the main layer's "
              f"{s['score']}/7 {EN_TIER[tk]}{tail}.</li>")
        pattern = re.compile(r"<li><b>Auxiliary score's role:</b>.*?</li>", re.S)
    text, n = pattern.subn(lambda _m: li, text)
    if n != 1:
        raise SystemExit(f"[FAIL] {path}: 辅助分段落匹配到 {n} 处（期望 1）")
    path.write_text(text, encoding="utf-8", newline="\n")
    print(f"[OK] {path.relative_to(ROOT)}  辅助分段落已更新")


def main() -> None:
    s = compute_snapshot()
    zh = build_page_data(s, "zh")
    en = build_page_data(s, "en")
    patch_app_js(ROOT / "assets" / "app.js", zh)
    patch_app_js(ROOT / "en" / "assets" / "app.js", en)
    patch_html(ROOT / "index.html", s, "zh")
    patch_html(ROOT / "en" / "index.html", s, "en")


if __name__ == "__main__":
    main()
