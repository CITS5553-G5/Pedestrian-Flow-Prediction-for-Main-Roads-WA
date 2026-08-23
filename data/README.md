# Team data directory

This directory is versioned in the private team repository. It contains the source evidence and the three core tables needed to reproduce model development. Access is restricted to approved project collaborators.

## Folder contract

- `raw/` contains original client/source files. Treat these files as immutable: never edit, rename or overwrite them in place.
- `external_raw/` contains dated snapshots of external/public datasets used by the feature pipeline. Preserve the source date and provider path.
- `processed/` contains approved, reproducible project datasets. `model_dataset.csv` and `model_dataset.xlsx` are the current 49-site modelling foundation.
- `templates/` contains the blank batch-input and prediction-output schemas in CSV and Excel form.
- `work/`, `cache/` and `tmp/` are local scratch areas and are excluded from Git.

Large Excel, macro-enabled, FST, RData, compressed and road-network source files are stored through Git LFS according to `.gitattributes`. Collaborators must install Git LFS before cloning or pulling the complete data.

Do not place API keys, access tokens, downloaded street imagery, fitted models or disposable experiment outputs in this directory. Schema or source replacements should be reviewed by the team because Git LFS stores each changed binary file as a complete new version.
