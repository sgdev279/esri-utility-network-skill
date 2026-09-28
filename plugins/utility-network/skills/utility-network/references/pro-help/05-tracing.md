# Utility Network — Tracing (Deep Reference)
*Source: ArcGIS Pro Help + Tool Reference, "Utility Network" book*

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
- **Connected** — all features connected to the starting point(s), regardless
  of direction.
- **Subnetwork** — traces a named subnetwork from its controller(s); can be
  invoked purely by **Subnetwork Name** (no explicit starting points needed —
  the controller(s) for that name become the starting points automatically).
- **Subnetwork controllers** — locates subnetwork controllers reachable from a
  starting point (useful to find "which subnetwork(s) does this feature belong
  to").
- **Upstream** — traces against the direction of flow toward sources.
- **Downstream** — traces with the direction of flow toward consumers/sinks.
- **Loops** — finds looped/meshed paths.
- **Shortest path** — path trace variant using cost/weight attributes.
- **Isolation** — traces to identify features (typically protective/isolating
  devices) that need to be operated to isolate a section of the network; works
  primarily **upstream**. This is the one trace type that can be configured to
  return **only the barrier features that stopped it**, rather than the full
  traced selection — a capability not available on the other trace types
  (see the "returning only barriers" gotcha below).
- **Path** *(implied by Num Paths/Max Hops parameters)* — finds path(s) between
  a start and a stopping point.
- **Circuit** — similar path-based semantics to Path but for circuit-style
  networks; also honors Num Paths/Max Hops.

## Configuring a trace — traversability

Configured in the **Traversability** section of the Trace tool/pane:
- **Condition barriers** — expressions built on **network attributes** or
  **network categories** that define where a trace should stop (e.g., "stop
  when `LIFECYCLESTATUS` ≠ In Service", or "stop at a feature tagged with the
  Protective network category").
- **Function barriers** — stop the trace when a running calculation crosses a
  threshold. Function options: **Minimum**, **Maximum**, **Add** (sum),
  **Average**, **Count**, **Subtract**. (Subnetwork controller and loops trace
  types do **not** support the Subtract function.) Example: starting value 20,
  next feature value 30 — Add accumulates, Subtract nets the difference — used
  for things like cumulative load calculations that should halt the trace once
  a capacity threshold is crossed.
- **Allow Indeterminate Flow**, **Infer Connectivity** — additional
  traversability toggles that loosen/tighten how strictly the trace trusts
  ambiguous or non-explicit connectivity.
- **When tracing across multiple tiers**, the trace configuration (traversability
  scope, condition barriers, function barriers, propagators) is **reloaded per
  tier** as the trace crosses from one tier into the next — configuration is
  *not* globally fixed for the whole trace if it spans tiers.

## Configuring a trace — what's returned

### Num Paths / Max Hops
Only honored for **Path** and **Circuit** trace types — bounds how many
distinct paths are returned and how many hops (feature-to-feature traversals)
a path may contain.

### Output filters (screen every encountered feature)
- **Output Asset Types** — restrict results to specific asset type(s).
- **Output Conditions** — expressions on **network categories** or **network
  attributes**, evaluated per-feature as it's encountered (e.g., "return only
  features with the Isolating network category").
- **Practical technique** (from Esri Community, confirmed working): to make a
  non-Isolation trace type (e.g., Downstream) return **only** the features that
  would have stopped it as barriers, **repeat the condition barrier expression
  as an output condition** — this filters the result set down to just the
  barrier-matching features, since there's no direct "return only barriers"
  toggle outside the Isolation trace type. (As of the source discussion, a
  dedicated trace type/option for this was an open enhancement request, not
  yet shipped — verify current-version release notes before assuming it's
  still unavailable.)

### Include containers, content, structures, and barriers
By default, a trace does **not** return containers, their content, or
structures — only "active" domain-network features. Configurable inclusion
options:
- **Include Barrier Features** (default: checked) — include the barrier
  feature(s) that stopped the trace in the result. Covers explicit feature
  barriers (set in the Trace/Trace Locations pane) *and* dynamically
  configured barriers (condition, function, filter, filter-function).
  - **Gotcha**: when a barrier sits on an edge feature with **midspan
    connectivity** and this option is **unchecked**, results can look
    unexpected — because if *any part* of a feature is returned by the trace,
    the **entire feature** is selected/displayed, not just the traced portion.
  - For subnetwork-based trace types, this option is also influenced by the
    **subnetwork trace configuration** loaded when a Tier is specified — i.e.
    the tier's own subnetwork definition can force barrier inclusion behavior.
- **Ignore Barriers At Starting Points** — lets a trace begin even if the
  starting feature is itself configured as a barrier.

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
   Shortest Path, etc., and the available configuration options differ per
   type (e.g., Num Paths/Max Hops only apply to Path/Circuit; Subtract
   function barriers aren't available on Subnetwork controller or Loops).
2. When someone wants "only the features that stop a trace" and isn't using
   Isolation, point them at the **output-condition-mirrors-barrier-condition**
   technique above rather than assuming there's a dedicated toggle.
3. Remember the **midspan + Include Barrier Features unchecked** gotcha
   before diagnosing "my trace results look wrong at an edge feature."
4. If the request spans multiple tiers, note that traversability settings are
   **reloaded per tier**, not fixed once — a barrier configured with one
   tier's attribute name may not carry meaning in the next tier.
