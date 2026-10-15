# Prediction workflow architecture

```text
pedflow-predict
  → read the selected processed input sheet
  → resolve roads and coordinates with local Main Roads SLK geometry
  → validate prediction coordinates
  → load the reviewed ABS, imagery and model configuration
  → extract ABS and imagery features; join by site_id
  → apply the released model to eligible sites
  → attach existing AusRAP categories, derived bands and client-recoded estimates
  → fill Prediction_Output, Features and Metadata; write the manifest
```

`pedflow.prediction.predict_sites(sites, project_root, ...)` returns predictions, feature evidence and run metadata without exporting workbooks. It may build a reusable local AusRAP index in `data/cache/ausrap/`; imagery checkpoints remain optional. Library callers load credentials before invoking it. The CLI handles input and export. Runs accept any positive number of WA locations, determined by the submitted input rows. Supplied example counts do not constrain a new batch, and no observed/random split is required. Valid entered coordinates remain eligible when only carriageway matching is ambiguous, with the ambiguity retained as a warning; road-only input must resolve to one position. The [input notes](../data/processed/README.md) document these examples. The workflow reads local AusRAP references without using their values as model features or computing accuracy metrics. OOF evaluation is separate optional research work and is not invoked by production.

`pedflow.prediction.ausrap` matches and aggregates references independently of model success. `pedflow.flow` owns the shared category and band conventions. Source fingerprints, matched Excel row numbers and matching rules are recorded under `ausrap` in the manifest. See the [AusRAP integration record](04_prediction_pipeline/ausrap_reference.md).

The tracer integration test exercises the real CLI, sources, released model and export with simulated external ABS/imagery responses. See the [run guide](04_prediction_pipeline/prediction_workflow.md).
