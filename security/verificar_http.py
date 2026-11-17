"""Comprueba rechazo HTTP real sin usar ni revelar el token del servicio."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen

for path in ('dataset-alumnos', 'webhook-alertas'):
    for token in (None, 'credencial-invalida-de-prueba'):
        headers = {'Accept': 'application/json', 'Content-Type': 'application/json'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        request = Request('http://127.0.0.1:8000/api/ml/' + path,
                          data=b'{}' if path == 'webhook-alertas' else None,
                          headers=headers)
        try:
            with urlopen(request, timeout=10) as response:
                raise AssertionError('Acceso sin credencial valida permitido')
        except HTTPError as error:
            assert error.code == 401, f'HTTP inesperado {error.code}'
            body = json.load(error)
            assert 'dataset' not in body and 'alerta_ids' not in body
            print(f'{path}: token {"invalido" if token else "ausente"} -> 401, sin datos')
