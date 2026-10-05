# Historical OOF evaluation

This module reproduces the reviewed survey comparison from saved road-grouped out-of-fold (OOF) predictions, observed targets and existing recoded AusRAP references. It does not load the final prediction model, retrain models or call imagery/ABS services. Operational prediction runs independently through `pedflow-predict`.

| File | Responsibility |
| --- | --- |
| [irap.py](irap.py) | Validate source fingerprints and keyed source tables, apply reviewed eligibility rules, assemble paired errors and calculate comparison metrics |
| [__main__.py](__main__.py) | Parse research-root/audit/output arguments and export CSV, JSON, manifest and summary |
| [__init__.py](__init__.py) | Identify the evaluation package |

From a repository root containing the exact reviewed research snapshot:

```bash
python -m pedflow.evaluation --output-directory outputs/evaluation/comparison_reproduction
```

The output directory must be new or empty. `--project-root` selects an isolated research root, and `--audit` selects an audit record. The default audit is `04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json`. Required inputs include the fingerprint-matched model dataset, saved OOF predictions, merged pedestrian-reference CSV, AusRAP Words workbook and six original survey workbooks recorded by the audit.

The active reformatted model dataset does not match the original workbook file hash. This command therefore requires the reviewed original snapshot even when `Model_Data` values are equivalent. The [reproduction guide](../../../docs/05_model_evaluation/reproduction.md) explains this boundary. Retain the checks; a changed input requires a new reviewed preflight rather than relabelling historical evidence.

Exports are `site_comparison.csv`, `paired_errors.csv`, `metrics.csv`, `comparison.json`, `manifest.json` and `comparison_report.md`. All 49 sites remain visible. The reviewed paired metrics use 45 crossing and 43 along-road sites, with identical eligible samples for both methods within each direction. Missing references stay missing; zero is a valid count. [Protocol details](../../../docs/05_model_evaluation/irap_comparison_protocol.md) and [delivered results](../../../04_prediction_pipeline/irap_comparison/README.md) describe exclusions and interpretation limits.
