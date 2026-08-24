# Pedestrian Exposure WA - Optional Container Guide

This environment is optional. The shared code and notebooks must also run in a Python 3.11 virtual environment on Windows or macOS as documented in the repository `README.md`.

## 1. Environment Overview

The development environment is managed as one Docker Compose project named `pedestrian-exposure-wa`.

It contains three services:

| Service | Container | Purpose |
| --- | --- | --- |
| `app` | `pedestrian-exposure-wa-app` | Python 3.11 development, spatial analysis, statistical modelling and machine learning |
| `postgres` | `pedestrian-exposure-wa-postgres` | PostgreSQL 17 database with PostGIS |
| `pgadmin` | `pedestrian-exposure-wa-pgadmin` | Browser-based PostgreSQL and PostGIS administration |

The project directory is mounted into the Python container at `/workspace`. Client data remains in the local `data/raw/` directory and is not copied into a Docker image.

## 2. Prerequisites

Install the following software before opening the environment:

- OrbStack or Docker Desktop
- Visual Studio Code
- The Microsoft Dev Containers extension for Visual Studio Code

## 3. Local Environment File

Copy `.devcontainer/.env.example` to `.devcontainer/.env` before the containers are created. The resulting file is local and excluded from Git. It has the following structure:

```dotenv
POSTGRES_DB=pedestrian_exposure_wa
POSTGRES_USER=pedestrian_exposure_user
POSTGRES_PASSWORD=<local-database-password>

PGADMIN_EMAIL=<local-pgadmin-email>
PGADMIN_PASSWORD=<local-pgadmin-password>

JUPYTER_TOKEN=<local-jupyter-token>
```

Replace every placeholder with the locally supplied value. Do not place passwords directly in `compose.yaml`, Python scripts or notebooks.

## 4. Open the Project in the Development Container

1. Start OrbStack or Docker Desktop.
2. Open the cloned repository root in Visual Studio Code.
3. Open the Command Palette with `Cmd+Shift+P` on macOS or `Ctrl+Shift+P` on Windows/Linux.
4. Select `Dev Containers: Reopen in Container`.
5. Wait while Docker builds the PostGIS image, downloads the remaining images and installs the Python packages in `requirements.txt`.

Visual Studio Code should reopen in the `app` service with `/workspace` as the project directory. The first build takes longer than later starts because images and Python packages must be downloaded.

## 5. Verify the Python Environment

Open a Visual Studio Code terminal after the container starts and run:

```bash
python --version
python -c "import pandas, geopandas, sklearn, statsmodels, xgboost; print('Python environment: OK')"
```

The Python version should be 3.11 and the import test should print:

```text
Python environment: OK
```

## 6. Verify PostgreSQL and PostGIS

From the terminal inside the `app` container, run:

```bash
python -c "import os, psycopg; conn = psycopg.connect(host=os.environ['POSTGRES_HOST'], port=os.environ['POSTGRES_PORT'], dbname=os.environ['POSTGRES_DB'], user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD']); cur = conn.cursor(); cur.execute('SELECT PostGIS_Version();'); print(cur.fetchone()[0]); conn.close()"
```

A PostGIS version number confirms that:

- the Python container can reach PostgreSQL;
- the database credentials are correct; and
- the PostGIS extension is enabled.

Within the Compose network, use the following database connection settings:

```text
Host: postgres
Port: 5432
Database: pedestrian_exposure_wa
User: pedestrian_exposure_user
Password: value of POSTGRES_PASSWORD in .devcontainer/.env
```

Use `postgres`, not `localhost`, when connecting from the `app` or `pgadmin` container.

## 7. Open and Configure pgAdmin

Open the following address in a browser:

```text
http://localhost:5050
```

Sign in using `PGADMIN_EMAIL` and `PGADMIN_PASSWORD` from `.devcontainer/.env`.

To register the project database for the first time:

1. Select `Add New Server`.
2. On the **General** tab, enter `Pedestrian Exposure WA` as the server name.
3. On the **Connection** tab, enter:

```text
Host name/address: postgres
Port: 5432
Maintenance database: pedestrian_exposure_wa
Username: pedestrian_exposure_user
Password: value of POSTGRES_PASSWORD
```

4. Enable `Save password` for the local development environment if appropriate.
5. Select `Save`.

## 8. Project Data Location

Place authorised source data in the repository-relative directory:

```text
data/raw/
```

Inside the Python container, the same directory is available at:

```text
/workspace/data/raw/
```

Use project-relative paths in Python whenever possible:

```python
from pathlib import Path

RAW_DATA_DIR = Path("data/raw")
```

Do not build client data into container images or store it in the PostgreSQL image layer. Database records are persisted separately in the Docker volume `pedestrian-exposure-wa-postgres-data`.

## 9. Start and Stop the Environment

The recommended method is to use `Dev Containers: Reopen in Container` in Visual Studio Code.

The environment can also be managed from the `.devcontainer` directory:

```bash
docker compose --env-file .env -f compose.yaml up -d
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env -f compose.yaml stop
docker compose --env-file .env -f compose.yaml down
```

`stop` stops the containers without removing them. `down` removes the containers and network but preserves the named PostgreSQL and pgAdmin volumes.

## 10. Rebuild After Configuration Changes

Rebuild the development environment after changing any of the following files:

- `.devcontainer/compose.yaml`
- `.devcontainer/devcontainer.json`
- `.devcontainer/postgres/Dockerfile`
- `requirements.txt`

In Visual Studio Code, run:

```text
Dev Containers: Rebuild Container
```

Changing `.devcontainer/postgres/init-postgis.sql` does not rerun it against an existing database volume. The script is executed only when PostgreSQL creates a new database volume for the first time.

## 11. Check Container Status and Logs

From `.devcontainer`, use:

```bash
docker compose --env-file .env -f compose.yaml ps
docker compose --env-file .env -f compose.yaml logs postgres
docker compose --env-file .env -f compose.yaml logs pgadmin
docker compose --env-file .env -f compose.yaml logs app
```

The PostgreSQL service should report `healthy` before the Python and pgAdmin services are considered ready.

## 12. Database Reset

Removing the PostgreSQL volume permanently deletes the local container database. It does not delete files in `data/raw/`, but any tables imported into PostgreSQL will need to be recreated.

Only perform a reset when the local database can be safely discarded:

```bash
docker compose --env-file .env -f compose.yaml down
docker volume rm pedestrian-exposure-wa-postgres-data
docker compose --env-file .env -f compose.yaml up -d
```

After a new volume is created, `init-postgis.sql` runs again and enables PostGIS in the new database.

## 13. Current Scope

This environment currently supports:

- Python 3.11 development;
- tabular and Excel data processing;
- geospatial analysis;
- PostgreSQL and PostGIS;
- traditional statistical modelling;
- machine learning;
- Jupyter development; and
- automated tests and Python code-quality checks.

Deep-learning libraries are intentionally not included in the current environment. They can be added later if the imagery-feature methodology requires them.
