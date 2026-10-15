# Configuration

| File | Purpose |
| --- | --- |
| [prediction/workflow_v1.json](prediction/workflow_v1.json) | Bind the Context, Imagery and model versions and local AusRAP reference source |
| `prediction/context_abs_v1.json` | ABS source and counts workbook path |
| `prediction/imagery_v1.json` | Gemini model, image sampling, concurrency, optional local pacing (`null` = disabled) and retries |
| [research](research/README.md) | Historical experiment settings |

Paths inside configurations are relative to the project root. API keys belong in
`.env`. Batch input and output paths are supplied to `pedflow-predict`.
The [prediction configuration guide](prediction/README.md) records current versions,
concurrency and standalone versus unified command settings.

The Context configuration's `input` and `output` sections apply only to the
standalone `pedflow-context` command; the unified command uses its own arguments.

Worker counts, request limits and timeouts may be adjusted without changing the
extraction recipe. Changing the model release, Gemini model, prompt or image
sampling requires a reviewed update to the hashes in `workflow_v1.json`.

The filename `workflow_v1.json` is retained for existing commands; its current
`workflow_version` is `prediction_v2`. The optional `ausrap_source` defaults to
`data/raw/AusRAP Data - Words - MSDS.xlsx`. A missing/unreadable reference source
is reported as `source_unavailable`, without discarding model predictions.
Legacy `prediction_v1` configurations remain readable and use the same default
reference source. Model and feature recipe hashes are unchanged.
