import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.song_recognition import recognize_song
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '🎵 تشخیص آهنگ')
def song_rec_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="song_rec", waiting_for="song_audio")

    bot.send_message(
        message.chat.id,
        "🎵 <b>تشخیص آهنگ</b>\n\n"
        "یه فایل صوتی یا ویدیو بفرست تا آهنگش رو تشخیص بدم.\n\n"
        "🎤 از Shazam استفاده می‌کنم.\n\n"
        "💡 بهترین نتیجه با ۱۰-۳۰ ثانیه از آهنگ.",
        parse_mode='HTML'
    )


# ============================================================
# دریافت فایل
# ============================================================
@bot.message_handler(
    content_types=['audio', 'voice', 'video', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "song_audio"
        and get_state(m.from_user.id).get("mode") == "song_rec"
)
def song_receive_audio(message):
    user_id = message.from_user.id
    path = None

    try:
        if message.content_type == 'audio':
            file_info_tg = bot.get_file(message.audio.file_id)
            ext = ".mp3"
        elif message.content_type == 'voice':
            file_info_tg = bot.get_file(message.voice.file_id)
            ext = ".ogg"
        elif message.content_type == 'video':
            file_info_tg = bot.get_file(message.video.file_id)
            ext = ".mp4"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            ext = os.path.splitext(file_info_tg.file_path)[1] or ".mp3"

        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "🔍 در حال تشخیص آهنگ... (چند ثانیه)")

        result = recognize_song(path)

        if result.get("success"):
            text = (
                f"🎵 <b>آهنگ پیدا شد!</b>\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"🎼 <b>نام:</b> {result['title']}\n"
                f"🎤 <b>خواننده:</b> {result['artist']}\n"
            )
            if result.get("album") and result["album"] != "?":
                text += f"💿 <b>آلبوم:</b> {result['album']}\n"
            if result.get("year") and result["year"] != "?":
                text += f"📅 <b>سال:</b> {result['year']}\n"
            if result.get("genre") and result["genre"] != "?":
                text += f"🎨 <b>سبک:</b> {result['genre']}\n"
            if result.get("url"):
                text += f"\n🔗 <a href='{result['url']}'>مشاهده در Shazam</a>"

            # ارسال با کاور
            if result.get("cover"):
                try:
                    bot.send_photo(
                        message.chat.id,
                        result["cover"],
                        caption=text,
                        parse_mode='HTML'
                    )
                except Exception:
                    bot.send_message(message.chat.id, text, parse_mode='HTML')
            else:
                bot.send_message(message.chat.id, text, parse_mode='HTML')

            mark_user_used(user_id)
        else:
            bot.send_message(
                message.chat.id,
                f"❌ {result.get('error', 'تشخیص ناموفق بود')}\n\n"
                f"💡 دلایل احتمالی:\n"
                f"• آهنگ ناشناخته\n"
                f"• کیفیت پایین\n"
                f"• سرور Shazam در دسترس نیست",
                reply_markup=main_menu_keyboard(user_id)
            )

    except Exception as e:
        logger.exception("خطا در تشخیص آهنگ")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

    finally:
        if path:
            delete_file(path)
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))