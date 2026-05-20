import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

SCAN_FILE = "data/scans/latest_scan.csv"
WATCHLIST_FILE = "data/watchlist/watchlist.csv"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat id missing. Skipping watchlist alert.")
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


def clean_scan(scan_df):
    scan_df = scan_df.copy()

    scan_df["symbol"] = (
        scan_df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    text_cols = [
        "sector",
        "industry",
        "trend",
        "score_band",
        "reasons",
        "technical_reasons",
        "fundamental_reasons",
        "relative_strength_reasons",
        "risk_reasons",
        "fundamental_risks"
    ]

    for col in text_cols:
        if col not in scan_df.columns:
            scan_df[col] = ""

        scan_df[col] = scan_df[col].fillna("").astype(str)

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
        if col not in scan_df.columns:
            scan_df[col] = 0

        scan_df[col] = pd.to_numeric(
            scan_df[col],
            errors="coerce"
        ).fillna(0)

    return scan_df


def clean_watchlist(watchlist_df):
    watchlist_df = watchlist_df.copy()

    required_cols = [
        "symbol",
        "basket",
        "notes",
        "added_at"
    ]

    for col in required_cols:
        if col not in watchlist_df.columns:
            watchlist_df[col] = ""

    watchlist_df["symbol"] = (
        watchlist_df["symbol"]
        .astype(str)
        .str.upper()
        .str.strip()
    )

    watchlist_df["basket"] = watchlist_df["basket"].fillna("").astype(str)
    watchlist_df["notes"] = watchlist_df["notes"].fillna("").astype(str)
    watchlist_df["added_at"] = watchlist_df["added_at"].fillna("").astype(str)

    watchlist_df = watchlist_df.dropna(subset=["symbol"])
    watchlist_df = watchlist_df[watchlist_df["symbol"] != ""]

    return watchlist_df


def get_alert_reasons(row):
    reasons = []

    final_score = safe_num(row.get("final_conviction_score"))
    rsi = safe_num(row.get("rsi"))
    volume_ratio = safe_num(row.get("volume_ratio"))
    distance_pct = safe_num(row.get("distance_pct"))
    distance_from_high_pct = safe_num(row.get("distance_from_high_pct"))
    risk_penalty = safe_num(row.get("risk_penalty"))
    fundamental_score = safe_num(row.get("fundamental_score"))
    relative_strength_score = safe_num(row.get("relative_strength_score"))
    day_change_pct = safe_num(row.get("day_change_pct"))
    score_band = str(row.get("score_band", ""))

    if final_score >= 75:
        reasons.append("A+ high conviction")
    elif final_score >= 65:
        reasons.append("Strong conviction score")

    if "A+" in score_band or "A Strong" in score_band:
        reasons.append(f"Score band: {score_band}")

    if fundamental_score >= 70:
        reasons.append("Strong fundamentals")

    if relative_strength_score >= 65:
        reasons.append("Strong relative strength")

    if volume_ratio >= 2:
        reasons.append("Volume breakout")

    if distance_pct <= 15:
        reasons.append("Near 52W low")

    if distance_from_high_pct <= 15 and rsi >= 50:
        reasons.append("Near 52W high momentum")

    if rsi <= 35:
        reasons.append("Oversold RSI")

    if rsi >= 70:
        reasons.append("Overbought RSI")

    if risk_penalty >= 25:
        reasons.append("High risk penalty")

    if day_change_pct <= -5:
        reasons.append("Sharp fall today")

    return reasons


def format_watchlist_stock(row):
    symbol = row.get("symbol", "")
    basket = row.get("basket", "")
    current_price = safe_num(row.get("current_price"))
    final_score = safe_num(row.get("final_conviction_score"))
    fundamental_score = safe_num(row.get("fundamental_score"))
    relative_strength_score = safe_num(row.get("relative_strength_score"))
    risk_penalty = safe_num(row.get("risk_penalty"))
    rsi = safe_num(row.get("rsi"))
    volume_ratio = safe_num(row.get("volume_ratio"))
    distance_pct = safe_num(row.get("distance_pct"))
    distance_from_high_pct = safe_num(row.get("distance_from_high_pct"))
    sector = row.get("sector", "Unknown")
    industry = row.get("industry", "Unknown")
    score_band = row.get("score_band", "Unknown")
    notes = str(row.get("notes", "")).strip()

    alert_reasons = get_alert_reasons(row)

    reason_text = ", ".join(alert_reasons)

    if not reason_text:
        reason_text = "Watchlist stock update"

    msg = (
        f"\n<b>{symbol}</b> | {basket}\n"
        f"Price: ₹{current_price:.2f} | Score: {final_score:.1f} | {score_band}\n"
        f"RSI: {rsi:.1f} | Volume: {volume_ratio:.2f}x | Risk: {risk_penalty:.1f}\n"
        f"Fundamental: {fundamental_score:.1f} | Relative Strength: {relative_strength_score:.1f}\n"
        f"52W Low Dist: {distance_pct:.1f}% | 52W High Dist: {distance_from_high_pct:.1f}%\n"
        f"Sector: {sector} | Industry: {industry}\n"
        f"Reason: {reason_text}"
    )

    if notes:
        msg += f"\nNote: {notes}"

    return msg


def build_watchlist_alert_message(merged_df, missing_df):
    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d.%m.%Y at %I:%M %p IST")

    scan_time = "Unavailable"

    if "scan_time" in merged_df.columns and not merged_df["scan_time"].dropna().empty:
        scan_time = str(merged_df["scan_time"].dropna().iloc[0])

    merged_df["alert_reasons_list"] = merged_df.apply(
        get_alert_reasons,
        axis=1
    )

    alert_df = merged_df[
        merged_df["alert_reasons_list"].apply(lambda x: len(x) > 0)
    ].copy()

    alert_df = alert_df.sort_values(
        [
            "final_conviction_score",
            "risk_penalty",
            "volume_ratio"
        ],
        ascending=[False, False, False]
    )

    message = f"""
<b>⭐ StockGPT Watchlist Alerts</b>

<b>Generated:</b> {now}
<b>Scan Time:</b> {scan_time}

<b>Total Watchlist Items:</b> {len(merged_df) + len(missing_df)}
<b>Matched in Latest Scan:</b> {len(merged_df)}
<b>Triggered Alerts:</b> {len(alert_df)}
<b>Missing from Latest Scan:</b> {len(missing_df)}
""".strip()

    if alert_df.empty:
        message += "\n\nNo watchlist stocks triggered alert conditions."
    else:
        top_alerts = alert_df.head(10)

        message += "\n\n<b>Triggered Watchlist Stocks</b>"

        for _, row in top_alerts.iterrows():
            message += format_watchlist_stock(row)

    if not missing_df.empty:
        message += "\n\n<b>Missing Watchlist Symbols</b>"

        missing_symbols = (
            missing_df["symbol"]
            .dropna()
            .astype(str)
            .str.upper()
            .unique()
            .tolist()
        )

        message += "\n" + ", ".join(missing_symbols[:20])

        if len(missing_symbols) > 20:
            message += f"\n...and {len(missing_symbols) - 20} more."

    message += "\n\n<i>Not financial advice. Use StockGPT for research only.</i>"

    return message


def main():
    if not Path(SCAN_FILE).exists():
        send_telegram_message(
            "❌ StockGPT watchlist alert failed: latest_scan.csv not found."
        )
        raise FileNotFoundError("latest_scan.csv not found")

    if not Path(WATCHLIST_FILE).exists():
        print("Watchlist file not found. Skipping watchlist alerts.")
        return

    scan_df = pd.read_csv(SCAN_FILE)
    watchlist_df = pd.read_csv(WATCHLIST_FILE)

    if scan_df.empty:
        send_telegram_message(
            "❌ StockGPT watchlist alert failed: latest_scan.csv is empty."
        )
        raise RuntimeError("latest_scan.csv is empty")

    if watchlist_df.empty:
        print("Watchlist is empty. Skipping watchlist alerts.")
        return

    scan_df = clean_scan(scan_df)
    watchlist_df = clean_watchlist(watchlist_df)

    merged = watchlist_df.merge(
        scan_df,
        on="symbol",
        how="left",
        suffixes=("", "_scan")
    )

    matched = merged[
        merged["current_price"].notna()
    ].copy()

    missing = merged[
        merged["current_price"].isna()
    ].copy()

    if matched.empty:
        send_telegram_message(
            "⚠️ StockGPT watchlist alert: No watchlist stocks matched latest scan."
        )
        return

    message = build_watchlist_alert_message(
        matched,
        missing
    )

    if len(message) > 3900:
        message = message[:3900] + "\n\n<i>Message trimmed due to Telegram limit.</i>"

    ok = send_telegram_message(message)

    if ok:
        print("Watchlist Telegram alert sent.")
    else:
        print("Watchlist Telegram alert not sent.")


if __name__ == "__main__":
    main()
