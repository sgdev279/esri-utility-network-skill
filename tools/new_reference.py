#!/usr/bin/env python3
"""Scaffold a new reference file in the house format and register it in SKILL.md.

Usage:
  python tools/new_reference.py --area pro-help --title "Attribute rules with the utility network" \
      --read-when "Calculation/constraint rules on UN classes, rule order, performance" \
      --source https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/an-overview-of-attribute-rules.html

  --area       one of: pro-help, rest-api, js-api, pro-sdk, arcpy, experience-builder, github-ecosystem
  --title      human title (used for the H1 and the file name)
  --read-when  one line for SKILL.md's index: when Claude should open this file
  --source     Esri doc URL(s) the content is based on (repeatable)
  --dry-run    print what would happen without writing
"""
from __future__ import annotations

import argparse
import re
import sys
from datetime import date

from _common import AREAS, REF_DIR, SKILL_MD

TEMPLATE = """# Utility Network — {title} (Deep Reference)
*Sources: {sources}. Last reviewed: {today} (Pro x.y / Enterprise x.y docs).*

One or two sentences: what this file covers and which questions it answers.

## Key facts
- Fact, in your own words. Say which versions it applies to when that matters.

## Procedure / details
Steps, parameter tables, JSON or code — whatever an expert would need to answer exactly.

## Gotchas
- Known failure modes and how to recognise them.

## How to answer
- How Claude should use this file: which answer format, what to ask the user, what to flag.
"""


def slugify(title: str) -> str:
    s = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
    return "-".join(s.split("-")[:8])


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--area", required=True, choices=sorted(AREAS))
    ap.add_argument("--title", required=True)
    ap.add_argument("--read-when", required=True)
    ap.add_argument("--source", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    folder = REF_DIR / a.area
    folder.mkdir(exist_ok=True)
    nums = [int(p.name[:2]) for p in folder.glob("[0-9][0-9]-*.md")]
    name = f"{(max(nums) + 1) if nums else 1:02d}-{slugify(a.title)}.md"
    rel = f"{a.area}/{name}"
    sources = ", ".join(a.source) if a.source else "<Esri doc URL>"
    body = TEMPLATE.format(title=a.title, sources=sources, today=date.today().isoformat())

    skill = SKILL_MD.read_text(encoding="utf-8")
    row = f"| `{rel}` | {a.read_when} |"
    lines = skill.splitlines()
    idx = max((i for i, l in enumerate(lines) if l.startswith(f"| `{a.area}/")), default=None)
    if idx is None:
        # new area: add after the last row of the table for its section
        section = AREAS[a.area].split(" (")[0]
        head = next((i for i, l in enumerate(lines) if l.startswith("**") and section in l), None)
        if head is None:
            print(f"Couldn't find the index table for '{a.area}'. Add this row to SKILL.md by hand:\n{row}")
            idx = None
        else:
            idx = head + 1
            while idx + 1 < len(lines) and lines[idx + 1].startswith("|"):
                idx += 1
    if a.dry_run:
        print(f"would create references/{rel}\nwould add to SKILL.md: {row}")
        return 0
    (folder / name).write_text(body, encoding="utf-8")
    if idx is not None:
        lines.insert(idx + 1, row)
        SKILL_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"created references/{rel}")
    print(f"indexed in SKILL.md: {row}" if idx is not None else "")
    print("next: fill in the file, then run  python tools/lint_references.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
