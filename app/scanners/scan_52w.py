import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
from datetime import datetime

universe = pd.read_csv("data/universe/universe.csv")

results = []

for _, row in universe.iterrows():

    symbol = row["symbol"]
    sector = row["sector"] if "sector" in universe.columns else "Others"

    try:
        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1y")

        if hist.empty:
            continue

        current_price = hist["Close"].iloc[-1]
        previous_close = hist["Close"].iloc[-2] if len(hist) > 1 else current_price

        day_change_pct = ((current_price - previous_close) / previous_close) * 100

        low_52 = hist["Low"].min()
        high_52 = hist["High"].max()

        distance_pct = ((current_price - low_52) / low_52) * 100
        distance_from_high_pct = ((high_52 - current_price) / high_52) * 100

        hist["rsi"] = ta.momentum.RSIIndicator(hist["Close"]).rsi()
        rsi = hist["rsi"].iloc[-1]

        sma50 = hist["Close"].rolling(50).mean().iloc[-1]
        sma200 = hist["Close"].rolling(200).mean().iloc[-1]

        trend = "Bullish"
        if current_price < sma50:
            trend = "Bearish"

        avg_volume_20 = hist["Volume"].tail(20).mean()
        latest_volume = hist["Volume"].iloc[-1]

        volume_ratio = latest_volume / avg_volume_20 if avg_volume_20 else 0

        score = 0
        reasons = []

        if distance_pct < 20:
            score += 25
            reasons.append("Near 52W Low")

        if rsi < 45:
            score += 25
            reasons.append("RSI Weak/Oversold")

        if trend == "Bullish":
            score += 20
            reasons.append("Above 50 DMA")

        if volume_ratio > 1.2:
            score += 15
            reasons.append("Volume Above Average")

        if current_price > sma200:
            score += 15
            reasons.append("Above 200 DMA")

        results.append({
            "symbol": symbol,
            "sector": sector,
            "current_price": round(current_price, 2),
            "day_change_pct": round(day_change_pct, 2),
            "52w_low": round(low_52, 2),
            "52w_high": round(high_52, 2),
            "distance_pct": round(distance_pct, 2),
            "distance_from_high_pct": round(distance_from_high_pct, 2),
            "rsi": round(rsi, 2),
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2),
            "volume_ratio": round(volume_ratio, 2),
            "trend": trend,
            "score": score,
            "reasons": ", ".join(reasons)
        })

        print(f"{symbol} scanned")

    except Exception as e:
        print(symbol, e)

df = pd.DataFrame(results)

df = df.sort_values(
    "score",
    ascending=False
)

Path("data/scans").mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    "data/scans/latest_scan.csv",
    index=False
)

today = datetime.now().strftime("%Y-%m-%d")

history_path = Path(
    f"data/history/{today}"
)

history_path.mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    history_path / "latest_scan.csv",
    index=False
)

print("SCAN COMPLETE")
