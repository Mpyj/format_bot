from telebot import types
from main import bot
from config import ADMIN_ID
from utils.states import clear_state, get_state, set_state
from utils.keyboards import main_menu_keyboard


@bot.message_handler(commands=['start'])
def start_handler(message):
    user_id = message.from_user.id
    clear_state(user_id)
    set_state(user_id, menu_page=1)

    text = (
        f"سلام {message.from_user.first_name} عزیز! 👋\n\n"
        "من دستیار فایل‌های تو هستم.\n"
        "از منوی پایین یه گزینه انتخاب کن.\n\n"
        "🎁 <b>هر قابلیت یک بار رایگان!</b>\n\n"
        "⚠️ <b>اگه دکمه‌ای کار نکرد، ربات رو دوباره استارت کن</b> (دستور /start).\n\n"
        "━━━━━━━━━━━━━━━\n"
        "🌐 <b>ما رو دنبال کن:</b>\n"
        "🐦 @Mpyj_X | 💻 @Mpyj | 📱 @MpyjTelegram"
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
        "🎨 <b>تصویر پیشرفته</b> — پالت، کولاژ، HDR\n"
        "📄 <b>ابزار PDF</b> — ادغام، تقسیم، قفل\n"
        "📑 <b>PDF پیشرفته</b> — شماره، جستجو، استخراج\n"
        "🎨 <b>جعبه خلاقیت</b> — رمز، ترجمه، TTS\n"
        "🎮 <b>سرگرمی</b> — تاس، جوک، فال حافظ",
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
        "📱 <b>ساخت QR Code</b> — ۶ رنگ سفارشی\n"
        "📥 <b>دانلودر</b> — یوتیوب، اینستاگرام، ...\n"
        "🎵 <b>تشخیص آهنگ</b> — Shazam + دانلود خودکار",
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(user_id, page=1)
    )


# ============================================================
# 📖 راهنما
# ============================================================
@bot.message_handler(func=lambda m: m.text == 'ℹ️ راهنما')
def help_handler(message):
    user_id = message.from_user.id
    set_state(user_id, menu_page=1)

    text = (
        "📖 <b>راهنمای ربات</b>\n"
        "━━━━━━━━━━━━━━━\n\n"

        "📄 <b>صفحه ۱ (قابلیت‌های اصلی):</b>\n\n"

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
        "   • ارز دیجیتال، نرخ ارز (دلاری/تومانی)، طلا\n"
        "   • تبدیل تاریخ، ماشین حساب\n\n"

        "🛠 <b>ابزار متنی</b>\n"
        "   • شمارش، تبدیل حروف، Base64، URL\n"
        "   • تحلیل، تبدیل اعداد، ASCII Art\n\n"

        "📱 <b>ساخت QR Code</b>\n"
        "   • با ۶ رنگ سفارشی\n\n"

        "📥 <b>دانلودر</b>\n"
        "   • یوتیوب، اینستاگرام، تیک‌تاک، توییتر (X)\n"
        "   • فیسبوک، Vimeo، Pinterest\n"
        "   • ویدیو (360p-1080p) یا فقط صدا (MP3)\n\n"

        "🎵 <b>تشخیص آهنگ</b>\n"
        "   • تشخیص با Shazam\n"
        "   • دانلود خودکار از YouTube\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "📄 <b>صفحه ۲ (قابلیت‌های پیشرفته):</b>\n\n"

        "🎵 <b>مبدل مدیا</b>\n"
        "   • ویدیو → MP3، GIF\n"
        "   • تبدیل فرمت (MP4/WEBM/MKV)\n"
        "   • تغییر سرعت، پیچ، نرمالایز، برش\n\n"

        "🎬 <b>مدیا پیشرفته</b>\n"
        "   • استخراج فریم، Thumbnail، تایم‌لپس\n"
        "   • افزودن زیرنویس (SRT)، موسیقی\n"
        "   • ساخت ویدیو از عکس (اسلایدشو)\n"
        "   • ترکیب ۲ ویدیو، حذف صدا\n"
        "   • افزایش صدا، Reverb، تغییر سرعت صدا\n"
        "   • نمودار موج صدا\n\n"

        "🎨 <b>تصویر پیشرفته</b>\n"
        "   • پالت رنگ، تاریخچه رنگ\n"
        "   • چرخش خودکار، بهبود کیفیت، HDR\n"
        "   • کولاژ (ترکیب عکس‌ها)\n"
        "   • افزودن فریم، افکت هنری\n"
        "   • برش هوشمند، عکس → GIF\n\n"

        "📄 <b>ابزار PDF</b>\n"
        "   • ادغام، تقسیم PDF\n"
        "   • قفل / باز کردن قفل\n"
        "   • PDF → عکس، عکس → PDF\n"
        "   • فشرده‌سازی، چرخش، واترمارک\n"
        "   • اطلاعات PDF\n\n"

        "📑 <b>PDF پیشرفته</b>\n"
        "   • 📝 شماره صفحه (۴ موقعیت)\n"
        "   • 🔍 جستجو در PDF\n"
        "   • 📋 استخراج متن\n"
        "   • 🖼️ استخراج عکس‌ها\n"
        "   • ✂️ حذف صفحات\n"
        "   • 🔄 مرتب‌سازی صفحات\n"
        "   • 💧 واترمارک عکس\n"
        "   • 📊 آمار PDF\n\n"

        "🎨 <b>جعبه خلاقیت</b>\n"
        "   • تولید رمز قوی\n"
        "   • ترجمه (۱۰ زبان)\n"
        "   • متن → صوت (فارسی/انگلیسی)\n"
        "   • متن → عکس\n"
        "   • واترمارک عکس\n\n"

        "🎮 <b>سرگرمی</b>\n"
        "   • تاس، سکه، عدد تصادفی\n"
        "   • قرعه‌کشی، جوک\n"
        "   • فال حافظ، معما\n"
        "   • جمله انگیزشی، رنگ تصادفی\n"
        "   • امروز (تاریخ)، چی بخوریم؟\n\n"

        "━━━━━━━━━━━━━━━\n"

        "⚠️ <b>نکات مهم:</b>\n\n"

        "🔹 <b>اگه دکمه‌ای کار نکرد:</b>\n"
        "   دستور /start رو بزن تا ربات ریست بشه.\n\n"

        "🔹 <b>محدودیت استفاده:</b>\n"
        "   هر قابلیت یک بار رایگان.\n"
        "   برای استفاده بیشتر، عضو کانال ما شوید.\n\n"

        "🔹 <b>حداکثر حجم فایل:</b>\n"
        "   ۲۰ مگابایت (برای دانلودر: ۴۸ مگابایت)\n\n"

        "━━━━━━━━━━━━━━━\n\n"

        "🌐 <b>ما رو دنبال کن:</b>\n"
        "🐦 توییتر (X): @Mpyj_X\n"
        "💻 گیت‌هاب: @Mpyj\n"
        "📱 تلگرام: @MpyjTelegram\n\n"

        "━━━━━━━━━━━━━━━\n"

        "🎁 <b>هر قابلیت یک بار رایگان!</b>"
    )
    bot.send_message(
        message.chat.id,
        text,
        parse_mode='HTML',
        reply_markup=main_menu_keyboard(user_id, page=1)
    )


# 👑 هندلر دکمه ادمین
@bot.message_handler(
    func=lambda m: m.text == '👑 پنل ادمین' and m.from_user.id == ADMIN_ID
)
def admin_button(message):
    from handlers.admin import admin_panel
    admin_panel(message)