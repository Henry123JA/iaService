# Verificacion de permisos docentes de alertas

10 de noviembre de 2026. Se realizaron pruebas HTTP autenticadas mediante
Laravel `actingAs` con el usuario Docente REAL asignado al grupo de la alerta 7.
Se selecciono ademas otra alerta cuyo grupo pertenece a un docente diferente.
No se cambiaron contraseñas, roles, asignaciones ni la sesion del navegador.
No se afirma una inspeccion visual autenticada como docente: esa es una prueba distinta.

## Resultado del modulo /riesgo

- Docente asignado: GET /riesgo/alertas/7 devuelve 200 con seis factores SHAP,
  resumen, score y tres acciones; rol_usuario=Docente.
- La respuesta Inertia carga Riesgo/Show con sus permisos de gestion.
- Una alerta de otro docente devuelve 403 tanto en HTML como en JSON.
- La respuesta JSON denegada no contiene factores ni resumen de la alerta ajena.
- La bandeja, sus grupos y KPIs se restringen al universo del docente autenticado.
- Forzar grupo_id de otro docente no devuelve alertas.
- Intentar modificar el estado de una alerta ajena devuelve 403 sin cambios.
- Registrar o editar intervenciones de otro grupo devuelve 403 sin cambios.
- El docente de otro grupo tampoco puede abrir la alerta 7.

Todas las escrituras de prueba se ejecutan dentro de DatabaseTransactions y se
revierten. La intervencion temporal usada para probar edicion no queda persistida.

## Correccion aplicada

En bootstrap/app.php, la configuracion shouldRenderJsonWhen solo contemplaba
api/*. Por ello, los errores de las rutas web ignoraban Accept: application/json
y devolvian HTML. El bloqueo ya era 403; no se encontro un acceso permitido en
las rutas de detalle probadas. Ahora se usa:

```php
fn (Request $request) => $request->is('api/*') || $request->expectsJson()
```

Esto mantiene HTML para navegacion normal y JSON para peticiones que lo solicitan.
No se deshabilito ni se cambio la regla de autorizacion por docente.

## Pruebas

Nuevo archivo sw-scala/tests/Feature/DocenteAlertasTest.php, 8 casos.
Con las suites existentes: 19 pruebas, 163 assertions, TODAS PASAN.

Desde sw-scala:

```powershell
php artisan test tests/Feature/DocenteAlertasTest.php tests/Feature/XaiPersistenciaTest.php tests/Feature/N8nBatchWebhookTest.php tests/Feature/FastApiIntegrationTest.php tests/Feature/RiesgoPredictivoTest.php
```

## Limite de esta verificacion y hallazgo pendiente

La garantia probada es para las rutas del modulo /riesgo. En routes/web.php,
GET /api/ml/dataset-alumnos y POST /api/ml/webhook-alertas siguen definidos fuera
del grupo auth; el POST excluye CSRF. Son integraciones globales para n8n y
actualmente no exigen token de servicio. Por tanto, NO afirmar aislamiento total
de los datos academicos a traves de todas las interfaces: el dataset global y
el guardado por integracion requieren una tarea adicional de autenticacion.
Esta etapa no cambio ese contrato para evitar interrumpir silenciosamente el
flujo diario de n8n. Si se protege, hay que actualizar coordinadamente Laravel,
las credenciales n8n, clientes locales y sus pruebas.

Las copias/aplicador en permissions/ ya se aplicaron. El manifest corresponde a
la ultima actualizacion del archivo de prueba; no reejecutar con hashes antiguos.
