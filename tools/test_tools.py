"""Run:  python3 -m unittest tools/test_tools.py   (from the repo root)"""

import datetime
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from common import SCHEMAS, load_lookups  # noqa: E402
from priority import add_working_days, road_priority, tree_priority  # noqa: E402
from validate import validate  # noqa: E402

LOOKUPS = load_lookups()
TODAY = datetime.date(2026, 10, 28)  # a Wednesday


def seg(sid, cls, freight="No"):
    return {"segment_id": sid, "street": "X STREET", "suburb": "Y", "road_class": cls,
            "primary_freight_route": freight, "state_controlled": "No"}


def defect(did, sid, reported, swerve="No", safety="No", status="Open"):
    return {"defect_id": did, "segment_id": sid, "reported_date": reported, "latitude": "-27.47",
            "longitude": "153.02", "defect_type": "Pothole", "traffic_swerving": swerve,
            "public_safety_concern": safety, "status": status, "council_request_ref": "", "notes": ""}


def assessment(aid, tid, date, risk="Medium", condition="Fair", outcome="Pruning"):
    return {"assessment_id": aid, "tree_id": tid, "assessment_date": date, "assessor": "", "condition": condition,
            "issue_type": "Other", "risk_rating": risk, "recommended_outcome": outcome,
            "council_request_ref": "", "notes": ""}


def work(wid, tid, aid, status):
    return {"work_id": wid, "tree_id": tid, "assessment_id": aid, "work_date": "2026-10-28",
            "work_type": "Clearance pruning", "clearance_context": "", "status": status, "crew": "",
            "council_request_ref": "", "notes": ""}


class WorkingDays(unittest.TestCase):
    def test_skips_weekend(self):
        self.assertEqual(add_working_days(datetime.date(2026, 10, 30), 1), datetime.date(2026, 11, 2))  # Fri -> Mon
        self.assertEqual(add_working_days(datetime.date(2026, 10, 28), 7), datetime.date(2026, 11, 6))


class RoadPriority(unittest.TestCase):
    segments = [seg("RD-1", "Neighbourhood / local"), seg("RD-2", "Arterial"), seg("RD-3", "Arterial", "Yes")]

    def test_urgent_then_overdue_then_class_then_freight(self):
        defects = [
            defect("D-local", "RD-1", "2026-10-27"),
            defect("D-arterial", "RD-2", "2026-10-27"),
            defect("D-freight", "RD-3", "2026-10-27"),
            defect("D-overdue", "RD-1", "2026-10-01"),
            defect("D-urgent", "RD-1", "2026-10-27", swerve="Yes"),
        ]
        order = [r["defect_id"] for r in road_priority(self.segments, defects, LOOKUPS, TODAY)]
        self.assertEqual(order, ["D-urgent", "D-overdue", "D-freight", "D-arterial", "D-local"])

    def test_due_dates_and_closed_excluded(self):
        defects = [defect("A", "RD-1", "2026-10-26", safety="Yes"), defect("B", "RD-1", "2026-10-28"),
                   defect("C", "RD-1", "2026-10-01", status="Repaired")]
        rows = {r["defect_id"]: r for r in road_priority(self.segments, defects, LOOKUPS, TODAY)}
        self.assertEqual(set(rows), {"A", "B"})
        self.assertEqual((rows["A"]["investigate_by"], rows["A"]["overdue"]), ("2026-10-27", "Yes"))
        self.assertEqual((rows["B"]["investigate_by"], rows["B"]["overdue"]), ("2026-11-06", "No"))

    def test_investigating_is_never_overdue(self):
        rows = road_priority(self.segments, [defect("A", "RD-1", "2026-01-01", status="Investigating")],
                             LOOKUPS, TODAY)
        self.assertEqual(rows[0]["overdue"], "No")


class TreePriority(unittest.TestCase):
    assets = [{"tree_id": t, "common_name": "", "latitude": "", "longitude": "", "protected_area_ids": ""}
              for t in ("T1", "T2", "T3", "T4")]

    def test_latest_assessment_drives_and_completed_work_resolves(self):
        assessments = [
            assessment("A1", "T1", "2026-01-01", risk="Extreme"),
            assessment("A2", "T1", "2026-06-01", outcome="No action"),  # later: tree now fine
            assessment("A3", "T2", "2026-05-01", risk="Low"),
            assessment("A4", "T3", "2026-05-01", risk="High"),
            assessment("A5", "T4", "2026-05-01", risk="High"),
        ]
        works = [work("W1", "T4", "A5", "Completed"), work("W2", "T3", "A4", "Scheduled")]
        rows = tree_priority(self.assets, assessments, works, LOOKUPS, TODAY)
        self.assertEqual([r["tree_id"] for r in rows], ["T3", "T2"])
        self.assertEqual(rows[0]["open_works"], 1)


class Validate(unittest.TestCase):
    def tables(self):
        t = {name: [] for name in SCHEMAS}
        t["trees/assets.csv"] = [dict.fromkeys(SCHEMAS["trees/assets.csv"], "") | {"tree_id": "T1"}]
        t["roads/segments.csv"] = [dict.fromkeys(SCHEMAS["roads/segments.csv"], "")
                                   | {"segment_id": "RD-1", "road_class": "Arterial"}]
        t["roads/defects.csv"] = [defect("D1", "RD-1", "2026-10-28")]
        t["trees/assessments.csv"] = [assessment("A1", "T1", "2026-10-28")]
        return t

    def test_valid_tables_pass(self):
        self.assertEqual(validate(self.tables(), LOOKUPS), [])

    def test_catches_bad_rows(self):
        t = self.tables()
        t["roads/defects.csv"].append(defect("D1", "RD-9", "28/10/2026", swerve="Maybe"))
        t["roads/defects.csv"][1]["latitude"] = "-33.9"
        t["trees/works.csv"] = [work("W1", "T1", "A9", "Done")]
        errors = "\n".join(validate(t, LOOKUPS))
        for expected in ["duplicate defect_id D1", "'RD-9' not found", "not YYYY-MM-DD", "'Maybe' is not in lookup",
                         "outside Brisbane", "'A9' not found", "'Done' is not in lookup"]:
            self.assertIn(expected, errors)


if __name__ == "__main__":
    unittest.main()
