# Changelog

## 2.0.0 — 2026-09-28
Repository
- Professional README with banner, badges, examples and architecture diagram; social preview image.
- Contribution pipeline: CONTRIBUTING guide, issue forms (add knowledge, correction, bug), PR template, knowledge inbox.
- Maintainer tools: `tools/new_reference.py` (scaffold + index), `tools/lint_references.py` (CI), `tools/freshness_report.py` (docs/FRESHNESS.md).
- Monthly Freshness workflow that refreshes the report and opens a review issue.
- ROADMAP, SECURITY and CODE_OF_CONDUCT.
- MCP server pinned to MCP Python SDK 1.x (`mcp<2`); SDK 2.x renamed FastMCP.

Skill
- Rewrote SKILL.md: broader trigger description, request workflow, six answer formats, MCP as a first-class section.
- New references: asset packages & Foundations, dataset versions & compatibility, publishing/ownership/licensing, full REST trace configuration schema, building a UN MCP server.
- Fixed: licensing contradiction, incomplete arcpy `UtilityNetwork` class, association-type encodings, REST updateSubnetwork/exportSubnetwork/validateNetworkTopology/associations parameters, stale cross-references.
- Added scripts: dirty-area Status decoder, association-type converter, trace request checker, MCP server template.
- Added evals (6 task prompts, 20 trigger queries).

MCP server
- 0.1.0: first release of `utility-network-mcp`.

## 1.0.0
- Original skill.
