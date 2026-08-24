# Team data directory

Only intentionally selected files in this directory are versioned in the private team repository. A new file must be both authorised for team sharing and required by a documented project workflow before it is added. Access is restricted to approved project collaborators.

## Folder contract

- `raw/` contains the curated client/source inputs used for target checking, road matching and AusRAP feature linkage. Treat tracked source files as immutable.
- `external_raw/` contains selected dated snapshots of external/public datasets used by the feature pipeline. Preserve the source date, provider, licence and retrieval path. Public availability does not automatically authorise redistribution through this repository.
- `processed/` contains approved, reproducible project datasets. `model_dataset.xlsx` is the authoritative 49-site modelling foundation.
- `templates/` contains the Excel-only batch-input and prediction-output workbooks used by the project workflow.
- `cache/` and `tmp/` are local scratch areas and are excluded from Git.

The 147 macro-enabled observation workbooks are not routine project inputs because their site-level results have already been consolidated. They remain in approved archival storage outside the current Git tree and are needed only if the target aggregation must be independently reconstructed. Candidate datasets that have not been selected for the model are also excluded until a documented pipeline uses them.

All retained files are stored in ordinary Git. Git LFS is not required for the current curated dataset. A normal clone or pull downloads the source inputs and core tables directly.

Do not place API keys, access tokens, downloaded street imagery, fitted models, archival survey workbooks or disposable experiment outputs in this directory. Schema or source replacements should be reviewed by the team, especially before adding any file near GitHub's regular-Git size limit.

Before staging a new source snapshot, confirm its sharing permission, record its source and licence, identify the notebook or script that consumes it, and decide whether storing it in Git is preferable to reproducible download code. Do not use an unchecked `git add .` for data changes.

## Tracked data files

### Curated client and road sources

- `raw/Ped_iRAP_merged.csv` — compact client-derived target table used to check most observed pedestrian targets.
- `raw/Road_Network.csv` — statewide Main Roads road-number, SLK interval and network-element reference used for location resolution.
- `raw/AusRAP Data - Words - MSDS.xlsx` — AusRAP road-segment attributes used for segment matching and retained road-safety features.

### External feature sources

- `external_raw/Mesh Block Counts, 2021.xlsx` — ABS 2021 Mesh Block population/count source used by the demographic feature workflow.
- `external_raw/microsoft_building_footprints/2026-07-24/dataset-links.csv` — dated manifest recording the Microsoft building-footprint source links.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310122330.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310123103.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310130331.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310302031.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310302303.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310303320.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310320033.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310320102.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310320120.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.
- `external_raw/microsoft_building_footprints/2026-07-24/australia_tiles/310320313.csv.gz` — compressed Microsoft building-footprint tile required by the current WA site coverage.

### Model-development table

- `processed/model_dataset.xlsx` — authoritative Excel workbook containing Metadata followed by the 49 reconciled observation locations and targets.

### Batch and output templates

- `templates/batch_input.xlsx` — populated 100-location API test input, with 49 observed benchmarks and 51 reproducibly sampled new AusRAP-linked locations.
- `templates/prediction_output.xlsx` — prefilled 100-location comparison and Dashboard table; source context is populated and model prediction fields remain blank.
