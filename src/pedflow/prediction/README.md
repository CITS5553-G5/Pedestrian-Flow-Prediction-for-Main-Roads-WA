# Prediction: Complete prediction workflow

This module connects Context, Imagery and Modeling through one entry point.
It coordinates execution, joins and status handling; feature calculations and
model formulas remain in their respective modules.

## File responsibilities

| File | Purpose |
| --- | --- |
| [__main__.py](__main__.py) | Entry point for `pedflow-predict` / `python -m pedflow.prediction`; parse arguments, load `.env`, read sites, call the service and export |
| [config.py](config.py) | Load Context and Imagery settings and the model; verify ABS-only configuration, extraction fingerprints and model file hashes/versions |
| [workflow.py](workflow.py) | Define `PredictionResult` and `predict_sites`; extract and join features, map categories, predict per site and record run metadata |
| [comparison.py](comparison.py) | Define output columns and attach reconciled observations, raw iRAP values and verified source-row links after inference |
| [io.py](io.py) | Write the three-sheet workbook and manifest; refresh existing comparisons offline |
| [__init__.py](__init__.py) | Expose `predict_sites` and `PredictionResult` |

## Execution flow

```text
__main__.py: load environment variables and call pedflow.io.read_sites
  → workflow.predict_sites
      → Shared validation: validate sites
      → config.load_settings: check configuration and load the model
      → context.workflow.build_context_features: extract ABS features
      → imagery.build_imagery_features: concurrent imagery extraction and resume
      → Shared validation: check coverage and join by site_id
      → modeling.simplify_abs_categories: map ABS categories
      → Check source statuses and all three features
      → model.predict: calculate predictions for eligible sites
      → comparison.add_comparisons: join local comparison evidence without changing predictions
      → Return PredictionResult
  → io.write_prediction_outputs: export results
```

Context and Imagery tables may have different row orders; joins always use
`site_id`. Predictions preserve input order, and an individual source or model
failure does not remove the site. Invalid input tables or configurations fail
the overall run.

## Inputs, results and exports

The entry point is `predict_sites(sites, project_root, ...)`. The site table
requires `site_id`, `latitude`, `longitude` and `coordinate_crs=EPSG:4326`.
Main optional arguments are `config_path`, `workers`, `checkpoint_path`, `resume`
and the imagery progress callback `progress`. Direct callers must load environment
variables themselves.

| Result | Contents | Command-line export |
| --- | --- | --- |
| `result.predictions` | Location, observations, predictions, iRAP references and independent prediction/comparison statuses | `Predictions` worksheet in `predictions.xlsx` |
| `result.features` | Three model inputs, original ABS category, necessary feature extraction diagnostics only | `Features` worksheet in the same workbook |
| `result.metadata` | Run ID, CRS, versions, source descriptions and processing counts | Readable `Metadata` sheet and full `predictions.manifest.json` |

The Python service returns data without exporting files. The command-line entry
point calls `io.py`; a future application can use the same returned results directly.

The output schema is `prediction_output_v3`; the extraction/model recipe remains
`prediction_v1`. Column names use `obs_peak_*` and `status` consistently with the
model dataset and service. `comparison_sites.csv` holds the 100 verified source
links formerly embedded in the output template. Matching requires both ID and
coordinates; stored source rows must also match the registered road and SLK.
Unregistered sites remain predictable with blank comparisons. iRAP comparisons and source IDs are in the main table; detailed row-level comparison
provenance is in `metadata.comparison.site_records`. No comparison column is placed
in `Features`. Full candidate
features remain in the unchanged research dataset, outside the prediction report.

`--refresh-comparison --output-directory outputs/predictions/run_001` refreshes
saved comparisons and layout without API calls or model inference. An optional
`--input` must contain the same IDs
and coordinates; it can provide road hints. Original inference times and run ID
remain unchanged, with a separate comparison refresh time added.

## Statuses and recovery

| Prediction status | Meaning |
| --- | --- |
| `predicted` | Both predictions are available |
| `predicted_with_warning` | Predictions are available with warnings, such as imagery coverage or values outside the training range |
| `not_predicted` | Source statuses prevent prediction or required features are missing |
| `prediction_failed` | Model input validation or calculation failed |

The workflow does not impute missing features. Command-line exit codes are `0`
when all sites are predicted, possibly with warnings; `2` when some sites remain
unpredicted; and `1` when the overall run fails.

`--resume` reuses imagery progress from `imagery.checkpoint.json` in the output
directory. ABS is queried on every run. The checkpoint does not cache complete
prediction results; the Imagery module manages reuse rules.

The default configuration is [workflow_v1.json](../../../configs/prediction/workflow_v1.json).
See the [project guide](../../../README.md) for commands, API keys and input examples,
and the [tracer bullet test](../../../tests/integration/test_prediction_tracer.py)
for verification of the complete workflow.
