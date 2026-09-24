# Module integration rules

Formal code belongs in `src/pedflow/`; notebooks call it for experiments and
explanation. Commands and application adapters call the shared workflow.

| Component | Contract |
| --- | --- |
| Context source | `SourceDefinition.extractor(sites, config, project_root)` returns `FeatureResult` |
| Imagery | `build_imagery_features(sites, config, ...)` returns `ImageryResult` |
| Model | `load_model(...).predict(features)` returns predictions |
| Prediction | `predict_sites(sites, project_root, ...)` returns `PredictionResult` |

## Required behaviour

Inputs, paths and settings are explicit arguments. Credentials come from the
runtime environment. Source results contain exactly one row per requested
`site_id`; joins use that ID. Reject duplicate IDs and incompatible schemas.
Keep unavailable values distinct from measured zero or false.

Record source/version, retrieval details and material settings in metadata.
Keep secrets and raw provider error messages out of outputs. Feature names, units,
categories and missing-value meanings are versioned contracts.

Only ABS belongs in the current default Context registry. Research sources require
an explicit registry and `configs/research/`. Google Places Aggregate remains an
exclusion guard under the existing project decision.

The model release contains the selected coefficients and preprocessing. Prediction
must not train or modify it. Training and evaluation stay in the research workflow;
preprocessing must be fitted within each validation fold.

Feature modules must not depend on prediction or notebooks. The prediction service
owns orchestration; the CLI handles files and the future backend handles HTTP.
Neither adapters nor the frontend duplicate feature/model calculations.

## Change checklist

1. Preserve source evidence and move reusable logic into the appropriate module.
2. Define inputs, outputs, missing-value behaviour and provenance.
3. Update configuration and version bindings when feature meaning or model changes.
4. Test the normal path, site coverage and relevant failures; run `tests/integration/test_prediction_tracer.py` for changes to the prediction path.
5. Update the calling notebook, command and affected documentation.

Keep reviewed data and model releases immutable. Put generated runs under ignored
`outputs/`; use `06_outputs/` only for reviewed team results.
