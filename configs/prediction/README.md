# Prediction configuration

These files define the maintained operational workflow. Paths inside them are relative to the repository root; credentials are read from the local environment or root `.env` file.

| File | Controls |
| --- | --- |
| [workflow_v1.json](workflow_v1.json) | Workflow version, feature configuration paths, model release, model/recipe fingerprints and local AusRAP source |
| [context_abs_v1.json](context_abs_v1.json) | ABS source settings, counts workbook, and standalone Context input/output defaults |
| [imagery_v1.json](imagery_v1.json) | Imagery model and prompt, sampling, worker count, timeouts, retries and optional request pacing |

The workflow filename is retained as `workflow_v1.json`, with current `workflow_version` `prediction_v2`. The release is `pedestrian-linear-v1`, and workbook export uses `prediction_output_v5`. Production Context uses ABS only; other source configurations remain under [research](../research/README.md).

The maintained imagery configuration uses 50 concurrent sites. Maps and Gemini local RPM limits are both `null`, meaning disabled. `--workers` overrides concurrency for a command run; concurrency is not a service quota. The [imagery guide](../../docs/02_feature_extraction/imagery_integration.md) describes requests, checkpoints and recovery.

Worker counts, timeouts and request pacing can be adjusted without changing the feature recipe. Changes to the model release, imagery model, prompt or sampling require reviewed version/fingerprint updates in the workflow configuration. The unified prediction command uses its own `--input`, `--sheet` and `--output-directory` arguments; the Context configuration's input/output sections apply to standalone `pedflow-context` runs. See the [run guide](../../docs/04_prediction_pipeline/prediction_workflow.md) for operational use.
