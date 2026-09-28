# Utility Network — JS API: The `UtilityNetwork`/`Network` Class in Depth (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/api-reference/ (esri/networks/UtilityNetwork, esri/networks/Network)*

This expands on the basic loading pattern in `js-api/01-javascript-sdk-utility-network.md`
with the full class surface: standalone loading (no web map required),
definition/schema access, and historical-moment queries.

## Class hierarchy

`UtilityNetwork` (`@arcgis/core/networks/UtilityNetwork.js`) extends the base
`Network` class (`@arcgis/core/networks/Network.js`). Properties/methods
common to any network type (utility or trace) live on `Network`; UN-specific
ones live on `UtilityNetwork` itself.

## Three ways to obtain a `UtilityNetwork` instance

### 1. From a loaded WebMap (most common — see `01-*.md` for the full pattern)
```javascript
if (webMap.utilityNetworks.length > 0) {
  utilityNetwork = webMap.utilityNetworks.at(0); // or getItemAt(0) in older syntax
  await utilityNetwork.load();
}
```
**Known limitation**: this method does **not** populate
`sharedNamedTraceConfigurations`... actually it does when going through
`load()` on the web-map-sourced instance — the limitation applies
specifically to `Network.fromPortalItem()` below. Don't assume every loading
path gives you the same populated property set; always check what a
specific loading method's own docs say it does and doesn't populate.

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
| `associationsTable` | `FeatureLayer \| null \| undefined` | Direct handle to the associations system table as an ordinary `FeatureLayer` — usable with normal `query()`/`applyEdits()` once you have it, without manually resolving `utilityNetworkLayerId` the way the raw-REST appendix requires (see `rest-api/05-feature-service-associations-appendix.md`). |
| `domainNetworkNames` | `String[]` | Names of all domain networks in this utility network (a simpler, name-only accessor; use `dataElement` for full domain network detail — sources, tiers, structure/telecom flags). Note: some docs/versions show this as `domainNetworks` — check the live reference for the SDK version in use if a property lookup fails. |
| `sharedNamedTraceConfigurations` | `NamedTraceConfiguration[]` | Usable **before** full `load()` completes (only `globalId`/`title` populated then); fully populated after `load()`. |
| `historicMoment` (on `Network`) | `Date \| null \| undefined` | Set this to query the network **as of a historical moment** instead of current — mirrors the REST `moment` parameter and the Pro Help "trace/analyze at a historical moment" capability (`pro-help/06-*.md`). |
| `networkSystemLayers` | Object | URLs **and IDs** for the network's system tables/layers — confirmed members include `dirtyAreasLayerUrl`/`dirtyAreasLayerId`, plus (per Esri's own description) rules and subnetworks tables/layers. This is the direct way to add e.g. the dirty-areas layer to a map in JS (see the validate-topology workflow in `05-editing-associations-validation.md`) without manually resolving `utilityNetworkLayerId` → systemLayers the raw-REST way. |

## Method: `synthesizeAssociationGeometries()`
```javascript
const result = await utilityNetwork.synthesizeAssociationGeometries(params);
// result: Promise<AssociationGeometriesResult>
```
The JS-native method mirroring the REST `synthesizeAssociationGeometries`
operation (`rest-api/02-topology-and-subnetwork-management-operations.md`) —
generates the visual line geometry for associations, which have no inherent
spatial presence of their own (see `pro-help/02-structure-of-a-utility-network.md`).
This is what `SynthesizeAssociationGeometriesParameters` (mentioned in
`01-javascript-sdk-utility-network.md`) is the parameter object for.

## Network Diagrams: not supported in the JS API (confirmed gap, not an oversight)

**As of this writing, the ArcGIS Maps SDK for JavaScript has no Network
Diagram classes or diagram-layer support**, confirmed directly by Esri staff
on the Esri Community forums. There is no JS equivalent to the Pro Help
diagram concepts (`pro-help/07-network-diagrams.md`) or the REST
`NetworkDiagramServer` (`rest-api/03-network-diagram-service.md`).

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
| `canAddAssociation(association)` | Returns `Promise<Boolean>` — checks whether a given association would be valid **before** attempting to write it (covered further in `05-editing-associations-validation.md`). |

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
