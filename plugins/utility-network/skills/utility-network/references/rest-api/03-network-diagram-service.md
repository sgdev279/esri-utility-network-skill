# Utility Network — REST API: Network Diagram Service (Deep Reference)
*Sources: https://developers.arcgis.com/rest/services-reference/enterprise/network-diagram-service/ and the per-operation pages linked from it. Last reviewed: 2026-10-27 (Enterprise 12.1). Deeper treatment: `learn/16-network-diagrams-in-depth.md`.*

## Don't confuse this with the legacy "Schematics" service

Esri has **two, unrelated** diagram-generation REST services in its history:
- **Schematics Server** (`.../MapServer/exts/SchematicsServer/...`,
  `generateDiagram` on a **Schematic Diagram Template** resource) — the
  **legacy** pre-utility-network schematic diagramming system, tied to
  geometric networks / arbitrary object classes, introduced at 10.1.
- **`NetworkDiagramServer`** (`.../<serviceName>/NetworkDiagramServer`) — the
  **current** utility-network/trace-network-integrated diagram service,
  introduced at 10.6, and the one this skill's REST source actually links to.
If a search or an older tutorial surfaces `generateDiagram` /
`SchematicsServer` syntax, flag it as the legacy system rather than mixing its
parameter names into `NetworkDiagramServer` usage — they are **not**
interchangeable APIs despite superficial similarity.

## `NetworkDiagramServer` — service-level operations

`https://<root>/<serviceName>/NetworkDiagramServer`
- **Operations**: `Create Diagram From Circuit Name` (12.1), `Create Diagram From Features`,
  `Create Diagram From Trace Locations` (11.5), `Delete Diagram`,
  `Find Diagram Infos`, `Find Diagram Names`, `Query Consistency State`.
- Service-level note (Esri): the active portal account must hold the **ArcGIS Advanced Editing** user type extension to use diagrams with utility/trace network services; per-operation notes below. All are POST.
- **Child resources**: `Diagram Dataset`, `Diagrams`, `Diagram Templates`.

### `createDiagramFromFeatures`
`.../NetworkDiagramServer/createDiagramFromFeatures`
- Requires the **ArcGIS Advanced Editing** user type extension.
- Creates a **new temporary diagram** (see Pro Help: diagrams are temporary
  by default unless stored) from a set of utility network feature GlobalIDs.
- Key parameters: `gdbVersion`, `sessionId`, `template` (the diagram template
  name — **must already exist**, configured only via Pro/DB connection per
  the Pro Help network-diagrams reference), `initialFeatures` (JSON array of
  feature GlobalID strings).
- Example request:
  ```
  GET .../createDiagramFromFeatures?gdbVersion=ABV1&sessionId=&template=Basic
      &initialFeatures=["{F199534-8B77-4D26-8C3C-8A55DB66728E}"]&f=pjson
  ```
- Response — a **Diagram Info** object:
  ```json
  {
    "diagramInfo": {
      "tag": "",
      "isStored": false,
      "canStore": true,
      "canExtend": true,
      "isSystem": false,
      "creator": "acb7352",
      "creationDate": 1505218557000,
      "lastUpdateBy": "acb7352",
      "lastUpdateDate": 1505218557000,
      "containerMargin": 0.5,
      "junctionCount": 2,
      "edgeCount": 1,
      "containerCount": 0,
      "aggregationCount": 0,
      "isHistorical": false,
      "access": "esriDiagramPublicAccess",
      "diagramExtent": { "xmin": 0, "ymin": 0, "xmax": 0, "ymax": 0 }
    }
  }
  ```
  Note `isStored: false` / `canStore: true` — confirms the temporary-by-default
  behavior at the REST layer, matching the Pro Help vocabulary entry.

### `findDiagramInfos`
`.../NetworkDiagramServer/findDiagramInfos`
- Licence (verified 2026-10-27): Esri states Advanced Editing only "for versions prior to ArcGIS Enterprise 11.5"; no extension is named from 11.5. The earlier claim here that it needs a Utility/Trace Network extension was wrong. `findDiagramNames` and `queryConsistencyState` carry the same pre-11.5 note.
- Parameters: `gdbVersion`, `sessionId`, `moment`, `diagramNames` (**required**
  array of diagram name strings), `f`.
- Response: `{ "diagramInfos": [ <diagramInfo1>, ..., <diagramInfoN> ] }` —
  an array of the same Diagram Info object shape shown above, one per
  requested name.

### `createDiagramFromTraceLocations` (11.5)
`.../NetworkDiagramServer/createDiagramFromTraceLocations`
- Requires Advanced Editing. Creates a temporary diagram from trace locations.
- Parameters: `gdbVersion`, `sessionId` (optional), `template` (required), `traceLocations` (required array; each item has `traceLocationType` = `startingPoint` | `barrier` | `stoppingPoint`, `globalId` (required), optional `terminalId`, `percentAlong`, `isFilterBarrier`, `firstUnit`, `numUnits`), `f`.
- Response: Diagram Info object (as above).

### `createDiagramFromCircuitName` (12.1)
`.../NetworkDiagramServer/createDiagramFromCircuitName`
- Requires Advanced Editing. Creates a temporary diagram for a telecom circuit.
- Parameters: `gdbVersion`, `sessionId` (optional), `template` (required; must have a Trace rule of type Circuit on a telecom domain), `circuitName` (required), `f`. Response: Diagram Info object.

### `findDiagramNames` and `queryConsistencyState`
- `findDiagramNames` (10.6): optional `extent`, `where` (fields NAME, USERTAG, CREATIONDATE, CREATOR, LASTUPDATE, UPDATEDBY), `features` (`globalIDs`), `excludeSystemDiagrams` (default false); returns `{"diagramNames": [...]}`.
- `queryConsistencyState` (10.6): `diagramNames` required; returns per name `esriDiagramIsConsistent`, `esriDiagramNotConsistentWithTopology` or `esriDiagramHasDirtyFeatures`.

### `deleteDiagram`
`.../NetworkDiagramServer/deleteDiagram`
- Requires Advanced Editing.
- Parameters: `gdbVersion`, `sessionId`, `name` (**required**), `f`.
- Response: `{ "moment": 1490875600791 }` — just the timestamp the deletion
  occurred.

## `Diagrams/<diagramName>` resource — per-diagram operations

Once a diagram exists (`.../NetworkDiagramServer/diagrams/<diagramName>`),
a much larger operation set becomes available (`POST`), including:
- **Content/query operations**: `queryDiagramContent` (basic connectivity +
  optional geometry/attributes/aggregation/diagram-property detail),
  `queryDiagramElementsByExtent`, `queryDiagramElementsByObjectIDs`,
  `queryFeatureAttributes` (attribute values for network features/objects
  represented in the diagram, aggregated or not), `getDiagramElementInfo`.
- **Editing/layout operations**: `Append Features`, `Apply Layout`,
  `Apply Template Layouts`, `Clear Flags`, `Extend`, `Find Diagram Features`,
  `Find Initial Network Objects`, `Find Network Features`, `Save Layout`,
  `Set Diagram Element Info`. Esri's resource page also lists Find Network Features from OIDs (11.5), Get Aggregations, Get Flags, Manage Flag, Overwrite From Features, Query Attributes By Source, Clear Diagram Element Info, Store and Update.
- Child resources of a diagram: Dynamic Layers, Layer Definitions, Web Layer Definitions, Diagram Map. Resource licence note: Advanced Editing.

### `findNetworkFeaturesFromOIDs` (11.5)
`.../diagrams/<diagramName>/findNetworkFeaturesFromOIDs`
- Advanced Editing. Maps diagram feature ObjectIDs to network element GlobalIDs; Esri recommends it over `findNetworkFeatures` from 11.5. Required: `junctionObjectIDs`, `edgeObjectIDs`, `containerObjectIDs`, `includeAggregations`. Optional: `gdbVersion`, `sessionId`, `moment`, `findContainerIfNonSpatial`, `f` (`html`, `json`, `pbf` from 12.0).
- Response: `features` array of `globalID`, `featureOID`, `networkSourceID`, `geometryType` (0 edge, 1 point, 4 polygon; 2 and 3 undocumented).
- Not in the service page's operation list, but linked from its description.

### `getDiagramElementInfo` (worked example — filter-by-selection pattern)
```
diagramElementFilter={
  "type": "filterBySelection",
  "junctionObjectIDs": [7018, 7019],
  "edgeObjectIDs": [],
  "containerObjectIDs": []
}
```
Response:
```json
{
  "diagramElementIDs": [ "..." ],
  "diagramElementInfo": [ "..." ]
}
```
Two **parallel arrays** (IDs and their corresponding info values) rather than
an array of `{id, info}` objects — a REST response shape worth calling out
explicitly since it's easy to assume a more "natural" paired-object shape
when writing client code against this endpoint.

## Practical guidance
- Diagram **templates** are configured only via Pro/DB connection (Pro Help
  reference); REST/JS only **consume** existing templates by name
  (`template=<name>` in `createDiagramFromFeatures`).
- A diagram is **temporary** unless explicitly stored — if a user's workflow
  needs the diagram to persist across sessions/users, they need the
  **Store Diagram** action (Pro-side) or check `canStore`/`isStored` at the
  REST layer before assuming persistence.
- Licence: Advanced Editing is the service-wide note. From 11.5 the find and consistency operations no longer state it; create and delete still do. Check each operation page.
