import pandas as pd
from pathlib import Path

INPUT_FILE = "data/fundamentals/fundamentals.csv"
OUTPUT_FILE = "data/fundamentals/fundamental_scores.csv"

Path("data/fundamentals").mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_FILE)


def clean_num(value):
    try:
        if pd.isna(value):
            return None

        return float(value)

    except Exception:
        return None


def score_row(row):
    score = 0
    reasons = []
    risk_flags = []

    roe = clean_num(row.get("roe"))
    roa = clean_num(row.get("roa"))
    debt_to_equity = clean_num(row.get("debt_to_equity"))
    operating_margin = clean_num(row.get("operating_margin"))
    net_profit_margin = clean_num(row.get("net_profit_margin"))
    revenue_growth = clean_num(row.get("revenue_growth"))
    earnings_growth = clean_num(row.get("earnings_growth"))
    operating_cashflow = clean_num(row.get("operating_cashflow"))
    free_cashflow = clean_num(row.get("free_cashflow"))
    price_to_book = clean_num(row.get("price_to_book"))
    trailing_pe = clean_num(row.get("trailing_pe"))
    current_ratio = clean_num(row.get("current_ratio"))

    # =========================
    # PROFITABILITY — 25
    # =========================

    if roe is not None:
        if roe >= 20:
            score += 12
            reasons.append("Strong ROE")
        elif roe >= 15:
            score += 9
            reasons.append("Good ROE")
        elif roe >= 10:
            score += 5
            reasons.append("Moderate ROE")
        elif roe < 5:
            risk_flags.append("Weak ROE")

    if roa is not None:
        if roa >= 10:
            score += 6
            reasons.append("Strong ROA")
        elif roa >= 5:
            score += 3
            reasons.append("Moderate ROA")

    if net_profit_margin is not None:
        if net_profit_margin >= 15:
            score += 7
            reasons.append("Strong net margin")
        elif net_profit_margin >= 8:
            score += 4
            reasons.append("Healthy net margin")
        elif net_profit_margin < 3:
            risk_flags.append("Low net margin")

    # =========================
    # GROWTH — 20
    # =========================

    if revenue_growth is not None:
        if revenue_growth >= 20:
            score += 10
            reasons.append("High revenue growth")
        elif revenue_growth >= 10:
            score += 7
            reasons.append("Good revenue growth")
        elif revenue_growth >= 5:
            score += 4
            reasons.append("Moderate revenue growth")
        elif revenue_growth < 0:
            risk_flags.append("Negative revenue growth")

    if earnings_growth is not None:
        if earnings_growth >= 20:
            score += 10
            reasons.append("High earnings growth")
        elif earnings_growth >= 10:
            score += 7
            reasons.append("Good earnings growth")
        elif earnings_growth >= 5:
            score += 4
            reasons.append("Moderate earnings growth")
        elif earnings_growth < 0:
            risk_flags.append("Negative earnings growth")

    # =========================
    # BALANCE SHEET — 20
    # =========================

    if debt_to_equity is not None:
        if debt_to_equity <= 25:
            score += 10
            reasons.append("Low debt")
        elif debt_to_equity <= 75:
            score += 6
            reasons.append("Manageable debt")
        elif debt_to_equity > 150:
            risk_flags.append("High debt")

    if current_ratio is not None:
        if current_ratio >= 1.5:
            score += 5
            reasons.append("Healthy current ratio")
        elif current_ratio >= 1:
            score += 3
            reasons.append("Acceptable current ratio")
        elif current_ratio < 1:
            risk_flags.append("Weak current ratio")

    if price_to_book is not None:
        if price_to_book <= 3:
            score += 5
            reasons.append("Reasonable price-to-book")
        elif price_to_book > 10:
            risk_flags.append("Expensive price-to-book")

    # =========================
    # CASH FLOW — 20
    # =========================

    if operating_cashflow is not None:
        if operating_cashflow > 0:
            score += 10
            reasons.append("Positive operating cash flow")
        else:
            risk_flags.append("Negative operating cash flow")

    if free_cashflow is not None:
        if free_cashflow > 0:
            score += 10
            reasons.append("Positive free cash flow")
        else:
            risk_flags.append("Negative free cash flow")

    # =========================
    # VALUATION DISCIPLINE — 15
    # =========================

    if trailing_pe is not None:
        if 0 < trailing_pe <= 25:
            score += 8
            reasons.append("Reasonable PE")
        elif 25 < trailing_pe <= 50:
            score += 4
            reasons.append("Moderate PE")
        elif trailing_pe > 80:
            risk_flags.append("Very high PE")

    if operating_margin is not None:
        if operating_margin >= 20:
            score += 7
            reasons.append("Strong operating margin")
        elif operating_margin >= 10:
            score += 4
            reasons.append("Healthy operating margin")
        elif operating_margin < 5:
            risk_flags.append("Weak operating margin")

    # =========================
    # PENALTIES
    # =========================

    penalty = 0

    if debt_to_equity is not None and debt_to_equity > 200:
        penalty += 10

    if revenue_growth is not None and revenue_growth < -10:
        penalty += 8

    if earnings_growth is not None and earnings_growth < -10:
        penalty += 8

    if operating_cashflow is not None and operating_cashflow < 0:
        penalty += 7

    if net_profit_margin is not None and net_profit_margin < 0:
        penalty += 10

    final_score = max(0, min(100, score - penalty))

    return pd.Series({
        "fundamental_score": round(final_score, 2),
        "fundamental_reasons": ", ".join(reasons),
        "fundamental_risks": ", ".join(risk_flags),
        "fundamental_penalty": penalty
    })


score_df = df.apply(score_row, axis=1)

result = pd.concat([df, score_df], axis=1)

result = result.sort_values(
    "fundamental_score",
    ascending=False
)

result.to_csv(OUTPUT_FILE, index=False)

print(f"Fundamental scores saved: {len(result)} rows")
