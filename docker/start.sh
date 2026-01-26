#!/usr/bin/env bash
# docker/start.sh
set -e

echo "Starting KNN Imputation Service..."

# Переходим в директорию с приложением
cd /opt/knn-service/app

# Запускаем FastAPI сервер с uvicorn
exec uvicorn app:app --host 0.0.0.0 --port 8000 --workers 2
