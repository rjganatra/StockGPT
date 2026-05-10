
import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
import time

universe = pd.read_csv("data/universe/universe.csv")

results = []

for symbol in universe["symbol"]:

    try:

        ticker = yf.Ticker(symbol + ".NS")

        hist = ticker.history(period="1y")

        if hist.empty:
            continue

        current_price = hist["Close"].iloc[-1]

        low_52 = hist["Low"].min()

        high_52 = hist["High"].max()

        distance_low = ((current_price - low_52) / low_52) * 100

        distance_high = ((high_52 - current_price) / high_52) * 100

        hist["rsi"] = ta.momentum.RSIIndicator(
            hist["Close"]
        ).rsi()

        rsi = hist["rsi"].iloc[-1]

        avg_volume = hist["Volume"].tail(20).mean()

        latest_volume = hist["Volume"].iloc[-1]

        volume_ratio = latest_volume / avg_volume

        sma_50 = hist["Close"].rolling(50).mean().iloc[-1]

        trend = "Bullish"

        if current_price < sma_50:
            trend = "Bearish"

        reasons = []

        if distance_low < 15:
            reasons.append("Near 52W Low")

        if rsi < 40:
            reasons.append("Oversold RSI")

        if volume_ratio > 1.5:
            reasons.append("High Volume")

        reasons_text = ", ".join(reasons)

        sector = "Others"

        if "sector" in universe.columns:

            sector = universe[
                universe["symbol"] == symbol
            ]["sector"].values[0]

        results.append({
            "symbol": symbol,
            "sector": sector,
            "current_price": round(current_price, 2),
            "52w_low": round(low_52, 2),
            "52w_high": round(high_52, 2),
            "distance_pct": round(distance_low, 2),
            "distance_from_high": round(distance_high, 2),
            "rsi": round(rsi, 2),
            "volume_ratio": round(volume_ratio, 2),
            "trend": trend,
            "reasons": reasons_text
        })

        print(symbol, "scanned")

        time.sleep(1)

    except Exception as e:

        print(symbol, "failed", e)

df = pd.DataFrame(results)

df = df.sort_values("distance_pct")

Path("data/scans").mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    "data/scans/latest_scan.csv",
    index=False
)

print("SCAN COMPLETE")
