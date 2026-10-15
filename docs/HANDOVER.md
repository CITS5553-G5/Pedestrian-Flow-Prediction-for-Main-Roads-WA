# Customer handover

Updated 15 October 2026. This guide identifies the delivered materials, local data requirements, verification status and limits of use. Follow the [setup guide](SETUP.md) for installation and the [prediction run guide](04_prediction_pipeline/prediction_workflow.md) for operational instructions.

## Delivered materials

The workflow predicts peak crossing and along-road pedestrian flows in pedestrians/hour from submitted locations. It resolves road positions, extracts ABS and imagery features, applies the released model and attaches existing AusRAP reference values when the local reference source is available. Observed counts are optional input fields and are never predictors.

| Material | Purpose |
| --- | --- |
| [Prediction workflow](04_prediction_pipeline/prediction_workflow.md) | Input preparation, batch execution, output fields and recovery |
| [Comparison workbook and reports](../04_prediction_pipeline/irap_comparison/README.md) | Saved model-validation predictions, observations, existing AusRAP estimates and supporting evidence |
| [Offline prediction example](../04_prediction_pipeline/prediction_example/README.md) | Ten locations replayed from saved features without external requests |
| [Original imagery research notebook](../02_feature_extraction/imagery/Image_Feature_Extraction_Pipeline.ipynb) | Complete research process, image previews, feature extraction, batching and export |
| [Reviewed imagery workflow notebook](../02_feature_extraction/imagery/Run_Reviewed_Imagery_Workflow.ipynb) | Shared extraction implementation with concurrency and checkpoints |
| [Model explanation](03_model_development/selected_model_explained.md) | Selected features, calculations and validation interpretation |
| [Research code](../03_model_development/README.md) and [reviewed outputs](../06_outputs/README.md) | Modelling methods, retained feature tables, validation results and fitted research bundles |

The deployed model is `pedestrian-linear-v1`. It uses `commercial_buildings`, `footpath_both_sides` and `abs_mb_category_simple`. Each prediction uses the same final fitted model; running a batch does not retrain it. Current versions are `prediction_v2` for the workflow and `prediction_output_v5` for the 29-column result schema.

## Prepare the environment and data

Install Python 3.11 and the project dependencies using [setup](SETUP.md). Supply your own `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY` in the repository-root `.env` for live imagery extraction. The [imagery notebook guide](../02_feature_extraction/imagery/README.md) explains both notebooks and their credential configuration.

| Local material | Required for |
| --- | --- |
| `data/external_raw/main_roads_slk/road_slk.sqlite.gz` | Road/SLK location matching and the offline example |
| `data/external_raw/Mesh Block Counts, 2021.xlsx` | ABS features for live location prediction |
| `data/raw/AusRAP Data - Words - MSDS.xlsx` | Existing AusRAP references and the complete offline example |
| A filled input workbook, CSV or Parquet table | Locations to predict; use the [input templates](../data/templates/README.md) |

GitHub includes only the README under `data/raw/`. Obtain the required raw files through the agreed data handover and place them at the exact paths in the [raw-source guide](../data/raw/README.md). Data reconciliation and historical evaluation require additional sources documented there. Processed datasets, templates and reviewed research outputs remain versioned.

A batch can contain any positive number of locations, using coordinates, road number plus SLK, or both. Each row needs a unique `site_id`. Unknown observed counts stay blank. The supplied 20-location processed example and 100-location template example do not constrain new batch sizes or the mix of locations.

## Run and inspect the results

After setup and local data preparation, reproduce the saved-feature example from the repository root:

```bash
python tools/replay_prediction_example.py --output-directory outputs/predictions/example_reproduction
```

For a live batch, replace the input path and worksheet below with your prepared file. Use a new output directory for each run.

```bash
pedflow-predict --input path/to/locations.xlsx --sheet Batch_Input --output-directory outputs/predictions/customer_run_001
```

The output workbook contains `Prediction_Output`, `Features` and `Metadata`. It is accompanied by a run manifest and, for imagery extraction, a checkpoint. Inspect `location_status`, prediction `status`/`message` and `comparison_status`/`comparison_notes` independently. Failed predictions remain blank, and missing values must not be treated as zero.

A valid supplied coordinate can remain usable when carriageway matching is ambiguous, with the warning retained. Unresolved road-only locations require correction before prediction. If the AusRAP source is unavailable, model predictions can still succeed while reference matching reports `source_unavailable`. A successful command exit therefore does not establish reference coverage. Recovery with `--resume` requires a compatible existing checkpoint; details are in the run guide.

## Verification and limits of use

Offline verification on 15 October 2026 passed 199 tests and 36 subtests. The ten-location replay preserved saved features and predictions, produced 29 result columns, matched all ten references and retained one imagery warning. These checks demonstrate calculation and workflow behaviour with saved or simulated features; fresh live ABS/Maps/Gemini acceptance remains outstanding. Review a live sample with your own credentials and inputs before operational use.

The comparison retains all 49 surveyed sites, with paired evaluation on 45 crossing and 43 along-road sites. It uses out-of-fold predictions from model development, while operational prediction uses the final model fitted to all 49 sites. Model and feature selection used these survey data, so the comparison is internal validation. Crossing improvements are sensitive to a small number of influential sites. A sensitivity refit excluding the two corrected-target sites has not been performed; its impact is not established. See the [comparison notes](../04_prediction_pipeline/irap_comparison/comparison_report.md).

Whole-network prediction and independent validation at new locations remain unverified. The dashboard is a prototype without a connection to the released model. The delivered analytical PDF is a static report whose generation script is not included. Workbook checks included rendered review and formula/chart verification; execution in the Microsoft Excel application has not been verified. Historical evaluation reproduction has separate source-snapshot requirements described in the [research reproduction guide](05_model_evaluation/reproduction.md).
