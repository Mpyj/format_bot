import os
import logging
import asyncio
import threading
import urllib.parse

logger = logging.getLogger(__name__)


def recognize_song(audio_path: str) -> dict:
    """
    تشخیص آهنگ با Shazam.
    از thread جداگانه استفاده می‌کنه تا با event loop FastAPI تداخل نکنه.
    """
    result_container = {"result": None, "error": None}

    def _run_in_thread():
        try:
            from shazamio import Shazam

            async def _recognize():
                shazam = Shazam()
                return await shazam.recognize(audio_path)

            # ساخت event loop جدید توی این thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(_recognize())
                result_container["result"] = result
            finally:
                loop.close()
        except Exception as e:
            result_container["error"] = str(e)
            logger.exception(f"خطا در thread تشخیص آهنگ: {e}")

    # اجرا توی thread جداگانه
    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=60)

    if thread.is_alive():
        return {"success": False, "error": "زمان تشخیص تموم شد (timeout)"}

    if result_container["error"]:
        return {"success": False, "error": result_container["error"]}

    result = result_container["result"]
    if not result or "track" not in result:
        return {"success": False, "error": "آهنگ تشخیص داده نشد"}

    try:
        track = result["track"]
        title = track.get("title", "?")
        subtitle = track.get("subtitle", "?")

        # کاور
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

        shazam_url = track.get("url", "")

        # 🎵 ساخت لینک SoundCloud
        soundcloud_search = _make_soundcloud_search(title, subtitle)

        return {
            "success": True,
            "title": title,
            "artist": subtitle,
            "album": album,
            "year": year,
            "genre": genre,
            "cover": image,
            "url": shazam_url,
            "soundcloud_url": soundcloud_search,
        }
    except Exception as e:
        logger.exception(f"خطا در پردازش نتیجه: {e}")
        return {"success": False, "error": str(e)}


def _make_soundcloud_search(title: str, artist: str) -> str:
    """ساخت لینک جستجو در SoundCloud"""
    try:
        # پاک‌سازی متن
        title_clean = title.strip()
        artist_clean = artist.strip() if artist and artist != "?" else ""

        # ساخت query
        if artist_clean:
            query = f"{artist_clean} - {title_clean}"
        else:
            query = title_clean

        # URL encode
        encoded = urllib.parse.quote(query)

        # لینک جستجو SoundCloud
        return f"https://soundcloud.com/search?q={encoded}"
    except Exception as e:
        logger.warning(f"خطا در ساخت لینک SoundCloud: {e}")
        return ""