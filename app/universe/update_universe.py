import pandas as pd
from pathlib import Path

# Nifty 500 + Extended Watchlist
symbols = [
    "RELIANCE","TCS","INFY","HDFCBANK","ICICIBANK",
    "SBIN","LT","ITC","KOTAKBANK","AXISBANK",
    "ASIANPAINT","BAJFINANCE","MARUTI","TITAN",
    "ULTRACEMCO","NESTLEIND","WIPRO","ONGC",
    "NTPC","POWERGRID","BEL","HAL","TRENT",
    "DMART","PIDILITIND","SUNPHARMA","ADANIPORTS",
    "ADANIENT","COALINDIA","TATASTEEL"
]

df = pd.DataFrame({
    "symbol": symbols
})

Path("data/universe").mkdir(parents=True, exist_ok=True)

df.to_csv("data/universe/universe.csv", index=False)

print(f"Universe updated with {len(df)} stocks")
