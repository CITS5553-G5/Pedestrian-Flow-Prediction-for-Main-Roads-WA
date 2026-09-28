# Prediction workflow

`__main__.py` reads the selected processed input sheet and invokes `workflow.predict_sites`; `location.py` resolves road number/SLK and coordinates using the local measured Main Roads snapshot; `config.py` verifies the reviewed feature and model recipe; `io.py` fills the maintained output template and manifest; `schema.py` defines the formal output columns.

The input template offers three alternative sheets: `Road_SLK` for a road reference, `Coordinates` for a WGS84 coordinate pair, and `Batch_Input` for both. `--sheet` selects the sheet; its default is `Batch_Input`. A formal run reads the explicitly supplied processed input file. The 50 existing rows are test locations, and batch size is not fixed.

Each row needs a unique `site_id` and either `latitude`/`longitude`, `road_no` + point `slk_km`, or `road_no` + `start_slk` + `end_slk` for an official segment. Point SLK is neither the segment start nor its end. A whole segment uses its SLK midpoint on the measured road line; optional `cway` resolves carriageway ambiguity. When both coordinates and a road reference are supplied, the entered coordinates determine the feature point and the road reference is checked against them. A distance over 30 m or an SLK difference over 0.05 km is reported as `road_coordinate_conflict`, and that row is not predicted.

`Prediction_Output` keeps the supplied `road_no`/`slk_km` and the `latitude`/`longitude` used for feature extraction. `matched_road_no`, `matched_slk_km`, `matched_cway` and `road_offset_m` describe the local road match; `location_status` reports its outcome. An unresolved or ambiguous road-only row has no prediction coordinate and is not predicted. A coordinate-only row can still be predicted when no road is safely identified, provided its ABS and imagery features succeed; its road match fields remain blank and its prediction has a warning. Check `status` and `message` for the final per-row outcome.

The service joins ABS and imagery features by `site_id` and applies the unchanged released model to produce crossing and along-road pedestrians/hour. `Features` records the deployed inputs and extraction diagnostics. Formal prediction does not read RAP values or a fixed site register. The command writes `predictions.xlsx` and `predictions.manifest.json`; imagery extraction also writes `imagery.checkpoint.json` for `--resume` to reuse. A resume requires an existing compatible checkpoint.

See the [run guide](../../../docs/04_prediction_pipeline/prediction_workflow.md) for commands and output meanings.
