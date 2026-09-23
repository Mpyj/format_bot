import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state
from utils.file_info import human_size
from utils.pdf_tools import (
    merge_pdfs, split_pdf, encrypt_pdf, decrypt_pdf,
    rotate_pdf, pdf_to_images, images_to_pdf,
    compress_pdf, add_watermark, get_pdf_info,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import check_usage_limit, mark_user_used

logger = logging.getLogger(__name__)


# ---------- شروع ----------
@bot.message_handler(func=lambda m: m.text == '📄 ابزار PDF')
@check_usage_limit
def pdf_start(message):
    user_id = message.from_user.id
    set_state(user_id, mode="pdf", waiting_for="pdf_menu", files=[])

    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("🔗 ادغام", callback_data="pdf_op_merge"),
        types.InlineKeyboardButton("✂️ تقسیم", callback_data="pdf_op_split"),
    )
    markup.add(
        types.InlineKeyboardButton("🔒 قفل", callback_data="pdf_op_lock"),
        types.InlineKeyboardButton("🔓 باز کردن قفل", callback_data="pdf_op_unlock"),
    )
    markup.add(
        types.InlineKeyboardButton("📷 PDF → عکس", callback_data="pdf_op_pdf2img"),
        types.InlineKeyboardButton("📄 عکس → PDF", callback_data="pdf_op_img2pdf"),
    )
    markup.add(
        types.InlineKeyboardButton("📉 فشرده‌سازی", callback_data="pdf_op_compress"),
        types.InlineKeyboardButton("🔄 چرخش", callback_data="pdf_op_rotate"),
    )
    markup.add(
        types.InlineKeyboardButton("💧 واترمارک", callback_data="pdf_op_watermark"),
    )
    markup.add(
        types.InlineKeyboardButton("ℹ️ اطلاعات PDF", callback_data="pdf_op_info"),
        types.InlineKeyboardButton("❌ انصراف", callback_data="pdf_op_cancel"),
    )

    bot.send_message(
        message.chat.id,
        "📄 <b>ابزار PDF</b>\n\n"
        "یه عملیات انتخاب کن:\n\n"
        "🔗 <b>ادغام</b> — چند PDF → یکی\n"
        "✂️ <b>تقسیم</b> — PDF → چند تا\n"
        "🔒 <b>قفل</b> — رمز بذار\n"
        "🔓 <b>باز کردن قفل</b> — رمز رو بردار\n"
        "📷 <b>PDF → عکس</b> — هر صفحه یه عکس\n"
        "📄 <b>عکس → PDF</b> — چند عکس → PDF\n"
        "📉 <b>فشرده‌سازی</b> — حجم رو کم کن\n"
        "🔄 <b>چرخش</b> — ۹۰/۱۸۰/۲۷۰ درجه\n"
        "💧 <b>واترمارک</b> — متن روی PDF\n"
        "ℹ️ <b>اطلاعات</b> — تعداد صفحه، نویسنده",
        parse_mode='HTML',
        reply_markup=markup
    )


# ---------- انتخاب عملیات ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("pdf_op_"))
def pdf_action(call):
    user_id = call.from_user.id
    action = call.data.replace("pdf_op_", "")

    if action == "cancel":
        _cleanup_user_files(user_id)
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

    bot.answer_callback_query(call.id)
    set_state(user_id, pdf_action=action, waiting_for=f"pdf_{action}")

    # راهنماهای هر عملیات
    hints = {
        "merge": "🔗 <b>ادغام PDF</b>\n\nچند فایل PDF بفرست (۲ تا ۱۰ تا).\nوقتی همه رو فرستادی، دکمه «✅ تمام شد» رو بزن.",
        "split": "✂️ <b>تقسیم PDF</b>\n\nیه PDF بفرست.\nبعدش بازه‌ها رو می‌نویسی (مثلاً <code>1-3,4-6</code>).",
        "lock": "🔒 <b>قفل PDF</b>\n\nیه PDF بفرست، بعد رمز رو بنویس.",
        "unlock": "🔓 <b>باز کردن قفل PDF</b>\n\nیه PDF رمزدار بفرست، بعد رمز رو بنویس.",
        "pdf2img": "📷 <b>PDF → عکس</b>\n\nیه PDF بفرست.\n(حداکثر ۱۰ صفحه اول تبدیل میشه)",
        "img2pdf": "📄 <b>عکس → PDF</b>\n\nچند عکس بفرست (به ترتیب).\nوقتی همه رو فرستادی، دکمه «✅ تمام شد» رو بزن.",
        "compress": "📉 <b>فشرده‌سازی PDF</b>\n\nیه PDF بفرست.",
        "rotate": "🔄 <b>چرخش PDF</b>\n\nیه PDF بفرست، بعد زاویه رو انتخاب کن.",
        "watermark": "💧 <b>واترمارک PDF</b>\n\nیه PDF بفرست، بعد متن واترمارک رو بنویس.",
        "info": "ℹ️ <b>اطلاعات PDF</b>\n\nیه PDF بفرست.",
    }

    bot.edit_message_text(
        hints.get(action, "عملیات نامشخص"),
        call.message.chat.id,
        call.message.message_id,
        parse_mode='HTML'
    )

    # برای merge و img2pdf، کیبورد خاص
    if action in ("merge", "img2pdf"):
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton('✅ تمام شد'), types.KeyboardButton('❌ انصراف'))
        bot.send_message(call.message.chat.id, "👇", reply_markup=markup)


# ---------- دریافت PDF ----------
@bot.message_handler(
    content_types=['document'],
    func=lambda m: _is_waiting_pdf(m)
)
def receive_pdf(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("pdf_action")

    if not message.document.file_name.lower().endswith(".pdf"):
        bot.send_message(message.chat.id, "❌ فقط PDF قبول می‌کنم.")
        return

    try:
        file_info_tg = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info_tg.file_path)

        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.pdf")
        with open(path, "wb") as f:
            f.write(downloaded)

        # برای merge و img2pdf → چند فایل
        if action in ("merge", "img2pdf"):
            files = state.get("files", [])
            files.append(path)
            set_state(user_id, files=files)
            bot.send_message(
                message.chat.id,
                f"✅ PDF دریافت شد. ({len(files)} فایل)\n"
                "بعدی رو بفرست یا «✅ تمام شد» بزن."
            )
            return

        # برای بقیه → یه فایل، ادامه بدیم
        set_state(user_id, input_path=path)

        if action == "split":
            info = get_pdf_info(path)
            set_state(user_id, waiting_for="pdf_split_ranges")
            bot.send_message(
                message.chat.id,
                f"📄 PDF دریافت شد ({info.get('pages', '?')} صفحه).\n\n"
                "بازه‌ها رو بنویس. مثال:\n"
                "<code>1-3,4-6,7-9</code>\n"
                "(یعنی سه تا PDF: صفحات ۱-۳، ۴-۶، ۷-۹)",
                parse_mode='HTML'
            )

        elif action == "lock":
            set_state(user_id, waiting_for="pdf_password_lock")
            bot.send_message(message.chat.id, "🔒 رمز مورد نظر رو بنویس:")

        elif action == "unlock":
            set_state(user_id, waiting_for="pdf_password_unlock")
            bot.send_message(message.chat.id, "🔓 رمز PDF رو بنویس:")

        elif action == "rotate":
            set_state(user_id, waiting_for="pdf_rotate_choice")
            markup = types.InlineKeyboardMarkup(row_width=3)
            markup.add(
                types.InlineKeyboardButton("90°", callback_data="pdfrot_90"),
                types.InlineKeyboardButton("180°", callback_data="pdfrot_180"),
                types.InlineKeyboardButton("270°", callback_data="pdfrot_270"),
            )
            bot.send_message(message.chat.id, "🔄 زاویه چرخش رو انتخاب کن:", reply_markup=markup)

        elif action == "watermark":
            set_state(user_id, waiting_for="pdf_watermark_text")
            bot.send_message(message.chat.id, "💧 متن واترمارک رو بنویس:")

        else:
            # pdf2img، compress، info → فوری پردازش
            _process_single_pdf(bot, message.chat.id, user_id, action, path)

    except Exception as e:
        logger.exception("خطا در دریافت PDF")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


def _is_waiting_pdf(message) -> bool:
    """چک می‌کنه کاربر منتظر ارسال PDF هست یا نه"""
    state = get_state(message.from_user.id)
    waiting = state.get("waiting_for", "")
    action = state.get("pdf_action")

    if waiting in ("pdf_merge", "pdf_img2pdf"):
        return True
    if waiting in ("pdf_split", "pdf_lock", "pdf_unlock", "pdf_pdf2img",
                   "pdf_compress", "pdf_rotate", "pdf_watermark", "pdf_info"):
        return not state.get("input_path")  # فقط اگه فایل نداشته
    return False


# ---------- پایان لیست فایل‌ها (merge / img2pdf) ----------
@bot.message_handler(
    func=lambda m: m.text in ('✅ تمام شد', '❌ انصراف')
        and get_state(m.from_user.id).get("pdf_action") in ("merge", "img2pdf")
)
def pdf_finish_list(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    files = state.get("files", [])
    action = state.get("pdf_action")

    if message.text == '❌ انصراف':
        _cleanup_user_files(user_id)
        clear_state(user_id)
        bot.send_message(
            message.chat.id,
            "❌ لغو شد.",
            reply_markup=main_menu_keyboard()
        )
        return

    if not files:
        bot.send_message(message.chat.id, "⚠️ هیچ فایلی نفرستادی!")
        return

    if action == "merge":
        if len(files) < 2:
            bot.send_message(message.chat.id, "⚠️ حداقل ۲ PDF لازمه.")
            return
        _do_merge(message.chat.id, user_id, files)
    elif action == "img2pdf":
        _do_img2pdf(message.chat.id, user_id, files)


def _do_merge(chat_id, user_id: int, files: list):
    bot.send_message(chat_id, f"⏳ در حال ادغام {len(files)} PDF...")
    output = merge_pdfs(files)
    _send_result(chat_id, user_id, output, "🔗 <b>ادغام انجام شد!</b>", "merge")


def _do_img2pdf(chat_id, user_id: int, images: list):
    bot.send_message(chat_id, f"⏳ در حال تبدیل {len(images)} عکس به PDF...")
    output = images_to_pdf(images)
    _send_result(chat_id, user_id, output, "📄 <b>عکس‌ها به PDF تبدیل شدن!</b>", "img2pdf")


def _process_single_pdf(bot, chat_id, user_id: int, action: str, path: str):
    """پردازش فوری روی یه PDF"""
    bot.send_message(chat_id, "⏳ در حال پردازش...")

    try:
        if action == "pdf2img":
            images = pdf_to_images(path)
            if not images:
                bot.send_message(chat_id, "❌ تبدیل ناموفق بود. (poppler نصب شده؟)")
                return
            for i, img_path in enumerate(images, 1):
                with open(img_path, "rb") as f:
                    bot.send_photo(chat_id, f, caption=f"صفحه {i}")
                delete_file(img_path)
            mark_user_used(user_id)

        elif action == "compress":
            output = compress_pdf(path)
            _send_result(chat_id, user_id, output, "📉 <b>فشرده‌سازی انجام شد!</b>", "compress")

        elif action == "info":
            info = get_pdf_info(path)
            if info.get("success"):
                text = (
                    "ℹ️ <b>اطلاعات PDF</b>\n\n"
                    f"📄 صفحات: {info['pages']}\n"
                    f"📊 حجم: {human_size(info['size'])}\n"
                    f"🔒 رمزدار: {'✅' if info['encrypted'] else '❌'}\n"
                )
                if info.get("title"):
                    text += f"📝 عنوان: {info['title']}\n"
                if info.get("author"):
                    text += f"👤 نویسنده: {info['author']}\n"
                if info.get("creator"):
                    text += f"🛠 سازنده: {info['creator']}\n"
                bot.send_message(chat_id, text, parse_mode='HTML')
            else:
                bot.send_message(chat_id, "❌ نتونستم اطلاعات بگیرم.")
            mark_user_used(user_id)

    except Exception as e:
        logger.exception(f"خطا در {action}")
        bot.send_message(chat_id, f"❌ خطا: {e}")
    finally:
        delete_file(path)
        clear_state(user_id)
        bot.send_message(chat_id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ---------- تقسیم ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdf_split_ranges"
        and m.text
)
def pdf_split_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("input_path")

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    # پارس بازه‌ها
    try:
        ranges = []
        for part in message.text.replace(" ", "").split(","):
            s, e = part.split("-")
            ranges.append((int(s), int(e)))
    except Exception:
        bot.send_message(
            message.chat.id,
            "❌ فرمت اشتباه. مثال: <code>1-3,4-6</code>",
            parse_mode='HTML'
        )
        return

    bot.send_message(message.chat.id, "⏳ در حال تقسیم...")

    outputs = split_pdf(path, ranges)
    if not outputs:
        bot.send_message(message.chat.id, "❌ تقسیم ناموفق بود.")
        delete_file(path)
        clear_state(user_id)
        return

    for out in outputs:
        with open(out, "rb") as f:
            bot.send_document(message.chat.id, f, caption=f"✂️ {os.path.basename(out)}")
        delete_file(out)

    _log_operation(user_id, "pdf_split", "pdf", "pdf", 0)
    mark_user_used(user_id)
    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "✅ تقسیم انجام شد.", reply_markup=main_menu_keyboard())


# ---------- قفل ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdf_password_lock"
        and m.text
)
def pdf_lock_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("input_path")
    password = message.text.strip()

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال قفل کردن...")
    output = encrypt_pdf(path, password)
    _send_result(message.chat.id, user_id, output, "🔒 <b>PDF قفل شد!</b>", "lock")

    delete_file(path)


# ---------- باز کردن قفل ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdf_password_unlock"
        and m.text
)
def pdf_unlock_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("input_path")
    password = message.text.strip()

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال باز کردن قفل...")
    output = decrypt_pdf(path, password)

    if not output:
        bot.send_message(message.chat.id, "❌ رمز اشتباهه یا PDF مشکل داره.")
        delete_file(path)
        clear_state(user_id)
        bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())
        return

    _send_result(message.chat.id, user_id, output, "🔓 <b>قفل باز شد!</b>", "unlock")
    delete_file(path)


# ---------- چرخش ----------
@bot.callback_query_handler(func=lambda c: c.data.startswith("pdfrot_"))
def pdf_rotate_receive(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("input_path")
    angle = int(call.data.replace("pdfrot_", ""))

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "فایل پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, f"در حال چرخش {angle}°...")
    bot.edit_message_text(
        f"⏳ در حال چرخش {angle}°...",
        call.message.chat.id,
        call.message.message_id
    )

    output = rotate_pdf(path, angle)
    if output:
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                call.message.chat.id, f,
                caption=f"🔄 <b>چرخش {angle}° انجام شد</b>\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        _log_operation(user_id, f"pdf_rotate_{angle}", "pdf", "pdf", size)
        mark_user_used(user_id)
    else:
        bot.send_message(call.message.chat.id, "❌ چرخش ناموفق بود.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(call.message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard())


# ---------- واترمارک ----------
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdf_watermark_text"
        and m.text
)
def pdf_watermark_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("input_path")
    text = message.text.strip()

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ فایل پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال اعمال واترمارک...")
    output = add_watermark(path, text)
    _send_result(message.chat.id, user_id, output, "💧 <b>واترمارک اعمال شد!</b>", "watermark")
    delete_file(path)


# ---------- توابع کمکی ----------
def _send_result(chat_id, user_id: int, output_path: str, caption: str, op_name: str):
    try:
        if not output_path or not os.path.exists(output_path):
            bot.send_message(chat_id, "❌ پردازش ناموفق بود.")
            return

        size = os.path.getsize(output_path)
        with open(output_path, "rb") as f:
            bot.send_document(
                chat_id, f,
                caption=f"{caption}\n📊 حجم: {human_size(size)}",
                parse_mode='HTML'
            )
        _log_operation(user_id, f"pdf_{op_name}", "pdf", "pdf", size)
        mark_user_used(user_id)
    except Exception as e:
        logger.exception(f"خطا در ارسال نتیجه: {e}")
        bot.send_message(chat_id, f"❌ خطا: {e}")
    finally:
        if output_path:
            delete_file(output_path)
        clear_state(user_id)
        bot.send_message(chat_id, "منوی اصلی:", reply_markup=main_menu_keyboard())


def _cleanup_user_files(user_id: int):
    state = get_state(user_id)
    for p in state.get("files", []):
        delete_file(p)
    if state.get("input_path"):
        delete_file(state["input_path"])


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