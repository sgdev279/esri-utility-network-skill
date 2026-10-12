# Utility Network — JS API: Trace Results & Tracing Widgets/Components (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/references/ (core/rest/networks/support/TraceResult,
FunctionResult, core/widgets/UtilityNetworkTrace, core/networks/UtilityNetworkTraceAnalysis,
map-components arcgis-utility-network-trace / -trace-analysis)*

> Last reviewed: 2026-10-12 (JS SDK 5.1 / Enterprise 12.1 / UN dataset v8)

**Version baseline / deprecation status (5.1):**
- `UtilityNetworkTrace` widget class — **deprecated since 5.0**.
- `<arcgis-utility-network-trace>` component (since 4.28) — **deprecated since 5.0**;
  Esri names `<arcgis-utility-network-trace-analysis>` (since 5.0) the preferred
  component for all new development.
- `UtilityNetworkTraceAnalysis` core class (`@arcgis/core/networks/UtilityNetworkTraceAnalysis.js`,
  since 5.0) provides the logic for the trace-analysis component.

This expands the tracing coverage in `01-javascript-sdk-utility-network.md`
with the full result-object shape and the ready-made tracing UI options —
which, for many apps, replace hand-writing `TraceParameters`/`TraceConfiguration`
code almost entirely.

## `TraceResult` — full property surface

```javascript
import TraceResult from "@arcgis/core/rest/networks/support/TraceResult.js";
```
Since 4.20. Inheritance: `TraceResult → Accessor`.

| Property | Type | Notes |
|---|---|---|
| `elements` | `NetworkElement[]` | Raw network elements (the topology's own graph representation) — populated only if `elements` is in the trace's `resultTypes`. |
| `aggregatedGeometry` | `AggregatedGeometry \| null \| undefined` | Only includes geometry for features whose asset group/asset type is included in the trace output; populated only if `aggregatedGeometry` is in `resultTypes`. |
| `globalFunctionResults` | `FunctionResult[]` | See below — populated when the trace configuration defines function barriers/propagators that produce an aggregate value. |
| `warnings` | `String[]` | Any warnings the trace operation encountered — **always check this**, even on an apparently successful trace; a trace can "succeed" while still reporting warnings about edge cases it hit. |
| `kFeaturesForKNNFound` | Boolean (default `false`) | Specific to the K-Nearest-Neighbors filter (the "nearest" trace filter) — `true` if any neighbors were actually found. |
| `startingPointsIgnored` | Boolean (default `false`) | `true` if the trace operation ignored the supplied starting points — a useful diagnostic when a trace returns unexpectedly empty/different results. |
| `paths` | `CircuitPath[] \| null \| undefined` (since 4.34) | Paths returned by a **path trace**. |
| `circuits` | `CircuitTraceResult[] \| null \| undefined` (since 4.34) | Telecom-specific circuit trace results. |

Note: **`TelecomNetworkElement`** (`@arcgis/core/rest/networks/support/TelecomNetworkElement.js`,
since 4.34) is a `NetworkElement` subclass "reserved for telecom domain
networks"; it always has a null `terminalId` because telecom networks do not
use terminals. The 5.1 reference page does not mark it beta.

## `FunctionResult` — the aggregate-function output object

```javascript
import FunctionResult from "@arcgis/core/rest/networks/support/FunctionResult.js";
```
| Property | Type | Notes |
|---|---|---|
| `functionName` | String (since 5.1) | Name of the function, when the configuration names it. |
| `functionType` | String | One of `"add" \| "subtract" \| "average" \| "count" \| "min" \| "max"` — directly mirrors the Pro Help function-barrier options (`pro-help/05-tracing.md`) and the C# SDK's function classes (`Add`, etc. in `pro-sdk/01-*.md`). |
| `networkAttributeName` | String | Which network attribute the function was computed over. |
| `result` | Number | The actual computed value (e.g., total accumulated shape length, count of features, etc.). |

This is the JS-side answer to "how do I get the sum/count/average my trace
was configured to compute" — read it off `traceResult.globalFunctionResults`,
matching entries by `networkAttributeName`/`functionType` if a trace
configured multiple functions at once.

## `UtilityNetworkTrace` widget — DEPRECATED since 5.0

```javascript
import UtilityNetworkTrace from "@arcgis/core/widgets/UtilityNetworkTrace.js";
```
Since 4.22; **deprecated since 5.0** (Esri recommends the Utility Network
Trace Analysis component instead). The code below is correct for 4.x apps and
still documents the concepts, but **do not start new 5.x apps with it**.

### Requirements / hard constraints (apply to the widget and both components)
- Requires a **WebMap published with a utility network AND shared named
  trace configurations** (named trace configs available starting Enterprise
  10.9 — see `rest-api/01-utility-network-server-and-trace.md`).
- **Cannot support proxied feature services or feature services using stored
  credentials.**
- **Network topology must be enabled**, and the area being traced must have
  been **validated** to reflect the latest edits — trace results over dirty
  areas are **not guaranteed accurate**. This is the JS-app-level restatement
  of the Pro Help dirty-area/validation material
  (`pro-help/04-associations-editing-errors.md`,
  `pro-help/06-administration-subnetworks-topology-versioning.md`) — always
  mention validation status when a JS trace looks wrong.

### Basic usage (4.x widget)
```javascript
const utilityNetworkTrace = new UtilityNetworkTrace({ view });
view.ui.add(utilityNetworkTrace, "top-right");
```

### Setting flags (starting points/barriers) programmatically (4.x widget)
```javascript
const unt = new UtilityNetworkTrace({
  view: view,
  showSelectionAttributes: true,
  selectOnComplete: true,
  showGraphicsOnComplete: true,
  selectedTraces: ["{E8D545B8-596D-4656-BF5E-16C1D7CBEC9B}"], // named trace config globalId(s)
  flags: [
    { type: "starting-point", mapPoint: { spatialReference: { wkid: 102100 }, x: -9814829.17, y: 5127094.10 } },
    { type: "barrier",        mapPoint: { spatialReference: { wkid: 102100 }, x: -9814828.45, y: 5127089.09 } }
  ]
});
```
- `selectedTraces` — pass named trace configuration **globalId(s)** to
  preselect which trace(s) run; the widget also exposes a "Trace types"
  dropdown for interactive selection, and can run **multiple traces
  concurrently**.
- `flags` — starting points and barriers can be set by **clicking the view**
  interactively, or supplied programmatically as shown.
- `enableResultArea` (since 4.27) — shows a convex hull or buffer around
  results.
- `traceResults` (readonly, since 4.34) — stores completed trace results as
  `TraceResultExtend[]` for programmatic inspection after the widget runs.
- `showSelectionAttributes: true` — organizes the resulting feature selection
  into a browsable list by **asset group → asset type → feature**.
- (An earlier version of this file listed a `gdbVersion` widget property;
  it does not appear in the 5.1 `UtilityNetworkTrace` reference. To trace a
  named version, use `TraceParameters.gdbVersion` / the programmatic API.)

## `<arcgis-utility-network-trace>` component — DEPRECATED since 5.0

`@arcgis/map-components/components/arcgis-utility-network-trace` (since 4.28).
Properties follow the widget but with inverted boolean names:
`selectOnCompleteDisabled`, `showGraphicsOnCompleteDisabled`,
`showSelectionAttributesDisabled`, plus `flags`, `selectedTraces`,
`enableResultArea`, `traceResults`, `view`, `state`; methods
`checkCanTrace()`, `confirmReset()`, `destroy()`. Deprecated in favor of the
component below.

## `<arcgis-utility-network-trace-analysis>` — the current tracing component (since 5.0)

```html
<script type="module">
  import "@arcgis/map-components/components/arcgis-utility-network-trace-analysis";
</script>
<arcgis-map item-id="...">
  <arcgis-utility-network-trace-analysis slot="top-right"></arcgis-utility-network-trace-analysis>
</arcgis-map>
```
- Runs traces and displays results; **trace locations are set by selecting
  features on the view**, and the trace and utility network must be stored in
  the map.
- Properties: `aggregatedGeometryGraphicsColor`, `disableHighlightFeatureResults`,
  `hideFeatureResults`, `label`, `messageOverrides`, `referenceElement`,
  `state` (readonly), `traceResultFeatures` (readonly), `view`.
- Events: `arcgisHideGraphicsChange`, `arcgisReady`, `arcgisTraceResultClear`,
  `arcgisTraceResultFeaturesReady`. Method: `destroy()`.
- The `shortest-path` trace type is **deprecated as of Pro 3.7 / Enterprise
  12.1**; the component page recommends the `path` trace instead.

## `UtilityNetworkTraceAnalysis` — core class behind the component (since 5.0)
```javascript
import UtilityNetworkTraceAnalysis from "@arcgis/core/networks/UtilityNetworkTraceAnalysis.js";
```
`UtilityNetworkTraceAnalysis → Accessor`, "provides the logic for the
UtilityNetworkTraceAnalysis component". Not marked deprecated or beta.
- `executeNamedTraceConfiguration(parameters: NamedTraceConfigurationParameters): Promise<TraceResult>` (parameter type since 4.32)
- `executeTraceConfiguration(parameters: TraceConfigurationParameters): Promise<TraceResult>` (parameter type since 4.34)
- Properties: `utilityNetwork`, `view` (2D `MapView`), `state`
  (`"disabled" | "executing" | "loading" | "ready"`), `executionError`
  (`"trace-error"`), `loadError` (`"no-user-type-extension" | "no-utility-network" | "no-view" | "sceneView-not-supported" | "utility-network-load-failed"`).
- (Before 5.0 this logic was exposed as a widgets-folder ViewModel since 4.32;
  verify the old import path against the Esri docs for the version you are on
  before using it.)

**When to pick which (5.x)**: use `<arcgis-utility-network-trace-analysis>` for
a fast, fully-built tracing panel; use `UtilityNetworkTraceAnalysis` (or plain
`utilityNetwork.trace()`) when the app needs **custom UI** around trace
execution. On 4.x, use the `UtilityNetworkTrace` widget.

## Practical guidance for Claude

1. Before writing manual tracing code, ask whether the
   **`arcgis-utility-network-trace-analysis` component** (5.x; the
   `UtilityNetworkTrace` widget on 4.x) already covers the need — it's
   frequently the faster, more correct answer for interactive apps.
2. Always check `traceResult.warnings` in generated code samples, not just
   the primary result arrays — silent partial-success is a real failure
   mode here.
3. When a trace "returns nothing" or "ignores my starting point," check
   `startingPointsIgnored` before assuming the trace configuration itself is
   wrong.
4. Remind users of the **topology-enabled + validated** precondition any
   time trace results look wrong or incomplete in a web app — this is the
   most common root cause reported in practice (per Esri Community threads).

## Sources
- https://developers.arcgis.com/javascript/latest/references/core/widgets/UtilityNetworkTrace/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-trace/
- https://developers.arcgis.com/javascript/latest/references/map-components/components/arcgis-utility-network-trace-analysis/
- https://developers.arcgis.com/javascript/latest/references/core/networks/UtilityNetworkTraceAnalysis/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/TraceResult/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/FunctionResult/
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/TelecomNetworkElement/
- https://developers.arcgis.com/javascript/latest/release-notes/
