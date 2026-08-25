# Pedestrian-Flow Model Feature Selection Recommendations: Complementing Context Integration with Imagery

Date: 2026-08-25
Status: Pre-registered recommendations before imagery extraction is complete
Applicable targets: `obs_peak_cross_ped_per_h` and `obs_peak_along_ped_per_h`

## 1. Selection principles

Context-integration and imagery features should not be treated as competing groups. Context features mainly describe why a location may generate pedestrian demand, including nearby population, schools, public transport and development intensity. Imagery features mainly describe whether pedestrians have the opportunity to walk along or cross the road, including footpaths, crossing facilities, separation treatments and shared paths. A location may have high potential demand but low observed flow because it lacks footpaths or contains barriers. Conversely, it may have good facilities but low flow because few residents or destinations are nearby. The final model should therefore represent both demand potential and movement opportunity or resistance.

Feature selection should first be based on meaning, availability and measurement quality, followed by testing of incremental value under grouped or spatial cross-validation. The project must not inspect correlations between all 49 targets and candidate features and then retain only the most favourable variables. Every imagery feature must first pass target-independent manual validation, coverage, repeated-extraction consistency and category sample-size checks.

## 2. Recommended context features for the core model

| Recommended feature | Recommended treatment | Main meaning | Complementary role with imagery | Priority |
| --- | --- | --- | --- | --- |
| `abs_mb_persons_per_sqkm_2021` | Apply `log1p`; do not include dwelling density at the same time | Approximation of nearby resident demand intensity | Imagery shows road facilities but cannot reliably identify the resident population | Core |
| `abs_mb_category_2021` | Collapse to Residential, Commercial/Education and Other non-residential | Basic land-use context of the containing Mesh Block | Cross-checks visible land use; ABS is stable but describes only the containing Mesh Block | Core |
| `education_nearest_active_school_distance_m` | Apply `log1p` | Proximity to a school destination | Combines with crossings, footpaths on both sides and fencing to describe conditions near schools | Core |
| `pta_nearest_active_stop_distance_m` | Apply `log1p` | Proximity to the nearest public-transport stop | Combines with footpath and shared-path information to describe both stop presence and pedestrian access | Core |
| `pta_active_stops_within_500m` | Apply `log1p` | Local supply of public-transport stops | A visible stop sign in imagery cannot replace the overall nearby stop supply | Core |
| `ms_building_coverage_ratio_500m` | Retain as a ratio; standardise if required | Surrounding development intensity | Imagery land use describes type, while building coverage describes amount and density | Core |
| `health_nearest_establishment_distance_m` | Apply `log1p` | Proximity to a hospital or nursing post | May represent a destination or town centre, but does not directly measure pedestrian activity | Conditional |

ABS dwelling count, person count and the two density measures are highly correlated and should not all enter the primary model. Use person density as the default representation and dwelling density as a sensitivity alternative. Microsoft building count and count per square kilometre are deterministically proportional, as are footprint area and coverage ratio; only one field from each pair should be used. Retain coverage ratio by default because it directly represents the proportion of the buffer occupied by detected buildings. Building count may enter an expanded specification to describe building granularity, but it must not be used with its density version.

Health distance has a weak univariate association across the current 49 sites, and HEALTH-001 covers only acute hospitals and nursing posts. It may enter a source-ablation or expanded model, but it should not be forced into the final deployed model merely to ensure that every source contributes a variable.

## 3. Recommended imagery fields for extraction and modelling

### 3.1 Footpaths

Raw extraction should retain information for both road sides, such as `footpath_driver_side` and `footpath_passenger_side`, and distinguish `unknown` from `absent`. For the current total-flow models, derive `footpath_side_count` with values 0, 1 or 2, `footpath_both_sides`, and `footpath_continuity_score`. Do not force a continuity score when imagery can reliably identify presence but not continuity.

`footpath_side_count` and continuity are core features for the along-road model. `footpath_both_sides` is also important for the across-road model because crossing opportunity depends partly on whether usable walking space exists at both ends of a crossing movement. Do not include driver side, passenger side, side count and both-sides indicators together in one linear model because they are deterministically related representations. Retain the two raw side fields for audit, while using one pre-selected derived representation in modelling.

### 3.2 Pedestrian crossing facilities

Extract at least `formal_crossing_present`, with `crossing_type` retained as a separate categorical field. Example categories are `signalised`, `zebra`, `refuge/median`, `uncontrolled/marked`, `none` and `uncertain`. The first across-road model should use the stable binary `formal_crossing_present` field. Use `crossing_type` in an expanded model only when each type has an adequate sample and manual validation is reliable.

Crossing facilities are a core imagery feature for the across-road model, but they must be interpreted as predictive associations rather than causal effects. High-demand locations may already be more likely to receive a crossing, so the model may capture both the effect of facilities on crossing and the effect of historical demand on facility provision.

### 3.3 Separation treatments and fencing

Extract `pedestrian_fencing` separately from `vehicle_safety_barrier`. Pedestrian fencing may prevent arbitrary crossing or guide pedestrians towards a designated crossing. A vehicle safety barrier mainly describes road-safety separation and does not always prevent pedestrian movement. The recommended core across-road feature is `pedestrian_fencing_any` or `pedestrian_permeability_barrier_present`. Retain the raw side-specific fields for audit.

Vehicle safety barriers should enter only an expanded model unless manual review confirms that they can be consistently identified in the available imagery and their meaning is genuinely related to pedestrian resistance. Do not combine all barriers and fences into one field without a clear directional interpretation.

### 3.4 Shared walking and cycling paths

Extract `shared_path_present`, and add `shared_path_side_count` or continuity only when these can be assessed reliably. This is a core along-road feature because shared paths may carry pedestrian activity missed by an ordinary footpath field. Do not merge it with ordinary footpath presence because traditional footpaths and shared paths describe different environments.

### 3.5 Parking and roadside activity

Extract `on_street_parking_present` separately from `off_street_parking_area_visible`. On-street parking may affect sight distance, roadside activity and crossing behaviour. Visible off-street parking is more likely to serve as a proxy for commercial or destination intensity. The two fields should not be combined by default because they have different meanings.

Parking features should first enter the expanded model. If imagery validation shows that the two parking types cannot be distinguished reliably, use a pre-defined `parking_activity_present` field, but decide the combination rule before viewing the targets.

### 3.6 Visible land use and the built environment

Limit imagery land-use labels to stable, broad categories such as `residential`, `commercial/active_frontage`, `industrial` and `mixed/uncertain`, rather than producing unrestricted text descriptions. Imagery supplies a local road-view environment and complements the ABS limitation of describing only the containing Mesh Block.

The default core model should use the collapsed ABS category and Microsoft building coverage. Imagery land use should first serve as an expanded feature and a cross-source consistency check. It may enter the final model if manual validation is adequate, category sample sizes are sufficient and grouped cross-validation shows stable incremental value. `imagery_land_use_agrees_with_abs` is mainly a QA field and is not recommended as a predictor because disagreement may result from geographic boundaries, field of view or classification error.

### 3.7 Other visible features

An allowed vocabulary for other visible features must be frozen before extraction. A model or LLM must not return uncontrolled free text. Prioritise fields that are directly related to pedestrian movement mechanisms and do not duplicate existing AusRAP fields, such as pedestrian refuge or median access, traffic signals, intersection proximity, visible bus stops, cycle lanes and service roads. A candidate should enter the expanded model only when it has approximately five positive and five negative sites and passes coverage and manual-agreement checks.

## 4. Use different imagery subsets for the two targets

| Information block | Across-road model | Along-road model |
| --- | --- | --- |
| Context demand core | Population density, Mesh Block category, school distance, PTA distance/count and building coverage | Same as across-road |
| Footpaths | `footpath_both_sides` or a pre-defined side representation | `footpath_side_count` and continuity |
| Crossings | Core: `formal_crossing_present`; expanded: crossing type | Usually expanded or explanatory only |
| Fencing/barriers | Core: pedestrian fencing or permeability | Usually expanded unless it clearly blocks the route |
| Shared path | Secondary or expanded | Core: `shared_path_present` |
| Parking | Expanded; may affect crossing and sight distance | Expanded; may represent roadside activity |
| Visible land use | Expanded, complementing ABS | Expanded, complementing ABS |

The targets should share the context core and validation folds, but they do not need identical imagery features. This preserves comparability while avoiding the inclusion of crossing-only fields in the along-road model or linear-walking-network fields in the across-road model.

## 5. Recommended first-round frozen lists

The compact first-round across-road specification should contain `log1p(person density)`, collapsed Mesh Block category, `log1p(school distance)`, `log1p(PTA distance)`, `log1p(PTA stops within 500m)`, building coverage ratio, `formal_crossing_present`, `footpath_both_sides` and `pedestrian_fencing_any`.

The compact first-round along-road specification should contain the same six context features plus `footpath_side_count`, `footpath_continuity_score` when reliable, and `shared_path_present`.

Health distance, building count, PTA stop type, school sector, crossing type, vehicle safety barriers, both parking fields and imagery land use belong in expanded or source-ablation specifications. Identifiers, names, coordinates, source status, error messages, confidence, image date and provider are QA, provenance, missingness and support-domain fields rather than behavioural predictors.

## 6. Gates before imagery features enter a model

1. Confirm that every definition is unambiguous, then freeze the category vocabulary, road-side convention and distinction between `unknown` and `absent`.
2. On a manually reviewed sample that does not use the targets, assess coverage, accuracy or balanced accuracy, inter-category agreement and repeated-call consistency. Suggested working thresholds are at least 90% coverage, approximately 0.75 balanced accuracy or approximately 0.60 Cohen's kappa. Fields below the relevant threshold should remain audit fields.
3. Check variability. A binary field with fewer than approximately five positive or five negative sites must not become a default one-hot feature. Combine it into a meaningful broader category or defer it.
4. Remove deterministic duplicate representations and select one interpretable, deployment-stable encoding for each related concept.
5. Freeze `context_only`, `imagery_only`, `combined_core` and `combined_expanded` feature sets, and compare them on exactly the same grouped or spatial folds.
6. Promote imagery or another source to the final deployed model only when it produces stable incremental value in paired OOF MAE, spatial stress tests and sensitivity analysis.

These numerical thresholds are current pre-registered working recommendations, not client-confirmed acceptance criteria. Reports should provide the achieved values and reasons for any failure, rather than presenting successful engineering extraction as proof of scientific predictive value.

## 7. Selection methods that are not recommended

Do not rank correlations on the full sample and retain the leading features. Likewise, do not run LASSO, recursive feature elimination or SHAP on all 49 rows and then report cross-validation on the same data. Those procedures indirectly expose test-fold information to feature selection. If regularisation, permutation importance or source ablation is used, it must run inside each outer training fold and be evaluated on the unseen outer test fold.

Do not create a large number of interaction terms at once. Only a few interactions have a strong domain basis, including school proximity × crossing, PTA proximity × footpath, and building intensity × footpath. Treat them as pre-declared sensitivity specifications or test them with a constrained nonlinear challenger instead of adding all of them to the primary linear model with only 49 rows.
