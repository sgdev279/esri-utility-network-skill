# Utility Network — REST API: Network Diagram Service (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

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
- **Operations**: `Create Diagram From Features`, `Delete Diagram`,
  `Find Diagram Infos`, `Find Diagram Names`, `Query Consistency State`.
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
- Requires the ArcGIS **Utility Network** or **Trace Network** user type
  extension (note: a *different* license requirement than
  `createDiagramFromFeatures`, which needs Advanced Editing — check the
  specific license per operation rather than assuming one license covers the
  whole service).
- Parameters: `gdbVersion`, `sessionId`, `moment`, `diagramNames` (**required**
  array of diagram name strings), `f`.
- Response: `{ "diagramInfos": [ <diagramInfo1>, ..., <diagramInfoN> ] }` —
  an array of the same Diagram Info object shape shown above, one per
  requested name.

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
  `Set Diagram Element Info`.

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
- License requirements **differ per operation** on this service (Advanced
  Editing for create/delete, Utility/Trace Network extension for find) —
  always double check the specific operation's license note rather than
  assuming uniform licensing across the whole `NetworkDiagramServer`.
