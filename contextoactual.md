# Contexto actual para continuar el trabajo

## Actualizacion mas reciente: arranque automatico desactivado

Se eliminaron las tareas `Scala-Servicios` y `Scala-Preparar-Seguimiento`.
`n8n/compose.yaml` usa `restart: "no"` y el contenedor actual tambien se actualizo
con politica de reinicio `no`. Se agrego `startup/start-manual.ps1` para iniciar
voluntariamente el supervisor y los servicios requeridos.

Windows denego el cambio de inicio automatico de PostgreSQL por falta de permisos
de administrador. El servicio `postgresql-x64-16` sigue en Automatic y activo; para
dejar todo el stack en inicio manual, ejecutar `startup/install.ps1` como admin.
Ver `startup/README.md`. Las aplicaciones que ya estaban en ejecucion no se detuvieron.

## Actualizacion mas reciente: /api/ml protegido y n8n actualizado

Usuario pidio cerrar el acceso global y mantener n8n, con urgencia.
YA COMPLETADO. Ambas rutas /api/ml exigen Bearer de servicio mediante nuevo
middleware RequireMlServiceToken. Sin token/invalido401; configuracion vacia503.
Sesion docente, grupo_id o token en query no autorizan esos endpoints globales.
Token aleatorio32bytes en sw-scala/.env ML_INTEGRATION_TOKEN y configservices.ml.integration_token.
No imprimir token ni leer/volcar .env completo. No se cambiaron roles ni contraseñas.

n8n usa la credencial cifrada httpHeaderAuth ID ScalaLaravelMl01, nombre
Scala Laravel ML - servicio, solo en los nodos Laravel dataset y guardado.
El flujo se respaldo desde la instancia, se actualizo, importo y publico otra vez,
manteniendo diario20h America/La_Paz. Archivo fuente n8n/workflows/scala-seguimiento-diario.json
contiene referencias de credencial, NO el secreto. Copias temporales de importacion
del token fueron borradas en host data/ y /tmp del contenedor tras importarlo.

Pruebas finales: 24 tests Laravel/180 assertions PASAN. Nuevos cinco casos
MlEndpointSecurityTest cubren credenciales ausentes/invalidas, sesion docente,
grupo forzado, token query, configuracion vacia y credencial servicio valida.
Suites n8n/SHAP/legacy ahora usan token explicito de prueba en setUp.
HTTP real tambien comprobo401 en ambos endpoints sin token y token erroneo.
Ejecucion REAL n8n autenticada: success, 7 actualizadas/5omitidas; verificacion
PostgreSQL de solo lectura ejecutada con origenN8N_AUTO y --xai, exit0.

Archivos backend cambiados: app/Http/Middleware/RequireMlServiceToken.php,
config/services.php, routes/web.php, .env/.env.example y pruebas de integracion.
No migraciones. php artisan config:clear ejecutado. Bootstrap conserva el arreglo
previo para respetar expectsJson. Rutas /riesgo mantienen aislamiento docente.

Documentacion nueva security/README.md. Evidencia: data/n8n-ejecucion-auth.log,
data/verificacion_auth.json; respaldo de flujo data/n8n-antes-auth.json.
Cliente predecir_laravel.py requiere LARAVEL_API_TOKEN en entorno (ya lo soportaba);
presentation/actualizar_alerta7.py ahora tambien lo admite. No enviar token a FastAPI.
Verificacion HTTP publica: python security/verificar_http.py (no necesita secreto).
Aplicador security/aplicar.py YA SE EJECUTO; usa manifest con hashes anteriores,
no repetir a ciegas. El pendiente de endpoints publicos de secciones antiguas queda
RESUELTO por esta actualizacion. No afirmar que siguen publicos.

## Actualizacion mas reciente: aislamiento del modulo de alertas por docente verificado

El usuario pidio verificar acceso docente a alerta7 y bloqueo de otros grupos.
Se agrego sw-scala/tests/Feature/DocenteAlertasTest.php con 8 pruebas HTTP
autenticadas usando actingAs del usuario Docente REAL asignado al grupo de
alerta7, y otro docente real de un grupo diferente. No se cambiaron roles,
contraseñas ni sesion de navegador; no fue una prueba visual con login docente.

Todas pasan: GET propio200 con seis factores/resumen/acciones/rolDocente;
Inertia Riesgo/Show correcto; GET ajeno403 HTML y JSON sin datos explicativos;
bandeja/grupos/KPIs limitados al alcance; filtro forzado de grupo ajeno vacio;
cambio de estado ajeno403; crear o editar intervencion ajena403 sin cambios;
docente de otro grupo no puede abrir alerta7.

Se corrigio bootstrap/app.php: shouldRenderJsonWhen antes solo is('api/*'),
ahora is('api/*') || expectsJson(). La autorizacion ya bloqueaba con403, pero
las peticiones JSON de rutas web recibian HTML. El fallo inicial de prueba
provenia de intentar inspeccionar ese HTML como JSON, no de un acceso permitido.
Las comparaciones de intervenciones se hacen tras refresh para usar valores
persistidos (PostgreSQL normaliza fecha y campos null), evitando falsos fallos.

Comprobacion final conjunta: 19 pruebas/163 assertions, PASAN:
DocenteAlertasTest, XaiPersistenciaTest, N8nBatchWebhookTest,
FastApiIntegrationTest y RiesgoPredictivoTest. Todo en DatabaseTransactions;
no quedan cambios academicos ni intervenciones temporales de prueba.
Documentacion: permissions/README.md. Copias y manifest en permissions/ ya aplicados.

HALLAZGO FUERA DE LAS RUTAS /riesgo, AUN PENDIENTE:
Los endpoints globales /api/ml/dataset-alumnos y /api/ml/webhook-alertas siguen
publicos, fuera de auth y sin token de servicio (POST sin CSRF para integracion).
No afirmar aislamiento completo entre grupos a traves de todas las interfaces.
Se requiere autenticar esos endpoints coordinadamente con credenciales n8n,
clientes y pruebas para no romper el flujo diario. No se modificaron en esta etapa.

## Actualizacion mas reciente: presentacion de alerta 7 corregida y revisada

El usuario pidio separar resumen/acciones, aclarar protecciones confusas y
mostrar el score con dos decimales. YA SE APLICO y se verifico visualmente en
Laravel autenticado; la sesion actual es Admin Propietario, NO docente. No se
cambiaron roles ni se comprobo acceso usando credenciales de un docente.

Cambios backend Python: app/explanations.py ya no agrega el texto de las acciones
dentro de resumen_explicativo; acciones_sugeridas sigue devolviendolas aparte.
Tests comprueban ausencia de duplicacion. Modelo, score y aportes SHAP no cambiaron.

Cambios Laravel: Show.vue muestra Resumen de la prediccion y una seccion separada
Acciones sugeridas para el docente con lista de tres elementos en alerta7.
Show.vue e Index.vue usan formatScore con toFixed(2), incluso para enteros.
La referencia interna tambien se muestra a dos decimales (49.91%).
El helper explicacion.js incorpora aclaracionFactor: ante un aporte SHAP negativo
con un indicador academicamente desfavorable, muestra aviso ambar explicando
que reducir la estimacion relativa del modelo NO hace favorable el indicador ni
implica que mejorarlo aumente el riesgo. Cubre faltas, tendencia negativa, promedio
<70, asistencia <75, atrasos y observaciones. Mantiene signos y scores reales.

Se recompilo sw-scala con npm run build exitosamente y pasaron 13 tests Python.
Se reinicio FastAPI: PID29480, sesion exec25957, puerto8001.
Se actualizo UNICAMENTE alerta7 mediante presentation/actualizar_alerta7.py:
GET datos actuales → predict individual → webhook lote de una inscripcion.
Resultado: alerta ID7, score45.62, tres acciones, estado EN_ATENCION e intervencion
previa conservados. No se reejecuto n8n para todas las alertas en esta etapa.
Otras alertas adoptaran el nuevo resumen sin acciones duplicadas al proximo analisis.
No cambio el horario diario de n8n.

Verificacion visual CUA de /riesgo/alertas/7: score45.62%, lista separada de acciones,
avisos ambar en factores protectores, sin desbordamiento observado en la ventana
normal. Captura de evidencia data/alerta7-resumen-acciones.jpg. Evidencia de API
en data/alerta7_presentacion.json. No se modificaron formularios ni estado en UI.
Copias y aplicador con hashes en presentation/laravel: YA APLICADO, no reejecutar
con manifest viejo. No hubo migraciones ni cambios al servicio de persistencia PHP.

## Actualizacion mas reciente: explicabilidad individual implementada

El usuario solicito factores de riesgo y resumen entendible por el docente.
YA ESTA IMPLEMENTADO, probado y guardado en las siete alertas reales. Los parrafos
anteriores que dicen factores vacios o explicabilidad pendiente quedaron obsoletos.

Metodo: Tree SHAP de la libreria shap, version instalada 0.54.1. Dependencia
agregada a requirements.txt como shap>=0.48,<1. Modelo de reprobacion positivo 1,
tree_path_dependent, raw (probabilidad para sklearn RandomForestClassifier).
Se comprueba por cada prediccion la aditividad contra predict_proba. No se cambio
el modelo ni sus scores; version modelo demo-sintetica-v2, explicacion tree-shap-v1.

Archivos nuevos: app/explanations.py, explainability/README.md y copias preparadas
de Laravel en explainability/laravel. Modificados predictor, schemas y test_api.py.
Cada prediccion calculada devuelve seis factores con direccion AUMENTA/REDUCE/NEUTRO,
contribucion_pp firmada, valor observado, categoria, descripcion y peso relativo
impacto. El campo factores_riesgo incluye tambien protecciones por compatibilidad.
El peso relativo normaliza magnitudes absolutas; no es score ni porcentaje de culpa.
explicacion_modelo contiene referencia interna y score reconstruido.
Referencia actual aprox49.91%; sintetica y balanceada, NO tasa real institucional.
acciones_sugeridas y resumen_explicativo se generan con plantillas, sin LLM ni
llamadas externas. Explican dos aumentos principales y una reduccion, proponen
seguimiento y advierten sobre umbrales actuales <51 notas o <65 asistencia.
PAUSADA se menciona aparte sin entrar en SHAP. Exclusiones siguen sin score/factores.

Laravel ya conserva explicacion_modelo y acciones_sugeridas en metricas_base.prediccion_ml
tanto para consulta directa como webhook n8n. Index.vue y Show.vue muestran
aportes de riesgo rojos y protecciones verdes, con unidades puntos porcentuales.
El helper nuevo resources/js/Pages/Riesgo/explicacion.js mantiene compatibilidad
con factores heurísticos antiguos. El detalle muestra referencia interna y
aclara que los pesos no son causas; factores vacios indican explicacion no disponible.
No hubo migraciones. Se compilaron los assets con npm run build, exitosamente.

Verificacion: 13 tests Python PASAN; 11 tests Laravel/107 assertions PASAN,
incluyendo XaiPersistenciaTest.php. N8nBatchWebhookTest ahora compara factores
con el payload en lugar de exigir lista vacia. La prueba FastApiIntegrationTest
que usa fixture HTTP fake sin explicacion sigue comprobando compatibilidad.

Se detuvo la instancia FastAPI anterior y se inicio otra con SHAP:
PID 2212, sesion exec 62517, localhost:8001. Se ejecuto n8n execute con broker5680:
success, 7 alertas actualizadas y 5 omitidas; horario diario20h no modificado.
Se verificaron las siete en PostgreSQL SOLO LECTURA: seis factores TREE_SHAP,
referencia mas aportes coincide con score, resumen sintetico y acciones presentes,
origen N8N_AUTO, version demo-sintetica-v2, sin duplicados.
Verificador acepta argumento --xai:
`php laravel-integration/verificar_alertas.php N8N_AUTO --xai`.

Ejemplo inscripcion7: score45.62 MEDIO, asistencia56% aporta +6.09pp,
observaciones2 +5.31pp, promedio67.5 aporta -11.76pp frente a referencia interna.
Que el promedio reduzca el score NO lo convierte en excelente: resumen recomienda
refuerzo y seguimiento de la pausa. Todas las cifras siguen siendo experimentales.

Evidencias en data/ (no publicar logs con datos personales): predicciones_xai.json,
predicciones_xai_lista.json, n8n-ejecucion-xai.log, verificacion_xai.json.
Documentacion completa y limites: explainability/README.md.
Pendientes reales: validacion historica, posible estado PAUSADA como feature,
alinear generador con asistencia ponderada real y asegurar servicios encendidos.
La interfaz se compilo y se probo el contrato del detalle Laravel; no se hizo
inspeccion visual autenticada de la pagina durante esta etapa.

## Actualizacion mas reciente: n8n configurado y publicado

El usuario pidio automatizar el recorrido completo y eligio TODOS LOS DIAS A LAS
20:00 (America/La_Paz). Se instalo n8n 2.47.3 en Docker Desktop, contenedor scala-n8n,
editor localhost:5678, volumen persistente scala-automation_scala_n8n_data.
Docker Desktop estaba instalado pero detenido; se inicio con su CLI.

Flujo ID ScalaMlDiario2000, nombre Scala Musical - seguimiento diario 20h.
Cron 0 20 * * *, timezone America/La_Paz. Importado y PUBLICADO con CLI; exportacion
confirmo active=true, activeVersionId coincide con versionId.
Fuente: n8n/workflows/scala-seguimiento-diario.json. Compose: n8n/compose.yaml.
Documentacion completa y reinicio: n8n/README.md.

Flujo: disparador diario/manual → GET Laravel dataset → POST FastAPI predict-batch
→ POST Laravel webhook-alertas. Desde Docker usa host.docker.internal:8000/8001.
Conexion comprobada HTTP 200 a ambos servicios. Reintentos HTTP: 3, espera 3s.
No hay nodos Code ni necesidad de Python dentro de n8n. Un aviso de runner Python
ausente es incidental; los nodos HTTP se ejecutaron correctamente.

Se adapto el webhook Laravel con un nuevo contrato estricto `resultados` que
acepta directamente el sobre FastAPI. Valida el lote, omite cinco exclusiones,
conserva factores vacios/version/metadata, usa transaccion y bloqueos, actualiza
sin duplicar. Lote vacio no ejecuta fallback. Contrato legado se conserva aparte.
Nuevo metodo RiesgoPredictivoService::procesarResultadosMl; apiWebhookAlertas
detecta resultados antes de la logica antigua.

Prueba REAL n8n execute exit 0, status success, ultimo nodo Guardar alertas en
Laravel. Respuesta: procesadas=7, omitidas=5, alerta_ids=[1,2,3,4,5,7,12],
inscripciones_omitidas=[6,8,9,10,11], origen=N8N_AUTO.
Se verificaron despues las 7 filas en PostgreSQL, lectura exclusiva:
origen N8N_AUTO, version demo-sintetica-v2, scores previos, metadata experimental,
sin duplicados. Cambio de origen es intencional: orquestador N8N_AUTO,
metricas_base.prediccion_ml.proveedor=ML_API identifica al proveedor del modelo.
El verificador ahora acepta argv[1] como origen esperado, ML_API por defecto:
`php laravel-integration/verificar_alertas.php N8N_AUTO`.

Se completaron las pruebas antes pendientes. Las heredadas esperaban factores
locales no vacios; se ajusto su setUp para desactivar services.ml.enabled y probar
explicitamente el motor local. Resultado final: 10 pruebas, 98 assertions, PASAN:
N8nBatchWebhookTest, FastApiIntegrationTest, RiesgoPredictivoTest.
La suite n8n comprueba rollback total, exclusiones, no duplicacion, metadata,
lote vacio y rechazo de totales/IDs duplicados.

Archivos backend de esta etapa: servicio, controlador, test nuevo N8nBatchWebhookTest
y setUp del test heredado RiesgoPredictivoTest. No hubo migraciones.
Copias de preparacion en n8n/laravel; aplicar.py YA se ejecuto. No reejecutar
sin revisar hashes. El manifest actual corresponde a la ultima aplicacion del test.

Evidencia local (data/ excluido de Git): n8n-ejecucion.log (incluye datos personales
del dataset, no publicar), n8n-publicado.json, verificacion_n8n.json.
Para n8n CLI execute mientras corre el editor, definir broker port 5680:
`docker exec -u node -e N8N_RUNNERS_BROKER_PORT=5680 scala-n8n n8n execute --id=ScalaMlDiario2000 --rawOutput`.
El primer intento sin ese cambio fallo por puerto 5679 ocupado; segundo exitoso.

Persistencia del flujo verificada con exportacion publicada y reinicio del contenedor.
PC, Docker Desktop, Laravel y FastAPI deben seguir encendidos a las 20:00;
no se implemento servicio Windows para PHP/Python ni servidor 24/7.
Al abrir editor puede pedir configuracion de cuenta propietaria local; no se
crearon credenciales ficticias ni se desactivo autenticacion. CLI publico el flujo.

Los pendientes antiguos sobre adaptar webhook/instalar n8n/verificar origen/ejecutar
tests de regresion quedaron resueltos por esta actualizacion. Siguen pendientes
validacion con historicos reales, explicabilidad individual, posible PAUSADA como
feature y ajustes de la simulacion al calculo real de asistencia de Laravel.

## Actualizacion posterior: verificacion PostgreSQL completada

El usuario solicito continuar verificando las 7 alertas. Se creo y ejecuto
`iaService/laravel-integration/verificar_alertas.php` mediante Laravel con una
transaccion PostgreSQL `SET TRANSACTION READ ONLY`. Resultado: codigo 0,
7 esperadas, 7 encontradas, 7 verificadas, errores vacios.

Todas tienen origen `ML_API`, relacion VersionModelo `demo-sintetica-v2`, metadata
experimental=true y entrenado_con=SINTETICO. Scores y niveles coinciden con las
predicciones previas de FastAPI. Cada inscripcion elegible tiene exactamente una
alerta existente (sin duplicados en esas siete).

Inscripcion/alerta IDs: 1,2,3,4,5,7,12. Scores respectivamente:
5.70,14.64,2.93,1.22,1.56,45.62,2.70. Solo la 7 tiene nivel MEDIO; otras BAJO.
Fechas de analisis observadas: 2026-11-10 19:22:53-54 UTC (15:22:53-54 La Paz).
Esta actualizacion resuelve el pendiente de lectura posterior descrito mas abajo;
ya no debe afirmarse que falta comprobar si el comando uso fallback.
No se modificaron filas durante esta verificacion. La prueba anterior
RiesgoPredictivoTest.php sigue pendiente; no se ejecuto en este turno.

Fecha: 10 de noviembre de 2026. Usuario trabaja en Windows, PowerShell, zona America/La_Paz.

## Objetivo y pedido actual

Construir un servicio externo Python/ML para Scala Musical, integrarlo con Laravel
y guardar alertas de seguimiento. Posteriormente se contempla automatizar con n8n.
El ultimo pedido fue conectar Laravel con FastAPI y guardar las alertas en sw-scala.
El usuario ahora solicita este documento para entregar el contexto a otra IA.

## Ubicaciones

- Servicio Python y carpeta principal: `C:/2-2026/taller/1erPanel/iaService`.
- Laravel: `C:/2-2026/taller/1erPanel/sw-scala` (proyecto hermano).
- Python del proyecto: `iaService/.venv/Scripts/python.exe`, Python 3.12.9.
- PHP encontrado: `C:/xampp/php/php.exe`.
- PostgreSQL existente de Laravel: se utiliza su configuracion; no copiar secretos al contexto.
- Laravel responde en `http://127.0.0.1:8000`.
- FastAPI responde en `http://127.0.0.1:8001`.

En esta sesion solo iaService era escribible directamente. Para escribir en
sw-scala, ejecutar Laravel o acceder a sockets locales fue necesario solicitar
ejecucion con `sandbox_permissions=require_escalated`. No eludir esas restricciones.
El ultimo intento de ejecutar una comprobacion adicional fue rechazado porque
la revision automatica de permisos no pudo completarse por limite de uso.

## Reglas de negocio comunicadas por el usuario

No todas se verificaron directamente contra el codigo; distinguir reglas
comunicadas de comportamiento efectivamente probado.

- Objetivo principal: anticipar reprobacion con tiempo para intervenir.
- Objetivo secundario: anticipar abandono, relacionado pero diferente.
- Escala de notas 0-100; aprobar desde 51, reprobar con nota final < 51.
- Periodos de 10-12 semanas, 1-2 sesiones semanales.
- Primera alerta desde semana 2-3, tras 3-4 sesiones y primera evaluacion practica.
- ACTIVA: cursando; PAUSADA: congelamiento temporal, requiere seguimiento;
  CANCELADA: retiro/abandono confirmado con fecha_retiro.
- PAUSADA aun NO entra en las seis features; no afirmar que el modelo la aprende.
- Score de salida: ALTO >= 65; MEDIO >= 35 y < 65; BAJO < 35.
- Semaforo institucional actual comunicado: excelente nota >= 90 y asistencia >=85;
  favorable nota 70-89.99 y asistencia >=75; regular nota 51-69.99;
  alto nota <51 o asistencia <65. No confundir ese semaforo con la prediccion futura.
  Hay combinaciones no cubiertas por las categorias comunicadas.

## Datos reales y limitaciones

Hay 12 inscripciones actuales, no resultados historicos confirmados para validar ML.
Se entrenaron modelos con 3000 registros SINTETICOS. Todas las probabilidades
son experimentales y no calibradas con resultados reales. No presentar metricas
sinteticas como eficacia educativa real ni como porcentajes exactos de riesgo.

Las seis entradas son:
1. porcentaje_asistencia
2. faltas_injustificadas
3. atrasos
4. promedio_calificaciones
5. tendencia_notas
6. observaciones_negativas

Laravel entrega la sexta como `total_obs_alerta` (coincide en los 12 casos
observados con obs_disciplina + obs_recomendacion). El adaptador acepta ese alias.
Laravel calcula asistencia ponderando atrasos al 80%; el generador sintetico
todavia usa proporcion simple de sesiones no faltadas: diferencia a revisar.

El endpoint de Laravel `GET /api/ml/dataset-alumnos` devuelve un objeto con:
status, generado_en, version_modelo, total_registros, dataset y alumnos.
dataset y alumnos son alias del mismo listado; NO concatenarlos.
Cada elemento incluye inscripcion_id, alumno, grupo, features.
features trae variables adicionales (estado, sesiones, evaluaciones, observaciones).
Algunas inscripciones sin evaluaciones tienen promedio_calificaciones=null.

De las 12 inscripciones observadas:
- 1,2,3,4,5,12: ACTIVA con datos suficientes.
- 7: PAUSADA con datos suficientes.
- 6: PAUSADA sin sesiones ni evaluaciones: DATOS_INSUFICIENTES.
- 8,9,10,11: CANCELADA: NO_APLICA_RETIRO_CONFIRMADO.

Solo 7 reciben prediccion. Procesar las 12 no significa inventar scores para las
cinco excluidas. No borrar alertas historicas de las excluidas sin nueva instruccion.

## Archivos de iaService

- `training/generar_dataset.py`: generador reproducible, semilla 42 por defecto.
  Fotografias tempranas 3-4 sesiones, 1 evaluacion, semana 2-3; periodo 10-12 semanas.
  Genera nota final futura simulada; reprobo = nota final <51; abandono separado.
  No usa resultados futuros ni IDs como features de entrenamiento.
- `training/train_model.py`: dos RandomForestClassifier (reprobo y abandono),
  particion estratificada 75/25, 200 arboles, profundidad 8, hojas minimas 8,
  class_weight balanced. Guarda bundle `models/modelos_demo.joblib`.
- Bundle actual: version `demo-sintetica-v2`, origen SINTETICO, lista ordenada
  de features y diccionario de los dos modelos. Joblib solo debe cargar artefactos propios.
- `app/predictor.py`: logica compartida con CLI; carga bundle, comprueba contrato,
  aplica exclusiones, calcula probabilidades y nivel, devuelve metadata experimental.
- `app/schemas.py`: contratos Pydantic, rangos, tipos estrictos, alias,
  estados, validacion de lotes y respuestas.
- `app/main.py`: FastAPI, carga unica en lifespan; variable opcional ML_MODEL_PATH;
  arranque falla si falta modelo o es incompatible.
- `reglas_negocio.py`: niveles a partir de limites 35/65.
- `predecir_laravel.py`: cliente CLI GET a Laravel o `--entrada` para JSON local;
  reutiliza Predictor, guarda salida local, NO escribe en Laravel.
- `requirements.txt`: scikit-learn, joblib, fastapi, uvicorn.
- `requirements-dev.txt`: requirements base mas httpx.
- `tests/test_api.py`: 9 pruebas de API.
- `README.md`: comandos, supuestos, contrato y ejemplo PHP para llamadas HTTP.
- `.gitignore`: excluye .venv, __pycache__, data y models.
- `contenido_necesarioVer.md`: guia inicial proporcionada por el usuario; sus
  afirmaciones de eficacia, explicabilidad y disponibilidad no son evidencia.

## API FastAPI implementada

- `GET /health`: status y version_modelo.
- `POST /api/v1/predict`: {inscripcion_id, features, alumno_codigo opcional}.
- `POST /api/v1/predict-batch`: acepta lista o envoltorios dataset, data, alumnos;
  1-1000 elementos, IDs unicos, total_registros coherente si se proporciona.
- `GET /docs`: Swagger; el usuario abrio esa pagina en el navegador integrado.

Respuesta individual incluye:
inscripcion_id, version_modelo, experimental, entrenado_con, estado_inscripcion,
estado_prediccion, score_riesgo, nivel_riesgo, estimacion_reprobo_pct,
estimacion_abandono_pct, requiere_seguimiento_por_pausa, aviso,
factores_riesgo, resumen_explicativo.

Score principal = estimacion de reprobacion. No sumar probabilidad de abandono.
Factores_riesgo esta VACIO porque no hay explicacion individual implementada;
no inventar impactos usando feature_importances_ global.
Con retiro o datos insuficientes score y nivel son null.
Nota null se acepta solo si no se va a calcular prediccion.
Si faltan conteos de sesiones/evaluaciones se asume elegibilidad ya comprobada
por el cliente; si se proporcionan, se exige >=3 sesiones y >=1 evaluacion.
Errores de validacion HTTP 422; lote invalido se rechaza completo.

Inicio desde iaService:
```powershell
.\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8001
```
La ultima instancia se inicio en una sesion exec con ID 68976, PID informado 18408.
Revisar disponibilidad antes de iniciar otra; el servicio puede haber finalizado.
Solo escucha en loopback; no se configuro autenticacion ni despliegue remoto.

## Evidencia de verificaciones Python

- Generador: cantidad, rangos, reproducibilidad, etiquetas futuras y limites 35/65.
- Entrenamiento de ambos modelos completado.
- `python -m unittest discover -s tests -v`: 9 pruebas pasaron.
- Pruebas HTTP reales de predict y predict-batch exitosas.
- Lote: 12 procesadas, 7 calculadas; scores coinciden con CLI anterior.
- httpx TestClient emite aviso de deprecacion con la version instalada de Starlette;
  las pruebas pasan. No se migro a httpx2.

Resultados de demostracion previos a la integracion Laravel:
| inscripcion | score reprobacion | nivel | estimacion abandono |
|---|---:|---|---:|
|1|5.70|BAJO|13.82|
|2|14.64|BAJO|38.56|
|3|2.93|BAJO|42.88|
|4|1.22|BAJO|25.30|
|5|1.56|BAJO|13.83|
|7|45.62|MEDIO|61.54|
|12|2.70|BAJO|40.38|

Archivos locales de evidencia, excluidos de Git:
- data/dataset_sintetico.csv
- data/respuesta_laravel.json (CONTIENE nombres/correos: no publicar ni copiar a logs)
- data/predicciones_demo.json
- data/predicciones_fastapi.json (sobre batch con resultados)
- data/predict_request.json
- data/prediccion_fastapi_individual.json
- data/respuesta_fastapi_error.json (diagnostico previo a correccion de notas nulas)

## Integracion Laravel YA APLICADA

El repositorio sw-scala estaba limpio segun `git status --short` antes de editar.
No se encontraron AGENTS.md en las rutas de instrucciones revisadas.
No hubo commits. Se aplicaron estos archivos mediante script autorizado:

1. `sw-scala/app/Services/RiesgoPredictivoService.php`
   - Ya existia integracion HTTP, pero estaba deshabilitada y usaba env directo.
   - Ahora lee config services.ml y llama a FastAPI /api/v1/predict.
   - connectTimeout=2; timeout configurable, actualmente 10 segundos.
   - Envia features reales con total_obs_alerta, sesiones y evaluaciones.
   - analizarInscripcion devuelve ?AlertaSeguimiento: null para CANCELADA,
     menos de 3 sesiones, menos de 1 evaluacion o promedio null.
   - analizarAcademia cuenta solo alertas realmente guardadas/actualizadas.
   - Valida ID, estado CALCULADA, score finito en 0-100, nivel coherente,
     version de 1-30 caracteres [a-zA-Z0-9._-], factores array y resumen string.
   - Conserva factores vacios de FastAPI: no los reemplaza con explicacion heuristica.
   - Registra/obtiene VersionModelo por version real devuelta por FastAPI.
     Nueva version se crea inactiva; NO cambia automaticamente el modelo activo.
     Esquema obliga fecha/metricas: usa fecha de registro y metricas 0 como
     marcadores, explicitados en descripcion. No afirmar entrenamiento en esa fecha.
   - Guarda metadata ML en metricas_base.prediccion_ml: version, experimental,
     origen sintetico, ambas estimaciones, seguimiento por pausa y aviso.
   - Guarda origen ML_API solo al obtener respuesta ML valida.
   - Si falla HTTP o contrato, usa clasificarLocalmente y origen MOTOR_LOCAL;
     registra warning sin nombres, features ni secretos.
   - Guarda origen solicitado del proceso en metricas_base.origen_ejecucion.
   - Actualiza alerta existente en vez de duplicar; preserva estados e intervenciones.
   - Se mantiene regla anterior: DESCARTADA reabre a PENDIENTE si sube a ALTO.

2. `sw-scala/config/services.php`: nueva seccion ml con enabled, url, timeout.
3. `sw-scala/.env.example`: variables ML documentadas con enabled=false.
4. `sw-scala/.env`: ML_SERVICE_ENABLED=true,
   ML_SERVICE_URL=http://127.0.0.1:8001, ML_SERVICE_TIMEOUT=10.
   No exponer otras variables de .env.
5. `sw-scala/tests/Feature/FastApiIntegrationTest.php`: 3 pruebas transaccionales.

No hubo migraciones ni alteracion de tablas.
Se ejecuto `php artisan config:clear` exitosamente.

En iaService/laravel-integration quedan los archivos preparados, manifest.json y
aplicar.py como evidencia. El aplicador verifica hashes originales para evitar
sobrescribir cambios concurrentes. YA SE EJECUTO; no volver a ejecutarlo a ciegas:
su manifest contiene hashes anteriores y debe rechazar un segundo intento.

## Pruebas y ejecucion real Laravel

`php artisan test --filter=FastApiIntegrationTest` inicialmente fallo porque
phpunit.xml referencia tests/Unit que no existe. No se modifico esa configuracion.
Usar archivo explicito:

```powershell
php artisan test tests/Feature/FastApiIntegrationTest.php
```

Resultado: 3 pruebas PASARON, 17 assertions, con DatabaseTransactions:
- guarda score/version/metadata y actualiza sin duplicar;
- fallo HTTP o nivel inconsistente usa origen MOTOR_LOCAL;
- retiros y datos insuficientes no generan alertas ni consultas HTTP.

Se verifico FastAPI health: ok, demo-sintetica-v2.

YA SE EJECUTO EL GUARDADO REAL solicitado por el usuario:

```powershell
php artisan scala:evaluar-riesgo --origen=ML_API
```

Codigo de salida 0. Salida:
"Iniciando analisis predictivo de riesgo academico SCALA..."
"Analisis finalizado exitosamente. Inscripciones evaluadas: 7."

Esto confirma que Laravel guardo/actualizo 7 alertas. AUN NO se hizo la lectura
posterior de PostgreSQL para confirmar IDs, origen ML_API, version y scores de
cada fila. Como existe fallback, el exito del comando NO prueba por si solo que
las siete vinieran de FastAPI. Esa es la siguiente verificacion importante.

El intento siguiente de ejecutar:
`php artisan test tests/Feature/RiesgoPredictivoTest.php`
NO se ejecuto: la revision automatica de permisos fallo por limite de uso.
No fue un resultado de tests ni un rechazo por considerar insegura la accion.
Mensaje esencial: "Automatic approval review failed: You've hit your usage limit ...
The action was not executed because automatic approval review could not be completed."
No intentar eludir esa revision mediante otra herramienta o shell.

## Pendientes prioritarios

1. Leer de forma autorizada las 7 filas actuales de alerta_seguimiento
   (solo ID, inscripcion_id, origen, score, nivel, version y metadata experimental;
   no imprimir nombres ni secretos). Confirmar que sean ML_API/demo-sintetica-v2
   y coincidan con los scores de arriba. Revisar logs si hay fallback.
2. Ejecutar pruebas anteriores RiesgoPredictivoTest.php cuando la revision de
   permisos permita hacerlo. La primera exige factores no vacios porque prueba
   motor local; con ML ahora habilitado puede necesitar config services.ml.enabled=false
   explicita en ese test para mantener su intencion. No falsificar resultados.
3. Revisar git diff en sw-scala y documentar integracion en su README.
4. Considerar prueba repetida del comando solo si se requiere confirmar idempotencia
   real (ya cubierta con HTTP fake en test).
5. La UI existente muestra modelo activo anterior: alertas ML quedan enlazadas a
   version real, pero no se cambio activo global. Verificar presentacion antes de
   afirmar que toda la bandeja representa modelo sintetico.
6. Webhook `/api/ml/webhook-alertas` EXISTE pero NO SE ADAPTO en esta etapa.
   Espera predicciones o alertas, mientras FastAPI batch devuelve resultados.
   Puede hacer fallback heuristico para scores null y rellenar factores vacios;
   NO enviar directamente el batch sin adaptar/validar/calcular exclusiones.
   Esto importa al implementar n8n.
7. No se implemento cliente batch Laravel: el comando actual usa endpoint individual
   siete veces. Ambos endpoints FastAPI estan disponibles y probados.
8. Posteriormente: n8n, explicabilidad individual, validacion con datos historicos,
   posible incorporacion temporal de PAUSADA y ajuste de simulacion a asistencia real.

## Preferencias de trabajo y comunicacion

- Responder en espanol, con explicaciones claras y concretas.
- Usuario pide avanzar paso a paso y ejecutar, no solo proponer.
- No crear subagentes salvo solicitud explicita/instruccion aplicable.
- No leer ni publicar credenciales completas. Evitar volcar .env o phpunit.xml entero.
- Si revision automatica vuelve a fallar, informar accion bloqueada y motivo;
  no decir que una prueba fallo cuando ni siquiera se ejecuto.
- Las lecturas Get-Content en PowerShell resultaron lentas. cmd.exe con login=false
  funciono para comandos simples; node_repl/fs se uso para lectura y preparacion local.
- En exec/cmd se observaron problemas con comillas en argumentos de curl/python -c;
  se uso cabecera `Content-Type:application/json` sin espacios y archivos JSON locales.
