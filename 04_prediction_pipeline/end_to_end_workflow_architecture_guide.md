# End-to-End Workflow Architecture Guide

Status: proposal for team review
Date: 29 August 2026

## Purpose

This document describes a practical direction for turning the current notebook-based work into a reproducible training and prediction workflow. It is an engineering proposal, not the current implementation and not a confirmed client requirement.

The team should keep two operations separate:

1. Training prepares approved data, compares models and creates a versioned model release.
2. Prediction loads an approved model and produces results for new locations without retraining or rerunning research notebooks.

## Current repository state

The repository currently uses the following project stages:

1. `01_data_preparation/` prepares and reconciles modelling data.
2. `02_feature_extraction/context/` contains shared source-specific feature notebooks.
3. `03_model_development/` is reserved for model training, comparison and selection.
4. `04_prediction_pipeline/` records prediction-stage documentation and reviewed interface material; formal prediction code belongs under `src/pedflow/`.
5. `05_application/` contains a reserved backend area and a React/Vite frontend demo.
6. `06_outputs/` contains reviewed, intentionally shared outputs.

Stage 1 and Stage 2 contain working notebooks and feature outputs. The Stage 3 and Stage 4 Python files are currently placeholders. The frontend is a visual demo with hard-coded values and browser-side rules; it is not connected to a trained model or backend.

Google Places Aggregate POI features are excluded from the prediction system by the recorded UWA project decision. The pre-exclusion experiment is retained only under `07_Archive/20260908_google_places_aggregate_poi_experiment/`; neither its workbook nor its fields may enter a released model or client batch workflow.

## Recommended dependency rule

The final workflow should have one authoritative implementation for data preparation, feature generation, training and inference:

```text
research notebooks ─┐
batch interface ────┼──> shared Python implementation ──> approved data and models
application backend ┘
```

Notebooks should explain sources, show checks and preserve scientific reasoning. Batch scripts and the backend should provide user interfaces. None of these interfaces should maintain a separate copy of the same calculation.

## Incremental target structure

The following additions are recommended only when the team begins converting validated notebook logic into shared code:

```text
03_Project/
├── 01_data_preparation/
├── 02_feature_extraction/
│   ├── context/
│   │   ├── 02_01_haoqi_abs_mesh_block_sa1.ipynb
│   │   ├── 02_03_haoqi_pta_stops.ipynb
│   │   ├── 02_04_haoqi_wa_health_establishments.ipynb
│   │   ├── 02_05_haoqi_wa_education_schools.ipynb
│   │   └── 02_07_haoqi_microsoft_building_footprints.ipynb
│   └── README.md
├── 03_model_development/
│   └── model-development notebooks
├── 04_prediction_pipeline/
│   ├── README.md
│   └── sample/
├── 05_application/
│   ├── backend/
│   └── frontend/
├── src/
│   └── pedflow/
│       ├── features/
│       └── prediction.py
├── configs/
└── tests/
```

This is a target layout, not a request to create empty folders now. Add each component only when validated logic or a confirmed interface needs it.

## Responsibilities

| Component | Responsibility |
| --- | --- |
| Stage notebooks | Source explanation, exploration, visual checks and interpretation |
| Shared Python modules | Reusable and tested preparation, feature, training and inference logic |
| Model-development notebooks | Compare models and export the selected fitted pipeline |
| Inference package entry | Validate a batch request and call the shared inference workflow |
| Backend | Handle application requests and call the same inference logic |
| Frontend | Collect inputs and display backend responses without prediction formulas |

A stable calculation should move out of a notebook only after its inputs, outputs, source version, failure behaviour and validation checks are understood. The notebook may then import the shared function and continue to display evidence and interpretation.

## Required contracts

Before implementing the client-facing workflow, the team should agree on four interfaces:

1. The input contract defines required fields, identifiers, types, coordinate reference, ranges and null rules.
2. The feature contract defines candidate and selected model fields, sources, transformations, categories and missing-data handling.
3. The model contract records target names, preprocessing, feature order, model version and compatible dependency versions.
4. The output contract defines predictions, processing status, warnings, provenance and version fields.

Identifiers, coordinates, source statuses and error messages should remain available for checking but should not automatically become predictors. Invalid keys, schemas or one-to-one joins should fail explicitly rather than being silently repaired.

## Training workflow

The training workflow should:

1. Load approved target and feature-table versions.
2. Validate keys, schemas, source status and target fields before joining.
3. Apply preprocessing and feature selection inside the training folds.
4. Compare pre-declared baselines and candidate models on the same grouped or spatial folds.
5. Produce out-of-fold results and sensitivity checks.
6. Select a model using the agreed simplicity and stability rules.
7. Refit the selected pipelines and create a versioned model release.
8. Test the release before it becomes available to prediction code.

The detailed scientific evaluation protocol remains in `docs/03_model_development/`. Training is a team-controlled activity and is not rerun for each client prediction.

## Prediction workflow

The prediction workflow should:

1. Read a submitted workbook or validated API request.
2. Validate the input contract and report unusable rows clearly.
3. Build the same approved features used during training.
4. Load the selected model and its fitted preprocessing.
5. Produce separate cross-road and along-road predictions.
6. Write predictions, statuses, warnings and model/source versions.

The installed inference command and the backend should call the same `src/pedflow` inference implementation so that command-line and web results cannot diverge. Prediction must not retrain a model or depend on executing notebooks manually.

## External sources and outputs

The delivery method for each external feature source must be agreed before client use. A source may use an approved dated snapshot, an authorised online request or a documented combination of both. Network access, credentials, rate limits, licence conditions and retention limits must be handled explicitly.

A missing source must not silently become zero. Return a partial result only if model testing supports that behaviour; otherwise return a clear failure or unsupported status.

Reviewed small outputs needed by teammates may be committed under `06_outputs/`. Temporary API results, disposable runs, fitted models and unreviewed reports should remain outside Git unless the team deliberately approves a compliant release method.

## Application boundary

The current React frontend is a demo. Its hard-coded predictions and fixed confidence value are not model results. Before the application is described as functional:

1. The backend contract must be defined and validated.
2. The backend must call the shared inference implementation.
3. The frontend must display only returned results and honest processing statuses.
4. Unsupported confidence claims must be removed or replaced by a validated uncertainty method.

The optional development container is a development convenience, not an assumed production deployment design.

## Minimum testing

Unit tests should cover stable calculations and schema rules. One small integration test should cover batch input, feature assembly and output writing. Once a model has been selected, extend that test through model loading and the final prediction schema. The reviewed combined context table provides the project-level feature contract; separate full-data regression tests for every source are not required.

Tests must also cover controlled failures such as missing fields, duplicate identifiers, invalid coordinates, unavailable sources, incompatible model releases and unwritable outputs. Production success must not depend on running every notebook.

## Recommended implementation order

1. Agree on the first input, feature and output contracts.
2. Implement Stage 3 data assembly and leakage checks using the existing reviewed outputs.
3. Build and validate the first reproducible training workflow.
4. Promote stable feature logic into shared modules one source at a time, with tests.
5. Implement a one-command prediction entry inside the installed `pedflow` package.
6. Connect the backend to the same prediction service.
7. Replace the frontend demo logic and rehearse setup in a clean environment.

The project does not currently need a distributed workflow platform. A small tested Python codebase, explicit contracts, a versioned model release and one batch or web interface are sufficient unless a confirmed operational requirement justifies additional infrastructure.

## Completion criteria

The workflow is ready for client-facing acceptance testing only when it can be installed without absolute-path changes, produces a tested model release, predicts through one supported entry point without notebook execution, reports invalid inputs and unavailable sources clearly, and returns the same result through batch and backend interfaces. Data permissions, source terms, secrets, model limitations and operating instructions must also be documented.
