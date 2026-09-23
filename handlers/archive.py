import os
import uuid
import zipfile
import logging
import threading
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.file_info import get_file_info, format_file_info
from utils.keyboards import main_menu_keyboard, zip_done_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '🗜️ ساخت ZIP')
@check_usage_limit
def archive_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="archive", waiting_for="files", files=[])
    bot.send_message(
        message.chat.id,
        "🗜️ <b>ساخت ZIP</b>\n\n"
        "فایل‌هات رو یکی‌یکی بفرست (هر نوعی: عکس، PDF، متن، ...).\n"
        "وقتی همه رو فرستادی، دکمه «✅ تمام شد» رو بزن.",
        parse_mode='HTML',
        reply_markup=zip_done_keyboard()
    )


# ---------- دریافت فایل ----------
@bot.message_handler(
    content_types=['document', 'photo', 'video', 'audio', 'voice'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "files"
)
def receive_file_for_zip(message):
    user_id = message.from_user.id
    state = get_state(user_id)

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
            original_name = f"photo_{uuid.uuid4().hex[:6]}.jpg"
        elif message.content_type == 'video':
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

        safe_name = f"{uuid.uuid4().hex[:8]}_{original_name}"
        path = os.path.join(TEMP_DIR, safe_name)

        with open(path, "wb") as f:
            f.write(downloaded)

        state.setdefault("files", []).append((path, original_name))
        set_state(user_id, files=state["files"])

        info = get_file_info(path)
        info["name"] = original_name
        info_text = format_file_info(info, show_image_details=True)

        count = len(state["files"])
        bot.send_message(
            message.chat.id,
            f"{info_text}\n\n"
            f"✅ فایل دریافت شد. ({count} فایل تو صف)\n"
            "فایل بعدی رو بفرست یا «✅ تمام شد» رو بزن.",
            parse_mode='HTML'
        )

    except Exception as e:
        logger.exception("خطا در دریافت فایل")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")


# ---------- تمام شد / انصراف ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "files"
        and m.text in ('✅ تمام شد', '❌ انصراف')
)
def finish_zip(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("files", [])

    if message.text == '❌ انصراف':
        for path, _ in files:
            delete_file(path)
        clear_state(user_id)
        bot.send_message(
            message.chat.id,
            "❌ عملیات لغو شد.",
            reply_markup=main_menu_keyboard()
        )
        return

    if not files:
        bot.send_message(message.chat.id, "⚠️ هیچ فایلی نفرستادی!")
        return

    bot.send_message(message.chat.id, f"⏳ در حال ساخت ZIP از {len(files)} فایل...")

    output_path = None
    try:
        output_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.zip")

        with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
            for path, original_name in files:
                zf.write(path, arcname=original_name)

        size = os.path.getsize(output_path)

        zip_info = {
            "name": os.path.basename(output_path),
            "ext": "ZIP",
            "size_bytes": size,
            "size_human": f"{size / 1024:.1f} کیلوبایت" if size < 1024*1024 else f"{size / (1024*1024):.1f} مگابایت",
            "is_image": False,
        }
        zip_info_text = format_file_info(zip_info, show_image_details=False)

        with open(output_path, "rb") as f:
            bot.send_document(
                message.chat.id, f,
                caption=f"✅ ZIP ساخته شد ({len(files)} فایل)\n\n{zip_info_text}",
                parse_mode='HTML',
                reply_markup=main_menu_keyboard()
            )

        _log_operation(user_id, "zip_create", None, "zip", size)
        mark_user_used(user_id)

    except Exception as e:
        logger.exception("خطا در ساخت ZIP")
        bot.send_message(
            message.chat.id, f"❌ خطا: {e}",
            reply_markup=main_menu_keyboard()
        )

    finally:
        for path, _ in files:
            delete_file(path)
        if output_path:
            delete_file(output_path)
        clear_state(user_id)


def _log_operation(user_id: int, op_type: str, in_fmt, out_fmt, size: int):
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