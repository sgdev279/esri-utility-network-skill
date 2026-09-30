#!/usr/bin/env python3
"""Lint the skill's reference files. Used by CI; run it before opening a PR.

Errors (fail CI):
  - file name not NN-kebab-case.md, or folder not a known area
  - first line isn't an H1 starting "# Utility Network"
  - no source line ("Source", "Sources" or "Builds on") in the first 10 lines
  - file not listed in SKILL.md's reference index
  - SKILL.md or a reference links to a references/ file that doesn't exist
  - "Last reviewed" date in the future
Warnings (reported, don't fail):
  - no "Last reviewed: YYYY-MM-DD" in the header
  - file longer than 400 lines without a "## Contents" section

Usage: python tools/lint_references.py [--strict]   (--strict turns warnings into errors)
"""
from __future__ import annotations

import re
import sys
from datetime import date

from _common import AREAS, NAME_RE, REF_DIR, SKILL_MD, reference_files

LINK_RE = re.compile(r"(pro-help|rest-api|js-api|pro-sdk|arcpy|experience-builder|github-ecosystem)/\d{2}-[a-z0-9-]+\.md")


def main() -> int:
    strict = "--strict" in sys.argv
    errors, warnings = [], []
    skill = SKILL_MD.read_text(encoding="utf-8")

    for rf in reference_files():
        area, name = rf.rel.split("/")
        if area not in AREAS:
            errors.append(f"{rf.rel}: unknown area folder '{area}' (add it to tools/_common.py AREAS)")
        if not NAME_RE.match(name):
            errors.append(f"{rf.rel}: name must look like 01-short-kebab-title.md")
        if not rf.text.startswith("# Utility Network"):
            errors.append(f"{rf.rel}: first line must be an H1 starting '# Utility Network'")
        if not re.search(r"Sources?:|Builds on", rf.header):
            errors.append(f"{rf.rel}: add a source line (e.g. '*Sources: <Esri doc URL>. Last reviewed: YYYY-MM-DD.*') in the first lines")
        if f"`{rf.rel}`" not in skill:
            errors.append(f"{rf.rel}: not listed in SKILL.md's reference index")
        if rf.reviewed is None:
            warnings.append(f"{rf.rel}: no 'Last reviewed: YYYY-MM-DD' in the header")
        elif rf.reviewed > date.today():
            errors.append(f"{rf.rel}: 'Last reviewed' date is in the future")
        lines = rf.text.count("\n")
        if lines > 400 and "## Contents" not in rf.text:
            warnings.append(f"{rf.rel}: {lines} lines — add a '## Contents' section near the top")

    sources = [("SKILL.md", skill)] + [(rf.rel, rf.text) for rf in reference_files()]
    for where, text in sources:
        for m in sorted(set(x.group(0) for x in LINK_RE.finditer(text))):
            if not (REF_DIR / m).exists():
                errors.append(f"{where}: links to missing file references/{m}")

    for w in warnings:
        print(f"warning: {w}")
    for e in errors:
        print(f"error:   {e}")
    n = len(reference_files())
    print(f"\n{n} reference files, {len(errors)} errors, {len(warnings)} warnings")
    return 1 if errors or (strict and warnings) else 0


if __name__ == "__main__":
    sys.exit(main())
