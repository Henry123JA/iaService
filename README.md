# Demostracion de alerta temprana

Automatizacion n8n instalada y publicada: consultar [n8n/README.md](n8n/README.md).
Explicaciones individuales Tree SHAP implementadas: [explainability/README.md](explainability/README.md).

Objetivo principal propuesto: anticipar la reprobacion de una inscripcion durante
el periodo, con tiempo para una intervencion docente. Objetivo secundario:
anticipar el abandono. Son resultados separados que pueden coexistir.

## Estado y supuestos

Solo hay 12 inscripciones actuales segun la informacion proporcionada. No hay
resultados historicos confirmados para entrenar o validar eficacia real.
El generador usa las mismas seis features del contrato, pero sus distribuciones,
coeficientes y frecuencias son supuestos; no estan ajustados a PostgreSQL.
Simula seguimiento en semana 2 o 3, tras 3 o 4 sesiones y una evaluacion practica,
en periodos de 10 a 12 semanas con 1 a 2 sesiones semanales. Asistencia y conteos
se calculan sobre esas sesiones. La nota final simulada determina `reprobo`:
nota < 51 reprueba; 51 o mas aprueba. No se usa la nota parcial para etiquetar
directamente el resultado final: se simulan recuperacion y deterioro posteriores.

Segun las reglas comunicadas por el usuario, CANCELADA confirma abandono definitivo
con fecha_retiro; PAUSADA es temporal con fecha_pausa y requiere seguimiento.
En datos reales, abandono debe ocurrir DESPUES de la fotografia de seguimiento.
Los estados no forman parte de las seis features; usar PAUSADA como predictor
requiere ampliar el contrato y entrenar con el estado observado en esa fecha.
El estado final simulado solo distingue abandono y ausencia de abandono; no simula pausas.

El semaforo institucional comunicado es una regla sobre la situacion actual:
excelente con nota >= 90 y asistencia >= 85; favorable con nota de 70 a 89.99
y asistencia >= 75; regular con nota de 51 a 69.99; riesgo alto con nota < 51
o asistencia < 65. No es la etiqueta futura ni se fuerza al Random Forest a
reproducirlo. Algunas combinaciones no quedan cubiertas por esas categorias;
su prioridad completa debe verificarse en Laravel antes de replicar ese semaforo.

`reprobo` y `abandono` son etiquetas futuras simuladas. Solo las seis features
entran al entrenamiento; ningun resultado futuro se usa como entrada.
Las metricas evalúan la simulacion y no prueban eficacia con alumnos reales.
Las probabilidades no estan calibradas con resultados reales. `score_riesgo`
es la estimacion porcentual de reprobacion; abandono se devuelve por separado,
sin sumar probabilidades. Se asigna ALTO desde 65, MEDIO desde 35 hasta menos de
65 y BAJO por debajo de 35, segun el contrato comunicado. Se aplica el umbral
al score redondeado que recibe Laravel. No se guardan alertas automaticamente.
Para uso real: recopilar fotografias fechadas y resultados posteriores, separar
entrenamiento y evaluacion por estudiante/periodo, comparar con reglas simples y
validar sensibilidad, precision y calibracion con los umbrales institucionales.

## Ejecutar desde esta carpeta (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe training/generar_dataset.py --cantidad 3000 --semilla 42
.\.venv\Scripts\python.exe training/train_model.py
.\.venv\Scripts\python.exe predecir_laravel.py
```

La ultima orden consulta `http://127.0.0.1:8000/api/ml/dataset-alumnos` y escribe
`data/predicciones_demo.json`; no modifica Laravel ni PostgreSQL.
La integracion Laravel ahora requiere autenticacion: configurar `LARAVEL_API_TOKEN`
en el entorno con la credencial de servicio. No usar credenciales de un docente.
Se espera una lista o `{ "data": [...] }`, con cada item de la forma:

```json
{
  "inscripcion_id": 5,
  "features": {
    "porcentaje_asistencia": 58.3,
    "faltas_injustificadas": 3,
    "atrasos": 2,
    "promedio_calificaciones": 62.5,
    "tendencia_notas": -8.5,
    "observaciones_negativas": 2
  }
}
```

Si la respuesta real tiene otra estructura, adaptar el lector antes de ejecutar.
El endpoint verificado devuelve `dataset` y su alias `alumnos`. El lector elige
solo una lista (dataset, data o alumnos), valida duplicados y total_registros.
`features.total_obs_alerta` se adapta a `observaciones_negativas`; en las 12
inscripciones verificadas coincide con obs_disciplina + obs_recomendacion.
Las CANCELADA se registran como retiro confirmado sin prediccion futura. Con
menos de 3 sesiones o ninguna evaluacion se registra DATOS_INSUFICIENTES sin
score; nunca se interpreta la ausencia de datos como riesgo academico alto.
PAUSADA con datos suficientes conserva su prediccion experimental y un aviso
de seguimiento; el modelo no incorpora el estado como entrada.

Para reproducir una consulta guardada sin volver a acceder al servidor:

```powershell
.\.venv\Scripts\python.exe predecir_laravel.py --entrada data/respuesta_laravel.json
```

La respuesta original puede contener nombres y correos: se guarda en `data/`,
excluido de Git; la salida de predicciones solo conserva el ID de inscripcion.
Guardar el formato real del endpoint sin datos personales ayudara a verificarlo.
El comando de entrenamiento muestra precision, recall y F1 por clase para cada
resultado. El modelo guardado es exclusivamente de demostracion.

## Servicio FastAPI para Laravel

Desde la raiz del proyecto:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```

Documentacion interactiva: http://127.0.0.1:8001/docs
Estado del servicio: `GET /health`. El modelo se carga una vez al iniciar,
desde `models/modelos_demo.joblib`, independientemente del directorio de trabajo.
`ML_MODEL_PATH` permite seleccionar otro artefacto propio. Si falta o es
incompatible, el arranque falla explicitamente. Reiniciar tras reentrenar.

`POST /api/v1/predict` recibe el ejemplo JSON de arriba y devuelve el ID,
score_riesgo, nivel_riesgo, version_modelo, estado_prediccion y ambas estimaciones.
Con CANCELADA o datos insuficientes devuelve score/nivel null; Laravel debe
comprobar `estado_prediccion == CALCULADA` antes de crear una alerta.
Si no se proporcionan los conteos de sesiones y evaluaciones se asume que
Laravel ya comprobo la elegibilidad. Para comprobarla aqui, enviar
`features.total_sesiones` y `features.evaluaciones_rendidas`.

`POST /api/v1/predict-batch` acepta una lista, `{ "alumnos": [...] }`,
`{ "data": [...] }` o la respuesta completa del endpoint Laravel con `dataset`.
Acepta de 1 a 1000 inscripciones y devuelve:

```json
{
  "total_registros": 12,
  "predicciones_calculadas": 7,
  "resultados": []
}
```

`resultados` contiene una respuesta por inscripcion, en el mismo orden.
El ejemplo muestra solo el sobre; el array real contiene los 12 resultados.
Errores de validacion devuelven HTTP 422 (rangos, tipos, variables ausentes,
estados contradictorios, IDs duplicados o total incorrecto); el lote se rechaza
completo sin resultados parciales. Los campos adicionales de Laravel se ignoran.
Se acepta promedio_calificaciones null solo cuando la inscripcion queda excluida
por retiro o seguimiento insuficiente; no se reemplaza por cero.

`factores_riesgo` incluye seis aportes individuales Tree SHAP, tanto de riesgo
como de proteccion, con contribucion_pp firmada, direccion y peso relativo.
`explicacion_modelo` permite reconstruir el score a partir de referencia y aportes.
`resumen_explicativo` explica las contribuciones y sugiere seguimiento docente;
`acciones_sugeridas` devuelve esas sugerencias por separado. En exclusiones los
factores siguen vacios. No son causas ni porcentajes de culpa. Ver el documento
de explicabilidad para interpretar la referencia interna y los pesos.
El servicio no escribe en Laravel ni en PostgreSQL. Escucha localmente sin
autenticacion; esta configuracion sirve para Laravel en la misma computadora.

Ejemplo desde Laravel (ajustar la construccion de `$payload` al controlador):

```php
use Illuminate\Support\Facades\Http;

$respuesta = Http::acceptJson()->timeout(10)
    ->post('http://127.0.0.1:8001/api/v1/predict', $payload)
    ->throw()->json();

// Para lotes, enviar la respuesta del endpoint dataset-alumnos como $dataset.
$lote = Http::acceptJson()->timeout(30)
    ->post('http://127.0.0.1:8001/api/v1/predict-batch', $dataset)
    ->throw()->json();
```

Pruebas del contrato, validacion, retiros, pausas y respuesta local de Laravel:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```
