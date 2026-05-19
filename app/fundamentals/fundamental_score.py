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


def clamp(value, minimum=0, maximum=100):
    return max(minimum, min(maximum, value))


def score_profitability(row):
    score = 0
    reasons = []
    risks = []

    roe = clean_num(row.get("roe"))
    roa = clean_num(row.get("roa"))
    operating_margin = clean_num(row.get("operating_margin"))
    net_profit_margin = clean_num(row.get("net_profit_margin"))

    # ROE — max 8
    if roe is not None:
        if roe >= 25:
            score += 8
            reasons.append("Excellent ROE")
        elif roe >= 18:
            score += 6
            reasons.append("Strong ROE")
        elif roe >= 12:
            score += 4
            reasons.append("Decent ROE")
        elif roe >= 8:
            score += 2
            reasons.append("Moderate ROE")
        elif roe < 5:
            risks.append("Weak ROE")

    # ROA — max 5
    if roa is not None:
        if roa >= 12:
            score += 5
            reasons.append("Excellent ROA")
        elif roa >= 8:
            score += 4
            reasons.append("Strong ROA")
        elif roa >= 5:
            score += 2
            reasons.append("Moderate ROA")
        elif roa < 2:
            risks.append("Weak ROA")

    # Operating margin — max 6
    if operating_margin is not None:
        if operating_margin >= 25:
            score += 6
            reasons.append("Excellent operating margin")
        elif operating_margin >= 18:
            score += 5
            reasons.append("Strong operating margin")
        elif operating_margin >= 10:
            score += 3
            reasons.append("Healthy operating margin")
        elif operating_margin < 5:
            risks.append("Weak operating margin")

    # Net margin — max 6
    if net_profit_margin is not None:
        if net_profit_margin >= 18:
            score += 6
            reasons.append("Excellent net margin")
        elif net_profit_margin >= 12:
            score += 5
            reasons.append("Strong net margin")
        elif net_profit_margin >= 6:
            score += 3
            reasons.append("Healthy net margin")
        elif net_profit_margin < 2:
            risks.append("Weak net margin")

    return clamp(score, 0, 25), reasons, risks


def score_growth(row):
    score = 0
    reasons = []
    risks = []

    revenue_growth = clean_num(row.get("revenue_growth"))
    earnings_growth = clean_num(row.get("earnings_growth"))

    # Revenue growth — max 10
    if revenue_growth is not None:
        if revenue_growth >= 25:
            score += 10
            reasons.append("Excellent revenue growth")
        elif revenue_growth >= 15:
            score += 8
            reasons.append("Strong revenue growth")
        elif revenue_growth >= 8:
            score += 5
            reasons.append("Healthy revenue growth")
        elif revenue_growth >= 3:
            score += 2
            reasons.append("Moderate revenue growth")
        elif revenue_growth < 0:
            risks.append("Negative revenue growth")

    # Earnings growth — max 10
    if earnings_growth is not None:
        if earnings_growth >= 25:
            score += 10
            reasons.append("Excellent earnings growth")
        elif earnings_growth >= 15:
            score += 8
            reasons.append("Strong earnings growth")
        elif earnings_growth >= 8:
            score += 5
            reasons.append("Healthy earnings growth")
        elif earnings_growth >= 3:
            score += 2
            reasons.append("Moderate earnings growth")
        elif earnings_growth < 0:
            risks.append("Negative earnings growth")

    return clamp(score, 0, 20), reasons, risks


def score_balance_sheet(row):
    score = 0
    reasons = []
    risks = []

    debt_to_equity = clean_num(row.get("debt_to_equity"))
    current_ratio = clean_num(row.get("current_ratio"))
    quick_ratio = clean_num(row.get("quick_ratio"))
    total_cash_cr = clean_num(row.get("total_cash_cr"))
    total_debt_cr = clean_num(row.get("total_debt_cr"))

    # Debt to equity — max 9
    if debt_to_equity is not None:
        if debt_to_equity <= 20:
            score += 9
            reasons.append("Very low debt")
        elif debt_to_equity <= 50:
            score += 7
            reasons.append("Low debt")
        elif debt_to_equity <= 100:
            score += 4
            reasons.append("Manageable debt")
        elif debt_to_equity <= 150:
            score += 2
            reasons.append("Elevated debt")
        elif debt_to_equity > 150:
            risks.append("High debt")

    # Current ratio — max 5
    if current_ratio is not None:
        if current_ratio >= 2:
            score += 5
            reasons.append("Strong current ratio")
        elif current_ratio >= 1.5:
            score += 4
            reasons.append("Healthy current ratio")
        elif current_ratio >= 1:
            score += 2
            reasons.append("Acceptable current ratio")
        elif current_ratio < 1:
            risks.append("Weak current ratio")

    # Quick ratio — max 3
    if quick_ratio is not None:
        if quick_ratio >= 1.5:
            score += 3
            reasons.append("Strong quick ratio")
        elif quick_ratio >= 1:
            score += 2
            reasons.append("Acceptable quick ratio")
        elif quick_ratio < 0.7:
            risks.append("Weak quick ratio")

    # Cash vs debt — max 3
    if total_cash_cr is not None and total_debt_cr is not None:
        if total_debt_cr <= 0 and total_cash_cr > 0:
            score += 3
            reasons.append("Net cash position")
        elif total_debt_cr > 0:
            cash_debt_ratio = total_cash_cr / total_debt_cr

            if cash_debt_ratio >= 1:
                score += 3
                reasons.append("Cash covers debt")
            elif cash_debt_ratio >= 0.5:
                score += 2
                reasons.append("Reasonable cash coverage")
            elif cash_debt_ratio < 0.2:
                risks.append("Low cash coverage")

    return clamp(score, 0, 20), reasons, risks


def score_cashflow(row):
    score = 0
    reasons = []
    risks = []

    operating_cashflow_cr = clean_num(row.get("operating_cashflow_cr"))
    free_cashflow_cr = clean_num(row.get("free_cashflow_cr"))
    net_profit_margin = clean_num(row.get("net_profit_margin"))

    # Operating cash flow — max 9
    if operating_cashflow_cr is not None:
        if operating_cashflow_cr > 0:
            score += 9
            reasons.append("Positive operating cash flow")
        elif operating_cashflow_cr < 0:
            risks.append("Negative operating cash flow")

    # Free cash flow — max 8
    if free_cashflow_cr is not None:
        if free_cashflow_cr > 0:
            score += 8
            reasons.append("Positive free cash flow")
        elif free_cashflow_cr < 0:
            risks.append("Negative free cash flow")

    # Cashflow + profitability confirmation — max 3
    if operating_cashflow_cr is not None and net_profit_margin is not None:
        if operating_cashflow_cr > 0 and net_profit_margin > 8:
            score += 3
            reasons.append("Cash flow supports profitability")
        elif operating_cashflow_cr < 0 and net_profit_margin > 10:
            risks.append("Profit not backed by cash flow")

    return clamp(score, 0, 20), reasons, risks


def score_valuation(row):
    score = 0
    reasons = []
    risks = []

    trailing_pe = clean_num(row.get("trailing_pe"))
    forward_pe = clean_num(row.get("forward_pe"))
    price_to_book = clean_num(row.get("price_to_book"))
    dividend_yield = clean_num(row.get("dividend_yield"))

    # PE — max 6
    if trailing_pe is not None:
        if 0 < trailing_pe <= 20:
            score += 6
            reasons.append("Attractive PE")
        elif trailing_pe <= 35:
            score += 4
            reasons.append("Reasonable PE")
        elif trailing_pe <= 60:
            score += 2
            reasons.append("Elevated PE")
        elif trailing_pe > 80:
            risks.append("Very high PE")

    # Forward PE confirmation — max 3
    if trailing_pe is not None and forward_pe is not None:
        if 0 < forward_pe < trailing_pe:
            score += 3
            reasons.append("Forward PE improving")
        elif forward_pe > trailing_pe * 1.3:
            risks.append("Forward PE deterioration")

    # Price to book — max 4
    if price_to_book is not None:
        if 0 < price_to_book <= 3:
            score += 4
            reasons.append("Reasonable price-to-book")
        elif price_to_book <= 6:
            score += 2
            reasons.append("Moderate price-to-book")
        elif price_to_book > 10:
            risks.append("Expensive price-to-book")

    # Dividend yield — max 2
    if dividend_yield is not None:
        if dividend_yield >= 2:
            score += 2
            reasons.append("Healthy dividend yield")
        elif dividend_yield >= 1:
            score += 1
            reasons.append("Some dividend support")
        elif dividend_yield > 15:
            risks.append("Suspiciously high dividend yield")

    return clamp(score, 0, 15), reasons, risks


def score_row(row):
    profitability_score, profitability_reasons, profitability_risks = score_profitability(row)
    growth_score, growth_reasons, growth_risks = score_growth(row)
    balance_sheet_score, balance_sheet_reasons, balance_sheet_risks = score_balance_sheet(row)
    cashflow_score, cashflow_reasons, cashflow_risks = score_cashflow(row)
    valuation_score, valuation_reasons, valuation_risks = score_valuation(row)

    all_reasons = (
        profitability_reasons
        + growth_reasons
        + balance_sheet_reasons
        + cashflow_reasons
        + valuation_reasons
    )

    all_risks = (
        profitability_risks
        + growth_risks
        + balance_sheet_risks
        + cashflow_risks
        + valuation_risks
    )

    penalty = 0

    roe = clean_num(row.get("roe"))
    debt_to_equity = clean_num(row.get("debt_to_equity"))
    net_profit_margin = clean_num(row.get("net_profit_margin"))
    revenue_growth = clean_num(row.get("revenue_growth"))
    earnings_growth = clean_num(row.get("earnings_growth"))
    operating_cashflow_cr = clean_num(row.get("operating_cashflow_cr"))
    free_cashflow_cr = clean_num(row.get("free_cashflow_cr"))
    trailing_pe = clean_num(row.get("trailing_pe"))
    dividend_yield = clean_num(row.get("dividend_yield"))

    if roe is not None and roe < 5:
        penalty += 5

    if debt_to_equity is not None and debt_to_equity > 200:
        penalty += 8

    if net_profit_margin is not None and net_profit_margin < 0:
        penalty += 10

    if revenue_growth is not None and revenue_growth < -10:
        penalty += 6

    if earnings_growth is not None and earnings_growth < -10:
        penalty += 8

    if operating_cashflow_cr is not None and operating_cashflow_cr < 0:
        penalty += 6

    if free_cashflow_cr is not None and free_cashflow_cr < 0:
        penalty += 5

    if trailing_pe is not None and trailing_pe > 100:
        penalty += 5

    if dividend_yield is not None and dividend_yield > 20:
        penalty += 5
        all_risks.append("Abnormally high dividend yield")

    raw_score = (
        profitability_score
        + growth_score
        + balance_sheet_score
        + cashflow_score
        + valuation_score
    )

    fundamental_score = clamp(raw_score - penalty, 0, 100)

    return pd.Series({
        "profitability_score": round(profitability_score, 2),
        "growth_score": round(growth_score, 2),
        "balance_sheet_score": round(balance_sheet_score, 2),
        "cashflow_score": round(cashflow_score, 2),
        "valuation_score": round(valuation_score, 2),
        "fundamental_risk_penalty": round(penalty, 2),
        "fundamental_score": round(fundamental_score, 2),
        "fundamental_reasons": ", ".join(dict.fromkeys(all_reasons)),
        "fundamental_risks": ", ".join(dict.fromkeys(all_risks))
    })


score_df = df.apply(score_row, axis=1)

result = pd.concat([df, score_df], axis=1)

result = result.sort_values(
    "fundamental_score",
    ascending=False
)

result.to_csv(OUTPUT_FILE, index=False)

print(f"Fundamental scores saved: {len(result)} rows")
