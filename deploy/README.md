# Guía de Despliegue en AWS EC2 (Ubuntu)

Este proyecto incluye todo lo necesario para ejecutarse en la misma instancia **EC2** junto a `sw-scala` (Laravel), escuchando de forma segura en loopback local (`127.0.0.1:8001`).

> [!IMPORTANT]
> **Detalle clave en Linux para Docker (`host.docker.internal`):**
> En Windows Docker Desktop resuelve `host.docker.internal` automáticamente, pero en Linux (Ubuntu EC2) requiere declarar `extra_hosts: ["host.docker.internal:host-gateway"]`. El archivo [compose.ec2.yaml](../compose.ec2.yaml) ya incluye esta configuración para que `n8n` se conecte sin cambios a Laravel (`:8000`) y FastAPI (`:8001`).

---

## Opción A: Despliegue con Docker Compose (FastAPI + n8n juntos)

Levanta tanto `iaService` como `n8n` con inicio automático (`restart: unless-stopped`):

```bash
cd /var/www/iaService
docker compose -f compose.ec2.yaml up -d --build
```

### Verificar estado:
```bash
curl http://127.0.0.1:8001/health
# Respuesta esperada: {"status":"ok","version_modelo":"demo-sintetica-v2"}
```

### Importar y activar el flujo en n8n (primera vez en el EC2):
```bash
docker exec -u node scala-n8n n8n import:workflow --input=/workflows/scala-seguimiento-diario.json
docker exec -u node scala-n8n n8n update:workflow --id=ScalaMlDiario2000 --active=true
docker restart scala-n8n
```
*(Recuerda crear en el editor de n8n o por CLI la credencial `httpHeaderAuth` con ID `ScalaLaravelMl01` y el header `Authorization: Bearer <ML_INTEGRATION_TOKEN>` que tengas en el `.env` de `sw-scala`).*

---

## Opción B: Despliegue Nativo con `systemd` (Sin Docker para Python)

Si prefieres correr `iaService` directamente en el Ubuntu del EC2 usando su propio `.venv` (consume menos disco y memoria):

1. **Ubicar el proyecto en `/var/www/iaService` y ejecutar el instalador:**
   ```bash
   cd /var/www/iaService
   chmod +x deploy/setup-ec2.sh
   ./deploy/setup-ec2.sh
   ```
   *(Si subiste el proyecto por Git y no copiaste `models/modelos_demo.joblib`, el script lo regenera automáticamente con la semilla exacta `42`, produciendo el mismo modelo `demo-sintetica-v2`).*

2. **Activar el servicio `systemd`:**
   *(Si tu carpeta no está en `/var/www/iaService` o tu usuario no es `ubuntu`, ajusta `User` y `WorkingDirectory` en `deploy/iaservice.service`).*
   ```bash
   sudo cp deploy/iaservice.service /etc/systemd/system/iaservice.service
   sudo systemctl daemon-reload
   sudo systemctl enable --now iaservice
   sudo systemctl status iaservice
   ```

3. **Levantar únicamente `n8n` con Docker (si usas Opción B):**
   ```bash
   docker compose -f compose.ec2.yaml up -d n8n
   ```

---

## Variables en el `.env` de Laravel (`sw-scala`) en EC2

Asegúrate de que en el archivo `.env` de `sw-scala` en el servidor estén definidas:

```env
ML_SERVICE_ENABLED=true
ML_SERVICE_URL=http://127.0.0.1:8001
ML_SERVICE_TIMEOUT=10
ML_INTEGRATION_TOKEN=<tu_token_seguro_de_32_bytes>
```

Y luego limpia la caché de configuración de Laravel:
```bash
php artisan config:clear
```

