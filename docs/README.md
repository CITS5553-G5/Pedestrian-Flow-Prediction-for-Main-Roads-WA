# Project documentation

This directory has two authoritative, project-wide guides. Start with
[`END_TO_END_WORKFLOW.md`](END_TO_END_WORKFLOW.md) to understand how research,
feature extraction, model training, prediction and the dashboard fit together.
Use [`MODULE_INTEGRATION_GUIDE.md`](MODULE_INTEGRATION_GUIDE.md) when moving a
team member's validated notebook code into the formal workflow.

These guides are deliberately stored directly in `docs/` so they are visible and
easy to find. There is no separate `CONTRIBUTING.md`: the contribution rules below
are the common rules for this repository. Detailed evidence that belongs to one
project stage remains in its existing stage subdirectory instead of being copied
into a second project-wide guide.

## Reference documents

| Location | Scope |
| --- | --- |
| `01_data_preparation/` | Shared table formats and verified source-data corrections |
| `02_feature_extraction/` | Reviewed feature definitions and feature summaries |
| `03_model_development/` | Scientific modelling and feature-selection guidance |

Detailed source research and personal implementation notes may remain local when
they are not shared project evidence. Confirmed team decisions, contracts and
operating instructions must be committed in an appropriate shared document.

## Contribution rules

The numbered project folders are workspaces for notebooks, experiments, evidence
and explanation. Formal reusable code belongs under `src/pedflow/`. A notebook may
call the package, but production code must never depend on executing notebook cells
or on hidden notebook state.

Each calculation has one authoritative implementation. Do not retain a notebook
copy and a Python-module copy that must be updated independently. After stable logic has been promoted, change the notebook to import the shared function while keeping the notebook's narrative, visual checks and interpretation.

Configuration belongs under `configs/`, automated checks under `tests/`, and
generated local results under ignored output or cache locations. Commit a reviewed
output only when teammates or project evidence genuinely require it. Never commit
credentials, tokens or private client data.

Before merging a workflow change, the contributor must confirm that inputs and
outputs have explicit contracts, paths are configurable, failures are clear,
provenance is recorded where relevant, and focused tests cover both success and an
important failure case. Run the affected tests and record any external-data or
licensing assumptions in the pull request or associated project documentation.

Documents must distinguish current implementation, approved decisions and future
proposals. Do not describe a planned model, prediction command or dashboard
connection as operational until it is implemented and tested.
