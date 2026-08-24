# Shared data table formats

This document defines the three shared Excel table formats used by the pedestrian-flow project. Each workbook has exactly two worksheets: `Metadata` first and the flat data table second. These Excel workbooks are the authoritative shared input, model-development and output formats.

## Files and Git policy

| Logical table | Excel workbook | Git treatment |
|---|---|---|
| Model dataset | `data/processed/model_dataset.xlsx` | Authoritative 49-site workbook is tracked |
| Batch input | `data/templates/batch_input.xlsx` | Populated 100-location API test input is tracked |
| Prediction output | `data/templates/prediction_output.xlsx` | Prefilled 100-location comparison/output workbook is tracked |

The private repository is the authorised team workspace for the curated source inputs and the 49-row model dataset. Only sources directly required by the current target-checking, feature or spatial-linkage workflow are tracked; the 147 original survey workbooks and unselected candidate datasets remain outside the current Git tree. All retained files are stored in ordinary Git, so Git LFS is not required. Repository access must remain limited to approved project collaborators, and secrets, disposable intermediates, generated experiment outputs and fitted models remain excluded.

The model dataset, the two controlled test workbooks and this contract are intended for private Git sharing. The test rows are explicitly identified by `site_id`, `location_role` and `PENDING` status so they cannot be mistaken for completed predictions. Other generated prediction workbooks should be committed only when the team deliberately treats them as an approved project dataset rather than a disposable run artefact.

## 1. Model dataset

`model_dataset.xlsx` is the one-row-per-observation-site foundation workbook. The `Model_Data` worksheet currently contains stable location fields and the two observed targets. Confirmed model feature columns will be joined programmatically after the feature pipeline is finalised; placeholder feature columns are intentionally excluded.

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

`batch_input.xlsx` is the workbook uploaded by a user or dashboard process. One row in `Batch_Input` represents one requested location. The tracked file is a ready-to-run 100-location test batch: all 49 observed benchmark sites plus 51 new AusRAP-linked sites selected reproducibly with random seed `5553`, using one segment per previously unused road number.

| Column | Type | Required | Definition |
|---|---|---:|---|
| `site_id` | string | Yes | Client-supplied unique identifier for the requested location |
| `latitude` | number | Yes | WGS84 latitude |
| `longitude` | number | Yes | WGS84 longitude |
| `road_no` | string | No | Known road number for validation; the pipeline must still spatially verify it |
| `slk_km` | number | No | Known SLK in kilometres for validation |
| `road_name` | string | No | Human-readable name for checking and dashboard labels |
| `local_government_name` | string | No | Local government area resolved from Road Network for checking |

`site_id`, `latitude` and `longitude` are the stable minimum input. Road fields are optional hints, not authoritative joins. The pipeline must resolve the point to the current version of the road network and return the matched road/segment fields in the prediction output. Production batches may replace the test rows without changing the headers. Output must be joined by `site_id`, never by Excel row position.

## 3. Prediction output

`prediction_output.xlsx` contains one prefilled row for each of the same 100 batch-input locations. It is the comparison/result workbook and the tabular source for the dashboard. Identifiers, coordinates, road context, matched AusRAP fields and benchmark observations are prepared before model inference; prediction and run-result columns remain blank or `PENDING` until the backend updates them by `site_id`.

| Column | Type | Required | Definition |
|---|---|---:|---|
| `run_id` | string | At output | Unique batch execution identifier; blank before inference |
| `site_id` | string | Yes | Stable key matching the batch input |
| `location_role` | enum | Yes | `observed_benchmark` or `unobserved_test` |
| `latitude` | number | Yes | Validated WGS84 point latitude |
| `longitude` | number | Yes | Validated WGS84 point longitude |
| `road_no` | string | Yes | Matched Main Roads/AusRAP road number |
| `slk_km` | number | Yes | Matched SLK in kilometres |
| `road_name` | string | Yes | Resolved road display name |
| `local_government_name` | string | When available | Local government area resolved from Road Network |
| `matched_segment_id` | string | Yes | Deterministic identifier of the matched AusRAP source row |
| `segment_start_latitude` | number | Yes | WGS84 latitude of the matched segment start |
| `segment_start_longitude` | number | Yes | WGS84 longitude of the matched segment start |
| `segment_end_latitude` | number | Yes | WGS84 latitude of the matched segment end |
| `segment_end_longitude` | number | Yes | WGS84 longitude of the matched segment end |
| `observed_peak_cross_ped_per_h` | number | Benchmark only | Observed across-road target; blank for unobserved sites |
| `observed_peak_along_ped_per_h` | number | Benchmark only | Observed along-road target; blank for unobserved sites |
| `irap_ped_cross_band` | string | When available | Official iRAP categorical pedestrian-flow band across the road |
| `irap_ped_along_driver_band` | string | When available | Official iRAP categorical along-road band on the driver side |
| `irap_ped_along_passenger_band` | string | When available | Official iRAP categorical along-road band on the passenger side |
| `irap_vehicle_flow_aadt` | number | When available | Official iRAP vehicle flow (AADT) |
| `irap_speed_limit` | string | When available | Official iRAP speed-limit category |
| `irap_area_type` | string | When available | Official iRAP area type |
| `pred_peak_cross_ped_per_h` | number | At output | Predicted peak-hour across-road flow, pedestrians/hour |
| `pred_peak_along_ped_per_h` | number | At output | Predicted peak-hour along-road flow, pedestrians/hour |
| `feature_completeness_pct` | number | At output | Required deployed-model feature availability before imputation, from 0 to 100 |
| `processing_status` | enum | Yes | `PENDING`, `SUCCESS`, `PARTIAL` or `FAILED` |
| `model_version` | string | At output | Immutable deployed-model version |
| `feature_schema_version` | string | At output | Version defining the deployed feature set and transformations |
| `predicted_at_utc` | datetime | At output | ISO 8601 UTC generation timestamp |

`feature_completeness_pct` is retained because it has a concrete operational meaning:

```text
100 × number of available required model features
    / total required model features in feature_schema_version
```

It is calculated after retrieval and transformation but before any imputation. Candidate features that are not used by the deployed model are excluded from the denominator. This metric is not accuracy, confidence or prediction quality. A value below 100 remains visible even if the model can produce a result using an approved imputation rule.

`processing_status` has the following meaning:

- `PENDING`: the prepared row is awaiting model inference.
- `SUCCESS`: a prediction was produced and all required features were available.
- `PARTIAL`: a prediction was produced using an approved missing-feature/imputation path, or the road segment could not be resolved for line-map display.
- `FAILED`: no valid prediction was produced; prediction fields must be empty.

The retained AusRAP source provides pedestrian-flow categories such as `1 pedestrian`, `2 to 3 pedestrians` and `8+ pedestrians`; these values are not continuous observations and are not computed Star Ratings. Source blanks remain blank. The dashboard can place a point using `latitude` and `longitude`, draw an approximate matched segment using the four endpoint-coordinate columns, and colour the segment using either prediction column. Colour classes belong in dashboard configuration, not in this data contract.

## Web application data flow

Excel is the upload/download contract, not the live database used by the browser. A production request should follow one result object through the backend so the downloadable workbook and the map cannot disagree:

1. The browser uploads `batch_input.xlsx` to a batch-prediction API endpoint.
2. The backend reads `Batch_Input`, validates the schema, unique `site_id` values and coordinate ranges, and rejects invalid rows with explicit messages.
3. The feature pipeline retrieves the deployed features and matched road context for each valid `site_id`.
4. The deployed model returns the two predictions keyed by `site_id`; the backend merges them into the prepared output rows by `site_id`, never by row number.
5. One result dataset is stored for the run. From that same dataset, the API returns JSON for immediate map rendering and generates the downloadable `prediction_output.xlsx` file.
6. The map uses point and segment coordinates for location, prediction fields for colour, and the observed/iRAP fields for popup comparisons. An unobserved site displays “Not surveyed” rather than a fabricated observed value.

The browser therefore does not need to reopen and parse the generated Excel file after every prediction. JSON is the normal runtime response; Excel remains the auditable team exchange and download format.

## Model development and cross-validation

Do not create permanent train, validation and test copies or worksheets. Model code reads the `Model_Data` worksheet from `model_dataset.xlsx`, filters approved rows, and creates splits from `site_id` so that one observation location cannot appear in more than one role in the same fold.

With the current small sample, the planned primary evaluation is grouped/spatial five-fold cross-validation. The split assignment, out-of-fold predictions and metrics are generated experiment artefacts and belong under the ignored `outputs/` directory. Feature preprocessing, imputation, scaling and feature selection must be fitted inside each training fold rather than on all sites before splitting.

After model selection and honest out-of-fold evaluation, the selected deployment pipeline may be refitted on all approved observation sites. New batch-input locations are inference records, not additional training observations unless real survey targets are later collected and quality checked.

## Flat-table conventions

- The second worksheet has one header row and one site, request or result per subsequent row.
- Empty cells represent missing or not applicable values; do not use sentinel numbers such as `-999`.
- Units are encoded in column names where material.
- Identifiers are text values and must not be interpreted as measurements.
- Schema changes require updating this document and the relevant workbook Metadata.

## Excel conventions

The first worksheet is `Metadata` and explains purpose, use, sharing status and every field. The second worksheet contains the flat table with the documented headers and column order. The Excel files do not introduce permanent training splits, hidden feature columns or dashboard-only formatting. `model_dataset.xlsx`, `batch_input.xlsx` and `prediction_output.xlsx` are the authoritative shared workbooks. Changes to the prediction schema must increment `feature_schema_version` where applicable.
