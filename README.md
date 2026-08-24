# Pedestrian Flow Prediction for Main Roads WA

This private repository is the CITS5553 Group 5 day-to-day development workspace for pedestrian-flow prediction on major roads in Western Australia.

## Project stages

1. `01_data_preparation` — prepare, reconcile and link the survey, AusRAP and road-network data.
2. `02_feature_extraction` — obtain approved external sources and extract additional spatial or imagery features.
3. `03_model_development` — train, compare and select models.
4. `04_prediction_pipeline` — integrate validated preparation, feature and model code into one reproducible prediction workflow.
5. `05_application` — provide the backend and frontend used to run the agreed prediction workflow and present its results.

Use `05_application/backend/` for the API and application-side validation, and `05_application/frontend/` for the user interface. Keep prediction logic in `04_prediction_pipeline/`; the backend should call it rather than duplicate it. The application technology has not yet been selected.

`docs/01_data_preparation/` contains table-format and verified-correction notes. `docs/02_feature_extraction/` contains a short summary of the features produced by the shared Stage 2 notebooks. Detailed personal working notes are excluded from Git. `data/` contains only authorised, intentionally shared inputs and approved project tables. Generated artefacts belong under `outputs/`, which is excluded from Git.

## File naming

Shared integration files use the stage number and purpose without a member name, for example `02_feature_extraction.py`.

Personal notebooks use this format:

```text
<stage>_<sequence>_<member>_<topic>.ipynb
```

For example:

```text
02_01_haoqi_abs_mesh_block_sa1.ipynb
02_03_haoqi_pta_stops.ipynb
```

Use lowercase letters, two-digit numbers and underscores. Do not use spaces. The sequence number must be unique within the stage and agreed before a new parallel notebook is added.

## Native setup for Windows and macOS

Python 3.11 is the supported team version. Clone the repository to any local folder; code must not depend on the host folder name or an absolute path.

The following setup is required once after cloning. On Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

On macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Open the repository root in VS Code and select the `.venv` Python interpreter. The repository path may differ between members. Python code and notebooks should build paths from the discovered repository root with `pathlib.Path`.

The `.venv` folder remains on the computer. Do not recreate it or reinstall all packages every time. In a new terminal, activate it only when the prompt does not already show `(.venv)`: use `.venv\Scripts\Activate.ps1` on Windows or `source .venv/bin/activate` on macOS. VS Code may activate the selected interpreter automatically.

The single `requirements.txt` contains the shared analysis, notebook, code-quality and optional database packages so every member uses the same straightforward installation command.

## Optional container environment

The `.devcontainer/` configuration is an optional OrbStack or Docker Desktop environment. Team members do not need it for ordinary notebook or Python work. It mounts the repository at `/workspace` inside the container, but project code must remain runnable outside the container.

See `.devcontainer/CONTAINER_GUIDE.md` for the optional PostgreSQL, PostGIS and pgAdmin environment.

## Runtime API configuration

Copy `.env.example` to `.env` and add only the credentials needed by the active experiment. `.env` files are excluded from Git.

The current imagery prototype uses Mapillary and tests Google Gemini:

```dotenv
VISION_PROVIDER=gemini
VISION_MODEL=auto
MAPILLARY_ACCESS_TOKEN=replace_with_local_token
GEMINI_API_KEY=replace_with_local_key
```

Local imagery API experiments are intentionally excluded from Git until the team selects an approach for integration. Alternative providers are candidates, not confirmed client requirements, and must not be described as adopted until the team validates them.

## Data rule

This private repository may contain only data that the client or source licence permits the approved project collaborators to share. A file being public or small enough for Git does not by itself authorise redistribution.

Tracked files under `data/raw/` are immutable inputs: analysis code may read them but must not overwrite them. API keys, `.env` files, downloaded imagery, disposable caches, fitted models and generated reports must remain outside Git. Before adding or replacing source data, record the provider, source URL, snapshot date, licence and the notebook or script that uses it. See `data/README.md` for the folder contract.

## Git workflow

`main` is the shared stable branch. Normal Stage 2 work should use one personal stage branch per member, such as `haoqi/02-extract-features`, followed by a Pull Request into `main`. A branch becomes visible to the team only after it is pushed to GitHub. Team members can review its Pull Request without downloading that branch. Do not force-push or delete `main`.

Before committing, check that notebook outputs contain no credentials or personal absolute paths, and stage files deliberately rather than using an unchecked `git add .`. See `GIT_WORKFLOW.md` for direct team instructions and `CONTRIBUTING.md` for repository rules. The local Chinese guide is intentionally excluded from Git.
