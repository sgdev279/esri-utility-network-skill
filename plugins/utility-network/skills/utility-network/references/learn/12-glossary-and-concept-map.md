# Utility Network: Glossary and Concept Map
> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Read this when you meet a Utility Network (UN) word you cannot place, when two people use different words for the same thing (Pro versus REST versus code versus the old geometric network), or when you need a reading order. It is a lookup and orientation file: every entry points to the file that teaches the mechanism, so the definitions are deliberately one line. Builds on `pro-help/01-core-concepts-and-vocabulary.md` and `pro-help/02-structure-of-a-utility-network.md`. Sources: the reference files linked in each row (which carry the Esri URLs they were built from) plus the Esri geometric network vocabulary page listed at the end. Domain-neutral: no per-industry vocabulary tables (a later release). Nothing here is new research; where the linked files say "verify against the Esri docs for your version", that caveat carries over.

## Contents
1. Concept map (one page)
2. A-Z glossary (about 140 terms)
3. Same thing, different names (Pro, REST, JS, C#, arcpy)
4. Foundation and geometric-network vocabulary mapped to UN terms
5. The commonly confused pairs, side by side
6. Suggested learning paths (analyst, administrator, developer)
7. Common misconceptions, quick checks, related files, sources

## 1. Concept map (one page)

Read top to bottom: what you design (schema), what you edit (data), what the engine derives (state), and what you ask (analysis). Arrows mean "is used by" or "produces". Section numbers refer to `learn/` files in brackets.

```
 STORED SCHEMA / CONFIGURATION (topology DISABLED, DEFAULT version, owners)      [02, 04, 05, 06, 13]
 ----------------------------------------------------------------------------
 Geodatabase -> Feature dataset -> Service territory (m/z polygon: edit boundary)
                                -> UTILITY NETWORK (one per dataset)
   STRUCTURE NETWORK (exactly 1)          DOMAIN NETWORK(S) (traditional or telecom)
    StructureJunction/Line/Boundary         Device, Line, Junction, Assembly, SubnetLine
    + 2 object tables                       + JunctionObject, EdgeObject tables
        |    (no flow, no tiers)                |  (telecom: 4 fc + 5 tables, no tiers/subnetworks)
        |                                       |
        +------ every class: ASSETGROUP (subtype) -> ASSETTYPE (domain) ------+
                         |   the PAIR is the key for:                          |
        terminal configuration | network category | association role | edge connectivity policy
        network RULES (5 types, from/to/via + terminals) <- limited by FEATURE RESTRICTIONS
        network ATTRIBUTES (field -> engine) | ATTRIBUTE RULES (Arcade, run by the geodatabase)
        TIER GROUP (hierarchical only) -> TIER -> SUBNETWORK DEFINITION (valid lists, barriers, outputs)

 DATA YOU EDIT (any state; enterprise: named branch version via feature service)   [01, 08]
 ----------------------------------------------------------------------------
 features / nonspatial objects (GlobalID identity)
   connected by:  geometric coincidence (junction-edge, edge-junction-edge, system junction)
                  | connectivity association | containment | structural attachment   (rows in ASSOCIATIONS)
   every relationship needs a RULE that respects a FEATURE RESTRICTION; terminals refine ports
   a SUBNETWORK CONTROLLER = a terminal on a device / junction object, set per tier

 BOOKKEEPING AND DERIVED STATE (written by tools, never by hand)                  [01, 03, 06]
 ----------------------------------------------------------------------------
 edit  -> EDIT DIRTY AREA (STATUS 1/2/4) --Validate Network Topology--> NETWORK TOPOLOGY (one graph)
 rule gap / bad data -> ERROR DIRTY AREA (STATUS 8/16/32; error ID 0-47; ignored by validate until edited)
 validate also traces to mark affected subnetworks DIRTY
 Update Subnetwork -> SUBNETWORKNAME + propagated values on features, SUBNETLINE row, SUBNETWORKS table
                      row per controller (Clean / Dirty / Invalid), system diagram
 Update Is Connected -> ISCONNECTED          Update Diagram -> non-system diagrams

 QUESTIONS YOU ASK (read the topology + cached network attribute values)           [07]
 ----------------------------------------------------------------------------
 TRACE = type (connected, subnetwork, upstream, downstream, isolation, loops, path, circuit, ...)
       + starting/stopping points + TRAVERSABILITY (condition/function barriers, propagators)
       + FILTERS (filter barriers, trace-only) + includes (containers, content, structures)
       + OUTPUT filters/conditions + functions + result types; saved as a NAMED TRACE CONFIGURATION

 SURFACES                                                                          [08, 13, 14]
 ----------------------------------------------------------------------------
 Pro (tab, panes, GP tools) | arcpy.un | Pro SDK (C#) | REST services (UtilityNetworkServer,
 FeatureServer, VersionManagementServer, ValidationServer, NetworkDiagramServer, UtilityNetworkTools)
 | JS Maps SDK | Experience Builder.  Single-user (file/mobile gdb) = Pro only, no versions, no services.
```

The four rules that explain most behaviour: (1) rules are default-deny; (2) edits reach the topology only through Validate; (3) subnetwork names and `ISCONNECTED` are snapshots refreshed only by their own tools; (4) schema changes need topology disabled, DEFAULT, and both owner connections.

## 2. A-Z glossary

Columns: **Shows up as** lists where you will see the term (Pro label, REST property, code name, arcpy parameter, system table field). **Floor** is a version floor only where the linked file states one. "Link" is the file to read next. Entries marked (telecom) apply to telecom domain networks.

| Term | One-line definition | Shows up as | Floor | Watch out / link |
|---|---|---|---|---|
| Aggregated lines | Subset of a tier's valid lines merged into the SubnetLine geometry | Set Subnetwork Definition "Aggregated Lines" | | Must be inside Valid Lines and have geometry. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Allow indeterminate flow | Whether features with unresolved flow are traced or excluded in upstream/downstream/isolation | Pro "Allow Indeterminate Flow"; REST `allowIndeterminateFlow` | UN v5+ | REST page states no default: send it. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Apportionable | Double network attribute option that splits a line's value across its edge elements | Add Network Attribute; arcpy `isApportionable` | | Double only; `Shape length` is apportionable. `learn/05-attributes-categories-and-attribute-rules.md` |
| Assembly | Point class that shows a group of devices as one symbol and usually acts as a container | `<Name>Assembly`; `SourceUsageType` Assembly | | No terminals; carries no flow. `learn/02-data-model-in-depth.md` |
| Asset group | Major classification; the class's subtype | `ASSETGROUP`; arcpy `from_assetgroup`; C# `AssetGroup`; REST `assetGroupCode` | | Not the asset type; rules key on the pair. `learn/02-data-model-in-depth.md` |
| Asset package | Geodatabase package carrying a Foundation schema, rules and sample data | Stage Utility Network, Apply Asset Package, Export Asset Package | | Config path, not an edit path. `pro-help/08-asset-packages-foundations-migration.md` |
| Asset type | Minor classification; a coded value domain per asset group | `ASSETTYPE`; REST `assetTypeCode`; C# `AssetType` | | Domain values cannot be deleted later. `learn/02-data-model-in-depth.md` |
| Association | Non-geometric relationship stored as a row: connectivity, containment or attachment | Associations table; Modify Associations pane | | Not a relationship class. `learn/02-data-model-in-depth.md` |
| Associations table | Hidden system table of association rows (22 fields) | `associationsTableId` (example 500001) | | Read IDs from `systemLayers`. `rest-api/05-feature-service-associations-appendix.md` |
| `ASSOCIATIONSTATUS` | System-maintained field encoding the feature's association role and content visibility | Field on every class | | Read-only; drives Select Associated Data. `learn/02-data-model-in-depth.md` |
| `ASSOCIATIONTYPE` | Codes 1-6: junction-junction, containment, attachment, junction-edge From/midspan/To | Associations table; REST `applyEdits` | subtype from v6 | `scripts/association_types.py` |
| Attribute rule | Arcade rule stored in the geodatabase: calculation, constraint or validation | Add Attribute Rule; `$feature`, `$originalfeature` | Pro 2.1+ | Not a network rule or network attribute. `learn/05-attributes-categories-and-attribute-rules.md` |
| Attribute substitution | System network category: attributes whose value is swapped for tap features | Network categories list | | Needs propagation. `learn/05-attributes-categories-and-attribute-rules.md` |
| Barrier (feature barrier) | A trace location you place that stops the trace there | REST `traceLocationType` "barrier"; Pro Barriers tab | | Not a condition barrier. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Batch rule | Attribute rule evaluated on demand, not on edit | Evaluate Rules; `ValidationServer` `evaluate` | | Validate Network Topology does not run it. `learn/05-attributes-categories-and-attribute-rules.md` |
| Bidirectional | Terminal-configuration directionality with no upstream/downstream | Add Terminal Configuration | | Controller use depends on tier definition. `learn/02-data-model-in-depth.md` |
| Big integer | Network attribute data type | Add Network Attribute | UN v7+ | `learn/05-attributes-categories-and-attribute-rules.md` |
| Branch versioning | Geodatabase versioning model required for enterprise UN editing through services | VersionManagementServer | | Single-user gdbs are unversioned. `learn/08-versioning-and-editing-workflows.md` |
| Circuit (telecom) | Defined path managed through Circuit, CircuitSection and Subcircuit tables | Find/Create Circuit; `circuit` trace | v8; trace 12.1+ | Telecom has no subnetworks. `rest-api/07-circuits-and-unit-identifiers-telecom.md` |
| Clean | Subnetwork status: names, SubnetLine, Subnetworks row and diagrams match the topology | `ISDIRTY`; green check in Find Subnetworks | | Not "no dirty areas". `learn/06-tiers-and-subnetworks-in-depth.md` |
| Condition barrier | Tier or trace setting that stops where a network attribute/category expression is true | REST `conditionBarriers`; Set Subnetwork Definition | | Used by update and export too, unlike filters. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Connected trace | Connectivity-only trace; ignores terminal directionality and subnetwork definition | `traceType` `connected` | | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Connectivity association | Association types that join points or objects without coincidence (codes 1, 4, 5, 6) | Modify Associations > Connectivity | | Needs a rule. `learn/02-data-model-in-depth.md` |
| Container | Feature that holds content; resource does not flow through it | Association role "Container" | | Not a structure; not the Conflict Container category. `learn/02-data-model-in-depth.md` |
| Containment | Association type 2: From = container, To = content | Enter Containment; REST code 2 | | Rule direction matters. `learn/04-rules-and-connectivity-design.md` |
| Content | Feature held by a container; hidden by default | `ISCONTENTVISIBLE`; `includeContent` | | A point is content of at most one container. `learn/02-data-model-in-depth.md` |
| Controller (subnetwork controller) | A terminal on a device or junction object that is the origin (source) or destination (sink) of a subnetwork | Modify Controller pane; Subnetworks table row; arcpy `EnableSubnetworkController` | | Not "Source". Cannot be deleted once set. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Controller name | Name unique within a tier for one controller | `SUBNETWORKCONTROLLERNAME` | | Not the subnetwork name. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Database utility network owner | Database login that created the network | The connection you open the dataset through | | Not the portal owner (errors 001400 vs 002144). `learn/13-arcgis-pro-fundamentals-and-workflow.md` |
| DEFAULT | The shared version; structure changes and Enable run only here | `sde.DEFAULT`; `gdbVersion` | | Named versions inherit its topology state. `learn/08-versioning-and-editing-workflows.md` |
| Device | Point class for operational features; can have terminals; can be a controller | `<Name>Device`; `SourceUsageType` Device | | Not a junction. `learn/02-data-model-in-depth.md` |
| Diagram, diagram template | Schematic generated from topology by a template | Network Diagram tab; `NetworkDiagramServer` | | System diagrams go inconsistent on validate. `pro-help/07-network-diagrams.md` |
| Dirty (subnetwork status) | Validated edits not yet processed by Update Subnetwork | `ISDIRTY`; yellow in Find Subnetworks | | Not a dirty area. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Dirty area | Record that a footprint of edit space is not yet in the topology; also stores errors | Dirty Areas sublayer; `dirtyAreasLayerId` | | `learn/03-topology-engine-and-validation.md` |
| Dirty objects table (telecom) | Tracks edits to nonspatial objects and associations | `dirtyObjectsTableId` | with telecom | `learn/02-data-model-in-depth.md` |
| Directional | Terminal configuration with at least one upstream terminal | Add Terminal Configuration | | Partitioned controllers need it. `learn/02-data-model-in-depth.md` |
| Disjoint subnetwork | Same-named controllers that cannot reach each other | Support Disjoint Subnetwork; error 28 | | Hierarchical always allows. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Domain network | Industry-specific class group inside a UN: traditional or telecom | Add Domain Network; `DomainNetwork` | | Not an attribute domain. `learn/02-data-model-in-depth.md` |
| Downstream | Direction away from controllers in a source network, toward them in a sink network | `traceType` `downstream` | | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Edge connectivity policy | Per line asset type: connect at Any vertex or End vertex | Set Edge Connectivity; error 13 | | Separate from rules. `learn/04-rules-and-connectivity-design.md` |
| Edge element | Piece of a line inside the topology, split at midspan connections | Function counts; trace result sizing | | Terminals count as junction elements. `learn/10-performance-scale-and-operations.md` |
| Edge object | Nonspatial edge row (for example a strand in a cable) | `<Name>EdgeObject` | UN v4+ | Not a junction object. `learn/02-data-model-in-depth.md` |
| Edge-junction-edge rule | Rule letting two lines connect through an intermediate junction or device | Add Rule type; "Via" fields | | Junction-edge is honoured first. `learn/04-rules-and-connectivity-design.md` |
| Edit mode | Whether Update Subnetwork honours geodatabase contracts: without eventing (default) or with | Set Subnetwork Definition | UN v4+ (verify against the Esri docs for your version) | With eventing fires attribute rules, holds a shared lock on DEFAULT. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Element | Lightweight handle: source + GlobalID (+ terminal) | C# `Element`; REST `elements` result; JS `NetworkElement` | | Not a feature row. `learn/14-developer-surfaces-and-sdk-fundamentals.md` |
| Enable Network Topology | Builds the topology; writes existing errors as dirty areas | Tool; REST `enableTopology` | | Cap 10000 errors default. `learn/03-topology-engine-and-validation.md` |
| Error dirty area | Dirty area carrying an error bit (8, 16, 32) | Dirty Areas `STATUS` | | Validate ignores it unless an edit bit is present. `learn/03-topology-engine-and-validation.md` |
| Error ID | Number 0-47 naming an enable/validate/update-subnetwork error | Pop-up `Error(s)`; message text | | Ten IDs undocumented. `learn/09-failure-anatomy-symptom-to-fix.md` |
| `ERRORCODE` | Bitmask on dirty areas and associations; error ID = log2 of a single bit | Dirty Areas table | big integer from v7 | Combined values are practitioner reading. `learn/09-failure-anatomy-symptom-to-fix.md` |
| Error Inspector | Pane listing errors; Map Extent filter on by default | Network Topology group | UN v4+ | Omits `Status`/`Error code`. `learn/13-arcgis-pro-fundamentals-and-workflow.md` |
| Export Subnetwork | Writes a Clean subnetwork to JSON; optional acknowledgment | Tool; REST `exportSubnetwork` | related records 11.5+; flow dirs 12.1+ | Acknowledgment: DEFAULT, portal owner. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Feature restriction | Built-in class-level limit on which classes may relate; cannot be changed | Feature restrictions page | | Rules cannot override. `learn/04-rules-and-connectivity-design.md` |
| Filter barrier | Barrier evaluated after traversability, in traces only | REST `filterBarriers`; Pro Filter Barrier | | Isolation needs one. `learn/07-tracing-in-depth-and-configuration-library.md` |
| `FLOWDIRECTION` | Persisted digitized-direction attribute: with, against, indeterminate | Field on lines and edge objects | UN v7+ | Not the `flowDirection` returned in results. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Foundation | Esri Solutions predefined data model: schema, rules, categories, attribute rules | Asset package; data dictionary | | Names change by release. `pro-help/08-asset-packages-foundations-migration.md` |
| Function | Summarises attribute values over traced features | REST `functions[]`; `globalFunctionResults` | | Reports; does not stop. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Function barrier | Stops the trace when a running total crosses a threshold | REST `functionBarriers`; `useLocalValues` | | `learn/07-tracing-in-depth-and-configuration-library.md` |
| `FROMDEVICETERMINAL` / `TODEVICETERMINAL` | Terminal IDs at the devices at a line's two ends | Fields on `Line` | | Not flow direction; do not hand-edit. `learn/02-data-model-in-depth.md` |
| Geometric coincidence | Features connect because they sit at the same place within tolerance | Snapping; Validate | | Needs a rule. `learn/02-data-model-in-depth.md` |
| Geometric network | Legacy desktop-era network model; connectivity implied by geometry | ArcMap era | | `learn/01-mental-model-and-life-of-an-edit.md` |
| GlobalID | GUID that identifies a row; the UN relates things by it | `FROMGLOBALID`; REST `globalId` | | Never key on ObjectID. `learn/02-data-model-in-depth.md` |
| Grouped object (telecom) | One row for a unit range via `FirstUnit`/`LastUnit` | Edge/junction object fields | v8 | `rest-api/07-circuits-and-unit-identifiers-telecom.md` |
| Hierarchical | Tier definition where tiers nest and a feature can be in several | Add Domain Network | | Choice is permanent. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Include containers/content/structures | Trace and definition flags adding those features to results or name stamping | `includeContainers` etc. | defs UN v5+ | All off by default. `learn/07-tracing-in-depth-and-configuration-library.md` |
| In Line | Network attribute stored inside the topology instead of read from the table | Add Network Attribute; arcpy `isEmbedded` | | 64-bit budget, 25 user bits (Pro 3.0+ datasets). `learn/05-attributes-categories-and-attribute-rules.md` |
| Indeterminate flow | Flow that cannot be resolved (loops, meshes, several sources) | `allowIndeterminateFlow` | UN v5+ | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Invalid | Subnetwork status after an update error; skipped until made Dirty | `ISDIRTY` = Invalid; red | UN v4; Ent 11.1+ (Esri's life-cycle page names no Pro version; verify against the Esri docs for your version) | `learn/06-tiers-and-subnetworks-in-depth.md` |
| `ISCONNECTED` | Snapshot: is the feature connected to a controller | Field; Update Is Connected | traditional only | `learn/01-mental-model-and-life-of-an-edit.md` |
| Isolation trace | Finds the operable features that cut a location off | `traceType` `isolation` | | Requires a filter barrier. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Junction | Point class for connectivity without effect on the resource; no terminals | `<Name>Junction` | | Not a device. `learn/02-data-model-in-depth.md` |
| Junction object | Nonspatial object (port, rack); can have terminals and be a controller | `<Name>JunctionObject` table | UN v4+ | Not an edge object. `learn/02-data-model-in-depth.md` |
| Junction-edge rule | Rule for a point meeting a line (or an edge object by association) | Add Rule type | | Honoured before edge-junction-edge. `learn/04-rules-and-connectivity-design.md` |
| Junction-junction | Rule or association type 1 joining two points/objects | Add Rule type | | `learn/04-rules-and-connectivity-design.md` |
| Line | Linear class that carries the resource | `<Name>Line` | | `FROMDEVICETERMINAL`. `learn/02-data-model-in-depth.md` |
| Locatable / unlocatable | Whether an association path reaches a spatial feature | Validate Locatability | | Unlocatable edits make no dirty area. `learn/02-data-model-in-depth.md` |
| Loops trace | Finds loops from a single starting point | `traceType` `loops` | | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Manage IsDirty | Tier option: whether status tracks Clean/Dirty | Set Subnetwork Definition | UN v5+ | Off means always Dirty; no Export. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Mesh / Radial | Tier topology type | Add Tier | | Esri: currently no effect. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Midspan | Connecting to a line's interior without splitting it | Any vertex policy; association code 5 | | Terminal devices cannot be midspan (error 38). `learn/04-rules-and-connectivity-design.md` |
| Moment | A point in time at which a version had a state | REST `moment`; `queryNetworkMoments` | | Unit varies by operation. `learn/08-versioning-and-editing-workflows.md` |
| Named trace configuration | Trace stored in the UN, run by name or GlobalID | Add Trace Configuration; `traceConfigurationGlobalId` | UN v5+ | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Named version | Branch off DEFAULT for isolated edits | Versioning tab; `create` | | One level only. `learn/08-versioning-and-editing-workflows.md` |
| Network attribute | Named definition mapped to one field per class so the engine can read it | Add/Set Network Attribute; `Describe(un).networkAttributes` | | Not a field, not an attribute rule. `learn/05-attributes-categories-and-attribute-rules.md` |
| Network category | Tag on an asset group/type used by tools and traces | Add/Set Network Category | | Set replaces the whole list. `learn/05-attributes-categories-and-attribute-rules.md` |
| Network rule | Admin-defined permission for a pair to connect, contain or attach (5 types) | Add Rule; Rules table | | Default-deny. `learn/04-rules-and-connectivity-design.md` |
| Network source, source ID | A registered class or table and its numeric ID | `FROMNETWORKSOURCEID`; REST `networkSourceId`; C# `NetworkSource` | | Not the controller type "source". `learn/02-data-model-in-depth.md` |
| Network topology | The persisted indexed graph that traces and diagrams read | Network Properties; `enableTopology` | | One per UN. `learn/03-topology-engine-and-validation.md` |
| Nonspatial object | Row without geometry that joins the network through associations | Object tables | UN v4+ | `learn/02-data-model-in-depth.md` |
| Nullable | Network attribute may be null; nulls count as zero cost; costs one In Line bit | Add Network Attribute | | `learn/05-attributes-categories-and-attribute-rules.md` |
| Output condition / output filter | Change what is reported, not where the trace goes | REST `outputConditions`, `outputFilters` | | Filtered features are still traced. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Partitioned | Tier definition where a feature belongs to one tier; tiers ranked in sequence | Add Domain Network | | Choice is permanent. `learn/06-tiers-and-subnetworks-in-depth.md` |
| `PARTITIONID` | Reserved field on all classes | Field | v8 | Not currently used. `learn/02-data-model-in-depth.md` |
| Path trace | Valid paths between points, optional stopping points | `traceType` `path` | Pro 3.7, Ent 12.1 | Replaces shortest path. `learn/07-tracing-in-depth-and-configuration-library.md` |
| `percentAlong` | Position 0-1 along an edge for a trace or midspan association | REST/JS location; `PERCENTALONG` | | Missing location property is silently ignored. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Portal utility network owner | Portal account signed in when the network was created | Network Properties > General | | Not the DB owner. `pro-help/10-publishing-ownership-licensing.md` |
| Post | Pushes a version's edits into DEFAULT | `post`; Versioning tab | | Does not validate; SubnetLine not posted. `learn/08-versioning-and-editing-workflows.md` |
| Propagator | Carries a value (phase, pressure) outward from controllers with a function and operator | `propagators`; `Propagated_BITWISE_AND` etc. | | Set per tier. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Propagator Resetter | Category: the feature's own values replace the propagated value | Network categories | UN v8 | `learn/05-attributes-categories-and-attribute-rules.md` |
| Rank | Order of a tier; 1 is highest | Add Tier | | Hierarchical: automatic per group. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Rebuild | Rebuilds topology in an extent, ignoring dirty areas | Rebuild Network Topology; `rebuild`/`forceRebuild` | Ent 10.9+ | Not routine. `learn/03-topology-engine-and-validation.md` |
| Reconcile | Pulls DEFAULT's changes into a version | `reconcile` | | Re-creates dirty areas; auto-commits. `learn/08-versioning-and-editing-workflows.md` |
| Rules table | Read-only system view of network rules | `rulesTableId` | | `learn/04-rules-and-connectivity-design.md` |
| Service territory | m/z polygon class bounding the network and restricting edits | Create Utility Network input | | Extent cannot be updated later. `learn/02-data-model-in-depth.md` |
| Session ID | Client GUID identifying an edit/read session on a version | `sessionId`/`sessionID` | | Required on named versions, omitted on DEFAULT. `learn/08-versioning-and-editing-workflows.md` |
| Single Terminal | Default configuration; behaves as if no terminals | Terminal Configuration | | `learn/02-data-model-in-depth.md` |
| Source / sink (controller type) | Whether the resource flows away from or toward controllers | Add Domain Network; C# `SubnetworkControllerCategory` | | Per domain network, permanent. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Starting point / stopping point | Where a trace begins; where a path ends | REST `traceLocationType`; `UN_Temp_Starting_Points` | stopping: Ent 12.1+ | `learn/07-tracing-in-depth-and-configuration-library.md` |
| `STATUS` (dirty areas) | Bitmask: 0 disabled, 1, 2, 4 edit; 8, 16, 32 error | Dirty Areas table | | Not Error ID 32. `scripts/decode_dirty_status.py` |
| Structural attachment | Association type 3: From = structure, To = attachment | Modify Associations > Attachment | | No terminals, no flow. `learn/02-data-model-in-depth.md` |
| Structure (role) | Association role allowed only on StructureJunction/StructureJunctionObject | Set Association Role | | Not the structure network. `learn/04-rules-and-connectivity-design.md` |
| Structure network | The single support-feature network (poles, vaults, trenches); no flow, tiers or subnetworks | `Structure*` classes | | `pro-help/02-structure-of-a-utility-network.md` |
| Subnetwork | Connected area traced from controllers within a tier, cached as names and rows | `SUBNETWORKNAME`; Subnetworks table | | Not a feature class. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Subnetwork definition | Per-tier configuration: valid lists, barriers, propagators, outputs, edit mode | Set Subnetwork Definition | | Needs topology disabled. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Subnetwork name fields | `SUBNETWORKNAME`, `SUPPORTEDSUBNETWORKNAME`, `SUPPORTINGSUBNETWORKNAME` | Fields | supported v4; supporting v5 | `Unknown` = not updated or untraversable. `learn/06-tiers-and-subnetworks-in-depth.md` |
| `SubnetLine` | One linear record per subnetwork; read-only | `<Name>SubnetLine` | | Reconcile includes, post does not. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Subnetworks table | One row per controller terminal with status | `subnetworksTableId` (example 500002) | | `learn/02-data-model-in-depth.md` |
| Subnetwork tap | Category for features tapped off a line's midspan | Network categories | | Error 37. `learn/05-attributes-categories-and-attribute-rules.md` |
| Substitution | Changes the propagated value passed on, without overwriting fields | Add Network Attribute (Long) | | Out-of-line Long only. `learn/05-attributes-categories-and-attribute-rules.md` |
| System junction | Hidden junction created where two same-group/type edges meet | Network diagrams | | No rule needed. `learn/02-data-model-in-depth.md` |
| Terminal | Logical port on a device or junction object | `FROMDEVICETERMINAL`; `terminalId` | | Not in telecom. `learn/02-data-model-in-depth.md` |
| Terminal configuration | Named layout of 2-8 terminals with directionality and valid paths | Add/Set Terminal Configuration | | Permanent after first enable. `learn/02-data-model-in-depth.md` |
| Tier | A rule set shared by a collection of subnetworks | Add Tier; `TIERNAME` | max 63 per UN | Not a subnetwork. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Tier group | Container for hierarchical tiers | Add Tier Group | | Hierarchical only. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Traversability | Connectivity plus the barrier/category rules that allow the trace to proceed | Trace settings | | Evaluated before filters. `learn/07-tracing-in-depth-and-configuration-library.md` |
| Update Is Connected | Recalculates `ISCONNECTED` for the whole network | Tool; REST `updateIsConnected` | | Traditional only. `learn/01-mental-model-and-life-of-an-edit.md` |
| Update Subnetwork | Re-traces and writes names, propagated values, SubnetLine and status | Tool; REST `updateSubnetwork`; C# `Subnetwork.Update()` | | Not Validate; needs no dirty areas. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Upstream | Toward controllers in a source network, away from them in a sink network | `traceType` `upstream` | | `learn/07-tracing-in-depth-and-configuration-library.md` |
| `UtilityNetworkServer` / `UtilityNetworkTools` | REST service for trace/validate/etc.; system GP service that runs long jobs | Service folders | async 10.9.1+ | `rest-api/01-utility-network-server-and-trace.md` |
| Valid lists | Per-tier allowed devices, lines, junctions, objects and controllers | Set Subnetwork Definition | objects UN v4+ | Enforced; errors 24, 26, 40-42. `learn/06-tiers-and-subnetworks-in-depth.md` |
| Validate Consistency | Trace option that fails the trace on reaching a dirty area | Pro (unchecked); REST `validateConsistency` | | Defaults differ by surface. `learn/03-topology-engine-and-validation.md` |
| Validate Locatability | Trace/definition option that fails on unlocatable objects | `validateLocatability` | UN v5+ (definition) | `learn/02-data-model-in-depth.md` |
| Validate Network Topology | Incorporates dirty areas into the topology; flags rule violations | Validate command; tool; REST `validateNetworkTopology` | | Not Update Subnetwork. `learn/03-topology-engine-and-validation.md` |
| Validation rule | Batch-only attribute rule that writes error features | Add Attribute Rule | | `learn/05-attributes-categories-and-attribute-rules.md` |
| Verify / Repair Network Topology | Check and fix topology system tables | Tools | | Owners, DEFAULT. `learn/13-arcgis-pro-fundamentals-and-workflow.md` |
| Version Management | Service extension for create, reconcile, post, locks | `VersionManagementServer` | capability at publish | `rest-api/04-version-management-validation-feature-service.md` |

## 3. Same thing, different names (Pro, REST, JS, C#, arcpy)

A dash means no equivalent was found in the linked files. Entry points only; parameters are in the per-surface reference files. Source: `learn/14-developer-surfaces-and-sdk-fundamentals.md` section 4 plus the per-surface files.

| Concept | Pro UI | REST | JS Maps SDK 5.1 | Pro SDK (C#) | arcpy |
|---|---|---|---|---|---|
| Classification | Asset Group / Asset Type | `assetGroupCode`, `assetTypeCode` | see `js-api/03-network-class-loading-and-definition.md` | `AssetGroup`, `AssetType` | `assetgroup`, `assettype` parameters |
| Row identity | GlobalID | `globalId` | `globalId` | `Element` (source + GlobalID) | `FEATUREGLOBALID` in locations |
| Starting point | Trace pane Start tab (label per `learn/13`; verify against the Esri docs for your version) | `traceLocationType` `startingPoint` | `TraceLocation` `type: "starting-point"` | `Element` in `TraceArgument.StartingLocations` | `starting_points` layer |
| Barrier / condition barrier | Barriers tab / Set Subnetwork Definition | `barrier` location / `conditionBarriers` | kebab-case `barrier` location (verify) | `TraceArgument.Barriers` / `Traversability` | `condition_barriers` |
| Trace | Trace pane, tool gallery | `.../trace` | `utilityNetwork.trace()` | `Tracer.Trace(TraceArgument)` | `arcpy.un.Trace` |
| Named trace configuration | Named Configurations tab | `traceConfigurationGlobalId` | `namedTraceConfigurationGlobalId` | `GetNamedTraceConfigurations` | `trace_config_name` |
| Validate | Validate command | `validateNetworkTopology` | `validateTopology`, `submitTopologyValidationJob` | `ValidateNetworkTopology` | `arcpy.un.ValidateNetworkTopology` |
| Update subnetwork | Update Subnetwork tool, Find Subnetworks | `updateSubnetwork` | - | `Subnetwork.Update()` | `arcpy.un.UpdateSubnetwork` |
| Set a controller | Modify Controller pane | `enableSubnetworkController` | - | `SubnetworkManager.EnableController` | `UtilityNetwork.EnableSubnetworkController` |
| Add an association | Modify Associations, Import Associations | `applyEdits` on the associations layer | `generateAddAssociations` | `AssociationDescription`, `AddAssociation` | `AddConnectivityAssociation`, etc. |
| Topology state | Network Properties | `queryNetworkMoments` (`validNetworkTopology`) | - | `GetState()` | `HasValidNetworkTopology()` |
| Dirty areas | Dirty Areas sublayer | `dirtyAreasLayerId` in `systemLayers` | `networkSystemLayers` | `SystemTableType.DirtyAreas` | - |
| Schema read | Network Properties | `queryDataElements` | `utilityNetwork.dataElement` | `UtilityNetworkDefinition` | `arcpy.Describe(un)` |
| Version / session | Versioning tab | `gdbVersion`, `sessionId` | `gdbVersion` on parameters | not in the UN namespace | Pro versioning tools |
| Long-running | ribbon sync; tool async | `async=true` + `statusUrl` | `submitTraceJob` | `ServiceSynchronizationType` | tool via `UtilityNetworkTools` |

Gotcha: `traceLocationType` is `startingPoint` in REST and `type: "starting-point"` in JS; `sessionId` and `sessionID` are both spelled in REST pages. Use the spelling on the operation's own page.

## 4. Foundation and geometric-network vocabulary mapped to UN terms

Geometric-network definitions come from the Esri geometric network vocabulary page (listed in Sources); UN statements come from the linked learn files. "Loosest analog" means the ideas overlap but the engines differ.

| Old geometric-network word | What it meant | UN word | Difference that matters |
|---|---|---|---|
| Junction | Point feature where edges connect | Junction, Device, Junction object | UN splits point roles; devices may have terminals |
| Edge | Line feature carrying the commodity | Line, Edge object | Edge objects are nonspatial rows |
| Simple edge | No midspan connections; a junction splits it | Line with End vertex policy | `Set Edge Connectivity`; midspan breaks it (error 13) |
| Complex edge | Junctions attach along it without splitting | Line with Any vertex policy; midspan connectivity | Terminal devices still cannot sit midspan |
| Orphan junction | System placeholder at an edge end with no junction | System junction (loosest analog) | UN system junction joins same group/type edges, not a placeholder |
| Logical network | Connectivity graph maintained automatically | Network topology | UN topology is rebuilt only by Validate |
| Weights | Traversal cost values; -1 impedes | Network attributes, function barriers, shortest-path cost | Must be mapped to a field |
| Enabled field / barriers | Disabled features stop a trace | Condition barrier on a status attribute (loosest analog) | UN also has feature, function and filter barriers |
| Source / sink (AncillaryRole on junctions) | Junctions that set flow direction | Subnetwork controller terminal; domain controller type source/sink | Per terminal and tier; digitized direction is an alternative |
| Flow direction | Computed from sources and sinks | Controller-based flow, or `FLOWDIRECTION` | `learn/07-tracing-in-depth-and-configuration-library.md` |
| One class per kind of thing | Many feature classes | Few classes + `ASSETGROUP`/`ASSETTYPE` | Config keys on the pair |
| Circuit / zone derived ad hoc | Not first-class | Subnetwork (tier, controllers, SubnetLine) | Cached by Update Subnetwork |
| ArcGIS Schematics | Old diagram product | Network diagrams | `pro-help/07-network-diagrams.md` |

Foundation wording: a **Foundation** is Esri's packaged UN data model (`pro-help/08-asset-packages-foundations-migration.md`). It ships as an **asset package** and a **data dictionary**; its tier, category and field names (for example a "pressure" or "isolation" tier) are Foundation conventions, not engine terms, and change between releases. When a user quotes such a name, ask which Foundation release before assuming a meaning.

## 5. The commonly confused pairs, side by side

| Pair | First | Second | Deep file |
|---|---|---|---|
| Asset group vs asset type | Subtype (major class) | Domain value under a group (minor class) | `learn/02-data-model-in-depth.md` |
| Subnetwork vs tier | Cached result of tracing from controllers | The rule set many subnetworks share | `learn/06-tiers-and-subnetworks-in-depth.md` |
| Status (bits) vs error ID | `STATUS` 32 = subnetwork-error bit in a bitmask | Error ID 32 = inline weight out of range | `learn/09-failure-anatomy-symptom-to-fix.md` |
| Controller vs source | Controller = a terminal marking a subnetwork's origin or destination | Source/sink = the domain network's controller type | `learn/06-tiers-and-subnetworks-in-depth.md` |
| Validate vs Update Subnetwork | Maintains the topology (connectivity truth) | Maintains names, SubnetLine, status | `learn/03-topology-engine-and-validation.md` |
| Container vs structure | Role holding contents (any class) | Role for attachment (StructureJunction/Object only); not the structure network | `learn/04-rules-and-connectivity-design.md` |
| Junction object vs edge object | Nonspatial point-like row (port, rack) | Nonspatial edge-like row (strand), joined by From and To associations | `learn/02-data-model-in-depth.md` |
| Network rule vs attribute rule | Which pairs may relate | Arcade logic on edit | `learn/05-attributes-categories-and-attribute-rules.md` |
| Network attribute vs field | Definition the engine reads | Column in the table | `learn/05-attributes-categories-and-attribute-rules.md` |
| Condition vs filter barrier | Traversability: tier/update/export/trace | Trace-only, after traversability | `learn/07-tracing-in-depth-and-configuration-library.md` |
| Database owner vs portal owner vs version owner | Connection user | Signed-in portal account; version access | `learn/13-arcgis-pro-fundamentals-and-workflow.md` |
| Domain network vs attribute domain | Group of UN classes | Coded value list on a field | `learn/02-data-model-in-depth.md` |
| Three meanings of "Status" | Dirty Areas `STATUS` bitmask | Associations `STATUS` bits; Subnetworks `ISDIRTY` (alias Status on new networks) | `learn/02-data-model-in-depth.md` |

## 6. Suggested learning paths

Prerequisite for every path: `pro-help/01-core-concepts-and-vocabulary.md`, then `pro-help/02-structure-of-a-utility-network.md`. Keep this file open as the lookup.

**GIS analyst (edits, QA, traces, reports)**
1. `learn/01-mental-model-and-life-of-an-edit.md` (the lifecycle; read section 4 twice)
2. `learn/13-arcgis-pro-fundamentals-and-workflow.md` (where things are in Pro)
3. `learn/02-data-model-in-depth.md` (sections 4 to 9 first)
4. `learn/03-topology-engine-and-validation.md` (dirty areas, why a trace is stale)
5. `learn/07-tracing-in-depth-and-configuration-library.md`
6. `learn/06-tiers-and-subnetworks-in-depth.md` (subnetwork status, Unknown names)
7. `learn/08-versioning-and-editing-workflows.md` (sections 5 to 10, 17)
8. `learn/09-failure-anatomy-symptom-to-fix.md` (as a reference when something fails)

**Administrator (design, configuration, operations)**
1. `learn/01-mental-model-and-life-of-an-edit.md`, then `learn/13-arcgis-pro-fundamentals-and-workflow.md` (build flow, owners)
2. `learn/02-data-model-in-depth.md`, `learn/04-rules-and-connectivity-design.md`
3. `learn/05-attributes-categories-and-attribute-rules.md`, `learn/06-tiers-and-subnetworks-in-depth.md`
4. `learn/03-topology-engine-and-validation.md`
5. `learn/08-versioning-and-editing-workflows.md` (sections 1 to 9, 15)
6. `learn/10-performance-scale-and-operations.md`, `learn/09-failure-anatomy-symptom-to-fix.md`
7. `pro-help/08-asset-packages-foundations-migration.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`, `pro-help/10-publishing-ownership-licensing.md`

**Developer (apps, automation, integrations)**
1. `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md` (sections 5 to 7, 10)
2. `learn/03-topology-engine-and-validation.md` (what validate does, async)
3. `learn/14-developer-surfaces-and-sdk-fundamentals.md` (choose the surface)
4. `learn/07-tracing-in-depth-and-configuration-library.md`
5. `learn/08-versioning-and-editing-workflows.md` (sessions, locks, section 11)
6. `learn/10-performance-scale-and-operations.md` (scheduling, time-outs)
7. Surface files: `rest-api/01-utility-network-server-and-trace.md`, `rest-api/08-trace-configuration-full-schema.md`, `js-api/01-javascript-sdk-utility-network.md`, `pro-sdk/01-csharp-sdk-utility-network-api.md`, `arcpy/01-utility-network-module.md`
8. `learn/09-failure-anatomy-symptom-to-fix.md` and `scripts/decode_dirty_status.py`, `scripts/build_trace_request.py`

## Common misconceptions

- "The glossary term and the Pro label are the same." Labels differ by release; REST, JS and C# names differ again (section 3).
- "Asset group and asset type are the same thing." Two levels; rules key on the pair.
- "A tier is a big subnetwork." A tier is configuration; subnetworks are cached results.
- "Status 32 and error 32 are the same." Different lists (section 5).
- "Source means the same in every sentence." It can mean a network source (class), the controller type, or the colloquial power source.
- "Old geometric-network habits carry over." Snapping alone does not connect; a rule and a Validate are needed.

## Quick checks

1. Which surface is the user quoting (Pro label, REST property, C# class, arcpy parameter)? Map it with section 3 before answering.
2. Is the term a stored value, a configuration object, or a derived snapshot?
3. Does the term have a version floor in the table (for example UN v7+, v8, Ent 12.1)? Does the user's dataset meet it?
4. Is the user mixing two meanings (Status bits, source/controller, domain network/attribute domain)?
5. Does a Foundation convention (a tier or category name) stand behind the word?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`, `learn/03-topology-engine-and-validation.md`, `learn/04-rules-and-connectivity-design.md`, `learn/05-attributes-categories-and-attribute-rules.md`, `learn/06-tiers-and-subnetworks-in-depth.md`, `learn/07-tracing-in-depth-and-configuration-library.md`
- `learn/08-versioning-and-editing-workflows.md`, `learn/09-failure-anatomy-symptom-to-fix.md`, `learn/10-performance-scale-and-operations.md`, `learn/13-arcgis-pro-fundamentals-and-workflow.md`, `learn/14-developer-surfaces-and-sdk-fundamentals.md`
- `pro-help/01-core-concepts-and-vocabulary.md`, `pro-help/02-structure-of-a-utility-network.md`
- `scripts/association_types.py`, `scripts/decode_dirty_status.py`

## Sources

- https://resources.arcgis.com/en/help/main/10.2/002r/002r00000003000000.htm (Esri, "Essential geometric networks vocabulary": junction, edge, simple/complex edge, orphan junction, logical network, weights, sources and sinks, enabled field, barriers)
- All other definitions are condensed from the repository reference files linked in each row; their own source lists (Esri Pro help, tool reference, REST reference, JS and Pro SDK references) apply.
