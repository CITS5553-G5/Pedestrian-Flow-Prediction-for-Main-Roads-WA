# Immutable raw data

Files in this directory are source evidence shared through the private team repository. Do not edit, overwrite, rename, or delete them during cleaning or analysis.

The supplied sources include:

- three batches of macro-enabled pedestrian survey workbooks;
- `Road_Network.csv` with Road Number and SLK intervals;
- a large AusRAP road-segment workbook containing road attributes and raw BF/BG/BH exposure categories;
- the client `Ped_iRAP_merged` files and R linkage scripts.

Binary and large files are managed by Git LFS.

Write extracted, cleaned and feature-engineered forms to `../processed/` only when they are approved team datasets. Put disposable intermediate files under `../work/`, which is excluded from Git.
