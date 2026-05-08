
import pandas as pd
import yfinance as yf
from pathlib import Path

universe = pd.read_csv("data/universe.csv")

results = []

for symbol in universe["symbol"]:
    try:
        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1y")

        if hist.empty:
            continue

        current = hist["Close"].iloc[-1]
        low = hist["Low"].min()

        dist = ((current - low) / low) * 100

        results.append({
            "symbol": symbol,
            "current_price": round(current,2),
            "52w_low": round(low,2),
            "distance_pct": round(dist,2)
        })

    except Exception as e:
        print(symbol, e)

df = pd.DataFrame(results)

Path("data/scans").mkdir(parents=True, exist_ok=True)

df.to_csv("data/scans/latest_scan.csv", index=False)

print("Scan completed")
