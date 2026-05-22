from pathlib import Path
import shutil

# =========================
# StockGPT Range Bound v1 Installer
# Creates scanner + patches Phase6 workflow + dashboard + Telegram /range command
# Run from repo root: python install_range_bound_v1.py
# =========================

SCANNER_PATH = Path('app/scanners/range_bound_scanner.py')
WORKFLOW_PATH = Path('.github/workflows/phase6_pipeline.yml')
DASHBOARD_PATH = Path('app/dashboard/dashboard.py')
TELEGRAM_PATH = Path('app/alerts/telegram_bot_commands.py')

SCANNER_CODE = r'''import math
import time
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import yfinance as yf

SCAN_FILE = Path("data/scans/latest_scan.csv")
OUTPUT_FILE = Path("data/range/range_bound.csv")
FAILED_FILE = Path("data/range/failed_range_symbols.csv")
OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

SCAN_TIME = datetime.now(ZoneInfo("Asia/Kolkata")).strftime("%d.%m.%Y at %I:%M %p IST")
LOOKBACK_DAYS = 120
MIN_HISTORY_DAYS = 80
CHUNK_SIZE = 75


def safe_float(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        value = float(value)
        if math.isinf(value) or math.isnan(value):
            return default
        return value
    except Exception:
        return default


def clip(value, low=0, high=100):
    return max(low, min(high, value))


def score_linear(value, low, high):
    if high == low:
        return 0
    return clip(((value - low) / (high - low)) * 100)


def calculate_rsi(close, period=14):
    close = pd.Series(close).dropna()
    if len(close) < period + 2:
        return 50.0
    delta = close.diff()
    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()
    rs = gain / loss.replace(0, pd.NA)
    rsi = 100 - (100 / (1 + rs))
    valid = rsi.dropna()
    return safe_float(valid.iloc[-1], 50.0) if not valid.empty else 50.0


def load_scan():
    if not SCAN_FILE.exists():
        raise FileNotFoundError("data/scans/latest_scan.csv not found. Run Phase6 pipeline first.")
    df = pd.read_csv(SCAN_FILE)
    if df.empty or "symbol" not in df.columns:
        raise RuntimeError("latest_scan.csv is empty or missing symbol column.")
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    return df.drop_duplicates(subset=["symbol"])


def chunk_list(items, size):
    for i in range(0, len(items), size):
        yield items[i:i + size]


def get_symbol_history(downloaded, yf_symbol):
    if downloaded is None or downloaded.empty:
        return pd.DataFrame()
    if isinstance(downloaded.columns, pd.MultiIndex):
        try:
            if yf_symbol in downloaded.columns.get_level_values(1):
                hist = downloaded.xs(yf_symbol, axis=1, level=1, drop_level=True)
            elif yf_symbol in downloaded.columns.get_level_values(0):
                hist = downloaded.xs(yf_symbol, axis=1, level=0, drop_level=True)
            else:
                return pd.DataFrame()
        except Exception:
            return pd.DataFrame()
    else:
        hist = downloaded.copy()
    needed = ["Close", "High", "Low", "Volume"]
    for col in needed:
        if col not in hist.columns:
            return pd.DataFrame()
    return hist[needed].dropna(subset=["Close"])


def width_score(range_width_pct):
    range_width_pct = safe_float(range_width_pct)
    if range_width_pct < 4:
        return 10
    if range_width_pct < 8:
        return score_linear(range_width_pct, 4, 8) * 0.7
    if 8 <= range_width_pct <= 22:
        return 100
    if range_width_pct <= 30:
        return 80
    if range_width_pct <= 40:
        return 50
    return 20


def position_buy_score(position_pct):
    position_pct = safe_float(position_pct)
    if position_pct <= 15:
        return 100
    if position_pct <= 30:
        return 90
    if position_pct <= 45:
        return 65
    if position_pct <= 60:
        return 40
    if position_pct <= 75:
        return 20
    return 5


def bounce_score(current_price, close, rsi, volume_ratio):
    close = pd.Series(close).dropna()
    if len(close) < 8:
        return 40
    ret_3d = ((close.iloc[-1] / close.iloc[-4]) - 1) * 100 if len(close) >= 4 else 0
    ret_5d = ((close.iloc[-1] / close.iloc[-6]) - 1) * 100 if len(close) >= 6 else 0
    sma20 = close.tail(20).mean() if len(close) >= 20 else close.mean()
    score = 0
    score += 35 if 35 <= rsi <= 55 else 20 if (30 <= rsi < 35 or 55 < rsi <= 62) else 5
    score += 25 if ret_3d >= 0 else 15 if ret_3d > -2 else 5
    score += 25 if current_price >= sma20 * 0.98 else 15 if current_price >= sma20 * 0.95 else 5
    score += 15 if volume_ratio <= 1.5 else 8 if volume_ratio <= 2.2 else 2
    if ret_5d < -6 and volume_ratio > 1.5:
        score -= 20
    return clip(score)


def quality_risk_score(row):
    active = safe_float(row.get("active_fundamental_score", 0))
    final = safe_float(row.get("final_conviction_score", 0))
    risk = safe_float(row.get("risk_penalty", 0))
    score = active * 0.45 + final * 0.35 + (100 - clip(risk, 0, 100)) * 0.20
    if risk >= 30:
        score -= 20
    if active < 25:
        score -= 15
    return clip(score)


def analyse_symbol(symbol, hist, scan_row):
    hist = hist.tail(LOOKBACK_DAYS).copy()
    if len(hist) < MIN_HISTORY_DAYS:
        return None
    close = hist["Close"].dropna()
    high = hist["High"].dropna()
    low = hist["Low"].dropna()
    volume = hist["Volume"].dropna()
    if close.empty or high.empty or low.empty:
        return None

    current_price = safe_float(close.iloc[-1])
    absolute_low = safe_float(low.min())
    absolute_high = safe_float(high.max())

    # Robust bands reduce one-day spike effect.
    range_low = safe_float(close.quantile(0.10))
    range_high = safe_float(close.quantile(0.90))
    if range_low <= 0 or range_high <= range_low or current_price <= 0:
        return None

    range_width_pct = ((range_high - range_low) / range_low) * 100
    absolute_range_width_pct = ((absolute_high - absolute_low) / absolute_low) * 100 if absolute_low > 0 else 0
    current_position_pct = clip(((current_price - range_low) / (range_high - range_low)) * 100)
    upside_to_range_high_pct = ((range_high - current_price) / current_price) * 100
    downside_to_range_low_pct = ((current_price - range_low) / current_price) * 100

    inside_range_days = ((close >= range_low) & (close <= range_high)).sum()
    inside_range_pct = (inside_range_days / len(close)) * 100
    lower_touch_days = (close <= range_low * 1.03).sum()
    upper_touch_days = (close >= range_high * 0.97).sum()

    avg_volume_20 = safe_float(volume.tail(20).mean(), 0)
    latest_volume = safe_float(volume.iloc[-1], 0)
    volume_ratio = latest_volume / avg_volume_20 if avg_volume_20 > 0 else safe_float(scan_row.get("volume_ratio", 1), 1)
    rsi = calculate_rsi(close)

    stability_score = score_linear(inside_range_pct, 55, 85)
    touch_score = (50 if lower_touch_days >= 2 else 0) + (50 if upper_touch_days >= 2 else 0)
    range_stability_score = clip(stability_score * 0.75 + touch_score * 0.25)
    rw_score = width_score(range_width_pct)
    pos_score = position_buy_score(current_position_pct)
    b_score = bounce_score(current_price, close, rsi, volume_ratio)
    qr_score = quality_risk_score(scan_row)

    breakdown_buffer_pct = ((current_price - range_low) / range_low) * 100
    breakout_buffer_pct = ((current_price - range_high) / range_high) * 100
    is_breakdown = current_price < range_low * 0.97 and volume_ratio >= 1.3
    is_breakout = current_price > range_high * 1.03 and volume_ratio >= 1.3

    range_score = range_stability_score * 0.25 + rw_score * 0.20 + pos_score * 0.25 + b_score * 0.15 + qr_score * 0.15

    if is_breakdown:
        range_status = "Range Breakdown Risk"
        range_score = min(range_score, 35)
    elif is_breakout:
        range_status = "Range Breakout Watch"
        range_score = max(range_score, 55)
    elif range_stability_score < 45:
        range_status = "Not Range Bound"
        range_score = min(range_score, 50)
    elif current_position_pct <= 30 and range_score >= 65:
        range_status = "Accumulation Zone"
    elif current_position_pct <= 45:
        range_status = "Lower Range Watch"
    elif current_position_pct >= 75:
        range_status = "Profit Booking Zone"
    else:
        range_status = "Neutral Range"

    if range_width_pct < 5:
        range_status = "Too Narrow Range"
        range_score = min(range_score, 45)
    if range_width_pct > 40:
        range_status = "Wide / Volatile Range"
        range_score = min(range_score, 50)

    range_reasons = [
        f"{inside_range_pct:.1f}% closes stayed inside robust range",
        f"Range width is {range_width_pct:.1f}%",
        f"Current position is {current_position_pct:.1f}% inside range",
        f"Upside to range high is {upside_to_range_high_pct:.1f}%",
        f"Downside to range low is {downside_to_range_low_pct:.1f}%",
    ]
    if is_breakdown:
        range_reasons.append("Price is below lower range with elevated volume")
    if is_breakout:
        range_reasons.append("Price is above upper range with elevated volume")
    if current_position_pct <= 30:
        range_reasons.append("Stock is near lower band")
    if current_position_pct >= 75:
        range_reasons.append("Stock is near upper band")
    if 35 <= rsi <= 55:
        range_reasons.append("RSI is in a reasonable range-bound zone")

    return {
        "range_scan_time": SCAN_TIME,
        "symbol": symbol,
        "range_status": range_status,
        "range_score": round(range_score, 2),
        "range_low": round(range_low, 2),
        "range_high": round(range_high, 2),
        "absolute_range_low": round(absolute_low, 2),
        "absolute_range_high": round(absolute_high, 2),
        "range_width_pct": round(range_width_pct, 2),
        "absolute_range_width_pct": round(absolute_range_width_pct, 2),
        "current_position_pct": round(current_position_pct, 2),
        "upside_to_range_high_pct": round(upside_to_range_high_pct, 2),
        "downside_to_range_low_pct": round(downside_to_range_low_pct, 2),
        "inside_range_pct": round(inside_range_pct, 2),
        "lower_touch_days": int(lower_touch_days),
        "upper_touch_days": int(upper_touch_days),
        "range_stability_score": round(range_stability_score, 2),
        "range_width_score": round(rw_score, 2),
        "range_position_score": round(pos_score, 2),
        "range_bounce_score": round(b_score, 2),
        "range_quality_risk_score": round(qr_score, 2),
        "range_rsi": round(rsi, 2),
        "range_volume_ratio": round(volume_ratio, 2),
        "range_breakdown_buffer_pct": round(breakdown_buffer_pct, 2),
        "range_breakout_buffer_pct": round(breakout_buffer_pct, 2),
        "is_range_breakdown": bool(is_breakdown),
        "is_range_breakout": bool(is_breakout),
        "range_reasons": " | ".join(range_reasons),
    }


def main():
    scan_df = load_scan()
    symbols = scan_df["symbol"].dropna().astype(str).str.upper().str.strip().unique().tolist()
    scan_lookup = scan_df.set_index("symbol").to_dict(orient="index")
    print(f"Starting range-bound scanner for {len(symbols)} stocks")
    print(f"Range scan time: {SCAN_TIME}")

    results = []
    failed = []
    for chunk in chunk_list(symbols, CHUNK_SIZE):
        yf_symbols = [symbol + ".NS" for symbol in chunk]
        print(f"Downloading range chunk: {chunk[0]} to {chunk[-1]}")
        try:
            downloaded = yf.download(yf_symbols, period="8mo", interval="1d", group_by="ticker", auto_adjust=False, threads=True, progress=False)
        except Exception as e:
            print(f"Chunk download failed: {chunk[0]} to {chunk[-1]} | {e}")
            failed.extend(chunk)
            time.sleep(2)
            continue

        for symbol in chunk:
            try:
                hist = get_symbol_history(downloaded, symbol + ".NS")
                if hist.empty:
                    failed.append(symbol)
                    continue
                result = analyse_symbol(symbol, hist, scan_lookup.get(symbol, {}))
                if result:
                    results.append(result)
                else:
                    failed.append(symbol)
            except Exception as e:
                print(f"{symbol} range analysis failed: {e}")
                failed.append(symbol)
        time.sleep(0.8)

    range_df = pd.DataFrame(results)
    pd.DataFrame({"symbol": sorted(set(failed))}).to_csv(FAILED_FILE, index=False)
    if range_df.empty:
        raise RuntimeError("No range-bound results generated.")
    range_df = range_df.drop_duplicates(subset=["symbol"])
    range_df.to_csv(OUTPUT_FILE, index=False)
    print(f"Range results saved: {len(range_df)} rows")
    print(f"Failed range symbols: {len(set(failed))}")

    merged = scan_df.merge(range_df, on="symbol", how="left", suffixes=("", "_range"))
    merged.to_csv(SCAN_FILE, index=False)
    print(f"latest_scan.csv enriched with range columns: {len(merged)} rows")


if __name__ == "__main__":
    main()
'''

DASHBOARD_TAB_CODE = r'''

# =========================
# TAB 10 — RANGE BOUND
# =========================

with tab10:
    st.header("📦 Range Bound / Mean Reversion Scanner")

    range_file = Path("data/range/range_bound.csv")

    if not range_file.exists():
        st.warning("Range-bound file not found. Run Phase6 Pipeline after adding range_bound_scanner.py.")
    else:
        range_df = pd.read_csv(range_file)

        if range_df.empty:
            st.info("Range-bound file exists but has no rows.")
        else:
            range_df["symbol"] = range_df["symbol"].astype(str).str.upper().str.strip()

            if "range_scan_time" in range_df.columns and not range_df["range_scan_time"].dropna().empty:
                st.caption(f"🕒 Range scan updated on {range_df['range_scan_time'].dropna().iloc[0]}")

            latest_cols = [
                "symbol", "sector", "industry", "sector_bucket", "current_price",
                "final_conviction_score", "technical_score", "active_fundamental_score",
                "relative_strength_score", "risk_penalty", "score_band"
            ]

            available_latest_cols = [col for col in latest_cols if col in df.columns]

            range_view = range_df.merge(
                df[available_latest_cols].drop_duplicates(subset=["symbol"]),
                on="symbol",
                how="left"
            )

            numeric_range_cols = [
                "range_score", "range_low", "range_high", "range_width_pct",
                "current_position_pct", "upside_to_range_high_pct",
                "downside_to_range_low_pct", "inside_range_pct", "range_stability_score",
                "range_width_score", "range_position_score", "range_bounce_score",
                "range_quality_risk_score", "range_rsi", "range_volume_ratio",
                "final_conviction_score", "active_fundamental_score", "risk_penalty"
            ]

            for col in numeric_range_cols:
                if col not in range_view.columns:
                    range_view[col] = 0
                range_view[col] = pd.to_numeric(range_view[col], errors="coerce").fillna(0)

            for col in ["sector", "industry", "sector_bucket", "range_status", "range_reasons"]:
                if col not in range_view.columns:
                    range_view[col] = "Unknown"
                range_view[col] = range_view[col].fillna("Unknown").astype(str)

            st.subheader("Range Filters")
            r1, r2, r3 = st.columns(3)

            with r1:
                selected_range_status = st.multiselect(
                    "Range Status",
                    sorted(range_view["range_status"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Leave blank for all",
                    key="range_status_filter"
                )

            with r2:
                selected_range_sector = st.multiselect(
                    "Sector Bucket",
                    sorted(range_view["sector_bucket"].dropna().unique().tolist()),
                    default=[],
                    placeholder="Leave blank for all",
                    key="range_sector_filter"
                )

            with r3:
                range_search = st.text_input(
                    "Search Symbol",
                    placeholder="Example: RECLTD, PFC, RELIANCE",
                    key="range_search"
                )

            r4, r5, r6 = st.columns(3)
            with r4:
                range_score_min, range_score_max = safe_range_slider("Range Score", range_view["range_score"], step=1.0, key="range_score_slider", sidebar=False)
            with r5:
                position_min, position_max = safe_range_slider("Current Position Inside Range %", range_view["current_position_pct"], step=1.0, key="range_position_slider", sidebar=False)
            with r6:
                width_min, width_max = safe_range_slider("Range Width %", range_view["range_width_pct"], step=1.0, key="range_width_slider", sidebar=False)

            filtered_range = range_view.copy()
            if selected_range_status:
                filtered_range = filtered_range[filtered_range["range_status"].isin(selected_range_status)]
            if selected_range_sector:
                filtered_range = filtered_range[filtered_range["sector_bucket"].isin(selected_range_sector)]
            if range_search.strip():
                filtered_range = filtered_range[filtered_range["symbol"].str.contains(range_search.strip().upper(), case=False, na=False)]

            filtered_range = filtered_range[filtered_range["range_score"].between(range_score_min, range_score_max)]
            filtered_range = filtered_range[filtered_range["current_position_pct"].between(position_min, position_max)]
            filtered_range = filtered_range[filtered_range["range_width_pct"].between(width_min, width_max)]

            st.caption(f"Showing {len(filtered_range)} out of {len(range_view)} range rows")

            range_cols = [
                "symbol", "sector", "industry", "sector_bucket", "current_price",
                "range_status", "range_score", "range_low", "range_high", "range_width_pct",
                "current_position_pct", "upside_to_range_high_pct", "downside_to_range_low_pct",
                "inside_range_pct", "range_rsi", "range_volume_ratio", "final_conviction_score",
                "active_fundamental_score", "relative_strength_score", "risk_penalty", "score_band", "range_reasons"
            ]

            st.subheader("🟢 Accumulation Zone")
            accumulation = filtered_range[
                filtered_range["range_status"].isin(["Accumulation Zone", "Lower Range Watch"])
            ].sort_values(["range_score", "upside_to_range_high_pct"], ascending=[False, False])
            display_table(accumulation, range_cols)

            st.subheader("🟡 Profit Booking Zone")
            profit_zone = filtered_range[filtered_range["range_status"] == "Profit Booking Zone"].sort_values(["current_position_pct", "range_score"], ascending=[False, False])
            display_table(profit_zone, range_cols)

            st.subheader("🔴 Breakdown / Volatility Risk")
            risk_zone = filtered_range[
                filtered_range["range_status"].isin(["Range Breakdown Risk", "Wide / Volatile Range", "Not Range Bound"])
            ].sort_values(["risk_penalty", "range_score"], ascending=[False, True])
            display_table(risk_zone, range_cols)

            st.subheader("📋 Full Range Bound Table")
            display_table(filtered_range.sort_values("range_score", ascending=False), range_cols)
'''

TELEGRAM_RANGE_CODE = r'''

def command_range(df, text):
    range_file = Path("data/range/range_bound.csv")
    if not range_file.exists():
        return "Range-bound data not found. Run Phase6 Pipeline first."

    range_df = pd.read_csv(range_file)
    if range_df.empty:
        return "Range-bound data file exists but has no rows."

    range_df["symbol"] = range_df["symbol"].astype(str).str.upper().str.strip()
    parts = text.strip().split()

    if len(parts) >= 2:
        symbol = parts[1].upper().strip()
        stock_df = range_df[range_df["symbol"] == symbol]
        if stock_df.empty:
            matches = range_df[range_df["symbol"].str.contains(symbol, case=False, na=False)]
            if matches.empty:
                return f"<b>{escape_html(symbol)}</b> not found in range-bound data."
            suggestions = ", ".join(matches["symbol"].head(10).tolist())
            return f"<b>{escape_html(symbol)}</b> not found exactly.\nPossible matches: {escape_html(suggestions)}"

        row = stock_df.iloc[0]
        message = f"<b>📦 Range Snapshot: {escape_html(symbol)}</b>\n"
        message += f"Status: <b>{escape_html(row.get('range_status', ''))}</b>\n"
        message += f"Range Score: {safe_num(row.get('range_score')):.1f}\n"
        message += f"Range Low: ₹{safe_num(row.get('range_low')):.2f}\n"
        message += f"Range High: ₹{safe_num(row.get('range_high')):.2f}\n"
        message += f"Range Width: {safe_num(row.get('range_width_pct')):.1f}%\n"
        message += f"Current Position: {safe_num(row.get('current_position_pct')):.1f}% inside range\n"
        message += f"Upside to Range High: {safe_num(row.get('upside_to_range_high_pct')):.1f}%\n"
        message += f"Downside to Range Low: {safe_num(row.get('downside_to_range_low_pct')):.1f}%\n"
        message += f"Inside Range Days: {safe_num(row.get('inside_range_pct')):.1f}%\n"
        message += f"Range RSI: {safe_num(row.get('range_rsi')):.1f}\n"
        message += f"Range Volume Ratio: {safe_num(row.get('range_volume_ratio')):.2f}x\n\n"
        reasons = clean_text(row.get("range_reasons", ""))
        if reasons:
            message += f"<b>Range Reasons</b>\n{escape_html(reasons[:1200])}\n\n"
        message += "<i>Not financial advice. Research tool only.</i>"
        return message.strip()

    top = range_df[range_df["range_status"].isin(["Accumulation Zone", "Lower Range Watch"])].sort_values(["range_score", "upside_to_range_high_pct"], ascending=[False, False]).head(10)
    if top.empty:
        top = range_df.sort_values("range_score", ascending=False).head(10)

    message = "<b>📦 Top Range Bound Opportunities</b>\n"
    for _, row in top.iterrows():
        message += (
            f"\n<b>{escape_html(row.get('symbol', ''))}</b> | {escape_html(row.get('range_status', ''))}\n"
            f"Score: {safe_num(row.get('range_score')):.1f} | Position: {safe_num(row.get('current_position_pct')):.1f}% | Width: {safe_num(row.get('range_width_pct')):.1f}%\n"
            f"Low: ₹{safe_num(row.get('range_low')):.2f} | High: ₹{safe_num(row.get('range_high')):.2f} | Upside: {safe_num(row.get('upside_to_range_high_pct')):.1f}%"
        )
    message += "\n\nUse /range SYMBOL for details. Example: /range RECLTD"
    message += "\n\n<i>Not financial advice. Research tool only.</i>"
    return message.strip()
'''

def backup(path: Path, suffix: str):
    if path.exists():
        shutil.copy2(path, path.with_suffix(path.suffix + suffix))

# 1 scanner file
SCANNER_PATH.parent.mkdir(parents=True, exist_ok=True)
SCANNER_PATH.write_text(SCANNER_CODE, encoding='utf-8')
print(f'✅ Wrote {SCANNER_PATH}')

# 2 workflow patch
if WORKFLOW_PATH.exists():
    backup(WORKFLOW_PATH, '.bak_range_bound')
    text = WORKFLOW_PATH.read_text(encoding='utf-8')
    if 'Run Range Bound Scanner' not in text:
        marker = '      - name: Run Final Score Engine\n        run: python app/scoring/score_engine.py\n\n'
        step = '      - name: Run Range Bound Scanner\n        run: python app/scanners/range_bound_scanner.py\n\n'
        if marker not in text:
            raise RuntimeError('Could not find Run Final Score Engine step in phase6_pipeline.yml')
        text = text.replace(marker, marker + step, 1)
        WORKFLOW_PATH.write_text(text, encoding='utf-8')
        print('✅ Added Range Bound Scanner step to Phase6 workflow')
    else:
        print('ℹ️ Phase6 workflow already has Range Bound step')
else:
    print('⚠️ phase6_pipeline.yml not found, skipped workflow patch')

# 3 dashboard patch
if DASHBOARD_PATH.exists():
    backup(DASHBOARD_PATH, '.bak_range_bound')
    text = DASHBOARD_PATH.read_text(encoding='utf-8')
    if 'Range Bound / Mean Reversion Scanner' not in text:
        old_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9 = st.tabs(['
        new_tabs = 'tab1, tab2, tab3, tab4, tab5, tab6, tab7, tab8, tab9, tab10 = st.tabs(['
        if old_tabs not in text:
            raise RuntimeError('Could not find 9-tab dashboard assignment. Dashboard may already be customized.')
        text = text.replace(old_tabs, new_tabs, 1)
        old_last = '    "Movers & Changes"\n])'
        new_last = '    "Movers & Changes",\n    "Range Bound"\n])'
        if old_last not in text:
            raise RuntimeError('Could not find Movers & Changes tab ending.')
        text = text.replace(old_last, new_last, 1)
        text += DASHBOARD_TAB_CODE
        DASHBOARD_PATH.write_text(text, encoding='utf-8')
        print('✅ Added Range Bound dashboard tab')
    else:
        print('ℹ️ Dashboard already has Range Bound tab')
else:
    print('⚠️ dashboard.py not found, skipped dashboard patch')

# 4 telegram patch
if TELEGRAM_PATH.exists():
    backup(TELEGRAM_PATH, '.bak_range_bound')
    text = TELEGRAM_PATH.read_text(encoding='utf-8')
    if 'def command_range' not in text:
        marker = 'COMMANDS = {'
        if marker not in text:
            raise RuntimeError('Could not find COMMANDS dictionary in telegram_bot_commands.py. Use v3 bot first.')
        text = text.replace(marker, TELEGRAM_RANGE_CODE + '\n' + marker, 1)
        if '    "/range": command_range,\n' not in text:
            text = text.replace('    "/risk": command_risk,\n', '    "/risk": command_risk,\n    "/range": command_range,\n', 1)
        text = text.replace('/risk - Avoid / risky stocks\n', '/risk - Avoid / risky stocks\n/range - Top range-bound opportunities\n/range SYMBOL - Range snapshot for one stock\n', 1)
        TELEGRAM_PATH.write_text(text, encoding='utf-8')
        print('✅ Added Telegram /range command')
    else:
        print('ℹ️ Telegram already has /range command')
else:
    print('⚠️ telegram_bot_commands.py not found, skipped Telegram patch')

print('\nNext checks:')
print('python -m py_compile app/scanners/range_bound_scanner.py')
print('python -m py_compile app/dashboard/dashboard.py')
print('python -m py_compile app/alerts/telegram_bot_commands.py')
