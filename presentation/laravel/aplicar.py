"""Aplica el cambio de explicabilidad ya preparado, verificando cambios concurrentes."""
import hashlib
import json
from pathlib import Path

stage = Path(__file__).resolve().parent
backend = stage.parents[2] / 'sw-scala'
items = json.loads((stage / 'manifest.json').read_text(encoding='utf-8'))
for item in items:
    path = backend / item['destino']
    actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None
    if actual != item['sha256_original']:
        raise RuntimeError(f"Cambio concurrente: {item['destino']}")
for item in items:
    path = backend / item['destino']
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((stage / item['fuente']).read_bytes())
print('Explicaciones y pantallas aplicadas sin modificar configuracion ni tablas.')
