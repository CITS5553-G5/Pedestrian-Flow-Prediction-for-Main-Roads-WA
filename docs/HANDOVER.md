# Delivery handover

Updated 5 October 2026. The [delivery folder](../04_prediction_pipeline/README.md) contains the reviewed comparison and final-model example; the [run guide](04_prediction_pipeline/prediction_workflow.md) describes operational use.

## Delivered state

The workflow accepts any positive number of locations, with batch size determined by the populated rows in the submitted input table. No predefined location count or observed/random split is required. It resolves road geometry, extracts ABS and imagery features, predicts crossing and along-road peak-hour flows, and attaches existing AusRAP categories, bands and client-recoded estimates. It uses one input contract for surveyed, unknown and mixed batches. Observations are optional supplied fields, never predictors or automatically looked-up survey counts.

The model is `pedestrian-linear-v1`, exported from Yashika's saved R bundle without refitting. The feature set remains `commercial_buildings`, `footpath_both_sides`, and `abs_mb_category_simple`. Release SHA-256 is `f85f5ca240093c32cea2e4a023e6b0a73c38ff467c032747b70fd57f8c287042`. The reviewed imagery recipe and model coefficients have not changed during delivery cleanup.

Workflow version is `prediction_v2`, still selected through `configs/prediction/workflow_v1.json`. The main output is `prediction_output_v5`, 29 columns. The [AusRAP reference contract](04_prediction_pipeline/ausrap_reference.md) contains the ordered dictionary and matching rules. Production computes no MAE/RMSE and exports no per-side flow columns. `cway` remains location information and must not be mistaken for a side-flow output.

The independent [OOF workbook and report](../04_prediction_pipeline/irap_comparison/comparison_report.md) retain all 49 survey sites and paired evaluation of 45 crossing / 43 along-road sites. Those historic metrics are not recalculated by production inference. The final-model [ten-site example](../04_prediction_pipeline/prediction_example/README.md) replays saved features and makes no external requests.

The delivered [illustrated analysis report](../04_prediction_pipeline/irap_comparison/analysis_report.pdf) contains six figures, diagnostic statistics and all 49 site values. Along-road gains are widespread (36/43 sites); crossing gains are narrower (24/45 sites) and depend strongly on two influential improvements. These are descriptive analyses of the same saved OOF results. Diagnostic evidence is indexed [here](../04_prediction_pipeline/irap_comparison/evidence/analysis/README.md). The reviewed reports and historical provenance records are retained; their generation script is not included.

## Files and runtime requirements

| Purpose | Required material | Result |
| --- | --- | --- |
| Fresh location prediction | Filled batch template or CSV/Parquet; project package/configs/model; local Main Roads SLK snapshot; ABS Mesh Block counts; live ABS access and configured Maps/Gemini services; AusRAP Words source for references | `predictions.xlsx`, `predictions.manifest.json`, and imagery checkpoint |
| Offline demonstration | Delivered `evidence/saved_run.json`, project package/configs/model, Main Roads snapshot and Words source | Same 29-column predictions and reference schema, with saved-feature provenance |

The main road snapshot is `data/external_raw/main_roads_slk/road_slk.sqlite.gz`. ABS counts default to `data/external_raw/Mesh Block Counts, 2021.xlsx`. Existing references default to `data/raw/AusRAP Data - Words - MSDS.xlsx`. The current `data/processed/batch_input_dataset.xlsx` is a 20-location customer-use simulation: 10 observed and 10 random sites. The template independently retains a 100-location example (49 observed and 51 random); neither size is required by the service. The [input notes](../data/processed/README.md) and [current batch manifest](../data/processed/batch_input_dataset.manifest.json) describe the processed file; the [historical template preparation record](../data/templates/batch_input_example_100.manifest.json) retains the original sampling provenance. Local road checks have 18 matched / 2 ambiguous sites in the current batch, and 87 / 13 in the template. Valid entered coordinates allow prediction with a carriageway warning. These counts are local location checks, not live prediction success counts.

The shared Python setup uses 3.11 and `requirements.txt`. The local pre-existing `.venv` had a broken interpreter link during cleanup and was not reused. Verification used a separate Python 3.11 environment with the relevant pinned runtime and test dependencies. Recreate a machine-local environment using [setup](SETUP.md); do not distribute or depend on this machine's `.venv`. No fresh live-service batch or fresh R execution is claimed by this cleanup.

## Raw-source distribution policy (15 October 2026)

Files and subdirectories under `data/raw/` are now provisioned locally and excluded from Git; only the [raw-source setup guide](../data/raw/README.md) is versioned. Obtain the required CSV/XLSX files through the project handover and restore their exact relative paths before running dependent workflows. The Words workbook is required for operational AusRAP references and the complete offline replay; data reconciliation and historical evaluation need their additional documented sources. Processed datasets and reviewed research outputs remain versioned. Earlier dated merge-verification records describe file preservation at that time; this distribution policy changes Git tracking, not the locally retained data or model values.

## Reproduction and acceptance

After installing the project, run these from the repository root. Choose new output folders so reviewed results are not overwritten.

```bash
python tools/replay_prediction_example.py --output-directory outputs/predictions/example_reproduction
python -m pytest tests/unit/test_irap_comparison.py tests/unit/test_ausrap_reference.py tests/unit/test_model.py tests/integration/test_ausrap_client_parity.py tests/integration/test_prediction_workflow.py tests/integration/test_prediction_location.py tests/integration/test_prediction_tracer.py -q
```

The updated offline regression checks passed 184 tests and 36 subtests on 5 October 2026, including both the 20-row processed simulation and the 100-row template example with simulated feature providers. Three research-source test modules were excluded because the available test environment lacks `geopandas`; a complete-environment full-suite pass is not claimed. The ten-site offline replay also passed, with unchanged features and predictions, ten matched references, nine normal statuses and one retained imagery warning. Observations stayed blank and accuracy metrics were not computed. Fresh live ABS/imagery acceptance remains pending without a working Gemini key.

Customer prediction does not run OOF evaluation, refit models or require the historical research-input hash checks. Read the delivered reports directly. Optional research reproduction is documented separately in the [developer evaluation notes](05_model_evaluation/reproduction.md); the active reformatted training workbook currently differs from the pinned preflight file hash, so that developer command requires the reviewed research snapshot.

The [delivery verification](../04_prediction_pipeline/irap_comparison/evidence/delivery_verification.json) records final workbook hashes, English-cell checks, formula caches and native chart checks. Spreadsheet rendering was reviewed; Microsoft Excel application execution is not claimed. The maintained workbook builder was also exercised separately, with its chart compatibility repair.

For a live acceptance batch, use the chosen input sheet and run `pedflow-predict` into a fresh output folder. Resolve road-only ambiguities before running; a valid supplied coordinate permits prediction with a carriageway warning. Inspect `location_status`, `status`/`message`, and `comparison_status`/`comparison_notes` independently. Exit 0 reports prediction completeness, not AusRAP coverage. Unknown observed values must remain blank and failures must remain visible in output order. Resume only with a compatible existing checkpoint.

## Boundaries and remaining work

The previous 49-site location precheck found 36 matched / 13 ambiguous carriageways with road references; coordinate-only matching found 33 matched / 16 ambiguous roads. Entered coordinates remain usable when only carriageway matching is ambiguous; road-only inputs still need a unique position. The saved OOF evaluation does not depend on fresh imagery or rerunning those positions.

The AusRAP source contains 189,222 records. Whole-network prediction has not been run, and source records are not necessarily unique physical locations. Network prediction requires explicit prediction units, geometry and feature-coverage review, and a plan for external requests. Use the optional snapshot-bound `ausrap_record_id` when comparison should reference one original row rather than a ±0.1 km aggregate.

The OOF result is internal validation because model/feature selection used the survey data. Refitting without corrected sites `250341-04` and `260335-38` is outside the current agreed delivery scope and was not performed; no negligible-impact claim is made. Dashboard integration is outside this workflow update.

## Delivery structure and cleanup

`04_prediction_pipeline/` remains the numbered delivery hub, `src/pedflow/` remains the implementation, `06_outputs/` retains reviewed research evidence, and future unreviewed runs use Git-ignored `outputs/`. All maintained delivery documents and workbook definitions are English with no language suffix. Source datasets, scientific evidence, selected research results, model releases and pinned requirements remain in place.

Superseded working notes, historical outputs and intermediate research artefacts are retained under Git-ignored `07_test/`. The local cleanup manifest records original paths and file fingerprints for recovery. These backups are separate from maintained delivery files and runtime inputs.

Git changes that existed before cleanup were preserved, including the new evaluation/AusRAP modules and tests. This delivery does not create a commit or push. Include the active new source, tests, tools, English documents and `04_prediction_pipeline` files when the team reviews and commits the handover; do not commit `07_test` or credentials.

## Main-branch merge verification (15 October 2026)

The merge retains the approved research outputs, fitted research bundles, processed examples and compact source references. Their 34 retained files, excluding the reconciled raw-data README, match the pre-merge branch byte-for-byte. Microsoft building download caches remain Git-ignored. The superseded combined Google/Mapillary notebook is removed from the shared workspace; its local copy is retained under ignored `07_test/imagery_retired_20261015/`. The credential template has empty values. The [detailed model explanation](03_model_development/selected_model_details.md) preserves the incoming equations and interpretation with portable links and current example descriptions.

The complete collected Python suite passed **199 tests and 36 subtests** using Python 3.11.16 and the applicable dependencies pinned in `requirements.txt`. The ten-site offline replay passed with 29 output columns, unchanged saved features and predictions, ten matched AusRAP references, nine normal statuses and one retained warning. No external service requests, model training or fresh R execution were performed. Model release SHA-256 remains `f85f5ca240093c32cea2e4a023e6b0a73c38ff467c032747b70fd57f8c287042`.

The separate model-analysis directory reorganisation was saved before merging and remains available in the named Git stash `WIP: model analysis relocation before PR 8 merge`; it is not part of this reconciliation. Restore and review that work separately before publishing its files.
