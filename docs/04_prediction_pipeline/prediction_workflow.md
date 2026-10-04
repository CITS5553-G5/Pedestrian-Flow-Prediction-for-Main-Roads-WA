# Run predictions

Run from the repository root (the folder containing `README.md` and
`pyproject.toml`), regardless of its local folder name, after completing
[setup](../SETUP.md). The current 50 rows in
`data/processed/batch_input_dataset.xlsx` are test locations. A formal run
reads the chosen processed input file and has no fixed location count.

## 1. Prepare locations

The workbook `data/templates/batch_input_template.xlsx` has three alternative sheets. `Batch_Input` includes both road references and coordinates; `Road_SLK` accepts `site_id`, `road_no` and point `slk_km`; `Coordinates` accepts `site_id`, `latitude` and `longitude`. Keep only the rows for the current prediction batch in a processed copy. CSV and Parquet inputs use the same columns. IDs must be unique. Coordinates are WGS84 (`coordinate_crs=EPSG:4326`, the default).

An official whole road segment can be supplied as `road_no`, `start_slk` and `end_slk`, with optional `cway`, and no `slk_km`. The predictor uses the SLK midpoint along the actual measured road line. A plain `road_no` + `slk_km` denotes one point, not a start or end. On divided roads, supply `cway` if the two carriageways cannot be distinguished.

When both a coordinate pair and road reference are present, the coordinates determine the feature point. The road reference is checked against the local Main Roads measured line. A conflicting pair is reported as `road_coordinate_conflict` and is not predicted. A coordinate within 30 m of an unambiguous road is assigned its road number and SLK, while the original coordinate remains the feature point. If no safe road match is found, a coordinate-only row can still be predicted with a warning and blank road fields.

The local [Main Roads SLK snapshot](../../data/external_raw/README.md) provides the road geometry. Location matching does not send submitted coordinates to that service. Refreshing the complete public snapshot is a separate maintenance task.

No observed flow is required. Optional `obs_peak_cross_ped_per_h` and `obs_peak_along_ped_per_h` must be finite, non-negative values and are shown only when supplied. When a row represents one original AusRAP record, optional `ausrap_record_id` can bind it to that record in a particular source snapshot; keep the normal location columns as well. The [integration record (中文)](ausrap_reference_integration_zh.md) defines the ID and matching rules.

## 2. Run

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --sheet Batch_Input --output-directory outputs/predictions/run_002
```

Choose `--sheet Road_SLK` or `--sheet Coordinates` for the other template layouts. `--workers` controls concurrent imagery extraction, `--config` selects the reviewed recipe, and `--project-root` allows execution from elsewhere. Use a new output directory for a new batch. The feature and model recipes are unchanged.

## 3. Read the result

`predictions.xlsx` contains `Prediction_Output`, `Features` and `Metadata`. The 29-column main sheet retains the entered road reference, prediction coordinates, road matching details and two pedestrian/hour predictions. It also shows optional observations, crossing categories, existing AusRAP crossing/combined along-road bands, client-recoded estimates and comparison notes. `Features` records the three model inputs plus extraction diagnostics. `Metadata` includes the bilingual field dictionary. `predictions.manifest.json` records run provenance, source fingerprint and matched AusRAP rows. `imagery.checkpoint.json` supports recovery. Rows retain input order; missing values remain blank rather than zero.

`location_status` describes road matching. `status` is `predicted`, `predicted_with_warning`, `not_predicted` or `prediction_failed`; `message` gives the reason. The command exits `0` when every row has both predictions, `2` when some rows are not predicted, and `1` for a run-level error.

`comparison_status` reports AusRAP availability separately: `matched`, `matched_partial`, `matched_bands_only`, `matched_no_flow`, or a specific source/location/matching problem. Check `comparison_notes` for the cause. CLI exit status continues to describe model prediction completion; exit `0` does not guarantee AusRAP coverage. Missing references never erase valid predictions, and reference matching can succeed when a model prediction fails.

The local source defaults to `data/raw/AusRAP Data - Words - MSDS.xlsx`. Point references use road/SLK ±0.1 km, averaging all overlapping source records without carriageway filtering or deduplication. Along-road references combine both sides before averaging; no per-side flow columns are exported. Mixed crossing categories leave the single original-category field blank and list categories in the notes. **Existing iRAP flow estimate (recoded)** is a client-defined recoding, not an official precise count. Multi-record interval endpoints are derived averages, not confidence intervals.

This workflow does not calculate MAE/RMSE. Unknown sites have blank observed fields unless supplied in the input. The independent 49-site OOF evaluation is preserved separately and does not constrain new prediction locations or supply their observations.

## 4. Resume

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --sheet Batch_Input --output-directory outputs/predictions/run_002 --resume
```

Resume reuses completed imagery and retries failed imagery; ABS and AusRAP matching are refreshed. The source SHA-256 selects a reusable SQLite index under `data/cache/ausrap/`, so a changed source creates a new index. Changing locations or imagery recipes requires a new checkpoint. `--resume` needs an existing checkpoint and cannot start a fresh imagery run.

The current 50 test points all match the local road snapshot. Live source/model validation for every new address remains a separate operational check, especially for ambiguous carriageways and locations beyond the 30 m road threshold.
