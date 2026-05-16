import pandas as pd
from pathlib import Path

UNIVERSE_FILE = "data/universe/universe.csv"
FUNDAMENTALS_FILE = "data/fundamentals/fundamentals.csv"
LATEST_SCAN_FILE = "data/scans/latest_scan.csv"

OUTPUT_MAP_FILE = "data/universe/sector_industry_map.csv"

Path("data/universe").mkdir(parents=True, exist_ok=True)


def clean_text(value):
    if pd.isna(value):
        return "Unknown"

    value = str(value).strip()

    if value == "" or value.lower() in ["nan", "none", "null"]:
        return "Unknown"

    return value


if not Path(FUNDAMENTALS_FILE).exists():
    raise FileNotFoundError("data/fundamentals/fundamentals.csv not found. Run weekly fundamentals first.")

fundamentals = pd.read_csv(FUNDAMENTALS_FILE)

required_cols = ["symbol", "sector_yf", "industry_yf"]

missing = [col for col in required_cols if col not in fundamentals.columns]

if missing:
    raise ValueError(f"Missing columns in fundamentals file: {missing}")

sector_map = fundamentals[
    [
        "symbol",
        "sector_yf",
        "industry_yf"
    ]
].copy()

sector_map["symbol"] = sector_map["symbol"].astype(str).str.upper().str.strip()
sector_map["sector_yf"] = sector_map["sector_yf"].apply(clean_text)
sector_map["industry_yf"] = sector_map["industry_yf"].apply(clean_text)

sector_map = sector_map.drop_duplicates(subset=["symbol"])

sector_map = sector_map.rename(
    columns={
        "sector_yf": "sector",
        "industry_yf": "industry"
    }
)

sector_map.to_csv(OUTPUT_MAP_FILE, index=False)

print(f"Sector/industry map saved: {len(sector_map)} rows")


# =========================
# UPDATE UNIVERSE
# =========================

if Path(UNIVERSE_FILE).exists():
    universe = pd.read_csv(UNIVERSE_FILE)

    universe["symbol"] = universe["symbol"].astype(str).str.upper().str.strip()

    universe = universe.drop(
        columns=[
            col for col in ["sector", "industry"]
            if col in universe.columns
        ],
        errors="ignore"
    )

    universe = universe.merge(
        sector_map,
        on="symbol",
        how="left"
    )

    universe["sector"] = universe["sector"].fillna("Unknown")
    universe["industry"] = universe["industry"].fillna("Unknown")

    universe.to_csv(UNIVERSE_FILE, index=False)

    print(f"Universe enriched: {len(universe)} rows")


# =========================
# UPDATE LATEST SCAN
# =========================

if Path(LATEST_SCAN_FILE).exists():
    scan = pd.read_csv(LATEST_SCAN_FILE)

    scan["symbol"] = scan["symbol"].astype(str).str.upper().str.strip()

    scan = scan.drop(
        columns=[
            col for col in ["sector", "industry"]
            if col in scan.columns
        ],
        errors="ignore"
    )

    scan = scan.merge(
        sector_map,
        on="symbol",
        how="left"
    )

    scan["sector"] = scan["sector"].fillna("Unknown")
    scan["industry"] = scan["industry"].fillna("Unknown")

    scan.to_csv(LATEST_SCAN_FILE, index=False)

    print(f"Latest scan enriched: {len(scan)} rows")
