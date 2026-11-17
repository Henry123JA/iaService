"""Aplica solamente los archivos del manifest con verificacion de hashes."""
import hashlib
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
backend = stage.parents[2] / 'sw-scala'
manifest = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
for item in manifest:
    dest = backend / item['destino']
    actual = hashlib.sha256(dest.read_bytes()).hexdigest() if dest.exists() else None
    if actual != item['sha256_original']:
        raise RuntimeError(f"Cambio concurrente: {item['destino']}")
for item in manifest:
    dest = backend / item['destino']
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes((stage / item['fuente']).read_bytes())
print('Webhook batch y pruebas aplicados; no se modifico .env.')
