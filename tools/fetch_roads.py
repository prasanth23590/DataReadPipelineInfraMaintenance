"""Refresh roads/segments.csv from Council open data.

Run:  python3 tools/fetch_roads.py

The defect and repair logs are created on first run and never overwritten.
"""

import math
from collections import defaultdict

from common import ensure_log, metres, query_all, write_csv

HIERARCHY = "Roads_hierarchy_overlay_Road_hierarchy"
FREIGHT = "Roads_hierarchy_overlay_Primary_freight_route"
STATE = "City_Plan_2014_Transport_noise_corridor_overlay_State_controlled_road_centreline"

# A segment is flagged when points spread along it all lie within this distance of a
# flag-layer line, so a side street that merely touches the flagged road is not flagged.
# The layers are digitised separately, so lines on the same road do not coincide exactly.
# Segments shorter than MIN_FLAG_M are mostly intersection stubs and are never flagged.
MATCH_M = 20
MIN_FLAG_M = 40
SAMPLES = (0.1, 0.3, 0.5, 0.7, 0.9)
CELL = 0.001  # grid cell in degrees, about 100 m


def along(paths, fraction):
    """Point at `fraction` of the way along a polyline, measured along its length."""
    pts = [p for path in paths for p in path]
    lengths = [metres(*a, *b) for a, b in zip(pts, pts[1:])]
    target, run = sum(lengths) * fraction, 0.0
    for (a, b), d in zip(zip(pts, pts[1:]), lengths):
        if run + d >= target and d > 0:
            t = (target - run) / d
            return a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        run += d
    return pts[0]


def point_segment_m(p, a, b):
    k = math.cos(math.radians(p[1]))
    ax, ay, bx, by, px, py = a[0] * k, a[1], b[0] * k, b[1], p[0] * k, p[1]
    dx, dy = bx - ax, by - ay
    t = 0.0 if dx == dy == 0 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy)) * 111_320


class LineIndex:
    """Grid index of line edges for 'is this point near any line' tests."""

    def __init__(self, features):
        self.cells = defaultdict(list)
        for f in features:
            for path in f["geometry"]["paths"]:
                for a, b in zip(path, path[1:]):
                    for cx in range(int(min(a[0], b[0]) // CELL), int(max(a[0], b[0]) // CELL) + 1):
                        for cy in range(int(min(a[1], b[1]) // CELL), int(max(a[1], b[1]) // CELL) + 1):
                            self.cells[cx, cy].append((a, b))

    def near(self, p, limit_m):
        cx, cy = int(p[0] // CELL), int(p[1] // CELL)
        return any(point_segment_m(p, a, b) <= limit_m
                   for dx in (-1, 0, 1) for dy in (-1, 0, 1) for a, b in self.cells.get((cx + dx, cy + dy), ()))


def main():
    geo = {"returnGeometry": "true", "outSR": 4326}
    freight = LineIndex(query_all(FREIGHT, outFields="OBJECTID", **geo))
    state = LineIndex(query_all(STATE, outFields="OBJECTID", **geo))

    rows = []
    # Future roads are planning lines, not built roads, so they are left out.
    for f in query_all(HIERARCHY, where="ROUTE_TYPE NOT LIKE 'Future%'",
                       outFields="OBJECTID,ROUTE_TYPE,DESCRIPTION,Shape__Length", **geo):
        a = f["attributes"]
        street, _, suburb = (a.get("DESCRIPTION") or "").rpartition(",")
        if not street:
            street, suburb = suburb, ""
        paths = f["geometry"]["paths"]
        mid = along(paths, 0.5)
        samples = [along(paths, x) for x in SAMPLES] if a["Shape__Length"] >= MIN_FLAG_M else []
        follows = lambda index: bool(samples) and all(index.near(p, MATCH_M) for p in samples)
        rows.append({
            "segment_id": f"RD-{a['OBJECTID']:06d}", "source_objectid": a["OBJECTID"],
            "street": street.strip(), "suburb": suburb.strip(), "road_class": a["ROUTE_TYPE"],
            "length_m": round(a["Shape__Length"], 1),
            "mid_latitude": round(mid[1], 7), "mid_longitude": round(mid[0], 7),
            "primary_freight_route": "Yes" if follows(freight) else "No",
            "state_controlled": "Yes" if follows(state) else "No",
        })
    rows.sort(key=lambda r: r["source_objectid"])
    write_csv("roads/segments.csv", rows)

    ensure_log("roads/defects.csv")
    ensure_log("roads/repairs.csv")
    print(f"roads: {len(rows)} segments, {sum(r['primary_freight_route'] == 'Yes' for r in rows)} freight, "
          f"{sum(r['state_controlled'] == 'Yes' for r in rows)} state-controlled")


if __name__ == "__main__":
    main()
