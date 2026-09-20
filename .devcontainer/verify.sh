#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="/opt/pedflow-venv/bin:$PATH"

python -m pip check
python - <<'PY'
import json
import platform
import sys

import geopandas
import google.genai
import ipykernel
import pandas
import pedflow
import sklearn
import statsmodels.api
import xgboost

with open('.devcontainer/devcontainer.json') as stream:
    config = json.load(stream)
expected = config['features']['ghcr.io/devcontainers/features/python:1']['version']
assert platform.python_version() == expected, (platform.python_version(), expected)
assert sys.prefix == '/opt/pedflow-venv', sys.prefix
print(f'Python {expected}: project imports OK')
PY
pedflow-context --list-sources
python -m pytest -q

node --input-type=module - <<'JS'
import fs from 'node:fs';
const config = JSON.parse(fs.readFileSync('.devcontainer/devcontainer.json', 'utf8'));
const expected = config.features['ghcr.io/devcontainers/features/node:1'].version;
if (process.versions.node !== expected) throw new Error(`Expected Node ${expected}, got ${process.versions.node}`);
console.log(`Node ${expected}: OK`);
JS
(cd 05_application/frontend && npm ci && npm run lint && npm run build)

Rscript --vanilla .devcontainer/restore-r.R --check
Rscript --vanilla - <<'RS'
packages <- c("rmarkdown", "glmnet", "ranger", "gbm", "readxl",
              "PerformanceAnalytics", "fst")
for (package in packages) stopifnot(requireNamespace(package, quietly = TRUE))
work <- tempfile("pedflow-render-")
dir.create(work)
input <- file.path(work, "smoke.Rmd")
writeLines(c("---", 'title: "Environment check"', "output: html_document",
             "---", "", "```{r}", "summary(cars)", "plot(cars)", "```"), input)
for (format in c("html_document", "pdf_document")) {
  output <- rmarkdown::render(input, output_format = format, quiet = TRUE)
  stopifnot(file.exists(output), file.info(output)$size > 0)
  cat(format, ": OK\n")
}
unlink(work, recursive = TRUE)
RS
