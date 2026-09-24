# Selected model: Python integration

The selected release is `pedestrian-linear-v1`: two separately fitted linear
regressions for `log1p` peak pedestrian flow, using the same three input features.
The coefficients and saved preprocessing were exported from Yashika's existing
R model bundle. This integration does not refit the models or change the reported
road-grouped cross-validation results.

`src/pedflow/modeling/model.py` provides inference. Its versioned release is
packaged at `src/pedflow/modeling/releases/pedestrian_linear_v1.json`, including
full-precision coefficients, factor levels, median/mode replacements, target
definitions, evaluation metrics and source-file checksums. Python predictions
require pandas and numpy from the shared requirements, but do not require R or
access to the original training workbook, RDS or notebook.

## Calling the model

```python
import pandas as pd
from pedflow.modeling import load_model

features = pd.DataFrame({
    "site_id": ["example-1"],
    "commercial_buildings": [2],
    "footpath_both_sides": [True],
    "abs_mb_category_simple": ["Commercial"],
})

model = load_model()  # Load once, then reuse for multiple batches.
predictions = model.predict(features)
```

An explicit release can be selected with `load_model(path_to_release_json)`.
The default release is located through package resources, independent of the
current working directory. It is included in built Python wheels.

| Input | Contract |
| --- | --- |
| `site_id` | Nonblank unique identifier; converted to a trimmed string |
| `commercial_buildings` | Finite non-negative numeric value using the training extraction definition; numeric strings may contain commas |
| `footpath_both_sides` | Boolean `True`/`False` or exact R strings `TRUE`/`FALSE` |
| `abs_mb_category_simple` | Exact string `Residential`, `Commercial` or `Other` |

Only these columns are required. Coordinates and imagery are handled upstream.
Extra columns, including observed targets, are ignored by inference. Input row
order and index are preserved and the caller's DataFrame is not modified.

For an ABS source result, use the supplied deterministic mapping before calling
the model:

```python
from pedflow.modeling import simplify_abs_categories

features["abs_mb_category_simple"] = simplify_abs_categories(
    context_features["abs_mb_category_2021"]
)
```

First join context and imagery tables by `site_id` with one-to-one validation;
the assignment above assumes rows/index have already been aligned. The helper
retains Residential and Commercial and maps other nonmissing ABS categories to
Other. Missing/blank source values remain missing. This is an intentional client
boundary improvement over the research notebook, which also mapped missing raw
ABS categories to Other. All 49 training records have nonmissing categories.

## Outputs and input failures

The returned table contains `site_id`, the three effective feature values,
`pred_peak_cross_ped_per_h`, `pred_peak_along_ped_per_h`, `model_version`, `status`
and `warnings`. Both predictions are in pedestrians per hour. Inference computes
the fitted linear predictor, applies `expm1`, then clips negative results to zero.
The effective footpath value is returned as `TRUE` or `FALSE`.

Default inference rejects missing features and unknown simplified categories with
`ContractError`, identifying the affected site. Missing columns, invalid values,
duplicate identifiers and nonfinite predictions also fail explicitly. The call is
atomic: it does not silently drop failed rows or return a partial batch.

For a reviewed use case that explicitly permits the original R preprocessing,
`model.predict(features, allow_fallback=True)` fills missing building counts with
the saved training median (2), missing footpath values with FALSE, and missing or
unseen simplified categories with Residential. Every replacement appears in the
row's warning; the returned feature columns show the values actually used. This
option does not permit malformed numbers or invalid boolean values. Upstream
source failures are handled by the shared prediction service, not
silently converted into imputable values.

Building counts outside the training range of 0–12 receive a warning. This is a
simple extrapolation flag, not a comprehensive out-of-distribution detector or a
prediction interval. No confidence score or interval is produced by this release.

## Reproducing the release and verification

Run the following from the project root in the supported R environment (jsonlite
and readxl are already in `renv.lock`):

```sh
Rscript --vanilla tools/export_linear_model.R \
  06_outputs/03_model_development/03_yashika_model_comparison/03_pedestrian_flow_final_model_bundle.rds \
  data/processed/model_dataset.xlsx \
  src/pedflow/modeling/releases/pedestrian_linear_v1.json \
  tests/fixtures/modeling/r_linear_reference.json

python -m pytest tests/unit/test_model.py -q
```

The exporter verifies that the workbook inputs and targets match the saved model
frames, checks the selected model, formula and treatment contrasts, and exports
the saved parameters without training. It checks that JSON serialization preserves
every fitted coefficient exactly when read back into R. The exported checksums
identify source files for provenance; they are not authenticity signatures.

The independent reference fixture applies the saved preprocessing, then R's
`predict.lm`, the inverse transformation and zero clipping. There are 79 cases: all
49 training records, 24 numerical/category combinations and 6 fallback cases.
Python is compared with these reference predictions using absolute tolerance
`1e-12` and relative tolerance `1e-13`. Further contract tests cover invalid inputs,
explicit fallback warnings, input preservation, extrapolation, overflow,
incompatible releases and saved-release round trips.

These reference predictions test software equivalence. They are full-model fitted
or synthetic predictions and must not replace the report's out-of-fold predictions
when showing generalisation performance.

## Remaining workflow integration

This completes the model inference component. Imagery now has its shared module
and concurrent batch adapter; its live feature compatibility remains to be reviewed.
Feature assembly, location-to-prediction orchestration and batch I/O now use
`pedflow.prediction.predict_sites` and `pedflow-predict`. See the
[prediction run guide](../04_prediction_pipeline/prediction_workflow.md).
The dashboard backend remains separate work and should call the same service.
No frontend model formulas are needed.

The R research workflow remains the source for training and scientific validation.
For a future approved fit, create a new model version, regenerate the release and
R references, run the same checks and explicitly select the new version. Do not
edit coefficients by hand or overwrite this release with a different fitted model
under the same version identifier.
