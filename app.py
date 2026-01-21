# app.py
import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import io
import sys
import os

# Добавляем core в путь для импорта
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.imputer_service import KNNImputationService

app = FastAPI(title="KNN Imputation Service")

# Создаем экземпляр сервиса
imputer = KNNImputationService(batch_size=10, k=3)

@app.get("/", response_class=HTMLResponse)
async def home():
    """Простая HTML форма для загрузки файла"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KNN Imputation Service</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            form { max-width: 500px; }
            input, button { padding: 10px; margin: 5px 0; width: 100%; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
            .info { background: #f5f5f5; padding: 15px; margin-top: 20px; border-radius: 5px; }
        </style>
    </head>
    <body>
        <h1>KNN Imputation Service</h1>
        <p>Заполнение пропусков во временных рядах с помощью KNN</p>
        
        <form action="/impute" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".csv" required><br><br>
            <label>Количество соседей (k): 
                <input type="number" name="k" value="3" min="1" max="20">
            </label><br><br>
            <button type="submit">Импутировать пропуски</button>
        </form>
        
        <div class="info">
            <h3>Формат CSV файла:</h3>
            <ul>
                <li>Первая колонка: временные метки</li>
                <li>Остальные колонки: числовые данные</li>
                <li>Пропуски обозначаются как пустые ячейки или NaN</li>
            </ul>
            
            <h3>Технологии:</h3>
            <ul>
                <li>Временной KNN для импутации</li>
                <li>Интерполяция для заполнения пропусков</li>
                <li>FastAPI + Python 3.11</li>
            </ul>
        </div>
    </body>
    </html>
    """

@app.post("/impute")
async def impute_csv(
    file: UploadFile = File(...),
    k: int = Form(3)
):
    """
    Основной эндпоинт для импутации
    """
    if not file.filename.lower().endswith('.csv'):
        return {"error": "Только CSV файлы поддерживаются"}
    
    try:
        # Читаем файл
        contents = await file.read()
        
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
                break
            except:
                continue
                
        if df_nans is None:
            return {"error": "Не удалось прочитать CSV файл. Проверьте кодировку и формат."}
        
        # Импутация пропусков
        df_imputed = imputer.impute_csv(df_nans, k=k)
        
        # Конвертируем в CSV для скачивания
        output = io.StringIO()
        df_imputed.to_csv(output, index=True)
        output.seek(0)
        
        # Формируем имя файла
        original_name = file.filename.rsplit('.', 1)[0]
        result_filename = f"{original_name}_imputed.csv"
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={result_filename}"}
        )
        
    except Exception as e:
        return {"error": f"Ошибка обработки: {str(e)}"}

@app.get("/health")
async def health_check():
    """Проверка работоспособности"""
    return {
        "status": "healthy",
        "service": "KNN Imputation",
        "version": "1.0.0"
    }

if __name__ == "__main__":
    import uvicorn
    print("KNN Imputation Service запускается...")
    print("Откройте http://localhost:8000 в браузере")
    uvicorn.run(app, host="0.0.0.0", port=8000)
