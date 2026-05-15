import os
import pandas as pd
import requests
from pathlib import Path

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SCAN_FILE = "data/scans/latest_scan.csv"

if not TOKEN or not CHAT_ID:
    raise RuntimeError("Telegram token or chat ID missing")

if not Path(SCAN_FILE).exists():
    raise RuntimeError("latest_scan.csv not found")

df = pd.read_csv(SCAN_FILE)

top = df.sort_values("score", ascending=False).head(10)

swing = df[
    (df["distance_pct"] < 20)
    &
    (df["rsi"] < 45)
].sort_values("score", ascending=False).head(10)

message = "📈 StockGPT Daily Market Scan\n\n"

message += "🔥 Top Opportunities\n"
for _, row in top.iterrows():
    message += (
        f"{row['symbol']} | "
        f"Score: {row['score']} | "
        f"RSI: {row['rsi']} | "
        f"Low Dist: {row['distance_pct']}%\n"
    )

message += "\n⚡ Swing Candidates\n"
if swing.empty:
    message += "No swing candidates today.\n"
else:
    for _, row in swing.iterrows():
        message += (
            f"{row['symbol']} | "
            f"RSI: {row['rsi']} | "
            f"Low Dist: {row['distance_pct']}%\n"
        )

url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

response = requests.post(
    url,
    data={
        "chat_id": CHAT_ID,
        "text": message
    },
    timeout=20
)

if response.status_code != 200:
    raise RuntimeError(response.text)

print("Telegram alert sent")
