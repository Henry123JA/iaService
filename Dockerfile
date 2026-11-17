FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    ML_MODEL_PATH=/app/models/modelos_demo.joblib

WORKDIR /app

# Dependencias del sistema necesarias para scikit-learn / shap
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY reglas_negocio.py .
COPY app/ ./app/
COPY training/ ./training/
COPY models/ ./models/

# Si el modelo no fue copiado (por ejemplo al clonar desde Git), se genera de forma determinista (semilla 42)
RUN if [ ! -f /app/models/modelos_demo.joblib ]; then \
        python training/generar_dataset.py --cantidad 5000 --semilla 42 && \
        python training/train_model.py && \
        rm -rf /app/data; \
    fi

EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

