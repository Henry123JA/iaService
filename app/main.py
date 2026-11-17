from contextlib import asynccontextmanager
import os
from pathlib import Path

from fastapi import FastAPI, Request

from app.predictor import Predictor
from app.schemas import BatchRequest, BatchResponse, PredictRequest, PredictResponse

ROOT = Path(__file__).resolve().parent.parent


@asynccontextmanager
async def lifespan(app):
    # Carga una vez al iniciar; falla explicitamente si no hay un modelo valido.
    app.state.predictor = Predictor(Path(os.environ.get(
        "ML_MODEL_PATH", ROOT / "models" / "modelos_demo.joblib")))
    yield


app = FastAPI(title="Scala ML Service", version="0.1.0", lifespan=lifespan)


@app.get("/health")
def health(request: Request):
    return {"status": "ok", "version_modelo": request.app.state.predictor.bundle["version"]}


@app.post("/api/v1/predict", response_model=PredictResponse)
def predict(body: PredictRequest, request: Request):
    return request.app.state.predictor.predict(body.model_dump(exclude_none=True))


@app.post("/api/v1/predict-batch", response_model=BatchResponse)
def predict_batch(body: BatchRequest, request: Request):
    resultados = [request.app.state.predictor.predict(a.model_dump(exclude_none=True))
                  for a in body.alumnos]
    return {"total_registros": len(resultados),
            "predicciones_calculadas": sum(r["estado_prediccion"] == "CALCULADA"
                                          for r in resultados),
            "resultados": resultados}
