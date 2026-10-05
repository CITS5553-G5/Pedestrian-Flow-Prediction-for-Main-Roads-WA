# Analytical report evidence

The [PDF analysis report](../../analysis_report.pdf) adds six analytical figures and a full 49-site appendix to the comparison. The [comparison notes](../../comparison_report.md) and [Excel workbook](../../irap_comparison.xlsx) document the methods and results.

The report examines observed-versus-estimated relationships, paired site wins, error distributions, signed bias, flow strata, influential sites and road-level omission diagnostics. It uses the reviewed OOF predictions. It neither invokes the released model nor changes production outputs or training data.

| File | Contents |
| --- | --- |
| [summary_metrics.csv](summary_metrics.csv) | MAE/RMSE, median and 90th-percentile absolute error, mean signed error, error thresholds and concentration of squared error |
| [site_diagnostics.csv](site_diagnostics.csv) | All 98 site-direction rows with original eligibility, signed/absolute errors and paired absolute-error gain |
| [flow_strata.csv](flow_strata.csv) | Descriptive results below 50 and at least 50 observed pedestrians/hour; not pre-specified validation subgroups |
| [figure_source_data.csv](figure_source_data.csv) | Exact eligible site IDs and observed/model/reference values for the scatter plots |
| [influence_diagnostics.json](influence_diagnostics.json) | Site wins, individual site/road omission ranges, equal-road weighting and omission of the two largest site gains |
| [analysis_manifest.json](analysis_manifest.json) | Input hashes, original Excel chart ranges, package versions, builder hash and report hashes |
| [verification.json](verification.json) | Independent reconciliation, source preservation, English text, PDF structure and visual checks |

Gain is `abs(existing - observed) - abs(model - observed)`, so positive favours the model. The main statistics remain site-weighted on 45 crossing / 43 along-road sites. Equal-road weighting first averages errors inside each road and then averages the road means. Omission checks summarise the saved predictions after excluding records; they do not refit a model. Removing the largest gains is an explicitly post-hoc stress test, not a replacement headline score or a confidence interval.

The delivered PDF is a reviewed static report. Supporting evidence and the historical generation manifest record source data, package versions and the original builder hash. The report-generation script is not included, so no report-regeneration command is provided. The earlier HTML edition is not part of the current delivery.

The original generation checked three fingerprint-pinned scientific comparison tables, workbook values, native chart ranges and primary metrics before rendering. If those inputs change, revise and review the analysis before issuing a new report edition.

The native Excel charts use `Errors!O:R` for crossing and `Errors!T:W` for along-road. Each group contains observed, model OOF, recoded existing estimate and an equality series repeating the observation. The report verifies every plotted input and the native XY references, then redraws the same pairs in separate method panels. The equality line is not a fitted trend.

All eight PDF pages were rendered and visually reviewed with embedded fonts. Numeric checks are independent of the page layout. No new live feature extraction, full-network prediction, refitted correction sensitivity analysis or external validation is implied by this report.
