from telebot import types
from main import bot
from config import ADMIN_ID
from utils.states import clear_state
from utils.keyboards import main_menu_keyboard


@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id

    # 👇 کل state کاربر رو پاک کن
    clear_state(user_id)

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
        reply_markup=main_menu_keyboard(user_id),
        parse_mode='HTML'
    )


@bot.message_handler(func=lambda m: m.text == 'ℹ️ راهنما')
def help_handler(message):
    text = (
        "📖 <b>راهنمای ربات</b>\n"
        "━━━━━━━━━━━━━━━\n\n"

        "🖼️ <b>تبدیل عکس</b>\n"
        "   • تبدیل فرمت: JPG / PNG / WEBP / PDF\n"
        "   • تغییر اندازه (درصد یا پیکسل)\n"
        "   • ۱۰ افکت (سیاه‌سفید، سپیا، بلور، ...)\n"
        "   • واترمارک متنی\n\n"

        "📄 <b>استخراج متن (OCR)</b>\n"
        "   • متن رو از عکس بکش\n"
        "   • فارسی + انگلیسی\n"
        "   • پیش‌پردازش هوشمند\n\n"

        "🗜️ <b>ساخت ZIP</b>\n"
        "   • چند فایل بفرست → یه ZIP بگیر\n\n"

        "🌐 <b>تحلیل سایت</b>\n"
        "   • 📡 پینگ سرور\n"
        "   • 🔒 گواهی SSL + تاریخ انقضا\n"
        "   • 🌍 موقعیت IP + ISP\n"
        "   • 📊 وضعیت HTTP + زمان پاسخ\n\n"

        "🌐 <b>ابزار شبکه</b>\n"
        "   • 🔍 WHOIS — مالک دامنه، تاریخ ثبت\n"
        "   • 📡 DNS — A، MX، NS، TXT\n"
        "   • 🚪 اسکن پورت — پورت‌های باز\n"
        "   • 🔒 SSL — گواهی و cipher\n"
        "   • 📶 تست سرعت — سرعت دانلود\n\n"

        "💰 <b>ابزار مالی</b>\n"
        "   • 💵 ارز دیجیتال (BTC، ETH، ...)\n"
        "   • 💱 نرخ ارز (دلاری و تومانی)\n"
        "   • 🥇 طلا و سکه\n"
        "   • 📅 تبدیل تاریخ (شمسی ↔ میلادی ↔ قمری)\n"
        "   • 🧮 ماشین حساب\n\n"

        "🛠 <b>ابزار متنی</b>\n"
        "   • 🔤 شمارش کلمات\n"
        "   • 🔄 تبدیل حالت حروف\n"
        "   • 🎭 استایل یونیکد\n"
        "   • 🔁 Reverse\n"
        "   • 🧹 پاک‌سازی متن\n"
        "   • 📊 تحلیل متن\n"
        "   • 🔐 Base64 (Encode / Decode)\n"
        "   • 🔗 URL (Encode / Decode)\n"
        "   • 🔢 تبدیل اعداد\n"
        "   • 🎨 ASCII Art\n\n"

        "📱 <b>ساخت QR Code</b>\n"
        "   • لینک، متن، شماره، ایمیل → QR\n"
        "   • 🎨 ۶ رنگ سفارشی\n\n"

        "🎵 <b>مبدل مدیا</b>\n"
        "   • 🎵 ویدیو → MP3\n"
        "   • 🎬 ویدیو → GIF\n"
        "   • 📼 تبدیل فرمت (MP4/WEBM/MKV/AVI/MOV)\n"
        "   • 🎵 صوت → MP3/WAV/OGG/M4A\n"
        "   • 🎚 تغییر سرعت (0.5x تا 3x)\n"
        "   • 🎼 تغییر پیچ صدا\n"
        "   • 📊 نرمالایز کردن\n"
        "   • 🔄 برعکس کردن\n"
        "   • ✂️ برش\n\n"

        "📄 <b>ابزار PDF</b>\n"
        "   • 🔗 ادغام چند PDF\n"
        "   • ✂️ تقسیم PDF\n"
        "   • 🔒 قفل / 🔓 باز کردن قفل\n"
        "   • 📷 PDF → عکس\n"
        "   • 📄 عکس → PDF\n"
        "   • 📉 فشرده‌سازی\n"
        "   • 🔄 چرخش\n"
        "   • 💧 واترمارک\n"
        "   • ℹ️ اطلاعات PDF\n\n"

        "🎨 <b>جعبه خلاقیت</b>\n"
        "   • 🔐 تولید رمز قوی\n"
        "   • 🌍 ترجمه (۱۰ زبان)\n"
        "   • 🔊 متن → صوت (فارسی/انگلیسی)\n"
        "   • 🎨 متن → عکس\n"
        "   • 💧 واترمارک عکس\n\n"

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