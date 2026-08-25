# Shared reviewed outputs

This directory contains small, reviewed results that teammates may use without rerunning every upstream notebook.

`02_feature_extraction/` contains the latest feature tables produced by the five shared Stage 2 notebooks. Each workbook has one row per `site_id` and is intended for later one-to-one joining with `data/processed/model_dataset.xlsx`.

When a notebook changes its feature values or schema, update the matching output in the same commit or Pull Request. Do not edit a generated workbook manually. Temporary runs, personal experiments, downloaded source caches, fitted models and large generated files do not belong here.
