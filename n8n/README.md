# Seguimiento automatico de Scala Musical

Configurado y probado el 10 de noviembre de 2026.

Actualizacion de seguridad: los dos nodos Laravel ahora usan una credencial
httpHeaderAuth cifrada. Los endpoints /api/ml requieren Bearer de servicio;
las sesiones docentes no autorizan acceso global. Ver [security/README.md](../security/README.md).

## Estado

- Contenedor: `scala-n8n`, imagen oficial fijada en `2.47.3`.
- Editor: http://localhost:5678
- Flujo: `Scala Musical - seguimiento diario 20h`, ID `ScalaMlDiario2000`.
- Publicado y activo cuando n8n esta iniciado manualmente. Cron `0 20 * * *`, zona `America/La_Paz`.
- Cada dia a las 20:00: Laravel GET dataset → FastAPI POST predict-batch → Laravel POST webhook.
- Disparador manual adicional para pruebas desde el editor.
- La instalacion incluye SQLite propio para n8n en un volumen Docker persistente;
  las alertas siguen guardandose en PostgreSQL mediante Laravel.

Al abrir por primera vez el editor puede solicitar configurar la cuenta local
propietaria. No se creo una contraseña ficticia ni se desactivo la autenticacion.
El flujo fue importado y publicado mediante la CLI administrativa local.

## Requisitos para que corra a las 20:00

La PC debe estar encendida y Docker Desktop, Laravel (puerto 8000) y FastAPI
(puerto 8001) deben iniciarse manualmente. El contenedor no se reinicia solo ni
despierta la PC. Para iniciar los servicios del proyecto, consulta
[`startup/README.md`](../startup/README.md).
Las ejecuciones perdidas durante una desconexion no se recuperan automaticamente
con esta configuracion. No se configuro un servicio remoto ni un alojamiento 24/7.

## Comandos desde iaService

```powershell
docker desktop start --detach
docker compose -f n8n/compose.yaml up -d
docker compose -f n8n/compose.yaml ps
docker logs --tail 30 scala-n8n
```

Para detener solo este contenedor, sin borrar su volumen:
```powershell
docker compose -f n8n/compose.yaml stop
```

El volumen `scala-automation_scala_n8n_data` contiene la base n8n y su clave de
cifrado. No ejecutar down -v ni borrar ese volumen si se desea conservarlo.

## Flujo importable y activacion

`workflows/scala-seguimiento-diario.json` es el archivo fuente versionable.
Se exporta inactivo por seguridad al importar; la instancia actual YA esta publicada.
No volver a importarlo sobre el mismo ID si hay cambios manuales que conservar.

Para una instalacion nueva:

```powershell
docker exec -u node scala-n8n n8n import:workflow --input=/workflows/scala-seguimiento-diario.json
docker exec -u node scala-n8n n8n publish:workflow --id=ScalaMlDiario2000
```

Se comprobo una vez el reinicio del contenedor y la persistencia del flujo.
Desde dentro del contenedor, `host.docker.internal` resuelve los servicios del host;
no usar 127.0.0.1 para llamar Laravel/Python desde n8n Docker.
El puerto del editor solo esta expuesto en el loopback del host.

Cada peticion HTTP tiene tres intentos con espera de 3 segundos. Si falla, el
flujo se detiene y NO dispara el fallback local ni sobrescribe alertas con datos
inventados. Los reintentos de guardado actualizan las mismas alertas, sin duplicarlas.

## Prueba manual y evidencia

Desde el editor se puede seleccionar Execute workflow. Alternativa CLI:

```powershell
docker exec -u node -e N8N_RUNNERS_BROKER_PORT=5680 scala-n8n n8n execute --id=ScalaMlDiario2000 --rawOutput > data/n8n-ejecucion.log
```

El puerto 5680 evita colision con el broker 5679 del editor. El flujo solo utiliza
nodos HTTP: no requiere Python dentro del contenedor ni nodos Code.
La imagen puede avisar que no tiene Python para su runner opcional; no afecta
estas llamadas HTTP.

La prueba real finalizo success en `Guardar alertas en Laravel`:
12 inscripciones recibidas, 7 alertas actualizadas, 5 omitidas (6,8,9,10,11).
Alerta IDs preservados: 1,2,3,4,5,7,12.

Verificacion PostgreSQL de solo lectura:

```powershell
php laravel-integration/verificar_alertas.php N8N_AUTO
```

Se comprobaron las siete: origen N8N_AUTO, modelo demo-sintetica-v2,
scores iguales a FastAPI, experimental=true, entrenado_con=SINTETICO, sin duplicados.

`data/n8n-ejecucion.log` contiene el detalle tecnico, incluida la respuesta de
Laravel que puede llevar datos personales: esta excluido de Git y no debe publicarse.
`data/verificacion_n8n.json` contiene la comprobacion sin datos personales.
`data/n8n-publicado.json` contiene la exportacion de la version publicada.
No se guardan los cuerpos de ejecuciones normales en n8n para evitar retener
copias adicionales de los datos academicos. Las preferencias se pueden cambiar
en compose.yaml y en los ajustes del flujo si se necesita otro historial.

## Contrato de guardado en Laravel

El webhook acepta directamente el sobre de FastAPI:
`{total_registros, predicciones_calculadas, resultados: [...]}`.

- Valida IDs unicos, totales, rangos, estado de prediccion, version y nivel coherente.
- Solo guarda CALCULADA, con elegibilidad actual de la inscripcion comprobada otra vez.
- Omite CANCELADA y seguimiento insuficiente, sin generar scores de reemplazo.
- Un lote vacio es una operacion de cero cambios; no dispara analisis local.
- Conserva los factores_riesgo tal como los devuelve FastAPI (actualmente seis
  aportes Tree SHAP para predicciones calculadas), resumen y metadata experimental.
- Conserva explicacion_modelo y acciones_sugeridas en metricas_base.prediccion_ml.
- Guarda origen N8N_AUTO y metricas_base.prediccion_ml.proveedor=ML_API.
- Usa transaccion y bloqueos de inscripcion para evitar escrituras parciales y duplicados.
- Mantiene el estado de la alerta e intervenciones; conserva la regla de reapertura
  de DESCARTADA cuando sube a ALTO.
- El contrato legado predicciones/alertas se conserva para compatibilidad; este
  flujo utiliza exclusivamente el nuevo contrato resultados.

Archivos Laravel modificados en esta etapa:
`app/Services/RiesgoPredictivoService.php`,
`app/Http/Controllers/RiesgoAcademicoController.php`,
`tests/Feature/N8nBatchWebhookTest.php`,
`tests/Feature/RiesgoPredictivoTest.php`.
Las pruebas anteriores del motor local ahora deshabilitan ML explicitamente
en su setUp para probar las heuristicas y no depender del servicio vivo.

Comprobacion final: 10 pruebas, 98 assertions, todas aprobadas:

```powershell
php artisan test tests/Feature/N8nBatchWebhookTest.php tests/Feature/FastApiIntegrationTest.php tests/Feature/RiesgoPredictivoTest.php
```

Los archivos `laravel/` son copias de preparacion; los cambios ya se aplicaron
al backend. No reejecutar los aplicadores sin revisar el manifest y los cambios
concurrentes: verifican hashes anteriores y no son instaladores generales.

## Fuentes utilizadas

- [Instalacion oficial de n8n con Docker](https://docs.n8n.io/deploy/host-n8n/install-options/install-with-docker.md).
- [CLI: importacion y publicacion de workflows](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line.md).
- [Schedule Trigger y zona horaria](https://docs.n8n.io/integrations/builtin/core-nodes/n8n-nodes-base.scheduletrigger).
