"""Download the complete public Main Roads measured SLK line layer for local matching.

No project locations are read or sent to the data provider. Refresh this snapshot
when Main Roads publishes a new network; see data/external_raw/README.md.
"""

import json
import gzip
import shutil
import sqlite3
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import urlopen

SERVICE = "https://gisservices.mainroads.wa.gov.au/arcgis/rest/services/OpenData/RoadAssets_DataPortal/MapServer/18/query"
DESTINATION = Path(__file__).resolve().parents[1] / "data/external_raw/main_roads_slk/road_slk.sqlite.gz"


def query(parameters):
    with urlopen(SERVICE + "?" + urlencode(parameters), timeout=120) as response:
        return json.load(response)


def main():
    DESTINATION.parent.mkdir(parents=True, exist_ok=True)
    count = int(query({"where": "1=1", "returnCountOnly": "true", "f": "json"})["count"])
    temporary = DESTINATION.with_suffix(".sqlite.part")
    temporary.unlink(missing_ok=True)
    connection = sqlite3.connect(temporary)
    try:
        connection.execute("CREATE TABLE roads (objectid INTEGER PRIMARY KEY, road TEXT NOT NULL, start_slk REAL, end_slk REAL, cway TEXT, min_lat REAL, max_lat REAL, min_lon REAL, max_lon REAL, paths TEXT NOT NULL)")
        for offset in range(0, count, 1000):
            payload = query({
                "where": "1=1", "outFields": "OBJECTID,ROAD,START_SLK,END_SLK,CWY",
                "returnGeometry": "true", "returnM": "true", "outSR": 4326,
                "resultOffset": offset, "resultRecordCount": 1000,
                "orderByFields": "OBJECTID ASC", "f": "json",
            })
            if "error" in payload or not payload.get("features"):
                raise RuntimeError(f"Incomplete Main Roads page at offset {offset}: {payload.get('error')}")
            rows = []
            for feature in payload["features"]:
                properties = feature["attributes"]
                paths = feature.get("geometry", {}).get("paths", [])
                vertices = [p for path in paths for p in path]
                if not vertices or any(len(p) < 3 or p[2] is None for p in vertices):
                    continue
                rows.append((properties["OBJECTID"], properties["ROAD"], properties["START_SLK"], properties["END_SLK"], properties["CWY"],
                             min(p[1] for p in vertices), max(p[1] for p in vertices),
                             min(p[0] for p in vertices), max(p[0] for p in vertices),
                             json.dumps(paths, separators=(",", ":"))))
            connection.executemany("INSERT INTO roads VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
            connection.commit()
            print(f"{min(offset+1000,count)}/{count}", flush=True)
        connection.execute("CREATE INDEX roads_road_slk ON roads(road,start_slk,end_slk)")
        connection.execute("CREATE INDEX roads_bbox_lat ON roads(min_lat,max_lat)")
        connection.execute("CREATE INDEX roads_bbox_lon ON roads(min_lon,max_lon)")
        saved = connection.execute("SELECT COUNT(*) FROM roads").fetchone()[0]
        if saved < count * 0.99:
            raise RuntimeError(f"Only {saved} of {count} road geometries included measured vertices")
    finally:
        connection.close()
    compressed = DESTINATION.with_suffix(".gz.part")
    with temporary.open("rb") as source, gzip.open(compressed, "wb", compresslevel=9) as target:
        shutil.copyfileobj(source, target)
    compressed.replace(DESTINATION)
    temporary.unlink()
    print(f"Saved {saved} measured road lines to {DESTINATION}")


if __name__ == "__main__":
    main()
