FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    ffmpeg \
    tesseract-ocr \
    poppler-utils \
    curl \
    dnsutils \
    whois \
    libxml2-dev \
    libxslt1-dev \
    libfreetype6-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /app/tessdata && \
    curl -L https://github.com/tesseract-ocr/tessdata/raw/main/fas.traineddata -o /app/tessdata/fas.traineddata && \
    curl -L https://github.com/tesseract-ocr/tessdata/raw/main/eng.traineddata -o /app/tessdata/eng.traineddata

EXPOSE 8080

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]