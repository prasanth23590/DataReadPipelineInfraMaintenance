# Data dictionary

Conventions for every table: UTF-8 CSV with a header row; dates `YYYY-MM-DD`; coordinates are WGS84 decimal degrees;
flags are `Yes`/`No`; a blank cell means unknown or not applicable. **Lookup** means the value must be one of the
`value`s for that list in [`lookups/lookups.csv`](lookups/lookups.csv). **Source** columns come from Council and are
rewritten by the fetch scripts; **you** columns are entered by you.

## Trees

### `trees/assets.csv` (source)

| Column | Type | Meaning |
| --- | --- | --- |
| `tree_id` | text, key | `SHW-` + Council Tree_ID, zero-padded; `-B` added where Council reuses an ID |
| `source` | text | Where the tree record comes from (`Sherwood Arboretum`) |
| `source_tree_id` | integer | Council's Tree_ID |
| `latitude`, `longitude` | decimal | Tree location |
| `scientific_name`, `common_name`, `family` | text | Species |
| `height_m` | number | Height in metres |
| `crown_width_m` | number | Crown width in metres |
| `dbh_mm` | number | Trunk diameter at breast height in millimetres |
| `year_established` | integer | Year planted, where known |
| `protected_area_ids` | text | `;`-separated `area_id`s from `protected_areas.csv` containing the tree |
| `in_significant_landscape_tree_overlay` | Yes/No | Inside a City Plan 2014 significant landscape tree site |

### `trees/protected_areas.csv` (source)

| Column | Type | Meaning |
| --- | --- | --- |
| `area_id` | text, key | Layer code + Council OBJECTID: `NALL-CV` Council Vegetation, `NALL-SUV` Significant Urban, `NALL-SNV` Significant Native, `NALL-WWV` Waterway and Wetland, `CP-SLT` significant landscape tree site |
| `layer`, `category`, `description` | text | Council layer name, category and description |
| `centroid_latitude`, `centroid_longitude` | decimal | Centre point of the area |
| `area_m2` | number | Area in square metres |

### `trees/assessments.csv` (you): one row per health inspection

| Column | Type | Meaning |
| --- | --- | --- |
| `assessment_id` | text, key, required | Your ID, e.g. `HA-0001` |
| `tree_id` | text, required | Tree assessed; must exist in `assets.csv` |
| `assessment_date` | date, required | Date of inspection |
| `assessor` | text | Who inspected |
| `condition` | lookup `tree_condition`, required | Dead, Poor, Fair, Good, Unknown (placeholder scale) |
| `issue_type` | lookup `tree_issue_type` | Main issue observed (Council's request reasons plus a few extras) |
| `risk_rating` | lookup `tree_risk_rating`, required | Extreme, High, Medium, Low (placeholder scale) |
| `recommended_outcome` | lookup `tree_outcome`, required | One of Council's four outcomes |
| `council_request_ref` | text | Council service-request reference, if any |
| `notes` | text | Free text |

### `trees/works.csv` (you): one row per maintenance job

| Column | Type | Meaning |
| --- | --- | --- |
| `work_id` | text, key, required | Your ID, e.g. `WK-0001` |
| `tree_id` | text, required | Tree worked on; must exist in `assets.csv` |
| `assessment_id` | text | Assessment the job responds to; must be for the same tree. A `Completed` job resolves that assessment in the priority list |
| `work_date` | date, required | Date done or planned |
| `work_type` | lookup `tree_work_type`, required | Type of work |
| `clearance_context` | lookup `tree_clearance_context` | Where the tree is; sets the required branch clearance (2.4 m, 4.5 m or 5 m) |
| `status` | lookup `work_status`, required | Requested, Scheduled, In progress, Completed, Cancelled |
| `crew`, `council_request_ref`, `notes` | text | Free text |

## Roads

### `roads/segments.csv` (source)

| Column | Type | Meaning |
| --- | --- | --- |
| `segment_id` | text, key | `RD-` + Council OBJECTID, zero-padded to 6 digits |
| `source_objectid` | integer | Council OBJECTID in the road hierarchy layer |
| `street`, `suburb` | text | From Council's segment description; blank for a few hundred unnamed segments |
| `road_class` | lookup `road_class` | Motorway, Arterial, District, Suburban, Neighbourhood / local (and tunnels) |
| `length_m` | number | Segment length in metres |
| `mid_latitude`, `mid_longitude` | decimal | Point halfway along the segment |
| `primary_freight_route` | Yes/No | Follows a City Plan primary freight route (approximate) |
| `state_controlled` | Yes/No | Follows a state-controlled road, maintained by the Queensland Government (approximate) |

### `roads/defects.csv` (you): one row per reported defect

| Column | Type | Meaning |
| --- | --- | --- |
| `defect_id` | text, key, required | Your ID, e.g. `DF-0001` |
| `segment_id` | text, required | Road segment; must exist in `segments.csv` |
| `reported_date` | date, required | Date reported |
| `latitude`, `longitude` | decimal, required | Exact defect location; must be inside Brisbane |
| `defect_type` | lookup `road_defect_type`, required | Pothole, Rut, Crack, Edge failure, Other |
| `traffic_swerving` | Yes/No, required | Council triage question; Yes makes the defect urgent |
| `public_safety_concern` | Yes/No, required | Council triage question; Yes makes the defect urgent |
| `status` | lookup `road_defect_status`, required | Open, Investigating, Repair scheduled, Repaired, Closed |
| `council_request_ref`, `notes` | text | Free text |

### `roads/repairs.csv` (you): one row per repair job

| Column | Type | Meaning |
| --- | --- | --- |
| `repair_id` | text, key, required | Your ID, e.g. `RP-0001` |
| `defect_id` | text, required | Defect repaired; must exist in `defects.csv` |
| `repair_date` | date, required | Date done or planned |
| `repair_type` | lookup `road_repair_type`, required | Make safe, Pothole fill, Patch, Crack seal, Edge repair, Resurface, Inspection only |
| `status` | lookup `work_status`, required | Requested, Scheduled, In progress, Completed, Cancelled |
| `crew`, `notes` | text | Free text |

Repairs do not change a defect's status automatically: set the defect to `Repaired` or `Closed` when it is done.

## Lookups: `lookups/lookups.csv`

| Column | Meaning |
| --- | --- |
| `list` | Lookup list name used above |
| `value` | Allowed value |
| `rank` | Priority order (1 = most urgent) for `tree_condition`, `tree_risk_rating` and `road_class`; minimum clearance in metres for `tree_clearance_context`; investigation target for `road_response_target` (calendar days if urgent, working days otherwise) |
| `source` | Where the value comes from, or that it is an assumption |

## Priority views (generated, in the workbooks and `tools/priority.py`)

| Column | Meaning |
| --- | --- |
| `priority` | 1 = most urgent |
| `urgency` (roads) | Urgent or Non-urgent, from the two triage questions |
| `investigate_by` (roads) | Reported date + 1 day if urgent, else + 7 working days (public holidays not excluded) |
| `overdue` (roads) | Yes when status is still Open after `investigate_by` |
| `days_open` / `days_since_assessed` | Days from the report or assessment to the priority date |
| `open_works` (trees) | Works for that assessment not yet Completed or Cancelled |
