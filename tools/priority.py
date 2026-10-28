"""Priority rules for open tree issues and road defects.

These are the only implementation of the rules: the workbooks and any app should call
these functions rather than re-deriving them. Each function takes rows as read by
common.read_csv and returns new dicts, most urgent first.
"""

import datetime

DONE_DEFECT = {"Repaired", "Closed"}


def parse_date(s):
    return datetime.date.fromisoformat(s)


def add_working_days(start, n):
    """Monday to Friday only; public holidays are not excluded."""
    d = start
    while n > 0:
        d += datetime.timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def rank(lookups, list_name, value, missing=99):
    try:
        return int(float(lookups[list_name][value]["rank"]))
    except (KeyError, ValueError):
        return missing


def road_priority(segments, defects, lookups, today):
    """Open defects (status not Repaired or Closed), ranked.

    Order: urgent first, then overdue for investigation, then road class (motorway
    first), then primary freight routes, then oldest report.
    Urgent means traffic is swerving or there is a public safety concern. Urgent
    reports are due for investigation 1 day after reporting, others 7 working days.
    """
    seg = {s["segment_id"]: s for s in segments}
    targets = lookups["road_response_target"]
    out = []
    for d in defects:
        if d["status"] in DONE_DEFECT:
            continue
        s = seg.get(d["segment_id"], {})
        reported = parse_date(d["reported_date"])
        urgent = "Yes" in (d["traffic_swerving"], d["public_safety_concern"])
        if urgent:
            due = reported + datetime.timedelta(days=int(targets["Urgent"]["rank"]))
        else:
            due = add_working_days(reported, int(targets["Non-urgent"]["rank"]))
        overdue = d["status"] == "Open" and today > due
        out.append({
            **d,
            "street": s.get("street", ""), "suburb": s.get("suburb", ""), "road_class": s.get("road_class", ""),
            "primary_freight_route": s.get("primary_freight_route", ""),
            "state_controlled": s.get("state_controlled", ""),
            "urgency": "Urgent" if urgent else "Non-urgent", "investigate_by": due.isoformat(),
            "overdue": "Yes" if overdue else "No", "days_open": (today - reported).days,
            "_key": (not urgent, not overdue, rank(lookups, "road_class", s.get("road_class")),
                     s.get("primary_freight_route") != "Yes", reported, d["defect_id"]),
        })
    out.sort(key=lambda r: r["_key"])
    for i, r in enumerate(out, 1):
        del r["_key"]
        r["priority"] = i
    return out


def tree_priority(assets, assessments, works, lookups, today):
    """Trees whose latest assessment recommends action that has not been completed, ranked.

    A tree's latest assessment is the one with the latest date (ties: highest ID). It is
    resolved when a works row for that assessment_id has status Completed.
    Order: risk rating (Extreme first), then condition (Dead first), then oldest assessment.
    """
    tree = {a["tree_id"]: a for a in assets}
    latest = {}
    for a in assessments:
        k = (a["assessment_date"], a["assessment_id"])
        if a["tree_id"] not in latest or k > (latest[a["tree_id"]]["assessment_date"],
                                              latest[a["tree_id"]]["assessment_id"]):
            latest[a["tree_id"]] = a
    done = {w["assessment_id"] for w in works if w["status"] == "Completed" and w["assessment_id"]}
    out = []
    for a in latest.values():
        if a["recommended_outcome"] == "No action" or a["assessment_id"] in done:
            continue
        t = tree.get(a["tree_id"], {})
        assessed = parse_date(a["assessment_date"])
        out.append({
            **a,
            "common_name": t.get("common_name", ""), "latitude": t.get("latitude", ""),
            "longitude": t.get("longitude", ""), "protected_area_ids": t.get("protected_area_ids", ""),
            "open_works": sum(1 for w in works if w["assessment_id"] == a["assessment_id"]
                              and w["status"] not in ("Completed", "Cancelled")),
            "days_since_assessed": (today - assessed).days,
            "_key": (rank(lookups, "tree_risk_rating", a["risk_rating"]),
                     rank(lookups, "tree_condition", a["condition"]), assessed, a["assessment_id"]),
        })
    out.sort(key=lambda r: r["_key"])
    for i, r in enumerate(out, 1):
        del r["_key"]
        r["priority"] = i
    return out
