# Pedestrian Flow Prediction for Main Roads WA

This private repository is the CITS5553 Group 5 workspace for pedestrian-flow prediction on major roads in Western Australia.

## Repository structure

The repository has two complementary parts: numbered project workspaces for
team-facing analysis and communication, and shared infrastructure for the formal,
reusable workflow.

### Numbered project workspaces

1. `01_data_preparation` — prepare, reconcile and link the survey, AusRAP and road-network data.
2. `02_feature_extraction` — obtain approved external sources and develop spatial or imagery features. Shared source-specific notebooks are kept in `02_feature_extraction/context/`.
3. `03_model_development` — explain, train, compare and select models.
4. `04_prediction_pipeline` — document and demonstrate the integration of validated preparation, feature and model code into one reproducible prediction workflow.
5. `05_application` — contain the frontend prototype and the reserved area for a future backend.
6. `06_outputs` — store reviewed outputs that teammates may use without rerunning every upstream notebook.

### Shared workflow infrastructure

- `configs/` — versioned settings for reproducible workflow runs.
- `data/` — authorised source data, approved processed datasets and input/output templates.
- `docs/` — shared schemas, technical decisions and documentation aligned with the project stages.
- `src/pedflow/` — authoritative reusable preparation, feature extraction, training and prediction code.
- `tests/` — automated tests for the reusable code under `src/pedflow/`.

Stable calculations belong in `src/pedflow/`; notebooks, batch interfaces and any
future backend should call that implementation rather than duplicate it.

## Native setup for Windows and macOS

Python 3.11 is the supported team version. Clone the repository to any local folder; code must not depend on the host folder name or an absolute path.

The following setup is required once after cloning.

On Windows PowerShell:
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

The single `requirements.txt` contains the shared analysis, notebook and code-quality packages so every member uses the same straightforward installation command. Application and database packages should be added only after the team selects that technical path.

## Runtime configuration

The repository uses one local environment file for runtime API configuration. Copy `.env.example` to `.env`, add only the credentials required by the active experiment, and keep the file local. Python code and notebooks that need these settings load the root `.env` explicitly with `python-dotenv`. Changing a provider, model or API key does not require rebuilding the development container.

## Optional container environment

The `.devcontainer/` configuration is an optional OrbStack or Docker Desktop environment. It provides the shared Python, Node.js and R Markdown toolchains, including Pandoc and LaTeX for HTML and PDF rendering. Team members do not need it for ordinary notebook or Python work. It mounts the repository at `/workspace` inside the container, but project code must remain runnable outside the container.

See `.devcontainer/CONTAINER_GUIDE.md` for the optional Python and frontend development environment.
