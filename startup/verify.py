"""Comprueba servicios y tareas en marcha sin credenciales de integracion."""
import json
from pathlib import Path
import time
from urllib.request import urlopen

urls = {'laravel': 'http://127.0.0.1:8000/up',
        'fastapi': 'http://127.0.0.1:8001/health',
        'n8n': 'http://127.0.0.1:5678/healthz'}
states = {}
for attempt in range(12):
    for name, url in urls.items():
        try:
            with urlopen(url, timeout=3) as response:
                states[name] = response.status == 200
        except OSError:
            states[name] = False
    if all(states.values()):
        break
    time.sleep(4)
root = Path(__file__).resolve().parent.parent
(root / 'data' / 'startup' / 'verified.json').write_text(json.dumps(states, indent=2), encoding='utf-8')
print(json.dumps(states))
raise SystemExit(0 if all(states.values()) else 1)
