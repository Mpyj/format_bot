import os
import time
import logging
from telebot import types

from main import bot
from config import ADMIN_ID, TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.admin_tools import (
    get_general_stats, get_top_users, get_operations_breakdown,
    get_all_user_ids, get_user_info, get_user_info_by_username,
    ban_user, export_users_csv, export_operations_csv,
)
from utils.keyboards import main_menu_keyboard

logger = logging.getLogger(__name__)


# ---------- دسترسی ----------
def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID


# ---------- پنل ادمین ----------
def admin_panel(message, edit: bool = False):
    """
    پنل ادمین.
    - edit=True: پیام فعلی رو ویرایش می‌کنه (برای بازگشت)
    - edit=False: پیام جدید می‌فرسته (برای اولین بار)
    """
    if not is_admin(message.from_user.id):
        return

    text = (
        "👑 <b>پنل ادمین</b>\n\n"
        "خوش آمدی! یه گزینه انتخاب کن:"
    )

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📊 آمار کلی", callback_data="adm_stats"),
        types.InlineKeyboardButton("🏆 کاربران برتر", callback_data="adm_top"),
    )
    markup.add(
        types.InlineKeyboardButton("📈 آمار عملیات", callback_data="adm_ops"),
        types.InlineKeyboardButton("👤 جستجوی کاربر", callback_data="adm_find_user"),
    )
    markup.add(
        types.InlineKeyboardButton("📢 پیام همگانی", callback_data="adm_broadcast"),
        types.InlineKeyboardButton("🚫 بن/آنبن", callback_data="adm_ban"),
    )
    markup.add(
        types.InlineKeyboardButton("📥 CSV کاربران", callback_data="adm_csv_users"),
        types.InlineKeyboardButton("📥 CSV عملیات", callback_data="adm_csv_ops"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="adm_close"))

    if edit:
        try:
            bot.edit_message_text(
                text,
                message.chat.id,
                message.message_id,
                parse_mode='HTML',
                reply_markup=markup
            )
            return
        except Exception as e:
            logger.warning(f"edit نشد، send می‌کنیم: {e}")

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)


# ---------- callback ها ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("adm_"))
def admin_callback(call):
    if not is_admin(call.from_user.id):
        bot.answer_callback_query(call.id, "❌ دسترسی نداری", show_alert=True)
        return

    action = call.data.replace("adm_", "")

    if action == "close":
        bot.answer_callback_query(call.id, "بسته شد")
        try:
            bot.delete_message(call.message.chat.id, call.message.message_id)
        except Exception:
            pass
        return

    if action == "back":
        bot.answer_callback_query(call.id)
        # 👇 ویرایش پیام فعلی به جای پاک کردن + فرستادن جدید
        admin_panel(call.message, edit=True)
        return

    if action == "stats":
        _show_stats(call)
    elif action == "top":
        _show_top(call)
    elif action == "ops":
        _show_ops(call)
    elif action == "find_user":
        bot.answer_callback_query(call.id)
        set_state(call.from_user.id, waiting_for="admin_find_user")
        _edit_with_back(
            call,
            "👤 <b>جستجوی کاربر</b>\n\n"
            "آیدی عددی یا یوزرنیم کاربر رو بفرست:\n\n"
            "💡 مثال:\n"
            "• <code>7144847927</code>\n"
            "• <code>@username</code>\n"
            "• <code>username</code>"
        )
    elif action == "broadcast":
        bot.answer_callback_query(call.id)
        set_state(call.from_user.id, waiting_for="admin_broadcast")
        _edit_with_back(
            call,
            "📢 <b>پیام همگانی</b>\n\n"
            "متن پیام رو بفرست تا به همه کاربرا ارسال بشه.\n\n"
            "⚠️ این کار ممکنه چند دقیقه طول بکشه."
        )
    elif action == "ban":
        bot.answer_callback_query(call.id)
        set_state(call.from_user.id, waiting_for="admin_ban_user")
        _edit_with_back(
            call,
            "🚫 <b>بن/آنبن</b>\n\n"
            "آیدی عددی یا یوزرنیم کاربر رو بفرست:\n\n"
            "💡 مثال:\n"
            "• <code>7144847927</code>\n"
            "• <code>@username</code>"
        )
    elif action == "csv_users":
        _export_csv(call, "users")
    elif action == "csv_ops":
        _export_csv(call, "ops")


def _edit_with_back(call, text: str):
    """ویرایش پیام + دکمه بازگشت"""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))
    try:
        bot.edit_message_text(
            text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode='HTML',
            reply_markup=markup
        )
    except Exception:
        bot.send_message(
            call.message.chat.id, text,
            parse_mode='HTML', reply_markup=markup
        )


def _show_stats(call):
    bot.answer_callback_query(call.id, "در حال محاسبه...")
    try:
        stats = get_general_stats()
        text = (
            "📊 <b>آمار کلی ربات</b>\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"👥 <b>کل کاربران:</b> {stats['total_users']}\n"
            f"🟢 <b>فعال ۲۴ ساعت:</b> {stats['active_24h']}\n"
            f"🟢 <b>فعال ۷ روز:</b> {stats['active_7d']}\n"
            f"🚫 <b>بن شده:</b> {stats['banned_users']}\n\n"
            "━━━━━━━━━━━━━━━\n\n"
            f"⚙️ <b>کل عملیات:</b> {stats['total_ops']}\n"
            f"📅 <b>امروز:</b> {stats['ops_today']}\n"
            f"📅 <b>۷ روز اخیر:</b> {stats['ops_7d']}\n\n"
            f"💾 <b>حجم فایل‌ها:</b> {stats['total_size_mb']:.1f} MB"
        )
        _edit_with_back(call, text)
    except Exception as e:
        logger.exception("خطا در آمار")
        _edit_with_back(call, f"❌ خطا: {e}")


def _show_top(call):
    bot.answer_callback_query(call.id)
    try:
        users = get_top_users(10)
        if not users:
            text = "🏆 هنوز کسی استفاده نکرده."
        else:
            text = "🏆 <b>۱۰ کاربر برتر</b>\n━━━━━━━━━━━━━━━\n\n"
            medals = ["🥇", "🥈", "🥉"]
            for i, (uid, fname, uname, count) in enumerate(users):
                medal = medals[i] if i < 3 else f"{i+1}."
                name = fname or (f"@{uname}" if uname else f"کاربر {uid}")
                text += f"{medal} <b>{name}</b>\n"
                text += f"   └ {count} عملیات\n\n"
        _edit_with_back(call, text)
    except Exception as e:
        logger.exception("خطا در top")
        _edit_with_back(call, f"❌ خطا: {e}")


def _show_ops(call):
    bot.answer_callback_query(call.id)
    try:
        ops = get_operations_breakdown()
        if not ops:
            text = "📈 هنوز عملیاتی ثبت نشده."
        else:
            text = "📈 <b>آمار عملیات</b>\n━━━━━━━━━━━━━━━\n\n"
            for op_type, count in ops:
                name = _op_name_fa(op_type)
                text += f"• <b>{name}</b>: {count}\n"
        _edit_with_back(call, text)
    except Exception as e:
        logger.exception("خطا در ops")
        _edit_with_back(call, f"❌ خطا: {e}")


def _op_name_fa(op_type: str) -> str:
    mapping = {
        "image_convert": "🖼️ تبدیل عکس",
        "ocr": "📄 استخراج متن",
        "zip_create": "🗜️ ساخت ZIP",
        "media_mp3": "🎵 ویدیو به MP3",
        "media_mp3_320": "🎵 MP3 (320k)",
        "media_gif": "🎬 ویدیو به GIF",
        "media_mp4": "📼 تبدیل به MP4",
        "media_webm": "📼 تبدیل به WEBM",
        "media_trim": "✂️ برش",
        "media_reverse": "🔄 برعکس",
        "media_normalize": "📊 نرمالایز",
        "pdf_merge": "🔗 ادغام PDF",
        "pdf_split": "✂️ تقسیم PDF",
        "pdf_lock": "🔒 قفل PDF",
        "pdf_unlock": "🔓 باز کردن قفل",
        "pdf_compress": "📉 فشرده‌سازی PDF",
        "pdf_watermark": "💧 واترمارک PDF",
        "pdf_img2pdf": "📄 عکس به PDF",
    }
    return mapping.get(op_type, op_type)


def _export_csv(call, kind: str):
    bot.answer_callback_query(call.id, "در حال ساخت...")
    try:
        bot.edit_message_text(
            "⏳ در حال ساخت فایل CSV...",
            call.message.chat.id, call.message.message_id
        )
    except Exception:
        pass

    try:
        if kind == "users":
            path = export_users_csv()
        else:
            path = export_operations_csv()

        if path and os.path.exists(path):
            with open(path, "rb") as f:
                bot.send_document(
                    call.message.chat.id, f,
                    caption=f"📥 خروجی CSV ({kind})"
                )
            delete_file(path)
        else:
            bot.send_message(call.message.chat.id, "❌ خطا در ساخت CSV.")
    except Exception as e:
        logger.exception("خطا در CSV")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")

    admin_panel(call.message, edit=True)


# ---------- جستجوی کاربر ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "admin_find_user"
        and is_admin(m.from_user.id)
        and m.text
)
def admin_find_user(message):
    user_id = message.from_user.id
    query = message.text.strip()

    info = _find_user_by_query(query)

    if not info:
        bot.send_message(
            message.chat.id,
            f"❌ کاربری با «{query}» پیدا نشد.\n\n"
            "💡 می‌تونی آیدی عددی یا یوزرنیم بدی."
        )
        clear_state(user_id)
        admin_panel(message)
        return

    text = (
        f"👤 <b>اطلاعات کاربر</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"🆔 <b>آیدی:</b> <code>{info['id']}</code>\n"
        f"📝 <b>اسم:</b> {info['first_name'] or '—'}\n"
        f"🔗 <b>یوزرنیم:</b> @{info['username'] or '—'}\n"
        f"📅 <b>عضویت:</b> {info['joined_at']}\n"
        f"🕐 <b>آخرین فعالیت:</b> {info['last_active']}\n"
        f"⚙️ <b>عملیات:</b> {info['op_count']}\n"
        f"🚫 <b>بن:</b> {'✅ بله' if info['is_banned'] else '❌ خیر'}"
    )

    bot.send_message(message.chat.id, text, parse_mode='HTML')
    clear_state(user_id)
    admin_panel(message)


# ---------- پیام همگانی ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "admin_broadcast"
        and is_admin(m.from_user.id)
        and m.text
)
def admin_broadcast(message):
    user_id = message.from_user.id
    text = message.text

    user_ids = get_all_user_ids()
    total = len(user_ids)

    if total == 0:
        bot.send_message(message.chat.id, "❌ هیچ کاربری نیست.")
        clear_state(user_id)
        return

    status_msg = bot.send_message(
        message.chat.id,
        f"📢 در حال ارسال به {total} کاربر...\n\n"
        f"✅ موفق: 0\n❌ ناموفق: 0"
    )

    success = 0
    failed = 0

    for i, uid in enumerate(user_ids, 1):
        try:
            bot.send_message(
                uid,
                f"📢 <b>پیام از ادمین:</b>\n\n{text}",
                parse_mode='HTML'
            )
            success += 1
        except Exception:
            failed += 1

        if i % 20 == 0 or i == total:
            try:
                bot.edit_message_text(
                    f"📢 در حال ارسال...\n\n"
                    f"📊 پیشرفت: {i}/{total}\n"
                    f"✅ موفق: {success}\n"
                    f"❌ ناموفق: {failed}",
                    message.chat.id, status_msg.message_id
                )
            except Exception:
                pass

        time.sleep(0.05)

    bot.edit_message_text(
        f"✅ <b>ارسال تموم شد!</b>\n\n"
        f"📊 کل: {total}\n"
        f"✅ موفق: {success}\n"
        f"❌ ناموفق: {failed}",
        message.chat.id, status_msg.message_id,
        parse_mode='HTML'
    )
    clear_state(user_id)
    admin_panel(message)


# ---------- بن/آنبن ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "admin_ban_user"
        and is_admin(m.from_user.id)
        and m.text
)
def admin_ban(message):
    user_id = message.from_user.id
    query = message.text.strip()

    info = _find_user_by_query(query)

    if not info:
        bot.send_message(
            message.chat.id,
            f"❌ کاربری با «{query}» پیدا نشد."
        )
        clear_state(user_id)
        admin_panel(message)
        return

    target_id = info["id"]
    markup = types.InlineKeyboardMarkup(row_width=2)
    if info["is_banned"]:
        markup.add(types.InlineKeyboardButton(
            "✅ آنبن کن", callback_data=f"adm_unban_{target_id}"
        ))
    else:
        markup.add(types.InlineKeyboardButton(
            "🚫 بن کن", callback_data=f"adm_doban_{target_id}"
        ))
    markup.add(types.InlineKeyboardButton("🔙 بازگشت", callback_data="adm_back"))

    bot.send_message(
        message.chat.id,
        f"👤 <b>{info['first_name'] or target_id}</b>\n"
        f"🔗 @{info['username'] or '—'}\n"
        f"وضعیت: {'🚫 بن' if info['is_banned'] else '✅ فعال'}\n\n"
        f"چیکار کنم؟",
        parse_mode='HTML',
        reply_markup=markup
    )
    clear_state(user_id)


@bot.callback_query_handler(
    func=lambda c: c.data.startswith("adm_doban_") or c.data.startswith("adm_unban_")
)
def admin_do_ban(call):
    if not is_admin(call.from_user.id):
        return

    if call.data.startswith("adm_doban_"):
        target_id = int(call.data.replace("adm_doban_", ""))
        success = ban_user(target_id, True)
        action = "بن"
    else:
        target_id = int(call.data.replace("adm_unban_", ""))
        success = ban_user(target_id, False)
        action = "آنبن"

    if success:
        bot.answer_callback_query(call.id, f"✅ کاربر {action} شد")
        try:
            bot.edit_message_text(
                f"✅ کاربر <code>{target_id}</code> با موفقیت {action} شد.",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML'
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                f"✅ کاربر <code>{target_id}</code> با موفقیت {action} شد.",
                parse_mode='HTML'
            )
    else:
        bot.answer_callback_query(call.id, "❌ خطا", show_alert=True)


# ---------- تابع کمکی ----------
def _find_user_by_query(query: str) -> dict | None:
    query = query.strip()

    if query.startswith("@"):
        query = query[1:]

    if query.isdigit():
        return get_user_info(int(query))

    return get_user_info_by_username(query)