# Data

The [raw sources](raw/README.md) preserve the supplied road and survey references. [External snapshots](external_raw/README.md) support location matching and feature research. [Processed tables](processed/README.md) contain the current prediction example and the separate modelling dataset. [Templates](templates/README.md) define workbook layouts and example inputs.

Prediction accepts any positive batch size, determined by the populated rows in the selected input sheet or table. New inputs can contain surveyed locations, unknown locations or any mixture; no fixed count or group ratio is required. Template rows can be replaced, added or removed before saving a separate input file.

`processed/batch_input_dataset.xlsx` and the populated input template are supplied examples. Their current row counts describe those files only. The [current batch manifest](processed/batch_input_dataset.manifest.json) describes the processed example; the [historical preparation record](templates/batch_input_example_100.manifest.json) records the original template sample. These records do not prescribe the size of another batch.

`templates/batch_input_template.xlsx` supports road + SLK, coordinates, and combined inputs. Local Main Roads geometry supports location matching. `templates/prediction_output_template.xlsx` defines `Prediction_Output`, `Features` and `Metadata`; each run writes a filled workbook under Git-ignored `outputs/predictions/`.

The 49 surveyed locations in `processed/model_dataset.xlsx` are training and evaluation records, not required prediction sites. Production prediction does not read a fixed survey register or run historical OOF evaluation. Original survey workbooks and some research source snapshots are stored separately from Git; their availability is documented in the source-folder guides.
