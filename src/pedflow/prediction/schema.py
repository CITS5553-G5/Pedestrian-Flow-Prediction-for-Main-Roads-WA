"""Formal prediction workbook columns; RAP comparisons are separate research work."""

OUTPUT_SCHEMA_VERSION = "prediction_output_v4"
OUTPUT_COLUMNS = (
    "site_id", "input_type", "road_no", "slk_km", "cway", "start_slk", "end_slk",
    "latitude", "longitude", "matched_road_no", "matched_slk_km", "matched_cway",
    "road_offset_m", "location_status", "pred_peak_cross_ped_per_h",
    "pred_peak_along_ped_per_h", "status", "message",
)
FEATURE_COLUMNS = (
    "site_id", "commercial_buildings", "footpath_both_sides",
    "abs_mb_category_simple", "abs_mb_category_2021", "abs_mb_code_2021",
    "abs_sa1_code_2021", "abs_match_status", "abs_error_message",
    "imagery_status", "imagery_error", "imagery_warnings", "image_count",
    "processed_at_utc",
)
