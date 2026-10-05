# Optional research evaluation reproduction

These notes are for developers reproducing the historic OOF comparison. Customers can read the delivered reports and run `pedflow-predict` without this procedure. Production inference does not read the OOF CSV, refit a model or check the historical survey-input hashes.

The evaluation command reads saved road-grouped out-of-fold predictions. It compares them with observed counts and the existing recoded iRAP estimates, using the pinned preflight exclusions. It does not create a fresh cross-validation run.

From a project root containing the reviewed research snapshot, the optional command is:

```bash
python -m pedflow.evaluation --output-directory outputs/evaluation/comparison_reproduction
```

It requires the reviewed training workbook, saved OOF CSV, client merged CSV, AusRAP Words workbook, pinned preflight audit and the six original survey workbooks listed in that audit. These materials are separate from the customer prediction inputs.

The SHA-256 checks ensure research reproduction uses the files from the documented snapshot. Excel formatting or metadata edits also change the file hash. On 4 October 2026 the active `model_dataset.xlsx` differed in file bytes from the pinned snapshot, while its `Model_Data` cell values matched the Git HEAD snapshot checked during review. The command therefore stops for the active workbook. Using the reviewed original bytes in an isolated temporary root reproduced the existing 45-crossing / 43-along-road comparison.

To reproduce those historical results, obtain the exact research snapshot matching `preflight_audit.json`. If deliberately changing research inputs, repeat the preflight and review the resulting evidence rather than bypassing checks or relabelling current files as the historical snapshot. This is optional developer work, not a prerequisite for customer prediction or reading the reports.

Production also checks its saved model and imagery recipe automatically. Those checks concern inference compatibility, independently of the historical evaluation hashes, and require no manual hash maintenance by customers.
