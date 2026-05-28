import importlib.util
import json
from pathlib import Path

BOT_PATH = Path("app/alerts/telegram_bot_commands.py")
WEBAPP_PATH = Path("webapp/index.html")

assert BOT_PATH.exists(), "telegram_bot_commands.py missing"
assert WEBAPP_PATH.exists(), "webapp/index.html missing"

spec = importlib.util.spec_from_file_location("bot", BOT_PATH)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

df = bot.load_scan()

assert df is not None, "load_scan returned None"
assert not df.empty, "latest scan is empty"
assert "symbol" in df.columns, "latest scan missing symbol column"


def route(payload):
    return bot.route_webapp_payload(df, json.dumps(payload))


def assert_command(payload, expected):
    out = route(payload)
    print(payload, "=>", out)
    assert out.get("command") == expected, f"{payload} expected {expected}, got {out}"


def assert_reply(payload):
    out = route(payload)
    print(payload, "=>", out)
    assert out.get("reply"), f"{payload} expected reply, got {out}"
    assert not out.get("command"), f"{payload} should not route command, got {out}"
    return out.get("reply", "")


# Core WebApp routes
assert_command({"action": "stock_analysis", "symbol": "RECLTD"}, "/why RECLTD")
assert_command({"action": "stock_analysis", "symbol": "rec"}, "/why RECLTD")
assert_command({"action": "stock_range", "symbol": "RECLTD"}, "/range RECLTD")
assert_command({"action": "stock_performance", "query": "range"}, "/performance range")
assert_command({"action": "stock_performance", "query": "swing"}, "/performance swing")
assert_command({"action": "stock_performance", "query": "risk"}, "/performance risk")
assert_command({"action": "compare", "symbol_a": "RECLTD", "symbol_b": "PFC"}, "/compare RECLTD PFC")
assert_command({"action": "sector", "query": "Bank"}, "/sector BANK")

# One-shot list routes
simple_routes = {
    "top": "/top",
    "range_list": "/range",
    "swing": "/swing",
    "low": "/low",
    "high": "/high",
    "risk": "/risk",
    "watchlist": "/watchlist",
    "performance": "/performance",
}

for action, expected in simple_routes.items():
    assert_command({"action": action}, expected)

# Advanced routes, if installed
advanced_routes = {
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
}

webapp_html = WEBAPP_PATH.read_text(encoding="utf-8")

for action, expected in advanced_routes.items():
    if f'value="{action}"' in webapp_html:
        assert_command({"action": action}, expected)

# Invalid stock inputs must not become random suggestions/commands
bad_reply = assert_reply({"action": "stock_analysis", "symbol": "stock analysis"})
assert "5PAISA" not in bad_reply, "Bad stock analysis returned unrelated 5PAISA suggestion"

bad_reply = assert_reply({"action": "stock_analysis", "symbol": "xyznotreal"})
assert "5PAISA" not in bad_reply, "Invalid stock returned unrelated 5PAISA suggestion"

assert_reply({"action": "stock_analysis", "symbol": ""})

# Sector must stay sector, never stock suggestion
sector_out = route({"action": "sector", "query": "Bank"})
assert sector_out.get("command") == "/sector BANK", sector_out

# Compare should require two valid symbols
assert_reply({"action": "compare", "symbol_a": "RECLTD", "symbol_b": ""})

# Bot commands should produce non-empty replies
commands_to_test = [
    "/top",
    "/range",
    "/swing",
    "/low",
    "/high",
    "/risk",
    "/performance",
    "/why RECLTD",
    "/range RECLTD",
    "/compare RECLTD PFC",
    "/sector BANK",
]

for command in commands_to_test:
    reply = bot.handle_command(command, df)
    print(command, "=>", str(reply)[:120])
    assert isinstance(reply, str) and reply.strip(), f"Empty reply for {command}"

# Advanced commands should also respond if installed
for command in [
    "/high_conviction",
    "/low_risk_quality",
    "/sector_adjusted_quality",
    "/range_accumulation",
    "/range_profit_booking",
    "/range_breakdown_risk",
]:
    if command in getattr(bot, "COMMANDS", {}):
        reply = bot.handle_command(command, df)
        print(command, "=>", str(reply)[:120])
        assert isinstance(reply, str) and reply.strip(), f"Empty reply for {command}"

# WebApp HTML sanity checks
required_html = [
    "StockGPT",
    "telegram-web-app.js",
    "stock_analysis",
    "stock_range",
    "stock_performance",
    "compare",
    "sector",
    "sendData",
]

for marker in required_html:
    assert marker in webapp_html, f"WebApp missing marker: {marker}"

# Mobile searchable dropdown should not depend on datalist
assert "combo-list" in webapp_html, "Custom mobile dropdown missing"
assert "setupCombo" in webapp_html, "setupCombo missing"
assert "<datalist" not in webapp_html.lower(), "datalist found; iPhone dropdown may fail again"

print("✅ StockGPT bot safety tests passed")


# Global reply quality checks
quality_commands = [
    "/top",
    "/range",
    "/swing",
    "/low",
    "/high",
    "/risk",
    "/performance",
    "/why RECLTD",
    "/range RECLTD",
    "/compare RECLTD PFC",
    "/sector BANK",
]

for command in [
    "/high_conviction",
    "/low_risk_quality",
    "/sector_adjusted_quality",
    "/range_accumulation",
    "/range_profit_booking",
    "/range_breakdown_risk",
]:
    if command in getattr(bot, "COMMANDS", {}):
        quality_commands.append(command)

for command in quality_commands:
    reply = bot.handle_command(command, df)
    assert isinstance(reply, str) and reply.strip(), f"Empty reply for {command}"
    assert (
        "Research tool only" in reply
        or "Not financial advice" in reply
        or "not financial advice" in reply.lower()
    ), f"Missing disclaimer for {command}"
    assert (
        "<b>How to use:</b>" in reply
        or "<b>How to read:</b>" in reply
    ), f"Missing usage guidance for {command}"

print("✅ Global reply quality checks passed")
