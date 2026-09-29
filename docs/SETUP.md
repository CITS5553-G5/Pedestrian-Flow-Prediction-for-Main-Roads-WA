# Setup

Run commands from the repository root (the folder containing `README.md` and
`pyproject.toml`), regardless of its local folder name. Use Python 3.11.

## Create the environment

Windows PowerShell:

```powershell
py -3.11 -m venv .venv
.venv\Scripts\Activate.ps1
```

macOS:

```bash
python3.11 -m venv .venv
source .venv/bin/activate
```

Install on either platform:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
```

Select `.venv` as the Python interpreter in your editor. For the container setup,
see [the container guide](../.devcontainer/CONTAINER_GUIDE.md).

## Configure access

Copy `.env.example` to `.env` and set `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY`.
The Maps key needs access to Static Maps and Street View. Keep `.env` local.

Confirm that `data/external_raw/Mesh Block Counts, 2021.xlsx` exists. If stored
elsewhere, change `counts_path` in `configs/prediction/context_abs_v1.json`.

Continue with the [run guide](04_prediction_pipeline/prediction_workflow.md).
