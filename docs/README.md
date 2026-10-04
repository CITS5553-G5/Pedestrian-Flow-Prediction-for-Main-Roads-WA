# Documentation

Start with [setup](SETUP.md), then the [prediction run guide](04_prediction_pipeline/prediction_workflow.md).

For the current prediction-plus-reference workflow, read the [2026-10-04 AusRAP integration record (中文)](04_prediction_pipeline/ausrap_reference_integration_zh.md). The 29-column output is implemented and computes no accuracy metrics. The [2026-10-03 handoff record (中文)](handover/20261003_irap_comparison_handoff_zh.md) preserves the earlier decisions; its latest-status paragraph takes precedence over the historical planning snapshot.

The [iRAP comparison protocol (中文)](05_model_evaluation/irap_comparison_protocol_zh.md) records the completed preflight checks, direction-specific evaluation samples, continuous category rules and multi-segment aggregation for implementation.

The [49-site comparison results (中文)](05_model_evaluation/irap_comparison_results_20261003_zh.md) contain the completed paired MAE/RMSE comparison, workbook location, reproduction instructions and remaining scope.

| Reference | Purpose |
| --- | --- |
| [Workflow](END_TO_END_WORKFLOW.md) | Runtime modules and interfaces |
| [Module integration](MODULE_INTEGRATION_GUIDE.md) | Code and test requirements |
| [Data contracts](01_data_preparation/haoqi-shared_data_tables.md) | Shared datasets and formal prediction input/output tables |
| [Imagery](02_feature_extraction/imagery_integration.md) | Extraction, retry and recovery behaviour |
| [Model](03_model_development/selected_model_integration.md) | Selected features, release and R/Python verification |
