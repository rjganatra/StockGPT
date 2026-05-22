import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCAN_FILE = "data/scans/latest_scan.csv"
FAILED_FILE = "data/scans/failed_symbols.csv"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat id missing. Skipping alert.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        response = requests.post(
            url,
            json=payload,
            timeout=20
        )

        if response.status_code != 200:
            print(f"Telegram send failed: {response.text}")
            return False

        return True

    except Exception as e:
        print(f"Telegram error: {e}")
        return False


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_df(df):
    df = df.copy()

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    text_cols = [
        "sector",
        "industry",
        "trend",
        "score_band",
        "reasons"
    ]

    for col in text_cols:
        if col not in df.columns:
            df[col] = "Unknown" if col != "reasons" else ""

        df[col] = df[col].fillna("Unknown" if col != "reasons" else "").astype(str)

    numeric_cols = [
        "current_price",
        "day_change_pct",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "volume_ratio",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
        "final_conviction_score",
        "return_1m",
        "return_3m",
        "return_6m"
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


def format_stock_line(row):
    return (
        f"<b>{row['symbol']}</b> | "
        f"₹{safe_num(row.get('current_price')):.2f} | "
        f"Score: {safe_num(row.get('final_conviction_score')):.1f} | "
        f"RSI: {safe_num(row.get('rsi')):.1f} | "
        f"{row.get('sector', 'Unknown')}"
    )


def format_table(title, data, max_rows=5):
    if data.empty:
        return ""

    lines = [f"\n<b>{title}</b>"]

    for _, row in data.head(max_rows).iterrows():
        lines.append(format_stock_line(row))

    return "\n".join(lines)


def build_alert_message(df):
    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d.%m.%Y at %I:%M %p IST")

    scan_time = "Unavailable"

    if "scan_time" in df.columns and not df["scan_time"].dropna().empty:
        scan_time = str(df["scan_time"].dropna().iloc[0])

    high_conviction = df[
        df["final_conviction_score"] >= 70
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    swing = df[
        (df["distance_pct"] <= 25)
        &
        (df["rsi"] <= 45)
        &
        (df["volume_ratio"] >= 1.0)
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    low_quality = df[
        (df["distance_pct"] <= 20)
        &
        (df["fundamental_score"] >= 55)
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    high_momentum = df[
        (df["distance_from_high_pct"] <= 15)
        &
        (df["rsi"] >= 50)
        &
        (df["trend"] == "Bullish")
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    volume_breakout = df[
        df["volume_ratio"] >= 2
    ].sort_values(
        "final_conviction_score",
        ascending=False
    )

    risk_warning = df[
        (df["risk_penalty"] >= 25)
        |
        (df["day_change_pct"] <= -5)
    ].sort_values(
        "risk_penalty",
        ascending=False
    )

    failed_count = 0

    if Path(FAILED_FILE).exists():
        try:
            failed_df = pd.read_csv(FAILED_FILE)
            failed_count = len(failed_df)
        except Exception:
            failed_count = 0

    message = f"""
<b>📈 StockGPT Market Alert</b>

<b>Generated:</b> {now}
<b>Scan Time:</b> {scan_time}

<b>Stocks Scanned:</b> {len(df)}
<b>High Conviction:</b> {len(high_conviction)}
<b>Swing Candidates:</b> {len(swing)}
<b>52W Low + Strong Fundamentals:</b> {len(low_quality)}
<b>Near 52W High Momentum:</b> {len(high_momentum)}
<b>Volume Breakouts:</b> {len(volume_breakout)}
<b>Risk Warnings:</b> {len(risk_warning)}
<b>Failed Symbols:</b> {failed_count}
""".strip()

    message += format_table(
        "🚀 High Conviction",
        high_conviction,
        max_rows=5
    )

    message += format_table(
        "⚡ Swing Candidates",
        swing,
        max_rows=5
    )

    message += format_table(
        "🎯 52W Low + Strong Fundamentals",
        low_quality,
        max_rows=5
    )

    message += format_table(
        "📈 Near 52W High Momentum",
        high_momentum,
        max_rows=5
    )

    message += format_table(
        "🔥 Volume Breakouts",
        volume_breakout,
        max_rows=5
    )

    message += format_table(
        "⚠️ Risk Warnings",
        risk_warning,
        max_rows=5
    )

    message += "\n\n<i>Not financial advice. Use StockGPT for research only.</i>"

    return message


def main():
    if not Path(SCAN_FILE).exists():
        send_telegram_message(
            "❌ StockGPT alert failed: latest_scan.csv not found."
        )
        raise FileNotFoundError("latest_scan.csv not found")

    df = pd.read_csv(SCAN_FILE)

    if df.empty:
        send_telegram_message(
            "❌ StockGPT alert failed: latest_scan.csv is empty."
        )
        raise RuntimeError("latest_scan.csv is empty")

    df = clean_df(df)

    message = build_alert_message(df)

    # Telegram limit is around 4096 characters.
    # Keep safe by trimming.
    if len(message) > 3900:
        message = message[:3900] + "\n\n<i>Message trimmed due to Telegram limit.</i>"

    ok = send_telegram_message(message)

    if ok:
        print("Telegram alert sent.")
    else:
        print("Telegram alert not sent.")


if __name__ == "__main__":
    main()
