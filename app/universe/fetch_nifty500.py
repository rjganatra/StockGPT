import pandas as pd
from pathlib import Path

NIFTY_500_URL = "https://www.niftyindices.com/IndexConstituent/ind_nifty500list.csv"

OUTPUT_FILE = "data/universe/universe.csv"

Path("data/universe").mkdir(parents=True, exist_ok=True)

try:
    df = pd.read_csv(NIFTY_500_URL)

    # NSE file usually has:
    # Company Name, Industry, Symbol, Series, ISIN Code

    df = df.rename(
        columns={
            "Symbol": "symbol",
            "Industry": "sector",
            "Company Name": "company_name",
            "ISIN Code": "isin",
            "Series": "series"
        }
    )

    required_cols = ["symbol", "sector"]

    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing column from NSE file: {col}")

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

    df["symbol"] = df["symbol"].astype(str).str.strip()
    df["sector"] = df["sector"].astype(str).str.strip()

    df = df.drop_duplicates(subset=["symbol"])

    df.to_csv(OUTPUT_FILE, index=False)

    print(f"Nifty 500 universe updated successfully: {len(df)} stocks")

except Exception as e:
    print(f"Failed to fetch Nifty 500 universe: {e}")

    fallback = pd.DataFrame({
        "symbol": [
            "RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK",
            "SBIN", "LT", "ITC", "KOTAKBANK", "AXISBANK"
        ],
        "sector": [
            "Oil Gas & Consumable Fuels", "Information Technology",
            "Information Technology", "Financial Services",
            "Financial Services", "Financial Services",
            "Construction", "Fast Moving Consumer Goods",
            "Financial Services", "Financial Services"
        ],
        "company_name": [
            "Reliance Industries Ltd.", "Tata Consultancy Services Ltd.",
            "Infosys Ltd.", "HDFC Bank Ltd.", "ICICI Bank Ltd.",
            "State Bank of India", "Larsen & Toubro Ltd.",
            "ITC Ltd.", "Kotak Mahindra Bank Ltd.", "Axis Bank Ltd."
        ],
        "series": ["EQ"] * 10,
        "isin": [""] * 10
    })

    fallback.to_csv(OUTPUT_FILE, index=False)

    print(f"Fallback universe saved: {len(fallback)} stocks")
