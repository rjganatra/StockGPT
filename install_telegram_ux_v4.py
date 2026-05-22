from pathlib import Path
import shutil
import re

BOT_PATH = Path("app/alerts/telegram_bot_commands.py")
TELEGRAM_STATE = Path("data/telegram/last_update_id.txt")

UX_HELPERS = r