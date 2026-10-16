# Utility Network: Mental Model and the Life of an Edit
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Read this first if you need to reason about the Utility Network (UN) end to end: what it is, why it replaced the geometric network, which component does what, and what physically happens between "I digitized a valve" and "my trace returned the right customers". Almost every UN support question ("my trace misses the new valve", "subnetwork name is stale", "validate says clean but errors remain") is a question about which step of the edit lifecycle has or has not run. Builds on `pro-help/01-core-concepts-and-vocabulary.md`. Sources: see the list at the end. Section 4 is the core of this file; sections 1 to 3 give you the vocabulary it uses. This file is the end-to-end walk-through; `learn/02-data-model-in-depth.md` has the schema detail and `learn/03-topology-engine-and-validation.md` the topology mechanics.

## Contents
1. What the UN is, and why it is not a geometric network
2. The components and how they fit together
3. Stored versus computed: the state model
4. The life of an edit, step by step
5. Variations on the lifecycle (named versions, bulk loads, telecom, single-user)
6. Which parts differ for electric, gas, water/wastewater and telecom
7. Common misconceptions, quick checks, related files, sources

## 1. What the UN is, and why it is not a geometric network

**Plain definition.** Esri describes the UN as the main ArcGIS component for managing utility and telecom networks (electric, gas, water, stormwater, wastewater, telecommunications). It models wires, pipes, valves, devices, circuits and zones, and it encodes real-world behaviour (connectivity, containment, structural attachment) so you can discover connectivity, trace resource flow, view device operating state and analyse the effect of events such as storms and outages.

**Mechanism: what actually changed.** A geometric network stored connectivity as a by-product of feature geometry: two features that touched were connected, and the network was a desktop-era artefact. The UN keeps geometry but adds a separate, explicit, indexed connectivity model.

| Question | Geometric network | Utility network |
|---|---|---|
| Where does connectivity live? | Implied by geometric coincidence | A graph called the network topology, built from geometric coincidence **plus** associations, governed by network rules |
| How many feature classes? | Often one per kind of thing (abandoned line, sampling station, ...) | A small fixed set (5 feature classes + 2 tables per traditional domain network); the kind of thing is `ASSETGROUP` + `ASSETTYPE` |
| Can an invalid connection be made? | Largely yes; flagged by users or by custom checks | Feature restrictions and network rules block or flag it; violations become error dirty areas |
| Non-coincident or non-spatial relationships | Not modelled | Associations: junction-junction, junction-edge, containment, structural attachment |
| Support structures (poles, vaults) | Usually plain feature classes | A structure network that participates in tracing and associations |
| What is "a circuit / pressure zone"? | Derived ad hoc | A subnetwork: first-class, named, with a tier, controllers, and a `SubnetLine` record |
| How are traces shaped? | Find connected, find upstream, with simple barriers | Traversability, trace configurations, categories, barriers, functions, propagators, output filters |
| Architecture | Desktop | Services-based on ArcGIS Enterprise (branch versioning, feature, utility network, diagram, validation services) or single-user in Pro |
| Diagrams | ArcGIS Schematics (ArcMap era) | Network diagrams generated from the topology |

Sources for the table: Esri's "what is a utility network", "benefits" and vocabulary pages for the UN column; the Esri Canada article (partner guidance, not Esri documentation) for the geometric-network column and the Schematics deprecation date. Esri's own help does not publish a feature-by-feature comparison.

**Example (water).** In a geometric network you might have `Hydrants`, `Valves`, `Blow-offs`, each a junction class with its own connectivity rules. In the UN these are asset types in the `WaterDevice` class (asset group such as Valve, asset type such as Gate Valve), and one connectivity rule between asset types governs how a line meets them.

**Pitfall.** Esri frames the trade as more underlying complexity in exchange for more functionality. If a project's real need is only "find connected", the UN will feel heavy; a trace network (a different, simpler dataset served by `TraceNetworkServer`) is out of scope for this skill.

## 2. The components and how they fit together

```
Geodatabase (enterprise / file / mobile)
 └── Feature dataset   (spatial reference; holds everything below)
      ├── Service territory polygon fc   (m- and z-enabled; bounds the network and restricts edits)
      └── Utility network  (one per feature dataset)
           ├── Structure network   (exactly one)   StructureJunction / Line / Boundary + 2 object tables
           ├── Domain network(s)   (one or more)   traditional (5 fc + 2 tables) or telecom (4 fc + 5 tables)
           │     ├── network sources  (each class has a numeric source ID)
           │     ├── ASSETGROUP (subtype) -> ASSETTYPE (domain)       <- the key for rules/terminals/categories
           │     ├── tier groups (hierarchical only) -> tiers -> subnetwork definition
           │     └── subnetwork controllers -> subnetworks -> SubnetLine
           ├── Network definition: network attributes, network categories, terminal configurations, rules
           ├── Network topology   (ONE graph, stored as binary pages; enabled or disabled)
           └── System tables/layers: Dirty Areas, Associations, Subnetworks, Rules, (Dirty Objects), diagrams
```

The table below names each component, what it does, and the moment in the edit lifecycle (section 4) at which it acts.

| Component | What it is | Acts at (step in section 4) |
|---|---|---|
| Feature dataset + service territory | The container and the legal editing area | Step 1 (edits outside the territory are refused) |
| Feature classes and tables (network sources) | Where the digitized features and nonspatial objects live | Step 1 |
| `ASSETGROUP` / `ASSETTYPE` | Two-level classification; the lookup key for nearly all configuration | Steps 1, 5 (rules look up the pair) |
| Feature restrictions | Built-in, system-maintained limits on which classes can relate | Steps 2, 5 |
| Network rules | Admin-defined allowed relationships (5 types) | Steps 2 (association edits), 5 (validate) |
| Terminals and terminal configurations | Logical ports on devices / junction objects, with paths and directionality | Steps 2, 5, 7 |
| Attribute rules (geodatabase) | Arcade logic: immediate calculation and constraint rules run during the edit; batch calculation and validation rules run on demand | Step 1 |
| Associations (system table) | Non-geometric relationships stored as rows (telecom also uses foreign keys) | Steps 2, 5 |
| Dirty areas (system layer) | Bookkeeping: where the map and the topology disagree, and where errors are | Steps 3, 5, 6 |
| Network topology | The indexed graph that traces and diagrams read | Steps 5, 6, 7, 8 |
| Network attributes and categories | Cached values and tags used to shape traversal and subnetworks | Steps 3 (change flagged), 5 (cache refreshed), 6, 7 |
| Tiers and subnetwork definitions | Where subnetworks live and what they may contain | Step 6 |
| Subnetwork controllers, Subnetworks table, `SubnetLine` | Origin points, status per controller, one line record per subnetwork | Step 6 |
| Services (`UtilityNetworkServer`, `FeatureServer`, `VersionManagementServer`, `ValidationServer`, `NetworkDiagramServer`) | The enterprise surface for all of the above | Steps 1 to 9 in enterprise |
| Branch versioning | Isolation of edits (Default and named versions), reconcile and post | Step 9 |

Esri-documented facts behind the diagram: one structure network per UN; a traditional domain network is created by `Add Domain Network` with exactly seven classes (no more can be added); a telecom domain network (`Add Telecom Domain Network`, UN dataset v8 and later) has four feature classes and five tables; a UN can have several domain networks of either kind; each UN has one network topology.

### 2.1 The three ways two things become related

This is the most important modelling idea; `learn/02-data-model-in-depth.md` section 7 goes deep.

| Mechanism | Needs geometry? | Stored where | Example |
|---|---|---|---|
| Geometric coincidence (endpoint or midspan snapping) | Yes: coincident within the dataset's x, y, z tolerances | In the topology after validate; terminal IDs on the line's `FROMDEVICETERMINAL` / `TODEVICETERMINAL` | A gas main ends exactly on a regulator's inlet |
| Connectivity association | No (features may be offset) | Associations table (types 1, 4, 5, 6); telecom uses foreign-key fields for junction-edge | A water service lateral modelled as an edge between a tap and a meter |
| Containment / structural attachment association | No | Associations table (types 2, 3); telecom containment uses `ContainerSourceID`/`ContainerGlobalID` | A fuse inside a vault; a transformer attached to a pole |

Either way a **rule must exist** (and not violate a feature restriction) or validation flags the pair and leaves it disconnected.

### 2.2 Subnetworks in one paragraph

A **subnetwork** is the connected area traced from one or more **subnetwork controllers** (a terminal on a device or junction object) within a **tier**. It is not stored as a polygon you edit: it is *discovered* by tracing, then *recorded* by `Update Subnetwork`, which writes the subnetwork name onto every participating feature, creates or refreshes a `SubnetLine` record, and sets the controller rows in the Subnetworks table to Clean (or Invalid). Electric calls them circuits or feeders, gas and water call them pressure zones or isolation zones. Telecom domain networks have no subnetworks.

## 3. Stored versus computed: the state model

Most "my data and my trace disagree" tickets are a confusion between these two columns.

| Item | Stored by you | Computed by a tool, then cached |
|---|---|---|
| Geometry, attributes, `ASSETGROUP`/`ASSETTYPE` | yes | |
| Associations rows | yes (Modify Associations, Import Associations, arcpy, attribute rule, `applyEdits`) | |
| `ASSOCIATIONSTATUS` on features | | maintained by the system when associations change |
| Network topology graph | | `Enable`, `Validate`, `Rebuild` |
| Network attribute values used by traces | | refreshed for dirty areas at each validate |
| System junctions (hidden junction where two same-type edges meet) | | validate/enable |
| Dirty areas and errors | | created by edits (edit bits) and by validate/enable/update subnetwork (error bits) |
| `SUBNETWORKNAME`, propagated values | | `Update Subnetwork` |
| Subnetworks table status, `SubnetLine` | | controller changes, validate, `Update Subnetwork` |
| `ISCONNECTED` | | `Update Is Connected` (traditional domain networks, topology enabled) |
| Diagrams | | diagram tools; marked inconsistent by validate |

Rule of thumb: a value that looks like an analytic result (subnetwork name, `ISCONNECTED`, a propagated phase) is a snapshot from the last run of its tool.

## 4. The life of an edit, step by step

Scenario used throughout (electric, illustrative): a crew adds a new fused cutout (a `Device`) on an existing overhead primary line in a medium-voltage feeder, in an enterprise deployment, edited through a feature service in a named branch version, with the network topology enabled. Gas, water and telecom differences are called out where the lifecycle bends.

```
 digitize ──> geodatabase-level logic ──> edit tracking ──> (more edits) ──> VALIDATE ──> UPDATE SUBNETWORK ──> TRACE
   (1)              (1)                       (3)                              (5)            (6)               (8)
   associations/terminals (2)        error dirty areas (5)          reconcile / post (9) ... publish/export (9)
```

### Step 0. Preconditions that decide everything else

- **Topology enabled?** If disabled, edits are *not tracked* (one dirty area covers the whole service territory, Status 0) and re-enabling validates all outstanding edits. Configuration tasks (rules, categories, terminal configurations, tiers, association roles) need it disabled; editing, validate, trace and update subnetwork need it enabled (Esri "Utility network management tasks").
- **Which version?** Enterprise branch versions are edited only through feature services. `Enable Network Topology` runs only on Default; `Validate` can run on Default or a named version by any user with edit permission on it.
- **Deployment:** single-user (file/mobile geodatabase, Pro only, one editor) behaves the same minus services and versions.

### Step 1. Digitize the feature (the geodatabase and the editor act)

What happens:
1. The editor chooses a feature template (or a **preset template** that places a group of features with their associations in one click, such as a pole with a transformer attached) and clicks the map. Snapping uses the network rules: Esri notes that snapping does not occur without a rule.
2. The feature goes into the right class by template; its **`ASSETGROUP`** (subtype field) and **`ASSETTYPE`** (domain) are set. The pair is the key that every rule, terminal configuration and category later looks up.
3. **Geodatabase-level logic fires inside the edit operation.** Attribute rules of the immediate kind evaluate on insert/update/delete: Esri documents the order as default values, then immediate calculation rules, then constraint rules. A calculation rule might populate the asset ID or phase; a constraint rule might refuse a device with no voltage class. Batch calculation and validation attribute rules are *deferred*: they run later through Error Inspector or `Evaluate Rules` (enterprise: a feature service with the Validation capability, `ValidationServer`) and write to error layers, not to dirty areas.
4. **Service territory check.** The service territory polygon restricts edits so features are not created outside the network area.
5. In an enterprise service, Pro or a web app sends the edit via `applyEdits` to the version in the `FeatureServer`; the `VersionManagementServer` holds the version context.

Component acting: feature dataset, class, subtype/domain, attribute rules, service territory, feature service.

Pitfall: attribute rules that read or write other network features can interact with the later `Update Subnetwork` edit mode (section 4 step 6).

### Step 2. Connectivity edits: geometry, terminals, associations

The new cutout must actually be connected. Which mechanism applies depends on what the class pair allows.

- **Geometric coincidence (most overhead/pipe devices).** The cutout is snapped to the line at an end vertex or midspan. Which positions are legal is set per asset type by the **edge connectivity policy** (`Set Edge Connectivity`: Any vertex or End vertex). Whether the pair may connect at all is set by **junction-edge** or **edge-junction-edge** network rules, always within **feature restrictions**.
- **Terminals.** If the cutout's asset type has a terminal configuration (for example "Line Side / Load Side"), the line-to-device terminal is set with the *Modify Terminal Connections* pane or the snap chip, which updates `FROMDEVICETERMINAL` / `TODEVICETERMINAL` on the line. With exactly one allowed terminal for the rule, validate fills these in automatically. Terminal-enabled features cannot sit midspan on a line; split the line or use a terminal-free junction.
- **Associations.** If the cutout also sits inside a vault (containment) or on a pole (structural attachment), the editor uses *Modify Associations*, `Import Associations`, arcpy, an attribute rule, or `applyEdits` against the Associations table. Network rules are enforced in the pane and the import tool; the import tool fails if no rule supports the association. `applyEdits` can skip validation with `applyEditsOptions {"utilityNetworkOptions":1}`; invalid rows are then flagged by the next validate (REST appendix).
- **Nonspatial objects (junction objects, edge objects).** They join the network only through associations; they are *locatable* only if some association path reaches a spatial feature.

Component acting: edge connectivity policy, feature restrictions, network rules, terminal configuration, Associations table.

Pitfall: a clean-looking map is not evidence of connectivity. With no rule, nothing connects (see step 5).

### Step 3. Edit tracking creates dirty areas

When the topology is enabled, the edit is recorded as an **edit dirty area**:

- Triggers (Esri's list of edit dirty areas): a change to geometry, to the `ASSETGROUP`/`ASSETTYPE` fields, to a field defined as a **network attribute**, to an association, or to terminal configuration information. Esri lists no other edit types, so other attribute edits do not create a dirty area.
- A geometry change makes **two** dirty areas: the old envelope and the new geometry.
- The `Status` field is a bitmask: 0 topology disabled, 1 inserted/updated, 2 deleted, 4 associated objects modified, 8 feature error, 16 object error, 32 subnetwork error (values add: a modified feature in error is 9). Use `scripts/decode_dirty_status.py` to decode.
- Edits to a **locatable** nonspatial object create a dirty area on the first spatial feature in its containment hierarchy; edits to **unlocatable** objects create none, so they are invisible to the topology until you disable and re-enable it.
- Telecom domain networks also write a row to the **dirty objects table** for nonspatial objects and associations.

Nothing about connectivity has changed yet. The map shows the new cutout; the topology does not know it.

Component acting: dirty areas layer (system), editor tracking, dirty objects table (telecom).

Pitfall: a trace run now may pass "through" the new cutout in the map sense but is answered from the old graph. Esri says tracing through a dirty area is allowed but may give unexpected results; the Trace tool's **Validate Consistency** option (unchecked by default in the Pro tool; the REST `validateConsistency` default is true, see `rest-api/08-trace-configuration-full-schema.md`) makes the trace error if it meets a dirty area.

### Step 4. More edits accumulate (nothing validates itself)

Validation is **never automatic after each edit** (Esri: "Validation is not automatic"). Dirty areas keep accumulating. In an enterprise version you may save, undo/redo through the version management service, and keep editing. The network stays editable and traceable while another session validates on Default (only one validation at a time on Default).

### Step 5. Validate Network Topology

Invoked with the Validate command (synchronous, current extent) or the `Validate Network Topology` tool (asynchronous on enterprise via the system `UtilityNetworkTools` geoprocessing service, which has a longer time-out; the tool input must be a utility network *service*). REST: `UtilityNetworkServer/validateNetworkTopology`.

What the engine does, in order of principle (Esri documents the outcomes; the internal order is not published):

1. Selects dirty areas that intersect the chosen **extent** (Current Extent or Entire Extent). Esri's tool page says dirty areas that intersect the extent are clipped; an Esri blog (Pro 2.5 era) adds that association dirty areas and update-subnetwork error dirty areas are exceptions evaluated whole. Re-test on current builds.
2. Re-reads the edited features and objects, rechecks **feature restrictions**, **network rules** and **edge connectivity policies**, and rebuilds connectivity from geometric coincidence and associations. Two edges of the same asset group and asset type meeting at an end get an invisible **system junction** with no rule needed.
3. Refreshes the **cached network attribute values** for the affected area.
4. Where a rule is missing or a restriction is broken, it writes an **error dirty area** (bits 8, 16 or 32) with an error ID and message (message trimmed at 512 characters) instead of connecting.
5. Runs a trace to discover **which subnetworks the edit affects**; those controller rows and `SubnetLine` records are marked **Dirty** and their system diagrams become inconsistent. The REST response lists them as `discoveredSubnetworks`; the GP tool returns them in an Output JSON string. In hierarchical tiers, if every subnetwork in a tier is already dirty, that tier is not traced.
6. Clears the edit dirty areas it processed. Error-only dirty areas (no edit bit, i.e. none of Status values 1, 2 or 4) are ignored by later validates: they stay until you fix the cause (geometry, attribute, rule or subnetwork definition; some fixes need the topology disabled).

Result for our cutout: if a junction-edge rule allows (cutout asset type, line asset type) and the terminal is unambiguous, it is now in the topology and the dirty area clears. If no rule exists, error 8 "No connectivity rule" is recorded and the cutout stays disconnected. After this step the feeder's subnetwork is **Dirty**.

Component acting: network rules, feature restrictions, edge connectivity policy, terminals, topology graph, network attributes cache, dirty areas, subnetwork status.

Pitfalls: (a) a successful job does not mean zero errors; look at the Dirty Areas layer or Error Inspector; (b) the topology reflects "the last time each area was enabled or validated"; (c) if Validate cannot complete, `Rebuild Network Topology` ignores dirty areas and rebuilds all features in an extent, but Esri says it should not be the default response; (d) `Enable Network Topology` has a "Maximum number of errors" parameter (default 10000) and an "Only generate errors" mode for pre-checks.

### Step 6. Update Subnetwork

`Update Subnetwork` (traditional domain networks only) is the step that makes subnetwork *records* agree with the topology. REST: `UtilityNetworkServer/updateSubnetwork`.

Preconditions Esri states: save edits, topology enabled, and **no dirty areas intersecting the subnetwork's features**.

1. Traces from every controller of the subnetwork in the given tier using the tier's **subnetwork definition** and its subnetwork trace configuration (valid features, barriers, propagators).
2. If a connected feature type is not in the tier's valid lists, or consistency checks fail, the update errors (subnetwork errors, error IDs 24 to 47), the controllers become **Invalid**, and invalid subnetworks are skipped on later runs until fixed and validated again.
3. On success, writes **`SUBNETWORKNAME`** and **propagated values** to the features (Default version: all traversed features; a named version "without eventing": only features edited in that version), also `SUPPORTEDSUBNETWORKNAME`/`SUPPORTINGSUBNETWORKNAME` on containers/content depending on the update policy.
4. Creates, updates or removes the **`SubnetLine`** record (aggregating only the lines the subnetwork definition lists), updates the **Subnetworks table** status to **Clean**, and rebuilds the **subnetwork system diagram** if the definition names a template.
5. **Edit mode** decides whether this write honours geodatabase contracts: *Without Eventing* (default, set per default and named version in `Set Subnetwork Definition`) does not use eventing; *With Eventing* applies geodatabase behaviour such as attribute rules and editor tracking (Esri). Esri's pages read do not document the performance cost, history behaviour or any lock taken: Verify against the Esri docs for your version before advising on blocking or reconcile.

Result for our cutout: the new cutout carries the feeder's `SUBNETWORKNAME`; the feeder row is Clean.

Component acting: tiers, subnetwork definition, controllers, Subnetworks table, `SubnetLine`, diagram templates.

Pitfalls: update one subnetwork per process; do not run "All subnetworks in tier" in several simultaneous processes (two processes updating the same subnetwork can fail); in tiers whose update policy does not manage `Is dirty`, every subnetwork looks Dirty; `Invalid` status needs Enterprise 11.1+ in enterprise.

### Step 7. Optional derived updates

- **`Update Is Connected`** refreshes `ISCONNECTED` on all features (connected to a subnetwork controller or not); new features start Unknown. Traditional domain networks only.
- **Diagrams**: `Update Diagram` makes non-system diagrams consistent; update subnetwork handles system diagrams.

### Step 8. Trace

A trace reads the **topology graph** (a cached, paged binary graph that is faster than querying features) plus cached network attribute values, then applies the **trace configuration**: traversability (what is currently allowed, such as open or closed devices), barriers, categories, functions, propagators and output filters. Starting points are features (with terminals where relevant) or points on edges. Over services the trace uses the saved state of the chosen version; Pro's *Trace* tool takes a utility network service in enterprise, not a database connection. Subnetwork, upstream, downstream and isolation trace types apply to traditional domain networks only; telecom uses path and circuit traces.

Result for our cutout: a downstream trace from the feeder breaker now includes it, because step 5 connected it. A **subnetwork** trace additionally honours the tier's configuration.

Component acting: topology, trace configuration (named trace configurations are stored from dataset v5), network attributes/categories.

### Step 9. Reconcile, post, publish, export

- **Reconcile.** A named version inherits Default's topology state; dirty areas are re-created for features edited in the named version, and must be validated before posting. `SubnetLine` is considered in reconcile.
- **Post.** Moves the version's edits into Default. `SubnetLine` is *not* carried by post: after a post, dirty areas are created in Default; validate there, then update subnetworks in Default to refresh `SubnetLine`.
- **Export.** `Export Subnetwork` writes a JSON file for external systems (outage management, asset tracking); only Clean subnetworks are eligible. With "Set export acknowledged" it also stamps `LASTACKEXPORTSUBNETWORK` and removes rows for deleted controllers.
- **Publishing.** The UN layers are published as a map image with Feature enabled referencing registered data (branch versioned); the Utility Network and Network Diagram services are enabled automatically. Definition queries and hidden fields are not supported on UN layers. Create/publish/edit needs the Advanced Editing user type extension; query and trace do not.

Component acting: `VersionManagementServer`, `UtilityNetworkServer`, `FeatureServer`, `NetworkDiagramServer`.

### 4.1 One-page recap table

| Step | Actor | Output | State after |
|---|---|---|---|
| 1 Digitize | Editor, attribute rules, service territory | Feature with `ASSETGROUP`/`ASSETTYPE` | In the database, not in the topology |
| 2 Connect | Snapping, edge connectivity policy, rules, terminals, Modify Associations | Coincidence, terminal fields, association rows | Intended connectivity recorded as geometry/rows |
| 3 Track | Topology-enabled edit tracking | Edit dirty area(s), Status 1/2/4 | Map and topology disagree |
| 4 Accumulate | Editors | More dirty areas | Same |
| 5 Validate | `Validate Network Topology` | Topology updated; error dirty areas; subnetworks marked Dirty; diagrams inconsistent | Topology matches map except for errors |
| 6 Update subnetwork | `Update Subnetwork` | Subnetwork names, propagated values, `SubnetLine`, status Clean/Invalid | Stored subnetwork data matches topology |
| 7 Derived | `Update Is Connected`, `Update Diagram` | `ISCONNECTED`, diagrams | Snapshots refreshed |
| 8 Trace | Trace tool / `trace` REST | Result per configuration | Read-only |
| 9 Version and publish | Reconcile, post, export | Default version consistent; export JSON | Shared state |

## 5. Variations on the lifecycle

**Bulk loads and configuration.** Esri's tasks page recommends importing large numbers of associations or subnetwork controllers while topology is disabled; disabling creates one dirty area over the whole territory and re-enabling validates everything outstanding. Rules, categories, terminal configurations, tiers, association roles, network attributes and domain networks can only be changed with topology disabled, connected to the Default version as the database utility network owner with the portal owner signed in (enterprise). Some changes are only possible before the **first** enable (deleting terminal configurations, unassigning terminal assignments, unassigning association roles).

**Named versions.** Dirty areas are per version; validate in the named version before posting; subnetwork updates in a named version default to features edited in that version unless the definition uses eventing/with-events mode.

**Telecom (dataset v8).** No terminals, no subnetworks, no `Update Subnetwork`. Junction-edge connectivity and containment on nonspatial classes use foreign-key fields (`FromGlobalID`, `ContainerGlobalID`, ...) instead of Associations rows; a dirty objects table tracks nonspatial edits; circuits (`Circuit`, `CircuitSection`, `Subcircuit`) are verified with `Verify Circuits`. See `rest-api/07-circuits-and-unit-identifiers-telecom.md`.

**Single-user.** No services: all tools run in Pro; no versions; good sandbox for rule and tier design.

## 6. Which parts differ for gas, water, electric and telecom

The engine and the lifecycle are identical; what differs is domain-network type, flow model, tier layout, signature devices and typical traces. "Esri" marks statements from Esri help or Esri-staff blogs; "illustrative" marks common patterns, not requirements.

| | Electric | Gas | Water | Wastewater / stormwater | Telecom |
|---|---|---|---|---|---|
| Domain network type | Traditional | Traditional | Traditional | Traditional | Telecom (v8+) |
| Controller type | Source (breakers, transformers) | Source (wells, compressors, regulators, meters) | Source (plants, pumps, tanks) | Sink (treatment plants, outlets) | n/a |
| Tier definition | Partitioned typical (Esri) | Hierarchical typical (Esri) | Hierarchical typical (Esri) | Hierarchical in Esri Foundations (see industry file) | n/a |
| Esri tier examples | Transmission rank 1, medium voltage rank 2, low voltage rank 3; MV controller a circuit breaker, LV a distribution transformer or network protector | Gas System, Gas Pressure, Gas Isolation, Cathodic Protection (Esri blog); isolation nested in pressure nested in system | System / Pressure / Isolation style nesting; verify against the Water Foundation | Sewer collection system and sewershed style nesting; verify | none; circuits instead |
| What a "subnetwork" is | Circuit / feeder | Pressure zone, isolation zone | Pressure zone, isolation zone | Drainage area to an outlet | none |
| Terminals matter for | Transformers, breakers, regulators (high/low side, line/load side) | Regulators, compressors (inlet/outlet, directional) | Pumps, PRVs | Pumps, outlets | not supported |
| Signature special structures | Phase propagation and substitution, taps, protective categories, poles via attachment | Isolation valves, cathodic protection tier | Valve isolation | Gravity mains, upstream (contributing area) traces | Grouped edge objects (e.g. 96 strands in one record), unit IDs, color schemes, wavelengths, circuits |
| Typical traces | Upstream/downstream, subnetwork, loops, isolation | Isolation, subnetwork | Isolation, subnetwork, upstream/downstream | Upstream and downstream | Path, circuit, connectivity inference |


Practitioner guidance: choose partitioned for strictly sequential, disjoint voltage or pressure levels where a feature belongs to exactly one level; choose hierarchical when a pipe legitimately belongs to a system, a pressure zone and an isolation zone at once. Remember that this choice is made when the domain network is added and cannot be changed afterwards.

## Common misconceptions

- "Snapped means connected." Coincidence connects only if a rule exists and a validate has run. Without a rule the pair gets an error and stays disconnected.
- "Saving or posting validates." Validation is never automatic. Esri says to validate the dirty areas re-created by a reconcile before posting, and that posting is blocked until the version is reconciled again (dirty areas page).
- "A finished Validate job means no errors." Error dirty areas remain until the cause is fixed.
- "Subnetworks are polygons I draw." They are traced from controllers and recorded by `Update Subnetwork`; `SubnetLine` is read-only and system generated.
- "The subnetwork name is live." It is a stored snapshot from the last `Update Subnetwork`; traces see new connectivity right after validate, the stored names do not.
- "Containers carry flow." Esri: resources do not flow through containers; a trace can return contained devices without returning the container.
- "Terminals are required everywhere." They are optional (default is Single Terminal) but required for subnetwork controllers; telecom domain networks do not support terminals.
- "Topology type (mesh/radial) changes tracing." Esri states it currently makes no difference to tracing or subnetwork management.
- "More tiers is free." A UN can hold at most 63 tiers across all domain networks.

## Quick checks

Ask or verify, in this order:
1. Enterprise or single-user? Default or named version? UN dataset version, Pro and Enterprise versions?
2. Is the topology enabled in the version being edited? When was the area last validated? Are there dirty areas (any Status) near the feature?
3. Is the feature's `ASSETGROUP`/`ASSETTYPE` pair covered by a rule (and a feature restriction) for the intended relationship? Was the relationship geometric, terminal-based or association-based?
4. Is the answer in question a stored snapshot (subnetwork name, `ISCONNECTED`, diagram) and has its tool run since validate?
5. Which controller and tier own the subnetwork, and what does the Subnetworks table say about Clean/Dirty/Invalid?
6. Did the trace use Validate Consistency, a named trace configuration, the right version, the right starting point (and terminal)?
7. Who is connected as which owner, and does the portal account hold the Advanced Editing user type extension (needed to create, publish, edit; not to query or trace)?

## Related files

- `learn/02-data-model-in-depth.md` (schema, terminals, associations, system tables)
- `learn/03-topology-engine-and-validation.md`, `learn/06-tiers-and-subnetworks-in-depth.md`
- `pro-help/01-core-concepts-and-vocabulary.md`, `pro-help/02-structure-of-a-utility-network.md`, `pro-help/04-associations-editing-errors.md`, `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/05-tracing.md`
- `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/04-version-management-validation-feature-service.md`, `rest-api/05-feature-service-associations-appendix.md`
- `scripts/decode_dirty_status.py`, `scripts/association_types.py`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/what-is-a-utility-network-.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/benefits-of-the-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-vocabulary.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/structure-of-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/traditional-domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/telecom-domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/geometric-concident-based-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/create-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/associations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/containment.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/nonspatial-objects.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/device-terminals.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-life-cycle.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetline-feature-class.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-hierarchies-with-tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-compatibility.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-is-connected.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-edge-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-domain-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/evaluate-attribute-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/an-overview-of-attribute-rules.html
- https://developers.arcgis.com/rest/services-reference/enterprise/overview-of-utility-network-services/
- https://developers.arcgis.com/rest/services-reference/enterprise/appendix-working-with-the-feature-server-utility-network-server/
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/creating-gas-subnetworks (Esri staff blog)
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/enable-unbalanced-distribution-subnetworks.htm
- https://resources.esri.ca/arcgis/5-differences-between-the-geometric-network-and-the-utility-network (partner guidance, not Esri documentation)
