# Explicaciones individuales para el docente

Implementado el 10 de noviembre de 2026. La prediccion sigue usando los mismos
dos Random Forest sinteticos; no se reentreno ni se cambio el score al agregar
explicaciones. La version del modelo permanece `demo-sintetica-v2` y la version
de explicacion es `tree-shap-v1`.

## Metodo y significado

Se utiliza `shap.TreeExplainer` sobre el modelo de REPROBACION, clase positiva 1,
con `feature_perturbation=tree_path_dependent` y `model_output=raw`.
En este RandomForestClassifier sklearn la salida es probabilidad; cada respuesta
verifica explicitamente que la referencia mas los aportes reproduce predict_proba.
No se explica aqui el modelo secundario de abandono.

Cada una de las seis variables devuelve:

- variable, nombre/factor, categoria y valor observado;
- `contribucion_pp`: aporte firmado, en puntos porcentuales;
- `direccion`: AUMENTA, REDUCE o NEUTRO;
- `impacto`: peso relativo de la MAGNITUD ABSOLUTA entre los seis aportes;
- descripcion docente y version del explicador.

El campo compatible `factores_riesgo` contiene tanto riesgos como protecciones;
se conservan las seis variables para poder reconstruir el score. Se ordenan
primero los incrementos, luego las reducciones. Los pesos relativos suman 100%
cuando hay aportes no nulos; si todos son cero, sus pesos son cero.
Ese 100% no es el score, no indica causalidad y no representa porcentaje de culpa.

`explicacion_modelo` incluye la referencia y score reconstruido. La referencia
interna actual es aproximadamente 49.91%; surge de los arboles sinteticos, con
entrenamiento balanceado, y NO es la tasa real de reprobacion de la institucion.
Las variables correlacionadas, como asistencia y faltas, pueden repartirse el
aporte segun los supuestos de Tree SHAP. No interpretar cada aporte como causa
independiente ni como prueba de que cambiar una variable producira ese efecto.

La suma de aportes redondeados a seis decimales mas referencia coincide con el
score sin redondear, salvo precision numerica. El score publicado tiene dos
decimales, por lo que una diferencia menor a 0.0051 puntos es solo redondeo.
Si la explicacion no reconstruye predict_proba, se genera un error; no se
devuelven porcentajes de explicacion inventados ni importancias globales.

## Resumen y sugerencias

`resumen_explicativo` se construye con plantillas deterministas en espanol,
usando los dos incrementos principales y la reduccion principal. No requiere
un LLM, una API de pago ni enviar datos del alumno a terceros.
Las sugerencias se basan en datos observados y se devuelven tambien como
`acciones_sugeridas` (asistencia, refuerzo de evaluaciones y revision pedagogica).
Ahora se devuelven exclusivamente en acciones_sugeridas y Laravel las muestra
en una lista separada: no se repiten dentro del resumen. El score en bandeja y
detalle usa dos decimales. Los aportes protectores asociados a indicadores
academicamente desfavorables llevan una aclaracion ambar junto al factor.

La pausa de inscripcion se menciona como seguimiento de negocio, separada del
calculo SHAP porque no es una feature del modelo. Si asistencia <65% o promedio
<51, el resumen avisa del umbral institucional critico aunque el score ML sea bajo.
La sugerencia no reemplaza el criterio docente ni ordena sanciones automaticas.
Los estudiantes CANCELADA o sin datos suficientes siguen sin recibir score ni
explicacion individual; mantienen un resumen del motivo de exclusion.

## Ejemplo real de demostracion: inscripcion 7

Score 45.62%, nivel MEDIO. Entre sus aportes:

- asistencia 56%: +6.09 puntos porcentuales;
- 2 observaciones: +5.31 puntos porcentuales;
- promedio 67.5/100: -11.76 puntos porcentuales frente a la referencia interna.

Que el promedio reduzca el score relativo al modelo NO significa que 67.5 sea
excelente: la nota sigue bajo 70 y se recomienda refuerzo. El estado PAUSADA y
asistencia bajo 65% justifican seguimiento docente adicional sin cambiar el score.

## Laravel y n8n

La consulta individual y el webhook batch conservan `explicacion_modelo` y
`acciones_sugeridas` en `metricas_base.prediccion_ml`. Los factores y resumen
se guardan en sus columnas existentes. No se modificaron tablas.

Las pantallas `resources/js/Pages/Riesgo/Index.vue` y `Show.vue` usan el helper
`explicacion.js`: rojo eleva el score, verde lo reduce, gris indica magnitud
no relevante al mostrar dos decimales. Las etiquetas dicen puntos porcentuales;
las barras representan peso relativo absoluto. La pantalla de detalle muestra
la referencia interna y distingue el indice heuristico local del ML experimental.
Para alertas antiguas sin SHAP, se identifica el peso como heuristico.

La respuesta vacia de factores ya no se interpreta como prueba de buen rendimiento:
la UI indica que no hay explicacion individual disponible.

Se reinicio FastAPI, luego se ejecuto el flujo n8n existente para renovar las
siete alertas elegibles, conservando IDs, estados e intervenciones.
Origen actual `N8N_AUTO`, proveedor ML_API, modelo demo-sintetica-v2.
La programacion diaria de las 20:00 America/La_Paz no cambio.

## Verificacion y evidencia

- Python: 13 pruebas aprobadas; reconstruccion, signos, individualidad, pausa,
  exclusion, pesos cero y contratos individual/batch.
- Laravel: 11 pruebas aprobadas, 107 assertions; incluye persistencia SHAP y
  presentacion de datos para el detalle, ademas de integracion/n8n/legacy.
- `npm run build`: correcto; quedo el aviso general de chunk grande de Vite.
- Ejecucion REAL de n8n: success, 7 actualizadas y 5 omitidas.
- Lectura PostgreSQL: 7 verificadas, seis factores cada una, referencia mas aportes
  consistente con el score, resumen y sugerencias guardados, sin duplicados.

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
php laravel-integration/verificar_alertas.php N8N_AUTO --xai
```

En sw-scala:

```powershell
php artisan test tests/Feature/XaiPersistenciaTest.php tests/Feature/N8nBatchWebhookTest.php tests/Feature/FastApiIntegrationTest.php tests/Feature/RiesgoPredictivoTest.php
npm run build
```

Evidencia excluida de Git: data/predicciones_xai.json,
data/predicciones_xai_lista.json, data/n8n-ejecucion-xai.log,
data/verificacion_xai.json. El log tecnico de n8n puede contener informacion
personal del dataset; no publicarlo.

Las copias en `explainability/laravel` se aplicaron al backend. No reejecutar
`aplicar.py` con hashes viejos ni sobrescribir cambios concurrentes.
La instancia FastAPI mas reciente se inicio con PID 2212, sesion exec 62517;
comprobar disponibilidad antes de iniciar otra instancia.

Fuente tecnica: [documentacion oficial de TreeExplainer](https://shap.readthedocs.io/en/stable/generated/shap.TreeExplainer.html).
