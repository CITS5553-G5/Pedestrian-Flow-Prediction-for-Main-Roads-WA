# Run predictions

Run from `03_Project` after completing [setup](../SETUP.md).

## 1. Prepare input

Use CSV, Parquet or an Excel worksheet named `Batch_Input`. Required columns are `site_id`,
`latitude` and `longitude`. IDs must be unique; coordinates must be WGS84.
`coordinate_crs` defaults to `EPSG:4326` when omitted. Address-only input is not supported. The processed dataset contains 51 prepared
locations; `data/templates/batch_input_template.xlsx` restores the original
100-location test batch. Replace its rows for other locations. Optional
road number, SLK, road name and local government fields remain reporting hints.

## 2. Run

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --output-directory outputs/predictions/run_002
```

Use a new output directory for a new batch. The default is at most 10 concurrent
imagery sites, with no local requests-per-minute cap for Maps or Gemini. Request
failures still respect retry backoff and server cooldowns. Use `--workers` to change
the number of active sites; this is separate from input batch size.

| Option | Use |
| --- | --- |
| `--workers 5` | Change imagery concurrency |
| `--sheet Name` | Select another input worksheet |
| `--project-root PATH` | Run from outside the project directory |
| `--config PATH` | Override `configs/prediction/workflow_v1.json` |

Settings are documented in [configs](../../configs/README.md).
`python -m pedflow.prediction` accepts the same arguments.

## 3. Check results

| File | Contents |
| --- | --- |
| `predictions.xlsx` | `Predictions`: observations, predictions and iRAP comparisons; `Features`: three model inputs and diagnostics; `Metadata`: CRS, versions, run details and source definitions |
| `predictions.manifest.json` | Run ID/time, source descriptions, settings and model/recipe versions |
| `imagery.checkpoint.json` | Saved imagery progress |

Rows retain input order. Failed predictions and unavailable comparisons are blank,
never zero-filled. `status` describes prediction; `comparison_status` describes
the registered raw segment match. iRAP numeric references are copied from the
client CSV; text labels come from the raw AusRAP workbook. Neither is substituted
for measured counts or used as a model input. See the [table contract](../01_data_preparation/haoqi-shared_data_tables.md).

| Status | Action |
| --- | --- |
| `predicted` | Prediction available |
| `predicted_with_warning` | Read the message before using the result |
| `not_predicted` | Check missing features or source failure |
| `prediction_failed` | Check the reported model input/inference error |

Exit codes: `0` all sites predicted, possibly with warnings; `2` some sites not
predicted; `1` run failed. A failed rerun can leave earlier output files in place;
check the exit code and manifest timestamp.

## 4. Resume

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --output-directory outputs/predictions/run_002 --resume
```

Resume reuses completed imagery and retries failed or unavailable imagery. Records
marked `needs_review` remain saved; use a new output directory to re-extract them.
ABS is refreshed on every run. Changed locations or image recipes require a new
checkpoint; reordering input and changing worker counts are allowed.
`--resume` requires an existing checkpoint; it cannot start a fresh imagery run.

If a crash leaves a checkpoint lock, remove it only after confirming the recorded
process has stopped.

## 5. Refresh comparison columns only

```bash
pedflow-predict --refresh-comparison --output-directory outputs/predictions/run_001
```

This local operation refreshes comparisons and upgrades the output layout. It preserves predictions, model inputs, run ID
and inference times. No API call or model inference is performed. An optional
`--input` may supply road hints but must identify the same locations as the saved
run. This option cannot be combined with `--resume`.

## Current limits

Live sample validation and the dashboard connection remain pending. Historical
training imagery lacks complete recipe provenance; see the
[imagery reference](../02_feature_extraction/imagery_integration.md).
Comparison coverage currently uses the 100 verified links in
`data/processed/comparison_sites.csv`. New locations require verified source links
to receive iRAP labels; missing comparisons never block inference. The 49 observed
benchmark sites participated in training, so they are not an independent test set.
