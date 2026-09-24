import os
import uuid
import logging
import subprocess
from config import TEMP_DIR
from utils.media_tools import get_media_info
logger = logging.getLogger(__name__)

TIMEOUT = 180


def _run_ffmpeg(args: list) -> bool:
    try:
        result = subprocess.run(
            ["ffmpeg", "-y"] + args,
            capture_output=True,
            timeout=TIMEOUT,
        )
        if result.returncode != 0:
            logger.error(f"ffmpeg error: {result.stderr.decode('utf-8', errors='ignore')[:800]}")
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
# 📸 استخراج فریم
# ============================================================
def extract_frame(input_path: str, timestamp: str = "00:00:01") -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_frame.jpg")
    ok = _run_ffmpeg([
        "-ss", timestamp,
        "-i", input_path,
        "-vframes", "1",
        "-q:v", "2",
        output,
    ])
    return output if ok and os.path.exists(output) else None


def auto_thumbnail(input_path: str, duration: float) -> str | None:
    middle = duration / 2
    timestamp = f"{int(middle // 3600):02d}:{int((middle % 3600) // 60):02d}:{int(middle % 60):02d}"
    return extract_frame(input_path, timestamp)


# ============================================================
# 📝 زیرنویس
# ============================================================
def add_subtitle(input_path: str, srt_path: str) -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_sub.mp4")
    srt_escaped = srt_path.replace("\\", "/").replace(":", "\\:")
    ok = _run_ffmpeg([
        "-i", input_path,
        "-vf", f"subtitles='{srt_escaped}'",
        "-c:a", "copy",
        "-movflags", "+faststart",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎵 موسیقی
# ============================================================
def add_music(video_path: str, audio_path: str, volume: float = 0.5) -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_music.mp4")
    ok = _run_ffmpeg([
        "-i", video_path,
        "-i", audio_path,
        "-filter_complex",
        f"[0:a]volume=0.3[a1];[1:a]volume={volume}[a2];[a1][a2]amix=inputs=2:duration=first[aout]",
        "-map", "0:v",
        "-map", "[aout]",
        "-c:v", "copy",
        "-c:a", "aac",
        "-shortest",
        "-movflags", "+faststart",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎬 اسلایدشو
# ============================================================
def images_to_video(image_paths: list, audio_path: str = None, duration_per_image: float = 3.0) -> str | None:
    try:
        concat_file = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_concat.txt")

        with open(concat_file, "w", encoding="utf-8") as f:
            for img in image_paths:
                img_escaped = img.replace("\\", "/").replace("'", "'\\''")
                f.write(f"file '{img_escaped}'\n")
                f.write(f"duration {duration_per_image}\n")
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
                "-movflags", "+faststart",
                output,
            ])
        else:
            ok = _run_ffmpeg([
                "-f", "concat",
                "-safe", "0",
                "-i", concat_file,
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
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
# 🔊 حذف صدای خواننده (بهبودیافته)
# ============================================================
def remove_vocals(input_path: str) -> str | None:
    """
    حذف صدای خواننده (روش ساده).
    ⚠️ این روش کامل نیست — فقط تا حدی صدا رو کم می‌کنه.
    """
    ext = os.path.splitext(input_path)[1].lstrip(".").lower()
    if ext not in ("mp3", "wav", "ogg", "m4a"):
        ext = "mp3"
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_karaoke.{ext}")

    # اول به استریو تبدیل کن
    temp_stereo = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_stereo.wav")
    ok = _run_ffmpeg([
        "-i", input_path,
        "-ac", "2",
        "-ar", "44100",
        temp_stereo,
    ])

    if not ok:
        return None

    # فیلتر karaoke
    ok = _run_ffmpeg([
        "-i", temp_stereo,
        "-af",
        "pan=stereo|c0=c0-c1|c1=c1-c0,"
        "highpass=f=200,"
        "lowpass=f=12000",
        "-ac", "2",
        output,
    ])

    try:
        os.remove(temp_stereo)
    except Exception:
        pass

    return output if ok and os.path.exists(output) else None


# ============================================================
# 📊 نمودار موج
# ============================================================
def audio_waveform(input_path: str) -> str | None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import numpy as np

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

        import wave
        with wave.open(wav_path, "rb") as wf:
            n_frames = wf.getnframes()
            frames = wf.readframes(n_frames)
            audio_data = np.frombuffer(frames, dtype=np.int16)

        fig, ax = plt.subplots(figsize=(12, 4), facecolor="#1a1a2e")
        ax.set_facecolor("#1a1a2e")

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

        try:
            os.remove(wav_path)
        except Exception:
            pass

        return output if os.path.exists(output) else None
    except Exception as e:
        logger.exception(f"خطا در نمودار موج: {e}")
        return None


# ============================================================
# ⏱ تایم‌لپس
# ============================================================
def timelapse(input_path: str, speed: float = 4.0) -> str | None:
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_timelapse.mp4")

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
        "-c:v", "libx264",
        "-c:a", "aac",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        output,
    ])
    return output if ok and os.path.exists(output) else None


# ============================================================
# 🎞 ترکیب دو ویدیو (اصلاح‌شده)
# ============================================================
def concat_videos(video1: str, video2: str) -> str | None:
    """ترکیب دو ویدیو — با بررسی صدا"""
    try:
        # چک کن صدا دارن یا نه
        info1 = get_media_info(video1)
        info2 = get_media_info(video2)

        has_audio1 = info1.get("has_audio", False)
        has_audio2 = info2.get("has_audio", False)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_concat.mp4")

        if has_audio1 and has_audio2:
            # هر دو صدا دارن
            filter_complex = (
                "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0];"
                "[1:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1];"
                "[v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]"
            )
            ok = _run_ffmpeg([
                "-i", video1,
                "-i", video2,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-map", "[a]",
                "-c:v", "libx264",
                "-c:a", "aac",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output,
            ])
        else:
            # حداقل یکی صدا نداره
            filter_complex = (
                "[0:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v0];"
                "[1:v]scale=1280:720:force_original_aspect_ratio=decrease,"
                "pad=1280:720:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30[v1];"
                "[v0][v1]concat=n=2:v=1:a=0[v]"
            )
            ok = _run_ffmpeg([
                "-i", video1,
                "-i", video2,
                "-filter_complex", filter_complex,
                "-map", "[v]",
                "-c:v", "libx264",
                "-pix_fmt", "yuv420p",
                "-movflags", "+faststart",
                output,
            ])

        return output if ok and os.path.exists(output) else None
    except Exception as e:
        logger.exception(f"خطا در ترکیب: {e}")
        return None


# ============================================================
# 🔇 حذف صدا (اصلاح‌شده)
# ============================================================
def remove_audio(input_path: str) -> str | None:
    """صدای ویدیو رو حذف می‌کنه (خروجی MP4)"""
    output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_noaudio.mp4")

    ok = _run_ffmpeg([
        "-i", input_path,
        "-an",
        "-c:v", "copy",
        "-f", "mp4",
        "-movflags", "+faststart",
        output,
    ])
    return output if ok and os.path.exists(output) else None