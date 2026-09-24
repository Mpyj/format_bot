import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.site_info import analyze_site
from utils.qrcode_gen import generate_qr
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🌐 تحلیل سایت')
@check_usage_limit
def site_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="site", waiting_for="site_url", input_path=None)

    bot.send_message(
        message.chat.id,
        "🌐 <b>تحلیل سایت</b>\n\n"
        "یه لینک یا دامنه بفرست تا این اطلاعات رو بگیرم:\n\n"
        "📡 پینگ سرور\n"
        "🔒 گواهی SSL\n"
        "🌍 موقعیت IP\n"
        "📊 وضعیت HTTP\n"
        "⏱ زمان پاسخ\n"
        "📦 اطلاعات سرور\n\n"
        "مثال: <code>google.com</code> یا <code>https://github.com</code>",
        parse_mode='HTML'
    )


# ---------- دریافت لینک ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "site_url"
        and get_state(m.from_user.id).get("mode") == "site"
        and m.text
        and not m.text.startswith("/")
        and not is_menu_button(m.text)
)
def receive_site_url(message):
    user_id = message.from_user.id
    url = message.text.strip()

    if "." not in url and not url.startswith(("http://", "https://")):
        bot.send_message(
            message.chat.id,
            "❌ این آدرس معتبر نیست. یه دامنه مثل <code>google.com</code> بفرست.",
            parse_mode='HTML'
        )
        return

    bot.send_message(message.chat.id, "⏳ در حال تحلیل... (چند ثانیه طول می‌کشه)")

    try:
        result = analyze_site(url)

        if not result.get("success"):
            bot.send_message(
                message.chat.id,
                "❌ نتونستم سایت رو تحلیل کنم. آدرس رو چک کن.",
                reply_markup=main_menu_keyboard(user_id)
            )
            clear_state(user_id)
            return

        text = _format_result(result)

        token = uuid.uuid4().hex[:12]
        set_state(user_id, site_url_token=token, site_url_for_qr=result["url"])

        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton(
                "📱 QR از این لینک",
                callback_data=f"site_qr_{token}"
            )
        )

        bot.send_message(
            message.chat.id,
            text,
            parse_mode='HTML',
            reply_markup=markup
        )

        mark_user_used(user_id)
        set_state(user_id, waiting_for=None)

    except Exception as e:
        logger.exception("خطا در تحلیل سایت")
        bot.send_message(
            message.chat.id,
            f"❌ خطا: {e}",
            reply_markup=main_menu_keyboard(user_id)
        )
        clear_state(user_id)


def _format_result(r: dict) -> str:
    lines = [
        f"🌐 <b>تحلیل {r['host']}</b>",
        "━━━━━━━━━━━━━━━",
    ]

    http = r.get("http", {})
    if http.get("success"):
        status = http["status_code"]
        status_emoji = "✅" if 200 <= status < 300 else ("↪️" if 300 <= status < 400 else "❌")
        lines.append(f"{status_emoji} <b>وضعیت HTTP:</b> {status} {http.get('reason', '')}")

        elapsed = http.get("elapsed_ms", 0)
        if elapsed < 500:
            speed_emoji = "⚡"
        elif elapsed < 1500:
            speed_emoji = "🚀"
        elif elapsed < 3000:
            speed_emoji = "🐢"
        else:
            speed_emoji = "🐌"
        lines.append(f"{speed_emoji} <b>زمان پاسخ:</b> {elapsed:.0f} میلی‌ثانیه")

        if http.get("redirects"):
            lines.append(f"↪️ <b>ریدایرکت‌ها:</b> {http['redirects']}")

        server = http.get("server", "?")
        if server != "?":
            lines.append(f"📦 <b>سرور:</b> <code>{server}</code>")

        size = http.get("content_length", 0)
        if size:
            lines.append(f"📊 <b>حجم پاسخ:</b> {_human_size(size)}")
    else:
        lines.append(f"❌ <b>HTTP:</b> {http.get('message', 'خطا')}")

    lines.append("━━━━━━━━━━━━━━━")

    ip = r.get("ip", {})
    if ip.get("success"):
        lines.append(f"🌍 <b>IP:</b> <code>{ip['ip']}</code>")
        if ip.get("country") != "?":
            lines.append(f"🗺 <b>کشور:</b> {ip.get('country', '?')} — {ip.get('city', '?')}")
        if ip.get("isp") != "?":
            lines.append(f"📡 <b>ISP:</b> {ip.get('isp', '?')}")

    ping = r.get("ping", {})
    if ping.get("success"):
        avg = ping["avg"]
        if avg < 100:
            ping_emoji = "🟢"
        elif avg < 300:
            ping_emoji = "🟡"
        else:
            ping_emoji = "🔴"
        lines.append(
            f"{ping_emoji} <b>پینگ:</b> میانگین {avg:.0f}ms "
            f"(کمترین {ping['min']:.0f} / بیشترین {ping['max']:.0f})"
        )

    lines.append("━━━━━━━━━━━━━━━")

    ssl_info = r.get("ssl", {})
    if ssl_info.get("valid"):
        lines.append(f"🔒 <b>SSL:</b> ✅ معتبر")
        lines.append(f"🏢 <b>صادرکننده:</b> {ssl_info.get('issuer', '?')}")
        lines.append(f"🔐 <b>نسخه TLS:</b> {ssl_info.get('tls_version', '?')}")

        days = ssl_info.get("days_left")
        if days is not None:
            if days < 0:
                lines.append(f"⚠️ <b>گواهی منقضی شده!</b>")
            elif days < 30:
                lines.append(f"⚠️ <b>انقضا:</b> {days} روز دیگه ({ssl_info.get('expire_date', '?')})")
            else:
                lines.append(f"📅 <b>انقضا:</b> {ssl_info.get('expire_date', '?')} ({days} روز دیگه)")
    elif ssl_info.get("success") and not ssl_info.get("valid"):
        lines.append(f"🔓 <b>SSL:</b> ❌ بدون HTTPS / نامعتبر")
    else:
        lines.append(f"🔓 <b>SSL:</b> ❌ نامشخص")

    lines.append("━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _human_size(size: int) -> str:
    if size < 1024:
        return f"{size} بایت"
    elif size < 1024 * 1024:
        return f"{size / 1024:.1f} کیلوبایت"
    else:
        return f"{size / (1024 * 1024):.1f} مگابایت"


# ---------- QR از لینک ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("site_qr_"))
def site_qr(call):
    user_id = call.from_user.id
    state = get_state(user_id)

    token = call.data.replace("site_qr_", "")
    stored_token = state.get("site_url_token")
    url = state.get("site_url_for_qr")

    if not url or token != stored_token:
        bot.answer_callback_query(call.id, "لینک پیدا نشد، دوباره تحلیل کن", show_alert=True)
        return

    bot.answer_callback_query(call.id, "در حال ساخت QR...")
    path = generate_qr(url)

    if path and os.path.exists(path):
        with open(path, "rb") as f:
            bot.send_photo(
                call.message.chat.id,
                f,
                caption=f"📱 <b>QR Code:</b>\n\n<code>{url}</code>",
                parse_mode='HTML'
            )
        delete_file(path)

        bot.send_message(
            call.message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        bot.send_message(call.message.chat.id, "❌ خطا در ساخت QR.")


# ---------- بخش مستقل QR Code ----------
@bot.message_handler(func=lambda m: m.text == '📱 ساخت QR Code')
@check_usage_limit
def qr_tool_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="qr", waiting_for="qr_text", input_path=None)

    bot.send_message(
        message.chat.id,
        "📱 <b>ساخت QR Code</b>\n\n"
        "هر متنی بفرست — لینک، شماره تلفن، ایمیل، وای‌فای، هر چی!\n\n"
        "💡 مثال:\n"
        "• <code>https://google.com</code>\n"
        "• <code>09123456789</code>\n"
        "• <code>test@example.com</code>\n\n"
        "بعدش می‌تونی رنگش رو هم انتخاب کنی 🎨",
        parse_mode='HTML'
    )


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "qr_text"
        and get_state(m.from_user.id).get("mode") == "qr"
        and m.text
        and not m.text.startswith("/")
        and not is_menu_button(m.text)
)
def qr_receive_text(message):
    user_id = message.from_user.id
    text = message.text.strip()

    set_state(user_id, qr_text=text, waiting_for="qr_color_choice")

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("⚫ مشکی (کلاسیک)", callback_data="qrpick_#000000"),
        types.InlineKeyboardButton("🔵 آبی", callback_data="qrpick_#0066FF"),
        types.InlineKeyboardButton("🟢 سبز", callback_data="qrpick_#00AA44"),
        types.InlineKeyboardButton("🔴 قرمز", callback_data="qrpick_#DD0000"),
        types.InlineKeyboardButton("🟣 بنفش", callback_data="qrpick_#8800CC"),
        types.InlineKeyboardButton("🟠 نارنجی", callback_data="qrpick_#FF6600"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="qrpick_cancel"),
    )
    bot.send_message(
        message.chat.id,
        f"✅ متن دریافت شد:\n<code>{_escape(text)}</code>\n\n"
        "🎨 رنگ QR رو انتخاب کن:",
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("qrpick_"))
def qr_pick_color(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    text = state.get("qr_text")

    color_data = call.data.replace("qrpick_", "")

    if color_data == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id,
            call.message.message_id
        )
        bot.send_message(
            call.message.chat.id,
            "منوی اصلی:",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    if not text:
        bot.answer_callback_query(call.id, "متن پیدا نشد!", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال ساخت...")
    path = generate_qr(text, fill_color=color_data, back_color="#FFFFFF")

    if path and os.path.exists(path):
        with open(path, "rb") as f:
            bot.send_photo(
                call.message.chat.id,
                f,
                caption=f"📱 <b>QR Code آماده‌ست!</b>\n\n"
                        f"📝 متن: <code>{_escape(text)}</code>\n"
                        f"🎨 رنگ: <code>{color_data}</code>",
                parse_mode='HTML'
            )
        delete_file(path)
        mark_user_used(user_id)
        clear_state(user_id)

        bot.send_message(
            call.message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard(user_id)
        )
    else:
        bot.send_message(call.message.chat.id, "❌ خطا در ساخت QR.")


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")