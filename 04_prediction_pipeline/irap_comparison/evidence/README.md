# Comparison evidence

These reviewed files accompany the English comparison workbook and report. Paths inside provenance records are relative to the repository root unless explicitly identified as historical runtime paths.

| File | Purpose |
| --- | --- |
| [site_comparison.csv](site_comparison.csv) | 49 sites and 19 machine-named comparison fields |
| [paired_errors.csv](paired_errors.csv) | 98 site-direction rows with eligibility and both methods' errors |
| [metrics.csv](metrics.csv) | Paired sample sizes, MAE and RMSE for both methods and directions |
| [comparison.json](comparison.json) | Workbook source data and current relocated manifest; unavailable values are null |
| [manifest.json](manifest.json) | Validated input fingerprints, OOF basis, eligible sample IDs and current audit location |
| [preflight_audit.json](preflight_audit.json) | Immutable reviewed 3 October audit: matched source rows, original category sets, interval endpoints and six survey evidence fingerprints |
| [original_verification.json](original_verification.json) | Historical workbook verification; its workbook hash identifies the original snapshot |
| [original_workbook_checks.json](original_workbook_checks.json) | Historical formula and chart checks |
| [delivery_verification.json](delivery_verification.json) | Checks and final workbook hash for this English delivery |

The source audit intentionally retains its original schema/template fingerprints. It must not be rewritten to imply the current production template was the one used on 3 October. The evaluation loader validates the four scientific source tables and six survey evidence files. Delivery-only changes to the template, language and paths do not change those data.

Historical workbook/build snapshots are not needed to read the reviewed results or use the maintained workbook builder. Strict source-provenance verification requires the exact research snapshot and original survey workbooks described in the [reproduction guide](../../../docs/05_model_evaluation/reproduction.md). Original survey evidence is supplied through approved project storage; it is not included in a Git clone.
