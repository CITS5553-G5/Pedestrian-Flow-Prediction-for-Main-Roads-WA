# Model development

This directory contains research notebooks and R Markdown reports for exploratory analysis, candidate-model comparison and internal validation. Routine prediction loads the selected `pedestrian-linear-v1` release through `src/pedflow/modeling/`; it does not rerun these notebooks or fit a new model.

| Research entry | Purpose |
| --- | --- |
| [Random forest](01_Shahil_random_forest_pedestrian_flow_modelling.ipynb) | Random-forest modelling and validation |
| [Gradient boosting](02_Merlyn_Gradient_Boosting.ipynb) | Gradient-boosting research |
| [Final model comparison](03_Yashika_Predict_Pedestrians_Final_Model_Comparison.Rmd) | R model comparison and saved selected-model bundle; [rendered report](03_Yashika_Predict_Pedestrians_Final_Model_Comparison.pdf) |
| [Additional modelling comparison](04_Jason_Modelling_Comparison.ipynb) | Candidate-model comparison |
| [Development and internal validation](05_Haoqi_Model%20Development%20and%20Internal%20Validation.ipynb) | Model-development and validation analysis |
| [Statistical modelling](06_Makoto_stat_model/Pedestrian_Prediction_Report.Rmd) | Statistical-model research; [rendered report](06_Makoto_stat_model/Pedestrian_Prediction_Report.pdf) |
| [Exploratory analysis](EDA/) | Survey and feature exploration in notebooks and R Markdown |

The research dataset is `data/processed/model_dataset.xlsx`, with 49 surveyed sites. The selected model uses `commercial_buildings`, `footpath_both_sides` and `abs_mb_category_simple` to predict crossing and along-road peak flow in pedestrians/hour. The [model explanation](../docs/03_model_development/selected_model_explained.md) describes the coefficients and transformations; the [integration guide](../docs/03_model_development/selected_model_integration.md) describes release export and R/Python equivalence checks.

[Reviewed modelling outputs](../06_outputs/03_model_development/README.md) contain metrics, saved out-of-fold (OOF) predictions and research bundles. OOF predictions come from road-grouped validation folds; production predictions use the final model fitted to all 49 training sites. They can differ even for identical input features. Feature and model selection used the survey dataset, so the OOF results are internal validation rather than independent external validation.

Notebook execution requirements vary: Python notebooks use the project environment, and R Markdown entries require their declared R packages and rendering tools. Execute research against the appropriate documented input snapshot. [Historical evaluation reproduction](../docs/05_model_evaluation/reproduction.md) requires exact source fingerprints and is separate from operational prediction.
