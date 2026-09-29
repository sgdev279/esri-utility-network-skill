# Roadmap

Content the skill doesn't cover well yet, roughly in priority order. Want to help with one? Open an ["Add UN knowledge" issue](https://github.com/sgdev279/esri-utility-network-skill/issues/new?template=add-knowledge.yml) or a PR, and mention the item.

## Content

| Priority | Topic | Why it matters | Target file |
|---|---|---|---|
| High | Review and date the 23 undated v1 reference files | Undated facts can't be trusted for current releases — see [FRESHNESS.md](FRESHNESS.md) | existing files |
| High | Complete error-code table (code → cause → fix) | Most support questions start from an error code | `pro-help/04-*` or a new `pro-help/` file |
| High | Field Maps and offline editing with the UN | Field crews are the biggest user group | new `pro-help/` or `apps/` file |
| High | Attribute rules alongside the UN | How most deployments enforce data quality | new `pro-help/` file |
| Medium | Tiers and asset groups for each Foundation (Electric, Gas, Sewer, Stormwater, Communications, District Energy) | Answers to "how is our network set up" need them | `pro-help/08-*` |
| Medium | Performance and scale: validation extents, dirty-area batching, trace config tuning | Large networks hit these first | new `pro-help/` file |
| Medium | Network diagram reduction/aggregation rules in detail | Currently marked "not pulled in detail" | `pro-help/07-*` |
| Medium | ArcGIS Maps SDKs for Native Apps (.NET MAUI, Kotlin, Swift, Qt) | Currently out of scope; mobile developers ask | new `native-sdk/` area |
| Low | Telecom circuits end-to-end workflow in Pro | Only REST is covered in depth | new `pro-help/` file |
| Medium | Migration follow-ups: asset package table schema in field-level detail, per-release availability of the Migration toolset, worked migration case studies | Core migration content is in `pro-help/11-*`; these are the remaining gaps | `pro-help/11-*` |

## MCP server

| Priority | Item |
|---|---|
| High | Port to MCP Python SDK 2.x (`MCPServer`) and drop the `mcp<2` pin |
| High | Integration test against a public or sample UN service |
| Medium | `export_subnetwork` tool that writes results to a file instead of the context window |
| Medium | Streamable HTTP transport + per-user auth for team deployments |
| Low | Network diagram tools via `NetworkDiagramServer` |

## Skill quality

| Priority | Item |
|---|---|
| High | Run the evals in `evals/evals.json` against each release and publish the pass rate |
| Medium | Optimise the trigger description with skill-creator's description optimiser |
