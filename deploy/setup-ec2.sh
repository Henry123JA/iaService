#!/usr/bin/env bash
set -euo pipefail

# Script de preparacion en Ubuntu EC2 para iaService (modo nativo systemd)
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$APP_DIR"

echo "==> 1. Verificando Python 3 y venv..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-venv python3-pip libgomp1

echo "==> 2. Creando entorno virtual .venv e instalando dependencias..."
python3 -m venv .venv
./.venv/bin/pip install --upgrade pip
./.venv/bin/pip install -r requirements.txt

echo "==> 3. Verificando artefacto del modelo (demo-sintetica-v2)..."
if [ ! -f "models/modelos_demo.joblib" ]; then
    echo "Modelo no encontrado en models/. Generando con semilla determinista 42..."
    ./.venv/bin/python training/generar_dataset.py --cantidad 5000 --semilla 42
    ./.venv/bin/python training/train_model.py
else
    echo "Modelo encontrado: models/modelos_demo.joblib"
fi

echo "==> 4. Ejecutando pruebas de verificacion..."
if [ -f "requirements-dev.txt" ]; then
    ./.venv/bin/pip install -r requirements-dev.txt
    ./.venv/bin/python -m unittest discover -s tests -v
fi

echo "==> Listo. Para registrar el servicio en systemd ejecuta:"
echo "    sudo cp deploy/iaservice.service /etc/systemd/system/iaservice.service"
echo "    sudo systemctl daemon-reload"
echo "    sudo systemctl enable --now iaservice"

