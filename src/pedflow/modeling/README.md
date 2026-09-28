# Modeling: Load trained models and predict

This module runs inference with the selected `pedestrian-linear-v1` models.
It requires no runtime training, data downloads or API keys.

## File responsibilities

| File | Purpose |
| --- | --- |
| [model.py](model.py) | Validate and load model releases, simplify ABS categories, check input features and calculate predictions and warnings |
| [releases/pedestrian_linear_v1.json](releases/pedestrian_linear_v1.json) | Store coefficients, category encodings, preprocessing parameters, versions and training provenance for both linear models |
| [__init__.py](__init__.py) | Expose `load_model`, `PedestrianFlowModel` and `simplify_abs_categories` |

The release is exported from saved R models by
[export_linear_model.R](../../../tools/export_linear_model.R). This script is for
model release and verification, not routine prediction.

## Execution flow

```text
load_model()
  → Read and validate the release JSON
  → Return PedestrianFlowModel
      → predict(features)
          → Check the three features, categories and missing values
          → Calculate crossing and along-road model predictions
          → Apply expm1 and clip negative results to zero
          → Return predictions, version, status and warnings
```

Both models use the same three features to predict peak hourly crossing and
along-road pedestrian flows respectively.

| Input field | Requirement |
| --- | --- |
| `site_id` | Unique, nonblank site identifier |
| `commercial_buildings` | Non-negative commercial building count |
| `footpath_both_sides` | `True`/`False` or the strings `TRUE`/`FALSE` |
| `abs_mb_category_simple` | `Residential`, `Commercial` or `Other` |

`model.predict(features)` returns `pred_peak_cross_ped_per_h` and
`pred_peak_along_ped_per_h` in pedestrians/hour, along with the effective inputs,
`model_version`, `status` and `warnings`. Missing or invalid inputs raise an error
by default; values outside the training range produce a warning. Explicitly setting
`allow_fallback=True` enables saved imputation rules, which the prediction workflow
does not use.

## Integration with other modules

Context returns the raw `abs_mb_category_2021`; Imagery returns the two imagery
features. Prediction joins them by `site_id` and calls `simplify_abs_categories`:
Residential and Commercial are retained, other nonmissing categories become Other,
and missing values stay missing. It then calls `predict`.

Modeling does not retrieve images, query ABS or check source statuses. Standalone
callers must supply checked features; see the [Python example](../../../docs/03_model_development/selected_model_integration.md#calling-the-model).
For complete prediction, use `pedflow-predict` as shown in the root README;
no additional script is required.

The [model tests](../../../tests/unit/test_model.py) compare calculations with
independent R reference results. See the [model integration guide](../../../docs/03_model_development/selected_model_integration.md)
for model provenance and release reproduction.
