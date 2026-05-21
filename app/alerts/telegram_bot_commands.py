import os
import requests
import pandas as pd
from pathlib import Path

SCAN_FILE = "data/scans/latest_scan.csv"
WATCHLIST_FILE = "data/watchlist/watchlist.csv"
STATE_FILE = "data/telegram/last_update_id.txt"

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

Path("data/telegram").mkdir(parents=True, exist_ok=True)


def safe_num(value, default=0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def clean_text(value, default=""):
    try:
        if pd.isna(value):
            return default
    except Exception:
        pass

    value = str(value).strip()
    return value if value else default


def escape_html(text):
    text = clean_text(text)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def telegram_api(method, payload=None):
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing.")
        return None

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"

    try:
        response = requests.post(url, json=payload or {}, timeout=25)
        data = response.json()

        if response.status_code != 200:
            print(f"Telegram API error: {data}")

        return data

    except Exception as e:
        print(f"Telegram API request failed: {e}")
        return None


def send_message(chat_id, message):
    if not chat_id:
        print("chat_id missing. Message not sent.")
        return False

    max_len = 3900
    chunks = [message[i:i + max_len] for i in range(0, len(message), max_len)]

    ok = True

    for chunk in chunks:
        data = telegram_api(
            "sendMessage",
            {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
        )

        if not data or not data.get("ok"):
            ok = False

    return ok


def read_last_update_id():
    path = Path(STATE_FILE)

    if not path.exists():
        return 0

    try:
        return int(path.read_text().strip() or 0)
    except Exception:
        return 0


def write_last_update_id(update_id):
    Path(STATE_FILE).write_text(str(update_id), encoding="utf-8")


def get_updates(last_update_id):
    payload = {"timeout": 0, "allowed_updates": ["message"]}

    if last_update_id > 0:
        payload["offset"] = last_update_id + 1

    data = telegram_api("getUpdates", payload)

    if not data or not data.get("ok"):
        return []

    return data.get("result", [])


def load_scan():
    if not Path(SCAN_FILE).exists():
        return pd.DataFrame()

    df = pd.read_csv(SCAN_FILE)

    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()

    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()

    text_cols = [
        "sector",
        "industry",
        "sector_bucket",
        "score_band",
        "trend",
        "reasons",
        "fundamental_reasons",
        "fundamental_risks",
        "risk_reasons",
    ]

    for col in text_cols:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)

    numeric_cols = [
        "current_price",
        "day_change_pct",
        "distance_pct",
        "distance_from_high_pct",
        "rsi",
        "volume_ratio",
        "technical_score",
        "fundamental_score",
        "sector_fundamental_adjustment",
        "sector_adjusted_fundamental_score",
        "active_fundamental_score",
        "relative_strength_score",
        "sector_score",
        "risk_penalty",
        "final_conviction_score",
        "return_1m",
        "return_3m",
        "return_6m",
    ]

    for col in numeric_cols:
        if col not in df.columns:
            df[col] = 0

        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

    return df


def scan_time_text(df):
    if "scan_time" in df.columns and not df["scan_time"].dropna().empty:
        return clean_text(df["scan_time"].dropna().iloc[0], "Unavailable")

    return "Unavailable"


def format_stock_line(row, include_reason=False):
    symbol = escape_html(row.get("symbol", ""))
    sector = escape_html(row.get("sector", ""))
    industry = escape_html(row.get("industry", ""))
    bucket = escape_html(row.get("sector_bucket", ""))
    band = escape_html(row.get("score_band", ""))

    line = (
        f"\n<b>{symbol}</b> | ₹{safe_num(row.get('current_price')):.2f} | {band}\n"
        f"Final: {safe_num(row.get('final_conviction_score')):.1f}"
        f" | Tech: {safe_num(row.get('technical_score')):.1f}"
        f" | Active Fund: {safe_num(row.get('active_fundamental_score')):.1f}"
        f" | RS: {safe_num(row.get('relative_strength_score')):.1f}"
        f" | Risk: {safe_num(row.get('risk_penalty')):.1f}\n"
        f"Raw Fund: {safe_num(row.get('fundamental_score')):.1f}"
        f" | Sector Adj: {safe_num(row.get('sector_fundamental_adjustment')):+.1f}"
        f" | Sector Adj Fund: {safe_num(row.get('sector_adjusted_fundamental_score')):.1f}\n"
        f"RSI: {safe_num(row.get('rsi')):.1f}"
        f" | Vol: {safe_num(row.get('volume_ratio')):.2f}x"
        f" | Low Dist: {safe_num(row.get('distance_pct')):.1f}%"
        f" | High Dist: {safe_num(row.get('distance_from_high_pct')):.1f}%\n"
        f"{sector} | {industry} | {bucket}"
    )

    if include_reason:
        reason = clean_text(row.get("reasons"))
        fund_reason = clean_text(row.get("fundamental_reasons"))
        risk_reason = clean_text(row.get("risk_reasons"))

        if reason:
            line += f"\nReason: {escape_html(reason[:350])}"
        if fund_reason:
            line += f"\nFundamental: {escape_html(fund_reason[:350])}"
        if risk_reason:
            line += f"\nRisk: {escape_html(risk_reason[:350])}"

    return line


def table_message(title, df, rows=10, include_reason=False):
    if df.empty:
        return f"<b>{escape_html(title)}</b>\n\nNo matching stocks found."

    message = f"<b>{escape_html(title)}</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n"

    for _, row in df.head(rows).iterrows():
        message += format_stock_line(row, include_reason=include_reason)
        message += "\n"

    message += "\n<i>Not financial advice. Use for research only.</i>"
    return message.strip()


def command_help():
    return """<b>🤖 StockGPT Commands</b>

/top - Top final conviction stocks
/low - 52W low + sector-adjusted quality
/swing - Swing candidates
/high - Near 52W high momentum
/risk - Avoid / risky stocks
/watchlist - Watchlist summary
/stock SYMBOL - Full stock snapshot
/why SYMBOL - Explain why stock is ranked that way
/sector SECTOR_BUCKET - Top stocks from sector bucket
/basket BASKET_NAME - Watchlist basket details
/compare SYMBOL1 SYMBOL2 - Compare two stocks

Examples:
/stock RELIANCE
/why RELIANCE
/sector IT_TECH
/sector BANK
/basket Swing Candidates
/compare RELIANCE TCS

<i>Commands use latest saved StockGPT scan data.</i>"""


def command_top(df):
    data = df.sort_values("final_conviction_score", ascending=False)
    return table_message("🏆 Top Final Conviction", data, rows=10)


def command_low(df):
    data = df[
        (df["distance_pct"] <= 20) & (df["active_fundamental_score"] >= 55)
    ].sort_values(["distance_pct", "final_conviction_score"], ascending=[True, False])
    return table_message("🎯 52W Low + Sector-Adjusted Quality", data, rows=10)


def command_swing(df):
    data = df[
        (df["distance_pct"] <= 25)
        & (df["rsi"] <= 45)
        & (df["volume_ratio"] >= 1.0)
    ].sort_values("final_conviction_score", ascending=False)
    return table_message("⚡ Swing Candidates", data, rows=10)


def command_high(df):
    data = df[
        (df["distance_from_high_pct"] <= 15)
        & (df["rsi"] >= 50)
        & (df["trend"].str.lower() == "bullish")
    ].sort_values(["distance_from_high_pct", "final_conviction_score"], ascending=[True, False])
    return table_message("🚀 Near 52W High Momentum", data, rows=10)


def command_risk(df):
    data = df[
        (df["score_band"] == "E Avoid")
        | (df["final_conviction_score"] < 35)
        | (df["risk_penalty"] >= 25)
        | ((df["active_fundamental_score"] < 30) & (df["relative_strength_score"] < 40))
    ].sort_values(["risk_penalty", "final_conviction_score"], ascending=[False, True])
    return table_message("🔴 Avoid / Risky Watch", data, rows=10, include_reason=True)


def load_watchlist():
    if not Path(WATCHLIST_FILE).exists():
        return pd.DataFrame(columns=["symbol", "basket", "notes", "added_at"])

    watchlist = pd.read_csv(WATCHLIST_FILE)

    if watchlist.empty or "symbol" not in watchlist.columns:
        return pd.DataFrame(columns=["symbol", "basket", "notes", "added_at"])

    for col in ["symbol", "basket", "notes", "added_at"]:
        if col not in watchlist.columns:
            watchlist[col] = ""

    watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper().str.strip()
    return watchlist


def command_watchlist(df):
    watchlist = load_watchlist()

    if watchlist.empty:
        return "<b>⭐ Watchlist</b>\n\nWatchlist is empty."

    merged = watchlist.merge(df, on="symbol", how="left")
    found = merged[merged["current_price"].notna()]
    missing = merged[merged["current_price"].isna()]

    message = "<b>⭐ Watchlist Summary</b>\n"
    message += f"Total: {len(watchlist)}\n"
    message += f"Found in latest scan: {len(found)}\n"
    message += f"Missing from latest scan: {len(missing)}\n"

    if not found.empty:
        basket_summary = (
            found.groupby("basket")
            .agg(
                stocks=("symbol", "count"),
                avg_final=("final_conviction_score", "mean"),
                avg_active_fund=("active_fundamental_score", "mean"),
                avg_risk=("risk_penalty", "mean"),
            )
            .reset_index()
            .sort_values("avg_final", ascending=False)
        )

        message += "\n<b>By Basket</b>\n"

        for _, row in basket_summary.iterrows():
            message += (
                f"\n<b>{escape_html(row['basket'])}</b>"
                f" | Stocks: {int(row['stocks'])}"
                f" | Avg Final: {safe_num(row['avg_final']):.1f}"
                f" | Avg Active Fund: {safe_num(row['avg_active_fund']):.1f}"
                f" | Avg Risk: {safe_num(row['avg_risk']):.1f}"
            )

        top = found.sort_values("final_conviction_score", ascending=False).head(10)
        message += "\n\n<b>Top Watchlist Stocks</b>\n"

        for _, row in top.iterrows():
            message += format_stock_line(row, include_reason=False)
            message += "\n"

    if not missing.empty:
        missing_symbols = ", ".join(missing["symbol"].dropna().astype(str).head(25).tolist())
        message += f"\n<b>Missing:</b> {escape_html(missing_symbols)}"

    message += "\n\n<i>Not financial advice. Use for research only.</i>"
    return message.strip()


def command_stock(df, text):
    parts = text.strip().split()

    if len(parts) < 2:
        return "Usage: /stock SYMBOL\nExample: /stock RELIANCE"

    symbol = parts[1].upper().strip()
    stock_df = df[df["symbol"] == symbol]

    if stock_df.empty:
        matches = df[df["symbol"].str.contains(symbol, case=False, na=False)]

        if matches.empty:
            return f"<b>{escape_html(symbol)}</b> not found in latest scan."

        suggestions = ", ".join(matches["symbol"].head(10).tolist())
        return f"<b>{escape_html(symbol)}</b> not found exactly.\nPossible matches: {escape_html(suggestions)}"

    row = stock_df.iloc[0]
    message = f"<b>🔎 Stock Snapshot: {escape_html(symbol)}</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n"
    message += format_stock_line(row, include_reason=True)
    message += "\n\n<i>Not financial advice. Use for research only.</i>"
    return message.strip()



def command_why(df, text):
    parts = text.strip().split()

    if len(parts) < 2:
        return "Usage: /why SYMBOL\\nExample: /why RELIANCE"

    symbol = parts[1].upper().strip()
    stock_df = df[df["symbol"] == symbol]

    if stock_df.empty:
        matches = df[df["symbol"].str.contains(symbol, case=False, na=False)]

        if matches.empty:
            return f"<b>{escape_html(symbol)}</b> not found in latest scan."

        suggestions = ", ".join(matches["symbol"].head(10).tolist())

        return (
            f"<b>{escape_html(symbol)}</b> not found exactly.\\n"
            f"Possible matches: {escape_html(suggestions)}"
        )

    row = stock_df.iloc[0]

    final_score = safe_num(row.get("final_conviction_score"))
    tech_score = safe_num(row.get("technical_score"))
    raw_fund = safe_num(row.get("fundamental_score"))
    sector_adj = safe_num(row.get("sector_fundamental_adjustment"))
    sector_adj_fund = safe_num(row.get("sector_adjusted_fundamental_score"))
    active_fund = safe_num(row.get("active_fundamental_score"))
    rs_score = safe_num(row.get("relative_strength_score"))
    sector_score = safe_num(row.get("sector_score"))
    risk = safe_num(row.get("risk_penalty"))

    reasons = []

    if final_score >= 75:
        reasons.append("A+ final conviction score")
    elif final_score >= 65:
        reasons.append("Strong final conviction score")
    elif final_score < 35:
        reasons.append("Weak final conviction score")

    if tech_score >= 60:
        reasons.append("technical setup is supportive")
    elif tech_score < 35:
        reasons.append("technical setup is weak")

    if active_fund >= 60:
        reasons.append("sector-adjusted fundamental quality is strong")
    elif active_fund < 35:
        reasons.append("sector-adjusted fundamental quality is weak")

    if sector_adj > 0:
        reasons.append(f"sector model added +{sector_adj:.1f} points to fundamentals")
    elif sector_adj < 0:
        reasons.append(f"sector model reduced fundamentals by {sector_adj:.1f} points")

    if rs_score >= 60:
        reasons.append("relative strength is strong")
    elif rs_score < 35:
        reasons.append("relative strength is weak")

    if risk >= 25:
        reasons.append("risk penalty is high")
    elif risk <= 10:
        reasons.append("risk penalty is low")

    tech_reason = clean_text(row.get("technical_reasons"))
    fund_reason = clean_text(row.get("fundamental_reasons"))
    risk_reason = clean_text(row.get("risk_reasons"))
    general_reason = clean_text(row.get("reasons"))
    fund_risks = clean_text(row.get("fundamental_risks"))

    message = f"<b>🧠 Why {escape_html(symbol)}?</b>\\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\\n\\n"

    message += "<b>Core Scores</b>\\n"
    message += f"Final Conviction: {final_score:.1f}\\n"
    message += f"Technical: {tech_score:.1f}\\n"
    message += f"Raw Fundamental: {raw_fund:.1f}\\n"
    message += f"Sector Adjustment: {sector_adj:+.1f}\\n"
    message += f"Sector Adjusted Fundamental: {sector_adj_fund:.1f}\\n"
    message += f"Active Fundamental: {active_fund:.1f}\\n"
    message += f"Relative Strength: {rs_score:.1f}\\n"
    message += f"Sector Score: {sector_score:.1f}\\n"
    message += f"Risk Penalty: {risk:.1f}\\n\\n"

    message += "<b>Classification</b>\\n"
    message += f"Score Band: {escape_html(row.get('score_band', ''))}\\n"
    message += f"Sector Bucket: {escape_html(row.get('sector_bucket', ''))}\\n"
    message += f"Sector: {escape_html(row.get('sector', ''))}\\n"
    message += f"Industry: {escape_html(row.get('industry', ''))}\\n\\n"

    if reasons:
        message += "<b>Interpretation</b>\\n"
        for reason in reasons:
            message += f"• {escape_html(reason)}\\n"
        message += "\\n"

    if general_reason:
        message += f"<b>General Reason</b>\\n{escape_html(general_reason[:700])}\\n\\n"

    if tech_reason:
        message += f"<b>Technical Reason</b>\\n{escape_html(tech_reason[:700])}\\n\\n"

    if fund_reason:
        message += f"<b>Fundamental Reason</b>\\n{escape_html(fund_reason[:700])}\\n\\n"

    if fund_risks:
        message += f"<b>Fundamental Risks</b>\\n{escape_html(fund_risks[:700])}\\n\\n"

    if risk_reason:
        message += f"<b>Risk Reason</b>\\n{escape_html(risk_reason[:700])}\\n\\n"

    message += "<i>Not financial advice. Use for research only.</i>"

    return message.strip()


def command_sector(df, text):
    parts = text.strip().split(maxsplit=1)

    if len(parts) < 2:
        buckets = ", ".join(sorted(df["sector_bucket"].dropna().astype(str).unique().tolist()))
        return (
            "Usage: /sector SECTOR_BUCKET\\n"
            "Example: /sector IT_TECH\\n\\n"
            f"Available buckets:\\n{escape_html(buckets)}"
        )

    query = parts[1].strip().upper().replace(" ", "_")

    sector_df = df[
        df["sector_bucket"].astype(str).str.upper().str.contains(
            query,
            case=False,
            na=False
        )
    ]

    if sector_df.empty:
        sector_df = df[
            df["sector"].astype(str).str.upper().str.contains(
                query.replace("_", " "),
                case=False,
                na=False
            )
        ]

    if sector_df.empty:
        return f"No stocks found for sector/bucket: <b>{escape_html(query)}</b>"

    sector_df = sector_df.sort_values("final_conviction_score", ascending=False)

    return table_message(
        f"🏭 Top Sector Stocks: {query}",
        sector_df,
        rows=10,
        include_reason=False
    )


def command_basket(df, text):
    parts = text.strip().split(maxsplit=1)

    if len(parts) < 2:
        return "Usage: /basket BASKET_NAME\\nExample: /basket Swing Candidates"

    basket_query = parts[1].strip().strip('"').strip("'").lower()
    watchlist = load_watchlist()

    if watchlist.empty:
        return "<b>⭐ Watchlist</b>\\n\\nWatchlist is empty."

    basket_df = watchlist[
        watchlist["basket"].astype(str).str.lower().str.contains(
            basket_query,
            case=False,
            na=False
        )
    ]

    if basket_df.empty:
        available = ", ".join(sorted(watchlist["basket"].dropna().astype(str).unique().tolist()))

        return (
            f"No basket found matching: <b>{escape_html(basket_query)}</b>\\n\\n"
            f"Available baskets:\\n{escape_html(available)}"
        )

    merged = basket_df.merge(df, on="symbol", how="left")
    found = merged[merged["current_price"].notna()]

    if found.empty:
        symbols = ", ".join(basket_df["symbol"].dropna().astype(str).tolist())
        return (
            f"<b>⭐ Basket: {escape_html(basket_df['basket'].iloc[0])}</b>\\n"
            f"No symbols from this basket were found in latest scan.\\n"
            f"Symbols: {escape_html(symbols)}"
        )

    found = found.sort_values("final_conviction_score", ascending=False)

    return table_message(
        f"⭐ Watchlist Basket: {basket_df['basket'].iloc[0]}",
        found,
        rows=15,
        include_reason=False
    )


def command_compare(df, text):
    parts = text.strip().split()

    if len(parts) < 3:
        return "Usage: /compare SYMBOL1 SYMBOL2\\nExample: /compare RELIANCE TCS"

    symbols = [parts[1].upper().strip(), parts[2].upper().strip()]
    rows = []

    for symbol in symbols:
        stock_df = df[df["symbol"] == symbol]

        if stock_df.empty:
            return f"<b>{escape_html(symbol)}</b> not found in latest scan."

        rows.append(stock_df.iloc[0])

    a, b = rows

    metrics = [
        ("Final Conviction", "final_conviction_score"),
        ("Technical", "technical_score"),
        ("Raw Fundamental", "fundamental_score"),
        ("Sector Adjustment", "sector_fundamental_adjustment"),
        ("Sector Adjusted Fundamental", "sector_adjusted_fundamental_score"),
        ("Active Fundamental", "active_fundamental_score"),
        ("Relative Strength", "relative_strength_score"),
        ("Sector Score", "sector_score"),
        ("Risk Penalty", "risk_penalty"),
        ("RSI", "rsi"),
        ("Volume Ratio", "volume_ratio"),
        ("Distance From Low %", "distance_pct"),
        ("Distance From High %", "distance_from_high_pct"),
        ("1M Return", "return_1m"),
        ("3M Return", "return_3m"),
        ("6M Return", "return_6m"),
    ]

    sym_a = escape_html(a.get("symbol", symbols[0]))
    sym_b = escape_html(b.get("symbol", symbols[1]))

    message = f"<b>⚖️ Compare: {sym_a} vs {sym_b}</b>\\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\\n\\n"

    message += f"{sym_a}: {escape_html(a.get('score_band', ''))} | {escape_html(a.get('sector_bucket', ''))}\\n"
    message += f"{sym_b}: {escape_html(b.get('score_band', ''))} | {escape_html(b.get('sector_bucket', ''))}\\n\\n"

    for label, col in metrics:
        va = safe_num(a.get(col))
        vb = safe_num(b.get(col))

        if col == "risk_penalty":
            winner = sym_a if va < vb else sym_b if vb < va else "Tie"
        else:
            winner = sym_a if va > vb else sym_b if vb > va else "Tie"

        message += f"<b>{escape_html(label)}</b>: {va:.1f} vs {vb:.1f} | Winner: {winner}\\n"

    message += "\\n<i>Not financial advice. Use for research only.</i>"

    return message.strip()



def handle_command(text, df):
    print(f"RAW COMMAND TEXT: {text}")

    # Telegram group commands may arrive as /why@BotUsername.
    # Normalize /why@BotUsername to /why.
    command = text.strip().split()[0].lower()
    command = command.split("@")[0]

    print(f"NORMALIZED COMMAND: {command}")

    if command in ["/help", "/start"]:
        return command_help()

    if df.empty:
        return "Latest scan data not found or empty. Run Phase6 pipeline first."

    if command == "/top":
        return command_top(df)
    if command == "/low":
        return command_low(df)
    if command == "/swing":
        return command_swing(df)
    if command == "/high":
        return command_high(df)
    if command == "/risk":
        return command_risk(df)
    if command == "/watchlist":
        return command_watchlist(df)
    if command == "/stock":
        return command_stock(df, text)

    return command_help()


def main():
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing. Exiting.")
        return

    last_update_id = read_last_update_id()
    updates = get_updates(last_update_id)

    if not updates:
        print("No Telegram commands found.")
        return

    df = load_scan()
    max_update_id = last_update_id
    processed = 0
    allowed_chat_id = str(TELEGRAM_CHAT_ID).strip()

    for update in updates:
        update_id = int(update.get("update_id", 0))
        max_update_id = max(max_update_id, update_id)

        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", ""))
        text = clean_text(message.get("text", ""))

        if not text.startswith("/"):
            continue

        if allowed_chat_id and chat_id != allowed_chat_id:
            print(f"Ignoring command from unauthorized chat_id={chat_id}")
            continue

        print(f"Processing command from chat_id={chat_id}: {text}")
        reply = handle_command(text, df)
        send_message(chat_id, reply)
        processed += 1

    write_last_update_id(max_update_id)
    print(f"Processed commands: {processed}")
    print(f"Last update id saved: {max_update_id}")


if __name__ == "__main__":
    main()
