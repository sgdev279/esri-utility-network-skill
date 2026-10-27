# Utility Network: Developer Surfaces and SDK Fundamentals
> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro SDK ProConcepts and API reference (3.7), ArcGIS Pro tool reference, ArcGIS Enterprise REST reference, ArcGIS Maps SDK for JavaScript 5.1 reference, ArcGIS Maps SDK for .NET reference (full list at the end).*

## Why this matters / when to read this

The utility network (UN) is exposed to developers through five different surfaces that look similar but are not interchangeable: the Pro SDK (C#), `arcpy.un` (Python), the Utility Network and related REST services, the Maps SDK for JavaScript, and low-code Experience Builder widgets. Most failed first attempts come from picking the wrong surface, copying class names across surfaces, or forgetting the shared preconditions (dirty areas, versions, sessions). Read this file when you must choose an API, move an idea from one surface to another, or review a new developer's first UN code. It assumes the mechanics in `learn/01-mental-model-and-life-of-an-edit.md` and `learn/03-topology-engine-and-validation.md`, and links to the per-surface reference files rather than repeating their parameter tables.

## Contents

1. Architecture: one core, three layers of access
2. Decision tree: which surface for which job
3. ArcGIS Pro SDK in depth
4. One idea, four surfaces: the concept table
5. Five worked snippets
6. Common mistakes of developers new to the UN
7. Common misconceptions, quick checks, related files, sources

## 1. Architecture: one core, three layers of access

**Plain definition.** There is exactly one utility network per feature dataset, stored in a geodatabase. Everything a developer touches is a different door into that same stored state. Esri's own REST overview describes the enterprise form as a set of coordinated services (see `learn/01-*.md` section 2 and `rest-api/04-version-management-validation-feature-service.md`).

**Mechanism.**

```
 GEODATABASE CORE (stored)            SERVICES (enterprise only)                 CLIENT SDKs / TOOLS
 feature classes, tables,   --->  FeatureServer (+ system layers)   --->   Pro (UI, tools, Pro SDK, arcpy)
 associations, dirty areas,       UtilityNetworkServer                       JS Maps SDK + map components
 topology, subnetworks,           VersionManagementServer                    Experience Builder widgets
 rules, attribute rules           ValidationServer, NetworkDiagramServer     native Maps SDKs, Field Maps
                                  UtilityNetworkTools (System-folder GP)     any REST client (Python, Node, ...)
```

| Layer | What lives there | Who can reach it |
|---|---|---|
| Geodatabase core | Data, topology, rules, associations, dirty areas, versions. Enterprise is branch versioned; file and mobile geodatabases are single-user and unversioned (`learn/08-versioning-and-editing-workflows.md` section 13) | Pro, Pro SDK, arcpy (direct connection). Not REST or JS |
| UN services | `UtilityNetworkServer` (trace, validate, update subnetwork, export, enable/disable topology and controllers, associations, locations, trace configurations; circuits and unit identifiers at 12.1), `VersionManagementServer`, `ValidationServer`, `NetworkDiagramServer`, a UN-aware `FeatureServer` | Any HTTP client, JS SDK, Experience Builder, Pro (as a service connection), native Maps SDKs |
| Client SDKs and tools | Object models and UI that wrap the above | Per-surface, below |

**Key consequences for developers.**

- The Pro SDK C# API is, in Esri's words, data manipulation only: it reads and writes rows, associations and subnetwork state. It does not create or configure the schema (rules, tiers, terminal configurations); that is the geoprocessing layer (`pro-sdk/01-csharp-sdk-utility-network-api.md`).
- Anything that changes the definition (add rule, add tier, set terminal configuration, enable topology in a fresh network) needs topology disabled, DEFAULT, and owner connections in enterprise (`learn/08-*.md` section 15). No developer API makes that unnecessary.
- Anything that changes data creates dirty areas; nothing validates itself. Every surface below inherits the "edit, validate, then trace" order (`learn/03-*.md`).
- Licensing is uniform: Pro Standard or Advanced for UN work; for enterprise create, publish and edit also need the portal account to hold the Advanced Editing user type extension; query and trace do not (`arcpy/01-utility-network-module.md`, `learn/01-*.md` step 9, `pro-help/10-publishing-ownership-licensing.md`).

**Example (water).** A utility wants a nightly job that validates DEFAULT, refreshes pressure-zone subnetworks and posts nothing else. The job has no map, so the JS SDK is the wrong tool. If it runs on a server without Pro, arcpy is out; REST with `async=true` fits. If it runs on a Windows workstation with Pro already installed, arcpy or the Pro SDK both fit. The surface follows the runtime environment, not the data.

## 2. Decision tree: which surface for which job

```
Need to CHANGE THE SCHEMA (rules, tiers, terminal configs, domain networks, categories)?
  -> Pro UI or arcpy.un geoprocessing tools (Pro SDK cannot; REST has no such operations).
Need a UI inside ArcGIS Pro (custom pane, tool, map tool, ribbon button)?
  -> Pro SDK add-in (C#).
Need unattended automation where Pro is installed (batch loads, reports, QC, scheduled tasks)?
  -> arcpy.un (tools + arcpy.un.UtilityNetwork class). Inputs for enterprise must be UN SERVICES.
Need a standalone Windows .NET app using the geodatabase API without Pro UI?
  -> Pro SDK CoreHost (no Add-in extension methods; see section 3.5).
Need a web app with a map?
  -> JS Maps SDK. Start with the arcgis-* map components; drop to utilityNetwork.trace() for custom UI.
Need a web app without code?
  -> Experience Builder (Trace widget, Branch Version Management widget; validation and associations are thin).
Need server-side or cross-language automation with no Pro and no map?
  -> REST (UtilityNetworkServer, VersionManagementServer) from any language; Node: @esri/arcgis-rest-request generic request().
Need a mobile or native field app?
  -> ArcGIS Maps SDKs for Native Apps (.NET, Qt, Swift, Kotlin). Check the UN dataset version first (see the gaps list below).
Need ArcGIS API for Python UN helpers?
  -> GAP: no UN-specific module was confirmed in this review. Use arcpy (inside Pro) or call REST directly.
```

| Surface | Runs where | Direct geodatabase access | Service access | Schema changes | Typical user |
|---|---|---|---|---|---|
| Pro SDK (`ArcGIS.Core.Data.UtilityNetwork`) | Pro add-in or CoreHost on Windows | Yes (file, mobile, enterprise) | Yes (feature service as a `Geodatabase`) | No (DML only) | Add-in developer |
| `arcpy.un` | Python with Pro installed | Yes (single-user) | Yes (UN service or layer) | Yes (geoprocessing tools) | GIS analyst, admin |
| REST | Anywhere with HTTP | No | Yes | No (runtime operations only) | Integrator, DevOps |
| JS Maps SDK 5.1 | Browser or Node | No | Yes | No | Web developer |
| Experience Builder | Browser, configured | No | Yes | No | Power user |
| Native Maps SDKs | Mobile or desktop apps | Offline via sync-enabled feature service (`learn/08-*.md` section 12); not UN v8 per Esri compatibility notes | Yes | No | Field-app developer |

**Gaps stated up front, so nobody searches for them.**

- **ArcGIS API for Python:** no UN trace, validate or subnetwork manager was confirmed in the sources read. `rest-api/04-*.md` documents its version-management pattern, and `learn/10-performance-scale-and-operations.md` section 11.4 says the same about UN methods. Verify against the API reference for your version before promising wrappers.
- **Network diagrams in JS:** no Network Diagram classes exist; only raw `NetworkDiagramServer` REST (`js-api/03-network-class-loading-and-definition.md`).
- **arcgis-rest-js:** no UN package; use the generic `request()` (`js-api/06-functional-api-web-components-calcite.md`).
- **Native Maps SDKs:** the .NET reference shows `ValidateNetworkTopology(Envelope)` returning a job that must be started, `GetStateAsync()`, `TraceAsync(UtilityTraceParameters)`, `CreateElement(...)`, `QueryNamedTraceConfigurationsAsync(...)`, `UtilityNetwork(ServiceGeodatabase)` and `LoadAsync()`. This family is not covered by a reference file here beyond that. Esri's compatibility page (summarised in `learn/08-*.md` section 12) says Field Maps and the Native Apps SDKs do not currently support UN dataset v8 with Enterprise 12.1.

## 3. ArcGIS Pro SDK in depth

### 3.1 Two namespaces, plus extensions

| Namespace | Purpose |
|---|---|
| `ArcGIS.Core.Data.UtilityNetwork` | Core object model (28 classes and 22 enumerations in the 3.4 namespace listing; more since, including telecom) |
| `ArcGIS.Core.Data.UtilityNetwork.Trace` | Tracing |
| `ArcGIS.Core.Data.UtilityNetwork.Telecom` | Telecom circuits and related types (appears in the Pro 3.7 API changes list) |
| `ArcGIS.Core.Data.UtilityNetwork.Extensions` | Add-in-only extension methods; needs a reference to `ArcGIS.Desktop.Extensions` |

The SDK is the "real" object-oriented API; do not confuse it with `arcpy.un` or with `Esri.ArcGISRuntime.UtilityNetworks` (Maps SDK for .NET). Class names overlap (`UtilityNetwork`, `Subnetwork`, `UtilityAssociation` vs `Association`), but the members and the threading model differ.

### 3.2 Namespace map: the classes you meet, in the order you meet them

Everything below is named in the Pro 3.x namespace listing or ProConcepts unless marked.

| Group | Class (or enum) | What it is, in one line |
|---|---|---|
| Root | `UtilityNetwork` | The dataset. Methods include `GetDefinition`, `GetTraceManager`, `GetSubnetworkManager`, `GetDiagramManager`, `GetCircuitManager`, `GetUnitIdentifierManager`, `GetTable(NetworkSource)`, `GetSystemTable`, `IsSystemTableSupported`, `CreateElement`, `GetFeaturesForElements`, `GetAssociations`, `GetAssociationFeatures`, `AddAssociation`, `DeleteAssociation`, `TraverseAssociations`, `GetState`, `GetExtent`, `ValidateNetworkTopology`, `GetServerCapabilities`, `AreServerCapabilitiesSupported`. It derives from `Dataset` (so `GetName`, `GetPath`, `GetDatastore` too) |
| Schema | `UtilityNetworkDefinition` | Schema and properties. `GetDomainNetworks`, `GetDomainNetwork`, `GetNetworkSources`, `GetNetworkSource`, `GetNetworkAttributes`, `GetNetworkAttribute`, `GetRules`, `GetTerminalConfigurations`, `GetAvailableCategories`, `GetAssetGroupField`, `GetAssetTypeField`, `GetAssociationStatusField`, `GetSchemaVersion` (a string), `GetServiceTerritoryEnvelope` |
| Schema | `NetworkSource`, `SourceType`, `SourceUsageType` | One per class/table. `UsageType` says Device, Junction, Line, Assembly, and so on. `GetAssetGroup(s)` |
| Schema | `AssetGroup`, `AssetType` | The subtype and domain pair (`learn/02-data-model-in-depth.md` section 4). `AssetType` exposes `GetTerminalConfiguration()` (guard with `IsTerminalConfigurationSupported()`), `GetCategoryList()`, `AssociationRoleType`, `AssociationDeletionSemantics`, `ContainerViewScale`, and linear-connectivity and container-split policy getters |
| Schema | `DomainNetwork` | `IsStructureNetwork`, `SubnetworkControllerCategory` (Source, Sink, None), `TierDefinition` (Hierarchical, Partitioned), `Tiers`, `TierGroups`, `NetworkSources`, `GetTier` |
| Schema | `Tier`, `TierGroup`, `TierTopologyType` | Tier has `SubnetworkFieldName`, `TopologyType` (Radial, Mesh), `IsDisjointSubnetworkSupported`, `HasUpdateSubnetworkPolicy`, `GetEditModeForSubnetwork`, `GetDiagramTemplateNames`, `TraceConfiguration`, and the `Valid*` lists (`ValidDevices`, `ValidLines`, `ValidSubnetworkControllers`, ...) |
| Schema | `Rule`, `RuleElement`, `RuleType` | From `GetRules()`; the five rule types of `learn/04-rules-and-connectivity-design.md` |
| Schema | `TerminalConfiguration`, `Terminal`, `TerminalPath`, `ConfigurationPath`, `Directionality` | `Terminal` has an ID, a name and `IsUpstreamTerminal` (`learn/02-*.md` section 6) |
| Schema | `NetworkAttribute`, `NetworkAttributeAssignment`, `NetworkAttributeDataType` | Data types Date, Double, Long, Short. Assignments map the attribute to fields |
| Schema | Categories | Not a class: category names are strings from `GetAvailableCategories()` and `AssetType.GetCategoryList()`, tested in a trace with `CategoryComparison` |
| Data | `Element` | Lightweight handle for a row plus an optional `Terminal`. Used for associations, trace locations and trace results. `ObjectID` is -1 unless the element came from a row or a trace; always identity by `GlobalID` + `NetworkSource` |
| Data | `Association`, `AssociationFeature`, `AssociationType`, `TraverseAssociationsDescription`, `TraverseAssociationsResult`, `TraversalDirection` | Association query and multi-level traversal |
| State | `UtilityNetworkState`, `ValidationResult`, `ValidationType`, `SystemTableType` | `GetState()` gives `IsNetworkTopologyEnabled`, `HasDirtyAreas`, `HasErrors`, `LastConsistentMoment`, `LastUpdateIsConnectedMoment`. Validation types Normal, Repair, ForceRebuild. System tables PointErrors, LineErrors, PolygonErrors (unsupported from schema version 4), DirtyAreas, Subnetworks, Associations |
| Subnetworks | `SubnetworkManager`, `Subnetwork`, `SubnetworkController`, `SubnetworkStates`, `EditMode`, `UpdateSubnetworkPolicy`, `SubnetworkExportOptions`, `SubnetworkExportResultType`, `ExportOptions` | Manager: `GetSubnetwork`, `GetSubnetworks`, `UpdateAllSubnetworks`, `EnableController`, `DisableController`. States include Dirty, Clean, DirtyAndDeleted, CleanAndDeleted |
| Trace | `TraceManager` | From `GetTraceManager()`. `GetTracer<T>()`, `GetTracer(NamedTraceConfiguration)`, `GetNamedTraceConfigurations(NamedTraceConfigurationQuery)` |
| Trace | `Tracer` and subclasses (`ConnectedTracer`, `UpstreamTracer`, `DownstreamTracer`, `SubnetworkTracer`, `IsolationTracer`, `LoopsTracer`, `ShortestPathTracer`; at 3.7 `PathTracer`, `CircuitTracer`) | `Trace(TraceArgument)` and `Trace(TraceArgument, ServiceSynchronizationType)`, both returning `IReadOnlyList<Result>`; `Export(...)` writes trace JSON |
| Trace | `TraceArgument` | `Barriers`, `FilterBarriers`, `StartingLocations`, `StoppingLocations`, `Configuration`, `ResultTypes`, `ResultOptions`, `Subnetwork`, `Circuit` |
| Trace | `TraceConfiguration` | Basic properties (`AllowIndeterminateFlow` default true, `IncludeContainers`, `IncludeContent`, `IncludeStructures`), then `Traversability` (`Barriers`, `FunctionBarriers`, `Scope`), `Filter` (`Barriers`, `FunctionBarriers`, `BitsetNetworkAttribute`, `NearestNeighbor`, `Scope`), `Functions`, `OutputAssetTypes`, `OutputCondition`, `Propagators`, `SourceTier`, `TargetTier`, `ShortestPathNetworkAttribute`, `UseDigitizedDirection`, `ValidateConsistency`; `InferConnectivity`, `SynthesizeGeometries`, `MaxHops`, `NumPaths` are in the 3.7 reference (there is no `Output` property) |
| Trace | `NetworkAttributeComparison`, `CategoryComparison`, `And`, `Or`, `Operator`, `CategoryOperator`, `FunctionBarrier`, `Add` (a `Function`), `Propagator`, `NearestNeighbor`, `OutputCondition` | The condition and function vocabulary of `learn/07-tracing-in-depth-and-configuration-library.md` |
| Trace | `ResultType` and `Result` subclasses | `ResultType` members: AggregatedGeometry, Circuit (reserved), Connectivity, ContainmentAndAttachment, Element, Feature, FunctionValue, Path (reserved). Results: `ElementResult`, `FeatureElementResult`, `FunctionOutputResult`, `AggregatedGeometryResult`, and at 3.7 `PathResult`, `CircuitResult` |
| Telecom (3.7) | `CircuitManager`, `Circuit`, `UnitIdentifierManager`, `UnitRange`, `DividePolicy`, `CombinePolicy` | See `rest-api/07-circuits-and-unit-identifiers-telecom.md` for the service behaviour |
| Diagrams | `DiagramManager` | From `GetDiagramManager()`; diagrams are in `ArcGIS.Core.Data.NetworkDiagrams` |

Checked against the 3.6/3.7 API reference: `Traversability.Barriers` (a condition) and `.Scope` (`TraversabilityScope`) are documented, `Filter` has the five properties above, and `UpdateAllSubnetworks(Tier, bool continueOnFailure)` returns void and creates its own transaction. `Traversability.FunctionBarriers` is used in `pro-sdk/01-*.md`; I did not find it on the class page, so verify against the Esri docs for your version.

### 3.3 Threading

Esri: almost all UN methods must run on the **Main CIM Thread (MCT)**; wrap them in `QueuedTask.Run`, otherwise a `ConstructedOnWrongThreadException` is thrown. Practical rules:

1. Open, read and dispose all UN objects inside one `QueuedTask.Run` lambda. Do not pass a `UtilityNetwork`, `Element` or `Subnetwork` across threads or keep it in a static field after the lambda ends.
2. Most of these objects are disposable; the Esri snippets wrap `TraceManager`, `UtilityNetworkDefinition`, `NetworkSource`, `AssetGroup`, `AssetType` and others in `using`.
3. `await QueuedTask.Run(...)` keeps the UI responsive, but the call inside is synchronous and blocks the MCT. A long full-network validation holds the MCT; plan UI feedback accordingly.

### 3.4 Opening a utility network

| Starting point | How (Esri) |
|---|---|
| A table or layer already in the map | `table.IsControllerDatasetSupported()`, then `table.GetControllerDatasets()`; keep the `UtilityNetwork` item and dispose the rest (a table can belong to several controller datasets but at most one is a UN). For a `UtilityNetworkLayer`, `GetUtilityNetwork()`; for a `SubtypeGroupLayer`, descend to its first child layer; for a `FeatureLayer`, `GetFeatureClass()` then `GetControllerDatasets()` |
| A geodatabase | `Geodatabase.OpenDataset<UtilityNetwork>(name)`; the definition via `geodatabase.GetDefinition<UtilityNetworkDefinition>(name)` |
| A feature service | `new Geodatabase(new ServiceConnectionProperties(new Uri(featureServerUrl)))` then open the UN as above. Esri notes that the client-server dataset name can differ from the name you expect, so read the name from the definition rather than assuming it. For federated Portal and ArcGIS Online services, credentials come from the signed-in Pro portal connection and cannot be set through the API; for a non-federated ArcGIS Server service, set `ServiceConnectionProperties.User` and `.Password` (Esri advises against clear text; use Windows Credential Manager) |

`UtilityNetwork.GetServerCapabilities()` (guard with `AreServerCapabilitiesSupported()`) is the SDK counterpart of the REST `capabilities` block in `rest-api/01-*.md`.

### 3.5 Add-in versus CoreHost

| | Pro Add-in | CoreHost application |
|---|---|---|
| Runs in | The Pro process (map, undo/redo, editor available) | Its own process; no Pro UI |
| `ArcGIS.Core.Data.UtilityNetwork.Extensions` methods (`ValidateNetworkTopologyInEditOperation`, `EnableControllerInEditOperation`, `DisableControllerInEditOperation`) | Available | Not available |
| Low-level `AddAssociation` / `DeleteAssociation` | Not recommended: no map refresh, no undo/redo | Fine; wrap in a transaction like other low-level edits |
| Typical use | Interactive tools, ribbon buttons | Batch utilities, servers, test harnesses |

### 3.6 Edit operations and the association editing rules

Two edit paths exist, and mixing them is the most common Pro SDK defect.

- **Inside an Add-in, use `EditOperation`.** Row handles and tokens (`RowHandle`, `RowToken`) let you create features and an association in one undoable step: create the structure and attachment with `CreateEx`, wrap their tokens in `RowHandle`, and add an association description between them before `Execute()`. For an existing pair, build elements with `utilityNetwork.CreateElement(assetType, globalId)` and wrap them in `RowHandle(element, utilityNetwork)`. Full pattern in `pro-sdk/01-csharp-sdk-utility-network-api.md`.
- **Low-level `AddAssociation(Association)` / `DeleteAssociation(Association)`** modify the data directly. They need the MCT, should be inside a transaction, and in an Add-in leave the map and the undo stack out of date.
- **Rules still apply.** An association needs a supporting network rule (and, for containment and attachment, an association role) exactly as in the UI (`learn/04-*.md`). The SDK does not bypass them; the same is true of every surface.

### 3.7 Methods that manage their own transaction

| Call | Constraint (Esri) |
|---|---|
| `UtilityNetwork.ValidateNetworkTopology(...)` | Manages its own transaction; cannot be issued inside an edit operation or `Geodatabase.ApplyEdits`. In an Add-in use `ValidateNetworkTopologyInEditOperation` |
| `SubnetworkManager.EnableController` / `DisableController` | Own transaction; cannot be nested inside another edit operation. Add-in variants end in `InEditOperation` |
| `Subnetwork.Update()` and its overloads | Cannot run inside an edit transaction; save or discard pending edits first |
| `Subnetwork.Export(Uri, SubnetworkExportOptions)` | With `SetAcknowledged = true` it throws inside `Geodatabase.ApplyEdits`; acknowledged export needs DEFAULT |

### 3.8 Sync versus async validate (and why the C# code looks the same)

There is no `Job<T>` in the Pro SDK (`pro-sdk/01-*.md`). You choose a service endpoint with `ServiceSynchronizationType` (`Synchronous` or `Asynchronous`); it is ignored for file and mobile geodatabases. Esri's ProConcepts states the rules:

| Overload | Endpoint used |
|---|---|
| `ValidateNetworkTopology()` (whole network) | Asynchronous (runs in the Geoprocessing Server; Pro polls until done) |
| `ValidateNetworkTopology(Geometry)` (an extent) | Synchronous, "intended for use with small areas" |
| `ValidateNetworkTopology(IEnumerable<Selection>)` | Synchronous |
| `(Geometry, ServiceSynchronizationType)` and `(IEnumerable<Selection>, ServiceSynchronizationType)` | The one you pass (a null extent means the entire network) |
| `(..., ServiceSynchronizationType, ValidationType)` | The one you pass; `ValidationType` is Normal, Repair or ForceRebuild |

Synchronous calls run on the UN server and can time out; asynchronous calls run on the GP server and Pro polls. Either way the C# call returns when the work is done. `Tracer.Trace(...)`, `Subnetwork.Update(TraceConfiguration, ServiceSynchronizationType)` and `SubnetworkExportOptions.ServiceSynchronizationType` use the same enumeration.

### 3.9 Licensing recap for SDK code

Pro Standard or Advanced; in enterprise the portal account needs Advanced Editing for validate, update subnetwork, enable/disable controllers and editing, but not for query or trace. Whether the SDK adds any license requirement beyond what the same operation needs in the UI: Verify against the Esri docs for your version.

### 3.10 Where the SDK is thinner than the UI

- No schema creation (rules, tiers, terminal configurations): use geoprocessing.
- Version management (create, reconcile, post): not covered by the UN namespace; whether to use the geodatabase version APIs or the service is a separate decision. Verify against the Esri docs for your version.
- `UtilityNetworkState` is a snapshot. Re-call `GetState()` after each operation that changes dirty areas.

## 4. One idea, four surfaces: the concept table

All five surfaces serialise the same concepts. The table gives the exact entry point on each; parameter detail is in the linked files. A dash means no equivalent was found in the sources read.

| Concept | Pro SDK (C#) | arcpy (`arcpy.un`) | REST (`UtilityNetworkServer`) | JS Maps SDK 5.1 |
|---|---|---|---|---|
| **Trace** | `TraceManager.GetTracer<T>()` or `GetTracer(NamedTraceConfiguration)`; `Tracer.Trace(TraceArgument[, ServiceSynchronizationType])` | `arcpy.un.Trace(in_utility_network, trace_type, starting_points, ...)` (`trace_type` keywords such as `UPSTREAM`; `result_types` such as `ELEMENTS`; the Pro 3.5/3.6 pages list no `PATH` or `CIRCUIT` keyword, and the 3.7 page shows Path and Circuit trace types but not their Python keywords: Verify against the Esri docs for your version) | `POST .../trace` (`traceType`, `traceLocations`, `traceConfiguration` or `traceConfigurationGlobalId`, `resultTypes`, `async`) | `utilityNetwork.trace(props)` or `trace(url, params)` from `@arcgis/core/rest/networks/trace.js`; component `<arcgis-utility-network-trace-analysis>` |
| **Starting point** | `Element` (from `CreateElement`) with a `Terminal` for multi-terminal devices | A layer or table with `FEATUREGLOBALID` (default `UN_Temp_Starting_Points`) | `{"traceLocationType":"startingPoint","globalId","terminalId"}` or `percentAlong` for edges | `TraceLocation { type: "starting-point", globalId, terminalId / percentAlong }` (kebab-case) |
| **Named trace configuration** | `NamedTraceConfigurationQuery`, `GetNamedTraceConfigurations` | `use_trace_config`, `trace_config_name` | `traceConfigurations` resource (`create`, `query`, `alter`, `delete`); `traceConfigurationGlobalId` | `utilityNetwork.sharedNamedTraceConfigurations`; `namedTraceConfigurationGlobalId` |
| **Validate** | `UtilityNetwork.ValidateNetworkTopology(...)` returning `ValidationResult`; `GetState()` first | `arcpy.un.ValidateNetworkTopology(in_utility_network, {extent})` (extent keywords `MAXOF`, `MINOF`, `DISPLAY`, layer, extent object, or "xmin ymin xmax ymax") | `POST .../validateNetworkTopology` (`validateArea`, `validationSet`, `validationType`, `async`) | `utilityNetwork.validateTopology({validateArea, validationType, validationSet})`, `submitTopologyValidationJob(...)`; component `<arcgis-utility-network-validate-network-topology>` |
| **Update subnetwork** | `Subnetwork.Update()`, `Update(TraceConfiguration, ServiceSynchronizationType)`; `SubnetworkManager.UpdateAllSubnetworks(Tier tier, bool continueOnFailure)` (returns void) | `arcpy.un.UpdateSubnetwork(in_utility_network, domain_network, tier, ...)` | `POST .../updateSubnetwork` (`domainNetworkName`, `tierName`, `subnetworkName` or `allSubnetworksInTier`, `continueOnFailure`, `async`) | - (no method found; call REST) |
| **Export subnetwork** | `Subnetwork.Export(Uri, SubnetworkExportOptions)` | `arcpy.un.ExportSubnetwork` | `POST .../exportSubnetwork` | - |
| **Associations: read** | `GetAssociations(element[, type])`, `TraverseAssociations(...)` | - (class has add/delete only) | `Associations/query`, `Associations/traverse` | `queryAssociations(props)`, `loadAssociationsTable()` |
| **Associations: write** | `EditOperation` + `AssociationDescription` (Add-in); `AddAssociation` / `DeleteAssociation` (low level) | `arcpy.un.UtilityNetwork`: `AddConnectivityAssociation`, `AddContainmentAssociation`, `AddStructuralAttachmentAssociation`, and the `Delete*` pair (Esri spells one `DeleteStructualAttachmentAssociation`); or the `Import Associations` tool | `applyEdits` on the associations system layer, `useGlobalIds: true`, integer `ASSOCIATIONTYPE` | `canAddAssociation`, `generateAddAssociations`, `generateDeleteAssociations` then `applyEdits` |
| **Association geometry** | `GetAssociationFeatures` | - | `synthesizeAssociationGeometries` (both endpoints must be inside `extent`) | `synthesizeAssociationGeometries(props)`; component `<arcgis-utility-network-associations>` |
| **Subnetwork controllers** | `SubnetworkManager.EnableController` / `DisableController` (+ `InEditOperation`) | `UtilityNetwork.EnableSubnetworkController(...)`, `DisableSubnetworkController(...)`; bulk: `Import Subnetwork Controllers` | `enableSubnetworkController`, `disableSubnetworkController` | - |
| **Topology state** | `GetState()` -> `UtilityNetworkState` | `UtilityNetwork.HasValidNetworkTopology()` (arcpy only) | `queryNetworkMoments` -> `validNetworkTopology`; `capabilities` | - |
| **Versions** | Not in the UN namespace | Pro versioning tools | `VersionManagementServer` (`create`, `reconcile`, `post`, `startEditing`, `stopEditing`, ...); UN operations take `gdbVersion` + `sessionId` | `gdbVersion` on `TraceParameters`, `validateTopology`, `applyEdits` options; no UN-specific version class |
| **Moments** | `UtilityNetworkState.LastConsistentMoment`, `LastUpdateIsConnectedMoment` | - | `moment` (epoch ms) on trace, queries; `queryNetworkMoments` | `TraceParameters.moment` (a `Date`), `Network.historicMoment` |
| **Schema read** | `UtilityNetworkDefinition` | `arcpy.Describe(un)` (`domainNetworks`, `networkAttributes`, `terminalConfigurations`, `categories`) | `FeatureServer/queryDataElements` | `utilityNetwork.dataElement` after `load()` |
| **System layers** | `GetSystemTable(SystemTableType)` | - | `utilityNetworkLayerId` -> system layers in `FeatureServer` | `utilityNetwork.networkSystemLayers` (dirty areas, rules, subnetworks, associations) |
| **Long-running** | `ServiceSynchronizationType` | Validate and Update Subnetwork (all subnetworks) tools run async via `UtilityNetworkTools` when given a service | `async=true` -> `statusUrl` polling (`Pending`, `InProgress`, then the normal body) | `submitTraceJob`, `submitTopologyValidationJob` |

Practitioner guidance: when translating a design between surfaces, translate the concept first (what does the engine do), then look up the entry point. For example, "stop at closed valves" is a condition barrier on a network attribute everywhere; its JSON property is `conditionBarriers`, its C# home is `TraceConfiguration.Traversability`, and its arcpy home is the `condition_barriers` value table.

## 5. Five worked snippets

Each snippet keeps to class, method and parameter names found in Esri documentation or in the reference files; anything else is called out. They illustrate order of operations, not production error handling. Replace placeholders in angle brackets.

### 5.1 C#: trace from a starting point with a named trace configuration

Pro 3.7 add-in. Uses a named configuration, so the traversability, result types and tier come from the administrator's saved setup (`learn/07-*.md` section 15) and no unverified `TraceConfiguration` property names are needed.

```csharp
using ArcGIS.Core.Data.UtilityNetwork;
using ArcGIS.Core.Data.UtilityNetwork.Trace;
using ArcGIS.Desktop.Framework.Threading.Tasks;

public static Task<List<Element>> TraceFromDeviceAsync(
    UtilityNetwork utilityNetwork,
    string sourceName,          // e.g. the device class name from GetNetworkSources()
    string assetGroupName, string assetTypeName,
    Guid startGlobalId, string namedTraceName)
{
  return QueuedTask.Run(() =>                       // all UN calls on the MCT
  {
    using (UtilityNetworkDefinition definition = utilityNetwork.GetDefinition())
    using (NetworkSource source = definition.GetNetworkSource(sourceName))
    using (AssetGroup group = source.GetAssetGroup(assetGroupName))
    using (AssetType assetType = group.GetAssetType(assetTypeName))
    using (TraceManager traceManager = utilityNetwork.GetTraceManager())
    {
      // 1. Element = row handle. Identity is the GlobalID, never the ObjectID.
      Element start = utilityNetwork.CreateElement(assetType, startGlobalId);

      // 2. A terminal is required when the configuration has several terminals
      //    (otherwise Trace throws InvalidOperationException). Choose deliberately.
      if (assetType.IsTerminalConfigurationSupported())
      {
        using (TerminalConfiguration config = assetType.GetTerminalConfiguration())
        {
          start.Terminal = config.Terminals.First(t => t.IsUpstreamTerminal);
        }
      }

      // 3. Find the saved configuration by name, build the tracer from it.
      var query = new NamedTraceConfigurationQuery { Names = new List<string> { namedTraceName } };
      NamedTraceConfiguration named = traceManager.GetNamedTraceConfigurations(query).FirstOrDefault();
      if (named == null) throw new InvalidOperationException("No such named trace configuration.");
      Tracer tracer = traceManager.GetTracer(named);

      // 4. Argument = named configuration + starting elements; ask for elements back.
      var argument = new TraceArgument(named, new List<Element> { start });
      argument.ResultTypes = new List<ResultType> { ResultType.Element };

      // 5. Run it. Synchronous call; the overload with ServiceSynchronizationType
      //    only matters when the UN is service-backed.
      IReadOnlyList<Result> results = tracer.Trace(argument);

      // 6. Result type matches the requested ResultType.
      return results.OfType<ElementResult>().SelectMany(r => r.Elements).ToList();
    }
  });
}
```

Notes: `GetFeaturesForElements(elements)` converts the result into ObjectID-based `Selection` objects when you need real features. The trace reads the saved topology, so validate first (snippet 5.2). Whether `ResultTypes` is required when the named configuration already names result types: Verify against the Esri docs for your version.

### 5.2 C#: check state, then validate an extent

Pro 3.7, CoreHost-safe (base method). In an Add-in use `ValidateNetworkTopologyInEditOperation` so the map refreshes and Pro's undo stack gets an entry; its overloads per ProConcepts are `(UtilityNetwork)`, `(UtilityNetwork, Geometry)`, `(UtilityNetwork, Geometry, ServiceSynchronizationType)`, `(UtilityNetwork, IEnumerable<Selection>)` and `(UtilityNetwork, IEnumerable<Selection>, ServiceSynchronizationType)`; none takes `ValidationType`.

```csharp
using ArcGIS.Core.Data.UtilityNetwork;
using ArcGIS.Core.Geometry;
using ArcGIS.Desktop.Framework.Threading.Tasks;

public static Task<ValidationResult> ValidateExtentAsync(UtilityNetwork utilityNetwork, Envelope extent)
{
  return QueuedTask.Run(() =>
  {
    UtilityNetworkState state = utilityNetwork.GetState();           // cheap snapshot

    if (!state.IsNetworkTopologyEnabled)
      throw new InvalidOperationException("Topology is disabled: nothing is tracked or validated.");

    if (!state.HasDirtyAreas)
      return null;                                                    // nothing to do

    // Must not be called inside an edit operation or Geodatabase.ApplyEdits.
    // Extent overload = synchronous endpoint, meant for small areas.
    ValidationResult result = utilityNetwork.ValidateNetworkTopology(
        extent, ServiceSynchronizationType.Synchronous, ValidationType.Normal);

    // "Success" only means the job ran. Check the outcome.
    if (result.HasErrors) { /* open Error Inspector, or read the DirtyAreas system table */ }
    if (result.IsDiscoveredSubnetworksSupported)
    {
      var dirtySubnetworks = result.GetDiscoveredSubnetworks();       // subnetworks marked Dirty
      // plan Update Subnetwork for these
    }
    return result;
  });
}
```

Notes: use `ValidationType.Repair` only after Normal fails and `ForceRebuild` only after Repair fails (`pro-sdk/01-*.md`). The same service-versus-geodatabase rule applies: on a file or mobile geodatabase `ServiceSynchronizationType` is ignored. A whole-network `ValidateNetworkTopology()` uses the asynchronous endpoint.

### 5.3 arcpy: validate, then update every subnetwork in a tier

Pro 3.7, Python with Pro installed. The inputs are a utility network **service** (or a UN layer that points to one) because the enterprise tools refuse database connections (`learn/01-*.md`). Keyword values are from the Esri tool pages; Esri's own second example passes `"ALL"` while the table lists `ALL_SUBNETWORKS_IN_TIER`, so the documented keyword is used.

```python
import arcpy

un = "Utility Network"            # a UN layer in the current project, or a UN service connection
extent = "-9815000 5127000 -9814000 5128000"   # xmin ymin xmax ymax, in the network's coordinate system

# 1. Validate the work area (needs Advanced Editing in enterprise).
arcpy.un.ValidateNetworkTopology(un, extent)
print(arcpy.GetMessages())

# 2. Update all subnetworks in a tier, rank order, stop on first failure.
#    Preconditions (Esri): topology enabled, edits saved, no dirty areas intersecting the subnetworks,
#    traditional domain network only, one process per subnetwork at a time.
try:
    arcpy.un.UpdateSubnetwork(
        un,
        "ElectricDistribution",           # domain network name
        "Medium Voltage",                 # tier name
        all_subnetworks_in_tier="ALL_SUBNETWORKS_IN_TIER",   # or SPECIFIC_SUBNETWORK + subnetwork_name
        continue_on_failure="STOP_ON_FAILURE")               # or CONTINUE_ON_FAILURE
except arcpy.ExecuteError:
    # Typical cause: a dirty area still intersects a subnetwork, or the subnetwork is already clean.
    print(arcpy.GetMessages(2))
    raise
```

Notes: the Python signature is `UpdateSubnetwork(in_utility_network, domain_network, tier, {all_subnetworks_in_tier}, {subnetwork_name}, {continue_on_failure}, {condition_barriers}, {function_barriers}, {include_barriers}, {traversability_scope}, {propagators})`; `ALL_SUBNETWORKS_IN_TIER` and `STOP_ON_FAILURE` are the defaults. Swap `ALL_SUBNETWORKS_IN_TIER` for `SPECIFIC_SUBNETWORK` and a name (Esri's example 1 uses `"RMT004"` with `CONTINUE_ON_FAILURE`). Tier ordering and scheduling patterns are in `learn/10-performance-scale-and-operations.md` section 11. The `arcpy.un.UtilityNetwork` class does not have an update method; update subnetwork is a tool.

### 5.4 REST: trace using a named configuration (async with polling)

Python `requests`; works against any UN service. Only names from `rest-api/01-*.md`, `rest-api/06-*.md` and `rest-api/08-*.md` appear. `async` is a Python keyword, so it goes through a dict.

```python
import time, requests

UNS = "https://<host>/server/rest/services/<Service>/UtilityNetworkServer"
TOKEN = "<token>"                       # from your org's auth flow; trace needs no user type extension

def post(path, **params):
    r = requests.post(f"{UNS}/{path}", data={"f": "json", "token": TOKEN, **params}, timeout=120)
    r.raise_for_status()
    body = r.json()
    if body.get("error") or body.get("success") is False:
        raise RuntimeError(body)
    return body

# 1. Find the named configuration (shared by an admin from Pro).
cfgs = post("traceConfigurations/query", names='["Downstream Trace"]')["traceConfigurations"]
cfg_id = cfgs[0]["globalId"]

# 2. Starting point: GUID + terminalId for a junction/device, percentAlong for an edge.
locations = '[{"traceLocationType":"startingPoint","globalId":"{<GUID>}","terminalId":1}]'

# 3. Submit asynchronously, DEFAULT version (no sessionId on DEFAULT).
job = post("trace", **{
    "traceType": "downstream",                 # required; the stored type of the named config wins
    "traceLocations": locations,
    "traceConfigurationGlobalId": cfg_id,
    "resultTypes": '[{"type":"elements"}]',
    "gdbVersion": "sde.DEFAULT",
    "async": "true"})

# 4. Poll the flat statusUrl (NOT the GPServer esriJob* vocabulary).
status = job["statusUrl"]
while True:
    s = requests.get(status, params={"f": "json", "token": TOKEN}, timeout=60).json()
    if s.get("status") not in ("Pending", "InProgress"):
        break
    time.sleep(5)

# 5. The completed body repeats the synchronous trace body (verify against the Esri docs for your version).
results = s.get("traceResults", {})
print("warnings:", results.get("warnings"), "start ignored:", results.get("startingPointsIgnored"))
for e in results.get("elements", []):
    # Codes, not names: map networkSourceId / assetGroupCode / assetTypeCode via queryDataElements.
    print(e["networkSourceId"], e["globalId"], e.get("objectId"), e.get("terminalId"))
```

Notes: for a named version add `gdbVersion` as `owner.versionName` and the `sessionId` of the lock holder only if that version is under an exclusive lock (`learn/08-*.md` section 4). Validate a hand-written request with `scripts/build_trace_request.py --check request.json`. If the service is a Trace Network (`TraceNetworkServer`), the available trace types are narrower (`rest-api/01-*.md`).

### 5.5 JavaScript (Maps SDK 5.1): trace with a shared named configuration

Web map that contains a utility network and shared named trace configurations; topology enabled and validated; user signed in. For a ready-made panel use `<arcgis-utility-network-trace-analysis>` instead (`js-api/04-*.md`).

```javascript
import TraceLocation from "@arcgis/core/rest/networks/support/TraceLocation.js";

const viewElement = document.querySelector("arcgis-map");
await new Promise((resolve) =>                         // pattern from js-api/01
  viewElement.addEventListener("arcgisViewReadyChange", resolve, { once: true }));
const webMap = viewElement.map;

// A web map may hold several utility networks; pick by name in a real app.
const utilityNetwork = webMap.utilityNetworks.getItemAt(0);
await utilityNetwork.load();                           // populates dataElement and sharedNamedTraceConfigurations

const named = utilityNetwork.sharedNamedTraceConfigurations
  .find((c) => c.title === "Downstream Trace");        // titles are not unique; globalId is
if (!named) throw new Error("Named trace configuration not shared with this web map.");

const start = new TraceLocation({
  type: "starting-point",                              // JS: kebab-case; REST: "startingPoint"
  globalId: "{<GUID>}",
  terminalId: 1                                        // junction/device; use percentAlong (0..1) for lines
});

const result = await utilityNetwork.trace({
  namedTraceConfigurationGlobalId: named.globalId,
  traceLocations: [start],
  resultTypes: [{ type: "elements", includeGeometry: false }]
});

if (result.warnings?.length) console.warn(result.warnings);
if (result.startingPointsIgnored) console.warn("Trace ignored the starting points: check terminalId / percentAlong.");

// elements are NetworkElement objects; resolve them to real layers and ObjectIDs:
const layerInfos = utilityNetwork.getObjectIdsFromElements(result.elements);
// ...then query/select on the matching layers; global function results are in result.globalFunctionResults.
```

Notes: `utilityNetwork.trace()` takes `TraceProperties` (`namedTraceConfigurationGlobalId`, `traceLocations`, `outSpatialReference`, `traceConfiguration`, `resultTypes`, `traceType`) and fills in `gdbVersion` and `moment` from the network object. To trace a named branch version explicitly, use the functional form `trace(url, new TraceParameters({ gdbVersion, ... }))` (`js-api/06-*.md`). Sources for the `TraceLocation` property names are the 5.1 class reference; its `type` values are `"starting-point"` and `"barrier"`. The exact `resultTypes` shape follows the REST schema; confirm in the `jsonTypes` reference for your SDK version.

## 6. Common mistakes of developers new to the UN

| # | Mistake | Why it fails | Fix |
|---|---|---|---|
| 1 | Keying on **ObjectID** (storing it, passing it as a trace start) | The UN refers to rows by GlobalID (associations, dirty areas, subnetworks, trace locations). ObjectIDs are 64-bit from dataset v7 and `Element.ObjectID` is -1 unless fetched | Use GlobalID plus network source ID; resolve ObjectIDs at the end (`getObjectIdsFromElements`, `GetFeaturesForElements`). See `learn/02-*.md` section 5 |
| 2 | **Terminal IDs** omitted or wrong | A multi-terminal device with no terminal makes C# throw `InvalidOperationException`; a REST location without `terminalId`/`percentAlong` is silently ignored; the terminal decides the trace direction | Always set the terminal for devices, `percentAlong` for edges; check `startingPointsIgnored`; telecom uses `terminalId: 1` per the JS reference |
| 3 | **Session IDs**: sending `sessionId` on DEFAULT, or omitting it on a named version | UN operations require it for a named version and forbid it for DEFAULT; spelling differs by page (`sessionId`, `sessionID`) | Use the spelling on the operation's own page; start/stop sessions through `VersionManagementServer` (`learn/08-*.md` section 4) |
| 4 | **Version names** | `gdbVersion` is `owner.versionName` (for example `sde.DEFAULT`); creation limits (62 chars, no `.` `;` `'` `"`) | Read names from `versionInfos`; never build them by hand |
| 5 | **Async polling** copied from a GPServer sample | UN `async=true` returns a flat `statusUrl`; states `Pending` and `InProgress`; no `jobId`, no `esriJobSucceeded`, no `results/` | Poll until `status` leaves `Pending`/`InProgress`; read the body at the same URL (`rest-api/06-*.md`) |
| 6 | **Job<T> confusion** | `Job`, `Start()`, `GetStateAsync()` belong to the Maps SDK for .NET (`Esri.ArcGISRuntime.UtilityNetworks`), not to the Pro SDK, which has plain synchronous methods and `ServiceSynchronizationType` | Pick the SDK by namespace: `ArcGIS.Core.Data.UtilityNetwork` (Pro) vs `Esri.ArcGISRuntime.UtilityNetworks` (native) |
| 7 | **Deprecated widgets** in new JS 5.x apps | `UtilityNetworkTrace`, `UtilityNetworkAssociations`, `UtilityNetworkValidateTopology` widgets are deprecated since 5.0; `<arcgis-utility-network-trace>` since 5.0; `<arcgis-utility-network-validate-topology>` as of 5.1 | `<arcgis-utility-network-trace-analysis>`, `<arcgis-utility-network-associations>`, `<arcgis-utility-network-validate-network-topology>` (`js-api/04-*.md`, `js-api/05-*.md`) |
| 8 | **`shortestPath`** | Deprecated at Pro 3.7 / Enterprise 12.1 in favour of `path` (the arcpy 3.4 page still lists `SHORTEST_PATH`) | Use `path` where the service supports it; verify the trace type list for your version |
| 9 | **Tracing before validating** | The trace reads the topology, not the map; dirty areas are not barriers | Edit, validate, then trace; enable `validateConsistency` in REST (default true) or the Pro tool option |
| 10 | **Treating "job succeeded" as "no errors"** | The REST response and `ValidationResult` also report errors created | Check `validateErrorsCreated`, `dirtyAreaCount`, `HasErrors` |
| 11 | **Wrong REST constants across surfaces** | `traceLocationType` is `startingPoint` in REST and `type: "starting-point"` in JS; association `types` filter is camelCase in REST query, a string in `applyEdits` (the same camelCase names as REST query; the integer codes are for the geodatabase field and arcpy), text in the CSV; JS deletes need `globalIdUsed: true` | Use `scripts/association_types.py`; copy names from the exact surface's reference file |
| 12 | **arcpy method names that exist only in one language** | `HasValidNetworkTopology()` is arcpy only; the C# way is `GetState()` | Cross-check with the concept table in section 4 |
| 13 | **Association edits without rules** | Every surface enforces the rule requirement (`canAddAssociation` in JS checks before writing). `utilityNetworkOptions: 1` skips the check and defers errors to the next validate | Add the rule first (topology disabled) or use the bypass only for trusted bulk loads (`rest-api/05-*.md`) |
| 14 | **Using low-level `AddAssociation` in an Add-in** | No map refresh, no undo | `EditOperation` pattern (section 3.6) |
| 15 | **Calling `Subnetwork.Update()` or `ValidateNetworkTopology` inside an edit operation** | Both manage their own transaction | Save or discard first; call outside the edit operation or use the `InEditOperation` extensions in an Add-in |
| 16 | **Publishing assumptions**: enterprise tools given a database connection | Validate and Update Subnetwork tools need a UN service as input in enterprise | Use a service URL or a layer from a service (`pro-help/10-*.md`) |
| 17 | **Assuming `fromPortalItem` loads trace configurations** | Documented gap | Load through a web map, or query named trace configurations separately (`js-api/03-*.md`) |
| 18 | **Assuming a native or Field Maps client supports your dataset version** | Esri notes no UN v8 support with Enterprise 12.1 | Check `learn/08-*.md` section 12 and `pro-help/09-*.md` before upgrading |

## Common misconceptions

- "The Pro SDK can configure my network." It is DML only; configuration is geoprocessing.
- "arcpy.un.UtilityNetwork is the arcpy twin of the C# `UtilityNetwork`." It is a small class for associations and controllers; most of the surface is tools.
- "The JS trace widget is the same as the component." The widget and `<arcgis-utility-network-trace>` are deprecated since 5.0; `<arcgis-utility-network-trace-analysis>` is the current component.
- "REST async and GPServer async are the same." Different vocabularies and endpoints.
- "There is a Python API method for everything." No UN trace/validate helper was confirmed; treat it as a gap.
- "Experience Builder can do everything the JS SDK can." Trace and Branch Version Management are covered; validation and associations are thin (`experience-builder/01-utility-network-widgets.md`).
- "A trace on a named version needs a session." Only if the version holds an exclusive lock by another session.

## Quick checks

Ask or verify, in this order:

1. Which surface is the user really in? Namespace (`ArcGIS.Core.Data.UtilityNetwork`, `Esri.ArcGISRuntime.UtilityNetworks`, `@arcgis/core`), or `arcpy.un`, or a REST URL?
2. Enterprise or single-user? DEFAULT or a named version? Is a `sessionId` involved?
3. Pro, Enterprise, SDK and UN dataset versions? (Many names here have version floors: `path`/`circuit` traces 12.1; `UtilityNetwork.trace()` 4.27; association editing helpers 4.29; telecom managers 4.34.)
4. Has the area been validated since the last edit? Is topology enabled? Does a dirty area intersect the start or path?
5. Are start locations identified by GlobalID with a terminal or `percentAlong`?
6. Which thread runs the C# call; is anything `using`-disposed too early?
7. Is the call inside an edit operation when it manages its own transaction?
8. Does the account hold Advanced Editing (needed to edit, validate, update; not to trace)?
9. For async calls: is the polling code written for `statusUrl` and the `Pending`/`InProgress` states?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/03-topology-engine-and-validation.md`, `learn/07-tracing-in-depth-and-configuration-library.md`, `learn/08-versioning-and-editing-workflows.md`, `learn/09-failure-anatomy-symptom-to-fix.md`, `learn/10-performance-scale-and-operations.md`
- `pro-sdk/01-csharp-sdk-utility-network-api.md`, `arcpy/01-utility-network-module.md`
- `rest-api/01-utility-network-server-and-trace.md`, `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/04-version-management-validation-feature-service.md`, `rest-api/05-feature-service-associations-appendix.md`, `rest-api/06-asynchronous-operations-job-status.md`, `rest-api/08-trace-configuration-full-schema.md`
- `js-api/01-javascript-sdk-utility-network.md`, `js-api/03-network-class-loading-and-definition.md`, `js-api/04-trace-results-and-widgets.md`, `js-api/05-editing-associations-validation.md`, `js-api/06-functional-api-web-components-calcite.md`
- `experience-builder/01-utility-network-widgets.md`
- `scripts/build_trace_request.py`, `scripts/association_types.py`, `scripts/decode_dirty_status.py`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/conceptdocs/docs/ProConcepts-Utility-Network.html (ProConcepts: namespaces, threading, validation synchronization, edit operations)
- https://github.com/esri/arcgis-pro-sdk/wiki/ProConcepts-Utility-Network (same page, GitHub copy)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/conceptdocs/docs/ProSnippets-UtilityNetwork.html (snippet headings and calls)
- https://pro.arcgis.com/en/pro-app/3.4/sdk/api-reference/topic17434.html (ArcGIS.Core.Data.UtilityNetwork namespace listing)
- https://pro.arcgis.com/en/pro-app/latest/sdk/api-reference/topic17637.html (UtilityNetwork class methods)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic15120.html (What's new for developers at 3.7: telecom, path, circuit)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic18396.html (DownstreamTracer.Trace overload)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic18394.html (ConnectedTracer.Trace overload)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic18070.html (TraceArgument members)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic19072.html (ResultType enumeration)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic7647.html (ServiceConnectionProperties constructor and feature service example)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic7649.html (ServiceConnectionProperties.URL)
- https://doc.esri.com/en/arcgis-pro/latest/arcpy/utility-network/what-is-the-utility-network-module.html (arcpy.un module)
- https://pro.arcgis.com/en/pro-app/3.4/tool-reference/utility-networks/update-subnetwork.htm (Python syntax and keywords)
- https://pro.arcgis.com/en/pro-app/3.4/tool-reference/utility-networks/validate-network-topology.htm (Python syntax and extent keywords)
- https://pro.arcgis.com/en/pro-app/3.4/tool-reference/utility-networks/trace.htm (arcpy.un.Trace signature)
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html (requirements and licensing)
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html (extent options, derived outputs)
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html (trace types and starting points)
- https://developers.arcgis.com/javascript/latest/references/core/networks/UtilityNetwork/ (JS methods and versions)
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/TraceLocation/ (TraceLocation properties)
- https://developers.arcgis.com/javascript/latest/references/core/rest/networks/support/TraceParameters/ (TraceParameters properties)
- https://developers.arcgis.com/javascript/latest/references/core/networks/support/NamedTraceConfiguration/ (NamedTraceConfiguration properties)
- https://developers.arcgis.com/javascript/latest/utility-network/tracing/ (JS tracing guide)
- https://developers.arcgis.com/net/api-reference/api/netwin/Esri.ArcGISRuntime/Esri.ArcGISRuntime.UtilityNetworks.UtilityNetwork.html (Maps SDK for .NET UtilityNetwork)
- Existing skill reference files named in the text (REST, JS, Experience Builder and learn files), which carry their own Esri source lists.
