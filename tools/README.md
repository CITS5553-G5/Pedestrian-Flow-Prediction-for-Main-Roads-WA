# Project utilities

## Survey sample map

Run the following command from the project directory:

```bash
python3 tools/view_sample_map.py
```

The script reads `data/processed/model_dataset.xlsx`, regenerates `outputs/internal_sample_map.html`, starts a local server and opens the English interactive map in the default browser. The terminal remains open while the map is available; press `Ctrl+C` to stop the server.

The map uses OpenStreetMap tiles so that city, suburb and road labels remain visible when zooming. An internet connection is required for the basemap and Leaflet JavaScript library. No API key is required.

Use `python3 tools/view_sample_map.py --write-only` when only the HTML file should be regenerated without opening a browser or starting the local server.
