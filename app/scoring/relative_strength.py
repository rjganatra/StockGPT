import yfinance as yf
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo
import time

SCAN_FILE = "data/scans/latest_scan.csv"
OUTPUT_FILE = "data/scoring/relative_strength.csv"

Path("data/scoring").mkdir(parents=True, exist_ok=True)

scan_df = pd.read_csv(SCAN_FILE)

scan_df["symbol"] = scan_df["symbol"].astype(str).str.upper().str.strip()

symbols = scan_df["symbol"].dropna().unique().tolist()

scan_time = datetime.now(
    ZoneInfo("Asia/Kolkata")
).strftime("%d.%m.%Y at %I:%M %p IST")


def chunk_list(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def calc_return(close_series, days):
    try:
        close_series = close_series.dropna()

        if len(close_series) <= days:
            return None

        latest = close_series.iloc[-1]
        past = close_series.iloc[-days]

        if past == 0:
            return None

        return round(((latest - past) / past) * 100, 2)

    except Exception:
        return None


def safe_download_nifty():
    try:
        nifty_data = yf.download(
            "^NSEI",
            period="8mo",
            interval="1d",
            progress=False,
            timeout=20
        )

        if nifty_data.empty or "Close" not in nifty_data.columns:
            return None, None, None

        nifty_close = nifty_data["Close"].dropna()

        return (
            calc_return(nifty_close, 21),
            calc_return(nifty_close, 63),
            calc_return(nifty_close, 126)
        )

    except Exception as e:
        print(f"Nifty benchmark failed. Continuing without Nifty comparison: {e}")

        return None, None, None


print(f"Starting relative strength calculation for {len(symbols)} stocks")

nifty_1m_return, nifty_3m_return, nifty_6m_return = safe_download_nifty()

results = []

CHUNK_SIZE = 100

for chunk in chunk_list(symbols, CHUNK_SIZE):
    yf_symbols = [symbol + ".NS" for symbol in chunk]

    try:
        print(f"Downloading relative strength chunk: {chunk[0]} to {chunk[-1]}")

        data = yf.download(
            tickers=yf_symbols,
            period="8mo",
            interval="1d",
            group_by="ticker",
            threads=True,
            progress=False,
            timeout=25
        )

        for symbol in chunk:
            yf_symbol = symbol + ".NS"

            try:
                if isinstance(data.columns, pd.MultiIndex):
                    if yf_symbol not in data.columns.get_level_values(0):
                        continue

                    hist = data[yf_symbol].dropna()
                else:
                    hist = data.dropna()

                if hist.empty or "Close" not in hist.columns:
                    continue

                close = hist["Close"]

                return_1m = calc_return(close, 21)
                return_3m = calc_return(close, 63)
                return_6m = calc_return(close, 126)

                vs_nifty_1m = (
                    round(return_1m - nifty_1m_return, 2)
                    if return_1m is not None and nifty_1m_return is not None
                    else 0
                )

                vs_nifty_3m = (
                    round(return_3m - nifty_3m_return, 2)
                    if return_3m is not None and nifty_3m_return is not None
                    else 0
                )

                vs_nifty_6m = (
                    round(return_6m - nifty_6m_return, 2)
                    if return_6m is not None and nifty_6m_return is not None
                    else 0
                )

                score = 0
                reasons = []

                if return_1m is not None:
                    if return_1m > 10:
                        score += 15
                        reasons.append("Strong 1M absolute return")
                    elif return_1m > 0:
                        score += 8
                        reasons.append("Positive 1M return")

                if return_3m is not None:
                    if return_3m > 20:
                        score += 20
                        reasons.append("Strong 3M absolute return")
                    elif return_3m > 0:
                        score += 10
                        reasons.append("Positive 3M return")

                if return_6m is not None:
                    if return_6m > 30:
                        score += 20
                        reasons.append("Strong 6M absolute return")
                    elif return_6m > 0:
                        score += 10
                        reasons.append("Positive 6M return")

                if nifty_1m_return is not None and vs_nifty_1m > 5:
                    score += 10
                    reasons.append("1M Nifty outperformance")

                if nifty_3m_return is not None and vs_nifty_3m > 10:
                    score += 15
                    reasons.append("3M Nifty outperformance")

                if nifty_6m_return is not None and vs_nifty_6m > 15:
                    score += 15
                    reasons.append("6M Nifty outperformance")

                if return_1m is not None and return_3m is not None and return_6m is not None:
                    if return_1m > 0 and return_3m > 0 and return_6m > 0:
                        score += 10
                        reasons.append("Positive across 1M/3M/6M")

                score = max(0, min(100, score))

                results.append({
                    "relative_scan_time": scan_time,
                    "symbol": symbol,
                    "return_1m": return_1m,
                    "return_3m": return_3m,
                    "return_6m": return_6m,
                    "nifty_1m_return": nifty_1m_return,
                    "nifty_3m_return": nifty_3m_return,
                    "nifty_6m_return": nifty_6m_return,
                    "return_vs_nifty_1m": vs_nifty_1m,
                    "return_vs_nifty_3m": vs_nifty_3m,
                    "return_vs_nifty_6m": vs_nifty_6m,
                    "relative_strength_score": score,
                    "relative_strength_reasons": ", ".join(reasons)
                })

            except Exception as e:
                print(f"{symbol} relative strength failed: {e}")

    except Exception as e:
        print(f"Relative strength chunk failed: {e}")

    time.sleep(2)


rs_df = pd.DataFrame(results)

if rs_df.empty:
    raise RuntimeError("Relative strength calculation produced no rows.")

sector_cols = ["symbol", "sector"]

if "industry" in scan_df.columns:
    sector_cols.append("industry")

rs_df = rs_df.merge(
    scan_df[sector_cols].drop_duplicates(subset=["symbol"]),
    on="symbol",
    how="left"
)

rs_df["sector"] = rs_df["sector"].fillna("Unknown")

rs_df["sector_rank"] = rs_df.groupby("sector")["relative_strength_score"].rank(
    ascending=False,
    method="dense"
)

rs_df["sector_count"] = rs_df.groupby("sector")["symbol"].transform("count")

rs_df["sector_rank_pct"] = round(
    (rs_df["sector_rank"] / rs_df["sector_count"]) * 100,
    2
)

rs_df.to_csv(OUTPUT_FILE, index=False)

print(f"Relative strength saved: {len(rs_df)} rows")
