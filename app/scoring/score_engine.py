import pandas as pd
from pathlib import Path

SCAN_FILE = "data/scans/latest_scan.csv"
FUNDAMENTALS_FILE = "data/fundamentals/fundamental_scores.csv"
RELATIVE_FILE = "data/scoring/relative_strength.csv"

OUTPUT_FILE = "data/scans/latest_scan.csv"


def num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_symbol_column(df):
    df = df.copy()

    if "symbol" not in df.columns:
        raise ValueError("symbol column missing")

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    df = df.drop_duplicates(subset=["symbol"])

    return df


def safe_merge(left, right, on="symbol"):
    left = left.copy()
    right = right.copy()

    left = left.loc[:, ~left.columns.duplicated()]
    right = right.loc[:, ~right.columns.duplicated()]

    if on not in left.columns:
        raise ValueError(f"{on} column missing from left dataframe")

    if on not in right.columns:
        raise ValueError(f"{on} column missing from right dataframe")

    if on == "symbol":
        left[on] = left[on].astype(str).str.upper().str.strip()
        right[on] = right[on].astype(str).str.upper().str.strip()
    else:
        left[on] = left[on].astype(str).str.strip()
        right[on] = right[on].astype(str).str.strip()

    right = right.drop_duplicates(subset=[on])

    overlapping_cols = [
        col for col in right.columns
        if col in left.columns and col != on
    ]

    right = right.drop(columns=overlapping_cols, errors="ignore")

    merged = left.merge(
        right,
        on=on,
        how="left"
    )

    merged = merged.loc[:, ~merged.columns.duplicated()]

    return merged


def calculate_technical_score(row):
    score = 0
    reasons = []

    current_price = num(row.get("current_price"))
    rsi = num(row.get("rsi"))
    sma50 = num(row.get("sma50"))
    sma200 = num(row.get("sma200"))
    volume_ratio = num(row.get("volume_ratio"))
    distance_pct = num(row.get("distance_pct"))
    distance_from_high_pct = num(row.get("distance_from_high_pct"))
    day_change_pct = num(row.get("day_change_pct"))

    if sma50 > 0 and current_price > sma50:
        score += 15
        reasons.append("Above 50 DMA")

    if sma200 > 0 and current_price > sma200:
        score += 15
        reasons.append("Above 200 DMA")

    if 50 <= rsi <= 70:
        score += 20
        reasons.append("Healthy RSI momentum")
    elif 45 <= rsi < 50:
        score += 12
        reasons.append("RSI recovering")
    elif 30 <= rsi < 45:
        score += 8
        reasons.append("Weak but watchable RSI")
    elif rsi > 70:
        score += 6
        reasons.append("Strong but overbought RSI")
    elif rsi < 30:
        score += 4
        reasons.append("Oversold RSI")

    if distance_pct <= 10 and rsi >= 30:
        score += 10
        reasons.append("Near 52W low with stable RSI")
    elif distance_pct <= 25:
        score += 6
        reasons.append("Near 52W low zone")

    if distance_from_high_pct <= 10 and rsi >= 50:
        score += 10
        reasons.append("Near 52W high momentum")

    if volume_ratio >= 2:
        score += 15
        reasons.append("Strong volume expansion")
    elif volume_ratio >= 1.3:
        score += 10
        reasons.append("Volume expansion")
    elif volume_ratio >= 1:
        score += 5
        reasons.append("Normal volume support")

    if day_change_pct > 0:
        score += 5
        reasons.append("Positive day move")

    score = max(0, min(100, score))

    return pd.Series({
        "technical_score": round(score, 2),
        "technical_reasons": ", ".join(reasons)
    })


def calculate_risk_penalty(row):
    penalty = 0
    risks = []

    current_price = num(row.get("current_price"))
    rsi = num(row.get("rsi"))
    sma200 = num(row.get("sma200"))
    distance_from_high_pct = num(row.get("distance_from_high_pct"))
    day_change_pct = num(row.get("day_change_pct"))
    volume_ratio = num(row.get("volume_ratio"))

    debt_to_equity = row.get("debt_to_equity")
    net_profit_margin = row.get("net_profit_margin")
    earnings_growth = row.get("earnings_growth")
    operating_cashflow = row.get("operating_cashflow")

    debt_to_equity = num(debt_to_equity, None) if debt_to_equity is not None else None
    net_profit_margin = num(net_profit_margin, None) if net_profit_margin is not None else None
    earnings_growth = num(earnings_growth, None) if earnings_growth is not None else None
    operating_cashflow = num(operating_cashflow, None) if operating_cashflow is not None else None

    if sma200 > 0 and current_price < sma200:
        penalty += 10
        risks.append("Below 200 DMA")

    if rsi < 25:
        penalty += 10
        risks.append("Extreme RSI weakness")

    if day_change_pct < -5:
        penalty += 5
        risks.append("Sharp daily fall")

    if distance_from_high_pct > 60:
        penalty += 5
        risks.append("Far from 52W high")

    if volume_ratio < 0.5:
        penalty += 3
        risks.append("Low volume participation")

    if debt_to_equity is not None and debt_to_equity > 200:
        penalty += 10
        risks.append("Very high debt")

    if net_profit_margin is not None and net_profit_margin < 0:
        penalty += 10
        risks.append("Negative net margin")

    if earnings_growth is not None and earnings_growth < -10:
        penalty += 7
        risks.append("Weak earnings growth")

    if operating_cashflow is not None and operating_cashflow < 0:
        penalty += 7
        risks.append("Negative operating cash flow")

    penalty = max(0, min(50, penalty))

    return pd.Series({
        "risk_penalty": round(penalty, 2),
        "risk_reasons": ", ".join(risks)
    })


df = pd.read_csv(SCAN_FILE)

df = clean_symbol_column(df)

df = df.loc[:, ~df.columns.duplicated()]

# =========================
# CLEAN BASE SCAN COLUMNS
# =========================

if "sector" not in df.columns:
    df["sector"] = "Unknown"

if "industry" not in df.columns:
    df["industry"] = "Unknown"

df["sector"] = df["sector"].fillna("Unknown").astype(str)
df["industry"] = df["industry"].fillna("Unknown").astype(str)

# =========================
# TECHNICAL SCORE
# =========================

technical_df = df.apply(calculate_technical_score, axis=1)

df = pd.concat(
    [
        df.reset_index(drop=True),
        technical_df.reset_index(drop=True)
    ],
    axis=1
)

df = df.loc[:, ~df.columns.duplicated()]

# =========================
# MERGE FUNDAMENTALS
# =========================

if Path(FUNDAMENTALS_FILE).exists():
    fundamentals = pd.read_csv(FUNDAMENTALS_FILE)

    if "symbol" in fundamentals.columns:
        fundamentals = clean_symbol_column(fundamentals)
        df = safe_merge(df, fundamentals, on="symbol")

if "fundamental_score" not in df.columns:
    df["fundamental_score"] = 0

df["fundamental_score"] = pd.to_numeric(
    df["fundamental_score"],
    errors="coerce"
).fillna(0)

# =========================
# MERGE RELATIVE STRENGTH
# =========================

if Path(RELATIVE_FILE).exists():
    relative = pd.read_csv(RELATIVE_FILE)

    if "symbol" in relative.columns:
        relative = clean_symbol_column(relative)
        df = safe_merge(df, relative, on="symbol")

if "relative_strength_score" not in df.columns:
    df["relative_strength_score"] = 0

df["relative_strength_score"] = pd.to_numeric(
    df["relative_strength_score"],
    errors="coerce"
).fillna(0)

# =========================
# SECTOR SCORE
# =========================

df["technical_score"] = pd.to_numeric(
    df["technical_score"],
    errors="coerce"
).fillna(0)

df["relative_strength_score"] = pd.to_numeric(
    df["relative_strength_score"],
    errors="coerce"
).fillna(0)

sector_base = df.groupby("sector", dropna=False).agg(
    sector_avg_technical=("technical_score", "mean"),
    sector_avg_relative=("relative_strength_score", "mean"),
    sector_avg_fundamental=("fundamental_score", "mean")
).reset_index()

sector_base["sector_score"] = (
    sector_base["sector_avg_technical"] * 0.40
    +
    sector_base["sector_avg_relative"] * 0.35
    +
    sector_base["sector_avg_fundamental"] * 0.25
)

sector_base["sector_score"] = sector_base["sector_score"].round(2)

df = safe_merge(
    df,
    sector_base[["sector", "sector_score"]],
    on="sector"
)

if "sector_score" not in df.columns:
    df["sector_score"] = 0

df["sector_score"] = pd.to_numeric(
    df["sector_score"],
    errors="coerce"
).fillna(0)

# =========================
# RISK PENALTY
# =========================

risk_df = df.apply(calculate_risk_penalty, axis=1)

df = pd.concat(
    [
        df.reset_index(drop=True),
        risk_df.reset_index(drop=True)
    ],
    axis=1
)

df = df.loc[:, ~df.columns.duplicated()]

if "risk_penalty" not in df.columns:
    df["risk_penalty"] = 0

df["risk_penalty"] = pd.to_numeric(
    df["risk_penalty"],
    errors="coerce"
).fillna(0)

# =========================
# FINAL CONVICTION SCORE
# =========================

df["final_conviction_score"] = (
    df["technical_score"].fillna(0) * 0.35
    +
    df["fundamental_score"].fillna(0) * 0.30
    +
    df["relative_strength_score"].fillna(0) * 0.20
    +
    df["sector_score"].fillna(0) * 0.15
    -
    df["risk_penalty"].fillna(0)
)

df["final_conviction_score"] = df["final_conviction_score"].clip(0, 100).round(2)

# Backward compatibility for dashboard
df["score"] = df["final_conviction_score"]

df = df.sort_values(
    "final_conviction_score",
    ascending=False
)

df.to_csv(OUTPUT_FILE, index=False)

print(f"Score engine updated latest_scan.csv: {len(df)} rows")
