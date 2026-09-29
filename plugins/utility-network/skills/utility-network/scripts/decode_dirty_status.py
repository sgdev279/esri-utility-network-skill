#!/usr/bin/env python3
"""Decode utility network dirty-area Status values.

Usage:
  python decode_dirty_status.py 1 9 40
  python decode_dirty_status.py --table          # print the bit table
  python decode_dirty_status.py --json 40        # machine-readable

Status is a bitmask; values add up when several conditions apply to one
dirty area. 0 means network topology is disabled.

Key rule (Esri, Dirty areas page): Validate Network Topology only evaluates
dirty areas that carry an EDIT bit (1, 2 or 4). An error-only dirty area
(8, 16, 32 or a sum of only those, e.g. 40) is ignored by validate: fix the
cause by editing the feature (or rule / subnetwork definition), then validate.
"""
import json
import sys

EDIT_BITS = (1, 2, 4)
ERROR_BITS = (8, 16, 32)
BITS = [
    (1, "feature inserted or updated", "edit"),
    (2, "feature deleted", "edit"),
    (4, "associated objects modified", "edit"),
    (8, "feature error", "error"),
    (16, "object error", "error"),
    (32, "subnetwork error", "error"),
]


def decode(status: int) -> dict:
    if not isinstance(status, int) or status < 0 or status > 63:
        raise ValueError(f"{status!r} is not a valid Status; expected an integer 0-63")
    if status == 0:
        return {"status": 0, "meanings": ["network topology is disabled"], "kind": "disabled",
                "validate_evaluates": False,
                "action": "Enable network topology; Status values are meaningless while it is off."}
    meanings = [m for bit, m, _ in BITS if status & bit]
    has_edit = any(status & b for b in EDIT_BITS)
    has_error = any(status & b for b in ERROR_BITS)
    if has_error and not has_edit:
        kind = "error only"
        action = ("Validate will IGNORE this row. Find the cause (Error Inspector: Network Source ID, "
                  "Feature GUID, error code), fix it by EDITING the feature, rule or subnetwork "
                  "definition, save, then validate.")
        if status & 32:
            action += (" Subnetwork error: after the fix, run Update Subnetwork; the subnetwork "
                       "stays Invalid until it updates cleanly.")
    elif has_error and has_edit:
        kind = "edit + error"
        action = ("Validate will evaluate it. If the feature still violates a rule the error bit "
                  "stays and the row becomes error-only; fix the cause by editing, then validate.")
    else:
        kind = "edit only"
        action = "No error. Just validate network topology over this area; validate clears it."
    return {"status": status, "meanings": meanings, "kind": kind,
            "validate_evaluates": has_edit, "action": action}


def main(argv):
    as_json = "--json" in argv
    argv = [a for a in argv if a != "--json"]
    if not argv or argv == ["--table"]:
        print("value  kind   meaning")
        for bit, m, kind in BITS:
            print(f"{bit:>5}  {kind:<5}  {m}")
        print("    0         network topology disabled")
        return 0
    rc = 0
    results = []
    for a in argv:
        try:
            results.append(decode(int(a)))
        except ValueError as e:
            print(f"error: {e}", file=sys.stderr)
            rc = 2
    if as_json:
        print(json.dumps(results, indent=2))
    else:
        for d in results:
            print(f"{d['status']}: " + "; ".join(d["meanings"]) + f"  [{d['kind']}]  ->  {d['action']}")
    return rc


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
