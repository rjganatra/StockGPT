from pathlib import Path
import pandas as pd
import numpy as np
import re

SCAN_FILE = Path("data/scans/latest_scan.csv")
SECTOR_MAP_FILE = Path("data/universe/sector_industry_map.csv")
UNIVERSE_FILE = Path("data/universe/universe.csv")
FUNDAMENTALS_FILE = Path("data/fundamentals/fundamentals.csv")
FUND_SCORES_FILE = Path("data/fundamentals/fundamental_scores.csv")

MANUAL_OVERRIDES = {
    "RECLTD": {
        "company_name": "REC Limited",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "sector_bucket": "Financial Services",
    },
    "PFC": {
        "company_name": "Power Finance Corporation Limited",
        "sector": "Financial Services",
        "industry": "Credit Services",
        "sector_bucket": "Financial Services",
    },
    "HDFCBANK": {
        "company_name": "HDFC Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "sector_bucket": "Banking",
    },
    "ICICIBANK": {
        "company_name": "ICICI Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "sector_bucket": "Banking",
    },
    "SBIN": {
        "company_name": "State Bank of India",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "sector_bucket": "Banking",
    },
    "AXISBANK": {
        "company_name": "Axis Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "sector_bucket": "Banking",
    },
    "KOTAKBANK": {
        "company_name": "Kotak Mahindra Bank Limited",
        "sector": "Financial Services",
        "industry": "Banks - Regional",
        "sector_bucket": "Banking",
    },
}


def read_csv(path):
    if not path.exists():
        return pd.DataFrame()
    try:
        return pd.read_csv(path, low_memory=False)
    except Exception:
        return pd.DataFrame()


def norm_symbol(value):
    value = str(value or "").strip().upper()
    value = value.replace(".NS", "").replace(".BO", "")
    value = re.sub(r"[^A-Z0-9&]", "", value)
    return value


def is_blank(value):
    if value is None:
        return True
    try:
        if pd.isna(value):
            return True
    except Exception:
        pass
    value = str(value).strip()
    return value == "" or value.lower() in ["nan", "none", "null", "unknown", "na", "n/a"]


def safe_num(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def ensure_col(df, col, default=np.nan):
    if col not in df.columns:
        df[col] = default


def build_lookup(df):
    if df.empty or "symbol" not in df.columns:
        return {}

    temp = df.copy()
    temp["_sym"] = temp["symbol"].map(norm_symbol)

    lookup = {}
    for _, row in temp.iterrows():
        sym = row.get("_sym", "")
        if sym and sym not in lookup:
            lookup[sym] = row.to_dict()
    return lookup


def pick(row, candidates):
    for col in candidates:
        if col in row and not is_blank(row.get(col)):
            return row.get(col)
    return np.nan


def fill_if_blank(df, idx, col, value):
    if col not in df.columns:
        df[col] = np.nan

    if not is_blank(value) and is_blank(df.at[idx, col]):
        df.at[idx, col] = value


def score_band(score):
    score = safe_num(score, 0)

    if score >= 75:
        return "A Strong"
    if score >= 60:
        return "B Positive"
    if score >= 40:
        return "C Watch"
    if score >= 20:
        return "D Weak Watch"
    return "E Avoid"


def main():
    if not SCAN_FILE.exists():
        raise FileNotFoundError(f"{SCAN_FILE} not found")

    scan = pd.read_csv(SCAN_FILE, low_memory=False)
    original_cols = list(scan.columns)

    if "symbol" not in scan.columns:
        raise RuntimeError("latest_scan.csv missing symbol column")

    scan["_sym"] = scan["symbol"].map(norm_symbol)

    for col in [
        "company_name",
        "sector",
        "industry",
        "sector_bucket",
        "sector_yf",
        "industry_yf",
        "fundamental_score",
        "active_fundamental_score",
        "sector_adjusted_fundamental_score",
        "final_conviction_score",
        "score_band",
        "technical_score",
        "range_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
    ]:
        ensure_col(scan, col, np.nan)

    sector_map = build_lookup(read_csv(SECTOR_MAP_FILE))
    universe = build_lookup(read_csv(UNIVERSE_FILE))
    fundamentals = build_lookup(read_csv(FUNDAMENTALS_FILE))
    fund_scores = build_lookup(read_csv(FUND_SCORES_FILE))

    filled_sector = 0
    filled_company = 0

    for idx, row in scan.iterrows():
        sym = row["_sym"]

        sources = []
        if sym in fundamentals:
            sources.append(fundamentals[sym])
        if sym in fund_scores:
            sources.append(fund_scores[sym])
        if sym in sector_map:
            sources.append(sector_map[sym])
        if sym in universe:
            sources.append(universe[sym])
        if sym in MANUAL_OVERRIDES:
            sources.append(MANUAL_OVERRIDES[sym])

        before_sector = scan.at[idx, "sector"]
        before_company = scan.at[idx, "company_name"]

        for src in sources:
            fill_if_blank(scan, idx, "company_name", pick(src, ["company_name", "name", "longName", "shortName", "security_name"]))
            fill_if_blank(scan, idx, "sector", pick(src, ["sector", "sector_yf", "macro_sector", "industry_group"]))
            fill_if_blank(scan, idx, "industry", pick(src, ["industry", "industry_yf", "sub_industry", "business"]))
            fill_if_blank(scan, idx, "sector_bucket", pick(src, ["sector_bucket", "bucket", "sector", "sector_yf"]))

            for col in [
                "market_cap",
                "market_cap_cr",
                "trailing_pe",
                "forward_pe",
                "price_to_book",
                "debt_to_equity",
                "roe",
                "roa",
                "operating_margin",
                "net_profit_margin",
                "revenue_growth",
                "earnings_growth",
                "current_ratio",
                "free_cashflow_cr",
                "operating_cashflow_cr",
                "dividend_yield",
                "beta",
                "profitability_score",
                "growth_score",
                "balance_sheet_score",
                "cashflow_score",
                "valuation_score",
                "fundamental_score",
                "sector_fundamental_adjustment",
                "sector_adjusted_fundamental_score",
                "active_fundamental_score",
            ]:
                if col in src:
                    fill_if_blank(scan, idx, col, src.get(col))

        if is_blank(before_sector) and not is_blank(scan.at[idx, "sector"]):
            filled_sector += 1
        if is_blank(before_company) and not is_blank(scan.at[idx, "company_name"]):
            filled_company += 1

    # Data completeness flags
    # Important:
    # Identity data = company_name / sector / industry.
    # Fundamental data = financial metrics and fundamental scores.
    # Filling sector/company from fallback should NOT make fundamentals "Available".
    market_cap = pd.to_numeric(scan.get("market_cap_cr", 0), errors="coerce").fillna(0)
    raw_market_cap = pd.to_numeric(scan.get("market_cap", 0), errors="coerce").fillna(0)
    fund_score = pd.to_numeric(scan.get("fundamental_score", 0), errors="coerce").fillna(0)
    active_fund = pd.to_numeric(scan.get("active_fundamental_score", 0), errors="coerce").fillna(0)
    adjusted_fund = pd.to_numeric(scan.get("sector_adjusted_fundamental_score", 0), errors="coerce").fillna(0)

    company_missing = scan["company_name"].map(is_blank)
    sector_missing = scan["sector"].map(is_blank) & scan["industry"].map(is_blank) & scan["sector_bucket"].map(is_blank)

    metric_cols = [
        "trailing_pe",
        "forward_pe",
        "price_to_book",
        "roe",
        "roa",
        "operating_margin",
        "net_profit_margin",
        "gross_margin",
        "revenue_growth",
        "earnings_growth",
        "current_ratio",
        "quick_ratio",
        "total_cash_cr",
        "total_debt_cr",
        "free_cashflow_cr",
        "operating_cashflow_cr",
        "dividend_yield",
        "beta",
    ]

    # Count only meaningful financial metrics.
    # Important: default-filled zeros should not make fundamentals "Available".
    meaningful_metric_count = pd.Series([0] * len(scan), index=scan.index)

    for col in metric_cols:
        if col in scan.columns:
            s = pd.to_numeric(scan[col], errors="coerce")

            # Treat NaN as missing.
            # Treat 0 as missing for this completeness test because many failed fetches default to 0.
            meaningful_metric_count += ((s.notna()) & (s.abs() > 0.000001)).astype(int)

    fundamental_scan_available = pd.Series([False] * len(scan), index=scan.index)

    if "fundamental_scan_time" in scan.columns:
        fundamental_scan_available = ~scan["fundamental_scan_time"].map(is_blank)

    fundamental_score_available = (
        (fund_score > 0)
        |
        (active_fund > 0)
        |
        (adjusted_fund > 0)
    )

    fundamental_metric_available = (
        (market_cap > 0)
        |
        (raw_market_cap > 0)
        |
        fundamental_scan_available
        |
        fundamental_score_available
        |
        (meaningful_metric_count >= 2)
    )

    fundamentals_missing = ~fundamental_metric_available

    scan["meaningful_fundamental_metric_count"] = meaningful_metric_count

    scan["identity_data_status"] = np.where(company_missing | sector_missing, "Partial", "Available")
    scan["fundamental_data_status"] = np.where(fundamentals_missing, "Missing", "Available")
    scan["sector_data_status"] = np.where(sector_missing, "Missing", "Available")

    scan["data_completeness_status"] = "Complete"
    scan.loc[fundamentals_missing & ~sector_missing, "data_completeness_status"] = "Fundamentals Missing"
    scan.loc[~fundamentals_missing & sector_missing, "data_completeness_status"] = "Sector Missing"
    scan.loc[fundamentals_missing & sector_missing, "data_completeness_status"] = "Fundamentals + Sector Missing"

    scan["data_confidence_score"] = 100
    scan.loc[fundamentals_missing, "data_confidence_score"] -= 30
    scan.loc[sector_missing, "data_confidence_score"] -= 15
    scan.loc[company_missing, "data_confidence_score"] -= 5
    scan["data_confidence_score"] = scan["data_confidence_score"].clip(lower=40)

    # Preserve original score
    if "final_conviction_score_original" not in scan.columns:
        scan["final_conviction_score_original"] = scan["final_conviction_score"]

    technical = pd.to_numeric(scan.get("technical_score", 0), errors="coerce").fillna(0)
    range_score = pd.to_numeric(scan.get("range_score", 0), errors="coerce").fillna(0)
    relative = pd.to_numeric(scan.get("relative_strength_score", 0), errors="coerce").fillna(0)
    sector_score = pd.to_numeric(scan.get("sector_score", 0), errors="coerce").fillna(0)
    risk = pd.to_numeric(scan.get("risk_penalty", 0), errors="coerce").fillna(0)
    current_final = pd.to_numeric(scan.get("final_conviction_score", 0), errors="coerce").fillna(0)

    fallback_score = (
        technical * 0.25
        + range_score * 0.50
        + relative * 0.10
        + sector_score * 0.15
        - risk * 0.50
    ).clip(lower=0, upper=100)

    has_real_nonfundamental_signal = (
        (technical > 0)
        | (range_score > 0)
        | (relative > 0)
        | (sector_score > 0)
    )

    original_final = pd.to_numeric(
        scan.get("final_conviction_score_original", current_final),
        errors="coerce"
    ).fillna(current_final)

    repair_mask = (
        fundamentals_missing
        &
        has_real_nonfundamental_signal
        &
        (
            (current_final <= 1)
            |
            (original_final <= 1)
        )
        &
        (fallback_score >= 10)
    )

    scan["final_conviction_score_source"] = "Original"
    scan.loc[repair_mask, "final_conviction_score"] = fallback_score[repair_mask].round(2)
    scan.loc[repair_mask, "final_conviction_score_source"] = "Fallback_NoFundamentals"

    scan["score_band"] = pd.to_numeric(scan["final_conviction_score"], errors="coerce").fillna(0).map(score_band)

    scan["data_quality_note"] = ""
    scan.loc[fundamentals_missing, "data_quality_note"] = "Fundamental metrics unavailable; identity/sector may be filled from fallback. Final score uses available technical/range/relative data with confidence penalty."
    scan.loc[sector_missing, "data_quality_note"] = scan.loc[sector_missing, "data_quality_note"].astype(str) + " Sector mapping unavailable."

    # Clean Unknown if manual/fallback filled sector_bucket from sector
    scan.loc[scan["sector_bucket"].map(is_blank) & ~scan["sector"].map(is_blank), "sector_bucket"] = scan["sector"]

    scan = scan.drop(columns=["_sym"], errors="ignore")

    # Keep original columns first, new columns after
    new_cols = [c for c in scan.columns if c not in original_cols and c != "_sym"]
    final_cols = [c for c in original_cols if c in scan.columns] + new_cols
    scan = scan[final_cols]

    SCAN_FILE.parent.mkdir(parents=True, exist_ok=True)
    scan.to_csv(SCAN_FILE, index=False)

    print("✅ Scan completeness repair complete")
    print(f"Rows: {len(scan)}")
    print(f"Sector/company fallback filled: sector={filled_sector}, company={filled_company}")
    print(f"Fallback final conviction repaired: {int(repair_mask.sum())}")

    if "RECLTD" in set(scan["symbol"].astype(str).str.upper()):
        rec = scan[scan["symbol"].astype(str).str.upper() == "RECLTD"].iloc[0]
        print("RECLTD check:")
        print(f"  sector={rec.get('sector')}")
        print(f"  industry={rec.get('industry')}")
        print(f"  company_name={rec.get('company_name')}")
        print(f"  final_conviction_score={rec.get('final_conviction_score')}")
        print(f"  score_band={rec.get('score_band')}")
        print(f"  data_completeness_status={rec.get('data_completeness_status')}")


if __name__ == "__main__":
    main()
