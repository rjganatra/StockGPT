import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
import time

# =========================
# STOCK UNIVERSE
# =========================

universe = pd.read_csv(
    "data/universe/universe.csv"
)

symbols = universe["symbol"].tolist()

results = []

# =========================
# SCANNER LOOP
# =========================

for symbol in symbols:

    try:

        ticker = yf.Ticker(symbol + ".NS")

        hist = ticker.history(period="1y")

        if hist.empty:
            continue

        current_price = hist["Close"].iloc[-1]

        low_52 = hist["Low"].min()

        high_52 = hist["High"].max()

        distance_low = (
            (current_price - low_52)
            / low_52
        ) * 100

        distance_high = (
            (high_52 - current_price)
            / high_52
        ) * 100

        # =========================
        # RSI
        # =========================

        hist["rsi"] = ta.momentum.RSIIndicator(
            hist["Close"]
        ).rsi()

        rsi = hist["rsi"].iloc[-1]

        # =========================
        # VOLUME
        # =========================

        avg_volume = hist["Volume"].tail(20).mean()

        latest_volume = hist["Volume"].iloc[-1]

        volume_ratio = latest_volume / avg_volume

        # =========================
        # TREND
        # =========================

        sma_50 = hist["Close"].rolling(50).mean().iloc[-1]

        trend = "Bullish"

        if current_price < sma_50:
            trend = "Bearish"

        # =========================
        # REASON ENGINE
        # =========================

        reasons = []

        if distance_low < 15:
            reasons.append("Near 52W Low")

        if rsi < 40:
            reasons.append("Oversold RSI")

        if volume_ratio > 1.5:
            reasons.append("High Volume")

        if trend == "Bullish":
            reasons.append("Above 50DMA")

        reason_text = ", ".join(reasons)

        # =========================
        # SAVE RESULT
        # =========================

        results.append({

            "symbol": symbol,

            "current_price": round(current_price, 2),

            "52w_low": round(low_52, 2),

            "52w_high": round(high_52, 2),

            "distance_pct": round(distance_low, 2),

            "distance_from_high": round(distance_high, 2),

            "rsi": round(rsi, 2),

            "volume_ratio": round(volume_ratio, 2),

            "trend": trend,

            "reasons": reason_text

        })

        print(f"{symbol} scanned")

        time.sleep(1)

    except Exception as e:

        print(f"{symbol} failed: {e}")

# =========================
# FINAL DATAFRAME
# =========================

df = pd.DataFrame(results)

df = df.sort_values(
    "distance_pct"
)

# =========================
# SAVE CSV
# =========================

Path("data/scans").mkdir(
    parents=True,
    exist_ok=True
)

df.to_csv(
    "data/scans/latest_scan.csv",
    index=False
)

print(df.head())

print("SCAN COMPLETED")
