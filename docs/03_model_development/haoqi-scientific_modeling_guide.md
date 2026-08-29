# Scientific Modeling Guide for Pedestrian-Flow Prediction

Version: 0.1 (pre-modeling protocol)
Date: 2026-08-24
Scope: the current 49 approved survey sites and the five public contextual feature sources prepared by Haoqi

This protocol freezes the five durable feature tables available when it was written. The later Google Places Aggregate experiment is not part of this frozen specification because its output is a temporary local API cache. Adding it to a model comparison requires an explicit protocol revision before results are inspected.

## 1. Executive conclusion

The current data meet the minimum requirements for beginning modeling experiments, but they do not justify training a complex model and treating its score as evidence of generalization. The authoritative target table contains 49 independent sites. All five feature tables join one-to-one through `site_id`, with no missing sites or duplicate keys. The sample remains small and geographically uneven, some sites are very close to one another, and both targets are strongly right-skewed and influenced by a few high-flow sites. The primary design should therefore use separate models for the two targets, repeated grouped cross-validation constrained by roads and nearby sites, a regularized main model, and tightly controlled nonlinear challengers. Every preprocessing, tuning, and feature-selection step must occur within the training folds.

The primary targets are the continuous, non-negative variables `obs_peak_cross_ped_per_h` and `obs_peak_along_ped_per_h`. Although they originate from pedestrian counts, they are aggregated peak values after averaging the same period over three survey days and may be fractional. They should not be treated as raw Poisson counts or prematurely converted into categories. After the client and iRAP thresholds have been confirmed, categories may be derived from the continuous predictions as secondary outputs.

The five public contextual sources support a scientifically defensible Phase A model, but they do not by themselves complete the comparison required by the client. The client requires evidence that new features add value over existing variables and a comparison with iRAP estimates. The five current sources are contextual data; they do not yet include imagery-derived features or the full set of existing road variables in the main modeling table. Phase A is therefore the immediately executable five-source contextual model. Phase B is the fair comparison of an existing-variable baseline, new features, and their combination that is required for the final client conclusion.

## 2. Evidence scope and factual baseline

The combined client and university requirements are recorded in `04_Project_Resources/20260810_Integrated_Client_Requirements_and_University_Guidance.docx`. The authoritative targets and locations come from the `Model_Data` sheet in `03_Project/data/processed/model_dataset.xlsx`. The five candidate feature tables are stored in `03_Project/06_outputs/02_feature_extraction/`; their fields, source coverage, and limitations are documented in the corresponding notebooks and `03_Project/docs/02_feature_extraction/haoqi-feature_summary.md`. The template `03_Project/data/templates/prediction_output.xlsx` includes some iRAP categories, AADT, speed-limit, and area-type information for the observed sites. These fields can support later baseline comparisons, but the iRAP pedestrian-flow categories must not be treated as continuous ground truth or training labels.

The current checks show 49 unique `site_id` values and 49 unique `location_id` values. Every row has `qa_status = ready`, and every site has three survey days. The cross-road target has a median of 7.33 pedestrians/hour, a mean of 25.39, a maximum of 192.33, a skewness of 2.50, and one zero value. The along-road target has a median of 13.00, a mean of 39.87, a maximum of 349.67, and a skewness of 3.41. Their Pearson correlation is approximately 0.84 and their Spearman correlation is approximately 0.76. They are related but not interchangeable. Both targets should use the same validation folds for fair comparisons, while retaining separate output models. The sample is too small to make a multi-task neural network or another complex multi-output structure the preferred approach.

Spatial diagnostics also support grouped validation. Eight of the 49 sites have another surveyed site within 1 km, and the closest pair is approximately 0.21 km apart. Nine `road_no` values occur at more than one site, and one road contains 10 sites. A random row-level split could therefore place the same road or near-identical locations in both the training and test sets. The three survey batches contain 17, 7, and 25 sites and have different target distributions. `survey_batch_id` should not be a predictor for new locations, but it should define groups in transfer-sensitivity analysis.

## 3. Scientific questions

The main question is not which algorithm obtains the highest R-squared on 49 rows. The analysis should determine whether public contextual features predict cross-road and along-road peak pedestrian flow at new Western Australian road sites more accurately, consistently, and interpretably than simple baselines without seeing the test-site targets. It should also determine whether the five sources provide repeatable incremental improvement after existing client road information is included, and whether any improvement depends on a few influential sites, a survey batch, spatial neighbours, or recorded target corrections.

The intended inference population is limited to Western Australian road locations that resemble the 49 observed sites and can be processed by the same coordinate-to-feature pipeline. The current sample does not cover every environment in the state, and the notebooks identify a lack of genuinely representative central Perth sites. Final claims must remain within the support of the training data and must not state that the model applies unconditionally to every road in Western Australia.

## 4. Targets and modeling unit

One row represents one surveyed site, and `site_id` is the unique modeling key. The two primary targets are `obs_peak_cross_ped_per_h` and `obs_peak_along_ped_per_h`, both measured in pedestrians/hour. They must not be added into a single total-flow target, because the client requires separate outputs. The along-road target must not be duplicated into invented observations for the two sides of a road. The models may share processing logic, validation folds, and version identifiers, but the saved artifact should contain either two separate predictors or a lightweight pipeline with two explicitly independent regression heads.

Continuous prediction is the primary task, and all final predictions must be non-negative. A model trained on `log1p(y)` must return to the original unit with `expm1`, with only numerical-error negatives clipped to zero. This transformation must be fixed in the pipeline rather than changed after test results are examined. Poisson regression is not the default because the targets are fractional three-day aggregate peaks and are clearly overdispersed. Tweedie regression may be evaluated as a quasi-likelihood challenger for non-negative, right-skewed continuous outcomes, but its distributional form is a working assumption rather than a claim about the true data-generating process.

## 5. Feature roles and frozen first-round specifications

The first model must not receive every output column. Identifiers, names, status fields, error messages, and spatial codes are for joins and audits. Coordinates are for spatial grouping and support-domain checks rather than primary predictors. `road_no` is used to prevent leakage, and `survey_batch_id` is used for transfer sensitivity. Target-source and QA fields are retained for auditing. Any `obs_*`, `Ped_Peak_*`, or `max_Ped_Peak_*` field contains an outcome or outcome-derived information and must never be a predictor. iRAP pedestrian-flow categories are comparison baselines, not features.

The pre-specified `F_new_core` should remain compact to prevent post-hoc selection on 49 rows. It should contain `log1p(abs_mb_persons_per_sqkm_2021)`, `log1p(pta_nearest_active_stop_distance_m)`, `log1p(pta_active_stops_within_500m)`, `log1p(health_nearest_establishment_distance_m)`, `log1p(education_nearest_active_school_distance_m)`, and `ms_building_coverage_ratio_500m`. It should also contain a domain-defined collapsed Mesh Block category with three levels: `Residential`; `activity_destination`, combining Commercial and Education; and `other_non_residential`, combining Industrial, Transport, Parkland, and Primary Production. The resulting groups contain approximately 26, 13, and 10 sites, avoiding the original seven-category specification in which five categories have fewer than five observations. The original categories may be used only in a pre-declared sensitivity specification, not to choose a grouping after inspecting target performance.

The secondary `F_new_expanded` sensitivity specification may add `log1p(ms_building_count_500m)`, `pta_nearest_active_stop_type`, and `education_nearest_school_sector`. The current health establishment category/type and school `low_year`/`high_year` fields are too sparse or weakly interpretable for the default model. ABS dwelling and person raw counts have a Spearman correlation of approximately 0.93, while the two density measures have a correlation of approximately 0.94; they should not enter a small-sample linear model together without restriction. Building count and count density are exact rescalings, as are footprint area and coverage ratio, so only one field from each pair may be used. Building count and coverage ratio still have a rank correlation of approximately 0.86 and should coexist only when regularization and stability checks support them.

The client incremental-value comparison requires an `F_existing_minimal` specification. The prepared comparison table can provide at least `log1p(irap_vehicle_flow_aadt)` and a parsed numeric speed limit. `irap_area_type` contains 47 Urban and 2 Rural observations and cannot support a stable estimated effect; it should remain an audit field. If the team later selects more existing road features from AusRAP, the exact fields and directions must be frozen before model results are reviewed. All pedestrian-flow estimates, Star Rating derivatives, and other target-derived information must be excluded.

| Specification | Purpose | Permitted fields |
| --- | --- | --- |
| `F0` | Feature-free constant baseline | Training-fold target median or mean only |
| `F_existing_minimal` | Minimum viable baseline using existing client information | AADT and speed limit; later expansion only through a pre-frozen AusRAP road-feature list |
| `F_new_core` | Current five-source contextual model | The compact new-feature set defined above |
| `F_existing_minimal + F_new_core` | Primary test of the incremental value of new features | Combination of both field sets |
| `F_new_expanded` | Feature-definition sensitivity | Core fields plus the small pre-declared expansion |

All primary comparisons must use exactly the same outer folds so that performance differences represent feature changes rather than different splits.

## 6. Data joins and preprocessing

The modeling code should start from `Model_Data`, load the five feature workbooks one by one, read every `site_id` as a string, and join with `how="left"` and `validate="one_to_one"`. The result must still contain 49 rows with the same key set, successful processing status for all five sources, and no unexpected missing candidate fields. A duplicate key, extra key, missing site, or changed field type must stop the pipeline rather than trigger silent deduplication or filling.

The `log1p` transformations of distance, population density, stop count, building count, and AADT are pre-specified deterministic transformations. Scaling, median imputation, categorical encoding, and any learned feature selection must be fitted only on the training part of each fold. Categorical encoding must safely handle unknown categories. Complete training data do not justify arbitrary production imputation. The model provides no evidence that imputing an entirely missing source is reliable. A production row with a whole missing source may receive a `PARTIAL` prediction only after simulated source-dropout validation supports that path; otherwise it should return `FAILED` or an explicit out-of-scope status.

Coordinates, ABS Mesh Block and SA1 codes, stop/school/health identifiers, organisation and school names, status and error fields, and road names must not enter the predictor matrix. They should remain in audit outputs. Reading an ABS code from Excel as an integer does not make it a continuous numeric feature.

## 7. Validation design and stress tests

A permanent holdout of approximately 10 sites is not recommended at this stage. With only 49 geographically uneven sites, a fixed 20% test result would depend heavily on which high-flow sites happen to be selected. The primary evaluation should use repeated, grouped, spatially constrained nested cross-validation. A true external test should use future surveyed sites with observed targets; the current 51 unobserved locations can test the feature pipeline, processing time, statuses, domain checks, and output format, but cannot provide accuracy evidence.

Outer-fold grouping should first create indivisible components. Sites with the same `road_no` must belong to the same component. Sites no more than 1 km apart must also belong to the same component, including the transitive closure of these relationships. The current rule produces approximately 25 components, with the largest containing about 11 sites, which can still be allocated across five folds. Using fixed seeds, create 10 five-fold assignments that preserve components and balance target distributions as far as possible. A component may occur in only one test fold per repetition. Both targets and all models must use the same versioned fold file. Seeds must not be repeatedly changed to improve scores.

Within each outer training set, use four-fold `GroupKFold` on the same components to select a small number of hyperparameters. Inner processing may see only outer-training data. Scaling, encoding, imputation, optional learned selection, and model tuning must all remain inside this inner procedure. Outer-test targets may be used only for final out-of-fold predictions and metrics. Each site will obtain 10 unseen-target predictions across the 10 outer repetitions. Aggregate predictions by site before calculating the overall result, and also report the score distribution across repetitions. The 490 repeated predictions must not be treated as 490 independent observations.

Three stress tests are required. A 25 km buffer test should remove any training site within 25 km of a test site to assess stricter spatial transfer. A leave-one-survey-batch-out test should use each of the 17-, 7-, and 25-site batches as the test group in turn to assess time and region transfer. Finally, external accuracy may be assessed only when future sites have real camera-survey targets.

## 8. Candidate models and selection rule

Retain both training-fold median and mean constant baselines. The median is the natural MAE baseline, while the mean is the natural RMSE baseline. The primary model is Ridge regression fitted to a `log1p` target because it is comparatively stable with a small sample, correlated variables, and one-hot categories, while remaining auditable. The inner search should use a small pre-defined alpha grid such as 0.1, 1, 10, and 100.

The first challenger is `TweedieRegressor` with a log link, a limited alpha grid, and a few pre-specified power values such as 1.1, 1.5, and 1.9. It directly constrains the expected value to be non-negative, but its assumptions and numerical stability must be judged through outer validation. The second challenger is a tightly restricted shallow Random Forest with a small grid for `max_depth`, `min_samples_leaf`, and `max_features`; the minimum leaf should contain approximately four or more sites. XGBoost, deep trees, neural networks, broad AutoML searches, and large interaction searches are outside the first-round protocol because 49 observations cannot select these degrees of freedom reliably.

To separate feature value from algorithm value, the main client comparison should hold the Ridge model family fixed and compare `F_existing_minimal` with `F_existing_minimal + F_new_core`. Tweedie and shallow forest models are algorithm challengers only on the combined specification. Selection follows a simplicity-first stability rule. Retain Ridge unless a more complex model lowers MAE across most repeated outer splits, improves or at least preserves high-flow-site RMSE, and shows paired-improvement uncertainty that does not include a materially unhelpful region. A single best fold score is not sufficient evidence.

## 9. Metrics and statistical reporting

The primary metric is pooled out-of-fold MAE on the original pedestrians/hour scale. It is directly interpretable and less dominated by extreme observations than RMSE. Secondary metrics are RMSE, RMSLE, Spearman rank correlation, pooled out-of-fold R-squared, and calibration intercept and slope. R-squared may be negative and is unstable on small test folds, so only the pooled OOF value should be reported; fold-level R-squared values must not be averaged into the main result. MAPE should not be used because the cross-road target includes zero and many small values.

Model differences must be paired by the same site and fold. Report `delta_MAE = MAE_combined - MAE_baseline`, where a negative value indicates improvement from the new features. Also report the proportion of the 10 outer repetitions showing improvement. For aggregated per-site absolute-error differences, use a road/spatial-component-level bootstrap to describe uncertainty. This interval is evidence of stability in the limited sample, not a strict confidence interval for the entire state.

Because a few high-flow sites dominate RMSE, also show per-site OOF errors, descriptive MAE/RMSE for sites in the upper target quartile, and the change in overall MAE after leaving out each individual site. High-flow sites must remain in the primary analysis. Influence analysis should only reveal whether conclusions depend heavily on a few locations such as Cowaramup or Bridgetown.

## 10. Correct comparison with iRAP

iRAP values are a gray-box comparison baseline, not ground truth and not model inputs. Among the observed sites, cross bands are available for 45 of 49 sites, along-driver bands for 34, and along-passenger bands for 46. Their ordering can be used, but project records note that displayed labels may be incorrect and some ranges are wide. Until the mapping is confirmed, labels such as `1 pedestrian` and `2 to 3` must not be converted to interval midpoints for MAE or RMSE calculations.

Before the mapping is confirmed, the cross-road comparison should be ordinal or rank-based, with coverage clearly reported. Suitable summaries include the Spearman association between ordered categories and observed cross-road counts and the observed-value distribution within each category. After confirmation, apply the same thresholds to observations and model predictions, then compare an ordered confusion matrix, weighted kappa, and ordinal absolute error. Continuous model MAE must still use camera observations as ground truth.

The along-road comparison is more limited. The observed target is the combined `obs_peak_along_ped_per_h` for both sides, while iRAP retains separate driver-side and passenger-side categories. Category intervals cannot be added, and the larger side category cannot be treated as combined flow. Unless the camera data retain side-specific observed targets or the client confirms a defensible combination rule, along-road iRAP comparison should remain descriptive and must not claim a precise numeric advantage.

## 11. Uncertainty and sensitivity

The final evaluation must be repeated after excluding sites `250341-04` and `260335-38` from both training and assessment, using the same complete nested procedure, and the direction of the conclusions must be compared. This does not declare the two rows erroneous; it tests whether recorded target corrections change model selection.

Location uncertainty also matters. The 49 coordinates were derived by linear interpolation along AusRAP segments and may not be the exact camera GPS locations. The minimum nearest-school distance is approximately 58.9 m, the minimum nearest-PTA-stop distance is approximately 8.6 m, and ABS Mesh Block membership is a discrete point-in-polygon result. If feasible, perturb each coordinate by plus or minus 50 m and 100 m, or use an endpoint sensitivity design, then re-extract the important spatial features. Record category-change rates and changes in distances and building coverage, and repeat the final model evaluation with perturbed features. If re-extraction is not completed, coordinate error must be listed as a limitation, and short-distance coefficients must not be interpreted causally.

The sources are not perfectly aligned in time. ABS represents the 2021 Census. The Microsoft release is dated 2026-07-24 and is based on imagery from approximately 2014–2024. Health content is current to 2025, while school and PTA snapshots are from 2026. Survey targets come from 2025 and 2026 batches. These features describe recent place context but are not same-day exposures. The 2026 school and PTA snapshots introduce a small temporal mismatch for 2025 surveys. Leave-one-batch-out analysis and source-version records must therefore be retained.

If prediction intervals are required, they may be generated after model selection with cross-conformal or CV+ methods based on outer OOF residuals, for example at 80% and 95%. Because of spatial non-exchangeability and the 49-site sample, they should be described as empirical intervals under the current sample and validation design, not as guaranteed statewide coverage. Adding interval fields, `out_of_domain`, or `nearest_training_site_km` to the output template is a formal schema change and requires an updated `feature_schema_version`.

## 12. Interpretability and evidence of feature value

Primary interpretation should use the distribution of standardized Ridge coefficients across outer folds, not one coefficient from a final refit on all 49 rows. Report each feature's median coefficient, sign consistency, and range across folds. Highly correlated fields should be interpreted jointly, and no variable should be given an independent causal interpretation. Statements such as "closer schools cause more pedestrians" must be replaced with observational language such as "school proximity is associated with predicted flow in the current sample."

Assess each source through source-level drop-column ablation: remove one source at a time while holding the model, folds, and other features fixed, then compare paired OOF MAE. This identifies model dependence on a source, but five comparisons on 49 sites provide diagnostic rather than definitive evidence. A shallow forest may also use fold-safe permutation importance. SHAP may illustrate individual cases, but it should not be the primary scientific evidence and must not obscure correlation or spatial confounding.

## 13. Support domain, missing data, and deployment

Only after model selection and all sensitivity analyses should the final deployment model be refitted on all 49 approved sites. The saved artifact should include the complete preprocessing and model pipelines for both targets, an immutable `model_version`, `feature_schema_version`, the training-site list, feature order, category mappings, source snapshot versions, code commit, validation-fold version, and metric summary. Inference code must not reimplement transformations differently from training.

For every new location, calculate support-domain flags using at least required-field ranges, robust-scaled distance to the nearest training site in feature space, and geographic distance to the nearest observed site. These flags should accompany the prediction rather than become target predictors. Because central Perth is under-represented, a location may be processed successfully while still lacking sufficient statistical support.

Calculate `feature_completeness_pct` strictly from the fields required by the deployed model. Failure of a whole source must not be converted into ordinary zero values. A missing-source path may be registered as an approved imputation path and return `PARTIAL` only if simulated source-dropout OOF testing shows acceptable behaviour. Otherwise the result should be `FAILED` or omitted. Model uncertainty, feature completeness, and processing status are separate concepts and must not be compressed into one confidence score.

## 14. Differences from requirements or current proposals

| ID | Requirement or proposal | Position in this protocol | Rationale and treatment |
| --- | --- | --- | --- |
| D1 | The five sources can support entry into prediction work | Agree for Phase A, but not as the complete client conclusion | The tables are sufficiently structured for a contextual model, but imagery and the full existing-variable baseline are absent. Complete the reproducible model first, then add the Phase B comparison. |
| D2 | Flow may be predicted as a number or category | Use continuous numbers for the primary analysis and derive categories secondarily | Continuous targets retain information and may be fractional. Categories are easier to display but lose information and depend on the unresolved iRAP label mapping. |
| D3 | iRAP and model outputs can be compared directly with standard error metrics | Do not turn current iRAP categories into invented continuous values | iRAP is ordinal and the labels have known issues. Use ordinal comparisons until thresholds are confirmed. The two along-road side categories also cannot currently be combined validly. |
| D4 | Prefer an untouched evaluation set | Do not permanently hold out a small fixed test set from the current 49 rows | The requirement is conditional on feasibility. A fixed set would have excessive variance; repeated nested grouped/spatial CV uses the limited data better, while future target-labelled sites provide the external test. |
| D5 | Start with simple interpretable models and adopt complexity only when it helps | Agree, with an added stability gate | Ridge is primary; Tweedie and shallow forest are limited challengers. Complexity is adopted only after stable paired improvement and spatial stress testing. |
| D6 | Processing approximately 7,000 coordinates is a useful scale goal | Do not equate engineering throughput with statistical generalization | Batch size tests processing speed and failure rates. Predictive validity requires target-labelled external observations. Report these as separate outcomes. |
| D7 | Bland–Altman and similar plots may be useful | Use conditionally, not for every comparison | Agreement plots suit two continuous measurements, not categorical iRAP bands. Continuous model predictions may use residual/agreement plots, while iRAP should remain ordinal. |

These positions do not reject the client's goals. They separate requirements, optional methods, and conclusions supported by the current evidence. If the client later confirms thresholds, evaluation priorities, or imagery features, update and version this protocol rather than silently changing an analysis after results are known.

## 15. Execution order and gates

1. Freeze this protocol, the model input fields, feature specifications, metrics, 10-by-5 outer validation design, and limited hyperparameter grids. Generate a fold-assignment file that is not manually edited.
2. Implement Stage 3 data assembly and schema validation. Produce a leakage-free modeling matrix and audit report without overwriting the five source feature tables or authoritative target table.
3. Run `F0` and the Ridge `F_new_core` model first. Verify nested OOF processing, non-negative inverse transformation, metrics, and per-site predictions as the minimum end-to-end walking skeleton.
4. Add `F_existing_minimal` and the combined specification, then perform the paired incremental-value test on the same folds.
5. Run the Tweedie and shallow-forest challengers and apply the simplicity-first stability rule. Do not expand the search space merely to pursue the best score.
6. Complete source ablation, the 25 km buffer test, leave-one-batch-out analysis, corrected-site exclusion, single-site influence analysis, and coordinate-perturbation sensitivity.
7. Complete the ordinal iRAP comparison. If category mapping or along-side definitions remain unresolved, record them as client-confirmation items rather than generating invented numbers.
8. Freeze the final model and feature schema and refit on all 49 sites. Use the 51 unobserved locations only for inference, support-domain, completeness, and processing-status validation.
9. Deliver reproducible modeling code, configuration, fold assignments, OOF predictions, metrics and intervals, ablation and sensitivity results, a model card, versioned model files, and an updated prediction-output schema.

Each stage must pass key-integrity, leakage, fold-isolation, and reproducibility checks before the next stage begins. A model is complete only when the same command reconstructs the same folds, OOF results, model version, and interpretable failure states from fixed inputs.

## 16. First implementation task

The next task should be limited to Stage 3 data assembly, schema and leakage auditing, and fixed fold generation. It should not select the final model. Join the five feature tables, authoritative targets, and minimum existing-variable baseline into a validated matrix. Produce the field-role list, duplicate/missing/range report, spatial components, and 10-by-5 fold assignments. Begin the first constant-baseline and Ridge OOF run only after this foundation passes validation.
