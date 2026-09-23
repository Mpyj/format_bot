import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.file_info import human_size
from utils.media_tools import (
    video_to_mp3, video_to_gif, video_to_format,
    audio_to_format, trim_media, get_media_info, format_duration,
    change_speed, reverse_media, normalize_audio, change_pitch,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🎵 مبدل مدیا')
@check_usage_limit
def media_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="media", waiting_for="media_file", input_path=None)

    bot.send_message(
        message.chat.id,
        "🎵 <b>مبدل مدیا</b>\n\n"
        "یه ویدیو یا فایل صوتی بفرست تا:\n\n"
        "🎵 به MP3 تبدیل کنم\n"
        "🎬 به GIF تبدیل کنم\n"
        "📼 فرمتش رو عوض کنم\n"
        "✂️ برشش بدم\n"
        "🎚 سرعتش رو عوض کنم\n"
        "🔄 برعکسش کنم\n"
        "📊 نرمالایزش کنم\n\n"
        "⚠️ حداکثر حجم: ۲۰ مگابایت\n"
        "⏱ حداکثر زمان پردازش: ۲ دقیقه",
        parse_mode='HTML'
    )


# ---------- دریافت فایل ----------
@bot.message_handler(
    content_types=['video', 'audio', 'voice', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "media_file"
)
def media_receive(message):
    user_id = message.from_user.id

    try:
        # 🎯 تشخیص نوع فایل بر اساس content_type تلگرام
        if message.content_type == 'video':
            file_info_tg = bot.get_file(message.video.file_id)
            original_name = message.video.file_name or f"video_{uuid.uuid4().hex[:6]}.mp4"
            media_type = "video"

        elif message.content_type == 'audio':
            # 🎵 آهنگ — همیشه صوت در نظر بگیر
            file_info_tg = bot.get_file(message.audio.file_id)
            original_name = message.audio.file_name or f"audio_{uuid.uuid4().hex[:6]}.mp3"
            media_type = "audio"

        elif message.content_type == 'voice':
            file_info_tg = bot.get_file(message.voice.file_id)
            original_name = f"voice_{uuid.uuid4().hex[:6]}.ogg"
            media_type = "audio"

        else:  # document
            file_info_tg = bot.get_file(message.document.file_id)
            original_name = message.document.file_name or f"file_{uuid.uuid4().hex[:6]}"
            media_type = "unknown"

        # ذخیره
        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(original_name)[1] or ".mp4"
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        size = os.path.getsize(path)
        media_info = get_media_info(path)

        # 🎯 اگه از تلگرام آهنگ اومد، حتی اگه کاور داشت، فقط صوت در نظر بگیر
        if media_type == "audio":
            media_info["has_video"] = False

        info_text = _format_media_info(original_name, size, media_info)

        set_state(user_id, waiting_for="media_action", input_path=path,
                  original_name=original_name, media_info=media_info,
                  media_type=media_type)

        # دکمه‌های مناسب
        markup = _media_action_keyboard(media_info, media_type)

        bot.send_message(
            message.chat.id,
            f"{info_text}\n\n"
            "🎯 چیکارش کنم؟",
            parse_mode='HTML',
            reply_markup=markup
        )

    except Exception as e:
        logger.exception("خطا در دریافت مدیا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


def _format_media_info(name: str, size: int, info: dict) -> str:
    lines = [
        "📋 <b>اطلاعات مدیا</b>",
        "━━━━━━━━━━━━━━━",
        f"📁 <b>اسم:</b> <code>{name}</code>",
        f"📊 <b>حجم:</b> {human_size(size)}",
    ]

    if info.get("duration"):
        lines.append(f"⏱ <b>مدت:</b> {format_duration(info['duration'])}")

    if info.get("has_video") and info.get("width"):
        lines.append(f"📐 <b>ابعاد:</b> {info['width']} × {info['height']}")

    if info.get("format"):
        lines.append(f"📄 <b>فرمت:</b> {info['format']}")

    # 🎵 اگه کاور داره
    if info.get("has_cover") and not info.get("has_video"):
        lines.append("🖼 <b>کاور:</b> دارد")

    features = []
    if info.get("has_video"):
        features.append("🎬 ویدیو")
    if info.get("has_audio"):
        features.append("🔊 صوت")
    if features:
        lines.append(f"✨ <b>شامل:</b> {' + '.join(features)}")

    lines.append("━━━━━━━━━━━━━━━")
    return "\n".join(lines)


def _media_action_keyboard(info: dict, media_type: str):
    """دکمه‌های عملیات بر اساس نوع مدیا"""
    markup = types.InlineKeyboardMarkup(row_width=2)

    # 🎬 ویدیو واقعی
    if media_type == "video" and info.get("has_video"):
        markup.add(
            types.InlineKeyboardButton("🎵 به MP3", callback_data="media_op_mp3"),
            types.InlineKeyboardButton("🎬 به GIF", callback_data="media_op_gif"),
        )
        markup.add(
            types.InlineKeyboardButton("📼 به MP4", callback_data="media_op_mp4"),
            types.InlineKeyboardButton("📼 به WEBM", callback_data="media_op_webm"),
        )
        markup.add(
            types.InlineKeyboardButton("🎚 سرعت", callback_data="media_op_speed"),
            types.InlineKeyboardButton("🔄 برعکس", callback_data="media_op_reverse"),
        )
        markup.add(
            types.InlineKeyboardButton("✂️ برش", callback_data="media_op_trim"),
        )

    # 🎵 آهنگ / صوت
    else:
        markup.add(
            types.InlineKeyboardButton("🎵 MP3 (192k)", callback_data="media_op_mp3"),
            types.InlineKeyboardButton("🎵 MP3 (320k)", callback_data="media_op_mp3_320"),
        )
        markup.add(
            types.InlineKeyboardButton("🎵 WAV", callback_data="media_op_wav"),
            types.InlineKeyboardButton("🎵 OGG", callback_data="media_op_ogg"),
        )
        markup.add(
            types.InlineKeyboardButton("🎵 M4A", callback_data="media_op_m4a"),
            types.InlineKeyboardButton("🎚 سرعت", callback_data="media_op_speed"),
        )
        markup.add(
            types.InlineKeyboardButton("🔄 برعکس", callback_data="media_op_reverse"),
            types.InlineKeyboardButton("📊 نرمالایز", callback_data="media_op_normalize"),
        )
        markup.add(
            types.InlineKeyboardButton("🎼 تغییر پیچ", callback_data="media_op_pitch"),
            types.InlineKeyboardButton("✂️ برش", callback_data="media_op_trim"),
        )

    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="media_op_cancel"))
    return markup


# ---------- انتخاب عملیات ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("media_op_"))
def media_action(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    media_type = state.get("media_type", "unknown")

    action = call.data.replace("media_op_", "")

    if action == "cancel":
        if input_path:
            delete_file(input_path)
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
            reply_markup=main_menu_keyboard()
        )
        return

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    # عملیات‌هایی که ورودی جداگانه می‌خوان
    if action == "trim":
        _start_trim(call, user_id)
        return
    if action == "speed":
        _start_speed(call, user_id)
        return
    if action == "pitch":
        _start_pitch(call, user_id)
        return

    # بقیه عملیات
    bot.answer_callback_query(call.id, "در حال تبدیل...")
    bot.edit_message_text(
        "⏳ در حال پردازش... (ممکنه چند ثانیه طول بکشه)",
        call.message.chat.id,
        call.message.message_id
    )

    output_path = None
    try:
        if action == "mp3":
            output_path = video_to_mp3(input_path, "192k")
            caption = "🎵 <b>MP3 (192kbps)</b>"
        elif action == "mp3_320":
            output_path = video_to_mp3(input_path, "320k")
            caption = "🎵 <b>MP3 (320kbps - کیفیت بالا)</b>"
        elif action == "gif":
            output_path = video_to_gif(input_path)
            caption = "🎬 <b>GIF</b> (۱۵ ثانیه اول)"
        elif action == "mp4":
            output_path = video_to_format(input_path, "mp4")
            caption = "📼 <b>MP4</b>"
        elif action == "webm":
            output_path = video_to_format(input_path, "webm")
            caption = "📼 <b>WEBM</b>"
        elif action == "wav":
            output_path = audio_to_format(input_path, "wav")
            caption = "🎵 <b>WAV</b>"
        elif action == "ogg":
            output_path = audio_to_format(input_path, "ogg")
            caption = "🎵 <b>OGG</b>"
        elif action == "m4a":
            output_path = audio_to_format(input_path, "m4a")
            caption = "🎵 <b>M4A</b>"
        elif action == "reverse":
            output_path = reverse_media(input_path)
            caption = "🔄 <b>برعکس شد</b>"
        elif action == "normalize":
            output_path = normalize_audio(input_path)
            caption = "📊 <b>نرمالایز شد</b>"
        else:
            bot.send_message(call.message.chat.id, "❌ عملیات نامشخص")
            return

        if not output_path or not os.path.exists(output_path):
            bot.send_message(call.message.chat.id, "❌ تبدیل ناموفق بود.")
            return

        size = os.path.getsize(output_path)
        caption += f"\n\n📊 حجم: {human_size(size)}"

        with open(output_path, "rb") as f:
            if action == "gif":
                bot.send_animation(call.message.chat.id, f, caption=caption, parse_mode='HTML')
            elif action in ("mp3", "mp3_320", "wav", "ogg", "m4a", "reverse", "normalize"):
                # اگه ویدیو بود و reverse، شاید ویدیو باشه
                ext = os.path.splitext(output_path)[1].lower()
                if ext in (".mp4", ".mkv", ".webm", ".mov", ".avi"):
                    bot.send_video(call.message.chat.id, f, caption=caption, parse_mode='HTML')
                else:
                    bot.send_audio(call.message.chat.id, f, caption=caption, parse_mode='HTML')
            else:
                bot.send_video(call.message.chat.id, f, caption=caption, parse_mode='HTML')

        _log_operation(user_id, f"media_{action}", None, action, size)
        mark_user_used(user_id)

        bot.send_message(
            call.message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.exception("خطا در تبدیل مدیا")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")

    finally:
        delete_file(input_path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)


# ---------- برش ----------
def _start_trim(call, user_id: int):
    set_state(user_id, waiting_for="trim_start")
    bot.answer_callback_query(call.id, "برش")
    bot.edit_message_text(
        "✂️ <b>برش مدیا</b>\n\n"
        "زمان شروع رو بفرست (فرمت <code>mm:ss</code> یا <code>ss</code>).\n\n"
        "مثال:\n"
        "• <code>0</code> — از ابتدا\n"
        "• <code>1:30</code> — از دقیقه ۱ و ۳۰ ثانیه\n"
        "• <code>30</code> — از ثانیه ۳۰",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "trim_start"
        and m.text
)
def trim_receive_start(message):
    user_id = message.from_user.id
    start = message.text.strip()
    set_state(user_id, trim_start=start, waiting_for="trim_duration")
    bot.send_message(
        message.chat.id,
        f"✅ شروع: <code>{start}</code>\n\n"
        "الان مدت زمان برش رو بفرست (مثلاً <code>10</code> برای ۱۰ ثانیه):",
        parse_mode='HTML'
    )


@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "trim_duration"
        and m.text
)
def trim_receive_duration(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")
    start = state.get("trim_start")
    duration = message.text.strip()

    if not input_path or not os.path.exists(input_path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال برش...")

    output_path = None
    try:
        output_path = trim_media(input_path, start, duration)

        if not output_path or not os.path.exists(output_path):
            bot.send_message(message.chat.id, "❌ برش ناموفق بود. زمان‌ها رو چک کن.")
            return

        size = os.path.getsize(output_path)
        ext = os.path.splitext(output_path)[1].lstrip(".").lower()

        with open(output_path, "rb") as f:
            caption = f"✂️ <b>برش انجام شد</b>\n\n⏱ از {start} به مدت {duration} ثانیه\n📊 حجم: {human_size(size)}"
            if ext in ("mp3", "wav", "ogg", "m4a"):
                bot.send_audio(message.chat.id, f, caption=caption, parse_mode='HTML')
            else:
                bot.send_video(message.chat.id, f, caption=caption, parse_mode='HTML')

        _log_operation(user_id, "media_trim", None, ext, size)
        mark_user_used(user_id)

        bot.send_message(
            message.chat.id,
            "می‌خوای کار دیگه‌ای بکنی؟ از منو انتخاب کن 👇",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.exception("خطا در برش")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
    finally:
        delete_file(input_path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)


# ---------- تغییر سرعت ----------
def _start_speed(call, user_id: int):
    set_state(user_id, waiting_for="speed_choice")
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("0.5x", callback_data="speed_0.5"),
        types.InlineKeyboardButton("0.75x", callback_data="speed_0.75"),
        types.InlineKeyboardButton("1.25x", callback_data="speed_1.25"),
        types.InlineKeyboardButton("1.5x", callback_data="speed_1.5"),
        types.InlineKeyboardButton("2x", callback_data="speed_2.0"),
        types.InlineKeyboardButton("3x", callback_data="speed_3.0"),
    )
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="speed_cancel"))
    bot.answer_callback_query(call.id, "سرعت")
    bot.edit_message_text(
        "🎚 <b>تغییر سرعت</b>\n\nسرعت جدید رو انتخاب کن:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("speed_"))
def speed_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")

    speed_data = call.data.replace("speed_", "")

    if speed_data == "cancel":
        if input_path:
            delete_file(input_path)
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
            reply_markup=main_menu_keyboard()
        )
        return

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    try:
        speed = float(speed_data)
    except ValueError:
        bot.answer_callback_query(call.id, "سرعت نامعتبر", show_alert=True)
        return

    bot.answer_callback_query(call.id, f"در حال تغییر به {speed}x...")
    bot.edit_message_text(
        f"⏳ در حال تغییر سرعت به {speed}x...",
        call.message.chat.id,
        call.message.message_id
    )

    output_path = None
    try:
        output_path = change_speed(input_path, speed)

        if not output_path or not os.path.exists(output_path):
            bot.send_message(call.message.chat.id, "❌ تغییر سرعت ناموفق بود.")
            return

        size = os.path.getsize(output_path)
        ext = os.path.splitext(output_path)[1].lstrip(".").lower()

        with open(output_path, "rb") as f:
            caption = f"🎚 <b>سرعت تغییر کرد به {speed}x</b>\n\n📊 حجم: {human_size(size)}"
            if ext in ("mp3", "wav", "ogg", "m4a"):
                bot.send_audio(call.message.chat.id, f, caption=caption, parse_mode='HTML')
            else:
                bot.send_video(call.message.chat.id, f, caption=caption, parse_mode='HTML')

        _log_operation(user_id, f"media_speed_{speed}", None, ext, size)
        mark_user_used(user_id)

        bot.send_message(
            call.message.chat.id,
            "منوی اصلی:",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.exception("خطا در تغییر سرعت")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")
    finally:
        delete_file(input_path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)


# ---------- تغییر پیچ ----------
def _start_pitch(call, user_id: int):
    set_state(user_id, waiting_for="pitch_choice")
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(
        types.InlineKeyboardButton("-12", callback_data="pitch_-12"),
        types.InlineKeyboardButton("-6", callback_data="pitch_-6"),
        types.InlineKeyboardButton("-3", callback_data="pitch_-3"),
        types.InlineKeyboardButton("+3", callback_data="pitch_3"),
        types.InlineKeyboardButton("+6", callback_data="pitch_6"),
        types.InlineKeyboardButton("+12", callback_data="pitch_12"),
    )
    markup.add(types.InlineKeyboardButton("❌ انصراف", callback_data="pitch_cancel"))
    bot.answer_callback_query(call.id, "پیچ")
    bot.edit_message_text(
        "🎼 <b>تغییر پیچ صدا</b>\n\n"
        "چند نیم‌پرده تغییر بدم؟\n"
        "منفی = بم‌تر، مثبت = زیرتر:",
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML',
        reply_markup=markup
    )


@bot.callback_query_handler(func=lambda c: c.data.startswith("pitch_"))
def pitch_chosen(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    input_path = state.get("input_path")

    pitch_data = call.data.replace("pitch_", "")

    if pitch_data == "cancel":
        if input_path:
            delete_file(input_path)
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
            reply_markup=main_menu_keyboard()
        )
        return

    if not input_path or not os.path.exists(input_path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    try:
        semitones = int(pitch_data)
    except ValueError:
        bot.answer_callback_query(call.id, "پیچ نامعتبر", show_alert=True)
        return

    bot.answer_callback_query(call.id, f"در حال تغییر پیچ...")
    bot.edit_message_text(
        "⏳ در حال تغییر پیچ...",
        call.message.chat.id,
        call.message.message_id
    )

    output_path = None
    try:
        output_path = change_pitch(input_path, semitones)

        if not output_path or not os.path.exists(output_path):
            bot.send_message(call.message.chat.id, "❌ تغییر پیچ ناموفق بود.")
            return

        size = os.path.getsize(output_path)
        with open(output_path, "rb") as f:
            caption = f"🎼 <b>پیچ تغییر کرد ({semitones:+d} نیم‌پرده)</b>\n\n📊 حجم: {human_size(size)}"
            bot.send_audio(call.message.chat.id, f, caption=caption, parse_mode='HTML')

        _log_operation(user_id, f"media_pitch_{semitones}", None, "pitch", size)
        mark_user_used(user_id)

        bot.send_message(
            call.message.chat.id,
            "منوی اصلی:",
            reply_markup=main_menu_keyboard()
        )

    except Exception as e:
        logger.exception("خطا در تغییر پیچ")
        bot.send_message(call.message.chat.id, f"❌ خطا: {e}")
    finally:
        delete_file(input_path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)


# ---------- ثبت در دیتابیس ----------
def _log_operation(user_id: int, op_type: str, in_fmt, out_fmt, size: int):
    import threading
    def runner():
        try:
            import psycopg2
            from config import DATABASE_URL

            sync_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
            conn = psycopg2.connect(sync_url)
            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO operations
                (user_id, operation_type, input_format, output_format, file_size, status)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (user_id, op_type, in_fmt, out_fmt, size, "success")
            )
            conn.commit()
            cur.close()
            conn.close()
        except Exception as e:
            logger.warning(f"ثبت عملیات ناموفق: {e}")

    threading.Thread(target=runner, daemon=True).start()