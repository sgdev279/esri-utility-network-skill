#!/usr/bin/env python3
"""Convert association types between the encodings used across ArcGIS APIs.

Encodings:
  code   integer in the associations table ASSOCIATIONTYPE field, REST
         FeatureServer applyEdits, and arcpy.un.UtilityNetwork methods
  csv    text used by Import/Export Associations CSV files
  rest   camelCase names used by UtilityNetworkServer associations/query
  gp     keyword for arcpy.un.ImportAssociations association_type

Usage:
  python association_types.py 5
  python association_types.py "Junction Edge Midspan Connectivity"
  python association_types.py junctionMidspanConnectivity
  python association_types.py --table
"""
import sys

TYPES = [
    {"code": 1, "csv": "Junction Junction Connectivity", "rest": "junctionJunctionConnectivity",
     "gp": "JUNCTION_JUNCTION_CONNECTIVITY"},
    {"code": 2, "csv": "Containment", "rest": "containment", "gp": "CONTAINMENT"},
    {"code": 3, "csv": "Structural Attachment", "rest": "attachment", "gp": "STRUCTURAL_ATTACHMENT"},
    {"code": 4, "csv": "Junction Edge From Connectivity", "rest": "junctionEdgeFromConnectivity",
     "gp": "JUNCTION_EDGE_FROM_CONNECTIVITY"},
    {"code": 5, "csv": "Junction Edge Midspan Connectivity", "rest": "junctionMidspanConnectivity",
     "gp": "JUNCTION_EDGE_MIDSPAN_CONNECTIVITY"},
    {"code": 6, "csv": "Junction Edge To Connectivity", "rest": "junctionEdgeToConnectivity",
     "gp": "JUNCTION_EDGE_TO_CONNECTIVITY"},
]
NOTE = ("gp keywords follow Esri's naming pattern (JUNCTION_JUNCTION_CONNECTIVITY is documented); "
        "confirm the others in the Import Associations tool reference for your Pro version.")


def lookup(value: str) -> dict:
    v = value.strip()
    for t in TYPES:
        if v.isdigit() and int(v) == t["code"]:
            return t
        if v.lower() in (t["csv"].lower(), t["rest"].lower(), t["gp"].lower()):
            return t
    raise KeyError(f"Unknown association type: {value!r}")


def main(argv):
    if not argv or argv == ["--table"]:
        print(f"{'code':<5}{'csv (Import/Export CSV)':<37}{'rest (associations/query)':<32}gp keyword")
        for t in TYPES:
            print(f"{t['code']:<5}{t['csv']:<37}{t['rest']:<32}{t['gp']}")
        print("\nNote:", NOTE)
        return
    for a in argv:
        t = lookup(a)
        print(f"{a!r} -> code={t['code']}  csv={t['csv']!r}  rest={t['rest']!r}  gp={t['gp']}")


if __name__ == "__main__":
    main(sys.argv[1:])
