# Utility Network — ArcGIS Maps SDK for JavaScript (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/ (API reference + utility-network guide pages)*

> Last reviewed: 2026-10-12 (JS SDK 5.1 / Enterprise 12.1 / UN dataset v8)

**Version baseline.** The current ArcGIS Maps SDK for JavaScript release is
**5.1 (June 2026)**. In 5.0 the imperative UN widgets
(`UtilityNetworkTrace`, `UtilityNetworkAssociations`,
`UtilityNetworkValidateTopology`) were **deprecated** in favor of
`arcgis-*` map components; see `04-trace-results-and-widgets.md` and
`05-editing-associations-validation.md` for the replacement tag names.

## Critical disambiguation: THREE separate Esri "UtilityNetwork" APIs exist

Esri ships utility-network object models in **three unrelated SDKs** that
share similar class names (`UtilityNetwork`, `UtilityElement`,
`UtilityAssociation`, `TraceConfiguration`...) — search results and even
AI-generated code frequently blend them by accident. **Always confirm which
one the user is actually in** before giving code:

| SDK | Language(s) | Namespace / import | Used for |
|---|---|---|---|
| **ArcGIS Pro SDK** | C# | `ArcGIS.Core.Data.UtilityNetwork` | Pro Add-ins (see `pro-sdk/01-csharp-sdk-utility-network-api.md`) |
| **ArcGIS Maps SDK for Native Apps (Runtime SDK)** | .NET, Qt/QML/C++, Kotlin, Swift | `Esri.ArcGISRuntime.UtilityNetworks` (or per-language equivalent) | Native/mobile field apps |
| **ArcGIS Maps SDK for JavaScript** | JavaScript/TypeScript | `@arcgis/core/networks/*`, `@arcgis/core/rest/networks/*` | **Web apps — this file's actual subject** |

This file covers **only** the JavaScript one. If a code sample uses
`Esri.ArcGISRuntime.*` or `ArcGIS.Core.Data.*`, it is **not** JS API code even
if the class names look identical.

## Import patterns

```javascript
// ESM
import TraceParameters from "@arcgis/core/rest/networks/support/TraceParameters.js";
import TraceConfiguration from "@arcgis/core/networks/support/TraceConfiguration.js";
import UNTraceConfiguration from "@arcgis/core/networks/support/UNTraceConfiguration.js";
import Association from "@arcgis/core/rest/networks/support/Association.js";

// CDN (newer $arcgis loader pattern)
const TraceParameters = await $arcgis.import("@arcgis/core/rest/networks/support/TraceParameters.js");
```
Note the **different top-level paths** depending on the class
(`@arcgis/core/networks/...`, `@arcgis/core/networks/support/...`, and
`@arcgis/core/rest/networks/support/...`) — getting this wrong is a common source of "module not found" errors; always
check the specific class's own reference page for its exact import path
rather than assuming a uniform `@arcgis/core/networks/...` prefix.

## Loading a `UtilityNetwork` from a web map (the standard entry pattern)

```javascript
const viewElement = document.querySelector("arcgis-map");
viewElement.addEventListener("arcgisViewReadyChange", () => {
  // Check if the WebMap contains utility networks at all
  if (webMap.utilityNetworks.length > 0) {
    // Assign the utility network at index 0
    utilityNetwork = webMap.utilityNetworks.getItemAt(0);

    // Triggers the loading of the UtilityNetwork instance
    utilityNetwork.load().then(() => {
      // safe to use utilityNetwork.sharedNamedTraceConfigurations, etc. here
    });
  }
});
```
- `webMap.utilityNetworks` is a **collection** — a web map can reference more
  than one utility network; **always check `.length` and pick the right item**
  rather than assuming index 0 in a real app (index 0 is fine for a quick
  demo, wrong for a production app with multiple networks in one map).
- `.load()` is asynchronous and **must complete** before schema-dependent
  properties (like `sharedNamedTraceConfigurations`) are populated — this
  mirrors the `ILoadable`/loadable pattern used across Esri's other SDKs.

## Tracing

### Two named-configuration levels
1. **`sharedNamedTraceConfigurations`** — trace configurations shared via the
   *service* (created via the REST `traceConfigurations/create` operation
   documented in the REST reference file) — available directly on the loaded
   `utilityNetwork` object:
   ```javascript
   utilityNetwork.sharedNamedTraceConfigurations.forEach((namedTraceConfig) => {
     console.log(namedTraceConfig.globalId + " - " + namedTraceConfig.title);
   });
   ```
2. **`UNTraceConfiguration`** (`@arcgis/core/networks/support/UNTraceConfiguration.js`)
   — build a full trace configuration client-side,
   optionally **starting from** a shared named configuration and then
   customizing it:
   ```javascript
   const sharedNamedTraceConfigurations = utilityNetwork.sharedNamedTraceConfigurations;
   const namedConfig = sharedNamedTraceConfigurations.find(
     (sharedNamedTraceConfig) => sharedNamedTraceConfig.title === "Downstream Trace"
   );
   // namedConfig.traceConfiguration (full definition) is only available once the
   // utility network is fully loaded. Customize a copy, then hand it to
   // TraceParameters.traceConfiguration (an UNTraceConfiguration), or just pass
   // namedConfig.globalId as namedTraceConfigurationGlobalId.
   ```

### `TraceParameters` — constructing the request
```javascript
const traceParameters = new TraceParameters({
  namedTraceConfigurationGlobalId: "{DF22DA8D-6EC0-408B-A8B2-E468EC7DC9BF}",
  traceLocations: [ /* TraceLocation objects: starting points and barriers */ ],
  gdbVersion: "SDE.DEFAULT",
  moment: new Date(),            // Date (autocast); branch-versioned data only
  resultTypes: [
    { type: "elements", includeGeometry: false }
    // additional result type objects follow the same REST resultTypes
    // schema documented in the REST reference file
  ]
});
const result = await utilityNetwork.trace(traceParameters);   // since 4.27
```
`TraceParameters` (since 4.20) has these documented properties:
`gdbVersion`, `moment` (a `Date`, not epoch milliseconds),
`namedTraceConfigurationGlobalId`, `outSpatialReference`, `resultTypes`,
`traceConfiguration` (`UNTraceConfiguration`), `traceLocations` and
`traceType`. These correspond conceptually to the REST `trace` request body
in `rest-api/01-utility-network-server-and-trace.md`, but **the JS property
names are not always the REST names** (e.g. the named-configuration
property is `namedTraceConfigurationGlobalId`, and `moment` is a `Date`).
Use the JS class reference for exact names rather than assuming a 1:1 REST
mapping; `UtilityNetwork.trace()` / `submitTraceJob()` (both since 4.27)
accept a `TraceProperties` object (`namedTraceConfigurationGlobalId`,
`traceLocations`, `outSpatialReference`, `traceConfiguration`,
`resultTypes`, `traceType`).

### Handling trace results (aggregated geometry example)
```javascript
if (traceResult.aggregatedGeometry.multipoint) {
  const multipointGraphic = new Graphic({
    geometry: {
      type: "multipoint",
      points: traceResult.aggregatedGeometry.multipoint.points,
      spatialReference: utilityNetwork.spatialReference
    },
    symbol: /* ... */
  });
}
```
`traceResult.aggregatedGeometry` (`AggregatedGeometry`) holds separate
sub-properties per geometry type: `multipoint` (points), `line` (polylines)
and `polygon` (polygons; usually outside connectivity topology but can appear
via containment associations) — check which sub-property is populated based on what geometry
types the trace's `resultTypes` requested, rather than assuming one fixed
shape.

## Associations

- **Conceptual note carried over from the Pro SDK**: associations are only
  *one* building block of network topology — features connected purely by
  **geometric coincidence** are **not** returned by an associations query.
  Don't treat an associations query as a complete connectivity picture; use a
  trace for that.
- **`synthesizeAssociationGeometries()`** on `UtilityNetwork` (since 4.28) —
  returns *visual* geometry for associations (which have no inherent spatial
  presence — see the Pro Help structure-network reference). It takes a
  `SynthesizeAssociationGeometriesProperties` object: `returnAttachmentAssociations`,
  `returnConnectivityAssociations`, `returnContainmentAssociations`, `extent`,
  `maxGeometryCount` and `outSpatialReference`. The equivalent parameter class
  `SynthesizeAssociationGeometriesParameters`
  (`@arcgis/core/rest/networks/support/SynthesizeAssociationGeometriesParameters.js`,
  since 4.20) is still documented. Load the utility network from the web map
  first (same pattern as above).
- **Associations UI**: the imperative `UtilityNetworkAssociations` widget
  (`@arcgis/core/widgets/UtilityNetworkAssociations.js`) is **deprecated since
  5.0**; use the **`<arcgis-utility-network-associations>`** component
  (`@arcgis/map-components/components/arcgis-utility-network-associations`,
  since 4.28, not deprecated as of 5.1) — worth suggesting when someone wants
  an associations *UI* rather than raw programmatic access.

## Practical guidance for Claude

1. **Always ask/confirm which SDK** the user means when they say "the
   UtilityNetwork class" — JS, Pro SDK, and Runtime SDK are three different
   things with confusingly identical-sounding type names.
2. When writing JS trace code, get the **exact import path** right per class
   (`networks/support/` vs `rest/networks/support/`) rather than guessing a
   single convention.
3. Remember `webMap.utilityNetworks` is a **collection** — don't hardcode
   index 0 in production-quality guidance without flagging that assumption.
4. When bridging "the user configured a trace in Pro" to "now they want it in
   a web app," the **named trace configuration** (shared via REST, consumed
   via `sharedNamedTraceConfigurations` in JS) is the correct mechanism —
   not re-building the whole `traceConfiguration` JSON by hand in JS.
5. New 5.x apps should use the `arcgis-*` UN components, not the deprecated
   imperative widgets (see files 04 and 05).

## Sources
- https://developers.arcgis.com/javascript/latest/release-notes/
- https://developers.arcgis.com/javascript/latest/references/core/networks/UtilityNetwork/
- https://developers.arcgis.com/javascript/latest/references/core/networks/support/NamedTraceConfiguration/
- https://developers.arcgis.com/javascript/latest/references/core/networks/support/TraceConfiguration/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/TraceParameters/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/Association/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/AggregatedGeometry/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/SynthesizeAssociationGeometriesParameters/
- https://developers.arcgis.com/javascript/latest/references/core/WebMap/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-associations/
- https://developers.arcgis.com/javascript/latest/references/core/widgets/UtilityNetworkAssociations/

