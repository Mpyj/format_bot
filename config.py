import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
DATABASE_URL = os.getenv("DATABASE_URL", "")
PORT = int(os.getenv("PORT", 8080))

# 📢 کانال
CHANNEL_ID = int(os.getenv("CHANNEL_ID", "0"))
CHANNEL_LINK = os.getenv("CHANNEL_LINK", "")

# 👑 ادمین
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

TEMP_DIR = "temp"
MAX_FILE_SIZE = 20 * 1024 * 1024