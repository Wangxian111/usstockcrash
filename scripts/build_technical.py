#!/usr/bin/env python3
"""
技术分析叠加回测
--------------------------------------------------------------------------
目标：未来 126 个交易日内，SPY 从当前收盘价起算的最大回撤是否 <= -10%。

内容：
  1. 日线 / 周线技术指标（均线、RSI、MACD、布林带、ATR、成交量、K 线形态）
  2. 逐个指标的“预警胜率 / 召回 / 误报 / 提升倍数”
  3. Purged walk-forward 逻辑回归：
     - 仅基本面评分
     - 仅技术指标
     - 基本面 + 技术
  4. 与简单规则（fund_score >= 45、fund_pct >= 80）对比

输出：data/technical.json、assets/technical-data.js、控制台摘要。
"""

from __future__ import annotations

import json
from datetime import datetime
from math import sqrt
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import roc_auc_score
from sklearn.preprocessing import StandardScaler

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"

HORIZON = 126  # 约 6 个月
DRAWDOWN_THRESHOLD = -0.10


def rsi(series: pd.Series, n: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.ewm(alpha=1 / n, adjust=False).mean()
    avg_loss = loss.ewm(alpha=1 / n, adjust=False).mean()
    rs = avg_gain / avg_loss.replace(0, np.nan)
    return 100 - 100 / (1 + rs)


def macd_parts(series: pd.Series):
    ema12 = series.ewm(span=12, adjust=False).mean()
    ema26 = series.ewm(span=26, adjust=False).mean()
    macd = ema12 - ema26
    signal = macd.ewm(span=9, adjust=False).mean()
    hist = macd - signal
    return macd, signal, hist


def atr(high: pd.Series, low: pd.Series, close: pd.Series, n: int = 14) -> pd.Series:
    prev_close = close.shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, adjust=False).mean()


def load_spy() -> pd.DataFrame:
    df = pd.read_csv(RAW / "nasdaq_SPY.csv")
    df["date"] = pd.to_datetime(df["date"], format="%m/%d/%Y", errors="coerce")
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(
            df[col].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False),
            errors="coerce",
        )
    return df.dropna(subset=["date"]).sort_values("date").set_index("date")


def load_score() -> pd.DataFrame:
    df = pd.read_csv(ROOT / "data" / "backtest_score_daily.csv", parse_dates=["date"])
    return df.set_index("date").sort_index()


def build_indicators(spy: pd.DataFrame) -> pd.DataFrame:
    close = spy["close"]
    high = spy["high"]
    low = spy["low"]
    open_ = spy["open"]
    volume = spy["volume"]

    sma20 = close.rolling(20).mean()
    sma50 = close.rolling(50).mean()
    sma200 = close.rolling(200).mean()

    # 日线 RSI / MACD
    rsi14 = rsi(close, 14)
    macd, macd_signal, macd_hist = macd_parts(close)

    # 布林带
    bb_mid = sma20
    bb_std = close.rolling(20).std()
    bb_up = bb_mid + 2 * bb_std
    bb_dn = bb_mid - 2 * bb_std
    bb_width = (bb_up - bb_dn) / bb_mid
    bb_width_pct = bb_width.rolling(252, min_periods=60).rank(pct=True)

    # ATR
    atr14 = atr(high, low, close, 14)
    atr_pct = atr14 / close
    atr_rank = atr_pct.rolling(252, min_periods=60).rank(pct=True)

    # 成交量 / 动量
    vol_ratio = volume / volume.rolling(20).mean()
    roc21 = close.pct_change(21)
    roc63 = close.pct_change(63)

    # 周线
    w = spy.resample("W-FRI").agg({
        "open": "first", "high": "max", "low": "min", "close": "last", "volume": "sum",
    }).dropna()
    w_rsi14 = rsi(w["close"], 14)
    w_macd, w_signal, w_hist = macd_parts(w["close"])
    w_sma30 = w["close"].rolling(30).mean()
    w_dist30 = w["close"] / w_sma30 - 1
    w_bb_mid = w["close"].rolling(20).mean()
    w_bb_std = w["close"].rolling(20).std()
    w_bb_width = (4 * w_bb_std) / w_bb_mid
    w_bb_width_pct = w_bb_width.rolling(52, min_periods=26).rank(pct=True)
    w_hist_norm = w_hist / w["close"]
    w_roc4 = w["close"].pct_change(4)

    def weekly(s: pd.Series) -> pd.Series:
        return s.reindex(close.index, method="ffill")

    # K 线形态
    body = close - open_
    upper = high - np.maximum(close, open_)
    lower = np.minimum(close, open_) - low
    bear_engulf = (
        (close.shift(1) > open_.shift(1))
        & (close < open_)
        & (open_ >= close.shift(1))
        & (close <= open_.shift(1))
    )
    shooting_star = (upper > 2 * body.abs()) & (lower < 0.3 * body.abs()) & (close < open_)
    outside_down = (high > high.shift(1)) & (low < low.shift(1)) & (close < open_)
    gap_down = open_ < low.shift(1)

    out = pd.DataFrame(index=close.index)
    out["close"] = close
    out["sma20"] = sma20
    out["sma50"] = sma50
    out["sma200"] = sma200
    out["dist20"] = close / sma20 - 1
    out["dist50"] = close / sma50 - 1
    out["dist200"] = close / sma200 - 1
    out["rsi14"] = rsi14
    out["macd"] = macd
    out["macd_signal"] = macd_signal
    out["macd_hist"] = macd_hist
    out["macd_hist_norm"] = macd_hist / close
    out["bb_up"] = bb_up
    out["bb_dn"] = bb_dn
    out["bb_width_pct"] = bb_width_pct
    out["atr_pct"] = atr_pct
    out["atr_rank"] = atr_rank
    out["vol_ratio"] = vol_ratio
    out["roc21"] = roc21
    out["roc63"] = roc63
    out["w_rsi14"] = weekly(w_rsi14)
    out["w_macd"] = weekly(w_macd)
    out["w_macd_signal"] = weekly(w_signal)
    out["w_macd_hist_norm"] = weekly(w_hist_norm)
    out["w_dist30"] = weekly(w_dist30)
    out["w_bb_width_pct"] = weekly(w_bb_width_pct)
    out["w_roc4"] = weekly(w_roc4)
    out["bear_engulf"] = bear_engulf.astype(float)
    out["shooting_star"] = shooting_star.astype(float)
    out["outside_down"] = outside_down.astype(float)
    out["gap_down"] = gap_down.astype(float)
    return out


def evaluate_indicators(ind: pd.DataFrame, y: pd.Series, fwd_dd: pd.Series, subset: pd.Series | None = None) -> list[dict]:
    if subset is None:
        subset = pd.Series(True, index=y.index)
    base_rate = float(y[subset & y.notna()].mean())
    conditions = {
        "收盘 < 200 日均线": (ind["close"] < ind["sma200"], "趋势"),
        "收盘 < 50 日均线": (ind["close"] < ind["sma50"], "趋势"),
        "50 日均线 < 200 日均线（死叉）": (ind["sma50"] < ind["sma200"], "趋势"),
        "RSI(14) > 70（超买）": (ind["rsi14"] > 70, "超买"),
        "RSI(14) < 40（走弱）": (ind["rsi14"] < 40, "动量"),
        "MACD 线 < 信号线": (ind["macd"] < ind["macd_signal"], "动量"),
        "布林带宽 < 20% 分位（挤压）": (ind["bb_width_pct"] < 0.2, "波动率"),
        "收盘 > 布林上轨": (ind["close"] > ind["bb_up"], "超买"),
        "ATR 分位 > 80%（高波动）": (ind["atr_rank"] > 0.8, "波动率"),
        "成交量 > 1.5×20 日均量": (ind["vol_ratio"] > 1.5, "成交量"),
        "周 RSI(14) > 70（超买）": (ind["w_rsi14"] > 70, "周线"),
        "周 MACD 线 < 信号线": (ind["w_macd"] < ind["w_macd_signal"], "周线"),
        "周收盘 < 30 周均线": (ind["w_dist30"] < 0, "周线"),
        "周布林带宽 < 20% 分位": (ind["w_bb_width_pct"] < 0.2, "周线"),
        "日线看跌吞没": (ind["bear_engulf"] > 0, "K 线形态"),
        "日线射击之星": (ind["shooting_star"] > 0, "K 线形态"),
        "日线外包下跌": (ind["outside_down"] > 0, "K 线形态"),
        "日线向下跳空": (ind["gap_down"] > 0, "K 线形态"),
    }

    rows = []
    for name, (cond, kind) in conditions.items():
        mask = cond.fillna(False) & y.notna() & subset
        n = int(mask.sum())
        if n < 30:
            continue
        precision = float(y[mask].mean())
        positives = int((y == 1).sum())
        negatives = int((y == 0).sum())
        recall = float(((mask) & (y == 1)).sum() / positives) if positives else None
        fpr = float(((mask) & (y == 0)).sum() / negatives) if negatives else None
        triggers = int((mask & ~mask.shift(1, fill_value=False)).sum())
        rows.append({
            "name": name,
            "kind": kind,
            "signalDays": n,
            "triggers": triggers,
            "precision": round(precision * 100, 1),
            "lift": round(precision / base_rate, 2) if base_rate else None,
            "recall": round(recall * 100, 1) if recall is not None else None,
            "fpr": round(fpr * 100, 1) if fpr is not None else None,
            "avgFwdDd": round(float(fwd_dd[mask].mean()) * 100, 1),
            "medianFwdDd": round(float(fwd_dd[mask].median()) * 100, 1),
        })
    return sorted(rows, key=lambda r: (-(r["lift"] or 0), -r["signalDays"]))


def wilson_ci(k: int, n: int, z: float = 1.96) -> list:
    """二项比例的 Wilson 95% 区间（标签重叠时实际不确定性更大）。"""
    if n == 0:
        return [None, None]
    p = k / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return [round((center - half) * 100, 1), round((center + half) * 100, 1)]


def model_metrics(y: pd.Series, p: np.ndarray, alert: np.ndarray) -> dict:
    y_arr = y.values
    positives = int((y_arr == 1).sum())
    negatives = int((y_arr == 0).sum())
    alert = np.asarray(alert, dtype=bool)
    alerts = int(alert.sum())
    hits = int((alert & (y_arr == 1)).sum())
    precision = float(y_arr[alert].mean()) if alerts else None
    recall = float(hits / positives) if positives else None
    fpr = float(((alert) & (y_arr == 0)).sum() / negatives) if negatives else None
    return {
        "n": int(len(y_arr)),
        "alerts": alerts,
        "hits": hits,
        "alertRate": round(float(alert.mean()) * 100, 1),
        "precision": round(precision * 100, 1) if precision is not None else None,
        "precisionCI": wilson_ci(hits, alerts) if alerts else [None, None],
        "recall": round(recall * 100, 1) if recall is not None else None,
        "fpr": round(fpr * 100, 1) if fpr is not None else None,
        "auc": round(float(roc_auc_score(y_arr, p)), 3) if positives and negatives else None,
        "baseRate": round(float(y_arr.mean()) * 100, 1),
        "lift": round(precision / float(y_arr.mean()), 2) if precision is not None and y_arr.mean() else None,
    }


def main() -> None:
    spy = load_spy()
    ind = build_indicators(spy)
    score = load_score().reindex(spy.index).ffill()

    close = ind["close"]
    fwd_min = close.shift(-1).rolling(HORIZON, min_periods=1).min().shift(-(HORIZON - 1))
    fwd_dd = fwd_min / close - 1
    y = (fwd_dd <= DRAWDOWN_THRESHOLD).astype(int)
    y = y.where(fwd_dd.notna())

    valid = y.notna()
    dd_from_high = close / close.cummax() - 1
    near_high = dd_from_high > -0.05
    base_rate = float(y[valid].mean())
    near_base_rate = float(y[valid & near_high].mean())
    print(f"SPY: {len(spy)} rows, {spy.index.min().date()} -> {spy.index.max().date()}")
    print(f"Target: forward {HORIZON}d max drawdown <= {DRAWDOWN_THRESHOLD:.0%}")
    print(f"Valid rows: {int(valid.sum())}, base rate: {base_rate:.1%}")
    print(f"Near-high rows: {int((valid & near_high).sum())}, base rate: {near_base_rate:.1%}")

    indicators_all = evaluate_indicators(ind, y, fwd_dd)
    indicators = evaluate_indicators(ind, y, fwd_dd, near_high)

    # ---------- 模型特征 ----------
    feat = pd.DataFrame(index=ind.index)
    feat["fund_score"] = score["score"] / 100
    feat["fund_pct"] = score["score_pct"] / 100
    feat["dist200"] = ind["dist200"]
    feat["dist50"] = ind["dist50"]
    feat["rsi14"] = ind["rsi14"] / 100
    feat["macd_hist"] = ind["macd_hist_norm"]
    feat["bb_width_pct"] = ind["bb_width_pct"]
    feat["atr_rank"] = ind["atr_rank"]
    feat["vol_ratio"] = ind["vol_ratio"].clip(0, 3)
    feat["roc21"] = ind["roc21"]
    feat["roc63"] = ind["roc63"]
    feat["w_rsi14"] = ind["w_rsi14"] / 100
    feat["w_macd_hist"] = ind["w_macd_hist_norm"]
    feat["w_dist30"] = ind["w_dist30"]
    feat["w_bb_width_pct"] = ind["w_bb_width_pct"]
    feat["w_roc4"] = ind["w_roc4"]
    feat["bear_engulf"] = ind["bear_engulf"]
    feat["shooting_star"] = ind["shooting_star"]
    feat["outside_down"] = ind["outside_down"]
    feat["gap_down"] = ind["gap_down"]

    data = feat.join(y.rename("y")).join(fwd_dd.rename("fwd_dd"))
    data = data[data.index >= "2017-11-01"].dropna(subset=["y"])
    data = data[near_high.reindex(data.index).fillna(False)]

    fundamentals = ["fund_score", "fund_pct"]
    technical = [
        "dist200", "dist50", "rsi14", "macd_hist", "bb_width_pct", "atr_rank",
        "vol_ratio", "roc21", "roc63", "w_rsi14", "w_macd_hist", "w_dist30",
        "w_bb_width_pct", "w_roc4", "bear_engulf", "shooting_star", "outside_down", "gap_down",
    ]
    models = {
        "fundamental": fundamentals,
        "technical": technical,
        "combined": fundamentals + technical,
    }

    # ---------- Purged walk-forward ----------
    test_years = list(range(2020, 2027))
    pooled = {k: [] for k in models}
    yearly = []

    for year in test_years:
        test_start = pd.Timestamp(f"{year}-01-01")
        train = data[data.index < test_start - pd.Timedelta(days=190)]
        test = data[(data.index >= test_start) & (data.index < pd.Timestamp(f"{year + 1}-01-01"))]

        year_row = {
            "year": year,
            "testDays": int(len(test)),
            "baseRate": round(float(test["y"].mean()) * 100, 1) if len(test) else None,
            "skipped": False,
        }

        if len(test) < 40:
            year_row["skipped"] = True
            year_row["reason"] = "距高点 5% 以内的样本不足 40 天"
            yearly.append(year_row)
            continue
        if len(train) < 300:
            year_row["skipped"] = True
            year_row["reason"] = "训练样本不足 300 天"
            yearly.append(year_row)
            continue

        for name, cols in models.items():
            cols_ok = [c for c in cols if c in data.columns]
            tr = train.dropna(subset=cols_ok + ["y"])
            te = test.dropna(subset=cols_ok + ["y"])
            if len(tr) < 300 or len(te) < 40:
                continue
            scaler = StandardScaler().fit(tr[cols_ok])
            Xtr = scaler.transform(tr[cols_ok])
            Xte = scaler.transform(te[cols_ok])
            clf = LogisticRegression(
                class_weight="balanced", max_iter=3000, random_state=42, C=0.5
            )
            clf.fit(Xtr, tr["y"].values)
            p_te = clf.predict_proba(Xte)[:, 1]

            # 测试年内按预测分位取前 20% / 前 10%，保证各模型预警率可比
            q80 = float(np.quantile(p_te, 0.80))
            q90 = float(np.quantile(p_te, 0.90))
            alert20 = p_te >= q80
            alert10 = p_te >= q90

            pooled[name].append(pd.DataFrame({
                "date": te.index,
                "y": te["y"].values,
                "p": p_te,
                "alert20": alert20,
                "alert10": alert10,
                "year": year,
            }))

            m20 = model_metrics(te["y"], p_te, alert20)
            m10 = model_metrics(te["y"], p_te, alert10)
            year_row[name + "_precision20"] = m20["precision"]
            year_row[name + "_recall20"] = m20["recall"]
            year_row[name + "_auc"] = m20["auc"]
            year_row[name + "_alerts20"] = m20["alerts"]
            year_row[name + "_precision10"] = m10["precision"]
            year_row[name + "_recall10"] = m10["recall"]
            year_row[name + "_alerts10"] = m10["alerts"]

        # 简单规则基线：fund_score >= 45 / fund_pct >= 80
        if "fund_score" in test.columns:
            rule45 = (test["fund_score"] >= 0.45).values
            year_row["rule45_precision"] = round(float(test["y"][rule45].mean()) * 100, 1) if rule45.sum() else None
            year_row["rule45_alerts"] = int(rule45.sum())
        if "fund_pct" in test.columns:
            rule80 = (test["fund_pct"] >= 0.80).values
            year_row["rule80_precision"] = round(float(test["y"][rule80].mean()) * 100, 1) if rule80.sum() else None
            year_row["rule80_alerts"] = int(rule80.sum())

        yearly.append(year_row)

    model_summary = {}
    for name, frames in pooled.items():
        if not frames:
            continue
        df = pd.concat(frames, ignore_index=True)
        model_summary[name] = {
            "top20": model_metrics(df["y"], df["p"].values, df["alert20"].values),
            "top10": model_metrics(df["y"], df["p"].values, df["alert10"].values),
        }

    tech_rows = [
        r for r in yearly
        if not r.get("skipped") and r.get("technical_precision20") is not None
    ]
    stability = {
        "years": len(tech_rows),
        "minPrecision": min((r["technical_precision20"] for r in tech_rows), default=None),
        "maxPrecision": max((r["technical_precision20"] for r in tech_rows), default=None),
        "medianPrecision": round(float(np.median([r["technical_precision20"] for r in tech_rows])), 1) if tech_rows else None,
        "yearsAboveBase": sum(
            1 for r in tech_rows
            if r["technical_precision20"] is not None and r["baseRate"] is not None
            and r["technical_precision20"] > r["baseRate"]
        ),
    }

    # 规则基线（在全样本测试期上）
    test_all = data[data.index >= "2020-01-01"].copy()
    rule_metrics = {}
    for label, cond in [
        ("fund_score >= 45", test_all["fund_score"] >= 0.45),
        ("fund_pct >= 80", test_all["fund_pct"] >= 0.80),
        ("收盘 < 200 日均线", test_all["dist200"] < 0),
        ("RSI(14) > 70", test_all["rsi14"] > 0.70),
    ]:
        mask = cond.fillna(False)
        if mask.sum() < 10:
            continue
        p = mask.astype(float).values
        rule_metrics[label] = model_metrics(test_all["y"], p, mask.values)

    best_indicator = None
    if indicators:
        candidates = [r for r in indicators if r["signalDays"] >= 50]
        if candidates:
            best_indicator = max(candidates, key=lambda r: r["lift"] or 0)
    best_rule = None
    if rule_metrics:
        best_rule = max(rule_metrics.items(), key=lambda kv: kv[1]["precision"] or 0)[0]

    # 给页面用的价格图数据（周频，减小体积）
    weekly_view = pd.DataFrame({
        "close": close,
        "sma200": ind["sma200"],
        "drawdown": close / close.cummax() - 1,
    }).resample("W-FRI").last().dropna()
    series = [
        {
            "d": d.strftime("%Y-%m-%d"),
            "close": round(float(r["close"]), 2),
            "sma200": round(float(r["sma200"]), 2) if pd.notna(r["sma200"]) else None,
            "dd": round(float(r["drawdown"]) * 100, 1),
        }
        for d, r in weekly_view.iterrows()
    ]

    out = {
        "meta": {
            "generatedAt": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "windowStart": data.index.min().strftime("%Y-%m-%d"),
            "windowEnd": data.index.max().strftime("%Y-%m-%d"),
            "horizonDays": HORIZON,
            "drawdownThreshold": DRAWDOWN_THRESHOLD,
            "baseRate": round(base_rate * 100, 1),
            "testStart": "2020-01-01",
            "purgeDays": 190,
            "alertQuantile": 0.80,
            "notes": [
                "目标：未来 126 个交易日内，SPY 从当前价格起算的最大回撤 <= -10%。",
                "主分析只保留距高点 5% 以内的样本，模拟“在高位判断下一次大跌”的场景。",
                "技术指标基于日线/周线 OHLCV；周线指标按周五收盘对齐到下一交易日。",
                "模型使用 purged walk-forward：每年用此前数据训练，训练集末尾剔除 190 天，避免标签重叠。",
                "每个测试年按测试年内的预测分位取前 20% / 10% 作为预警，用于回顾性评估；实盘阈值需用训练集确定。",
                "样本小、标签重叠，胜率与 AUC 都是探索性结果，不是实盘承诺。",
            ],
        },
        "indicators": indicators,
        "indicatorsAll": indicators_all,
        "nearHighBaseRate": round(near_base_rate * 100, 1),
        "models": model_summary,
        "rules": rule_metrics,
        "stability": stability,
        "bestIndicator": best_indicator,
        "bestRule": best_rule,
        "yearly": yearly,
        "series": series,
    }

    (ROOT / "data" / "technical.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (ROOT / "assets" / "technical-data.js").write_text(
        "const TECHNICAL_DATA = " + json.dumps(out, ensure_ascii=False, indent=2) + ";\n",
        encoding="utf-8",
    )

    # ---------- 控制台摘要 ----------
    print("\n=== 单指标（按 lift 排序）===")
    for r in indicators[:12]:
        print(f"{r['name']:<28} precision={r['precision']}% lift={r['lift']} recall={r['recall']}% fpr={r['fpr']}% n={r['signalDays']}")

    print("\n=== 模型（purged walk-forward, 2020-2026）===")
    for name, m in model_summary.items():
        a = m["top20"]
        b = m["top10"]
        print(
            f"{name:<12} top20: 胜率={a['precision']}% CI={a['precisionCI']} AUC={a['auc']} "
            f"召回={a['recall']}% FPR={a['fpr']}% | top10: 胜率={b['precision']}% AUC={b['auc']} 召回={b['recall']}%"
        )
    print("\n=== 稳定性 ===")
    print(stability)
    print("\n=== 规则基线 ===")
    for name, m in rule_metrics.items():
        print(f"{name:<20} 胜率={m['precision']}% 召回={m['recall']}% FPR={m['fpr']}% 预警率={m['alertRate']}%")


if __name__ == "__main__":
    main()
