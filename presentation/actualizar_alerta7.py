"""Actualiza solamente la explicacion de la inscripcion 7 mediante las APIs."""
import json
import os
from pathlib import Path
from urllib.request import Request, urlopen


def solicitar(url, body=None):
    headers = {'Accept': 'application/json'}
    if url.startswith('http://127.0.0.1:8000/') and os.environ.get('LARAVEL_API_TOKEN'):
        headers['Authorization'] = 'Bearer ' + os.environ['LARAVEL_API_TOKEN']
    data = None
    if body is not None:
        headers['Content-Type'] = 'application/json'
        data = json.dumps(body).encode('utf-8')
    with urlopen(Request(url, data=data, headers=headers), timeout=30) as response:
        return json.load(response)


payload = solicitar('http://127.0.0.1:8000/api/ml/dataset-alumnos')
alumno = next(x for x in payload['dataset'] if x['inscripcion_id'] == 7)
prediction = solicitar('http://127.0.0.1:8001/api/v1/predict', {
    'inscripcion_id': 7, 'features': alumno['features'],
})
if prediction['estado_prediccion'] != 'CALCULADA':
    raise RuntimeError('La inscripcion no es elegible; no se actualizo la alerta')
if 'Seguimiento sugerido:' in prediction['resumen_explicativo']:
    raise RuntimeError('FastAPI todavia usa el resumen anterior')
saved = solicitar('http://127.0.0.1:8000/api/ml/webhook-alertas', {
    'total_registros': 1, 'predicciones_calculadas': 1, 'resultados': [prediction],
})
if saved['procesadas'] != 1 or saved['alerta_ids'] != [7]:
    raise RuntimeError('Resultado de guardado inesperado')
output = Path(__file__).resolve().parent.parent / 'data' / 'alerta7_presentacion.json'
output.write_text(json.dumps({'prediccion': prediction, 'guardado': saved},
                            ensure_ascii=False, indent=2), encoding='utf-8')
print(f"Alerta 7 actualizada: score {prediction['score_riesgo']:.2f}; acciones separadas: {len(prediction['acciones_sugeridas'])}")
