# End-to-End Workflow

Status: authoritative architecture and incremental delivery plan  
Last reviewed: 20 September 2026

## Purpose

The delivered system should let a client submit a batch of locations and receive
predictions without opening notebooks or running the project stages one by one.
Notebooks remain important for research, teaching, model comparison and scientific
evidence, but they are not the production workflow.

The formal workflow has one implementation under `src/pedflow/`. Batch processing
and the future dashboard are two interfaces to that same implementation. This rule
prevents notebook code, batch code and dashboard code from producing different
answers.

## System boundary

The client-facing prediction path is:

```text
batch workbook or dashboard request
                |
                v
        input contract validation
                |
                v
   required context and imagery features
                |
                v
     released preprocessing and model
                |
                v
 predictions, row status and provenance
                |
                v
 output workbook or dashboard response
```

Training is a separate, team-controlled process. It builds and evaluates candidate
models, then publishes one approved model release. Client prediction loads that
release; it must not retrain a model.

## Current project status and planned additions

Context and imagery feature extraction have both been completed for the current
project dataset. Context extraction has already been promoted into the formal
`src/pedflow/context/` workflow. Its formal configuration and default registry now
run ABS only (`context_abs_v1`), validate a common site table and retain ABS match
status and provenance. Historical candidate sources remain available for research
with explicit source registration and the preserved `configs/research/` settings.
The ABS calculation itself is unchanged; its category is simplified by the model
input mapping when assembling the three selected features.

Imagery extraction was completed and is currently preserved in the shared imagery notebook. Its scientific work is complete; its remaining engineering task is to move the stable calculation into `src/pedflow/imagery/` so that the future prediction service can call it without executing the notebook.

EDA and model comparison are complete. The team selected Yashika's parsimonious
log1p linear regressions with three features. The saved R models are now exported
as the versioned `pedestrian-linear-v1` release, with Python inference under
`src/pedflow/modeling/` and independent R/Python parity checks. Training remains in
the R research workflow. Feature orchestration and the backend connection have
not yet been implemented. The application frontend therefore remains a user
interface demonstration rather than evidence of live model predictions. See the
[selected-model integration guide](03_model_development/selected_model_integration.md).

The package should grow incrementally in this form:

```text
src/pedflow/
├── context/       # implemented context feature workflow
├── imagery/       # next integration: implement notebook logic
├── modeling/      # implemented: selected model release and Python inference
├── prediction/    # planned: the single client prediction workflow
└── api/           # planned only when the dashboard backend is connected
```

The names describe business responsibilities, not individual contributors or
notebook numbers. A package should be created when there is tested code to place in
it, not in anticipation of possible work.

## Responsibilities and dependency direction

| Component | Responsibility | May depend on |
| --- | --- | --- |
| Research notebooks | Exploration, explanation, visual checks and scientific decisions | Public functions in `src/pedflow` |
| `context` and `imagery` feature components | Produce validated feature tables | Shared contracts, configuration and source adapters |
| `modeling` component | Assemble approved training data, evaluate candidate models and create a release | Feature contracts and approved training datasets |
| Future `prediction` package | Validate client input, request required features, load a release and predict | Feature packages and the model release |
| Future backend/API | Translate web requests and responses | Public prediction service only |
| Frontend | Collect input and display returned results and statuses | Backend API only |

Dependencies flow towards the shared implementation. Production modules must not
import notebooks. Feature extractors must not import the prediction layer, and the
frontend must not contain feature or model formulas.

## Operating workflows

The project has three related workflows, but only one of them is run by the client.

| Workflow | Current status | Main result | Operator |
| --- | --- | --- | --- |
| Feature development | Context and imagery extraction completed | Tested feature components and versioned feature definitions | Project team |
| Model development | Selected R models exported; Python inference verified | Versioned model release; training remains in R | Project team |
| Client prediction | Not yet implemented | Predictions, row statuses and provenance | Client or application |

Feature and model development prepare the reusable components. They are not stages
that the client runs before every prediction. The operational relationship is:

```text
team development
    feature notebooks -> tested feature modules ─┐
    model notebooks   -> approved model release ─┤
                                                 v
client operation
    batch input or dashboard -> prediction service -> results
```

Notebooks retain the reasoning and visual evidence. Stable calculations move to
`src/pedflow/`, and the notebooks call those modules when they need to reproduce a
result. Detailed module-promotion rules are defined in
[`MODULE_INTEGRATION_GUIDE.md`](MODULE_INTEGRATION_GUIDE.md).

## Interfaces between components

Four contracts connect the system:

| Contract | Defines |
| --- | --- |
| Input | Required site identifiers, coordinates, types and validity rules |
| Feature | Feature names, types, units, missing-value meanings and source versions |
| Model release | Required features and order, fitted preprocessing, targets and compatible versions |
| Output | Predictions, row status, warnings, model version and feature provenance |

The prediction service validates each contract before moving to the next component.
It must reject duplicate or invalid sites, incomplete feature coverage and an
incompatible model release rather than silently repairing them. Missing source data
must remain distinguishable from a measured zero.

## One prediction service, two client interfaces

Batch processing and the dashboard are adapters around the same prediction service:

```text
batch workbook ──> batch adapter ──┐
                                   ├──> prediction service ──> validated results
dashboard ───────> backend API ────┘
```

The batch adapter handles workbook reading and writing. The backend handles web
requests and responses. Neither contains feature calculations, preprocessing or
model logic. The frontend only displays values and statuses returned by the backend.

The intended client command may later be registered as `pedflow-predict`; it does
not exist yet. The existing `pedflow-context` command is a developer and feature
workflow entry point, not a sequence the client must run manually.

## Delivery order

1. Promote the completed imagery extraction into an Imagery package and verify that Context and Imagery follow the same site-level contract.
2. Retain the completed candidate comparison and selected three-feature model as the scientific baseline.
3. Use the published model release and verified Python inference; promote reusable training code when extending the training workflow.
4. Build the Prediction package to combine the Context and Imagery features required by that release.
5. Expose the Prediction service through one batch command and then through the dashboard backend.

Client acceptance begins only when a clean installation can process a sample batch
without notebooks, report invalid inputs clearly and return equivalent prediction
content through batch and dashboard interfaces.
