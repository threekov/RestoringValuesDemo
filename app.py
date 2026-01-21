# app.py
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import io
import sys
import os
import logging
import json
import time

# Настройка логирования в JSON формате
logger = logging.getLogger("knn_api")
logger.setLevel(os.getenv("LOG_LEVEL", "INFO").upper())

handler = logging.StreamHandler()

class JsonFormatter(logging.Formatter):
    def format(self, record):
        log_record = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if hasattr(record, "extra"):
            log_record.update(record.extra)
        return json.dumps(log_record)

handler.setFormatter(JsonFormatter())
logger.addHandler(handler)

# Инициализация FastAPI приложения
app = FastAPI(
    title="KNN Imputation Service",
    description="Сервис для заполнения пропусков во временных рядах с использованием KNN",
    version="1.0.0"
)

# ------------------- MIDDLEWARE ДЛЯ ЛОГИРОВАНИЯ -------------------

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Пропускаем запрос через обработчики
    response = await call_next(request)
    
    # Рассчитываем время выполнения
    process_time = round((time.time() - start_time) * 1000, 2)
    
    # Логируем информацию о запросе
    logger.info("request_processed", extra={
        "method": request.method,
        "path": request.url.path,
        "query_params": str(request.query_params),
        "status_code": response.status_code,
        "response_time_ms": process_time,
        "client_host": request.client.host if request.client else None,
    })
    
    # Добавляем время выполнения в заголовки ответа
    response.headers["X-Process-Time-MS"] = str(process_time)
    
    return response

# ------------------- ИМПОРТ НАШИХ МОДУЛЕЙ -------------------

# Добавляем core в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.imputer_service import KNNImputationService

# Создаем экземпляр сервиса
imputer = KNNImputationService(batch_size=10, k=3)

# ------------------- ENDPOINTS -------------------

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Главная страница с формой загрузки"""
    logger.info("home_page_accessed", extra={
        "endpoint": "/",
        "client": request.client.host if request.client else "unknown"
    })
    
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KNN Imputation Service</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 40px auto;
                padding: 20px;
                background-color: #f8f9fa;
            }
            .container {
                background: white;
                padding: 30px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #007bff;
                padding-bottom: 10px;
            }
            .form-group {
                margin-bottom: 20px;
            }
            label {
                display: block;
                margin-bottom: 8px;
                font-weight: 600;
                color: #555;
            }
            input[type="file"], input[type="number"] {
                width: 100%;
                padding: 10px;
                border: 1px solid #ddd;
                border-radius: 5px;
                box-sizing: border-box;
                font-size: 16px;
            }
            button {
                background: #007bff;
                color: white;
                border: none;
                padding: 12px 24px;
                font-size: 16px;
                border-radius: 5px;
                cursor: pointer;
                transition: background 0.3s;
                width: 100%;
            }
            button:hover {
                background: #0056b3;
            }
            .info-box {
                background: #e7f3ff;
                padding: 20px;
                border-radius: 5px;
                margin-top: 30px;
                border-left: 4px solid #007bff;
            }
            .status {
                margin-top: 20px;
                padding: 10px;
                background: #28a745;
                color: white;
                border-radius: 5px;
                text-align: center;
                display: none;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>KNN Imputation Service</h1>
            <p>Сервис для заполнения пропусков во временных рядах с использованием алгоритма K-ближайших соседей</p>
            
            <form id="uploadForm" action="/impute" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="file">Выберите CSV файл с пропусками:</label>
                    <input type="file" name="file" id="file" accept=".csv" required>
                </div>
                
                <div class="form-group">
                    <label for="k">Количество соседей (k):</label>
                    <input type="number" name="k" id="k" value="3" min="1" max="20">
                </div>
                
                <button type="submit" id="submitBtn">Импутировать пропуски</button>
            </form>
            
            <div id="status" class="status">Обработка файла...</div>
            
            <div class="info-box">
                <h3>Требования к файлу:</h3>
                <ul>
                    <li><strong>Формат:</strong> CSV (Comma Separated Values)</li>
                    <li><strong>Первая колонка:</strong> временные метки (DateTime)</li>
                    <li><strong>Остальные колонки:</strong> числовые данные</li>
                    <li><strong>Пропуски:</strong> пустые ячейки или значения NaN</li>
                </ul>
                
                <h3>Технологии:</h3>
                <ul>
                    <li>Временной KNN для импутации пропусков</li>
                    <li>Интерполяция для заполнения соседних значений</li>
                    <li>FastAPI + Python 3.11 для веб-интерфейса</li>
                    <li>JSON логирование для мониторинга</li>
                </ul>
                
                <h3>Доступные методы:</h3>
                <ul>
                    <li><code>GET /</code> - Эта страница</li>
                    <li><code>POST /impute</code> - Импутация CSV файла</li>
                    <li><code>GET /health</code> - Проверка работоспособности</li>
                    <li><code>GET /metrics</code> - Метрики сервиса</li>
                </ul>
            </div>
        </div>
        
        <script>
            document.getElementById('uploadForm').addEventListener('submit', function(e) {
                const submitBtn = document.getElementById('submitBtn');
                const statusDiv = document.getElementById('status');
                
                submitBtn.disabled = true;
                submitBtn.textContent = 'Обработка...';
                statusDiv.style.display = 'block';
            });
        </script>
    </body>
    </html>
    """

@app.post("/impute")
async def impute_csv(
    request: Request,
    file: UploadFile = File(...),
    k: int = Form(3)
):
    """
    Основной эндпоинт для импутации пропусков в CSV файле
    """
    logger.info("impute_endpoint_called", extra={
        "endpoint": "/impute",
        "filename": file.filename,
        "file_size": file.size if hasattr(file, 'size') else "unknown",
        "k_value": k,
        "client": request.client.host if request.client else "unknown"
    })
    
    if not file.filename.lower().endswith('.csv'):
        logger.warning("invalid_file_extension", extra={
            "filename": file.filename,
            "expected_extension": ".csv"
        })
        return {"error": "Только CSV файлы поддерживаются"}
    
    try:
        start_time = time.time()
        
        # Читаем файл
        contents = await file.read()
        file_size_kb = len(contents) / 1024
        
        logger.info("file_received", extra={
            "filename": file.filename,
            "size_kb": round(file_size_kb, 2),
            "k": k
        })
        
        # Пробуем разные кодировки
        encodings = ['utf-8', 'cp1251', 'latin1', 'windows-1251']
        df_nans = None
        
        for encoding in encodings:
            try:
                df_nans = pd.read_csv(
                    io.BytesIO(contents),
                    index_col=0,
                    parse_dates=True,
                    encoding=encoding
                )
                logger.debug("file_read_success", extra={"encoding": encoding})
                break
            except Exception as e:
                logger.debug("file_read_failed", extra={
                    "encoding": encoding,
                    "error": str(e)
                })
                continue
                
        if df_nans is None:
            logger.error("file_read_all_encodings_failed", extra={
                "filename": file.filename,
                "tried_encodings": encodings
            })
            return {"error": "Не удалось прочитать CSV файл. Проверьте кодировку и формат."}
        
        # Логируем информацию о данных
        missing_values = df_nans.isna().sum().sum()
        missing_percentage = (missing_values / (df_nans.shape[0] * df_nans.shape[1])) * 100
        
        logger.info("data_analysis", extra={
            "rows": df_nans.shape[0],
            "columns": df_nans.shape[1],
            "missing_values": int(missing_values),
            "missing_percentage": round(missing_percentage, 2),
            "columns_list": list(df_nans.columns)
        })
        
        # Импутация пропусков
        logger.info("starting_imputation", extra={"k": k})
        imputation_start = time.time()
        
        df_imputed = imputer.impute_csv(df_nans, k=k)
        
        imputation_time = round((time.time() - imputation_start) * 1000, 2)
        
        # Логируем результат импутации
        remaining_missing = df_imputed.isna().sum().sum()
        
        logger.info("imputation_completed", extra={
            "imputation_time_ms": imputation_time,
            "remaining_missing": int(remaining_missing),
            "imputed_values": int(missing_values - remaining_missing),
            "success_rate": round(((missing_values - remaining_missing) / missing_values * 100), 2) if missing_values > 0 else 100
        })
        
        # Конвертируем в CSV для скачивания
        output = io.StringIO()
        df_imputed.to_csv(output, index=True)
        csv_content = output.getvalue()
        output.seek(0)
        
        # Формируем имя файла
        original_name = file.filename.rsplit('.', 1)[0]
        result_filename = f"{original_name}_imputed_k{k}.csv"
        
        total_time = round((time.time() - start_time) * 1000, 2)
        
        logger.info("response_ready", extra={
            "result_filename": result_filename,
            "result_size_kb": round(len(csv_content) / 1024, 2),
            "total_processing_time_ms": total_time
        })
        
        return StreamingResponse(
            iter([csv_content]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename={result_filename}",
                "X-Imputation-Time-MS": str(imputation_time),
                "X-Total-Time-MS": str(total_time),
                "X-Imputed-Values": str(int(missing_values - remaining_missing))
            }
        )
        
    except Exception as e:
        logger.error("imputation_error", extra={
            "error": str(e),
            "error_type": type(e).__name__,
            "filename": file.filename
        }, exc_info=True)
        return {"error": f"Ошибка обработки: {str(e)}"}

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервиса"""
    logger.info("health_check_called")
    return {
        "status": "healthy",
        "service": "KNN Imputation Service",
        "version": "1.0.0",
        "timestamp": time.time(),
        "model_ready": True,
        "features": ["csv_imputation", "time_series_knn", "json_logging"]
    }

@app.get("/metrics")
async def get_metrics():
    """Метрики сервиса (заглушка для демонстрации)"""
    import psutil
    import platform
    
    logger.info("metrics_endpoint_called")
    
    # Собираем системные метрики
    cpu_percent = psutil.cpu_percent(interval=0.1)
    memory = psutil.virtual_memory()
    disk = psutil.disk_usage('/')
    
    return {
        "system": {
            "cpu_percent": cpu_percent,
            "memory_percent": memory.percent,
            "memory_available_gb": round(memory.available / (1024**3), 2),
            "disk_percent": disk.percent,
            "disk_free_gb": round(disk.free / (1024**3), 2),
            "python_version": platform.python_version(),
            "platform": platform.platform()
        },
        "service": {
            "start_time": time.strftime("%Y-%m-%d %H:%M:%S"),
            "uptime_seconds": round(time.time() - psutil.boot_time(), 0),
            "endpoints_available": ["/", "/impute", "/health", "/metrics"]
        }
    }

@app.get("/test-data")
async def test_data():
    """Генерация тестовых данных для демонстрации"""
    logger.info("test_data_generated")
    
    # Создаем тестовый DataFrame
    dates = pd.date_range(start='2023-01-01', periods=100, freq='H')
    data = {
        'DateTime': dates,
        'Temperature': np.random.normal(20, 5, 100),
        'Humidity': np.random.normal(60, 10, 100),
        'Pressure': np.random.normal(1013, 5, 100)
    }
    
    df = pd.DataFrame(data)
    
    # Добавляем пропуски
    for col in ['Temperature', 'Humidity', 'Pressure']:
        mask = np.random.random(100) < 0.2  # 20% пропусков
        df.loc[mask, col] = np.nan
    
    # Сохраняем как CSV
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=test_data_with_nans.csv"}
    )

if __name__ == "__main__":
    import uvicorn
    
    logger.info("service_starting", extra={
        "service": "KNN Imputation Service",
        "host": "0.0.0.0",
        "port": 8000
    })
    
    print("KNN Imputation Service запускается...")
    print("Откройте http://localhost:8000 в браузере")
    print("Логи выводятся в JSON формате")
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        log_config=None  # Используем наше собственное логирование
    )
