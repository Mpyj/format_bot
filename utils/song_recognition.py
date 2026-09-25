import os
import uuid
import logging
import asyncio
import threading
import subprocess
import urllib.parse
from config import TEMP_DIR

logger = logging.getLogger(__name__)


# ============================================================
# 🎧 پیش‌پردازش صدا
# ============================================================
def _preprocess_audio(input_path: str) -> str | None:
    """
    پیش‌پردازش صدا قبل از Shazam:
    1. فقط ۱۵ ثانیه وسط آهنگ (بهترین بخش)
    2. نرمالایز صدا (loudnorm)
    3. کاهش نویز (dynaudnorm)
    4. حذف فرکانس‌های اضافه (highpass + lowpass)
    5. تبدیل به WAV مونو با کیفیت بالا
    """
    try:
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_prep.wav")

        # ۱) گرفتن مدت آهنگ
        probe = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                input_path,
            ],
            capture_output=True, text=True, timeout=15,
        )

        try:
            duration = float(probe.stdout.strip())
        except (ValueError, AttributeError):
            duration = 0

        logger.info(f"📊 مدت فایل: {duration:.1f} ثانیه")

        # ۲) انتخاب بخش وسط
        if duration > 30:
            start = (duration / 2) - 7.5
            start_str = f"{start:.2f}"
            duration_str = "15"
        elif duration > 15:
            start_str = "0"
            duration_str = "15"
        else:
            start_str = "0"
            duration_str = str(int(duration)) if duration > 0 else "15"

        # ۳) پردازش با ffmpeg
        result = subprocess.run(
            [
                "ffmpeg", "-y",
                "-ss", start_str,
                "-i", input_path,
                "-t", duration_str,
                "-af",
                "loudnorm=I=-16:TP=-1.5:LRA=11,"  # نرمالایز
                "dynaudnorm,"                     # کاهش نویز
                "highpass=f=200,"                 # حذف فرکانس پایین
                "lowpass=f=12000",                # حذف فرکانس بالا
                "-ar", "44100",                   # نمونه‌برداری
                "-ac", "1",                       # مونو
                output,
            ],
            capture_output=True,
            timeout=45,
        )

        if result.returncode == 0 and os.path.exists(output) and os.path.getsize(output) > 0:
            logger.info(f"✅ پیش‌پردازش موفق: {output}")
            return output
        else:
            logger.warning(f"پیش‌پردازش ناموفق: {result.stderr.decode('utf-8', errors='ignore')[:300]}")
            return None

    except Exception as e:
        logger.warning(f"خطا در پیش‌پردازش: {e}")
        return None


# ============================================================
# 🎵 تشخیص آهنگ
# ============================================================
def recognize_song(audio_path: str) -> dict:
    """
    تشخیص آهنگ با Shazam.
    از thread جداگانه استفاده می‌کنه تا با event loop FastAPI تداخل نکنه.
    """
    # 🎧 پیش‌پردازش
    preprocessed = _preprocess_audio(audio_path)
    if preprocessed:
        audio_path = preprocessed
    else:
        logger.info("⚠️ پیش‌پردازش نشد، از فایل اصلی استفاده می‌شه")

    result_container = {"result": None, "error": None}

    def _run_in_thread():
        try:
            from shazamio import Shazam

            async def _recognize():
                shazam = Shazam()
                return await shazam.recognize(audio_path)

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

    thread = threading.Thread(target=_run_in_thread, daemon=True)
    thread.start()
    thread.join(timeout=90)

    # پاک‌سازی فایل پیش‌پردازش شده
    if preprocessed and preprocessed != audio_path:
        try:
            os.remove(preprocessed)
        except Exception:
            pass

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

        # 🎧 لینک SoundCloud
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


# ============================================================
# 🎧 لینک SoundCloud
# ============================================================
def _make_soundcloud_search(title: str, artist: str) -> str:
    """ساخت لینک جستجو در SoundCloud"""
    try:
        title_clean = title.strip()
        artist_clean = artist.strip() if artist and artist != "?" else ""

        if artist_clean:
            query = f"{artist_clean} - {title_clean}"
        else:
            query = title_clean

        encoded = urllib.parse.quote(query)
        return f"https://soundcloud.com/search?q={encoded}"
    except Exception as e:
        logger.warning(f"خطا در ساخت لینک SoundCloud: {e}")
        return ""