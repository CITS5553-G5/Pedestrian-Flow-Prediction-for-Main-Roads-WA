# Selected model explained

The production release is `pedestrian-linear-v1`, exported without refitting from Yashika's saved R model bundle. It contains two separate linear regressions on `log1p` peak-hour flow: one for crossing and one for along-road flow. Both use the same three features and all 49 training observations from 28 roads.

The [detailed model explanation](selected_model_details.md) includes the full equations, worked examples, grouped-validation results and interpretation limits.

## Inputs and calculation

`commercial_buildings` is the numeric imagery feature, `footpath_both_sides` is the imagery boolean, and `abs_mb_category_simple` is the ABS class (`Residential`, `Other` or `Commercial`). The official [integration contract](selected_model_integration.md) specifies allowed values, failure handling and the saved preprocessing. Coordinates determine feature extraction but are not regression inputs. Observed counts and existing AusRAP values are not predictors.

For each direction, compute `eta = intercept + building coefficient * commercial_buildings + footpath effect + ABS effect`, then `predicted pedestrians/hour = max(expm1(eta), 0)`. FALSE and Residential are reference levels with zero effects. No final rounding is applied to the stored prediction.

| Term | Crossing | Along-road |
| --- | ---: | ---: |
| Intercept | 1.4403 | 1.9802 |
| Commercial buildings | 0.2616 | 0.2962 |
| Footpath on both sides: TRUE | 0.4261 | 0.2727 |
| ABS: Other | 0.1676 | 0.1193 |
| ABS: Commercial | 0.0724 | -0.1073 |

These displayed coefficients match Table 13 in Yashika's final comparison report to its four-decimal precision. Runtime inference uses full-precision values from the [release JSON](../../src/pedflow/modeling/releases/pedestrian_linear_v1.json), whose SHA-256 remains `f85f5ca240093c32cea2e4a023e6b0a73c38ff467c032747b70fd57f8c287042`. Delivery cleanup does not change the model, feature recipe or coefficients.

## Validation predictions versus production predictions

OOF means out of fold. In road-grouped five-fold cross-validation, each site's road group is held out while that fold's model is trained on the other groups. The saved predictions test the selected modelling approach on held-out roads within this dataset. They come from actual fitted fold models, not invented estimates. Feature/model selection still used these survey data, so this is internal validation.

The [49-site comparison](../../04_prediction_pipeline/irap_comparison/comparison_report.md) reads those saved OOF predictions and compares them with observed counts and the existing recoded baseline on matched samples. It does not run the final production model. The published final model uses all 49 sites and therefore has a different fitted parameter set from each fold. Equal features do not imply that OOF and final-model values are equal.

Every production batch uses the same final release, whether it contains surveyed sites, unknown sites or both. It does not recognize a surveyed ID and substitute an OOF result or automatically fill observations. With identical three input features and the same release, production predictions are deterministic. Fresh imagery or changed feature inputs may change the output, but running a batch does not retrain the model.

## Verification and interpretation

The saved R reference fixture contains 79 cases: 49 training rows, 24 feature combinations and six fallback cases. Python unit tests compare inference with these saved R outputs; this demonstrates implementation equivalence, not held-out predictive accuracy. Fresh R execution requires the documented R environment and was not performed during delivery cleanup.

Default inference rejects missing or invalid model features. Explicit reviewed fallback can use saved training replacements and reports every replacement. Building counts outside 0–12 receive an extrapolation warning. The model does not provide confidence intervals. Along-road predictions inherit the training target's survey definition; the two special coverage cases and outstanding correction sensitivity analysis are described in the comparison report.

Use the [run guide](../04_prediction_pipeline/prediction_workflow.md) for live prediction and the [offline example](../../04_prediction_pipeline/prediction_example/README.md) for a reproducible local test. Neither path computes production MAE/RMSE.
