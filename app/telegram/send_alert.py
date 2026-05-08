import os
import pandas as pd
import requests

token = os.getenv("TELEGRAM_BOT_TOKEN")
chat_id = os.getenv("TELEGRAM_CHAT_ID")

df = pd.read_csv("data/scans/latest_scan.csv")

message = "Top Stocks Near 52W Low\n\n"

for _, row in df.head(5).iterrows():
    message += f"{row['symbol']} | {row['distance_pct']}%\n"

requests.post(
    f"https://api.telegram.org/bot{token}/sendMessage",
    data={
        "chat_id": chat_id,
        "text": message
    }
)

print("Telegram alert sent")
