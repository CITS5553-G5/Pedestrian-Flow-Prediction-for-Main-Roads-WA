# Automated verification

The test suite covers feature contracts, location resolution, imagery checkpoints, released-model calculations, reference matching and workbook export. `unit/` contains focused checks, `integration/` checks connected workflows and reviewed source tables, and `fixtures/` contains synthetic source extracts and saved R prediction cases.

After [project setup](../docs/SETUP.md), run from the repository root:

```bash
python -m pytest tests -q
```

The full suite requires the complete project dependencies, including `geopandas` for spatial research-source tests, and the versioned datasets and outputs consumed by integration checks. A missing package can prevent collection; it is not equivalent to a passing or skipped test. Some local-data tests explicitly skip when their required source or audit is absent. Check the pytest summary for skips and collection errors before interpreting results.

A smaller set of deterministic checks uses synthetic inputs, saved R references and mocked external responses:

```bash
python -m pytest tests/unit/test_model.py tests/unit/test_imagery.py tests/unit/test_ausrap_reference.py tests/unit/test_irap_comparison.py tests/integration/test_prediction_tracer.py -q
```

The tracer exercises the real readers, adapters, model and exporters while replacing external service responses. The [79 R reference cases](fixtures/modeling/README.md) test calculation equivalence. [Context fixtures](fixtures/context/README.md) are synthetic records for source-cleaning and spatial checks. Passing these tests does not establish live imagery accuracy, provider availability or model accuracy at new locations.

The 45-site reference parity check in `integration/test_ausrap_client_parity.py` requires the AusRAP Words workbook, merged pedestrian-reference CSV and pinned preflight audit. [Historical OOF reproduction](../docs/05_model_evaluation/reproduction.md) additionally requires exact research snapshots and original survey evidence; it is not part of routine inference. Generated test files use temporary directories or Git-ignored caches.
