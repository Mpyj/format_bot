import logging
from telebot import types

from main import bot
from utils.states import set_state, get_state, clear_state
from utils.network_tools import (
    get_whois, get_dns, scan_ports, test_download_speed, get_ssl_details,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🌐 ابزار شبکه')
@check_usage_limit
def network_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="network", waiting_for=None)

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔍 WHOIS", callback_data="net_op_whois"),
        types.InlineKeyboardButton("📡 DNS", callback_data="net_op_dns"),
    )
    markup.add(
        types.InlineKeyboardButton("🚪 اسکن پورت", callback_data="net_op_ports"),
        types.InlineKeyboardButton("🔒 جزئیات SSL", callback_data="net_op_ssl"),
    )
    markup.add(
        types.InlineKeyboardButton("📶 تست سرعت", callback_data="net_op_speed"),
    )
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="net_op_cancel"))

    bot.send_message(
        message.chat.id,
        "🌐 <b>ابزار شبکه</b>\n\n"
        "🔍 <b>WHOIS</b> — مالک دامنه، تاریخ ثبت، انقضا\n"
        "📡 <b>DNS</b> — A، MX، NS، TXT، ...\n"
        "🚪 <b>اسکن پورت</b> — پورت‌های باز\n"
        "🔒 <b>جزئیات SSL</b> — گواهی و cipher\n"
        "📶 <b>تست سرعت</b> — سرعت دانلود از یه لینک",
        parse_mode='HTML',
        reply_markup=markup
    )


# ---------- انتخاب عملیات ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("net_op_"))
def network_action(call):
    user_id = call.from_user.id
    action = call.data.replace("net_op_", "")

    if action == "cancel":
        clear_state(user_id)
        bot.answer_callback_query(call.id, "لغو شد")
        bot.edit_message_text(
            "❌ عملیات لغو شد.",
            call.message.chat.id, call.message.message_id
        )
        bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))
        return

    bot.answer_callback_query(call.id)

    hints = {
        "whois": "🔍 <b>WHOIS</b>\n\nاسم دامنه رو بفرست:\nمثال: <code>google.com</code>",
        "dns": "📡 <b>DNS Lookup</b>\n\nاسم دامنه رو بفرست:\nمثال: <code>google.com</code>",
        "ports": "🚪 <b>اسکن پورت</b>\n\nاسم دامنه یا IP رو بفرست:\nمثال: <code>google.com</code>",
        "ssl": "🔒 <b>جزئیات SSL</b>\n\nاسم دامنه رو بفرست:\nمثال: <code>google.com</code>",
        "speed": "📶 <b>تست سرعت</b>\n\nیه لینک دانلود بفرست:\nمثال: <code>https://speed.hetzner.de/100MB.bin</code>",
    }

    set_state(user_id, net_action=action, waiting_for=f"net_{action}")
    bot.edit_message_text(
        hints.get(action, "عملیات نامشخص"),
        call.message.chat.id, call.message.message_id,
        parse_mode='HTML'
    )


# ---------- دریافت ورودی ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for", "").startswith("net_")
        and m.text
        and not m.text.startswith("/")
)
def network_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("net_action")
    query = message.text.strip()

    bot.send_message(message.chat.id, "⏳ در حال پردازش...")

    try:
        if action == "whois":
            _show_whois(message, query, user_id)
        elif action == "dns":
            _show_dns(message, query, user_id)
        elif action == "ports":
            _show_ports(message, query, user_id)
        elif action == "ssl":
            _show_ssl(message, query, user_id)
        elif action == "speed":
            _show_speed(message, query, user_id)
        else:
            bot.send_message(message.chat.id, "❌ عملیات نامشخص")

    except Exception as e:
        logger.exception(f"خطا در {action}")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

    finally:
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🔍 WHOIS
# ============================================================
def _show_whois(message, domain: str, user_id: int):
    info = get_whois(domain)

    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error', 'ناشناخته')}")
        return

    text = (
        f"🔍 <b>WHOIS: {info['domain']}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🏢 <b>Registrar:</b> {info['registrar']}\n"
        f"📅 <b>ثبت:</b> {info['creation_date']}\n"
        f"📅 <b>انقضا:</b> {info['expiration_date']}\n"
        f"🔄 <b>آخرین آپدیت:</b> {info['updated_date']}\n"
        f"🌍 <b>کشور:</b> {info['country']}\n"
    )

    if info.get("org") and info["org"] != "—":
        text += f"🏛 <b>سازمان:</b> {info['org']}\n"

    if info.get("name_servers"):
        ns_list = info["name_servers"][:5]
        text += "\n🌐 <b>Name Servers:</b>\n"
        for ns in ns_list:
            text += f"  • <code>{ns}</code>\n"

    if info.get("emails"):
        emails = info["emails"][:3]
        text += "\n📧 <b>ایمیل‌ها:</b>\n"
        for em in emails:
            text += f"  • <code>{em}</code>\n"

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    mark_user_used(user_id)


# ============================================================
# 📡 DNS
# ============================================================
def _show_dns(message, domain: str, user_id: int):
    info = get_dns(domain)

    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error', 'ناشناخته')}")
        return

    text = f"📡 <b>DNS: {info['domain']}</b>\n━━━━━━━━━━━━━━━\n\n"

    for rtype in ["A", "AAAA", "MX", "NS", "TXT", "CNAME"]:
        records = info.get(rtype, [])
        if records:
            text += f"<b>{rtype}:</b>\n"
            for r in records[:5]:
                text += f"  • <code>{r}</code>\n"
            if len(records) > 5:
                text += f"  ... و {len(records) - 5} تا دیگه\n"
            text += "\n"

    if len(text) < 100:
        text += "⚠️ هیچ رکوردی پیدا نشد."

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    mark_user_used(user_id)


# ============================================================
# 🚪 اسکن پورت
# ============================================================
def _show_ports(message, host: str, user_id: int):
    result = scan_ports(host)

    if not result.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {result.get('error', 'ناشناخته')}")
        return

    text = (
        f"🚪 <b>اسکن پورت: {result['host']}</b>\n"
        f"🌐 IP: <code>{result['ip']}</code>\n"
        f"━━━━━━━━━━━━━━━\n\n"
    )

    if result["open_ports"]:
        text += f"✅ <b>{len(result['open_ports'])} پورت باز:</b>\n\n"
        for p in result["open_ports"]:
            text += f"🟢 <b>{p['port']}</b> — {p['service']}\n"
    else:
        text += "🔒 هیچ پورت بازی پیدا نشد."

    text += f"\n\n📊 {result['total_scanned']} پورت اسکن شد."

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    mark_user_used(user_id)


# ============================================================
# 🔒 SSL
# ============================================================
def _show_ssl(message, host: str, user_id: int):
    info = get_ssl_details(host)

    if not info.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {info.get('error', 'ناشناخته')}")
        return

    if not info.get("valid"):
        bot.send_message(
            message.chat.id,
            f"🔓 <b>SSL نامعتبر</b>\n\n{info.get('error', '')}",
            parse_mode='HTML'
        )
        return

    text = (
        f"🔒 <b>SSL: {host}</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"✅ <b>وضعیت:</b> معتبر\n"
        f"🏢 <b>صادرکننده:</b> {info['issuer']}\n"
        f"🔐 <b>CN:</b> {info['issuer_cn']}\n"
        f"🌐 <b>Subject:</b> {info['subject']}\n"
        f"📌 <b>نسخه TLS:</b> {info['tls_version']}\n"
        f"🔑 <b>Cipher:</b> <code>{info['cipher']}</code>\n"
        f"📅 <b>انقضا:</b> {info['expire_date']}\n"
    )

    days = info.get("days_left")
    if days is not None:
        if days < 0:
            text += f"\n⚠️ <b>گواهی منقضی شده!</b>"
        elif days < 30:
            text += f"\n⚠️ <b>{days} روز</b> تا انقضا"
        else:
            text += f"\n🟢 <b>{days} روز</b> تا انقضا"

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    mark_user_used(user_id)


# ============================================================
# 📶 تست سرعت
# ============================================================
def _show_speed(message, url: str, user_id: int):
    result = test_download_speed(url)

    if not result.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {result.get('error', 'ناشناخته')}")
        return

    speed = result["speed_mbps"]
    if speed > 50:
        emoji = "🚀"
        quality = "عالی"
    elif speed > 10:
        emoji = "⚡"
        quality = "خوب"
    elif speed > 2:
        emoji = "👍"
        quality = "متوسط"
    else:
        emoji = "🐢"
        quality = "کند"

    text = (
        f"📶 <b>تست سرعت</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🔗 <b>لینک:</b>\n<code>{url[:80]}...</code>\n\n"
        f"{emoji} <b>سرعت:</b> {speed:.2f} Mbps ({quality})\n"
        f"📥 <b>دانلود شده:</b> {result['downloaded_mb']:.2f} MB\n"
        f"⏱ <b>زمان:</b> {result['elapsed']:.1f} ثانیه\n"
        f"📊 <b>کیلوبایت بر ثانیه:</b> {result['speed_kbps']:.0f} KB/s"
    )

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    mark_user_used(user_id)