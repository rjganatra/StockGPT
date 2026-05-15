import pandas as pd
import requests
from pathlib import Path
from io import StringIO

OUTPUT_FILE = "data/universe/universe.csv"

NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
}

Path("data/universe").mkdir(parents=True, exist_ok=True)


def fetch_nse_eq_universe():
    response = requests.get(
        NSE_EQUITY_URL,
        headers=HEADERS,
        timeout=30
    )

    response.raise_for_status()

    text = response.text.strip()

    if "SYMBOL" not in text.upper():
        raise ValueError("Downloaded file does not look like NSE equity list")

    df = pd.read_csv(StringIO(text))

    df.columns = [str(col).strip().upper() for col in df.columns]

    # Common NSE columns:
    # SYMBOL, NAME OF COMPANY, SERIES, DATE OF LISTING, PAID UP VALUE, MARKET LOT, ISIN NUMBER, FACE VALUE

    rename_map = {
        "SYMBOL": "symbol",
        "NAME OF COMPANY": "company_name",
        "SERIES": "series",
        "DATE OF LISTING": "listing_date",
        "ISIN NUMBER": "isin",
        "FACE VALUE": "face_value",
    }

    df = df.rename(columns=rename_map)

    required_cols = ["symbol", "series"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required NSE column: {col}")

    # Only normal mainboard equity
    df = df[df["series"].astype(str).str.upper().str.strip() == "EQ"]

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["company_name"] = df.get("company_name", "").astype(str).str.strip()
    df["isin"] = df.get("isin", "").astype(str).str.strip()

    # NSE equity list does not always provide clean sector.
    # Scanner/dashboard can still work with sector = Unknown.
    # Later we can enrich sectors from NSE/Nifty index lists or yfinance.
    df["sector"] = "Unknown"

    df = df[
        [
            "symbol",
            "sector",
            "company_name",
            "series",
            "isin"
        ]
    ]

    df = df.dropna(subset=["symbol"])
    df = df[df["symbol"] != ""]
    df = df.drop_duplicates(subset=["symbol"])

    return df


def fallback_universe():
    symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN",
        "LT", "ITC", "KOTAKBANK", "AXISBANK", "BHARTIARTL",
        "BAJFINANCE", "ASIANPAINT", "MARUTI", "TITAN",
        "SUNPHARMA", "ULTRACEMCO", "NTPC", "POWERGRID",
        "ONGC", "COALINDIA", "TATASTEEL", "HINDALCO", "JSWSTEEL",
        "M&M", "TATAMOTORS", "BAJAJFINSV", "HCLTECH", "WIPRO",
        "TECHM", "ADANIENT", "ADANIPORTS", "BEL", "HAL",
        "MTARTECH", "DATAPATTNS", "ZENTEC", "KAYNES", "CYIENTDLM",
        "BLS", "DIXON", "ZOMATO", "BSE", "CDSL", "MCX", "IEX"
    ]

    return pd.DataFrame({
        "symbol": symbols,
        "sector": "Unknown",
        "company_name": symbols,
        "series": "EQ",
        "isin": ""
    })


try:
    universe = fetch_nse_eq_universe()

    if len(universe) < 800:
        raise ValueError(f"Fetched only {len(universe)} EQ stocks, expected broader universe")

    universe.to_csv(OUTPUT_FILE, index=False)

    print(f"NSE EQ universe updated: {len(universe)} stocks")

except Exception as error:
    print(f"NSE EQ universe fetch failed: {error}")
    print("Using fallback universe.")

    universe = fallback_universe()
    universe.to_csv(OUTPUT_FILE, index=False)

    print(f"Fallback universe saved: {len(universe)} stocks")
