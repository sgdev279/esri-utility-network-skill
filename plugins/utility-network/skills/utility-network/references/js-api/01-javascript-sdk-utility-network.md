# Utility Network — ArcGIS Maps SDK for JavaScript (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/ (API reference + utility-network guide pages)*

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

// CDN (newer $arcgis loader pattern)
const TraceParameters = await $arcgis.import("@arcgis/core/rest/networks/support/TraceParameters.js");
```
Note the **two different top-level paths** depending on the class:
`@arcgis/core/networks/support/...` vs. `@arcgis/core/rest/networks/support/...`
— getting this wrong is a common source of "module not found" errors; always
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
2. **`UNTraceConfiguration`** — build a full trace configuration client-side,
   optionally **starting from** a shared named configuration and then
   customizing it:
   ```javascript
   const sharedNamedTraceConfigurations = utilityNetwork.sharedNamedTraceConfigurations;
   const traceConfiguration = sharedNamedTraceConfigurations.find(
     (sharedNamedTraceConfig) => sharedNamedTraceConfig.title === "Downstream Trace"
   );
   // ... customize traceConfiguration further, then hand off to TraceParameters
   ```

### `TraceParameters` — constructing the request
```javascript
const traceParameters = TraceParameters.fromJSON({
  traceConfigurationGlobalId: "{DF22DA8D-6EC0-408B-A8B2-E468EC7DC9BF}",
  moment: 1554214441244,
  gdbVersion: "SDE.DEFAULT",
  resultTypes: [
    { type: "elements", includeGeometry: false }
    // additional result type objects follow the same REST resultTypes
    // schema documented in the REST reference file
  ]
});
```
This is a **direct client-side mirror** of the REST `trace` operation's
request body — `traceConfigurationGlobalId`, `moment`, `gdbVersion`, and
`resultTypes` all map 1:1 to the REST parameters documented in
`rest-api/01-utility-network-server-and-trace.md`. When translating between
"how do I do this via REST" and "how do I do this in JS," this shared
vocabulary is the bridge, same as the Pro UI ↔ REST ↔ C# SDK bridge noted in
the REST reference file.

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
`traceResult.aggregatedGeometry` holds separate sub-properties per geometry
type (`multipoint`, presumably `polyline`/`polygon` siblings for edge/area
results) — check which sub-property is populated based on what geometry
types the trace's `resultTypes` requested, rather than assuming one fixed
shape.

## Associations

- **Conceptual note carried over from the Pro SDK**: associations are only
  *one* building block of network topology — features connected purely by
  **geometric coincidence** are **not** returned by an associations query.
  Don't treat an associations query as a complete connectivity picture; use a
  trace for that.
- **`SynthesizeAssociationGeometriesParameters`** — the JS class for
  configuring an associations query that needs *visual* geometry back (since
  associations themselves have no inherent spatial presence — see the Pro
  Help structure-network reference). Typical usage: load the utility network
  from the web map first (same pattern as above), then set parameters to
  filter to specific association types (e.g., structural attachment +
  connectivity) and cap the result count (example from Esri's guide: max 500
  associations within the current view extent).
- **`UtilityNetworkAssociations` widget**
  (`@arcgis/core/widgets/UtilityNetworkAssociations.js`) — a ready-made UI
  widget for browsing/managing associations without hand-building the
  query + rendering logic — worth suggesting when someone wants an
  associations *UI* rather than raw programmatic access.

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
