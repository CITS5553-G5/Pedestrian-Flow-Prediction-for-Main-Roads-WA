# Haoqi's Stage 2 feature summary

These six notebooks prepare candidate context features for the same 49 project sites. Every table contains one row per `site_id` and can be joined to `data/processed/model_dataset.xlsx` using `site_id`. The first five reviewed workbooks are shared under `06_outputs/02_feature_extraction/`; the Google Places Aggregate workbook is a temporary local API cache and is not committed to Git.

## Feature dimensions

| Dimension | Notebook | Spatial unit | Main information extracted |
| --- | --- | --- | --- |
| Statistical area and residential context | `context/02_01_haoqi_abs_mesh_block_sa1.ipynb` | The 2021 ABS Mesh Block containing each site | Mesh Block category and area, dwelling and usual-resident counts, and densities per square kilometre |
| Public transport context | `context/02_03_haoqi_pta_stops.ipynb` | Nearest active PTA stop and a 500 m radius around each site | Distance to the nearest active stop, its stop type, and the number of active stops within 500 m |
| Health-establishment proximity | `context/02_04_haoqi_wa_health_establishments.ipynb` | Nearest open Acute Hospital or Nursing Post | Straight-line distance, establishment category, and Public/Private type |
| Education proximity | `context/02_05_haoqi_wa_education_schools.ipynb` | Nearest active school | Straight-line distance, school sector, and lowest and highest year levels |
| Built-environment intensity | `context/02_07_haoqi_microsoft_building_footprints.ipynb` | Exact 500 m buffer around each site | Detected building count, count density, total footprint area, and building coverage ratio |
| Nearby destinations | `context/02_08_haoqi_google_places_aggregate_poi.ipynb` | Selected place types within 500 m of each site | Food and drink, grocery and convenience, major shopping presence, and other retail counts |

## Extracted candidate features

### 1. ABS Mesh Block and SA1

- `abs_mb_category_2021`: categorical land-use context, such as Residential, Commercial, Transport or Industrial.
- `abs_mb_area_sqkm_2021`: area of the containing Mesh Block.
- `abs_mb_dwellings_2021`: dwelling count in the Mesh Block.
- `abs_mb_persons_usual_resident_2021`: usual-resident count in the Mesh Block.
- `abs_mb_dwellings_per_sqkm_2021`: dwelling density.
- `abs_mb_persons_per_sqkm_2021`: usual-resident density.

The Mesh Block and SA1 codes are retained for joining and checking. They are identifiers, not numeric model features.

### 2. PTA stops

- `pta_nearest_active_stop_distance_m`: distance in metres to the nearest active stop.
- `pta_nearest_active_stop_type`: category of the nearest stop, such as Standard, School, Rail, Ferry or Transwa.
- `pta_active_stops_within_500m`: number of active stop points within 500 m.

The nearest stop ID is retained only for checking. The 500 m count measures nearby stop locations, not timetable frequency or passenger use.

### 3. WA health establishments

- `health_nearest_establishment_distance_m`: distance in metres to the nearest open establishment.
- `health_nearest_establishment_category`: Acute Hospital or Nursing Post.
- `health_nearest_establishment_type`: Public or Private.

The distance is the main first-round candidate. Establishment ID and name are retained only for checking.

### 4. WA active schools

- `education_nearest_active_school_distance_m`: distance in metres to the nearest active school.
- `education_nearest_school_sector`: Government, Non-Government or Community Kinder.
- `education_nearest_school_low_year`: lowest year level offered by the nearest school.
- `education_nearest_school_high_year`: highest year level offered by the nearest school.

The distance is the main first-round candidate. Sector and year range are categorical context fields. School code and name are retained only for checking.

### 5. Microsoft building footprints

- `ms_building_count_500m`: number of detected building footprints intersecting the 500 m buffer.
- `ms_building_count_per_sqkm_500m`: detected-building count per square kilometre.
- `ms_building_footprint_area_m2_500m`: total detected footprint area inside the buffer.
- `ms_building_coverage_ratio_500m`: proportion of the buffer covered by detected building footprints.

Because every site uses the same buffer size, count and count per square kilometre contain the same relative information. Footprint area and coverage ratio also contain the same relative information. A model should normally select one field from each pair instead of using both.

### 6. Google Places Aggregate POIs

- `google_food_drink_count_500m`: nearby food and drink places.
- `google_grocery_convenience_market_count_500m`: nearby grocery and convenience places.
- `google_major_shopping_present_500m`: whether the selected major-shopping group is present within 500 m.
- `google_other_retail_count_500m`: nearby places in the selected other-retail group.

`google_places_data_status` and `google_places_error_message` are QA fields, not predictors. The four values are API-derived candidate features rather than adopted model inputs. The generated workbook is intentionally ignored because it is a temporary cache with source-specific retention restrictions; rerun the notebook when an authorised refresh is required.

## Feature types

- **Continuous numeric features:** distances, Mesh Block area, densities, footprint area and coverage ratio.
- **Count features:** dwellings, usual residents, nearby PTA stops, detected buildings and nearby place groups.
- **Binary features:** presence of a selected major-shopping group within 500 m.
- **Categorical features:** Mesh Block category, stop type, health category/type, school sector and year range.
- **QA and audit fields:** processing status, error messages, source IDs, codes and names. These support checking and should not automatically be used as predictors.

These notebooks extract candidate features only. Final feature selection, transformations and encoding belong in the model-development workflow and must be evaluated without using the full dataset to choose the best-looking result.
