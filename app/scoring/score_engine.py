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

    df["symbol"] = (
        df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

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

    right = right.drop(
        columns=overlapping_cols,
        errors="ignore"
    )

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

    # =========================
    # TREND QUALITY â 30
    # =========================

    if sma50 > 0 and current_price > sma50:
        score += 15
        reasons.append("Above 50 DMA")

    if sma200 > 0 and current_price > sma200:
        score += 15
        reasons.append("Above 200 DMA")

    # =========================
    # MOMENTUM HEALTH â 25
    # =========================

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
        score += 7
        reasons.append("Strong but overbought RSI")
    elif rsi < 30:
        score += 4
        reasons.append("Oversold RSI")

    # =========================
    # PRICE LOCATION â 20
    # =========================

    if distance_from_high_pct <= 10 and rsi >= 50:
        score += 10
        reasons.append("Near 52W high momentum")

    if distance_pct <= 10 and rsi >= 30:
        score += 8
        reasons.append("Near 52W low with stable RSI")
    elif distance_pct <= 25:
        score += 5
        reasons.append("Near 52W low zone")

    # =========================
    # VOLUME CONFIRMATION â 20
    # =========================

    if volume_ratio >= 2:
        score += 15
        reasons.append("Strong volume expansion")
    elif volume_ratio >= 1.3:
        score += 10
        reasons.append("Volume expansion")
    elif volume_ratio >= 1:
        score += 5
        reasons.append("Normal volume support")

    # =========================
    # DAILY CONFIRMATION â 5
    # =========================

    if day_change_pct > 0:
        score += 5
        reasons.append("Positive day move")

    score = max(0, min(100, score))

    return pd.Series({
        "technical_score": round(score, 2),
        "technical_reasons": ", ".join(dict.fromkeys(reasons))
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

    debt_to_equity = num(row.get("debt_to_equity"), None)
    net_profit_margin = num(row.get("net_profit_margin"), None)
    earnings_growth = num(row.get("earnings_growth"), None)
    revenue_growth = num(row.get("revenue_growth"), None)
    operating_cashflow_cr = num(row.get("operating_cashflow_cr"), None)
    free_cashflow_cr = num(row.get("free_cashflow_cr"), None)
    fundamental_risk_penalty = num(row.get("fundamental_risk_penalty"), 0)

    # =========================
    # TECHNICAL RISK
    # =========================

    if sma200 > 0 and current_price < sma200:
        penalty += 8
        risks.append("Below 200 DMA")

    if rsi < 25:
        penalty += 8
        risks.append("Extreme RSI weakness")

    if day_change_pct < -5:
        penalty += 5
        risks.append("Sharp daily fall")

    if distance_from_high_pct > 65:
        penalty += 5
        risks.append("Far from 52W high")

    if volume_ratio < 0.5:
        penalty += 3
        risks.append("Low volume participation")

    # =========================
    # FUNDAMENTAL RISK
    # =========================

    if debt_to_equity is not None and debt_to_equity > 200:
        penalty += 8
        risks.append("Very high debt")

    if net_profit_margin is not None and net_profit_margin < 0:
        penalty += 8
        risks.append("Negative net margin")

    if revenue_growth is not None and revenue_growth < -15:
        penalty += 5
        risks.append("Revenue contraction")

    if earnings_growth is not None and earnings_growth < -15:
        penalty += 7
        risks.append("Earnings contraction")

    if operating_cashflow_cr is not None and operating_cashflow_cr < 0:
        penalty += 5
        risks.append("Negative operating cash flow")

    if free_cashflow_cr is not None and free_cashflow_cr < 0:
        penalty += 4
        risks.append("Negative free cash flow")

    # Carry a portion of the fundamental model's own risk penalty.
    penalty += min(fundamental_risk_penalty * 0.5, 10)

    penalty = max(0, min(50, penalty))

    return pd.Series({
        "risk_penalty": round(penalty, 2),
        "risk_reasons": ", ".join(dict.fromkeys(risks))
    })


# =========================
# LOAD LATEST SCAN
# =========================

df = pd.read_csv(SCAN_FILE)
df = clean_symbol_column(df)
df = df.loc[:, ~df.columns.duplicated()]

# =========================
# BASE COLUMN SAFETY
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

technical_df = df.apply(
    calculate_technical_score,
    axis=1
)

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

# v3 sector-adjusted fallback:
# If v3 fundamentals exist, use sector_adjusted_fundamental_score.
# If not, safely fall back to plain fundamental_score.
if "sector_adjusted_fundamental_score" not in df.columns:
    df["sector_adjusted_fundamental_score"] = df["fundamental_score"]

df["sector_adjusted_fundamental_score"] = pd.to_numeric(
    df["sector_adjusted_fundamental_score"],
    errors="coerce"
).fillna(df["fundamental_score"])

df["active_fundamental_score"] = df["sector_adjusted_fundamental_score"]

# Ensure component columns exist
fundamental_component_cols = [
    "sector_bucket",
    "profitability_score",
    "growth_score",
    "balance_sheet_score",
    "cashflow_score",
    "valuation_score",
    "fundamental_risk_penalty",
    "sector_fundamental_adjustment",
    "sector_adjusted_fundamental_score",
    "active_fundamental_score"
]

for col in fundamental_component_cols:
    if col not in df.columns:
        df[col] = "Unknown" if col == "sector_bucket" else 0

    if col != "sector_bucket":
        df[col] = pd.to_numeric(
            df[col],
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
# NUMERIC CLEANUP
# =========================

numeric_needed = [
    "technical_score",
    "fundamental_score",
    "sector_adjusted_fundamental_score",
    "active_fundamental_score",
    "relative_strength_score",
    "current_price",
    "rsi",
    "sma50",
    "sma200",
    "volume_ratio",
    "distance_pct",
    "distance_from_high_pct",
    "day_change_pct",
    "debt_to_equity",
    "net_profit_margin",
    "earnings_growth",
    "revenue_growth",
    "operating_cashflow_cr",
    "free_cashflow_cr"
]

for col in numeric_needed:
    if col not in df.columns:
        df[col] = 0

    df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)

# =========================
# SECTOR SCORE
# =========================

sector_base = df.groupby("sector", dropna=False).agg(
    sector_avg_technical=("technical_score", "mean"),
    sector_avg_relative=("relative_strength_score", "mean"),
    sector_avg_fundamental=("active_fundamental_score", "mean")
).reset_index()

sector_base["sector_score"] = (
    sector_base["sector_avg_technical"] * 0.35
    +
    sector_base["sector_avg_relative"] * 0.35
    +
    sector_base["sector_avg_fundamental"] * 0.30
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

risk_df = df.apply(
    calculate_risk_penalty,
    axis=1
)

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
# FINAL CONVICTION SCORE V3
# =========================

df["final_conviction_score"] = (
    df["technical_score"].fillna(0) * 0.25
    +
    df["active_fundamental_score"].fillna(0) * 0.35
    +
    df["relative_strength_score"].fillna(0) * 0.25
    +
    df["sector_score"].fillna(0) * 0.15
    -
    df["risk_penalty"].fillna(0)
)

df["final_conviction_score"] = (
    df["final_conviction_score"]
    .clip(0, 100)
    .round(2)
)


def classify_score(score):
    try:
        score = float(score)
    except Exception:
        return "Unknown"

    if score >= 75:
        return "A+ High Conviction"
    elif score >= 65:
        return "A Strong"
    elif score >= 55:
        return "B Watchlist"
    elif score >= 45:
        return "C Neutral"
    elif score >= 35:
        return "D Weak"

    return "E Avoid"


df["score_band"] = df["final_conviction_score"].apply(classify_score)

# Backward compatibility for dashboard
df["score"] = df["final_conviction_score"]

df = df.sort_values(
    "final_conviction_score",
    ascending=False
)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"Score engine v3 updated latest_scan.csv: {len(df)} rows")
print("Final model uses active_fundamental_score = sector_adjusted_fundamental_score")
