# Data

`raw/` preserves client files; `external_raw/` holds public source snapshots; `processed/` holds cleaned research tables and the current prediction input; `templates/` holds workbook layouts. Each of these four folders has one README; their subfolders contain data only.

The 50 rows in `processed/batch_input_dataset.xlsx` are current test locations. Formal predictions read the explicitly selected processed input, with any batch size. `templates/batch_input_template.xlsx` offers road + SLK, coordinates, and both input layouts. The local Main Roads measured road snapshot supports new WA locations in both directions. `templates/prediction_output_template.xlsx` is the maintained three-sheet output layout, including `Features`; it is filled per run under `outputs/predictions/`.

The 49 surveyed locations in `processed/model_dataset.xlsx` are training and evaluation records, not required prediction sites. Formal prediction does not depend on a historical site comparison register.
