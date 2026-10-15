# Templates

`batch_input_template.xlsx` provides field layouts for batches of any positive size. Replace the example rows with your locations, adding or removing rows as needed, and save a separate input workbook. The selected input's populated rows determine the batch size; no fixed location count or observed/random split is required. The [processed input](../processed/README.md) is a separate supplied example, and its rows need not match the template.

`Batch_Input` supports road references and coordinates; `Road_SLK` and `Coordinates` are blank alternative layouts, with optional observed-count columns. `Road_SLK` accepts road number plus point SLK, or complete segment bounds; `Coordinates` accepts WGS84 latitude/longitude. Copy and fill one layout, then select your workbook with `--input` and its sheet with `--sheet`. Excel filters do not restrict the rows read by the pipeline.

`prediction_output_template.xlsx` is the maintained styled layout for `Prediction_Output`, `Features` and `Metadata`; the exporter fills it for any batch size. `model_dataset_template.xlsx` preserves the original modelling workbook for reference.

The prediction template now uses `prediction_output_v5`: 29 output columns and an English field dictionary, including existing AusRAP categories, derived bands and **Existing iRAP flow estimate (recoded)**. The input template and output filenames are unchanged. Observed counts are optional and stay blank for unknown sites. A processed input may optionally add `ausrap_record_id` for an exact original AusRAP record; see the [matching contract](../../docs/04_prediction_pipeline/prediction_workflow.md). No MAE/RMSE or separate side-flow columns are added.

## Delivered example snapshot

The populated `Batch_Input` example currently contains 100 locations: 49 observed sites and 51 sampled random locations. Its observations, carriageways, groups, provenance and prechecks describe that sample only. Thirteen sample sites have carriageway ambiguity; their supplied coordinates still allow prediction with a road warning. `Metadata` defines the fields and original sampling method, while the [historical preparation record](batch_input_example_100.manifest.json) preserves original provenance and historical hashes. These sample counts do not constrain newly prepared inputs.
