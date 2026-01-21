import pandas as pd
import numpy as np
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import HTMLResponse, StreamingResponse
import io
import os

from core.imputer_service import KNNImputationService

app = FastAPI(title="KNN Imputation")
imputer = KNNImputationService()

@app.get("/")
async def home():
    return HTMLResponse("""
    <html>
    <head>
        <script>
            function resetForm() {
                // Ждем 1 секунду и сбрасываем форму
                setTimeout(() => {
                    document.getElementById('submitBtn').disabled = false;
                    document.getElementById('submitBtn').innerText = 'Impute';
                    document.getElementById('fileInput').value = '';
                }, 1000);
            }
        </script>
    </head>
    <body style="font-family: Arial; margin: 40px;">
        <h1>KNN Imputation Service</h1>
        <form action="/impute" method="post" enctype="multipart/form-data" 
              onsubmit="document.getElementById('submitBtn').disabled=true; document.getElementById('submitBtn').innerText='Processing...';"
              target="_blank"> <!-- ОТКРЫВАЕМ В НОВОЙ ВКЛАДКЕ! -->
            
            <input type="file" name="file" id="fileInput" accept=".csv" required><br><br>
            <label>k: <input type="number" name="k" value="3" min="1"></label><br><br>
            <button type="submit" id="submitBtn" onclick="setTimeout(resetForm, 100)">Impute</button>
        </form>
        <p style="margin-top: 30px; color: #666;">
            CSV format: first column = time, other columns = numeric data with NaN
        </p>
    </body>
    </html>
    """)

@app.post("/impute")
async def impute_csv(file: UploadFile = File(...), k: int = Form(3)):
    try:
        # Read file
        contents = await file.read()
        
        # Try to parse
        try:
            df = pd.read_csv(io.BytesIO(contents), index_col=0, parse_dates=True)
        except:
            df = pd.read_csv(io.BytesIO(contents), index_col=0)
        
        print(f"Processing: {file.filename}, shape: {df.shape}, k={k}")
        
        # Impute
        df_imputed = imputer.impute_csv(df, k=k)
        
        # Return as CSV
        output = io.StringIO()
        df_imputed.to_csv(output, index=True)
        output.seek(0)
        
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=imputed_{file.filename}"}
        )
        
    except Exception as e:
        print(f"Error: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    print("Server starting at http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)
