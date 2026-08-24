# Curated source inputs

The private team repository tracks only source inputs that are directly required by the current project workflow. Do not edit or overwrite these files during cleaning or analysis.

The tracked sources are:

- `Ped_iRAP_merged.csv`, the compact client-derived target source used to check most site targets in `../processed/model_dataset.xlsx`;
- `Road_Network.csv`, used to resolve Road Number and SLK intervals;
- `AusRAP Data - Words - MSDS.xlsx`, used for road-segment matching and retained road attributes.

The 147 macro-enabled observation workbooks, R linkage files and duplicate FST form are excluded from the current Git tree. The observation workbooks are already consolidated into the 49-site modelling table and are only required when the team needs to reconstruct or audit the target aggregation. Keep them in approved archival storage; do not copy them into a public service.

Candidate PBI index files are also excluded until the team selects them as model features and implements a reproducible join. Write approved, cleaned and feature-engineered forms to `../processed/`. Keep disposable intermediate files outside `data/` and Git.
