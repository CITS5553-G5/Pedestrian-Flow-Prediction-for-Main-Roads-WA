# Shared reviewed outputs

This directory contains reviewed research results and selected model bundles used by the documented workflow.

| Directory | Contents |
| --- | --- |
| [01_data_preparation](01_data_preparation/README.md) | Reconciled candidate workbook and survey-site map |
| [02_feature_extraction](02_feature_extraction/README.md) | Six source-specific Context workbooks, combined Context table and supplied imagery features |
| [03_model_development](03_model_development/README.md) | Model-comparison metrics, saved OOF predictions and selected fitted bundles |

Feature tables use `site_id` for one-to-one joins with the modelling dataset. Changes to generated values or schemas require the corresponding generating code and reviewed output to be updated together. Selected fitted bundles are retained for model export and research traceability; new experimental models, temporary runs and downloaded caches belong in Git-ignored working directories.

The reviewed comparison and prediction demonstration are maintained in [04_prediction_pipeline](../04_prediction_pipeline/README.md). The production model is the versioned JSON release under `src/pedflow/modeling/releases/`; research bundles in this directory are not loaded for routine prediction.
