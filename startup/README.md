# Inicio manual de los servicios en Windows

Las tareas que iniciaban Laravel, FastAPI y n8n al iniciar sesion fueron
eliminadas, y n8n ya no se reinicia solo. PostgreSQL sigue configurado para
iniciar con Windows hasta ejecutar el script como administrador.

Para configurar o quitar una configuracion anterior de arranque automatico:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File startup/install.ps1
```

Ejecuta ese comando como administrador para cambiar tambien PostgreSQL a inicio
manual. El script elimina las tareas `Scala-Servicios` y
`Scala-Preparar-Seguimiento` si todavia existen; no detiene los servidores que ya
estan funcionando.

Para iniciar manualmente el supervisor y los servicios que falten:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File startup/start-manual.ps1
```

El supervisor queda ejecutandose en segundo plano y revisa los servicios cada
30 segundos. PostgreSQL se inicia bajo demanda si hace falta. Para evitar que
vuelva a iniciarse automaticamente, no ejecutes el antiguo programador de tareas.
El flujo de n8n a las 20:00 solo puede ejecutarse mientras n8n y sus dependencias
esten iniciados manualmente.

Estado y registros:

- `data/startup/supervisor.log`: eventos y fallos; rotacion de 1 MB.
- `data/startup/laravel.log`, `fastapi.log` y `n8n-start.log`: salida de procesos.
- `data/startup/status.json`: ultima muestra de salud.
- `startup/config.json`: rutas locales sin secretos, excluido de Git.

El supervisor no mata procesos desconocidos si detecta un puerto ocupado.
Laravel, FastAPI y n8n se mantienen ligados a `127.0.0.1`.
