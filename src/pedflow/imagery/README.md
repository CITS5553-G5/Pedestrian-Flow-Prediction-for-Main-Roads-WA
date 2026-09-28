# Imagery: Image feature extraction

This module retrieves Google satellite and Street View images for each site and
uses Gemini to assess visible features. The current model features are
`commercial_buildings` and `footpath_both_sides`.

## File responsibilities

| File | Purpose |
| --- | --- |
| [__main__.py](__main__.py) | Entry point for `pedflow-imagery` / `python -m pedflow.imagery`; load `.env`, arguments and configuration, then extract and export |
| [contracts.py](contracts.py) | Define `ImageryConfig`, `ImageryResult` and safe error types; load prompts and fingerprint extraction settings |
| [workflow.py](workflow.py) | Implement `build_imagery_features`: validate sites, manage concurrent tasks, isolate site failures, save progress and restore input order |
| [providers.py](providers.py) | Retrieve images for one site, call Gemini, validate count and boolean fields in JSON, and record imagery provenance |
| [requests.py](requests.py) | Rate-limit Maps and Gemini separately and apply bounded retries with backoff for transient failures |
| [checkpoint.py](checkpoint.py) | Manage progress files and write locks; check whether inputs and extraction settings permit reuse of saved records |
| [io.py](io.py) | Export feature CSV and manifest; retain the legacy `read_sites` import while delegating reads to shared `pedflow.io` |
| [prompts/notebook_v1.txt](prompts/notebook_v1.txt) | Preserve the full prompt migrated from the original notebook |
| [__init__.py](__init__.py) | Expose configuration, results and interfaces including `build_imagery_features` |

## Execution flow

```text
__main__.py → Load configuration, API keys and sites
  → workflow.py
      → checkpoint.py: read and validate saved progress
      → Concurrent tasks: one site per task
          → providers.py: satellite + Street View → Gemini → two features
              → requests.py: rate limits and retries for each external call
      → checkpoint.py: save each completed site
      → Assemble ImageryResult in input order
  → io.py: export CSV and manifest
```

By default, up to ten sites run concurrently. As one finishes, the next starts
without waiting for a fixed group to complete. Each Gemini request contains
images from one site only.

## Inputs, outputs and configuration

The entry point is `build_imagery_features(sites, config, checkpoint_path=..., resume=False)`.
Input is a site table containing `site_id`, WGS84 coordinates and CRS. The returned
`ImageryResult` contains `features` with both features, statuses, warnings and
processing times, and `metadata` with settings and imagery provenance.

Settings are in [imagery_v1.json](../../../configs/prediction/imagery_v1.json).
Both `GOOGLE_MAPS_API_KEY` and `GEMINI_API_KEY` are required. The command loads the
project `.env` automatically; callers of the Python interface must load environment
variables themselves. See the [project guide](../../../README.md) for setup.

The prompt still requests the original 13 fields, but `providers.py` retains only
the two model features. Editing the prompt changes the extraction fingerprint,
requires revalidation and an updated version binding, and prevents direct reuse
of old checkpoints.

## Statuses and resume behavior

| Status | Meaning | Resume behavior |
| --- | --- | --- |
| `complete` | Both features are available | Reuse |
| `needs_review` | At least one feature cannot be determined | Retain; use a new checkpoint to extract again |
| `no_imagery` | An imagery service returned 404 | Retry |
| `failed` | A request or result validation failed | Retry |

Unavailable or indeterminate features remain missing rather than becoming zero
or False. Raw images are held in memory and released after processing; checkpoints
store features and provenance, not images. Prediction checks the returned statuses
and uses only complete features that meet the model's input requirements.
