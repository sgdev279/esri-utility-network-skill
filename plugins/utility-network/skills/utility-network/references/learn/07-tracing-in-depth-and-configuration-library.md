# Utility Network: Tracing in Depth and Trace Configuration Library (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro 3.7 help and tool reference, Esri REST API reference (Trace, Trace Configurations), Esri blogs and Learn lessons; full URL list at the end. Vendor and community material is labelled.*

This file explains how a trace actually evaluates (what is checked, in what order, and why a result is too big or too small), then gives a library of starter trace configurations for electric, gas, water, wastewater/stormwater and telecom. Read it when a trace returns something unexpected, when you are designing a named trace configuration, or when you translate a Pro trace into REST JSON. Settings tables and field-level syntax live in `pro-help/05-tracing.md`, `rest-api/01-utility-network-server-and-trace.md` and `rest-api/08-trace-configuration-full-schema.md`; this file supplies the mechanism and the recipes.

## Contents
1. The life of a trace
2. Starting points, stopping points and barrier locations
3. Traversability: connectivity, condition barriers, function barriers
4. Filters and filter barriers
5. Flow direction: controllers, digitized direction, indeterminate flow
6. Terminals and directional devices
7. Containers, content, structures
8. Output filters and output conditions
9. Functions
10. Propagators and attribute substitution
11. Nearest neighbor
12. Subnetwork-based traces and tier configuration
13. Trace types: what each does and when to use it
14. Results
15. Named trace configurations
16. Trace tool versus Trace pane
17. Performance tuning
18. Configuration library
19. Why did my trace return too much or too little
Common misconceptions, Quick checks, Related files, Sources

## 1. The life of a trace

A trace is a graph search over the **network topology** (the cached index the engine builds when you validate), not over the map. Esri notes that the Trace tool reads this cached topology rather than the map, which is why it is fast on large networks and why it is only as right as the last validation.

Conceptual order of events (the barrier ordering is Esri-documented; the numbered framing is a teaching model):

1. **Resolve the configuration.** Either a named trace configuration (stored in the network), or the parameters you typed, or, for subnetwork-based traces, the values auto-loaded from the chosen tier's subnetwork definition.
2. **Check preconditions.** Topology enabled; for subnetwork-based traces the subnetworks should be clean. With `validateConsistency` the trace fails if a dirty area intersects its path; with `validateLocatability` it fails when it meets nonspatial objects that cannot be located.
3. **Place the starting points** (and stopping points and barrier locations) on junction terminals or along edges.
4. **Establish flow direction** if the trace type needs it (upstream, downstream, isolation).
5. **Expand outward.** At every junction and edge the engine asks: is this element connected, is it allowed through terminal paths, does a **traversability** barrier (condition, then function) stop here, does a **filter** (filter barrier, then filter function barrier) stop here.
6. **Accumulate** function values and propagated values as it goes.
7. **Assemble the result.** Apply containers/content/structures inclusion, barrier inclusion, output filters and output conditions, then serialize in the requested result type.

```
 starting points
      |
      v
 +-------------------+     +---------------------+     +-------------------+
 | connectivity      | --> | traversability      | --> | filters           |
 | (shared geometry, |     | condition barriers, |     | filter barriers,  |
 |  terminals,       |     | function barriers,  |     | filter function   |
 |  associations)    |     | propagators         |     | barriers          |
 +-------------------+     +---------------------+     +-------------------+
                                                                |
                                                                v
                    results <-- output filters/conditions <-- containers,
                    (selection, JSON, geometry)               content, structures
```

Esri documents two evaluation-order facts: traversability barriers are always evaluated first and filters after them; and within each family, condition barriers are evaluated before filter barriers, function barriers before filter function barriers (Esri Barriers page). Everything else in the diagram is explanatory.

**Important consequence:** tracing never reads your fields directly. It reads **network attributes** (and **network categories**) that you mapped to fields. If a field is not mapped to a network attribute, no barrier, function or filter can use it (see `pro-help/03-creation-configuration-attributes-categories-rules.md`).

## 2. Starting points, stopping points and barrier locations

**Definition.** A starting point is where a trace begins; a stopping point marks the end of a path (Path traces only, Enterprise 12.1+ for enterprise data); a **feature barrier** is a location you place by hand that stops the trace. All three are "trace locations".

**Mechanism.**

| Feature kind | How you locate it | REST `traceLocations` field |
|---|---|---|
| Junction or device with terminals | pick the terminal (Pro prompts if you add several terminals from a selection) | `terminalId` |
| Edge (line, edge object) | anywhere along it | `percentAlong` (0 to 1) |
| Polygon (Pro) | place on the polygon feature | n/a, resolved by the client |
| Telecom grouped object | optional unit range | `firstUnit`, `lastUnit` (12.1) |

- A REST location missing its required property is **silently ignored** (Esri), and the response can report `startingPointsIgnored`. This is the first thing to check when "the trace starts nowhere".
- Pro stores locations in the project geodatabase classes `UN_Temp_Starting_Points`, `UN_Temp_Barriers` and `UN_Temp_Stopping_Points`. Your own table works if it has a populated `FEATUREGLOBALID`; rows without one are skipped.
- In the Pro pane an edge accepts one starting point, one stopping point and one barrier; adding more of a kind keeps the last one added. Adding more than 10 features at once raises a confirmation prompt (default limit).
- A feature barrier may be flagged as a **filter barrier** (REST `isFilterBarrier`). In subnetwork-based traces Esri says the trace first finds the controllers and then applies such barriers on a second pass (Enterprise 10.9+).
- With the Aggregated Geometry result, a barrier placed along an edge returns a partial edge; with a Selection result the whole feature is selected (see section 14).

**Example (gas).** A valve with terminals High/Low as a starting point: choosing High versus Low decides which side the trace treats as "the" side, and so which direction counts as upstream in a directional trace.

**Pitfalls.** Wrong terminal on a multi-terminal start; edge locations with no `percentAlong`; stale `UN_Temp_*` points left from a previous trace (use Trace > Clear All); starting points outside the tier named in the configuration (Esri: starting points must be inside the tier).

## 3. Traversability: connectivity, condition barriers, function barriers

**Definition.** *Connectivity* means two features touch through coincident geometry or a connectivity association. *Traversability* is connectivity plus the attribute and category rules that say whether the trace may proceed (Esri Tracing overview).

**Mechanism.** Four kinds of barrier exist (Esri Barriers page):

| Kind | Where set | Used by | What it does |
|---|---|---|---|
| Feature barrier | you place it as a trace location | Trace (and subnetwork update/export) | stops at that exact feature/terminal |
| Condition barrier | `conditionBarriers`; tier default via Set Subnetwork Definition | Trace, update, export | stops where a network attribute or category expression is true (for example Device Status closed) |
| Function barrier | `functionBarriers`; tier default | Trace, update, export | stops when a running total crosses a threshold (for example 500 m traced) |
| Filter / filter function barrier | `filterBarriers`, `filterFunctionBarriers` | **Trace only** | evaluated after traversability; see section 4 |

Details worth knowing:

- **Scope.** `traversabilityScope` (Pro: Apply Traversability To) is `junctions`, `edges` or `junctionsAndEdges` (default both). A Device Status condition with edges-only scope never fires, because edges have no device status.
- **Combining.** Multiple conditions combine with And or Or (REST `combineUsingOr` per condition; Esri's REST page does not define exactly how adjacent conditions are joined: verify against the Esri docs for your version and test with a two-condition case).
- **Category conditions.** Esri: set `name` and `type` to Category with `isSpecificValue` true (Pro: when Name is a category, Type must be Specific Value). Confirm exact casing against a configuration saved from Pro.
- **Attribute-versus-attribute.** `isSpecificValue: false` compares to another network attribute named in `value`.
- **Function barriers accumulate.** Functions are Add, Subtract, Average, Count, Min, Max. **Use Local Values** (REST `useLocalValues`, default off) changes a global running total into per-path totals. Esri example: a 3-mile limit at a three-way fork gives 1 mile to each branch globally, or 3 miles to each branch locally. Subtract is not supported by Subnetwork controllers and Loops traces.
- **Apportionment.** If the threshold falls midspan on an apportionable attribute, the whole feature is the barrier, so a result can total less than the threshold; Aggregated Geometry can return the partial feature.
- **Include Barrier Features** (`includeBarriers`, default true) controls whether the stopping features appear in results; it covers feature barriers and all four dynamic kinds, does not apply to devices with terminals, and in subnetwork-based traces the tier's configuration can override it. Unchecked with a barrier on a midspan edge, the whole edge may still be selected because any returned part selects the entire feature.
- **Ignore Barriers At Starting Points** (`ignoreBarriersAtStartingPoints`, default false) lets a trace begin on a feature that is itself a barrier. Esri names chained upstream protective-device traces as the use case: the device you start on is protective, and you want the next one.
- **Multi-tier traces reload settings.** When a trace crosses into another tier, that tier's traversability scope, condition barriers, function barriers and propagators are loaded (Pro Trace tool help). A barrier written in one tier's attribute names may mean nothing in the next.

**Example (water).** Condition barrier "Device Status equal Closed" plus a function barrier "Add Shape length greater than 500" reads: stop at any closed valve, and in any case stop after about 500 length units. Esri uses almost exactly this example.

**Pitfalls.** Edges-only scope on a device attribute; assuming values are numbers (REST values are strings; coded values compare by stored code, not description); forgetting `ignoreBarriersAtStartingPoints` on a start that sits on a barrier device.

## 4. Filters and filter barriers

**Definition.** Filters are trace-time settings (they exist only in the Trace tool/pane/REST request, not in subnetwork update or export). Esri's definition: filter barriers work like condition barriers, and filter function barriers like function barriers, but they are applied after traversability and only to traces.

**Why they exist.** Traversability describes the *system state* ("closed valves are walls"); filters describe the *question of this trace* ("which of the things I meet should I treat as the answer?"). That split is why an isolation trace needs a filter barrier: the tier's traversability (closed devices stop the trace) is the same for everyone; the filter picks the operable, accessible valves that count as isolating devices.

**Mechanism.** `filterScope` (Pro: Apply Filter To) restricts filters to junctions, edges or both. `filterBarriers` carry `name`, `operator`, `value`, `combineUsingOr`, `isSpecificValue` per the Esri REST page, which lists no `type` property for them; category-based filter barriers (the classic Isolating category) must still express a category, so check how your Pro-saved configuration serializes them (query `traceConfigurations` and copy the shape). `filterFunctionBarriers` have no `useLocalValues`.

**Isolation requires one.** Esri: an isolation trace needs at least one filter barrier, typically a user-defined category such as Isolating assigned to the valve asset types, optionally narrowed by attributes such as operable and accessible.

**Behavior.** Esri documents that filter barriers stop the trace like condition barriers do ("a feature that meets the filter condition stops the trace"), evaluated on a second pass after traversability, in traces only. `rest-api/08-*.md` now says the same. The REST syntax for `filterBarriers` shows no `type` and no category example, while arcpy's `filterBarriers` object has `type`; the blocks below include `type` for category filters on that basis, so confirm against a Pro-saved configuration.

## 5. Flow direction: controllers, digitized direction, indeterminate flow

**Definition.** Upstream, downstream and isolation traces need to know which way things flow. There are two independent sources of direction.

| | Controller-based (default) | Digitized direction (`useDigitizedDirection`) |
|---|---|---|
| Source of direction | subnetwork controllers (source or sink), directional terminals, barriers, computed at trace time | line digitization, From/To IDs on association edge objects, and the persisted `FLOWDIRECTION` attribute |
| Needs | traditional domain network, controllers, clean subnetworks | UN dataset v7+, Pro 3.3, Enterprise 11.3+ |
| Domain/tier parameters | required for upstream/downstream | **ignored** (hidden in Pro) |
| Propagation | works | **ignored** |
| Telecom | not available | the only way to run directional traces on telecom |
| Typical fit | electric, gas, pressurized water | gravity sewer/storm, telecom |

- `FLOWDIRECTION` coded values (Esri): 1 with digitized direction (default, and the value every line gets on upgrade to v7), 2 against, 3 indeterminate/bidirectional. Editing it creates a dirty area; validate before tracing. Esri warns not to use digitized direction if you model flow with controllers.
- **Source versus sink.** Source-based networks (electric, gas, water): upstream moves toward controllers, downstream away. Sink-based (sewer, storm): upstream moves away from controllers, downstream toward them.
- **How controller-based direction is estimated.** Esri's flow article describes it as a path-finding estimate built from three inputs: controllers, barriers and directional terminals. It is not a hydraulic or load-flow solution.
- **Indeterminate flow** arises from loops and meshes, several sources feeding one area, and valves left open in GIS data. `allowIndeterminateFlow` (Pro default on; UN v5+; honored by upstream, downstream, isolation only) decides what happens: on, indeterminate features are included and traced; off, the trace stops at them and excludes them. In REST the page states no default, so send it explicitly.
- **Loops.** With controllers, a loop between the start and the sink is indeterminate, and with the option on the whole loop is selected. A support note (BUG-000137618, Known Limit) records this behavior and recommends devices with terminals at junctions to tell the engine how flow passes.
- **Mesh.** Esri: an upstream or downstream trace that starts in a mesh includes the whole mesh (and downstream also the features beyond network protectors).
- **Two different "flow direction" things.** The persisted `FLOWDIRECTION` attribute (input) versus the `flowDirection` value returned on edges in results (`withDigitized`, `againstDigitized`, `indeterminate`), computed from controllers and requested with Include flow directions / `includeFlowDirections` (introduced at Enterprise 12.1 per REST and the Pro tool page; applies to elements, features and connectivity results; Pro help says it is intended for subnetwork-based traces).
- **Target tier.** An upstream/downstream trace stops at the starting subnetwork boundary unless a Target Tier lets it extend.

**Pitfalls.** Expecting a directional result on a subnetwork with no controller; leaving valves "open" so the whole pressure zone is indeterminate; mixing digitized-direction assumptions with controller-modelled flow.

## 6. Terminals and directional devices

Terminals route flow inside a device. How trace types use them (Esri trace types page):

| Trace | Terminal behavior |
|---|---|
| Connected | connectivity only; ignores terminal directionality and valid paths |
| Path, Shortest path | respect terminal paths; ignore directionality |
| Upstream/Downstream/Isolation | use directional terminal configurations and the subnetwork definition |

A "1 in, 2 out" device (transformer, regulator, check valve) tells the engine how flow can pass; without it, a junction of several mains is ambiguous. Terminal configuration rules (2 to 8 terminals, directional or bidirectional, valid paths for 3 to 4 terminals) are in `pro-help/02-structure-of-a-utility-network.md`. Devices with terminals cannot be midspan on a line. A subnetwork controller needs a terminal.

## 7. Containers, content, structures

By default a trace returns only "active" domain-network features. Inclusion flags (Esri):

| Pro | REST | Effect |
|---|---|---|
| Include Containers | `includeContainers` | add containers and the containers of traced content (useful to return structure network ducts) |
| Include up to First Spatial Container | `includeUpToFirstSpatialContainer` | needs containers on; stops at the first spatial container (all nonspatial ones if none is spatial) |
| Include Content | `includeContent` | add contents of container features; use output filters to separate container types |
| Include Structures | `includeStructures` | add structures when attachment features are traced |

All default off. During Update Subnetwork the same flags decide which containers, content and structures receive the subnetwork name. Telecom circuit traces use Include Containers to show nonspatial objects contained by spatial features. `validateLocatability` fails the trace when a traversed nonspatial object has no containment, attachment or connectivity path to a spatial feature.

## 8. Output filters and output conditions

Both change what is **reported**, not where the trace goes: Esri states filtered-out features are still traced. `outputFilters` (Pro: Output Asset Types) are `networkSourceId` + `assetGroupCode` + `assetTypeCode` triples. `outputConditions` are attribute or category expressions with the same operator vocabulary as barriers.

Technique, community-sourced (Esri Community, not in the Esri help): to make a non-isolation trace return only the features that stopped it, repeat the condition-barrier expression as an output condition. The Esri Learn electric lesson shows the related pattern in a named configuration: "Upstream Protective" has a filter barrier and an output condition.

## 9. Functions

Functions summarize attribute values over what the trace touched: total conductor length, customer count, minimum pipe diameter. REST: `functions[]` with `functionType` (`add`, `subtract`, `average`, `count`, `min`, `max`), `networkAttributeName`, optional `conditions[]`, `functionName` (Esri's example: "Fiber length (meters)"). Pro: Function, Function Name, Filter Name/Operator/Type/Value. Esri notes these use edge elements for apportionable attributes, so counts reflect individual edges. Results come back in `globalFunctionResults`. Do not confuse with function **barriers**, which stop the trace; functions only report.

## 10. Propagators and attribute substitution

**Definition.** Propagation carries a value (phase, voltage, pressure) outward from a controller along the topology, filtering it at each feature with a function and operator. It is configured per tier in Set Subnetwork Definition, and a trace can use it as a barrier source.

**Mechanism (Esri attribute propagation page).**
1. Propagation starts at the controller.
2. It moves downstream; at each feature the propagator function (`Propagated_BITWISE_AND`, `Propagated_MIN`, `Propagated_MAX`) is evaluated with the operator and value.
3. If the propagator returns false the feature is a barrier; for BITWISE_AND the propagated value becomes 0 there.
4. Update Subnetwork writes the values to a Propagated Attribute field; a trace can instead return them (Features result, Include propagated values; Enterprise 12.1+ per the Esri page).
5. Propagator resetter features (UN dataset v8) reset the propagated value to their own value when met.

Null handling: if a network attribute allows null, nulls met during propagation are ignored. Propagation is ignored for traces using digitized direction.

**Phases are bit masks.** Esri's example scheme: A=4, B=2, C=1, so AB=6, ABC=7. An Esri blog scheme adds N=8, so ABCN=15. The values come from your coded value domain; read your own.

**Substitution.** A tap that carries a different phase than its parent line uses an attribute of type substitution. Substitution never overwrites field values; it only changes the value passed to the next feature. Esri's blog states it is diminishing: one energized phase can become another single phase, but not two. Requires the Attribute Substitution network category and propagation to be configured.

**Where to set it.** Pro GP exposes `propagators` on Trace only in Python/ModelBuilder; REST accepts a `propagators` array: `networkAttributeName`, `substitutionAttributeName`, `propagatorFunctionType` (`bitwiseAnd`, `min`, `max`), `operator`, `value` (numeric string), `propagatedAttributeName`. Subnetwork definitions can only be changed while topology is disabled.

**Example (electric).** `Phases Current` propagates with `bitwiseAnd` + `includesAny` + `15`: keep going while any phase is still energized. A single-phase switch on a three-phase main restricts both the main and the tap it feeds.

## 11. Nearest neighbor

"Filter by nearest" returns the k closest features (Pro: Count, Cost Network Attribute, Nearest Categories, Nearest Asset Groups/Types; Python `nearest_count`, `nearest_cost_network_attribute`, `nearest_categories`, `nearest_assets`). REST: `nearestNeighbor { count, costNetworkAttributeName, nearestCategories[], nearestAssets[] }`; Esri's example sends `count: -1` and empty lists when unused. The response may carry `kFeaturesForKNNFound`. Use it for "nearest three switches" or "nearest open point"; the cost attribute must be numeric (for example Shape length). Behavior with barriers beyond the above is not described in the pages read: verify on your version.

## 12. Subnetwork-based traces and tier configuration

Subnetwork, Subnetwork controllers, Upstream, Downstream and Isolation use the **subnetwork definition** of the tier (traditional domain networks only). Choosing Domain Network + Tier in Pro auto-loads that tier's traversability, include flags and propagators; this saves effort and keeps results consistent with Update Subnetwork.

- **Python/arcpy does not auto-load** the tier's configuration: specify it manually (Esri).
- **REST** needs `domainNetworkName` and `tierName` in the configuration (and `subnetworkName` for a name-based subnetwork trace with `traceLocations: []`), unless using a named configuration or digitized direction.
- **Partitioned vs hierarchical.** Partitioned: traces stop at subnetwork controllers. Hierarchical: they stop at controllers whose tier matches the trace's tier. Boundary controllers in hierarchical networks need a category or attribute set in Traversability.
- **Cleanliness.** Results are not guaranteed accurate if dirty areas or subnetwork errors exist in the traceable area (Esri). Validate, then Update Subnetwork. See `learn/03-topology-engine-and-validation.md` and `learn/06-tiers-and-subnetworks-in-depth.md`.
- **Filter by bitset** (`filterBitsetNetworkAttributeName`): upstream/downstream/loops only (see section 18, E3).

## 13. Trace types: what each does and when to use it

| Trace (`traceType`) | Domain networks | Needs | Use when |
|---|---|---|---|
| Connected (`connected`) | traditional + telecom | topology only; ignores subnetwork definition, terminal directionality | "what is physically attached to this", post-edit connectivity checks |
| Subnetwork (`subnetwork`) | traditional | clean subnetwork; start points or Subnetwork Name | list all members of a feeder, pressure zone or sewershed; with a name, controllers become starting points; without output filters the SubnetLine feature is also returned |
| Subnetwork controllers (`subnetworkController`) | traditional | clean subnetwork | find the sources/sinks (including boundary tie devices) that feed a point |
| Upstream (`upstream`) | traditional; telecom only with digitized direction | direction source (controllers or digitized) | trace toward sources (source-based) or away from sinks; protective device search; contributing area |
| Downstream (`downstream`) | same | same | customers affected, spill path, what a device feeds |
| Loops (`loops`) | traditional + telecom | single starting point | find ambiguous-flow areas; errors in radial nets, expected in mesh |
| Isolation (`isolation`) | traditional | **filter barrier** required; tier subnetwork definition | valves/switches to operate; with Include Isolated Features, everything cut off |
| Path (`path`) | traditional + telecom | connectivity only (terminal paths still apply); stopping points optional in the Trace tool (stops can also be unterminated edges); Pro 3.7, Enterprise 12.1+ | valid paths between points; shortest path with `shortestPathNetworkAttributeName` and Num Paths 1; fiber routes |
| Shortest path (`shortestPath`) | both | exactly two starting points; cost attribute | **deprecated** at Pro 3.7 / Enterprise 12.1; migrate to Path |
| Circuit (`circuit`) | telecom only | circuit name or starting points; circuit tables; Enterprise 12.1+ | return a physical or virtual circuit including gaps |

Path details: stop locations are stopping points, unterminated edges (valence 1), or in telecom features with the Circuit Location category. `numPaths` (default 1; total = starts x stops x numPaths) and `maxHops` (default 100; terminal devices count 2) are 12.1 and honored only for path (maxHops also circuit). With the default 100, a circuit crossing more than 100 junctions returns no paths. `inferConnectivity` (path, telecom) climbs containment when explicit connectivity is missing. Note: the Add Trace Configuration tool page lists Num Paths default 2 while Trace and REST state 1; set it explicitly.

**Decision guide.**
1. "What belongs to this feeder/zone?" -> Subnetwork.
2. "What is just connected here?" -> Connected.
3. "What feeds this?" -> Upstream (or Subnetwork controllers for the sources only).
4. "Who loses service?" -> Downstream, or Isolation + Include Isolated Features.
5. "What do I close?" -> Isolation.
6. "How do I get from A to B?" -> Path.
7. "Is circuit X intact?" -> Circuit.

## 14. Results

| Result (Pro) | REST `resultTypes[].type` | Floor | Notes |
|---|---|---|---|
| Selection (default) | n/a (client-side) | | whole features selected even if only part traced; Selection Type: new/add/remove/subset/switch |
| Aggregated Geometry | `aggregatedGeometry` | | multipart points/lines/polygons in `Trace_Results_Aggregated_*`; needs `TRACENAME` field for custom classes; Clear All Previous Trace Results default on; Synthesize Geometries (Enterprise 11.3+) |
| Connectivity | `connectivity` | 10.9.1 | graph of from/via/to; `flowDirection` per edge on request |
| Elements | `elements` | original | codes only (source, asset group/type, ids, terminal, positions) |
| Features | `features` | 11.1 | geometry, network attributes, fields, domain descriptions, propagated values; names included |
| Containment and attachment associations | `associations` | 11.1 | |
| Related records | `relatedRecords` | 11.5 | needs `relationshipClasses` |
| Circuits | `circuits` (create page also lists it) | 12.1 | telecom only |
| (paths) | `paths` | 12.1 | `pathConnectivity` per path |

Other options: Include geometry, Include domain descriptions, Result Network Attributes (`networkAttributeNames`), Result Fields (`resultTypeFields`), `outSR` (11.1), `diagramTemplateName`. Trace response keys include `traceResults`, `sourceMapping`, `globalFunctionResults`, `kFeaturesForKNNFound`, `startingPointsIgnored`, `warnings`. See `rest-api/01-utility-network-server-and-trace.md` and `js-api/04-trace-results-and-widgets.md`.

## 15. Named trace configurations

A named trace configuration stores a complex trace inside the utility network so users run it without knowing the details (introduced with UN dataset v5).

| Surface | How |
|---|---|
| Pro: create | Add Trace Configuration tool (needs UN v5+; Standard or Advanced license; enterprise needs the Advanced Editing user type extension). Records the portal user as creator (OS login in single-user). |
| Pro: use | Trace tool "Use Trace Configuration" + name (other parameters are ignored except name, starting points, barriers, plus stopping points for path), or the Trace pane **Named Configurations** tab (bypasses geoprocessing, no GP history) |
| Pro: manage | Layer Properties > Network Properties > Trace Configurations (name, description, creator, date, tags); Delete, Export, Import tools (JSON; the file's `creator` is honored on import) |
| Share to web/field | Enterprise 10.9+: tick **Active** on the Sharing tab of Network Options; new configurations are inactive by default |
| REST | `.../UtilityNetworkServer/traceConfigurations` with Create, Query, Alter, Delete (10.9+); run with `traceConfigurationGlobalId` on `trace`; its stored trace type wins over `traceType` |
| Permissions | Enterprise: portal UN owner or Administrator can change any; others only their own. Single-user: anyone |

Deleting breaks web maps that reference the configuration; Alter (REST) edits in place. Query response fields: `name`, `description`, `traceType`, `traceConfiguration`, `resultTypes`, `minNumStartingPoints`, `tags`, `creator`, `globalId`. Whether a stored configuration includes the tier defaults depends on how it was saved: re-test after any subnetwork-definition change. A saved configuration that names a renamed field fails (for example the Foundation field renames in the March 2026 water, sewer and stormwater releases, see Esri Foundation documentation).

## 16. Trace tool versus Trace pane

| | Trace tool (GP) | Trace pane |
|---|---|---|
| What | geoprocessing tool with every parameter | UI on the Utility Network tab: set locations, pick a trace gallery item, run |
| History / ModelBuilder / Python | yes | pane runs of named configs bypass GP, no history |
| Enterprise | works only against a utility network feature service; optional async mode runs through the UtilityNetworkTools GP service | same |
| Locations | `starting_points`, `barriers`, `stopping_points` layers | click/Add selected, stored in `UN_Temp_*` |
| Configuration | all parameters; propagators Python only | tier auto-load; named configurations |

Use the pane for interactive work; the tool for scripts and repeatable models; REST for services.

## 17. Performance tuning

Esri-documented: validate and keep subnetworks clean (the trace reads the cache); the Trace tool offers an asynchronous mode in enterprise deployments; the Trace tool is faster than map-based logic because it reads topology; `validateConsistency` is off by default in Pro (REST page lists true), so it costs a check on dirty areas.

Practitioner guidance (test, do not assume):
- Constrain with Domain Network + Tier (and Target Tier only when needed) instead of tracing the whole network.
- Cap runaway traces with a function barrier (length, count) while testing.
- Leave containers/content/structures off unless needed.
- Request only the result types and fields you need; geometry and Features results cost more than Elements.
- Narrow with output filters server-side rather than filtering a large JSON client-side.
- Prefer named configurations for consistency.
- Rule out dirty areas and Manage IsDirty off (always-dirty subnetworks) before blaming the engine.

## 18. Configuration library

**How to read these.** Every JSON block is an **illustrative** request body (traceType, traceLocations, traceConfiguration, resultTypes) using only property names from `rest-api/01` and `rest-api/08` and Esri's Trace page. Angle-bracket tokens are placeholders for names in *your* schema: Foundation names change between releases (for example Lifecycle Status became Asset State in the March 2026 water, sewer and stormwater Foundations). Values are strings. Source ids and asset codes are placeholder integers.

**Validate before use.** Save a block as `req.json` and run `python scripts/build_trace_request.py --check req.json` from the skill directory. It catches unknown keys, bad operators and missing tier/domain. Known quirks: it flags `percentAlong: -1` (Esri's own example sends -1 for non-edge locations) still asks for domain/tier on upstream/downstream when `useDigitizedDirection` is true (the service ignores them in that mode, so the blocks below include them only to satisfy the check), and reports "circuit trace has no starting points" for a circuit trace driven by `circuitName` (Esri says locations are not required then; expect exit status 1 for block T2). The other blocks pass cleanly. Then export a Pro-saved equivalent with `traceConfigurations/query` and compare shapes, especially category conditions.

Not shown in the blocks: the usual request shell, `"f":"json"`, `"gdbVersion":"<OWNER.VERSION>"`, optional `"sessionId"`, `"async":true` for long runs.

### Electric

**E1. Upstream protective device.**

| Item | Value |
|---|---|
| Intent | from any point find the first protective device toward the source |
| Type | `upstream`, tier e.g. `<MV_TIER>` |
| Key settings | filter barrier on category Protective; output condition on Protective; `ignoreBarriersAtStartingPoints` true for chaining; `allowIndeterminateFlow` true in radial |
| Basis | Esri Learn electric lesson ("Upstream Protective" has a filter barrier and an output condition); REST page names the ignore flag for this use |

```json
{ "traceType": "upstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000001}", "terminalId": 1 } ],
  "traceConfiguration": {
    "domainNetworkName": "<ELECTRIC_DOMAIN>", "tierName": "<MV_TIER>",
    "includeBarriers": true, "ignoreBarriersAtStartingPoints": true, "allowIndeterminateFlow": true,
    "filterScope": "junctions",
    "filterBarriers": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<PROTECTIVE_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true } ],
    "outputConditions": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<PROTECTIVE_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**E2. Downstream customers.**

| Item | Value |
|---|---|
| Intent | customers and load fed by a device (outage scope) |
| Type | `downstream` |
| Key settings | open devices stop the trace (tier default or `conditionBarriers` Device Status); output filter or output condition on customer-load category; `count` function over a customer-count attribute; Allow Indeterminate Flow on in radial |
| Basis | Esri Learn lesson ("Downstream Customer Load" returns services categorized as customer load); functions per REST |

```json
{ "traceType": "downstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000002}", "terminalId": 2 } ],
  "traceConfiguration": {
    "domainNetworkName": "<ELECTRIC_DOMAIN>", "tierName": "<LV_OR_MV_TIER>", "includeBarriers": true, "allowIndeterminateFlow": true,
    "conditionBarriers": [ { "name": "<DEVICE_STATUS_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<OPEN_CODE>", "combineUsingOr": false, "isSpecificValue": true } ],
    "outputConditions": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<CUSTOMER_LOAD_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true } ],
    "functions": [ { "functionType": "count", "networkAttributeName": "<CUSTOMER_COUNT_ATTRIBUTE>", "functionName": "Customers", "conditions": [] } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**E3. Phase tracing and open phases.**

| Item | Value |
|---|---|
| Intent | which phases are energized at or below a point; downstream of an open phase |
| Type | `subnetwork` (by `subnetworkName`, `traceLocations: []`) with propagators, or `downstream` plus `filterBitsetNetworkAttributeName` |
| Key settings | propagator `bitwiseAnd` + `includesAny` + all-phases mask; `Features` result with `includePropagatedValues` (subnetwork traces; 12.1 per Pro) ; clean subnetwork; phases stored as bit masks in a coded domain |
| Basis | Esri propagation page and blog; REST example uses "Phases Current", `includesAny`, 15 |

```json
{ "traceType": "subnetwork", "traceLocations": [],
  "traceConfiguration": {
    "domainNetworkName": "<ELECTRIC_DOMAIN>", "tierName": "<MV_TIER>", "subnetworkName": "<FEEDER_NAME>",
    "includeBarriers": true, "validateConsistency": true, "traversabilityScope": "junctionsAndEdges",
    "conditionBarriers": [ { "name": "<DEVICE_STATUS_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<OPEN_CODE>", "combineUsingOr": false, "isSpecificValue": true } ],
    "propagators": [ { "networkAttributeName": "<PHASES_CURRENT_ATTRIBUTE>", "substitutionAttributeName": "<SUBSTITUTION_ATTRIBUTE>",
                       "propagatorFunctionType": "bitwiseAnd", "operator": "includesAny", "value": "<ALL_PHASES_MASK>", "propagatedAttributeName": "<PROPAGATED_FIELD>" } ] },
  "resultTypes": [ { "type": "features", "includeGeometry": false, "includePropagatedValues": true, "includeDomainDescriptions": true, "networkAttributeNames": [ "<PHASES_CURRENT_ATTRIBUTE>" ] } ] }
```

Open-phase reading: a feature whose propagated value is 0 (or lacks a phase bit) is not energized for that phase. Esri documents the de-energized outcome, not a feature named "open phase". Variant: for a point query, use `downstream` from the device with `filterBitsetNetworkAttributeName` set to the phase attribute; Esri's wording is that results include any bit set on the starting points for it, so confirm results on a known example.

**E4. Feeder trace.**

| Item | Value |
|---|---|
| Intent | everything on a circuit |
| Type | `subnetwork` by name |
| Key settings | `traceLocations: []`; domain+tier; includes per tier definition; result Elements or Features |
| Note | subnetwork must be clean; SubnetLine returned when no output filters |

```json
{ "traceType": "subnetwork", "traceLocations": [],
  "traceConfiguration": {
    "domainNetworkName": "<ELECTRIC_DOMAIN>", "tierName": "<MV_TIER>", "subnetworkName": "<FEEDER_NAME>",
    "includeContainers": true, "includeContent": true, "includeStructures": false, "includeBarriers": true, "validateConsistency": true },
  "resultTypes": [ { "type": "elements" } ] }
```

### Gas

**G1. Isolation for a leak (valves to close).**

| Item | Value |
|---|---|
| Intent | operable valves that isolate a leak; optionally what loses gas |
| Type | `isolation`, pressure tier `<PRESSURE_TIER>` |
| Key settings | filter barrier on Isolating category (add operable/accessible attributes); condition barriers from tier (closed devices); `includeIsolated` false returns isolating devices only, true adds cut-off features; `allowIndeterminateFlow` true |
| Basis | Esri Gas Foundation lesson (config "Isolation Trace (isolating features only)": Device Status Closed, Normal Status Open, Isolating category); Esri isolation pages |
| Practitioner | dead-end sections: SSP's vendor blog notes a valve between a dead end and its only regulator should be ignored; check single-fed areas |

```json
{ "traceType": "isolation",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000003}", "percentAlong": 0.5 } ],
  "traceConfiguration": {
    "domainNetworkName": "<GAS_DOMAIN>", "tierName": "<PRESSURE_TIER>",
    "includeIsolated": false, "includeBarriers": true, "allowIndeterminateFlow": true, "filterScope": "junctions",
    "conditionBarriers": [ { "name": "<DEVICE_STATUS_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<CLOSED_CODE>", "combineUsingOr": false, "isSpecificValue": true } ],
    "filterBarriers": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<ISOLATING_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true },
                        { "name": "<OPERABLE_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<YES_CODE>", "combineUsingOr": false, "isSpecificValue": true } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

To see customers affected set `includeIsolated` true and add `outputFilters` for the service/meter asset type plus a `count` function.

**G2. Pressure-zone shutdown.**

| Item | Value |
|---|---|
| Intent | all assets and customers in a pressure zone; boundary devices to close |
| Type | `subnetwork` by name for membership; `subnetworkController` at the Pressure tier for feeding stations; or `isolation` at the Pressure tier |
| Key settings | domain `<GAS_DOMAIN>`, tier `<PRESSURE_TIER>`; System tier traces the whole network, Pressure tier only the zone (Esri Gas lesson); `count` function on customers |
| Caveat | Esri notes hierarchical trace stops at controllers of its own tier |

```json
{ "traceType": "subnetwork", "traceLocations": [],
  "traceConfiguration": {
    "domainNetworkName": "<GAS_DOMAIN>", "tierName": "<PRESSURE_TIER>", "subnetworkName": "<PRESSURE_ZONE_NAME>",
    "includeBarriers": true, "validateConsistency": true,
    "functions": [ { "functionType": "count", "networkAttributeName": "<CUSTOMER_COUNT_ATTRIBUTE>", "functionName": "Customers", "conditions": [] } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

### Water

**W1. Isolation zone.**

| Item | Value |
|---|---|
| Intent | valves to close to isolate a main break, optionally the isolated area |
| Type | `isolation`, tier `<WATER_PRESSURE_TIER>` (System tier covers more but ignores storage) |
| Key settings | filter barrier on Isolating + closeable/accessible; `includeIsolated`; Allow Indeterminate Flow; aggregated geometry to avoid over-selecting long mains |
| Basis | Esri isolation trace pages |

```json
{ "traceType": "isolation",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000004}", "percentAlong": 0.4 } ],
  "traceConfiguration": {
    "domainNetworkName": "<WATER_DOMAIN>", "tierName": "<WATER_PRESSURE_TIER>",
    "includeIsolated": true, "includeBarriers": true, "allowIndeterminateFlow": true,
    "filterBarriers": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<ISOLATING_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true },
                        { "name": "<CLOSEABLE_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<YES_CODE>", "combineUsingOr": false, "isSpecificValue": true } ],
    "outputFilters": [ { "networkSourceId": 9, "assetGroupCode": 3, "assetTypeCode": 12 } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**W2. Affected customers.** Same trace, `includeIsolated: true`; `outputFilters` = service connection or meter asset types; add `functions` `count` (customers), `add` (length). Excluding isolating valves from output is done by the output filter. Customer identity comes from your CIS link, not the UN.

```json
{ "traceType": "isolation",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000004}", "percentAlong": 0.4 } ],
  "traceConfiguration": {
    "domainNetworkName": "<WATER_DOMAIN>", "tierName": "<WATER_PRESSURE_TIER>", "includeIsolated": true, "allowIndeterminateFlow": true,
    "filterBarriers": [ { "name": "Category", "type": "category", "operator": "includesTheValues", "value": "<ISOLATING_CATEGORY>", "combineUsingOr": false, "isSpecificValue": true } ],
    "outputFilters": [ { "networkSourceId": 9, "assetGroupCode": 7, "assetTypeCode": 1 } ],
    "functions": [ { "functionType": "count", "networkAttributeName": "<CUSTOMER_COUNT_ATTRIBUTE>", "functionName": "Customers", "conditions": [] } ] },
  "resultTypes": [ { "type": "features", "includeGeometry": false, "networkAttributeNames": [ "<CUSTOMER_COUNT_ATTRIBUTE>" ] } ] }
```

**W3. Flushing (practitioner guidance; Esri documents no flushing trace).**
Intent: see the path water takes to a hydrant when planned valves are closed. Esri's flow article says barriers can turn a looped area into one with a single flow direction, naming hydrant flushing and DMA planning as uses. Approach: place the hydrant as the start, the valves you plan to close as barrier locations, run `upstream`, request flow directions, then run again with `allowIndeterminateFlow` false: features dropped out are still indeterminate and need another closed valve. Flow is an estimate, not hydraulics.

```json
{ "traceType": "upstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000005}", "terminalId": 1 },
                      { "traceLocationType": "barrier", "globalId": "{00000000-0000-0000-0000-000000000006}", "terminalId": 1 } ],
  "traceConfiguration": {
    "domainNetworkName": "<WATER_DOMAIN>", "tierName": "<WATER_PRESSURE_TIER>", "includeBarriers": true, "allowIndeterminateFlow": false,
    "conditionBarriers": [ { "name": "<DEVICE_STATUS_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<CLOSED_CODE>", "combineUsingOr": false, "isSpecificValue": true } ] },
  "resultTypes": [ { "type": "connectivity", "includeGeometry": false, "includeFlowDirections": true } ] }
```

**W4. Pressure zone trace.**
Intent: members of a zone or its feeding sources. `subnetwork` with `subnetworkName` (like G2, domain `<WATER_DOMAIN>`), or `subnetworkController` from a point:

```json
{ "traceType": "subnetworkController",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000007}", "percentAlong": 0.5 } ],
  "traceConfiguration": { "domainNetworkName": "<WATER_DOMAIN>", "tierName": "<WATER_PRESSURE_TIER>", "includeBarriers": true, "validateConsistency": true },
  "resultTypes": [ { "type": "elements" } ] }
```

### Wastewater and stormwater

**S1. Downstream flow path using digitized direction.**

| Item | Value |
|---|---|
| Intent | where does a spill or discharge go |
| Type | `downstream`, `useDigitizedDirection` true (UN v7+, Enterprise 11.3+) |
| Key settings | domain/tier ignored; propagation ignored; relies on `FLOWDIRECTION`; closed gates/stop logs as condition barriers |
| Basis | Esri configure-a-trace page; Esri blog on digitized direction |

```json
{ "traceType": "downstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000008}", "terminalId": 1 } ],
  "traceConfiguration": {
    "useDigitizedDirection": true, "allowIndeterminateFlow": true, "includeBarriers": true,
    "domainNetworkName": "<SEWER_DOMAIN>", "tierName": "<SEWERSHED_TIER>",
    "conditionBarriers": [ { "name": "<DEVICE_STATUS_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<CLOSED_CODE>", "combineUsingOr": false, "isSpecificValue": true } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**S2. Upstream catchment (controller-based).**

| Item | Value |
|---|---|
| Intent | everything contributing to a point; customers upstream of a manhole |
| Type | `upstream` on a sink-based domain (upstream moves away from the sink) |
| Key settings | tier `<SEWERSHED_TIER>`, optional `targetTierName`; output filter on service connection type; `count` function; clean subnetworks |
| Basis | Esri configuration notes |

```json
{ "traceType": "upstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000009}", "terminalId": 1 } ],
  "traceConfiguration": {
    "domainNetworkName": "<SEWER_DOMAIN>", "tierName": "<SEWERSHED_TIER>", "targetTierName": "<COLLECTION_SYSTEM_TIER>",
    "allowIndeterminateFlow": true, "includeBarriers": true,
    "outputFilters": [ { "networkSourceId": 9, "assetGroupCode": 4, "assetTypeCode": 2 } ],
    "functions": [ { "functionType": "count", "networkAttributeName": "<CUSTOMER_COUNT_ATTRIBUTE>", "functionName": "Connections", "conditions": [] } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**S3. Upstream with digitized direction.** Same as S1 with `traceType` `upstream`. Check data first: a line that Connected reaches but Upstream misses is probably flipped (Esri's QA recipe); subnetworks themselves ignore digitized direction.

### Telecom

Telecom has no subnetworks and tiers; circuits replace them. Directional traces need `useDigitizedDirection`.

**T1. Fiber path (path trace).**

| Item | Value |
|---|---|
| Intent | route between two ports and its length |
| Type | `path` (Pro 3.7, Enterprise 12.1+) |
| Key settings | stopping point; `numPaths`; `maxHops` (default 100); `shortestPathNetworkAttributeName`; `inferConnectivity` for incomplete data; unit ranges on locations; `add` function on length |
| Basis | Esri Trace page telecom path example ("Fiber length (meters)") |

```json
{ "traceType": "path",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000010}", "terminalId": 1, "firstUnit": 1, "lastUnit": 1 },
                      { "traceLocationType": "stoppingPoint", "globalId": "{00000000-0000-0000-0000-000000000011}", "terminalId": 1, "firstUnit": 1, "lastUnit": 1 } ],
  "traceConfiguration": {
    "domainNetworkName": "<TELECOM_DOMAIN>", "numPaths": 1, "maxHops": 100, "inferConnectivity": false,
    "shortestPathNetworkAttributeName": "<LENGTH_ATTRIBUTE>", "traversabilityScope": "junctionsAndEdges",
    "functions": [ { "functionType": "add", "networkAttributeName": "<LENGTH_ATTRIBUTE>", "functionName": "Fiber length (meters)", "conditions": [] } ] },
  "resultTypes": [ { "type": "paths", "includeGeometry": true } ] }
```

**T2. Circuit trace.**
Intent: return a defined circuit including virtual sections. Type `circuit` (Enterprise 12.1+). With `circuitName` set, locations are optional (Esri).

```json
{ "traceType": "circuit", "traceLocations": [],
  "traceConfiguration": { "domainNetworkName": "<TELECOM_DOMAIN>", "circuitName": "<CIRCUIT_NAME>", "maxHops": 100 },
  "resultTypes": [ { "type": "circuits", "includeGeometry": true } ] }
```

**T3. Splice connectivity (what is spliced to this strand).**
Intent: follow connectivity from a strand range through splices. Type `connected` (connectivity only; ignores directionality), start with unit range; consider `path` when you need an ordered route.

```json
{ "traceType": "connected",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000012}", "percentAlong": 0.5, "firstUnit": 1, "lastUnit": 12 } ],
  "traceConfiguration": { "domainNetworkName": "<TELECOM_DOMAIN>", "includeContainers": true, "includeBarriers": true },
  "resultTypes": [ { "type": "connectivity", "includeGeometry": false } ] }
```

**T4. Outage by strand (practitioner guidance; no dedicated Esri tool found).**
Intent: what is beyond a cut. Run `downstream` with `useDigitizedDirection` true from the cut edge object (reliable direction required), or `connected` with a barrier at the cut. Then list circuits through the cut unit range using circuits query (`rest-api/07-circuits-and-unit-identifiers-telecom.md`) and trace each circuit.

```json
{ "traceType": "downstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000013}", "percentAlong": 0.5, "firstUnit": 1, "lastUnit": 12 } ],
  "traceConfiguration": { "useDigitizedDirection": true, "allowIndeterminateFlow": true, "includeBarriers": true,
                          "domainNetworkName": "<TELECOM_DOMAIN>", "tierName": "<IGNORED_WHEN_DIGITIZED>" },
  "resultTypes": [ { "type": "connectivity", "includeGeometry": false, "includeFlowDirections": true } ] }
```

## 19. Why did my trace return too much or too little

| Symptom | Likely cause | How to confirm | Fix |
|---|---|---|---|
| Trace starts nowhere / empty | location missing `terminalId`/`percentAlong`, or wrong class | `startingPointsIgnored` in response; run `--check` | supply the property |
| Nothing returned but no error | start inside the wrong tier; start sits on a barrier | try Ignore Barriers At Starting Points; remove Tier | correct tier/flag |
| Far too much (whole network) | no barrier fired: scope wrong, attribute not mapped, wrong coded value, devices "open" in GIS | test one barrier alone; check value is stored code | fix scope/value; edit device status |
| Far too much, upstream/downstream | indeterminate flow with option on; loop selected whole | rerun with Allow Indeterminate Flow off | add terminals, barriers, or controllers |
| Too little, stops early | a tier-loaded condition barrier you did not know about | read tier subnetwork definition; compare to the Pro-loaded values | override in the request |
| Too little at a device | Include Barrier Features off, or barrier on terminal device | toggle option | include barriers |
| Whole long main selected | selection of whole feature when part traced | use Aggregated Geometry | switch result type |
| No customers / services returned | containers, content or structures off; output filter too narrow; services not connected | toggle includes; remove output filters | adjust |
| Upstream/Downstream returns nothing or errors | no controller, dirty subnetwork, wrong domain/tier | check Subnetworks table, dirty areas | update subnetwork |
| Direction reversed | source/sink confusion, flipped line (digitized) | Include flow directions; Connected vs Upstream compare | fix controllers or flip line, validate |
| Digitized trace ignores tier | by design (tier ignored) | n/a | none |
| Phase trace shows wrong phases | stale propagated values; propagator on wrong tier; digitized direction in use | check propagated values; update subnetwork | re-run Update Subnetwork; avoid digitized |
| Isolation returns nothing | no filter barrier; valves not categorized/operable | inspect configuration | add filter barrier, categories |
| Isolation returns too much | closed valve not modelled, valve attributes wrong | check Device Status | edit data |
| Path returns none | `maxHops` too low; stopping point missing; unit mismatch | raise Max Hops; add stops | adjust |
| Path returns too many | Num Paths too high; splitters without Splitter category | set Num Paths | set category |
| Trace errors on dirty area | `validateConsistency` true | Validate Network Topology | validate |
| Named config works in Pro, differs in REST | stored trace type wins; tier defaults not applied; `percentAlong` -1 | compare JSON from `traceConfigurations/query` | pass `traceConfigurationGlobalId` only |
| Results differ between users | different version or unsaved edits (trace reads saved state) | compare `gdbVersion`, `moment` | align versions |
| Saved config broke after Foundation upgrade | renamed attributes | read config JSON | update names |

## Common misconceptions

- "Filter barriers and condition barriers are the same." They behave alike but have different owners, ordering and lifetimes: conditions are tier defaults used by update/export; filters are trace-only.
- "Isolation traces find valves automatically." They find what your filter barrier says counts as isolating; no filter, no result.
- "Include Barrier Features is cosmetic." It changes what gets selected, including midspan edge behavior.
- "Digitized direction works with tiers and propagation." It ignores both.
- "The trace uses the map." It uses the validated topology cache.
- "Shortest path is the way to do routing." Deprecated at Pro 3.7 / Enterprise 12.1: use Path.
- "Directional results are hydraulic truth." Esri calls flow an estimate.
- "One JSON works across industries." Names, codes and categories are model-specific.

## Quick checks

1. Which surface (Pro pane, GP tool, REST, JS, arcpy) and which UN dataset/Pro/Enterprise version?
2. Which trace type, domain network and tier? Subnetworks clean (`Status`, dirty areas)?
3. Controller-based or digitized direction? Is `FLOWDIRECTION` populated?
4. Is the trace configuration named, tier-loaded, or typed? Compare against a Pro-saved JSON.
5. Do barrier attributes exist as network attributes, with the right scope and stored code?
6. Is a filter barrier present for isolation?
7. Are containers/content/structures and Include Barrier Features set as intended?
8. Did the response contain `startingPointsIgnored` or `warnings`?

## Related files

- `pro-help/05-tracing.md`, `pro-help/02-structure-of-a-utility-network.md`, `pro-help/03-creation-configuration-attributes-categories-rules.md`
- `rest-api/01-utility-network-server-and-trace.md`, `rest-api/08-trace-configuration-full-schema.md`, `rest-api/06-asynchronous-operations-job-status.md`, `rest-api/07-circuits-and-unit-identifiers-telecom.md`
- `js-api/01-javascript-sdk-utility-network.md`, `js-api/04-trace-results-and-widgets.md`
- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/03-topology-engine-and-validation.md`, `learn/06-tiers-and-subnetworks-in-depth.md`
- `scripts/build_trace_request.py`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/configure-a-trace.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-trace-types.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://pro.arcgis.com/en/pro-app/3.0/help/data/utility-network/barriers.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/attribute-propagation.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/substitution.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-trace-configurations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/isolation-trace.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/return-circuit-information.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-starting-points-and-barriers.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-trace-configuration.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-subnetwork-definition.html
- https://pro.arcgis.com/en/pro-app/3.3/help/data/utility-network/about-tracing-utility-networks.htm
- https://pro.arcgis.com/en/pro-app/2.7/arcpy/functions/nearest-neighbor.htm
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-utility-network-server/
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/exploring-propagation-and-attribute-substitution-in-subnetwork-management
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/utility-network-flow
- https://support.esri.com/en-us/bug/the-utility-network-downstream-trace-returns-different-bug-000137618
- https://learn.arcgis.com/en/projects/get-started-with-arcgis-utility-network-for-electric/
- https://doc.arcgis.com/en/arcgis-solutions/reference/use-gas-and-pipeline-referencing-utility-network-foundation.htm
- https://developers.arcgis.com/net/utility-network/trace-parameters/
- https://sspinnovations.com/blog/gas-isolation-tracing/ (vendor blog)
- https://sspinnovations.com/blog/esri-utility-network-can-you-trace-phase/ (vendor blog)
- https://sspinnovations.com/blog/esri-utility-network-introducing-electric-tracing/ (vendor blog)
