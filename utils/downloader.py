import os
import re
import uuid
import logging
import subprocess
import requests
from config import TEMP_DIR

logger = logging.getLogger(__name__)

TIMEOUT = 180
MAX_SIZE_MB = 48


# ============================================================
# 🔍 اطلاعات لینک
# ============================================================
def get_info(url: str) -> dict:
    """اطلاعات ویدیو/آهنگ رو از لینک می‌گیره"""
    try:
        url = _normalize_soundcloud_url(url)

        result = subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--no-playlist",
                "--dump-json",
                "--no-check-certificate",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode != 0:
            error = result.stderr[:500]
            logger.warning(f"yt-dlp error: {error}")
            return {"success": False, "error": "نتونستم اطلاعات بگیرم"}

        import json
        data = json.loads(result.stdout.strip().split("\n")[0])

        return {
            "success": True,
            "title": data.get("title", "?"),
            "uploader": data.get("uploader") or data.get("channel") or "?",
            "duration": data.get("duration", 0),
            "thumbnail": data.get("thumbnail", ""),
            "extractor": data.get("extractor", "?"),
            "view_count": data.get("view_count", 0),
            "like_count": data.get("like_count", 0),
            "upload_date": data.get("upload_date", ""),
            "webpage_url": data.get("webpage_url", url),
            "formats": len(data.get("formats", [])),
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "زمان تموم شد"}
    except Exception as e:
        logger.exception(f"خطا در get_info: {e}")
        return {"success": False, "error": str(e)}


def _normalize_soundcloud_url(url: str) -> str:
    """لینک کوتاه SoundCloud رو باز می‌کنه"""
    if "soundcloud.app.goo.gl" in url or "on.soundcloud.com" in url:
        try:
            r = requests.head(url, allow_redirects=True, timeout=15)
            logger.info(f"لینک کوتاه باز شد: {r.url}")
            return r.url
        except Exception:
            pass
    return url


# ============================================================
# 🎬 دانلود ویدیو
# ============================================================
def download_video(url: str, quality: str = "720") -> str | None:
    try:
        url = _normalize_soundcloud_url(url)
        output_template = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.%(ext)s")

        if quality == "1080":
            fmt = "bestvideo[height<=1080][ext=mp4]+bestaudio[ext=m4a]/best[height<=1080][ext=mp4]/best"
        elif quality == "720":
            fmt = "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/best[height<=720][ext=mp4]/best"
        elif quality == "480":
            fmt = "bestvideo[height<=480][ext=mp4]+bestaudio[ext=m4a]/best[height<=480][ext=mp4]/best"
        else:
            fmt = "bestvideo[height<=360][ext=mp4]+bestaudio[ext=m4a]/best[height<=360][ext=mp4]/best"

        result = subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--no-playlist",
                "--no-check-certificate",
                "-f", fmt,
                "--merge-output-format", "mp4",
                "-o", output_template,
                "--max-filesize", f"{MAX_SIZE_MB}M",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )

        if result.returncode != 0:
            logger.warning(f"yt-dlp error: {result.stderr[:500]}")
            return None

        base = output_template.replace(".%(ext)s", "")
        for f in os.listdir(TEMP_DIR):
            if f.startswith(os.path.basename(base)) and f.endswith(".mp4"):
                return os.path.join(TEMP_DIR, f)

        return None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout در دانلود ویدیو")
        return None
    except Exception as e:
        logger.exception(f"خطا در دانلود ویدیو: {e}")
        return None


# ============================================================
# 🎵 دانلود صدا (MP3)
# ============================================================
def download_audio(url: str) -> str | None:
    try:
        url = _normalize_soundcloud_url(url)
        output_template = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.%(ext)s")

        result = subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--no-playlist",
                "--no-check-certificate",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", output_template,
                "--max-filesize", f"{MAX_SIZE_MB}M",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )

        if result.returncode != 0:
            logger.warning(f"yt-dlp error: {result.stderr[:500]}")
            return None

        base = output_template.replace(".%(ext)s", "")
        for f in os.listdir(TEMP_DIR):
            if f.startswith(os.path.basename(base)) and f.endswith(".mp3"):
                return os.path.join(TEMP_DIR, f)

        return None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout در دانلود صدا")
        return None
    except Exception as e:
        logger.exception(f"خطا در دانلود صدا: {e}")
        return None


# ============================================================
# 🎧 SoundCloud — دانلود
# ============================================================
def download_soundcloud(url: str) -> str | None:
    """دانلود از SoundCloud با yt-dlp"""
    try:
        url = _normalize_soundcloud_url(url)

        # لینک جستجو رو فیلتر کن
        if "/search" in url or "search?q=" in url:
            logger.warning("لینک جستجو پشتیبانی نمی‌شه")
            return None

        output_template = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.%(ext)s")

        result = subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--no-playlist",
                "--no-check-certificate",
                "-x",
                "--audio-format", "mp3",
                "--audio-quality", "0",
                "-o", output_template,
                "--max-filesize", f"{MAX_SIZE_MB}M",
                url,
            ],
            capture_output=True,
            text=True,
            timeout=TIMEOUT,
        )

        if result.returncode != 0:
            logger.warning(f"SoundCloud yt-dlp error: {result.stderr[:500]}")
            return None

        base = output_template.replace(".%(ext)s", "")
        for f in os.listdir(TEMP_DIR):
            if f.startswith(os.path.basename(base)) and f.endswith(".mp3"):
                return os.path.join(TEMP_DIR, f)

        return None
    except subprocess.TimeoutExpired:
        logger.warning("Timeout در دانلود SoundCloud")
        return None
    except Exception as e:
        logger.exception(f"خطا در دانلود SoundCloud: {e}")
        return None


# ============================================================
# 🔧 توابع کمکی
# ============================================================
def human_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: int) -> str:
    if not seconds:
        return "?"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"