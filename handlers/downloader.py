import os
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.downloader import (
    get_info, download_video, download_audio, download_soundcloud,
    human_size, format_duration,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منو
# ============================================================
def _downloader_menu(user_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎬 یوتیوب", callback_data="dl_youtube"),
        types.InlineKeyboardButton("📷 اینستاگرام", callback_data="dl_instagram"),
    )
    markup.add(
        types.InlineKeyboardButton("🎵 تیک‌تاک", callback_data="dl_tiktok"),
        types.InlineKeyboardButton("🐦 توییتر (X)", callback_data="dl_twitter"),
    )
    markup.add(
        types.InlineKeyboardButton("🎧 SoundCloud", callback_data="dl_soundcloud"),
        types.InlineKeyboardButton("📘 فیسبوک", callback_data="dl_facebook"),
    )
    markup.add(
        types.InlineKeyboardButton("🎥 Vimeo", callback_data="dl_vimeo"),
        types.InlineKeyboardButton("📌 Pinterest", callback_data="dl_pinterest"),
    )
    markup.add(
        types.InlineKeyboardButton("🔗 هر لینک دیگه", callback_data="dl_auto"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="dl_close"))
    return markup


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '📥 دانلودر')
def downloader_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="downloader", waiting_for=None)

    bot.send_message(
        message.chat.id,
        "📥 <b>دانلودر</b>\n\n"
        "لینک از کدوم پلتفرم؟\n\n"
        "🎬 یوتیوب — 📷 اینستاگرام\n"
        "🎵 تیک‌تاک — 🐦 توییتر (X)\n"
        "🎧 SoundCloud — 📘 فیسبوک\n"
        "🎥 Vimeo — 📌 Pinterest\n\n"
        "💡 حداکثر حجم: ۴۸ مگابایت",
        parse_mode='HTML',
        reply_markup=_downloader_menu(user_id)
    )


# ============================================================
# callback
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("dl_"))
def dl_action(call):
    user_id = call.from_user.id
    action = call.data.replace("dl_", "")

    # 🔙 back
    if action == "back":
        bot.answer_callback_query(call.id)
        clear_state(user_id)
        set_state(user_id, mode="downloader", waiting_for=None)
        try:
            bot.edit_message_text(
                "📥 <b>دانلودر</b>\n\nلینک از کدوم پلتفرم؟",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_downloader_menu(user_id)
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "📥 <b>دانلودر</b>",
                parse_mode='HTML', reply_markup=_downloader_menu(user_id)
            )
        return

    # ❌ بستن
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

    hints = {
        "youtube": "🎬 <b>یوتیوب</b>\n\nلینک ویدیو رو بفرست:",
        "instagram": "📷 <b>اینستاگرام</b>\n\nلینک پست/رئیلز رو بفرست:",
        "tiktok": "🎵 <b>تیک‌تاک</b>\n\nلینک ویدیو رو بفرست:",
        "twitter": "🐦 <b>توییتر (X)</b>\n\nلینک توییت رو بفرست:",
        "soundcloud": "🎧 <b>SoundCloud</b>\n\nلینک آهنگ رو بفرست:",
        "facebook": "📘 <b>فیسبوک</b>\n\nلینک ویدیو رو بفرست:",
        "vimeo": "🎥 <b>Vimeo</b>\n\nلینک ویدیو رو بفرست:",
        "pinterest": "📌 <b>Pinterest</b>\n\nلینک پین رو بفرست:",
        "auto": "🔗 <b>هر لینک</b>\n\nلینک رو بفرست:",
    }

    set_state(user_id, mode="downloader", dl_platform=action,
              waiting_for="dl_url")

    try:
        bot.edit_message_text(
            hints.get(action, "لینک رو بفرست:"),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="dl_back"),
            )
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            hints.get(action, "لینک رو بفرست:"),
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="dl_back"),
            )
        )


# ============================================================
# دریافت لینک
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "dl_url"
        and get_state(m.from_user.id).get("mode") == "downloader"
        and m.text
        and not is_menu_button(m.text)
)
def dl_receive_url(message):
    user_id = message.from_user.id
    url = message.text.strip()

    if not url.startswith(("http://", "https://")):
        bot.send_message(
            message.chat.id,
            "❌ لینک معتبر نیست. باید با http یا https شروع بشه."
        )
        return

    set_state(user_id, dl_url=url, waiting_for="dl_quality")

    bot.send_message(message.chat.id, "⏳ در حال دریافت اطلاعات...")

    info = get_info(url)

    if not info.get("success"):
        bot.send_message(
            message.chat.id,
            f"❌ {info.get('error', 'نتونستم اطلاعات بگیرم')}\n\n"
            f"💡 ممکنه:\n"
            f"• لینک اشتباه باشه\n"
            f"• پلتفرم پشتیبانی نشه",
            reply_markup=main_menu_keyboard(user_id)
        )
        clear_state(user_id)
        return

    text = (
        f"📊 <b>اطلاعات</b>\n"
        f"━━━━━━━━━━━━━━━\n\n"
        f"📌 <b>عنوان:</b> {info['title'][:100]}\n"
        f"👤 <b>سازنده:</b> {info['uploader']}\n"
        f"⏱ <b>مدت:</b> {format_duration(info['duration'])}\n"
        f"🌐 <b>پلتفرم:</b> {info['extractor']}\n"
    )

    if info.get("view_count"):
        text += f"👁 <b>بازدید:</b> {info['view_count']:,}\n"
    if info.get("like_count"):
        text += f"👍 <b>لایک:</b> {info['like_count']:,}\n"

    text += f"\n✅ چیکار کنم؟"

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🎬 ویدیو 360p", callback_data="dlq_360"),
        types.InlineKeyboardButton("🎬 ویدیو 480p", callback_data="dlq_480"),
    )
    markup.add(
        types.InlineKeyboardButton("🎬 ویدیو 720p", callback_data="dlq_720"),
        types.InlineKeyboardButton("🎬 ویدیو 1080p", callback_data="dlq_1080"),
    )
    markup.add(
        types.InlineKeyboardButton("🎵 فقط صدا (MP3)", callback_data="dlq_audio"),
    )
    markup.add(
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="dl_back"),
    )

    bot.send_message(message.chat.id, text, parse_mode='HTML', reply_markup=markup)


# ============================================================
# انتخاب کیفیت
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("dlq_"))
def dl_quality_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    url = state.get("dl_url")
    quality = call.data.replace("dlq_", "")

    if not url:
        bot.answer_callback_query(call.id, "لینک پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "شروع دانلود...")

    is_soundcloud = "soundcloud.com" in url.lower()

    # 🎧 SoundCloud
    if is_soundcloud:
        bot.edit_message_text(
            "⏳ در حال دانلود از SoundCloud...\n\n"
            "ممکنه چند ثانیه طول بکشه.",
            call.message.chat.id, call.message.message_id
        )
        output = download_soundcloud(url)

    # 🎵 فقط صدا
    elif quality == "audio":
        bot.edit_message_text(
            "⏳ در حال دانلود صدا (MP3)...",
            call.message.chat.id, call.message.message_id
        )
        output = download_audio(url)

    # 🎬 ویدیو
    else:
        bot.edit_message_text(
            f"⏳ در حال دانلود ویدیو ({quality}p)...",
            call.message.chat.id, call.message.message_id
        )
        output = download_video(url, quality)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        size_str = human_size(size)
        ext = os.path.splitext(output)[1].lstrip(".").lower()

        try:
            with open(output, "rb") as f:
                if ext in ("mp3", "m4a", "wav", "ogg"):
                    bot.send_audio(
                        call.message.chat.id, f,
                        caption=f"🎵 <b>دانلود شد</b>\n📊 حجم: {size_str}",
                        parse_mode='HTML'
                    )
                else:
                    bot.send_video(
                        call.message.chat.id, f,
                        caption=f"🎬 <b>دانلود شد</b>\n📊 حجم: {size_str}",
                        parse_mode='HTML',
                        supports_streaming=True,
                    )

            mark_user_used(user_id)
        except Exception as e:
            logger.exception("خطا در ارسال")
            bot.send_message(call.message.chat.id, f"❌ خطا در ارسال: {e}")
    else:
        bot.send_message(
            call.message.chat.id,
            "❌ دانلود ناموفق بود.\n\n"
            "💡 دلایل احتمالی:\n"
            "• حجم فایل > ۴۸MB\n"
            "• لینک خصوصی/حذف شده\n"
            "• مشکل موقت در سرویس",
            reply_markup=main_menu_keyboard(user_id)
        )

    delete_file(output)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))