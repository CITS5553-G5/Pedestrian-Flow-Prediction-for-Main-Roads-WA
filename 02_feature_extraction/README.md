# Stage 2 feature extraction

Shared source-specific notebooks are stored in `context/` and normally use `02_<sequence>_<member>_<topic>.ipynb`. Their sequence numbers identify parallel data-source work; they are not execution dependencies unless a notebook explicitly documents one.

| Notebook | Purpose |
| --- | --- |
| `context/02_01_haoqi_abs_mesh_block_sa1.ipynb` | ABS Mesh Block and SA1 context |
| `context/02_03_haoqi_pta_stops.ipynb` | Public Transport Authority stop proximity |
| `context/02_04_haoqi_wa_health_establishments.ipynb` | WA health-establishment proximity |
| `context/02_05_haoqi_wa_education_schools.ipynb` | WA school proximity |
| `context/02_07_haoqi_microsoft_building_footprints.ipynb` | Building-footprint density and coverage |
| `context/02_09_haoqi_overture_places.ipynb` | Food/drink and shopping places within 500 m |

A short team-facing summary of the extracted fields is available in `docs/02_feature_extraction/haoqi-feature_summary.md`. Detailed source research, personal implementation notes and explicitly excluded experiments remain local.

Reviewed, reusable feature tables belong under `06_outputs/02_feature_extraction/`. The Google Places Aggregate experiment was excluded from modelling by the recorded UWA project decision. Its pre-exclusion notebook, code and outputs are preserved only in `../07_Archive/20260908_google_places_aggregate_poi_experiment/` and must not be restored to the active workflow without a new documented UWA decision.

The formal Stage 2 workflow is entirely under `src/pedflow/context/`.
`workflow.py` coordinates the run and `sources/` contains the six approved sources
listed above plus an explicit guard for the excluded Google experiment. The numbered Stage 2 directory contains notebooks and team-facing
documentation only; it does not maintain a second executable workflow. The PTA
source is the Data WA PTA-001 stop layer, not the Transperth GTFS timetable feed.

Install the project package in the supported Python 3.11 environment before using
the entry point:

```bash
python -m pip install -r requirements.txt
python -m pip install -e .
python -m pedflow.context --list-sources
```

The equivalent installed command is `pedflow-context --list-sources`. Both commands
execute the same `src/pedflow` package entry; they are not separate implementations.

The default configuration is `configs/context_features_v1.json`. It reads
`data/templates/batch_input_template.xlsx`, enables the six approved context sources and writes
generated files under ignored `outputs/context_features/`. Use `--input` and
`--output-directory` to run another batch without editing the configuration. The
reviewed 49-site training feature table remains
`06_outputs/02_feature_extraction/02_00_haoqi_context_features.xlsx`.

The formal 49-site Overture source table is
`06_outputs/02_feature_extraction/02_09_haoqi_overture_places_features.xlsx`.
It remains an independent table keyed by `site_id`; the source notebook does not
rewrite `model_dataset.xlsx` or silently replace the previously reviewed combined
context snapshot.

Local-only notebooks are excluded through `.gitignore` and therefore do not appear in this shared index.
