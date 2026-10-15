"""Model predictions and AusRAP references; accuracy evaluation remains separate."""

OUTPUT_SCHEMA_VERSION = "prediction_output_v5"
OUTPUT_COLUMNS = (
    "site_id", "input_type", "road_no", "slk_km", "cway", "start_slk", "end_slk",
    "latitude", "longitude", "matched_road_no", "matched_slk_km", "matched_cway",
    "road_offset_m", "location_status", "obs_peak_cross_ped_per_h",
    "pred_peak_cross_ped_per_h", "existing_irap_cross_recoded_ped_per_h",
    "observed_cross_category", "predicted_cross_category", "existing_ausrap_cross_category",
    "existing_ausrap_cross_band", "obs_peak_along_ped_per_h", "pred_peak_along_ped_per_h",
    "existing_irap_along_recoded_ped_per_h", "existing_ausrap_along_combined_band",
    "status", "message", "comparison_status", "comparison_notes",
)
FEATURE_COLUMNS = (
    "site_id", "commercial_buildings", "footpath_both_sides",
    "abs_mb_category_simple", "abs_mb_category_2021", "abs_mb_code_2021",
    "abs_sa1_code_2021", "abs_match_status", "abs_error_message",
    "imagery_status", "imagery_error", "imagery_warnings", "image_count",
    "processed_at_utc",
)
