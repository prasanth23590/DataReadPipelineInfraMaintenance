"""Refresh trees/assets.csv and trees/protected_areas.csv from Council open data.

Run:  python3 tools/fetch_trees.py

The assessment and works logs are created on first run and never overwritten.
"""

import json

from common import ensure_log, query_all, write_csv

SHERWOOD = "botanic_collection_sherwood_arboretum"
NALL_LAYERS = [
    ("NALL-CV", "Council Vegetation", "Protected_Vegetation_Natural_Assets_Local_Law_2003_Council_Vegetation"),
    ("NALL-SUV", "Significant Urban Vegetation",
     "Protected_Vegetation_Natural_Assets_Local_Law_2003_Significant_Urban_Vegetation"),
    ("NALL-SNV", "Significant Native Vegetation",
     "Protected_Vegetation_Natural_Assets_Local_Law_2003_Significant_Native_Vegetation"),
    ("NALL-WWV", "Waterway and Wetland Vegetation",
     "Protected_Vegetation_Natural_Assets_Local_Law_2003_Waterway_and_Wetland_Vegetation"),
]
SLT = ("CP-SLT", "City Plan 2014 Significant landscape tree overlay", "Significant_landscape_tree_overlay")


def point_in_rings(x, y, rings):
    """Even-odd rule over all rings, which handles Esri holes."""
    inside = False
    for ring in rings:
        for (x1, y1), (x2, y2) in zip(ring, ring[1:]):
            if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
                inside = not inside
    return inside


def overlay_hits(trees, service):
    """Return {tree ObjectId: [polygon OBJECTID, ...]} for polygons of `service` containing each tree."""
    xs = [t["longitude"] for t in trees]
    ys = [t["latitude"] for t in trees]
    env = {"xmin": min(xs), "ymin": min(ys), "xmax": max(xs), "ymax": max(ys), "spatialReference": {"wkid": 4326}}
    polys = query_all(service, outFields="OBJECTID", geometry=json.dumps(env), geometryType="esriGeometryEnvelope",
                      inSR=4326, spatialRel="esriSpatialRelIntersects", outSR=4326, returnGeometry="true")
    hits = {}
    for t in trees:
        for p in polys:
            if point_in_rings(t["longitude"], t["latitude"], p["geometry"]["rings"]):
                hits.setdefault(t["ObjectId"], []).append(p["attributes"]["OBJECTID"])
    return hits


def main():
    trees = sorted((f["attributes"] for f in query_all(SHERWOOD, returnGeometry="false")),
                   key=lambda t: (t["Tree_ID"], t["ObjectId"]))
    hits = {code: overlay_hits(trees, svc) for code, _, svc in NALL_LAYERS + [SLT]}

    assets, used = [], set()
    for t in trees:
        tid, oid = t["Tree_ID"], t["ObjectId"]
        # Council reuses a few Tree_IDs for different trees; later ones get -B, -C, ...
        tree_id, suffix = f"SHW-{tid:04d}", "B"
        while tree_id in used:
            tree_id, suffix = f"SHW-{tid:04d}-{suffix}", chr(ord(suffix) + 1)
        used.add(tree_id)
        assets.append({
            "tree_id": tree_id, "source": "Sherwood Arboretum", "source_tree_id": tid,
            "latitude": t["latitude"], "longitude": t["longitude"], "scientific_name": t["Scientific_Name"],
            "common_name": t["Common_name"], "family": t["Family"], "height_m": t.get("Height"),
            "crown_width_m": t.get("Crown_Width"), "dbh_mm": t.get("DBH"),
            "year_established": t.get("Year_Established"),
            "protected_area_ids": ";".join(f"{code}-{area}" for code, _, _ in NALL_LAYERS
                                           for area in hits[code].get(oid, [])),
            "in_significant_landscape_tree_overlay": "Yes" if hits[SLT[0]].get(oid) else "No",
        })
    write_csv("trees/assets.csv", assets)

    areas = []
    for code, name, svc in NALL_LAYERS:
        for f in query_all(svc, returnGeometry="false", returnCentroid="true", outSR=4326):
            a = f["attributes"]
            areas.append({"area_id": f"{code}-{a['OBJECTID']}", "layer": name, "category": a.get("CATEGORY") or name,
                          "description": "", "centroid_latitude": round(f["centroid"]["y"], 7),
                          "centroid_longitude": round(f["centroid"]["x"], 7), "area_m2": round(a["Shape__Area"], 1)})
    for f in query_all(SLT[2], returnGeometry="false", returnCentroid="true", outSR=4326):
        a = f["attributes"]
        areas.append({"area_id": f"{SLT[0]}-{a['OBJECTID']}", "layer": SLT[1], "category": a["OVL2_DESC"],
                      "description": a.get("DESCRIPTION") or "", "centroid_latitude": round(f["centroid"]["y"], 7),
                      "centroid_longitude": round(f["centroid"]["x"], 7), "area_m2": round(a["Shape__Area"], 1)})
    write_csv("trees/protected_areas.csv", areas)

    ensure_log("trees/assessments.csv")
    ensure_log("trees/works.csv")
    print(f"trees: {len(assets)} trees, {len(areas)} protected areas")


if __name__ == "__main__":
    main()
