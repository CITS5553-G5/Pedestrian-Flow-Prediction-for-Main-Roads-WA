# Shared data table formats

The input, research and output tables serve different purposes. Each data sheet
has one header row and one location per row. Match by `site_id`, never row order.
Identifiers are text; blanks mean unavailable, never zero.

| File | Purpose |
| --- | --- |
| `data/processed/model_dataset.xlsx` | Unchanged, authoritative 49-site research dataset |
| `data/processed/batch_input_dataset.xlsx` | Prepared 51-site prediction batch |
| `data/templates/batch_input_template.xlsx` | Restored 100-location test input |
| `data/templates/prediction_output_template.xlsx` | 100-location `prediction_output_v3` comparison template; prediction values blank |
| `data/processed/comparison_sites.csv` | 100 verified site/coordinate/source-row links migrated from the old output template |
| `data/templates/model_dataset_template.xlsx` | Preserved original modelling foundation |

Raw sources and the approved model dataset remain unchanged. Generated predictions
belong in `outputs/predictions/<run>/`, outside tracked research data. The pre-v2
templates and `run_001` output are backed up under `07_test/output_schema_before_20260921/`.

## 1. Model dataset

`model_dataset.xlsx` is the one-row-per-observation-site processed modelling workbook. The `Model_Data` worksheet contains stable location fields, the two observed targets, 24 context fields and 13 candidate imagery fields. Context and imagery were joined by exact `site_id`; all 49 retained imagery rows were also required to match the foundation latitude, longitude, road number, SLK and road name. The 51 `TEST-AUSRAP-*` imagery rows were excluded. The four food-and-shopping context fields come from Overture Maps Places release `2026-08-19.0` and replace the excluded Google Places Aggregate experiment. The source QA field `overture_places_data_status` remains in the source-specific workbook and is not included as a model predictor. The original pre-feature workbook remains unchanged at `data/templates/model_dataset_template.xlsx`.

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

The processed workbook deliberately omits the former `target_source`, `qa_status` and `qa_note` columns. Their original values and row-level reconciliation notes remain in `model_dataset_template.xlsx`. The processed workbook's `Metadata` sheet is the authoritative dictionary for the 24 context and 13 candidate imagery fields, including source links, derivations, completeness, and known imagery-provenance limitations.

The target aggregation follows the client R logic: calculate hourly values, average the three survey days at each time of day, then take the maximum of that mean hourly profile separately for across-road and along-road movement. The resulting site-level values are already stored in this table; the raw macro-enabled workbooks are archival audit inputs rather than routine training inputs.

The local file contains 49 unique `site_id` values and 49 unique `location_id` values, and all 49 rows are `ready` after source reconciliation:

- `250341-04`: the client compact values (125 cross, 25.5 along) exactly reproduce a Thursday-Friday average. Recalculation from all three survey days, independently confirmed by the workbooks' embedded hourly values, gives 87 cross and 17.3333 along.
- `260335-38`: the special Carnarvon layout contains one 15-minute along-road table. Treating embedded hourly columns as additional 15-minute inputs caused the client value 29.6667; the actual 15-minute series and embedded hourly values both give 18.3333 along.
- `260335-31` and `260335-32`: `M010` is Chidlow York Road, while Road Network places Coolgardie Esperance Highway SLK 366.85 and 165.45 on `H010`. The standardised identifiers therefore use `H010`; observed targets independently reproduce from the workbooks.
- `260335-40`: the location is absent from `Ped_iRAP_merged.csv`, but all three raw workbooks and their embedded hourly values reproduce the stored targets. The internal workbook label also resolves the filename's “Norseman” wording to Northampton.

Primary model development may use all 49 rows. Because two target values were corrected from the client compact table, final reporting must also include a sensitivity check that repeats the evaluation without `250341-04` and `260335-38`; this tests whether either correction materially changes the model conclusion.

## 2. Batch input

Use `Batch_Input` in the processed dataset for the prepared batch, or use the
restored 100-location template for testing. Replace its rows for other locations. The seven input columns are:

| Column | Required | Definition |
| --- | --- | --- |
| `site_id` | Yes | Unique, nonblank location ID |
| `latitude` | Yes | WGS84 latitude in degrees |
| `longitude` | Yes | WGS84 longitude in degrees |
| `road_no` | No | Road number hint, checked against the comparison register |
| `slk_km` | No | SLK position hint in kilometres |
| `road_name` | No | Road display name |
| `local_government_name` | No | Local government display name |

Readers accept an optional `coordinate_crs`, defaulting to `EPSG:4326`; other CRS
values are rejected. Do not add model features or observed targets to user input.
Unverified road hints do not establish a road match.

## 3. Prediction output

The service, exported workbook and output template share `prediction_output_v3`.
The extraction/model configuration remains `prediction_v1` because neither the
features nor the model changed. The workbook has `Predictions`, `Features` and
`Metadata`, in that order. The restored output template contains 100 locations and available reference
values, with blank predictions and `pending` status until inference. Its Features
sheet has headers only because the template has not extracted features. Completed
runs contain actual features and prediction statuses; no values are imputed.

### Predictions

| Column | Meaning |
| --- | --- |
| `site_id` | Input location ID |
| `road_no`, `slk_km`, `road_name`, `local_government_name` | Input road hints, replaced by registered values only for verified locations |
| `latitude`, `longitude` | Validated WGS84 coordinates |
| `location_role` | `observed_benchmark` when ID and coordinates match the model dataset; otherwise `unobserved` |
| `obs_peak_cross_ped_per_h` | Reconciled observed peak crossing flow, pedestrians/hour |
| `pred_peak_cross_ped_per_h` | Predicted peak crossing flow, pedestrians/hour |
| `irap_peak_cross_reference` | Original `Ped_Peak_Cross` from the client CSV, copied without conversion |
| `irap_ped_cross_band` | Original crossing label from the registered AusRAP source row |
| `obs_peak_along_ped_per_h` | Reconciled observed peak along-road flow, pedestrians/hour |
| `pred_peak_along_ped_per_h` | Predicted peak along-road flow, pedestrians/hour |
| `irap_peak_along_reference` | Original `Ped_Peak_Along` from the client CSV, copied without conversion |
| `irap_peak_driver_reference`, `irap_peak_passenger_reference` | Original separate-side numeric references, copied without filling missing values |
| `irap_numeric_status` | Availability of the original client numeric reference |
| `matched_segment_id`, `irap_numeric_source_id` | Identifiers linking the result to the raw segment and client numeric record |
| `irap_ped_along_driver_band`, `irap_ped_along_passenger_band` | Original along-road labels for each side |
| `status` | `predicted`, `predicted_with_warning`, `not_predicted` or `prediction_failed` |
| `message` | Prediction warning or failure explanation; blank when none |
| `comparison_status` | `matched`, `unregistered_site`, `coordinate_mismatch`, `road_reference_conflict` or `source_unavailable_or_changed` |

Prediction status is independent of comparison availability. A matched iRAP row
may itself contain blank labels; `matched` never implies complete reference data.
The 49 observed locations trained the released model, so their current predictions
are in-sample checks, not independent model evaluation.

### Features

The first columns hold `site_id` and the three actual model inputs:
`commercial_buildings`, `footpath_both_sides`, `abs_mb_category_simple`.
Retain the original ABS category and MB/SA1 codes, ABS/imagery statuses and errors,
imagery warnings, image count and extraction time for traceability. Population,
density and area fields unused by the deployed model are omitted from this report;
the standalone Context export and research dataset retain them.

`Features` contains no observed targets or iRAP comparison fields. Original iRAP
numbers, labels, availability and source identifiers are in `Predictions`. Detailed
per-site source rows, survey dates and match diagnostics are retained in the JSON
manifest under `comparison.site_records`; duplicate row identifiers and statuses
are not repeated in the feature table.

### Metadata and source meaning

CRS, model version, run ID, inference times, output schema, units, source descriptions
and key definitions appear once in `Metadata`. The JSON manifest retains full
configuration and source details. An offline comparison refresh
preserves the original run ID and inference times and adds its own refresh time.

`data/raw/AusRAP Data - Words - MSDS.xlsx` supplies the original text labels.
`data/raw/Ped_iRAP_merged.csv` supplies the existing numeric references. The local
client script `data/raw/R scripts for process and linkage/2. Link to iRAP.R` documents
code-to-representative-count conversion and averaging overlapping segments within
SLK +/- 0.1 km. Those approximate numeric references are not measured counts and
do not describe the same single-segment aggregation as the text labels. Do not
decode the word labels to invent missing numeric references or calculate automatic
errors against them. Observations come from the reconciled model dataset, not the
CSV's historical uncorrected observation columns.

The literal label `None` in the word export remains text. It is distinct from an
empty source cell and is not silently parsed as missing or converted to zero.

### Comparison registration

`comparison_sites.csv` stores the existing 100 approved site/coordinate/road links
and raw Excel row numbers. Every original label was verified against raw data
when moving these links out of the former output template. Runtime matching
requires exact ID and coordinates within 1e-7 degrees; supplied road number and
SLK must not conflict. Stored source rows must match the registered road and SLK.

For additional locations, prediction works immediately, with unavailable
comparisons left blank. To add comparison coverage, verify the road, SLK,
coordinates and source Excel row, then append the approved link. When replacing
the raw source, update the row links to match. This is a curated reference join, not
an automatic nearest-road matcher. Templates are never runtime reference sources.

## Application integration

The backend should call `predict_sites` and use the same `PredictionResult` for
JSON and workbook export. Display point locations from latitude/longitude and
comparison values from the returned table. Convert missing values to JSON null;
never replace them with zero. The backend connection remains to be implemented.

## Model development and cross-validation

Do not create permanent train, validation and test copies or worksheets. All 49 rows in the current processed workbook came from the approved foundation recorded in `model_dataset_template.xlsx`. Model code reads `Model_Data` from `model_dataset.xlsx` and creates splits from `site_id` so that one observation location cannot appear in more than one role in the same fold.

With the current small sample, the planned primary evaluation is grouped/spatial five-fold cross-validation. Working split assignments, out-of-fold predictions and metrics are experiment artefacts and remain outside Git until the team deliberately promotes a reviewed result into `06_outputs/`. Feature preprocessing, imputation, scaling and feature selection must be fitted inside each training fold rather than on all sites before splitting.

After model selection and honest out-of-fold evaluation, the selected deployment pipeline may be refitted on all approved observation sites. New batch-input locations are inference records, not additional training observations unless real survey targets are later collected and quality checked.
