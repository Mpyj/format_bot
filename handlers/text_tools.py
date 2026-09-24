import logging
from telebot import types

from main import bot
from utils.states import set_state, get_state, clear_state
from utils.text_tools import (
    count_text, transform_case, unicode_styles, reverse_text,
    clean_text, base64_encode, base64_decode,
    url_encode, url_decode, convert_number,
    analyze_text, ascii_art, get_ascii_fonts,
)
from utils.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منوهای صفحه‌بندی شده
# ============================================================
def _menu_page(user_id: int, page: int = 1):
    """منوی صفحه‌بندی شده ابزار متنی"""
    if page == 1:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🔤 شمارش کلمات", callback_data="txt_op_count"),
            types.InlineKeyboardButton("🔄 تبدیل حروف", callback_data="txt_op_case"),
        )
        markup.add(
            types.InlineKeyboardButton("🎭 استایل یونیکد", callback_data="txt_op_unicode"),
            types.InlineKeyboardButton("🔁 Reverse", callback_data="txt_op_reverse"),
        )
        markup.add(
            types.InlineKeyboardButton("بعدی ➡️", callback_data="txt_page_2"),
            types.InlineKeyboardButton("❌ بستن", callback_data="txt_op_close"),
        )
        return markup

    if page == 2:
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("🧹 پاک‌سازی", callback_data="txt_op_clean"),
            types.InlineKeyboardButton("📊 تحلیل متن", callback_data="txt_op_analyze"),
        )
        markup.add(
            types.InlineKeyboardButton("🔐 Base64", callback_data="txt_op_base64"),
            types.InlineKeyboardButton("🔗 URL", callback_data="txt_op_url"),
        )
        markup.add(
            types.InlineKeyboardButton("🔢 تبدیل اعداد", callback_data="txt_op_number"),
            types.InlineKeyboardButton("🎨 ASCII Art", callback_data="txt_op_ascii"),
        )
        markup.add(
            types.InlineKeyboardButton("⬅️ قبلی", callback_data="txt_page_1"),
            types.InlineKeyboardButton("❌ بستن", callback_data="txt_op_close"),
        )
        return markup

    return markup


def _menu_text(page: int) -> str:
    if page == 1:
        return (
            "🛠 <b>ابزار متنی — صفحه ۱/۲</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            "🔤 <b>شمارش کلمات</b> — آمار کامل متن\n"
            "🔄 <b>تبدیل حروف</b> — UPPER، lower، Title و ...\n"
            "🎭 <b>استایل یونیکد</b> — متن با فونت‌های خاص\n"
            "🔁 <b>Reverse</b> — برعکس کردن متن"
        )
    return (
        "🛠 <b>ابزار متنی — صفحه ۲/۲</b>\n"
        "━━━━━━━━━━━━━━━\n\n"
        "🧹 <b>پاک‌سازی</b> — حذف فاصله و کاراکتر اضافه\n"
        "📊 <b>تحلیل متن</b> — پربسامدترین کلمات\n"
        "🔐 <b>Base64</b> — Encode / Decode\n"
        "🔗 <b>URL</b> — Encode / Decode\n"
        "🔢 <b>تبدیل اعداد</b> — دهدهی، باینری، هگز\n"
        "🎨 <b>ASCII Art</b> — متن به هنر اسکی"
    )


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '🛠 ابزار متنی')
def text_tools_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="text", waiting_for=None, text_page=1)

    bot.send_message(
        message.chat.id,
        _menu_text(1),
        parse_mode='HTML',
        reply_markup=_menu_page(user_id, 1)
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("txt_page_"))
def text_page_nav(call):
    user_id = call.from_user.id
    page = int(call.data.replace("txt_page_", ""))
    set_state(user_id, text_page=page)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            _menu_text(page),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_menu_page(user_id, page)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            _menu_text(page),
            parse_mode='HTML', reply_markup=_menu_page(user_id, page)
        )


@bot.callback_query_handler(func=lambda c: c.data == "txt_back")
def text_back(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    page = state.get("text_page", 1)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            _menu_text(page),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_menu_page(user_id, page)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            _menu_text(page),
            parse_mode='HTML', reply_markup=_menu_page(user_id, page)
        )


# ============================================================
# انتخاب عملیات
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("txt_op_"))
def text_action(call):
    user_id = call.from_user.id
    action = call.data.replace("txt_op_", "")

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

    # راهنماها
    hints = {
        "count": "🔤 <b>شمارش کلمات</b>\n\nمتن رو بفرست:",
        "case": "🔄 <b>تبدیل حروف</b>\n\nمتن رو بفرست:",
        "unicode": "🎭 <b>استایل یونیکد</b>\n\nمتن رو بفرست (انگلیسی):",
        "reverse": "🔁 <b>Reverse</b>\n\nمتن رو بفرست:",
        "clean": "🧹 <b>پاک‌سازی متن</b>\n\nمتن رو بفرست:",
        "analyze": "📊 <b>تحلیل متن</b>\n\nمتن رو بفرست:",
        "base64": "🔐 <b>Base64</b>\n\nمتن رو بفرست:",
        "url": "🔗 <b>URL Encode/Decode</b>\n\nمتن یا URL رو بفرست:",
        "number": "🔢 <b>تبدیل اعداد</b>\n\nیه عدد بفرست (دهدهی):\nمثال: <code>255</code>",
        "ascii": "🎨 <b>ASCII Art</b>\n\nیه متن انگلیسی بفرست:",
    }

    set_state(user_id, text_action=action, waiting_for=f"txt_{action}")

    try:
        bot.edit_message_text(
            hints.get(action, "عملیات نامشخص"),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="txt_back")
            )
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            hints.get(action, "عملیات نامشخص"),
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="txt_back")
            )
        )


# ============================================================
# پردازش متن ورودی
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for", "").startswith("txt_")
        and m.text
        and not m.text.startswith("/")
)
def text_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("text_action")
    text = message.text.strip()

    if action == "count":
        _handle_count(message, text)
    elif action == "case":
        _handle_case(message, text)
    elif action == "unicode":
        _handle_unicode(message, text)
    elif action == "reverse":
        _handle_reverse(message, text)
    elif action == "clean":
        _handle_clean(message, text)
    elif action == "analyze":
        _handle_analyze(message, text)
    elif action == "base64":
        _handle_base64(message, text)
    elif action == "url":
        _handle_url(message, text)
    elif action == "number":
        _handle_number(message, text)
    elif action == "ascii":
        _handle_ascii(message, text)
    else:
        bot.send_message(message.chat.id, "❌ عملیات نامشخص")

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# هندلرهای اختصاصی
# ============================================================
def _handle_count(message, text: str):
    info = count_text(text)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    result = (
        f"🔤 <b>آمار متن</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>کلمات:</b> {info['word_count']:,}\n"
        f"🔤 <b>حروف:</b> {info['letter_count']:,}\n"
        f"📊 <b>کاراکتر (با فاصله):</b> {info['char_count']:,}\n"
        f"📊 <b>کاراکتر (بدون فاصله):</b> {info['char_no_space']:,}\n"
        f"📄 <b>خطوط:</b> {info['line_count']}\n"
        f"📃 <b>پاراگراف:</b> {info['para_count']}\n"
        f"📖 <b>جملات:</b> {info['sentence_count']}\n\n"
        f"⏱ <b>زمان خوندن:</b> ~{info['reading_time']} دقیقه\n"
        f"🗣 <b>زمان صحبت:</b> ~{info['speaking_time']} دقیقه"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_case(message, text: str):
    info = transform_case(text)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    # escape
    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    result = (
        f"🔄 <b>حالت‌های مختلف</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>UPPER:</b>\n<code>{esc(info['upper'])}</code>\n\n"
        f"<b>lower:</b>\n<code>{esc(info['lower'])}</code>\n\n"
        f"<b>Title:</b>\n<code>{esc(info['title'])}</code>\n\n"
        f"<b>Sentence:</b>\n<code>{esc(info['sentence'])}</code>\n\n"
        f"<b>aLtErNaTiNg:</b>\n<code>{esc(info['alternate'])}</code>\n\n"
        f"<b>iNVERSE:</b>\n<code>{esc(info['inverse'])}</code>"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_unicode(message, text: str):
    info = unicode_styles(text[:50])  # محدود به ۵۰ کاراکتر
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    result = (
        f"🎭 <b>استایل‌های یونیکد</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>Bold:</b>\n{info['bold']}\n\n"
        f"<b>Italic:</b>\n{info['italic']}\n\n"
        f"<b>Script:</b>\n{info['script']}\n\n"
        f"<b>Fraktur:</b>\n{info['fraktur']}\n\n"
        f"<b>Mono:</b>\n{info['mono']}"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_reverse(message, text: str):
    info = reverse_text(text)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    result = (
        f"🔁 <b>Reverse</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>کل متن برعکس:</b>\n<code>{esc(info['reversed'])}</code>\n\n"
        f"<b>ترتیب کلمات برعکس:</b>\n<code>{esc(info['reversed_words'])}</code>\n\n"
        f"<b>هر کلمه برعکس:</b>\n<code>{esc(info['each_word_reversed'])}</code>"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_clean(message, text: str):
    info = clean_text(text)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    def esc(s):
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    # فقط ۲۰۰ کاراکتر اول هر کدوم
    def short(s):
        s = s[:200]
        return s + "..." if len(s) == 200 else s

    result = (
        f"🧹 <b>پاک‌سازی متن</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>حذف فاصله اضافه:</b>\n<code>{esc(short(info['no_extra_space']))}</code>\n\n"
        f"<b>حذف خط خالی:</b>\n<code>{esc(short(info['no_empty_lines']))}</code>\n\n"
        f"<b>فقط حروف:</b>\n<code>{esc(short(info['only_letters']))}</code>\n\n"
        f"<b>حذف اعداد:</b>\n<code>{esc(short(info['no_numbers']))}</code>\n\n"
        f"<b>حذف ایموجی:</b>\n<code>{esc(short(info['no_emoji']))}</code>"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_analyze(message, text: str):
    info = analyze_text(text, top_n=10)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    result = (
        f"📊 <b>تحلیل متن</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📝 <b>کل کلمات:</b> {info['total_words']:,}\n"
        f"🔤 <b>کلمات یکتا:</b> {info['unique_words']:,}\n\n"
        f"🏆 <b>پربسامدترین کلمات:</b>\n\n"
    )

    medals = ["🥇", "🥈", "🥉"]
    for i, (word, count) in enumerate(info["top_words"]):
        medal = medals[i] if i < 3 else f"{i+1}."
        # escape
        word_safe = word.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        result += f"{medal} <code>{word_safe}</code> — {count} بار\n"

    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_base64(message, text: str):
    # چک کن آیا Base64 معتبره
    import re
    is_b64 = bool(re.fullmatch(r"[A-Za-z0-9+/=\s]+", text)) and len(text) % 4 == 0 or text.endswith("=")

    result_text = "🔐 <b>Base64</b>\n━━━━━━━━━━━━━━━\n\n"

    # Encode
    enc = base64_encode(text)
    if enc.get("success"):
        result_text += f"<b>Encode:</b>\n<code>{enc['result']}</code>\n\n"

    # Decode (فقط اگه شبیه Base64 باشه)
    if is_b64:
        dec = base64_decode(text)
        if dec.get("success"):
            dec_safe = dec["result"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            result_text += f"<b>Decode:</b>\n<code>{dec_safe}</code>"
        else:
            result_text += f"<b>Decode:</b> ❌ {dec.get('error')}"
    else:
        result_text += "<b>Decode:</b> (متن Base64 نیست)"

    bot.send_message(message.chat.id, result_text, parse_mode='HTML')


def _handle_url(message, text: str):
    enc = url_encode(text)
    dec = url_decode(text)

    result = "🔗 <b>URL Encode/Decode</b>\n━━━━━━━━━━━━━━━\n\n"

    if enc.get("success"):
        result += f"<b>Encode:</b>\n<code>{enc['result']}</code>\n\n"

    if dec.get("success"):
        dec_safe = dec["result"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        result += f"<b>Decode:</b>\n<code>{dec_safe}</code>"

    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_number(message, text: str):
    info = convert_number(text)
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    result = (
        f"🔢 <b>تبدیل عدد</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"<b>دهدهی:</b> <code>{info['decimal']}</code>\n"
        f"<b>باینری:</b> <code>{info['binary']}</code>\n"
        f"<b>اکتال:</b> <code>{info['octal']}</code>\n"
        f"<b>هگز:</b> <code>{info['hex']}</code>"
    )
    bot.send_message(message.chat.id, result, parse_mode='HTML')


def _handle_ascii(message, text: str):
    info = ascii_art(text[:20])  # محدود به ۲۰ کاراکتر
    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error')}")
        return

    # escape برای HTML
    ascii_safe = info["result"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    result = f"🎨 <b>ASCII Art</b> (<code>{info['font']}</code>)\n\n<pre>{ascii_safe}</pre>"
    bot.send_message(message.chat.id, result, parse_mode='HTML')