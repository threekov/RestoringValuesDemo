import pandas as pd
import numpy as np
from .knn_model import knn_model

class KNNImputationService:
    def __init__(self, batch_size=10, k=3):
        self.model = knn_model()
        self.model.batch_size = batch_size
        self.k = k
    
    def impute_csv(self, df, k=None):
        if k is None:
            k = self.k
            
        # Если нет временной колонки - создаем из индекса
        if df.index.name is None:
            df_work = df.reset_index()
            time_col = df_work.columns[0]
        else:
            df_work = df.reset_index()
            time_col = df.index.name
            
        # Переименовываем во временную колонку
        df_work = df_work.rename(columns={time_col: 'DateTime'})
        
        # Обрабатываем каждую числовую колонку
        for col in df_work.select_dtypes(include=[np.number]).columns:
            if col == 'DateTime':
                continue
                
            temp_df = df_work[['DateTime', col]].copy()
            
            # Импутация
            imputed_df, _, _ = self.model.compare_fill_methods_and_calculate_mape_knn(
                temp_df, 
                original_batch=None, 
                k=k
            )
            
            df_work[col] = imputed_df[col]
        
        # Возвращаем к исходному виду
        result = df_work.set_index('DateTime')
        result.index.name = time_col if time_col != 'DateTime' else None
        
        return result
