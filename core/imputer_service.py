# core/imputer_service.py
import pandas as pd
import numpy as np
from typing import Optional, Dict
from .knn_model import knn_model

class KNNImputationService:
    """Сервис для импутации пропусков с KNN"""
    
    def __init__(self, batch_size: int = 10, k: int = 3):
        self.model = knn_model()
        self.model.batch_size = batch_size
        self.default_k = k
        
    def impute_csv(self, 
                   df: pd.DataFrame, 
                   time_column: Optional[str] = None,
                   k: Optional[int] = None) -> pd.DataFrame:
        """
        Импутация пропусков во всем DataFrame
        
        Args:
            df: DataFrame с пропусками
            time_column: Имя колонки с временем (если None - используется индекс)
            k: Количество соседей (если None - используется default_k)
        
        Returns:
            DataFrame с заполненными пропусками
        """
        if k is None:
            k = self.default_k
            
        # Если не указана временная колонка, создаем её из индекса
        if time_column is None:
            df_work = df.reset_index()
            time_column = df_work.columns[0]  # Первая колонка после reset_index
        else:
            df_work = df.copy()
            
        # Проверяем, что временная колонка существует
        if time_column not in df_work.columns:
            raise ValueError(f"Временная колонка '{time_column}' не найдена")
            
        # Переименовываем временную колонку в 'DateTime' для совместимости с моделью
        df_work = df_work.rename(columns={time_column: 'DateTime'})
        
        # Импутируем каждую числовую колонку отдельно
        numeric_columns = df_work.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            if col == 'DateTime':
                continue
                
            # Подготавливаем данные для одной колонки
            temp_df = df_work[['DateTime', col]].copy()
            
            # Используем модель для импутации
            imputed_df, _, _ = self.model.compare_fill_methods_and_calculate_mape_knn(
                temp_df, 
                original_batch=None, 
                k=k
            )
            
            # Обновляем значения в основном DataFrame
            df_work[col] = imputed_df[col]
        
        # Восстанавливаем исходную структуру
        result_df = df_work.rename(columns={'DateTime': time_column})
        
        if time_column == df.index.name or df.index.name is None:
            result_df = result_df.set_index(time_column)
            
        return result_df
    
    def calculate_metrics(self,
                         df_with_nans: pd.DataFrame,
                         df_clean: pd.DataFrame,
                         time_column: Optional[str] = None,
                         k: Optional[int] = None) -> Dict:
        """
        Расчет метрик качества импутации
        
        Returns:
            Словарь с метриками
        """
        # Сбрасываем метрики модели
        self.model.mape_inter = []
        self.model.mape_mean = []
        
        if k is None:
            k = self.default_k
            
        # Импутация с расчетом метрик
        if time_column is None:
            df_nans_work = df_with_nans.reset_index()
            df_clean_work = df_clean.reset_index()
            time_column = df_nans_work.columns[0]
        else:
            df_nans_work = df_with_nans.copy()
            df_clean_work = df_clean.copy()
            
        # Переименовываем для совместимости
        df_nans_work = df_nans_work.rename(columns={time_column: 'DateTime'})
        df_clean_work = df_clean_work.rename(columns={time_column: 'DateTime'})
        
        numeric_columns = df_nans_work.select_dtypes(include=[np.number]).columns
        
        for col in numeric_columns:
            if col == 'DateTime':
                continue
                
            temp_nans = df_nans_work[['DateTime', col]].copy()
            temp_clean = df_clean_work[[col]].copy()  # Только данные без времени
            
            # Импутация с расчетом метрик
            _, mape_inter, mape_mean = self.model.compare_fill_methods_and_calculate_mape_knn(
                temp_nans,
                temp_clean,
                k=k
            )
            
        # Собираем финальные метрики
        metrics = {}
        if self.model.mape_inter:
            metrics["MAPE"] = sum(self.model.mape_inter) / len(self.model.mape_inter)
        
        if self.model.mape_mean:
            metrics["MAPE_mean"] = sum(self.model.mape_mean) / len(self.model.mape_mean)
            
        return metrics
