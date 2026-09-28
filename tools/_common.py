"""Shared helpers for the maintainer tools."""
from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILL_DIR = ROOT / "plugins" / "utility-network" / "skills" / "utility-network"
REF_DIR = SKILL_DIR / "references"
SKILL_MD = SKILL_DIR / "SKILL.md"

AREAS = {
    "pro-help": "Concepts & administration (ArcGIS Pro Help)",
    "rest-api": "REST API",
    "js-api": "Developer SDKs and apps",
    "pro-sdk": "Developer SDKs and apps",
    "arcpy": "Developer SDKs and apps",
    "experience-builder": "Developer SDKs and apps",
    "github-ecosystem": "Developer SDKs and apps",
    "mcp": "MCP / AI agents",
}

REVIEWED_RE = re.compile(r"Last\s+reviewed:\s*(\d{4}-\d{2}-\d{2})")
NAME_RE = re.compile(r"^\d{2}-[a-z0-9]+(-[a-z0-9]+)*\.md$")


@dataclass
class RefFile:
    path: Path

    @property
    def rel(self) -> str:
        return self.path.relative_to(REF_DIR).as_posix()

    @property
    def text(self) -> str:
        return self.path.read_text(encoding="utf-8")

    @property
    def header(self) -> str:
        return "\n".join(self.text.splitlines()[:10])

    @property
    def title(self) -> str:
        first = self.text.splitlines()[0] if self.text else ""
        return first.lstrip("# ").strip()

    @property
    def reviewed(self) -> date | None:
        m = REVIEWED_RE.search(self.header)
        return date.fromisoformat(m.group(1)) if m else None


def reference_files() -> list[RefFile]:
    return [RefFile(p) for p in sorted(REF_DIR.glob("*/*.md"))]
