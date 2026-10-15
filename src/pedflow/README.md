# pedflow: Shared workflow code

Reusable Python modules shared by command-line tools, notebooks and the future
application. See the [project guide](../../README.md) for environment setup,
API keys and standalone commands.

## Module responsibilities

| Directory | Responsibility | Input → Output |
| --- | --- | --- |
| [context](context/README.md) | Extract ABS context features | Site coordinates → ABS categories, attributes and match status |
| [imagery](imagery/README.md) | Retrieve images and use Gemini to assess visible features | Site coordinates → commercial building count, footpaths on both sides and extraction status |
| [modeling](modeling/README.md) | Load trained models and calculate predictions | Three complete features → crossing and along-road pedestrian flows |
| [prediction](prediction/README.md) | Resolve road/SLK or coordinates, extract features, predict and export | Site table → predictions, features and run metadata |
| [evaluation](evaluation/README.md) | Reproduce the historical internal OOF comparison from a pinned research snapshot | Saved observations, OOF predictions and reference evidence → paired metrics and comparison tables |

```text
pedflow-predict
    │
    └─ prediction: resolve road/SLK and coordinates, validate sites, load configuration and model
          │
          ├─ context: extract ABS features
          ├─ imagery: extract imagery features concurrently across sites
          │
          └─ Join by site_id, simplify ABS categories, check completeness
                └─ modeling: calculate both predictions
                      └─ prediction: return results for command-line export
```

Context runs before Imagery; concurrency occurs across sites within Imagery.
Context and Imagery are independent, and Modeling can run directly on prepared
features.

## Shared files

| File | Purpose |
| --- | --- |
| [validation.py](validation.py) | Validate site IDs, coordinates and CRS; check feature coverage; join one-to-one by ID while preserving input order |
| [io.py](io.py) | Read Excel, CSV and Parquet; preserve text IDs; calculate content fingerprints; write through temporary files before replacing destination files |
| [paths.py](paths.py) | Locate the project root and resolve relative configuration paths |
| [exceptions.py](exceptions.py) | Define shared exceptions for configuration, data contracts and source execution |
| [flow.py](flow.py) | Define versioned continuous-flow categories, reference recoding values and band formatting |
| [__init__.py](__init__.py) | Identify the Python package and expose its version |

## Data and configuration

Workflow settings are in [configs/prediction](../../configs/prediction/); API keys
are in the project root `.env`. Prediction accepts either road number plus SLK,
WGS84 coordinates, or both; it resolves a coordinate before invoking Context
and Imagery. Those source modules require `site_id`, `latitude`, `longitude`
and `coordinate_crs`. File readers default a missing CRS column to `EPSG:4326`.

Source modules return features and statuses for each site without calling the
model. Prediction checks source statuses and feature completeness before inference.
Failed sites remain in the results; missing features are not replaced with zeros.

Evaluation runs separately from prediction. It reads saved OOF results rather than
the released model and requires fingerprint-matched research inputs; see the
[research reproduction guide](../../docs/05_model_evaluation/reproduction.md).

## Integration verification

The [tracer bullet test](../../tests/integration/test_prediction_tracer.py) runs
three simulated sites through the actual readers, ABS and imagery adapters, model
and exporters, replacing only external service responses. It checks individual
site failures, resume behavior and agreement with independent R reference predictions.

Run from the project root:

```bash
python -m pytest tests/integration/test_prediction_tracer.py -q
```

This test does not validate live imagery feature accuracy or API performance.
