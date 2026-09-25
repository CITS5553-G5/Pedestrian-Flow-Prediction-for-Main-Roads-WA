# Prediction workflow architecture

```text
pedflow-predict
  → read the selected processed input sheet
  → resolve roads and coordinates with local Main Roads SLK geometry
  → validate prediction coordinates
  → load the reviewed ABS, imagery and model configuration
  → extract ABS and imagery features; join by site_id
  → apply the released model to eligible sites
  → fill Prediction_Output, Features and Metadata; write the manifest
```

`pedflow.prediction.predict_sites(sites, project_root, ...)` returns predictions, feature evidence and run metadata without writing files. Library callers load credentials before invoking it. The CLI handles input and export. The 50 current processed rows are test locations; future batches may contain any number of WA locations. RAP and surveyed counts are separate evaluation data and do not limit prediction coverage.

The tracer integration test exercises the real CLI, sources, released model and export with simulated external ABS/imagery responses. See the [run guide](04_prediction_pipeline/prediction_workflow.md).
