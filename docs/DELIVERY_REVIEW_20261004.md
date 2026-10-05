# Prediction workflow delivery review

## Status recorded on 5 October 2026

This document retains the initial 4 October review as a historical record. Its original priorities and recommendations are not the current implementation backlog. Credential remediation is recorded as handled separately, and Git packaging remains separate work. Dashboard integration, report regeneration, dependency separation and additional recovery/retry features are outside the current scope. The corrected-site refit sensitivity analysis is not being performed; no claim is made that its effect has been shown to be negligible.

Operational prediction accepts any positive number of locations, determined by the input rows; no predefined count or group ratio is required. The processed workbook contains a 20-location prediction example, while the template contains a separate 100-location example. Their row counts need not match. Documentation, workbook descriptions and dynamic row-count tests have been updated. The current input manifest records the 20-row batch; the original 100-row sampling record is retained as a historical preparation record.

OOF evaluation is separate from operational prediction. Its reproduction procedure is documented for developers, and the historical input-fingerprint checks remain active. The reformatted research workbook requires the original pinned snapshot for that developer command. Production model and imagery-recipe compatibility checks remain automatic.

Valid supplied coordinates remain eligible for prediction when only carriageway matching is ambiguous, with the warning retained. Road/coordinate conflicts and unresolved road-only locations still receive no prediction. The maintained concurrency default is 50 sites, and exported strings are stored as text. Fresh live-service acceptance and imagery-feature consistency checks remain unverified because no working Gemini key was available for that verification.

## Initial review record: 4 October 2026

The review covered the active `03_Project` workspace and examined the older `pedflow-frontend-update` worktree for credential residue and delivery descriptions. The initial review did not change business code, models, input data or reviewed outputs. Temporary test and reproduction files were kept outside the delivered repository.

The workflow already had a unified prediction entry point, an independent model release, per-site failure statuses, imagery checkpoints and an offline example. The review identified inconsistent input manifests, a stopped historical evaluation command, suspected credential residue and gaps in operational acceptance. These findings did not support describing the workflow as a fully accepted prediction product at that date.

The delivery scope covers reusable Python/R code, crossing and along-road peak-flow predictions, and comparison with existing iRAP estimates. A dashboard and whole-network production deployment are separate from that scope.

## Evidence and verification boundaries

Inspection covered input reading, road/SLK location resolution, ABS Context, Google/Gemini Imagery, model inference, AusRAP matching, workbook/manifest export, checkpoint recovery, OOF evaluation, tests, the frontend and delivery documentation.

The existing Python 3.11 test environment could not collect three research-source modules because `geopandas` was missing. This was an environment limitation, not proof of a defect in those modules. Excluding them gave **178 passed, 3 failed and 36 subtests passed** in the initial run. The failing checks were `test_formal_batch_preserves_observations_and_location_ambiguities[data/processed/batch_input_dataset.xlsx]`, `test_formal_mixed_batch_reaches_model_and_preserves_blocked_rows`, and `test_config_load_and_prompt_identity`. The initial core delivery subset gave 82 passed, 2 failed and 33 subtests passed.

The ten-location offline replay succeeded with 10 rows, 29 output columns, nine normal prediction statuses, one retained warning and ten matched references. Saved features and predictions were preserved, observations stayed blank, and no external service requests were made. The historical OOF CLI stopped because `model_dataset.xlsx` did not match the preflight file hash. An isolated temporary root containing the matching Git HEAD workbook reproduced the existing comparison of 45 crossing and 43 along-road sites. The inspected `Model_Data` values matched between the active and HEAD workbooks.

Frontend build and lint verification stopped during tool loading because Vite/oxlint executables were absent from the local dependencies. Dependencies were not installed, and browser acceptance was not performed. The review did not test key validity, paid imagery/LLM services, fresh live prediction, Windows installation, whole-network inference or independent external model validation.

The subsequent 5 October regression result is recorded in the [handover](HANDOVER.md). It supersedes the initial failing-test counts above for the checks that were rerun; it does not establish a full-suite pass in a complete environment or live-service acceptance.

## Historical P0 findings

### P0-01: Suspected credentials in tracked files and Git history

The initial scan found a Google API-key-shaped string in `02_feature_extraction/imagery/combined_google_mapillary_feature_extraction.ipynb`, at line 480 in the inspected snapshot, in both local worktrees. Earlier `.env.example` commits `c179416f727f` and `ea25a4d4de34` also contained strings of that format. Key values were not printed or tested for validity.

The initial recommendation covered identifying and rotating shared credentials, replacing embedded values with environment variables, and inspecting notebook source/output, historical configuration and delivery archives. Shared-history cleanup requires team coordination. Removing a current value does not remove an earlier commit. Credential handling was subsequently recorded as addressed separately; this documentation update does not independently verify revocation or rewritten history.

### P0-02: Input, template, manifest and test disagreement

The processed `Batch_Input` contained 20 locations: 10 observed and 10 random, with 18 matched and two `ambiguous_carriageway` results. The template contained 100: 49 observed and 51 random, with 87 matched and 13 ambiguous results. At the initial review, the manifest, README, handover and two integration tests still described the processed file as a 100-row batch, and the recorded output hashes did not match the active workbooks. The service preserved supplied input rows; it did not reduce a 100-row input to 20 rows.

The recommendation was to give each example a clear role, record actual row/group counts and hashes, and retain arbitrary-size service tests alongside example-specific checks. This mismatch was subsequently corrected by documenting the two independent examples and separating the current batch manifest from the historical preparation record.

### P0-03: Historical OOF command stopped on a fingerprint mismatch

`python -m pedflow.evaluation` raised `ContractError` for the active research workbook because its file hash differed from the pinned preflight snapshot. The compared `Model_Data` values were equal, so this finding did not demonstrate changed training values or model coefficients. The strict fingerprint check was operating as designed.

Historical reproduction requires the exact reviewed research snapshot. A deliberate research-input change requires a reviewed preflight and resulting evidence, rather than disabling checks or replacing a hash to imply historical identity. The developer [reproduction guide](05_model_evaluation/reproduction.md) now documents this requirement; operational prediction does not depend on running that command.

## Historical P1 findings

### P1-01: Live acceptance of the maintained configuration was incomplete

The ten-location example used saved features, and tracer tests used simulated external responses. The recorded 21 September imagery run used earlier 120/30 RPM limits; it did not establish acceptance of the maintained 50-worker configuration with disabled local request pacing or the complete prediction chain.

The initial recommendation was a small manually reviewed live batch covering coordinate, road/SLK and combined inputs, missing imagery/ABS matches, temporary failures and recovery. Acceptance evidence would record versions, duration, requests and per-site outcomes while preserving order, missing predictions and unknown observations. Fresh live-service acceptance remains unverified.

### P1-02: Carriageway ambiguity blocked some input locations

At the initial review, two locations in the 20-row example and 13 in the 100-row template had carriageway ambiguity. The inspected workflow blocked these rows before feature extraction. Counts from the two inputs therefore could not be treated as equivalent prediction-completion rates.

The subsequent workflow change allows valid supplied coordinates to remain the feature point when only the carriageway is ambiguous, retaining a warning. Road-only input still needs a unique measured location, with verified `cway` where necessary. Road/coordinate conflicts remain blocking conditions. Location-precheck counts are not live prediction-success counts.

### P1-03: Training and live imagery-feature consistency was unverified

Historical training imagery provenance was incomplete. The [imagery integration guide](02_feature_extraction/imagery_integration.md) records the need to compare live samples with training features. The 79 R/Python reference cases verify calculations for identical supplied features; they do not verify building counts or footpath recognition from new imagery.

The initial recommendation was manual review of representative new imagery features, their prediction effects, and available image dates, panorama IDs, prompts, model/recipe versions and review records. A changed feature definition requires model-chain revalidation. No fresh consistency check is claimed.

### P1-04: Concurrency settings, tests and documentation disagreed

The initial configuration specified 50 workers and `null` Maps/Gemini RPM limits, while a test and the imagery guide still specified ten workers. This caused the inspected configuration test to fail. A fully covered site can make up to 11 Maps calls and one Gemini call before retries, so 50 concurrent sites is not a total request count or a provider quota.

The default was subsequently aligned to 50 sites across configuration, tests and maintained documentation. Request pacing remains configurable and independent for the two providers. This alignment does not establish acceptance against a particular service account's quota.

### P1-05: Corrected-site refit sensitivity was not performed

The recorded sensitivity question concerns refitting after excluding corrected sites `250341-04` and `260335-38`. Direction-specific evaluation exclusions for `250341-01` and `260335-38` do not answer that question.

The initial recommendation was an independent rerun of the same modelling procedure with documented sample, coefficient and road-grouped metric changes, preserving the current release. That refit is outside the current scope and has not been performed. The comparison remains internal validation, and crossing gains remain sensitive to a small number of influential improvements.

### P1-06: The active working tree was not a frozen release package

The initial status included untracked evaluation/reference modules, tests, handover documents, examples and reports. A package containing only the then-current commit would omit active dependencies. Strict historical evaluation also requires six original `.xlsm` survey workbooks that are stored locally and excluded from Git.

Release packaging should include the reviewed active implementation, configuration, templates and examples. Original research evidence remains in approved project storage, with relative paths and fingerprints recorded in the audit; it need not be forced into Git. [Raw-source notes](../data/raw/README.md) describe availability. Credential files and machine-local environments remain outside the package. Git packaging is separate from this documentation update.

### P1-07: The dashboard prototype implied unsupported functionality

The inspected frontend produced values with browser-side rules and `setTimeout`, hard-coded 94% confidence, hourly trends and initial history, and displayed service-status labels. No backend was implemented. The released model predicts two peak-hour flows from three features; it does not provide weather/date effects, hourly curves or that confidence definition.

The [application guide](../05_application/README.md) identifies the interface as a demonstration without a model connection. Operational delivery uses the batch workflow. Future functional integration would call `predict_sites`, present the real dual-direction contract and require separate acceptance of job status, failures and download behaviour. Dashboard integration remains outside the current scope.

### P1-08: Workbook export did not force every string to text

A temporary synthetic export showed that `site_id='=1+1'` was stored as text while `road_no='=1+1'` and `message='=1+1'` were stored as formulas. The check made no external calls. It demonstrated an export-boundary inconsistency, not an incident in a normal input batch.

The subsequent exporter change stores diagnostic and external-input strings as text. Regression checks cover string fields and preserve normal numeric formatting and blanks. Only explicitly authored calculation fields should be formulas.

## Historical P2 maintenance findings

### P2-01: ABS retry and reusable query results

The inspected ABS extractor queried locations serially, recording transient failures as `request_failed`; resume refreshed ABS rather than reusing a cache. Bounded retry/backoff and a versioned coordinate/source/configuration cache were identified as possible later improvements. Such changes would need explicit refresh semantics and retained permanent failures. They are outside the current scope.

### P2-02: Re-extracting needs-review imagery

The imagery workflow reuses `needs_review` and `complete` checkpoints. Prediction still rejects incomplete model features. The documented way to re-extract needs-review rows is a new checkpoint. Explicit selected-site retry was identified as a convenience improvement, with successful checkpoints and separately recorded manual corrections preserved. No additional retry feature is included in the current scope.

### P2-03: Research and runtime dependency separation

The shared requirements include research, notebook, test and inference packages, while `pyproject.toml` does not declare a standalone runtime dependency set. The inspected local environment had a broken interpreter link. Installing the package alone does not replace the complete dependency setup documented in the README.

A separate minimal runtime extra and clean-environment acceptance were identified as possible later work. Dependency separation is outside the current scope. The recorded partial-environment test result must not be described as a complete-environment full-suite pass.

### P2-04: Report-generation portability

The workbook builder requires a separately provisioned `@oai/artifact-tool` runtime; the repository does not include a portable installation lockfile for it. The PDF/HTML analysis-report generator is not included. Static results remain readable, but all reports cannot be described as reproducible with one command in a standard clone.

The [tools guide](../tools/README.md) documents workbook inputs, runtime selection, chart repair and the static-report boundary. Portable report-generation dependencies and broader release automation remain outside the current scope.

## Interpretation of the review

The current status section governs interpretation of this dated record. Initial recommendations describe the evidence and possible remedies identified on 4 October; they are not instructions to expand the current scope or claims that every listed check has since passed.

Acceptance evidence must refer to a defined release snapshot, with consistent input roles and manifests, applicable passing tests, runnable setup, visible per-site failures and documented live-service limits. Historical OOF reproduction and operational prediction have distinct requirements. This review does not replace those checks or establish model accuracy at unseen locations.
