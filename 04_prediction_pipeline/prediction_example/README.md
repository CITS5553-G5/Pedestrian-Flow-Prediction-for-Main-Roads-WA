# Released-model prediction example

Operational prediction accepts any positive number of locations, determined by the submitted input table. This directory is one saved-feature demonstration; its sample size does not prescribe the size of another prediction batch.

This example contains ten locations, predictions from `pedestrian-linear-v1`, and existing AusRAP references. The workbook has 29 output columns. All ten references match; nine rows are `predicted` and one is `predicted_with_warning` because an imagery warning is retained from the original extraction. Observed fields are blank and no MAE/RMSE is calculated.

The three model features, context diagnostics and imagery warnings were saved by an earlier extraction completed on 28 September 2026 at 02:42:06 UTC. Model inference and local AusRAP matching were rerun for this delivery. This is an offline saved-feature replay, not a fresh imagery or ABS run. Predictions match the saved final-model results within `1e-9`; feature values are unchanged.

| File | Contents |
| --- | --- |
| [predictions.xlsx](predictions.xlsx) | `Prediction_Output`, `Features` and English `Metadata` |
| [input_locations.csv](input_locations.csv) | The ten location inputs, with no observed counts |
| [predictions.manifest.json](predictions.manifest.json) | Current model/reference fingerprints, matching rows and original feature timestamp |
| [verification.json](verification.json) | Output checks and workbook SHA-256 |
| [evidence/saved_run.json](evidence/saved_run.json) | Portable source tables and original run metadata, including original workbook/manifest hashes |

After [setup](../../docs/SETUP.md), reproduce into a new empty directory from the repository root:

```bash
python tools/replay_prediction_example.py --output-directory outputs/predictions/example_reproduction
```

The replay requires the delivered feature snapshot, model release, current workflow/configuration files, local Main Roads SLK snapshot and AusRAP Words workbook. It makes no external service requests and does not require the archived old output directories. It deliberately checks that the configured model and feature recipe still match the saved snapshot.

For new locations or refreshed imagery, use `pedflow-predict` with your prepared input as described in the [run guide](../../docs/04_prediction_pipeline/prediction_workflow.md). Replace, add or remove template rows for any positive batch size. The same layout supports surveyed sites, unknown sites or any mixture, with no required group counts. Optional observations come only from the submitted input. Production always uses the final model; the separate [49-site comparison](../irap_comparison/comparison_report.md) uses OOF validation predictions.
