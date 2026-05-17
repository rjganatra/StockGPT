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


def normalize_symbol(df):
    df = df.copy()

    if "symbol" not in df.columns:
        raise ValueError("symbol column missing")

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    return df


def ensure_sector_industry(df):
    df = df.copy()

    if "sector" not in df.columns:
        df["sector"] = "Unknown"

    if "industry" not in df.columns:
        df["industry"] = "Unknown"

    df["sector"] = df["sector"].apply(clean_text)
    df["industry"] = df["industry"].apply(clean_text)

    return df


# =========================
# LOAD EXISTING MAP IF AVAILABLE
# =========================

sector_map = None

if Path(FUNDAMENTALS_FILE).exists():
    fundamentals = pd.read_csv(FUNDAMENTALS_FILE)

    if all(col in fundamentals.columns for col in ["symbol", "sector_yf", "industry_yf"]):
        fundamentals = normalize_symbol(fundamentals)

        sector_map = fundamentals[
            [
                "symbol",
                "sector_yf",
                "industry_yf"
            ]
        ].copy()

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

if sector_map is None:
    if Path(OUTPUT_MAP_FILE).exists():
        sector_map = pd.read_csv(OUTPUT_MAP_FILE)
        sector_map = normalize_symbol(sector_map)
        sector_map = ensure_sector_industry(sector_map)

        print(f"Using existing sector/industry map: {len(sector_map)} rows")
    else:
        sector_map = pd.DataFrame(
            columns=["symbol", "sector", "industry"]
        )

        print("No fundamentals/map found. Continuing with existing sector/industry data.")


# =========================
# UPDATE UNIVERSE
# =========================

if Path(UNIVERSE_FILE).exists():
    universe = pd.read_csv(UNIVERSE_FILE)
    universe = normalize_symbol(universe)
    universe = ensure_sector_industry(universe)

    if not sector_map.empty:
        universe = universe.drop(
            columns=["sector", "industry"],
            errors="ignore"
        )

        universe = universe.merge(
            sector_map,
            on="symbol",
            how="left"
        )

        universe = ensure_sector_industry(universe)

    universe.to_csv(UNIVERSE_FILE, index=False)

    print(f"Universe enriched: {len(universe)} rows")


# =========================
# UPDATE LATEST SCAN
# =========================

if Path(LATEST_SCAN_FILE).exists():
    scan = pd.read_csv(LATEST_SCAN_FILE)
    scan = normalize_symbol(scan)
    scan = ensure_sector_industry(scan)

    if not sector_map.empty:
        scan = scan.drop(
            columns=["sector", "industry"],
            errors="ignore"
        )

        scan = scan.merge(
            sector_map,
            on="symbol",
            how="left"
        )

        scan = ensure_sector_industry(scan)

    scan.to_csv(LATEST_SCAN_FILE, index=False)

    print(f"Latest scan enriched: {len(scan)} rows")
