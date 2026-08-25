# Data preparation utilities

## Model dataset ETL and reconciliation audit

Open `01_01_haoqi_model_dataset_etl_reconciliation.ipynb` to review the complete preparation flow for the 49-site modelling dataset. The notebook reads the current source tables, reproduces the documented reconciliation and quality checks, verifies that `data/processed/model_dataset.xlsx` is unchanged, and then generates `model_dataset_candidate.xlsx` in this same folder for direct review. The authoritative workbook is never overwritten.

## Survey sample map

Run the following command from the project directory:

```bash
python3 01_data_preparation/view_sample_map.py
```

The script reads `data/processed/model_dataset.xlsx`, regenerates `06_outputs/internal_sample_map.html`, starts a local server and opens the English interactive map in the default browser. The terminal remains open while the map is available; press `Ctrl+C` to stop the server.

The map uses OpenStreetMap tiles so that city, suburb and road labels remain visible when zooming. An internet connection is required for the basemap and Leaflet JavaScript library. No API key is required.

Use `python3 01_data_preparation/view_sample_map.py --write-only` when only the HTML file should be regenerated without opening a browser or starting the local server.
