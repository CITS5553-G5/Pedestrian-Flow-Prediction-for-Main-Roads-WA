# Raw client sources

Obtain client data through the agreed private handover and place it locally at the paths below. Preserve the filenames, worksheet names and source contents. These files are ignored by Git for new additions; do not upload them to the public repository or overwrite them with predictions.

The current data-audit notebook, `01_data_preparation/01_model_dataset_etl_reconciliation.ipynb`, requires these three files in `data/raw/`:

| Local path | Purpose |
| --- | --- |
| `data/raw/Ped_iRAP_merged.csv` | Client numeric pedestrian references and observed-count comparisons |
| `data/raw/AusRAP Data - Words - MSDS.xlsx` | Road segments, coordinate linkage and original categorical pedestrian bands |
| `data/raw/Road_Network.csv` | Road-number and SLK validation |

The audit also requires the separately supplied reviewed workbook `data/processed/model_dataset.xlsx`, with its `Model_Data` worksheet. Model-development notebooks use this workbook for training. The current audit validates the reviewed table and creates a candidate copy; it does not fully rebuild the training table from raw surveys.

For review of the original survey evidence, retain the original workbooks under `data/raw/Obs Count Data/`, preserving these batch folder names:

```text
250303 South West Vulnerable Road Users RESULTS/
250341 Regional Surveys - Kimberley RESULTS/
260335 Vulnerable Users RESULTS/
```

Keep the client's original processing and linkage scripts in `data/raw/R scripts for process and linkage/` when that historical processing needs to be reviewed. The original workbooks and scripts are optional audit evidence for the current notebook, not inputs to formal prediction. The `.fst` copy and the `SS_all_index` / `ST_all_index` workbooks are not required by the current audit or prediction workflow.

To run predictions with the released model, none of the client files in `data/raw/` or the training workbook is required. Prepare your own input in `data/processed/` using `data/templates/batch_input_template.xlsx`, replacing its example rows with your locations. Keep `data/templates/prediction_output_template.xlsx`, the released model JSON and prediction configurations available. The workflow also needs the local ABS workbook and Main Roads SLK snapshot described in the [prediction setup](../../README.md#runtime-configuration), plus your API credentials in `.env`. Prediction results are generated locally in `outputs/`.
