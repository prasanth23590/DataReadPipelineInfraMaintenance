"""Shared helpers: Council ArcGIS access, CSV schemas and I/O, lookups."""

import csv
import json
import math
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TREES = ROOT / "trees"
ROADS = ROOT / "roads"
LOOKUPS = ROOT / "lookups" / "lookups.csv"

ARCGIS = "https://services2.arcgis.com/dEKgZETqwmDAh1rP/arcgis/rest/services"

# Column order of every table. Register tables are rebuilt from Council data by the
# fetch scripts; log tables are yours and are never overwritten.
SCHEMAS = {
    "trees/assets.csv": [
        "tree_id", "source", "source_tree_id", "latitude", "longitude", "scientific_name", "common_name",
        "family", "height_m", "crown_width_m", "dbh_mm", "year_established", "protected_area_ids",
        "in_significant_landscape_tree_overlay",
    ],
    "trees/protected_areas.csv": [
        "area_id", "layer", "category", "description", "centroid_latitude", "centroid_longitude", "area_m2",
    ],
    "trees/assessments.csv": [
        "assessment_id", "tree_id", "assessment_date", "assessor", "condition", "issue_type", "risk_rating",
        "recommended_outcome", "council_request_ref", "notes",
    ],
    "trees/works.csv": [
        "work_id", "tree_id", "assessment_id", "work_date", "work_type", "clearance_context", "status",
        "crew", "council_request_ref", "notes",
    ],
    "roads/segments.csv": [
        "segment_id", "source_objectid", "street", "suburb", "road_class", "length_m", "mid_latitude",
        "mid_longitude", "primary_freight_route", "state_controlled",
    ],
    "roads/defects.csv": [
        "defect_id", "segment_id", "reported_date", "latitude", "longitude", "defect_type", "traffic_swerving",
        "public_safety_concern", "status", "council_request_ref", "notes",
    ],
    "roads/repairs.csv": [
        "repair_id", "defect_id", "repair_date", "repair_type", "status", "crew", "notes",
    ],
}

# Example rows written when a log file is first created, to show the expected format.
EXAMPLES = {
    "trees/assessments.csv": ["HA-0001", "SHW-0661", "2026-10-28", "EXAMPLE", "Fair", "Fallen or broken branches",
                              "Medium", "Pruning", "", "EXAMPLE row: replace or delete"],
    "trees/works.csv": ["WK-0001", "SHW-0661", "HA-0001", "2026-11-04", "Clearance pruning", "Verge or footpath",
                        "Scheduled", "", "", "EXAMPLE row: replace or delete"],
    "roads/defects.csv": ["DF-0001", "RD-000001", "2026-10-28", "-27.3775877", "153.0201129", "Pothole", "Yes", "No",
                          "Open", "", "EXAMPLE row: replace or delete"],
    "roads/repairs.csv": ["RP-0001", "DF-0001", "2026-10-30", "Pothole fill", "Scheduled", "",
                          "EXAMPLE row: replace or delete"],
}


def get_json(url, params):
    with urllib.request.urlopen(url + "?" + urllib.parse.urlencode(params), timeout=180) as r:
        data = json.load(r)
    if "error" in data:
        raise RuntimeError(f"{url}: {data['error']}")
    return data


def query_all(service, **params):
    """Page through every feature of layer 0 of a Council hosted Feature Service."""
    url = f"{ARCGIS}/{service}/FeatureServer/0/query"
    base = {"where": "1=1", "outFields": "*", "f": "json", "resultRecordCount": 2000}
    base.update(params)
    feats, offset = [], 0
    while True:
        data = get_json(url, {**base, "resultOffset": offset})
        feats += data["features"]
        if not data.get("exceededTransferLimit") and len(data["features"]) < base["resultRecordCount"]:
            return feats
        offset += len(data["features"])


def metres(lon1, lat1, lon2, lat2):
    """Equirectangular distance in metres; accurate to well under 1% at city scale."""
    k = math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot((lon2 - lon1) * k, lat2 - lat1) * 111_320


def read_csv(rel):
    with open(ROOT / rel, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def write_csv(rel, rows):
    """Write dict rows in the schema's column order."""
    path = ROOT / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=SCHEMAS[rel], lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def ensure_log(rel):
    """Create a log file with its header and example row, unless it already exists."""
    if not (ROOT / rel).exists():
        write_csv(rel, [dict(zip(SCHEMAS[rel], EXAMPLES[rel]))])


def load_lookups():
    """Return {list_name: {value: row}} from lookups.csv, in file order."""
    out = {}
    with open(LOOKUPS, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            out.setdefault(row["list"], {})[row["value"]] = row
    return out
