"""Resolve WA road number/SLK and coordinates with measured Main Roads geometry."""

from __future__ import annotations

import gzip
import hashlib
import json
import math
import os
import shutil
import sqlite3
import tempfile
from pathlib import Path

import pandas as pd

from pedflow.exceptions import ContractError
from pedflow.flow import flow_category

DEFAULT_SNAPSHOT = Path(__file__).resolve().parents[3] / "data/external_raw/main_roads_slk/road_slk.sqlite.gz"
MATCH_RADIUS_M = 30.0
AMBIGUITY_GAP_M = 5.0
REFERENCE_TOLERANCE_KM = 0.05


def _present(value):
    return pd.notna(value) and str(value).strip() != ""


def _vertices(feature):
    for path in feature.get("geometry", {}).get("paths", []):
        for point in path:
            if len(point) < 3 or point[2] is None:
                break
        else:
            if len(path) >= 2:
                yield path


def _at_slk(feature, slk):
    for path in _vertices(feature):
        for a, b in zip(path, path[1:]):
            if min(a[2], b[2]) - 1e-6 <= slk <= max(a[2], b[2]) + 1e-6:
                fraction = 0 if a[2] == b[2] else (slk - a[2]) / (b[2] - a[2])
                return (a[1] + fraction * (b[1] - a[1]),
                        a[0] + fraction * (b[0] - a[0]))
    return None


def _nearest(feature, latitude, longitude):
    closest = None
    scale_x = 111_320 * math.cos(math.radians(latitude))
    for path in _vertices(feature):
        for a, b in zip(path, path[1:]):
            ax, ay = (a[0] - longitude) * scale_x, (a[1] - latitude) * 110_540
            bx, by = (b[0] - longitude) * scale_x, (b[1] - latitude) * 110_540
            dx, dy = bx - ax, by - ay
            fraction = max(0, min(1, -(ax * dx + ay * dy) / (dx * dx + dy * dy))) if dx or dy else 0
            distance = math.hypot(ax + fraction * dx, ay + fraction * dy)
            if closest is None or distance < closest[0]:
                closest = (distance, a[2] + fraction * (b[2] - a[2]))
    return closest


class RoadLocator:
    """Query a local snapshot of the public measured Main Roads SLK layer."""

    def __init__(self, path=None):
        self.path = Path(path) if path else DEFAULT_SNAPSHOT
        self._ready_path = None

    def _database_path(self):
        if self._ready_path is not None:
            return self._ready_path
        if not self.path.exists():
            raise FileNotFoundError(f"Road SLK snapshot missing: {self.path}")
        if self.path.suffix != ".gz":
            self._ready_path = self.path
            return self.path
        digest = hashlib.sha256(self.path.read_bytes()).hexdigest()[:20]
        cached = Path(tempfile.gettempdir()) / f"pedflow-road-slk-{digest}.sqlite"
        if not cached.exists():
            temporary = cached.with_name(f"{cached.name}.{os.getpid()}.part")
            try:
                with gzip.open(self.path, "rb") as source, temporary.open("wb") as target:
                    shutil.copyfileobj(source, target)
                temporary.replace(cached)
            finally:
                temporary.unlink(missing_ok=True)
        self._ready_path = cached
        return cached

    def _query(self, statement, parameters):
        database = self._database_path()
        with sqlite3.connect(f"file:{database}?mode=ro", uri=True) as connection:
            rows = connection.execute(statement, parameters).fetchall()
        return [
            {"attributes": {"ROAD": road, "START_SLK": start, "END_SLK": end, "CWY": cway},
             "geometry": {"paths": json.loads(paths)}}
            for road, start, end, cway, paths in rows
        ]

    def by_road(self, road_no, slk_km, cway=None):
        sql = "SELECT road,start_slk,end_slk,cway,paths FROM roads WHERE road=? AND start_slk<=? AND end_slk>=?"
        args = [str(road_no).strip().upper(), slk_km, slk_km]
        if _present(cway):
            sql += " AND UPPER(cway)=?"
            args.append(str(cway).strip().upper())
        return self._query(sql, args)

    def near(self, latitude, longitude):
        lat_gap = 50 / 110_540
        lon_gap = 50 / (111_320 * math.cos(math.radians(latitude)))
        return self._query(
            "SELECT road,start_slk,end_slk,cway,paths FROM roads WHERE min_lat<=? AND max_lat>=? AND min_lon<=? AND max_lon>=?",
            [latitude + lat_gap, latitude - lat_gap, longitude + lon_gap, longitude - lon_gap],
        )


def resolve_locations(table: pd.DataFrame, locator=None) -> pd.DataFrame:
    """Return input rows with prediction coordinates and explicit road-match status."""
    if not isinstance(table, pd.DataFrame) or table.empty or table.columns.duplicated().any():
        raise ContractError("Location input needs at least one row and unique columns.")
    if "site_id" not in table:
        raise ContractError("Location input requires site_id.")
    sites = table.reset_index(drop=True).copy()
    sites["site_id"] = sites.site_id.astype("string").str.strip()
    if sites.site_id.isna().any() or sites.site_id.eq("").any() or sites.site_id.duplicated().any():
        raise ContractError("site_id must be unique and nonblank.")
    for column in ("latitude", "longitude", "road_no", "slk_km", "cway", "start_slk", "end_slk"):
        if column not in sites:
            sites[column] = pd.NA
    if "coordinate_crs" not in sites:
        sites["coordinate_crs"] = "EPSG:4326"
    if sites.coordinate_crs.astype(str).str.upper().ne("EPSG:4326").any():
        raise ContractError("Coordinates must use EPSG:4326.")
    for column in ("latitude", "longitude", "slk_km", "start_slk", "end_slk"):
        invalid = sites[column].map(_present) & pd.to_numeric(sites[column], errors="coerce").isna()
        if invalid.any():
            raise ContractError(f"{column} must be numeric for: {sites.loc[invalid, 'site_id'].tolist()}")
        sites[column] = pd.to_numeric(sites[column], errors="coerce")
    has_lat, has_lon = sites.latitude.notna(), sites.longitude.notna()
    if (has_lat != has_lon).any():
        raise ContractError("latitude and longitude must be supplied together.")
    has_road, has_slk = sites.road_no.map(_present), sites.slk_km.notna()
    segment = sites.start_slk.notna() & sites.end_slk.notna()
    if ((has_road != (has_slk | segment)) | (segment & has_slk)).any():
        raise ContractError("Supply road_no + slk_km, or road_no + start_slk + end_slk.")
    if (~has_lat & ~has_road).any():
        raise ContractError("Each row needs coordinates or a road number and SLK.")
    if (segment & (sites.start_slk >= sites.end_slk)).any():
        raise ContractError("Segment end_slk must exceed start_slk.")
    if has_lat.any() and ((~sites.latitude[has_lat].between(-90, 90)) | (~sites.longitude[has_lat].between(-180, 180))).any():
        raise ContractError("Invalid WGS84 coordinates.")
    for column in ("obs_peak_cross_ped_per_h", "obs_peak_along_ped_per_h"):
        if column in sites:
            invalid = sites[column].map(_present) & sites[column].map(flow_category).isna()
            if invalid.any():
                raise ContractError(f"{column} must be finite and non-negative when provided.")
    service = locator or RoadLocator()
    records = []
    for row in sites.to_dict("records"):
        coordinates = _present(row["latitude"])
        road = _present(row["road_no"])
        is_segment = _present(row["start_slk"]) and _present(row["end_slk"])
        point_slk = (row["start_slk"] + row["end_slk"]) / 2 if is_segment else row["slk_km"]
        if is_segment:
            row["slk_km"] = point_slk
        row.update(input_type="both" if coordinates and road else "coordinates" if coordinates else "road_segment" if is_segment else "road_slk",
                   matched_road_no=None, matched_slk_km=None, matched_cway=None,
                   road_offset_m=None, location_status="unmatched")
        try:
            if road:
                candidates = []
                for feature in service.by_road(row["road_no"], point_slk, row["cway"]):
                    position = _at_slk(feature, point_slk)
                    if position is None:
                        continue
                    attributes = feature["attributes"]
                    if coordinates:
                        nearest = _nearest(feature, row["latitude"], row["longitude"])
                        if nearest is None:
                            continue
                        candidates.append((nearest[0], nearest[1], position, attributes))
                    else:
                        candidates.append((0, point_slk, position, attributes))
                if not candidates:
                    row["location_status"] = "road_reference_not_found"
                elif not coordinates and len({(c[3]["ROAD"], c[3]["CWY"]) for c in candidates}) > 1:
                    row["location_status"] = "ambiguous_carriageway"
                else:
                    candidates.sort(key=lambda c: c[0])
                    distance, measured_slk, position, attributes = candidates[0]
                    if coordinates and (distance > MATCH_RADIUS_M or abs(measured_slk - point_slk) > REFERENCE_TOLERANCE_KM):
                        row["location_status"] = "road_coordinate_conflict"
                        row["road_offset_m"] = round(distance, 2)
                    elif coordinates and len(candidates) > 1 and candidates[1][0] - distance < AMBIGUITY_GAP_M and candidates[1][3]["CWY"] != attributes["CWY"]:
                        row["location_status"] = "ambiguous_carriageway"
                    else:
                        if not coordinates:
                            row["latitude"], row["longitude"] = position
                        row.update(matched_road_no=attributes["ROAD"], matched_slk_km=round(measured_slk, 3),
                                   _matched_slk_km_exact=measured_slk,
                                   matched_cway=attributes["CWY"], road_offset_m=round(distance, 2),
                                   location_status="matched")
            else:
                candidates = []
                for feature in service.near(row["latitude"], row["longitude"]):
                    nearest = _nearest(feature, row["latitude"], row["longitude"])
                    if nearest is not None:
                        candidates.append((*nearest, feature["attributes"]))
                candidates.sort(key=lambda c: c[0])
                if candidates and candidates[0][0] <= MATCH_RADIUS_M:
                    distance, measured_slk, attributes = candidates[0]
                    if len(candidates) > 1 and candidates[1][0] - distance < AMBIGUITY_GAP_M and (candidates[1][2]["ROAD"], candidates[1][2]["CWY"]) != (attributes["ROAD"], attributes["CWY"]):
                        row["location_status"] = "ambiguous_road"
                    else:
                        row.update(matched_road_no=attributes["ROAD"], matched_slk_km=round(measured_slk, 3),
                                   _matched_slk_km_exact=measured_slk,
                                   matched_cway=attributes["CWY"], road_offset_m=round(distance, 2),
                                   location_status="matched")
                else:
                    row["location_status"] = "no_nearby_road"
        except (OSError, sqlite3.Error, ValueError, KeyError, TypeError) as exc:
            row["location_status"] = "road_lookup_failed"
            row["location_error"] = str(exc)
        records.append(row)
    return pd.DataFrame(records)
