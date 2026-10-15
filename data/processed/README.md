# Processed tables

Prediction accepts any positive number of locations. Save the desired locations in an input workbook, CSV or Parquet table and select it with `--input`; the populated input rows determine the batch size. There is no required observed/random split, and the input does not need to match the template's example rows. All locations use the same released-model workflow. Observed counts are optional and remain blank when unknown.

The [current batch manifest](batch_input_dataset.manifest.json) records the delivered processed example, and the template's [historical preparation record](../templates/batch_input_example_100.manifest.json) records its original sample. Neither manifest is required for new prediction inputs; each run writes its own metadata automatically. `sampling_source_row` is provenance only; comparison still uses road/SLK +/- 0.1 km aggregation.

When valid coordinates are supplied, carriageway ambiguity remains a warning and does not block extraction or prediction. Road-only ambiguity still requires `cway` to determine a unique coordinate. `location_precheck` is a dated annotation; the workflow recomputes matching. Road-matching results are distinct from prediction success counts. No fresh live ABS/imagery acceptance run is claimed.

Use the [template layouts](../templates/README.md) for new batches of any positive size. To run a subset, copy its rows into a separate input file; hiding or filtering Excel rows does not remove them from pipeline input. Optional group/source/audit fields are not predictors and do not change the 29-column output. Join annotations by `site_id`. `model_dataset.xlsx` remains the separate 49-site research dataset; production prediction does not require running OOF evaluation.

## Delivered example snapshots

The current processed example contains 20 locations: 10 observed and 10 random. Its dated road precheck records 18 matches and two carriageway ambiguities. The template example contains 100 locations: 49 observed and 51 random, sampled with seed `20261004`; its precheck records 87 matches and 13 ambiguities. These are descriptions of the delivered examples, not allowed batch sizes, required group counts or limits on another input file.
