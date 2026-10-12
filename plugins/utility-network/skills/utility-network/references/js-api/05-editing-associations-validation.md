# Utility Network — JS API: Editing, Associations & Validating Topology (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/utility-network/editing-utility-networks/,
references/core/networks/UtilityNetwork, references/core/networks/UnitIdentifierManager,
arcgis-utility-network-validate-network-topology / -validate-topology / -associations components*

> Last reviewed: 2026-10-12 (JS SDK 5.1 / Enterprise 12.1 / UN dataset v8)

**Version baseline / deprecation status (5.1):** the imperative widgets
`UtilityNetworkValidateTopology` and `UtilityNetworkAssociations` are
**deprecated since 5.0**. For validation, `<arcgis-utility-network-validate-topology>`
is itself **deprecated as of 5.1** in favor of the new
**`<arcgis-utility-network-validate-network-topology>`** (since 5.1).
`<arcgis-utility-network-associations>` (since 4.28) is not deprecated.

This is the complete "how do I actually edit a UN in a web app" story:
editing plain features, editing associations the easy way, and validating
topology afterward — the three steps that always go together (per Esri's own
guide: **"Validate should be done after edits are made, and before network
tracing"**).

## Editing plain UN features

Nothing UN-specific here beyond one consequence: **editing features on the
`FeatureLayer.applyEdits()` API generates dirty areas**, exactly as any Pro
edit would. The UN-awareness lives in the *effects* of the edit (dirty
areas, subsequent need to validate), not in a different editing API.

## Editing associations — the easy way (since 4.29)

Before 4.29, editing associations meant hand-building the raw association
attribute schema (see `rest-api/05-feature-service-associations-appendix.md`)
and calling `applyEdits` on the associations systemLayer directly. **Since
4.29, the `UtilityNetwork` class generates the edit payload for you:**

### `generateAddAssociations` / `canAddAssociation`
`generateAddAssociations(associations: Association[])` (**plural**, takes an
array, returns `ServiceEdits`, since 4.29). There is **no
`generateAddAssociation` (singular)** method. `Association` is imported from
`@arcgis/core/rest/networks/support/Association.js`.
```javascript
import Association from "@arcgis/core/rest/networks/support/Association.js";

const association = new Association({ /* associationType, fromNetworkElement, toNetworkElement */ });
const canAdd = await utilityNetwork.canAddAssociation(association); // Promise<Boolean>
// ... if true:
const generatedAddAssociation = utilityNetwork.generateAddAssociations([association]);
await featureService.applyEdits([generatedAddAssociation], {
  gdbVersion: "name.demo",
  globalIdUsed: false,
  honorSequenceOfEdits: false,
  usePreviousEditMoment: false,
  returnServiceEditsInSourceSR: false,
});
```
- **Always check `canAddAssociation()` first** in generated code — it
  validates whether the association would actually be legal (per the network
  rules table and association roles — see `pro-help/03-*.md` and `pro-help/04-*.md`)
  **before** attempting the write, giving immediate feedback instead of
  deferring discovery to the next `validateNetworkTopology` run.
- `featureService` here is the `FeatureService` class from the JS SDK's
  feature-service REST module; confirm its import path in the Esri docs for
  your version.

### `generateDeleteAssociations`
```javascript
const association = new Association({
  globalId: "{323FF251-A5FC-4665-97A3-D78615C3DD21}",
});
const generatedDeleteAssociations = utilityNetwork.generateDeleteAssociations([association]);

await featureService.applyEdits([generatedDeleteAssociations], {
  gdbVersion: "unadmin.testVersion",
  globalIdUsed: true, // MUST be true when deleting associations this way
  honorSequenceOfEdits: false,
  usePreviousEditMoment: false,
  returnServiceEditsInSourceSR: false,
});
```
**`globalIdUsed: true` is a hard requirement for deletes** via this method —
a common source of a confusing failure if copied from an add-association
example without changing this flag.

### Telecom unit-identifier edits: `UnitIdentifierManager` (since 4.34; combine/divide since 5.1)
`generateCombineNetworkElements` is **not** a `UtilityNetwork` method. It (and
`generateDivideNetworkElements`) lives on `UnitIdentifierManager`
(`@arcgis/core/networks/UnitIdentifierManager.js`), obtained with
`await utilityNetwork.getUnitIdentifierManager()`:
```javascript
const uim = await utilityNetwork.getUnitIdentifierManager();   // telecom networks only
const serviceEdits = uim.generateCombineNetworkElements([networkElementA, networkElementB, networkElementC]); // since 5.1
await featureService.applyEdits([serviceEdits]);
```
- `generateCombineNetworkElements(networkElements: NetworkElement[]): ServiceEdits`
  and `generateDivideNetworkElements(networkElement: NetworkElement, numUnits: number[]): ServiceEdits`
  are both **since 5.1** and not marked beta on the 5.1 reference page.
- Other `UnitIdentifierManager` methods: `query(containers)`,
  `reserve(container, firstUnit, lastUnit)`, `reset(containers)`,
  `resize(content, lastUnit)` — the JS counterparts of the REST
  `unitIdentifiers` operations (`rest-api/07-circuits-and-unit-identifiers-telecom.md`).
- Circuits: `await utilityNetwork.getCircuitManager(telecomDomainNetworkName)`
  returns a `CircuitManager` (`create`, `alter`, `queryCircuits`,
  `queryCircuitNames`, `verify`, `export`, `delete`, `submitVerifyJob`,
  `submitExportJob`). Telecom support is documented for Pro 3.7 / Enterprise 12.1
  / JS 5.1.
- Earlier notes said combined elements must have consecutive unit IDs, live in
  the same table and unit container, and share attribute values; that
  constraint was not re-confirmed in this review — verify against the Esri docs.

### `applyEdits` options relevant to all of the above
| Option | Meaning |
|---|---|
| `gdbVersion` | Target a specific named version rather than DEFAULT — same versioning concepts as `rest-api/04-version-management-validation-feature-service.md`. |
| `globalIdUsed` | Whether edits reference features by GlobalID (required `true` for association deletes, as noted). |
| `honorSequenceOfEdits` | Whether to preserve the exact order of multiple edits in the payload. |
| `usePreviousEditMoment` | Reuse the moment from a prior edit rather than establishing a new one — relevant for multi-step edit sequences that must appear atomic in time. |
| `returnServiceEditsInSourceSR` | Whether returned edit results use the source spatial reference rather than the service's. |

## Validating network topology from JS

### The `validateTopology` method (since 4.26, on both `Network` and `UtilityNetwork`)
```javascript
const validationResult = await utilityNetwork.validateTopology({
  validateArea: extent,          // an Extent object
  gdbVersion: "sde.DEFAULT",     // optional
  validationType: "rebuild",     // REST values: normal (default) | rebuild | forceRebuild (Enterprise 10.9+); check the JS ValidationType type for exact accepted strings
  validationSet: [
    { sourceId: 4134325151, globalIds: ["{7865BAA6-ED9C-4346-9F72-894A49E10C73}"] }
  ]
});
```
- `validateArea` scopes validation to an extent, mirroring the REST
  operation's required `extent` parameter
  (`rest-api/02-topology-and-subnetwork-management-operations.md`).
- `validationSet` scopes validation to **specific features/objects** (the
  JS-level equivalent of the REST features/objects filter introduced at
  Enterprise 10.9).
- The JS result is `ValidateNetworkTopologyResult` with `moment` (`Date`),
  `fullUpdate`, `validateErrorsCreated`, `discoveredSubnetworks`
  (`{ domain, tier, subnetwork }[]`, subnetworks marked dirty during the run —
  see the REST "hierarchical all-dirty tier" edge case), `exceededTransferLimit`
  and `serviceEdits`. The REST response's `dirtyAreaCount` is **not** a
  documented property of the JS result class.

### `submitTopologyValidationJob` — the async/job-based variant (since 4.26)
```javascript
const jobInfo = await utilityNetwork.submitTopologyValidationJob({
  validateArea: extent,
  validationType: "rebuild",
  validationSet: [ /* ... */ ]
});
```
Returns a `Promise<TopologyValidationJobInfo>` — use this for larger
validation operations where you want job-style progress tracking rather than
awaiting a single synchronous call, matching the REST API's
synchronous-vs-asynchronous validate option. This is the JS-side counterpart
to the REST `async=true`/`statusUrl` polling pattern
(`rest-api/06-asynchronous-operations-job-status.md`) and the C# SDK's
`Job<T>`/`UtilityNetworkValidationJob` model
(`pro-sdk/01-csharp-sdk-utility-network-api.md`) — all three represent the
same underlying server-side async job, just surfaced idiomatically per
platform. Unlike the C# job object, `submitTopologyValidationJob`'s returned
promise/info object does not require a separate explicit "start" call — the
JS API submits it as part of the call itself.
**Note**: `UtilityNetwork` also has **`submitTraceJob(props)`** (since 4.27,
returns `Promise<TraceJobInfo>`) alongside `trace()`. No dedicated JS job
methods were found for `updateSubnetwork`/`exportSubnetwork` — for those, the
async REST pattern (`rest-api/06-*.md`) is the fallback if a long-running call
risks timing out; verify the current JS API docs for the SDK version in use.
(Esri's editing guide text calls the validation job method
`submitTopologyJob`; the `UtilityNetwork` class reference names it
`submitTopologyValidationJob` — use the class reference name.)

### Validate-topology UI: widget (deprecated) -> components
Replacement chain (JS SDK 5.1):
1. `UtilityNetworkValidateTopology` widget (since 4.27) — **deprecated since 5.0**.
2. `<arcgis-utility-network-validate-topology>` component — **deprecated as of 5.1**.
3. **`<arcgis-utility-network-validate-network-topology>`** (since 5.1) — use
   this for new development.

```html
<script type="module">
  import "@arcgis/map-components/components/arcgis-utility-network-validate-network-topology";
</script>
<arcgis-map item-id="...">
  <arcgis-utility-network-validate-network-topology slot="top-right"></arcgis-utility-network-validate-network-topology>
</arcgis-map>
```
- Properties: `extentToValidate` (`"current"` default | `"entire"`),
  `utilityNetwork` (defaults to the first utility network in the map),
  `hideUtilityNetworkSelect`, `disabled`, `label`, `messageOverrides`,
  `referenceElement`, `view` (2D `MapView` only), readonly `state`, and
  `result` (`ValidateNetworkTopologyResult` of the latest successful run).
- Events: `arcgisReady`, `arcgisValidateNetworkTopologyStart` (call
  `event.preventDefault()` to cancel), `arcgisValidateNetworkTopologyEnd`.
- Requirements: utility network stored in the map, topology enabled, the
  required user type extension; no proxied or stored-credential feature
  services; validation can fail if there are no dirty areas in the extent or
  a version lock cannot be acquired.
- Legacy widget usage (4.27-4.x only):
  ```javascript
  import UtilityNetworkValidateTopology from "@arcgis/core/widgets/UtilityNetworkValidateTopology.js";
  const vntWidget = new UtilityNetworkValidateTopology({ view: myView, utilityNetwork: myUtilityNetwork });
  ```
- **Show the dirty areas layer on the map** if you want to see what is being
  validated — get its URL from
  `utilityNetwork.networkSystemLayers.dirtyAreasLayerUrl` (see
  `js-api/03-network-class-loading-and-definition.md`) and add it as an
  ordinary `FeatureLayer`:
  ```javascript
  const dirtyArea = new FeatureLayer({
    url: utilityNetwork.networkSystemLayers.dirtyAreasLayerUrl
  });
  await dirtyArea.load();
  map.add(dirtyArea);
  ```

## Associations UI: `UtilityNetworkAssociations` widget (deprecated) -> `<arcgis-utility-network-associations>`

The widget (`@arcgis/core/widgets/UtilityNetworkAssociations.js`, since 4.26)
is **deprecated since 5.0**. The component
`@arcgis/map-components/components/arcgis-utility-network-associations`
(since 4.28) is the current UI. Key component properties:
| Property | Notes |
|---|---|
| `showAssociationsEnabled` | Default `false`. Controls display when auto-refresh is on. |
| `autoRefreshAssociationsDisabled` | Default `false` (the widget's `autoRefreshAssociations` default was `true`; the boolean is inverted on the component). |
| `includeConnectivityAssociationsDisabled`, `includeStructuralAttachmentAssociationsDisabled` | Default `false`. |
| `connectivityAssociationsLineSymbol`, `structuralAttachmentAssociationsLineSymbol` | `SimpleLineSymbol` for the synthesized polylines. |
| `maxAllowableAssociations` | Default 250. |
| `utilityNetwork`, `view`, `referenceElement` | Connection to the network and map. |

## Practical guidance for Claude

1. **Always sequence generated code as: edit → validate → trace** — this
   ordering is explicit in Esri's own guide and is the single most important
   structural fact for any "how do I edit and then do X" JS request.
2. For association edits, default to `generateAddAssociations`/
   `generateDeleteAssociations` (both take an `Association[]`; 4.29+) rather than hand-building the raw
   association JSON schema — only fall back to the raw schema
   (`rest-api/05-*.md`) if the target app is stuck on an older SDK version.
3. Never omit `globalIdUsed: true` from a delete-association example —
   it's a documented hard requirement, not an optional tuning knob.
4. When adding topology validation to an app, mention that the **dirty areas
   layer isn't automatically part of the map** — it must be added explicitly
   via `networkSystemLayers.dirtyAreasLayerUrl`, whether or not a ready-made
   component is used.
5. On 5.x use the `arcgis-*` components, not the deprecated widgets; for
   validation prefer `arcgis-utility-network-validate-network-topology`.

## Sources
- https://developers.arcgis.com/javascript/latest/utility-network/editing-utility-networks/
- https://developers.arcgis.com/javascript/latest/references/core/networks/UtilityNetwork/
- https://developers.arcgis.com/javascript/latest/references/core/networks/UnitIdentifierManager/
- https://developers.arcgis.com/javascript/latest/utility-network/telecom-domain-network/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/Association/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/ValidateNetworkTopologyParameters/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/ValidateNetworkTopologyResult/
- https://developers.arcgis.com/javascript/latest/references/core/widgets/UtilityNetworkValidateTopology/
- https://developers.arcgis.com/javascript/latest/references/core/widgets/UtilityNetworkAssociations/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-validate-topology/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-validate-network-topology/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-associations/
- https://developers.arcgis.com/rest/services-reference/enterprise/validatenetworktopology-utiility-network-server/
- https://developers.arcgis.com/javascript/latest/release-notes/
