import os
import uuid
import logging
import subprocess
from config import TEMP_DIR

logger = logging.getLogger(__name__)

TIMEOUT = 120


def _run_ffmpeg(args: list) -> bool:
    """اجرای ffmpeg با args مشخص"""
    try:
        result = subprocess.run(
            ["ffmpeg", "-y"] + args,
            capture_output=True,
            timeout=TIMEOUT,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr.decode('utf-8', errors='ignore')[:500]}")
            return False
        return True
    except subprocess.TimeoutExpired:
        logger.error("ffmpeg timeout")
        return False
    except FileNotFoundError:
        logger.error("ffmpeg نصب نیست!")
        return False
    except Exception as e:
        logger.exception(f"خطای ffmpeg: {e}")
        return False


# ---------- ویدیو → MP3 ----------
def video_to_mp3(input_path: str, bitrate: str = "192k") -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.mp3")
    ok = _run_ffmpeg([
        "-i", input_path,
        "-vn",
        "-ab", bitrate,
        "-ar", "44100",
        output,
    ])
    return output if ok else None


# ---------- ویدیو → GIF ----------
def video_to_gif(input_path: str, fps: int = 10, width: int = 480) -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.gif")
    vf = f"fps={fps},scale={width}:-1:flags=lanczos"
    ok = _run_ffmpeg([
        "-i", input_path,
        "-vf", vf,
        "-t", "15",
        output,
    ])
    return output if ok else None


# ---------- تبدیل فرمت ویدیو ----------
def video_to_format(input_path: str, fmt: str, quality: str = "medium") -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.{fmt}")
    presets = {"low": "ultrafast", "medium": "medium", "high": "slow"}
    preset = presets.get(quality, "medium")

    args = ["-i", input_path, "-preset", preset]

    if fmt == "mp4":
        args += ["-c:v", "libx264", "-c:a", "aac", "-movflags", "+faststart"]
    elif fmt == "webm":
        args += ["-c:v", "libvpx-vp9", "-c:a", "libopus"]
    elif fmt == "mkv":
        args += ["-c:v", "libx264", "-c:a", "aac"]
    elif fmt == "avi":
        args += ["-c:v", "mpeg4", "-c:a", "mp3"]
    elif fmt == "mov":
        args += ["-c:v", "libx264", "-c:a", "aac"]

    args.append(output)
    ok = _run_ffmpeg(args)
    return output if ok else None


# ---------- تبدیل فرمت صوت ----------
def audio_to_format(input_path: str, fmt: str, bitrate: str = "192k") -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.{fmt}")
    args = ["-i", input_path]

    if fmt == "mp3":
        args += ["-ab", bitrate, "-ar", "44100"]
    elif fmt == "wav":
        args += ["-ar", "44100"]
    elif fmt == "ogg":
        args += ["-c:a", "libvorbis", "-ab", bitrate]
    elif fmt == "m4a":
        args += ["-c:a", "aac", "-ab", bitrate]
    elif fmt == "flac":
        args += ["-c:a", "flac"]

    args.append(output)
    ok = _run_ffmpeg(args)
    return output if ok else None


# ---------- برش ----------
def trim_media(input_path: str, start: str, duration: str, fmt: str = None) -> str | None:
    if not fmt:
        fmt = os.path.splitext(input_path)[1].lstrip(".")

    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_trim.{fmt}")
    ok = _run_ffmpeg([
        "-ss", start,
        "-i", input_path,
        "-t", duration,
        "-c", "copy",
        output,
    ])
    return output if ok else None


# ---------- 🆕 تغییر سرعت ----------
def change_speed(input_path: str, speed: float) -> str | None:
    """
    سرعت پخش رو تغییر بده.
    speed=0.5 → نصف سرعت (آهسته‌تر)
    speed=2.0 → دو برابر (سریع‌تر)
    """
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_speed.{ext}")

    # atempo فقط بین 0.5 تا 2 کار می‌کنه. برای خارج از این، باید زنجیره‌ای بشه
    filter_parts = []
    remaining = speed
    while remaining > 2.0:
        filter_parts.append("atempo=2.0")
        remaining /= 2.0
    while remaining < 0.5:
        filter_parts.append("atempo=0.5")
        remaining /= 0.5
    filter_parts.append(f"atempo={remaining}")

    audio_filter = ",".join(filter_parts)

    # اگه ویدیو داره، ویدیو رو هم سریع کن
    info = get_media_info(input_path)
    if info.get("has_video"):
        video_speed = 1.0 / speed  # setpts برعکسه
        ok = _run_ffmpeg([
            "-i", input_path,
            "-filter_complex",
            f"[0:v]setpts={video_speed}*PTS[v];[0:a]{audio_filter}[a]",
            "-map", "[v]", "-map", "[a]",
            output,
        ])
    else:
        ok = _run_ffmpeg([
            "-i", input_path,
            "-filter:a", audio_filter,
            output,
        ])
    return output if ok else None


# ---------- 🆕 برعکس کردن ----------
def reverse_media(input_path: str) -> str | None:
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_reverse.{ext}")

    info = get_media_info(input_path)
    if info.get("has_video"):
        ok = _run_ffmpeg([
            "-i", input_path,
            "-vf", "reverse",
            "-af", "areverse",
            output,
        ])
    else:
        ok = _run_ffmpeg([
            "-i", input_path,
            "-af", "areverse",
            output,
        ])
    return output if ok else None


# ---------- 🆕 نرمالایز صدا ----------
def normalize_audio(input_path: str) -> str | None:
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext not in ("mp3", "wav", "ogg", "m4a", "flac", "aac"):
        ext = "mp3"
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_norm.{ext}")

    # loudnorm فیلتر استاندارد نرمالایز
    ok = _run_ffmpeg([
        "-i", input_path,
        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11",
        output,
    ])
    return output if ok else None


# ---------- 🆕 تغییر پیچ صدا ----------
def change_pitch(input_path: str, semitones: int) -> str | None:
    """
    پیچ صدا رو تغییر بده (بدون تغییر سرعت).
    semitones: -12 تا +12
    """
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_pitch.{ext}")

    # فرمول: pitch shift با rubberband یا asetrate
    # روش ساده: asetrate + aresample + atempo
    factor = 2 ** (semitones / 12)
    new_rate = int(44100 * factor)

    ok = _run_ffmpeg([
        "-i", input_path,
        "-filter:a", f"asetrate={new_rate},aresample=44100,atempo={1/factor}",
        output,
    ])
    return output if ok else None


# ---------- اطلاعات مدیا (اصلاح‌شده) ----------
def get_media_info(input_path: str) -> dict:
    """
    اطلاعات مدیا رو می‌گیره.
    کاور آهنگ رو به عنوان ویدیو تشخیص نمی‌ده.
    """
    info = {
        "success": False,
        "duration": None,
        "width": None,
        "height": None,
        "has_video": False,
        "has_audio": False,
        "has_cover": False,   # 🆕 کاور آهنگ
        "format": None,
        "video_codec": None,
    }

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=duration,format_name",
                "-show_entries", "stream=codec_type,codec_name,width,height,nb_frames,disposition",
                "-of", "default=noprint_wrappers=1",
                input_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode != 0:
            return info

        output = result.stdout
        current_stream = {}
        streams = []
        current_codec_type = None

        for line in output.splitlines():
            if "=" not in line:
                continue
            key, val = line.split("=", 1)

            if key == "duration":
                try:
                    info["duration"] = float(val)
                except ValueError:
                    pass
            elif key == "format_name":
                info["format"] = val
            elif key == "codec_type":
                # یه stream جدید شروع شد
                if current_codec_type is not None:
                    streams.append(current_stream)
                current_codec_type = val
                current_stream = {"codec_type": val}
            elif key == "codec_name":
                current_stream["codec_name"] = val
            elif key == "width":
                try:
                    current_stream["width"] = int(val)
                except ValueError:
                    pass
            elif key == "height":
                try:
                    current_stream["height"] = int(val)
                except ValueError:
                    pass
            elif key == "nb_frames":
                try:
                    current_stream["nb_frames"] = int(val)
                except ValueError:
                    pass
            elif key.startswith("disposition"):
                if "attached_pic" in key and val == "1":
                    current_stream["attached_pic"] = True

        if current_codec_type is not None:
            streams.append(current_stream)

        # تحلیل streams
        for s in streams:
            codec_type = s.get("codec_type")

            if codec_type == "video":
                # چک کن کاوره یا ویدیو واقعی
                is_cover = (
                    s.get("attached_pic") or
                    (s.get("nb_frames") == 1) or
                    (s.get("width", 999) <= 600 and s.get("height", 999) <= 600) or
                    s.get("codec_name") in ("mjpeg", "png", "bmp", "gif")
                )

                # اگه ابعاد بزرگ داشت و کدکش h264/hevc/vp9 بود، ویدیو واقعیه
                if s.get("width", 0) >= 640 and s.get("codec_name") in ("h264", "hevc", "vp9", "vp8", "mpeg4", "av1"):
                    is_cover = False

                if is_cover:
                    info["has_cover"] = True
                else:
                    info["has_video"] = True
                    info["width"] = s.get("width")
                    info["height"] = s.get("height")
                    info["video_codec"] = s.get("codec_name")

            elif codec_type == "audio":
                info["has_audio"] = True

        info["success"] = True
        return info

    except Exception as e:
        logger.warning(f"خطا در ffprobe: {e}")
        return info


def format_duration(seconds: float) -> str:
    if not seconds:
        return "?"
    seconds = int(seconds)
    h = seconds // 3600
    m = (seconds % 3600) // 60
    s = seconds % 60
    if h:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{m:02d}:{s:02d}"