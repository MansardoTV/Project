FROM python:3.9-slim

# Установка Chrome
RUN apt-get update && apt-get install -y wget \
    && wget -q https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb \
    && apt-get install -y ./google-chrome-stable_current_amd64.deb \
    && rm google-chrome-stable_current_amd64.deb \
    && rm -rf /var/lib/apt/lists/*
# После установки Chrome добавь:
RUN apt-get update && apt-get install -y \
    libsasl2-dev \
    gcc \
    g++ \
    libkrb5-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Копируем зависимости и устанавливаем
COPY requirements.txt .
RUN pip install --no-cache-dir selenium beautifulsoup4
RUN pip install --no-cache-dir pyhive thrift
RUN pip install --no-cache-dir pandas matplotlib
RUN pip install --no-cache-dir thrift thrift-sasl sasl
# Копируем парсер
COPY parser_docker.py .

# Копируем остальные файлы проекта
COPY hive_loader.py .
COPY . .

# Создаем папку для результатов
RUN mkdir -p /app/output

CMD ["python", "parser_docker.py"]