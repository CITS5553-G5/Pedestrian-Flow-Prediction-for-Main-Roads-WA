# Local reviewed outputs

This directory contains reviewed results generated locally. Its contents, except this README, are ignored for new Git additions because they may contain client records. Share required results through the agreed private handover.

`02_feature_extraction/` contains the latest feature tables produced by the five shared Stage 2 notebooks. Each workbook has one row per `site_id` and is intended for later one-to-one joining with `data/processed/model_dataset.xlsx`.

When a notebook changes its feature values or schema, regenerate the matching local output. Do not edit a generated workbook manually. Temporary runs, personal experiments, downloaded source caches, fitted models and large generated files do not belong here.
