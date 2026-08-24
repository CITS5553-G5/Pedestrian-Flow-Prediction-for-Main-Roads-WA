# Stage 2 feature notebooks

Personal notebooks use `02_<sequence>_<member>_<topic>.ipynb`. Their sequence numbers identify parallel feature-source work; they are not execution dependencies unless a notebook explicitly documents one.

| Notebook | Purpose |
| --- | --- |
| `02_01_haoqi_abs_mesh_block_sa1.ipynb` | ABS Mesh Block and SA1 context |
| `02_03_haoqi_pta_stops.ipynb` | Public Transport Authority stop proximity |
| `02_04_haoqi_wa_health_establishments.ipynb` | WA health-establishment proximity |
| `02_05_haoqi_wa_education_schools.ipynb` | WA school proximity |
| `02_07_haoqi_microsoft_building_footprints.ipynb` | Building-footprint density and coverage |

Source definitions and scientific limitations are documented under `docs/feature_sources/`. Generated feature tables belong under `outputs/02_imagery_features/` and are excluded from Git until the team deliberately promotes an output into an approved project dataset.

The shared `02_imagery_features.py` file is the future integration entry point. Personal notebook work should be moved into it only after team review and validation.

Local-only notebooks are excluded through `.gitignore` and therefore do not appear in this shared index.
