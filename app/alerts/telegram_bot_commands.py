import os
import requests
import pandas as pd
from pathlib import Path
import re
import json
import hashlib
from datetime import datetime
# =========================
# UX V4 FINAL — MENU + NATURAL ROUTER
# =========================

MAIN_MENU_REPLY_MARKUP = {
    "keyboard": [
        [{"text": "📊 Top Ideas"}, {"text": "📦 Range Bound"}],
        [{"text": "⚡ Swing"}, {"text": "📉 52W Low"}],
        [{"text": "🚀 Momentum"}, {"text": "⚠️ Risky / Avoid"}],
        [{"text": "⭐ Watchlist"}, {"text": "📈 Performance"}],
        [{"text": "🔍 Stock Analysis"}, {"text": "📦 Stock Range"}],
        [{"text": "📊 Stock Performance"}, {"text": "⚖️ Compare Stocks"}],
        [{"text": "🏭 Sector View"}, {"text": "❓ Help"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
    "is_persistent": True,
}



def command_menu():
    return (
        "<b>🚀 Welcome to StockGPT Bot</b>\n\n"
        "Tap a button below or type naturally.\n\n"
        "<b>Direct buttons:</b> Top Ideas, Range Bound, Swing, 52W Low, Momentum, Risky, Watchlist, Performance.\n\n"
        "<b>Guided buttons:</b>\n"
        "🔍 Stock Analysis → bot asks for stock\n"
        "📦 Stock Range → bot asks for stock\n"
        "📊 Stock Performance → bot asks for stock/signal\n"
        "⚖️ Compare Stocks → bot asks for two stocks\n"
        "🏭 Sector View → bot asks for sector\n\n"
        "<b>You can also type:</b>\n"
        "RECLTD\n"
        "range RECLTD\n"
        "compare RELIANCE TCS\n"
        "performance range\n\n"
        "<i>After sending/tapping, run your StockGPT Bot shortcut.</i>"
    )


def ux_symbols(df):
    if df is None or df.empty or "symbol" not in df.columns:
        return []

    return sorted(
        df["symbol"]
        .dropna()
        .astype(str)
        .str.upper()
        .str.strip()
        .unique()
        .tolist()
    )


def ux_alias_map():
    return {
        "hdfc": "HDFCBANK",
        "hdfc bank": "HDFCBANK",
        "hdfcbank": "HDFCBANK",
        "rec": "RECLTD",
        "rec ltd": "RECLTD",
        "recltd": "RECLTD",
        "recl": "RECLTD",
        "pfc": "PFC",
        "reliance": "RELIANCE",
        "ril": "RELIANCE",
        "tcs": "TCS",
        "infosys": "INFY",
        "infy": "INFY",
        "sbi": "SBIN",
        "sbin": "SBIN",
        "icici": "ICICIBANK",
        "icici bank": "ICICIBANK",
        "axis": "AXISBANK",
        "axis bank": "AXISBANK",
        "kotak": "KOTAKBANK",
        "kotak bank": "KOTAKBANK",
        "tata motors": "TATAMOTORS",
        "tata steel": "TATASTEEL",
        "bajaj finance": "BAJFINANCE",
        "asian paints": "ASIANPAINT",
        "pidilite": "PIDILITIND",
        "dmart": "DMART",
        "zomato": "ETERNAL",
        "eternal": "ETERNAL",
    }


def ux_clean_user_text(value):
    value = str(value or "").strip()

    # remove bot username from commands like /range@BotName RECLTD
    if value.startswith("/") and "@" in value.split()[0]:
        parts = value.split(maxsplit=1)
        first = parts[0].split("@", 1)[0]
        value = first + (" " + parts[1] if len(parts) > 1 else "")

    return " ".join(value.split())


def ux_normalize_symbol_text(value):
    value = str(value or "").lower().strip()

    noise = [
        "please", "pls", "stock", "share", "analysis", "analyse", "analyze",
        "tell me about", "show me", "what about", "how about", "why",
        "details", "detail", "view", "of", "the", "for", "is"
    ]

    for word in noise:
        value = value.replace(word, " ")

    value = re.sub(r"[^a-z0-9& ]", " ", value)
    return " ".join(value.split())


def ux_find_symbol(df, value):
    symbols = ux_symbols(df)
    symbol_set = set(symbols)

    raw = str(value or "").strip()
    clean = ux_normalize_symbol_text(raw)

    if not clean:
        return ""

    aliases = ux_alias_map()

    if clean in aliases and aliases[clean] in symbol_set:
        return aliases[clean]

    compact = re.sub(r"[^A-Z0-9&]", "", clean.upper())

    if compact in symbol_set:
        return compact

    for token in clean.upper().split():
        token = re.sub(r"[^A-Z0-9&]", "", token)

        if token in symbol_set:
            return token

    for symbol in symbols:
        if compact == re.sub(r"[^A-Z0-9&]", "", symbol.upper()):
            return symbol

    return ""


def ux_suggest_symbols(df, query, limit=8):
    query = re.sub(r"[^A-Z0-9&]", "", str(query or "").upper())

    if not query:
        return []

    suggestions = []

    for symbol in ux_symbols(df):
        compact = re.sub(r"[^A-Z0-9&]", "", symbol.upper())

        if compact.startswith(query):
            suggestions.append(symbol)

    for symbol in ux_symbols(df):
        compact = re.sub(r"[^A-Z0-9&]", "", symbol.upper())

        if query in compact and symbol not in suggestions:
            suggestions.append(symbol)

    return suggestions[:limit]


def command_suggest(df, text):
    parts = str(text or "").split(maxsplit=1)
    query = parts[1] if len(parts) > 1 else ""
    suggestions = ux_suggest_symbols(df, query)

    if not suggestions:
        return (
            "<b>🤔 I could not understand that.</b>\n\n"
            "Try:\n"
            "• RELIANCE\n"
            "• range RECLTD\n"
            "• top stocks\n"
            "• performance range\n"
            "• compare RELIANCE TCS"
        )

    message = "<b>Did you mean:</b>\n\n"

    for symbol in suggestions:
        message += f"• {escape_html(symbol)}\n"

    message += "\nType one symbol directly, example: <b>RELIANCE</b>"
    return message.strip()


def ux_route_natural_message(df, incoming_text):
    text = ux_clean_user_text(incoming_text)

    if not text:
        return "/menu"

    lowered = text.lower().strip()
    simple = re.sub(r"[^a-z0-9& ]", " ", lowered)
    simple = " ".join(simple.split())

    if text.startswith("/"):
        command = text.split(maxsplit=1)[0].split("@", 1)[0].lower()
        rest = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""

        if command in ["/start", "/menu"]:
            return "/menu"

        return command + (" " + rest if rest else "")

    button_routes = {
        "📊 top ideas": "/top",
        "top ideas": "/top",
        "📦 range bound": "/range",
        "range bound": "/range",
        "⚡ swing": "/swing",
        "swing": "/swing",
        "📉 52w low": "/low",
        "52w low": "/low",
        "🚀 momentum": "/high",
        "momentum": "/high",
        "⚠️ risky / avoid": "/risk",
        "risky / avoid": "/risk",
        "risky avoid": "/risk",
        "⭐ watchlist": "/watchlist",
        "watchlist": "/watchlist",
        "📈 performance": "/performance",
        "performance": "/performance",
        "🔍 stock analysis": "/menu",
        "stock analysis": "/menu",
        "❓ help": "/menu",
        "help": "/menu",
        "menu": "/menu",
    }

    if lowered in button_routes:
        return button_routes[lowered]

    if simple.startswith("compare "):
        body = simple.replace("compare", "", 1).replace(" and ", " ")
        found = []

        for token in body.split():
            symbol = ux_find_symbol(df, token)

            if symbol and symbol not in found:
                found.append(symbol)

        if len(found) >= 2:
            return f"/compare {found[0]} {found[1]}"

    if any(word in simple for word in ["range", "range bound", "rangebound", "sideways", "mean reversion", "support", "resistance"]):
        cleaned = simple

        for word in ["range bound", "rangebound", "range", "sideways", "mean reversion", "support", "resistance"]:
            cleaned = cleaned.replace(word, " ")

        symbol = ux_find_symbol(df, cleaned) or ux_find_symbol(df, simple)

        if symbol:
            return f"/range {symbol}"

        return "/range"

    if any(word in simple for word in ["performance", "accuracy", "backtest", "back test", "did it work", "result", "worked"]):
        symbol = ux_find_symbol(df, simple)

        if symbol:
            return f"/performance {symbol}"

        if "range" in simple:
            return "/performance range"
        if "swing" in simple or "bounce" in simple:
            return "/performance swing"
        if "risk" in simple or "avoid" in simple:
            return "/performance risk"
        if "top" in simple or "conviction" in simple:
            return "/performance top"

        return "/performance"

    list_routes = [
        (["top", "best", "best stocks", "top stocks", "top ideas", "high conviction", "conviction"], "/top"),
        (["low", "near low", "52w low", "52 week low", "cheap", "discount"], "/low"),
        (["swing", "bounce", "oversold", "short term", "short term stocks"], "/swing"),
        (["high", "near high", "52w high", "52 week high", "momentum", "breakout"], "/high"),
        (["risk", "avoid", "weak", "danger", "risky"], "/risk"),
        (["watchlist", "my watchlist"], "/watchlist"),
    ]

    for phrases, route in list_routes:
        if simple in phrases:
            return route

    if simple.startswith("sector "):
        sector_query = simple.replace("sector", "", 1).strip()

        if sector_query:
            return f"/sector {sector_query.upper()}"

    symbol = ux_find_symbol(df, simple)

    if symbol:
        return f"/why {symbol}"

    if len(simple.split()) <= 3:
        return f"/suggest {simple}"

    return "/menu"

SCAN_FILE = Path("data/scans/latest_scan.csv")
WATCHLIST_FILE = Path("data/watchlist/watchlist.csv")
STATE_FILE = Path("data/telegram/last_update_id.txt")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "").strip()

def parse_chat_ids(value):
    return [
        str(chat_id).strip()
        for chat_id in str(value).replace("\n", ",").split(",")
        if str(chat_id).strip()
    ]

ALLOWED_CHAT_IDS = parse_chat_ids(TELEGRAM_CHAT_ID)

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
            "reply_markup": MAIN_MENU_REPLY_MARKUP,
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
/performance - Signal performance tracker
/performance QUERY - Filter performance by signal/symbol
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



def command_performance(df, text):
    performance_file = Path("data/performance/signal_performance.csv")

    if not performance_file.exists():
        return (
            "<b>📊 Signal Performance</b>\n\n"
            "Performance data is not available yet.\n"
            "Run Phase6 Pipeline first, then try:\n"
            "/performance\n"
            "/performance range\n"
            "/performance swing\n"
            "/performance RELIANCE"
        )

    try:
        perf_df = pd.read_csv(performance_file)
    except Exception as e:
        return f"Could not read performance file: {escape_html(str(e))}"

    if perf_df.empty:
        return "Performance file exists but has no rows yet."

    needed_text_cols = [
        "symbol", "signal_type", "signal_direction", "horizon_bucket",
        "result_status", "sector", "industry", "sector_bucket"
    ]

    for col in needed_text_cols:
        if col not in perf_df.columns:
            perf_df[col] = ""
        perf_df[col] = perf_df[col].fillna("").astype(str)

    needed_numeric_cols = [
        "return_pct", "entry_price", "latest_price", "days_passed",
        "entry_final_score", "latest_final_score"
    ]

    for col in needed_numeric_cols:
        if col not in perf_df.columns:
            perf_df[col] = 0
        perf_df[col] = pd.to_numeric(perf_df[col], errors="coerce").fillna(0)

    if "is_success" not in perf_df.columns:
        perf_df["is_success"] = False

    perf_df["is_success"] = perf_df["is_success"].astype(bool)

    parts = text.strip().split(maxsplit=1)
    title_suffix = "All Signals"
    filtered = perf_df.copy()

    if len(parts) >= 2:
        query = parts[1].strip()
        query_upper = query.upper()
        query_lower = query.lower()
        symbol_df = perf_df[perf_df["symbol"].astype(str).str.upper() == query_upper]

        if not symbol_df.empty:
            filtered = symbol_df
            title_suffix = query_upper
        else:
            alias_map = {
                "range": "Range",
                "swing": "Swing",
                "risk": "Risk|Avoid|Breakdown",
                "avoid": "Avoid|Risk",
                "top": "Top Final",
                "high": "High Conviction|High Momentum",
                "low": "52W Low",
                "fundamental": "Fundamental",
                "rs": "Relative Strength",
                "relative": "Relative Strength",
            }

            pattern = alias_map.get(query_lower, query)

            filtered = perf_df[
                perf_df["signal_type"].str.contains(pattern, case=False, na=False)
                |
                perf_df["sector"].str.contains(query, case=False, na=False)
                |
                perf_df["industry"].str.contains(query, case=False, na=False)
                |
                perf_df["sector_bucket"].str.contains(query, case=False, na=False)
            ]
            title_suffix = query

    if filtered.empty:
        return f"No performance rows found for: <b>{escape_html(parts[1] if len(parts) >= 2 else 'All')}</b>"

    total = len(filtered)
    win_rate = filtered["is_success"].mean() * 100 if total else 0
    avg_return = filtered["return_pct"].mean() if total else 0
    median_return = filtered["return_pct"].median() if total else 0

    message = f"<b>📊 Signal Performance: {escape_html(title_suffix)}</b>\n"

    if "performance_scan_time" in filtered.columns and not filtered["performance_scan_time"].dropna().empty:
        message += f"<b>Updated:</b> {escape_html(filtered['performance_scan_time'].dropna().iloc[0])}\n"

    message += f"\nSignals Tested: {total}\n"
    message += f"Win Rate: {win_rate:.1f}%\n"
    message += f"Avg Return: {avg_return:.2f}%\n"
    message += f"Median Return: {median_return:.2f}%\n"

    summary = (
        filtered.groupby(["signal_type", "horizon_bucket"])
        .agg(
            signals=("symbol", "count"),
            win_rate=("is_success", "mean"),
            avg_return=("return_pct", "mean"),
            best_return=("return_pct", "max"),
            worst_return=("return_pct", "min"),
        )
        .reset_index()
        .sort_values(["avg_return", "win_rate"], ascending=[False, False])
        .head(10)
    )

    message += "\n<b>Top Signal Groups</b>\n"

    for _, row in summary.iterrows():
        message += (
            f"\n<b>{escape_html(row['signal_type'])}</b> | {escape_html(row['horizon_bucket'])}\n"
            f"Signals: {int(row['signals'])}"
            f" | Win: {safe_num(row['win_rate']) * 100:.1f}%"
            f" | Avg: {safe_num(row['avg_return']):.2f}%"
            f" | Best: {safe_num(row['best_return']):.2f}%"
            f" | Worst: {safe_num(row['worst_return']):.2f}%"
        )

    best = filtered.sort_values("return_pct", ascending=False).head(5)
    worst = filtered.sort_values("return_pct", ascending=True).head(5)

    message += "\n\n<b>Best Signals</b>\n"
    for _, row in best.iterrows():
        message += (
            f"\n{escape_html(row['symbol'])}"
            f" | {escape_html(row['signal_type'])}"
            f" | {safe_num(row['return_pct']):.2f}%"
            f" | {escape_html(row['horizon_bucket'])}"
        )

    message += "\n\n<b>Worst Signals</b>\n"
    for _, row in worst.iterrows():
        message += (
            f"\n{escape_html(row['symbol'])}"
            f" | {escape_html(row['signal_type'])}"
            f" | {safe_num(row['return_pct']):.2f}%"
            f" | {escape_html(row['horizon_bucket'])}"
        )

    message += "\n\nExamples: /performance range | /performance swing | /performance RELIANCE"
    message += "\n\n<i>Not financial advice. Research tool only.</i>"

    return message.strip()


# =========================
# UX V5 — Stateful Guided Flow
# =========================

CHAT_SESSIONS_FILE = Path("data/telegram/chat_sessions.json")


def safe_chat_ref(chat_id):
    """
    Safe non-reversible-ish reference for logs.
    Does not expose raw Telegram chat ID.
    """
    salt = TELEGRAM_BOT_TOKEN or "stockgpt"
    raw = f"{salt}:{str(chat_id)}"
    return "chat_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]


def chat_session_key(chat_id):
    """
    Key used in chat_sessions.json.
    Raw chat IDs are never saved.
    """
    salt = os.getenv("TELEGRAM_SESSION_SALT", "").strip() or TELEGRAM_BOT_TOKEN or "stockgpt"
    raw = f"{salt}:{str(chat_id)}"
    return "chat_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]


def load_chat_sessions():
    try:
        if CHAT_SESSIONS_FILE.exists():
            with open(CHAT_SESSIONS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)

            if isinstance(data, dict):
                return data
    except Exception as e:
        print(f"Could not load chat sessions: {e}")

    return {}


def save_chat_sessions(sessions):
    CHAT_SESSIONS_FILE.parent.mkdir(parents=True, exist_ok=True)

    with open(CHAT_SESSIONS_FILE, "w", encoding="utf-8") as f:
        json.dump(sessions, f, indent=2, sort_keys=True)


def set_chat_session(chat_id, waiting_for):
    sessions = load_chat_sessions()
    key = chat_session_key(chat_id)

    sessions[key] = {
        "waiting_for": waiting_for,
        "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    save_chat_sessions(sessions)


def get_chat_session(chat_id):
    sessions = load_chat_sessions()
    key = chat_session_key(chat_id)
    session = sessions.get(key, {})

    if not isinstance(session, dict):
        return {}

    return session


def clear_chat_session(chat_id):
    sessions = load_chat_sessions()
    key = chat_session_key(chat_id)

    if key in sessions:
        del sessions[key]
        save_chat_sessions(sessions)


def guided_button_mode(text):
    lowered = str(text or "").lower().strip()

    mapping = {
        "🔍 stock analysis": "stock_analysis",
        "stock analysis": "stock_analysis",
        "📦 stock range": "stock_range",
        "stock range": "stock_range",
        "📊 stock performance": "stock_performance",
        "stock performance": "stock_performance",
        "⚖️ compare stocks": "compare_stocks",
        "compare stocks": "compare_stocks",
        "🏭 sector view": "sector_view",
        "sector view": "sector_view",
    }

    return mapping.get(lowered, "")


def prompt_for_mode(mode):
    if mode == "stock_analysis":
        return (
            "<b>🔍 Stock Analysis</b>\n\n"
            "Which stock do you want to analyse?\n\n"
            "Type a symbol/name like:\n"
            "RECLTD\n"
            "RELIANCE\n"
            "HDFC Bank\n\n"
            "Quick examples: RECLTD | PFC | RELIANCE | TCS"
        )

    if mode == "stock_range":
        return (
            "<b>📦 Stock Range Analysis</b>\n\n"
            "Which stock do you want range-bound analysis for?\n\n"
            "Example:\n"
            "RECLTD"
        )

    if mode == "stock_performance":
        return (
            "<b>📊 Stock / Signal Performance</b>\n\n"
            "Type a stock or signal:\n\n"
            "Examples:\n"
            "RECLTD\n"
            "range\n"
            "swing\n"
            "risk\n"
            "top"
        )

    if mode == "compare_stocks":
        return (
            "<b>⚖️ Compare Stocks</b>\n\n"
            "Enter two stocks to compare.\n\n"
            "Examples:\n"
            "RECLTD PFC\n"
            "RELIANCE TCS\n"
            "HDFCBANK ICICIBANK"
        )

    if mode == "sector_view":
        return (
            "<b>🏭 Sector View</b>\n\n"
            "Which sector or industry do you want to check?\n\n"
            "Examples:\n"
            "Bank\n"
            "Power\n"
            "Finance\n"
            "IT\n"
            "Auto"
        )

    return command_menu()


def extract_two_symbols(df, text):
    cleaned = str(text or "").replace(",", " ").replace(" and ", " ")
    tokens = [t.strip() for t in cleaned.split() if t.strip()]
    found = []

    # First try token by token.
    for token in tokens:
        symbol = ux_find_symbol(df, token)
        if symbol and symbol not in found:
            found.append(symbol)

    if len(found) >= 2:
        return found[:2]

    # Then try two-word chunks for names like HDFC Bank.
    for i in range(len(tokens) - 1):
        chunk = tokens[i] + " " + tokens[i + 1]
        symbol = ux_find_symbol(df, chunk)
        if symbol and symbol not in found:
            found.append(symbol)

    return found[:2]


def route_pending_session(df, text, session):
    mode = session.get("waiting_for", "")
    raw = clean_text(text)

    if not raw:
        return {
            "reply": prompt_for_mode(mode),
            "command": "",
            "clear": False,
        }

    if raw.lower().strip() in ["/cancel", "cancel", "back", "menu"]:
        return {
            "reply": "Cancelled. Use /menu to start again.",
            "command": "",
            "clear": True,
        }

    if mode == "stock_analysis":
        symbol = ux_find_symbol(df, raw)

        if symbol:
            return {"reply": "", "command": f"/why {symbol}", "clear": True}

        return {
            "reply": command_suggest(df, "/suggest " + raw),
            "command": "",
            "clear": False,
        }

    if mode == "stock_range":
        symbol = ux_find_symbol(df, raw)

        if symbol:
            return {"reply": "", "command": f"/range {symbol}", "clear": True}

        return {
            "reply": command_suggest(df, "/suggest " + raw),
            "command": "",
            "clear": False,
        }

    if mode == "stock_performance":
        symbol = ux_find_symbol(df, raw)

        if symbol:
            return {"reply": "", "command": f"/performance {symbol}", "clear": True}

        query = raw.lower().strip()

        allowed = ["range", "swing", "risk", "avoid", "top", "low", "fundamental", "relative", "rs"]

        for item in allowed:
            if item in query:
                return {"reply": "", "command": f"/performance {item}", "clear": True}

        return {
            "reply": (
                "<b>📊 Performance</b>\n\n"
                "Type a stock or one of these signals:\n"
                "range, swing, risk, top, low\n\n"
                "Example: range"
            ),
            "command": "",
            "clear": False,
        }

    if mode == "compare_stocks":
        symbols = extract_two_symbols(df, raw)

        if len(symbols) >= 2:
            return {
                "reply": "",
                "command": f"/compare {symbols[0]} {symbols[1]}",
                "clear": True,
            }

        return {
            "reply": (
                "<b>⚖️ Compare Stocks</b>\n\n"
                "I need two valid stocks.\n\n"
                "Examples:\n"
                "RECLTD PFC\n"
                "RELIANCE TCS"
            ),
            "command": "",
            "clear": False,
        }

    if mode == "sector_view":
        return {
            "reply": "",
            "command": f"/sector {raw.upper()}",
            "clear": True,
        }

    return {
        "reply": "",
        "command": ux_route_natural_message(df, raw),
        "clear": True,
    }

COMMANDS = {
    "/help": command_menu,
    "/start": command_menu,
    "/menu": command_menu,
    "/suggest": command_suggest,
    "/top": command_top,
    "/low": command_low,
    "/swing": command_swing,
    "/high": command_high,
    "/risk": command_risk,
    "/watchlist": command_watchlist,
    "/stock": command_stock,
    "/why": command_why,
    "/sector": command_sector,
    "/basket": command_basket,
    "/compare": command_compare,
    "/range": command_range,
    "/performance": command_performance,
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
    if command in ["/help", "/start", "/menu"]:
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
        if not text:
            continue

        chat_ref = safe_chat_ref(chat_id)

        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            print(f"Ignoring unauthorized chat: {chat_ref}")
            continue

        mode = guided_button_mode(text)

        if mode:
            set_chat_session(chat_id, mode)
            print(f"Guided mode set for {chat_ref}: {mode}")
            send_message(chat_id, prompt_for_mode(mode))
            processed += 1
            continue

        session = get_chat_session(chat_id)

        if session:
            routed = route_pending_session(df, text, session)

            if routed.get("clear"):
                clear_chat_session(chat_id)

            if routed.get("reply"):
                print(f"Guided reply for {chat_ref}: {session.get('waiting_for', '')}")
                send_message(chat_id, routed["reply"])
                processed += 1
                continue

            text = routed.get("command", text)
        else:
            text = ux_route_natural_message(df, text)

        print(f"Processing command from {chat_ref}: {text}")

        try:
            reply = handle_command(text, df)
        except Exception as e:
            print(f"Command failed for {chat_ref}: {e}")
            reply = f"Command failed: {escape_html(str(e))}"

        if reply:
            send_message(chat_id, reply)
            processed += 1
    write_last_update_id(max_update_id)
    print(f"Processed commands: {processed}")
    print(f"Last update id saved: {max_update_id}")


if __name__ == "__main__":
    main()
