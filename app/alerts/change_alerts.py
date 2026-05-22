import os
import requests
import pandas as pd
from pathlib import Path
from datetime import datetime
from zoneinfo import ZoneInfo

def parse_chat_ids(value):
    return [
        str(chat_id).strip()
        for chat_id in str(value).replace("\\n", ",").split(",")
        if str(chat_id).strip()
    ]

CHANGES_FILE = "data/history/latest_changes.csv"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")
TELEGRAM_CHAT_IDS = parse_chat_ids(TELEGRAM_CHAT_ID)



def send_telegram_message(message):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("Telegram token/chat id missing. Skipping change alert.")
        return False

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    try:
        success_count = 0

        for chat_id in TELEGRAM_CHAT_IDS:

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


def clean_changes(df):
    df = df.copy()

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    text_cols = [
        "sector",
        "industry",
        "previous_score_band",
        "current_score_band",
        "change_signal"
    ]

    for col in text_cols:
        if col not in df.columns:
            df[col] = "Unknown"

        df[col] = df[col].fillna("Unknown").astype(str)

    numeric_cols = [
        "current_price",
        "previous_final_score",
        "current_final_score",
        "score_change",
        "previous_rsi",
        "current_rsi",
        "rsi_change",
        "previous_risk",
        "current_risk",
        "risk_change",
        "technical_score",
        "fundamental_score",
        "relative_strength_score",
        "volume_ratio",
        "distance_pct",
        "distance_from_high_pct"
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


def stock_line(row):
    return (
        f"\n<b>{row['symbol']}</b> | ₹{safe_num(row.get('current_price')):.2f}\n"
        f"Score: {safe_num(row.get('previous_final_score')):.1f} → "
        f"{safe_num(row.get('current_final_score')):.1f} "
        f"({safe_num(row.get('score_change')):+.1f})\n"
        f"RSI: {safe_num(row.get('previous_rsi')):.1f} → "
        f"{safe_num(row.get('current_rsi')):.1f} "
        f"({safe_num(row.get('rsi_change')):+.1f})\n"
        f"Risk: {safe_num(row.get('previous_risk')):.1f} → "
        f"{safe_num(row.get('current_risk')):.1f} "
        f"({safe_num(row.get('risk_change')):+.1f})\n"
        f"Band: {row.get('previous_score_band', 'Unknown')} → "
        f"{row.get('current_score_band', 'Unknown')}\n"
        f"Signal: {row.get('change_signal', 'Unknown')}"
    )


def section(title, data, max_rows=5):
    if data.empty:
        return ""

    message = f"\n\n<b>{title}</b>"

    for _, row in data.head(max_rows).iterrows():
        message += stock_line(row)

    return message


def build_message(df):
    now = datetime.now(
        ZoneInfo("Asia/Kolkata")
    ).strftime("%d.%m.%Y at %I:%M %p IST")

    change_time = "Unavailable"

    if "change_scan_time" in df.columns and not df["change_scan_time"].dropna().empty:
        change_time = str(df["change_scan_time"].dropna().iloc[0])

    new_high_conviction = df[
        df["change_signal"].str.contains(
            "New High Conviction",
            case=False,
            na=False
        )
    ].sort_values(
        "current_final_score",
        ascending=False
    )

    entered_strong = df[
        df["change_signal"].str.contains(
            "Entered Strong Zone",
            case=False,
            na=False
        )
    ].sort_values(
        "current_final_score",
        ascending=False
    )

    score_improved = df[
        df["score_change"] >= 8
    ].sort_values(
        "score_change",
        ascending=False
    )

    score_dropped = df[
        df["score_change"] <= -8
    ].sort_values(
        "score_change",
        ascending=True
    )

    risk_increased = df[
        df["change_signal"].str.contains(
            "Risk Increased|New Risk Warning",
            case=False,
            na=False
        )
    ].sort_values(
        "risk_change",
        ascending=False
    )

    rsi_recovery = df[
        df["change_signal"].str.contains(
            "RSI Recovery|Fresh Momentum",
            case=False,
            na=False
        )
    ].sort_values(
        "rsi_change",
        ascending=False
    )

    message = f"""
<b>📈 StockGPT Change Alerts</b>

<b>Generated:</b> {now}
<b>Change Scan Time:</b> {change_time}

<b>Rows Compared:</b> {len(df)}
<b>New High Conviction:</b> {len(new_high_conviction)}
<b>Entered Strong Zone:</b> {len(entered_strong)}
<b>Score Improved +8:</b> {len(score_improved)}
<b>Score Dropped -8:</b> {len(score_dropped)}
<b>Risk Increased:</b> {len(risk_increased)}
<b>RSI Recovery / Momentum:</b> {len(rsi_recovery)}
""".strip()

    message += section("🚀 New High Conviction", new_high_conviction)
    message += section("🟢 Entered Strong Zone", entered_strong)
    message += section("📈 Biggest Score Improvements", score_improved)
    message += section("🔴 Biggest Score Drops", score_dropped)
    message += section("⚠️ Risk Increased", risk_increased)
    message += section("💪 RSI Recovery / Fresh Momentum", rsi_recovery)

    message += "\n\n<i>Not financial advice. Use StockGPT for research only.</i>"

    return message


def main():
    if not Path(CHANGES_FILE).exists():
        print("latest_changes.csv not found. Skipping change alerts.")
        return

    df = pd.read_csv(CHANGES_FILE)

    if df.empty:
        print("latest_changes.csv is empty. Skipping change alerts.")
        return

    df = clean_changes(df)

    # Send only if something meaningful happened
    meaningful = df[
        (df["score_change"].abs() >= 8)
        |
        (df["risk_change"].abs() >= 8)
        |
        (df["change_signal"].str.contains(
            "New High Conviction|Entered Strong Zone|Risk Increased|RSI Recovery|Fresh Momentum",
            case=False,
            na=False
        ))
    ]

    if meaningful.empty:
        print("No meaningful changes. Skipping Telegram change alert.")
        return

    message = build_message(df)

    if len(message) > 3900:
        message = message[:3900] + "\n\n<i>Message trimmed due to Telegram limit.</i>"

    ok = send_telegram_message(message)

    if ok:
        print("Change Telegram alert sent.")
    else:
        print("Change Telegram alert not sent.")


if __name__ == "__main__":
    main()
