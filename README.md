# 🤖 FormatMaster Bot

A multi-purpose Telegram bot for file conversion, processing, and downloading.

[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-blue.svg)](https://core.telegram.org/bots)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

[![Twitter](https://img.shields.io/badge/Twitter-@Mpyj__X-1DA1F2?logo=x)](https://x.com/Mpyj_X)
[![GitHub](https://img.shields.io/badge/GitHub-@Mpyj-181717?logo=github)](https://github.com/Mpyj)
[![Telegram](https://img.shields.io/badge/Telegram-@MpyjTelegram-26A5E4?logo=telegram)](https://t.me/MpyjTelegram)

> 📖 [**نسخه فارسی**](README_FA.md) | **English**

---

## ✨ Features

### 📄 Page 1 (Main Features)

| Feature | Description |
|---|---|
| 🖼️ **Image Tools** | Convert (JPG/PNG/WEBP/PDF), resize, 10 effects, watermark |
| 📄 **OCR** | Extract text from images (Persian + English) with smart preprocessing |
| 🗜️ **ZIP Creator** | Combine multiple files into one ZIP |
| 🌐 **Site Analyzer** | Ping, SSL certificate, IP geolocation, HTTP status |
| 🌐 **Network Tools** | WHOIS, DNS lookup, port scan, SSL details, speed test |
| 💰 **Finance Tools** | Crypto prices, currency rates (USD/IRR), gold, date converter |
| 🛠 **Text Tools** | Word count, case convert, Base64, URL encode/decode, ASCII art |
| 📱 **QR Generator** | Generate QR codes with 6 custom colors |
| 📥 **Downloader** | YouTube, Instagram, TikTok, Twitter (X), Facebook, Vimeo, Pinterest |
| 🎵 **Song Recognition** | Identify songs via Shazam + auto-download from YouTube |

### 📄 Page 2 (Advanced Features)

| Feature | Description |
|---|---|
| 🎵 **Media Converter** | Video → MP3/GIF, format conversion, speed, pitch, normalize, trim |
| 🎬 **Advanced Media** | Extract frame, thumbnail, timelapse, slideshow, subtitles, music |
| 🎨 **Advanced Image** | Color palette, collage, HDR, enhance quality, artistic effects |
| 📄 **PDF Tools** | Merge, split, lock, unlock, PDF ↔ Image, compress, watermark |
| 📑 **Advanced PDF** | Page numbering, search, extract text/images, delete/reorder pages |
| 🎨 **Creativity Box** | Password generator, translation (10 langs), TTS, text-to-image |
| 🎮 **Fun** | Dice, coin, jokes, Hafez fal, riddles, motivational quotes |

### 👑 Admin Panel

- 📊 User and operation statistics
- 📢 Broadcast messages
- 🚫 Ban/Unban users
- 📥 CSV export

---

## 🚀 Installation

### Prerequisites

- **Python** 3.12+
- **PostgreSQL** 14+
- **FFmpeg**
- **Tesseract OCR** (with `fas.traineddata` for Persian)
- **Poppler** (for PDF to image conversion)

### Linux (Ubuntu/Debian)

```bash
# System dependencies
sudo apt update
sudo apt install -y \
    python3.12 python3.12-venv \
    ffmpeg \
    tesseract-ocr tesseract-ocr-fas \
    poppler-utils \
    postgresql

# Clone and setup
git clone https://github.com/Mpyj/format_bot.git
cd format_bot
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
Windows
powershell
# Install FFmpeg from https://www.gyan.dev/ffmpeg/builds/
# Install Tesseract from https://github.com/UB-Mannheim/tesseract/wiki
# Install Poppler from https://github.com/oschwartz10612/poppler-windows/releases/

git clone https://github.com/Mpyj/format_bot.git
cd format_bot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
Configuration
bash
cp .env.example .env
# Edit .env with your values
.env variables:

Variable	Description
TELEGRAM_BOT_TOKEN	Bot token from @BotFather
DATABASE_URL	PostgreSQL connection string (async)
CHANNEL_ID	Telegram channel ID (starts with -100)
CHANNEL_LINK	Telegram channel link
ADMIN_ID	Your Telegram user ID
Run Locally
bash
python run_local.py
🌐 Deploy on Railway
1. Push to GitHub
bash
git add .
git commit -m "Initial commit"
git push origin main
2. Create Railway Project
Go to railway.app

New Project → Deploy from GitHub repo

Select your repository

3. Add PostgreSQL
In your project → New → Database → PostgreSQL

Wait for it to be ready

4. Set Environment Variables
In your bot service → Variables:

text
TELEGRAM_BOT_TOKEN = your_token
DATABASE_URL = ${{Postgres.DATABASE_URL}}
CHANNEL_ID = -1001234567890
CHANNEL_LINK = https://t.me/your_channel
ADMIN_ID = 123456789
5. Generate Domain
In your bot service → Settings → Networking → Generate Domain

Railway automatically sets RAILWAY_PUBLIC_DOMAIN for webhook.

🛠 Tech Stack
Category	Technology
Backend	FastAPI + Uvicorn
Bot	pyTelegramBotAPI
Database	PostgreSQL + SQLAlchemy (async)
Image	Pillow, OpenCV
Video/Audio	FFmpeg, ffmpeg-python
OCR	Tesseract (pytesseract)
PDF	pypdf, reportlab, pdf2image
Download	yt-dlp
Song Recognition	shazamio
TTS	gTTS, persian-speech
Translation	deep-translator
Network	python-whois, dnspython
📁 Project Structure
text
format_bot/
├── main.py                    # FastAPI app + webhook
├── run_local.py               # Local polling runner
├── config.py                  # Configuration
├── requirements.txt
├── Dockerfile
├── railway.toml
├── .env.example
├── handlers/                  # Bot handlers
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
├── utils/                     # Utilities
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
└── temp/                      # Temporary files
🧪 Usage Examples
Convert an image
text
/start → 🖼️ تبدیل عکس → Send image → Select format
Extract text from image
text
/start → 📄 استخراج متن → Select language → Send image
Download from YouTube
text
/start → 📄 صفحه ۲ ➡️ → 📥 دانلودر → 🎬 یوتیوب → Send link → Select quality
Recognize a song
text
/start → 🎵 تشخیص آهنگ → Send audio → Get song info + auto download
🔐 Access Control
First use free: Each feature is free once per user

Channel membership: After first use, users must join your channel

Ban system: Admin can ban/unban users

Admin panel: Only accessible to ADMIN_ID

📝 License
This project is licensed under the MIT License. See LICENSE file for details.

👨‍💻 Author
Mpyj

https://img.shields.io/badge/Twitter-@Mpyj__X-1DA1F2?logo=x
https://img.shields.io/badge/GitHub-@Mpyj-181717?logo=github
https://img.shields.io/badge/Telegram-@MpyjTelegram-26A5E4?logo=telegram

🙏 Acknowledgments
pyTelegramBotAPI

FastAPI

yt-dlp

ShazamIO

And all other open-source contributors

⭐ Support
If you like this project:

⭐ Star it on GitHub

🐦 Follow me on Twitter (X)

📱 Join my Telegram

📞 Contact
🐦 Twitter (X): @Mpyj_X

💻 GitHub: @Mpyj

📱 Telegram: @MpyjTelegram

⭐ If you like this project, please give it a star! ⭐