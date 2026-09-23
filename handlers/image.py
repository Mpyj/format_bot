import os
import uuid
import logging
import threading
from PIL import Image
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.file_info import get_file_info, format_file_info, human_size
from utils.creative_tools import (
    resize_image, apply_effect, EFFECTS,
    add_watermark_to_image,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🖼️ تبدیل عکس')
@check_usage_limit
def image_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="image", waiting_for=None)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔄 تبدیل فرمت", callback_data="img_op_convert"),
        types.InlineKeyboardButton("📐 تغییر اندازه", callback_data="img_op_resize"),
    )
    markup.add(
        types.InlineKeyboardButton("🎭 افکت", callback_data="img_op_effect"),
        types.InlineKeyboardButton("💧 واترمارک", callback_data="img_op_watermark"),
    )
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="img_op_cancel"))

    bot.send_message(
        message.chat.id,
        "🖼️ <b>ابزار عکس</b>\n\n"
        "🔄 <b>تبدیل فرمت</b> — JPG/PNG/WEBP/PDF\n"
        "📐 <b>تغییر اندازه</b> — با درصد یا پیکسل\n"
        "🎭 <b>افکت</b> — ۱۰ افکت مختلف\n"
        "💧 <b>واترمارک</b> — اسم/لوگو روی عکس",
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("img_op_"))
def image_action(call):
    user_id = call.from_user.id
    action = call.data.replace("img_op_", "")

    if action == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id, call.message.message_id
        )
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    bot.answer_callback_query(call.id)

    if action == "convert":
        set_state(user_id, waiting_for="photo", img_action="convert")
        bot.edit_message_text(
            "🔄 <b>تبدیل فرمت</b>\n\n"
            "یه عکس بفرست (JPG/PNG/WEBP/BMP).",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
    elif action == "resize":
        set_state(user_id, waiting_for="resize_image", img_action="resize")
        bot.edit_message_text(
            "📐 <b>تغییر اندازه</b>\n\n"
            "اول عکس رو بفرست.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
    elif action == "effect":
        set_state(user_id, waiting_for="effect_image", img_action="effect")
        bot.edit_message_text(
            "🎭 <b>افکت عکس</b>\n\n"
            "اول عکس رو بفرست.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
    elif action == "watermark":
        set_state(user_id, waiting_for="wm_image", img_action="watermark")
        bot.edit_message_text(
            "💧 <b>واترمارک</b>\n\n"
            "اول عکس رو بفرست، بعد متن واترمارک رو می‌نویسی.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )


# ---------- دریافت عکس برای تبدیل فرمت ----------
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "photo"
)
def receive_photo_convert(message):
    user_id = message.from_user.id

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
        else:
            file_info_tg = bot.get_file(message.document.file_id)

        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        set_state(user_id, waiting_for="format", input_path=path)

        info = get_file_info(path)
        info_text = format_file_info(info, show_image_details=True)

        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("JPG", callback_data="img_fmt_jpg"),
            types.InlineKeyboardButton("PNG", callback_data="img_fmt_png"),
            types.InlineKeyboardButton("WEBP", callback_data="img_fmt_webp"),
            types.InlineKeyboardButton("PDF", callback_data="img_fmt_pdf"),
            types.InlineKeyboardButton("❌ انصراف", callback_data="img_fmt_cancel"),
        )
        bot.send_message(
            message.chat.id,
            f"{info_text}\n\n✅ فرمت خروجی رو انتخاب کن:",
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception as e:
        logger.exception("خطا در دریافت عکس")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


# ---------- انتخاب فرمت و تبدیل ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("img_fmt_"))
def image_format_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)

    if call.data == "img_fmt_cancel":
        if state.get("input_path"):
            delete_file(state["input_path"])
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text("❌ لغو شد.", call.message.chat.id, call.message.message_id)
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    fmt = call.data.replace("img_fmt_", "")
    input_path = state.get("input_path")

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"در حال تبدیل...")
    bot.edit_message_text(
        f"⏳ در حال تبدیل به {fmt.upper()}...",
        call.message.chat.id, call.message.message_id
    )

    output_path = None
    try:
        output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.{fmt}")
        _convert_image(input_path, output_path, fmt)

        size = os.path.getsize(output_path)
        with open(output_path, "rb") as f:
            bot.send_document(
                call.message.chat.id, f,
                caption=f"✅ {fmt.upper()} — {human_size(size)}"
            )

        mark_user_used(user_id)
    except Exception as e:
        logger.exception("خطا در تبدیل")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")
    finally:
        delete_file(input_path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 📐 تغییر اندازه
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "resize_image"
)
def resize_receive_image(message):
    user_id = message.from_user.id

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

        set_state(user_id, input_path=path, waiting_for="resize_percent")

        markup = types.InlineKeyboardMarkup(row_width=3)
        markup.add(
            types.InlineKeyboardButton("25%", callback_data="rsz_25"),
            types.InlineKeyboardButton("50%", callback_data="rsz_50"),
            types.InlineKeyboardButton("75%", callback_data="rsz_75"),
            types.InlineKeyboardButton("150%", callback_data="rsz_150"),
            types.InlineKeyboardButton("200%", callback_data="rsz_200"),
            types.InlineKeyboardButton("✏️ دستی", callback_data="rsz_custom"),
        )
        bot.send_message(message.chat.id, "📐 درصد تغییر اندازه رو انتخاب کن:", reply_markup=markup)
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("rsz_"))
def resize_percent_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    percent_data = call.data.replace("rsz_", "")

    if percent_data == "custom":
        set_state(user_id, waiting_for="resize_custom")
        bot.answer_callback_query(call.id, "دستی")
        bot.edit_message_text(
            "✏️ درصد رو بنویس (مثلاً <code>60</code>):",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
        return

    percent = int(percent_data)
    _do_resize(call, user_id, input_path, percent)


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "resize_custom"
        and m.text
)
def resize_custom_receive(message):
    user_id = message.from_user.id
    try:
        percent = int(message.text.strip())
        if percent < 5 or percent > 500:
            raise ValueError
    except ValueError:
        bot.send_message(message.chat.id, "❌ عدد بین ۵ تا ۵۰۰ بفرست.")
        return

    state = get_state(user_id)
    input_path = state.get("input_path")

    if not input_path or not os.path.exists(input_path):
        bot.send_message(message.chat.id, "❌ عکس پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, f"⏳ در حال تغییر اندازه ({percent}%)...")
    output = resize_image(input_path, percent=percent)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"📐 {percent}%")
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(input_path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


def _do_resize(call, user_id: int, input_path: str, percent: int):
    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"({percent}%)")
    bot.edit_message_text(
        f"⏳ در حال تغییر اندازه ({percent}%)...",
        call.message.chat.id, call.message.message_id
    )

    output = resize_image(input_path, percent=percent)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_document(call.message.chat.id, f, caption=f"📐 {percent}%")
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(input_path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 🎭 افکت
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "effect_image"
)
def effect_receive_image(message):
    user_id = message.from_user.id

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

        set_state(user_id, input_path=path, waiting_for="effect_choice")

        markup = types.InlineKeyboardMarkup(row_width=2)
        for code, name in EFFECTS.items():
            markup.add(types.InlineKeyboardButton(name, callback_data=f"eff_{code}"))

        bot.send_message(message.chat.id, "🎭 افکت مورد نظر:", reply_markup=markup)
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


@bot.callback_query_handler(func=lambda c: c.data.startswith("eff_"))
def effect_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    effect = call.data.replace("eff_", "")

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال اعمال...")
    bot.edit_message_text(
        f"⏳ افکت {EFFECTS.get(effect, effect)}...",
        call.message.chat.id, call.message.message_id
    )

    output = apply_effect(input_path, effect)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                call.message.chat.id, f,
                caption=f"🎭 <b>{EFFECTS.get(effect, effect)}</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(input_path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 💧 واترمارک (توی بخش عکس)
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "wm_image"
        and get_state(m.from_user.id).get("img_action") == "watermark"
)
def wm_receive_image(message):
    user_id = message.from_user.id

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

        set_state(user_id, input_path=path, waiting_for="wm_text")
        bot.send_message(message.chat.id, "✍️ متن واترمارک رو بنویس:")
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "wm_text"
        and get_state(m.from_user.id).get("img_action") == "watermark"
        and m.text
)
def wm_receive_text(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    text = message.text.strip()

    if not input_path or not os.path.exists(input_path):
        bot.send_message(message.chat.id, "❌ عکس پیدا نشد.")
        clear_state(user_id)
        return

    set_state(user_id, wm_text=text, waiting_for="wm_position")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("↖️ بالا چپ", callback_data="wmpos_top-left"),
        types.InlineKeyboardButton("↗️ بالا راست", callback_data="wmpos_top-right"),
        types.InlineKeyboardButton("↙️ پایین چپ", callback_data="wmpos_bottom-left"),
        types.InlineKeyboardButton("↘️ پایین راست", callback_data="wmpos_bottom-right"),
        types.InlineKeyboardButton("🎯 وسط", callback_data="wmpos_center"),
    )
    bot.send_message(
        message.chat.id,
        f"✅ موقعیت رو انتخاب کن:",
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("wmpos_"))
def wm_position_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    text = state.get("wm_text")
    position = call.data.replace("wmpos_", "")

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال اعمال...")
    bot.edit_message_text("⏳ ...", call.message.chat.id, call.message.message_id)

    output = add_watermark_to_image(input_path, text, position=position)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                call.message.chat.id, f,
                caption=f"💧 <b>واترمارک اعمال شد</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(input_path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ---------- تبدیل عکس (کمکی) ----------
def _convert_image(input_path: str, output_path: str, fmt: str):
    img = Image.open(input_path)

    if fmt == "pdf":
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGB")
        img.save(output_path, "PDF", resolution=100.0)
        return

    if fmt == "jpg" and img.mode in ("RGBA", "LA", "P"):
        background = Image.new("RGB", img.size, (255, 255, 255))
        if img.mode == "RGBA":
            background.paste(img, mask=img.split()[-1])
        else:
            background.paste(img)
        img = background
    elif img.mode == "P":
        img = img.convert("RGBA")

    img.save(output_path, fmt.upper())


# ---------- ثبت در دیتابیس ----------
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
            logger.warning(f"log fail: {e}")
    threading.Thread(target=runner, daemon=True).start()