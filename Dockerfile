FROM python:3.12-slim

RUN apt-get update && apt-get install -y \
    libglib2.0-0 libnss3 libatk-bridge2.0-0 libdrm2 libxkbcommon0 libgbm1 \
    libpango-1.0-0 libcairo2 libasound2 libatspi2.0-0 libxcomposite1 \
    libxdamage1 libxfixes3 libxrandr2 libxshmfence1 libcups2 fonts-liberation \
    libnspr4 libx11-6 libxcb1 libxext6 libxrender1 libxss1 libxtst6 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN python -m rebrowser_playwright install chromium chromium-headless-shell

COPY . .

CMD ["python", "main.py"]
