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


TELEGRAM_WEBAPP_VERSION = "v202605281357"

TELEGRAM_WEBAPP_URL = os.getenv(
    "TELEGRAM_WEBAPP_URL",
    "https://rjganatra.github.io/StockGPT/"
).strip()


def stockgpt_webapp_url(action=""):
    base = TELEGRAM_WEBAPP_URL.rstrip("/")
    version = TELEGRAM_WEBAPP_VERSION

    if not action:
        return base + "/?v=" + version

    return base + "/?action=" + str(action).strip() + "&v=" + version

    if not action:
        return base + "/"

    return base + "/?action=" + str(action).strip()

MAIN_MENU_REPLY_MARKUP = {
    "keyboard": [
        [{"text": "🧠 Ask StockGPT", "web_app": {"url": stockgpt_webapp_url()}}],
        [{"text": "🔍 Stock Analysis", "web_app": {"url": stockgpt_webapp_url("stock_analysis")}},
         {"text": "📦 Stock Range", "web_app": {"url": stockgpt_webapp_url("stock_range")}}],
        [{"text": "📊 Stock Performance", "web_app": {"url": stockgpt_webapp_url("stock_performance")}},
         {"text": "⚖️ Compare Stocks", "web_app": {"url": stockgpt_webapp_url("compare")}}],
        [{"text": "🏭 Sector View", "web_app": {"url": stockgpt_webapp_url("sector")}}],
        [{"text": "📊 Top Ideas"}, {"text": "📦 Range Bound"}],
        [{"text": "⚡ Swing"}, {"text": "📉 52W Low"}],
        [{"text": "🚀 Momentum"}, {"text": "⚠️ Risky / Avoid"}],
        [{"text": "⭐ Watchlist"}, {"text": "📈 Performance"}],
        [{"text": "❓ Help"}],
    ],
    "resize_keyboard": True,
    "one_time_keyboard": False,
    "is_persistent": True,
}




def command_menu():
    return (
        "<b>🚀 Welcome to StockGPT Bot</b>\n\n"
        "Use the WebApp buttons below for one-shot queries.\n\n"
        "<b>Best flow:</b>\n"
        "1. Tap 🧠 Ask StockGPT or a form button\n"
        "2. Fill the form once\n"
        "3. Submit\n"
        "4. Run your StockGPT Bot shortcut once\n\n"
        "<b>You can also type naturally:</b>\n"
        "RECLTD\n"
        "range RECLTD\n"
        "compare RELIANCE TCS\n"
        "performance range\n\n"
        "<i>Research tool only. Not financial advice.</i>"
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

def safe_chat_ref(chat_id):
    """
    Privacy-safe chat reference for logs.
    Never prints or stores raw Telegram chat ID.
    """
    salt = TELEGRAM_BOT_TOKEN or "stockgpt"
    raw = f"{salt}:{str(chat_id)}"
    return "chat_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10]



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
        perf_df = pd.read_csv(performance_file, low_memory=False)
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
# UX V6 — Telegram WebApp Payload Router
# =========================


def normalize_query_text(value):
    value = clean_text(value)
    value = re.sub(r"[^A-Za-z0-9& ]", " ", value)
    return " ".join(value.split())


def exact_symbol_or_alias(df, value):
    raw = normalize_query_text(value)

    if not raw:
        return ""

    symbols = ux_symbols(df)
    symbol_set = set(symbols)

    aliases = ux_alias_map()
    lowered = raw.lower().strip()

    if lowered in aliases and aliases[lowered] in symbol_set:
        return aliases[lowered]

    compact = re.sub(r"[^A-Z0-9&]", "", raw.upper())

    if compact in symbol_set:
        return compact

    compact_lower = lowered.replace(" ", "")

    if compact_lower in aliases and aliases[compact_lower] in symbol_set:
        return aliases[compact_lower]

    return ""


def safe_symbol_suggestions(df, query, limit=8):
    q = normalize_query_text(query).upper()
    q_compact = re.sub(r"[^A-Z0-9&]", "", q)

    if len(q_compact) < 2:
        return []

    symbols = ux_symbols(df)

    starts = []
    contains = []

    for symbol in symbols:
        compact_symbol = re.sub(r"[^A-Z0-9&]", "", str(symbol).upper())

        if compact_symbol.startswith(q_compact):
            starts.append(symbol)
        elif len(q_compact) >= 3 and q_compact in compact_symbol:
            contains.append(symbol)

    out = []

    for symbol in starts + contains:
        if symbol not in out:
            out.append(symbol)

    return out[:limit]


def html_lines(items):
    return chr(10).join(items)


def stock_not_found_message(df, query, purpose="stock"):
    query = clean_text(query)

    if not query:
        return html_lines([
            "<b>Stock required</b>",
            "",
            "Please enter a valid stock symbol like:",
            "RECLTD",
            "RELIANCE",
            "TCS",
        ])

    suggestions = safe_symbol_suggestions(df, query)

    if not suggestions:
        return html_lines([
            f"<b>I could not find this {escape_html(purpose)}:</b> {escape_html(query)}",
            "",
            "Try exact NSE symbol or common name.",
            "Examples:",
            "RECLTD",
            "RELIANCE",
            "HDFCBANK",
        ])

    lines = [
        f"<b>I could not find exact match for:</b> {escape_html(query)}",
        "",
        "<b>Did you mean:</b>",
    ]

    for symbol in suggestions:
        lines.append(f"• {escape_html(symbol)}")

    lines.extend([
        "",
        "Submit the exact symbol from the form.",
    ])

    return html_lines(lines)


def route_stock_payload_strict(df, value, command_prefix, purpose):
    found = exact_symbol_or_alias(df, value)

    if found:
        return {"reply": "", "command": f"{command_prefix} {found}"}

    return {
        "reply": stock_not_found_message(df, value, purpose),
        "command": "",
    }


def route_compare_payload_strict(df, symbol_a, symbol_b, query=""):
    a = exact_symbol_or_alias(df, symbol_a)
    b = exact_symbol_or_alias(df, symbol_b)

    if (not a or not b) and query:
        cleaned = normalize_query_text(query)
        tokens = cleaned.replace(",", " ").replace(" and ", " ").split()

        found = []

        for token in tokens:
            symbol = exact_symbol_or_alias(df, token)

            if symbol and symbol not in found:
                found.append(symbol)

        if len(found) >= 2:
            a, b = found[0], found[1]

    if a and b:
        return {
            "reply": "",
            "command": f"/compare {a} {b}",
        }

    return {
        "reply": html_lines([
            "<b>⚖️ Compare Stocks</b>",
            "",
            "I need two exact stock symbols.",
            "",
            "Examples:",
            "RECLTD and PFC",
            "RELIANCE and TCS",
            "HDFCBANK and ICICIBANK",
        ]),
        "command": "",
    }


def route_webapp_payload(df, payload_text):
    try:
        payload = json.loads(str(payload_text or "{}"))
    except Exception as e:
        return {
            "reply": f"Could not read WebApp request: {escape_html(str(e))}",
            "command": "",
        }

    if not isinstance(payload, dict):
        return {
            "reply": "Invalid WebApp request.",
            "command": "",
        }

    action = clean_text(payload.get("action", "")).lower().strip()

    action_aliases = {
        "analysis": "stock_analysis",
        "stock": "stock_analysis",
        "why": "stock_analysis",
        "range": "stock_range",
        "stockrange": "stock_range",
        "performance": "stock_performance",
        "stockperformance": "stock_performance",
        "compare_stocks": "compare",
        "sector_view": "sector",
    }

    action = action_aliases.get(action, action)

    symbol = clean_text(payload.get("symbol", ""))
    query = clean_text(payload.get("query", ""))
    symbol_a = clean_text(payload.get("symbol_a", ""))
    symbol_b = clean_text(payload.get("symbol_b", ""))

    if action == "stock_analysis":
        return route_stock_payload_strict(df, symbol or query, "/why", "stock")

    if action == "stock_range":
        return route_stock_payload_strict(df, symbol or query, "/range", "stock")

    if action == "stock_performance":
        value = symbol or query
        found = exact_symbol_or_alias(df, value)

        if found:
            return {"reply": "", "command": f"/performance {found}"}

        value_clean = normalize_query_text(value).lower()

        if not value_clean:
            return {"reply": "", "command": "/performance"}

        signal_aliases = {
            "range": "range",
            "range bound": "range",
            "rangebound": "range",
            "swing": "swing",
            "bounce": "swing",
            "risk": "risk",
            "avoid": "risk",
            "top": "top",
            "conviction": "top",
            "low": "low",
            "52w low": "low",
            "fundamental": "fundamental",
            "relative": "relative",
            "rs": "relative",
        }

        for key, target in signal_aliases.items():
            if key in value_clean:
                return {"reply": "", "command": f"/performance {target}"}

        return {
            "reply": html_lines([
                "<b>📊 Performance</b>",
                "",
                "Enter a valid stock or signal.",
                "",
                "Examples:",
                "RECLTD",
                "range",
                "swing",
                "risk",
                "top",
            ]),
            "command": "",
        }

    if action == "compare":
        return route_compare_payload_strict(df, symbol_a, symbol_b, query)

    if action == "sector":
        sector_query = clean_text(query or symbol)

        if sector_query:
            return {"reply": "", "command": f"/sector {sector_query.upper()}"}

        return {
            "reply": html_lines([
                "<b>🏭 Sector View</b>",
                "",
                "Please enter a sector or industry like Bank, Power, Finance, IT, Auto.",
            ]),
            "command": "",
        }

    if action == "range_plan":
        symbol_value = symbol or query
        buy_price = clean_text(payload.get("buy_price", ""))

        if not symbol_value or not buy_price:
            return {
                "reply": (
                    "<b>📦 Range Plan</b>\n\n"
                    "Please enter stock symbol and buy price.\n\n"
                    "Example: RECLTD and 365"
                ),
                "command": "",
            }

        return {"reply": "", "command": f"/range_plan {symbol_value} {buy_price}"}

    simple_actions = {
        "top": "/top",
        "range_list": "/range",
        "swing": "/swing",
        "low": "/low",
        "high": "/high",
        "risk": "/risk",
        "watchlist": "/watchlist",
        "performance": "/performance",
        "high_conviction": "/high_conviction",
        "low_risk_quality": "/low_risk_quality",
        "sector_adjusted_quality": "/sector_adjusted_quality",
        "range_accumulation": "/range_accumulation",
        "range_profit_booking": "/range_profit_booking",
        "range_breakdown_risk": "/range_breakdown_risk",
        "performance_range": "/performance range",
        "performance_swing": "/performance swing",
        "performance_risk": "/performance risk",
        "performance_top": "/performance top",
        "performance_combo": "/performance_combo",
    }

    if action in simple_actions:
        return {"reply": "", "command": simple_actions[action]}

    return {
        "reply": html_lines([
            "<b>🧠 Ask StockGPT</b>",
            "",
            "Invalid request from form. Please reopen the StockGPT form and try again.",
        ]),
        "command": "",
    }



# =========================
# UX V6.4 — Advanced WebApp Action Commands
# =========================

def sg_num(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def sg_col(df, preferred, fallbacks=None, default=0):
    fallbacks = fallbacks or []

    if preferred in df.columns:
        return preferred

    for col in fallbacks:
        if col in df.columns:
            return col

    df[preferred] = default
    return preferred


def sg_text(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value or "").strip()


def sg_html_lines(lines):
    return chr(10).join(lines)


def sg_score_band(row):
    for col in ["score_band", "band"]:
        if col in row.index and sg_text(row.get(col)):
            return sg_text(row.get(col))
    return ""


def sg_row_line(row, include_range=False):
    symbol = escape_html(sg_text(row.get("symbol", "")))
    sector = escape_html(sg_text(row.get("sector", "")))
    price = sg_num(row.get("current_price", 0))
    final_score = sg_num(row.get("final_conviction_score", row.get("score", 0)))
    active_fund = sg_num(row.get("active_fundamental_score", row.get("fundamental_score", 0)))
    adjusted_fund = sg_num(row.get("sector_adjusted_fundamental_score", active_fund))
    risk = sg_num(row.get("risk_penalty", 0))
    rsi = sg_num(row.get("rsi", 0))

    line = (
        f"• <b>{symbol}</b>"
        f" | ₹{price:.2f}"
        f" | Final {final_score:.1f}"
        f" | Active Fund {active_fund:.1f}"
        f" | Adj Fund {adjusted_fund:.1f}"
        f" | Risk {risk:.1f}"
        f" | RSI {rsi:.1f}"
    )

    if sector:
        line += f" | {sector}"

    if include_range:
        distance_low = sg_num(row.get("distance_pct", 0))
        distance_high = sg_num(row.get("distance_from_high_pct", 0))
        line += f" | From Low {distance_low:.1f}% | From High {distance_high:.1f}%"

    return line


def sg_table_message(title, subtitle, data, include_range=False, limit=12):
    if data is None or data.empty:
        return sg_html_lines([
            f"<b>{title}</b>",
            "",
            "No stocks matched this filter in the latest scan.",
        ])

    lines = [
        f"<b>{title}</b>",
    ]

    if subtitle:
        lines.extend(["", subtitle])

    lines.append("")

    for _, row in data.head(limit).iterrows():
        lines.append(sg_row_line(row, include_range=include_range))

    lines.extend([
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return sg_html_lines(lines)


def command_high_conviction(df, text):
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    risk_col = sg_col(df, "risk_penalty", [], 0)

    data = df.copy()
    data[score_col] = pd.to_numeric(data[score_col], errors="coerce").fillna(0)
    data[risk_col] = pd.to_numeric(data[risk_col], errors="coerce").fillna(0)

    filtered = data[
        data[score_col] >= 60
    ].sort_values(
        [score_col, risk_col],
        ascending=[False, True]
    )

    return sg_table_message(
        "🎯 High Conviction Ideas",
        "Sorted by final conviction score with lower risk preferred.",
        filtered,
        include_range=False,
        limit=12,
    )


def command_low_risk_quality(df, text):
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    risk_col = sg_col(df, "risk_penalty", [], 0)
    active_col = sg_col(df, "active_fundamental_score", ["sector_adjusted_fundamental_score", "fundamental_score"], 0)

    data = df.copy()
    for col in [score_col, risk_col, active_col]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    filtered = data[
        (data[active_col] >= 55)
        &
        (data[risk_col] <= 10)
        &
        (data[score_col] >= 50)
    ].sort_values(
        [score_col, active_col, risk_col],
        ascending=[False, False, True]
    )

    return sg_table_message(
        "🛡️ Low Risk Quality",
        "Active fundamentals above threshold, low risk penalty, and decent conviction.",
        filtered,
        include_range=False,
        limit=12,
    )


def command_sector_adjusted_quality(df, text):
    adjusted_col = sg_col(df, "sector_adjusted_fundamental_score", ["active_fundamental_score", "fundamental_score"], 0)
    active_col = sg_col(df, "active_fundamental_score", [adjusted_col, "fundamental_score"], 0)
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    risk_col = sg_col(df, "risk_penalty", [], 0)

    data = df.copy()
    for col in [adjusted_col, active_col, score_col, risk_col]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    filtered = data[
        (data[adjusted_col] >= 55)
        &
        (data[active_col] >= 50)
        &
        (data[risk_col] <= 15)
    ].sort_values(
        [adjusted_col, score_col, risk_col],
        ascending=[False, False, True]
    )

    return sg_table_message(
        "🏭 Sector-Adjusted Quality",
        "Prioritises sector-adjusted fundamentals, active fundamental strength, and controlled risk.",
        filtered,
        include_range=False,
        limit=12,
    )


def command_range_accumulation(df, text):
    distance_low_col = sg_col(df, "distance_pct", [], 0)
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    rsi_col = sg_col(df, "rsi", [], 0)
    risk_col = sg_col(df, "risk_penalty", [], 0)

    data = df.copy()
    for col in [distance_low_col, score_col, rsi_col, risk_col]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    if "range_signal" in data.columns:
        mask = data["range_signal"].astype(str).str.contains("accumulation|lower|support", case=False, na=False)
    else:
        mask = (
            (data[distance_low_col] <= 20)
            &
            (data[rsi_col].between(35, 60))
            &
            (data[risk_col] <= 18)
        )

    filtered = data[mask].sort_values(
        [score_col, distance_low_col, risk_col],
        ascending=[False, True, True]
    )

    return sg_table_message(
        "📦 Range Accumulation Zone",
        "Stocks closer to lower/support area with acceptable RSI and risk.",
        filtered,
        include_range=True,
        limit=12,
    )


def command_range_profit_booking(df, text):
    distance_high_col = sg_col(df, "distance_from_high_pct", [], 0)
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    rsi_col = sg_col(df, "rsi", [], 0)

    data = df.copy()
    for col in [distance_high_col, score_col, rsi_col]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    if "range_signal" in data.columns:
        mask = data["range_signal"].astype(str).str.contains("profit|upper|resistance|booking", case=False, na=False)
    else:
        mask = (
            (data[distance_high_col] <= 15)
            |
            (data[rsi_col] >= 65)
        )

    filtered = data[mask].sort_values(
        [distance_high_col, score_col],
        ascending=[True, False]
    )

    return sg_table_message(
        "💰 Range Profit Booking Zone",
        "Stocks near upper range/resistance area or showing higher RSI.",
        filtered,
        include_range=True,
        limit=12,
    )


def command_range_breakdown_risk(df, text):
    distance_low_col = sg_col(df, "distance_pct", [], 0)
    score_col = sg_col(df, "final_conviction_score", ["score"], 0)
    rsi_col = sg_col(df, "rsi", [], 0)
    risk_col = sg_col(df, "risk_penalty", [], 0)

    data = df.copy()
    for col in [distance_low_col, score_col, rsi_col, risk_col]:
        data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    if "range_signal" in data.columns:
        mask = data["range_signal"].astype(str).str.contains("breakdown|risk|weak", case=False, na=False)
    else:
        mask = (
            (data[risk_col] >= 15)
            |
            ((data[distance_low_col] <= 10) & (data[rsi_col] < 40))
        )

    filtered = data[mask].sort_values(
        [risk_col, score_col],
        ascending=[False, True]
    )

    return sg_table_message(
        "⚠️ Range Breakdown Risk",
        "Stocks with elevated risk, weak RSI, or lower-range breakdown characteristics.",
        filtered,
        include_range=True,
        limit=12,
    )


# =========================
# V9 — Personal Range Plan
# =========================

def rp_num(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def rp_text(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value or "").strip()


def rp_lines(items):
    return chr(10).join([str(x) for x in items])


def rp_price(value):
    value = rp_num(value, 0)

    if value <= 0:
        return "NA"

    return f"₹{value:.2f}"


def rp_find_symbol(df, value):
    value = rp_text(value)

    if not value:
        return ""

    try:
        found = exact_symbol_or_alias(df, value)
        if found:
            return found
    except Exception:
        pass

    try:
        found = ux_find_symbol(df, value)
        if found:
            return found
    except Exception:
        pass

    compact = re.sub(r"[^A-Z0-9&]", "", value.upper())

    if "symbol" in df.columns:
        symbols = df["symbol"].dropna().astype(str).str.upper().str.strip().tolist()

        if compact in set(symbols):
            return compact

    return ""


def rp_find_row(df, symbol):
    symbol = rp_find_symbol(df, symbol)

    if not symbol or "symbol" not in df.columns:
        return None, symbol

    rows = df[df["symbol"].astype(str).str.upper().str.strip() == symbol]

    if rows.empty:
        return None, symbol

    return rows.iloc[0], symbol


def rp_zone_label(pct):
    if pct <= -10:
        return "deep below your buy price"
    if pct <= -5:
        return "below your buy price"
    if pct < 5:
        return "near your buy price"
    if pct < 10:
        return "above your buy price"
    return "well above your buy price"


def rp_action_view(pct_from_buy, distance_low, distance_high, risk, rsi):
    if risk >= 20:
        return (
            "⚠️ Risk-first zone",
            "Risk penalty is elevated. Avoid averaging down blindly; wait for confirmation."
        )

    if pct_from_buy <= -7 and distance_low <= 20 and 35 <= rsi <= 60:
        return (
            "📦 Accumulation watch zone",
            "Price is meaningfully below your buy price and closer to lower range/support area."
        )

    if -7 < pct_from_buy < 7:
        return (
            "⏳ Hold / observe zone",
            "Price is still near your buy band. Let the range confirm before adding or exiting."
        )

    if pct_from_buy >= 7 or distance_high <= 15 or rsi >= 65:
        return (
            "💰 Profit-booking watch zone",
            "Price is above your buy price or near upper range/resistance. Avoid fresh chasing."
        )

    return (
        "🔎 Neutral watch zone",
        "The setup is not clearly accumulation or profit-booking yet."
    )


def command_range_plan(df, text):
    parts = str(text or "").split()

    if len(parts) < 3:
        return rp_lines([
            "<b>📦 Range Plan</b>",
            "",
            "<b>How to use:</b>",
            "Send stock symbol and your buy price.",
            "",
            "Example:",
            "<code>/range_plan RECLTD 365</code>",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    raw_symbol = parts[1]
    raw_buy = parts[2].replace(",", "")

    try:
        buy_price = float(raw_buy)
    except Exception:
        return rp_lines([
            "<b>📦 Range Plan</b>",
            "",
            "Buy price should be a number.",
            "",
            "Example:",
            "<code>/range_plan RECLTD 365</code>",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    if buy_price <= 0:
        return rp_lines([
            "<b>📦 Range Plan</b>",
            "",
            "Buy price must be greater than zero.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    row, symbol = rp_find_row(df, raw_symbol)

    if row is None:
        return rp_lines([
            "<b>📦 Range Plan</b>",
            "",
            f"I could not find exact stock: <b>{escape_html(raw_symbol)}</b>",
            "",
            "Try exact NSE symbol like RECLTD, PFC, RELIANCE.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    company = escape_html(rp_text(row.get("company_name", "")))
    sector = escape_html(rp_text(row.get("sector", "")))
    industry = escape_html(rp_text(row.get("industry", "")))

    current_price = rp_num(row.get("current_price", 0))
    final_score = rp_num(row.get("final_conviction_score", row.get("score", 0)))
    active_fund = rp_num(row.get("active_fundamental_score", row.get("fundamental_score", 0)))
    adjusted_fund = rp_num(row.get("sector_adjusted_fundamental_score", active_fund))
    risk = rp_num(row.get("risk_penalty", 0))
    rsi = rp_num(row.get("rsi", 0))
    distance_low = rp_num(row.get("distance_pct", 0))
    distance_high = rp_num(row.get("distance_from_high_pct", 0))
    volume = rp_num(row.get("volume_ratio", 0))

    if current_price <= 0:
        return rp_lines([
            "<b>📦 Range Plan</b>",
            "",
            f"Current price not available for <b>{escape_html(symbol)}</b>.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    pct_from_buy = ((current_price - buy_price) / buy_price) * 100
    action_title, action_note = rp_action_view(pct_from_buy, distance_low, distance_high, risk, rsi)

    lower_add_zone = buy_price * 0.93
    upper_book_zone = buy_price * 1.07
    deeper_risk_zone = buy_price * 0.90

    title = f"<b>📦 Range Plan: {escape_html(symbol)}</b>"

    if company and company.upper() != symbol.upper():
        title += f" — {company}"

    sector_line = ""

    if sector and industry and sector != industry:
        sector_line = f"{sector} / {industry}"
    elif sector or industry:
        sector_line = sector or industry

    lines = [
        title,
    ]

    if sector_line:
        lines.append(f"Sector: {sector_line}")

    lines.extend([
        "",
        "<b>Your position context</b>",
        f"Buy price: <b>{rp_price(buy_price)}</b>",
        f"Current price: <b>{rp_price(current_price)}</b>",
        f"Move from buy: <b>{pct_from_buy:+.2f}%</b> — {rp_zone_label(pct_from_buy)}",
        "",
        "<b>Range zones from your buy price</b>",
        f"Accumulation watch: around <b>{rp_price(lower_add_zone)}</b> or lower (-7%)",
        f"Profit-booking watch: around <b>{rp_price(upper_book_zone)}</b> or higher (+7%)",
        f"Breakdown caution: below <b>{rp_price(deeper_risk_zone)}</b> (-10%)",
        "",
        "<b>Latest StockGPT scan</b>",
        f"Final conviction: {final_score:.1f}",
        f"Active fundamental: {active_fund:.1f} | Sector-adjusted: {adjusted_fund:.1f}",
        f"Risk penalty: {risk:.1f}",
        f"RSI: {rsi:.1f} | Volume: {volume:.2f}x",
        f"52W range context: {distance_low:.1f}% above low | {distance_high:.1f}% below high",
        "",
        "<b>Action view</b>",
        f"{action_title}",
        action_note,
        "",
        "<b>How to use:</b>",
        "Use this as a range-trading decision map. Do not average down unless price stabilises near support.",
        "",
        "<b>What to watch:</b>",
        "Confirm support/resistance on chart, avoid illiquid names, and keep stop/risk level clear.",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return rp_lines(lines)


# =========================
# V10 — Combo Signal Performance
# =========================

def combo_perf_build_if_needed():
    from pathlib import Path
    import subprocess
    import sys

    summary = Path("data/performance/combo_signal_performance.csv")
    members = Path("data/performance/combo_signal_members.csv")

    if not summary.exists() or not members.exists():
        subprocess.run([sys.executable, "app/performance/combo_signal_performance.py"], check=True)

    return summary, members


def combo_perf_lines(items):
    return chr(10).join([str(x) for x in items])


def command_performance_combo(df, text):
    import pandas as pd

    summary_file, members_file = combo_perf_build_if_needed()

    summary = pd.read_csv(summary_file, low_memory=False)

    parts = str(text or "").split()
    requested_combo = parts[1].strip() if len(parts) > 1 else ""

    if requested_combo:
        row_df = summary[summary["combo_id"].astype(str).str.lower() == requested_combo.lower()]

        if row_df.empty:
            available = summary["combo_id"].astype(str).head(12).tolist()
            return combo_perf_lines([
                "<b>📊 Combo Signal Performance</b>",
                "",
                f"Combo not found: <b>{escape_html(requested_combo)}</b>",
                "",
                "<b>Available combos:</b>",
                *[f"• {escape_html(x)}" for x in available],
                "",
                "<i>Research tool only. Not financial advice.</i>",
            ])

        row = row_df.iloc[0]
        members = pd.read_csv(members_file, low_memory=False)

        combo_members = members[members["combo_id"].astype(str).str.lower() == requested_combo.lower()]

        lines = [
            f"<b>📊 Combo Signal: {escape_html(str(row.get('combo_name', requested_combo)))}</b>",
            "",
            "<b>Quick read:</b>",
            escape_html(str(row.get("interpretation", ""))),
            "",
            "<b>Signal recipe:</b>",
            escape_html(str(row.get("description", ""))),
            "",
            "<b>Current performance snapshot:</b>",
            f"Matches now: <b>{int(row.get('current_matches', 0))}</b>",
            f"Avg final conviction: {float(row.get('avg_final_conviction', 0)):.2f}",
            f"Avg range score: {float(row.get('avg_range_score', 0)):.2f}",
            f"Avg RSI: {float(row.get('avg_rsi', 0)):.2f}",
            f"Avg risk penalty: {float(row.get('avg_risk_penalty', 0)):.2f}",
            f"Positive 1M rate: {float(row.get('positive_1m_rate', 0)):.1f}%",
            f"Positive 3M rate: {float(row.get('positive_3m_rate', 0)):.1f}%",
            "",
            "<b>Top current matches:</b>",
        ]

        if combo_members.empty:
            lines.append("No current symbols matched this combo.")
        else:
            for _, m in combo_members.head(10).iterrows():
                lines.append(
                    f"• <b>{escape_html(str(m.get('symbol', '')))}</b>"
                    f" | ₹{float(m.get('current_price', 0)):.2f}"
                    f" | Final {float(m.get('final_conviction_score', 0)):.1f}"
                    f" | Range {float(m.get('range_score', 0)):.1f}"
                    f" | RSI {float(m.get('rsi', 0)):.1f}"
                    f" | Risk {float(m.get('risk_penalty', 0)):.1f}"
                )

        lines.extend([
            "",
            "<b>How to use:</b>",
            "This is closer to how real strategy filters work: multiple conditions together, not one isolated signal.",
            "",
            "<b>What to watch:</b>",
            "Small samples can mislead. Confirm chart, liquidity, news and your own risk level.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

        return combo_perf_lines(lines)

    summary = summary.sort_values(
        ["positive_1m_rate", "avg_final_conviction", "current_matches"],
        ascending=[False, False, False],
    )

    lines = [
        "<b>📊 Combo Signal Performance</b>",
        "",
        "<b>Quick read:</b>",
        "This checks performance-style snapshots for multi-condition signal recipes.",
        "",
        "<b>Why this matters:</b>",
        "A single signal like 52W low can be weak alone. But 52W low + range accumulation + controlled risk can behave very differently.",
        "",
        "<b>Top combo recipes:</b>",
    ]

    for _, row in summary.head(12).iterrows():
        lines.append(
            f"• <b>{escape_html(str(row.get('combo_name', '')))}</b>"
            f" | ID: <code>{escape_html(str(row.get('combo_id', '')))}</code>"
            f" | Matches {int(row.get('current_matches', 0))}"
            f" | 1M+ {float(row.get('positive_1m_rate', 0)):.1f}%"
            f" | 3M+ {float(row.get('positive_3m_rate', 0)):.1f}%"
            f" | Avg Final {float(row.get('avg_final_conviction', 0)):.1f}"
        )

    lines.extend([
        "",
        "<b>Open one combo:</b>",
        "<code>/performance_combo 52w_low_bearish_strong_rsi</code>",
        "<code>/performance_combo range_accumulation_low_risk</code>",
        "<code>/performance_combo high_conviction_quality</code>",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return combo_perf_lines(lines)

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
    "/high_conviction": command_high_conviction,
    "/low_risk_quality": command_low_risk_quality,
    "/sector_adjusted_quality": command_sector_adjusted_quality,
    "/range_accumulation": command_range_accumulation,
    "/range_profit_booking": command_range_profit_booking,
    "/range_breakdown_risk": command_range_breakdown_risk,
    "/range_plan": command_range_plan,
    "/performance_combo": command_performance_combo,
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



# =========================
# UX V7 FINAL — Global Telegram Reply Quality Wrapper
# =========================

def stockgpt_command_family(command_text):
    raw = str(command_text or "").strip()
    command = raw.split(maxsplit=1)[0].lower() if raw else ""

    mapping = {
        "/top": ("📊 Top Ideas", "Highest ranked opportunities from the latest scan."),
        "/range": ("📦 Range View", "Range-bound or stock-specific range analysis."),
        "/swing": ("⚡ Swing Candidates", "Short-term opportunity candidates from the scan."),
        "/low": ("📉 52W Low View", "Stocks closer to 52-week low zones."),
        "/high": ("🚀 Momentum View", "Stocks closer to strength / 52-week high zones."),
        "/risk": ("⚠️ Risk / Avoid Watch", "Stocks with weaker or risky characteristics."),
        "/watchlist": ("⭐ Watchlist", "Your configured watchlist view."),
        "/performance": ("📈 Performance", "Signal or stock performance review."),
        "/why": ("🔍 Stock Analysis", "Single-stock explanation from latest scan."),
        "/stock": ("🔍 Stock Analysis", "Single-stock explanation from latest scan."),
        "/sector": ("🏭 Sector View", "Sector or industry-filtered scan output."),
        "/basket": ("🧺 Basket View", "Basket-filtered scan output."),
        "/compare": ("⚖️ Compare Stocks", "Side-by-side stock comparison."),
        "/high_conviction": ("🎯 High Conviction Ideas", "Highest conviction names after ranking and risk checks."),
        "/low_risk_quality": ("🛡️ Low Risk Quality", "Quality names with controlled risk penalty."),
        "/sector_adjusted_quality": ("🏭 Sector-Adjusted Quality", "Quality names after sector-relative adjustment."),
        "/range_accumulation": ("📦 Range Accumulation Zone", "Potential range support / accumulation watchlist."),
        "/range_profit_booking": ("💰 Range Profit Booking Zone", "Potential upper-range / resistance watchlist."),
        "/range_breakdown_risk": ("⚠️ Range Breakdown Risk", "Range names with weakness or breakdown risk."),
    }

    return mapping.get(command, ("🧠 StockGPT", "Latest StockGPT scan output."))


def stockgpt_has_disclaimer(reply):
    text = str(reply or "").lower()
    return (
        "not financial advice" in text
        or "research tool only" in text
        or "paper/research use only" in text
    )


def stockgpt_clean_reply(reply):
    reply = str(reply or "").strip()
    reply = re.sub(r"\n{4,}", "\n\n\n", reply)
    return reply


def stockgpt_quality_footer(command_text):
    title, interpretation = stockgpt_command_family(command_text)

    return chr(10).join([
        "",
        "<b>How to use:</b> " + escape_html(interpretation),
        "<b>Watch:</b> Do not act only on this bot output. Check chart, liquidity, news, broader market and position sizing.",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])


def stockgpt_should_add_context(reply):
    reply = str(reply or "")

    if not reply.strip():
        return False

    # Do not over-wrap tiny errors repeatedly.
    if "Command failed:" in reply:
        return True

    return True


def stockgpt_polish_reply(command_text, reply):
    reply = stockgpt_clean_reply(reply)

    if not stockgpt_should_add_context(reply):
        return reply

    footer_needed = not stockgpt_has_disclaimer(reply)
    how_to_needed = "<b>How to use:</b>" not in reply and "<b>How to read:</b>" not in reply

    if footer_needed and how_to_needed:
        reply += stockgpt_quality_footer(command_text)
    elif footer_needed:
        reply += chr(10) + chr(10) + "<i>Research tool only. Not financial advice.</i>"
    elif how_to_needed:
        title, interpretation = stockgpt_command_family(command_text)
        reply += chr(10) + chr(10) + "<b>How to use:</b> " + escape_html(interpretation)

    return stockgpt_clean_reply(reply)


# Keep original command engine intact. Wrap output only.
_stockgpt_original_handle_command = handle_command


def handle_command(text, df):
    reply = _stockgpt_original_handle_command(text, df)
    return stockgpt_polish_reply(text, reply)



# =========================
# UX V8 — Human Telegram Reply Renderer
# =========================

def r8_num(value, default=0.0):
    try:
        if pd.isna(value):
            return default
        return float(value)
    except Exception:
        return default


def r8_text(value):
    try:
        if pd.isna(value):
            return ""
    except Exception:
        pass
    return str(value or "").strip()


def r8_lines(items):
    return chr(10).join([str(x) for x in items])


def r8_col(df, preferred, fallbacks=None, default=0):
    fallbacks = fallbacks or []

    if preferred in df.columns:
        return preferred

    for col in fallbacks:
        if col in df.columns:
            return col

    df[preferred] = default
    return preferred


def r8_price(value):
    value = r8_num(value, 0)

    if value <= 0:
        return "NA"

    return f"₹{value:.2f}"


def r8_pct(value):
    return f"{r8_num(value, 0):.1f}%"


def r8_clean(value, max_len=120):
    value = r8_text(value)
    value = re.sub(r"\\s+", " ", value).strip()

    if not value:
        return ""

    if len(value) > max_len:
        value = value[:max_len].rstrip() + "..."

    return escape_html(value)


def r8_prepare_df(df):
    data = df.copy()

    numeric_cols = [
        "current_price",
        "final_conviction_score",
        "score",
        "technical_score",
        "fundamental_score",
        "active_fundamental_score",
        "sector_adjusted_fundamental_score",
        "risk_penalty",
        "rsi",
        "volume_ratio",
        "distance_pct",
        "distance_from_high_pct",
        "market_cap",
    ]

    for col in numeric_cols:
        if col in data.columns:
            data[col] = pd.to_numeric(data[col], errors="coerce").fillna(0)

    return data


def r8_symbol_exact(df, value):
    value = r8_text(value)

    if not value:
        return ""

    try:
        found = exact_symbol_or_alias(df, value)
        if found:
            return found
    except Exception:
        pass

    try:
        found = ux_find_symbol(df, value)
        if found:
            return found
    except Exception:
        pass

    compact = re.sub(r"[^A-Z0-9&]", "", value.upper())

    if "symbol" in df.columns:
        symbols = df["symbol"].dropna().astype(str).str.upper().str.strip().tolist()

        if compact in set(symbols):
            return compact

    return ""


def r8_find_row(df, value):
    symbol = r8_symbol_exact(df, value)

    if not symbol or "symbol" not in df.columns:
        return None, ""

    rows = df[df["symbol"].astype(str).str.upper().str.strip() == symbol]

    if rows.empty:
        return None, symbol

    return rows.iloc[0], symbol


def r8_score_label(value, high_good=True):
    value = r8_num(value, 0)

    if high_good:
        if value >= 75:
            return "excellent"
        if value >= 65:
            return "strong"
        if value >= 50:
            return "decent"
        if value >= 35:
            return "mixed"
        return "weak"

    if value <= 6:
        return "low"
    if value <= 12:
        return "controlled"
    if value <= 18:
        return "moderate"
    return "high"


def r8_stock_one_liner(row, mode="general"):
    symbol = escape_html(r8_text(row.get("symbol", "")))
    sector = escape_html(r8_text(row.get("sector", "")))
    price = r8_price(row.get("current_price", 0))
    final_score = r8_num(row.get("final_conviction_score", row.get("score", 0)))
    active = r8_num(row.get("active_fundamental_score", row.get("fundamental_score", 0)))
    adjusted = r8_num(row.get("sector_adjusted_fundamental_score", active))
    risk = r8_num(row.get("risk_penalty", 0))
    rsi = r8_num(row.get("rsi", 0))

    line = (
        f"• <b>{symbol}</b> | {price} | Final {final_score:.1f} | "
        f"Active {active:.1f} | Adj {adjusted:.1f} | Risk {risk:.1f} | RSI {rsi:.1f}"
    )

    if sector:
        line += f" | {sector}"

    if mode.startswith("range"):
        line += (
            f" | Low+ {r8_pct(row.get('distance_pct', 0))}"
            f" | High- {r8_pct(row.get('distance_from_high_pct', 0))}"
        )

    return line


def r8_stock_detail(row, mode="general"):
    symbol = escape_html(r8_text(row.get("symbol", "")))
    company = escape_html(r8_text(row.get("company_name", "")))
    sector = escape_html(r8_text(row.get("sector", "")))
    industry = escape_html(r8_text(row.get("industry", "")))

    final_score = r8_num(row.get("final_conviction_score", row.get("score", 0)))
    tech = r8_num(row.get("technical_score", 0))
    fund = r8_num(row.get("fundamental_score", 0))
    active = r8_num(row.get("active_fundamental_score", fund))
    adjusted = r8_num(row.get("sector_adjusted_fundamental_score", active))
    risk = r8_num(row.get("risk_penalty", 0))
    rsi = r8_num(row.get("rsi", 0))
    volume = r8_num(row.get("volume_ratio", 0))
    low_distance = r8_num(row.get("distance_pct", 0))
    high_distance = r8_num(row.get("distance_from_high_pct", 0))

    title = f"<b>{symbol}</b>"

    if company and company.upper() != symbol.upper():
        title += f" — {company}"

    lines = [
        title,
        f"Price: <b>{r8_price(row.get('current_price', 0))}</b>",
    ]

    if sector or industry:
        if sector and industry and sector != industry:
            lines.append(f"Sector: {sector} / {industry}")
        else:
            lines.append(f"Sector: {sector or industry}")

    lines.extend([
        "",
        "<b>Scorecard:</b>",
        f"Final conviction: <b>{final_score:.1f}</b> ({r8_score_label(final_score)})",
        f"Technical: {tech:.1f} | Fundamental: {fund:.1f}",
        f"Active fundamental: {active:.1f} | Sector-adjusted: {adjusted:.1f}",
        f"Risk penalty: <b>{risk:.1f}</b> ({r8_score_label(risk, high_good=False)})",
        "",
        "<b>Market behaviour:</b>",
        f"RSI: {rsi:.1f} | Volume: {volume:.2f}x",
        f"Range: {low_distance:.1f}% above 52W low | {high_distance:.1f}% below 52W high",
    ])

    reason = (
        r8_clean(row.get("reasons", ""))
        or r8_clean(row.get("technical_reasons", ""))
        or r8_clean(row.get("fundamental_reasons", ""))
    )

    if reason:
        lines.extend([
            "",
            "<b>Why it is showing up:</b>",
            reason,
        ])

    quick = "Mixed setup. Use it as a watchlist candidate, not a direct trade."

    if final_score >= 65 and risk <= 12:
        quick = "Strong scan profile with controlled risk."
    elif adjusted >= 60 and active >= 55:
        quick = "Quality is strong versus sector/active fundamental filters."
    elif risk >= 18:
        quick = "Risk is elevated. Treat this as caution-first."
    elif mode.startswith("range"):
        quick = "Range context matters more than conviction alone here."

    lines.extend([
        "",
        "<b>Quick read:</b>",
        quick,
        "",
        "<b>How to use:</b>",
        "Use this as a stock-specific research summary. Compare score, quality, risk and range context before deciding.",
        "",
        "<b>What to watch:</b>",
        "Check chart confirmation, liquidity, news and broader market direction before acting.",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return r8_lines(lines)


def r8_list_message(title, quick_read, logic, data, mode="general", limit=8):
    if data is None or data.empty:
        return r8_lines([
            f"<b>{title}</b>",
            "",
            "<b>Quick read:</b>",
            "No stocks matched this filter in the latest scan.",
            "",
            "<b>What to do next</b>",
            "Try another filter or wait for the next scan update.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    lines = [
        f"<b>{title}</b>",
        "",
        "<b>Quick read:</b>",
        escape_html(quick_read),
        "",
        "<b>Filter logic:</b>",
        escape_html(logic),
        "",
        "<b>Top results:</b>",
    ]

    for _, row in data.head(limit).iterrows():
        lines.append(r8_stock_one_liner(row, mode=mode))

    lines.extend([
        "",
        "<b>How to use:</b>",
        "Use this as a shortlist. Open individual stock analysis before making any decision.",
        "",
        "<b>What to watch:</b>",
        "Avoid chasing gaps. Confirm trend, support/resistance, liquidity and news.",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return r8_lines(lines)


def r8_sort(data, columns, ascending):
    available_cols = []
    available_asc = []

    for col, asc in zip(columns, ascending):
        if col in data.columns:
            available_cols.append(col)
            available_asc.append(asc)

    if not available_cols:
        return data

    return data.sort_values(available_cols, ascending=available_asc)


def r8_top(df):
    data = r8_prepare_df(df)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    risk_col = r8_col(data, "risk_penalty", [], 0)

    data = r8_sort(data, [score_col, risk_col], [False, True])

    return r8_list_message(
        "📊 Top Ideas",
        "Highest ranked names from the latest scan, with risk used as a secondary check.",
        "Sorted by final conviction score, then lower risk penalty.",
        data,
        mode="general",
    )


def r8_swing(df):
    data = r8_prepare_df(df)
    tech_col = r8_col(data, "technical_score", [], 0)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    rsi_col = r8_col(data, "rsi", [], 0)
    risk_col = r8_col(data, "risk_penalty", [], 0)

    filtered = data[
        (data[rsi_col].between(35, 70))
        &
        (data[risk_col] <= 18)
    ]

    filtered = r8_sort(filtered, [tech_col, score_col, risk_col], [False, False, True])

    return r8_list_message(
        "⚡ Swing Candidates",
        "Short-term candidates with acceptable RSI and controlled risk penalty.",
        "RSI 35–70, risk penalty ≤ 18, sorted by technical and conviction strength.",
        filtered,
        mode="general",
    )


def r8_low(df):
    data = r8_prepare_df(df)
    low_col = r8_col(data, "distance_pct", [], 0)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    risk_col = r8_col(data, "risk_penalty", [], 0)

    filtered = data[data[low_col] >= 0]
    filtered = r8_sort(filtered, [low_col, score_col, risk_col], [True, False, True])

    return r8_list_message(
        "📉 52W Low Watch",
        "Stocks closer to their 52-week low area. These may be value setups or falling knives.",
        "Sorted by distance from 52W low, then conviction score.",
        filtered,
        mode="range",
    )


def r8_high(df):
    data = r8_prepare_df(df)
    high_col = r8_col(data, "distance_from_high_pct", [], 0)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    tech_col = r8_col(data, "technical_score", [], 0)

    filtered = data[data[high_col] >= 0]
    filtered = r8_sort(filtered, [high_col, score_col, tech_col], [True, False, False])

    return r8_list_message(
        "🚀 Momentum / 52W High Watch",
        "Stocks closer to strength zones. Good for momentum watch, risky for chasing.",
        "Sorted by closeness to 52W high, then conviction and technical score.",
        filtered,
        mode="range",
    )


def r8_risk(df):
    data = r8_prepare_df(df)
    risk_col = r8_col(data, "risk_penalty", [], 0)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)

    filtered = data[data[risk_col] > 0]
    filtered = r8_sort(filtered, [risk_col, score_col], [False, True])

    return r8_list_message(
        "⚠️ Risk / Avoid Watch",
        "Names with elevated risk penalty or weaker scan characteristics.",
        "Sorted by highest risk penalty first.",
        filtered,
        mode="general",
    )


def r8_range_list(df):
    data = r8_prepare_df(df)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    low_col = r8_col(data, "distance_pct", [], 0)
    high_col = r8_col(data, "distance_from_high_pct", [], 0)
    risk_col = r8_col(data, "risk_penalty", [], 0)

    if "range_score" in data.columns:
        data["range_score"] = pd.to_numeric(data["range_score"], errors="coerce").fillna(0)
        filtered = r8_sort(data, ["range_score", score_col, risk_col], [False, False, True])
        logic = "Sorted by range score, conviction and lower risk."
    else:
        filtered = data[
            (data[low_col] >= 0)
            &
            (data[high_col] >= 0)
            &
            (data[risk_col] <= 20)
        ]
        filtered = r8_sort(filtered, [score_col, risk_col], [False, True])
        logic = "Range-compatible names with available 52W low/high distance and controlled risk."

    return r8_list_message(
        "📦 Range Bound Opportunities",
        "Potential range or mean-reversion candidates from the latest scan.",
        logic,
        filtered,
        mode="range",
    )


def r8_range_symbol(df, symbol):
    row, found = r8_find_row(df, symbol)

    if row is None:
        return r8_lines([
            "<b>📦 Range Analysis</b>",
            "",
            f"I could not find exact stock: <b>{escape_html(symbol)}</b>",
            "",
            "Try exact NSE symbol like RECLTD, PFC, RELIANCE.",
            "",
            "<b>How to use:</b>",
            "Submit an exact NSE symbol from the WebApp searchable dropdown.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    return r8_stock_detail(row, mode="range")


def r8_why(df, symbol):
    row, found = r8_find_row(df, symbol)

    if row is None:
        return r8_lines([
            "<b>🔍 Stock Analysis</b>",
            "",
            f"I could not find exact stock: <b>{escape_html(symbol)}</b>",
            "",
            "Try exact NSE symbol like RECLTD, PFC, RELIANCE.",
            "",
            "<b>How to use:</b>",
            "Submit an exact NSE symbol from the WebApp searchable dropdown.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    return r8_stock_detail(row, mode="why")


def r8_compare(df, a, b):
    row_a, sym_a = r8_find_row(df, a)
    row_b, sym_b = r8_find_row(df, b)

    if row_a is None or row_b is None:
        return r8_lines([
            "<b>⚖️ Compare Stocks</b>",
            "",
            "I need two exact valid symbols.",
            "",
            "Examples:",
            "RECLTD PFC",
            "RELIANCE TCS",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    metrics = [
        ("Price", r8_price(row_a.get("current_price", 0)), r8_price(row_b.get("current_price", 0))),
        ("Final conviction", f"{r8_num(row_a.get('final_conviction_score', row_a.get('score', 0))):.1f}", f"{r8_num(row_b.get('final_conviction_score', row_b.get('score', 0))):.1f}"),
        ("Technical", f"{r8_num(row_a.get('technical_score', 0)):.1f}", f"{r8_num(row_b.get('technical_score', 0)):.1f}"),
        ("Active fundamental", f"{r8_num(row_a.get('active_fundamental_score', row_a.get('fundamental_score', 0))):.1f}", f"{r8_num(row_b.get('active_fundamental_score', row_b.get('fundamental_score', 0))):.1f}"),
        ("Sector-adjusted", f"{r8_num(row_a.get('sector_adjusted_fundamental_score', 0)):.1f}", f"{r8_num(row_b.get('sector_adjusted_fundamental_score', 0)):.1f}"),
        ("Risk penalty", f"{r8_num(row_a.get('risk_penalty', 0)):.1f}", f"{r8_num(row_b.get('risk_penalty', 0)):.1f}"),
        ("RSI", f"{r8_num(row_a.get('rsi', 0)):.1f}", f"{r8_num(row_b.get('rsi', 0)):.1f}"),
    ]

    score_a = r8_num(row_a.get("final_conviction_score", row_a.get("score", 0)))
    score_b = r8_num(row_b.get("final_conviction_score", row_b.get("score", 0)))
    risk_a = r8_num(row_a.get("risk_penalty", 0))
    risk_b = r8_num(row_b.get("risk_penalty", 0))

    winner = sym_a if (score_a - risk_a) >= (score_b - risk_b) else sym_b

    lines = [
        "<b>⚖️ Compare Stocks</b>",
        "",
        f"<b>Quick read:</b> On score-minus-risk basis, <b>{escape_html(winner)}</b> looks stronger in the latest scan.",
        "",
        f"<b>{escape_html(sym_a)}</b> vs <b>{escape_html(sym_b)}</b>",
        "",
    ]

    for label, va, vb in metrics:
        lines.append(f"• {label}: <b>{escape_html(sym_a)}</b> {va} | <b>{escape_html(sym_b)}</b> {vb}")

    lines.extend([
        "",
        "<b>How to use:</b>",
        "Prefer the stock with stronger conviction and lower risk only after checking chart and news.",
        "",
        "<i>Research tool only. Not financial advice.</i>",
    ])

    return r8_lines(lines)


def r8_sector(df, query):
    query = r8_text(query)

    if not query:
        return r8_lines([
            "<b>🏭 Sector View</b>",
            "",
            "Enter a sector or industry like Bank, Power, IT, Auto.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    data = r8_prepare_df(df)

    mask = pd.Series([False] * len(data))

    for col in ["sector", "industry", "sector_bucket"]:
        if col in data.columns:
            mask = mask | data[col].astype(str).str.contains(query, case=False, na=False)

    filtered = data[mask]
    score_col = r8_col(filtered, "final_conviction_score", ["score"], 0) if not filtered.empty else "final_conviction_score"
    risk_col = r8_col(filtered, "risk_penalty", [], 0) if not filtered.empty else "risk_penalty"

    if not filtered.empty:
        filtered = r8_sort(filtered, [score_col, risk_col], [False, True])

    return r8_list_message(
        f"🏭 Sector View: {query.upper()}",
        f"Best matching names from sector/industry search for '{query}'.",
        "Filtered by sector, industry or sector bucket, then sorted by conviction and risk.",
        filtered,
        mode="general",
    )


def r8_advanced(df, mode):
    data = r8_prepare_df(df)
    score_col = r8_col(data, "final_conviction_score", ["score"], 0)
    active_col = r8_col(data, "active_fundamental_score", ["fundamental_score"], 0)
    adjusted_col = r8_col(data, "sector_adjusted_fundamental_score", [active_col], 0)
    risk_col = r8_col(data, "risk_penalty", [], 0)
    rsi_col = r8_col(data, "rsi", [], 0)
    low_col = r8_col(data, "distance_pct", [], 0)
    high_col = r8_col(data, "distance_from_high_pct", [], 0)

    if mode == "high_conviction":
        filtered = data[data[score_col] >= 60]
        filtered = r8_sort(filtered, [score_col, risk_col], [False, True])
        return r8_list_message(
            "🎯 High Conviction Ideas",
            "Strongest conviction names from the latest scan.",
            "Final conviction ≥ 60, sorted by conviction and lower risk.",
            filtered,
            mode="general",
        )

    if mode == "low_risk_quality":
        filtered = data[(data[active_col] >= 55) & (data[risk_col] <= 10)]
        filtered = r8_sort(filtered, [active_col, score_col, risk_col], [False, False, True])
        return r8_list_message(
            "🛡️ Low Risk Quality",
            "Quality candidates where risk penalty is controlled.",
            "Active fundamental ≥ 55 and risk penalty ≤ 10.",
            filtered,
            mode="general",
        )

    if mode == "sector_adjusted_quality":
        filtered = data[(data[adjusted_col] >= 55) & (data[active_col] >= 50) & (data[risk_col] <= 15)]
        filtered = r8_sort(filtered, [adjusted_col, score_col, risk_col], [False, False, True])
        return r8_list_message(
            "🏭 Sector-Adjusted Quality",
            "Quality candidates after sector-relative adjustment.",
            "Sector-adjusted fundamental ≥ 55, active fundamental ≥ 50, risk ≤ 15.",
            filtered,
            mode="general",
        )

    if mode == "range_accumulation":
        filtered = data[(data[low_col] <= 20) & (data[rsi_col].between(35, 60)) & (data[risk_col] <= 18)]
        filtered = r8_sort(filtered, [score_col, low_col, risk_col], [False, True, True])
        return r8_list_message(
            "📦 Range Accumulation Zone",
            "Possible lower-range/support watchlist names.",
            "Distance from low ≤ 20%, RSI 35–60, risk ≤ 18.",
            filtered,
            mode="range",
        )

    if mode == "range_profit_booking":
        filtered = data[(data[high_col] <= 15) | (data[rsi_col] >= 65)]
        filtered = r8_sort(filtered, [high_col, score_col], [True, False])
        return r8_list_message(
            "💰 Range Profit Booking Zone",
            "Names closer to upper-range/resistance areas.",
            "Distance from 52W high ≤ 15% or RSI ≥ 65.",
            filtered,
            mode="range",
        )

    if mode == "range_breakdown_risk":
        filtered = data[(data[risk_col] >= 15) | ((data[low_col] <= 10) & (data[rsi_col] < 40))]
        filtered = r8_sort(filtered, [risk_col, score_col], [False, True])
        return r8_list_message(
            "⚠️ Range Breakdown Risk",
            "Caution list for range failure or weak setups.",
            "Risk ≥ 15 or near low with weak RSI.",
            filtered,
            mode="range",
        )

    return ""


def r8_human_handle_command(text, df):
    raw = r8_text(text)
    parts = raw.split()
    command = parts[0].lower() if parts else ""
    args = parts[1:]

    if command == "/top":
        return r8_top(df)

    if command == "/swing":
        return r8_swing(df)

    if command == "/low":
        return r8_low(df)

    if command == "/high":
        return r8_high(df)

    if command == "/risk":
        return r8_risk(df)

    if command == "/range":
        if args:
            return r8_range_symbol(df, args[0])
        return r8_range_list(df)

    if command == "/range_plan":
        return command_range_plan(df, raw)

    if command in ["/why", "/stock"]:
        if args:
            return r8_why(df, args[0])
        return r8_lines([
            "<b>🔍 Stock Analysis</b>",
            "",
            "Please provide a stock symbol.",
            "Example: /why RECLTD",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    if command == "/compare":
        if len(args) >= 2:
            return r8_compare(df, args[0], args[1])
        return r8_lines([
            "<b>⚖️ Compare Stocks</b>",
            "",
            "Please provide two symbols.",
            "Example: /compare RECLTD PFC",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    if command == "/sector":
        return r8_sector(df, " ".join(args))

    if command == "/high_conviction":
        return r8_advanced(df, "high_conviction")

    if command == "/low_risk_quality":
        return r8_advanced(df, "low_risk_quality")

    if command == "/sector_adjusted_quality":
        return r8_advanced(df, "sector_adjusted_quality")

    if command == "/range_accumulation":
        return r8_advanced(df, "range_accumulation")

    if command == "/range_profit_booking":
        return r8_advanced(df, "range_profit_booking")

    if command == "/range_breakdown_risk":
        return r8_advanced(df, "range_breakdown_risk")

    # Performance and watchlist may rely on existing project-specific history/config.
    if command in ["/performance", "/watchlist", "/basket"]:
        old_reply = _stockgpt_v8_previous_handle_command(raw, df)
        return r8_lines([
            f"<b>{'📈 Performance' if command == '/performance' else '⭐ Watchlist' if command == '/watchlist' else '🧺 Basket View'}</b>",
            "",
            "<b>Quick read:</b>",
            "This view uses the existing StockGPT backend output.",
            "",
            old_reply,
            "",
            "<b>How to use:</b>",
            "Use this as a research summary and verify the underlying details before acting.",
            "",
            "<i>Research tool only. Not financial advice.</i>",
        ])

    return _stockgpt_v8_previous_handle_command(raw, df)


_stockgpt_v8_previous_handle_command = handle_command


def handle_command(text, df):
    return r8_human_handle_command(text, df)


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
        webapp_data = message.get("web_app_data", {})
        webapp_payload = ""

        if isinstance(webapp_data, dict):
            webapp_payload = clean_text(webapp_data.get("data", ""))

        text = clean_text(message.get("text", ""))

        chat_ref = safe_chat_ref(chat_id)

        if webapp_payload:
            parsed_webapp = route_webapp_payload(df, webapp_payload)

            if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
                print(f"Ignoring unauthorized WebApp request: {chat_ref}")
                continue

            if parsed_webapp.get("reply"):
                print(f"Processing WebApp request from {chat_ref}: reply")
                send_message(chat_id, parsed_webapp["reply"])
                processed += 1
                continue

            text = clean_text(parsed_webapp.get("command", ""))

        if not text:
            continue

        if ALLOWED_CHAT_IDS and chat_id not in ALLOWED_CHAT_IDS:
            print(f"Ignoring unauthorized chat: {chat_ref}")
            continue

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
