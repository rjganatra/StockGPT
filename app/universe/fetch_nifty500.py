import pandas as pd
import requests
from pathlib import Path
from io import StringIO

OUTPUT_FILE = "data/universe/universe.csv"

NSE_EQUITY_URL = "https://archives.nseindia.com/content/equities/EQUITY_L.csv"
NIFTY_500_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.nseindia.com/",
}

Path("data/universe").mkdir(parents=True, exist_ok=True)


def fetch_nse_eq_universe():
    response = requests.get(NSE_EQUITY_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))

    df.columns = [str(col).strip().upper() for col in df.columns]

    df = df.rename(columns={
        "SYMBOL": "symbol",
        "NAME OF COMPANY": "company_name",
        "SERIES": "series",
        "ISIN NUMBER": "isin"
    })

    df = df[df["series"].astype(str).str.upper().str.strip() == "EQ"]

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["company_name"] = df["company_name"].astype(str).str.strip()
    df["isin"] = df["isin"].astype(str).str.strip()
    df["sector"] = "Unknown"

    return df[["symbol", "sector", "company_name", "series", "isin"]]


def fetch_nifty500_sector_map():
    response = requests.get(NIFTY_500_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()

    df = pd.read_csv(StringIO(response.text))

    df = df.rename(columns={
        "Symbol": "symbol",
        "Industry": "sector"
    })

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()

    return dict(zip(df["symbol"], df["sector"]))


CUSTOM_SECTOR_MAP = {
    "MTARTECH": "Capital Goods",
    "DATAPATTNS": "Capital Goods",
    "ZENTEC": "Capital Goods",
    "KAYNES": "Consumer Durables",
    "CYIENTDLM": "Capital Goods",
    "BLS": "Services",
    "TITAGARH": "Capital Goods",
    "RVNL": "Construction",
    "IRFC": "Financial Services",
    "IRCON": "Construction",
    "RAILTEL": "Telecommunication",
    "RITES": "Services",
    "MAZDOCK": "Capital Goods",
    "GRSE": "Capital Goods",
    "COCHINSHIP": "Capital Goods",
    "BDL": "Capital Goods",
    "HAL": "Capital Goods",
    "BEL": "Capital Goods",
}


def fallback_universe():
    symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
        "SBIN", "LT", "ITC", "KOTAKBANK", "AXISBANK",
        "MTARTECH", "DATAPATTNS", "ZENTEC", "KAYNES",
        "CYIENTDLM", "BLS", "TITAGARH", "RVNL", "IRFC",
        "IRCON", "RAILTEL", "RITES", "MAZDOCK", "GRSE",
        "COCHINSHIP", "BDL", "HAL", "BEL"
    ]

    return pd.DataFrame({
        "symbol": symbols,
        "sector": [CUSTOM_SECTOR_MAP.get(symbol, "Unknown") for symbol in symbols],
        "company_name": symbols,
        "series": "EQ",
        "isin": ""
    })


try:
    universe = fetch_nse_eq_universe()

    try:
        nifty_sector_map = fetch_nifty500_sector_map()
    except Exception as e:
        print(f"Nifty sector map fetch failed: {e}")
        nifty_sector_map = {}

    universe["sector"] = universe["symbol"].map(nifty_sector_map).fillna("Unknown")

    universe["sector"] = universe.apply(
        lambda row: CUSTOM_SECTOR_MAP.get(row["symbol"], row["sector"]),
        axis=1
    )

    universe = universe.drop_duplicates(subset=["symbol"])

    if len(universe) < 800:
        raise ValueError(f"Fetched only {len(universe)} stocks")

    universe.to_csv(OUTPUT_FILE, index=False)

    print(f"NSE EQ universe updated: {len(universe)} stocks")

except Exception as error:
    print(f"Universe fetch failed: {error}")
    print("Using fallback universe.")

    fallback = fallback_universe()
    fallback.to_csv(OUTPUT_FILE, index=False)

    print(f"Fallback universe saved: {len(fallback)} stocks")
