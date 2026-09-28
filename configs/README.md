# Configuration

| File | Purpose |
| --- | --- |
| `prediction/workflow_v1.json` | Bind the Context, Imagery and model versions |
| `prediction/context_abs_v1.json` | ABS source and counts workbook path |
| `prediction/imagery_v1.json` | Gemini model, image sampling, concurrency, optional local pacing (`null` = disabled) and retries |
| `research/` | Historical experiment settings |

Paths inside configurations are relative to the project root. API keys belong in
`.env`. Batch input and output paths are supplied to `pedflow-predict`.

The Context configuration's `input` and `output` sections apply only to the
standalone `pedflow-context` command; the unified command uses its own arguments.

Worker counts, request limits and timeouts may be adjusted without changing the
extraction recipe. Changing the model release, Gemini model, prompt or image
sampling requires a reviewed update to the hashes in `workflow_v1.json`.
