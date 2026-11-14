#!/usr/bin/env python3
"""
美股暴跌预警 · 历史评分回测
--------------------------------------------------------------------------
数据源（均为公开、无需 API Key）：
  - Nasdaq API：SPY / RSP / HYG / LQD 日线（约 10 年）
  - CBOE：VIX / VIX3M 日线（长历史）
  - 美国财政部：2Y / 10Y 名义收益率 + 10Y TIPS 实际收益率（按年 CSV）
  - DBnomics / ILO：美国月度失业率（LFS/CPS）
  - multpl.com：Shiller CAPE 月度

回测版信号（6 个可计算信号）：
  信用 25 / 宽度 20 / 估值 15 / 波动率 15 / 利率 10 / 宏观 15
说明：
  - HY OAS 免费历史仅 3 年，信用用 HYG/LQD 相对 200 日均线 + 动量的代理。
  - 宽度用 RSP/SPY（等权/市值权）相对 200 日均线 + 动量的代理。
  - 杠杆/流动性（NFCI）、情绪、结构性风险没有稳定免费历史，未纳入；
    主站模型仍保留这三类信号。
  - 月度数据滞后一个月，避免前视偏差。

输出：data/backtest.json、assets/backtest-data.js、控制台摘要。
"""

from __future__ import annotations

import io
import json
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
RAW.mkdir(parents=True, exist_ok=True)

UA = {"User-Agent": "Mozilla/5.0"}
SESSION = requests.Session()
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=5,
            backoff_factor=1.2,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"],
        )
    ),
)

NASDAQ_SYMBOLS = ["SPY", "RSP", "HYG", "LQD"]
TREASURY_YEARS = list(range(2015, 2027))

WEIGHTS = {
    "credit": 25,
    "breadth": 20,
    "valuation": 15,
    "volatility": 15,
    "rates": 10,
    "macro": 15,
}
WEIGHT_SUM = sum(WEIGHTS.values())


def clip01(s: pd.Series) -> pd.Series:
    return s.clip(0, 1)


def rolling_rank(s: pd.Series, window: int, min_periods: int) -> pd.Series:
    return s.rolling(window, min_periods=min_periods).rank(pct=True)


def fetch_nasdaq(symbol: str) -> pd.DataFrame:
    cache = RAW / f"nasdaq_{symbol}.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        url = (
            f"https://api.nasdaq.com/api/quote/{symbol}/historical"
            f"?assetclass=etf&fromdate=2015-01-01&todate=2026-11-10&limit=9999"
        )
        r = SESSION.get(url, headers={**UA, "Accept": "application/json"}, timeout=60)
        r.raise_for_status()
        df = pd.DataFrame(r.json()["data"]["tradesTable"]["rows"])
        df.to_csv(cache, index=False)
        time.sleep(1.0)
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        if col in df.columns:
            df[col] = pd.to_numeric(
                df[col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
                errors="coerce",
            )
    return df.dropna(subset=["date"]).sort_values("date").set_index("date")


def fetch_cboe(name: str) -> pd.Series:
    cache = RAW / f"cboe_{name}.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        url = f"https://cdn.cboe.com/api/global/us_indices/daily_prices/{name}_History.csv"
        r = SESSION.get(url, headers=UA, timeout=60)
        r.raise_for_status()
        cache.write_text(r.text, encoding="utf-8")
        df = pd.read_csv(io.StringIO(r.text))
    df["DATE"] = pd.to_datetime(df["DATE"], errors="coerce")
    df["CLOSE"] = pd.to_numeric(df["CLOSE"], errors="coerce")
    return df.dropna(subset=["DATE"]).set_index("DATE")["CLOSE"].sort_index()


def fetch_treasury(kind: str) -> pd.DataFrame:
    """kind: nominal | real"""
    frames = []
    for year in TREASURY_YEARS:
        cache = RAW / f"treasury_{kind}_{year}.csv"
        if cache.exists():
            text = cache.read_text(encoding="utf-8")
        else:
            if kind == "real":
                type_ = "daily_treasury_real_yield_curve"
            else:
                type_ = "daily_treasury_yield_curve"
            url = (
                "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/"
                f"daily-treasury-rates.csv/{year}/all?type={type_}&"
                f"field_tdr_date_value={year}&page&_format=csv"
            )
            r = SESSION.get(url, headers=UA, timeout=60)
            if r.status_code != 200 or len(r.text) < 50:
                continue
            text = r.text
            cache.write_text(text, encoding="utf-8")
            time.sleep(0.4)
        df = pd.read_csv(io.StringIO(text))
        df.columns = [c.strip().replace("﻿", "") for c in df.columns]
        df["Date"] = pd.to_datetime(df["Date"], errors="coerce")
        frames.append(df)
    out = pd.concat(frames, ignore_index=True).dropna(subset=["Date"])
    out = out.sort_values("Date").drop_duplicates("Date").set_index("Date")
    return out


def fetch_unemployment() -> pd.Series:
    """OECD 月度失业率（美国，15 岁以上，总计，季调）。"""
    cache = RAW / "oecd_unemployment_usa.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        base = "https://api.db.nomics.world/v22/series/OECD/DSD_LFS@DF_IALFS_UNE_M"
        params = {
            "dimensions": json.dumps({
                "REF_AREA": ["USA"],
                "FREQ": ["M"],
                "MEASURE": ["UNE_LF_M"],
                "UNIT_MEASURE": ["PT_LF_SUB"],
                "AGE": ["Y_GE15"],
                "SEX": ["_T"],
                "ADJUSTMENT": ["Y"],
            }),
            "observations": "1",
            "limit": "5",
        }
        r = SESSION.get(base, params=params, timeout=60)
        r.raise_for_status()
        doc = r.json()["series"]["docs"][0]
        df = pd.DataFrame({"period": doc["period"], "value": doc["value"]})
        df.to_csv(cache, index=False)
    df["period"] = pd.to_datetime(df["period"], format="%Y-%m", errors="coerce")
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    return df.dropna(subset=["period"]).set_index("period")["value"].sort_index()


def fetch_cape() -> pd.Series:
    cache = RAW / "multpl_cape.csv"
    if cache.exists():
        df = pd.read_csv(cache)
    else:
        r = SESSION.get(
            "https://www.multpl.com/shiller-pe/table/by-month",
            headers=UA,
            timeout=60,
        )
        r.raise_for_status()
        df = pd.read_html(io.StringIO(r.text))[0]
        df.to_csv(cache, index=False)
    df.columns = ["date", "cape"]
    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["cape"] = pd.to_numeric(df["cape"], errors="coerce")
    series = df.dropna(subset=["date"]).set_index("date")["cape"].sort_index()
    return series.resample("MS").last()


def main() -> None:
    # ---------- 行情 ----------
    prices = {}
    for sym in NASDAQ_SYMBOLS:
        df = fetch_nasdaq(sym)
        prices[sym] = df["close"]
        print(f"{sym}: {len(df)} rows, {df.index.min().date()} -> {df.index.max().date()}")

    spy = prices["SPY"].dropna()
    idx = spy.index

    def align_daily(s: pd.Series) -> pd.Series:
        return s.reindex(idx).ffill()

    # ---------- CBOE ----------
    vix_all = fetch_cboe("VIX")
    vix3m_all = fetch_cboe("VIX3M")
    vix = align_daily(vix_all)
    vix3m = align_daily(vix3m_all)
    print(f"VIX: {len(vix_all)} rows, {vix_all.index.min().date()} -> {vix_all.index.max().date()}")
    print(f"VIX3M: {len(vix3m_all)} rows, {vix3m_all.index.min().date()} -> {vix3m_all.index.max().date()}")

    # ---------- 财政部 ----------
    nominal = fetch_treasury("nominal")
    real = fetch_treasury("real")
    nom10 = align_daily(pd.to_numeric(nominal["10 Yr"], errors="coerce"))
    nom2 = align_daily(pd.to_numeric(nominal["2 Yr"], errors="coerce"))
    real10 = align_daily(pd.to_numeric(real["10 YR"], errors="coerce"))
    print(f"Treasury nominal: {len(nominal)} rows, {nominal.index.min().date()} -> {nominal.index.max().date()}")
    print(f"Treasury real: {len(real)} rows, {real.index.min().date()} -> {real.index.max().date()}")

    # ---------- 失业率 / CAPE ----------
    unrate_m = fetch_unemployment().resample("MS").last().shift(1)
    unrate = align_daily(unrate_m)
    print(f"UNRATE: {len(unrate_m)} months, {unrate_m.index.min().date()} -> {unrate_m.index.max().date()}")

    cape_m = fetch_cape().shift(1)
    cape = align_daily(cape_m)
    print(f"CAPE: {len(cape_m)} months, {cape_m.index.min().date()} -> {cape_m.index.max().date()}")

    # ---------- 信号 ----------
    # 1) 信用压力代理：HYG/LQD 相对 200 日均线 + 3 个月动量 + HYG 自身趋势
    hyg = align_daily(prices["HYG"])
    lqd = align_daily(prices["LQD"])
    hyg_lqd = hyg / lqd
    hl_ma = hyg_lqd.rolling(200, min_periods=100).mean()
    credit_trend = clip01((hl_ma - hyg_lqd) / hl_ma / 0.05)
    credit_mom = clip01(-(hyg_lqd / hyg_lqd.shift(63) - 1) / 0.08)
    hyg_ma = hyg.rolling(200, min_periods=100).mean()
    hyg_trend = clip01((hyg_ma - hyg) / hyg_ma / 0.05)
    credit = clip01(0.5 * credit_trend + 0.3 * credit_mom + 0.2 * hyg_trend)

    # 2) 宽度代理：等权 RSP / 市值权 SPY 相对 200 日均线 + 3 个月动量
    rsp = align_daily(prices["RSP"])
    ratio = rsp / spy
    ratio_ma = ratio.rolling(200, min_periods=100).mean()
    breadth_trend = clip01((ratio_ma - ratio) / ratio_ma / 0.05)
    breadth_mom = clip01(-(ratio / ratio.shift(63) - 1) / 0.08)
    breadth = clip01(0.6 * breadth_trend + 0.4 * breadth_mom)

    # 3) 估值：CAPE 在 20 年滚动窗口中的百分位（月度，滞后一月）
    valuation = align_daily(rolling_rank(cape_m, 240, 120))

    # 4) 波动率：VIX 2 年百分位 + VIX/VIX3M 期限结构
    vix_rank = rolling_rank(vix, 504, 126)
    vix_term = clip01((vix / vix3m - 1) / 0.30)
    volatility = clip01(0.5 * vix_rank + 0.5 * vix_term)

    # 5) 利率：10Y TIPS 实际利率 3 个月变化 + 2s10s 倒挂
    real_mom = clip01((real10 - real10.shift(63)) / 1.0)
    curve = nom10 - nom2
    curve_score = clip01(-curve / 1.0)
    rates = clip01(0.5 * real_mom + 0.5 * curve_score)

    # 6) 宏观：失业率 12 个月变化（Sahm 思路）
    macro = clip01((unrate - unrate.shift(12)) / 0.5)

    signals = pd.DataFrame({
        "credit": credit,
        "breadth": breadth,
        "valuation": valuation,
        "volatility": volatility,
        "rates": rates,
        "macro": macro,
    })

    score = sum(signals[k] * w for k, w in WEIGHTS.items()) / WEIGHT_SUM * 100
    score = score.rolling(5, min_periods=1).mean().clip(0, 100)
    score = score.dropna()

    # 滚动 3 年分位：避免用未来数据，回答“当前风险分在过去 3 年中的相对位置”
    score_pct = (score.rolling(756, min_periods=126).rank(pct=True) * 100)

    # 供技术分析模块合并的日频评分
    daily_out = pd.DataFrame({"score": score, "score_pct": score_pct}).join(signals)
    daily_out.index.name = "date"
    daily_out.to_csv(ROOT / "data" / "backtest_score_daily.csv", encoding="utf-8")

    # ---------- 回撤与危机片段 ----------
    peak = spy.cummax()
    dd = spy / peak - 1

    episodes = []
    in_ep = False
    trough_val = 0.0
    trough_date = None
    peak_date = None
    for i in range(1, len(spy)):
        d = spy.index[i]
        if not in_ep:
            if dd.iloc[i] <= -0.08:
                prior = spy.iloc[: i + 1]
                peak_val = prior.max()
                peak_date = prior[prior == peak_val].index[-1]
                in_ep = True
                trough_val = dd.iloc[i]
                trough_date = d
        else:
            if dd.iloc[i] < trough_val:
                trough_val = dd.iloc[i]
                trough_date = d
            if dd.iloc[i] >= -0.001:
                episodes.append({
                    "peak": peak_date,
                    "trough": trough_date,
                    "drawdown": trough_val,
                    "recovery": d,
                })
                in_ep = False
    if in_ep:
        episodes.append({
            "peak": peak_date,
            "trough": trough_date,
            "drawdown": trough_val,
            "recovery": None,
        })

    def score_at(date: pd.Timestamp, offset: int):
        if date not in score.index:
            return None
        i = score.index.get_loc(date)
        j = i - offset
        return float(score.iloc[j]) if j >= 0 else None

    def first_cross_before(peak_date: pd.Timestamp, level: float, lookback: int = 126):
        if peak_date not in score.index:
            return None
        i = score.index.get_loc(peak_date)
        window = score.iloc[max(0, i - lookback): i + 1]
        hit = window[window >= level]
        return int((peak_date - hit.index[0]).days) if len(hit) else None

    def pct_at(date: pd.Timestamp, offset: int):
        if date not in score_pct.index:
            return None
        i = score_pct.index.get_loc(date)
        j = i - offset
        return float(score_pct.iloc[j]) if j >= 0 and not pd.isna(score_pct.iloc[j]) else None

    def pct_max_between(a: pd.Timestamp, b: pd.Timestamp):
        s = score_pct.loc[a:b].dropna()
        return float(s.max()) if len(s) else None

    def first_cross_pct_before(peak_date: pd.Timestamp, level: float, lookback: int = 126):
        if peak_date not in score_pct.index:
            return None
        i = score_pct.index.get_loc(peak_date)
        window = score_pct.iloc[max(0, i - lookback): i + 1].dropna()
        hit = window[window >= level]
        return int((peak_date - hit.index[0]).days) if len(hit) else None

    rows = []
    for ep in episodes:
        peak_date = ep["peak"]
        trough_date = ep["trough"]
        if peak_date not in score.index:
            continue
        pi = score.index.get_loc(peak_date)
        ti = score.index.get_loc(trough_date) if trough_date in score.index else pi
        pre90 = score.iloc[max(0, pi - 90): pi + 1]
        pre_max_90 = float(pre90.max()) if len(pre90) else None
        pre_max_30 = float(score.iloc[max(0, pi - 30): pi + 1].max())
        post10 = score.iloc[pi: min(len(score), pi + 11)]
        post_max_10 = float(post10.max()) if len(post10) else None
        lead60 = first_cross_before(peak_date, 60)
        lead65 = first_cross_before(peak_date, 65)
        lead80 = first_cross_pct_before(peak_date, 80)

        pct_t90 = pct_at(peak_date, 90)
        pct_t30 = pct_at(peak_date, 30)
        pct_t10 = pct_at(peak_date, 10)
        pct_trough = float(score_pct.iloc[ti]) if not pd.isna(score_pct.iloc[ti]) else None
        pre_pct = score_pct.iloc[max(0, pi - 90): pi + 1].dropna()
        pct_pre_max = float(pre_pct.max()) if len(pre_pct) else None
        post_pct = score_pct.iloc[pi: min(len(score_pct), pi + 11)].dropna()
        pct_post_max_10 = float(post_pct.max()) if len(post_pct) else None

        # 关键规则：预警必须在峰值附近仍然成立，不能只看 90 天内曾经高过
        if ep["drawdown"] > -0.10:
            label = "小幅回撤"
        elif (pct_t30 is not None and pct_t30 >= 80) or (
            pct_t10 is not None and pct_t30 is not None and pct_t10 >= 80 and pct_t30 >= 65
        ):
            label = "提前预警"
        elif (pct_t30 is not None and pct_t30 >= 65) or (pct_t10 is not None and pct_t10 >= 75):
            label = "部分预警"
        elif pct_post_max_10 is not None and pct_post_max_10 >= 80:
            label = "同步确认"
        else:
            label = "未捕捉"

        rows.append({
            "peak": peak_date.strftime("%Y-%m-%d"),
            "trough": trough_date.strftime("%Y-%m-%d"),
            "recovery": ep["recovery"].strftime("%Y-%m-%d") if ep["recovery"] is not None else None,
            "drawdown": round(float(ep["drawdown"]) * 100, 1),
            "major": bool(ep["drawdown"] <= -0.10),
            "score_t90": round(score_at(peak_date, 90), 1) if score_at(peak_date, 90) is not None else None,
            "score_t60": round(score_at(peak_date, 60), 1) if score_at(peak_date, 60) is not None else None,
            "score_t30": round(score_at(peak_date, 30), 1) if score_at(peak_date, 30) is not None else None,
            "score_t10": round(score_at(peak_date, 10), 1) if score_at(peak_date, 10) is not None else None,
            "pre_max_90": round(pre_max_90, 1) if pre_max_90 is not None else None,
            "pre_max_30": round(pre_max_30, 1) if pre_max_30 is not None else None,
            "score_trough": round(float(score.iloc[ti]), 1),
            "post_max_10": round(post_max_10, 1) if post_max_10 is not None else None,
            "lead60_days": lead60,
            "lead65_days": lead65,
            "lead80_days": lead80,
            "pct_t90": round(pct_t90, 0) if pct_t90 is not None else None,
            "pct_t30": round(pct_t30, 0) if pct_t30 is not None else None,
            "pct_t10": round(pct_t10, 0) if pct_t10 is not None else None,
            "pct_pre_max": round(pct_pre_max, 0) if pct_pre_max is not None else None,
            "pct_trough": round(pct_trough, 0) if pct_trough is not None else None,
            "pct_post_max_10": round(pct_post_max_10, 0) if pct_post_max_10 is not None else None,
            "label": label,
        })

    # ---------- 假阳性 ----------
    above = score >= 60
    runs = []
    start = None
    prev = None
    for d, v in above.items():
        if v and start is None:
            start = d
        if not v and start is not None:
            runs.append((start, prev))
            start = None
        prev = d
    if start is not None:
        runs.append((start, prev))

    false_positives = []
    for a, b in runs:
        n_days = int(np.busday_count(a.date(), b.date())) + 1
        if n_days < 20:
            continue
        future = spy.loc[b: b + pd.Timedelta(days=190)]
        if len(future) < 2:
            continue
        fwd_dd = float(future.min() / future.iloc[0] - 1)
        if fwd_dd > -0.10:
            false_positives.append({
                "start": a.strftime("%Y-%m-%d"),
                "end": b.strftime("%Y-%m-%d"),
                "trading_days": n_days,
                "max_score": round(float(score.loc[a:b].max()), 1),
                "forward_6m_return": round(fwd_dd * 100, 1),
            })

    # ---------- 预警误报统计 ----------
    def warning_stats(threshold: float, min_days: int = 10, merge_gap: int = 10, horizon: int = 126, hit_dd: float = 0.10):
        """滚动分位 >= threshold 持续 >= min_days 个交易日为一次预警；
        相隔 <= merge_gap 个交易日的预警合并；未来 126 个交易日内出现 >=10% 回撤为命中。"""
        above = score_pct >= threshold
        runs = []
        start = None
        prev = None
        for d, v in above.items():
            if v and start is None:
                start = d
            if not v and start is not None:
                runs.append((start, prev))
                start = None
            prev = d
        if start is not None:
            runs.append((start, prev))

        runs = [(a, b) for a, b in runs if int(np.busday_count(a.date(), b.date())) + 1 >= min_days]
        merged = []
        for a, b in runs:
            if merged and int(np.busday_count(merged[-1][1].date(), a.date())) <= merge_gap:
                merged[-1] = (merged[-1][0], b)
            else:
                merged.append((a, b))

        out_rows = []
        hits = fps = post = 0
        for a, b in merged:
            if a not in spy.index:
                continue
            i = spy.index.get_loc(a)
            p0 = float(spy.iloc[i])
            peak = float(spy.iloc[: i + 1].max())
            dd_start = p0 / peak - 1
            future = spy.iloc[i: i + horizon + 1]
            fwd = float(future.min() / p0 - 1) if len(future) else 0.0

            if dd_start <= -0.08:
                outcome = "post"
                post += 1
            elif fwd <= -hit_dd:
                outcome = "hit"
                hits += 1
            else:
                outcome = "false"
                fps += 1

            out_rows.append({
                "start": a.strftime("%Y-%m-%d"),
                "end": b.strftime("%Y-%m-%d"),
                "max_pct": round(float(score_pct.loc[a:b].dropna().max()), 0) if len(score_pct.loc[a:b].dropna()) else None,
                "dd_at_start": round(dd_start * 100, 1),
                "forward_6m_dd": round(fwd * 100, 1),
                "outcome": outcome,
            })

        pre = hits + fps
        return {
            "threshold": threshold,
            "minDays": min_days,
            "mergeGapDays": merge_gap,
            "horizonDays": horizon,
            "episodes": len(out_rows),
            "preCrisis": pre,
            "hits": hits,
            "falsePositives": fps,
            "postCrisis": post,
            "falsePositiveRate": round(fps / pre * 100, 0) if pre else None,
            "rows": out_rows,
        }

    warning_stats_out = {str(t): warning_stats(t, hit_dd=0.10) for t in [75, 80, 85]}
    warning_stats_8_out = {str(t): warning_stats(t, hit_dd=0.08) for t in [75, 80, 85]}

    # ---------- 汇总 ----------
    major = [r for r in rows if r["major"]]
    sharp = [r for r in rows if not r["major"]]
    early = [r for r in major if r["label"] == "提前预警"]
    partial = [r for r in major if r["label"] == "部分预警"]
    coincident = [r for r in major if r["label"] == "同步确认"]
    missed = [r for r in major if r["label"] == "未捕捉"]

    weekly = score.resample("W-FRI").last().dropna()
    series = [{"d": d.strftime("%Y-%m-%d"), "v": round(float(v), 1)} for d, v in weekly.items()]
    weekly_pct = score_pct.resample("W-FRI").last().dropna()
    series_pct = [{"d": d.strftime("%Y-%m-%d"), "v": round(float(v), 1)} for d, v in weekly_pct.items()]

    signal_rows = []
    for r in rows:
        peak_date = pd.Timestamp(r["peak"])
        if peak_date not in signals.index:
            continue
        i = signals.index.get_loc(peak_date)
        j = max(0, i - 30)
        signal_rows.append({
            "peak": r["peak"],
            "values": {k: round(float(signals[k].iloc[j]) * 100, 0) for k in WEIGHTS},
        })

    out = {
        "meta": {
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "windowStart": score.index.min().strftime("%Y-%m-%d"),
            "windowEnd": score.index.max().strftime("%Y-%m-%d"),
            "priceStart": spy.index.min().strftime("%Y-%m-%d"),
            "priceEnd": spy.index.max().strftime("%Y-%m-%d"),
            "weights": WEIGHTS,
            "weightSum": WEIGHT_SUM,
            "signalCount": len(WEIGHTS),
            "notes": [
                "HY OAS 免费历史仅 3 年，信用信号使用 HYG/LQD 相对 200 日均线 + 动量的代理。",
                "宽度信号使用 RSP/SPY（等权/市值权）相对 200 日均线 + 动量的代理。",
                "杠杆/流动性（NFCI）、情绪、结构性风险没有稳定免费历史，未纳入回测；主站模型仍保留这三类信号。",
                "月度数据滞后一个月，避免前视偏差。",
            ],
        },
        "summary": {
            "episodeCount": len(rows),
            "majorCount": len(major),
            "sharpCount": len(sharp),
            "early": len(early),
            "partial": len(partial),
            "coincident": len(coincident),
            "missed": len(missed),
            "falsePositiveCount": len(false_positives),
            "medianPreMax": round(float(np.median([r["pre_max_90"] for r in major if r["pre_max_90"] is not None])), 1) if major else None,
        },
        "series": series,
        "seriesPct": series_pct,
        "episodes": rows,
        "signalRows": signal_rows,
        "falsePositives": false_positives,
        "warningStats": warning_stats_out,
        "warningStats8": warning_stats_8_out,
    }

    (ROOT / "data" / "backtest.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "assets" / "backtest-data.js").write_text(
        "const BACKTEST_DATA = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    print("\n=== 回测摘要 ===")
    print(f"窗口: {out['meta']['windowStart']} -> {out['meta']['windowEnd']}")
    print(f"危机片段: {len(rows)} (>=10%: {len(major)}, 8-10%: {len(sharp)})")
    print(f"提前预警: {len(early)} | 部分预警: {len(partial)} | 同步确认: {len(coincident)} | 未捕捉: {len(missed)}")
    print(f"假阳性: {len(false_positives)}")
    print("\n=== 预警误报统计（分位阈值 / 持续10日 / 未来126交易日） ===")
    for t, st in warning_stats_out.items():
        print(f"分位>={t} / 10%: 事前 {st['preCrisis']} 次, 命中 {st['hits']}, 误报 {st['falsePositives']}, 误报率 {st['falsePositiveRate']}%, 事后高位 {st['postCrisis']}")
    print("--- 8% 也算大跌 ---")
    for t, st in warning_stats_8_out.items():
        print(f"分位>={t} / 8%: 事前 {st['preCrisis']} 次, 命中 {st['hits']}, 误报 {st['falsePositives']}, 误报率 {st['falsePositiveRate']}%, 事后高位 {st['postCrisis']}")
    print("\n=== 片段明细 ===")
    for r in rows:
        print(
            f"{r['peak']} -> {r['trough']}  dd={r['drawdown']}%  "
            f"T-90={r['score_t90']} T-30={r['score_t30']} preMax={r['pre_max_90']}  "
            f"pct90={r['pct_t90']} pct30={r['pct_t30']} pct10={r['pct_t10']} pctPreMax={r['pct_pre_max']} lead80={r['lead80_days']}  {r['label']}"
        )


if __name__ == "__main__":
    main()
