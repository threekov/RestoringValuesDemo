import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import io
import sys
import os

# Добавляем текущую директорию в путь для импорта модели
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Импортируем ТВОЮ модель
from knn_model import knn_model

app = FastAPI(title="KNN Imputation Service")

# Создаем экземпляр модели
model = knn_model()

@app.get("/", response_class=HTMLResponse)
async def home():
    """Простая HTML форма для загрузки файла"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>KNN Imputation</title>
        <style>
            body { font-family: Arial; margin: 40px; }
            form { max-width: 500px; }
            input, button { padding: 10px; margin: 5px 0; width: 100%; }
            button { background: #007bff; color: white; border: none; cursor: pointer; }
        </style>
    </head>
    <body>
        <h1>Загрузите CSV файл с пропусками</h1>
        <form action="/impute" method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".csv" required><br><br>
            <label>k-соседей: <input type="number" name="k" value="3" min="1"></label><br><br>
            <button type="submit">Импутировать пропуски</button>
        </form>
        <p><strong>Формат:</strong> Первая колонка - время, остальные - числовые данные с NaN</p>
    </body>
    </html>
    """

@app.post("/impute")
async def impute_csv(
    file: UploadFile = File(...),
    k: int = Form(3)
):
    """
    Принимает CSV, импутирует пропуски, возвращает CSV
    """
    # Проверка расширения
    if not file.filename.endswith('.csv'):
        return {"error": "Только CSV файлы"}
    
    try:
        # Читаем загруженный файл
        contents = await file.read()
        
        # Парсим CSV (первая колонка как индекс времени)
        df_nans = pd.read_csv(
            io.BytesIO(contents),
            index_col=0,
            parse_dates=True
        )
        
        print(f"Загружен файл: {df_nans.shape[0]} строк, {df_nans.shape[1]} колонок")
        print(f"Найдено пропусков: {df_nans.isna().sum().sum()}")
        
        # Проверяем структуру
        if df_nans.shape[1] == 0:
            return {"error": "В файле нет данных (только временная метка)"}
        
        # Если есть clean.csv рядом, используем для метрик
        clean_path = os.path.join("test_data", "clean.csv")
        df_clean = None
        if os.path.exists(clean_path):
            df_clean = pd.read_csv(clean_path, index_col=0, parse_dates=True)
            print("Найден clean.csv для расчета метрик")
        
        # Переименовываем первую колонку в DateTime для совместимости с моделью
        df_for_imputation = df_nans.reset_index()
        time_col_name = df_for_imputation.columns[0]
        df_for_imputation = df_for_imputation.rename(columns={time_col_name: "DateTime"})
        
        # Обрабатываем каждый столбец отдельно (твоя модель работает с одним целевым столбцом)
        for col in df_for_imputation.columns[1:]:  # Пропускаем DateTime
            print(f"Обрабатываю колонку: {col}")
            
            # Подготавливаем DataFrame для модели
            temp_df = df_for_imputation[["DateTime", col]].copy()
            
            if df_clean is not None:
                # Если есть ground truth, берем соответствующие данные
                clean_col_data = df_clean[col].reset_index()
                clean_col_data = clean_col_data.rename(columns={time_col_name: "DateTime"})
                
                # Импутация с метриками
                imputed_df, mape_inter, mape_mean = model.compare_fill_methods_and_calculate_mape_knn(
                    temp_df, 
                    clean_col_data[[col]],  # Только данные этой колонки
                    k=k
                )
            else:
                # Импутация без метрик
                imputed_df, _, _ = model.compare_fill_methods_and_calculate_mape_knn(
                    temp_df, 
                    None,
                    k=k
                )
            
            # Обновляем значения в основном DataFrame
            df_for_imputation[col] = imputed_df[col]
        
        # Восстанавливаем исходную структуру
        df_imputed = df_for_imputation.set_index("DateTime")
        df_imputed.index.name = time_col_name
        
        print(f"Импутация завершена. Осталось пропусков: {df_imputed.isna().sum().sum()}")
        
        # Конвертируем в CSV для скачивания
        output = io.StringIO()
        df_imputed.to_csv(output, index=True)
        output.seek(0)
        
        # Возвращаем файл для скачивания
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={
                "Content-Disposition": f"attachment; filename=imputed_{file.filename}"
            }
        )
        
    except Exception as e:
        print(f"Ошибка: {str(e)}")
        return {"error": f"Ошибка обработки: {str(e)}"}

@app.get("/test")
async def test_endpoint():
    """Тестовый эндпоинт для проверки работы"""
    return {
        "status": "ok",
        "message": "Сервер работает",
        "model": "KNN Imputer"
    }

if __name__ == "__main__":
    import uvicorn
    print("Запуск сервера KNN импутации...")
    print("Откройте http://localhost:8000 в браузере")
    uvicorn.run(app, host="0.0.0.0", port=8000)
