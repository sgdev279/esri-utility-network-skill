# Utility Network — JS API: Trace Results & Tracing Widgets (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/api-reference/ (esri/rest/networks/support/TraceResult,
esri/rest/networks/support/FunctionResult, esri/widgets/UtilityNetworkTrace,
esri/widgets/UtilityNetworkTraceAnalysis)*

This expands the tracing coverage in `01-javascript-sdk-utility-network.md`
with the full result-object shape and the two ready-made tracing widgets —
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
| `circuits` | `CircuitTraceResult[] \| null \| undefined` | Telecom-specific circuit trace results. |

Note: **`TelecomNetworkElement`** as a possible `elements` member type is
explicitly documented as **beta / reserved for future use** in a telecom
domain network — flag this as not-yet-stable if it comes up.

## `FunctionResult` — the aggregate-function output object

```javascript
import FunctionResult from "@arcgis/core/rest/networks/support/FunctionResult.js";
```
| Property | Type | Notes |
|---|---|---|
| `functionType` | String | One of `"add" \| "subtract" \| "average" \| "count" \| "min" \| "max"` — directly mirrors the Pro Help function-barrier options (`pro-help/05-tracing.md`) and the C# SDK's function classes (`Add`, etc. in `pro-sdk/01-*.md`). |
| `networkAttributeName` | String | Which network attribute the function was computed over. |
| `result` | Number | The actual computed value (e.g., total accumulated shape length, count of features, etc.). |

This is the JS-side answer to "how do I get the sum/count/average my trace
was configured to compute" — read it off `traceResult.globalFunctionResults`,
matching entries by `networkAttributeName`/`functionType` if a trace
configured multiple functions at once.

## `UtilityNetworkTrace` widget — the ready-made tracing UI

```javascript
import UtilityNetworkTrace from "@arcgis/core/widgets/UtilityNetworkTrace.js";
```
Since 4.22. **This widget is often the right answer to "how do I add tracing
to my UN web app"** — it can replace most of the manual
`TraceParameters`/`TraceConfiguration` code for interactive use cases.

### Requirements / hard constraints (check these first when troubleshooting)
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

### Basic usage
```javascript
const utilityNetworkTrace = new UtilityNetworkTrace({ view });
view.ui.add(utilityNetworkTrace, "top-right");
```

### Setting flags (starting points/barriers) programmatically
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
  interactively, or supplied programmatically as shown — the widget supports
  **nonspatial data** as flags too (e.g., a nonspatial junction object) and
  lets users examine nonspatial data within results.
- `enableResultArea` (since 4.27) — shows a convex hull or buffer around
  results.
- `traceResults` (readonly, since 4.34) — stores completed trace results as
  `TraceResultExtend[]` for programmatic inspection after the widget runs.
- `showSelectionAttributes: true` — organizes the resulting feature selection
  into a browsable list by **asset group → asset type → feature**, useful for
  large result sets.
- `gdbVersion` — run traces against a specific named version rather than
  DEFAULT.

## `UtilityNetworkTraceAnalysis` — the newer component-based alternative
```javascript
import UtilityNetworkTraceAnalysisViewModel from
  "@arcgis/core/widgets/UtilityNetworkTraceAnalysis/UtilityNetworkTraceAnalysisViewModel.js";
```
Since 4.32. A more decoupled, ViewModel-driven building block (vs. the
all-in-one `UtilityNetworkTrace` widget) with:
- `executeNamedTraceConfiguration(parameters: NamedTraceConfigurationParameters): Promise<TraceResult>`
- `executeTraceConfiguration(parameters: TraceConfigurationParameters): Promise<TraceResult>`
- `state`, `executionError`, `loadError` — standard Esri ViewModel state
  pattern for building custom UI around the same underlying trace-execution
  logic the `UtilityNetworkTrace` widget uses internally.

**When to pick which**: use `UtilityNetworkTrace` for a fast, fully-built
tracing panel; use `UtilityNetworkTraceAnalysis`'s ViewModel when the app
needs **custom UI** around trace execution (e.g., embedded in a larger
custom workflow) but still wants Esri's tested execution logic rather than
hand-rolling `TraceParameters` calls from scratch.

## Practical guidance for Claude

1. Before writing manual tracing code, ask whether the **`UtilityNetworkTrace`
   widget** already covers the need — it's frequently the faster, more
   correct answer for interactive apps.
2. Always check `traceResult.warnings` in generated code samples, not just
   the primary result arrays — silent partial-success is a real failure
   mode here.
3. When a trace "returns nothing" or "ignores my starting point," check
   `startingPointsIgnored` before assuming the trace configuration itself is
   wrong.
4. Remind users of the **topology-enabled + validated** precondition any
   time trace results look wrong or incomplete in a web app — this is the
   most common root cause reported in practice (per Esri Community threads).
