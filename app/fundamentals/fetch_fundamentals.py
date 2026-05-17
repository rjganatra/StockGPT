import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

UNIVERSE_FILE = "data/universe/universe.csv"
SCAN_FILE = "data/scans/latest_scan.csv"
OUTPUT_FILE = "data/fundamentals/fundamentals.csv"

Path("data/fundamentals").mkdir(parents=True, exist_ok=True)

scan_time = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y at %I:%M %p IST")


def load_symbols():
    """
    Prefer latest_scan.csv because those are symbols Yahoo successfully scanned.
    Fall back to universe.csv if latest scan is unavailable.
    """

    if Path(SCAN_FILE).exists():
        scan_df = pd.read_csv(SCAN_FILE)

        if "symbol" in scan_df.columns and not scan_df.empty:
            return scan_df["symbol"].dropna().astype(str).str.upper().unique().tolist()

    universe_df = pd.read_csv(UNIVERSE_FILE)

    return universe_df["symbol"].dropna().astype(str).str.upper().unique().tolist()


def safe_percent(value):
    """
    Yahoo sometimes returns 0.15 for 15%.
    Convert to percentage if value looks like ratio.
    """

    if value is None:
        return None

    try:
        value = float(value)

        if abs(value) <= 5:
            return round(value * 100, 2)

        return round(value, 2)

    except Exception:
        return None


def safe_number(value):
    if value is None:
        return None

    try:
        return round(float(value), 2)
    except Exception:
        return None


def get_info_value(info, keys):
    for key in keys:
        if key in info and info[key] is not None:
            return info[key]

    return None


def fetch_one(symbol):
    yf_symbol = symbol + ".NS"

    try:
        ticker = yf.Ticker(yf_symbol)
        info = None

for attempt in range(3):
    try:
        info = ticker.info

        if info:
            break

    except Exception as e:
        print(f"{symbol} info fetch attempt {attempt + 1} failed: {e}")
        time.sleep(2 + attempt * 3)

if not info:
    return None

        company_name = get_info_value(
            info,
            ["longName", "shortName"]
        )

        sector = get_info_value(
            info,
            ["sector"]
        )

        industry = get_info_value(
            info,
            ["industry"]
        )

        market_cap = safe_number(
            get_info_value(info, ["marketCap"])
        )

        trailing_pe = safe_number(
            get_info_value(info, ["trailingPE"])
        )

        forward_pe = safe_number(
            get_info_value(info, ["forwardPE"])
        )

        price_to_book = safe_number(
            get_info_value(info, ["priceToBook"])
        )

        debt_to_equity = safe_number(
            get_info_value(info, ["debtToEquity"])
        )

        roe = safe_percent(
            get_info_value(info, ["returnOnEquity"])
        )

        roa = safe_percent(
            get_info_value(info, ["returnOnAssets"])
        )

        operating_margin = safe_percent(
            get_info_value(info, ["operatingMargins"])
        )

        net_profit_margin = safe_percent(
            get_info_value(info, ["profitMargins"])
        )

        gross_margin = safe_percent(
            get_info_value(info, ["grossMargins"])
        )

        revenue_growth = safe_percent(
            get_info_value(info, ["revenueGrowth"])
        )

        earnings_growth = safe_percent(
            get_info_value(info, ["earningsGrowth"])
        )

        current_ratio = safe_number(
            get_info_value(info, ["currentRatio"])
        )

        quick_ratio = safe_number(
            get_info_value(info, ["quickRatio"])
        )

        total_cash = safe_number(
            get_info_value(info, ["totalCash"])
        )

        total_debt = safe_number(
            get_info_value(info, ["totalDebt"])
        )

        free_cashflow = safe_number(
            get_info_value(info, ["freeCashflow"])
        )

        operating_cashflow = safe_number(
            get_info_value(info, ["operatingCashflow"])
        )

        dividend_yield = safe_percent(
            get_info_value(info, ["dividendYield"])
        )

        beta = safe_number(
            get_info_value(info, ["beta"])
        )

        return {
            "fundamental_scan_time": scan_time,
            "symbol": symbol,
            "company_name": company_name,
            "sector_yf": sector,
            "industry_yf": industry,
            "market_cap": market_cap,
            "trailing_pe": trailing_pe,
            "forward_pe": forward_pe,
            "price_to_book": price_to_book,
            "debt_to_equity": debt_to_equity,
            "roe": roe,
            "roa": roa,
            "operating_margin": operating_margin,
            "net_profit_margin": net_profit_margin,
            "gross_margin": gross_margin,
            "revenue_growth": revenue_growth,
            "earnings_growth": earnings_growth,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "total_cash": total_cash,
            "total_debt": total_debt,
            "free_cashflow": free_cashflow,
            "operating_cashflow": operating_cashflow,
            "dividend_yield": dividend_yield,
            "beta": beta
        }

    except Exception as e:
        print(f"{symbol} fundamentals failed: {e}")
        return None


symbols = load_symbols()

print(f"Starting fundamentals fetch for {len(symbols)} stocks")
print(f"Fundamental scan time: {scan_time}")

results = []
failed_symbols = []

MAX_WORKERS = 3

with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {
        executor.submit(fetch_one, symbol): symbol
        for symbol in symbols
    }

    for future in as_completed(futures):
        symbol = futures[future]

        try:
            result = future.result()

            if result:
                results.append(result)
                print(f"{symbol} fundamentals fetched")
            else:
                failed_symbols.append(symbol)

        except Exception as e:
            print(f"{symbol} future failed: {e}")

        time.sleep(0.8)

fundamentals_df = pd.DataFrame(results)

if fundamentals_df.empty:
    raise RuntimeError("No fundamentals fetched.")

fundamentals_df = fundamentals_df.drop_duplicates(subset=["symbol"])

fundamentals_df.to_csv(OUTPUT_FILE, index=False)

print(f"Fundamentals saved: {len(fundamentals_df)} rows")
