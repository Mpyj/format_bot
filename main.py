import os
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telebot

from config import BOT_TOKEN, PORT
from utils.database import engine
from utils.models import Base
from utils.cleanup import ensure_temp_dir, cleanup_old_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

bot = telebot.TeleBot(BOT_TOKEN, threaded=False)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ۱) ساخت پوشه temp
    ensure_temp_dir()
    cleanup_old_files()

    # ۲) ساخت جدول‌های دیتابیس
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("✅ جدول‌های دیتابیس آماده‌ست")
    except Exception as e:
        logger.error(f"❌ خطا در اتصال دیتابیس: {e}")

    # ۳) ایمپورت هندلرها
    from handlers import (  # noqa
        start, image, ocr, archive, site, network, finance, text_tools,
        media, pdf, creativity, admin, middleware
    )

    # ۴) ست کردن وبهوک
    domain = os.getenv("RAILWAY_PUBLIC_DOMAIN")
    if domain and BOT_TOKEN:
        webhook_url = f"https://{domain}/{BOT_TOKEN}"
        try:
            bot.remove_webhook()
            bot.set_webhook(url=webhook_url)
            logger.info(f"✅ وبهوک ست شد: {webhook_url}")
        except Exception as e:
            logger.error(f"❌ خطا در ست کردن وبهوک: {e}")
    else:
        logger.warning("⚠️ دامنه یا توکن موجود نیست (لوکال؟)")

    yield

    await engine.dispose()
    logger.info("🛑 خاموش شد")


app = FastAPI(lifespan=lifespan, title="Format Bot")


@app.get("/")
async def root():
    return {"status": "alive", "bot": "format_bot"}


@app.get("/healthz")
async def health():
    return JSONResponse({"status": "ok"}, status_code=200)


@app.post(f"/{BOT_TOKEN}")
async def webhook(request: Request):
    if request.headers.get("content-type") == "application/json":
        try:
            json_string = (await request.body()).decode("utf-8")
            update = telebot.types.Update.de_json(json_string)
            bot.process_new_updates([update])
        except Exception as e:
            logger.warning(f"خطا در پردازش آپدیت: {e}")
        return JSONResponse({"ok": True})
    return JSONResponse({"ok": False}, status_code=403)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=PORT)