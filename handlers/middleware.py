import logging
from telebot import types
from telebot.apihelper import ApiTelegramException
from main import bot
from config import CHANNEL_ID, CHANNEL_LINK
from utils.admin_tools import (
    is_user_banned, register_user, update_last_active
)

logger = logging.getLogger(__name__)

# 📊 دیتابیس ساده در حافظه برای محدودیت استفاده
_user_usage = {}


def is_subscribed(chat_id: int, user_id: int) -> bool:
    """چک می‌کنه کاربر عضو کانال هست یا نه"""
    try:
        member = bot.get_chat_member(chat_id, user_id)
        return member.status in ('creator', 'administrator', 'member')
    except ApiTelegramException as e:
        desc = (e.description or "").lower()
        if 'user not found' in desc:
            return False
        if 'chat not found' in desc or 'bot is not a member' in desc:
            logger.error(f"❌ بات ادمین کانال {chat_id} نیست یا کانال پیدا نشد!")
            return False
        logger.exception(f"خطا در چک عضویت: {e}")
        return False
    except Exception as e:
        logger.exception(f"خطای غیرمنتظره در چک عضویت: {e}")
        return False


def send_join_message(chat_id: int):
    """پیام عضویت در کانال رو با دکمه می‌فرسته"""
    markup = types.InlineKeyboardMarkup()
    markup.add(
        types.InlineKeyboardButton("📢 عضویت در کانال", url=CHANNEL_LINK),
        types.InlineKeyboardButton("✅ عضو شدم", callback_data="check_sub")
    )
    bot.send_message(
        chat_id,
        "⚠️ <b>دسترسی محدود</b>\n\n"
        "شما قبلاً از قابلیت‌های ربات استفاده کرده‌اید.\n"
        "برای استفاده مجدد، لطفاً عضو کانال ما شوید:\n\n"
        f"👉 {CHANNEL_LINK}",
        parse_mode='HTML',
        reply_markup=markup
    )


def mark_user_used(user_id: int):
    """علامت‌گذاری که کاربر از قابلیت استفاده کرده"""
    _user_usage[user_id] = True


def check_usage_limit(func):
    """
    دکوراتور محدودیت استفاده.
    - چک بن
    - ثبت کاربر
    - چک عضویت کانال
    """
    def wrapper(message, *args, **kwargs):
        user_id = message.from_user.id

        # ۱) ثبت کاربر جدید
        try:
            register_user(
                user_id,
                message.from_user.first_name or "",
                message.from_user.username or ""
            )
        except Exception as e:
            logger.warning(f"خطا در ثبت کاربر: {e}")

        # ۲) آپدیت last_active
        try:
            update_last_active(user_id)
        except Exception:
            pass

        # ۳) چک بن
        if is_user_banned(user_id):
            bot.send_message(
                message.chat.id,
                "🚫 <b>شما از ربات مسدود شده‌اید.</b>\n\n"
                "اگه فکر می‌کنی اشتباه شده، با ادمین تماس بگیر.",
                parse_mode='HTML'
            )
            return

        # ۴) چک عضویت کانال
        if _user_usage.get(user_id, False) and not is_subscribed(CHANNEL_ID, user_id):
            send_join_message(message.chat.id)
            return

        if is_subscribed(CHANNEL_ID, user_id):
            _user_usage[user_id] = False

        return func(message, *args, **kwargs)
    return wrapper


# ✅ هندلر برای دکمه «عضو شدم»
@bot.callback_query_handler(func=lambda c: c.data == "check_sub")
def check_sub_callback(call):
    user_id = call.from_user.id
    if is_subscribed(CHANNEL_ID, user_id):
        bot.answer_callback_query(call.id, "✅ عضویت تایید شد!")
        _user_usage[user_id] = False
        bot.edit_message_text(
            "✅ عضویت شما تایید شد.\nالان می‌تونید از قابلیت‌ها استفاده کنید.",
            call.message.chat.id,
            call.message.message_id
        )
    else:
        bot.answer_callback_query(call.id, "❌ هنوز عضو نشدی!", show_alert=True)