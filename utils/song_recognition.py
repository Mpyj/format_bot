import os
import logging
import asyncio

logger = logging.getLogger(__name__)


def recognize_song(audio_path: str) -> dict:
    """
    تشخیص آهنگ با Shazam.
    ورودی: مسیر فایل صوتی
    خروجی: اطلاعات آهنگ
    """
    try:
        from shazamio import Shazam

        async def _recognize():
            shazam = Shazam()
            return await shazam.recognize(audio_path)

        # اجرای async
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_recognize())
        finally:
            loop.close()

        if not result or "track" not in result:
            return {"success": False, "error": "آهنگ تشخیص داده نشد"}

        track = result["track"]

        # اطلاعات
        title = track.get("title", "?")
        subtitle = track.get("subtitle", "?")  # خواننده

        # تصویر
        image = ""
        if track.get("images"):
            image = track["images"].get("coverart", "") or track["images"].get("background", "")

        # آلبوم/سال/سبک
        album = "?"
        year = "?"
        genre = "?"
        for section in track.get("sections", []):
            if section.get("type") == "SONG":
                for meta in section.get("metadata", []):
                    if meta.get("title") == "Album":
                        album = meta.get("text", "?")
                    elif meta.get("title") == "Released":
                        year = meta.get("text", "?")
                    elif meta.get("title") == "Genre":
                        genre = meta.get("text", "?")

        # لینک Shazam
        shazam_url = track.get("url", "")

        return {
            "success": True,
            "title": title,
            "artist": subtitle,
            "album": album,
            "year": year,
            "genre": genre,
            "cover": image,
            "url": shazam_url,
        }
    except ImportError:
        return {"success": False, "error": "کتابخونه shazamio نصب نیست"}
    except Exception as e:
        logger.exception(f"خطا در تشخیص آهنگ: {e}")
        return {"success": False, "error": str(e)}