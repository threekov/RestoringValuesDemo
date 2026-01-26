# docker/Dockerfile
FROM python:3.11-slim

# Установка системных зависимостей
RUN apt-get update && apt-get install -y \
    curl \
    tar \
    && rm -rf /var/lib/apt/lists/*

# Создание структуры директорий
RUN mkdir -p /opt/knn-service/app /opt/knn-service/run
WORKDIR /opt/knn-service

# Копирование требований и установка зависимостей
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Копирование исходного кода
COPY . /opt/knn-service/app/

# Копирование скрипта запуска
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh

# Открываем порт для FastAPI
EXPOSE 8000

CMD ["/start.sh"]
