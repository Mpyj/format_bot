import os
import uuid
import logging
import string
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance, ImageOps
from config import TEMP_DIR
from utils.cleanup import delete_file

logger = logging.getLogger(__name__)


# ============================================================
# 🔐 تولید رمز قوی
# ============================================================
def generate_password(
    length: int = 16,
    use_upper: bool = True,
    use_lower: bool = True,
    use_digits: bool = True,
    use_symbols: bool = True,
) -> str:
    """رمز تصادفی امن می‌سازه"""
    chars = ""
    if use_upper:
        chars += string.ascii_uppercase
    if use_lower:
        chars += string.ascii_lowercase
    if use_digits:
        chars += string.digits
    if use_symbols:
        chars += "!@#$%^&*()_+-=[]{}|;:,.<>?"

    if not chars:
        chars = string.ascii_letters + string.digits

    import secrets
    return "".join(secrets.choice(chars) for _ in range(length))


def password_strength(password: str) -> tuple[str, str]:
    """قدرت رمز رو تخمین می‌زنه. (سطح، ایموجی)"""
    score = 0
    if len(password) >= 8:
        score += 1
    if len(password) >= 12:
        score += 1
    if len(password) >= 16:
        score += 1
    if any(c.isupper() for c in password):
        score += 1
    if any(c.islower() for c in password):
        score += 1
    if any(c.isdigit() for c in password):
        score += 1
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in password):
        score += 1

    if score <= 3:
        return "ضعیف", "🔴"
    elif score <= 5:
        return "متوسط", "🟡"
    return "قوی", "🟢"


# ============================================================
# 🌍 ترجمه
# ============================================================
SUPPORTED_LANGS = {
    "fa": "فارسی 🇮🇷",
    "en": "انگلیسی 🇬🇧",
    "ar": "عربی 🇸🇦",
    "tr": "ترکی 🇹🇷",
    "de": "آلمانی 🇩🇪",
    "fr": "فرانسوی 🇫🇷",
    "es": "اسپانیایی 🇪🇸",
    "ru": "روسی 🇷🇺",
    "zh-CN": "چینی 🇨🇳",
    "ja": "ژاپنی 🇯🇵",
}


# mapping کدهای کوتاه ما به فرمت MyMemory
MYMEMORY_LANG_MAP = {
    "fa": "fa-IR",
    "en": "en-GB",
    "ar": "ar-SA",
    "tr": "tr-TR",
    "de": "de-DE",
    "fr": "fr-FR",
    "es": "es-ES",
    "ru": "ru-RU",
    "zh-CN": "zh-CN",
    "ja": "ja-JP",
}


def translate_text(text: str, target_lang: str, source_lang: str = "auto") -> str | None:
    """
    متن رو ترجمه می‌کنه.
    1) Google (سریع‌ترین و بهترین)
    2) MyMemory (fallback با فرمت درست زبان)
    """
    # ==================== تلاش اول: Google ====================
    try:
        from deep_translator import GoogleTranslator
        translator = GoogleTranslator(source=source_lang, target=target_lang)
        result = translator.translate(text)
        if result:
            logger.info("✅ ترجمه با Google موفق بود")
            return result
    except Exception as e:
        err = str(e).lower()
        if "toomanyrequests" in err or "too many" in err:
            logger.warning("⚠️ گوگل محدودیت داد، می‌ریم سراغ MyMemory")
        else:
            logger.warning(f"⚠️ خطا در ترجمه گوگل: {e}")

    # ==================== تلاش دوم: MyMemory ====================
    try:
        from deep_translator import MyMemoryTranslator

        mm_target = MYMEMORY_LANG_MAP.get(target_lang, target_lang)

        # MyMemory از auto پشتیبانی نمی‌کنه — یه زبان پیش‌فرض انتخاب می‌کنیم
        if source_lang == "auto":
            # اگه مقصد انگلیسیه، فرض می‌کنیم مبدأ فارسیه و برعکس
            mm_source = "fa-IR" if mm_target != "fa-IR" else "en-GB"
        else:
            mm_source = MYMEMORY_LANG_MAP.get(source_lang, source_lang)

        translator = MyMemoryTranslator(source=mm_source, target=mm_target)
        result = translator.translate(text)
        if result:
            logger.info(f"✅ ترجمه با MyMemory موفق بود ({mm_source} → {mm_target})")
            return result
    except Exception as e:
        logger.warning(f"⚠️ خطا در ترجمه MyMemory: {e}")

    # ==================== تلاش سوم: LibreTranslate (اگه داشتی) ====================
    # فعلاً این بخش غیرفعاله — اگه بعداً سرور خودت رو راه انداختی، فعالش کن
    # try:
    #     from deep_translator import LibreTranslateTranslator
    #     translator = LibreTranslateTranslator(
    #         source=source_lang, target=target_lang,
    #         api_url="http://localhost:5000"
    #     )
    #     return translator.translate(text)
    # except Exception as e:
    #     logger.warning(f"خطا در LibreTranslate: {e}")

    logger.error("❌ همه سرویس‌های ترجمه شکست خوردن")
    return None


# ============================================================
# 🔊 متن → صوت
# ============================================================
def text_to_speech(text: str, lang: str = "fa") -> str | None:
    """
    متن رو به صوت تبدیل می‌کنه.
    - فارسی: persian-speech (آفلاین) + فیلتر کاهش خش
    - انگلیسی: gTTS (نیاز به اینترنت)
    """
    try:
        if lang == "fa":
            from persian_speech_runtime import talk

            raw_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_raw.wav")
            talk(text, raw_path)

            # 🎧 کاهش خش با ffmpeg
            import subprocess
            clean_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.mp3")
            try:
                result = subprocess.run(
                    [
                        "ffmpeg", "-y", "-i", raw_path,
                        "-af",
                        "afftdn=nf=-25,"
                        "highpass=f=200,"
                        "lowpass=f=8000,"
                        "acompressor=threshold=-18dB:ratio=3:attack=5:release=50",
                        "-ab", "128k",
                        clean_path,
                    ],
                    capture_output=True,
                    timeout=60,
                )
                if (result.returncode == 0
                        and os.path.exists(clean_path)
                        and os.path.getsize(clean_path) > 0):
                    delete_file(raw_path)
                    return clean_path
                else:
                    logger.warning(
                        f"ffmpeg فیلتر خطا داد: "
                        f"{result.stderr.decode('utf-8', errors='ignore')[:300]}"
                    )
            except Exception as e:
                logger.warning(f"ffmpeg نیست یا خطا داد: {e}")

            # اگه فیلتر کار نکرد، WAV خام رو برگردون
            return raw_path

        else:
            from gtts import gTTS
            output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.mp3")
            tts = gTTS(text=text, lang="en", slow=False)
            tts.save(output)
            return output

    except ImportError as e:
        logger.error(f"کتابخونه TTS نصب نیست: {e}")
        return None
    except Exception as e:
        logger.exception(f"خطا در TTS: {e}")
        return None


# ============================================================
# 💧 واترمارک روی عکس
# ============================================================
def _get_font(size: int = 40):
    """فونت (با پشتیبانی از فارسی)"""
    font_paths = [
        "C:/Windows/Fonts/tahoma.ttf",      # پشتیبانی فارسی
        "C:/Windows/Fonts/arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for p in font_paths:
        if os.path.exists(p):
            try:
                return ImageFont.truetype(p, size)
            except Exception:
                pass
    return ImageFont.load_default()


def add_watermark_to_image(
    input_path: str,
    text: str,
    position: str = "bottom-right",
    opacity: int = 180,
    font_size: int = 40,
) -> str | None:
    """واترمارک متنی روی عکس"""
    try:
        img = Image.open(input_path).convert("RGBA")
        watermark = Image.new("RGBA", img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(watermark)
        font = _get_font(font_size)

        bbox = draw.textbbox((0, 0), text, font=font)
        text_w = bbox[2] - bbox[0]
        text_h = bbox[3] - bbox[1]

        padding = 20
        positions = {
            "top-left": (padding, padding),
            "top-right": (img.width - text_w - padding, padding),
            "bottom-left": (padding, img.height - text_h - padding),
            "bottom-right": (img.width - text_w - padding, img.height - text_h - padding),
            "center": ((img.width - text_w) // 2, (img.height - text_h) // 2),
        }
        pos = positions.get(position, positions["bottom-right"])

        # سایه برای خوانایی
        draw.text((pos[0] + 2, pos[1] + 2), text, font=font, fill=(0, 0, 0, opacity))
        draw.text(pos, text, font=font, fill=(255, 255, 255, opacity))

        result = Image.alpha_composite(img, watermark).convert("RGB")
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_wm.jpg")
        result.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در واترمارک عکس: {e}")
        return None


# ============================================================
# 📐 تغییر اندازه عکس
# ============================================================
def resize_image(
    input_path: str,
    width: int = None,
    height: int = None,
    percent: int = None,
) -> str | None:
    """تغییر اندازه عکس"""
    try:
        img = Image.open(input_path)
        orig_w, orig_h = img.size

        if percent:
            new_w = int(orig_w * percent / 100)
            new_h = int(orig_h * percent / 100)
        elif width and height:
            new_w, new_h = width, height
        elif width:
            new_w = width
            new_h = int(orig_h * width / orig_w)
        elif height:
            new_h = height
            new_w = int(orig_w * height / orig_h)
        else:
            return None

        img = img.resize((new_w, new_h), Image.LANCZOS)

        ext = os.path.splitext(input_path)[1] or ".jpg"
        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_resized{ext}")

        if img.mode in ("RGBA", "LA", "P") and ext.lower() in (".jpg", ".jpeg"):
            img = img.convert("RGB")

        img.save(output)
        return output
    except Exception as e:
        logger.exception(f"خطا در تغییر اندازه: {e}")
        return None


# ============================================================
# 🎭 افکت روی عکس
# ============================================================
EFFECTS = {
    "grayscale": "سیاه و سفید",
    "blur": "بلور",
    "sharpen": "شارپ",
    "sepia": "سپیا (قدیمی)",
    "invert": "معکوس",
    "contour": "خطی",
    "emboss": "برجسته",
    "edge": "لبه",
    "brightness": "روشن‌تر",
    "contrast": "کنتراست بالا",
}


def apply_effect(input_path: str, effect: str) -> str | None:
    """افکت روی عکس"""
    try:
        img = Image.open(input_path).convert("RGB")

        if effect == "grayscale":
            img = ImageOps.grayscale(img).convert("RGB")
        elif effect == "blur":
            img = img.filter(ImageFilter.GaussianBlur(5))
        elif effect == "sharpen":
            img = img.filter(ImageFilter.SHARPEN)
        elif effect == "sepia":
            img = ImageOps.grayscale(img).convert("RGB")
            sepia = Image.new("RGB", img.size)
            pixels = img.getdata()
            sepia_pixels = []
            for r, g, b in pixels:
                tr = int(0.393 * r + 0.769 * g + 0.189 * b)
                tg = int(0.349 * r + 0.686 * g + 0.168 * b)
                tb = int(0.272 * r + 0.534 * g + 0.131 * b)
                sepia_pixels.append((min(255, tr), min(255, tg), min(255, tb)))
            sepia.putdata(sepia_pixels)
            img = sepia
        elif effect == "invert":
            img = ImageOps.invert(img)
        elif effect == "contour":
            img = img.filter(ImageFilter.CONTOUR)
        elif effect == "emboss":
            img = img.filter(ImageFilter.EMBOSS)
        elif effect == "edge":
            img = img.filter(ImageFilter.FIND_EDGES)
        elif effect == "brightness":
            img = ImageEnhance.Brightness(img).enhance(1.5)
        elif effect == "contrast":
            img = ImageEnhance.Contrast(img).enhance(2.0)
        else:
            return None

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_{effect}.jpg")
        img.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در افکت: {e}")
        return None


# ============================================================
# 🎨 متن → عکس
# ============================================================
def text_to_image(
    text: str,
    width: int = 800,
    height: int = 400,
    bg_color: str = "#FFFFFF",
    text_color: str = "#000000",
    font_size: int = 60,
) -> str | None:
    """متن رو روی یه عکس می‌ذاره"""
    try:
        img = Image.new("RGB", (width, height), bg_color)
        draw = ImageDraw.Draw(img)
        font = _get_font(font_size)

        # شکستن متن به خطوط
        max_width = width - 40
        lines = []
        current = ""
        for word in text.split():
            test = f"{current} {word}".strip()
            bbox = draw.textbbox((0, 0), test, font=font)
            if bbox[2] - bbox[0] <= max_width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = word
        if current:
            lines.append(current)

        line_height = font_size + 10
        total_height = len(lines) * line_height
        start_y = max(20, (height - total_height) // 2)

        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=font)
            text_w = bbox[2] - bbox[0]
            x = (width - text_w) // 2
            y = start_y + i * line_height
            draw.text((x, y), line, font=font, fill=text_color)

        output = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}_text.jpg")
        img.save(output, "JPEG", quality=95)
        return output
    except Exception as e:
        logger.exception(f"خطا در متن به عکس: {e}")
        return None