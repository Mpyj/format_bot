from telebot import types
from main import bot
from config import ADMIN_ID
from utils.states import clear_state, get_state, set_state
from utils.keyboards import main_menu_keyboard


@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id

    # 👇 کل state کاربر رو پاک کن
    clear_state(user_id)
    set_state(user_id, menu_page=1)

    text = (
        f"سلام {message.from_user.first_name} عزیز! 👋\n\n"
        "من دستیار فایل‌های تو هستم.\n"
        "از منوی پایین یه گزینه انتخاب کن.\n\n"
        "🎁 <b>هر قابلیت یک بار رایگان!</b>\n\n"
        "⚠️ <b>اگه دکمه‌ای کار نکرد، ربات رو دوباره استارت کن</b> (دستور /start)."
    )
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu_keyboard(user_id, page=1),
        parse_mode='HTML'
    )


# ============================================================
# 🔄 ناوبری بین صفحه‌ها
# ============================================================
@bot.message_handler(func=lambda m: m.text == '📄 صفحه ۲ ➡️')
def go_to_page_2(message):
    user_id = message.from_user.id
    set_state(user_id, menu_page=2)

    bot.send_message(
        message.chat.id,
        "📄 <b>صفحه ۲</b>\n\n"
        "🎵 <b>مبدل مدیا</b> — MP3، GIF، فرمت، سرعت\n"
        "🎬 <b>مدیا پیشرفته</b> — فریم، زیرنویس، تایم‌لپس\n"
        "📄 <b>ابزار PDF</b> — ادغام، تقسیم، قفل\n"
        "🎨 <b>جعبه خلاقیت</b> — رمز، ترجمه، TTS",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(user_id, page=2)
    )


@bot.message_handler(func=lambda m: m.text == '⬅️ صفحه ۱')
def go_to_page_1(message):
    user_id = message.from_user.id
    set_state(user_id, menu_page=1)

    bot.send_message(
        message.chat.id,
        "📄 <b>صفحه ۱</b>\n\n"
        "🖼️ <b>تبدیل عکس</b> — فرمت، اندازه، افکت\n"
        "📄 <b>استخراج متن</b> — OCR فارسی/انگلیسی\n"
        "🗜️ <b>ساخت ZIP</b> — چند فایل → ZIP\n"
        "🌐 <b>تحلیل سایت</b> — پینگ، SSL، IP\n"
        "🌐 <b>ابزار شبکه</b> — WHOIS، DNS، پورت\n"
        "💰 <b>ابزار مالی</b> — ارز، طلا، تاریخ\n"
        "🛠 <b>ابزار متنی</b> — شمارش، Base64، ASCII\n"
        "📱 <b>ساخت QR Code</b> — ۶ رنگ سفارشی",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(user_id, page=1)
    )


@bot.message_handler(func=lambda m: m.text == 'ℹ️ راهنما')
def help_handler(message):
    text = (
        "📖 <b>راهنمای ربات</b>\n"
        "━━━━━━━━━━━━━━━\n\n"

        "📄 <b>صفحه ۱:</b>\n\n"

        "🖼️ <b>تبدیل عکس</b>\n"
        "   • تبدیل فرمت: JPG / PNG / WEBP / PDF\n"
        "   • تغییر اندازه، افکت، واترمارک\n\n"

        "📄 <b>استخراج متن (OCR)</b>\n"
        "   • فارسی + انگلیسی\n\n"

        "🗜️ <b>ساخت ZIP</b>\n"
        "   • چند فایل → یه ZIP\n\n"

        "🌐 <b>تحلیل سایت</b>\n"
        "   • پینگ، SSL، IP، HTTP\n\n"

        "🌐 <b>ابزار شبکه</b>\n"
        "   • WHOIS، DNS، اسکن پورت، SSL، تست سرعت\n\n"

        "💰 <b>ابزار مالی</b>\n"
        "   • ارز دیجیتال، نرخ ارز، طلا، تاریخ، ماشین حساب\n\n"

        "🛠 <b>ابزار متنی</b>\n"
        "   • شمارش، تبدیل، Base64، URL، ASCII Art\n\n"

        "📱 <b>ساخت QR Code</b>\n"
        "   • با ۶ رنگ سفارشی\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "📄 <b>صفحه ۲:</b>\n\n"

        "🎵 <b>مبدل مدیا</b>\n"
        "   • MP3، GIF، فرمت، سرعت، پیچ، برش\n\n"

        "🎬 <b>مدیا پیشرفته</b>\n"
        "   • استخراج فریم، زیرنویس، تایم‌لپس\n\n"

        "📄 <b>ابزار PDF</b>\n"
        "   • ادغام، تقسیم، قفل، عکس↔PDF، واترمارک\n\n"

        "🎨 <b>جعبه خلاقیت</b>\n"
        "   • رمز قوی، ترجمه، TTS، متن→عکس\n\n"

        "━━━━━━━━━━━━━━━\n"

        "⚠️ <b>نکات مهم:</b>\n\n"

        "🔹 <b>اگه دکمه‌ای کار نکرد:</b>\n"
        "   دستور /start رو بزن تا ربات ریست بشه.\n"
        "   این اتفاق ممکنه وقتی بیفته که یه عملیات\n"
        "   نیمه‌کاره مونده باشه.\n\n"

        "🔹 <b>محدودیت استفاده:</b>\n"
        "   هر قابلیت یک بار رایگان.\n"
        "   برای استفاده بیشتر، عضو کانال ما شوید.\n\n"

        "🔹 <b>حداکثر حجم فایل:</b>\n"
        "   ۲۰ مگابایت\n\n"

        "🎁 <b>هر قابلیت یک بار رایگان!</b>"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# 👑 هندلر دکمه ادمین
@bot.message_handler(
    func=lambda m: m.text == '👑 پنل ادمین' and m.from_user.id == ADMIN_ID
)
def admin_button(message):
    from handlers.admin import admin_panel
    admin_panel(message)