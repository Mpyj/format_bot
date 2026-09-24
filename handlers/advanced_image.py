import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.file_info import human_size
from utils.advanced_image import (
    get_color_palette, generate_palette_image, get_color_history,
    auto_rotate, zoom_image, make_collage, add_frame,
    smart_crop, artistic_effect, images_to_gif, get_image_dimensions,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منوی تصویر پیشرفته
# ============================================================
def _adv_image_menu(user_id: int = None, page: int = 1):
    markup = types.InlineKeyboardMarkup(row_width=2)

    if page == 1:
        markup.add(
            types.InlineKeyboardButton("🎨 پالت رنگ", callback_data="advimg_palette"),
            types.InlineKeyboardButton("📊 تاریخچه رنگ", callback_data="advimg_history"),
        )
        markup.add(
            types.InlineKeyboardButton("📐 چرخش خودکار", callback_data="advimg_rotate"),
            types.InlineKeyboardButton("🔍 بزرگ‌نمایی", callback_data="advimg_zoom"),
        )
        markup.add(
            types.InlineKeyboardButton("بعدی ➡️", callback_data="advimg_page_2"),
            types.InlineKeyboardButton("❌ بستن", callback_data="advimg_close"),
        )
    elif page == 2:
        markup.add(
            types.InlineKeyboardButton("📸 کولاژ", callback_data="advimg_collage"),
            types.InlineKeyboardButton("🖼️ افزودن فریم", callback_data="advimg_frame"),
        )
        markup.add(
            types.InlineKeyboardButton("🎭 افکت هنری", callback_data="advimg_art"),
            types.InlineKeyboardButton("✂️ برش هوشمند", callback_data="advimg_crop"),
        )
        markup.add(
            types.InlineKeyboardButton("🎬 عکس → GIF", callback_data="advimg_gif"),
        )
        markup.add(
            types.InlineKeyboardButton("⬅️ قبلی", callback_data="advimg_page_1"),
            types.InlineKeyboardButton("❌ بستن", callback_data="advimg_close"),
        )
    return markup


def _menu_text(page: int) -> str:
    if page == 1:
        return (
            "🎨 <b>تصویر پیشرفته — صفحه ۱/۲</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "🎨 <b>پالت رنگ</b> — ۵ رنگ غالب\n"
            "📊 <b>تاریخچه رنگ</b> — تحلیل رنگ‌ها\n"
            "📐 <b>چرخش خودکار</b> — بر اساس EXIF\n"
            "🔍 <b>بزرگ‌نمایی</b> — ۲x، ۴x بدون افت"
        )
    return (
        "🎨 <b>تصویر پیشرفته — صفحه ۲/۲</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "📸 <b>کولاژ</b> — ترکیب چند عکس\n"
        "🖼️ <b>افزودن فریم</b> — قاب رنگی\n"
        "🎭 <b>افکت هنری</b> — نقاشی، مدادی، کارتونی\n"
        "✂️ <b>برش هوشمند</b> — نسبت‌های آماده\n"
        "🎬 <b>عکس → GIF</b> — انیمیشن"
    )


def _back_markup():
    return types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="advimg_back")
    )


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '🎨 تصویر پیشرفته')
def adv_image_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="adv_image", waiting_for=None, advimg_page=1)

    bot.send_message(
        message.chat.id,
        _menu_text(1),
        parse_mode='HTML',
        reply_markup=_adv_image_menu(user_id, 1)
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("advimg_page_"))
def adv_image_page_nav(call):
    user_id = call.from_user.id
    page = int(call.data.replace("advimg_page_", ""))
    set_state(user_id, advimg_page=page)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            _menu_text(page),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_adv_image_menu(user_id, page)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            _menu_text(page),
            parse_mode='HTML', reply_markup=_adv_image_menu(user_id, page)
        )


@bot.callback_query_handler(func=lambda c: c.data == "advimg_back")
def adv_image_back(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    page = state.get("advimg_page", 1)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            _menu_text(page),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_adv_image_menu(user_id, page)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            _menu_text(page),
            parse_mode='HTML', reply_markup=_adv_image_menu(user_id, page)
        )


# ============================================================
# callback اصلی
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("advimg_"))
def adv_image_action(call):
    user_id = call.from_user.id
    action = call.data.replace("advimg_", "")

    if action == "close":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "بسته شد")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        bot.send_message(
            call.message.chat.id,
            "منوی اصلی:",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    bot.answer_callback_query(call.id)

    # کولاژ و GIF حالت خاص دارن
    if action == "collage":
        set_state(user_id, mode="adv_image", advimg_action="collage",
                  waiting_for="advimg_collage", advimg_files=[])
        try:
            bot.edit_message_text(
                "📸 <b>کولاژ</b>\n\n"
                "چند عکس بفرست (۲ تا ۹ عکس).\n"
                "وقتی همه رو فرستادی، دکمه «✅ تمام شد» رو بزن.",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton('✅ تمام شد'),
                    types.KeyboardButton('❌ انصراف')
                )
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "📸 <b>کولاژ</b>\n\nچند عکس بفرست:",
                parse_mode='HTML',
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton('✅ تمام شد'),
                    types.KeyboardButton('❌ انصراف')
                )
            )
        return

    if action == "gif":
        set_state(user_id, mode="adv_image", advimg_action="gif",
                  waiting_for="advimg_gif", advimg_files=[])
        try:
            bot.edit_message_text(
                "🎬 <b>عکس → GIF</b>\n\n"
                "چند عکس بفرست (۲ تا ۱۰ عکس).\n"
                "وقتی همه رو فرستادی، دکمه «✅ تمام شد» رو بزن.",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML',
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton('✅ تمام شد'),
                    types.KeyboardButton('❌ انصراف')
                )
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "🎬 <b>عکس → GIF</b>\n\nچند عکس بفرست:",
                parse_mode='HTML',
                reply_markup=types.ReplyKeyboardMarkup(resize_keyboard=True).add(
                    types.KeyboardButton('✅ تمام شد'),
                    types.KeyboardButton('❌ انصراف')
                )
            )
        return

    if action == "zoom":
        set_state(user_id, mode="adv_image", advimg_action="zoom", waiting_for="advimg_zoom")
        try:
            bot.edit_message_text(
                "🔍 <b>بزرگ‌نمایی</b>\n\nعکس رو بفرست:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_markup()
            )
        except Exception:
            bot.send_message(call.message.chat.id, "🔍 عکس رو بفرست:", parse_mode='HTML', reply_markup=_back_markup())
        return

    if action == "frame":
        set_state(user_id, mode="adv_image", advimg_action="frame", waiting_for="advimg_frame")
        try:
            bot.edit_message_text(
                "🖼️ <b>افزودن فریم</b>\n\nعکس رو بفرست:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_markup()
            )
        except Exception:
            bot.send_message(call.message.chat.id, "🖼️ عکس رو بفرست:", parse_mode='HTML', reply_markup=_back_markup())
        return

    if action == "art":
        set_state(user_id, mode="adv_image", advimg_action="art", waiting_for="advimg_art")
        try:
            bot.edit_message_text(
                "🎭 <b>افکت هنری</b>\n\nعکس رو بفرست:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_markup()
            )
        except Exception:
            bot.send_message(call.message.chat.id, "🎭 عکس رو بفرست:", parse_mode='HTML', reply_markup=_back_markup())
        return

    if action == "crop":
        set_state(user_id, mode="adv_image", advimg_action="crop", waiting_for="advimg_crop")
        try:
            bot.edit_message_text(
                "✂️ <b>برش هوشمند</b>\n\nعکس رو بفرست:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_markup()
            )
        except Exception:
            bot.send_message(call.message.chat.id, "✂️ عکس رو بفرست:", parse_mode='HTML', reply_markup=_back_markup())
        return

    # راهنماهای ساده
    hints = {
        "palette": "🎨 <b>پالت رنگ</b>\n\nعکس رو بفرست:",
        "history": "📊 <b>تاریخچه رنگ</b>\n\nعکس رو بفرست:",
        "rotate": "📐 <b>چرخش خودکار</b>\n\nعکس رو بفرست:",
    }

    set_state(user_id, mode="adv_image", advimg_action=action, waiting_for=f"advimg_{action}")
    try:
        bot.edit_message_text(
            hints.get(action, "عملیات نامشخص"),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_back_markup()
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            hints.get(action, "عملیات نامشخص"),
            parse_mode='HTML', reply_markup=_back_markup()
        )


# ============================================================
# 📥 دریافت عکس
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for", "").startswith("advimg_")
        and get_state(m.from_user.id).get("mode") == "adv_image"
        and get_state(m.from_user.id).get("waiting_for") not in (
            "advimg_collage",
            "advimg_gif",
            "advimg_zoom_choice",
            "advimg_frame_color",
            "advimg_art_choice",
            "advimg_crop_choice",
        )
)
def adv_image_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("advimg_action")
    path = None

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
            ext = ".jpg"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"

        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        set_state(user_id, advimg_input_path=path)

        if action == "palette":
            _process_palette(message, user_id, path)
        elif action == "history":
            _process_history(message, user_id, path)
        elif action == "rotate":
            _process_rotate(message, user_id, path)
        elif action == "zoom":
            set_state(user_id, waiting_for="advimg_zoom_choice")
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("2x", callback_data="zoom_2"),
                types.InlineKeyboardButton("3x", callback_data="zoom_3"),
                types.InlineKeyboardButton("4x", callback_data="zoom_4"),
            )
            bot.send_message(message.chat.id, "🔍 ضریب بزرگ‌نمایی:", reply_markup=markup)
        elif action == "frame":
            set_state(user_id, waiting_for="advimg_frame_color")
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("⚪ سفید", callback_data="frame_#FFFFFF"),
                types.InlineKeyboardButton("⚫ مشکی", callback_data="frame_#000000"),
                types.InlineKeyboardButton("🔴 قرمز", callback_data="frame_#DD0000"),
                types.InlineKeyboardButton("🔵 آبی", callback_data="frame_#0066FF"),
                types.InlineKeyboardButton("🟢 سبز", callback_data="frame_#00AA44"),
                types.InlineKeyboardButton("🟡 زرد", callback_data="frame_#FFD700"),
            )
            bot.send_message(message.chat.id, "🖼️ رنگ فریم:", reply_markup=markup)
        elif action == "art":
            set_state(user_id, waiting_for="advimg_art_choice")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("🎨 نقاشی روغنی", callback_data="art_oil"),
                types.InlineKeyboardButton("✏️ طرح مدادی", callback_data="art_pencil"),
            )
            markup.add(
                types.InlineKeyboardButton("💧 آبرنگ", callback_data="art_watercolor"),
                types.InlineKeyboardButton("📺 کارتونی", callback_data="art_cartoon"),
            )
            markup.add(
                types.InlineKeyboardButton("🌈 HDR", callback_data="art_hdr"),
                types.InlineKeyboardButton("📷 قدیمی", callback_data="art_vintage"),
            )
            bot.send_message(message.chat.id, "🎭 افکت رو انتخاب کن:", reply_markup=markup)
        elif action == "crop":
            set_state(user_id, waiting_for="advimg_crop_choice")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("1:1 (مربع)", callback_data="crop_1:1"),
                types.InlineKeyboardButton("16:9 (یوتیوب)", callback_data="crop_16:9"),
            )
            markup.add(
                types.InlineKeyboardButton("9:16 (استوری)", callback_data="crop_9:16"),
                types.InlineKeyboardButton("4:3 (کلاسیک)", callback_data="crop_4:3"),
            )
            markup.add(
                types.InlineKeyboardButton("3:2 (عکس)", callback_data="crop_3:2"),
            )
            bot.send_message(message.chat.id, "✂️ نسبت رو انتخاب کن:", reply_markup=markup)

    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        if path:
            delete_file(path)
        clear_state(user_id)


# ============================================================
# 🎨 پالت رنگ
# ============================================================
def _process_palette(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال استخراج رنگ‌ها...")
    output = generate_palette_image(path, 5)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption="🎨 <b>پالت رنگ عکس</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📊 تاریخچه رنگ
# ============================================================
def _process_history(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال تحلیل...")
    result = get_color_history(path)

    if result.get("success"):
        text = "📊 <b>تاریخچه رنگ</b>\n━━━━━━━━━━━━━━━\n\n"
        for item in result["history"]:
            text += f"{item['name']}: <b>{item['percentage']}%</b>\n"
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📐 چرخش خودکار
# ============================================================
def _process_rotate(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال چرخش...")
    output = auto_rotate(path)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption="📐 <b>چرخش خودکار انجام شد</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🔍 بزرگ‌نمایی
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("zoom_"))
def zoom_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("advimg_input_path")
    factor = int(call.data.replace("zoom_", ""))

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"({factor}x)")
    bot.edit_message_text(
        f"⏳ در حال بزرگ‌نمایی ({factor}x)...",
        call.message.chat.id, call.message.message_id
    )

    output = zoom_image(path, factor)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                call.message.chat.id, f,
                caption=f"🔍 <b>بزرگ‌نمایی {factor}x</b>\n📊 {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🖼️ فریم
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("frame_"))
def frame_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("advimg_input_path")
    color = call.data.replace("frame_", "")

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال افزودن...")
    bot.edit_message_text(
        "⏳ در حال افزودن فریم...",
        call.message.chat.id, call.message.message_id
    )

    output = add_frame(path, color, 30)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_photo(
                call.message.chat.id, f,
                caption=f"🖼️ <b>فریم افزوده شد</b>\n🎨 {color}\n📊 {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🎭 افکت هنری
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("art_"))
def art_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("advimg_input_path")
    effect = call.data.replace("art_", "")

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    effect_names = {
        "oil": "نقاشی روغنی",
        "pencil": "طرح مدادی",
        "watercolor": "آبرنگ",
        "cartoon": "کارتونی",
        "hdr": "HDR",
        "vintage": "قدیمی",
    }

    bot.answer_callback_query(call.id, f"({effect_names.get(effect, effect)})")
    bot.edit_message_text(
        f"⏳ در حال اعمال {effect_names.get(effect, effect)}...",
        call.message.chat.id, call.message.message_id
    )

    output = artistic_effect(path, effect)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_photo(
                call.message.chat.id, f,
                caption=f"🎭 <b>{effect_names.get(effect, effect)}</b>\n📊 {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# ✂️ برش
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("crop_"))
def crop_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("advimg_input_path")
    ratio = call.data.replace("crop_", "")

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"({ratio})")
    bot.edit_message_text(
        f"⏳ در حال برش ({ratio})...",
        call.message.chat.id, call.message.message_id
    )

    output = smart_crop(path, ratio)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_photo(
                call.message.chat.id, f,
                caption=f"✂️ <b>برش {ratio}</b>\n📊 {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📸 کولاژ — دریافت عکس‌ها
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "advimg_collage"
        and get_state(m.from_user.id).get("mode") == "adv_image"
)
def adv_collage_add(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("advimg_files", [])

    if len(files) >= 9:
        bot.send_message(message.chat.id, "⚠️ حداکثر ۹ عکس. دکمه «✅ تمام شد» رو بزن.")
        return

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
            ext = ".jpg"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"

        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        files.append(path)
        set_state(user_id, advimg_files=files)

        bot.send_message(
            message.chat.id,
            f"✅ عکس {len(files)} دریافت شد.\nعکس بعدی یا «✅ تمام شد»."
        )
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")


# ============================================================
# 🎬 GIF — دریافت عکس‌ها
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "advimg_gif"
        and get_state(m.from_user.id).get("mode") == "adv_image"
)
def adv_gif_add(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("advimg_files", [])

    if len(files) >= 10:
        bot.send_message(message.chat.id, "⚠️ حداکثر ۱۰ عکس. دکمه «✅ تمام شد» رو بزن.")
        return

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
            ext = ".jpg"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"

        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        files.append(path)
        set_state(user_id, advimg_files=files)

        bot.send_message(
            message.chat.id,
            f"✅ عکس {len(files)} دریافت شد.\nعکس بعدی یا «✅ تمام شد»."
        )
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")


# ============================================================
# ✅ تمام شد (کولاژ / GIF)
# ============================================================
@bot.message_handler(
    func=lambda m: m.text in ('✅ تمام شد', '❌ انصراف')
        and get_state(m.from_user.id).get("waiting_for") in ("advimg_collage", "advimg_gif")
        and get_state(m.from_user.id).get("mode") == "adv_image"
)
def adv_image_finish_list(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("advimg_files", [])
    waiting_for = state.get("waiting_for")

    if message.text == '❌ انصراف':
        for f in files:
            delete_file(f)
        clear_state(user_id)
        bot.send_message(message.chat.id, "❌ لغو شد.", reply_markup=main_menu_keyboard(user_id))
        return

    if len(files) < 2:
        bot.send_message(message.chat.id, "⚠️ حداقل ۲ عکس لازمه.")
        return

    if waiting_for == "advimg_collage":
        bot.send_message(message.chat.id, f"⏳ در حال ساخت کولاژ از {len(files)} عکس...")
        output = make_collage(files, cols=0, cell_size=400)

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_photo(
                    message.chat.id, f,
                    caption=f"📸 <b>کولاژ</b>\n🖼 {len(files)} عکس\n📊 {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ناموفق بود.")
    else:
        bot.send_message(message.chat.id, f"⏳ در حال ساخت GIF از {len(files)} عکس...")
        output = images_to_gif(files, duration=500)

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_animation(
                    message.chat.id, f,
                    caption=f"🎬 <b>GIF</b>\n🖼 {len(files)} فریم\n📊 {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ناموفق بود.")

    for f in files:
        delete_file(f)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))