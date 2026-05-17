import sqlite3
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCAN_FILE = "data/scans/latest_scan.csv"
DB_FILE = "data/database/stockgpt.db"

Path("data/database").mkdir(parents=True, exist_ok=True)

if not Path(SCAN_FILE).exists():
    raise FileNotFoundError("data/scans/latest_scan.csv not found")

df = pd.read_csv(SCAN_FILE)

stored_at = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y %I:%M %p IST")

df["stored_at"] = stored_at

conn = sqlite3.connect(DB_FILE)

df.to_sql(
    "daily_scans",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print(f"Scans stored: {len(df)} rows")
