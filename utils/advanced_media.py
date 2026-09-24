import os
import uuid
import logging
import subprocess
from config import TEMP_DIR

logger = logging.getLogger(__name__)

TIMEOUT = 180  # 3 دقیقه


def _run_ffmpeg(args: list) -> bool:
    """اجرای ffmpeg"""
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


# ============================================================
# 📸 استخراج فریم از ویدیو
# ============================================================
def extract_frame(input_path: str, timestamp: str = "00:00:01") -> str | None:
    """عکس از ثانیه X ویدیو"""
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_frame.jpg")
    ok = _run_ffmpeg([
        "-ss", timestamp,
        "-i", input_path,
        "-vframes", "1",
        "-q:v", "2",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🖼️ Thumbnail خودکار (فریم وسط)
# ============================================================
def auto_thumbnail(input_path: str, duration: float) -> str | None:
    """فریم وسط ویدیو رو به عنوان thumbnail"""
    middle = duration / 2
    timestamp = f"{int(middle // 3600):02d}:{int((middle % 3600) // 60):02d}:{int(middle % 60):02d}"
    return extract_frame(input_path, timestamp)


# ============================================================
# 📝 افزودن زیرنویس
# ============================================================
def add_subtitle(input_path: str, srt_path: str) -> str | None:
    """SRT به ویدیو"""
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_sub.mp4")

    # escape مسیر srt برای ffmpeg
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")

    ok = _run_ffmpeg([
        "-i", input_path,
        "-vf", f"subtitles='{srt_escaped}'",
        "-c:a", "copy",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎵 افزودن موسیقی به ویدیو
# ============================================================
def add_music(video_path: str, audio_path: str, volume: float = 0.5) -> str | None:
    """موسیقی روی ویدیو (صدای اصلی کم میشه)"""
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_music.mp4")
    ok = _run_ffmpeg([
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:a]volume=0.3[a1];[1:a]volume={volume}[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-shortest",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎬 ساخت ویدیو از عکس + موسیقی
# ============================================================
def images_to_video(image_paths: list, audio_path: str = None, duration_per_image: float = 3.0) -> str | None:
    """چند عکس → ویدیو اسلایدشو"""
    try:
        # ساخت لیست concat
        concat_file = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_concat.txt")

        with open(concat_file, "w", encoding="utf-8") as f:
            for img in image_paths:
                # escape مسیر
                img_escaped = img.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{img_escaped}'\n")
                f.write(f"duration {duration_per_image}\n")
            # آخرین عکس رو دوباره اضافه کن (باگ ffmpeg)
            img_escaped = image_paths[-1].replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{img_escaped}'\n")

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_slideshow.mp4")

        if audio_path:
            ok = _run_ffmpeg([
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-i", audio_path,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-shortest",
                output,
            ])
        else:
            ok = _run_ffmpeg([
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                output,
            ])

        try:
            os.remove(concat_file)
        except Exception:
            pass

        return output if ok and os.path.exists(output) else None
    except Exception as e:
        logger.exception(f"خطا در ساخت اسلایدشو: {e}")
        return None


# ============================================================
# 🔊 حذف صدای خواننده (vocal remover ساده)
# ============================================================
def remove_vocals(input_path: str) -> str | None:
    """حذف صدای مرکزی (خواننده) — ساده"""
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext not in ("mp3", "wav", "ogg", "m4a"):
        ext = "mp3"
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_karaoke.{ext}")

    # فیلتر karaoke: حذف کانال مرکزی
    ok = _run_ffmpeg([
        "-i", input_path,
        "-af", "pan=stereo|c0=c0-c1|c1=c1-c0",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 📊 نمودار موج صدا
# ============================================================
def audio_waveform(input_path: str) -> str | None:
    """نمودار موج صدا"""
    try:
        import matplotlib
        matplotlib.use("Agg")  # backend بدون display
        import matplotlib.pyplot as plt
        import numpy as np

        # استخراج موج با ffmpeg به WAV
        wav_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_temp.wav")
        ok = _run_ffmpeg([
            "-i", input_path,
            "-ac", "1",
            "-ar", "8000",
            "-f", "wav",
            wav_path,
        ])

        if not ok:
            return None

        # خوندن WAV
        import wave
        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)
            audio_data = np.frombuffer(frames, dtype=np.int16)

        # رسم نمودار
        fig, ax = plt.subplots(figsize=(12, 4), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")

        # downsample اگه خیلی زیاده
        if len(audio_data) > 100000:
            step = len(audio_data) // 100000
            audio_data = audio_data[::step]

        ax.plot(audio_data, color="#00d9ff", linewidth=0.5)
        ax.set_xlabel("Samples", color="white")
        ax.set_ylabel("Amplitude", color="white")
        ax.set_title("Audio Waveform", color="white", fontsize=14)
        ax.tick_params(colors="white")
        for spine in ax.spines.values():
            spine.set_color("white")

        plt.tight_layout()

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_waveform.png")
        plt.savefig(output, dpi=80, facecolor="#1a1a2e")
        plt.close(fig)

        # پاک‌سازی
        try:
            os.remove(wav_path)
        except Exception:
            pass

        return output if os.path.exists(output) else None
    except Exception as e:
        logger.exception(f"خطا در نمودار موج: {e}")
        return None


# ============================================================
# ⏱ تایم‌لپس (افزایش سرعت)
# ============================================================
def timelapse(input_path: str, speed: float = 4.0) -> str | None:
    """سرعت ویدیو رو زیاد می‌کنه (بدون تغییر پیچ صدا)"""
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_timelapse.mp4")

    # setpts: سرعت ویدیو
    # atempo: سرعت صدا (فقط 0.5 تا 2.0)
    audio_filter = []
    remaining = speed
    while remaining > 2.0:
        audio_filter.append("atempo=2.0")
        remaining /= 2.0
    audio_filter.append(f"atempo={remaining}")
    audio_filter_str = ",".join(audio_filter)

    ok = _run_ffmpeg([
        "-i", input_path,
        "-filter_complex",
        f"[0:v]setpts={1/speed}*PTS[v];[0:a]{audio_filter_str}[a]",
        "-map", "[v]", "-map", "[a]",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎞 ترکیب دو ویدیو
# ============================================================
def concat_videos(video1: str, video2: str) -> str | None:
    """دو ویدیو رو با هم می‌چسبونه"""
    try:
        concat_file = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_concat.txt")

        with open(concat_file, "w", encoding="utf-8") as f:
            v1 = video1.replace("\\", "/").replace("'", "'\\''")
            v2 = video2.replace("\\", "/").replace("'", "'\\''")
            f.write(f"file '{v1}'\n")
            f.write(f"file '{v2}'\n")

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_concat.mp4")
        ok = _run_ffmpeg([
            "-f", "concat",
            "-safe", "0",
            "-i", concat_file,
            "-c", "copy",
            output,
        ])

        try:
            os.remove(concat_file)
        except Exception:
            pass

        return output if ok and os.path.exists(output) else None
    except Exception as e:
        logger.exception(f"خطا در ترکیب: {e}")
        return None


# ============================================================
# 🔇 حذف صدا
# ============================================================
def remove_audio(input_path: str) -> str | None:
    """صدای ویدیو رو حذف می‌کنه"""
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext not in ("mp4", "mkv", "webm", "mov", "avi"):
        ext = "mp4"
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_noaudio.{ext}")

    ok = _run_ffmpeg([
        "-i", input_path,
        "-an",
        "-c:v", "copy",
        output,
    ])
    return output if ok and os.path.exists(output) else None