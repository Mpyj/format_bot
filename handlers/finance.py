import logging
from telebot import types

from main import bot
from utils.states import set_state, get_state, clear_state
from utils.finance_tools import (
    get_crypto_price, get_global_rates, get_iran_rates,
    convert_date, calculate, CRYPTO_NAMES, CURRENCY_NAMES,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منوی اصلی ابزار مالی
# ============================================================
def _main_finance_menu(user_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("💵 ارز دیجیتال", callback_data="fin_op_crypto"),
        types.InlineKeyboardButton("💱 نرخ ارز", callback_data="fin_op_rates"),
    )
    markup.add(
        types.InlineKeyboardButton("🥇 طلا و سکه", callback_data="fin_op_iran"),
        types.InlineKeyboardButton("📅 تبدیل تاریخ", callback_data="fin_op_date"),
    )
    markup.add(
        types.InlineKeyboardButton("🧮 ماشین حساب", callback_data="fin_op_calc"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="fin_op_close"))
    return markup


def _back_button_markup(callback_data: str = "fin_back"):
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data=callback_data))
    return markup


# ---------- شروع (بدون محدودیت) ----------
@bot.message_handler(func=lambda m: m.text == '💰 ابزار مالی')
def finance_start(message):
    user_id = message.from_user.id

    # 👇 اول کل state رو پاک کن
    clear_state(user_id)
    set_state(user_id, mode="finance", waiting_for=None)

    bot.send_message(
        message.chat.id,
        "💰 <b>ابزار مالی</b>\n\n"
        "💵 <b>ارز دیجیتال</b> — BTC، ETH، USDT و ...\n"
        "💱 <b>نرخ ارز</b> — دلار، یورو، پوند (دلاری و تومانی)\n"
        "🥇 <b>طلا و سکه</b> — طلای ۱۸ عیار، سکه امامی\n"
        "📅 <b>تبدیل تاریخ</b> — شمسی ↔ میلادی ↔ قمری\n"
        "🧮 <b>ماشین حساب</b> — محاسبات ریاضی",
        parse_mode='HTML',
        reply_markup=_main_finance_menu(user_id)
    )


# ============================================================
# 🔙 بازگشت به منوی اصلی ابزار مالی
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data == "fin_back")
def finance_back(call):
    user_id = call.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="finance", waiting_for=None)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "💰 <b>ابزار مالی</b>\n\n"
            "💵 <b>ارز دیجیتال</b> — BTC، ETH، USDT و ...\n"
            "💱 <b>نرخ ارز</b> — دلار، یورو، پوند (دلاری و تومانی)\n"
            "🥇 <b>طلا و سکه</b> — طلای ۱۸ عیار، سکه امامی\n"
            "📅 <b>تبدیل تاریخ</b> — شمسی ↔ میلادی ↔ قمری\n"
            "🧮 <b>ماشین حساب</b> — محاسبات ریاضی",
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_main_finance_menu(user_id)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "💰 <b>ابزار مالی</b>",
            parse_mode='HTML', reply_markup=_main_finance_menu(user_id)
        )


# ============================================================
# انتخاب عملیات
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("fin_op_"))
def finance_action(call):
    user_id = call.from_user.id
    action = call.data.replace("fin_op_", "")

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

    if action == "crypto":
        _crypto_menu(call, user_id)
    elif action == "rates":
        _rates_menu(call, user_id)
    elif action == "iran":
        _show_iran(call, user_id)
    elif action == "date":
        set_state(user_id, mode="finance", waiting_for="fin_date")
        try:
            bot.edit_message_text(
                "📅 <b>تبدیل تاریخ</b>\n\n"
                "تاریخ رو بفرست:\n\n"
                "💡 مثال:\n"
                "• <code>1403/06/15</code> (شمسی)\n"
                "• <code>2024-09-05</code> (میلادی)",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_button_markup()
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "📅 <b>تبدیل تاریخ</b>\n\nتاریخ رو بفرست:",
                parse_mode='HTML', reply_markup=_back_button_markup()
            )
    elif action == "calc":
        set_state(user_id, mode="finance", waiting_for="fin_calc")
        try:
            bot.edit_message_text(
                "🧮 <b>ماشین حساب</b>\n\n"
                "عبارت ریاضی رو بفرست:\n\n"
                "💡 مثال: <code>25 * 4 + 100</code>",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_back_button_markup()
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "🧮 <b>ماشین حساب</b>\n\nعبارت ریاضی رو بفرست:",
                parse_mode='HTML', reply_markup=_back_button_markup()
            )


# ============================================================
# 💵 ارز دیجیتال
# ============================================================
def _crypto_menu(call, user_id: int):
    set_state(user_id, mode="finance", waiting_for="fin_crypto")

    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = [
        types.InlineKeyboardButton(name, callback_data=f"crypto_{sym}")
        for sym, (_, name, _) in CRYPTO_NAMES.items()
    ]
    markup.add(*buttons)
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="fin_back"))

    try:
        bot.edit_message_text(
            "💵 <b>ارز دیجیتال</b>\n\nیه ارز انتخاب کن:",
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "💵 <b>ارز دیجیتال</b>\n\nیه ارز انتخاب کن:",
            parse_mode='HTML', reply_markup=markup
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("crypto_"))
def crypto_chosen(call):
    user_id = call.from_user.id
    symbol = call.data.replace("crypto_", "")

    bot.answer_callback_query(call.id, "در حال دریافت...")

    info = get_crypto_price(symbol)

    if not info.get("success"):
        try:
            bot.edit_message_text(
                f"❌ خطا: {info.get('error', 'ناشناخته')}",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup("fin_back_crypto")
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                f"❌ خطا: {info.get('error', 'ناشناخته')}"
            )
        return

    change = info["change_24h"]
    if change > 0:
        change_emoji = "🟢"
        change_str = f"+{change:.2f}%"
    elif change < 0:
        change_emoji = "🔴"
        change_str = f"{change:.2f}%"
    else:
        change_emoji = "⚪"
        change_str = "0%"

    text = (
        f"💵 <b>{info['name']} ({info['ticker']})</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💰 <b>قیمت:</b> ${info['price_usd']:,.2f}\n"
    )

    if info.get("price_irr"):
        text += f"🇮🇷 <b>تومانی:</b> {info['price_irr']:,} تومان\n"

    text += (
        f"{change_emoji} <b>تغییر ۲۴ساعت:</b> {change_str}\n"
        f"📊 <b>حجم ۲۴ساعت:</b> ${info['volume_24h']:,.0f}\n\n"
        f"🕐 آخرین آپدیت: {info['updated']}"
    )

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=_back_button_markup("fin_back_crypto")
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    mark_user_used(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "fin_back_crypto")
def back_to_crypto(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    _crypto_menu(call, user_id)


# ============================================================
# 💱 نرخ ارز
# ============================================================
def _rates_menu(call, user_id: int):
    set_state(user_id, mode="finance", waiting_for="rates_base")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🌍 بر اساس دلار", callback_data="ratesbase_usd"),
        types.InlineKeyboardButton("🇮🇷 بر اساس تومان", callback_data="ratesbase_irr"),
    )
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="fin_back"))

    try:
        bot.edit_message_text(
            "💱 <b>نرخ ارز</b>\n\nنرخ‌ها رو بر اساس چی می‌خوای؟",
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "💱 <b>نرخ ارز</b>\n\nنرخ‌ها رو بر اساس چی می‌خوای؟",
            parse_mode='HTML', reply_markup=markup
        )


@bot.callback_query_handler(func=lambda c: c.data.startswith("ratesbase_"))
def rates_base_chosen(call):
    user_id = call.from_user.id
    mode = call.data.replace("ratesbase_", "")

    bot.answer_callback_query(call.id, "در حال دریافت...")

    if mode == "usd":
        _show_rates_usd(call, user_id)
    else:
        _show_rates_irr(call, user_id)


def _show_rates_usd(call, user_id: int):
    info = get_global_rates("USD")

    if not info.get("success"):
        try:
            bot.edit_message_text(
                f"❌ خطا: {info.get('error', 'ناشناخته')}",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup("fin_back_rates")
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                f"❌ خطا: {info.get('error', 'ناشناخته')}"
            )
        return

    text = "💱 <b>نرخ ارز (نسبت به دلار)</b>\n━━━━━━━━━━━━━━━\n\n"

    for code in ["EUR", "GBP", "AED", "TRY", "CNY", "RUB", "CAD", "AUD", "JPY"]:
        rate = info["rates"].get(code)
        if rate:
            name = CURRENCY_NAMES.get(code, code)
            text += f"{name}: <code>{rate:.4f}</code>\n"

    text += f"\n🕐 {info.get('updated', '')}"

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=_back_button_markup("fin_back_rates")
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    mark_user_used(user_id)


def _show_rates_irr(call, user_id: int):
    iran_info = get_iran_rates()
    if not iran_info.get("success"):
        try:
            bot.edit_message_text(
                "❌ خطا در دریافت نرخ دلار.\n"
                "سرورهای ایرانی موقتاً در دسترس نیستن.\n\n"
                "💡 دوباره تلاش کن.",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup("fin_back_rates")
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ خطا در دریافت نرخ دلار. دوباره تلاش کن."
            )
        return

    usd_rate = iran_info["data"].get("دلار")
    if not usd_rate:
        try:
            bot.edit_message_text(
                "❌ نرخ دلار از سرور دریافت نشد. دوباره تلاش کن.",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup("fin_back_rates")
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ نرخ دلار از سرور دریافت نشد."
            )
        return

    global_info = get_global_rates("USD")
    if not global_info.get("success"):
        try:
            bot.edit_message_text(
                f"❌ خطا در دریافت نرخ جهانی: {global_info.get('error', 'ناشناخته')}",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup("fin_back_rates")
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "❌ خطا در نرخ جهانی"
            )
        return

    rates = global_info["rates"]

    text = (
        f"💱 <b>نرخ ارز (به تومان)</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"💵 <b>دلار پایه:</b> {usd_rate:,} تومان\n\n"
    )

    for code in ["EUR", "GBP", "AED", "TRY", "CNY", "RUB", "CAD", "AUD", "JPY"]:
        rate_vs_usd = rates.get(code)
        if rate_vs_usd:
            toman_price = usd_rate / rate_vs_usd
            name = CURRENCY_NAMES.get(code, code)
            text += f"{name}: <code>{toman_price:,.0f}</code> تومان\n"

    text += f"\n🕐 {iran_info.get('updated', '')}"

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=_back_button_markup("fin_back_rates")
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    mark_user_used(user_id)


@bot.callback_query_handler(func=lambda c: c.data == "fin_back_rates")
def back_to_rates(call):
    user_id = call.from_user.id
    bot.answer_callback_query(call.id)
    _rates_menu(call, user_id)


# ============================================================
# 🥇 طلا و سکه
# ============================================================
def _show_iran(call, user_id: int):
    bot.answer_callback_query(call.id, "در حال دریافت...")

    info = get_iran_rates()

    if not info.get("success"):
        try:
            bot.edit_message_text(
                f"❌ خطا: {info.get('error', 'ناشناخته')}\n\n"
                f"سرورهای ایرانی موقتاً در دسترس نیستن. دوباره تلاش کن.",
                call.message.chat.id, call.message.message_id,
                reply_markup=_back_button_markup()
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                f"❌ خطا: {info.get('error', 'ناشناخته')}"
            )
        return

    data = info["data"]
    text = "🥇 <b>قیمت طلا و سکه (تومان)</b>\n━━━━━━━━━━━━━━━\n\n"

    for name, price in data.items():
        if isinstance(price, int):
            text += f"• <b>{name}:</b> {price:,}\n"
        else:
            text += f"• <b>{name}:</b> {price}\n"

    text += f"\n🕐 {info.get('updated', '')}"

    try:
        bot.edit_message_text(
            text,
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=_back_button_markup()
        )
    except Exception:
        bot.send_message(call.message.chat.id, text, parse_mode='HTML')

    mark_user_used(user_id)


# ============================================================
# 📅 تبدیل تاریخ
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "fin_date"
        and get_state(m.from_user.id).get("mode") == "finance"
        and m.text
)
def date_receive(message):
    user_id = message.from_user.id
    info = convert_date(message.text.strip())

    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error', 'ناشناخته')}")
    else:
        text = (
            f"📅 <b>تبدیل تاریخ</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"🇮🇷 <b>شمسی:</b> <code>{info['jalali']}</code>\n"
            f"🌍 <b>میلادی:</b> <code>{info['gregorian']}</code>\n"
            f"🌙 <b>قمری:</b> <code>{info['hijri']}</code>\n"
            f"📆 <b>روز هفته:</b> {info['weekday']}"
        )
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        mark_user_used(user_id)

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🧮 ماشین حساب
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "fin_calc"
        and get_state(m.from_user.id).get("mode") == "finance"
        and m.text
)
def calc_receive(message):
    user_id = message.from_user.id
    info = calculate(message.text.strip())

    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error', 'ناشناخته')}")
    else:
        text = (
            f"🧮 <b>ماشین حساب</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📝 <b>عبارت:</b> <code>{info['expression']}</code>\n"
            f"✅ <b>نتیجه:</b> <code>{info['result']}</code>"
        )
        bot.send_message(message.chat.id, text, parse_mode='HTML')
        mark_user_used(user_id)

    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))