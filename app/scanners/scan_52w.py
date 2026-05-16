import yfinance as yf
import pandas as pd
import ta
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time

universe = pd.read_csv("data/universe/universe.csv")

symbols = universe["symbol"].dropna().unique().tolist()
sector_map = dict(zip(universe["symbol"], universe["sector"]))

scan_time = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y at %I:%M %p IST")

print(f"Starting scan for {len(symbols)} stocks")
print(f"Scan time: {scan_time}")


def chunk_list(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def download_chunk(chunk_symbols, retry=False):
    yf_symbols = [symbol + ".NS" for symbol in chunk_symbols]

    try:
        data = yf.download(
            tickers=yf_symbols,
            period="1y",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=25
        )

        return data

    except Exception as e:
        print(f"Chunk failed: {chunk_symbols[:5]}... | {e}")

        if not retry:
            time.sleep(5)
            return download_chunk(chunk_symbols, retry=True)

        return None


results = []
failed_symbols = []

CHUNK_SIZE = 100

for chunk in chunk_list(symbols, CHUNK_SIZE):

    print(f"Downloading chunk: {chunk[0]} to {chunk[-1]}")

    data = download_chunk(chunk)

    if data is None or data.empty:
        failed_symbols.extend(chunk)
        continue

    for symbol in chunk:
        yf_symbol = symbol + ".NS"

        try:
            if isinstance(data.columns, pd.MultiIndex):
                if yf_symbol not in data.columns.get_level_values(0):
                    failed_symbols.append(symbol)
                    continue

                hist = data[yf_symbol].dropna()
            else:
                hist = data.dropna()

            if hist.empty or len(hist) < 60:
                failed_symbols.append(symbol)
                continue

            current_price = hist["Close"].iloc[-1]
            previous_close = hist["Close"].iloc[-2]

            low_52 = hist["Low"].min()
            high_52 = hist["High"].max()

            day_change_pct = ((current_price - previous_close) / previous_close) * 100
            distance_pct = ((current_price - low_52) / low_52) * 100
            distance_from_high_pct = ((high_52 - current_price) / high_52) * 100

            hist = hist.copy()
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
            print(f"{symbol} failed during processing: {e}")
            failed_symbols.append(symbol)

    time.sleep(2)


# One-by-one retry for important missed stocks
IMPORTANT_RETRY = [
    "ASIANPAINT", "KPITTECH", "COFORGE", "MPHASIS", "AUROPHARMA",
    "PAGEIND", "HONAUT", "COLPAL", "PRAJIND", "CCL", "ACC",
    "KFINTECH", "MRPL", "KAJARIACER", "IRB", "GPIL", "HBLENGINE"
]

already_scanned = {row["symbol"] for row in results}
retry_symbols = [s for s in IMPORTANT_RETRY if s not in already_scanned]

for symbol in retry_symbols:

    try:
        print(f"Retrying important stock: {symbol}")

        ticker = yf.Ticker(symbol + ".NS")
        hist = ticker.history(period="1y", timeout=20)

        if hist.empty or len(hist) < 60:
            continue

        current_price = hist["Close"].iloc[-1]
        previous_close = hist["Close"].iloc[-2]

        low_52 = hist["Low"].min()
        high_52 = hist["High"].max()

        day_change_pct = ((current_price - previous_close) / previous_close) * 100
        distance_pct = ((current_price - low_52) / low_52) * 100
        distance_from_high_pct = ((high_52 - current_price) / high_52) * 100

        hist = hist.copy()
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
        print(f"Important retry failed for {symbol}: {e}")


df = pd.DataFrame(results)

if df.empty:
    raise RuntimeError("Scan produced zero results")

df = df.drop_duplicates(subset=["symbol"])
df = df.sort_values("score", ascending=False)

Path("data/scans").mkdir(parents=True, exist_ok=True)
df.to_csv("data/scans/latest_scan.csv", index=False)

today = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%Y-%m-%d")

history_path = Path(f"data/history/{today}")
history_path.mkdir(parents=True, exist_ok=True)
df.to_csv(history_path / "latest_scan.csv", index=False)

failed_df = pd.DataFrame({"symbol": sorted(set(failed_symbols))})
failed_df.to_csv("data/scans/failed_symbols.csv", index=False)

print(f"SCAN COMPLETE: {len(df)} stocks scanned")
print(f"FAILED SYMBOLS: {len(set(failed_symbols))}")
