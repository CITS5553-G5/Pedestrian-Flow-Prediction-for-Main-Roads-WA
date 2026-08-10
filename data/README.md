# Local data directory

Client data are stored locally and are not committed to GitHub.

- `raw/` contains original client files and must never be modified by processing scripts.
- `work/` may be created locally for cleaned, linked and feature-engineered tables.
- Generated model inputs must be reproducible from declared source files and Python scripts.

The current source files include the AusRAP data workbook, Road Network CSV, survey workbooks and related client-provided source files. Do not copy these files into another tracked directory.
