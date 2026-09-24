# Data

| Path | Use |
| --- | --- |
| `processed/batch_input_dataset.xlsx` | Prepared 51-location batch input |
| `templates/batch_input_template.xlsx` | Restored 100-location test input with required and optional fields |
| `external_raw/Mesh Block Counts, 2021.xlsx` | ABS counts used during extraction |
| `processed/model_dataset.xlsx` | Approved 49-site modelling dataset |
| `templates/model_dataset_template.xlsx` | Preserved original modelling workbook |
| `templates/prediction_output_template.xlsx` | 100-location comparison template; predictions remain blank until a run |
| `processed/comparison_sites.csv` | 100 verified site/coordinate/road/source-row links for comparison enrichment |
| `raw/` | Client and road sources for research, matching and validation |
| `external_raw/` | Dated external source files and local research caches |
| `cache/`, `tmp/` | Local scratch data; ignored by Git |

Prediction reads the batch table and ABS source. It loads the model release from
`src/pedflow/modeling/releases/`; it does not retrain on `model_dataset.xlsx`.
After inference, it reads reconciled observations from the model dataset and
iRAP references from `raw/`. These comparison values never become model features.
Generated results belong in `outputs/predictions/<run>/`.

Preserve original sources and approved datasets. Add source files only when needed
by a documented workflow and authorised for team sharing; record source, date and
licence. Keep credentials, raw street images and disposable caches out of Git.

See [data contracts](../docs/01_data_preparation/haoqi-shared_data_tables.md) for
field definitions and the shared prediction output schema.
