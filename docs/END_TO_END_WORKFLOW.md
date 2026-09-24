# Prediction workflow architecture

```text
pedflow-predict
  → read and validate locations
  → load configs/prediction/workflow_v1.json
  → extract ABS, then concurrent imagery
  → join features by site_id
  → run pedestrian-linear-v1
  → attach observed/iRAP comparisons from local sources
  → write workbook and manifest
```

| Module | Responsibility |
| --- | --- |
| `prediction/` | Orchestration, eligibility, batch command and export |
| `context/` | ABS features and match status |
| `imagery/` | Images, Gemini features, request limits and checkpoints |
| `modeling/` | Released coefficients, feature mapping and inference |
| `validation.py` | Common site contract |
| `io.py` | Shared input reading, fingerprints and atomic file writes |

`pedflow.prediction.predict_sites(sites, project_root, ...)` returns a
`PredictionResult` with `predictions`, `features` and `metadata`. Library callers
load credentials and supply `site_id`, `latitude`, `longitude` and
`coordinate_crs=EPSG:4326`.

The workflow loads the saved model without training. Source modules return one row
per site; the prediction service checks coverage and joins by ID. Failed sources
retain missing values. Incomplete features block that site's prediction.

The CLI handles files around this service. The future backend must call the same
service; feature and model calculations stay out of the frontend. The output
template now uses this same three-sheet schema. Comparisons are limited to verified
site/coordinate links; unregistered locations remain predictable without them.

For operation, use the [run guide](04_prediction_pipeline/prediction_workflow.md).
For code changes, use the [integration rules](MODULE_INTEGRATION_GUIDE.md).

The tracer bullet test runs the real CLI, ABS/imagery adapters, released model and
export with three synthetic sites; only external HTTP/SDK responses are replaced.
It checks failed-site recovery, cached reuse, workbook provenance and independent
R reference predictions:

```bash
python -m pytest tests/integration/test_prediction_tracer.py -q
```
