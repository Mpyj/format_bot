import logging
from config import BOT_TOKEN
from main import bot
from utils.cleanup import ensure_temp_dir, cleanup_old_files

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


def main():
    if not BOT_TOKEN:
        logger.error("❌ توکن توی .env نیست!")
        return

    ensure_temp_dir()
    cleanup_old_files()

    from handlers import (  # noqa
        start, image, ocr, archive, site, network, finance, text_tools,
        media, advanced_media, pdf, creativity, admin, middleware
    )

    bot.remove_webhook()
    logger.info("🚀 بات در حالت Polling روشن شد...")
    bot.infinity_polling(timeout=30, long_polling_timeout=20)


if __name__ == "__main__":
    main()