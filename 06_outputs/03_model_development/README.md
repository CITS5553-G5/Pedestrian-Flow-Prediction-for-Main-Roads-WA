# Reviewed modelling outputs

This directory retains saved modelling results and selected fitted research bundles. Its generating research entries are indexed under [model development](../../03_model_development/README.md).

| Directory | Contents |
| --- | --- |
| [01_random_forest_pedestrian_flow_modelling](01_random_forest_pedestrian_flow_modelling/) | Crossing/along-road metrics, OOF predictions, final predictions, sensitivity comparison and a saved random-forest bundle |
| [03_yashika_model_comparison](03_yashika_model_comparison/) | Cross-validation metrics, bootstrap intervals, largest errors, OOF predictions, ranking and the selected R model bundle |

`03_model_comparison_oof_predictions.csv` supplies the saved linear-regression OOF rows used by the delivered 49-site comparison. OOF values come from validation folds and are distinct from predictions made by the final fitted model. Compare metric files only after confirming the same target, eligible sites and validation design.

`03_pedestrian_flow_final_model_bundle.rds` is the saved R source for the production release and R reference cases. The [export guide](../../docs/03_model_development/selected_model_integration.md) documents preprocessing, inverse transformation, zero clipping and verification. Production reads `src/pedflow/modeling/releases/pedestrian_linear_v1.json`; it does not require R or load the research `.rds` or `.joblib` files.

Retain model bundles with their generating code and matching data provenance. The [historical evaluation guide](../../docs/05_model_evaluation/reproduction.md) documents fingerprint requirements for reproducing the reviewed OOF comparison. New experimental runs belong in Git-ignored working directories until reviewed.
