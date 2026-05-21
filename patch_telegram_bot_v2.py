from pathlib import Path
import shutil

BOT = Path("app/alerts/telegram_bot_commands.py")

if not BOT.exists():
    raise FileNotFoundError("app/alerts/telegram_bot_commands.py not found. Run this from repo root.")

backup = BOT.with_suffix(".py.bak_v2_commands")
shutil.copy2(BOT, backup)

text = BOT.read_text(encoding="utf-8")


def replace_once(old, new, label):
    global text

    if old in text:
        text = text.replace(old, new, 1)
        print(f"✅ {label}")
    else:
        print(f"⚠️ Not found / already changed: {label}")


# =========================
# 1. Update help command
# =========================

old_help = """/top - Top final conviction stocks
/low - 52W low + sector-adjusted quality
/swing - Swing candidates
/high - Near 52W high momentum
/risk - Avoid / risky stocks
/watchlist - Watchlist summary
/stock SYMBOL - Full stock snapshot

Examples:
/stock RELIANCE
/stock IDEA
/stock MTARTECH"""

new_help = """/top - Top final conviction stocks
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
/compare RELIANCE TCS"""

replace_once(old_help, new_help, "Update /help text")


# =========================
# 2. Add helper functions before handle_command
# =========================

insert_marker = "def handle_command(text, df):"

new_functions = r