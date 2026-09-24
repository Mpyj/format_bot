FROM python:3.12-slim

# نصب پکیج‌های سیستمی
RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    poppler-utils \
    curl \
    && rm -rf /var/lib/apt/lists/*

# تنظیم پوشه کاری
WORKDIR /app

# کپی و نصب نیازمندی‌های پایتون
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# کپی بقیه پروژه
COPY . .

# دانلود فایل‌های زبان Tesseract
RUN mkdir -p /app/tessdata && \
    curl -L https://github.com/tesseract-ocr/tessdata/raw/main/fas.traineddata -o /app/tessdata/fas.traineddata && \
    curl -L https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata -o /app/tessdata/eng.traineddata

# پورت
EXPOSE 8080

# دستور اجرا
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]