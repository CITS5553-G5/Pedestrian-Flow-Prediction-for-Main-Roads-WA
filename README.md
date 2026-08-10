# Pedestrian Flow Prediction for Main Roads WA

This repository contains the CITS5553 Group 5 Python code for pedestrian-flow prediction on major roads in Western Australia.

## Stages(This is not the final delivery; it is only to meet the needs of the current stage)

1. `01_data_preparation` — prepare and link survey, AusRAP and Road Network data.
3. `02_imagery_features` — retrieve imagery and extract additional features.
4. `03_model_development` — train, compare and select models.
5. `04_final_pipeline` — integrate the agreed code and generate final predictions.

## Team file naming

Each member writes one Python file for the stage they are working on:

```text
firstname_01_data_preparation.py
firstname_02_imagery_features.py
firstname_03_model_development.py
firstname_04_final_pipeline.py
``

For example: `haoqi_03_model_development.py`.

Members can develop different approaches independently. After comparison, the team will combine the selected code into the final version. Split a stage into smaller files only when the team agrees it is necessary.

## Data rule

GitHub is for code only. Client data, generated datasets, model files and API keys must not be committed. Local source files remain under `data/raw/` and are excluded by `.gitignore`.
