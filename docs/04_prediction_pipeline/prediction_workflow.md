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

## 2. Run

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --sheet Batch_Input --output-directory outputs/predictions/run_002
```

Choose `--sheet Road_SLK` or `--sheet Coordinates` for the other template layouts. `--workers` controls concurrent imagery extraction, `--config` selects the reviewed recipe, and `--project-root` allows execution from elsewhere. Use a new output directory for a new batch. The feature and model recipes are unchanged.

## 3. Read the result

`predictions.xlsx` contains `Prediction_Output`, `Features` and `Metadata`. The main sheet retains the entered road reference, the prediction coordinates, matched road number/SLK/carriageway, road distance, location status, and two pedestrian/hour predictions. `Features` records the three model inputs plus extraction diagnostics. `predictions.manifest.json` records run provenance. `imagery.checkpoint.json` supports recovery. Rows retain input order; missing predictions remain blank rather than zero.

`location_status` describes road matching. `status` is `predicted`, `predicted_with_warning`, `not_predicted` or `prediction_failed`; `message` gives the reason. The command exits `0` when every row has both predictions, `2` when some rows are not predicted, and `1` for a run-level error.

Formal results contain no RAP estimates or observed counts. The 49 surveyed sites and RAP files can be used in a separate evaluation; their coverage does not limit where the released model can predict.

## 4. Resume

```bash
pedflow-predict --input data/processed/batch_input_dataset.xlsx --sheet Batch_Input --output-directory outputs/predictions/run_002 --resume
```

Resume reuses completed imagery and retries failed imagery; ABS is refreshed. Changing locations or imagery recipes requires a new checkpoint. `--resume` needs an existing checkpoint and cannot start a fresh imagery run.

The current 50 test points all match the local road snapshot. Live source/model validation for every new address remains a separate operational check, especially for ambiguous carriageways and locations beyond the 30 m road threshold.
