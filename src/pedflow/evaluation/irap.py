"""Compare saved road-grouped OOF predictions with the audited client baseline."""

import hashlib
import json
import math
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pandas as pd

from pedflow.exceptions import ContractError
from pedflow.flow import UPPER_BOUNDS, flow_category

PROTOCOL = "irap_comparison_protocol_v1"
MODEL_PATH = "data/processed/model_dataset.xlsx"
CLIENT_PATH = "data/raw/Ped_iRAP_merged.csv"
WORDS_PATH = "data/raw/AusRAP Data - Words - MSDS.xlsx"
OOF_PATH = (
    "06_outputs/03_model_development/03_yashika_model_comparison/"
    "03_model_comparison_oof_predictions.csv"
)
AUDIT_PATH = "04_prediction_pipeline/irap_comparison/evidence/preflight_audit.json"
MODEL_LABEL = "Model (road-grouped OOF)"
REFERENCE_LABEL = "Existing iRAP flow estimate (recoded)"
ALONG_EXCLUSIONS = {
    "250341-01": "along_coverage_unconfirmed_south_walkway",
    "260335-38": "along_coverage_west_only",
}
TARGETS = {"cross": "Cross-road", "along": "Along-road"}


@dataclass
class ComparisonResult:
    sites: pd.DataFrame
    errors: pd.DataFrame
    metrics: pd.DataFrame
    manifest: dict


def _keyed(table, key, required, name):
    missing = {key, *required} - set(table.columns)
    if missing:
        raise ContractError(f"{name}: missing columns {sorted(missing)}")
    result = table.copy(deep=True)
    if result[key].isna().any():
        raise ContractError(f"{name}: missing {key}")
    result[key] = result[key].astype(str).str.strip()
    if result[key].eq("").any() or result[key].duplicated().any():
        raise ContractError(f"{name}: {key} must be unique and nonblank")
    return result.set_index(key, drop=False)


def _flow(value, label, *, missing_allowed=False):
    if pd.isna(value) or value == "":
        if missing_allowed:
            return None
        raise ContractError(f"{label}: missing flow")
    if isinstance(value, (bool, np.bool_)):
        raise ContractError(f"{label}: invalid flow")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ContractError(f"{label}: invalid flow") from exc
    if not math.isfinite(number) or number < 0:
        raise ContractError(f"{label}: flow must be finite and non-negative")
    return number


def _band(bounds):
    if not isinstance(bounds, list) or len(bounds) != 2:
        raise ContractError("Audited band must contain two numeric endpoints")
    lower = _flow(bounds[0], "Band lower endpoint")
    upper = _flow(bounds[1], "Band upper endpoint")
    if lower > upper:
        raise ContractError("Audited band endpoints are reversed")
    def display(value):
        return f"{value:.2f}".rstrip("0").rstrip(".")
    return display(lower) if lower == upper else f"{display(lower)}–{display(upper)}"


def build_comparison(model, oof, client, audit):
    """Validate joins and targets; return all sites and identically paired metrics.

    The versioned preflight contains reviewed coverage exclusions and derived
    bands. File provenance is checked by load_comparison before this pure builder.
    No fitted model is invoked and no observed or predicted count is rounded.
    """
    if audit.get("protocol_version") != PROTOCOL:
        raise ContractError("Unsupported comparison protocol in preflight audit")
    observed_columns = [f"obs_peak_{direction}_ped_per_h" for direction in TARGETS]
    model = _keyed(model, "site_id", ["source_location_id", "road_no", "slk_km",
                                    *observed_columns], "Model data")
    client = _keyed(client, "ID", ["ROAD_NO", "SLK", "Ped_Peak_Cross", "Ped_Peak_Along"],
                    "Client reference")
    checked = _keyed(pd.DataFrame(audit.get("sites", [])), "site_id",
                     ["available", "cross_eligible", "along_eligible"], "Preflight")
    if set(checked.index) != set(model.index):
        raise ContractError("Preflight and model site sets differ")
    if model.empty:
        raise ContractError("No survey sites")
    source_ids = model.source_location_id.dropna()
    source_ids = source_ids[source_ids.astype(str).str.strip().ne("")]
    if source_ids.duplicated().any():
        raise ContractError("Duplicate source_location_id would reuse a client reference")
    required = {"Model", "Target", "site_id", "road_no", "actual", "predicted"}
    if not required.issubset(oof.columns):
        raise ContractError("OOF table is missing required columns")
    selected = oof.loc[oof.Model.eq("Linear regression")].copy()
    if set(selected.Target) != set(TARGETS.values()):
        raise ContractError("Selected OOF targets must be Cross-road and Along-road")
    predictions = {}
    for direction, target in TARGETS.items():
        values = _keyed(selected.loc[selected.Target.eq(target)], "site_id", [], target)
        if set(values.index) != set(model.index):
            raise ContractError(f"{target}: OOF and model site sets differ")
        values = values.loc[model.index]
        if not values.road_no.astype(str).eq(model.road_no.astype(str)).all():
            raise ContractError(f"{target}: OOF road grouping identifiers differ")
        for site in model.index:
            actual = _flow(values.loc[site, "actual"], f"{site} OOF actual")
            current = _flow(model.loc[site, f"obs_peak_{direction}_ped_per_h"], site)
            if not math.isclose(actual, current, abs_tol=1e-9, rel_tol=0):
                raise ContractError(f"{site} {target}: OOF actual does not match corrected target")
            _flow(values.loc[site, "predicted"], f"{site} OOF prediction")
        predictions[direction] = values

    site_rows, error_rows = [], []
    for site, observation in model.iterrows():
        record = checked.loc[site]
        source = observation.source_location_id
        source = None if pd.isna(source) or str(source).strip() == "" else str(source).strip()
        baseline = client.loc[source] if source in client.index else None
        old = {
            direction: None if baseline is None else _flow(
                baseline[f"Ped_Peak_{'Cross' if direction == 'cross' else 'Along'}"],
                f"{site} {direction} reference", missing_allowed=True,
            ) for direction in TARGETS
        }
        available = all(value is not None for value in old.values())
        if available != bool(record.available):
            raise ContractError(f"{site}: reference availability changed since preflight")
        if available and record.get("source_location_id") != source:
            raise ContractError(f"{site}: audited source ID differs")
        eligibility = {"cross": old["cross"] is not None,
                       "along": old["along"] is not None and site not in ALONG_EXCLUSIONS}
        for direction in TARGETS:
            if eligibility[direction] != bool(record[f"{direction}_eligible"]):
                raise ContractError(f"{site}: {direction} eligibility differs from preflight")
        notes = []
        if not available:
            notes.append("Client reference row absent" if baseline is None
                         else "Client reference flow values missing")
        if site in ALONG_EXCLUSIONS:
            notes.append("Excluded from along-road metrics: " + ALONG_EXCLUSIONS[site])
        unique_category = None
        if available:
            categories = record.get("cross_codes")
            if not isinstance(categories, list) or not categories or any(
                isinstance(code, bool) or not isinstance(code, int) or code not in range(1, 12)
                for code in categories
            ):
                raise ContractError(f"{site}: invalid audited crossing categories")
            if len(set(categories)) == 1:
                unique_category = categories[0]
            else:
                notes.append("Mixed crossing categories: " + ", ".join(map(str, categories)))
            if len(record.get("cways", [])) > 1:
                notes.append("Client mean spans multiple carriageways")
        row = {"site_id": site, "road_no": observation.road_no,
               "slk_km": observation.slk_km, "source_location_id": source}
        for direction in TARGETS:
            actual = float(observation[f"obs_peak_{direction}_ped_per_h"])
            predicted = float(predictions[direction].loc[site, "predicted"])
            row[f"obs_peak_{direction}_ped_per_h"] = actual
            row[f"pred_peak_{direction}_ped_per_h"] = predicted
            row[f"existing_irap_{direction}_recoded_ped_per_h"] = old[direction]
            if direction == "cross":
                row.update(observed_cross_category=flow_category(actual),
                           predicted_cross_category=flow_category(predicted),
                           existing_ausrap_cross_category=unique_category,
                           existing_ausrap_cross_band=_band(record.cross_band_mean)
                           if available else None)
            else:
                row["existing_ausrap_along_combined_band"] = (
                    _band(record.along_band_mean) if available else None
                )
            reason = ("client_reference_unavailable" if old[direction] is None else
                      ALONG_EXCLUSIONS.get(site, "") if direction == "along" else "")
            model_error = predicted - actual
            reference_error = None if old[direction] is None else old[direction] - actual
            error_rows.append({
                "site_id": site, "direction": TARGETS[direction], "observed": actual,
                "model_oof": predicted, "existing_recoded": old[direction],
                "eligible": eligibility[direction], "exclusion_reason": reason,
                "model_error": model_error, "model_absolute_error": abs(model_error),
                "model_squared_error": model_error ** 2,
                "reference_error": reference_error,
                "reference_absolute_error": None if reference_error is None else abs(reference_error),
                "reference_squared_error": None if reference_error is None else reference_error ** 2,
            })
        row.update(cross_evaluation_eligible=eligibility["cross"],
                   along_evaluation_eligible=eligibility["along"],
                   comparison_status="compared_both" if all(eligibility.values()) else
                   "compared_cross_only" if eligibility["cross"] else "reference_unavailable",
                   comparison_notes="; ".join(notes))
        site_rows.append(row)
    errors = pd.DataFrame(error_rows)
    metrics = []
    for target in TARGETS.values():
        common = errors.loc[errors.direction.eq(target) & errors.eligible]
        for name, prefix in [(MODEL_LABEL, "model"), (REFERENCE_LABEL, "reference")]:
            metrics.append({
                "direction": target, "method": name, "n": len(common),
                "mae": float(common[f"{prefix}_absolute_error"].mean()) if len(common) else None,
                "rmse": math.sqrt(float(common[f"{prefix}_squared_error"].mean()))
                if len(common) else None,
            })
    sites = pd.DataFrame(site_rows)
    for name in ("observed_cross_category", "predicted_cross_category", "existing_ausrap_cross_category"):
        sites[name] = sites[name].astype("Int64")
    return ComparisonResult(sites, errors, pd.DataFrame(metrics), {
        "protocol_version": PROTOCOL, "evaluation_schema_version": "survey_comparison_v1",
        "prediction_basis": "road_grouped_oof", "selected_model": "Linear regression",
        "units": "pedestrians_per_hour", "site_count": len(sites),
        "category_rule": "positive_upper_bound_v1", "category_upper_bounds": list(UPPER_BOUNDS),
        "along_exclusions": ALONG_EXCLUSIONS,
        "sample_ids": {target: errors.loc[errors.direction.eq(target) & errors.eligible,
                                        "site_id"].tolist() for target in TARGETS.values()},
        "limitations": [
            "Internal road-grouped CV; model and feature selection used these survey data.",
            "Existing reference is a client recoding and aggregation of ordinal estimates.",
            "Survey coverage, peak definitions and observation periods may differ.",
            "Multi-carriageway matches preserve the client's existing aggregation.",
            "Refitted sensitivity analysis excluding the two corrected sites is not included.",
        ],
    })


def load_comparison(project_root, audit_path=None):
    """Read pinned inputs; reject stale preflight before using its derived bands."""
    root = Path(project_root).resolve()
    path = Path(audit_path) if audit_path else root / AUDIT_PATH
    audit = json.loads(path.read_text(encoding="utf-8"))
    fingerprints = {record["path"]: record for record in audit["source_files"]}
    checked_sources = []
    for relative in (MODEL_PATH, CLIENT_PATH, WORDS_PATH, OOF_PATH):
        if relative not in fingerprints:
            raise ContractError(f"Preflight does not fingerprint {relative}")
        content = (root / relative).read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if actual != fingerprints[relative]["sha256"]:
            raise ContractError(f"Source changed; repeat preflight before evaluation: {relative}")
        checked_sources.append({"path": relative, "sha256": actual, "size_bytes": len(content)})
    for evidence in audit.get("survey_evidence", []):
        actual = hashlib.sha256((root / evidence["path"]).read_bytes()).hexdigest()
        if actual != evidence["sha256"]:
            raise ContractError(f"Survey evidence changed: {evidence['path']}")
    result = build_comparison(
        pd.read_excel(root / MODEL_PATH, sheet_name="Model_Data", dtype={"site_id": str}),
        pd.read_csv(root / OOF_PATH, dtype={"site_id": str}),
        pd.read_csv(root / CLIENT_PATH, dtype={"ID": str}), audit,
    )
    result.manifest.update(
        generated_at_utc=datetime.now(UTC).isoformat(), sources=checked_sources,
        preflight_path=str(path.relative_to(root)) if path.is_relative_to(root) else str(path),
        preflight_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )
    return result
