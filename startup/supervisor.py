"""Supervisor local para Laravel, FastAPI y n8n; ejecutado por Windows Task Scheduler."""
import argparse
from datetime import datetime, timezone
import json
import logging
from logging.handlers import RotatingFileHandler
import msvcrt
from pathlib import Path
import socket
import subprocess
import time
from urllib.error import URLError
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parent.parent
LOGS = ROOT / 'data' / 'startup'
LOGS.mkdir(parents=True, exist_ok=True)
CONFIG = json.loads((ROOT / 'startup' / 'config.json').read_text(encoding='utf-8-sig'))
logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s', handlers=[
    RotatingFileHandler(LOGS / 'supervisor.log', maxBytes=1_000_000, backupCount=3, encoding='utf-8')])
FLAGS = subprocess.CREATE_NO_WINDOW
LAST_TRY = {}
PREVIOUS = {}


def reachable(port):
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            return True
    except OSError:
        return False


def health(url):
    try:
        with urlopen(url, timeout=4) as response:
            return response.status == 200
    except (OSError, URLError):
        return False


def launch(name, command, cwd):
    if time.monotonic() - LAST_TRY.get(name, -1000) < 60:
        return
    LAST_TRY[name] = time.monotonic()
    path = LOGS / f'{name}.log'
    if path.exists() and path.stat().st_size > 5_000_000:
        path.replace(LOGS / f'{name}.previous.log')
    with path.open('ab') as output:
        process = subprocess.Popen(command, cwd=cwd, stdin=subprocess.DEVNULL,
                                   stdout=output, stderr=subprocess.STDOUT,
                                   creationflags=FLAGS, close_fds=True)
    logging.info('Iniciado %s PID=%s', name, process.pid)


def cycle():
    postgres = reachable(CONFIG['postgres_port'])
    if not postgres:
        launch('postgres-start', ['sc.exe', 'start', CONFIG['postgres_service']], str(ROOT))
    definitions = [
        ('laravel', 8000, 'http://127.0.0.1:8000/up',
         [CONFIG['php'], 'artisan', 'serve', '--host=127.0.0.1', '--port=8000', '--no-reload'], CONFIG['laravel']),
        ('fastapi', 8001, 'http://127.0.0.1:8001/health',
         [CONFIG['python'], '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1', '--port', '8001'], str(ROOT)),
    ]
    states = {'postgres': postgres}
    for name, port, url, command, cwd in definitions:
        states[name] = health(url)
        # No mata procesos ajenos ni intenta ocupar un puerto ya utilizado.
        if not states[name] and not reachable(port):
            launch(name, command, cwd)
    states['n8n'] = health('http://127.0.0.1:5678/healthz')
    if not states['n8n']:
        try:
            result = subprocess.run([CONFIG['docker'], 'info', '--format', '{{.ServerVersion}}'],
                                    capture_output=True, timeout=12, creationflags=FLAGS)
            docker_ready = result.returncode == 0
        except (OSError, subprocess.TimeoutExpired):
            docker_ready = False
        if docker_ready:
            launch('n8n-start', [CONFIG['docker'], 'compose', '-f', str(ROOT / 'n8n' / 'compose.yaml'),
                                'up', '-d', '--pull', 'never'], str(ROOT))
        else:
            launch('docker-start', [CONFIG['docker'], 'desktop', 'start', '--detach'], str(ROOT))
    for name, status in states.items():
        if PREVIOUS.get(name) != status:
            logging.info('%s: %s', name, 'disponible' if status else 'pendiente')
            PREVIOUS[name] = status
    report = {'checked_at_utc': datetime.now(timezone.utc).isoformat(),
              'supervisor_pid': __import__('os').getpid(), 'services': states}
    temporary = LOGS / 'status.tmp'
    temporary.write_text(json.dumps(report, indent=2), encoding='utf-8')
    temporary.replace(LOGS / 'status.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--once', action='store_true')
    args = parser.parse_args()
    logging.info('Supervisor iniciado: %s', 'comprobacion unica' if args.once else 'vigilancia continua')
    # Un bloqueo por ciclo evita carreras entre la tarea diaria y el supervisor.
    while True:
        with (LOGS / 'cycle.lock').open('a+b') as lock:
            lock.seek(0, 2)
            if lock.tell() == 0:
                lock.write(b'0')
                lock.flush()
            lock.seek(0)
            try:
                msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError:
                if args.once:
                    return
            else:
                try:
                    cycle()
                except Exception:
                    logging.exception('Fallo de comprobacion; se reintentara')
                finally:
                    lock.seek(0)
                    msvcrt.locking(lock.fileno(), msvcrt.LK_UNLCK, 1)
        if args.once:
            return
        time.sleep(30)


if __name__ == '__main__':
    main()
