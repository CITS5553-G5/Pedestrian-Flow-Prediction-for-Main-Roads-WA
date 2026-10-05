# Prediction and comparison delivery

This folder contains the reviewed comparison results and a reproducible prediction example. The operational pipeline is implemented in `src/pedflow`; run new batches using the [prediction guide](../docs/04_prediction_pipeline/prediction_workflow.md).

| Deliverable | Purpose |
| --- | --- |
| [49-site comparison workbook](irap_comparison/irap_comparison.xlsx) | Observed counts, saved road-grouped OOF model predictions, existing AusRAP estimates, paired errors and charts |
| [Data analysis report (PDF)](irap_comparison/analysis_report.pdf) | Eight-page analysis with six figures, paired errors, influential cases and all 49 site values |
| [Comparison index](irap_comparison/README.md) | Workbook, reports, evidence and reproduction boundaries |
| [Comparison method and delivery notes](irap_comparison/comparison_report.md) | Results, source meanings, exclusions and workbook behaviour |
| [Analytical evidence](irap_comparison/evidence/analysis/README.md) | Derived statistics, chart lineage and checks for the delivered report |
| [Comparison evidence](irap_comparison/evidence/README.md) | Machine-readable results, source fingerprints and reviewed matching audit |
| [Prediction example](prediction_example/README.md) | Ten saved-feature predictions using the released model, with AusRAP references and no accuracy metrics |
| [Handover](../docs/HANDOVER.md) | Current implementation, required inputs, testing and remaining work |

The comparison workbook is an internal validation result from model development. The prediction example uses the final released model. A production batch does not switch between OOF and final-model predictions based on whether a location was surveyed.

New unreviewed prediction runs use the Git-ignored `outputs/` directory. The delivered PDF is a reviewed static report; workbook and historical evaluation reproduction have separate dependencies described in the comparison index.
