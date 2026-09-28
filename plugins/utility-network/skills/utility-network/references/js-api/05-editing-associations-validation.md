# Utility Network — JS API: Editing, Associations & Validating Topology (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/utility-network/editing-utility-networks/,
esri/networks/UtilityNetwork, esri/networks/Network, esri/widgets/UtilityNetworkValidateTopology,
esri/widgets/UtilityNetworkAssociations*

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

### `generateAddAssociation` / `canAddAssociation`
```javascript
const canAdd = await utilityNetwork.canAddAssociation(association); // Promise<Boolean>
// ... if true:
const generatedAddAssociation = utilityNetwork.generateAddAssociation(association);
await featureService.applyEdits([generatedAddAssociation], {
  gdbVersion: "name.demo",
  globalIdUsed: false,
  honorSequenceOfEdits: false,
  usePreviousEditMoment: false,
  returnServiceEditsInSourceSR: false,
});
```
- **Always check `canAddAssociation()` first** in generated code — it
  validates whether the association would actually be legal (per network
  rules and association roles — see `pro-help/03-*.md` and `pro-help/04-*.md`)
  **before** attempting the write, giving immediate feedback instead of
  deferring discovery to the next `validateNetworkTopology` run.

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

### `generateCombineNetworkElements` (telecom-only, beta, since 4.34)
```javascript
const serviceEdits = utilityNetwork.generateCombineNetworkElements([
  networkElementA, networkElementB, networkElementC,
]);
await featureService.applyEdits([serviceEdits]);
```
- Combines network elements in a **telecom domain network** — the elements
  being combined **must have consecutive unit IDs, exist in the same table
  and unit container, and share the same attribute values**. This is the
  JS-side counterpart to telecom unit-identifier management
  (`rest-api/02-topology-and-subnetwork-management-operations.md`'s "Unit
  Identifiers" resource). **Beta** — flag as such if it comes up.

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
  validationType: "rebuild",     // e.g. "normal" | "rebuild" (mirrors Pro's rebuild/forceRebuild options, Enterprise 10.9+)
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
- Response shape mirrors the REST `validateNetworkTopology` JSON response:
  `moment`, `fullUpdate`, `validateErrorsCreated`, `dirtyAreaCount`,
  and (matching the REST "hierarchical all-dirty tier" edge case documented
  in the REST file) a **`discoveredSubnetworks`** array of
  `{ domain, tier, subnetwork }` entries for subnetworks found dirty during
  the run.

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
**Note**: as of this writing, `trace`/`updateSubnetwork`/`exportSubnetwork`
don't have documented JS-specific "submit as job" method variants distinct
from `validateTopology`'s — for those operations in a JS app, the async REST
pattern (`rest-api/06-*.md`) is the fallback if a long-running call risks
timing out; verify current JS API docs for the SDK version in use in case
dedicated job methods have since been added.

### `UtilityNetworkValidateTopology` widget (since 4.27) — the ready-made UI
```javascript
import UtilityNetworkValidateTopology from "@arcgis/core/widgets/UtilityNetworkValidateTopology.js";

const vntWidget = new UtilityNetworkValidateTopology({
  view: myView,
  utilityNetwork: myUtilityNetwork // must be set explicitly, even if the map already has one loaded
});
```
- **The dirty areas layer must be explicitly added to the map** for the
  widget to visualize what it's validating — get its URL from
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
- Simplifies validating a specific `DirtyArea` interactively, analogous to
  how `UtilityNetworkTrace` simplifies tracing and `UtilityNetworkAssociations`
  simplifies association management.

## `UtilityNetworkAssociations` widget — additional properties

Beyond the basics in `01-javascript-sdk-utility-network.md`:
| Property | Notes |
|---|---|
| `showAssociationsEnabled` | Default `false`. When `autoRefreshAssociations` is also `true`, associations are re-shown automatically every time the map extent changes. |
| `structuralAttachmentAssociationsLineSymbol` | A `SimpleLineSymbol` (autocasts) controlling how the synthesized polyline geometry for **structural attachment** associations is drawn — separately configurable from connectivity/containment association symbology. |

## Practical guidance for Claude

1. **Always sequence generated code as: edit → validate → trace** — this
   ordering is explicit in Esri's own guide and is the single most important
   structural fact for any "how do I edit and then do X" JS request.
2. For association edits, default to `generateAddAssociation`/
   `generateDeleteAssociations` (4.29+) rather than hand-building the raw
   association JSON schema — only fall back to the raw schema
   (`rest-api/05-*.md`) if the target app is stuck on an older SDK version.
3. Never omit `globalIdUsed: true` from a delete-association example —
   it's a documented hard requirement, not an optional tuning knob.
4. When adding topology validation to an app, mention that the **dirty areas
   layer isn't automatically part of the map** — it must be added explicitly
   via `networkSystemLayers.dirtyAreasLayerUrl`, whether or not a ready-made
   widget is used.
