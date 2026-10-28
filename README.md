# Brisbane infrastructure maintenance datasets

Two linked datasets for maintaining Brisbane City Council infrastructure, built from Council open data:

| Dataset | Assets (with location) | Health log | Maintenance log | Spreadsheet |
| --- | --- | --- | --- | --- |
| [Trees](trees/) | 1,181 Sherwood Arboretum trees (`assets.csv`) | `assessments.csv` | `works.csv` | [`trees.xlsx`](trees/trees.xlsx) |
| [Roads](roads/) | 41,674 road segments (`segments.csv`) | `defects.csv` (potholes and road damage) | `repairs.csv` | [`roads.xlsx`](roads/roads.xlsx) |

Every log row points at an asset by ID (`tree_id`, `segment_id`), so each asset's health and maintenance history
can be pulled together, and each dataset has a **Priority** view ranking what needs attention first.
Column definitions are in [`DATA_DICTIONARY.md`](DATA_DICTIONARY.md).

## What the data can and cannot tell you

* **Locations.** Roads cover the whole city. Trees do not: the only Council dataset with individual tree
  locations is the [Sherwood Arboretum botanic collection](https://www.spatial-data.brisbane.qld.gov.au/search?q=sherwood),
  so every tree has `source` "Sherwood Arboretum". Council publishes no citywide street or park tree inventory.
  Add trees you survey yourself to `trees/assets.csv` with your own ID prefix and `source`.
* **Health and maintenance.** Council publishes its *process* (request reasons, assessment outcomes, clearance rules,
  response targets) but **no per-asset health, defect or works records**. The four log files therefore start with one
  example row each (marked `EXAMPLE`), to be replaced by your own inspections, reports and works, or by Council
  service-request data if you obtain it (for example through a Right to Information request).
* **State-controlled roads** are maintained by the Queensland Government, not Council. `segments.state_controlled`
  and `segments.primary_freight_route` are matched by geometry and are approximate (see [Sources](#sources)).

## Using it

### For planning and prioritising work

Open `trees/trees.xlsx` or `roads/roads.xlsx`. The **Priority** sheet lists open items, most urgent first:

* **Roads:** open defects (status not `Repaired` or `Closed`), ordered by
  1. urgency: *Urgent* when traffic is swerving or there is a public safety concern;
  2. overdue: status still `Open` after Council's investigation target, 24 hours for urgent reports and
     7 working days for others ([Council potholes page](https://www.brisbane.qld.gov.au/online-services/report-an-issue/potholes));
  3. road class: motorway, arterial, district, suburban, then neighbourhood/local;
  4. primary freight route first;
  5. oldest report first.
* **Trees:** trees whose latest assessment recommends action (any outcome except *No action*) with no `Completed`
  work recorded against that assessment, ordered by risk rating, then condition, then oldest assessment.

The workbooks are **generated, read-only views**. Make changes in the CSV files (Excel opens them directly),
then rebuild. The class order, response targets, condition and risk scales are in
[`lookups/lookups.csv`](lookups/lookups.csv); the `rank` column sets the priority order. The condition and risk
scales are placeholders, since Council publishes neither: replace them with your own standard.

### For an app or tool

* Load the CSV files: one table per file, UTF-8, header row, ISO dates (`YYYY-MM-DD`), decimal-degree WGS84
  coordinates, `Yes`/`No` flags. IDs are stable strings (`SHW-0661`, `RD-000001`).
* Use `tools/priority.py` (`road_priority`, `tree_priority`) rather than re-implementing the rules, so the app and
  the spreadsheets always agree.
* Run `tools/validate.py` on any data before loading it.
* The CSV files suit an app that **reads** this data. Once many people **write** to it (for example residents reporting
  potholes), move the four log tables into a database; the column layouts are designed to load into one unchanged.

## Updating

From the repository root:

```bash
python3 tools/fetch_trees.py      # refresh trees/assets.csv and trees/protected_areas.csv from Council
python3 tools/fetch_roads.py      # refresh roads/segments.csv from Council
python3 tools/validate.py         # check every table; exits 1 on problems
python3 tools/build_xlsx.py       # rebuild both workbooks (optional YYYY-MM-DD sets "today")
python3 -m unittest tools/test_tools.py
```

* The fetch scripts only rewrite the Council-sourced files. The log files are created once and never overwritten.
* Run `validate.py` before committing. It checks unique IDs, that every log row points at a real asset (and works at a
  real assessment of the same tree), allowed values, date formats, and that defect locations fall inside Brisbane.
* IDs come from Council's own IDs (`Tree_ID`, road `OBJECTID`). If Council renumbers a layer, `validate.py` reports
  log rows that no longer match an asset.

## Layout

```
  README.md, DATA_DICTIONARY.md
  lookups/lookups.csv          allowed values and priority ranks for every controlled column
  trees/  assets.csv  protected_areas.csv  assessments.csv  works.csv  trees.xlsx
  roads/  segments.csv  defects.csv  repairs.csv  roads.xlsx
  tools/  common.py  fetch_trees.py  fetch_roads.py  priority.py  validate.py  build_xlsx.py  test_tools.py
```

## Sources

All Council data is from Brisbane City Council's open data (ArcGIS Feature Services behind the
[Open Spatial Data site](https://www.spatial-data.brisbane.qld.gov.au/)):

| Used for | Dataset |
| --- | --- |
| Trees: `assets.csv` | Botanic collection — Sherwood Arboretum (point per tree; species, height, crown width, trunk diameter). Council reuses Tree_IDs 704 and 1243 for two trees each; the second of each pair is `SHW-0704-B` / `SHW-1243-B`. |
| Trees: `protected_areas.csv`, `assets.protected_area_ids`, `assets.in_significant_landscape_tree_overlay` | Protected Vegetation (Natural Assets Local Law 2003): Council Vegetation, Significant Urban Vegetation, Significant Native Vegetation, Waterway and Wetland Vegetation; City Plan 2014 Significant landscape tree overlay. Trees are tagged by point-in-polygon test. |
| Roads: `segments.csv` | City Plan 2014 — Road hierarchy overlay — Road hierarchy. The 79 future (unbuilt) road lines are excluded. `street` and `suburb` are split from Council's description; 370 segments have no suburb and 343 of those no street name either. |
| Roads: `primary_freight_route`, `state_controlled` | City Plan 2014 — Road hierarchy overlay — Primary freight route; Transport noise corridor overlay — State controlled road centreline. A segment is flagged when five points spread along it all lie within 20 m of a flagged line; segments under 40 m (mostly intersection stubs) are never flagged. Expect some errors at junctions and service roads. |
| Lookups | [Brisbane trees](https://www.brisbane.qld.gov.au/environment-and-water/plants--trees-and-gardening/brisbane-trees) (outcomes, clearances, maintenance), [Request tree removal assessment](https://www.brisbane.qld.gov.au/online-services/report-an-issue/report-it-tree-removal) (removal reasons), [Report potholes and road damage](https://www.brisbane.qld.gov.au/online-services/report-an-issue/potholes) (defect types, triage questions, response targets) |

Council data is © Brisbane City Council; check the licence shown on each dataset's page before redistributing it.
