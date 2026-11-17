"""Aplica archivos revisados en la carpeta hermana sw-scala, con control de cambios."""
import hashlib
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
backend = stage.parent.parent / 'sw-scala'
manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    target = backend / item['destino']
    actual = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    if actual != item['sha256_original']:
        raise RuntimeError(f"Cambio concurrente en {item['destino']}; no se aplico nada")
for item in manifest:
    target = backend / item['destino']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes((stage / item['fuente']).read_bytes())
env_path = backend / '.env'
lines = env_path.read_text(encoding='utf-8').splitlines()
values = {'ML_SERVICE_ENABLED': 'true', 'ML_SERVICE_URL': 'http://127.0.0.1:8001',
          'ML_SERVICE_TIMEOUT': '10'}
lines = [line for line in lines if line.split('=', 1)[0] not in values]
lines.extend(f'{key}={value}' for key, value in values.items())
env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print('Integracion aplicada; ML habilitado en .env sin exponer otras variables.')
