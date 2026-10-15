# Reviewed data-preparation outputs

| File | Purpose |
| --- | --- |
| [model_dataset_candidate.xlsx](model_dataset_candidate.xlsx) | Candidate workbook produced by the reconciliation notebook for review |
| [internal_sample_map.html](internal_sample_map.html) | Interactive map of the surveyed modelling locations |

The candidate workbook is separate from the authoritative `data/processed/model_dataset.xlsx`. Generating or reviewing the candidate does not approve replacement of that dataset. The [data contracts](../../docs/01_data_preparation/haoqi-shared_data_tables.md) define the modelling targets, stable site IDs and prediction inputs.

The [preparation notebook and map utility](../../01_data_preparation/README.md) document generation. Run `python 01_data_preparation/01_view_sample_map.py --write-only` from the repository root to regenerate the HTML without opening a browser. The map needs internet access for its Leaflet library and basemap tiles. Neither output is an input required for new-location prediction.
