# Core table data contract

This document defines the three flat tables used by the pedestrian-flow project. Each table has a CSV form for code/API use and an Excel companion for people. Every Excel workbook has exactly two worksheets: `Metadata` first and the flat data table second.

## Files and Git policy

| Logical table | CSV | Excel | Git treatment |
|---|---|---|---|
| Model dataset | `data/processed/model_dataset.csv` | `data/processed/model_dataset.xlsx` | Both tracked in the authorised private team repository |
| Batch input | `data/templates/batch_input.csv` | `data/templates/batch_input.xlsx` | Both blank templates are tracked |
| Prediction output | `data/templates/prediction_output.csv` | `data/templates/prediction_output.xlsx` | Both blank templates are tracked |

The private repository is the authorised team workspace for the curated source inputs and the 49-row model dataset. Only sources directly required by the current target-checking, feature or spatial-linkage workflow are tracked; the 147 original survey workbooks and unselected candidate datasets remain outside the current Git tree. All retained files are stored in ordinary Git, so Git LFS is not required. Repository access must remain limited to approved project collaborators, and secrets, disposable intermediates, generated experiment outputs and fitted models remain excluded.

The model dataset, two empty CSV/Excel template pairs and this contract are intended for private Git sharing. Do not add example records to the templates because examples can be mistaken for real API requests or results. Generated prediction files should be committed only when the team deliberately treats them as an approved project dataset rather than a disposable run artefact.

## 1. Model dataset

`model_dataset.csv` is the one-row-per-observation-site foundation table. It currently contains stable location fields and the two observed targets. Confirmed model feature columns will be joined programmatically after the feature pipeline is finalised; placeholder feature columns are intentionally excluded.

| Column | Type | Required | Definition |
|---|---|---:|---|
| `site_id` | string | Yes | Stable survey-site key in `<survey_batch_id>-<two-digit-site-number>` form |
| `survey_batch_id` | string | Yes | Survey batch identifier parsed from the source workbook folder |
| `source_location_id` | string | No | Original client-derived road/SLK identifier; retained for traceability |
| `location_id` | string | Yes | Standardised `<road_no>-<slk>` identifier used by the current pipeline |
| `road_no` | string | Yes | Standardised Main Roads/AusRAP road number |
| `slk_km` | number | Yes | Straight Line Kilometre position, in kilometres |
| `road_name` | string | Yes | Standardised road name |
| `survey_location_name` | string | Yes | Human-readable survey location label; standardised when an internal workbook label resolves a filename error |
| `latitude` | number | Yes | WGS84 latitude derived from the containing AusRAP segment |
| `longitude` | number | Yes | WGS84 longitude derived from the containing AusRAP segment |
| `coordinate_crs` | string | Yes | Coordinate reference system; currently `EPSG:4326` |
| `coordinate_method` | string | Yes | Method used to derive coordinates from road number and SLK |
| `ausrap_segment_match_count` | integer | Yes | Number of AusRAP rows containing the road/SLK position |
| `n_survey_days` | integer | Yes | Number of raw survey days contributing to the site target; currently three |
| `obs_peak_cross_ped_per_h` | number | Yes | Observed peak-hour across-road pedestrian target, pedestrians/hour |
| `obs_peak_along_ped_per_h` | number | Yes | Observed peak-hour along-road pedestrian target, pedestrians/hour |
| `target_source` | string | Yes | File or reconstruction path supplying the target values |
| `qa_status` | enum | Yes | `ready` or `review_required` |
| `qa_note` | string | No | Reconciliation or audit note; a ready row may retain a documented correction |

The target aggregation follows the client R logic: calculate hourly values, average the three survey days at each time of day, then take the maximum of that mean hourly profile separately for across-road and along-road movement. The resulting site-level values are already stored in this table; the raw macro-enabled workbooks are archival audit inputs rather than routine training inputs.

The local file contains 49 unique `site_id` values and 49 unique `location_id` values, and all 49 rows are `ready` after source reconciliation:

- `250341-04`: the client compact values (125 cross, 25.5 along) exactly reproduce a Thursday-Friday average. Recalculation from all three survey days, independently confirmed by the workbooks' embedded hourly values, gives 87 cross and 17.3333 along.
- `260335-38`: the special Carnarvon layout contains one 15-minute along-road table. Treating embedded hourly columns as additional 15-minute inputs caused the client value 29.6667; the actual 15-minute series and embedded hourly values both give 18.3333 along.
- `260335-31` and `260335-32`: `M010` is Chidlow York Road, while Road Network places Coolgardie Esperance Highway SLK 366.85 and 165.45 on `H010`. The standardised identifiers therefore use `H010`; observed targets independently reproduce from the workbooks.
- `260335-40`: the location is absent from `Ped_iRAP_merged.csv`, but all three raw workbooks and their embedded hourly values reproduce the stored targets. The internal workbook label also resolves the filename's “Norseman” wording to Northampton.

Primary model development may use all 49 rows. Because two target values were corrected from the client compact table, final reporting must also include a sensitivity check that repeats the evaluation without `250341-04` and `260335-38`; this tests whether either correction materially changes the model conclusion.

## 2. Batch input

`batch_input.csv` is the only table a client or dashboard upload process should populate manually. One row represents one requested location.

| Column | Type | Required | Definition |
|---|---|---:|---|
| `site_id` | string | Yes | Client-supplied unique identifier for the requested location |
| `latitude` | number | Yes | WGS84 latitude |
| `longitude` | number | Yes | WGS84 longitude |
| `road_no` | string | No | Known road number for validation; the pipeline must still spatially verify it |
| `slk_km` | number | No | Known SLK in kilometres for validation |
| `road_name` | string | No | Human-readable name for checking and dashboard labels |

`site_id`, `latitude` and `longitude` are the stable minimum input. Road fields are optional hints, not authoritative joins. The pipeline must resolve the point to the current version of the road network and return the matched road/segment fields in the prediction output.

## 3. Prediction output

`prediction_output.csv` is one row per processed batch-input record. It is the download/API table and the tabular source for the dashboard.

| Column | Type | Required | Definition |
|---|---|---:|---|
| `run_id` | string | Yes | Unique batch execution identifier |
| `site_id` | string | Yes | Echo of the batch-input key |
| `latitude` | number | Yes | Validated WGS84 latitude |
| `longitude` | number | Yes | Validated WGS84 longitude |
| `road_no` | string | No | Road number resolved by the pipeline |
| `slk_km` | number | No | SLK resolved by the pipeline |
| `road_name` | string | No | Resolved display name |
| `matched_segment_id` | string | No | Versioned road-segment key used to join dashboard geometry |
| `pred_peak_cross_ped_per_h` | number | Conditional | Predicted peak-hour across-road flow, pedestrians/hour |
| `pred_peak_along_ped_per_h` | number | Conditional | Predicted peak-hour along-road flow, pedestrians/hour |
| `feature_completeness_pct` | number | Yes | Percentage of required deployed-model features successfully obtained before imputation, from 0 to 100 |
| `processing_status` | enum | Yes | `SUCCESS`, `PARTIAL` or `FAILED` |
| `model_version` | string | Conditional | Immutable deployed-model version; required when a prediction is produced |
| `feature_schema_version` | string | Yes | Version that defines the required feature denominator and transformations |
| `predicted_at_utc` | datetime | Conditional | ISO 8601 UTC generation timestamp |

`feature_completeness_pct` is retained because it has a concrete operational meaning:

```text
100 × number of available required model features
    / total required model features in feature_schema_version
```

It is calculated after retrieval and transformation but before any imputation. Candidate features that are not used by the deployed model are excluded from the denominator. This metric is not accuracy, confidence or prediction quality. A value below 100 remains visible even if the model can produce a result using an approved imputation rule.

`processing_status` has the following meaning:

- `SUCCESS`: a prediction was produced and all required features were available.
- `PARTIAL`: a prediction was produced using an approved missing-feature/imputation path, or the road segment could not be resolved for line-map display.
- `FAILED`: no valid prediction was produced; prediction fields must be empty.

The dashboard can colour a road using either prediction column after joining `matched_segment_id` to versioned road geometry. Colour classes belong in dashboard configuration, not in this data contract.

## Model development and cross-validation

Do not create permanent `train.csv`, `validation.csv` and `test.csv` copies. Model code reads `model_dataset.csv`, filters approved rows, and creates splits from `site_id` so that one observation location cannot appear in more than one role in the same fold.

With the current small sample, the planned primary evaluation is grouped/spatial five-fold cross-validation. The split assignment, out-of-fold predictions and metrics are generated experiment artefacts and belong under the ignored `outputs/` directory. Feature preprocessing, imputation, scaling and feature selection must be fitted inside each training fold rather than on all sites before splitting.

After model selection and honest out-of-fold evaluation, the selected deployment pipeline may be refitted on all approved observation sites. New batch-input locations are inference records, not additional training observations unless real survey targets are later collected and quality checked.

## CSV conventions

- UTF-8 encoding, comma delimiter and one header row.
- One row is one site/request/result; no merged cells or multi-row headings.
- Empty fields represent missing/not applicable values; do not use sentinel numbers such as `-999`.
- Units are encoded in column names where material.
- Identifiers are strings and must not be interpreted as measurements.
- Schema changes require updating this document and, for prediction output, incrementing `feature_schema_version` where applicable.

## Excel conventions

The first worksheet is `Metadata` and explains purpose, use, sharing status and every field. The second worksheet preserves the exact CSV headers and column order. The Excel files do not introduce training splits, calculations, hidden feature columns or dashboard-only formatting. Code should continue to treat the CSV schema as authoritative; the Excel files are human-friendly entry and review companions.
