# Reviewed feature tables

These files support model-development research. Context workbooks use one row per `site_id`; join them by that key rather than row order. The [feature definitions](../../docs/02_feature_extraction/haoqi-feature_summary.md) describe units, cleaning, spatial methods and limitations.

| File | Source or role |
| --- | --- |
| [02_00_haoqi_context_features.xlsx](02_00_haoqi_context_features.xlsx) | Combined reviewed Context features |
| [02_01_haoqi_abs_mesh_block_sa1_features.xlsx](02_01_haoqi_abs_mesh_block_sa1_features.xlsx) | ABS Mesh Block and SA1 features |
| [02_03_haoqi_pta_stops_features.xlsx](02_03_haoqi_pta_stops_features.xlsx) | Public-transport stop proximity |
| [02_04_haoqi_wa_health_features.xlsx](02_04_haoqi_wa_health_features.xlsx) | Health-establishment proximity |
| [02_05_haoqi_wa_education_features.xlsx](02_05_haoqi_wa_education_features.xlsx) | School proximity |
| [02_07_haoqi_microsoft_building_footprints_features.xlsx](02_07_haoqi_microsoft_building_footprints_features.xlsx) | Building-footprint count and coverage |
| [02_09_haoqi_overture_places_features.xlsx](02_09_haoqi_overture_places_features.xlsx) | Nearby food/drink and shopping places |
| [ausrap_with_gemini_features (3).csv](ausrap_with_gemini_features%20%283%29.csv) | Supplied candidate imagery features; original extraction provenance is incomplete |

The six source-specific Context notebooks are indexed in the [feature-extraction workspace](../../02_feature_extraction/README.md). Regeneration requires each notebook's matching source snapshot and settings; some research snapshots are stored outside Git. Update generating code and reviewed outputs together when values or schemas change.

The selected production model uses only the simplified ABS category and two imagery features. Routine prediction extracts features for the submitted locations through `src/pedflow/`; it does not join these research workbooks to an arbitrary new batch. The supplied imagery CSV is research evidence rather than independently verified ground truth. Google Places Aggregate fields remain excluded from active modelling.
