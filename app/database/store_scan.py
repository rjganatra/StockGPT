import sqlite3
import pandas as pd
from pathlib import Path

DB_PATH = "data/database/stockgpt.db"
SCAN_FILE = "data/scans/latest_scan.csv"

Path("data/database").mkdir(parents=True, exist_ok=True)

df = pd.read_csv(SCAN_FILE)

conn = sqlite3.connect(DB_PATH)

# Replace table so schema always matches latest scanner output
df.to_sql(
    "daily_scans",
    conn,
    if_exists="replace",
    index=False
)

conn.close()

print("Scans stored successfully with latest schema.")
