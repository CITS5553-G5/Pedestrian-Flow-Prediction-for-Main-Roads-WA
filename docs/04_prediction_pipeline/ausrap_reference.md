# Prediction with existing AusRAP references

Delivery edition: 4 October 2026. Workflow: `prediction_v2`. Main output: `prediction_output_v5`, 29 columns. Configuration filename: `configs/prediction/workflow_v1.json`.

The existing `pedflow-predict` command resolves locations, extracts the same three model features, applies `pedestrian-linear-v1`, and attaches local AusRAP comparison information. No new prediction workflow or model fit is required. This path computes no MAE/RMSE, even when observed counts are supplied. The [49-site OOF evaluation](../../04_prediction_pipeline/irap_comparison/comparison_report.md) is a separate deliverable.

## Input and output

Use the same [batch template](../../data/templates/batch_input_template.xlsx) for surveyed sites, unknown sites, or a mixture. Provide a unique `site_id` and either WGS84 coordinates, road/SLK, or both. A segment can use `road_no`, `start_slk`, `end_slk` and optional `cway`; its measured-line midpoint is the prediction point. See the [run guide](prediction_workflow.md) for exact location rules.

Optional `obs_peak_cross_ped_per_h` and `obs_peak_along_ped_per_h` are finite, non-negative numeric counts. They are copied from this input only, never retrieved automatically from the survey dataset and never used as predictors. Unknown observations stay blank; actual zero remains zero. A surveyed site still uses the final released model when submitted to this pipeline.

The exporter produces `predictions.xlsx` with `Prediction_Output`, `Features` and `Metadata`, plus `predictions.manifest.json`. Online imagery runs also write `imagery.checkpoint.json`. Output filenames and the input template remain the same for every site type. The optional `ausrap_record_id` identifies one original source record; it is distinct from the survey dataset's `source_location_id` and from the user-supplied `site_id`.

## Reference matching

The default source is `data/raw/AusRAP Data - Words - MSDS.xlsx`, containing 189,222 records. A source-hash-specific SQLite index is generated under `data/cache/ausrap/`. It is a rebuildable runtime cache, not an additional required input. The source snapshot has 21 reversed SLK intervals, normalized internally while preserving original Excel row numbers, and 2,082 missing flow cells. Source data are not edited.

For a point, the reference window is `[SLK - 0.1, SLK + 0.1]` km on the same road. A supplied segment uses its midpoint for this window. Include source rows whose normalized start is at most the window end and end is at least the window start. Comparisons use the stored floating-point values directly: no epsilon, SLK rounding, or integer-metre conversion. Each matching record receives equal weight, with no length weighting, deduplication or carriageway filtering. This deliberately reproduces the customer's existing baseline. Road geometry matching can still require a carriageway to identify the feature point; `cway` is not a side-flow column.

For a batch representing individual AusRAP records, provide `ausrap_record_id` in the form `ausrap:<source SHA-256>:<Excel row number>` alongside normal location columns. This project identifier selects exactly one row in that snapshot, subject to location checks. Invalid, stale or conflicting IDs are reported without silently falling back to nearby-record aggregation. It is not an official global record ID.

## Counts, categories and ranges

**Existing iRAP flow estimate (recoded)** means client-provided AusRAP categories converted by the customer's recoding script, potentially combined across sides and averaged across records. It is not an official exact predicted pedestrian count. The observation and model prediction columns remain original continuous counts.

| Category | Reference integer band (pedestrians/hour) | Client recoded value |
| ---: | --- | ---: |
| 1 | 0 | 0 |
| 2 | 1–5 | 3 |
| 3 | 6–25 | 15 |
| 4 | 26–50 | 38 |
| 5 | 51–100 | 75 |
| 6 | 101–200 | 150 |
| 7 | 201–300 | 250 |
| 8 | 301–400 | 350 |
| 9 | 401–500 | 450 |
| 10 | 501–900 | Unavailable |
| 11 | 900+ | Unavailable |

The reference dictionary is the [iRAP manual, version 1.5 (2024), pages 26 and 30–31](https://austroads.gov.au/__data/assets/pdf_file/0033/836295/iRAP_Star_Rating_and_Investment_Plan_Manual_English.pdf), checked during preflight. This does not establish the exact edition used by the historic source dataset or imply it is the latest manual.

The Words source's labels `None`, `1 pedestrian`, `2 to 3 pedestrians`, `4 to 5 pedestrians`, `6 to 7 pedestrians` and `8+ pedestrians` map to categories 1–6, respectively. These source labels are category encodings; they are not hourly model counts. Literal `None` represents category 1 / zero flow. An actually empty cell is missing and must not be converted to zero.

A unique crossing category is displayed only if all required matched source categories agree. Mixed categories leave that field blank and list the category set in `comparison_notes`. Do not infer an original category by reclassifying the mean recoded count. Missing required categories leave the affected result unavailable rather than silently averaging a smaller subset.

Crossing bands average source lower endpoints and upper endpoints separately. Along-road bands first sum Driver and Passenger endpoints within each record, then average the combined endpoints across matched rows. Recoded along-road counts use the same sum-then-average order. No separate side-flow columns are exported. Open upper bounds remain open; they are not replaced by an invented maximum. Derived multi-record intervals are neither new official bands nor confidence intervals.

Observed and model crossing categories use `positive_upper_bound_v1`: category 1 for zero; positive counts use inclusive upper bounds `5,25,50,100,200,300,400,500,900`, then category 11 above 900. For example, 5 is category 2, 5.2 is category 3, and 900 is category 10. This project rule handles continuous values without rounding or replacing counts. There is no single-side category for a combined along-road total.

## Main output dictionary

The maintained [output template](../../data/templates/prediction_output_template.xlsx) has the same ordered fields as the exporter. All flow counts and interval endpoints are pedestrians/hour; SLK is kilometres, road offset is metres, and coordinates are WGS84 degrees.

| Position | Field | Type | Meaning |
| ---: | --- | --- | --- |
| 1 | `site_id` | text | Unique input location ID |
| 2 | `input_type` | text | Coordinates, road_slk, road_segment or both |
| 3 | `road_no` | text | Supplied official road number |
| 4 | `slk_km` | number | Supplied point SLK in kilometres |
| 5 | `cway` | text | Supplied carriageway |
| 6 | `start_slk` | number | Official segment start SLK |
| 7 | `end_slk` | number | Official segment end SLK |
| 8 | `latitude` | number | Prediction point WGS84 latitude |
| 9 | `longitude` | number | Prediction point WGS84 longitude |
| 10 | `matched_road_no` | text | Road number resolved from measured geometry |
| 11 | `matched_slk_km` | number | SLK resolved from measured geometry |
| 12 | `matched_cway` | text | Resolved carriageway |
| 13 | `road_offset_m` | number | Distance from supplied coordinates to matched road in metres |
| 14 | `location_status` | text | Road matching or input consistency outcome |
| 15 | `obs_peak_cross_ped_per_h` | number | Observed peak-hour flow — Crossing. Optional input only; blank for unknown sites. |
| 16 | `pred_peak_cross_ped_per_h` | number | Predicted peak crossing pedestrians per hour |
| 17 | `existing_irap_cross_recoded_ped_per_h` | number | Existing iRAP flow estimate (recoded) — Crossing. Client recoding, then equal-weight source-row mean; not an official exact count. |
| 18 | `observed_cross_category` | integer | Observed flow category — Crossing. Project continuous upper-bound rule; raw count is unchanged. |
| 19 | `predicted_cross_category` | integer | Model-predicted flow category — Crossing. Same continuous rule as observed categories. |
| 20 | `existing_ausrap_cross_category` | integer | Existing AusRAP flow category — Crossing. Blank when categories are missing or mixed; details in comparison_notes. |
| 21 | `existing_ausrap_cross_band` | text | Existing AusRAP flow band — Crossing. Mean source endpoints when multiple records match; not a confidence interval. |
| 22 | `obs_peak_along_ped_per_h` | number | Observed peak-hour flow — Along-road. Optional input only; original survey coverage retained. |
| 23 | `pred_peak_along_ped_per_h` | number | Predicted peak along-road pedestrians per hour |
| 24 | `existing_irap_along_recoded_ped_per_h` | number | Existing iRAP flow estimate (recoded) — Along-road. Sum both sides within each record, then average matched records. |
| 25 | `existing_ausrap_along_combined_band` | text | Existing AusRAP combined flow band — Along-road. Sum side endpoints, then average matched records. |
| 26 | `status` | text | Prediction outcome |
| 27 | `message` | text | Warning or failure details |
| 28 | `comparison_status` | text | AusRAP reference matching/availability. Separate from model prediction status; does not measure accuracy. |
| 29 | `comparison_notes` | text | AusRAP comparison notes: missing categories, multiple carriageways, mixed categories, source or matching problems. |

## Status and provenance

`location_status` describes position resolution. `status` and `message` describe model inference. `comparison_status` and `comparison_notes` describe AusRAP availability independently. Missing reference data never erase a valid model prediction, and reference data may be present for a row whose model prediction failed.

Successful reference statuses include `matched`, `matched_partial`, `matched_bands_only` and `matched_no_flow`; other statuses identify source, location or matching problems. These are availability states, not accuracy grades. CLI exit code 0 means every row has both model predictions, 2 means some rows lack predictions, and 1 is a run-level error. Exit 0 does not guarantee reference coverage.

The manifest records model/configuration fingerprints, source SHA-256, matching method, original Excel rows and category sets. A source change selects a new reference index. Resume reuses completed imagery and retries failed imagery while refreshing ABS and AusRAP matching; a fresh batch or changed imagery recipe needs its own output/checkpoint.

## Verification and limits

The [offline example](../../04_prediction_pipeline/prediction_example/README.md) replays ten previously extracted feature rows through the final model and attaches references. It is not a fresh imagery run. The integration test reproduces all 45 available historic client means and bands, including `H009-170.3` / site `250303-13`, whose along-road recoded mean is 126. Adding an overlap epsilon would incorrectly change that baseline.

The 49-site location precheck found 36 unambiguous matches and 13 ambiguous carriageways when road/SLK inputs were used. Coordinate-only inputs found 33 unambiguous matches and 16 ambiguous roads. Supply reviewed carriageway/location information before claiming a fresh 49-site operational run is complete. Those operational constraints do not invalidate the saved OOF workbook, which uses model-development records.

The full network has not been predicted. Source-row count does not imply unique physical locations, complete feature coverage or guaranteed prediction success. For a whole-network batch, define the prediction unit, review geometry and service coverage, and plan external requests separately.
