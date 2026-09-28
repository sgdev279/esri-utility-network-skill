# Utility Network — MCP (Model Context Protocol): Current State & Relevance (Deep Reference)
*Sources: esri.com/arcgis-blog (June 29, 2026 announcement), developers.arcgis.com/ai/mcp-arcgis-location-services/,
mcpbeta.webgistesting.net/mcpbetadoc/ (ArcGIS Enterprise MCP beta docs, tool catalog),
earlyadopter.esri.com "MCP in ArcGIS" program page. Last reviewed: 2026-09-28.*

**Where to go next**: this file covers Esri's own MCP offerings. For building
a UN-capable MCP server (the usual real need), read
`03-building-a-utility-network-mcp-server.md` and use
`scripts/un_mcp_server.py`. For the GP-task route inside Esri's overlay,
read `02-custom-gp-tool-worked-example-outage-isolation.md`.

**Status flag**: everything in this file describes **beta** functionality as
of late June 2026 — after this skill's other content was originally
compiled, and squarely in the "verify before relying on it" zone. Beta
features change fast; treat specifics here (endpoint shapes, tool names,
exact privileges) as a snapshot, not a stable contract, and suggest checking
Esri's current docs before shipping anything against it.

## There are two separate, unrelated MCP efforts — don't conflate them

This is the single most important thing to get right when someone asks
"can I use MCP with the utility network":

| | **MCP for ArcGIS Location Services** | **MCP in ArcGIS Enterprise** |
|---|---|---|
| Product | ArcGIS **Location Platform** (the consumer/developer location-services API platform — geocoding, routing, etc.) | ArcGIS **Enterprise** (self-hosted ArcGIS Server/Portal — where utility networks actually live) |
| Announced | June 29, 2026, ArcGIS Location Platform release blog | Separate beta, documented on a distinct Early Adopter Community testing site |
| Endpoint | `https://location-services-mcp.arcgis.com/beta/mcp` (Esri-hosted) | `https://<your-server>/<web-adaptor>/platform/mcp` (deployed **onto your own** ArcGIS Server via an installable "MCP overlay") |
| Capabilities | Geocoding, Routing, Elevation, Static Maps, Data Enrichment (GeoEnrichment) | Portal content search/describe, generic feature query, map image generation, geocoding/routing, **and exposing your own GP tasks as tools** |
| Utility Network relevance | **None.** These are consumer location services, unrelated to Enterprise UN infrastructure. | **Indirect, and not yet first-class** — see below. |

**If someone read the Esri blog post and asks about MCP + utility network,
the honest first answer is: that specific announcement (Location Platform
MCP) has nothing to do with utility networks.** The Enterprise MCP beta is
the one worth discussing further.

## MCP for ArcGIS Location Services (Location Platform) — confirmed NOT relevant

- Requires an **ArcGIS Location Platform account** (a rebranded ArcGIS
  Developer account), not an Enterprise/Portal credential.
- The API key privileges it needs are scoped to: `Geocoding > Geocode
  (stored)`, `Routing > Simple routing`, `Elevation > Elevation service`,
  `Static maps > Static maps service`, `Data Enrichment > GeoEnrichment
  service`, plus a beta-access flag. **No utility-network, feature-service,
  or Enterprise-content privilege appears anywhere in this list.**
- Supported MCP clients (per Esri's own get-started guide): Microsoft
  Copilot Studio, VS Code + GitHub Copilot, Goose, Claude, AWS Kiro, Postman
  — general-purpose MCP clients, not anything UN-specific.
- **Conclusion**: this MCP surface cannot trace, query subnetworks, validate
  topology, or do anything else covered elsewhere in this skill. Don't
  suggest it for UN work.

## MCP in ArcGIS Enterprise (beta) — the one that's actually adjacent

This is a **separate, ArcGIS-Server-hosted** beta: an installable "MCP
overlay" that stands up a `/platform` context on your own ArcGIS Server,
exposing an MCP catalog endpoint that AI clients (Claude Desktop, Microsoft
Copilot, ChatGPT, Cursor, GitHub Copilot, Postman, and others) can connect
to against **your organization's own portal content** — which is exactly
where a utility network's feature services actually live.

### Setup shape
1. **Apply the MCP overlay** to ArcGIS Server (install script or manual) —
   the `/platform` context and MCP endpoint don't exist until this is done.
2. **Authenticate** — API key, token, or OAuth 2.0 (manual) are the three
   supported techniques.
3. **Endpoint**: `https://<domain>/<web-adaptor-or-context-name>/platform/mcp`.
4. **"Prepare your data to be MCP-ready"** — this is the key mechanism for
   any relevance to UN data: **portal items must be explicitly tagged
   `mcp`**, with rich titles/descriptions, before MCP tools will discover
   and act on them. Nothing is exposed by default just because it exists in
   the portal.

### The default MCP tool catalog (confirmed, current beta, Sept 2026)
| Tool | Purpose |
|---|---|
| `search_portal_content` | Find portal items (structured filters or raw passthrough query) |
| `get_search_portal_content_passthrough_instructions` | Helper for building raw portal search strings |
| `describe_item` | Item details; service definition for service items |
| `describe_layer` | Fields, geometry type, capabilities, example values for a layer/table |
| `query_data` | Query a feature layer: where, spatial filter, paging, sorting, statistics |
| `get_map_image` | Export a map image from a map service |
| `find_address_candidates` / `reverse_geocode` | Geocoding via the portal's configured locator |
| `solve_route` | Routing via the configured network analysis service |
| `get_gp_task_definition` / `get_gp_task_job_status` | Inspect and poll geoprocessing tasks |

Esri's early-adopter program page describes the goal as MCP across ArcGIS
Enterprise, ArcGIS Online and Location Platform; as of Sept 2026 only the
Enterprise overlay beta and the Location Platform beta are documented.

**None of these are utility-network-specific.** There is no built-in
"Trace," "Validate Network Topology," "Query Associations," or any other
`UtilityNetworkServer`/`NetworkDiagramServer`-specific tool in this catalog
as of this beta. The tools operate at the generic **content, feature-layer,
mapping, geocoding/routing, and geoprocessing-job** level.

### Where the real UN opportunity is: exposing custom GP tasks

The beta explicitly supports **"Expose Custom GP Tasks as Custom MCP
Tools"**: publish your own geoprocessing task (synchronous or asynchronous)
as a service, tag it `mcp`, and it appears as a new tool in the MCP catalog
— discoverable and callable by an AI agent via natural language, using the
catalog's `Get GP Task Definition`/`Get GP Task Job Status` tools to
introspect and poll it.

**This is the concrete, currently-available path to "AI agent access to
utility network operations via MCP"**: since the arcpy Utility Network
toolset (`arcpy.un.*` — `Trace`, `ValidateNetworkTopology`,
`UpdateSubnetwork`, `SetTerminalConfiguration`, and everything else
documented in this skill's `pro-help/*.md` and `arcpy/01-*.md` files) **is
itself a geoprocessing toolset**, a script tool wrapping one of these
operations (e.g., a script tool that runs a UN trace and returns results)
could in principle be published as a GP service, tagged `mcp`, and become
callable through this beta — but **this requires deliberately building and
publishing that wrapper GP service yourself; it is not a shipped, ready-made
capability.**

### What's plausible today vs. what would need custom work
| Ask | Status |
|---|---|
| "List/describe our utility network feature layers via an AI agent" | **Plausible today** — tag the feature service/layer `mcp`, use `Describe Layer`/`Query Data`. Works at the ordinary-feature-layer level; won't surface UN-specific concepts (associations, subnetworks, tiers) beyond whatever's queryable as plain feature/attribute data. |
| "Get a map image showing network features" | **Plausible today** — `Get Map Image` is a generic tool; works the same way it would for any map service. |
| "Run a trace through natural language via MCP" | **Not built-in.** Would require publishing a custom GP service wrapping `arcpy.un.Trace` (or the `Trace` GP tool), tagging it `mcp`, and exposing it as a custom tool — a genuine build effort, not a flip-a-switch feature. |
| "Validate topology / manage subnetworks via MCP" | Same as above — only reachable by wrapping the relevant `arcpy.un`/`arcpy.nd` GP tools as custom published services. |
| "Direct MCP access to `UtilityNetworkServer`/`NetworkDiagramServer`/`VersionManagementServer` REST operations" | **Not through Esri's overlay** — it only exposes GP tasks, not arbitrary REST services. **Available today via a custom MCP server** that calls the REST API directly (Route C in `03-building-a-utility-network-mcp-server.md`; template `scripts/un_mcp_server.py`). |

## Practical guidance for Claude

1. **Always disambiguate which MCP** a person means first — the Location
   Platform one (irrelevant to UN) or the Enterprise one (the only one
   worth discussing further).
2. For the Enterprise MCP beta, be precise about the gap between "generic
   content/feature tools that happen to work on UN-hosted feature layers"
   and "first-class utility-network analytic operations" — the former
   works today with tagging; the latter would need a custom GP-service
   wrapper.
3. If someone wants UN operations through MCP, present the routes in
   `03-building-a-utility-network-mcp-server.md` (Esri overlay, overlay + GP
   tasks, custom REST MCP server, Pro Add-in bridge) and recommend one. For
   the GP-task route, the `arcpy.un`/`arcpy.nd` signatures in `pro-help/*.md`
   and `arcpy/01-utility-network-module.md` are what to wrap.
4. Flag prominently that both surfaces are **beta**, dated **June 2026**,
   and that tool catalogs/privilege names/endpoint shapes are exactly the
   kind of thing that changes between beta and general availability —
   recommend checking Esri's current docs (and, for the Enterprise MCP
   beta specifically, the Early Adopter Community) before building
   anything production-facing on this.
