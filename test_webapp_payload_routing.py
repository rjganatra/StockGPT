import importlib.util
import json

spec = importlib.util.spec_from_file_location(
    "bot",
    "app/alerts/telegram_bot_commands.py"
)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

df = bot.load_scan()

base_tests = [
    ({"action": "stock_analysis", "symbol": "RECLTD"}, "/why RECLTD"),
    ({"action": "stock_analysis", "symbol": "rec"}, "/why RECLTD"),
    ({"action": "stock_analysis", "symbol": "RELIANCE"}, "/why RELIANCE"),
    ({"action": "stock_range", "symbol": "RECLTD"}, "/range RECLTD"),
    ({"action": "stock_performance", "query": "range"}, "/performance range"),
    ({"action": "stock_performance", "query": "swing"}, "/performance swing"),
    ({"action": "stock_performance", "query": "risk"}, "/performance risk"),
    ({"action": "compare", "symbol_a": "RECLTD", "symbol_b": "PFC"}, "/compare RECLTD PFC"),
    ({"action": "sector", "query": "Bank"}, "/sector BANK"),
    ({"action": "sector", "query": "Power"}, "/sector POWER"),
    ({"action": "top"}, "/top"),
    ({"action": "range_list"}, "/range"),
    ({"action": "swing"}, "/swing"),
    ({"action": "low"}, "/low"),
    ({"action": "high"}, "/high"),
    ({"action": "risk"}, "/risk"),
    ({"action": "performance"}, "/performance"),
]

for payload, expected in base_tests:
    out = bot.route_webapp_payload(df, json.dumps(payload))
    print(payload, "=>", out)
    assert out.get("command") == expected, (payload, out, expected)

symbols = ["RECLTD", "PFC", "RELIANCE", "TCS", "HDFCBANK", "INFY", "SBIN", "ICICIBANK"]
signals = ["range", "swing", "risk", "top", "low", "fundamental", "relative"]
sectors = ["Bank", "Power", "Finance", "IT", "Auto", "Metal", "Energy", "FMCG"]

stress_payloads = []

for symbol in symbols:
    stress_payloads.append({"action": "stock_analysis", "symbol": symbol})
    stress_payloads.append({"action": "stock_range", "symbol": symbol})
    stress_payloads.append({"action": "stock_performance", "query": symbol})

for signal in signals:
    stress_payloads.append({"action": "stock_performance", "query": signal})

for sector in sectors:
    stress_payloads.append({"action": "sector", "query": sector})

for i in range(len(symbols) - 1):
    stress_payloads.append({
        "action": "compare",
        "symbol_a": symbols[i],
        "symbol_b": symbols[i + 1],
    })

invalids = [
    {"action": "stock_analysis", "symbol": ""},
    {"action": "stock_analysis", "symbol": "stock analysis"},
    {"action": "stock_analysis", "symbol": "xyznotreal"},
    {"action": "stock_range", "symbol": "range please"},
    {"action": "compare", "symbol_a": "RECLTD", "symbol_b": ""},
    {"action": "sector", "query": ""},
]

stress_payloads.extend(invalids)
stress_payloads = stress_payloads + stress_payloads + stress_payloads

for payload in stress_payloads:
    out = bot.route_webapp_payload(df, json.dumps(payload))
    assert out.get("command") or out.get("reply"), (payload, out)

    if payload.get("action") == "sector" and payload.get("query"):
        assert out.get("command", "").startswith("/sector "), (payload, out)

    if payload.get("action") == "stock_analysis" and payload.get("symbol") in ["stock analysis", "xyznotreal", ""]:
        assert not out.get("command"), (payload, out)
        assert "5PAISA" not in out.get("reply", ""), (payload, out)

print(f"✅ Passed {len(stress_payloads) + len(base_tests)} WebApp routing tests")
