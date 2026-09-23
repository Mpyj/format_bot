import os
import uuid
import logging
import threading
from PIL import Image, ImageEnhance
import pytesseract
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)

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


# ---------- دریافت عکس ----------
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "ocr_photo"
)
def ocr_receive_photo(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    lang = state.get("ocr_lang", "fas+eng")

    path = None
    preprocessed_path = None
    try:
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

        preprocessed_path = _preprocess_image(path)
        img = Image.open(preprocessed_path)

        config = f'--tessdata-dir {TESSDATA_PATH} --psm 6'
        text = pytesseract.image_to_string(img, lang=lang, config=config).strip()

        if not text:
            bot.send_message(message.chat.id, "⚠️ متنی توی عکس پیدا نشد.")
        else:
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

        _log_operation(user_id, "ocr", ext.lstrip("."), "txt", len(text))
        mark_user_used(user_id)

        bot.send_message(
            message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard()
        )

    except pytesseract.TesseractError:
        logger.exception("خطای Tesseract")
        bot.send_message(message.chat.id, "❌ خطا در تشخیص متن.")
    except Exception as e:
        logger.exception("خطا در OCR")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    finally:
        if path:
            delete_file(path)
        if preprocessed_path:
            delete_file(preprocessed_path)
        clear_state(user_id)


def _preprocess_image(path: str) -> str:
    img = Image.open(path)
    if img.mode != "L":
        img = img.convert("L")
    w, h = img.size
    if w < 2000:
        img = img.resize((w * 2, h * 2), Image.LANCZOS)
    enhancer = ImageEnhance.Contrast(img)
    img = enhancer.enhance(2.0)
    new_path = path + "_prep.png"
    img.save(new_path, "PNG")
    return new_path


def _escape_html(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


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