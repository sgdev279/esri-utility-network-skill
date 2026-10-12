# Utility Network — REST API Reference: UtilityNetworkServer & Trace (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Source: developers.arcgis.com/rest/services-reference/enterprise/ (URLs in the Sources list at the bottom)*

## Two different network services — don't conflate them

- **`UtilityNetworkServer`** — the full utility network service (what this
  whole skill is about): `.../<serviceName>/UtilityNetworkServer`. Operations:
  `disableSubnetworkController`, `disableTopology`, `enableSubnetworkController`,
  `enableTopology`, `exportSubnetwork`, `queryNetworkMoments`,
  `synthesizeAssociationGeometries`, `trace`, `updateIsConnected`,
  `updateSubnetwork`, `validateNetworkTopology`. Child resources:
  **Associations, Locations, Trace Configurations** (and, in newer versions,
  **Circuits, Unit Identifiers** for telecom, both introduced at **12.1** —
  see `rest-api/07-circuits-and-unit-identifiers-telecom.md`). Introduced at
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
  lighter-weight tracing-only network type. Esri's service page does not spell out the data-model
  differences, so **if a user's service is a Trace Network rather than a
  Utility Network, don't assume subnetwork/domain network/structure network
  concepts apply** — confirm which service type they actually have before
  answering. The Trace Network `trace` operation is narrower than the
  Utility Network one: `traceType` is limited to `connected`, `upstream`,
  `downstream`, `shortestPath`; `traceLocationType` to `startingPoint` and
  `barrier`; `resultTypes.type` to `elements`, `aggregatedGeometry`,
  `connectivity` (`connectivity` at 10.9.1); `traceType` and `traceLocations`
  are required, and `shortestPathNetworkAttributeName` is required for
  `shortestPath`.

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
    // ... more flags — the exact set depends on the UN dataset version;
    // always read this response fresh rather than hardcoding a list.
  }
}
```
The `capabilities` property itself was introduced at 10.8.1. The
dataset-version-8 example in Esri's service page lists 44 flags; beyond those
above, it includes: `supportsTraceConfigurations`, `supportsTraceValidateLocatability`,
`supportsValidationTypes`, `supportsValidationSets`, `supportsValidationTypeRebuild`,
`supportsValidationTypeForceRebuild`, `supportsTraceConnectivityResults`,
`supportsAsyncExportSubnetwork`, `supportsAsyncUpdateIsConnected`,
`supportsAsyncTrace`, `supportsAsyncEnableTopology`, `supportsAsyncDisableTopology`,
`supportsAsyncLocationsQuery`, `supportsValidationDiscoveredSubnetworks`,
`supportsTraceFeatureElementResults`, `supportsTraceAssociationResults`,
`supportsPBFResponse`, `supportsOutSR`, `supportsFlowDirections`,
`supportsTraceSynthesizeGeometries`, `supportsRelatedRecordResults`,
`supportsUnitIdentifiers`, `supportsPathTrace`, `supportsCircuits`,
`supportsPropagatorResetters`, `supportsConnectivityInference`,
`supportsFlowDirectionResults`, `supportsPropagatedValueResults`,
`supportsFunctionName`, `supportsForceUpdate`. Version 7 and older datasets
report fewer flags (for example, no telecom or connectivity-inference flags).
Esri states introduction versions for few of these flags (only
`supportsTraceSystemNetworkAttributes`, 11.0) — **verify against the Esri docs
for your version** before quoting an intro version for any other flag.
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
| `sessionId` (optional) | GUID token used to lock the version. Esri's wording: the request fails without it if the version is held under an **exclusive lock** by an editing session — the calling client's own session, or another session, in which case the supplied `sessionId` must match the lock holder's. A trace on a version nobody has locked needs no `sessionId`, and a trace reads the version's saved state (it does not see unsaved edits). Omit it for ordinary read-only traces. |
| `moment` (optional) | Epoch time in milliseconds — run the trace as of a historical moment instead of the version's current moment. |
| `traceType` (**required**) | `connected \| subnetwork \| subnetworkController \| upstream \| downstream \| loops \| shortestPath \| isolation \| path \| circuit`. `shortestPath` is **deprecated at 12.1 — use `path`**. `path` and `circuit` are listed in the 12.1 reference (`maxHops` is only honored for `path`/`circuit`; `circuitName` only for `circuit`); the Trace page gives no per-value introduction note — **verify against the Esri docs for your version**. |
| `traceLocations` (**required**) | Array of starting points / stopping points / barriers (schema below). **Must be an empty array `[]`** for a `subnetwork` trace where `subnetworkName` is supplied via `traceConfiguration` instead of explicit locations. |
| `traceConfiguration` (optional) | The full trace configuration object (schema below). |
| `traceConfigurationGlobalId` (optional, introduced 10.9) | GUID of a **named** trace configuration. When given, it is used **instead of** `traceConfiguration`, and its stored trace type takes precedence over `traceType`. |
| `resultTypes` (optional) | Array controlling what is returned (schema below). The old single `resultType` parameter is deprecated (10.8). |
| `async` (optional) | `true \| false`, default `false`. `true` runs the trace as an async job and returns a `statusUrl` (see `06-*.md`). |
| `outSR` (optional, introduced 11.1) | Output spatial reference (wkid/latestWkid or wkt/wkt2) for trace result geometry. Defaults to the feature service's spatial reference if omitted. |

### `traceLocations` schema
```json
[
  {
    "traceLocationType": "startingPoint" | "stoppingPoint" | "barrier",
    "globalId": "<guid>",
    "terminalId": 0,          // required for junction features
    "percentAlong": 0.0,      // required for edge features
    "isFilterBarrier": true,  // optional
    "firstUnit": 1,           // optional, 12.1, telecom grouped objects
    "lastUnit": 1             // optional, 12.1, telecom grouped objects
  }
]
```
- A `terminalId` is **required for junction features** (which terminal is the
  actual start/barrier point on a multi-terminal device).
- A `percentAlong` is **required for edge features** (where along the line
  the point sits).
- A location missing its required property is **silently ignored** by the
  trace (Esri: "ignored if required properties are missing"), not rejected
  with an error — a good thing to check first when a trace "isn't starting
  where expected."
- The 12.1 note also mentions `inferConnectivity` and `circuitName` for
  `traceLocations`, but Esri's syntax block omits them — **verify against the
  Esri docs for your version** before using them.

### `resultTypes` schema
```json
[
  {
    "type": "elements" | "connectivity" | "features" | "associations" | "paths" | "circuits" | "relatedRecords",
    "includeGeometry": true,
    "includePropagatedValues": true,
    "includeDomainDescriptions": true,
    "includeFlowDirections": true,
    "networkAttributeNames": ["..."],
    "diagramTemplateName": "...",
    "resultTypeFields": [ { "networkSourceId": 9, "fieldname": "..." } ],
    "relationshipClasses": [ { "originLayerId": 1, "destinationLayerId": 2 } ]
  }
]
```
- Request `type` values and when they arrived (Esri): `connectivity` 10.9.1;
  `features` and `associations` 11.1; `relatedRecords` 11.5 (needs
  `relationshipClasses` with `originLayerId` and `destinationLayerId`; optional
  `outFields` / `relationshipOutFields` choose the fields returned);
  `paths` and `circuits` 12.1. `elements` is the original type.
- `includePropagatedValues`: only for the `features` type on subnetwork
  traces. `includeFlowDirections` (12.1): only `elements`, `features`,
  `connectivity`.
- **`aggregatedGeometry`**: Esri's current Trace page does **not** list it in
  the `resultTypes.type` syntax, yet its `synthesizeGeometries` description
  refers to it, the `supportsAggregatedGeometryAsTraceResult` capability flag
  exists, and the Trace Network Server trace and the named-trace-configuration
  `resultTypes` still list it. Treat it as a legacy/limited type and **verify
  against the Esri docs for your version** before relying on it.
- The *response* echoes `resultTypes` with a **different** `type` list:
  `features`, `connectivity`, `controllers`, `associations`, `paths`,
  `circuits`, `relatedRecords` (`controllers` appears only in responses).

### Trace response structure
Synchronous: `traceResults`, `sourceMapping`, `resultTypes`, `success`, and
`error` (`extendedCode`, `message`, `details`) only when `success` is false.
`traceResults` can contain `elements`, `connectivity`, `featureElements`,
`associations`, `relatedRecords`, `paths`, plus `diagramName`,
`globalFunctionResults`, `kFeaturesForKNNFound`, `startingPointsIgnored` and
`warnings`. Async: submit returns `{"statusUrl": ...}`; the status URL returns
`status` (`Pending`/`InProgress`), `submissionTime`, `lastUpdatedTime` — see
`06-asynchronous-operations-job-status.md`.

### `traceResults.elements` (verified against Esri's Trace page)
Each element carries **codes, not names**: `networkSourceId`, `globalId`, `objectId`,
`terminalId` (junctions/devices only), `assetGroupCode`, `assetTypeCode`,
`positionFrom` / `positionTo` (edges only), `flowDirection`
(`withDigitized` | `againstDigitized` | `indeterminate`, edges only) and, for telecom
networks, `firstUnit` / `lastUnit`. To show "Service Connection / Meter" to a person,
map `networkSourceId` and the two codes to names using the network's data element
(`FeatureServer/queryDataElements`) or the layer's subtypes; do not filter on
`assetGroupName` in a `jq` or code path for `elements`, because the field does
not exist there (names such as `assetGroupName` are returned only in the
`featureElements` results of the `features` result type).

This directly parallels the Pro Help "subnetwork-based trace output" section
(`Include propagated values` in the Pro UI = `includePropagatedValues` here).

### `traceConfiguration` schema (from the `create traceConfiguration` example — illustrative values, not defaults)
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
  // propagators, nearestNeighbor, traversabilityScope, filterScope,
  // shortestPathNetworkAttributeName, filterBitsetNetworkAttributeName,
  // inferConnectivity, circuitName, numPaths, maxHops: see
  // 08-trace-configuration-full-schema.md
}
```
Documented defaults for the boolean flags (Esri Trace page): `includeContainers`
false, `includeContent` false, `includeStructures` false, `includeBarriers`
**true**, `validateConsistency` **true**, `validateLocatability` false,
`synthesizeGeometries` false (added 11.3; applies only with the
`aggregatedGeometry` result type), `includeIsolated` false,
`ignoreBarriersAtStartingPoints` false, `includeUpToFirstSpatialContainer`
**false** (no-op unless `includeContainers` is true), `useDigitizedDirection`
false (added 11.3, UN dataset version 7+; when true, `domainNetworkName`,
`tierName` and `targetTierName` are ignored), `inferConnectivity` false (path
traces only). `allowIndeterminateFlow` is honored only for upstream,
downstream and isolation traces. `domainNetworkName` and `tierName` are
required for subnetwork traces.
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
- **Query response** (each item): `name`, `description`, `traceType`,
  `traceConfiguration` (the full body), `resultTypes`, `minNumStartingPoints`
  (`none` | `one` | `many`), `tags`, `creator`, `globalId` (the live example
  also shows an undocumented `creationDate`). Abbreviated example:
  ```json
  {
    "traceConfigurations": [
      { "name": "Connected_default", "globalId": "{...}", "creator": "unadmin" },
      { "name": "Upstream Protected RMT002", "globalId": "{...}", "creator": "larry" }
    ],
    "success": true
  }
  ```
- **`create`** — `POST .../traceConfigurations/create` (introduced 10.9):
  | Parameter | Required | Notes |
  |---|---|---|
  | `f` | no | `html` (default), `json`, `pjson` |
  | `name` | **yes** | |
  | `traceType` | **yes** | `connected`, `subnetwork`, `subnetworkController`, `upstream`, `downstream`, `loops`, `shortestPath` (deprecated 12.1, use `path`), `isolation`, `path`, `circuit` |
  | `traceConfiguration` | **yes** | same properties as the Trace operation |
  | `description` | no | |
  | `resultTypes` | no | default `elements`; per Esri `type` here is `elements`, `aggregatedGeometry` or `circuits` (`circuits` only for `circuit` traces in a telecom domain network); also `includeGeometry`, `includePropagatedValues`, `networkAttributeNames`, `diagramTemplateName`, `resultTypeFields` |
  | `tags` | no | array of strings |

  Response: `{"success": true}` or `success: false` plus `error`. Example:
  ```
  f=json
  name=Connected_IncludeContainers
  description=Connected trace example with containers
  traceType=connected
  traceConfiguration={ "includeContainers": true, "includeContent": false, ... }
  ```
- **`query`** — filters, all optional: `globalIds`, `creators`, `tags`,
  `names` (each an array). Esri does not say how multiple filters combine or
  what happens with none — **verify against the Esri docs for your version**.
- **`alter`** — `globalId` (**required**, GUID of the configuration) plus
  optional `name`, `description`, `traceType`, `traceConfiguration`,
  `resultTypes`, `tags`. Only an **administrator or the creator** of the named
  trace configuration can alter it. (The `alter` page lists the result type
  `circuit`, singular, where `create` lists `circuits` — **verify against the
  Esri docs for your version**.)
- **`delete`** — `globalIds` (**required**, array of GUID strings). Only an
  administrator or the creator can delete.
- The equivalent resource exists on `TraceNetworkServer` too
  (`traceconfigurations-trace-network-server` in Esri's docs; operations Alter,
  Create, Delete, Query) — shape not independently compared here, so verify
  against the Esri docs for your version before assuming it is identical.

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/utility-network-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/traceconfigurations-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/create-traceconfiguration-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/alter-traceconfiguration-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/delete-traceconfiguration-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-traceconfiguration-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-network-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-trace-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/unitIdentifiers-utility-network-server/
