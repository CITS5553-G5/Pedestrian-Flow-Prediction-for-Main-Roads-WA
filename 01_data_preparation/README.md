# Data preparation

The [reconciliation notebook](01_model_dataset_etl_reconciliation.ipynb) prepares and audits the 49-site modelling dataset. It verifies the authoritative `data/processed/model_dataset.xlsx` and creates a separate candidate workbook for review rather than overwriting the approved data.

The [sample-map utility](01_view_sample_map.py) reads the approved model dataset and writes the reviewed map under `06_outputs/01_data_preparation/`. Run `python 01_data_preparation/01_view_sample_map.py --write-only` from the repository root to regenerate the HTML without opening a browser. The interactive basemap needs internet access for map tiles and Leaflet.

Use the [shared data contracts](../docs/01_data_preparation/haoqi-shared_data_tables.md) for authoritative dataset roles, keys, target definitions and prediction inputs. Operational prediction uses the maintained [batch template](../data/templates/batch_input_template.xlsx); the survey model dataset is not a requirement for new-location inference.
