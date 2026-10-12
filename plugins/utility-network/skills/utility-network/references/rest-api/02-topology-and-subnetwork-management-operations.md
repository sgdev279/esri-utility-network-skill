# Utility Network — REST API: Topology & Subnetwork Management Operations (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Source: developers.arcgis.com/rest/services-reference/enterprise/ (URLs in the Sources list at the bottom). All UtilityNetworkServer operations below were introduced at 10.6 unless stated; Associations, Locations and Trace Configurations resources at 10.9; Circuits and Unit Identifiers at 12.1.*

**Licensing and sessions, applies to every operation here**: the portal account
needs the **ArcGIS Advanced Editing** user type extension (view/query/trace
operations do not). `f` is never marked optional on Esri's pages but defaults to
`html`, so always pass `f=json`. On the editing operations, `sessionId` is
"required when editing a named version, and should not be specified when
editing DEFAULT"; the spelling differs between pages (`sessionId` vs
`sessionID`) — use the spelling on the operation's own page.

## Full `UtilityNetworkServer` resource tree (as of recent Enterprise versions)

```
UtilityNetworkServer
├── disableSubnetworkController
├── disableTopology
├── enableSubnetworkController
├── enableTopology
├── exportSubnetwork
├── queryNetworkMoments
├── synthesizeAssociationGeometries
├── trace
├── updateIsConnected
├── updateSubnetwork
├── validateNetworkTopology
├── Associations
│   ├── query
│   └── traverse
├── Circuits                    (telecom, 12.1)
│   ├── alter / create / delete / export / query / verify
├── Locations
│   └── query
├── Trace Configurations
│   └── alter / create / delete / query
└── Unit Identifiers             (telecom, 12.1)
    └── query / reserve / reset / resize
```
This is the authoritative endpoint map — use it to sanity-check whether a
requested capability exists on this service at all before trying to
construct a request for it.

## `enableTopology`

`POST .../UtilityNetworkServer/enableTopology`
- Enables network topology **for the DEFAULT version only** (topology is a
  DEFAULT-version concept — you cannot enable topology on a named version).
- Parameters: `f`; `maxErrorCount` (optional, default 10,000 — the error
  threshold that stops the enable process); `async` (optional, default
  `false`, introduced 10.9.1). Esri's page lists **no** `gdbVersion` or
  `sessionId` parameter.
- **Must be run by the portal utility network owner** (plus the Advanced
  Editing license).
- Effects: topology is built/updated for the network's **full extent**, all
  **existing errors are deleted**, any new errors go to the dirty areas
  sublayer, and the network is marked enabled. Once enabled, feature and
  association edits generate dirty areas for `validateNetworkTopology` to
  consume.
- Can run **synchronously or asynchronously**. Sync response:
  `{"moment", "success", "error"?}`; async: `{"statusUrl"}` (see `06-*.md`).
- **Concurrency lock**: while enabling, **all other sessions connected to
  DEFAULT are blocked** from running validate or enable — a real operational
  consideration for coordinating a maintenance window.

## `validateNetworkTopology`

`POST .../UtilityNetworkServer/validateNetworkTopology`
- Cleans dirty areas within a specified extent and keeps feature-edit-space
  and network-topology-space consistent.
- Requires the ArcGIS Advanced Editing user type extension.
- Request parameters (all optional on Esri's page except that `f` is not
  labelled optional):
  | Parameter | Notes |
  |---|---|
  | `f` | `html` (default), `json`, `pjson` |
  | `gdbVersion` | default `sde.DEFAULT` |
  | `sessionID` | the parameter table spells it `sessionID`, the syntax block `sessionId`; required when editing a **named version**, not to be specified when editing DEFAULT |
  | `validationType` | `normal` (default), `rebuild`, `forceRebuild` (both added 10.9). `rebuild` works on dirty areas within `validateArea`/`validationSet`; `forceRebuild` ignores dirty areas and rebuilds everything in those inputs |
  | `validateArea` | envelope (`xmin`,`ymin`,`xmax`,`ymax`,`spatialReference`) — the area to validate; optional when `validationSet` is populated, and can be combined with it |
  | `validationSet` | `[{"sourceId": 9, "globalIds": ["{...}"]}]` — validate only these features (for cases where geometry-based validation through the spatial container isn't possible) |
  | `returnEdits` | default `false`; returns edited features per layer in `serviceEdits`; **ignored when `async=true`**; if the count exceeds `maxRecordCount`, no edits are returned and `exceededTransferLimit` is `true` |
  | `async` | `true`/`false`, default `false`; `true` returns a `statusUrl` |
  | `outSR` | introduced 11.1; default is the feature service's spatial reference |
- Sync response: `moment`, `fullUpdate`, `validateErrorsCreated`,
  `dirtyAreaCount`, `exceededTransferLimit` (only with `returnEdits`),
  `serviceEdits` (only with `returnEdits` and `async=false`),
  **`discoveredSubnetworks`**, `success`, `error`. Async completed status adds
  `status`, `submissionTime`, `lastUpdatedTime` and has no `serviceEdits`.
- **`discoveredSubnetworks`** (not `discovered`) — the subnetworks marked
  dirty during the validate run; each item carries `domain`, `tier` and
  `subnetwork`. A subnetwork that was already dirty still appears if the
  operation modified it. The matching capability flag is
  `supportsValidationDiscoveredSubnetworks`.
- **Hierarchical-network edge case worth knowing**: if **every** subnetwork
  in a tier is already dirty, that tier is **not traced** during validate —
  and in that specific scenario, those dirty subnetworks will **not** appear
  in `discoveredSubnetworks` even though they remain dirty. Don't
  interpret an empty/partial list as "nothing is dirty" without
  accounting for this.
- The `TraceNetworkServer` flavour of this operation takes only `f`,
  `gdbVersion`, `sessionID`, `validateArea`, `returnEdits` and has no
  `discoveredSubnetworks` in its documented response.

## `queryNetworkMoments`

`GET/POST .../UtilityNetworkServer/queryNetworkMoments`
- Request: `f=json`; optional `gdbVersion` (default `sde.DEFAULT`),
  `sessionId`, `moment`; optional `momentsToReturn` (array, default = all).
  Allowed `momentsToReturn` values: `initialEnableTopology`,
  `fullValidateTopology`, `partialValidateTopology`, `enableTopology`,
  `disableTopology`, `definitionModification`, `updateIsConnected`,
  `indexUpdate`, `all`. Example: `momentsToReturn=[enableTopology, initialEnableTopology]`.
- Response:
  ```json
  {
    "networkMoments": [
      { "moment": "enableTopology", "time": 1559840642, "duration": 1663 },
      { "moment": "initialEnableTopology", "time": 1559035822, "duration": 1259 }
    ],
    "validNetworkTopology": true,
    "success": true
  }
  ```
- `time` is documented only as a "datetime" (the example shows a 10-digit
  epoch number — the unit is not stated, so **verify against the Esri docs
  for your version** before converting); `duration` is a double in
  milliseconds.
- `initialEnableTopology` vs. `enableTopology` — the very first time topology
  was ever enabled on this network, vs. the most recent enable — useful to
  distinguish "network age" from "last maintenance operation." The other
  moment types report last full/partial validation, last disable, last
  definition modification, last `updateIsConnected` and last index update.

## `updateSubnetwork` (verified against the REST reference, Sept 2026)

`POST .../UtilityNetworkServer/updateSubnetwork` — requires the ArcGIS
Advanced Editing user type extension.

| Parameter | Required | Notes |
|---|---|---|
| `f` | no | `html` (default), `json`, `pjson` |
| `gdbVersion` | no | default `sde.DEFAULT` |
| `sessionId` | no | required when editing a **named version**; not to be specified when editing DEFAULT |
| `domainNetworkName` | **yes** | |
| `tierName` | **yes** | |
| `subnetworkName` | one of these two | a specific subnetwork; if omitted, `allSubnetworksInTier` must be `true` or the request errors |
| `allSubnetworksInTier` | one of these two | default `false`; `true` updates every subnetwork in the tier (bulk refresh after a load) |
| `continueOnFailure` | no | default `false`; applies with `allSubnetworksInTier`: keep going if one fails |
| `traceConfiguration` | no | same properties as the Trace operation's `traceConfiguration`; overrides the tier's subnetwork trace configuration |
| `async` | no | default `false`; `true` returns `{"statusUrl": ...}` (see `06-*.md`) |

Behaviour: traces from all subnetwork controllers, updates the Subnetwork Name
attribute on every feature in the subnetwork, refreshes the SubnetLine record
and the Subnetworks table, generates/updates diagrams, and marks the subnetwork
clean.

Responses: sync `{"moment": ..., "success": true}` plus `failures`
(only when `continueOnFailure=true`; items `subnetworkName`, `message` and
`extendedError`); async `{"statusUrl": ...}`, completed status adds `status:
"Completed"`, `submissionTime`, `lastUpdatedTime` (its `failures` items name the
code field `extendedCode` — Esri's page is inconsistent between sync and async);
failure `{"success": false, "error": {"extendedCode", "message", "details"}}`.

## `exportSubnetwork` (verified against the REST reference, Sept 2026)

`POST .../UtilityNetworkServer/exportSubnetwork` — requires the Advanced
Editing user type extension.

| Parameter | Required | Notes |
|---|---|---|
| `f` | no | adds `pbf` at 11.3 |
| `gdbVersion`, `sessionId`, `moment` | no | as for trace |
| `domainNetworkName`, `tierName`, `subnetworkName` | **yes** | |
| `exportAcknowledgement` | no | default `false`; when `true`, `gdbVersion` must be the default version. A subnetwork whose controllers are all logically deleted and which is exported with `true` has its rows physically deleted from the Subnetworks table and **no JSON file is created** |
| `traceConfiguration` | no | same properties as the Trace operation's |
| `resultTypes` | no | `type` = `features`, `connectivity`, `associations`, `relatedRecords` (11.5+); also `includeGeometry`, `includeDomainDescriptions`, `includePropagatedValues` (`features` only, 12.1), `includeFlowDirections` (`features`/`connectivity` only, 12.1), `networkAttributeNames`, `diagramTemplateName`, `resultTypeFields`, `relationshipClasses` (`originLayerId`/`destinationLayerId` required with `relatedRecords`) |
| `async` | no | default `false`; introduced 10.9.1 |
| `outSR` | no | 11.1+ |

`pbf` is not supported with the `relatedRecords` result type (11.5).

Response: `{"moment", "url", "subnetworkHasBeenDeleted", "success"}` — `url`
points to the created JSON file. Async: `{"statusUrl"}`; the completed status
repeats the sync body plus `status: "Completed"`, `submissionTime`,
`lastUpdatedTime`. The file's top-level keys (12.1+) are `controllers`,
`featureElements`, `connectivity`, `associations`, `relatedRecords`,
`sourceMapping`, `resultTypes`, `spatialReference` (older versions have fewer;
12.1 adds `flowDirection`). Download it; don't expect the payload inline.

## `disableTopology`
Inverse of `enableTopology` — required before many schema-configuration GP
tools can run (they require topology disabled, per `pro-help/03-*.md`).
`POST .../disableTopology`; parameters `f`, `gdbVersion` (default
`sde.DEFAULT`), `sessionId` (required when editing a named version),
`async` (default `false`, introduced 10.9.1). Unlike `enableTopology`, it can
be run in DEFAULT **or a named version**; once disabled in a named version it
cannot be re-enabled there (reconcile to inherit DEFAULT's state). Must be run
by the **portal utility network owner**. Effects: deletes all rows in the
topology tables, edits no longer generate dirty areas (existing errors and dirty
areas remain), analytics and diagram generation cannot run while disabled.
Response `{"moment", "success", "error"?}`; async `{"statusUrl"}`.

## `updateIsConnected`
`POST .../updateIsConnected`; parameters `f` and `async` (default `false`,
10.9.1) **only** — no `gdbVersion`/`sessionId`: it works on the DEFAULT
version. Updates the `IsConnected` attribute on all network features based on
connectivity to subnetwork controllers. Requires topology enabled, a
**traditional** (non-telecom) domain network, and the **portal utility
network owner**. Response `{"moment", "success", "error"?}`; async
`{"statusUrl"}`.

`enableSubnetworkController`/`disableSubnetworkController` and
`synthesizeAssociationGeometries` are documented in full below.

## `Associations` resource

`.../UtilityNetworkServer/Associations` — operations **`query`** and
**`traverse`**.

### `query`
```
POST .../associations/query
types=["containment"]
elements=[{"networkSourceId":19,"globalId":"{AE323515-8E6F-4CC2-B9A8-1DB963E769AB}"}]
```
- Parameters (GET or POST, introduced 10.9): `f`; `gdbVersion` (default
  `sde.DEFAULT`); `moment` (epoch ms); `types` (optional, default all);
  **`elements` (required)**; `returnDeletes` (optional, default `false`;
  include logically deleted associations). There is no `async`/`outSR`.
- `types` — filter by association type(s). Exact allowed values:
  `attachment`, `containment`, `junctionJunctionConnectivity`,
  `junctionEdgeFromConnectivity`, `junctionMidspanConnectivity`,
  `junctionEdgeToConnectivity`. (There is no plain `"connectivity"` value in
  this filter, although the `associationType` strings returned by `traverse`,
  `locations/query` and `synthesizeAssociationGeometries` do use
  `connectivity` — and `locations/query` spells the midspan value
  `junctionEdgeMidspanConnectivity`.)
- Each returned association carries `globalId`, `associationType`
  (camelCase), from/to network source, globalId and terminal (`-1` = no
  terminal), `percentAlong`, `isContentVisible`, `status`, `errorCode`,
  `errorMessage`.
- `elements` — an array of `{networkSourceId, globalId}` objects (optional
  `terminalId`) identifying the feature(s) to find associations for — this
  `networkSourceId` + `globalId` shape is the same element-addressing
  pattern used in trace starting points and the `traverse` operation.
- Recall the standing caveat (from the C# SDK reference): a **query is only
  one building block of topology** — features connected purely by geometric
  coincidence won't show up here; use a trace for full connectivity.

### `traverse`
`POST .../associations/traverse` (introduced 10.9; Advanced Editing license).
Walks a **chain of associations** from starting `elements`, staying within
association-relationships rather than invoking trace/connectivity semantics —
e.g. "what's nested inside this container, all the way down". All parameters
are optional on Esri's page except `f` is unlabelled:

| Parameter | Values / default |
|---|---|
| `gdbVersion`, `moment` | as elsewhere (default `sde.DEFAULT` / current moment) |
| `elements` | array of `{networkSourceId, globalId, terminalId?}` where the traversal starts |
| `type` | `unspecified` (default), `dirtyAreaExpansion`, `firstContainers`, `spatialParents`, `topContainers`, `errorsNotModified`, `modifiedObjects` — any value other than `unspecified` makes the five custom-traversal parameters below ignored |
| `direction` | `ascending`, `descending` (default) |
| `dirtyStatusFilter` | `none` (default), `dirty`, `notDirty` |
| `errorStatusFilter` | `none` (default), `inError`, `notInError` (combined with the dirty filter by AND) |
| `stopAtFirstSpatial` | boolean, default `true` |
| `maxDepth` | short, default `MAX_INT` |

Response: `associations` (same fields as `query`) and `objects`
(`sourceId`, `globalId`), `success`, `error`.

### Capability flags relevant to Associations (on the root `UtilityNetworkServer` response)
```json
{
  "supportsAssociations": true,
  "supportsQueryAssociations": true,
  "supportsJunctionEdgeAssociations": true,
  "supportsMidspanAssociations": true,
  "supportsTraverseAssociations": true
}
```
Check `supportsTraverseAssociations` specifically before assuming `traverse`
is available — it's a distinct, separately-introduced capability from basic
`query` support.

## `Locations` resource

`.../UtilityNetworkServer/Locations` — operation **`query`** only.

### `query`
```
POST .../locations/query
objects=[{"sourceId": 20, "globalIds": ["{...}"]}]
maxGeometryCount=500
attachmentAssociations=true
connectivityAssociations=true
containmentAssociations=true
locations=true
async=false
```
- **Purpose**: reports the **locatability** of the given objects and,
  optionally, **synthesizes geometry** for them (returned as a geometry bag
  of points/polylines) — this is how a client resolves "where is this
  nonspatial object, spatially, right now" without that object carrying its
  own geometry.
- Parameters (GET or POST, introduced 10.9): `f`, `gdbVersion`, `sessionId`
  (needed if a session holds an exclusive lock on the version), `moment`,
  **`objects` (required)**, **`maxGeometryCount` (required, short — maximum
  number of geometries to synthesize and return)**, the three association
  booleans, `locations`, `outSR` (11.1+), `async` (10.9.1+).
- `objects` (required) — array of `{sourceId, globalIds}` — note **plural
  `globalIds`** here (an array per source), a different shape from the
  singular `globalId` used in `Associations query`'s `elements` array —
  **don't assume uniform parameter shapes across sibling resources.**
- Response: `exceededTransferLimit`, `objects` (`sourceId`, `globalId`,
  `isLocatable`, optional `geometry` — Esri's syntax block spells it `sourceID`
  but its example uses `sourceId`), `associations` (with `geometry`),
  `success`, `error`.
- `attachmentAssociations` / `connectivityAssociations` /
  `containmentAssociations` (each boolean, default `false`) — independently
  toggle which association-derived geometry types get synthesized alongside
  the object's own location.
- `locations` (boolean) — synthesize the geometry representing the object's
  own **derived location** (only meaningful when the target `objects` are
  features or nonspatial objects).
- `async` (default `false`) — supported here too (see
  `rest-api/06-asynchronous-operations-job-status.md` for the polling shape)
  — relevant for locating/synthesizing geometry for a large batch of objects.

## Enable / Disable Subnetwork Controller

`.../UtilityNetworkServer/enableSubnetworkController` and
`.../disableSubnetworkController` — the REST-level equivalent of the Pro UI's
**Modify Controller** pane (`pro-help/02-structure-of-a-utility-network.md`).

### `enableSubnetworkController` parameters
`POST` only. Not async.
| Parameter | Required | Notes |
|---|---|---|
| `f` | no | `html` (default), `json`, `pjson` |
| `gdbVersion` | no | default `sde.DEFAULT` |
| `sessionID` | no | required when editing a named version; omit for DEFAULT |
| `networkSourceId` | **yes** | network source ID of the class the controller participates in |
| `featureGlobalId` | **yes** | GUID of the device to enable |
| `terminalID` | **yes** | terminal ID of the device (capital `ID` on Esri's page) |
| `subnetworkControllerName` | **yes** | name of the controller |
| `tierName` | **yes** | tier the subnetwork belongs to |
| `subnetworkName` | no | if omitted, a unique GUID is generated as the name |
| `description` | no | default `null` |
| `notes` | no | free text |
| `outSR` | no | 11.1+; JSON `{"wkid":..}` or wkt/wkt2 |

There is **no** `domainNetworkName` parameter on this operation.

### `disableSubnetworkController` parameters
`f`, `gdbVersion`, `sessionId` (same conventions), and **required**
`networkSourceId`, `featureGlobalId`, `terminalId` (all three identify the
terminal to disable); `outSR` optional (11.1+).

Both operations return the generic edit response: `moment`,
`exceededTransferLimit`, `serviceEdits` (`id` plus `editedFeatures` with
`adds`/`updates`/`deletes`), `success`, `error`. They apply to devices that
have the Subnetwork Controller network capability set. Recall from the Pro Help
reference: eligibility to become a controller depends on terminal
configuration, network category assignment, and the tier's subnetwork
definition — these REST operations **toggle an already-eligible** feature's
controller status; they don't perform the underlying eligibility
configuration themselves (that's a Pro/GP-tool-time configuration step, not a
runtime REST call).

## Synthesize Association Geometries

`.../UtilityNetworkServer/synthesizeAssociationGeometries`
- **Purpose**: exports geometry representing associations — synthesized as
  **line segments** connecting the geometries of the features at each
  association's endpoints (since associations themselves carry no inherent
  geometry — `pro-help/02-structure-of-a-utility-network.md`).
- **Hard requirement**: **both** features in an association must fall within
  the specified `extent` for a line to be synthesized — if only one
  endpoint intersects the extent, **no geometry is synthesized** for that
  association. This is a common "why don't I see this connector line"
  troubleshooting root cause.
- Parameters: `f`, `gdbVersion` (default `sde.DEFAULT`), `sessionId`
  (needed if a session holds an exclusive lock), `moment`,
  `attachmentAssociations`, `connectivityAssociations`,
  `containmentAssociations` (each boolean, default `false`, toggling which
  association types are included), `outSR` (11.1+), and two **required**
  parameters: **`extent`** (envelope JSON: `xmin`, `ymin`, `xmax`, `ymax`,
  `spatialReference`) and **`maxGeometryCount`** (short — the maximum
  number of geometries to synthesize and return). Not async.
- Response: `maxGeometryCountExceeded`, `associations` (each with `globalId`,
  `associationType` = `attachment`/`connectivity`/`containment`, from/to
  network source / globalId / terminalId, `geometry`), `success`, `error`.
- This is the REST operation underlying the JS API's
  `synthesizeAssociationGeometries()` method
  (`js-api/03-network-class-loading-and-definition.md`) and the
  `UtilityNetworkAssociations` widget's rendering
  (`js-api/01-javascript-sdk-utility-network.md`).

## Telecom-only child resources (brief — full detail in `07-circuits-and-unit-identifiers-telecom.md`)
- **`Circuits`** (introduced 12.1) — `alter / create / delete / export / query / verify` —
  telecom circuit management, parallel to how domain/subnetwork management
  works for traditional networks but modeling telecom circuits specifically.
- **`Unit Identifiers`** (introduced 12.1) — `query / reserve / reset / resize` — manages
  telecom unit identifier pools (e.g., allocating the next available fiber
  strand/unit ID) — a telecom-specific resource-allocation system with no
  equivalent in traditional (electric/gas/water) domain networks.

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/utility-network-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/enabletopology-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/disabletopology-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/validatenetworktopology-utiility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/validatenetworktopology-trace-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/querynetworkmoments-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/updatesubnetwork-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/exportsubnetwork-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/updateisconnected-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/enablesubnetworkcontroller-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/disablesubnetworkcontroller-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/synthesizeassociationgeometries-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/associations-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-associations-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/traverse-associations-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/locations-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-locations-utilitynetwork-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/unitIdentifiers-utility-network-server/
