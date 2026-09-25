# Shared data table formats

The input, research and output tables serve different purposes. Each data sheet
has one header row and one location per row. Match by `site_id`, never row order.
Identifiers are text; blanks mean unavailable, never zero.

| File | Purpose |
| --- | --- |
| `data/processed/model_dataset.xlsx` | Unchanged, authoritative 49-site research dataset |
| `data/processed/batch_input_dataset.xlsx` | Current 50-location test batch; formal prediction input after its rows are replaced |
| `data/templates/batch_input_template.xlsx` | Example input layout, not the formal prediction source |
| `data/templates/prediction_output_template.xlsx` | Styled `prediction_output_v4` layout with empty result and feature tables |
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

`data/processed/batch_input_dataset.xlsx` contains 50 current test points, not a geographic or batch-size limit. Formal runs read the locations in the chosen processed input file. `data/templates/batch_input_template.xlsx` provides three alternative sheets: `Batch_Input` for both road reference and coordinates, `Road_SLK` for road reference only, and `Coordinates` for coordinates only. Each row needs a unique `site_id`.

Coordinates are a WGS84 `latitude`/`longitude` pair. A point road reference is `road_no` plus `slk_km`. An official segment uses `road_no`, `start_slk` and `end_slk`, with optional `cway`; its representative prediction point is the SLK midpoint on the measured road line. `slk_km` alone is a point and does not mean the start or end of a segment. The optional `coordinate_crs` defaults to `EPSG:4326`; other systems are rejected.
The existing `road_name` and `local_government_name` columns in the 50-site test sheet are legacy notes; formal matching and modelling do not read them.

When both input pairs exist, entered coordinates drive feature extraction and the road reference is checked. A conflict blocks that row's prediction. A coordinate-only row retains its exact entered position and can still be predicted if no road can be matched; `location_status` records the issue. Road-only rows must resolve to a unique measured road point. The local [Main Roads SLK snapshot](../../data/external_raw/README.md) enables both directions without sending submitted locations to the road service.

## 3. Prediction output

The formal output schema is `prediction_output_v4`; model recipe `prediction_v1` is unchanged. `data/templates/prediction_output_template.xlsx` retains its established workbook style and has `Metadata`, `Prediction_Output` and `Features`. The exporter writes exactly one row per submitted site, preserving input order.

`Prediction_Output` contains the input type; supplied `road_no`, `slk_km`, `cway` and optional segment bounds; prediction `latitude`/`longitude`; matched road number, SLK and carriageway; offset from the measured road; location status; crossing and along-road predicted pedestrians/hour; prediction status; and message. For a road-only input, the prediction coordinate is interpolated from measured geometry. For coordinate input, the supplied coordinate remains the prediction point. Missing numbers stay blank.

`Features` records the deployed inputs `commercial_buildings`, `footpath_both_sides` and `abs_mb_category_simple`, plus original ABS category/codes and ABS/imagery status diagnostics. `Metadata` and the JSON manifest record run ID, times, versions, units and source information. Formal output contains no surveyed counts, RAP estimates or text bands.

Formal prediction does not need a fixed site comparison register. The separate 49-site surveyed dataset and client RAP files remain available for model evaluation. The client numeric RAP estimates cover only some sites; raw AusRAP pedestrian categories should not be turned into arbitrary continuous counts.

## Application integration

The backend should call `predict_sites` and use the returned `PredictionResult` for JSON and workbook export. Display location and prediction statuses with both numerical predictions; represent missing values as JSON null, never zero. The backend connection remains to be implemented.

## Model development and cross-validation

Do not create permanent train, validation and test copies or worksheets. All 49 rows in the current processed workbook came from the approved foundation recorded in `model_dataset_template.xlsx`. Model code reads `Model_Data` from `model_dataset.xlsx` and creates splits from `site_id` so that one observation location cannot appear in more than one role in the same fold.

With the current small sample, the planned primary evaluation is grouped/spatial five-fold cross-validation. Working split assignments, out-of-fold predictions and metrics are experiment artefacts and remain outside Git until the team deliberately promotes a reviewed result into `06_outputs/`. Feature preprocessing, imputation, scaling and feature selection must be fitted inside each training fold rather than on all sites before splitting.

After model selection and honest out-of-fold evaluation, the selected deployment pipeline may be refitted on all approved observation sites. New batch-input locations are inference records, not additional training observations unless real survey targets are later collected and quality checked.
