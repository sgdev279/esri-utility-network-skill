# Utility Network — ArcGIS Pro SDK (C#/.NET) Deep Reference
*Source: Esri "ProConcepts Utility Network" (GitHub wiki + doc.esri.com SDK conceptdocs),
Esri "Utility Network Object Model Diagram," arcpy Utility Network module docs*

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
| `GetSystemTable(SystemTableType)` → `Table` | System tables — enum includes `PointErrors`, `LineErrors`, `PolygonErrors`, `DirtyAreas`, `Subnetworks`, `Associations`. |
| `IsSystemTableSupported(SystemTableType)` → `bool` | Guard before calling `GetSystemTable`. |
| `CreateElement(AssetType, Guid, Terminal)` → `Element` | Build an `Element` handle for a feature without a full row fetch. |
| `GetAssociations(Element[, AssociationType])` → `IReadOnlyList<Association>` | Query associations for a feature, optionally filtered by type. |
| `GetAssociationFeatures(Envelope[, AssociationType])` | Spatial query for association features. |
| `AddAssociation(Association)` / `DeleteAssociation(Association)` | Low-level association editing (see caveats below). |
| `GetExtent()` / `GetServiceTerritoryEnvelope()` | Spatial extent accessors. |
| `GetServerCapabilities()` → `UtilityNetworkServerCapabilities` | What the backing service supports (relevant when the UN is service-backed). |
| `ValidateNetworkTopology(...)` | Programmatic topology validation; `ValidationType` enum includes `Repair = 1`, `ForceRebuild = 2`. |
| `GetSchemaVersion()` | Reports the utility network's schema/version number. |
| `GetTerminalConfigurations()` / `GetRules()` / `GetNetworkSources()` | Schema introspection, mirrors the arcpy `Describe` properties covered in the Pro Help reference. |

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

- `utilityNetwork.HasValidNetworkTopology()` (or the equivalent
  `UtilityNetworkDefinition`/`UtilityNetwork` check) — confirm topology is
  enabled **before** attempting to create associations or modify subnetwork
  controllers; both operations assume valid topology.
- `ValidateNetworkTopology(...)` with `ValidationType.Repair` or
  `ValidationType.ForceRebuild` for programmatic validation, mirroring the
  Pro UI's Validate Network Topology command but callable from an Add-in.

## Asynchronous / long-running operations — the `Job<T>` pattern

This is the C# SDK's answer to the REST `async=true`/`statusUrl` pattern
(`rest-api/06-asynchronous-operations-job-status.md`) — a job-object model
shared across the whole ArcGIS Maps SDK for Native Apps family (.NET, Kotlin,
Swift, Flutter all expose the same shape under their own naming
conventions).

### `ValidateNetworkTopology` returns a `UtilityNetworkValidationJob`
```csharp
public UtilityNetworkValidationJob ValidateNetworkTopology(Envelope extent)
public UtilityNetworkValidationJob ValidateNetworkTopology(Envelope extent, GeoprocessingExecutionType executionType)
```
- `UtilityNetworkValidationJob : Job<UtilityValidationResult>` — a strongly
  typed job whose eventual `Result` is a `UtilityValidationResult`.
- **The returned job is dormant** — it does **not** start automatically; you
  must call `.Start()` explicitly. This is a common "why isn't anything
  happening" gotcha in generated code that only calls `ValidateNetworkTopology(...)`
  without a follow-up `.Start()`.
- `GeoprocessingExecutionType`:
  - `SynchronousExecute` (**default** when unspecified) — significantly
    faster to start up; **preferred** for smaller validation jobs.
  - `AsynchronousSubmit` — use for **larger jobs** where synchronous
    execution risks timing out.
- **Enterprise geodatabase constraint**: only a **single session** can run
  the validate operation at a time against the DEFAULT version — matching
  the equivalent REST-level constraint in
  `rest-api/02-topology-and-subnetwork-management-operations.md`.

### Common `Job<T>` members (apply to any job-returning operation, not just validation)
| Member | Purpose |
|---|---|
| `Status` / `StatusChanged` | Current job status and a change notification event. |
| `Progress` / `ProgressChanged` | Percent-complete tracking, where supported. |
| `Messages` / `MessageAdded` | Job message log, appended to as the job runs. |
| `ServerJobId` | The underlying server-side job identifier — useful for correlating with server logs or a matching REST `statusUrl` if debugging across layers. |
| `Start()` | **Required** to actually begin a dormant job. |
| `Pause()` | Pause a running job. |
| `CancelAsync()` | Cancel the job and wait for any server-side cancellation to complete — **always cancel jobs you no longer need** (e.g., on app exit) to avoid unnecessary server load. |
| `CheckStatusAsync()` | Force an immediate status check rather than waiting for the next poll interval. |
| `GetResultAsync()` | Retrieve the typed result once the job has succeeded. |

### Related: `GetStateAsync()` for a quick, non-job network health check
```csharp
Task<UtilityNetworkState> GetStateAsync();
```
A lighter-weight call (not a `Job<T>`) that reports the network's current
state (e.g., whether dirty areas/errors exist, whether topology is valid) —
the natural first call before deciding whether a full validate job is even
needed. Throws if the network doesn't support network state at all (check
`SupportsNetworkState` first).

### Practical guidance
- Always pair a job-returning call with an explicit `.Start()` in generated
  code — don't let this be an implicit, easy-to-miss step.
- Default to `SynchronousExecute` unless the validation area/network is
  known to be large; switch to `AsynchronousSubmit` specifically to avoid
  timeouts, not as a default choice.
- Suggest `GetStateAsync()` before a full validate when someone just wants
  to know "is there a problem" rather than actually fix one.

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

- `GetSubnetworkManager()` → `SubnetworkManager` is the entry point; exposes
  the subnetwork life-cycle operations equivalent to the Pro UI/GP tools
  (Update Subnetwork, Export Subnetwork) but callable from code.
- **`SubnetworkExportOptions`** — the object controlling an export, with
  (confirmed) properties:
  | Property | Purpose |
  |---|---|
  | `SetAcknowledged` | Whether to mark the export as acknowledged (recall: only valid against DEFAULT version — see Pro Help admin reference). |
  | `IncludeDomainDescriptions` | Include human-readable domain/coded-value descriptions in export output. |
  | `IncludeGeometry` | Include feature geometry in the export. |
  | `ServiceSynchronizationType` | e.g. `ServiceSynchronizationType.Asynchronous` — controls sync vs. async export execution against a service. |
  | `SubnetworkExportResultTypes` | A list, e.g. `{ SubnetworkExportResultType.Connectivity, SubnetworkExportResultType.Features }` — controls what's actually included in the export payload. |
  | `ResultNetworkAttributes` | Which network attributes to include (typically populated from `utilityNetworkDefinition.GetNetworkAttributes()`). |
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
