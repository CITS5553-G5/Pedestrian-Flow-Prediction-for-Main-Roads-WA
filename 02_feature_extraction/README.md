# Stage 2 feature extraction

Shared source-specific notebooks are stored in `context/` and normally use `02_<sequence>_<member>_<topic>.ipynb`. Their sequence numbers identify parallel data-source work; they are not execution dependencies unless a notebook explicitly documents one.

| Notebook | Purpose |
| --- | --- |
| `context/02_01_haoqi_abs_mesh_block_sa1.ipynb` | ABS Mesh Block and SA1 context |
| `context/02_03_haoqi_pta_stops.ipynb` | Public Transport Authority stop proximity |
| `context/02_04_haoqi_wa_health_establishments.ipynb` | WA health-establishment proximity |
| `context/02_05_haoqi_wa_education_schools.ipynb` | WA school proximity |
| `context/02_07_haoqi_microsoft_building_footprints.ipynb` | Building-footprint density and coverage |
| `context/02_08_haoqi_google_places_aggregate_poi.ipynb` | Counts of selected destination categories around each site |

A short team-facing summary of the extracted fields is available in `docs/02_feature_extraction/haoqi-feature_summary.md`. Detailed source research, personal implementation notes and explicitly excluded experiments remain local.

Reviewed, reusable feature tables belong under `06_outputs/02_feature_extraction/`. The Google Places Aggregate workbook is an exception: it is a temporary API-derived cache, is excluded from Git, and must not be treated as a durable shared output. The notebook documents its retention and regeneration rules.

The shared `02_feature_extraction.py` file is the future integration entry point. Personal notebook work should be moved into it only after team review and validation.

Local-only notebooks are excluded through `.gitignore` and therefore do not appear in this shared index.
