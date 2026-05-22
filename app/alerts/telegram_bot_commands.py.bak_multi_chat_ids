import os
import requests
import pandas as pd
from pathlib import Path

SCAN_FILE = Path("data/scans/latest_scan.csv")
WATCHLIST_FILE = Path("data/watchlist/watchlist.csv")
STATE_FILE = Path("data/telegram/last_update_id.txt")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

STATE_FILE.parent.mkdir(parents=True, exist_ok=True)


def safe_num(value, default=0.0):
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


def escape_html(value):
    value = clean_text(value)
    return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def clip(value, limit=600):
    value = clean_text(value)
    return value if len(value) <= limit else value[:limit].rstrip() + "..."


def normalize_symbol(value):
    return clean_text(value).upper().strip()


def normalize_command_token(token):
    return clean_text(token).lower().split("@")[0]


def telegram_api(method, payload=None):
    if not TELEGRAM_BOT_TOKEN:
        print("TELEGRAM_BOT_TOKEN missing.")
        return None
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/{method}"
    try:
        response = requests.post(url, json=payload or {}, timeout=30)
        try:
            data = response.json()
        except Exception:
            print(f"Telegram non-JSON response: {response.text}")
            return None
        if response.status_code != 200 or not data.get("ok"):
            print(f"Telegram API error for {method}: {data}")
        return data
    except Exception as e:
        print(f"Telegram request failed for {method}: {e}")
        return None


def send_message(chat_id, message):
    message = clean_text(message) or "No response generated."
    if not chat_id:
        print("Missing chat_id. Cannot send message.")
        return False
    chunks = [message[i:i + 3900] for i in range(0, len(message), 3900)]
    ok = True
    for chunk in chunks:
        data = telegram_api("sendMessage", {
            "chat_id": chat_id,
            "text": chunk,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        })
        if not data or not data.get("ok"):
            ok = False
    return ok


def read_last_update_id():
    if not STATE_FILE.exists():
        return 0
    try:
        return int(STATE_FILE.read_text(encoding="utf-8").strip() or 0)
    except Exception:
        return 0


def write_last_update_id(update_id):
    STATE_FILE.write_text(str(int(update_id)), encoding="utf-8")


def get_updates(last_update_id):
    payload = {"timeout": 0, "allowed_updates": ["message"]}
    if last_update_id > 0:
        payload["offset"] = last_update_id + 1
    data = telegram_api("getUpdates", payload)
    if not data or not data.get("ok"):
        return []
    return data.get("result", [])


TEXT_COLUMNS = [
    "symbol", "sector", "industry", "sector_bucket", "score_band", "trend",
    "reasons", "technical_reasons", "fundamental_reasons", "fundamental_risks",
    "risk_reasons", "scan_time",
]

NUMERIC_COLUMNS = [
    "current_price", "day_change_pct", "distance_pct", "distance_from_high_pct",
    "rsi", "volume_ratio", "technical_score", "fundamental_score",
    "sector_fundamental_adjustment", "sector_adjusted_fundamental_score",
    "active_fundamental_score", "relative_strength_score", "sector_score",
    "risk_penalty", "final_conviction_score", "return_1m", "return_3m", "return_6m",
]


def load_scan():
    if not SCAN_FILE.exists():
        print(f"Missing scan file: {SCAN_FILE}")
        return pd.DataFrame()
    try:
        df = pd.read_csv(SCAN_FILE)
    except Exception as e:
        print(f"Could not read {SCAN_FILE}: {e}")
        return pd.DataFrame()
    if df.empty or "symbol" not in df.columns:
        return pd.DataFrame()
    for col in TEXT_COLUMNS:
        if col not in df.columns:
            df[col] = ""
        df[col] = df[col].fillna("").astype(str)
    for col in NUMERIC_COLUMNS:
        if col not in df.columns:
            df[col] = 0
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
    df["symbol"] = df["symbol"].astype(str).str.upper().str.strip()
    return df


def load_watchlist():
    if not WATCHLIST_FILE.exists():
        return pd.DataFrame(columns=["symbol", "basket", "notes", "added_at"])
    try:
        watchlist = pd.read_csv(WATCHLIST_FILE)
    except Exception as e:
        print(f"Could not read {WATCHLIST_FILE}: {e}")
        return pd.DataFrame(columns=["symbol", "basket", "notes", "added_at"])
    if watchlist.empty:
        return pd.DataFrame(columns=["symbol", "basket", "notes", "added_at"])
    for col in ["symbol", "basket", "notes", "added_at"]:
        if col not in watchlist.columns:
            watchlist[col] = ""
    watchlist["symbol"] = watchlist["symbol"].astype(str).str.upper().str.strip()
    watchlist["basket"] = watchlist["basket"].fillna("").astype(str)
    watchlist["notes"] = watchlist["notes"].fillna("").astype(str)
    watchlist["added_at"] = watchlist["added_at"].fillna("").astype(str)
    return watchlist[["symbol", "basket", "notes", "added_at"]]


def scan_time_text(df):
    if not df.empty and "scan_time" in df.columns and not df["scan_time"].dropna().empty:
        return clean_text(df["scan_time"].dropna().iloc[0], "Unavailable")
    return "Unavailable"


def stock_line(row, include_reason=False):
    symbol = escape_html(row.get("symbol", ""))
    sector = escape_html(row.get("sector", "Unknown"))
    industry = escape_html(row.get("industry", "Unknown"))
    bucket = escape_html(row.get("sector_bucket", "Unknown"))
    band = escape_html(row.get("score_band", "Unknown"))
    message = (
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
        for label, value in [
            ("Reason", row.get("reasons", "")),
            ("Technical", row.get("technical_reasons", "")),
            ("Fundamental", row.get("fundamental_reasons", "")),
            ("Risk", row.get("risk_reasons", "")),
        ]:
            value = clip(value, 350)
            if value:
                message += f"\n<b>{label}:</b> {escape_html(value)}"
    return message


def table_message(title, df, rows=10, include_reason=False):
    if df.empty:
        return f"<b>{escape_html(title)}</b>\n\nNo matching stocks found."
    message = f"<b>{escape_html(title)}</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n"
    for _, row in df.head(rows).iterrows():
        message += stock_line(row, include_reason=include_reason) + "\n"
    message += "\n<i>Not financial advice. Research tool only.</i>"
    return message.strip()


def get_stock_row(df, symbol):
    symbol = normalize_symbol(symbol)
    result = df[df["symbol"] == symbol]
    if result.empty:
        return None
    return result.iloc[0]


def stock_not_found_message(df, symbol):
    symbol = normalize_symbol(symbol)
    matches = df[df["symbol"].str.contains(symbol, case=False, na=False)]
    if matches.empty:
        return f"<b>{escape_html(symbol)}</b> not found in latest scan."
    suggestions = ", ".join(matches["symbol"].head(10).tolist())
    return f"<b>{escape_html(symbol)}</b> not found exactly.\nPossible matches: {escape_html(suggestions)}"


def command_help():
    return """<b>🤖 StockGPT Commands</b>

/top - Top final conviction stocks
/low - 52W low + sector-adjusted quality
/swing - Swing candidates
/high - Near 52W high momentum
/risk - Avoid / risky stocks
/range - Top range-bound opportunities
/range SYMBOL - Range snapshot for one stock
/watchlist - Watchlist summary
/stock SYMBOL - Full stock snapshot
/why SYMBOL - Explain stock score
/sector SECTOR_BUCKET - Top stocks from sector bucket
/basket BASKET_NAME - Watchlist basket details
/compare SYMBOL1 SYMBOL2 - Compare two stocks

Examples:
/top
/why RELIANCE
/stock IDEA
/sector IT_TECH
/sector BANK
/basket Swing Candidates
/compare RELIANCE TCS

<i>Commands use latest StockGPT scan data.</i>"""


def command_top(df, _text):
    return table_message("🏆 Top Final Conviction", df.sort_values("final_conviction_score", ascending=False), rows=10)


def command_low(df, _text):
    data = df[(df["distance_pct"] <= 20) & (df["active_fundamental_score"] >= 55)]
    data = data.sort_values(["distance_pct", "final_conviction_score"], ascending=[True, False])
    return table_message("🎯 52W Low + Sector-Adjusted Quality", data, rows=10)


def command_swing(df, _text):
    data = df[(df["distance_pct"] <= 25) & (df["rsi"] <= 45) & (df["volume_ratio"] >= 1.0)]
    return table_message("⚡ Swing Candidates", data.sort_values("final_conviction_score", ascending=False), rows=10)


def command_high(df, _text):
    data = df[(df["distance_from_high_pct"] <= 15) & (df["rsi"] >= 50) & (df["trend"].str.lower() == "bullish")]
    data = data.sort_values(["distance_from_high_pct", "final_conviction_score"], ascending=[True, False])
    return table_message("🚀 Near 52W High Momentum", data, rows=10)


def command_risk(df, _text):
    data = df[(df["score_band"] == "E Avoid") | (df["final_conviction_score"] < 35) | (df["risk_penalty"] >= 25) | ((df["active_fundamental_score"] < 30) & (df["relative_strength_score"] < 40))]
    data = data.sort_values(["risk_penalty", "final_conviction_score"], ascending=[False, True])
    return table_message("🔴 Avoid / Risky Watch", data, rows=10, include_reason=True)


def command_stock(df, text):
    parts = text.strip().split()
    if len(parts) < 2:
        return "Usage: /stock SYMBOL\nExample: /stock RELIANCE"
    symbol = parts[1]
    row = get_stock_row(df, symbol)
    if row is None:
        return stock_not_found_message(df, symbol)
    message = f"<b>🔎 Stock Snapshot: {escape_html(normalize_symbol(symbol))}</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n"
    message += stock_line(row, include_reason=True)
    message += "\n\n<i>Not financial advice. Research tool only.</i>"
    return message.strip()


def command_why(df, text):
    parts = text.strip().split()
    if len(parts) < 2:
        return "Usage: /why SYMBOL\nExample: /why RELIANCE"
    symbol = parts[1]
    row = get_stock_row(df, symbol)
    if row is None:
        return stock_not_found_message(df, symbol)
    symbol = normalize_symbol(symbol)
    final_score = safe_num(row.get("final_conviction_score"))
    tech_score = safe_num(row.get("technical_score"))
    raw_fund = safe_num(row.get("fundamental_score"))
    sector_adj = safe_num(row.get("sector_fundamental_adjustment"))
    sector_adj_fund = safe_num(row.get("sector_adjusted_fundamental_score"))
    active_fund = safe_num(row.get("active_fundamental_score"))
    rs_score = safe_num(row.get("relative_strength_score"))
    sector_score = safe_num(row.get("sector_score"))
    risk = safe_num(row.get("risk_penalty"))
    interpretation = []
    if final_score >= 75:
        interpretation.append("A+ final conviction score.")
    elif final_score >= 65:
        interpretation.append("Strong final conviction score.")
    elif final_score < 35:
        interpretation.append("Weak final conviction score.")
    if tech_score >= 60:
        interpretation.append("Technical setup is supportive.")
    elif tech_score < 35:
        interpretation.append("Technical setup is weak.")
    if active_fund >= 60:
        interpretation.append("Sector-adjusted fundamental quality is strong.")
    elif active_fund < 35:
        interpretation.append("Sector-adjusted fundamental quality is weak.")
    if sector_adj > 0:
        interpretation.append(f"Sector model added +{sector_adj:.1f} points to fundamentals.")
    elif sector_adj < 0:
        interpretation.append(f"Sector model reduced fundamentals by {sector_adj:.1f} points.")
    if rs_score >= 60:
        interpretation.append("Relative strength is strong.")
    elif rs_score < 35:
        interpretation.append("Relative strength is weak.")
    if risk >= 25:
        interpretation.append("Risk penalty is high.")
    elif risk <= 10:
        interpretation.append("Risk penalty is low.")
    message = f"<b>🧠 Why {escape_html(symbol)}?</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n\n"
    message += "<b>Core Scores</b>\n"
    message += f"Final Conviction: {final_score:.1f}\nTechnical: {tech_score:.1f}\nRaw Fundamental: {raw_fund:.1f}\n"
    message += f"Sector Adjustment: {sector_adj:+.1f}\nSector Adjusted Fundamental: {sector_adj_fund:.1f}\n"
    message += f"Active Fundamental: {active_fund:.1f}\nRelative Strength: {rs_score:.1f}\nSector Score: {sector_score:.1f}\nRisk Penalty: {risk:.1f}\n\n"
    message += "<b>Classification</b>\n"
    message += f"Score Band: {escape_html(row.get('score_band', ''))}\nSector Bucket: {escape_html(row.get('sector_bucket', ''))}\n"
    message += f"Sector: {escape_html(row.get('sector', ''))}\nIndustry: {escape_html(row.get('industry', ''))}\n\n"
    if interpretation:
        message += "<b>Interpretation</b>\n" + "".join(f"• {escape_html(item)}\n" for item in interpretation) + "\n"
    for label, value in [
        ("General Reason", row.get("reasons")),
        ("Technical Reason", row.get("technical_reasons")),
        ("Fundamental Reason", row.get("fundamental_reasons")),
        ("Fundamental Risks", row.get("fundamental_risks")),
        ("Risk Reason", row.get("risk_reasons")),
    ]:
        value = clip(value, 700)
        if value:
            message += f"<b>{escape_html(label)}</b>\n{escape_html(value)}\n\n"
    message += "<i>Not financial advice. Research tool only.</i>"
    return message.strip()


def command_sector(df, text):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        buckets = ", ".join(sorted(df["sector_bucket"].dropna().astype(str).unique().tolist()))
        return f"Usage: /sector SECTOR_BUCKET\nExample: /sector IT_TECH\n\nAvailable sector buckets:\n{escape_html(buckets)}"
    query_raw = parts[1].strip()
    query = query_raw.upper().replace(" ", "_")
    sector_df = df[df["sector_bucket"].astype(str).str.upper().str.contains(query, case=False, na=False)]
    if sector_df.empty:
        relaxed = query_raw.upper().replace("_", " ")
        sector_df = df[df["sector"].astype(str).str.upper().str.contains(relaxed, case=False, na=False) | df["industry"].astype(str).str.upper().str.contains(relaxed, case=False, na=False)]
    if sector_df.empty:
        return f"No stocks found for sector/bucket: <b>{escape_html(query_raw)}</b>"
    return table_message(f"🏭 Top Sector Stocks: {query_raw}", sector_df.sort_values("final_conviction_score", ascending=False), rows=10)


def command_watchlist(df, _text):
    watchlist = load_watchlist()
    if watchlist.empty:
        return "<b>⭐ Watchlist</b>\n\nWatchlist is empty."
    merged = watchlist.merge(df, on="symbol", how="left")
    found = merged[merged["current_price"].notna()]
    missing = merged[merged["current_price"].isna()]
    message = "<b>⭐ Watchlist Summary</b>\n"
    message += f"Total: {len(watchlist)}\nFound in latest scan: {len(found)}\nMissing from latest scan: {len(missing)}\n"
    if not found.empty:
        summary = found.groupby("basket").agg(stocks=("symbol", "count"), avg_final=("final_conviction_score", "mean"), avg_active_fund=("active_fundamental_score", "mean"), avg_risk=("risk_penalty", "mean")).reset_index().sort_values("avg_final", ascending=False)
        message += "\n<b>By Basket</b>\n"
        for _, row in summary.iterrows():
            message += f"\n<b>{escape_html(row['basket'])}</b> | Stocks: {int(row['stocks'])} | Avg Final: {safe_num(row['avg_final']):.1f} | Avg Active Fund: {safe_num(row['avg_active_fund']):.1f} | Avg Risk: {safe_num(row['avg_risk']):.1f}"
        message += "\n\n<b>Top Watchlist Stocks</b>\n"
        top = found.sort_values("final_conviction_score", ascending=False).head(10)
        for _, row in top.iterrows():
            message += stock_line(row) + "\n"
    if not missing.empty:
        missing_symbols = ", ".join(missing["symbol"].dropna().astype(str).head(25).tolist())
        message += f"\n<b>Missing:</b> {escape_html(missing_symbols)}"
    message += "\n\n<i>Not financial advice. Research tool only.</i>"
    return message.strip()


def command_basket(df, text):
    parts = text.strip().split(maxsplit=1)
    if len(parts) < 2:
        return "Usage: /basket BASKET_NAME\nExample: /basket Swing Candidates"
    query = parts[1].strip().strip('"').strip("'").lower()
    watchlist = load_watchlist()
    if watchlist.empty:
        return "<b>⭐ Watchlist</b>\n\nWatchlist is empty."
    basket_df = watchlist[watchlist["basket"].astype(str).str.lower().str.contains(query, case=False, na=False)]
    if basket_df.empty:
        available = ", ".join(sorted(watchlist["basket"].dropna().astype(str).unique().tolist()))
        return f"No basket found matching: <b>{escape_html(query)}</b>\n\nAvailable baskets:\n{escape_html(available)}"
    merged = basket_df.merge(df, on="symbol", how="left")
    found = merged[merged["current_price"].notna()]
    if found.empty:
        symbols = ", ".join(basket_df["symbol"].dropna().astype(str).tolist())
        return f"<b>⭐ Basket: {escape_html(basket_df['basket'].iloc[0])}</b>\nNo symbols from this basket were found in latest scan.\nSymbols: {escape_html(symbols)}"
    return table_message(f"⭐ Watchlist Basket: {basket_df['basket'].iloc[0]}", found.sort_values("final_conviction_score", ascending=False), rows=15)


def command_compare(df, text):
    parts = text.strip().split()
    if len(parts) < 3:
        return "Usage: /compare SYMBOL1 SYMBOL2\nExample: /compare RELIANCE TCS"
    symbol_a = normalize_symbol(parts[1])
    symbol_b = normalize_symbol(parts[2])
    row_a = get_stock_row(df, symbol_a)
    row_b = get_stock_row(df, symbol_b)
    if row_a is None:
        return stock_not_found_message(df, symbol_a)
    if row_b is None:
        return stock_not_found_message(df, symbol_b)
    metrics = [
        ("Final Conviction", "final_conviction_score", "higher"), ("Technical", "technical_score", "higher"),
        ("Raw Fundamental", "fundamental_score", "higher"), ("Sector Adjustment", "sector_fundamental_adjustment", "higher"),
        ("Sector Adjusted Fundamental", "sector_adjusted_fundamental_score", "higher"), ("Active Fundamental", "active_fundamental_score", "higher"),
        ("Relative Strength", "relative_strength_score", "higher"), ("Sector Score", "sector_score", "higher"),
        ("Risk Penalty", "risk_penalty", "lower"), ("RSI", "rsi", "higher"), ("Volume Ratio", "volume_ratio", "higher"),
        ("Distance From Low %", "distance_pct", "lower"), ("Distance From High %", "distance_from_high_pct", "lower"),
        ("1M Return", "return_1m", "higher"), ("3M Return", "return_3m", "higher"), ("6M Return", "return_6m", "higher"),
    ]
    message = f"<b>⚖️ Compare: {escape_html(symbol_a)} vs {escape_html(symbol_b)}</b>\n"
    message += f"<b>Scan:</b> {escape_html(scan_time_text(df))}\n\n"
    message += f"{escape_html(symbol_a)}: {escape_html(row_a.get('score_band', ''))} | {escape_html(row_a.get('sector_bucket', ''))}\n"
    message += f"{escape_html(symbol_b)}: {escape_html(row_b.get('score_band', ''))} | {escape_html(row_b.get('sector_bucket', ''))}\n\n"
    for label, col, direction in metrics:
        a = safe_num(row_a.get(col))
        b = safe_num(row_b.get(col))
        if direction == "lower":
            winner = symbol_a if a < b else symbol_b if b < a else "Tie"
        else:
            winner = symbol_a if a > b else symbol_b if b > a else "Tie"
        message += f"<b>{escape_html(label)}</b>: {a:.1f} vs {b:.1f} | Winner: {escape_html(winner)}\n"
    message += "\n<i>Not financial advice. Research tool only.</i>"
    return message.strip()




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

COMMANDS = {
    "/help": command_help, "/start": command_help, "/top": command_top, "/low": command_low,
    "/swing": command_swing, "/high": command_high, "/risk": command_risk, "/watchlist": command_watchlist,
    "/stock": command_stock, "/why": command_why, "/sector": command_sector, "/basket": command_basket,
    "/compare": command_compare,
}


def handle_command(text, df):
    text = clean_text(text)
    if not text.startswith("/"):
        return None
    raw_command = text.split()[0]
    command = normalize_command_token(raw_command)
    print(f"RAW COMMAND TEXT: {text}")
    print(f"NORMALIZED COMMAND: {command}")
    handler = COMMANDS.get(command)
    if handler is None:
        print(f"Unknown command routed to help: {command}")
        return command_help()
    print(f"ROUTED COMMAND: {command}")
    if command in ["/help", "/start"]:
        return handler()
    if df.empty:
        return "Latest scan data not found or empty. Run Phase6 pipeline first."
    return handler(df, text)


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
    for update in updates:
        update_id = int(update.get("update_id", 0))
        max_update_id = max(max_update_id, update_id)
        message = update.get("message", {})
        chat = message.get("chat", {})
        chat_id = str(chat.get("id", "")).strip()
        text = clean_text(message.get("text", ""))
        if not text.startswith("/"):
            continue
        if TELEGRAM_CHAT_ID and chat_id != TELEGRAM_CHAT_ID:
            print(f"Ignoring unauthorized chat_id={chat_id}")
            continue
        print(f"Processing command from chat_id={chat_id}: {text}")
        try:
            reply = handle_command(text, df)
        except Exception as e:
            print(f"Command failed: {e}")
            reply = f"Command failed: {escape_html(str(e))}"
        if reply:
            send_message(chat_id, reply)
            processed += 1
    write_last_update_id(max_update_id)
    print(f"Processed commands: {processed}")
    print(f"Last update id saved: {max_update_id}")


if __name__ == "__main__":
    main()
