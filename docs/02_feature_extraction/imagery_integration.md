# Imagery extraction

`src/pedflow/imagery/` implements the notebook recipe. The notebook and
`pedflow-imagery` call this shared module. Normal prediction uses
[the unified command](../04_prediction_pipeline/prediction_workflow.md).

## Configuration and recipe

`configs/prediction/imagery_v1.json` sets the model, sampling, concurrency, request
limits, timeouts and retries. Credentials are `GOOGLE_MAPS_API_KEY` and
`GEMINI_API_KEY`.

The recipe uses `gemini-3.7-flash`, the original 13-field prompt, a zoom-19 satellite
image (640×640, scale 2), and centre/N/S/E/W Street View images (640×640, heading 0,
pitch 0, FOV 90). The 50 m offset is measured in EPSG:3857 map coordinates.
Only `commercial_buildings` and `footpath_both_sides` are returned as model features.

Up to 50 workers take sites from a shared queue by default. Each LLM request contains images
from one site. Results return in input order. Local request pacing is disabled by
default for both Maps and Gemini: `maps_requests_per_minute` and
`llm_requests_per_minute` are `null`. Available workers start requests immediately,
without the former 120/30 requests-per-minute spacing. A positive number explicitly
enables pacing for that provider. This does not change provider/account quotas or
the separate maximum number of active sites (`--workers`).

Transient failures use bounded retries, backoff and `Retry-After`. Invalid
credentials and malformed feature responses fail without repeated calls. Raw
images stay in memory; available panorama dates, IDs and attribution are retained
in provenance.

The 21 September `run_001` completed 100 sites in 554 seconds using the old
120 Maps / 30 Gemini local limits. Its 481 Street View images imply 1,081 Maps
requests before retries, explaining approximately nine minutes of local pacing.
This identifies a local bottleneck, not the account's actual quota. Speed after
removing pacing still needs a fresh timed run; completed checkpoints skip extraction.

## Standalone extraction

```bash
pedflow-imagery --input data/processed/batch_input_dataset.xlsx --output-directory outputs/imagery_features/run_001
```

The command writes `imagery_features.csv`, `imagery_features.manifest.json` and
`imagery.checkpoint.json`. Add `--resume` to continue, or `--workers` to change
concurrency. Library callers load credentials before `build_imagery_features`.

## Status and recovery

| Status | Meaning | Resume |
| --- | --- | --- |
| `complete` | Both features available | Reuse |
| `needs_review` | At least one feature undetermined | Reuse; new checkpoint to re-extract |
| `no_imagery` | Image service returned 404 | Retry |
| `failed` | Request or response failure | Retry |

Missing Street View with usable aerial imagery is flagged `aerial_only`. Feature
failures retain nulls. The prediction workflow blocks incomplete features and
preserves coverage warnings.

Each completed site is saved atomically before progress is reported. A lock
prevents simultaneous checkpoint writers. Changed sites, coordinates or recipes
reject reuse. In-flight requests interrupted before saving may repeat on resume.
Exit codes are `0` all complete, `2` some incomplete and `1` input/configuration error.

## Validation

Offline tests cover concurrency, ordering, optional pacing, retries, failure isolation
and checkpoint recovery. The live timing above establishes the previous configuration's
throughput; throughput with pacing disabled and feature equivalence remain unverified.
The historical training workbook lacks complete imagery provenance; compare a reviewed
live sample with training features before client delivery.

The original notebook is preserved locally under
`07_test/imagery_before_migration_20260920/`. Do not publish this archive: historical
cells or outputs may contain credentials.
