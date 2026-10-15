# Feature extraction

This folder retains research notebooks. Operational extraction and prediction are implemented in `src/pedflow`, with ABS as the production Context source and the reviewed imagery recipe supplying the selected image features. The [imagery guide](../docs/02_feature_extraction/imagery_integration.md) and [prediction run guide](../docs/04_prediction_pipeline/prediction_workflow.md) describe those entry points.

| Research notebook | Purpose |
| --- | --- |
| [ABS](context/01_haoqi_abs_mesh_block_sa1.ipynb) | Mesh Block and SA1 context |
| [PTA](context/03_pta_stops.ipynb) | Public Transport Authority stop proximity |
| [Health](context/04_wa_health_establishments.ipynb) | Health-establishment proximity |
| [Education](context/05_wa_education_schools.ipynb) | School proximity |
| [Buildings](context/07_microsoft_building_footprints.ipynb) | Building-footprint coverage |
| [Overture](context/09_overture_places.ipynb) | Food/drink and shopping places |
| [Original imagery research pipeline](imagery/Image_Feature_Extraction_Pipeline.ipynb) | Full original image retrieval, Gemini extraction, batch processing, exports and historical previews |
| [Reviewed imagery workflow](imagery/Run_Reviewed_Imagery_Workflow.ipynb) | Maintained shared implementation with concurrent extraction and checkpoints |

The [feature summary](../docs/02_feature_extraction/haoqi-feature_summary.md) explains reviewed candidate fields. Candidate-source research does not mean every feature is used in the selected model. The [reviewed feature tables](../06_outputs/02_feature_extraction/README.md) document source workbooks and join keys; research configurations remain in `configs/research/`. Production imagery uses the configuration-bound recipe in `src/pedflow/imagery/`.

Google Places Aggregate is excluded from the active modelling workflow by the recorded project decision. Its archived experiments are not needed for production. Personal working notes and superseded experiments remain outside the maintained delivery.

## Imagery notebook setup

The [imagery README](imagery/README.md) explains both notebooks. Before running either, copy the root `.env.example` to `.env` and enter your own `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY`. Both notebooks load credentials from `.env` or the process environment; keep working keys out of notebook source and saved output. The original research notebook exposes the complete process for inspection and generates new CSV files under Git-ignored `outputs/`. Its retained images and tables are historical outputs rather than a fresh execution.
