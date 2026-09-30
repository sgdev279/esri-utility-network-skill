# Changelog

## Unreleased
Repository
- The MCP server (`mcp-server/`, `scripts/un_mcp_server.py`, its mock-service tests, and the PyPI and MCP Registry release steps) has been removed from this repository. It moves to its own repository. This repo is now the skill only.
- The skill keeps its MCP guidance: `references/mcp/*` and the MCP section of SKILL.md describe Esri's MCP offerings, the four routes, and the design of a UN MCP server (tool set, REST shapes, auth, write safety). It no longer points to a bundled implementation.
- Released `utility-network-mcp` 0.2.0 on PyPI and its MCP Registry entry are not affected by this change; they are no longer maintained from here.
- CI, issue templates, labels, SECURITY, CONTRIBUTING, README and roadmap updated to match.

## 2.1.0 — 2026-09-29
Skill
- New reference `pro-help/11-migration-and-schema-mapping.md`: choosing between Foundation, Migration Wizard, Migrate To Utility Network tool and manual setup; schema mapping vs object mapping; the mapping-workbook loading workflow; Migrate To Utility Network parameters and limits; Analyze Network Data / Apply Error Resolutions loop; relationship classes to associations (`C_Associations`, Sync the C Tables); pre-load QC rules; post-migration order.
- Corrected `pro-help/08`: source-to-target mapping lives in a mapping workbook, not the asset package tables; migration section now points to file 11.
- `github-ecosystem/01`: added Create Simple Data Mapping, Load Data Using Workspace and Sync the C Tables to the UDMS table.
- SKILL.md description and index now route migration and schema-mapping questions.
- Evals: 3 migration evals (ids 7-9), four specific scenario evals (ids 10-13) and 4 trigger queries.
- Corrected `sessionId` semantics for trace (only when the caller holds the exclusive edit session), documented the trace element fields, and added the rule that Validate ignores error-only dirty areas (Status 8, 16, 32, 40).
- Full Subnetworks table field list in `pro-help/02` (`ISDIRTY` codes flagged as unverified).
- `decode_dirty_status.py` reports whether validate will evaluate each Status and the next action, and fails cleanly on bad input.
- `build_trace_request.py` now separates PROBLEMS from WARNINGS, and checks condition names, GUID format, sessionId shape and category shape.

MCP server 0.2.0
- New `find_features` tool: asset ID (for example CB-1042) to globalId plus asset group and type names. Field set by `UN_ASSET_ID_FIELD`.
- `trace` summaries add asset group and type names when the service exposes them.
- `dirty_area_summary` classifies each Status (edit only, error only, edit + error) and reports how many error-only rows validate will ignore.

Repository
- `tests/`: 25 tests including an end-to-end MCP test against a mock service; runs in CI. `examples/isolation-trace/` and `docs/EXAMPLES.md` and `docs/TESTING.md` replace the generic README examples with specific, verified ones.

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
