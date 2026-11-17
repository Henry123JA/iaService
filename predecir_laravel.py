"""Consulta Laravel y calcula estimaciones experimentales, sin guardar alertas."""
import argparse
import json
import math
import os
from pathlib import Path
from urllib.request import Request, urlopen

from app.predictor import Predictor


def extraer_alumnos(payload):
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for clave in ("dataset", "data", "alumnos"):
            if isinstance(payload.get(clave), list):
                return payload[clave]
    raise ValueError("Se esperaba una lista o un objeto con dataset, data o alumnos.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8000/api/ml/dataset-alumnos")
    parser.add_argument("--modelo", type=Path, default=Path("models/modelos_demo.joblib"))
    parser.add_argument("--salida", type=Path, default=Path("data/predicciones_demo.json"))
    parser.add_argument("--entrada", type=Path, help="JSON local previamente obtenido de Laravel")
    args = parser.parse_args()
    headers = {"Accept": "application/json"}
    if os.environ.get("LARAVEL_API_TOKEN"):
        headers["Authorization"] = "Bearer " + os.environ["LARAVEL_API_TOKEN"]
    if args.entrada:
        payload = json.loads(args.entrada.read_text(encoding="utf-8"))
    else:
        with urlopen(Request(args.url, headers=headers), timeout=15) as respuesta:
            payload = json.load(respuesta)
    alumnos = extraer_alumnos(payload)
    ids = [alumno["inscripcion_id"] for alumno in alumnos]
    if len(ids) != len(set(ids)):
        raise ValueError("Hay inscripciones duplicadas en la respuesta.")
    if isinstance(payload, dict) and "total_registros" in payload:
        if payload["total_registros"] != len(alumnos):
            raise ValueError("total_registros no coincide con el listado recibido.")
    predictor = Predictor(args.modelo)
    resultados = [predictor.predict(alumno) for alumno in alumnos]
    args.salida.parent.mkdir(parents=True, exist_ok=True)
    args.salida.write_text(json.dumps(resultados, ensure_ascii=False, indent=2), encoding="utf-8")
    calculadas = sum(r["estado_prediccion"] == "CALCULADA" for r in resultados)
    print(f"Procesadas {len(resultados)} inscripciones; {calculadas} predicciones experimentales. Salida: {args.salida}")


if __name__ == "__main__":
    main()
