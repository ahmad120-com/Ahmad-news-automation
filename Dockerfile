FROM python:3.12-slim

ENV DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y --no-install-recommends \
    chromium \
    chromium-driver \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY app.py .

ENV REGISTRATION="FA23-BDS-048"
ENV NEWS_SOURCE_NAME="Al Jazeera Media Network"
ENV NEWS_SOURCE_URL="https://www.aljazeera.com"

EXPOSE 7000

CMD ["python", "app.py"]
