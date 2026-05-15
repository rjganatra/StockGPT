import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

universe = pd.read_csv("data/universe/universe.csv")

symbols = universe["symbol"].dropna().unique().tolist()
sector_map = dict(zip(universe["symbol"], universe["sector"]))

yf_symbols = [symbol + ".NS" for symbol in symbols]

from zoneinfo import ZoneInfo

scan_time = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y at %I:%M %p IST")

print(f"Starting batch scan for {len(yf_symbols)} stocks")
print(f"Scan time: {scan_time}")

data = yf.download(
    tickers=yf_symbols,
    period="1y",
    interval="1d",
    group_by="ticker",
    threads=True,
    progress=False,
    timeout=20
)

results = []

for symbol in symbols:
    yf_symbol = symbol + ".NS"

    try:
        if yf_symbol not in data.columns.get_level_values(0):
            print(f"{symbol} missing from download")
            continue

        hist = data[yf_symbol].dropna()

        if hist.empty or len(hist) < 60:
            continue

        current_price = hist["Close"].iloc[-1]
        previous_close = hist["Close"].iloc[-2]

        low_52 = hist["Low"].min()
        high_52 = hist["High"].max()

        day_change_pct = ((current_price - previous_close) / previous_close) * 100
        distance_pct = ((current_price - low_52) / low_52) * 100
        distance_from_high_pct = ((high_52 - current_price) / high_52) * 100

        hist["rsi"] = ta.momentum.RSIIndicator(hist["Close"]).rsi()
        rsi = hist["rsi"].iloc[-1]

        sma50 = hist["Close"].rolling(50).mean().iloc[-1]
        sma200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else None

        avg_volume_20 = hist["Volume"].tail(20).mean()
        latest_volume = hist["Volume"].iloc[-1]
        volume_ratio = latest_volume / avg_volume_20 if avg_volume_20 > 0 else 0

        trend = "Bullish" if current_price > sma50 else "Bearish"

        reasons = []
        score = 0

        if distance_pct < 15:
            score += 25
            reasons.append("Near 52W low")

        if rsi < 45:
            score += 20
            reasons.append("RSI weak/oversold")

        if trend == "Bullish":
            score += 20
            reasons.append("Above 50 DMA")

        if volume_ratio > 1.3:
            score += 15
            reasons.append("Volume expansion")

        if sma200 and current_price > sma200:
            score += 20
            reasons.append("Above 200 DMA")

        results.append({
            "scan_time": scan_time,
            "symbol": symbol,
            "sector": sector_map.get(symbol, "Unknown"),
            "current_price": round(current_price, 2),
            "day_change_pct": round(day_change_pct, 2),
            "52w_low": round(low_52, 2),
            "52w_high": round(high_52, 2),
            "distance_pct": round(distance_pct, 2),
            "distance_from_high_pct": round(distance_from_high_pct, 2),
            "rsi": round(rsi, 2),
            "sma50": round(sma50, 2),
            "sma200": round(sma200, 2) if sma200 else None,
            "avg_volume_20": round(avg_volume_20, 2),
            "latest_volume": round(latest_volume, 2),
            "volume_ratio": round(volume_ratio, 2),
            "trend": trend,
            "score": score,
            "reasons": ", ".join(reasons)
        })

    except Exception as e:
        print(f"{symbol} failed: {e}")

df = pd.DataFrame(results)

if df.empty:
    raise RuntimeError("Scan produced zero results")

df = df.sort_values("score", ascending=False)

Path("data/scans").mkdir(parents=True, exist_ok=True)

df.to_csv("data/scans/latest_scan.csv", index=False)

today = datetime.now().strftime("%Y-%m-%d")

history_path = Path(f"data/history/{today}")
history_path.mkdir(parents=True, exist_ok=True)

df.to_csv(history_path / "latest_scan.csv", index=False)

print(f"SCAN COMPLETE: {len(df)} stocks scanned")
