# Haoqi's Stage 2 feature summary

Runtime scope (20 September 2026): the selected linear model needs only the ABS
category from Context. Formal extraction now uses `context_abs_v1` and the default
ABS-only registry. The six-source catalogue below documents historical candidate
features and reviewed research outputs; it is not the current prediction source
list. Its configuration is preserved under `configs/research/`.

These six approved notebooks prepare candidate context features for the same 49 project sites. Every table contains one row per `site_id` and can be joined to `data/processed/model_dataset.xlsx` using `site_id`. The previously reviewed combined context snapshot is `06_outputs/02_feature_extraction/02_00_haoqi_context_features.xlsx`; source-specific workbooks remain the traceable source outputs. The four approved fields from `06_outputs/02_feature_extraction/02_09_haoqi_overture_places_features.xlsx` are now integrated into the authoritative `Model_Data` table, while `overture_places_data_status` remains source QA only. No active table contains Google-derived POI fields.

## Feature dimensions

| Dimension | Notebook | Spatial unit | Main information extracted |
| --- | --- | --- | --- |
| Statistical area and residential context | `context/02_01_haoqi_abs_mesh_block_sa1.ipynb` | The 2021 ABS Mesh Block containing each site | Mesh Block category and area, dwelling and usual-resident counts, and densities per square kilometre |
| Public transport context | `context/02_03_haoqi_pta_stops.ipynb` | Nearest active PTA stop and a 500 m radius around each site | Distance to the nearest active stop, its stop type, and the number of active stops within 500 m |
| Health-establishment proximity | `context/02_04_haoqi_wa_health_establishments.ipynb` | Nearest open Acute Hospital or Nursing Post | Straight-line distance, establishment category, and Public/Private type |
| Education proximity | `context/02_05_haoqi_wa_education_schools.ipynb` | Nearest active school | Straight-line distance, school sector, and lowest and highest year levels |
| Built-environment intensity | `context/02_07_haoqi_microsoft_building_footprints.ipynb` | Exact 500 m buffer around each site | Detected building count, count density, total footprint area, and building coverage ratio |
| Food, drink and shopping context | `context/02_09_haoqi_overture_places.ipynb` | Exact geodesic 500 m radius around each site point | Counts of food/drink, routine shopping and other shopping places, plus shopping-mall presence |

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

### 6. Overture Places

- `overture_food_drink_count_500m`: number of eligible places whose current Overture taxonomy hierarchy contains the official `food_and_drink` ancestor.
- `overture_grocery_convenience_pharmacy_count_500m`: number of eligible places whose taxonomy hierarchy contains `food_and_beverage_store`, `convenience_store` or `pharmacy_and_drug_store`.
- `overture_shopping_mall_present_500m`: whether at least one eligible place has the `shopping_mall` ancestor.
- `overture_other_shopping_count_500m`: number of eligible places under the official `shopping` ancestor after excluding the three routine-shopping ancestors above and `shopping_mall`.

The calculation uses the Overture `2026-08-19.0` release through the official `overturemaps` Python client. A query bounding box is downloaded for each site, then the code applies exact WGS84 distance filtering to 500 m. Duplicate GERS place IDs within a site query are removed. Records explicitly marked `temporarily_closed` or `permanently_closed` are excluded. This release leaves `operating_status` blank for the places returned around the project sites, so retained records must be interpreted as “not explicitly marked closed”, not as independently confirmed currently operating businesses. No additional confidence threshold is imposed because Overture confidence is relative rather than a calibrated probability.

`overture_places_data_status` is a QA field: `complete` means at least one target-category place was counted, while `complete_no_eligible_places` means the query completed but all four derived values were zero. It is not a pedestrian-demand measure and should not automatically enter the model.

### Excluded experiment: Google Places Aggregate POIs

Google Support did not interpret or authorise the proposed modelling use and referred the decision to UWA. UWA selected the lower-risk project option of excluding Google POI features from pedestrian-flow models. The four experimental Google fields are therefore absent from the active combined feature table and must not be used for training, validation, testing, feature selection or client prediction. The pre-exclusion experiment is retained only as an audit record in `07_Archive/20260908_google_places_aggregate_poi_experiment/`.

## Feature types

- **Continuous numeric features:** distances, Mesh Block area, densities, footprint area and coverage ratio.
- **Count features:** dwellings, usual residents, nearby PTA stops, detected buildings, and Overture food/drink and shopping-place counts.
- **Binary features:** Overture shopping-mall presence.
- **Categorical features:** Mesh Block category, stop type, health category/type, school sector and year range.
- **QA and audit fields:** processing status, error messages, source IDs, codes and names. These support checking and should not automatically be used as predictors.

These notebooks extract candidate features only. Final feature selection, transformations and encoding belong in the model-development workflow and must be evaluated without using the full dataset to choose the best-looking result.
