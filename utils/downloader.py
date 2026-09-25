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
        # اگه SoundCloud بود، از API خودش
        if "soundcloud.com" in url.lower():
            info = _get_soundcloud_info(url)
            if info.get("success"):
                return info

        # بقیه پلتفرم‌ها با yt-dlp
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


# ============================================================
# 🎬 دانلود ویدیو
# ============================================================
def download_video(url: str, quality: str = "720") -> str | None:
    """دانلود ویدیو با کیفیت مشخص"""
    try:
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
    """دانلود فقط صدا به صورت MP3"""
    try:
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
# 🎧 SoundCloud — Client ID
# ============================================================
def _get_soundcloud_client_id() -> str | None:
    """Client ID رو از سایت SoundCloud استخراج می‌کنه"""
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "en-US,en;q=0.9",
        }

        # صفحه اصلی SoundCloud
        r = requests.get("https://soundcloud.com", headers=headers, timeout=15)
        if r.status_code != 200:
            logger.warning(f"SoundCloud صفحه اصلی خطا: {r.status_code}")
            return None

        # پیدا کردن script URLها
        scripts = re.findall(r'src="(https://a-v2\.sndcdn\.com/assets/[^"]+\.js)"', r.text)

        if not scripts:
            scripts = re.findall(r'src="([^"]+\.js)"', r.text)

        # جستجو توی scriptها
        for script_url in reversed(scripts):
            if not script_url.startswith("http"):
                script_url = "https://soundcloud.com" + script_url

            try:
                s_res = requests.get(script_url, headers=headers, timeout=15)
                if s_res.status_code != 200:
                    continue

                # الگوهای مختلف client_id
                patterns = [
                    r'client_id:"([a-zA-Z0-9]{32})"',
                    r'client_id=([a-zA-Z0-9]{32})',
                    r'"client_id":"([a-zA-Z0-9]{32})"',
                ]
                for pattern in patterns:
                    found = re.findall(pattern, s_res.text)
                    if found:
                        logger.info(f"✅ Client ID پیدا شد: {found[0][:8]}...")
                        return found[0]
            except Exception:
                continue

        logger.warning("Client ID پیدا نشد")
        return None
    except Exception as e:
        logger.warning(f"خطا در استخراج Client ID: {e}")
        return None


# ============================================================
# 🎧 SoundCloud — اطلاعات
# ============================================================
def _get_soundcloud_info(url: str) -> dict:
    """اطلاعات track از SoundCloud API"""
    try:
        client_id = _get_soundcloud_client_id()
        if not client_id:
            return {"success": False, "error": "Client ID پیدا نشد"}

        # Resolve URL
        resolve_url = "https://api-v2.soundcloud.com/resolve"
        params = {"url": url, "client_id": client_id}

        r = requests.get(resolve_url, params=params, timeout=15)
        if r.status_code != 200:
            return {"success": False, "error": f"SoundCloud API خطا: {r.status_code}"}

        data = r.json()

        duration_ms = data.get("duration", 0)
        duration_sec = duration_ms // 1000

        return {
            "success": True,
            "title": data.get("title", "?"),
            "uploader": data.get("user", {}).get("username", "?"),
            "duration": duration_sec,
            "thumbnail": data.get("artwork_url", "") or "",
            "extractor": "SoundCloud",
            "view_count": data.get("playback_count", 0),
            "like_count": data.get("likes_count", 0),
            "upload_date": data.get("created_at", ""),
            "webpage_url": url,
            "formats": 1,
        }
    except Exception as e:
        logger.warning(f"خطا در info ساندکلاد: {e}")
        return {"success": False, "error": str(e)}


# ============================================================
# 🎧 SoundCloud — دانلود
# ============================================================
def download_soundcloud(url: str) -> str | None:
    """دانلود از SoundCloud با API مستقیم"""
    try:
        client_id = _get_soundcloud_client_id()
        if not client_id:
            logger.warning("Client ID پیدا نشد")
            return None

        # Resolve URL
        resolve_url = "https://api-v2.soundcloud.com/resolve"
        params = {"url": url, "client_id": client_id}

        r = requests.get(resolve_url, params=params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"SoundCloud resolve خطا: {r.status_code}")
            return None

        track_data = r.json()
        track_id = track_data.get("id")

        if not track_id:
            logger.warning("Track ID پیدا نشد")
            return None

        # گرفتن stream URL
        stream_url = f"https://api-v2.soundcloud.com/tracks/{track_id}/stream"
        stream_params = {
            "client_id": client_id,
            "track_authorization": "null",
        }

        r = requests.get(stream_url, params=stream_params, timeout=15)
        if r.status_code != 200:
            logger.warning(f"SoundCloud stream خطا: {r.status_code}")
            return None

        stream_data = r.json()

        # پیدا کردن لینک دانلود
        download_url = None
        if stream_data.get("url"):
            download_url = stream_data["url"]
        elif stream_data.get("location"):
            download_url = stream_data["location"]

        if not download_url:
            logger.warning("لینک دانلود پیدا نشد")
            return None

        # دانلود فایل
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.mp3")

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                          "AppleWebKit/537.36 (KHTML, like Gecko) "
                          "Chrome/120.0.0.0 Safari/537.36"
        }

        r = requests.get(download_url, headers=headers, stream=True, timeout=120)

        total_size = 0
        with open(output, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    total_size += len(chunk)

                    # چک حجم
                    if total_size > MAX_SIZE_MB * 1024 * 1024:
                        logger.warning("فایل خیلی بزرگه")
                        try:
                            os.remove(output)
                        except Exception:
                            pass
                        return None

        return output if os.path.exists(output) and os.path.getsize(output) > 0 else None

    except Exception as e:
        logger.exception(f"خطا در دانلود SoundCloud: {e}")
        return None


# ============================================================
# 🔧 توابع کمکی
# ============================================================
def human_size(size_bytes: int) -> str:
    """تبدیل بایت به فرمت خوانا"""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def format_duration(seconds: int) -> str:
    """ثانیه به mm:ss یا hh:mm:ss"""
    if not seconds:
        return "?"
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"