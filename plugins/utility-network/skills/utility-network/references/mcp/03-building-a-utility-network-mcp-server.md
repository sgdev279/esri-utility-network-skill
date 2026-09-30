# Utility Network — Building a Custom MCP Server (Deep Reference)
*Last reviewed: 2026-09-28. Sources: MCP Python SDK (FastMCP), ArcGIS REST API
UtilityNetworkServer reference (trace, associations/query, validateNetworkTopology,
updateSubnetwork, exportSubnetwork), MCP in ArcGIS Enterprise beta tool catalog,
community MCP projects listed at the end.*

Read this when someone wants an AI agent (Claude, Copilot, Cursor, a custom
agent) to **actually work with their utility network** — trace, find dirty
areas, check subnetworks, answer "what's downstream of this breaker" — rather
than only search portal content.

## The four routes, and when each is right

| Route | What it is | UN depth | Effort | Pick it when |
|---|---|---|---|---|
| **A. Esri's MCP in ArcGIS Enterprise (beta)** | Esri's MCP overlay on ArcGIS Server; generic tools + tagged GP tasks | Generic layers only, unless you add GP tasks | Low | They want Esri-supported, portal-governed access and can live with beta. See `01-*.md`. |
| **B. Route A + custom GP task tools** | Publish script tools that wrap `arcpy.un.*`, tag `mcp` | Anything arcpy can do | Medium | They want UN operations but must stay inside Esri's MCP overlay. Worked example in `02-*.md`. |
| **C. Custom MCP server over UN REST** | Your own MCP server calling `UtilityNetworkServer` + `FeatureServer` | Full REST surface | Medium | They want first-class UN tools today, from any MCP client, on any Enterprise version with UN services. This skill does not ship an implementation; use this file as the design. |
| **D. MCP ↔ Pro Add-in bridge** | MCP server talks to a running ArcGIS Pro via an Add-in (e.g. named pipes) | Full C# SDK, desktop session | High | The agent must act inside a user's Pro session (their map, selection, local file/mobile gdb, single-user deployment). |

Default recommendation: **C for UN analysis and troubleshooting**, B when
governance says "only through Esri's overlay", D only for desktop-session
automation. Single-user (file/mobile geodatabase) networks have no REST
surface, so only D (or plain arcpy scripts) can reach them.

## Route C in detail — tool design

Design principle: **few, well-described tools that each answer a question a
utility engineer actually asks**, not one tool per REST operation. The model
chooses tools from their descriptions, so descriptions must say when to use
the tool and what the arguments look like.

### Recommended tool set

| Tool | Tier | REST call | Why it exists |
|---|---|---|---|
| `describe_network` | read | `FeatureServer/queryDataElements` (+ UN layer JSON for `systemLayers`) | Every other call needs domain network, tier, source IDs and names. Call first; cache. |
| `list_trace_configurations` | read | `UtilityNetworkServer/traceConfigurations/query` | Named configs encode the admin's intent; running one beats hand-building JSON. |
| `trace` | read | `UtilityNetworkServer/trace` | The core question-answerer. Returns a **summary**, not raw elements. |
| `query_associations` | read | `UtilityNetworkServer/associations/query` | "What's in this vault / on this pole / connected to this device". |
| `query_subnetworks` | read | `FeatureServer/<subnetworksTable>/query` | "Which subnetworks are dirty", "who feeds RMT001". |
| `dirty_area_summary` | read | `FeatureServer/<dirtyAreas>/query` with `outStatistics` | Health check: pending edits vs. real errors, decoded from the Status bitmask, with whether Validate will evaluate each row (error-only rows are ignored by validate). |
| `find_features` | read | `FeatureServer/<layer>/query` on each feature layer | People say "CB-1042", the trace needs a globalId. Returns globalId plus asset group/type names. Make the asset-ID field configurable (default `ASSETID`). |
| `network_moments` | read | `UtilityNetworkServer/queryNetworkMoments` | Is topology valid; when it was last enabled. |
| `job_status` | read | the `statusUrl` from an async job | Polls long-running operations. |
| `validate_network_topology` | **write** | `UtilityNetworkServer/validateNetworkTopology` | Opt-in only. |
| `update_subnetwork` | **write** | `UtilityNetworkServer/updateSubnetwork` | Opt-in only. |

Deliberately **not** exposed by default: `enableTopology`/`disableTopology`
(locks DEFAULT for everyone, deletes existing errors), `exportSubnetwork` with
acknowledgement (changes controller state that downstream systems depend on),
association `applyEdits` with validation bypass, and anything that alters
schema. These are maintenance-window operations for a human.

### Exact REST shapes the tools rely on (verified Sept 2026)

- `trace`: `traceType` ∈ `connected | subnetwork | subnetworkController |
  upstream | downstream | loops | shortestPath | isolation`;
  `traceLocations` items need `terminalId` (junctions/devices) **or**
  `percentAlong` (edges). A location missing both is **silently ignored** —
  so validate before sending. Named configs via `traceConfigurationGlobalId`.
  Full `traceConfiguration` schema: `rest-api/08-trace-configuration-full-schema.md`.
- `associations/query`: `elements` = `[{networkSourceId, globalId, terminalId?}]`
  (required); `types` ∈ `attachment, containment, junctionJunctionConnectivity,
  junctionEdgeFromConnectivity, junctionMidspanConnectivity,
  junctionEdgeToConnectivity`; optional `moment`, `returnDeletes`.
- `validateNetworkTopology`: `validateArea` (envelope + spatialReference),
  `validationType` ∈ `normal | rebuild | forceRebuild`, optional
  `validationSet` `[{sourceId, globalIds:[...]}]`, `returnEdits`, `async`,
  `outSR`; `sessionID` (note capital *ID* in the docs) for named versions.
- `updateSubnetwork`: `domainNetworkName`, `tierName` (required);
  `subnetworkName` **or** `allSubnetworksInTier=true`; `continueOnFailure`;
  optional `traceConfiguration`; `async`.
- Async: submit with `async=true`, poll `statusUrl` (see
  `rest-api/06-asynchronous-operations-job-status.md`).

### Result shaping — the most important design decision

A subnetwork trace on a real distribution network returns tens of thousands
of elements. Dumping that into the model's context wastes tokens and buries
the answer. Return:

1. `totalElements`
2. counts grouped by network source → asset group → asset type (with names
   resolved from `describe_network`)
3. a capped sample of globalIds per group (default 25) with a `truncated` flag
4. any `globalFunctionResults` (e.g. summed customer count, load)
5. warnings such as `startingPointsIgnored`, with a plain-language hint

If the user needs the full list (to select features in a map, to export),
the server should write it to a file or return a `resultUrl`, not inline JSON.

### Auth patterns

| Situation | Pattern | Notes |
|---|---|---|
| Personal/desktop agent (Claude Desktop, Claude Code) | User's own token (`generateToken` or OAuth user login) | Edits carry the user's identity; editor tracking stays truthful. |
| Shared service agent | OAuth2 `client_credentials` app credential | Scope it to the UN feature service only; never use the UN owner account. |
| Enterprise with SAML/IWA | Pre-issued token via env var, refreshed by an outer process | `generateToken` won't work with SAML-only logins. |

Licensing reminder: query and trace don't need the Advanced Editing user type
extension; validate, update subnetwork and any edit do. A read-only MCP
server can therefore run under a cheaper user type.

### Safety rails (bake these in, don't rely on the prompt)

1. **Read-only by default.** Write tools register only when the operator sets
   `UN_ALLOW_WRITES=true`.
2. **Two-step confirmation.** Write tools refuse unless `confirm=true`, and the
   refusal message tells the agent to ask the user first. This makes the
   human approval explicit in the transcript.
3. **Version discipline.** Default reads to `sde.DEFAULT`; for writes prefer a
   named branch version (pass `sessionID` if your client started the edit session) unless the task is inherently
   DEFAULT-only (update subnetwork on DEFAULT, export with acknowledgement).
4. **Extent limits.** Refuse validate requests over a configured area or
   without an extent — full-extent validation on a large network can run for
   hours.
5. **Pin the host.** `job_status` accepts only URLs on the configured server,
   so a prompt-injected URL can't turn the tool into an open fetcher.
6. **Log every write** with the requesting user, version, parameters and
   response.

### Configuring a server built to this design

Suggested environment convention (names are a suggestion, not a shipped product):
`UN_FEATURE_SERVICE_URL` (the FeatureServer URL), `UN_PORTAL_URL`, then one auth
route: `UN_TOKEN`, `UN_CLIENT_ID` + `UN_CLIENT_SECRET` (OAuth client credentials),
or `UN_USERNAME` + `UN_PASSWORD` (generateToken; fails for SAML-only portals).
Also `UN_ALLOW_WRITES` (default off), `UN_DEFAULT_VERSION` and `UN_ASSET_ID_FIELD`.

The MCP Python SDK 1.x exposes `FastMCP`; SDK 2.x renamed it (`MCPServer`), so
pin the SDK major version you tested against.

Claude Desktop / Claude Code config entry (adjust `command` and `args` to how
the server is installed):

```json
{
  "mcpServers": {
    "utility-network": {
      "command": "<COMMAND_THAT_STARTS_YOUR_SERVER>",
      "args": [],
      "env": {
        "UN_FEATURE_SERVICE_URL": "https://gis.example.com/server/rest/services/Electric/FeatureServer",
        "UN_PORTAL_URL": "https://gis.example.com/portal",
        "UN_CLIENT_ID": "…", "UN_CLIENT_SECRET": "…"
      }
    }
  }
}
```

For a team deployment, switch FastMCP to the streamable HTTP transport behind
the organisation's reverse proxy and require per-user auth at the proxy.

### Things that will bite

- **`systemLayers` key names** differ slightly across releases; match by
  substring (`dirty`, `subnetwork`, `association`) rather than hard-coding.
- **Network source IDs** are per-service, not global. Always resolve them
  from `queryDataElements`; never hard-code IDs from another environment.
- **Sessions**: `sessionId` matters only when *your own* client holds an
  exclusive edit session on the version (Esri: the request fails if you do and
  omit it). Someone else editing the version does not block reads; a trace
  sees the saved state. If a call fails with a lock or session error, surface
  it plainly rather than retrying.
- **Named trace config names aren't unique keys** — use the `globalId`.
- **Branch versions and topology**: validate on a named version writes to that
  version's dirty areas; the DEFAULT subnetwork state won't change until the
  version is reconciled and posted.
- **Timeouts**: sync REST calls on big extents hit the server's request
  timeout; always use `async=true` for validate/update/export.

## Route D in brief — Pro Add-in bridge

Pattern (as in the community `MCP-Server-ArcGIS-Pro-AddIn` project): a Pro
Add-in starts a named-pipe server on load; a separate .NET MCP server (stdio)
forwards tool calls to it; the Add-in executes them on `QueuedTask.Run` using
the C# SDK (`pro-sdk/01-*.md`). Use it when the agent needs the user's active
map, selection, or a single-user network. Keep the same read/write tiers and
confirmation rule as Route C.

## How Claude should answer MCP + UN questions

1. Name which route fits and why in one or two sentences (use the table above).
2. State what works today vs. what needs building — no overpromising about
   Esri's beta.
3. For Route C, give the tool set, the REST call behind each tool, the
   environment variables and the client config block from this file. Say
   plainly that this skill describes the design and does not ship a server.
4. Always mention the write-safety rails and the licensing split
   (read tools vs. write tools).
5. Date-stamp beta facts ("as of Sept 2026").

## Community projects worth knowing (not Esri-supported)

- `Asem-D/arcgis-portal-mcp` (July 2026) — generic Portal/AGOL MCP server
  (search, query, edit, publish, run GP). Useful for content tasks; has no
  UN-specific tools.
- `nicogis/MCP-Server-ArcGIS-Pro-AddIn` — reference implementation of the
  Pro Add-in named-pipe bridge (Route D).
- FME has a "create an MCP server" workflow that can front Esri services —
  an option for organisations already standardised on FME.
