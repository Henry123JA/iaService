"""Aplica cambios y genera credencial privada sin imprimirla."""
import hashlib
import json
import secrets
from pathlib import Path

stage = Path(__file__).resolve().parent
root = stage.parent
backend = root.parent / 'sw-scala'
items = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
for item in items:
    path = backend / item['destino']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if actual != item['sha256_original']:
        raise RuntimeError(f"Cambio concurrente: {item['destino']}")
env_path = backend / '.env'
lines = env_path.read_text(encoding='utf-8').splitlines()
existing = next((x.split('=', 1)[1].strip().strip('\"\'') for x in lines
                 if x.startswith('ML_INTEGRATION_TOKEN=')), '')
token = existing or secrets.token_hex(32)
for item in items:
    path = backend / item['destino']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((stage / item['fuente']).read_bytes())
lines = [x for x in lines if not x.startswith('ML_INTEGRATION_TOKEN=')]
lines.append('ML_INTEGRATION_TOKEN=' + token)
env_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
# Credencial importable por n8n, excluida de Git mediante data/.
credentials = [{
    'id': 'ScalaLaravelMl01', 'name': 'Scala Laravel ML - servicio',
    'type': 'httpHeaderAuth', 'data': {'name': 'Authorization', 'value': 'Bearer ' + token},
}]
(root / 'data' / 'n8n-ml-credential.json').write_text(json.dumps(credentials), encoding='utf-8')
print('Autenticacion aplicada y credencial privada preparada. Token no mostrado.')
