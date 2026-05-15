import pandas as pd
import requests
from pathlib import Path
from io import StringIO

OUTPUT_FILE = "data/universe/universe.csv"

NIFTY_500_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"

HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "text/csv,application/csv,text/plain,*/*",
    "Referer": "https://www.niftyindices.com/",
}

Path("data/universe").mkdir(parents=True, exist_ok=True)


def normalize_columns(df):
    df.columns = [str(col).strip() for col in df.columns]

    rename_map = {
        "Company Name": "company_name",
        "Industry": "sector",
        "Symbol": "symbol",
        "Series": "series",
        "ISIN Code": "isin",
    }

    df = df.rename(columns=rename_map)

    required = ["symbol", "sector"]

    for col in required:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")

    if "company_name" not in df.columns:
        df["company_name"] = ""

    if "series" not in df.columns:
        df["series"] = "EQ"

    if "isin" not in df.columns:
        df["isin"] = ""

    df = df[["symbol", "sector", "company_name", "series", "isin"]]

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()

    df = df.dropna(subset=["symbol"])
    df = df[df["symbol"] != ""]
    df = df.drop_duplicates(subset=["symbol"])

    return df


def fetch_from_niftyindices():
    response = requests.get(
        NIFTY_500_URL,
        headers=HEADERS,
        timeout=30,
    )

    response.raise_for_status()

    text = response.text.strip()

    if "Symbol" not in text:
        raise ValueError("Downloaded file does not look like Nifty 500 CSV")

    df = pd.read_csv(StringIO(text))

    return normalize_columns(df)


def fallback_universe():
    symbols = [
        "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK", "SBIN", "LT", "ITC",
        "KOTAKBANK", "AXISBANK", "BHARTIARTL", "BAJFINANCE", "ASIANPAINT",
        "MARUTI", "TITAN", "SUNPHARMA", "ULTRACEMCO", "NTPC", "POWERGRID",
        "ONGC", "COALINDIA", "TATASTEEL", "HINDALCO", "JSWSTEEL", "M&M",
        "TATAMOTORS", "BAJAJFINSV", "HCLTECH", "WIPRO", "TECHM", "LTIM",
        "ADANIENT", "ADANIPORTS", "GRASIM", "CIPLA", "DRREDDY", "DIVISLAB",
        "APOLLOHOSP", "EICHERMOT", "HEROMOTOCO", "BAJAJ-AUTO", "BRITANNIA",
        "NESTLEIND", "HINDUNILVR", "TATACONSUM", "PIDILITIND", "DMART",
        "TRENT", "BEL", "HAL", "BHEL", "IRCTC", "INDIGO", "DLF", "LODHA",
        "GODREJPROP", "SBILIFE", "HDFCLIFE", "ICICIPRULI", "ICICIGI",
        "CHOLAFIN", "MUTHOOTFIN", "RECLTD", "PFC", "CANBK", "BANKBARODA",
        "PNB", "FEDERALBNK", "IDFCFIRSTB", "AUBANK", "BANDHANBNK",
        "JINDALSTEL", "SAIL", "NMDC", "VEDL", "HINDZINC", "TATAPOWER",
        "ADANIGREEN", "ADANIPOWER", "IOC", "BPCL", "HINDPETRO", "GAIL",
        "PETRONET", "IGL", "MGL", "TATACHEM", "UPL", "PIIND", "SRF",
        "DEEPAKNTR", "AARTIIND", "DIXON", "VOLTAS", "BLUESTARCO",
        "CROMPTON", "HAVELLS", "POLYCAB", "ABB", "SIEMENS", "CUMMINSIND",
        "ASHOKLEY", "TVSMOTOR", "BOSCHLTD", "MRF", "BALKRISIND",
        "PAGEIND", "NYKAA", "ZOMATO", "PAYTM", "NAUKRI", "POLICYBZR",
        "YESBANK", "UNIONBANK", "INDUSINDBK", "RBLBANK", "BSE", "CDSL",
        "MCX", "IEX", "IRFC", "RVNL", "IRCON", "CONCOR", "GMRINFRA",
        "ADANITRANS", "NHPC", "SJVN", "TORNTPOWER", "JSWENERGY",
        "MAXHEALTH", "FORTIS", "LUPIN", "AUROPHARMA", "ALKEM", "BIOCON",
        "LAURUSLABS", "GLENMARK", "MANKIND", "IPCALAB", "OBEROIRLTY",
        "PHOENIXLTD", "PRESTIGE", "TATACOMM", "BHARATFORG", "MOTHERSON",
        "SONACOMS", "SUPREMEIND", "ASTRAL", "KEI", "KPITTECH", "COFORGE",
        "MPHASIS", "PERSISTENT", "OFSS", "LTTS"
    ]

    sector_map = {
        "RELIANCE": "Oil Gas & Consumable Fuels",
        "TCS": "Information Technology",
        "INFY": "Information Technology",
        "HDFCBANK": "Financial Services",
        "ICICIBANK": "Financial Services",
        "SBIN": "Financial Services",
        "AXISBANK": "Financial Services",
        "KOTAKBANK": "Financial Services",
        "BEL": "Capital Goods",
        "HAL": "Capital Goods",
        "SUNPHARMA": "Healthcare",
        "CIPLA": "Healthcare",
        "TATASTEEL": "Metals & Mining",
        "TATAMOTORS": "Automobile and Auto Components",
        "MARUTI": "Automobile and Auto Components",
        "M&M": "Automobile and Auto Components",
        "ZOMATO": "Consumer Services",
    }

    df = pd.DataFrame({
        "symbol": symbols,
        "sector": [sector_map.get(symbol, "Others") for symbol in symbols],
        "company_name": symbols,
        "series": "EQ",
        "isin": "",
    })

    return df


try:
    universe = fetch_from_niftyindices()

    if len(universe) < 400:
        raise ValueError(f"Fetched only {len(universe)} rows, expected around 500")

    universe.to_csv(OUTPUT_FILE, index=False)

    print(f"Nifty 500 universe updated: {len(universe)} stocks")

except Exception as error:
    print(f"Nifty 500 fetch failed: {error}")
    print("Using expanded fallback universe instead.")

    universe = fallback_universe()
    universe.to_csv(OUTPUT_FILE, index=False)

    print(f"Fallback universe saved: {len(universe)} stocks")
