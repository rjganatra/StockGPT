from pathlib import Path
import pandas as pd
import numpy as np

SCAN_FILE = Path("data/scans/latest_scan.csv")
PERF_FILE = Path("data/performance/signal_performance.csv")
OUT_SUMMARY = Path("data/performance/combo_signal_performance.csv")
OUT_MEMBERS = Path("data/performance/combo_signal_members.csv")


def num(series, default=0):
    return pd.to_numeric(series, errors="coerce").fillna(default)


def text(series):
    return series.astype(str).fillna("")


def ensure_col(df, col, default=0):
    if col not in df.columns:
        df[col] = default


def add_combo(rows, members, combo_id, combo_name, description, data):
    count = len(data)

    if count == 0:
        rows.append({
            "combo_id": combo_id,
            "combo_name": combo_name,
            "description": description,
            "current_matches": 0,
            "avg_final_conviction": 0,
            "avg_range_score": 0,
            "avg_rsi": 0,
            "avg_risk_penalty": 0,
            "avg_return_1m": 0,
            "avg_return_3m": 0,
            "positive_1m_rate": 0,
            "positive_3m_rate": 0,
            "top_symbols": "",
            "interpretation": "No current matches in latest scan.",
        })
        return

    final_score = num(data.get("final_conviction_score", pd.Series([0] * count)))
    range_score = num(data.get("range_score", pd.Series([0] * count)))
    rsi = num(data.get("rsi", pd.Series([0] * count)))
    risk = num(data.get("risk_penalty", pd.Series([0] * count)))
    ret_1m = num(data.get("return_1m", pd.Series([0] * count)))
    ret_3m = num(data.get("return_3m", pd.Series([0] * count)))

    top = data.copy()
    top["_sort_score"] = final_score + (range_score * 0.25) - risk
    top = top.sort_values("_sort_score", ascending=False)

    top_symbols = ", ".join(top["symbol"].astype(str).head(8).tolist())

    positive_1m = float((ret_1m > 0).mean() * 100) if count else 0
    positive_3m = float((ret_3m > 0).mean() * 100) if count else 0

    avg_score = float(final_score.mean())
    avg_range = float(range_score.mean())
    avg_risk = float(risk.mean())

    if avg_score >= 60 and avg_risk <= 12:
        interpretation = "Strong quality setup with controlled risk."
    elif avg_range >= 65 and avg_risk <= 18:
        interpretation = "Range setup is strong; confirm support/resistance before entry."
    elif avg_risk >= 18:
        interpretation = "Caution: elevated risk even if signal looks attractive."
    elif count < 5:
        interpretation = "Small sample. Treat as watchlist, not a reliable signal."
    else:
        interpretation = "Moderate setup. Use as filter, not standalone decision."

    rows.append({
        "combo_id": combo_id,
        "combo_name": combo_name,
        "description": description,
        "current_matches": count,
        "avg_final_conviction": round(avg_score, 2),
        "avg_range_score": round(avg_range, 2),
        "avg_rsi": round(float(rsi.mean()), 2),
        "avg_risk_penalty": round(avg_risk, 2),
        "avg_return_1m": round(float(ret_1m.mean()), 2),
        "avg_return_3m": round(float(ret_3m.mean()), 2),
        "positive_1m_rate": round(positive_1m, 2),
        "positive_3m_rate": round(positive_3m, 2),
        "top_symbols": top_symbols,
        "interpretation": interpretation,
    })

    for _, row in top.head(50).iterrows():
        members.append({
            "combo_id": combo_id,
            "combo_name": combo_name,
            "symbol": row.get("symbol", ""),
            "current_price": row.get("current_price", 0),
            "final_conviction_score": row.get("final_conviction_score", 0),
            "score_band": row.get("score_band", ""),
            "range_status": row.get("range_status", ""),
            "range_score": row.get("range_score", 0),
            "rsi": row.get("rsi", 0),
            "trend": row.get("trend", ""),
            "risk_penalty": row.get("risk_penalty", 0),
            "distance_pct": row.get("distance_pct", 0),
            "distance_from_high_pct": row.get("distance_from_high_pct", 0),
            "return_1m": row.get("return_1m", 0),
            "return_3m": row.get("return_3m", 0),
            "sector": row.get("sector", ""),
            "industry": row.get("industry", ""),
            "data_completeness_status": row.get("data_completeness_status", ""),
        })


def build_combo_performance():
    if not SCAN_FILE.exists():
        raise FileNotFoundError(f"{SCAN_FILE} not found")

    df = pd.read_csv(SCAN_FILE, low_memory=False)

    if "symbol" not in df.columns:
        raise RuntimeError("latest_scan missing symbol column")

    for col in [
        "current_price",
        "final_conviction_score",
        "range_score",
        "rsi",
        "risk_penalty",
        "distance_pct",
        "distance_from_high_pct",
        "return_1m",
        "return_3m",
        "technical_score",
        "active_fundamental_score",
        "sector_adjusted_fundamental_score",
        "relative_strength_score",
    ]:
        ensure_col(df, col, 0)
        df[col] = num(df[col])

    for col in [
        "trend",
        "score_band",
        "range_status",
        "risk_reasons",
        "reasons",
        "sector",
        "industry",
        "data_completeness_status",
        "final_conviction_score_source",
    ]:
        ensure_col(df, col, "")
        df[col] = text(df[col])

    lower_reasons = (df["reasons"] + " " + df["risk_reasons"]).str.lower()
    range_status = df["range_status"].str.lower()
    trend = df["trend"].str.lower()
    band = df["score_band"].str.lower()

    near_52w_low = df["distance_pct"] <= 15
    near_52w_high = df["distance_from_high_pct"] <= 15
    bearish = trend.str.contains("bearish|down", na=False) | lower_reasons.str.contains("below 200 dma|bearish", na=False)
    bullish_or_stable = trend.str.contains("bullish|up|stable", na=False) | lower_reasons.str.contains("stable|watchable", na=False)
    strong_rsi = df["rsi"].between(35, 55)
    oversold_rsi = df["rsi"] < 35
    hot_rsi = df["rsi"] >= 65
    high_conviction = df["final_conviction_score"] >= 60
    medium_conviction = df["final_conviction_score"] >= 40
    low_risk = df["risk_penalty"] <= 10
    controlled_risk = df["risk_penalty"] <= 18
    high_risk = df["risk_penalty"] >= 18
    range_accumulation = range_status.str.contains("accumulation|lower|support", na=False)
    range_strong = df["range_score"] >= 65
    range_profit_zone = range_status.str.contains("profit|upper|resistance|booking", na=False) | near_52w_high | hot_rsi
    quality = (df["active_fundamental_score"] >= 50) | (df["sector_adjusted_fundamental_score"] >= 55)
    missing_fund = df["data_completeness_status"].str.contains("fundamentals missing", case=False, na=False)
    fallback_score = df["final_conviction_score_source"].str.contains("fallback", case=False, na=False)

    combos = [
        (
            "52w_low_bearish_strong_rsi",
            "52W Low + Bearish + Watchable RSI",
            "Near 52W low, bearish/weak trend, but RSI is not crashing.",
            near_52w_low & bearish & strong_rsi,
        ),
        (
            "52w_low_accumulation_controlled_risk",
            "52W Low + Accumulation + Controlled Risk",
            "Near 52W low, range accumulation zone, and risk penalty not excessive.",
            near_52w_low & range_accumulation & controlled_risk,
        ),
        (
            "range_accumulation_low_risk",
            "Range Accumulation + Low Risk",
            "Range accumulation candidates where risk penalty is low.",
            range_accumulation & range_strong & low_risk,
        ),
        (
            "range_accumulation_watchable_rsi",
            "Range Accumulation + Watchable RSI",
            "Range accumulation candidates with RSI in a playable zone.",
            range_accumulation & strong_rsi & controlled_risk,
        ),
        (
            "high_conviction_quality",
            "High Conviction + Quality",
            "High conviction candidates that also pass active/sector-adjusted quality.",
            high_conviction & quality,
        ),
        (
            "high_conviction_low_risk",
            "High Conviction + Low Risk",
            "High conviction names with controlled risk.",
            high_conviction & low_risk,
        ),
        (
            "medium_conviction_range_strong",
            "Medium Conviction + Strong Range",
            "Names where final score is not top-tier but range quality is strong.",
            medium_conviction & range_strong & controlled_risk,
        ),
        (
            "fallback_range_opportunity",
            "Fallback Score + Range Opportunity",
            "Names where fundamentals are missing but technical/range signal is still meaningful.",
            missing_fund & fallback_score & range_strong & controlled_risk,
        ),
        (
            "profit_booking_hot_zone",
            "Profit Booking / Hot Zone",
            "Names near upper range or heated RSI.",
            range_profit_zone,
        ),
        (
            "avoid_high_risk_weak",
            "Avoid: High Risk + Weak Score",
            "High risk names with weak conviction.",
            high_risk & (df["final_conviction_score"] < 30),
        ),
        (
            "near_high_quality_momentum",
            "Near High + Quality Momentum",
            "Near 52W high with decent quality and controlled risk.",
            near_52w_high & quality & controlled_risk,
        ),
        (
            "oversold_but_risky",
            "Oversold but Risky",
            "Oversold RSI but risk is elevated. Useful as caution list.",
            oversold_rsi & high_risk,
        ),
    ]

    rows = []
    members = []

    for combo_id, combo_name, description, mask in combos:
        add_combo(rows, members, combo_id, combo_name, description, df[mask].copy())

    OUT_SUMMARY.parent.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(rows).to_csv(OUT_SUMMARY, index=False)
    pd.DataFrame(members).to_csv(OUT_MEMBERS, index=False)

    print(f"✅ Combo signal performance written: {OUT_SUMMARY}")
    print(f"✅ Combo signal members written: {OUT_MEMBERS}")
    print(f"Combos: {len(rows)}")
    print(pd.DataFrame(rows)[["combo_id", "current_matches", "avg_final_conviction", "avg_range_score", "positive_1m_rate"]].to_string(index=False))


if __name__ == "__main__":
    build_combo_performance()
