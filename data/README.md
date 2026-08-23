# Team data directory

This directory is versioned in the private team repository. It contains only the source files directly needed by the current pipeline and the three core project tables. Access is restricted to approved project collaborators.

## Folder contract

- `raw/` contains the curated client/source inputs used for target checking, road matching and AusRAP feature linkage. Treat tracked source files as immutable.
- `external_raw/` contains dated snapshots of external/public datasets used by the feature pipeline. Preserve the source date and provider path.
- `processed/` contains approved, reproducible project datasets. `model_dataset.csv` and `model_dataset.xlsx` are the current 49-site modelling foundation.
- `templates/` contains the blank batch-input and prediction-output schemas in CSV and Excel form.
- `work/`, `cache/` and `tmp/` are local scratch areas and are excluded from Git.

The 147 macro-enabled observation workbooks are not routine project inputs because their site-level results have already been consolidated. They remain in approved archival storage outside the current Git tree and are needed only if the target aggregation must be independently reconstructed. Candidate datasets that have not been selected for the model are also excluded until a documented pipeline uses them.

Large Excel, compressed and road-network source files that remain directly necessary are stored through Git LFS according to `.gitattributes`. Collaborators must install Git LFS before cloning or pulling the complete data.

Do not place API keys, access tokens, downloaded street imagery, fitted models, archival survey workbooks or disposable experiment outputs in this directory. Schema or source replacements should be reviewed by the team because Git LFS stores each changed binary file as a complete new version.
