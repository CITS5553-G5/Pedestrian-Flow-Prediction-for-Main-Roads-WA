# Raw source evidence

The approved source files below are versioned for the documented research and reference workflow. Preserve source contents and do not overwrite them with prediction results.

| File | Purpose |
| --- | --- |
| `Ped_iRAP_merged.csv` | Compact pedestrian references and observed-count reconciliation |
| `AusRAP Data - Words - MSDS.xlsx` | Road segments, original categorical pedestrian bands and operational AusRAP reference matching |
| `Road_Network.csv` | Road-number and SLK validation |

The [reconciliation notebook](../../01_data_preparation/01_model_dataset_etl_reconciliation.ipynb) also requires the reviewed `data/processed/model_dataset.xlsx` and its `Model_Data` worksheet. It audits the approved table and creates a separate candidate copy; it does not claim to rebuild every target from original survey files absent from a clone. Model-development notebooks use the separate reviewed modelling workbook for training.

Original survey workbooks remain local under `Obs Count Data/`, preserving these batch folder names:

```text
250303 South West Vulnerable Road Users RESULTS/
250341 Regional Surveys - Kimberley RESULTS/
260335 Vulnerable Users RESULTS/
```

Original processing and linkage scripts belong under `R scripts for process and linkage/`. These original workbooks and scripts are Git-ignored and supplied through approved project storage. They are optional for the current reconciliation notebook but required when a particular historical audit explicitly calls for them. The `.fst` copy and the `SS_all_index` / `ST_all_index` workbooks are not required by the current notebook or prediction workflow.

The [historical evaluation guide](../../docs/05_model_evaluation/reproduction.md) identifies the exact research snapshot and six survey workbooks needed for strict provenance verification. The [preflight audit](../../04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json) records relative evidence paths and fingerprints.

For new-location prediction, prepare a batch using the [input contract](../processed/README.md). Model inference does not require the training workbook, merged survey CSV or original survey workbooks. The workflow uses the AusRAP Words workbook after inference to attach existing reference values; those values are not predictors. ABS counts, the Main Roads SLK snapshot, model/configuration files, output template and live service credentials have separate requirements in the [project setup](../../README.md#runtime-configuration). New runs write to Git-ignored `outputs/`.
