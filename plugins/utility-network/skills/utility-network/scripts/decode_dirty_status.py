#!/usr/bin/env python3
"""Decode utility network dirty-area Status values.

Usage:
  python decode_dirty_status.py 10 17 40
  python decode_dirty_status.py --table          # print the bit table

Status is a bitmask; values add up when several conditions apply to one
dirty area. 0 means network topology is disabled.
"""
import sys

BITS = [
    (1, "feature modified (inserted/updated)", "edit"),
    (2, "feature deleted", "edit"),
    (4, "associated objects modified", "edit"),
    (8, "feature error discovered", "error"),
    (16, "object error discovered", "error"),
    (32, "subnetwork error discovered", "error"),
]


def decode(status: int) -> dict:
    if status < 0 or status > 63:
        raise ValueError(f"{status} is outside the documented 0-63 range")
    if status == 0:
        return {"status": 0, "meanings": ["network topology is disabled"],
                "action": "Enable network topology; Status values are meaningless while it is off."}
    meanings = [m for bit, m, _ in BITS if status & bit]
    has_error = any(status & bit for bit, _, kind in BITS if kind == "error")
    action = ("Fix the error (Error Inspector / ERRORCODE), then validate."
              if has_error else "No error — just validate network topology over this area.")
    return {"status": status, "meanings": meanings, "action": action}


def main(argv):
    if not argv or argv == ["--table"]:
        print("value  meaning")
        for bit, m, _ in BITS:
            print(f"{bit:>5}  {m}")
        print("    0  network topology disabled")
        return
    for a in argv:
        d = decode(int(a))
        print(f"{d['status']}: " + "; ".join(d["meanings"]) + f"  ->  {d['action']}")


if __name__ == "__main__":
    main(sys.argv[1:])
