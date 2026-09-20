# Workflow Module Integration Guide

Status: required team integration rules  
Last reviewed: 16 September 2026

## Purpose

This guide explains how a team member turns validated notebook work into code that
participates in the end-to-end workflow. It applies to context extraction, imagery
extraction, model training, prediction and the future backend. The architecture and
system boundaries are defined in [`END_TO_END_WORKFLOW.md`](END_TO_END_WORKFLOW.md);
this document defines the contribution interface.

The central rule is that a contributor supplies an importable module with explicit
inputs and outputs, not a standalone script that expects a person to run it before
the next stage. The workflow orchestrator calls modules. A user-facing command is a
thin entry point into an orchestrator and is registered in `pyproject.toml`; it is
not a second implementation.

## Where code belongs

| Contribution | Formal location | Research or explanation location |
| --- | --- | --- |
| New context data source | `src/pedflow/context/sources/<source_name>.py` | `02_feature_extraction/context/` |
| Imagery feature logic | `src/pedflow/imagery/` when the first module is ready | `02_feature_extraction/imagery/` |
| Reusable training and evaluation logic | `src/pedflow/modeling/` when ready | `03_model_development/` |
| Client prediction orchestration | `src/pedflow/prediction/` when ready | `04_prediction_pipeline/` for interface evidence only |
| Dashboard request adapter | `src/pedflow/api/` when the backend is implemented | `05_application/` |
| Runtime choices | `configs/` | Explain important decisions in the relevant notebook or document |
| Automated verification | `tests/unit/`, `tests/integration/` and small fixtures | Notebooks may show additional visual checks |

Use lowercase `snake_case` module names that describe the domain or source, not a
team member, notebook number or temporary experiment. Public function names should
describe an action, such as `extract_*`, `build_*`, `train_*` or `predict_*`.

Do not create an empty package just to reserve a future name. The first contributor
to a planned area should add the smallest coherent package together with its public
contract and tests.

## Rules shared by every module

Every module receives its data and configuration through function arguments. It
must not depend on notebook variables, the current working directory, a developer's
absolute path or a manually executed earlier file. Repository paths are resolved
from an explicit project root or configuration.

Separate external input/output from deterministic transformation where practical.
This makes scientific calculations testable without network calls and lets source
downloads use controlled timeouts, retries and caches. A low-level source module
returns data to its orchestrator; it does not write the final integrated workbook
or modify the model dataset itself.

Errors must be specific and actionable. Do not silently drop sites, repair duplicate
identifiers, interpret unavailable data as zero, or continue with an incompatible
schema. Use the shared exception types in `src/pedflow/exceptions.py` where they fit.

Feature names, units, category meanings and missing-data behaviour are part of the
public interface. Renaming a released field or changing its meaning requires a new
feature-set version and corresponding model compatibility decision.

External-source modules must record enough provenance to reproduce or audit the
result, including a source identifier, version or retrieval date and material
options. Respect source licensing, retention and attribution requirements. Tokens
and credentials come from the runtime environment and must never appear in tracked
files or test fixtures.

Comments should explain scientific assumptions, safety checks and non-obvious
decisions. They should not narrate self-evident Python line by line. Keep public
functions small enough to test, but do not introduce layers that serve no current
requirement.

## Context source contract

The context package already provides a working integration pattern. A source module
exports one `SourceDefinition`. Its extractor has this interface:

```python
def extract_features(
    sites: pandas.DataFrame,
    config: SourceConfig,
    project_root: pathlib.Path,
) -> FeatureResult:
    ...


DEFINITION = SourceDefinition(
    name="source_name",
    description="Short source and feature description.",
    column_prefixes=("source_",),
    extractor=extract_features,
)
```

The `sites` table has already passed the common input validation and contains
`site_id`, `latitude`, `longitude` and `coordinate_crs`. The extractor must return a
`FeatureResult` whose `features` value is a pandas DataFrame with exactly one row for
every input `site_id`. It must not add, remove or duplicate sites. Every feature
column other than `site_id` must use one of the prefixes declared in the definition,
and the result must not contain target-derived fields.

`source_version` must identify the data used well enough for provenance. Put
machine-readable run information in `metadata` and non-fatal, interpretable issues
in `warnings`. Do not use warnings to hide contract violations or a mandatory-source
failure.

To integrate a context source:

1. Confirm the source, feature definitions, licence, access method, units and missing-value semantics in the notebook.
2. Move reusable retrieval, cleaning and calculation functions into one source module under `src/pedflow/context/sources/`.
3. Export `DEFINITION`. The selected model's `build_default_registry()` contains ABS only; add another source there only when an approved model release requires it. Research workflows pass an explicit source registry instead.
4. Add its options and enabled state to the appropriate versioned file under `configs/`; do not hard-code local paths in the module.
5. Add unit tests for deterministic calculations and validation, plus mocked or fixture-based tests for external I/O.
6. Run a small integrated context build and confirm exact site coverage, stable names, provenance and output types.
7. Change the research notebook to import the promoted functions if it still demonstrates the calculation; do not keep a second maintained implementation.

The existing Google Places Aggregate module is an exclusion guard, not an approved
source example. Do not enable or replace that guard without a new documented UWA
decision.

## Imagery module contract

An imagery extractor should follow the same boundary even though its data types may
differ. It receives validated site records and source configuration, obtains or
loads imagery through a controlled adapter, returns one feature record per
`site_id`, and reports source and processing provenance. Downloading, image
selection, inference and site-level aggregation should be separable enough to test
with local fixtures.

Before promotion from a notebook, define image ownership and licence conditions,
selection radius or view rules, date and quality rules, feature vocabulary, units,
aggregation and missing-image behaviour. Distinguish "feature not visible" from
"no usable image" and "source request failed"; these states must not all become
numeric zero. Cache behaviour, request limits and model weights must be configurable.

The first imagery contributor should define a small result contract analogous to
the context result rather than importing context-specific classes by convenience.
The future prediction orchestrator should combine the validated context and imagery
tables on `site_id`; individual source modules must not join themselves directly to
the final client output.

## Modelling module contract

Model-development notebooks remain the place to compare candidates and explain
scientific choices. Promote code that is needed to reproduce the approved result:
training-table assembly, schema validation, split construction, preprocessing,
fitting, metric calculation and release creation. Plotting used only for explanation
may remain in the notebook.

Training functions must accept explicit data and configuration, prevent target or
future-information leakage, and fit preprocessing and feature selection within the
appropriate folds. Random seeds, grouping variables, target definitions, candidate
models and metrics must be recorded. Do not train on the client batch path.

The modelling package must publish a complete model release, not a loose estimator
whose expected inputs are known only to its author. The release manifest must match
the requirements in the end-to-end guide and must be validated before prediction.
Tests should cover schema rejection, deterministic split behaviour where applicable,
release round-tripping and a small prediction with the saved artifact.

## Prediction and dashboard integration

The prediction package owns orchestration, not feature formulas. It reads the model
manifest, determines the required feature-set versions, calls the relevant feature
workflows, validates the assembled columns and order, loads the fitted pipeline and
returns the output contract. Its public service function should operate on validated
in-memory data so both a batch adapter and a backend adapter can call it.

The batch command handles file reading and writing around that service. The backend
handles HTTP validation and serialization around the same service. Neither adapter
may duplicate orchestration, preprocessing or prediction calculations. An
integration test using the same small request through both adapters should compare
their result content after transport-specific formatting is removed.

## Required tests and review evidence

A module is not integrated because it imports successfully or because its notebook
runs once. Focused unit tests must cover its deterministic rules and important edge
cases. Contract tests must prove key uniqueness, expected row coverage, stable column
names and explicit failure behaviour. External calls should normally be mocked or
served from small compliant fixtures so routine tests are repeatable and do not
consume credentials or quotas.

The contributor should also provide one small integration test showing that the
parent orchestrator can call the module. Large live-source downloads and full model
training are not suitable as routine tests; run them as documented controlled checks
when necessary.

## Completion checklist

Before requesting integration, confirm all of the following:

- The notebook records the scientific rationale, while the reusable logic has one implementation under `src/pedflow/`.
- Inputs, outputs, types, units, missing states and failure behaviour are explicit.
- Paths, source options and credentials are handled through the supported configuration boundary.
- The module preserves `site_id` and cannot silently change the requested population.
- Provenance and compatibility versions are sufficient for the parent workflow.
- Unit and integration tests pass without requiring a personal file path or live credential.
- The appropriate registry, orchestrator or public package interface calls the module.
- Existing commands, model releases and reviewed outputs remain compatible, or the version change is explicit.

## Template for assigning integration work

When asking a teammate to promote notebook work, provide the notebook path, the
target module area, the approved input and expected output fields, the source or
model version, known exclusions, configuration needs and acceptance tests. A useful
request is: "Extract the validated calculation from `<notebook>` into `<module>`;
implement the documented contract, preserve the notebook as explanation, register
the module with `<orchestrator>`, and add focused unit and integration tests. Do not
change feature meaning or add a second executable workflow."

If those inputs are not yet known, the task is still scientific definition work and
should remain in the notebook until the contract can be agreed.
