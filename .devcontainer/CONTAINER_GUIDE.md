# Pedestrian Exposure WA - Optional Container Guide

This environment is optional. The shared code and notebooks must also run in a Python 3.11 virtual environment on Windows or macOS as documented in the repository `README.md`.

## Current environment

The development environment starts one service named `app`, using the `pedestrian-exposure-wa-app` container. It provides Python 3.11 and Node.js 22 development and mounts the repository at `/workspace`.

The frontend dependency directory is mounted as the Docker named volume `pedestrian-exposure-wa-frontend-node-modules`. Packages installed at `/workspace/05_application/frontend/node_modules` therefore remain inside Docker storage rather than being written into the host project directory.

## Prerequisites

- OrbStack or Docker Desktop
- Visual Studio Code
- The Microsoft Dev Containers extension for Visual Studio Code

## Open the project in the container

1. Start OrbStack or Docker Desktop.
2. Open the cloned repository root in Visual Studio Code.
3. Open the Command Palette with `Cmd+Shift+P` on macOS or `Ctrl+Shift+P` on Windows/Linux.
4. Select `Dev Containers: Reopen in Container`.
5. Wait while the container starts and the Python packages in `requirements.txt` are installed.

Visual Studio Code should reopen in the `app` service with `/workspace` as the project directory.

## Runtime environment

The project uses one local environment file at the repository root. Copy `.env.example` to `.env` and add only the credentials required by the active experiment. The same file is available inside the container as `/workspace/.env`; Python code and notebooks that require runtime configuration load it explicitly with `python-dotenv`.

The development container does not require a separate `.devcontainer/.env` file. Changing a runtime API key or provider setting does not require rebuilding the container; restart the Python command or notebook kernel instead.

## Verify Python

Run the following commands inside the container:

```bash
python --version
python -c "import pandas, geopandas, sklearn, statsmodels, xgboost; print('Python environment: OK')"
```

The Python version should be 3.11 and the import test should print `Python environment: OK`.

## Install and run the frontend

Run these commands inside the container:

```bash
cd /workspace/05_application/frontend
npm ci
npm run dev -- --host 0.0.0.0
```

Open `http://localhost:5173` on the host after VS Code reports that port 5173 has been forwarded.

The first `npm ci` populates the Docker volume. Later container rebuilds reuse that volume unless it is explicitly removed. If `package-lock.json` changes, run `npm ci` again.

The container creation process assigns this volume to the `vscode` user before installing packages. If an older container was created before that setup was added, repair it once with `sudo chown -R vscode:vscode /workspace/05_application/frontend/node_modules`.

## Project data

Place authorised source data in the repository-relative directory `data/raw/`. Inside the container, the same directory is `/workspace/data/raw/`. Use project-relative paths in code whenever possible.

## Start, stop and rebuild

The recommended method is `Dev Containers: Reopen in Container`. The environment can also be managed from `.devcontainer`:

```bash
docker compose -f compose.yaml up -d
docker compose -f compose.yaml ps
docker compose -f compose.yaml stop
docker compose -f compose.yaml down
```

Use `Dev Containers: Rebuild Container` after changing `compose.yaml`, `devcontainer.json` or the base image. A normal rebuild recreates the app container but retains repository files and the named frontend dependency volume.

To inspect the app service logs, run:

```bash
docker compose -f compose.yaml logs app
```

## Persistence and removal

Stopping, rebuilding or running `docker compose down` does not normally remove named volumes. Do not add `--volumes` unless the stored frontend dependencies can be discarded.

Removing `pedestrian-exposure-wa-frontend-node-modules` only deletes installed frontend packages; they can be restored with `npm ci`.
