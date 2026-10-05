# Pedestrian flow: model and existing AusRAP comparison

**Results: 3 October 2026. Delivery edition: 4 October 2026.** Protocol: `irap_comparison_protocol_v1`. Units: pedestrians per hour.

The model has lower MAE and RMSE than **Existing iRAP flow estimate (recoded)** on the same eligible observed sites in each direction. The evidence is an internal road-grouped cross-validation comparison, with 45 crossing sites and 43 along-road sites. It does not establish accuracy across the full road network.

## Results

| Direction | Paired sites | Model MAE | Existing estimate MAE | Model RMSE | Existing estimate RMSE |
| --- | ---: | ---: | ---: | ---: | ---: |
| Crossing | 45 | 15.4962 | 18.0463 | 29.9543 | 36.4778 |
| Along-road | 43 | 21.1725 | 52.4767 | 38.9263 | 74.7284 |

Relative to the existing recoded estimate, crossing MAE is 14.1% lower and crossing RMSE is 17.9% lower. Along-road MAE is 59.7% lower and RMSE is 47.9% lower. These are descriptive differences on this sample; no statistical significance claim is made.

MAE is the mean absolute difference from the observed count. RMSE is the square root of the mean squared difference and gives larger errors more influence. Both use unrounded counts and exactly the same eligible sites for both methods within each direction. Smaller is better. The metrics are retained from the completed evaluation; the operational prediction workflow does not calculate them.

## What is being compared

| Quantity | Origin | Interpretation |
| --- | --- | --- |
| Observed peak-hour flow | Corrected `Model_Data` targets in the modelling dataset | Survey observations, including their original spatial and temporal coverage |
| Model-predicted peak-hour flow | Saved linear-regression OOF predictions | For each site, the fitted fold model excluded that site's road group from training |
| Existing iRAP flow estimate (recoded) | Client `Ped_Peak_Cross` and `Ped_Peak_Along` fields | Client recoding and aggregation of AusRAP categories; not an official exact pedestrian count |

OOF means **out of fold**. During model development, roads were split into five groups. Each group was predicted using a model fitted to the other groups. The saved held-out predictions were combined into one validation table. The comparison does not invoke the final released model or retrain anything.

The production release, `pedestrian-linear-v1`, was fitted using all 49 training sites on 28 roads. It has the same selected model type and features, but its coefficients differ from those of individual validation folds. Running a surveyed location through the production pipeline produces a final-model prediction, which can differ from its OOF value even with identical features. The Python release preserves Yashika's saved model parameters; this delivery cleanup does not change them.

## Coverage and exclusions

All 49 sites remain in [the workbook](irap_comparison.xlsx) and [site_comparison.csv](evidence/site_comparison.csv). Four sites lack a usable existing baseline: `250303-15`, `260335-31`, `260335-32` and `260335-40`. Their reference fields remain blank, not zero. The remaining 45 sites form the crossing comparison.

The along-road comparison additionally excludes `250341-01` and `260335-38`. The former records South plus Walkway counts, without confirmed coverage of both road sides. The latter records West-side counts only. Their available values remain visible, but they do not contribute to along-road metrics. Crossing eligibility is unaffected. Counts are neither doubled nor filled with zero to manufacture a two-side observation.

Eligibility filtering does not change the original 49-site model fit. Refitting the selected modelling procedure after excluding corrected sites `250341-04` and `260335-38` remains a separate, outstanding sensitivity analysis.

## Categories, ranges and recoded counts

AusRAP stores estimated categories for road records. The iRAP manual supplies reference meanings for those categories. For example, category 3 corresponds to the integer band 6–25 pedestrians/hour. This is one coding system applied to the supplied data; a category value is not itself an exact count.

The client recodes categories 1–9 to `0, 3, 15, 38, 75, 150, 250, 350, 450`. The name **Existing iRAP flow estimate (recoded)** identifies this client-defined transformation. The model and observed counts remain their original numeric values; they are not replaced by these representative values.

Matching reproduces the client's road and SLK ±0.1 km method. Overlapping source rows have equal weight; carriageways are not filtered and records are not deduplicated. The along-road reference adds both sides within each record before averaging. All 45 available client baselines were reproduced to an absolute tolerance of `1e-9`.

For multiple matched records, displayed bands average lower and upper endpoints separately. Along-road bands first add both side endpoints. These are derived descriptive ranges, not official new categories or confidence intervals. Of 45 matched sites, 24 contain mixed crossing categories: the single original-category cell is blank and the notes list the category set. Their numeric baseline can still be available. Twelve sites span multiple source carriageway identifiers.

Observed and model crossing categories use the same project convention for continuous counts: zero is separate, then positive values use inclusive upper bounds of 5, 25, 50, 100, 200, 300, 400, 500 and 900. Values above 900 enter category 11. This resolves decimal and boundary cases without changing stored counts. It is a project extension of integer reference labels, not an additional official rule. Along-road totals are not assigned a single-side category.

## Reading the workbook

| Sheet | Contents |
| --- | --- |
| `Summary` | Paired sample sizes, formula-based MAE/RMSE, relative reductions and two observed-versus-estimated scatter charts |
| `Site_Comparison` | All 49 sites, 19 English-labelled fields, counts, categories, bands, eligibility and notes |
| `Errors` | All 98 site-direction rows, lookup-based counts and errors, plus frozen chart helper values |
| `Definitions` | English field meanings, units, source conventions and interpretation limits |

Each chart uses the eligible sample for its direction. The horizontal axis is observed flow; the vertical axis is estimated flow. Blue points show OOF predictions, orange points show the recoded existing estimate, and grey points mark equality. The chart helpers and categorical fields are snapshots. Regenerate the workbook after changing source values; editing cells alone will not refresh every derived display.

## Reproduction and traceability

The [evidence index](evidence/README.md) describes the CSV/JSON exports and source audit. The [comparison protocol](../../docs/05_model_evaluation/irap_comparison_protocol.md) specifies matching, continuous categories and exclusions. The audit is a preserved 3 October snapshot: some recorded template/schema fingerprints describe that earlier state and are not current production fingerprints. Its source observations, OOF predictions, client data and six survey evidence files remain unchanged.

After [environment setup](../../docs/SETUP.md), run from the repository root into a new empty directory:

```bash
python -m pedflow.evaluation --output-directory outputs/evaluation/comparison_reproduction
python -m pytest tests/unit/test_irap_comparison.py tests/integration/test_ausrap_client_parity.py -q
```

The default audit is now `04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json`. The evaluation CLI validates source hashes and exports CSV, JSON and an English summary. It requires the audit's six original survey workbooks for provenance validation, in addition to the model dataset, saved OOF CSV, client CSV and Words workbook. Those original survey files remain in approved local data storage; they are not silently reconstructed if absent.

The maintained [workbook builder](../../tools/build_comparison_workbook.mjs) takes the CLI result directory and an output directory. It requires Node.js with `@oai/artifact-tool` available. The [chart export repair](../../tools/repair_comparison_charts.py) fills native scatter-chart XY references if required by the exporter; it uses Python's standard library and openpyxl for read-only verification. These optional presentation tools are separate from model inference:

```bash
node tools/build_comparison_workbook.mjs outputs/evaluation/comparison_reproduction outputs/evaluation/comparison_workbook
python tools/repair_comparison_charts.py outputs/evaluation/comparison_workbook/irap_comparison.xlsx
```

The delivery verification checks unchanged source counts and predictions, formula caches, missing-value handling, native chart series and English-only cells. No fresh imagery, external service requests or model fit is part of this comparison.

## Limits of the conclusion

Feature and model selection used these survey data, so this is internal validation rather than an independent external test. Survey coverage, observation periods and peak definitions can differ from the existing reference. Multi-carriageway aggregation reproduces the client's baseline without proving identical physical coverage. The reduced paired samples also differ from the original 49-site model-selection metrics; their numbers should not be compared as if the samples were identical.

The 189,222 rows in the AusRAP source are source records, not a guarantee of that many unique, fully predictable locations. Whole-network prediction has not been run. At unknown sites without observations, differences between model and existing estimates are descriptive comparisons and cannot establish which estimate is accurate.

The reference category dictionary is the [iRAP Star Rating and Investment Plan Manual, version 1.5 (2024), pages 26 and 30–31](https://austroads.gov.au/__data/assets/pdf_file/0033/836295/iRAP_Star_Rating_and_Investment_Plan_Manual_English.pdf), checked during the original preflight. This does not establish the exact manual version used to code the customer's historical data or assert that it is the latest manual.
