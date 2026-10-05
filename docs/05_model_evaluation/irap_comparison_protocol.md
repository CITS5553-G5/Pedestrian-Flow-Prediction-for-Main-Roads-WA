# Model versus existing reference: comparison protocol

Protocol `irap_comparison_protocol_v1`; category rule `positive_upper_bound_v1`; evaluation schema `survey_comparison_v1`. Reviewed 3 October 2026; English delivery edition 4 October 2026.

## Objective and sources

Compare corrected observed peak-hour counts with saved linear-regression out-of-fold predictions and the customer's existing recoded AusRAP estimates. The [result report](../../04_prediction_pipeline/irap_comparison/comparison_report.md) presents the completed comparison. The [production reference contract](../04_prediction_pipeline/ausrap_reference.md) describes inference at arbitrary locations, which computes no accuracy metrics.

| Component | Authoritative source | Join |
| --- | --- | --- |
| Observations | `data/processed/model_dataset.xlsx`, `Model_Data` | Unique `site_id` |
| Model estimates | `06_outputs/03_model_development/03_yashika_model_comparison/03_model_comparison_oof_predictions.csv` | `Model == Linear regression`, `site_id`, and `Target` |
| Existing counts | `data/raw/Ped_iRAP_merged.csv`, `Ped_Peak_Cross` and `Ped_Peak_Along` | `source_location_id` to client `ID` |
| Original categories and ranges | `data/raw/AusRAP Data - Words - MSDS.xlsx` | Reviewed source rows in the pinned audit |
| Coverage evidence | Six original survey workbooks for Broome and Carnarvon | Paths and hashes preserved in the audit |

Counts keep full numeric precision. Only the existing reference uses the client's category recoding; observations and predictions do not. Display rounding never changes classification, matching or error calculations. Duplicate keys, mismatched site sets, changed source hashes, changed observed targets, invalid predictions or eligibility drift cause an explicit failure.

## Paired samples and coverage

The detail table retains 49 sites and both directions. Crossing metrics use the 45 sites with an available existing reference. Along-road metrics use the same set minus `250341-01` and `260335-38`, yielding 43. Each method is evaluated against the same observations within each direction. Missing baselines at `250303-15`, `260335-31`, `260335-32` and `260335-40` stay blank, not zero.

For `250341-01` (Broome), three original workbooks label 15-minute observations `PEDESTRIAN SOUTH` and `PEDESTRIAN WALKWAY`. The Walkway diagram and reviewed imagery do not establish complete opposite-side coverage. Hourly EAST/WEST headings conflict with the primary 15-minute labels and are not sufficient to override them. Keep the existing along-road value (about 20.333333), but exclude it under `along_coverage_unconfirmed_south_walkway`. Crossing (about 8.333333) remains eligible.

For `260335-38` (Carnarvon), three workbooks label the along-road table `PEDESTRIAN WEST`; NORTHBOUND and SOUTHBOUND are two walking directions on that side. No independent opposite-side 15-minute table was found. Retain the corrected along-road count (about 18.333333), exclude it under `along_coverage_west_only`, and retain crossing (about 4.333333). Do not double the observation or impute the other side as zero.

Other sites' standard side headings rely on the preceding 147-workbook audit; this comparison did not visually re-review all 47 other sites. The observed combined-hour peak and the existing sum of side estimates need not represent the same peak moment. Evaluation filtering leaves the saved model fit unchanged.

## Matching and aggregation

Reproduce the customer baseline using identical road and SLK ±0.1 km overlap. Normalize reversed source intervals, retain Excel row numbers, use inclusive comparisons on original floating-point values, and apply no epsilon or rounding. All source carriageways are included; every source row is equally weighted, with no deduplication or length weighting. Result tolerance `1e-9` is for numeric verification only, not spatial selection.

This reproduces 45 of 45 available client means in both directions, using 2–8 source rows per site. At `250303-13` / `H009-170.3`, rows 73747–73749 yield along-road recodes 150, 78 and 150, with mean 126. The earlier epsilon-dependent value 132 is not used. Twelve sites span multiple carriageway labels. A future refined baseline must have a distinct version rather than silently replace this client-parity result.

There are 21 matched sites with one crossing category and 24 with mixed categories. Preserve a unique source category only when all categories agree. Otherwise leave the single-category field blank and list the category set. Do not substitute a mode, maximum or category inferred from the averaged recoded value.

For crossing, average lower and upper source-band endpoints separately. For along-road, add both side endpoints within each record before averaging. These derived ranges use the same source rows and weights as the recoded baseline. They are not statistical intervals or the min/max envelope across records. Missing required categories make the affected result unavailable; do not reduce the denominator by dropping them. Open upper bounds remain open.

The [reference contract](../04_prediction_pipeline/ausrap_reference.md) gives the full category and client-recoding tables. Positive continuous values use inclusive upper bounds; 0 is separate and 900 belongs to category 10. No epsilon or prior rounding is used. This project convention extends integer reference labels. Display bands are descriptive; this protocol does not compute a string-based interval hit rate or classification accuracy.

## Outputs, checks and unresolved scope

The 19-column evaluation table and 98-row error table explicitly record direction-specific eligibility. Metrics use those boolean fields, never inferred free text. `prediction_basis` is `road_grouped_oof`; final-model inference must not be mixed into these accuracy metrics. The workbook presents English display names; CSV retains machine field names. Along-road totals do not receive a single-side category.

The [pinned audit](../../04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json) records matching rows, category sets, endpoints, source hashes and six coverage-evidence workbooks. Its original template/schema fingerprints are historical; scientific source inputs remain pinned and are validated by the loader. The audit is preserved rather than rewritten during delivery cleanup.

Required checks cover source fingerprints, all 49 unique sites, identical paired method samples, 45/43 eligibility, zero versus blank, category boundaries, mixed categories, keyed rather than positional alignment, and 45-site client parity. The final workbook also requires formula/cache and chart-series verification.

Internal road-grouped cross-validation does not eliminate selection optimism because model and feature choice used these data. Refitting after excluding corrected sites `250341-04` and `260335-38` is outstanding; the along-road eligibility exclusions above do not replace it. Full-network prediction, external validation and service-coverage checks are separate work.
