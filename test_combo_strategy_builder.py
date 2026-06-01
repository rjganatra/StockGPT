import importlib.util
import json

spec = importlib.util.spec_from_file_location("bot", "app/alerts/telegram_bot_commands.py")
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

df = bot.load_scan()

payload = {
    "action": "performance_combo_custom",
    "factors": ["near_52w_low", "bearish", "watchable_rsi"]
}

out = bot.route_webapp_payload(df, json.dumps(payload))
assert out.get("command") == "/performance_combo_custom near_52w_low,bearish,watchable_rsi", out

reply = bot.handle_command(out["command"], df)
assert "Custom Combo Strategy" in reply, reply
assert "Your signal recipe" in reply, reply
assert "Current matches" in reply, reply
assert "Research tool only" in reply, reply

print("✅ Combo strategy builder tests passed")
