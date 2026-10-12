# Utility Network — JS API: The `UtilityNetwork`/`Network` Class in Depth (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/references/core/networks/ (UtilityNetwork, Network)*

> Last reviewed: 2026-10-12 (JS SDK 5.1 / Enterprise 12.1 / UN dataset v8)

This expands on the basic loading pattern in `js-api/01-javascript-sdk-utility-network.md`
with the full class surface: standalone loading (no web map required),
definition/schema access, and historical-moment queries.

## Class hierarchy

`UtilityNetwork` (`@arcgis/core/networks/UtilityNetwork.js`) extends the base
`Network` class (`@arcgis/core/networks/Network.js`, both since 4.20).
Properties/methods common to any network type (`Network.type` is `"utility"`
or `"trace"`) live on `Network`; UN-specific ones live on `UtilityNetwork`
itself (`UtilityNetwork → Network → Accessor`).

## Three ways to obtain a `UtilityNetwork` instance

### 1. From a loaded WebMap (most common — see `01-*.md` for the full pattern)
```javascript
if (webMap.utilityNetworks.length > 0) {
  utilityNetwork = webMap.utilityNetworks.at(0); // or getItemAt(0) in older syntax
  await utilityNetwork.load();
}
```
`load()` loads the network definition **and all shared named trace
configurations**, so `sharedNamedTraceConfigurations` is populated on this
path. Don't assume every loading path gives you the same populated property
set — see `fromPortalItem()` below, which does not populate them.

### 2. Standalone, directly from a feature service URL (no map needed)
```javascript
const utilityNetwork = new UtilityNetwork({
  layerUrl: "https://hostName.com/server/rest/services/Test/FeatureServer/17"
});
await utilityNetwork.load();
```
This is the right pattern for **server-side scripts, Node tooling, or
headless analysis** that doesn't need a map/view at all — a trace or
association edit can be run purely against this loaded instance.

### 3. From a portal item
```javascript
const utilityNetwork = await UtilityNetwork.fromPortalItem({
  portalItem: { id: "..." }
});
```
Static method on `Network`. **Documented limitation**: `fromPortalItem()`
does **not** populate `sharedNamedTraceConfigurations` — if named trace
configs are needed, load through a web map instead, or fetch them separately.

## Key properties

| Property | Type | Notes |
|---|---|---|
| `dataElement` | `NetworkDataElementJSON \| null \| undefined` | **The full network definition** — domain networks, tiers, network attributes, sources, etc. — only populated **after** `load()` completes. This is the JS equivalent of the C# SDK's `UtilityNetworkDefinition` / the Runtime SDK's same-named class. |
| `datasetName` | String | The physical dataset name in the backend database — useful for cross-referencing against DB-level tooling/logs. |
| `owner` | String | The portal user who owns the network — relevant for permission-related troubleshooting (recall several REST operations require being the network/version owner). |
| `associationsTable` | `FeatureLayer \| null \| undefined` (readonly) | Direct handle to the associations system table as an ordinary `FeatureLayer` — load it with `utilityNetwork.loadAssociationsTable()` (since 4.32); usable with normal `query()` once you have it, without manually resolving `utilityNetworkLayerId` the way the raw-REST appendix requires (see `rest-api/05-feature-service-associations-appendix.md`). |
| `domainNetworkNames` | `String[]` (readonly) | Names of all domain networks in this utility network (a simpler, name-only accessor; use `dataElement` for full domain network detail — sources, tiers, structure/telecom flags). Also see `getTierNames(domainNetworkName)`, `terminalConfigurations`, and `hasTelecomNetwork` (since 4.34). |
| `sharedNamedTraceConfigurations` | `NamedTraceConfiguration[]` | Trace configurations shared on the web map. `NamedTraceConfiguration.traceConfiguration` (the full definition) is documented as available only when the utility network is fully loaded. |
| `historicMoment` (on `Network`) | `Date \| null \| undefined` | Set this to query the network **as of a historical moment** instead of current — mirrors the REST `moment` parameter and the Pro Help "trace/analyze at a historical moment" capability (`pro-help/06-*.md`). |
| `networkSystemLayers` | `NetworkSystemLayers` (`@arcgis/core/networks/support/NetworkSystemLayers.js`) | URLs **and IDs** for the network's system tables/layers: `dirtyAreasLayerUrl`/`dirtyAreasLayerId`, `rulesTableUrl`/`rulesTableId`, `subnetworksTableUrl`/`subnetworksTableId`, `associationsTableUrl`/`associationsTableId` (since 4.29), plus on-demand `loadAssociationsTable()` (4.32) and `loadSubnetworksTable()` (4.34). This is the direct way to add e.g. the dirty-areas layer to a map in JS (see the validate-topology workflow in `05-editing-associations-validation.md`) without manually resolving `utilityNetworkLayerId` → systemLayers the raw-REST way. |

## Method: `synthesizeAssociationGeometries()`
```javascript
const result = await utilityNetwork.synthesizeAssociationGeometries(params);
// result: Promise<AssociationGeometriesResult>
```
Since 4.28; takes a `SynthesizeAssociationGeometriesProperties` object
(`returnAttachmentAssociations`, `returnConnectivityAssociations`,
`returnContainmentAssociations`, `extent`, `maxGeometryCount`,
`outSpatialReference`). The JS-native method mirroring the REST
`synthesizeAssociationGeometries` operation (`rest-api/02-topology-and-subnetwork-management-operations.md`) —
generates the visual line geometry for associations, which have no inherent
spatial presence of their own (see `pro-help/02-structure-of-a-utility-network.md`).
The `SynthesizeAssociationGeometriesParameters` class (mentioned in
`01-javascript-sdk-utility-network.md`) is the equivalent standalone
parameter class for the functional REST API.

## Network Diagrams: no JS API support found

**As of this review (JS SDK 5.1), no Network Diagram classes or diagram-layer
support were found in the ArcGIS Maps SDK for JavaScript reference or the
utility-network guide** (an earlier Esri Community answer from Esri staff said
the same). There is no JS equivalent to the Pro Help diagram concepts
(`pro-help/07-network-diagrams.md`) or the REST `NetworkDiagramServer`
(`rest-api/03-network-diagram-service.md`). Absence is not formally
announced as permanent — check the current release notes before asserting it.

**What this means practically**: a JS web app can only reach network
diagrams by **calling the `NetworkDiagramServer` REST operations directly**
(e.g., `createDiagramFromFeatures`, `findDiagramInfos`) via `fetch`/`esriRequest`
and building **custom, from-scratch rendering** of the returned diagram
content (nodes/edges/containers) — there is no widget or layer type to hand
this to. If someone asks for "a network diagram viewer in my JS app," set
this expectation clearly up front rather than searching for a nonexistent
class, and point them at the REST reference file for the raw data they'd
need to render themselves.

## `dataElement` — the full schema, in JS terms

`dataElement` is a `NetworkDataElementJSON` object. One documented nested
type worth knowing explicitly is **`DomainNetworkJSON`**:

| Property | Type | Notes |
|---|---|---|
| `domainNetworkName` | String | |
| `isStructureNetwork` | Boolean | True for the network's single structure network entry |
| `isTelecomNetwork` | Boolean | True for a telecom domain network (vs. traditional) |
| `junctionSources` | Object[] | Network source objects for junction features in this domain network |
| `terminalConfigurationId` | Number (optional) | The terminal configuration ID for an asset type, if applicable |

(Property list carried over from earlier research and not re-verified in this
review — confirm against the `NetworkDataElementJSON` / `DomainNetworkJSON`
types in the JS reference for your version.)

This directly mirrors the Pro Help / C# SDK concepts (traditional vs. telecom
domain network, terminal configurations) — see
`pro-help/02-structure-of-a-utility-network.md` and
`pro-sdk/01-csharp-sdk-utility-network-api.md` for the conceptual/administrative
side of the same schema.

## Useful `Network`/`UtilityNetwork` methods beyond loading

| Method | Purpose |
|---|---|
| `getLayerIdBySourceId(sourceId)` | Resolve a network source's internal ID to the actual **feature service layer ID** — useful when a trace result gives you `sourceId`s and you need to know which layer to query for the real features. |
| `getObjectIdsFromElements(elements)` | Convert an array of `NetworkElement` (as returned by a trace) into `LayerInfo[]` (layer + Object ID pairs) — the standard bridge from **trace results** to **actually selecting/querying the real features** in a `FeatureLayer`. |
| `canAddAssociation(association)` | Since 4.29. Returns `Promise<Boolean>` — checks whether a given association would be valid **before** attempting to write it (covered further in `05-editing-associations-validation.md`). |
| `queryAssociations(props)` | Since 4.28. Returns `Promise<Association[]>`; props: `elements`, `types`, `returnDeletes`. |
| `trace(props)` / `submitTraceJob(props)` | Since 4.27. Run a trace (or submit it as a job) from a `TraceProperties` object. |
| `getCircuitManager(telecomDomainNetworkName)` / `getUnitIdentifierManager()` | Since 4.34. Telecom domain network entry points (see `05-editing-associations-validation.md`). |

## Practical guidance for Claude

1. **Default to the web-map loading pattern** for typical map-centric apps;
   reach for the standalone `layerUrl` constructor only when there's
   genuinely no map/view involved (scripts, background jobs, server-side
   Node code).
2. When someone has trace results and wants to **actually select or zoom to**
   the real features, the missing link is almost always
   `getObjectIdsFromElements` — mention it proactively rather than letting
   them reinvent ID-matching logic by hand.
3. Don't assume `sharedNamedTraceConfigurations` is populated from *every*
   loading path — call out `fromPortalItem()`'s documented gap specifically
   if that's the loading method in play.
4. For historical/"as of a past moment" queries or traces, set
   `historicMoment` rather than trying to pass a moment parameter into
   individual trace calls — it's a property on the network object itself.

## Sources
- https://developers.arcgis.com/javascript/latest/references/core/networks/UtilityNetwork/
- https://developers.arcgis.com/javascript/latest/references/core/networks/Network/
- https://developers.arcgis.com/javascript/latest/references/core/networks/support/NetworkSystemLayers/
- https://developers.arcgis.com/javascript/latest/references/core/WebMap/
- https://developers.arcgis.com/javascript/latest/utility-network/utility-network-intro
