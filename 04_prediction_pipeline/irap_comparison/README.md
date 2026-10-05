# Survey model and AusRAP comparison

This directory contains the reviewed internal comparison of saved model OOF predictions and existing recoded AusRAP estimates against observed peak-hour pedestrian flows. It retains all 49 surveyed sites; paired metrics use 45 crossing and 43 along-road sites. Units are pedestrians/hour.

| File or directory | Purpose |
| --- | --- |
| [irap_comparison.xlsx](irap_comparison.xlsx) | Four-sheet workbook with observations, OOF predictions, references, paired errors and native charts |
| [comparison_report.md](comparison_report.md) | Methods, results, exclusions, source meanings and workbook behaviour |
| [analysis_report.pdf](analysis_report.pdf) | Eight-page illustrated diagnostic report with six figures and all 49 site values |
| [evidence](evidence/README.md) | Comparison tables, source audit, manifests and workbook checks |
| [Analytical evidence](evidence/analysis/README.md) | Derived statistics, figure source data and diagnostic verification |

The OOF predictions were saved during model development; this comparison does not use the final production model or calculate accuracy for new locations. Feature and model selection used the survey data, so the results are internal validation. The [released-model example](../prediction_example/README.md) separately demonstrates inference from saved features without accuracy metrics.

The delivered PDF is a reviewed static report; its generation script is not included. The Excel builder is available under [tools](../../tools/README.md) and requires a separately provisioned compatible `@oai/artifact-tool` runtime. Historical evaluation reproduction also requires the exact pinned research inputs and original survey evidence described in the [developer reproduction guide](../../docs/05_model_evaluation/reproduction.md). Reading these results or running operational prediction does not require that reproduction environment.
