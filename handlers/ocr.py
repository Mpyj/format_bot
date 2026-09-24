import os
import uuid
import logging
import threading
from PIL import Image, ImageEnhance, ImageOps, ImageFilter, ImageStat
import pytesseract
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)

# ============================================================
# ⚠️ مسیر Tesseract و tessdata
# - ویندوز: C:\PROGRA~1\Tesseract-OCR
# - لینوکس (Docker): /usr/bin/tesseract و /app/tessdata
# ============================================================
TESSERACT_PATH = "/usr/bin/tesseract"
TESSDATA_PATH = "/app/tessdata"

if os.name == "nt":
    TESSERACT_PATH = r"C:\PROGRA~1\Tesseract-OCR\tesseract.exe"
    TESSDATA_PATH = r"C:\PROGRA~1\Tesseract-OCR\tessdata"

if os.path.exists(TESSERACT_PATH):
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '📄 استخراج متن')
@check_usage_limit
def ocr_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="ocr", waiting_for="ocr_lang", input_path=None)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("فقط فارسی", callback_data="ocr_lang_fas"),
        types.InlineKeyboardButton("فقط انگلیسی", callback_data="ocr_lang_eng"),
        types.InlineKeyboardButton("فارسی + انگلیسی", callback_data="ocr_lang_fas+eng"),
    )
    bot.send_message(
        message.chat.id,
        "📄 <b>استخراج متن از عکس</b>\n\n"
        "اول زبان متن رو انتخاب کن، بعد عکس رو بفرست:\n\n"
        "💡 <i>برای نتیجه بهتر، عکس واضح و با کنتراست بالا بفرست.</i>",
        parse_mode='HTML',
        reply_markup=markup
    )


# ---------- انتخاب زبان ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("ocr_lang_"))
def ocr_lang_chosen(call):
    user_id = call.from_user.id
    lang = call.data.replace("ocr_lang_", "")
    set_state(user_id, ocr_lang=lang, waiting_for="ocr_photo")

    lang_names = {"fas": "فارسی", "eng": "انگلیسی", "fas+eng": "فارسی + انگلیسی"}
    bot.answer_callback_query(call.id, f"زبان: {lang_names.get(lang, lang)}")
    bot.edit_message_text(
        f"✅ زبان انتخاب شد: <b>{lang_names.get(lang, lang)}</b>\n\nالان عکس رو بفرست:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )


# ---------- دریافت عکس و OCR ----------
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "ocr_photo"
)
def ocr_receive_photo(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    lang = state.get("ocr_lang", "fas+eng")

    path = None
    preprocessed_paths = []
    try:
        # دریافت فایل
        if message.content_type == 'photo':
            file_info = bot.get_file(message.photo[-1].file_id)
        else:
            file_info = bot.get_file(message.document.file_id)

        downloaded = bot.download_file(file_info.file_path)
        ext = os.path.splitext(file_info.file_path)[1] or ".jpg"
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "⏳ در حال استخراج متن...")

        # ============================================================
        # 🎯 چند نسخه پیش‌پردازش، بهترین نتیجه رو انتخاب کن
        # ============================================================
        preprocessed_paths = _preprocess_image_multi(path)
        img = Image.open(path)

        text = _run_ocr_multi(img, preprocessed_paths, lang)

        # ارسال نتیجه
        if not text or len(text.strip()) < 3:
            bot.send_message(
                message.chat.id,
                "⚠️ متنی توی عکس پیدا نشد.\n\n"
                "💡 اگه عکس متن داره، ممکنه فونت تزئینی یا پس‌زمینه پیچیده داشته باشه."
            )
        else:
            text = text.strip()
            if len(text) <= 4000:
                bot.send_message(
                    message.chat.id,
                    f"📄 <b>متن استخراج شده:</b>\n\n<pre>{_escape_html(text)}</pre>",
                    parse_mode='HTML'
                )
            else:
                txt_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.txt")
                with open(txt_path, "w", encoding="utf-8") as f:
                    f.write(text)
                with open(txt_path, "rb") as f:
                    bot.send_document(
                        message.chat.id, f,
                        caption="📄 متن استخراج شده (طولانی بود، به‌صورت فایل)"
                    )
                delete_file(txt_path)

        # ثبت در دیتابیس
        _log_operation(user_id, "ocr", ext.lstrip("."), "txt", len(text or ""))
        mark_user_used(user_id)

        bot.send_message(
            message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard(user_id)
        )

    except pytesseract.TesseractError as e:
        logger.exception("خطای Tesseract")
        bot.send_message(
            message.chat.id,
            "❌ خطا در تشخیص متن.\n\n"
            "🔹 ممکنه فایل زبان نصب نباشه.\n"
            "🔹 یا مسیر tessdata اشتباهه."
        )
    except Exception as e:
        logger.exception("خطا در OCR")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    finally:
        if path:
            delete_file(path)
        for p in preprocessed_paths:
            delete_file(p)
        clear_state(user_id)


# ============================================================
# 🎨 پیش‌پردازش چندگانه
# ============================================================
def _preprocess_image_multi(path: str) -> list:
    """
    چند نسخه از عکس رو می‌سازه:
    1. Grayscale ساده
    2. Invert شده (برای پس‌زمینه تیره)
    3. Binarized (سیاه-سفید)
    4. Contrast بالا
    """
    output_paths = []
    img_orig = Image.open(path)

    # تبدیل به grayscale
    if img_orig.mode != "L":
        img_gray = img_orig.convert("L")
    else:
        img_gray = img_orig.copy()

    # بزرگ‌نمایی اگه کوچیکه
    w, h = img_gray.size
    if w < 1500:
        img_gray = img_gray.resize((w * 2, h * 2), Image.LANCZOS)

    # ---- نسخه ۱: Grayscale ساده ----
    p1 = path + "_gray.png"
    img_gray.save(p1, "PNG")
    output_paths.append(p1)

    # ---- نسخه ۲: تشخیص تیرگی و invert ----
    stat = ImageStat.Stat(img_gray)
    mean_brightness = stat.mean[0]
    logger.info(f"🌓 میانگین روشنایی: {mean_brightness:.1f}")

    if mean_brightness < 128:
        # عکس تیره → invert
        img_inv = ImageOps.invert(img_gray)
        p2 = path + "_inv.png"
        img_inv.save(p2, "PNG")
        output_paths.append(p2)
        logger.info("🌓 نسخه invert شده ساخته شد")
    else:
        img_inv = img_gray

    # ---- نسخه ۳: کنتراست بالا ----
    enhancer = ImageEnhance.Contrast(img_inv)
    img_contrast = enhancer.enhance(2.5)
    p3 = path + "_contrast.png"
    img_contrast.save(p3, "PNG")
    output_paths.append(p3)

    # ---- نسخه ۴: Binarization + Denoise + Sharpen ----
    # Sharpen
    img_sharp = img_contrast.filter(ImageFilter.SHARPEN)
    # Denoise
    img_denoised = img_sharp.filter(ImageFilter.MedianFilter(size=3))
    # Binarization
    img_bin = img_denoised.point(lambda x: 255 if x > 128 else 0, mode="1")
    p4 = path + "_bin.png"
    img_bin.save(p4, "PNG")
    output_paths.append(p4)

    return output_paths


# ============================================================
# 🔍 اجرای OCR روی همه نسخه‌ها و انتخاب بهترین
# ============================================================
def _run_ocr_multi(img_orig, preprocessed_paths: list, lang: str) -> str:
    """
    OCR رو روی همه نسخه‌ها اجرا می‌کنه و بهترین نتیجه رو برمی‌گردونه.
    معیار: بیشترین تعداد کلمات meaningful
    """
    best_text = ""
    best_score = 0

    # حالت‌های مختلف PSM
    psm_modes = [6, 4, 11]  # 6: بلوک متن، 4: ستون، 11: متن پراکنده

    for i, p_path in enumerate(preprocessed_paths):
        if not os.path.exists(p_path):
            continue

        img = Image.open(p_path)

        for psm in psm_modes:
            try:
                config = f'--tessdata-dir {TESSDATA_PATH} --psm {psm} --oem 3'
                text = pytesseract.image_to_string(img, lang=lang, config=config).strip()

                score = _score_text(text)
                logger.info(f"📊 نسخه {i+1}, psm {psm}: امتیاز {score}")

                if score > best_score:
                    best_score = score
                    best_text = text

                # اگه امتیاز خیلی خوب بود، زودتر تموم کن
                if score > 50:
                    logger.info(f"✅ نتیجه خوب پیدا شد (امتیاز {score})")
                    return text

            except Exception as e:
                logger.warning(f"خطا در psm {psm}: {e}")
                continue

    logger.info(f"🏆 بهترین امتیاز نهایی: {best_score}")
    return best_text


def _score_text(text: str) -> int:
    """
    به متن امتیاز می‌ده بر اساس:
    - تعداد کلمات meaningful (>= 2 حرف)
    - نسبت حروف به کل کاراکترها
    - پاداش برای کلمات فارسی/انگلیسی معتبر
    """
    if not text:
        return 0

    words = text.split()
    meaningful_words = [w for w in words if len(w) >= 2]

    # نسبت حروف به کل
    total_chars = len(text)
    letter_chars = sum(1 for c in text if c.isalpha())
    letter_ratio = letter_chars / total_chars if total_chars > 0 else 0

    # امتیاز
    score = len(meaningful_words) * 2
    score += int(letter_ratio * 30)

    # پاداش برای کلمات طولانی
    long_words = [w for w in words if len(w) >= 4]
    score += len(long_words) * 3

    return score


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


# ============================================================
# 📊 ثبت در دیتابیس
# ============================================================
def _log_operation(user_id: int, op_type: str, in_fmt, out_fmt, size: int):
    def runner():
        try:
            import psycopg2
            from config import DATABASE_URL

            sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            conn = psycopg2.connect(sync_url)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO operations
                (user_id, operation_type, input_format, output_format, file_size, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, op_type, in_fmt, out_fmt, size, "success")
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"ثبت عملیات ناموفق: {e}")

    threading.Thread(target=runner, daemon=True).start()