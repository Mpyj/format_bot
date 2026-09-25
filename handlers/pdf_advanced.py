import os
import uuid
import logging
from telebot import types

from main import bot
from config import TEMP_DIR
from utils.cleanup import delete_file
from utils.states import set_state, get_state, clear_state, is_menu_button
from utils.file_info import human_size
from utils.pdf_advanced import (
    add_page_numbers, search_pdf, extract_text, extract_images,
    delete_pages, reorder_pages, add_image_watermark, get_pdf_stats,
    parse_pages_input, parse_order_input,
)
from utils.keyboards import main_menu_keyboard
from handlers.middleware import mark_user_used

logger = logging.getLogger(__name__)


# ============================================================
# 🏠 منو
# ============================================================
def _pdf_menu(user_id: int = None):
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("📝 شماره صفحه", callback_data="pdfadv_numbers"),
        types.InlineKeyboardButton("🔍 جستجو", callback_data="pdfadv_search"),
    )
    markup.add(
        types.InlineKeyboardButton("📋 استخراج متن", callback_data="pdfadv_text"),
        types.InlineKeyboardButton("🖼️ استخراج عکس", callback_data="pdfadv_images"),
    )
    markup.add(
        types.InlineKeyboardButton("✂️ حذف صفحات", callback_data="pdfadv_delete"),
        types.InlineKeyboardButton("🔄 مرتب‌سازی", callback_data="pdfadv_reorder"),
    )
    markup.add(
        types.InlineKeyboardButton("💧 واترمارک عکس", callback_data="pdfadv_watermark"),
        types.InlineKeyboardButton("📊 آمار PDF", callback_data="pdfadv_stats"),
    )
    markup.add(types.InlineKeyboardButton("❌ بستن", callback_data="pdfadv_close"))
    return markup


def _back_markup():
    return types.InlineKeyboardMarkup().add(
        types.InlineKeyboardButton("🔙 بازگشت", callback_data="pdfadv_back")
    )


# ============================================================
# شروع
# ============================================================
@bot.message_handler(func=lambda m: m.text == '📄 PDF پیشرفته')
def pdf_adv_start(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, mode="pdf_adv", waiting_for=None)

    bot.send_message(
        message.chat.id,
        "📄 <b>PDF پیشرفته</b>\n\n"
        "📝 <b>شماره صفحه</b> — شماره‌گذاری\n"
        "🔍 <b>جستجو</b> — پیدا کردن کلمه\n"
        "📋 <b>استخراج متن</b> — متن رو بکش\n"
        "🖼️ <b>استخراج عکس</b> — عکس‌های داخل PDF\n"
        "✂️ <b>حذف صفحات</b> — صفحات خاص\n"
        "🔄 <b>مرتب‌سازی</b> — ترتیب دلخواه\n"
        "💧 <b>واترمارک عکس</b> — عکس روی PDF\n"
        "📊 <b>آمار PDF</b> — تعداد کلمات",
        parse_mode='HTML',
        reply_markup=_pdf_menu(user_id)
    )


# ============================================================
# callback
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pdfadv_"))
def pdf_adv_action(call):
    user_id = call.from_user.id
    action = call.data.replace("pdfadv_", "")

    if action == "back":
        bot.answer_callback_query(call.id)
        clear_state(user_id)
        set_state(user_id, mode="pdf_adv", waiting_for=None)
        try:
            bot.edit_message_text(
                "📄 <b>PDF پیشرفته</b>\n\nیه عملیات انتخاب کن:",
                call.message.chat.id, call.message.message_id,
                parse_mode='HTML', reply_markup=_pdf_menu(user_id)
            )
        except Exception:
            bot.send_message(
                call.message.chat.id,
                "📄 <b>PDF پیشرفته</b>",
                parse_mode='HTML', reply_markup=_pdf_menu(user_id)
            )
        return

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
        "numbers": "📝 <b>شماره صفحه</b>\n\nPDF رو بفرست:",
        "search": "🔍 <b>جستجو در PDF</b>\n\nPDF رو بفرست:",
        "text": "📋 <b>استخراج متن</b>\n\nPDF رو بفرست:",
        "images": "🖼️ <b>استخراج عکس</b>\n\nPDF رو بفرست:",
        "delete": "✂️ <b>حذف صفحات</b>\n\nPDF رو بفرست:",
        "reorder": "🔄 <b>مرتب‌سازی صفحات</b>\n\nPDF رو بفرست:",
        "watermark": "💧 <b>واترمارک عکس</b>\n\nاول PDF رو بفرست، بعد عکس:",
        "stats": "📊 <b>آمار PDF</b>\n\nPDF رو بفرست:",
    }

    set_state(user_id, mode="pdf_adv", pdfadv_action=action,
              waiting_for=f"pdfadv_{action}")

    try:
        bot.edit_message_text(
            hints.get(action, "PDF رو بفرست:"),
            call.message.chat.id, call.message.message_id,
            parse_mode='HTML', reply_markup=_back_markup()
        )
    except Exception:
        bot.send_message(
            call.message.chat.id,
            hints.get(action, "PDF رو بفرست:"),
            parse_mode='HTML', reply_markup=_back_markup()
        )


# ============================================================
# دریافت PDF
# ============================================================
@bot.message_handler(
    content_types=['document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for", "").startswith("pdfadv_")
        and get_state(m.from_user.id).get("mode") == "pdf_adv"
        and get_state(m.from_user.id).get("waiting_for") not in (
            "pdfadv_watermark_image",
        )
)
def pdf_adv_receive(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    action = state.get("pdfadv_action")

    fname = (message.document.file_name or "").lower()
    if not fname.endswith(".pdf"):
        bot.send_message(message.chat.id, "❌ فقط PDF قبول می‌کنم.")
        return

    try:
        file_info_tg = bot.get_file(message.document.file_id)
        downloaded = bot.download_file(file_info_tg.file_path)
        path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.pdf")
        with open(path, "wb") as f:
            f.write(downloaded)

        set_state(user_id, pdfadv_input_path=path)

        # بر اساس action
        if action == "numbers":
            set_state(user_id, waiting_for="pdfadv_numbers_position")
            markup = types.InlineKeyboardMarkup(row_width=2)
            markup.add(
                types.InlineKeyboardButton("⬇️ پایین وسط", callback_data="pdfnum_bottom-center"),
                types.InlineKeyboardButton("⬇️ پایین راست", callback_data="pdfnum_bottom-right"),
            )
            markup.add(
                types.InlineKeyboardButton("⬆️ بالا وسط", callback_data="pdfnum_top-center"),
                types.InlineKeyboardButton("⬆️ بالا راست", callback_data="pdfnum_top-right"),
            )
            bot.send_message(message.chat.id, "📍 موقعیت شماره:", reply_markup=markup)

        elif action == "search":
            set_state(user_id, waiting_for="pdfadv_search_query")
            bot.send_message(message.chat.id, "🔍 کلمه مورد نظر رو بفرست:")

        elif action == "text":
            _process_text(message, user_id, path)

        elif action == "images":
            _process_images(message, user_id, path)

        elif action == "delete":
            set_state(user_id, waiting_for="pdfadv_delete_pages")
            bot.send_message(
                message.chat.id,
                "✂️ شماره صفحات رو بفرست:\n\n"
                "💡 مثال:\n"
                "<code>1,3,5</code>\n"
                "<code>2-5</code>\n"
                "<code>1,3-5,8</code>",
                parse_mode='HTML'
            )

        elif action == "reorder":
            set_state(user_id, waiting_for="pdfadv_reorder_pages")
            bot.send_message(
                message.chat.id,
                "🔄 ترتیب جدید رو بفرست:\n\n"
                "💡 مثال:\n"
                "<code>3,1,2,4,5</code>\n\n"
                "یعنی: صفحه ۳ اول، بعد ۱، بعد ۲، ...",
                parse_mode='HTML'
            )

        elif action == "watermark":
            set_state(user_id, waiting_for="pdfadv_watermark_image")
            bot.send_message(message.chat.id, "💧 الان عکس واترمارک رو بفرست:")

        elif action == "stats":
            _process_stats(message, user_id, path)

    except Exception as e:
        logger.exception("خطا")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")
        clear_state(user_id)


# ============================================================
# 📝 شماره صفحه — انتخاب موقعیت
# ============================================================
@bot.callback_query_handler(func=lambda c: c.data.startswith("pdfnum_"))
def pdf_numbers_position(call):
    user_id = call.from_user.id
    state = get_state(user_id)
    path = state.get("pdfadv_input_path")
    position = call.data.replace("pdfnum_", "")

    if not path or not os.path.exists(path):
        bot.answer_callback_query(call.id, "PDF پیدا نشد", show_alert=True)
        clear_state(user_id)
        return

    bot.answer_callback_query(call.id, "در حال شماره‌گذاری...")
    bot.edit_message_text(
        "⏳ در حال شماره‌گذاری...",
        call.message.chat.id, call.message.message_id
    )

    output = add_page_numbers(path, start=1, position=position)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                call.message.chat.id, f,
                caption=f"📝 <b>شماره‌گذاری شد</b>\n📊 {human_size(size)}",
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
# 🔍 جستجو
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdfadv_search_query"
        and get_state(m.from_user.id).get("mode") == "pdf_adv"
        and m.text
        and not is_menu_button(m.text)
)
def pdf_search_query(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("pdfadv_input_path")
    query = message.text.strip()

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ PDF پیدا نشد.")
        clear_state(user_id)
        return

    bot.send_message(message.chat.id, "⏳ در حال جستجو...")

    result = search_pdf(path, query)

    if not result.get("success"):
        bot.send_message(message.chat.id, f"❌ خطا: {result.get('error')}")
    else:
        if result["found_pages"] == 0:
            bot.send_message(
                message.chat.id,
                f"🔍 <b>جستجو: {query}</b>\n\n"
                f"❌ توی {result['total_pages']} صفحه پیدا نشد.",
                parse_mode='HTML'
            )
        else:
            text = (
                f"🔍 <b>جستجو: {query}</b>\n"
                f"━━━━━━━━━━━━━━━\n\n"
                f"📄 <b>کل صفحات:</b> {result['total_pages']}\n"
                f"✅ <b>صفحات با نتیجه:</b> {result['found_pages']}\n\n"
            )

            for r in result["results"][:10]:
                text += f"📌 <b>صفحه {r['page']}</b> ({r['count']} بار)\n"
                for snippet in r["snippets"][:2]:
                    # escape
                    snippet_safe = snippet.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
                    text += f"   <i>...{snippet_safe}...</i>\n"
                text += "\n"

            bot.send_message(message.chat.id, text, parse_mode='HTML')
            mark_user_used(user_id)

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📋 استخراج متن
# ============================================================
def _process_text(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال استخراج متن...")
    text = extract_text(path)

    if text:
        # اگه طولانی بود، فایل بفرست
        if len(text) > 4000:
            txt_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}.txt")
            with open(txt_path, "w", encoding="utf-8") as f:
                f.write(text)
            with open(txt_path, "rb") as f:
                bot.send_document(
                    message.chat.id, f,
                    caption=f"📋 <b>متن استخراج شد</b>\n📊 {human_size(len(text))}",
                    parse_mode='HTML'
                )
            delete_file(txt_path)
        else:
            text_safe = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
            bot.send_message(
                message.chat.id,
                f"📋 <b>متن استخراج شد:</b>\n\n<pre>{text_safe}</pre>",
                parse_mode='HTML'
            )
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ متنی پیدا نشد یا خطا داد.")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🖼️ استخراج عکس
# ============================================================
def _process_images(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال استخراج عکس‌ها...")
    images = extract_images(path)

    if not images:
        bot.send_message(message.chat.id, "❌ عکسی توی PDF پیدا نشد.")
    else:
        count = len(images)
        bot.send_message(message.chat.id, f"✅ {count} عکس پیدا شد. در حال ارسال...")

        for i, img_path in enumerate(images, 1):
            try:
                with open(img_path, "rb") as f:
                    bot.send_photo(
                        message.chat.id, f,
                        caption=f"🖼️ عکس {i}/{count}"
                    )
            except Exception as e:
                logger.warning(f"خطا در ارسال عکس {i}: {e}")
            finally:
                delete_file(img_path)

        mark_user_used(user_id)

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# ✂️ حذف صفحات
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdfadv_delete_pages"
        and get_state(m.from_user.id).get("mode") == "pdf_adv"
        and m.text
        and not is_menu_button(m.text)
)
def pdf_delete_pages(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("pdfadv_input_path")
    pages = parse_pages_input(message.text.strip())

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ PDF پیدا نشد.")
        clear_state(user_id)
        return

    if not pages:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه. مثال: <code>1,3,5</code>", parse_mode='HTML')
        return

    bot.send_message(message.chat.id, f"⏳ در حال حذف {len(pages)} صفحه...")

    output = delete_pages(path, pages)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                message.chat.id, f,
                caption=f"✂️ <b>صفحات حذف شد</b>\n📊 {human_size(size)}",
                parse_mode='HTML'
            )
        delete_file(output)
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, "❌ حذف ناموفق بود (شماره‌ها رو چک کن).")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 🔄 مرتب‌سازی
# ============================================================
@bot.message_handler(
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdfadv_reorder_pages"
        and get_state(m.from_user.id).get("mode") == "pdf_adv"
        and m.text
        and not is_menu_button(m.text)
)
def pdf_reorder_pages(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    path = state.get("pdfadv_input_path")
    order = parse_order_input(message.text.strip())

    if not path or not os.path.exists(path):
        bot.send_message(message.chat.id, "❌ PDF پیدا نشد.")
        clear_state(user_id)
        return

    if not order:
        bot.send_message(message.chat.id, "❌ فرمت اشتباه. مثال: <code>3,1,2,4</code>", parse_mode='HTML')
        return

    bot.send_message(message.chat.id, "⏳ در حال مرتب‌سازی...")

    output = reorder_pages(path, order)

    if output and os.path.exists(output):
        size = os.path.getsize(output)
        with open(output, "rb") as f:
            bot.send_document(
                message.chat.id, f,
                caption=f"🔄 <b>مرتب‌سازی شد</b>\n📊 {human_size(size)}",
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
# 💧 واترمارک عکس — دریافت عکس
# ============================================================
@bot.message_handler(
    content_types=['photo', 'document'],
    func=lambda m: get_state(m.from_user.id).get("waiting_for") == "pdfadv_watermark_image"
        and get_state(m.from_user.id).get("mode") == "pdf_adv"
)
def pdf_watermark_receive_image(message):
    user_id = message.from_user.id
    state = get_state(user_id)
    pdf_path = state.get("pdfadv_input_path")

    if not pdf_path or not os.path.exists(pdf_path):
        bot.send_message(message.chat.id, "❌ PDF پیدا نشد.")
        clear_state(user_id)
        return

    try:
        if message.content_type == 'photo':
            file_info_tg = bot.get_file(message.photo[-1].file_id)
        else:
            file_info_tg = bot.get_file(message.document.file_id)

        downloaded = bot.download_file(file_info_tg.file_path)
        ext = os.path.splitext(file_info_tg.file_path)[1] or ".jpg"
        img_path = os.path.join(TEMP_DIR, f"{uuid.uuid4().hex}{ext}")
        with open(img_path, "wb") as f:
            f.write(downloaded)

        bot.send_message(message.chat.id, "⏳ در حال اعمال واترمارک...")

        output = add_image_watermark(pdf_path, img_path, opacity=0.3, position="center")

        if output and os.path.exists(output):
            size = os.path.getsize(output)
            with open(output, "rb") as f:
                bot.send_document(
                    message.chat.id, f,
                    caption=f"💧 <b>واترمارک اعمال شد</b>\n📊 {human_size(size)}",
                    parse_mode='HTML'
                )
            delete_file(output)
            mark_user_used(user_id)
        else:
            bot.send_message(message.chat.id, "❌ ناموفق بود.")

        delete_file(img_path)

    except Exception as e:
        logger.exception("خطا در واترمارک")
        bot.send_message(message.chat.id, f"❌ خطا: {e}")

    delete_file(pdf_path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))


# ============================================================
# 📊 آمار PDF
# ============================================================
def _process_stats(message, user_id: int, path: str):
    bot.send_message(message.chat.id, "⏳ در حال تحلیل PDF...")
    result = get_pdf_stats(path)

    if result.get("success"):
        text = (
            f"📊 <b>آمار PDF</b>\n"
            f"━━━━━━━━━━━━━━━\n\n"
            f"📄 <b>صفحات:</b> {result['pages']:,}\n"
            f"📝 <b>کلمات:</b> {result['words']:,}\n"
            f"📏 <b>خطوط:</b> {result['lines']:,}\n"
            f"📊 <b>میانگین کلمات/صفحه:</b> {result['avg_words_per_page']:.0f}\n"
            f"📊 <b>میانگین کاراکتر/صفحه:</b> {result['avg_chars_per_page']:.0f}\n"
            f"💾 <b>حجم:</b> {human_size(result['size'])}\n"
            f"🔒 <b>رمزدار:</b> {'✅' if result['encrypted'] else '❌'}\n"
        )

        if result.get("title"):
            text += f"\n📝 <b>عنوان:</b> {result['title'][:100]}\n"
        if result.get("author"):
            text += f"👤 <b>نویسنده:</b> {result['author'][:100]}\n"
        if result.get("creator"):
            text += f"🛠 <b>سازنده:</b> {result['creator'][:100]}\n"

        if result.get("note"):
            text += f"\n⚠️ {result['note']}"

        bot.send_message(message.chat.id, text, parse_mode='HTML')
        mark_user_used(user_id)
    else:
        bot.send_message(message.chat.id, f"❌ خطا: {result.get('error')}")

    delete_file(path)
    clear_state(user_id)
    bot.send_message(message.chat.id, "منوی اصلی:", reply_markup=main_menu_keyboard(user_id))