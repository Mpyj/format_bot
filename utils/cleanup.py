import os
import time
import logging
from config import TEMP_DIR

logger = logging.getLogger(__name__)

def ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)

def delete_file(path: str):
    try:
        if path and os.path.exists(path):
            os.remove(path)
    except Exception as e:
        logger.warning(f"خطا در حذف {path}: {e}")

def cleanup_old_files(max_age_seconds: int = 3600):
    if not os.path.exists(TEMP_DIR):
        return
    now = time.time()
    for name in os.listdir(TEMP_DIR):
        if name == ".gitkeep":
            continue
        path = os.path.join(TEMP_DIR, name)
        try:
            if os.path.isfile(path) and now - os.path.getmtime(path) > max_age_seconds:
                os.remove(path)
                logger.info(f"🗑 فایل قدیمی پاک شد: {name}")
        except Exception as e:
            logger.warning(f"خطا در پاک‌سازی {name}: {e}")