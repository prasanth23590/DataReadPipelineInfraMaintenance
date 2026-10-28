"""Check every dataset table before committing or loading it into an app.

Run:  python3 tools/validate.py     (exit code 1 when anything is wrong)
"""

import datetime
import sys

from common import SCHEMAS, load_lookups, read_csv

# (table, column) -> lookup list its values must come from
CONTROLLED = {
    ("trees/assessments.csv", "condition"): "tree_condition",
    ("trees/assessments.csv", "issue_type"): "tree_issue_type",
    ("trees/assessments.csv", "risk_rating"): "tree_risk_rating",
    ("trees/assessments.csv", "recommended_outcome"): "tree_outcome",
    ("trees/works.csv", "work_type"): "tree_work_type",
    ("trees/works.csv", "clearance_context"): "tree_clearance_context",
    ("trees/works.csv", "status"): "work_status",
    ("roads/segments.csv", "road_class"): "road_class",
    ("roads/defects.csv", "defect_type"): "road_defect_type",
    ("roads/defects.csv", "traffic_swerving"): "yes_no",
    ("roads/defects.csv", "public_safety_concern"): "yes_no",
    ("roads/defects.csv", "status"): "road_defect_status",
    ("roads/repairs.csv", "repair_type"): "road_repair_type",
    ("roads/repairs.csv", "status"): "work_status",
}
REQUIRED = {
    "trees/assessments.csv": ["assessment_id", "tree_id", "assessment_date", "condition", "risk_rating",
                              "recommended_outcome"],
    "trees/works.csv": ["work_id", "tree_id", "work_date", "work_type", "status"],
    "roads/defects.csv": ["defect_id", "segment_id", "reported_date", "latitude", "longitude", "defect_type",
                          "traffic_swerving", "public_safety_concern", "status"],
    "roads/repairs.csv": ["repair_id", "defect_id", "repair_date", "repair_type", "status"],
}
DATES = {"trees/assessments.csv": "assessment_date", "trees/works.csv": "work_date",
         "roads/defects.csv": "reported_date", "roads/repairs.csv": "repair_date"}
# (table, column, target table, target key); blanks are left to REQUIRED
FOREIGN = [
    ("trees/assessments.csv", "tree_id", "trees/assets.csv", "tree_id"),
    ("trees/works.csv", "tree_id", "trees/assets.csv", "tree_id"),
    ("trees/works.csv", "assessment_id", "trees/assessments.csv", "assessment_id"),
    ("roads/defects.csv", "segment_id", "roads/segments.csv", "segment_id"),
    ("roads/repairs.csv", "defect_id", "roads/defects.csv", "defect_id"),
]
BRISBANE = (-28.0, -26.9, 152.6, 153.6)  # lat min, lat max, lon min, lon max


def validate(tables, lookups):
    """Return a list of error strings; empty means valid."""
    errors = []
    for name, cols in SCHEMAS.items():
        rows = tables[name]
        if rows and list(rows[0].keys()) != cols:
            errors.append(f"{name}: columns must be {', '.join(cols)}")
            continue
        seen = set()
        for i, r in enumerate(rows, 2):
            key = r[cols[0]]
            if not key:
                errors.append(f"{name} line {i}: {cols[0]} is blank")
            elif key in seen:
                errors.append(f"{name} line {i}: duplicate {cols[0]} {key}")
            seen.add(key)
            for c in REQUIRED.get(name, []):
                if not r[c]:
                    errors.append(f"{name} line {i}: {c} is blank")
            if name in DATES and r[DATES[name]]:
                try:
                    datetime.date.fromisoformat(r[DATES[name]])
                except ValueError:
                    errors.append(f"{name} line {i}: {DATES[name]} '{r[DATES[name]]}' is not YYYY-MM-DD")
    for (name, col), lst in CONTROLLED.items():
        for i, r in enumerate(tables[name], 2):
            if r[col] and r[col] not in lookups[lst]:
                errors.append(f"{name} line {i}: {col} '{r[col]}' is not in lookup list {lst}")
    for name, col, target, tkey in FOREIGN:
        keys = {r[tkey] for r in tables[target]}
        for i, r in enumerate(tables[name], 2):
            if r[col] and r[col] not in keys:
                errors.append(f"{name} line {i}: {col} '{r[col]}' not found in {target}")
    areas = {r["area_id"] for r in tables["trees/protected_areas.csv"]}
    for i, r in enumerate(tables["trees/assets.csv"], 2):
        for area in filter(None, r["protected_area_ids"].split(";")):
            if area not in areas:
                errors.append(f"trees/assets.csv line {i}: protected area {area} not found in trees/protected_areas.csv")
    tree_of = {r["assessment_id"]: r["tree_id"] for r in tables["trees/assessments.csv"]}
    for i, r in enumerate(tables["trees/works.csv"], 2):
        if r["assessment_id"] in tree_of and tree_of[r["assessment_id"]] != r["tree_id"]:
            errors.append(f"trees/works.csv line {i}: assessment {r['assessment_id']} is for tree "
                          f"{tree_of[r['assessment_id']]}, not {r['tree_id']}")
    for i, r in enumerate(tables["roads/defects.csv"], 2):
        try:
            lat, lon = float(r["latitude"]), float(r["longitude"])
            if not (BRISBANE[0] <= lat <= BRISBANE[1] and BRISBANE[2] <= lon <= BRISBANE[3]):
                errors.append(f"roads/defects.csv line {i}: location {lat}, {lon} is outside Brisbane")
        except ValueError:
            errors.append(f"roads/defects.csv line {i}: latitude/longitude must be decimal degrees")
    return errors


def main():
    tables = {name: read_csv(name) for name in SCHEMAS}
    errors = validate(tables, load_lookups())
    for e in errors:
        print(e)
    print(f"{len(errors)} problem(s) in {sum(len(t) for t in tables.values()):,} rows")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
