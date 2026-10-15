# Local raw source data

All source files and subdirectories under `data/raw/` are Git-ignored. Only this README is versioned. Cloning or downloading the GitHub repository does not supply these data files. Obtain the required files through the agreed project handover and place them under the exact paths below before running a dependent workflow. Keep filenames, worksheet names and source contents unchanged; placing the files directly under `data/` does not satisfy code expecting `data/raw/`.

| Required local path | Used by |
| --- | --- |
| `data/raw/Ped_iRAP_merged.csv` | Data reconciliation, compact observed-count comparisons, historical OOF evaluation and applicable parity tests |
| `data/raw/AusRAP Data - Words - MSDS.xlsx` | Data reconciliation, road-segment linkage, historical evaluation, operational AusRAP reference matching and the offline prediction replay |
| `data/raw/Road_Network.csv` | Data reconciliation and road-number/SLK checks |

The [reconciliation notebook](../../01_data_preparation/01_model_dataset_etl_reconciliation.ipynb) requires all three files and the separately versioned `data/processed/model_dataset.xlsx` with its `Model_Data` worksheet. It audits the reviewed table and writes a candidate copy; it does not fully rebuild every target from unavailable original survey workbooks. Model-development notebooks use the processed modelling workbook and their own documented inputs.

## Original survey evidence

When reproducing an audit that requires the original surveys, restore the relevant workbooks under these batch directories:

```text
data/raw/Obs Count Data/250303 South West Vulnerable Road Users RESULTS/
data/raw/Obs Count Data/250341 Regional Surveys - Kimberley RESULTS/
data/raw/Obs Count Data/260335 Vulnerable Users RESULTS/
```

Original processing and linkage scripts belong under `data/raw/R scripts for process and linkage/`. These original workbooks and scripts are optional for the current reconciliation notebook but required when a particular historical audit calls for them. The `.fst` copy and the `SS_all_index` / `ST_all_index` workbooks are not required by the current reconciliation notebook or prediction workflow. They also remain local when retained.

The [historical reproduction guide](../../docs/05_model_evaluation/reproduction.md) identifies the exact research snapshot and six original survey workbooks used by strict provenance verification. The [preflight audit](../../04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json) records relative paths and fingerprints. Use the matching source versions rather than a different file with the same name.

## Prediction and replay dependencies

New-location model inference does not require `Ped_iRAP_merged.csv`, `Road_Network.csv`, the training workbook or original survey workbooks. The integrated workflow uses the local AusRAP Words workbook after inference to attach existing reference values; those values are not predictors. A missing or unreadable Words source is reported as `comparison_status=source_unavailable`, so prediction completeness must not be confused with reference coverage. Place that workbook at the path above to obtain the documented comparison fields. The delivered offline replay also requires the local Words source and will not reproduce the complete example from a clone without it.

ABS counts and the Main Roads SLK snapshot have separate requirements under [external data](../external_raw/README.md). Processed datasets, templates and reviewed research outputs retain their existing versioning policy. See [setup](../../docs/SETUP.md) and the [prediction run guide](../../docs/04_prediction_pipeline/prediction_workflow.md) for the remaining configuration and API keys. New runs write to Git-ignored `outputs/`; they must not overwrite raw sources.
