## 📝 فایل ۲: `README_FA.md` (فارسی — آپدیت‌شده)

```markdown
# 🤖 ربات FormatMaster

یک ربات تلگرام چندکاره برای تبدیل، پردازش و دانلود فایل‌ها.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Twitter](https://img.shields.io/badge/Twitter-@Mpyj__X-1DA1F2?logo=x)](https://x.com/Mpyj_X)
[![GitHub](https://img.shields.io/badge/GitHub-@Mpyj-181717?logo=github)](https://github.com/Mpyj)
[![Telegram](https://img.shields.io/badge/Telegram-@MpyjTelegram-26A5E4?logo=telegram)](https://t.me/MpyjTelegram)

> 📖 **نسخه فارسی** | [**English**](README.md)

---

## ✨ قابلیت‌ها

### 📄 صفحه ۱ (قابلیت‌های اصلی)

| قابلیت | توضیح |
|---|---|
| 🖼️ **ابزار عکس** | تبدیل (JPG/PNG/WEBP/PDF)، تغییر اندازه، ۱۰ افکت، واترمارک |
| 📄 **استخراج متن (OCR)** | متن از عکس — فارسی + انگلیسی با پیش‌پردازش هوشمند |
| 🗜️ **ساخت ZIP** | ترکیب چند فایل در یه ZIP |
| 🌐 **تحلیل سایت** | پینگ، گواهی SSL، موقعیت IP، وضعیت HTTP |
| 🌐 **ابزار شبکه** | WHOIS، DNS، اسکن پورت، جزئیات SSL، تست سرعت |
| 💰 **ابزار مالی** | قیمت ارز دیجیتال، نرخ ارز (دلاری/تومانی)، طلا، تبدیل تاریخ |
| 🛠 **ابزار متنی** | شمارش کلمات، تبدیل حروف، Base64، URL، ASCII Art |
| 📱 **ساخت QR Code** | با ۶ رنگ سفارشی |
| 📥 **دانلودر** | یوتیوب، اینستاگرام، تیک‌تاک، توییتر (X)، فیسبوک، Vimeo، Pinterest |
| 🎵 **تشخیص آهنگ** | شناسایی آهنگ با Shazam + دانلود خودکار از YouTube |

### 📄 صفحه ۲ (قابلیت‌های پیشرفته)

| قابلیت | توضیح |
|---|---|
| 🎵 **مبدل مدیا** | ویدیو → MP3/GIF، تبدیل فرمت، سرعت، پیچ، نرمالایز، برش |
| 🎬 **مدیا پیشرفته** | استخراج فریم، Thumbnail، تایم‌لپس، اسلایدشو، زیرنویس، موسیقی |
| 🎨 **تصویر پیشرفته** | پالت رنگ، کولاژ، HDR، بهبود کیفیت، افکت هنری |
| 📄 **ابزار PDF** | ادغام، تقسیم، قفل، باز کردن قفل، PDF ↔ عکس، فشرده‌سازی، واترمارک |
| 📑 **PDF پیشرفته** | شماره‌گذاری، جستجو، استخراج متن/عکس، حذف/مرتب‌سازی صفحات |
| 🎨 **جعبه خلاقیت** | تولید رمز قوی، ترجمه (۱۰ زبان)، متن → صوت، متن → عکس |
| 🎮 **سرگرمی** | تاس، سکه، جوک، فال حافظ، معما، جمله انگیزشی |

### 👑 پنل ادمین

- 📊 آمار کاربران و عملیات
- 📢 پیام همگانی
- 🚫 بن/آنبن کاربران
- 📥 خروجی CSV

---

## 🚀 نصب

### پیش‌نیازها

- **Python** 3.12+
- **PostgreSQL** 14+
- **FFmpeg**
- **Tesseract OCR** (با `fas.traineddata` برای فارسی)
- **Poppler** (برای تبدیل PDF به عکس)

### لینوکس (اوبونتو/دبیان)

```bash
# نصب وابستگی‌های سیستمی
sudo apt update
sudo apt install -y \
    python3.12 python3.12-venv \
    ffmpeg \
    tesseract-ocr tesseract-ocr-fas \
    poppler-utils \
    postgresql

# کلون و راه‌اندازی
git clone https://github.com/Mpyj/format_bot.git
cd format_bot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
ویندوز
powershell
# FFmpeg رو از https://www.gyan.dev/ffmpeg/builds/ نصب کن
# Tesseract رو از https://github.com/UB-Mannheim/tesseract/wiki نصب کن
# Poppler رو از https://github.com/oschwartz10612/poppler-windows/releases/ نصب کن

git clone https://github.com/Mpyj/format_bot.git
cd format_bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
پیکربندی
bash
cp .env.example .env
# فایل .env رو با مقادیر خودت پر کن
متغیرهای .env:

متغیر	توضیح
TELEGRAM_BOT_TOKEN	توکن ربات از @BotFather
DATABASE_URL	رشته اتصال PostgreSQL (async)
CHANNEL_ID	آیدی کانال تلگرام (با -100 شروع میشه)
CHANNEL_LINK	لینک کانال تلگرام
ADMIN_ID	آیدی عددی تلگرام خودت
اجرای لوکال
bash
python run_local.py
🌐 دیپلوی روی Railway
۱. پوش به GitHub
bash
git add .
git commit -m "Initial commit"
git push origin main
۲. ساخت پروژه در Railway
برو به railway.app

New Project → Deploy from GitHub repo

ریپوت رو انتخاب کن

۳. اضافه کردن PostgreSQL
توی پروژه → New → Database → PostgreSQL

صبر کن تا آماده بشه

۴. تنظیم Environment Variables
توی سرویس بات → Variables:

text
TELEGRAM_BOT_TOKEN = توکن_خودت
DATABASE_URL = ${{Postgres.DATABASE_URL}}
CHANNEL_ID = -1001234567890
CHANNEL_LINK = https://t.me/your_channel
ADMIN_ID = 123456789
۵. ساخت Domain
توی سرویس بات → Settings → Networking → Generate Domain

Railway خودش RAILWAY_PUBLIC_DOMAIN رو برای webhook ست می‌کنه.

🛠 تکنولوژی‌ها
دسته	تکنولوژی
Backend	FastAPI + Uvicorn
Bot	pyTelegramBotAPI
Database	PostgreSQL + SQLAlchemy (async)
تصویر	Pillow, OpenCV
ویدیو/صدا	FFmpeg, ffmpeg-python
OCR	Tesseract (pytesseract)
PDF	pypdf, reportlab, pdf2image
دانلود	yt-dlp
تشخیص آهنگ	shazamio
TTS	gTTS, persian-speech
ترجمه	deep-translator
شبکه	python-whois, dnspython
📁 ساختار پروژه
text
format_bot/
├── main.py                    # اپ FastAPI + وبهوک
├── run_local.py               # اجرای لوکال (Polling)
├── config.py                  # تنظیمات
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
├── handlers/                  # هندلرهای بات
│   ├── start.py
│   ├── image.py
│   ├── ocr.py
│   ├── pdf.py
│   ├── pdf_advanced.py
│   ├── media.py
│   ├── advanced_media.py
│   ├── advanced_image.py
│   ├── network.py
│   ├── finance.py
│   ├── text_tools.py
│   ├── site.py
│   ├── archive.py
│   ├── creativity.py
│   ├── fun.py
│   ├── downloader.py
│   ├── song_recognition.py
│   ├── admin.py
│   └── middleware.py
├── utils/                     # ابزارها
│   ├── database.py
│   ├── models.py
│   ├── cleanup.py
│   ├── states.py
│   ├── keyboards.py
│   ├── file_info.py
│   ├── media_tools.py
│   ├── advanced_media.py
│   ├── advanced_image.py
│   ├── pdf_tools.py
│   ├── pdf_advanced.py
│   ├── network_tools.py
│   ├── finance_tools.py
│   ├── text_tools.py
│   ├── site_info.py
│   ├── qrcode_gen.py
│   ├── creative_tools.py
│   ├── fun_tools.py
│   ├── downloader.py
│   ├── song_recognition.py
│   └── admin_tools.py
└── temp/                      # فایل‌های موقت
🧪 نمونه استفاده
تبدیل عکس
text
/start → 🖼️ تبدیل عکس → عکس بفرست → فرمت انتخاب کن
استخراج متن از عکس
text
/start → 📄 استخراج متن → زبان انتخاب کن → عکس بفرست
دانلود از یوتیوب
text
/start → 📄 صفحه ۲ ➡️ → 📥 دانلودر → 🎬 یوتیوب → لینک بفرست → کیفیت انتخاب کن
تشخیص آهنگ
text
/start → 🎵 تشخیص آهنگ → فایل صوتی بفرست → اطلاعات آهنگ + دانلود خودکار
🔐 کنترل دسترسی
استفاده اول رایگان: هر قابلیت یک بار رایگان برای هر کاربر

عضویت کانال: بعد از اولین استفاده، کاربر باید عضو کانال بشه

سیستم بن: ادمین می‌تونه کاربران رو بن/آنبن کنه

پنل ادمین: فقط برای ADMIN_ID قابل دسترسه

📝 لایسنس
این پروژه تحت لایسنس MIT منتشر شده. برای جزئیات فایل LICENSE رو ببین.

👨‍💻 سازنده
Mpyj

https://img.shields.io/badge/Twitter-@Mpyj__X-1DA1F2?logo=x
https://img.shields.io/badge/GitHub-@Mpyj-181717?logo=github
https://img.shields.io/badge/Telegram-@MpyjTelegram-26A5E4?logo=telegram

🙏 تشکر
pyTelegramBotAPI

FastAPI

yt-dlp

ShazamIO

و همه مشارکت‌کنندگان اوپن‌سورس

⭐ حمایت
اگه از این پروژه خوشت اومد:

⭐ ستاره بده توی GitHub

🐦 فالو کن توی توییتر (X)

📱 عضو شو توی تلگرام

📞 تماس
🐦 توییتر (X): @Mpyj_X

💻 گیت‌هاب: @Mpyj

📱 تلگرام: @MpyjTelegram

⭐ اگه از این پروژه خوشت اومد، یه ستاره بده! ⭐
