# Documentation

Start with the [delivery handover](HANDOVER.md), [prediction run guide](04_prediction_pipeline/prediction_workflow.md) and [reviewed results](../04_prediction_pipeline/README.md).

| Reference | Purpose |
| --- | --- |
| [Setup](SETUP.md) | Python environment and external data requirements |
| [Workflow](END_TO_END_WORKFLOW.md) | Runtime modules and interfaces |
| [Module integration](MODULE_INTEGRATION_GUIDE.md) | Code and test requirements |
| [Data contracts](01_data_preparation/haoqi-shared_data_tables.md) | Shared datasets and prediction input/output contracts |
| [Imagery](02_feature_extraction/imagery_integration.md) | Extraction, retry and recovery |
| [Model explanation](03_model_development/selected_model_explained.md) | Final-model coefficients, inputs and OOF versus production |
| [Detailed model explanation](03_model_development/selected_model_details.md) | Equations, worked examples, grouped validation and interpretation |
| [Model integration](03_model_development/selected_model_integration.md) | Release and R/Python verification |
| [AusRAP reference](04_prediction_pipeline/ausrap_reference.md) | Matching, category meanings, 29 output fields and limitations |
| [Comparison protocol](05_model_evaluation/irap_comparison_protocol.md) | Paired OOF evaluation rules and reviewed exclusions |
| [Research reproduction](05_model_evaluation/reproduction.md) | Optional historical evaluation, exact input snapshots and fingerprint requirements |
| [Data analysis report](../04_prediction_pipeline/irap_comparison/analysis_report.pdf) | Six figures analysing errors, influential sites and robustness, with a 49-site appendix |
| [Comparison notes](../04_prediction_pipeline/irap_comparison/comparison_report.md) | Reviewed results, source meanings, exclusions and workbook behaviour |
| [Workflow review](DELIVERY_REVIEW_20261004.md) | Dated findings, subsequent fixes and remaining verification limits |

Operational setup and prediction guides describe the maintained runtime. Research reproduction has separate snapshot requirements and is not a prerequisite for prediction. Use the dated handover and workflow review to distinguish completed checks from pending live-service validation.
