# Context: ABS feature extraction

This module queries ABS Mesh Block / SA1 locations from site coordinates, joins
the local ABS 2021 workbook and returns context features, match statuses and
provenance. The current prediction workflow uses ABS only.

## File responsibilities

| File | Purpose |
| --- | --- |
| [__main__.py](__main__.py) | Entry point for `pedflow-context` / `python -m pedflow.context`; parse arguments, run extraction and export results |
| [config.py](config.py) | Load JSON configuration, validate fields and select configured sources |
| [contracts.py](contracts.py) | Define configuration and result structures, including `SourceConfig`, `SourceDefinition`, `FeatureResult` and `ContextBuildResult` |
| [workflow.py](workflow.py) | Implement `build_context_features`: validate input, call enabled sources, validate returned tables and merge results |
| [validation.py](validation.py) | Reuse shared site validation, check source column prefixes and reject target-leakage columns |
| [io.py](io.py) | Read the configured site table; export Context Excel/Parquet files and provenance |
| [sources/registry.py](sources/registry.py) | Register sources available to the prediction workflow; currently only `abs_meshblock_sa1` |
| [sources/abs_meshblock_sa1.py](sources/abs_meshblock_sa1.py) | Load and clean the ABS workbook, query geographic membership, join attributes, calculate densities and produce quality checks and provenance |
| [__init__.py](__init__.py), [sources/__init__.py](sources/__init__.py) | Identify packages without eagerly loading every external source on import |

## Execution flow

```text
__main__.py
  → config.py: load configuration
  → io.py: read sites
  → workflow.py: validate sites and check enabled sources
      → sources/registry.py: locate the ABS extractor
      → sources/abs_meshblock_sa1.py: extract, calculate and check
      → validation.py: validate columns and site_id coverage
  → io.py: export features and manifest
```

The complete prediction workflow calls `workflow.py` directly and receives results
in memory. It does not require a separate Context command or intermediate Excel file.

## Inputs, outputs and configuration

The entry point is `build_context_features(sites, config, project_root)`. Input
requires `site_id`, WGS84 coordinates and `coordinate_crs`. The returned
`ContextBuildResult` contains `features`, with one row per site, and
`source_results`, with source versions, metadata and warnings.

The workflow configuration is [context_abs_v1.json](../../../configs/prediction/context_abs_v1.json).
Extraction requires internet access to ABS services and the local
`Mesh Block Counts, 2021.xlsx` workbook, but no API key.

The current model uses only `abs_mb_category_2021`, which Prediction converts to
`abs_mb_category_simple` using Modeling's category mapping. Population, dwelling
counts, area and density remain in the ABS output but are not model inputs.
Check `abs_match_status` and `abs_error_message` before using results.

## Retained research sources

These files remain in use by some research notebooks or tests but are excluded
from the default prediction workflow.

| File | Research purpose |
| --- | --- |
| [pta_stops.py](sources/pta_stops.py) | Public transport stop distances and nearby stop features |
| [wa_health_establishments.py](sources/wa_health_establishments.py) | Health facility locations and proximity features |
| [wa_education_schools.py](sources/wa_education_schools.py) | School locations and proximity features |
| [microsoft_building_footprints.py](sources/microsoft_building_footprints.py) | Building footprints and coverage features |
| [overture_places.py](sources/overture_places.py) | Nearby places, including dining and shopping |
| [google_places_aggregate_poi.py](sources/google_places_aggregate_poi.py) | Guard against reuse of an excluded experiment; raises an error instead of extracting data |

Research settings are retained in [configs/research](../../../configs/research/).
Using another research source through the Context workflow requires explicitly
passing its registry; changing `enabled` alone does not register it.
See the [project guide](../../../README.md) for standalone commands.
