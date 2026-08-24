# Data preparation utilities

## Model dataset ETL and reconciliation audit

Open `01-haoqi-01-model-dataset-etl-reconciliation.ipynb` to review the complete, read-only preparation flow for the 49-site modelling dataset. Each explanation is provided first in English and then in Chinese. The notebook reads the current source tables, reproduces the documented reconciliation and quality checks, and verifies that `data/processed/model_dataset.xlsx` is unchanged. It does not generate or overwrite the shared workbook.

## Survey sample map

Run the following command from the project directory:

```bash
python3 01_data_preparation/view_sample_map.py
```

The script reads `data/processed/model_dataset.xlsx`, regenerates `outputs/internal_sample_map.html`, starts a local server and opens the English interactive map in the default browser. The terminal remains open while the map is available; press `Ctrl+C` to stop the server.

The map uses OpenStreetMap tiles so that city, suburb and road labels remain visible when zooming. An internet connection is required for the basemap and Leaflet JavaScript library. No API key is required.

Use `python3 01_data_preparation/view_sample_map.py --write-only` when only the HTML file should be regenerated without opening a browser or starting the local server.
