# Project support tools

This folder contains scripts for exporting the reviewed model, reproducing delivery
artefacts and repairing workbook charts. The shared prediction implementation lives
in [`src/pedflow`](../src/pedflow/README.md); use `pedflow-predict` for new locations.
These tools run separately when preparing or checking a release or deliverable.

| File | Purpose and inputs/outputs |
| --- | --- |
| [`export_linear_model.R`](export_linear_model.R) | Reads the saved selected R model bundle and matching training workbook. Exports the Python-readable model release and 79 R reference prediction cases for equivalence tests, without retraining. Requires R, `jsonlite` and `readxl`. See the [export and verification guide](../docs/03_model_development/selected_model_integration.md#reproducing-the-release-and-verification). |
| [`build_comparison_workbook.mjs`](build_comparison_workbook.mjs) | Reads `comparison.json` containing the reviewed 49-site comparison. Creates `irap_comparison.xlsx` with observed counts, saved out-of-fold (OOF) predictions, existing iRAP estimates, error formulas and charts, plus preview images and checks. Requires Node.js and `@oai/artifact-tool`. See the [comparison notes](../04_prediction_pipeline/irap_comparison/comparison_report.md). |
| [`repair_comparison_charts.py`](repair_comparison_charts.py) | Repairs missing X/Y cell references and cached values in the two scatter charts exported by the workbook builder. Updates the supplied XLSX in place while preserving other workbook parts. Requires `openpyxl`; it is specific to this comparison workbook's layout and sample sizes. |
| [`replay_prediction_example.py`](replay_prediction_example.py) | Reads the delivered ten-location feature snapshot, reruns released-model prediction and local road/AusRAP matching, and writes the prediction workbook, manifest, input CSV and verification JSON. Makes no external service requests. Requires the installed project and local reference data. See the [prediction example](../04_prediction_pipeline/prediction_example/README.md). |

Run commands from the project root after [Python setup](../docs/SETUP.md).
The prediction replay requires a new or empty output directory. The workbook builder
requires an output location without an existing `irap_comparison.xlsx`; using a new
directory keeps reviewed files separate. The R exporter writes its specified
release/reference paths, and chart repair modifies its supplied workbook in place.
The replay provides `--help`; the R exporter and Node.js builder use positional arguments.

## Offline prediction replay

```bash
python tools/replay_prediction_example.py --output-directory outputs/predictions/example_reproduction
```

This replays the delivered feature snapshot. Local model and road/AusRAP references
are required; API keys and external service calls are not. Replay reproduces that
particular saved sample. New prediction batches can contain any positive number of
locations and use `pedflow-predict` with their own input file.

## Comparison workbook preparation

The optional builder needs Node.js and a compatible, separately provisioned
`@oai/artifact-tool` package. That package is not installed by `requirements.txt`
or the frontend's `npm ci`, and the repository does not supply a standalone
installation or lockfile for it. An existing compatible runtime can be selected
with `ARTIFACT_NODE_MODULES`, pointing to its `node_modules` directory. Use its
actual local path; the path below is a placeholder.

```bash
export ARTIFACT_NODE_MODULES="/path/to/compatible-runtime/node_modules"
node -e "console.log(require.resolve('@oai/artifact-tool', {paths: [process.env.ARTIFACT_NODE_MODULES || process.cwd()]}))"
node tools/build_comparison_workbook.mjs 04_prediction_pipeline/irap_comparison/evidence outputs/evaluation/comparison_workbook
python tools/repair_comparison_charts.py outputs/evaluation/comparison_workbook/irap_comparison.xlsx
```

In Windows PowerShell, set the same runtime variable with
`$env:ARTIFACT_NODE_MODULES = 'C:\path\to\compatible-runtime\node_modules'`
before running the Node.js commands. Chart repair uses `openpyxl` for read-only
cell verification and the standard library to update only the two chart XML parts.
It assumes this workbook's reviewed layout and 45/43 paired sample sizes.

The command above builds a presentation from the delivered `comparison.json`.
Producing a new historical evaluation JSON requires the exact research snapshot
described in the [reproduction guide](../docs/05_model_evaluation/reproduction.md).
If the artifact runtime is unavailable, the delivered workbook and reports remain
readable, but the builder is not runnable in that environment. Inspect generated
formula values and scatter-chart references before treating a new workbook as reviewed.

OOF predictions assess internal cross-validation performance in the comparison.
The R references check Python/R calculation equivalence, while the replay reproduces
final-model inference from saved features. Neither is a fresh live extraction or
external validation.

The delivered PDF analysis report and its [diagnostic evidence](../04_prediction_pipeline/irap_comparison/evidence/analysis/README.md)
are reviewed static results. The report-generation script is not included, so
the workbook commands above do not regenerate the PDF analysis report.
