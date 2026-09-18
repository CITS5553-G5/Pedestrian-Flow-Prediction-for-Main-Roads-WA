#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."

sudo mkdir -p /opt/pedflow-venv
sudo chown "$(id -u):$(id -g)" /opt/pedflow-venv
sudo chown -R "$(id -u):$(id -g)" 05_application/frontend/node_modules

/usr/local/python/current/bin/python -m venv /opt/pedflow-venv
/opt/pedflow-venv/bin/python -m pip install -r requirements.txt
/opt/pedflow-venv/bin/python -m pip install --no-deps -e .
/opt/pedflow-venv/bin/python -m pip check

sudo Rscript --vanilla .devcontainer/restore-r.R
