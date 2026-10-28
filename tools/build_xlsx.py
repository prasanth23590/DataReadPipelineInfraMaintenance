"""Build trees/trees.xlsx and roads/roads.xlsx from the CSV files.

Run:  python3 tools/build_xlsx.py [YYYY-MM-DD]

The workbooks are read-only planning views: edit the CSV files, then rebuild. The
optional date sets "today" for the priority sheets (default: the real date).
"""

import datetime
import sys

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from common import ROOT, load_lookups, read_csv
from priority import road_priority, tree_priority

FONT = Font(name="Arial", size=10)
HEADER = Font(name="Arial", size=10, bold=True, color="FFFFFF")
HEADER_FILL = PatternFill("solid", fgColor="1F4E78")
NUMERIC = {"latitude", "longitude", "mid_latitude", "mid_longitude", "centroid_latitude", "centroid_longitude",
           "height_m", "crown_width_m", "dbh_mm", "length_m", "area_m2", "source_tree_id", "source_objectid",
           "year_established", "required_clearance_m", "rank"}
DATES = {"assessment_date", "work_date", "reported_date", "repair_date", "investigate_by"}


def cell_value(col, v):
    if v in ("", None):
        return None
    if col in DATES:
        try:
            return datetime.date.fromisoformat(v)
        except ValueError:
            return v
    if col in NUMERIC:
        try:
            return float(v) if "." in str(v) else int(v)
        except ValueError:
            return v
    return v


def add_table(wb, title, rows, columns=None):
    ws = wb.create_sheet(title)
    columns = columns or (list(rows[0].keys()) if rows else [])
    ws.append(columns)
    for c in ws[1]:
        c.font, c.fill = HEADER, HEADER_FILL
        c.alignment = Alignment(wrap_text=True, vertical="center")
    for r in rows:
        ws.append([cell_value(c, r.get(c)) for c in columns])
    for i, col in enumerate(columns, 1):
        if col in DATES:
            for (c,) in ws.iter_rows(min_row=2, min_col=i, max_col=i):
                c.number_format = "yyyy-mm-dd"
        width = max([len(col)] + [len(str(r.get(col) or "")) for r in rows[:500]])
        ws.column_dimensions[get_column_letter(i)].width = min(max(width + 2, 9), 48)
    ws.freeze_panes = "B2"
    if rows:
        ws.auto_filter.ref = f"A1:{get_column_letter(len(columns))}{len(rows) + 1}"
    return ws


def add_readme(wb, lines):
    ws = wb.active
    ws.title = "README"
    ws.column_dimensions["A"].width = 120
    for i, text in enumerate(lines, 1):
        c = ws.cell(row=i, column=1, value=text)
        c.font = Font(name="Arial", size=14 if i == 1 else 10, bold=i == 1 or text.endswith(":"))
        c.alignment = Alignment(wrap_text=True, vertical="top")


def lookup_rows(lookups, prefixes):
    return [row for name, values in lookups.items() if name.startswith(prefixes) or name in ("work_status", "yes_no")
            for row in values.values()]


def finish(wb, path):
    for ws in wb.worksheets[1:]:
        for row in ws.iter_rows(min_row=2):
            for c in row:
                c.font = FONT
    wb.save(path)
    print(f"wrote {path.relative_to(ROOT.parent)}")


def build_trees(lookups, today):
    assets = read_csv("trees/assets.csv")
    assessments = read_csv("trees/assessments.csv")
    works = read_csv("trees/works.csv")
    clearance = lookups["tree_clearance_context"]
    works_view = [{**w, "required_clearance_m": clearance.get(w["clearance_context"], {}).get("rank", "")}
                  for w in works]
    wb = Workbook()
    add_readme(wb, [
        "Brisbane trees: maintenance register",
        f"Generated {datetime.date.today().isoformat()} from trees/*.csv; priority as at {today.isoformat()}.",
        "This workbook is a read-only view. Edit the CSV files and run tools/build_xlsx.py to update it.",
        "",
        "Sheets:",
        "Priority: trees whose latest assessment recommends action that is not yet completed, most urgent first "
        "(risk, then condition, then oldest assessment).",
        "Assets: every tree with its location. Tree_ID links all sheets.",
        "Assessments and Works: the health and maintenance logs.",
        "Protected_Areas: the protected-vegetation areas named in Assets.protected_area_ids.",
        "Lookups: allowed values; rank sets priority order.",
        "",
        "Limits:",
        "Only the Sherwood Arboretum's 1,181 trees: Council publishes no citywide tree inventory with locations.",
        "Council publishes no tree health or works records; the logs hold your own entries (row 1 is an example).",
        "See README.md for sources and full documentation.",
    ])
    add_table(wb, "Priority", tree_priority(assets, assessments, works, lookups, today),
              ["priority", "tree_id", "common_name", "risk_rating", "condition", "issue_type", "recommended_outcome",
               "assessment_date", "days_since_assessed", "open_works", "assessment_id", "latitude", "longitude",
               "protected_area_ids", "notes"])
    add_table(wb, "Assets", assets)
    add_table(wb, "Assessments", assessments)
    add_table(wb, "Works", works_view)
    add_table(wb, "Protected_Areas", read_csv("trees/protected_areas.csv"))
    add_table(wb, "Lookups", lookup_rows(lookups, "tree_"))
    finish(wb, ROOT / "trees" / "trees.xlsx")


def build_roads(lookups, today):
    segments = read_csv("roads/segments.csv")
    defects = read_csv("roads/defects.csv")
    wb = Workbook()
    add_readme(wb, [
        "Brisbane roads: defect and repair register",
        f"Generated {datetime.date.today().isoformat()} from roads/*.csv; priority as at {today.isoformat()}.",
        "This workbook is a read-only view. Edit the CSV files and run tools/build_xlsx.py to update it.",
        "",
        "Sheets:",
        "Priority: open defects, most urgent first (urgent, then overdue for investigation, then road class, then "
        "freight route, then oldest). Urgent = traffic swerving or public safety concern; Council investigates urgent "
        "reports within 24 hours and others within 7 working days.",
        "Segments: every built road segment in Council's road hierarchy, with its midpoint. Segment_ID links all sheets.",
        "Defects and Repairs: the road health and repair logs.",
        "Lookups: allowed values; rank sets priority order.",
        "",
        "Limits:",
        "Council publishes no pothole or road condition records; the logs hold your own entries (row 1 is an example).",
        "state_controlled and primary_freight_route are matched by geometry and are approximate. State-controlled "
        "roads are maintained by the Queensland Government, not Council.",
        "See README.md for sources and full documentation.",
    ])
    add_table(wb, "Priority", road_priority(segments, defects, lookups, today),
              ["priority", "defect_id", "urgency", "overdue", "investigate_by", "days_open", "status", "defect_type",
               "street", "suburb", "road_class", "primary_freight_route", "state_controlled", "segment_id",
               "latitude", "longitude", "reported_date", "notes"])
    add_table(wb, "Segments", segments)
    add_table(wb, "Defects", defects)
    add_table(wb, "Repairs", read_csv("roads/repairs.csv"))
    add_table(wb, "Lookups", lookup_rows(lookups, "road_"))
    finish(wb, ROOT / "roads" / "roads.xlsx")


def main():
    today = datetime.date.fromisoformat(sys.argv[1]) if len(sys.argv) > 1 else datetime.date.today()
    lookups = load_lookups()
    build_trees(lookups, today)
    build_roads(lookups, today)


if __name__ == "__main__":
    main()
