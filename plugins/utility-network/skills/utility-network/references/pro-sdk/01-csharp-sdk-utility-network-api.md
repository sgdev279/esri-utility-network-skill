# Utility Network — ArcGIS Pro SDK (C#/.NET) Deep Reference
*Source: Esri "ProConcepts Utility Network" (GitHub wiki + doc.esri.com SDK conceptdocs),
Esri "Utility Network Object Model Diagram," arcpy Utility Network module docs*

> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

**Audience note**: this is for developers extending **ArcGIS Pro itself** via a
C# Add-in (or CoreHost app) — a different audience from REST/JS web developers.
Use this file when the user is writing a **Pro Add-in**, not a web app.

## Two distinct utility-network APIs — don't conflate them

There are **two separate, non-interchangeable** utility network programming
surfaces inside the Pro ecosystem:

1. **`arcpy.un` (ArcPy Utility Network module)** — Python, geoprocessing-tool
   based, plus a small `arcpy.un.UtilityNetwork` class for associations and
   subnetwork controllers. Fully documented in
   `arcpy/01-utility-network-module.md`; don't duplicate it here.
2. **`ArcGIS.Core.Data.UtilityNetwork` (Pro SDK, C#)** — the "real" object-oriented
   API for building Add-ins, covered in the rest of this file. Tracing-specific
   types live in **`ArcGIS.Core.Data.UtilityNetwork.Trace`**.

If someone asks for "the utility network API," always clarify **which** one —
a script meant for the Python window should not use `ArcGIS.Core.Data`, and a
Pro Add-in should not shell out to arcpy GP tools for anything performance
sensitive (arcpy GP tool calls are comparatively heavyweight vs. the native
C# API inside an Add-in's own process).

## Architecture facts (C# SDK)

- The C# API is explicitly a **Data Manipulation Language (DML)-only API** —
  it reads and writes rows/associations/subnetwork state; it does **not**
  handle schema creation/configuration (that's the GP-tool/arcpy layer covered
  in the Pro Help reference files).
- Namespaces:
  - `ArcGIS.Core.Data.UtilityNetwork` — core classes (`UtilityNetwork`,
    `Element`, `Association`, `UtilityNetworkDefinition`, etc.)
  - `ArcGIS.Core.Data.UtilityNetwork.Trace` — tracing-specific classes
    (`TraceManager`, tracers, `TraceConfiguration`, barriers, comparisons).
- **Extension methods**: some higher-level Pro-integration functionality is
  provided via C# extension methods requiring:
  ```csharp
  // Add a reference to ArcGIS.Desktop.Extensions in your project, then:
  using ArcGIS.Core.Data.UtilityNetwork.Extensions;
  ```
  These extension methods are **only usable inside ArcGIS Pro Add-ins** —
  **not available in CoreHost** (standalone, non-Pro-hosted) applications. If
  someone is building a CoreHost app, flag this limitation early.
- **REST timeout caveat** (explicitly called out by Esri, relevant when a Pro
  Add-in or script talks to a published service instead of a local
  connection): most utility-network REST operations via `UtilityNetworkServer`
  are **synchronous** and have low processing overhead normally, but are
  **susceptible to timeout** if the underlying processing takes too long
  (large trace, large export) — worth mentioning when someone's REST/service
  calls intermittently time out on big networks.

## `UtilityNetwork` class — key methods (from the Object Model Diagram)

The root object. Representative method surface (not exhaustive, but covers
the methods people actually reach for):

| Method | Purpose |
|---|---|
| `GetDefinition()` → `UtilityNetworkDefinition` | Schema/definition access point (network attributes, sources, rules, terminal configurations). |
| `GetTraceManager()` → `TraceManager` | Entry point for tracing (see below). |
| `GetSubnetworkManager()` → `SubnetworkManager` | Entry point for subnetwork life-cycle operations. |
| `GetDiagramManager()` → `DiagramManager` | Entry point for network diagram operations. |
| `GetTable(NetworkSource)` → `Table` | The underlying geodatabase table for a given network source. |
| `GetSystemTable(SystemTableType)` → `Table` | System tables — enum has `PointErrors`, `LineErrors`, `PolygonErrors`, `DirtyAreas`, `Subnetworks`, `Associations`. The three `*Errors` tables are **not supported once the schema version (`UtilityNetworkDefinition.GetSchemaVersion()`) is 4 or greater** — i.e. on current v8 datasets only `DirtyAreas`, `Subnetworks` and `Associations` are available. Guard with `IsSystemTableSupported(...)`. |
| `IsSystemTableSupported(SystemTableType)` → `bool` | Guard before calling `GetSystemTable`. |
| `CreateElement(AssetType, Guid, Terminal)` → `Element` | Build an `Element` handle for a feature without a full row fetch. |
| `GetAssociations(Element[, AssociationType])` → `IReadOnlyList<Association>` | Query associations for a feature, optionally filtered by type. |
| `GetAssociationFeatures(Envelope[, AssociationType])` | Spatial query for association features. |
| `AddAssociation(Association)` / `DeleteAssociation(Association)` | Low-level association editing (see caveats below). |
| `GetExtent()` | Envelope covering the maximum extent of the stored data (`UtilityNetworkDefinition.GetServiceTerritoryEnvelope()` returns the same extent). |
| `GetServerCapabilities()` → `UtilityNetworkServerCapabilities` | What the backing service supports (relevant when the UN is service-backed); guard with `AreServerCapabilitiesSupported()`. |
| `GetState()` → `UtilityNetworkState` | Synchronous snapshot of topology state: `IsNetworkTopologyEnabled`, `HasDirtyAreas`, `HasErrors`, `LastConsistentMoment`, `LastUpdateIsConnectedMoment`. Call on the MCT (`QueuedTask.Run`). |
| `ValidateNetworkTopology(...)` → `ValidationResult` | Programmatic topology validation. Overloads: `()`, `(Geometry)`, `(Geometry, ServiceSynchronizationType)`, `(Geometry, ServiceSynchronizationType, ValidationType)` and the same three with `IEnumerable<Selection>`. `ValidationType` has `Normal`, `Repair`, `ForceRebuild`. Extension method `ValidateNetworkTopologyInEditOperation` (Add-in only) adds an undo/redo entry and refreshes the map. |
| `GetCircuitManager()` / `GetUnitIdentifierManager()` / `TraverseAssociations(...)` | Other documented members of the class (circuits, unit identifiers, association traversal). |

**Schema introspection lives on `UtilityNetworkDefinition`** (obtained via `utilityNetwork.GetDefinition()`), not on `UtilityNetwork` itself: `GetNetworkSources()`, `GetRules()`, `GetTerminalConfigurations()`, `GetSchemaVersion()` (returns a string), `GetServiceTerritoryEnvelope()`. These mirror the arcpy `Describe` properties covered in the Pro Help reference.

## `Element` class

`Element` is the SDK's lightweight handle to a network feature (roughly
analogous to a row reference, but understood by trace/association/subnetwork
APIs without a full row fetch).

**Creating an element from a fresh row:**
```csharp
using (RowBuffer lineRowBuffer = table.CreateRowBuffer(mediumVoltageSubtype))
{
  lineRowBuffer["Name"] = "Overhead Line";
  using (Row lineRow = table.CreateRow(lineRowBuffer))
  {
    Element lineElement = utilityNetwork.CreateElement(lineRow);
  }
}
```

**Fetching the underlying row back from an element** (when you need full
attribute access, not just the element handle):
```csharp
public static Row FetchRowFromElement(UtilityNetwork utilityNetwork, Element element)
{
  using (Table table = utilityNetwork.GetTable(element.NetworkSource))
  using (TableDefinition tableDefinition = table.GetDefinition())
  {
    QueryFilter queryFilter = new QueryFilter()
    {
      WhereClause = tableDefinition.GetGlobalIDField() + " = {" +
                     element.GlobalID.ToString().ToUpper() + "}"
    };
    using (RowCursor rowCursor = table.Search(queryFilter))
    {
      if (rowCursor.MoveNext())
      {
        return rowCursor.Current;
      }
    }
  }
  return null;
}
```

## Network topology

- There is **no `HasValidNetworkTopology()` member** on the Pro SDK
  `ArcGIS.Core.Data.UtilityNetwork.UtilityNetwork` class. That name is a method
  of the **arcpy** class `arcpy.un.UtilityNetwork` (returns `True` when topology
  is enabled) — see `arcpy/01-utility-network-module.md`. Don't carry it over
  into C#.
- In C#, read topology state with **`utilityNetwork.GetState()`** (call on the
  MCT inside `QueuedTask.Run`), which returns a `UtilityNetworkState` with
  `IsNetworkTopologyEnabled`, `HasDirtyAreas`, `HasErrors`,
  `LastConsistentMoment` and `LastUpdateIsConnectedMoment`.
- Whether topology must be enabled/valid before creating associations or
  modifying subnetwork controllers: Verify against the Esri docs for your
  version.
- `ValidateNetworkTopology(...)` runs validation and returns a
  **`ValidationResult`** (`HasErrors`, `IsFullUpdate`, `UpdateLocalTime`,
  `IsDiscoveredSubnetworksSupported`, `GetDiscoveredSubnetworks()`). Pass a
  `ValidationType` of `Normal`, `Repair` (rebuild the dirty-area extents; use
  when Normal fails) or `ForceRebuild` (ignore dirty areas and rebuild the whole
  given extent; use when Repair fails).
- `ValidateNetworkTopology` manages its own transaction, so it **cannot be
  issued inside an edit operation** and cannot be wrapped in
  `Geodatabase.ApplyEdits`. In an Add-in use the extension method
  `ValidateNetworkTopologyInEditOperation` instead (refreshes map views and adds
  an entry to the Pro operation stack).

## Long-running operations in the Pro SDK — there is no `Job<T>`

The Pro SDK (`ArcGIS.Core.Data.UtilityNetwork`) has **no `Job<T>`,
`UtilityNetworkValidationJob`, `GeoprocessingExecutionType`, `.Start()` /
`CancelAsync()` job lifecycle or `GetStateAsync()`**. Those belong to a
different product: the **ArcGIS Maps SDK for .NET / Native Apps runtime**
(`Esri.ArcGISRuntime.UtilityNetworks`), where
`UtilityNetwork.ValidateNetworkTopology(Envelope[, GeoprocessingExecutionType])`
returns a job and `GetStateAsync()` exists. Don't mix the two: a Pro Add-in or
CoreHost app never calls `.Start()` on a validation.

What the Pro SDK has instead:
- Calls are **plain synchronous methods** that must run on the MCT:
  `await QueuedTask.Run(() => utilityNetwork.ValidateNetworkTopology(extent));`.
- **`ServiceSynchronizationType`** (`Synchronous` | `Asynchronous`) selects which
  flavour of the service endpoint is called when the utility network is
  service-backed. `Synchronous` runs faster but the client may time out;
  `Asynchronous` is slower to start but the client won't time out. It is ignored
  for non-service-based utility networks (e.g. file or mobile geodatabases). It appears on
  `ValidateNetworkTopology(Geometry, ServiceSynchronizationType[, ValidationType])`,
  `Subnetwork.Update(TraceConfiguration, ServiceSynchronizationType)` and as the
  `ServiceSynchronizationType` property on `SubnetworkExportOptions`.
- Per Esri's ProConcepts: the extent overload is intended for small areas and
  uses the synchronous service endpoint; `ValidateNetworkTopology()` with no
  arguments validates the entire network using the asynchronous endpoint.
- `GetState()` (synchronous, see above) is the lightweight "is there a problem"
  check before deciding whether a full validation is needed.

The REST-level single-session constraint on validating the DEFAULT version
(`rest-api/02-topology-and-subnetwork-management-operations.md`) is a
service/enterprise-geodatabase rule; whether and how it surfaces through the Pro
SDK: Verify against the Esri docs for your version.

## Associations (C# API)

- `AddAssociation()` / `DeleteAssociation()` on `UtilityNetwork`, taking an
  `Association` object — these are the **low-level** editing methods.
- **Explicit caution from Esri**: these low-level methods are fine in a
  stand-alone (CoreHost) application, but are **not recommended inside an
  ArcGIS Pro Add-in** because they **do not refresh the map** and **do not
  participate in the undo/redo stack** — using them in an Add-in silently
  desyncs the UI from the underlying edits. Inside a Pro Add-in, prefer the
  **`EditOperation`**-based pattern (see "Pro Integration" below) so edits
  play nicely with the map and undo/redo.
- `GetAssociations(element)` — query associations for a given element,
  optionally filtered by `AssociationType`.

### Editing associations with `EditOperation` (Pro Add-in–correct pattern)
```csharp
EditOperation editOperation = new EditOperation();
editOperation.Name = "Create structural attachment association";

Element poleElement = utilityNetwork.CreateElement(poleAssetType, poleGlobalID);
RowHandle poleRowHandle = new RowHandle(poleElement, utilityNetwork);

Element transformerBankElement = utilityNetwork.CreateElement(transformerBankAssetType, transformerBankGlobalID);
RowHandle transformerBankRowHandle = new RowHandle(transformerBankElement, utilityNetwork);

// ... editOperation then adds an association description between the two
// RowHandles and is executed (editOperation.Execute()) like any other Pro edit.
```

### Creating features AND an association in one edit operation
```csharp
EditOperation editOperation = new EditOperation();
editOperation.Name = "Create pole; create transformer bank; attach transformer bank to pole";

RowToken transformerBankToken = editOperation.CreateEx(transformerBankLayer, transformerBankAttributes);
RowToken poleToken = editOperation.CreateEx(poleLayer, poleAttributes);

RowHandle poleHandle = new RowHandle(poleToken);
RowHandle transformerBankHandle = new RowHandle(transformerBankToken);
// ... editOperation adds a structural-attachment AssociationDescription between
// poleHandle and transformerBankHandle before Execute() — letting Pro create
// two brand-new features AND their association atomically in one undo-able step.
```

## Subnetworks (C# API)

- `GetSubnetworkManager()` → `SubnetworkManager` is the entry point. Its members:
  `GetSubnetwork`, `GetSubnetworks`, `UpdateAllSubnetworks`, `EnableController`,
  `DisableController`, plus the Add-in extension methods
  `EnableControllerInEditOperation` / `DisableControllerInEditOperation`.
- A single subnetwork is a `Subnetwork` object: **`Subnetwork.Update()`**,
  `Update(TraceConfiguration)` and `Update(TraceConfiguration, ServiceSynchronizationType)`
  are the code equivalent of the Update Subnetwork GP tool, and
  **`Subnetwork.Export(Uri, SubnetworkExportOptions)`** writes the export JSON
  (the Export Subnetwork equivalent). There are no `UpdateSubnetwork` /
  `ExportSubnetwork` methods on the manager.
- `Subnetwork.Update()` cannot be called inside an edit transaction (save or
  discard pending edits first); `EnableController`/`DisableController` manage
  their own transaction and cannot be called inside another edit operation.
  `Export` with `SetAcknowledged = true` throws if called inside
  `Geodatabase.ApplyEdits()`.
- **`SubnetworkExportOptions`** — the object controlling an export, with
  (confirmed against the Pro 3.7 class reference) these properties:
  | Property | Purpose |
  |---|---|
  | `SetAcknowledged` | Whether to mark the export as acknowledged. When true, the DEFAULT version is required; it physically deletes the subnetwork rows marked as deleted. |
  | `IncludeDomainDescriptions` | Include human-readable domain/coded-value descriptions in export output. |
  | `IncludeGeometry` | Include feature geometry in the export. |
  | `ServiceSynchronizationType` | `Synchronous` or `Asynchronous` — controls sync vs. async export execution against a service (inherited from `ExportOptions`). |
  | `SubnetworkExportResultTypes` | A list, e.g. `{ SubnetworkExportResultType.Connectivity, SubnetworkExportResultType.Features }` — controls what's actually included in the export payload. |
  | `ResultNetworkAttributes` | Which network attributes to include (typically populated from `utilityNetworkDefinition.GetNetworkAttributes()`). |
  | `IncludeFlowDirections` / `IncludePropagatedValues` | Include flow-direction / propagated-value results. |
  | `ResultFieldsByNetworkSourceID` | A dictionary keyed by network source ID controlling which extra fields to include per source, e.g. keyed off `networkSources.First(f => f.Name.Contains("ElectricDevice")).ID`. |

## Tracing (C# API) — the deepest part of the SDK surface

### Getting a tracer
```csharp
using (TraceManager traceManager = utilityNetwork.GetTraceManager())
{
  DownstreamTracer downstreamTracer = traceManager.GetTracer<DownstreamTracer>();
}
```
`GetTracer<T>()` is generic — swap `DownstreamTracer` for `UpstreamTracer`,
`ConnectedTracer`, `SubnetworkTracer`, `IsolationTracer`, `LoopsTracer`,
`ShortestPathTracer`, etc., matching the trace types documented in the Pro
Help tracing reference.

### Building trace arguments
```csharp
IReadOnlyList<Element> startingPointList = new List<Element>();
// ... populate starting points ...

TraceArgument traceArgument = new TraceArgument(startingPointList);
TraceConfiguration traceConfiguration = new TraceConfiguration();
// ... configure traceConfiguration ...
traceArgument.Configuration = traceConfiguration;
```
Or, using a **named trace configuration** (a saved/shared configuration,
analogous to the REST API's Trace Configurations resource):
```csharp
using (TraceManager traceManager = utilityNetwork.GetTraceManager())
{
  IReadOnlyList<Element> startingPoints = new List<Element>();
  IReadOnlyList<NamedTraceConfiguration> namedTraceConfigurations =
      traceManager.GetNamedTraceConfigurations(new NamedTraceConfigurationQuery());
  NamedTraceConfiguration namedTraceConfiguration = namedTraceConfigurations.FirstOrDefault();

  TraceArgument traceArgument = new TraceArgument(namedTraceConfiguration, startingPoints);
}
```

### Traversability — condition comparisons
```csharp
const int InDesign = 4;
const int InService = 8;

using (NetworkAttribute lifecycleNetworkAttribute = utilityNetworkDefinition.GetNetworkAttribute("Lifecycle"))
{
  NetworkAttributeComparison inDesignComparison =
      new NetworkAttributeComparison(lifecycleNetworkAttribute, Operator.NotEqual, InDesign);
  NetworkAttributeComparison inServiceComparison =
      new NetworkAttributeComparison(lifecycleNetworkAttribute, Operator.NotEqual, InService);

  // Combine with And: stop traversal if Lifecycle is neither In Design nor In Service
  And lifecycleFilter = new And(inDesignComparison, inServiceComparison);
  traceConfiguration.Traversability.Barriers = lifecycleFilter;
}
```

### Function barriers (cumulative-value stopping condition)
```csharp
using (NetworkAttribute shapeLengthAttribute = utilityNetworkDefinition.GetNetworkAttribute("Shape length"))
{
  Add lengthFunction = new Add(shapeLengthAttribute);
  // Stop traversal once accumulated shape length exceeds 1000 (feet):
  FunctionBarrier distanceBarrier = new FunctionBarrier(lengthFunction, Operator.GreaterThan, 1000);
  traceConfiguration.Traversability.FunctionBarriers = new List<FunctionBarrier> { distanceBarrier };
}
```

### Output filtering by category
```csharp
traceConfiguration.OutputCondition =
    new CategoryComparison(CategoryOperator.IsEqual, "Service Point");
```
This mirrors the Pro Help "Output Conditions" filter — restrict trace results
to only features carrying a specific network category.

### Executing and interpreting results
- `traceArgument.Configuration = traceConfiguration;` then run via the tracer
  object obtained from `GetTracer<T>()`.
- Result types (from the JS/.NET Runtime API family, structurally mirrored in
  the Pro SDK): `UtilityElementTraceResult` (raw elements),
  `UtilityGeometryTraceResult` (geometry objects), function-output result
  sets (`UtilityFunctionTraceResult` family) for function-barrier
  accumulation values.

## Pro Integration summary

- Use `EditOperation` + `RowHandle`/`RowToken` for any feature/association
  edit that should show up correctly in the map and undo/redo stack — this is
  the single most important practical rule distinguishing "correct Pro
  Add-in code" from "code that happens to compile."
- An **object model diagram** (OMD) is published by Esri covering the full
  utility network API class relationships — useful to point advanced users
  toward when they need the complete class graph beyond what's summarized
  here.

## Sources

- https://github.com/esri/arcgis-pro-sdk/wiki/ProConcepts-Utility-Network
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17635.html (UtilityNetwork class members)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17662.html (ValidateNetworkTopology overloads)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17663.html (ValidateNetworkTopology())
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic24261.html (ValidateNetworkTopology(Geometry, ServiceSynchronizationType, ValidationType))
- https://doc.esri.com/en/arcgis-pro/3.7/sdk/api-reference/topic24263.html (ValidationType enum)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17693.html (ValidationResult)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17684.html (UtilityNetworkState)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic75127.html (ServiceSynchronizationType enum)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic20025.html (SystemTableType enum)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17595.html (SubnetworkManager members)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17566.html (Subnetwork class)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic18382.html (SubnetworkExportOptions)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17679.html (UtilityNetworkDefinition.GetSchemaVersion)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17680.html (UtilityNetworkDefinition.GetServiceTerritoryEnvelope)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17677.html (UtilityNetworkDefinition.GetNetworkSources)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17678.html (UtilityNetworkDefinition.GetRules)
- https://doc.esri.com/en/arcgis-pro/latest/sdk/api-reference/topic17681.html (UtilityNetworkDefinition.GetTerminalConfigurations)
- https://developers.arcgis.com/net/api-reference/api/netwin/Esri.ArcGISRuntime/Esri.ArcGISRuntime.UtilityNetworks.UtilityNetwork.html (Maps SDK for .NET — where the job-based ValidateNetworkTopology/GetStateAsync live)
