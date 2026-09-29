# Utility Network — REST API Reference: UtilityNetworkServer & Trace (Deep Reference)
*Last reviewed: 2026-09-28. Source: developers.arcgis.com/rest/services-reference/enterprise/*

## Two different network services — don't conflate them

- **`UtilityNetworkServer`** — the full utility network service (what this
  whole skill is about): `.../<serviceName>/UtilityNetworkServer`. Operations:
  `disableSubnetworkController`, `disableTopology`, `enableSubnetworkController`,
  `enableTopology`, `exportSubnetwork`, `queryNetworkMoments`,
  `synthesizeAssociationGeometries`, `trace`, `updateIsConnected`,
  `updateSubnetwork`, `validateNetworkTopology`. Child resources:
  **Associations, Locations, Trace Configurations** (and, in newer versions,
  **Circuits, Unit Identifiers** for telecom, introduced at 11.5+ — see
  `rest-api/07-circuits-and-unit-identifiers-telecom.md`). Introduced at
  10.6. Most operations require the **ArcGIS Advanced Editing / Utility
  Network** user type extension license — **confirmed precisely**: view,
  query, and trace operations do **not** require the user type extension;
  everything else (enable/disable topology or controllers, update/export/
  validate, editing operations) does.
- **`TraceNetworkServer`** — a **separate, simpler** service:
  `.../<serviceName>/TraceNetworkServer`, introduced at 10.9. Operations:
  `queryNetworkMoments`, `trace`, `validateNetworkTopology`. Child resource:
  **Trace Configurations** only (no Associations/Locations — because a Trace
  Network doesn't have the full utility network data model: no domain
  networks, no subnetworks, no structure network). Conceptually described by
  Esri as "similar to the Utility Network and Network Analysis services...
  for utility and transportation networks, respectively" — i.e., a
  lighter-weight tracing-only network type. **If a user's service is a Trace
  Network rather than a Utility Network, don't assume subnetwork/domain
  network/structure network concepts apply** — confirm which service type
  they actually have before answering.

### `UtilityNetworkServer` capabilities response (fuller confirmed example)
```json
{
  "name": "Utility Network Server",
  "type": "Map Server Extension",
  "capabilities": {
    "supportsAggregatedGeometryAsTraceResult": true,
    "supportsAssociations": true,
    "supportsDiagnostics": true,
    "supportsExportSubnetworkAssociations": true,
    "supportsExportSubnetworkIncludeDomainDescriptions": true,
    "supportsFilterBarriers": true,
    "supportsIncludeUpToFirstSpatialContainer": true,
    "supportsQueryAssociations": true,
    "supportsJunctionEdgeAssociations": true,
    "supportsMidspanAssociations": true,
    "supportsTraverseAssociations": true,
    "supportsLocations": true,
    "supportsTraceAllowIndeterminateFlow": true,
    "supportsTraceSystemNetworkAttributes": true
    // ... additional flags per rest-api/06-*.md (supportsAsync* family) —
    // the exact set is version-dependent; always read this response fresh
    // rather than hardcoding an assumed capability list.
  }
}
```
`capabilities` is **read-only** — it reports what the *specific utility
network version* backing this service supports; not configurable via REST.
One notable flag, `supportsTraceSystemNetworkAttributes` (introduced at
ArcGIS Enterprise 11.0), applies across **all** utility network versions —
worth checking before assuming a capability isn't available on an older UN
version.

## The `trace` operation (the single most-used REST endpoint)

`POST/GET https://<root>/<serviceName>/UtilityNetworkServer/trace`

### Request parameters
| Parameter | Details |
|---|---|
| `f` | `html \| json \| pjson \| pbf` (pbf introduced at Enterprise 11.2). Default `html`. |
| `gdbVersion` (optional) | Geodatabase version name. Default `sde.DEFAULT`. |
| `sessionId` (optional) | GUID token that identifies **your own** service session. Esri's wording: if the calling client has started a service session (editing) and holds an **exclusive lock** on the version, the request fails unless `sessionId` is provided. It is **not** needed just because another user has the version open; a trace without it reads the version's saved state and does not see anyone's unsaved edits. Omit it for ordinary read-only traces. |
| `moment` (optional) | Epoch time in milliseconds — run the trace as of a historical moment instead of the version's current moment. |
| `outSR` (optional, introduced 11.1) | Output spatial reference (wkid or wkt/wkt2) for trace result geometry. Defaults to the feature service's spatial reference if omitted. |
| `traceType` (**required**) | `connected \| subnetwork \| subnetworkController \| upstream \| downstream \| loops \| shortestPath \| isolation` |
| `traceLocations` | Array of starting points/barriers (schema below). **Must be an empty array `[]`** when running a `subnetwork` trace where `subnetworkName` is supplied via `traceConfiguration` instead of explicit locations. |
| `traceConfiguration` | The full trace configuration object (schema below). |
| `resultTypes` | Array controlling what's returned (schema below). |

### `traceLocations` schema
```json
[
  {
    "traceLocationType": "startingPoint" | "barrier",
    "globalId": "<guid>",
    "terminalId": 0,          // required for junction features
    "percentAlong": 0.0,      // required for edge features
    "isFilterBarrier": true   // optional, introduced 10.8.1
  }
]
```
- A `terminalId` is **required for junction features** (which terminal is the
  actual start/barrier point on a multi-terminal device).
- A `percentAlong` is **required for edge features** (where along the line
  the point sits).
- A location missing its required property is **silently ignored** by the
  trace, not rejected with an error — a good thing to check first when a
  trace "isn't starting where expected."

### `resultTypes` schema
```json
[
  {
    "type": "elements" | "aggregatedGeometry" | "connectivity" | "features" | "associations",
    "includeGeometry": true,
    "includePropagatedValues": true,
    "includeDomainDescriptions": true
  }
]
```
### Trace response: `traceResults.elements` (verified against Esri's Trace page)
Each element carries **codes, not names**: `networkSourceId`, `globalId`, `objectId`,
`terminalId` (junctions/devices only), `assetGroupCode`, `assetTypeCode`,
`positionFrom` / `positionTo` (edges only), `flowDirection`
(`withDigitized` | `againstDigitized` | `indeterminate`, edges only) and, for telecom
networks, `firstUnit` / `lastUnit`. To show "Service Connection / Meter" to a person,
map `networkSourceId` and the two codes to names using the network's data element
(`FeatureServer/queryDataElements`) or the layer's subtypes; do not filter on
`assetGroupName` in a `jq` or code path, because the field does not exist.

This directly parallels the Pro Help "subnetwork-based trace output" section
(`Include propagated values` in the Pro UI = `includePropagatedValues` here).

### `traceConfiguration` schema (from the `create traceConfiguration` example — full observed field set)
```json
{
  "includeContainers": true,
  "includeContent": false,
  "includeStructures": false,
  "includeBarriers": true,
  "validateConsistency": true,
  "validateLocatability": false,
  "synthesizeGeometries": false,
  "includeIsolated": false,
  "ignoreBarriersAtStartingPoints": false,
  "includeUpToFirstSpatialContainer": true,
  "allowIndeterminateFlow": true,
  "useDigitizedDirection": false,
  "domainNetworkName": "",
  "tierName": "",
  "targetTierName": "",
  "subnetworkName": "",
  "diagramTemplateName": ""
  // conditionBarriers, functionBarriers, filterBarriers,
  // filterFunctionBarriers, functions, outputFilters, outputConditions,
  // propagators, nearestNeighbor, traversabilityScope, filterScope and
  // shortestPathNetworkAttributeName: full schemas in
  // 08-trace-configuration-full-schema.md
}
```
This maps directly, field-for-field in spirit, to the Pro UI's Trace pane
options and the C# SDK's `TraceConfiguration` object — the three surfaces
(Pro UI, REST JSON, C# SDK) are three serializations of the same underlying
concept set. When translating a Pro UI trace setup into a REST call for
someone, this shared vocabulary is the bridge: e.g., "Include Barrier
Features" (Pro UI) = `includeBarriers` (REST) = `Traversability`-adjacent
config (C# SDK).

## Named trace configurations — `traceConfigurations` resource

`https://<root>/<serviceName>/UtilityNetworkServer/traceConfigurations`
- Operations: **Alter, Create, Delete, Query**. Introduced at 10.9. Requires
  the **ArcGIS Advanced Editing** user type extension license.
- Purpose (per Esri): named trace configurations **store the properties of a
  complex trace** so it can be **shared** through the service to any
  consuming web map or field app — avoiding re-specifying a complex
  `traceConfiguration` JSON blob on every client.
- **List response:**
  ```json
  {
    "traceConfigurations": [
      { "name": "Connected_default", "globalId": "{...}", "creator": "unadmin" },
      { "name": "Upstream Protected RMT002", "globalId": "{...}", "creator": "larry" }
    ],
    "success": true
  }
  ```
- **`create` operation** — `POST .../traceConfigurations/create` — required
  `name`, optional `description`, `traceType`, and the full
  `traceConfiguration` JSON object (same schema as above). Example:
  ```
  f=json
  name=Connected_IncludeContainers
  description=Connected trace example with containers
  traceType=connected
  traceConfiguration={ "includeContainers": true, "includeContent": false, ... }
  ```
- **`query` operation** — filter by `globalIds` (array), `creators` (array),
  or `tags` (array) — useful for "find all trace configs a specific admin
  built" or "find configs tagged for a specific workflow" without listing
  everything.
- **`alter` and `delete` operations** — exist on this resource (confirmed
  from the operations list) for modifying or removing a named trace
  configuration, but their exact parameter schemas weren't independently
  verified at the same depth as `create`/`query` here. Expect the same
  general conventions as `create` (a `globalId` or `name` to identify the
  target, plus `gdbVersion`/`sessionId`) — **verify against the live docs
  for the target Enterprise version before generating exact request code**
  for `alter`/`delete` specifically.
- The equivalent resource exists on `TraceNetworkServer` too
  (`traceConfigurations-trace-network-server`) with the same shape — a good
  sign that trace-configuration management is uniform across both service
  types even though their other resources diverge.
