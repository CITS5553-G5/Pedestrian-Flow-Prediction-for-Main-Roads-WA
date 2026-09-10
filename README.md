# Pedestrian Flow Prediction for Main Roads WA

This private repository is the CITS5553 Group 5 day-to-day development workspace for pedestrian-flow prediction on major roads in Western Australia.

## Project stages

1. `01_data_preparation` — prepare, reconcile and link the survey, AusRAP and road-network data.
2. `02_feature_extraction` — obtain approved external sources and extract additional spatial or imagery features. Shared source-specific notebooks are kept in `02_feature_extraction/context/`.
3. `03_model_development` — train, compare and select models.
4. `04_prediction_pipeline` — integrate validated preparation, feature and model code into one reproducible prediction workflow.
5. `05_application` — provide the backend and frontend used to run the agreed prediction workflow and present its results.
6. `06_outputs` — store reviewed outputs that teammates may use without rerunning every upstream notebook.

Use `03_model_development/` for explanatory model-development notebooks,
`05_application/backend/` for a future API and `05_application/frontend/` for the
user interface. Reusable preparation, feature and prediction code belongs under
`src/pedflow/`. A selected notebook model should be exported with its fitted
preprocessing so prediction code can load it without repeating training logic.

`docs/01_data_preparation/` contains table-format and verified-correction notes. `docs/02_feature_extraction/` contains a short summary of the features produced by the shared Stage 2 notebooks. Detailed personal working notes are excluded from Git. `data/` contains only authorised, intentionally shared inputs and approved project tables.

Reviewed feature tables and other small results that the team needs directly belong under `06_outputs/`. Update a shared output in the same commit as the notebook or script that generated it. Temporary runs, exploratory results, fitted models, large generated files and outputs restricted by source terms must remain outside Git.

## File naming

Formal reusable Python workflow code belongs under `src/pedflow/`. Use descriptive
lowercase module names that state one responsibility, such as `workflow.py`,
`validation.py` and `sources/pta_stops.py`. Executable package entry points use
Python's standard `__main__.py` mechanism and are registered as readable project
commands in `pyproject.toml`.

Stage 2 source-specific notebooks normally use this format:

```text
<stage>_<sequence>_<member>_<topic>.ipynb
```

For example:

```text
02_01_haoqi_abs_mesh_block_sa1.ipynb
02_03_haoqi_pta_stops.ipynb
```

Use lowercase letters, two-digit numbers and underscores. Do not use spaces. In Stage 2, the sequence identifies a data-source work item; it does not imply execution order. Other stages should add a sequence only when it helps distinguish parallel files. Agree on a number before adding another shared notebook in the same stage.

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

The single `requirements.txt` contains the shared analysis, notebook and code-quality packages so every member uses the same straightforward installation command. Application and database packages should be added only after the team selects that technical path.

## Optional container environment

The `.devcontainer/` configuration is an optional OrbStack or Docker Desktop environment. Team members do not need it for ordinary notebook or Python work. It mounts the repository at `/workspace` inside the container, but project code must remain runnable outside the container.

See `.devcontainer/CONTAINER_GUIDE.md` for the optional Python and frontend development environment.

## Runtime API configuration

Copy `.env.example` to `.env` and add only the credentials needed by the active experiment. `.env` files are excluded from Git.

The current imagery prototype uses Mapillary and tests Google Gemini. Google Places Aggregate POI features are excluded from the modelling workflow by the recorded UWA project decision, so no Google Maps Platform key is required. The replacement Overture Places workflow uses the public Overture dataset through the official Python client and also requires no API key:

```dotenv
VISION_PROVIDER=gemini
VISION_MODEL=auto
MAPILLARY_ACCESS_TOKEN=replace_with_local_token
GEMINI_API_KEY=replace_with_local_key
```

The shared imagery notebook is still a prototype. Additional personal imagery API experiments remain excluded from Git until the team selects an integration approach. Alternative providers are candidates, not confirmed client requirements, and must not be described as adopted until the team validates them.

## Data rule

This private repository may contain only data that the client or source licence permits the approved project collaborators to share. A file being public or small enough for Git does not by itself authorise redistribution.

Tracked files under `data/raw/` are immutable inputs: analysis code may read them but must not overwrite them. API keys, `.env` files, downloaded imagery, disposable caches, fitted models and unreviewed generated reports must remain outside Git. Reviewed feature tables under `06_outputs/` are the exception because they let teammates use the agreed results directly. Before adding or replacing source data, record the provider, source URL, snapshot date, licence and the notebook or script that uses it. See `data/README.md` for the folder contract.

## Git workflow

`main` is the shared stable branch. Normal Stage 2 work should use one personal stage branch per member, such as `haoqi/02-extract-features`, followed by a Pull Request into `main`. A branch becomes visible to the team only after it is pushed to GitHub. Team members can review its Pull Request without downloading that branch. Do not force-push or delete `main`.

Before committing, check that notebook outputs contain no credentials or personal absolute paths, and stage files deliberately rather than using an unchecked `git add .`. See `GIT_WORKFLOW.md` for direct team instructions and repository rules. The local Chinese guide is intentionally excluded from Git.
