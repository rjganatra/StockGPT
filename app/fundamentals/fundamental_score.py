import pandas as pd
from pathlib import Path

INPUT_FILE = "data/fundamentals/fundamentals.csv"
OUTPUT_FILE = "data/fundamentals/fundamental_scores.csv"

Path("data/fundamentals").mkdir(parents=True, exist_ok=True)

df = pd.read_csv(INPUT_FILE)


def n(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clamp(value, low=0, high=100):
    return max(low, min(high, value))


def txt(value):
    if pd.isna(value):
        return ""
    return str(value).lower().strip()


def bucket(row):
    text = f"{txt(row.get('sector_yf'))} {txt(row.get('industry_yf'))}"

    if "bank" in text:
        return "BANK"

    if any(x in text for x in ["nbfc", "finance", "financial", "insurance", "capital markets", "asset management", "credit"]):
        return "FINANCIAL"

    if any(x in text for x in ["software", "information technology", "technology", "semiconductor", "electronic", "computer"]):
        return "IT_TECH"

    if any(x in text for x in ["pharma", "healthcare", "hospital", "diagnostic", "biotech", "medical"]):
        return "PHARMA_HEALTHCARE"

    if any(x in text for x in ["fmcg", "food", "beverage", "household", "personal products", "consumer staples", "tobacco"]):
        return "FMCG_CONSUMER"

    if any(x in text for x in ["auto", "automobile", "tyre", "tire", "ancillaries"]):
        return "AUTO"

    if any(x in text for x in ["metal", "steel", "aluminium", "aluminum", "copper", "mining", "coal"]):
        return "METALS_MINING"

    if any(x in text for x in ["oil", "gas", "energy", "power", "utility", "utilities", "renewable", "electricity"]):
        return "ENERGY_UTILITIES"

    if any(x in text for x in ["capital goods", "engineering", "industrial", "machinery", "defence", "defense", "aerospace", "rail", "infrastructure"]):
        return "CAPITAL_GOODS_INFRA"

    if any(x in text for x in ["chemical", "fertilizer", "agrochemical", "paint"]):
        return "CHEMICALS"

    if any(x in text for x in ["cement", "real estate", "building material", "construction material"]):
        return "CEMENT_REALTY"

    if any(x in text for x in ["telecom", "communication"]):
        return "TELECOM"

    if any(x in text for x in ["retail", "textile", "apparel", "footwear", "jewellery", "jewelry", "consumer cyclical"]):
        return "CONSUMER_DISCRETIONARY"

    return "GENERAL"


def points(value, rules):
    value = n(value, None)

    if value is None:
        return 0

    for condition, score in rules:
        if condition(value):
            return score

    return 0


def risk_text(items):
    return ", ".join(dict.fromkeys([x for x in items if x]))


def score_row(row):
    reasons = []
    risks = []

    roe = n(row.get("roe"), None)
    roa = n(row.get("roa"), None)
    opm = n(row.get("operating_margin"), None)
    npm = n(row.get("net_profit_margin"), None)
    rev_g = n(row.get("revenue_growth"), None)
    earn_g = n(row.get("earnings_growth"), None)
    dte = n(row.get("debt_to_equity"), None)
    cr = n(row.get("current_ratio"), None)
    qr = n(row.get("quick_ratio"), None)
    cash = n(row.get("total_cash_cr"), None)
    debt = n(row.get("total_debt_cr"), None)
    ocf = n(row.get("operating_cashflow_cr"), None)
    fcf = n(row.get("free_cashflow_cr"), None)
    pe = n(row.get("trailing_pe"), None)
    fpe = n(row.get("forward_pe"), None)
    pb = n(row.get("price_to_book"), None)
    div = n(row.get("dividend_yield"), None)

    # =========================
    # BASE COMPONENT SCORES
    # =========================

    profitability_score = 0

    profitability_score += points(roe, [
        (lambda x: x >= 25, 8),
        (lambda x: x >= 18, 6),
        (lambda x: x >= 12, 4),
        (lambda x: x >= 8, 2)
    ])

    profitability_score += points(roa, [
        (lambda x: x >= 12, 5),
        (lambda x: x >= 8, 4),
        (lambda x: x >= 5, 2)
    ])

    profitability_score += points(opm, [
        (lambda x: x >= 25, 6),
        (lambda x: x >= 18, 5),
        (lambda x: x >= 10, 3)
    ])

    profitability_score += points(npm, [
        (lambda x: x >= 18, 6),
        (lambda x: x >= 12, 5),
        (lambda x: x >= 6, 3)
    ])

    profitability_score = clamp(profitability_score, 0, 25)

    if roe is not None and roe >= 18:
        reasons.append("Strong ROE")
    if opm is not None and opm >= 18:
        reasons.append("Strong operating margin")
    if npm is not None and npm < 0:
        risks.append("Negative net margin")

    growth_score = 0

    growth_score += points(rev_g, [
        (lambda x: x >= 25, 10),
        (lambda x: x >= 15, 8),
        (lambda x: x >= 8, 5),
        (lambda x: x >= 3, 2)
    ])

    growth_score += points(earn_g, [
        (lambda x: x >= 25, 10),
        (lambda x: x >= 15, 8),
        (lambda x: x >= 8, 5),
        (lambda x: x >= 3, 2)
    ])

    growth_score = clamp(growth_score, 0, 20)

    if rev_g is not None and rev_g >= 15:
        reasons.append("Strong revenue growth")
    if earn_g is not None and earn_g >= 15:
        reasons.append("Strong earnings growth")
    if rev_g is not None and rev_g < 0:
        risks.append("Negative revenue growth")
    if earn_g is not None and earn_g < 0:
        risks.append("Negative earnings growth")

    balance_sheet_score = 0

    balance_sheet_score += points(dte, [
        (lambda x: x <= 20, 9),
        (lambda x: x <= 50, 7),
        (lambda x: x <= 100, 4),
        (lambda x: x <= 150, 2)
    ])

    balance_sheet_score += points(cr, [
        (lambda x: x >= 2, 5),
        (lambda x: x >= 1.5, 4),
        (lambda x: x >= 1, 2)
    ])

    balance_sheet_score += points(qr, [
        (lambda x: x >= 1.5, 3),
        (lambda x: x >= 1, 2)
    ])

    if cash is not None and debt is not None:
        if debt <= 0 and cash > 0:
            balance_sheet_score += 3
            reasons.append("Net cash position")
        elif debt > 0:
            cash_debt = cash / debt

            if cash_debt >= 1:
                balance_sheet_score += 3
                reasons.append("Cash covers debt")
            elif cash_debt >= 0.5:
                balance_sheet_score += 2
                reasons.append("Reasonable cash coverage")

    balance_sheet_score = clamp(balance_sheet_score, 0, 20)

    if dte is not None and dte <= 50:
        reasons.append("Low debt")
    if dte is not None and dte > 200:
        risks.append("Very high debt")

    cashflow_score = 0

    if ocf is not None and ocf > 0:
        cashflow_score += 9
        reasons.append("Positive operating cash flow")
    elif ocf is not None and ocf < 0:
        risks.append("Negative operating cash flow")

    if fcf is not None and fcf > 0:
        cashflow_score += 8
        reasons.append("Positive free cash flow")
    elif fcf is not None and fcf < 0:
        risks.append("Negative free cash flow")

    if ocf is not None and npm is not None:
        if ocf > 0 and npm > 8:
            cashflow_score += 3
            reasons.append("Cash flow supports profitability")
        elif ocf < 0 and npm > 10:
            risks.append("Profit not backed by cash flow")

    cashflow_score = clamp(cashflow_score, 0, 20)

    valuation_score = 0

    valuation_score += points(pe, [
        (lambda x: 0 < x <= 20, 6),
        (lambda x: x <= 35, 4),
        (lambda x: x <= 60, 2)
    ])

    if pe is not None and fpe is not None:
        if 0 < fpe < pe:
            valuation_score += 3
            reasons.append("Forward PE improving")
        elif fpe > pe * 1.3:
            risks.append("Forward PE deterioration")

    valuation_score += points(pb, [
        (lambda x: 0 < x <= 3, 4),
        (lambda x: x <= 6, 2)
    ])

    valuation_score += points(div, [
        (lambda x: x >= 2, 2),
        (lambda x: x >= 1, 1)
    ])

    valuation_score = clamp(valuation_score, 0, 15)

    if pe is not None and pe > 80:
        risks.append("Very high PE")
    if pb is not None and pb > 10:
        risks.append("Expensive price-to-book")
    if div is not None and div > 20:
        risks.append("Abnormally high dividend yield")

    # =========================
    # BASE PENALTY
    # =========================

    penalty = 0

    if roe is not None and roe < 5:
        penalty += 5
    if dte is not None and dte > 200:
        penalty += 8
    if npm is not None and npm < 0:
        penalty += 10
    if rev_g is not None and rev_g < -10:
        penalty += 6
    if earn_g is not None and earn_g < -10:
        penalty += 8
    if ocf is not None and ocf < 0:
        penalty += 6
    if fcf is not None and fcf < 0:
        penalty += 5
    if pe is not None and pe > 100:
        penalty += 5
    if div is not None and div > 20:
        penalty += 5

    raw_score = (
        profitability_score
        + growth_score
        + balance_sheet_score
        + cashflow_score
        + valuation_score
    )

    fundamental_score = clamp(raw_score - penalty, 0, 100)

    # =========================
    # SECTOR ADJUSTMENT
    # =========================

    sector_bucket = bucket(row)
    adj = 0
    sector_reasons = []
    sector_risks = []

    if sector_bucket == "BANK":
        if dte is not None and dte > 200:
            adj += 6
            sector_reasons.append("Bank leverage treated differently")
        if roe is not None and roe >= 15:
            adj += 6
            sector_reasons.append("Strong bank ROE")
        elif roe is not None and roe < 8:
            adj -= 5
            sector_risks.append("Weak bank ROE")
        if roa is not None and roa >= 1.2:
            adj += 5
            sector_reasons.append("Healthy bank ROA")
        elif roa is not None and roa < 0.5:
            adj -= 5
            sector_risks.append("Weak bank ROA")
        if pb is not None and pb > 5:
            adj -= 4
            sector_risks.append("Expensive bank P/B")

    elif sector_bucket == "FINANCIAL":
        if dte is not None and dte > 200:
            adj += 4
            sector_reasons.append("Financial leverage treated differently")
        if roe is not None and roe >= 16:
            adj += 5
            sector_reasons.append("Strong financial ROE")
        elif roe is not None and roe < 8:
            adj -= 5
            sector_risks.append("Weak financial ROE")
        if earn_g is not None and earn_g >= 15:
            adj += 4
            sector_reasons.append("Strong financial earnings growth")
        if pb is not None and pb > 8:
            adj -= 4
            sector_risks.append("Expensive financial P/B")

    elif sector_bucket == "IT_TECH":
        if roe is not None and roe >= 20:
            adj += 5
            sector_reasons.append("Strong tech ROE")
        if opm is not None and opm >= 18:
            adj += 5
            sector_reasons.append("Strong tech operating margin")
        if fcf is not None and fcf > 0:
            adj += 4
            sector_reasons.append("Positive tech free cash flow")
        if pe is not None and pe > 55 and (rev_g is None or rev_g < 10):
            adj -= 5
            sector_risks.append("Expensive tech valuation without growth")

    elif sector_bucket == "FMCG_CONSUMER":
        if roe is not None and roe >= 20:
            adj += 5
            sector_reasons.append("Strong consumer ROE")
        if opm is not None and opm >= 15:
            adj += 4
            sector_reasons.append("Healthy consumer margins")
        if dte is not None and dte <= 50:
            adj += 3
            sector_reasons.append("Low debt consumer business")
        if pe is not None and pe > 60 and (rev_g is None or rev_g < 8):
            adj -= 5
            sector_risks.append("Premium valuation without growth")

    elif sector_bucket == "PHARMA_HEALTHCARE":
        if opm is not None and opm >= 18:
            adj += 4
            sector_reasons.append("Strong healthcare margin")
        if rev_g is not None and rev_g >= 12:
            adj += 4
            sector_reasons.append("Healthcare growth support")
        if dte is not None and dte <= 75:
            adj += 3
            sector_reasons.append("Controlled healthcare debt")
        if earn_g is not None and earn_g < -10:
            adj -= 5
            sector_risks.append("Healthcare earnings contraction")

    elif sector_bucket == "CAPITAL_GOODS_INFRA":
        if rev_g is not None and rev_g >= 15:
            adj += 5
            sector_reasons.append("Strong capital goods revenue growth")
        if earn_g is not None and earn_g >= 15:
            adj += 4
            sector_reasons.append("Strong capital goods earnings growth")
        if dte is not None and dte <= 100:
            adj += 3
            sector_reasons.append("Manageable capital goods debt")
        if ocf is not None and ocf > 0:
            adj += 3
            sector_reasons.append("Capital goods cashflow support")
        if pe is not None and pe > 75 and (rev_g is None or rev_g < 10):
            adj -= 4
            sector_risks.append("Expensive capital goods valuation without growth")

    elif sector_bucket == "METALS_MINING":
        if dte is not None and dte <= 75:
            adj += 4
            sector_reasons.append("Controlled metal sector debt")
        if ocf is not None and ocf > 0:
            adj += 4
            sector_reasons.append("Metal cashflow support")
        if div is not None and div >= 2:
            adj += 2
            sector_reasons.append("Commodity dividend support")
        if earn_g is not None and earn_g < -20:
            adj -= 5
            sector_risks.append("Cyclical earnings decline")

    elif sector_bucket == "ENERGY_UTILITIES":
        if ocf is not None and ocf > 0:
            adj += 4
            sector_reasons.append("Energy cashflow support")
        if div is not None and div >= 2:
            adj += 3
            sector_reasons.append("Energy dividend support")
        if dte is not None and dte > 200:
            adj -= 4
            sector_risks.append("High energy/utility leverage")

    elif sector_bucket == "CHEMICALS":
        if opm is not None and opm >= 15:
            adj += 4
            sector_reasons.append("Strong chemical margin")
        if rev_g is not None and rev_g >= 12:
            adj += 4
            sector_reasons.append("Chemical revenue growth support")
        if dte is not None and dte <= 75:
            adj += 3
            sector_reasons.append("Controlled chemical debt")
        if earn_g is not None and earn_g < -15:
            adj -= 4
            sector_risks.append("Chemical earnings weakness")

    elif sector_bucket == "AUTO":
        if rev_g is not None and rev_g >= 12:
            adj += 4
            sector_reasons.append("Auto revenue growth support")
        if opm is not None and opm >= 10:
            adj += 3
            sector_reasons.append("Healthy auto margin")
        if dte is not None and dte <= 100:
            adj += 3
            sector_reasons.append("Manageable auto debt")
        if ocf is not None and ocf > 0:
            adj += 3
            sector_reasons.append("Auto cashflow support")

    elif sector_bucket == "CEMENT_REALTY":
        if dte is not None and dte <= 100:
            adj += 4
            sector_reasons.append("Manageable cement/realty debt")
        if opm is not None and opm >= 15:
            adj += 3
            sector_reasons.append("Healthy cement/realty margin")
        if ocf is not None and ocf > 0:
            adj += 3
            sector_reasons.append("Cement/realty cashflow support")

    elif sector_bucket == "TELECOM":
        if ocf is not None and ocf > 0:
            adj += 4
            sector_reasons.append("Telecom cashflow support")
        if rev_g is not None and rev_g >= 8:
            adj += 3
            sector_reasons.append("Telecom revenue growth support")
        if dte is not None and dte > 250:
            adj -= 5
            sector_risks.append("Very high telecom leverage")
        if npm is not None and npm < 0:
            adj -= 5
            sector_risks.append("Telecom negative profitability")

    elif sector_bucket == "CONSUMER_DISCRETIONARY":
        if rev_g is not None and rev_g >= 12:
            adj += 4
            sector_reasons.append("Consumer discretionary growth support")
        if opm is not None and opm >= 10:
            adj += 3
            sector_reasons.append("Healthy discretionary margin")
        if dte is not None and dte <= 75:
            adj += 3
            sector_reasons.append("Controlled discretionary debt")
        if pe is not None and pe > 70 and (rev_g is None or rev_g < 10):
            adj -= 4
            sector_risks.append("Expensive discretionary valuation without growth")

    else:
        if roe is not None and roe >= 18:
            adj += 2
            sector_reasons.append("General quality ROE support")
        if dte is not None and dte <= 75:
            adj += 2
            sector_reasons.append("General low debt support")
        if rev_g is not None and rev_g >= 12:
            adj += 2
            sector_reasons.append("General growth support")

    adj = clamp(adj, -15, 15)

    sector_adjusted_fundamental_score = clamp(
        fundamental_score + adj,
        0,
        100
    )

    final_reasons = reasons + sector_reasons
    final_risks = risks + sector_risks

    return pd.Series({
        "sector_bucket": sector_bucket,
        "profitability_score": round(profitability_score, 2),
        "growth_score": round(growth_score, 2),
        "balance_sheet_score": round(balance_sheet_score, 2),
        "cashflow_score": round(cashflow_score, 2),
        "valuation_score": round(valuation_score, 2),
        "fundamental_risk_penalty": round(penalty, 2),
        "fundamental_score": round(fundamental_score, 2),
        "sector_fundamental_adjustment": round(adj, 2),
        "sector_adjusted_fundamental_score": round(sector_adjusted_fundamental_score, 2),
        "fundamental_reasons": risk_text(final_reasons),
        "fundamental_risks": risk_text(final_risks)
    })


score_df = df.apply(score_row, axis=1)

result = pd.concat([df, score_df], axis=1)

result = result.sort_values(
    "sector_adjusted_fundamental_score",
    ascending=False
)

result.to_csv(OUTPUT_FILE, index=False)

print(f"Fundamental scores v3 saved: {len(result)} rows")
print(f"Output: {OUTPUT_FILE}")
