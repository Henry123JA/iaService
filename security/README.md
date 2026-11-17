# Autenticacion de la integracion ML

Aplicado y probado el 10 de noviembre de 2026.

Ambos endpoints globales /api/ml/dataset-alumnos y /api/ml/webhook-alertas
exigen `Authorization: Bearer <credencial-de-servicio>`. La clave se genera con
32 bytes aleatorios y se conserva en sw-scala/.env como ML_INTEGRATION_TOKEN;
Laravel la lee mediante config/services.php, services.ml.integration_token.
No esta incluida en este documento, en el flujo exportado ni en el chat.

Middleware App\Http\Middleware\RequireMlServiceToken aplicado directamente a
ambas rutas. Sin credencial o con credencial incorrecta: HTTP401, sin datos.
Si la clave no esta configurada: HTTP503 (falla cerrado). Se compara con hash_equals.
Sesion docente, parametro grupo_id, token en query o login de navegador no
sustituyen la credencial de servicio. Los docentes usan las rutas /riesgo, con
el aislamiento por grupos ya probado. La clave global es exclusiva del servicio,
no se entrega a docentes ni se incluye en componentes Vue.

n8n actualizado y publicado: los nodos Consultar Laravel y Guardar alertas en
Laravel usan httpHeaderAuth, credencial ID ScalaLaravelMl01, nombre
Scala Laravel ML - servicio. El valor esta en el almacen cifrado de n8n;
el workflow JSON solo contiene la referencia a la credencial. El nodo FastAPI
no recibe este token, porque solo se necesita para Laravel.
Se conservaron el flujo existente, sus ajustes y cron diario20h America/La_Paz.

La copia temporal de importacion de credencial en data/ y /tmp del contenedor
se elimino tras la importacion. No exportar credenciales descifradas.
El token persistente vive en .env del backend y en el volumen cifrado de n8n.
Para rotacion, actualizar ambos coordinadamente; no regenerar solo uno.

Verificado:
- 24 pruebas Laravel, 180 assertions: PASAN, incluyendo 5 casos nuevos de
  autenticacion, 8 casos de alcance docente y compatibilidad de n8n/SHAP.
- HTTP real: GET y POST sin token o con token invalido devuelven401 sin datos.
- Flujo real n8n autenticado: success, 7 alertas guardadas y 5 omitidas.
- Lectura PostgreSQL de comprobacion: siete alertas correctas con origen N8N_AUTO,
  version demo-sintetica-v2, seis factores SHAP y resumen/acciones.

Los clientes Python que consultan Laravel requieren LARAVEL_API_TOKEN en el entorno.
predecir_laravel.py ya soportaba ese header; presentation/actualizar_alerta7.py
tambien lo admite ahora. No pasar el token en URL ni imprimirlo en comandos/logs.
El verificador PHP de PostgreSQL no necesita token HTTP porque consulta localmente
mediante la configuracion protegida del backend en una transaccion de solo lectura.

Evidencia local excluida de Git: data/n8n-antes-auth.json (respaldo de flujo),
data/n8n-ejecucion-auth.log (puede incluir datos personales),
data/verificacion_auth.json. El script security/verificar_http.py reproduce
las pruebas de rechazo sin leer el token verdadero.
Los archivos security/ se aplicaron al backend; no reejecutar aplicar.py con
manifest viejo. No hubo migraciones ni cambios de roles/contraseñas.

Fuentes de configuracion:
[Header/Bearer auth de n8n](https://docs.n8n.io/integrations/builtin/credentials/httprequest),
[CLI de n8n](https://docs.n8n.io/deploy/host-n8n/configure-n8n/use-the-command-line.md).
