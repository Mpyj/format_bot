from telebot import types
from main import bot
from config import ADMIN_ID
from utils.keyboards import main_menu_keyboard


@bot.message_handler(commands=['start'])
def start_handler(message):
    text = (
        f"سلام {message.from_user.first_name} عزیز! 👋\n\n"
        "من دستیار فایل‌های تو هستم.\n"
        "از منوی پایین یه گزینه انتخاب کن.\n\n"
        "🎁 <b>هر قابلیت یک بار رایگان!</b>"
    )
    bot.send_message(
        message.chat.id,
        text,
        reply_markup=main_menu_keyboard(message.from_user.id),
        parse_mode='HTML'
    )


@bot.message_handler(func=lambda m: m.text == 'ℹ️ راهنما')
def help_handler(message):
    text = (
        "📖 <b>راهنمای ربات</b>\n"
        "━━━━━━━━━━━━━━━\n\n"

        "🖼️ <b>تبدیل عکس</b>\n"
        "   • تبدیل فرمت: JPG / PNG / WEBP / PDF\n"
        "   • تغییر اندازه\n"
        "   • ۱۰ افکت\n"
        "   • واترمارک\n\n"

        "📄 <b>استخراج متن (OCR)</b>\n"
        "   • فارسی + انگلیسی\n\n"

        "🗜️ <b>ساخت ZIP</b>\n"
        "   • چند فایل → یه ZIP\n\n"

        "🌐 <b>تحلیل سایت</b>\n"
        "   • پینگ، SSL، IP، HTTP\n\n"

        "📱 <b>ساخت QR Code</b>\n"
        "   • با ۶ رنگ سفارشی\n\n"

        "🎵 <b>مبدل مدیا</b>\n"
        "   • MP3، GIF، فرمت‌ها\n"
        "   • سرعت، پیچ، نرمالایز، برش\n\n"

        "📄 <b>ابزار PDF</b>\n"
        "   • ادغام، تقسیم، قفل\n"
        "   • عکس ↔ PDF، فشرده‌سازی\n"
        "   • واترمارک، چرخش\n\n"

        "🎨 <b>جعبه خلاقیت</b>\n"
        "   • رمز قوی، ترجمه\n"
        "   • متن → صوت، متن → عکس\n"
        "   • واترمارک عکس\n\n"

        "━━━━━━━━━━━━━━━\n"
        "🎁 <b>هر قابلیت یک بار رایگان!</b>\n"
        "برای استفاده بیشتر، عضو کانال ما شوید.\n\n"
        "⚠️ حداکثر حجم هر فایل: ۲۰ مگابایت"
    )
    bot.send_message(message.chat.id, text, parse_mode='HTML')


# 👑 هندلر دکمه ادمین
@bot.message_handler(
    func=lambda m: m.text == '👑 پنل ادمین' and m.from_user.id == ADMIN_ID
)
def admin_button(message):
    from handlers.admin import admin_panel
    admin_panel(message)