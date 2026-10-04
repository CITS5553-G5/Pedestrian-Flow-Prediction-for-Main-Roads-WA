# Pedestrian Flow Prediction for Main Roads WA

CITS5553 Group 5 — predict peak crossing and along-road pedestrian flows

```text
Location table → ABS + imagery → three selected features → model → add AusRAP reference → predictions.xlsx
```

## Repository structure

### Numbered project workspaces

| Directory | Purpose |
| --- | --- |
| `01_data_preparation/` | Prepare and reconcile survey and road-network data |
| `02_feature_extraction/` | Develop Context and Imagery features |
| `03_model_development/` | Train, compare and select models |
| `04_prediction_pipeline/` | Integrate and demonstrate the prediction workflow |
| `05_application/` | Dashboard prototype and future backend |
| `06_outputs/` | Reviewed team outputs |

### Shared workflow infrastructure

| Directory | Purpose |
| --- | --- |
| `src/pedflow/` | Reusable extraction and prediction code |
| `configs/` | Prediction settings and retained research configurations |
| `data/` | Source data, processed datasets and templates |
| `docs/` | Technical documentation |
| `tests/` | Automated verification |
| `outputs/` | Local run results; ignored by Git |

Notebooks and application code use the shared implementation in `src/pedflow/`.
See the [code guide](src/pedflow/README.md) for module and script responsibilities.

## Native setup for Windows and macOS

Install Python 3.11 and run all commands from the repository root, beside this
README and `pyproject.toml`. Each teammate creates their own `.venv`; dependencies
are installed from the shared `requirements.txt`. The local folder containing the
repository can have any name.

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

Then install on either platform:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install --no-deps -e .
python -m pip check
```

Select `.venv` as the VS Code interpreter and notebook kernel. Reactivate it in
new terminals. After dependency changes, reinstall `requirements.txt`; after new
commands are added, rerun the editable installation (`pip install --no-deps -e .`).

## Runtime configuration

### API keys

If `.env` is absent, copy `.env.example` to `.env`. If it exists, fill its missing
keys from the template. `.env` stays local; the shared template currently contains
the imagery notebook's temporary test keys, to be removed after testing.

| Variable | Used for |
| --- | --- |
| `GOOGLE_MAPS_API_KEY` | Satellite/Static Maps and Street View |
| `GEMINI_API_KEY` | Imagery feature extraction |

`pedflow-imagery` and `pedflow-predict` load `.env` automatically. Existing process
environment variables take precedence. Context and model-only tests need no keys.

### Data and settings

Confirm that `data/external_raw/Mesh Block Counts, 2021.xlsx` exists. If stored
elsewhere, update `sources.abs_meshblock_sa1.options.counts_path` in the Context
configuration.

| Configuration | Controls |
| --- | --- |
| `configs/prediction/context_abs_v1.json` | ABS source path, input worksheet and export formats |
| `configs/prediction/imagery_v1.json` | Gemini model, sampling, concurrency and request limits |
| `configs/prediction/workflow_v1.json` | Selected feature and model versions |

The prediction workflow uses ABS only for Context. Other candidate sources remain
under `configs/research/`. See the [configuration guide](configs/README.md) before
changing feature or model versions.

## Run the workflow

### Prepare input

`data/processed/batch_input_dataset.xlsx` contains the current 50-location test
batch. Formal runs read the specified processed input, with any positive number
of locations. `data/templates/batch_input_template.xlsx` offers three input
sheets: `Batch_Input` (both identifiers and coordinates), `Road_SLK` (road and
SLK), and `Coordinates` (latitude/longitude). Select one sheet with `--sheet`.
CSV and Parquet with the same columns are also supported.

| Column | Requirement | Example |
| --- | --- | --- |
| `site_id` | Unique, nonblank text identifier | `site_001` |
| `latitude`, `longitude` | WGS84 coordinate pair; required for coordinate input | `-31.95`, `115.86` |
| `coordinate_crs` | Optional; defaults to `EPSG:4326` | `EPSG:4326` |
| `road_no`, `slk_km` | Road number and point SLK pair; required for road input | `H001`, `356.36` |
| `start_slk`, `end_slk` | Optional official segment bounds instead of `slk_km`; the midpoint SLK is used | `356.30`, `356.40` |
| `cway` | Optional carriageway code where a divided road is ambiguous | `Single` |
| `road_name`, `local_government_name` | Optional legacy notes in the 50-site test sheet; not used for matching or modelling | `Albany Highway`, `Albany` |

When both pairs are present, the entered coordinates drive feature extraction;
the road reference is checked against the local measured road line. Conflicts
are flagged without a prediction. A coordinate near, but not exactly on, the
road is retained as the prediction point and matched to a road within 30 m when
unambiguous. Road-only points are placed directly on the measured line. The
[local Main Roads SLK snapshot](data/external_raw/README.md) is
used for matching; the client's submitted locations are not sent to that service.

### Complete prediction

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --output-directory outputs/predictions/run_001
```

This command extracts ABS and imagery, joins the three features by `site_id` and
runs the saved models. No additional script or model training is required.

| Output | Contents |
| --- | --- |
| `predictions.xlsx` | `Prediction_Output`: 29 columns with locations, model predictions and existing AusRAP references; `Features`: model inputs and source checks; `Metadata`: bilingual field definitions and run details |
| `predictions.manifest.json` | Run versions, settings, source fingerprint and matched AusRAP source rows |
| `imagery.checkpoint.json` | Saved imagery progress |

Predictions are in **pedestrians/hour**. Check `status` and `message`; failed sites
retain blank predictions. Use a new output directory for each batch. To continue
the same batch from its checkpoint:

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --output-directory outputs/predictions/run_001 --resume
```

Resume refreshes ABS, reuses completed imagery and retries failed imagery. See the
[run guide](docs/04_prediction_pipeline/prediction_workflow.md) for recovery details.

`Features` contains the model inputs and extraction diagnostics. After model
inference, the workflow adds existing categories, derived flow bands and
**Existing iRAP flow estimate (recoded)** from the local AusRAP Words workbook.
Check `comparison_status` and `comparison_notes` separately from prediction status.
Unknown sites need no observed counts; the prediction workflow computes no
MAE/RMSE and reads no fixed survey-site register. The released model and its
three predictors remain unchanged. See the [integration record (中文)](docs/04_prediction_pipeline/ausrap_reference_integration_zh.md).

### Independent modules

| Module | Input | Output | Access needed |
| --- | --- | --- | --- |
| Context | Location table | ABS features and match status | Internet and ABS workbook |
| Imagery | Location table | Building count, footpath feature and status | Maps and Gemini keys |
| Model | Three prepared features and `site_id` | Crossing and along-road predictions | Local model release |

**Context — ABS only**

```bash
pedflow-context --input data/processed/batch_input_dataset.xlsx --output-directory outputs/context_features/run_001
```

Writes `batch_abs_context_features.xlsx`, a Parquet copy and a manifest. Check
`abs_match_status` and `abs_error_message` in the `Context_Features` worksheet.

**Imagery — Google Maps + Gemini**

```bash
pedflow-imagery --input data/processed/batch_input_dataset.xlsx --output-directory outputs/imagery_features/run_001 --workers 10
```

Writes `imagery_features.csv`, a manifest and a checkpoint. Check `imagery_status`,
`imagery_error` and `imagery_warnings`. Use `--sheet Name` for another worksheet or
`--resume` to continue the same batch. See the [Imagery guide](docs/02_feature_extraction/imagery_integration.md).

**Model — included in complete prediction**

`pedflow-predict` calls the model automatically. Direct prediction from prepared
features uses the Python interface in the [model guide](docs/03_model_development/selected_model_integration.md);
there is no separate model-only command. To test the model, use the command below.

## Verification and current status

Run the existing model and integrated workflow tests offline:

```bash
python -m pytest tests/unit/test_model.py tests/integration/test_prediction_tracer.py -q
```

These check model results against R references and exercise workflow recovery with
simulated provider responses. Live sample validation and dashboard integration
remain pending. Use `--help` with any installed command for its options.

## Optional container environment

Open the repository in VS Code and select **Dev Containers: Reopen in Container**.
The container provides Python, R and Node.js with a separate environment at
`/opt/pedflow-venv`. Use the same runtime configuration and workflow commands above.
See the [container guide](.devcontainer/CONTAINER_GUIDE.md) for setup and maintenance.
