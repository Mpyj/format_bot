import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.file_info import human_size
from utils.media_tools import get_media_info, format_duration
from utils.advanced_media import (
    extract_frame, auto_thumbnail, add_subtitle,
    add_music, images_to_video, remove_vocals,
    audio_waveform, timelapse, concat_videos, remove_audio,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منوی مدیا پیشرفته
# ============================================================
def _adv_media_menu(user_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📸 استخراج فریم", callback_data="adv_media_frame"),
        types.InlineKeyboardButton("🖼️ Thumbnail", callback_data="adv_media_thumb"),
    )
    markup.add(
        types.InlineKeyboardButton("⏱ تایم‌لپس", callback_data="adv_media_timelapse"),
        types.InlineKeyboardButton("🔇 حذف صدا", callback_data="adv_media_noaudio"),
    )
    markup.add(
        types.InlineKeyboardButton("🎞 ترکیب ۲ ویدیو", callback_data="adv_media_concat"),
    )
    markup.add(
        types.InlineKeyboardButton("📝 زیرنویس", callback_data="adv_media_subtitle"),
        types.InlineKeyboardButton("🎵 افزودن موسیقی", callback_data="adv_media_music"),
    )
    markup.add(
        types.InlineKeyboardButton("🎬 عکس → ویدیو", callback_data="adv_media_slideshow"),
        types.InlineKeyboardButton("🔊 حذف صدا خواننده", callback_data="adv_media_karaoke"),
    )
    markup.add(
        types.InlineKeyboardButton("📊 نمودار موج صدا", callback_data="adv_media_waveform"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="adv_media_close"))
    return markup


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🎬 مدیا پیشرفته')
def adv_media_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="adv_media", waiting_for=None)

    bot.send_message(
        message.chat.id,
        "🎬 <b>مدیا پیشرفته</b>\n\n"
        "📸 <b>استخراج فریم</b> — عکس از ثانیه X\n"
        "🖼️ <b>Thumbnail</b> — بهترین فریم خودکار\n"
        "⏱ <b>تایم‌لپس</b> — ویدیو سریع‌تر\n"
        "🔇 <b>حذف صدا</b> — ویدیو بی‌صدا\n"
        "🎞 <b>ترکیب ۲ ویدیو</b> — چسبوندن\n"
        "📝 <b>زیرنویس</b> — SRT روی ویدیو\n"
        "🎵 <b>افزودن موسیقی</b> — موسیقی روی ویدیو\n"
        "🎬 <b>عکس → ویدیو</b> — اسلایدشو\n"
        "🔊 <b>حذف صدا خواننده</b> — کارائوکه\n"
        "📊 <b>نمودار موج صدا</b> — waveform",
        parse_mode='HTML',
        reply_markup=_adv_media_menu(user_id)
    )


# ---------- callback ها ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("adv_media_"))
def adv_media_action(call):
    user_id = call.from_user.id
    action = call.data.replace("adv_media_", "")

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
        "frame": "📸 <b>استخراج فریم</b>\n\nویدیو رو بفرست تا از ثانیه دلخواه عکس بگیرم.",
        "thumb": "🖼️ <b>Thumbnail</b>\n\nویدیو رو بفرست تا بهترین فریم رو انتخاب کنم.",
        "timelapse": "⏱ <b>تایم‌لپس</b>\n\nویدیو رو بفرست تا سرعتش رو زیاد کنم.",
        "noaudio": "🔇 <b>حذف صدا</b>\n\nویدیو رو بفرست تا صدا رو حذف کنم.",
        "concat": "🎞 <b>ترکیب ۲ ویدیو</b>\n\nویدیو <b>اول</b> رو بفرست.",
        "subtitle": "📝 <b>افزودن زیرنویس</b>\n\nویدیو رو بفرست، بعد فایل SRT.",
        "music": "🎵 <b>افزودن موسیقی</b>\n\nویدیو رو بفرست، بعد فایل صوتی.",
        "slideshow": "🎬 <b>عکس → ویدیو</b>\n\nچند عکس بفرست، بعد دکمه «✅ تمام شد».",
        "karaoke": "🔊 <b>حذف صدا خواننده</b>\n\nفایل صوتی رو بفرست.",
        "waveform": "📊 <b>نمودار موج صدا</b>\n\nفایل صوتی رو بفرست.",
    }

    set_state(user_id, mode="adv_media", adv_action=action, waiting_for=f"adv_{action}")
    try:
        bot.edit_message_text(
            hints.get(action, "عملیات نامشخص"),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML',
            reply_markup=types.InlineKeyboardMarkup().add(
                types.InlineKeyboardButton("🔙 بازگشت", callback_data="adv_media_back")
            )
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            hints.get(action, "عملیات نامشخص"),
            parse_mode='HTML'
        )


@bot.callback_query_handler(func=lambda c: c.data == "adv_media_back")
def adv_media_back(call):
    user_id = call.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="adv_media", waiting_for=None)

    bot.answer_callback_query(call.id)
    try:
        bot.edit_message_text(
            "🎬 <b>مدیا پیشرفته</b>\n\nیه عملیات انتخاب کن:",
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_adv_media_menu(user_id)
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            "🎬 <b>مدیا پیشرفته</b>",
            parse_mode='HTML', reply_markup=_adv_media_menu(user_id)
        )


# ============================================================
# 📥 دریافت ویدیو / صوت
# ============================================================
@bot.message_handler(
    content_types=['video', 'document', 'audio', 'voice'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for", "").startswith("adv_")
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_receive_media(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("adv_action")

    try:
        # دریافت فایل
        if message.content_type == 'video':
            file_info_tg = bot.get_file(message.video.file_id)
            original_name = message.video.file_name or f"video_{uuid.uuid4().hex[:6]}.mp4"
        elif message.content_type == 'audio':
            file_info_tg = bot.get_file(message.audio.file_id)
            original_name = message.audio.file_name or f"audio_{uuid.uuid4().hex[:6]}.mp3"
        elif message.content_type == 'voice':
            file_info_tg = bot.get_file(message.voice.file_id)
            original_name = f"voice_{uuid.uuid4().hex[:6]}.ogg"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            original_name = message.document.file_name or f"file_{uuid.uuid4().hex[:6]}"

        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(original_name)[1] or ".mp4"
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        # ذخیره path
        set_state(user_id, adv_input_path=path, adv_original_name=original_name)

        # ادامه بر اساس action
        if action == "frame":
            # زمان رو بپرس
            set_state(user_id, waiting_for="adv_frame_time")
            bot.send_message(
                message.chat.id,
                "✅ ویدیو دریافت شد.\n\n"
                "⏱ زمان رو بفرست (فرمت <code>mm:ss</code> یا <code>hh:mm:ss</code>):\n\n"
                "💡 مثال:\n"
                "• <code>00:05</code> — ثانیه ۵\n"
                "• <code>01:30</code> — دقیقه ۱ و ۳۰ ثانیه\n"
                "• <code>00:00:10</code> — ثانیه ۱۰",
                parse_mode='HTML'
            )
        elif action == "thumb":
            _process_thumb(message, user_id, path)
        elif action == "timelapse":
            set_state(user_id, waiting_for="adv_timelapse_speed")
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("2x", callback_data="advspeed_2"),
                types.InlineKeyboardButton("4x", callback_data="advspeed_4"),
                types.InlineKeyboardButton("8x", callback_data="advspeed_8"),
                types.InlineKeyboardButton("16x", callback_data="advspeed_16"),
            )
            bot.send_message(
                message.chat.id,
                "⏱ سرعت رو انتخاب کن:",
                reply_markup=markup
            )
        elif action == "noaudio":
            _process_noaudio(message, user_id, path)
        elif action == "concat":
            # ویدیو اول ذخیره شد، منتظر ویدیو دوم
            set_state(user_id, waiting_for="adv_concat_second")
            bot.send_message(
                message.chat.id,
                "✅ ویدیو اول دریافت شد.\n\n"
                "الان ویدیو <b>دوم</b> رو بفرست:",
                parse_mode='HTML'
            )
        elif action == "subtitle":
            set_state(user_id, waiting_for="adv_subtitle_srt")
            bot.send_message(
                message.chat.id,
                "✅ ویدیو دریافت شد.\n\n"
                "الان فایل <b>SRT</b> رو بفرست:"
            )
        elif action == "music":
            set_state(user_id, waiting_for="adv_music_audio")
            bot.send_message(
                message.chat.id,
                "✅ ویدیو دریافت شد.\n\n"
                "الان فایل <b>موسیقی</b> رو بفرست:"
            )
        elif action == "slideshow":
            # عکس‌ها رو ذخیره کن
            files = state.get("adv_slideshow_files", [])
            # اگه ویدیو یا سند بود، به عنوان فایل
            files.append(path)
            set_state(user_id, adv_slideshow_files=files, waiting_for="adv_slideshow_more")
            bot.send_message(
                message.chat.id,
                f"✅ عکس {len(files)} دریافت شد.\n\n"
                "عکس بعدی رو بفرست یا دکمه «✅ تمام شد» رو بزن.\n\n"
                "💡 بعدش موسیقی هم می‌تونی اضافه کنی.",
                reply_markup=_slideshow_keyboard()
            )
        elif action == "karaoke":
            _process_karaoke(message, user_id, path)
        elif action == "waveform":
            _process_waveform(message, user_id, path)
        else:
            bot.send_message(message.chat.id, "❌ عملیات نامشخص")
            delete_file(path)

    except Exception as e:
        logger.exception("خطا در دریافت مدیا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


def _slideshow_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton('✅ تمام شد'), types.KeyboardButton('❌ انصراف'))
    return markup


# ============================================================
# 📸 استخراج فریم — دریافت زمان
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "adv_frame_time"
        and get_state(m.from_user.id).get("mode") == "adv_media"
        and m.text
        and not is_menu_button(m.text)
)
def adv_frame_time(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("adv_input_path")
    timestamp = message.text.strip()

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال استخراج فریم...")

    output = extract_frame(path, timestamp)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption=f"📸 <b>فریم استخراج شد</b>\n"
                        f"⏱ زمان: <code>{timestamp}</code>\n"
                        f"📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ استخراج ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🖼️ Thumbnail خودکار
# ============================================================
def _process_thumb(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال انتخاب بهترین فریم...")

    info = get_media_info(path)
    duration = info.get("duration", 5)

    output = auto_thumbnail(path, duration)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption=f"🖼️ <b>Thumbnail</b>\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# ⏱ تایم‌لپس
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("advspeed_"))
def adv_timelapse_speed(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("adv_input_path")
    speed = float(call.data.replace("advspeed_", ""))

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"در حال پردازش ({speed}x)...")
    bot.edit_message_text(
        f"⏳ در حال تایم‌لپس ({speed}x)...",
        call.message.chat.id, call.message.message_id
    )

    output = timelapse(path, speed)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_video(
                call.message.chat.id, f,
                caption=f"⏱ <b>تایم‌لپس {speed}x</b>\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🔇 حذف صدا
# ============================================================
def _process_noaudio(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال حذف صدا...")

    output = remove_audio(path)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                message.chat.id, f,
                caption=f"🔇 <b>ویدیو بدون صدا</b>\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🎞 ترکیب — دریافت ویدیو دوم
# ============================================================
@bot.message_handler(
    content_types=['video', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "adv_concat_second"
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_concat_second(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    video1 = state.get("adv_input_path")

    if not video1 or not os.path.exists(video1):
        bot.send_message(message.chat.id, "❌ ویدیو اول پیدا نشد.")
        clear_state(user_id)
        return

    try:
        if message.content_type == 'video':
            file_info_tg = bot.get_file(message.video.file_id)
        else:
            file_info_tg = bot.get_file(message.document.file_id)

        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(file_info_tg.file_path)[1] or ".mp4"
        video2 = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(video2, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "⏳ در حال ترکیب دو ویدیو...")

        output = concat_videos(video1, video2)

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_video(
                    message.chat.id, f,
                    caption=f"🎞 <b>ترکیب انجام شد</b>\n📊 حجم: {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ترکیب ناموفق بود.")

        delete_file(video1)
        delete_file(video2)
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))

    except Exception as e:
        logger.exception("خطا در ترکیب")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        delete_file(video1)
        clear_state(user_id)


# ============================================================
# 📝 زیرنویس — دریافت SRT
# ============================================================
@bot.message_handler(
    content_types=['document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "adv_subtitle_srt"
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_subtitle_srt(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    video_path = state.get("adv_input_path")

    if not video_path or not os.path.exists(video_path):
        bot.send_message(message.chat.id, "❌ ویدیو پیدا نشد.")
        clear_state(user_id)
        return

    # چک SRT
    fname = (message.document.file_name or "").lower()
    if not fname.endswith(".srt"):
        bot.send_message(message.chat.id, "❌ فقط فایل SRT قبول می‌کنم.")
        return

    try:
        file_info_tg = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info_tg.file_path)
        srt_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.srt")
        with open(srt_path, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "⏳ در حال افزودن زیرنویس...")

        output = add_subtitle(video_path, srt_path)

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_video(
                    message.chat.id, f,
                    caption=f"📝 <b>زیرنویس افزوده شد</b>\n📊 حجم: {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ناموفق بود.")

        delete_file(video_path)
        delete_file(srt_path)
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))

    except Exception as e:
        logger.exception("خطا در زیرنویس")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        delete_file(video_path)
        clear_state(user_id)


# ============================================================
# 🎵 موسیقی — دریافت فایل صوتی
# ============================================================
@bot.message_handler(
    content_types=['audio', 'document', 'voice'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "adv_music_audio"
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_music_audio(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    video_path = state.get("adv_input_path")

    if not video_path or not os.path.exists(video_path):
        bot.send_message(message.chat.id, "❌ ویدیو پیدا نشد.")
        clear_state(user_id)
        return

    try:
        if message.content_type == 'audio':
            file_info_tg = bot.get_file(message.audio.file_id)
        elif message.content_type == 'voice':
            file_info_tg = bot.get_file(message.voice.file_id)
        else:
            file_info_tg = bot.get_file(message.document.file_id)

        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(file_info_tg.file_path)[1] or ".mp3"
        audio_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(audio_path, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "⏳ در حال افزودن موسیقی...")

        output = add_music(video_path, audio_path)

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_video(
                    message.chat.id, f,
                    caption=f"🎵 <b>موسیقی افزوده شد</b>\n📊 حجم: {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ناموفق بود.")

        delete_file(video_path)
        delete_file(audio_path)
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))

    except Exception as e:
        logger.exception("خطا در موسیقی")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        delete_file(video_path)
        clear_state(user_id)


# ============================================================
# 🎬 اسلایدشو — دریافت عکس‌های بیشتر
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "adv_slideshow_more"
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_slideshow_add(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("adv_slideshow_files", [])

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
            ext = ".jpg"
        else:
            file_info_tg = bot.get_file(message.document.file_id)
            ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"

        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(path, "wb") as f:
            f.write(downloaded)

        files.append(path)
        set_state(user_id, adv_slideshow_files=files)

        bot.send_message(
            message.chat.id,
            f"✅ عکس {len(files)} دریافت شد.\n"
            "عکس بعدی یا «✅ تمام شد».",
            reply_markup=_slideshow_keyboard()
        )
    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")


@bot.message_handler(
    func=lambda m: m.text in ('✅ تمام شد', '❌ انصراف')
        and get_state(m.from_user.id).get("waiting_for") == "adv_slideshow_more"
        and get_state(m.from_user.id).get("mode") == "adv_media"
)
def adv_slideshow_finish(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("adv_slideshow_files", [])

    if message.text == '❌ انصراف':
        for f in files:
            delete_file(f)
        clear_state(user_id)
        bot.send_message(
            message.chat.id,
            "❌ لغو شد.",
            reply_markup=main_menu_keyboard(user_id)
        )
        return

    if len(files) < 2:
        bot.send_message(message.chat.id, "⚠️ حداقل ۲ عکس لازمه.")
        return

    bot.send_message(message.chat.id, f"⏳ در حال ساخت ویدیو از {len(files)} عکس...")

    output = images_to_video(files, audio_path=None, duration_per_image=3.0)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_video(
                message.chat.id, f,
                caption=f"🎬 <b>اسلایدشو ساخته شد</b>\n"
                        f"🖼 {len(files)} عکس\n"
                        f"📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    for f in files:
        delete_file(f)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🔊 حذف صدا خواننده
# ============================================================
def _process_karaoke(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال حذف صدای خواننده...")

    output = remove_vocals(path)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_audio(
                message.chat.id, f,
                caption=f"🔊 <b>کارائوکه (بدون خواننده)</b>\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📊 نمودار موج صدا
# ============================================================
def _process_waveform(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال ساخت نمودار... (چند ثانیه)")

    output = audio_waveform(path)

    if output and os.path.exists(output):
        with open(output, "rb") as f:
            bot.send_photo(
                message.chat.id, f,
                caption="📊 <b>نمودار موج صدا</b>",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))