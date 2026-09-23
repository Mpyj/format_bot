import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.file_info import human_size
from utils.creative_tools import (
    generate_password, password_strength,
    translate_text, SUPPORTED_LANGS,
    text_to_speech,
    add_watermark_to_image,
    text_to_image,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


def _escape_html(text: str) -> str:
    """escape کردن کاراکترهای خاص HTML"""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🎨 جعبه خلاقیت')
@check_usage_limit
def creativity_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="creative", waiting_for=None)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔐 رمز قوی", callback_data="crt_op_pass"),
        types.InlineKeyboardButton("🌍 ترجمه", callback_data="crt_op_trans"),
    )
    markup.add(
        types.InlineKeyboardButton("🔊 متن → صوت", callback_data="crt_op_tts"),
        types.InlineKeyboardButton("🎨 متن → عکس", callback_data="crt_op_t2i"),
    )
    markup.add(
        types.InlineKeyboardButton("💧 واترمارک عکس", callback_data="crt_op_wm"),
    )
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="crt_op_cancel"))

    bot.send_message(
        message.chat.id,
        "🎨 <b>جعبه خلاقیت</b>\n\n"
        "🔐 <b>رمز قوی</b> — تولید رمز عبور امن\n"
        "🌍 <b>ترجمه</b> — ۱۰ زبان\n"
        "🔊 <b>متن → صوت</b> — فارسی و انگلیسی\n"
        "🎨 <b>متن → عکس</b> — متن رو روی عکس\n"
        "💧 <b>واترمارک عکس</b> — اسم/لوگو روی عکس",
        parse_mode='HTML',
        reply_markup=markup
    )


# ---------- انتخاب عملیات ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("crt_op_"))
def creativity_action(call):
    user_id = call.from_user.id
    action = call.data.replace("crt_op_", "")

    if action == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    bot.answer_callback_query(call.id)

    if action == "pass":
        _password_menu(call, user_id)
    elif action == "trans":
        _translate_menu(call, user_id)
    elif action == "tts":
        set_state(user_id, waiting_for="creative_tts_text")
        bot.edit_message_text(
            "🔊 <b>متن → صوت</b>\n\n"
            "متن رو بفرست تا برات صوت کنم.\n\n"
            "💡 حداکثر ۵۰۰۰ کاراکتر.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
    elif action == "t2i":
        set_state(user_id, waiting_for="creative_t2i_text")
        bot.edit_message_text(
            "🎨 <b>متن → عکس</b>\n\n"
            "متن رو بفرست تا تبدیل به عکس کنم.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )
    elif action == "wm":
        set_state(user_id, waiting_for="creative_wm_image")
        bot.edit_message_text(
            "💧 <b>واترمارک عکس</b>\n\n"
            "اول عکس رو بفرست، بعد متن واترمارک رو می‌نویسی.",
            call.message.chat.id, call.message.message_id, parse_mode='HTML'
        )


# ============================================================
# 🔐 رمز قوی
# ============================================================
def _password_menu(call, user_id: int):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("۸ کاراکتر", callback_data="pwd_8"),
        types.InlineKeyboardButton("۱۲ کاراکتر", callback_data="pwd_12"),
        types.InlineKeyboardButton("۱۶ کاراکتر", callback_data="pwd_16"),
        types.InlineKeyboardButton("۲۴ کاراکتر", callback_data="pwd_24"),
        types.InlineKeyboardButton("۳۲ کاراکتر", callback_data="pwd_32"),
        types.InlineKeyboardButton("۶۴ کاراکتر", callback_data="pwd_64"),
    )
    bot.edit_message_text(
        "🔐 <b>تولید رمز قوی</b>\n\n"
        "طول رمز رو انتخاب کن:",
        call.message.chat.id, call.message.message_id,
        parse_mode='HTML', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("pwd_"))
def creative_pwd_generate(call):
    user_id = call.from_user.id
    length = int(call.data.replace("pwd_", ""))

    password = generate_password(length)
    level, emoji = password_strength(password)

    passwords = [generate_password(length) for _ in range(3)]
    passwords.insert(0, password)

    text = f"🔐 <b>رمزهای تولید شده ({length} کاراکتر)</b>\n\n"
    for i, pwd in enumerate(passwords, 1):
        text += f"{i}. <code>{pwd}</code>\n\n"
    text += f"\n{emoji} <b>قدرت:</b> {level}\n"
    text += "💡 روی رمز بزن تا کپی کنی."

    bot.edit_message_text(
        text,
        call.message.chat.id, call.message.message_id,
        parse_mode='HTML'
    )
    mark_user_used(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 🌍 ترجمه
# ============================================================
def _translate_menu(call, user_id: int):
    set_state(user_id, waiting_for="creative_trans_lang")

    markup = types.InlineKeyboardMarkup(row_width=2)
    buttons = [
        types.InlineKeyboardButton(name, callback_data=f"trlang_{code}")
        for code, name in SUPPORTED_LANGS.items()
    ]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="trlang_cancel"))

    bot.edit_message_text(
        "🌍 <b>ترجمه</b>\n\n"
        "زبان مقصد رو انتخاب کن، بعد متن رو می‌فرستی:",
        call.message.chat.id, call.message.message_id,
        parse_mode='HTML', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("trlang_"))
def creative_translate_lang(call):
    user_id = call.from_user.id
    lang = call.data.replace("trlang_", "")

    if lang == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ لغو شد.",
            call.message.chat.id, call.message.message_id
        )
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    set_state(user_id, trans_lang=lang, waiting_for="creative_trans_text")
    lang_name = SUPPORTED_LANGS.get(lang, lang)
    bot.answer_callback_query(call.id, f"زبان: {lang_name}")
    bot.edit_message_text(
        f"✅ زبان مقصد: <b>{lang_name}</b>\n\n"
        "الان متن رو بفرست:",
        call.message.chat.id, call.message.message_id,
        parse_mode='HTML'
    )


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "creative_trans_text"
        and m.text
)
def creative_translate_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    lang = state.get("trans_lang")
    text = message.text.strip()

    bot.send_message(message.chat.id, "⏳ در حال ترجمه...")

    result = translate_text(text, lang)

    if result:
        lang_name = SUPPORTED_LANGS.get(lang, lang)

        # 👇 escape کردن برای جلوگیری از خطای HTML
        safe_original = _escape_html(text[:500])
        safe_result = _escape_html(result)

        bot.send_message(
            message.chat.id,
            f"🌍 <b>ترجمه به {lang_name}:</b>\n\n"
            f"📝 <b>متن اصلی:</b>\n<i>{safe_original}</i>\n\n"
            f"✅ <b>ترجمه:</b>\n<code>{safe_result}</code>",
            parse_mode='HTML'
        )
        mark_user_used(user_id)
    else:
        bot.send_message(
            message.chat.id,
            "❌ ترجمه ناموفق بود.\n\n"
            "🔹 هر دو سرویس (Google و MyMemory) خطا دادن.\n"
            "🔹 چند لحظه دیگه دوباره تلاش کن."
        )

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 🔊 متن → صوت
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "creative_tts_text"
        and m.text
)
def creative_tts_receive(message):
    user_id = message.from_user.id
    text = message.text.strip()[:5000]

    set_state(user_id, tts_text=text, waiting_for="creative_tts_lang")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🇮🇷 فارسی", callback_data="tts_lang_fa"),
        types.InlineKeyboardButton("🇬🇧 انگلیسی", callback_data="tts_lang_en"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="tts_lang_cancel"),
    )
    bot.send_message(
        message.chat.id,
        f"✅ متن دریافت شد:\n<code>{_escape_html(text[:300])}</code>\n\n"
        "کدوم زبان؟",
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("tts_lang_"))
def creative_tts_lang(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    text = state.get("tts_text")
    lang = call.data.replace("tts_lang_", "")

    if lang == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ لغو شد.",
            call.message.chat.id, call.message.message_id
        )
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    if not text:
        bot.answer_callback_query(call.id, "متن پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    lang_name = {"fa": "فارسی", "en": "انگلیسی"}.get(lang, lang)
    bot.answer_callback_query(call.id, f"در حال ساخت ({lang_name})...")
    bot.edit_message_text(
        f"⏳ در حال ساخت صوت {lang_name}...",
        call.message.chat.id, call.message.message_id
    )

    output = text_to_speech(text, lang=lang)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        ext = os.path.splitext(output)[1].lstrip(".").lower()

        with open(output, "rb") as f:
            bot.send_audio(
                call.message.chat.id, f,
                caption=f"🔊 <b>صوت {lang_name} آماده‌ست</b>\n"
                        f"📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        if lang == "fa":
            bot.send_message(
                call.message.chat.id,
                "❌ ساخت صوت فارسی ناموفق بود.\n"
                "ممکنه `persian-speech` نصب نباشه."
            )
        else:
            bot.send_message(
                call.message.chat.id,
                "❌ ساخت صوت انگلیسی ناموفق بود."
            )

    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 🎨 متن → عکس
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "creative_t2i_text"
        and m.text
)
def creative_t2i_receive(message):
    user_id = message.from_user.id
    text = message.text.strip()

    bot.send_message(message.chat.id, "⏳ در حال ساخت عکس...")

    output = text_to_image(text)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption="🎨 <b>عکس ساخته شد!</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ساخت عکس ناموفق بود.")

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ============================================================
# 💧 واترمارک عکس
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "creative_wm_image"
)
def creative_wm_receive_image(message):
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

        set_state(user_id, input_path=path, waiting_for="creative_wm_text")
        bot.send_message(message.chat.id, "✍️ الان متن واترمارک رو بنویس:")

    except Exception as e:
        logger.exception("خطا در دریافت عکس")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "creative_wm_text"
        and m.text
)
def creative_wm_receive_text(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    text = message.text.strip()

    if not input_path or not os.path.exists(input_path):
        bot.send_message(message.chat.id, "❌ عکس پیدا نشد.")
        clear_state(user_id)
        return

    set_state(user_id, wm_text=text, waiting_for="creative_wm_position")
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("↖️ بالا چپ", callback_data="cwmpos_top-left"),
        types.InlineKeyboardButton("↗️ بالا راست", callback_data="cwmpos_top-right"),
        types.InlineKeyboardButton("↙️ پایین چپ", callback_data="cwmpos_bottom-left"),
        types.InlineKeyboardButton("↘️ پایین راست", callback_data="cwmpos_bottom-right"),
        types.InlineKeyboardButton("🎯 وسط", callback_data="cwmpos_center"),
    )
    bot.send_message(
        message.chat.id,
        f"✅ متن: <code>{_escape_html(text)}</code>\n\n📍 موقعیت رو انتخاب کن:",
        parse_mode='HTML', reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("cwmpos_"))
def creative_wm_position(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    text = state.get("wm_text")
    position = call.data.replace("cwmpos_", "")

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "عکس پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال اعمال...")
    bot.edit_message_text(
        "⏳ در حال اعمال واترمارک...",
        call.message.chat.id, call.message.message_id
    )

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