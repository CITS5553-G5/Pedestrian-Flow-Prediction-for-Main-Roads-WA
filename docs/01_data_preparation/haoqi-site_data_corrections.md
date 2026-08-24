# Site-level data reconciliation

## Process name and purpose

The work completed for the flagged survey sites is **source-traceable site reconciliation and correction**. It is a data-quality process that compares a consolidated table with the underlying survey workbooks and road-reference sources, identifies the cause of a disagreement, and records a defensible correction in the modelling dataset.

This was not generic missing-value imputation. Four issue cases affected five site rows: one two-day-versus-three-day aggregation error, one road-code issue affecting two sites, one special workbook-layout error, and one site absent from the consolidated client table.

## Sources used

The reconciliation used the following source hierarchy:

1. Archived raw survey workbooks and their embedded hourly summaries for observed pedestrian counts.
2. `data/raw/Ped_iRAP_merged.csv` as the compact client-derived target table.
3. `data/raw/Road_Network.csv` for road-number and SLK validation.
4. `data/raw/AusRAP Data - Words - MSDS.xlsx` for road-segment and coordinate linkage.
5. `data/processed/model_dataset.xlsx` as the authoritative reconciled project table.

The archived macro-enabled survey workbooks remain outside Git. They are audit sources, not routine model inputs, and must not be overwritten.

## Reconciliation method

For every flagged site, the process was:

1. Retain the original identifier or compact-table value for traceability.
2. Inspect the workbook layout and identify the actual 15-minute and embedded hourly tables.
3. Reconstruct the target rule separately for across-road and along-road movement: calculate hourly values, average the three survey days at each time point, then take the maximum of the mean hourly profile.
4. Compare the reconstructed values with the compact client table and the workbook's embedded hourly values.
5. Validate road number and SLK against Road Network and AusRAP sources.
6. Correct only the fields supported by agreeing evidence, record the reason in `qa_note`, and set `qa_status` to `ready` only after reconciliation.

## Issue and correction record

All pedestrian-flow values below are pedestrians per hour.

| Issue case | Site row(s) | Original problem | Evidence and diagnosis | Authoritative change |
|---|---|---|---|---|
| Two-day aggregation used instead of three days | `250341-04` | The compact table stored cross-road `125` and along-road `25.5`, which did not match a three-day reconstruction. | Those values exactly reproduce a Thursday-Friday average. All three raw survey days and the embedded hourly values agree on cross-road `87` and along-road `17.3333`. | Targets changed to `87` and `17.3333`; `target_source` records the three-day raw-workbook reconstruction. |
| Incorrect road number | `260335-31`, `260335-32` | The client identifier used `M010` for Coolgardie Esperance Highway. | Road Network identifies `M010` as Chidlow York Road and places SLK `366.85` and `165.45` on `H010`, Coolgardie Esperance Highway. Raw target values were reproducible and did not require correction. | `road_no` and `location_id` use `H010`; `source_location_id` retains the original `M010` values for traceability. Targets remain `3`/`8.3333` and `2`/`12.3333` respectively. |
| Special workbook layout interpreted twice | `260335-38` | The compact table stored along-road `29.6667`; the site workbook did not follow the standard layout. | The workbook contains one actual 15-minute along-road table. Treating its embedded hourly columns as another 15-minute input caused double interpretation. The real 15-minute series and embedded hourly values both give along-road `18.3333`; cross-road `4.3333` was already correct. | Along-road target changed to `18.3333`; cross-road remains `4.3333`; the schema-aware reconstruction is recorded in `target_source` and `qa_note`. |
| Site missing from compact table and filename locality error | `260335-40` | The site was absent from `Ped_iRAP_merged.csv`, and the filename referred to Norseman. | Three raw survey workbooks and their embedded hourly values agree on cross-road `53.6667` and along-road `66.3333`. The internal workbook label states `NWCH Northampton`, consistent with H007 SLK 52.5. | Targets reconstructed as `53.6667` and `66.3333`; the survey label is standardised to North West Coastal Highway, Northampton; the raw-workbook derivation is recorded. |

## Result and modelling treatment

After reconciliation, `model_dataset.xlsx` contains 49 unique `site_id` values, 49 unique `location_id` values and 49 rows with `qa_status = ready`.

The primary model may use all 49 sites. Because `250341-04` and `260335-38` contain corrected target values, final evaluation must also repeat the selected modelling procedure without those two sites. This sensitivity check determines whether either correction materially changes the reported model conclusion.

## Reproducibility rule

Any future correction must preserve the raw source, record the original and replacement values, name the evidence used, update `qa_note`, and rerun the 49-row uniqueness and readiness checks. A row must not be marked `ready` merely to increase the training sample size.
