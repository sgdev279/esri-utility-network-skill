# Utility Network — Tracing (Deep Reference)
*Source: ArcGIS Pro Help + Tool Reference, "Utility Network" book*

> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Tracing is the single most heavily used analytic capability of a utility
network, and it's the feature most likely to come up across all three other
doc sources too (REST `Trace` operation, JS API `TraceParameters` /
`TraceConfiguration`) — so this file is deliberately the most detailed of the
Pro Help set.

## How tracing works (mental model)

A trace starts at one or more **starting points** (or at the subnetwork
controller(s) of a named subnetwork) and spans **outward radially**, following
paths of connected/associated features, until it reaches an **end location** —
either a barrier or the natural end of a path. Results can be returned as:
- A **selection set** in the map,
- **Aggregated geometry** in multipart feature classes,
- A **connectivity graph** (for building custom representations elsewhere),
- Information written to a **.json file**.

**Connectivity vs. traversability** — the two mechanisms a trace can follow:
- **Connectivity** — purely structural: is there a path of connected/associated
  features at all?
- **Traversability** — connectivity *plus* configuration constraints (barriers,
  categories, attribute filters) that determine whether the trace is actually
  allowed to continue through a given feature, even if it's structurally
  connected.

## Trace types
Trace types of the `Trace` tool in Pro 3.7 (all are run from the **Trace** tool
or the Trace gallery on the Utility Network tab; starting points and barriers
are set in the **Trace** pane):

- **Connected** (default) — spans outward from the starting point(s) along
  connected features until a barrier or the end of a path, regardless of flow
  direction. Works with traditional and telecom domain networks; does not use
  the subnetwork definition.
- **Subnetwork** — finds all features in a subnetwork from starting points or a
  **Subnetwork Name** (no explicit starting points needed when a name is given).
  Traditional domain networks only.
- **Subnetwork controllers** — locates the subnetwork controllers for the
  traceable subnetwork (returned as a selection set by default). Traditional
  domain networks only.
- **Upstream** / **Downstream** — find features upstream or downstream of a
  location. Flow direction comes from the subnetwork controllers (traditional
  domain networks only) or, when **Use Digitized Direction** is checked, from
  digitized line direction, which also works with telecom domain networks
  (UN version 7+; Enterprise 11.3+).
- **Loops** — starts from a single starting point, spans outward by
  connectivity and returns loops, i.e. areas where flow direction is ambiguous
  (expected in mesh networks, usually an error in radial ones). Traditional and
  telecom.
- **Isolation** — finds the isolating features (typically operable devices such
  as valves or switches) needed to isolate an area. Traditional domain networks
  only; uses the tier's subnetwork definition. **A filter barrier must be
  defined** in the trace configuration. The isolating features are returned as
  the result selection set; **Include Isolated Features** adds the traversable
  features that lead to them.
- **Path** *(new in Pro 3.7; enterprise geodatabases need ArcGIS Enterprise
  12.1+)* — finds valid paths between start and stop locations, or the shortest
  path when a **Shortest Path Network Attribute Name** is given with
  **Num Paths** = 1. Traditional and telecom. Runs on connectivity alone
  (terminal paths are respected). Stopping points are required for traditional
  domain networks and optional for telecom ones.
- **Shortest path** — between two starting points using a numeric network
  attribute (e.g. shape length). **Deprecated with ArcGIS Pro 3.7 and ArcGIS
  Enterprise 12.1**; use the Path trace instead.
- **Circuit** — returns a circuit definition (physical or virtual circuits) from
  a **Circuit Name** or starting points. **Telecom domain networks only**;
  enterprise geodatabases need Enterprise 12.1+.

### Which options belong to which trace type (verified against Pro 3.7 docs)

| Option | Applies to |
|---|---|
| **Num Paths** (default 1) | **Path** trace only |
| **Max Hops** (default 100; max edge-to-edge hops, excluding the starting point; terminal devices count as 2) | **Path**; Esri's circuit page also lists Max Hops (default 100) for **Circuit** |
| **Infer Connectivity** (default off) | **Path** trace in **telecom** domain networks only (traverses containment associations when explicit connectivity is missing) |
| **Shortest Path Network Attribute Name** | **Path** (optional) and the deprecated **Shortest path** (required) |
| **Allow Indeterminate Flow** (default on; UN version 5+) | **Upstream**, **Downstream**, **Isolation** only |
| **Use Digitized Direction** (UN version 7+; Enterprise 11.3+) | **Upstream**, **Downstream** |
| **Subtract** function barrier | Not supported by **Subnetwork controllers** and **Loops** |

Num Paths and Max Hops need ArcGIS Enterprise 12.1+ on enterprise
geodatabases. If you cannot confirm an option for a trace type not in this
table, verify against the Esri docs for your version.

## Configuring a trace — traversability

Configured in the **Traversability** section of the Trace tool/pane:
- **Condition barriers** — expressions built on **network attributes** or
  **network categories** that define where a trace should stop (e.g., "stop
  when `LIFECYCLESTATUS` ≠ In Service", or "stop at a feature tagged with the
  Protective network category").
- **Function barriers** — stop the trace when a running calculation crosses a
  threshold. Function options: **Minimum**, **Maximum**, **Add** (sum),
  **Average**, **Count**, **Subtract**. (Subnetwork controllers and loops trace
  types do **not** support the Subtract function.) Example: starting value 20,
  next feature value 30 — Add accumulates, Subtract nets the difference — used
  for things like cumulative load calculations that should halt the trace once
  a capacity threshold is crossed.
- **Allow Indeterminate Flow** — whether features with indeterminate flow are
  traced; only applicable to upstream, downstream and isolation traces
  (default checked, UN version 5+).
- **Infer Connectivity** — not a general traversability toggle: it applies to
  the **Path** trace in **telecom** domain networks only (see the table
  above).
- **When tracing across multiple tiers**, the trace configuration (traversability
  scope, condition barriers, function barriers, propagators) is **reloaded per
  tier** as the trace crosses from one tier into the next — configuration is
  *not* globally fixed for the whole trace if it spans tiers.

## Configuring a trace — what's returned

### Num Paths / Max Hops
**Num Paths** is honored only by the **Path** trace type and bounds how many
paths are returned per start/stop pair (fewest hops first; with Num Paths above
1 the paths are not ordered by length, though the first is the shortest).
**Max Hops** bounds the number of edge-to-edge hops in a path and is documented
for **Path** (and listed on Esri's circuit page for **Circuit**). Neither
applies to Connected, Subnetwork, Upstream, Downstream, Loops or Isolation.

### Output filters (screen every encountered feature)
- **Output Asset Types** — restrict results to specific asset type(s).
- **Output Conditions** — expressions on **network categories** or **network
  attributes**, evaluated per-feature as it's encountered (e.g., "return only
  features with the Isolating network category").
- **Practical technique** (from Esri Community; not in the Esri help, so
  treat as community guidance): to make a non-Isolation trace type (e.g.,
  Downstream) return **only** the features that would have stopped it as
  barriers, **repeat the condition barrier expression as an output condition**
  — this filters the result set down to just the barrier-matching features.
  The Isolation trace returns its isolating features as the result selection
  by default. Verify against the Esri docs for your version whether a
  dedicated "return only barriers" option now exists.

### Include containers, content, structures, and barriers
By default, a trace does **not** return containers, their content, or
structures — only "active" domain-network features. Configurable inclusion
options:
- **Include Barrier Features** (default: checked) — include the barrier
  feature(s) that stopped the trace in the result (Esri: traversability
  barriers are optional even if preset in the subnetwork definition). Covers
  explicit feature barriers (set in the Trace pane) *and* dynamically
  configured barriers (condition, function, filter, filter-function).
  - **Gotcha**: when a barrier sits on an edge feature with **midspan
    connectivity** and this option is **unchecked**, results can look
    unexpected — because if *any part* of a feature is returned by the trace,
    the **entire feature** is selected/displayed, not just the traced portion.
  - For subnetwork-based trace types, this option is also influenced by the
    **subnetwork trace configuration** loaded when a Tier is specified — i.e.
    the tier's own subnetwork definition can force barrier inclusion behavior.
- **Ignore Barriers At Starting Points** — whether dynamic barriers in the
  trace configuration are ignored for the starting points, so a trace can
  begin even if the starting feature is itself configured as a barrier.

### Subnetwork-based trace output
For subnetwork (and subnetwork-controller) traces, if **propagated values**
are needed in the output, use the **Features** result type with **Include
propagated values** checked — writes a `propagatedValues` block per traversed
feature into the output `.json`.

## `Trace` geoprocessing tool — summary

> Returns network features in a utility network based on connectivity or
> traversability from specified starting points.

- `in_utility_network` — the target utility network.
- Barrier condition components: `Name` (any defined network attribute, or
  `Category` to use a network category) + comparison + value.
- Results can be **propagated** to another map, a network diagram view, or
  chained as input to another tool/trace.
- Trace results can be exported/analyzed and are foundational to load-summary
  reporting (e.g., "how many customers are downstream of this point")
  discussed in the core-concepts file.

## Inspecting an active trace configuration via arcpy Describe

For a **subnetwork's Update Subnetwork trace configuration**, `arcpy.Describe`
on a utility network exposes an `updateSubnetworkTraceConfiguration` object
with (partial list, confirmed from live docs):
- `conditionBarriers` — object exposing the configured condition barrier set.
- `diagramTemplateName` — the diagram template tied to this trace
  configuration (links tracing to the Network Diagrams sub-system).
- `domainNetworkName`
- `filterBarriers`
- `filterBitsetNetworkAttributeName`
- *(additional properties for function barriers, propagators, and output
  filters follow the same object-per-concern pattern — treat this as a
  scriptable audit surface: "dump every tier's trace configuration" is a
  realistic admin script built entirely on this Describe object.)*

## Practical guidance for Claude when helping with tracing

1. Always ask/confirm **which trace type** first — "trace" alone is
   ambiguous between Connected, Upstream, Downstream, Subnetwork, Isolation,
   Path, etc., and the available configuration options differ per type
   (e.g., Num Paths is Path-only and Infer Connectivity is Path-in-telecom-only;
   Subtract function barriers aren't available on Subnetwork controllers or
   Loops). Shortest path is deprecated at Pro 3.7 / Enterprise 12.1: steer new
   work to Path.
2. When someone wants "only the features that stop a trace" and isn't using
   Isolation, point them at the **output-condition-mirrors-barrier-condition**
   technique above rather than assuming there's a dedicated toggle.
3. Remember the **midspan + Include Barrier Features unchecked** gotcha
   before diagnosing "my trace results look wrong at an edge feature."
4. If the request spans multiple tiers, note that traversability settings are
   **reloaded per tier**, not fixed once — a barrier configured with one
   tier's attribute name may not carry meaning in the next tier.

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-trace-types.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/trace.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/discover-valid-paths.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/discover-the-shortest-path.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/return-circuit-information.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/isolation-trace.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/configure-a-trace.html
