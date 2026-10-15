# Source snapshot scripts

[download_road_slk.py](download_road_slk.py) downloads the complete public Main Roads WA measured road-line layer used for local road/SLK matching. It retrieves road numbers, SLK measures, carriageways and measured geometry; it does not read or transmit prediction locations and does not download pedestrian-flow estimates.

Run from the repository root with Python 3.11 and internet access:

```bash
python scripts/download_road_slk.py
```

The script uses Python's standard library. It paginates the source, validates measured vertices and source coverage, creates local SQLite indexes and compresses the result to `data/external_raw/main_roads_slk/road_slk.sqlite.gz`. A completed download replaces that snapshot; intermediate files use `.part` suffixes. Preserve the existing reviewed snapshot separately when a recorded run depends on it.

Review source changes before adopting a refreshed snapshot. Record its date and fingerprint, and rerun the relevant [location checks](../tests/README.md) before using it for new batches. The [external-data guide](../data/external_raw/README.md) records source attribution and the delivered snapshot. Model release, workbook reproduction and saved-feature replay utilities are documented separately under [tools](../tools/README.md).
