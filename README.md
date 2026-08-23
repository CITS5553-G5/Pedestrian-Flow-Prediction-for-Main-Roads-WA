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

This private repository is the authorised team workspace for the curated source inputs and the three core project tables under `data/`. Only data directly used by the current target-checking, feature or spatial-linkage workflow are tracked. Access must remain limited to approved project collaborators; do not make the repository public, create public mirrors, or copy client files into an unapproved service.

Large retained source files are managed by Git LFS so that ordinary Git history remains usable. Every collaborator must install Git LFS once and then run `git lfs install`. A normal clone or pull will retrieve the current large files; if only pointer files appear, run `git lfs pull`.

The sharing rule does not extend to archival survey workbooks, unselected candidate datasets, secrets or disposable artefacts. API keys and `.env` files, downloaded imagery, temporary working files, experiment outputs, fitted models and generated reports remain excluded. Tracked source files under `data/raw/` are immutable inputs: analysis code may read them but must never overwrite them. See `data/README.md` for the folder contract.
