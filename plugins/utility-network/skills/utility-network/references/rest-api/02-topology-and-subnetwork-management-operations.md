# Utility Network — REST API: Topology & Subnetwork Management Operations (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

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
├── Circuits                    (telecom)
│   ├── alter / create / delete / export / query / verify
├── Locations
│   └── query
├── Trace Configurations
│   └── alter / create / delete / query
└── Unit Identifiers             (telecom)
    └── query / reserve / reset / resize
```
This is the authoritative endpoint map — use it to sanity-check whether a
requested capability exists on this service at all before trying to
construct a request for it.

## `enableTopology`

`POST .../UtilityNetworkServer/enableTopology`
- Enables network topology **for the DEFAULT version only** (topology is a
  DEFAULT-version concept — you cannot enable topology on a named version).
- Effects: topology is built/updated for the network's **full extent**, all
  **existing errors are deleted**, any new errors go to the dirty areas
  sublayer, and the network is marked enabled.
- Can run **synchronously or asynchronously**.
- **Concurrency lock**: while enabling, **all other sessions connected to
  DEFAULT are blocked** from running validate or enable — a real operational
  consideration for coordinating a maintenance window.

## `validateNetworkTopology`

`POST .../UtilityNetworkServer/validateNetworkTopology`
- Cleans dirty areas within a specified extent and keeps feature-edit-space
  and network-topology-space consistent.
- Requires the ArcGIS Advanced Editing user type extension.
- Request parameters (verified Sept 2026):
  | Parameter | Notes |
  |---|---|
  | `f` | `html`, `json`, `pjson` |
  | `gdbVersion` | default `sde.DEFAULT` |
  | `sessionID` | spelled with capital *ID* in the reference; needed when **your client** holds the edit session (exclusive lock) on the version; omit otherwise. Same rule as trace; confirm on the live operation page |
  | `validationType` | `normal`, `rebuild`, `forceRebuild` |
  | `validateArea` | envelope with `spatialReference` — the area to validate |
  | `validationSet` | optional `[{"sourceId": 9, "globalIds": ["{...}"]}]` — validate only these features |
  | `returnEdits` | return edited features by layer |
  | `async` | `true` for large areas |
  | `outSR` | output spatial reference |
- **Response includes a `discovered` collection** — the subnetworks marked
  dirty during (or found already dirty before) the validate run, each
  reported with its domain network and tier.
- **Hierarchical-network edge case worth knowing**: if **every** subnetwork
  in a tier is already dirty, that tier is **not traced** during validate —
  and in that specific scenario, those dirty subnetworks will **not** appear
  in the `discovered` collection even though they remain dirty. Don't
  interpret an empty/partial `discovered` list as "nothing is dirty" without
  accounting for this.

## `queryNetworkMoments`

`GET/POST .../UtilityNetworkServer/queryNetworkMoments`
- Request: `f=json`, `momentsToReturn=[enableTopology, initialEnableTopology]`
  (array of which moment types to fetch).
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
- `time` is epoch seconds; `duration` is how long that enable operation took
  (useful for auditing/monitoring how expensive topology enable operations
  have been historically on this network).
- `initialEnableTopology` vs. `enableTopology` — the very first time topology
  was ever enabled on this network, vs. the most recent enable — useful to
  distinguish "network age" from "last maintenance operation."

## `updateSubnetwork` (verified against the REST reference, Sept 2026)

`POST .../UtilityNetworkServer/updateSubnetwork` — requires the ArcGIS
Advanced Editing user type extension.

| Parameter | Required | Notes |
|---|---|---|
| `f` | no | `html` (default), `json`, `pjson` |
| `gdbVersion` | no | default `sde.DEFAULT` |
| `sessionId` | no | needed when your client holds the exclusive edit session on the version (edits made in that session are then visible to the operation); omit for reads |
| `domainNetworkName` | **yes** | |
| `tierName` | **yes** | |
| `subnetworkName` | one of these two | a specific subnetwork |
| `allSubnetworksInTier` | one of these two | `true` updates every subnetwork in the tier (bulk refresh after a load) |
| `continueOnFailure` | no | with `allSubnetworksInTier`: keep going if one fails |
| `traceConfiguration` | no | override the tier's subnetwork trace configuration |
| `async` | no | `true` returns `{"statusUrl": ...}` (see `06-*.md`) |

Responses: sync `{"moment": ..., "success": true}`; async
`{"statusUrl": ...}`; failure `{"success": false, "error": {"extendedCode",
"message", "details"}}`.

## `exportSubnetwork` (verified against the REST reference, Sept 2026)

`POST .../UtilityNetworkServer/exportSubnetwork` — requires the Advanced
Editing user type extension.

| Parameter | Required | Notes |
|---|---|---|
| `f` | no | adds `pbf` at 11.3 |
| `gdbVersion`, `sessionId`, `moment` | no | as for trace |
| `domainNetworkName`, `tierName`, `subnetworkName` | **yes** | |
| `exportAcknowledgement` | no | `true` stamps the controllers' last-exported time; **DEFAULT only** |
| `traceConfiguration` | no | |
| `resultTypes` | no | `features`, `connectivity`, `associations`, `relatedRecords` (11.5+) |
| `async` | no | 10.9.1+ |
| `outSR` | no | 11.1+ |

Response: `{"moment", "url", "subnetworkHasBeenDeleted", "success"}` — `url`
points to the JSON file in `arcgisoutput` (controllers, features,
connectivity, associations). Download it; don't expect the payload inline.

## `disableTopology` (brief note)
Inverse of `enableTopology` — disables topology on DEFAULT, required before
many schema-configuration GP tools can run (they require topology disabled,
per `pro-help/03-*.md`). Same request-parameter conventions as
`enableTopology`; supports `async` (`rest-api/06-*.md`). `updateIsConnected`
is documented in full in `rest-api/06-asynchronous-operations-job-status.md`.
`enableSubnetworkController`/`disableSubnetworkController` and
`synthesizeAssociationGeometries` are now documented in full below.

## `Associations` resource

`.../UtilityNetworkServer/Associations` — operations **`query`** and
**`traverse`**.

### `query`
```
POST .../associations/query
types=["containment"]
elements=[{"networkSourceId":19,"globalId":"{AE323515-8E6F-4CC2-B9A8-1DB963E769AB}"}]
```
- `types` — filter by association type(s). Exact allowed values (verified
  Sept 2026): `attachment`, `containment`, `junctionJunctionConnectivity`,
  `junctionEdgeFromConnectivity`, `junctionMidspanConnectivity`,
  `junctionEdgeToConnectivity`. (There is no plain `"connectivity"` value.)
- `moment`, `returnDeletes` — optional.
- Each returned association carries `associationType` (camelCase),
  from/to network source, globalId and terminal (`-1` = no terminal),
  `isContentVisible`, `status`, `errorCode`.
- `elements` — an array of `{networkSourceId, globalId}` pairs identifying
  the feature(s) to find associations for — this `networkSourceId` +
  `globalId` shape is the same element-addressing pattern used in trace
  starting points and Locations queries (below).
- Recall the standing caveat (from the C# SDK reference): a **query is only
  one building block of topology** — features connected purely by geometric
  coincidence won't show up here; use a trace for full connectivity.

### `traverse`
Walks a **chain of associations** (e.g., recursively expanding container →
content → sub-content) from a starting element, staying within
association-relationships rather than invoking full trace/connectivity
semantics — useful for "what's nested inside this container, all the way
down" without the overhead of a full network trace.

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
- `objects` (required) — array of `{sourceId, globalIds}` — note **plural
  `globalIds`** here (an array per source), a different shape from the
  singular `globalId` used in `Associations query`'s `elements` array —
  **don't assume uniform parameter shapes across sibling resources.**
- `attachmentAssociations` / `connectivityAssociations` /
  `containmentAssociations` (each boolean, default `false`) — independently
  toggle which association-derived geometry types get synthesized alongside
  the object's own location.
- `locations` (boolean) — synthesize the geometry representing the object's
  own **derived location** (only meaningful when the target `objects` are
  features or nonspatial objects).
- `async` — supported here too (see
  `rest-api/06-asynchronous-operations-job-status.md` for the polling shape)
  — relevant for locating/synthesizing geometry for a large batch of objects.

## Enable / Disable Subnetwork Controller

`.../UtilityNetworkServer/enableSubnetworkController` and
`.../disableSubnetworkController` — the REST-level equivalent of the Pro UI's
**Modify Controller** pane (`pro-help/02-structure-of-a-utility-network.md`).

### `enableSubnetworkController` parameters
| Parameter | Notes |
|---|---|
| `f`, `gdbVersion`, `sessionID` | Standard version/session parameters, same conventions as elsewhere in this service. |
| (feature/terminal identification) | Which feature + terminal to enable as a controller — same element-addressing pattern as other operations. |
| `description` (optional) | Free-text description of the subnetwork controller; default `null`. |
| `notes` (optional) | Free-text notes associated with the controller. |
| `outSR` (optional, 11.1+) | Output spatial reference for any returned geometry. |

`disableSubnetworkController` follows the same general shape in reverse
(identify the controller to disable). Recall from the Pro Help reference:
eligibility to become a controller depends on terminal configuration,
network category assignment, and the tier's subnetwork definition — these
REST operations **toggle an already-eligible** feature's controller status;
they don't perform the underlying eligibility configuration themselves
(that's a Pro/GP-tool-time configuration step, not a runtime REST call).

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
- Parameters: `f`, `gdbVersion`, `sessionId`, `moment`, `attachmentAssociations`,
  `connectivityAssociations`, `containmentAssociations` (each boolean,
  toggling which association types are included), `outSR`.
- This is the REST operation underlying the JS API's
  `synthesizeAssociationGeometries()` method
  (`js-api/03-network-class-loading-and-definition.md`) and the
  `UtilityNetworkAssociations` widget's rendering
  (`js-api/01-javascript-sdk-utility-network.md`).

## Telecom-only child resources (brief — full detail in `07-circuits-and-unit-identifiers-telecom.md`)
- **`Circuits`** — `alter / create / delete / export / query / verify` —
  telecom circuit management, parallel to how domain/subnetwork management
  works for traditional networks but modeling telecom circuits specifically.
- **`Unit Identifiers`** — `query / reserve / reset / resize` — manages
  telecom unit identifier pools (e.g., allocating the next available fiber
  strand/unit ID) — a telecom-specific resource-allocation system with no
  equivalent in traditional (electric/gas/water) domain networks.
