# Utility Network: Data Model in Depth
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Read this when you need the exact schema: which classes exist, what each field means, how two things become connected (geometry, terminal or association), what the system tables hold, and which limits Esri states. It is the reference to open before writing a rule set, a migration mapping, an association import, a REST `applyEdits` call or an Arcade expression that reads `ASSOCIATIONSTATUS`. Builds on `pro-help/02-structure-of-a-utility-network.md`. Sources: see the list at the end. The narrative companion is `learn/01-mental-model-and-life-of-an-edit.md`; subnetwork mechanics are in `learn/06-tiers-and-subnetworks-in-depth.md`. Where Esri's page was silent I say so rather than guess.

## Contents
1. Feature dataset layout
2. Network sources and classes
3. Fields common to the classes
4. Subtypes: asset group and asset type
5. Global IDs and why they matter
6. Terminals and terminal configurations
7. The three kinds of connectivity
8. Containment, structural attachment and the structure network
9. Junction objects and edge objects
10. System tables and layers (with key fields)
11. Is it geometric or logical? A decision table
12. Limits and numbers Esri states
13. Version effects on the schema
14. Common misconceptions, quick checks, related files, sources

## 1. Feature dataset layout

```
Feature dataset  (one utility network per dataset)
 ├─ <ServiceTerritory>                  polygon fc, m- and z-enabled; extent = network extent; edit boundary
 ├─ Structure network (always, exactly one)
 │    ├─ StructureJunction   point      ├─ StructureJunctionObject  table
 │    ├─ StructureLine       line       ├─ StructureEdgeObject      table
 │    └─ StructureBoundary   polygon
 ├─ Domain network <Name>   (traditional)  prefix = domain network name
 │    ├─ <Name>Device  point   ├─ <Name>Line  line   ├─ <Name>Junction   ├─ <Name>Assembly  point
 │    ├─ <Name>SubnetLine      └─ tables: <Name>JunctionObject, <Name>EdgeObject
 ├─ Domain network <Name>   (telecom, UN v8+)
 │    ├─ <Name>Device, Line, Junction, Assembly   feature classes (4)
 │    └─ <Name>JunctionObject, EdgeObject, Circuit, CircuitSection, Subcircuit   tables (5)
 └─ System objects: Associations, Subnetworks, Rules tables; Dirty Areas layer; diagram layers;
    Dirty Objects table (only with a telecom domain network); trace configurations table (v5+)
```

- Create the dataset with `Create Utility Network` (manual) or let a Foundation / asset package build it. Prerequisites Esri states: an existing feature dataset, plus an existing **m- and z-enabled polygon feature class in that dataset** to be the service territory. The polygon extent defines the network extent and restricts edits so features are not created outside it. Updating the service territory extent after creation is currently not allowed (Esri "management tasks").
- Domain networks are not created by `Create Utility Network`; add them afterwards with `Add Domain Network` or `Add Telecom Domain Network` (topology must be disabled; Default version; database utility network owner connection and portal owner in enterprise).
- Class naming: the domain network name prefixes the class names (domain `ElectricDistribution` produces `ElectricDistributionJunction`; telecom example `TelcoDevice`, `TelcoCircuit`). Structure classes are not prefixed (`StructureJunction`). Aliases can differ.
- Supported containers: enterprise, file or mobile geodatabase; enterprise on SQL Server, Oracle, PostgreSQL or SAP HANA at a release supported by your ArcGIS Enterprise.
- Spatial indexes are required on all UN feature classes before enabling topology.

## 2. Network sources and classes

A **network source** is a class or table registered in the network; each gets a numeric **source ID**. Source IDs appear in the Associations table (`FROMNETWORKSOURCEID`, `TONETWORKSOURCEID`), in the Dirty Objects table (`SOURCEID`), in telecom foreign keys (`ContainerSourceID`, `FromSourceID`, ...), and in REST/JS results. In the Pro SDK the role of a source is its `UsageType`: Device, Junction, Line, Assembly, SubnetLine, StructureJunction, StructureLine, StructureBoundary, SystemJunction, Association, JunctionObject, EdgeObject, StructureJunctionObject, StructureEdgeObject. (`SystemJunction` is the hidden junction the topology creates; `Association` is the Associations table.)

### 2.1 Structure network classes (exactly one structure network)

| Class | Kind | Role | Example |
|---|---|---|---|
| `StructureJunction` | point fc | Points that support other features; can be container or structure | pole, pad, vault, cabinet, central office |
| `StructureLine` | line fc | Linear support/containers | trench, span guy, duct bank |
| `StructureBoundary` | polygon fc | Container outlines | substation outline, central office |
| `StructureJunctionObject` | table | Nonspatial objects that contain other objects; can take the structure role | fuse, rack |
| `StructureEdgeObject` | table | Nonspatial linear containers | trench, duct, microduct |

The structure network carries no resource flow. It supports structural attachment and containment, and can be returned by traces that include structures. It does not support tiers or subnetworks.

### 2.2 Traditional domain network: seven classes, fixed

`Add Domain Network` creates exactly these; no classes can be added later.

| Class | Kind / geometry | Role | Can have terminals | Notes |
|---|---|---|---|---|
| `Device` | point fc | Operational features that control or change the resource: valves, meters, transformers, switches, regulators | Yes | Connects to devices, junctions and lines; can be contained in assemblies, structure junctions, lines, boundaries; can be a subnetwork controller |
| `Line` | line fc | Carries the resource: wires, pipes, mains | n/a (it references device terminals) | Has `FROMDEVICETERMINAL`, `TODEVICETERMINAL`, `FLOWDIRECTION` (v7+) |
| `Junction` | fc (Esri's page does not state the geometry; points in practice) | Connectivity without effect on the resource: taps, tees, intermediate vertices | No | Placed to complete connections |
| `Assembly` | point fc | Shows a group of significant devices as one symbol: switchgear, transformer bank, pump assembly | No | No `SUBNETWORKNAME`/`SUPPORTINGSUBNETWORKNAME` field |
| `SubnetLine` | fc (geometry not stated on the classes page; linear) | One record per subnetwork | n/a | Read-only, system maintained; see section 10.5 |
| `JunctionObject` | table | Nonspatial objects (racks, ports, ...) | Yes | Can be a subnetwork controller |
| `EdgeObject` | table | Nonspatial edges (fibers in a cable, ...) | n/a | Stored as a table because a cable may contain many |

### 2.3 Telecom domain network: four classes plus five tables

| Class | Kind | Role | Telecom-specific fields |
|---|---|---|---|
| `Device` | point fc | Equipment: switches, optical network terminals; can be a Junction Unit Container | `CONTAINERSOURCEID`, `CONTAINERGLOBALID`, `NEXTUNITID` |
| `Line` | line fc | Cables or wireless paths; can be an Edge Unit Container | `FLOWDIRECTION` (v7+), `CONTAINERSOURCEID`, `CONTAINERGLOBALID`, `MAXCONTENTUNITID`, `COLORSCHEME` (default `Unknown`) |
| `Junction` | fc ("locations" per Esri) | Splice closures, slack loops, risers | `CONTAINERSOURCEID`, `CONTAINERGLOBALID` |
| `Assembly` | fc | Patch panels, splitters; shown as one symbol | `CONTAINERSOURCEID`, `CONTAINERGLOBALID` |
| `JunctionObject` | table | Chassis, ports, splices; can contain other junction objects | `CONTAINERSOURCEID`, `CONTAINERGLOBALID`, `FIRSTUNIT`, `LASTUNIT`, `NEXTUNITID`, `WAVELENGTHSCHEME`, `WAVELENGTHS` |
| `EdgeObject` | table | Copper/fiber strands, wireless signals inside a line; can be an Edge Unit Container | `FLOWDIRECTION`, `CONTAINERSOURCEID`, `CONTAINERGLOBALID`, `FROMSOURCEID`, `FROMGLOBALID`, `FROMFIRSTUNIT`, `FROMLASTUNIT`, `TOSOURCEID`, `TOGLOBALID`, `TOFIRSTUNIT`, `TOLASTUNIT`, `FIRSTUNIT`, `LASTUNIT`, `NEXTUNITID`, `MAXCONTENTUNITID`, `RECORDTYPE` (default `Ungrouped`), `COLORSCHEME` (default `Unknown`), `WAVELENGTHSCHEME`, `WAVELENGTHS` |
| `Circuit`, `CircuitSection`, `Subcircuit` | tables | System-maintained circuit management | see `rest-api/07-circuits-and-unit-identifiers-telecom.md` |

Telecom has no `SubnetLine` and no subnetwork management; it does not support terminals. One grouped edge object can represent all 96 strands of a cable (Esri's example).

### 2.4 Structure versus domain classes at a glance

| Aspect | Structure network | Domain network |
|---|---|---|
| Count | exactly 1 | 1 or more (traditional and telecom may mix; no maximum stated) |
| Flow | none | yes (traditional) or circuits (telecom) |
| Tiers / subnetworks | no | traditional only |
| Terminals | no | devices and junction objects (traditional) |
| Association role "Structure" allowed on | `StructureJunction`, `StructureJunctionObject` only | never |
| Association role "Container" allowed on | any network class | any network class |

## 3. Fields common to the classes

| Field | Where | Meaning |
|---|---|---|
| `ASSETGROUP` | all classes except `SubnetLine` | Subtype field; major classification |
| `ASSETTYPE` | same | Minor classification, an attribute domain per asset group |
| `ASSOCIATIONSTATUS` | all | System-maintained: association type, the feature's role, and content visibility; drives display filters and Select Associated Data choices (section 8.4) |
| `SUBNETWORKNAME` | all except `Assembly` (traditional) | Subnetwork the feature belongs to; alias "Supported subnetwork name" (v4+) or "Subnetwork name" (upgraded from v3 or earlier) on structure classes |
| `SUPPORTEDSUBNETWORKNAME` | traditional domain classes (v4+) | Subnetwork a container/structure supports |
| `SUPPORTINGSUBNETWORKNAME` | traditional domain classes except `Assembly` (v5+) | Subnetwork supporting a content feature |
| `ISSUBNETWORKCONTROLLER`, `SUBNETWORKCONTROLLERNAME`, `TIERNAME`, `TIERRANK`, `TERMINALCONFIGURATION` | `Device`, `JunctionObject` | Controller flag, controller name, tier, and the feature's current terminal path |
| `ISCONNECTED` | `Device`, `Line`, `Junction`, `JunctionObject`, `EdgeObject` | Set by `Update Is Connected`; new features start unknown |
| `FROMDEVICETERMINAL`, `TODEVICETERMINAL` | `Line` | Terminal IDs at the devices at the line's first and last vertices |
| `FLOWDIRECTION` | `Line`, `EdgeObject`, `StructureLine`, `StructureEdgeObject` | v7+: flow with/against digitized direction, or indeterminate; for edge objects relative to the association's From and To global IDs |
| `PARTITIONID` | all classes (v8+) | Reserved; not currently used |
| `CONFLICTCONTAINERSTATE` | telecom classes | Whether content changed since the last reconcile |
| Global ID, editor tracking fields | added when those are enabled | See section 5 |

Pitfall: `FROMDEVICETERMINAL`/`TODEVICETERMINAL` identify which device sits at which end; Esri states they do not indicate resource flow direction.

## 4. Subtypes: asset group and asset type

**Definition.** `ASSETGROUP` is the feature class's subtype field; each subtype code is an asset group. `ASSETTYPE` is a coded-value domain assigned per subtype, so the allowed asset types depend on the group. The pair is "the classification".

**Mechanism.** The UN deliberately keeps few classes and carries the kind of thing in the pair. Configuration then keys on the pair, not on the class:

| Configured per (class, asset group, asset type) | Tool |
|---|---|
| Terminal configuration | `Set Terminal Configuration` |
| Network categories (Subnetwork Controller, Connector Junction, ...) | `Set Network Category` |
| Association role (Container / Structure / None) with deletion semantics, view scale, split content | `Set Association Role` |
| Network rules (each side by class + group + type, and terminals) | `Add Rule` |
| Edge connectivity policy | `Set Edge Connectivity` |
| Valid controllers / valid features in a tier | `Set Subnetwork Definition` |

**Example (gas, illustrative).** Class `GasDevice`, asset group `Regulator`, asset type `Pressure Reducing`: gets a three-terminal configuration (inlet, outlet, bypass), the Subnetwork Controller category, and rules that allow high-pressure and low-pressure main asset types to connect at its terminals.

**Pitfalls.**
- Esri's management-tasks table lists as currently not allowed: deleting subtypes assigned to the asset group field, deleting domains assigned to the asset type field, and deleting network attributes, tiers or domain networks (and updating the service territory extent). Plan the classification before first use; adding, editing or renaming asset type domain values is allowed with topology enabled or disabled (Default version, owner connection in enterprise).
- Changing `ASSETGROUP`/`ASSETTYPE` on an existing feature is an edit that creates a dirty area, because rules depend on it.
- Once a device or junction object is a subnetwork controller, its asset group and asset type fields become read-only and it cannot be deleted.
- `SubnetLine` uses the **tier name** as its subtype field instead; `Add Tier` adds a subtype code/description pair there.

## 5. Global IDs and why they matter

**Definition.** A Global ID is the GUID that identifies a row independently of its ObjectID. Esri notes that Global ID and editor tracking fields are added to UN classes when those are enabled, and attribute rules require the dataset to have Global IDs.

**Mechanism: the UN refers to features by Global ID, not ObjectID.**
- The Associations table stores `FROMGLOBALID` and `TOGLOBALID` (plus source IDs).
- Telecom foreign keys store `ContainerGlobalID`, `FromGlobalID`, `ToGlobalID`.
- The Dirty Objects table stores the object's Global ID in `GUID`; dirty areas store the feature's GUID in the "Feature Guid" field; error messages contain GUIDs of the features in error.
- The Subnetworks table stores `FEATUREGLOBALID` (the controller feature) and `SUBNETLINEGLOBALID`.

**Why it matters in practice.**
- *Migration and loading.* Esri's load-data guidance shows a device's reference to its structure being stored as the structure's Global ID, which becomes the association's destination Global ID. Every load or copy path must therefore preserve Global IDs, or the association rows no longer point at anything. Practitioner guidance: check, for the specific tool you use, how it treats existing Global IDs before the first production load.
- *Branch versioning.* Associations and dirty areas are ordinary rows in the version, so they reconcile like other edits; see `pro-help/06-administration-subnetworks-topology-versioning.md`.
- *64-bit ObjectIDs (v7+).* ObjectIDs were migrated to 64-bit on all UN classes; Global IDs are unchanged. Practitioner guidance: do not store ObjectIDs as long-lived foreign keys in external systems.
- *REST/JS.* `applyEdits` associations take `fromGlobalId`/`toGlobalId`; trace starting points are identified by Global ID plus optional terminal (see `rest-api/01-utility-network-server-and-trace.md`).

**Pitfalls.** Duplicate Global IDs after a bad append/copy produce duplicate or dangling associations (see `pro-help/04-associations-editing-errors.md` for the diagnostic tools). Re-keying a class's Global IDs after associations exist breaks them silently until validate.

## 6. Terminals and terminal configurations

**Definition.** A terminal is a logical connection point on a `Device` or `JunctionObject`. It does not appear on the map. It controls how other features connect and which paths a resource can take through the device. Telecom domain networks do not support terminals.

**Why have them.** Model distinct physical ports (transformer bushings, regulator inlet/outlet), one-way devices, and anything that will be a subnetwork controller (a terminal is required). Skip them when connections are interchangeable, such as the two sides of a switch or valve. With no configuration assigned, an asset type uses **Single Terminal**, which behaves as if there were no terminals.

**Mechanism: the configuration.**

| Property | Rule (Esri) |
|---|---|
| Directionality | `Directional` (at least one terminal is upstream, restricting flow) or `Bidirectional` (no upstream/downstream, flow either way) |
| Number of terminals | 2 to 8, uniquely named |
| Terminal name length | up to 32 characters |
| Directional terminals | each marked upstream or downstream (the `Add Terminal Configuration` tool's "Terminals (Directional)" table has an Upstream setting per terminal) |
| Valid paths | 2 terminals: none needed (one path). 3 or 4 terminals: valid paths and a default path required. 5 to 8 terminals: valid paths not supported; all paths are valid |
| Default path | `All` (default) or `None` for new features; if no valid paths are defined, All is used. Paths are written like `A-B` or `A-B, A-C` |
| Assignment | many asset types may share one configuration, but each asset type has exactly one; only `Device` and `JunctionObject` asset types |
| Current path on a feature | stored in the `TERMINALCONFIGURATION` attribute; changed in the *Modify Terminal Paths* pane (only valid paths shown) |
| Partitioned tiers | subnetwork controllers need a directional configuration |
| Hierarchical tiers | controllers may use directional or bidirectional |

Pro SDK note: the `Terminal` object has an ID, a name and `IsUpstreamTerminal`; upstream means toward the subnetwork controller in source-based networks and away from it in sink-based networks.

**Permanence.** Configurations cannot be changed after creation, except an unassigned configuration in a network whose topology has never been enabled. Deleting a configuration, removing an assignment, or unassigning an association role must happen before the first enable. Both `Add` and `Set Terminal Configuration` require topology disabled and Default version in enterprise.

**Connecting a line to a terminal.** Via *Modify Terminal Connections* or the snap chip, which writes `FROMDEVICETERMINAL`/`TODEVICETERMINAL`. For junction and edge objects, *Modify Associations* sets the terminal on the connectivity association (`FROMTERMINALID`/`TOTERMINALID`). Network rules must name the terminal when the asset type has terminals (the `Add Rule` From/To Terminal parameters are optional but required then). Do not hand-edit the terminal fields.

**Constraints.** A terminal-enabled feature cannot sit midspan on a line (split the line or add a terminal-free junction). Terminal selection affects traversability-based traces, so the starting point terminal matters. Esri advises creating a dedicated configuration for controller asset types and not modifying a controller's configuration afterwards.

**Examples.** Electric: a distribution transformer with high-side and low-side terminals, directional (a controller for a low-voltage tier). Gas: a regulator with inlet, outlet and bypass (3 terminals so valid paths are required). Water: a simple gate valve needs none (Single Terminal).

**Where to see them.** *Network Properties* dialog, Terminal Configurations section (directionality, terminals, valid paths) and the Terminal Configuration Name column for assignments. REST `queryDataElements` returns `terminalConfigurations`.

## 7. The three kinds of connectivity

Every relationship that lets a trace move from one feature to another is one of: geometric coincidence, a connectivity association, or (for containment and attachment) a non-flow association. All require a network rule that does not violate a **feature restriction**.

### 7.1 Geometric coincidence

- Features connect when they are geometrically coincident, achieved in Pro with endpoint or midspan snapping. The dataset's **x, y, z tolerances** define coincidence at validate; features offset within tolerance are treated as coincident. Esri does not publish tolerance values on these pages.
- Supported shapes: **junction-edge** (a point and a line, or a line end and a terminal on a device) and **edge-junction-edge** (two lines joined through an intermediate point; midspan is not supported for this one).
- The **edge connectivity policy** per line asset type decides where on it a point may connect: *Any vertex* or *End vertex* (`Set Edge Connectivity`, topology disabled, Default version).
- Rule priority: a junction at the end of an edge belongs in a junction-edge rule; a junction between two edges in an edge-junction-edge rule. If both exist, junction-edge rules are honoured first. Esri's example: a reducer between edges needs an edge-junction-edge rule; a valve at an edge end needs a junction-edge rule, and a valve placed between edges still connects through its junction-edge rules.
- No rule means no snapping help and, at validate, errors (error 8) and a disconnected pair.
- Two edges with the same asset group and asset type meeting at their endpoints need no rule and no user-placed junction: the topology creates an invisible **system junction** at validate/enable (visible in a network diagram).
- A device cannot be geometrically coincident with another device (Esri's example of a prohibited case).
- Midspan connectivity (vocabulary): connecting features to a line's interior vertices without splitting the line; a "complex edge" lets resource flow in or out at midspan.

### 7.2 Connectivity associations

For features that are not coincident, or that are nonspatial. They live in the Associations table (telecom junction-edge connectivity uses foreign keys on the edge object instead). Six codes in `ASSOCIATIONTYPE`:

| Code | Name | Direction semantics | Typical use |
|---|---|---|---|
| 1 | Junction-junction connectivity | between two points or junction objects, possibly offset in x, y or z; terminals allowed | A meter to a tap, a fuse to a busbar port |
| 2 | Containment | From = container, To = content | Fuse in a vault |
| 3 | Structural attachment | From = structure, To = attachment | Transformer on a pole |
| 4 | Junction-edge From connectivity | a junction or point to an edge object | Start of a fiber strand at a splice |
| 5 | Junction-edge midspan connectivity | a junction placed along an edge object; position in `PERCENTALONG` (Esri's pages do not state the value range) | A tap partway along a service-lateral edge object |
| 6 | Junction-edge To connectivity | an edge object to a point or junction object (the receiving end) | End of a strand at a port |

An edge object is joined to a point by **two** rows, one From (4) and one To (6), which establishes its direction. The nonspatial object is on the "to" side of junction-edge associations. Edge-junction-edge for edge objects is the From and To pair through an intermediate object. Edge attributes can model values like service lateral length (Esri's example: a water service lateral modelled as an edge between a tap and a meter rather than junction-junction).

Rule types that govern them (the `Add Rule` tool's Rule Type): junction-junction connectivity; containment (From = container, To = content); structural attachment (From = structure, To = attachment); junction-edge connectivity (also covers point-to-line by coincidence, and edge object to point/junction object by association); edge-junction-edge connectivity (also edge object to line/edge object through a junction object; uses the Via parameters). Rules may be added only with topology disabled. Esri's topology page says applicable network rules must exist for features to connect; whether Enable refuses to run with no rules at all is not stated: Verify against the Esri docs for your version.

### 7.3 Feature restrictions: the hard limit under all rules

System maintained; cannot be modified. Network rules can only add relationships that do not violate them.

| Edge-junction-edge | From | To | Via |
|---|---|---|---|
| | Line | Line | Device, Junction |
| | StructureLine | StructureLine | StructureJunction |

| Connectivity association | From | To | Via |
|---|---|---|---|
| | Line | EdgeObject | Device, Junction |
| | StructureLine | StructureEdgeObject | StructureJunction |
| | EdgeObject | EdgeObject | Device, Junction, JunctionObject |
| | EdgeObject | Line | Device, Junction |
| | StructureEdgeObject | StructureEdgeObject | StructureJunction, StructureJunctionObject |
| | StructureEdgeObject | StructureLine | StructureJunction |

Containment and attachment validity is published as a matrix image in Esri's feature restrictions page; read that page for the exact pairs. Telecom: grouped edge objects cannot connect directly to ungrouped junction objects; a generic grouped junction object with the Connector Junction category bridges them. Ungrouped unit-container devices can connect to grouped edge objects without connector junctions if the From/To first and last units are specified.

### 7.4 What each connectivity type is used for (summary)

| Need | Use |
|---|---|
| Ordinary overhead or pipe network | Geometric coincidence with rules and terminals |
| Offset symbols, dense cabinets, or 3D separation | Junction-junction association |
| Fiber/copper strands, nonspatial cables | Junction-edge From/To (and midspan) associations or foreign keys |
| Hide a cluster behind one symbol | Containment |
| "What is on this pole" | Structural attachment |

## 8. Containment, structural attachment and the structure network

### 8.1 Containment

- A **container** holds **content**. Containers may be polygons (substation), lines (duct bank), points (vault), edge objects (cable) or junction objects (switch). Containers can nest; a line can be content of several containers; "a point feature cannot be content in more than one container."
- Resource does not flow through a container. A trace can return contained lines and devices without the container; subnetwork traces honour the status of contained content (an open internal switch stops the trace). Containers can connect to other containers (vault to duct bank).
- Role setup (`Set Association Role`, topology disabled): **Role Type** Container / Structure / None; **Deletion Semantics** (Restricted blocks deletion while content exists, Cascade deletes content, Set to none removes the association and keeps the content); **View Scale** (map scale used on entering containment mode for point containers; not for junction/edge objects); **Split Content** (container role on line classes only; default off). Only after the role exists can containment rules be added.
- Split Content off (default): splitting a line container does not split content; parallel content stays contained by both sections, nonparallel content goes to the closest container, junction content goes to the larger container, edge content stays with both parents. On: content is divided among sections; junction content is duplicated, edge content is split. (The container itself is never split by this.)
- Removing container or structure roles is only possible before topology is first enabled.
- Visibility: content is hidden by default (`ISCONTENTVISIBLE` false). Hiding needs display filters or definition queries on `ASSOCIATIONSTATUS`; the Display Content command toggles the display filters; diagrams can also show content. Note: definition queries are not supported on UN layers when publishing with a UN layer.
- Editing: *Enter Containment* then create features; they are auto-associated as content if a rule allows.
- Telecom: containment on nonspatial classes uses `ContainerSourceID`/`ContainerGlobalID`. Foreign keys cannot hold two containers: if a line or edge object already has one, the new containment goes to the Associations table, `ContainerSourceID` becomes the sentinel `Association` and `ContainerGlobalID` is `NULL`.

Example (electric): switchgear modelled as an `Assembly`; its devices are contained and hidden; a trace honours each internal switch state. Example (telecom): a central office `StructureBoundary` containing racks and chassis.

### 8.2 Structural attachment

- The structure side must have the **Structure** role; only `StructureJunction` and `StructureJunctionObject` can take it. Deletion semantics apply. Then add structural attachment rules for the asset-type pairs allowed (transformer to pole).
- It is not terminal-aware and carries no flow. Attached features can be returned by traces that include structures, and a pole can carry devices of several domain networks, which is what makes cross-domain "what is on this pole" and joint-use queries possible.

### 8.3 Assemblies, boundaries and groups

`Assembly` (point), `StructureBoundary` (polygon) and any container-role class are all containers. The difference is cartographic and semantic: an assembly shows one symbol for its internal devices; a boundary is a polygon outline; neither carries flow itself.

### 8.4 `ASSOCIATIONSTATUS`

A system-maintained attribute on every network feature; it tells you the association type, the feature's role and whether content is visible. Pro's "Select Associated Data" options (All, Connectivity, Contained In, Contains, Attached To, Attachments) depend on it. Esri's domain has 36 codes that are sums of six flags; reading the published list, the flags are Container = 1, Structure = 2, Content = 4, Attachment = 8, Visible Content = 16, Connectivity = 32 (this decoding is an inference from the published code list, not a stated bit definition). Examples from Esri's list: 9 = Attachment and Container; 40 = Connectivity and Attachment; 46 = Connectivity, Attachment, Content and Structure. Not every bit combination appears in the domain. Do not write to this field; treat it as read-only.

## 9. Junction objects and edge objects

- Nonspatial objects that represent many real-world things sharing one location (strands in a cable, ports in a chassis). Require UN v4 or later. Tables: `JunctionObject`, `EdgeObject` (traditional and telecom) and `StructureJunctionObject`, `StructureEdgeObject`.
- Unlike ordinary tables they take part in connectivity and can be containers; associations give them connectivity, containment and attachment.
- **Locatable** if some association path reaches a spatial feature (connected, contained, or attached). **Unlocatable** otherwise (association deleted or never existed when the topology was enabled). Junction-junction connectivity does not establish locatability. An edge object becomes locatable through junction-edge associations at its ends (or midspan) with a locatable junction.
- Dirty-area consequence: editing a locatable object creates a dirty area on the first spatial feature in its containment hierarchy; unlocatable edits create none, and disabling/re-enabling the topology is needed to reflect them. Trace and Set Subnetwork Definition have a *Validate Locatability* option.
- Geometry synthesis for results (Trace, Aggregated Geometry, Synthesize Geometries; enterprise needs Enterprise 11.3+): content of a line takes that line's geometry; with no linear container a straight line is synthesized between endpoints; multiple linear containers return the union; `PERCENTALONG` (default 0.5 in `UN_Temp_Starting_Points` and `UN_Temp_Barriers`) returns partial geometry only when the edge object is content of a line.
- Practical guidance: only the highest-level asset needs a shape; model lower levels (strands, ports) as tabular objects associated to it.
- Grouping (telecom): `FirstUnit`/`LastUnit` ranges let one row represent contiguous units and support 1:1, 1:M and M:N connectivity, including unequal sides such as a 1:8 splitter. A grouped edge object can have only one To and one From association; REST `divideGroupedObjects`/`combineGroupedObjects` split and merge groups.

## 10. System tables and layers

System tables and layers are created with the network, are system maintained, and are exposed in the feature service. Their IDs are found in the utility network layer's `systemLayers` object (`utilityNetworkLayerId` on the FeatureServer root). The IDs below are Esri's documentation examples; your service differs.

| System object | `systemLayers` key (v8) | Example ID | Operations documented |
|---|---|---|---|
| Dirty Areas (layer) | `dirtyAreasLayerId` | 13 (12 for v6) | none listed |
| Associations (table) | `associationsTableId` | 500001 | `query`, `applyEdits` |
| Subnetworks (table) | `subnetworksTableId` | 500002 | `query` |
| Rules (table) | `rulesTableId` | 500003 | `query` |
| Diagram edge/junction/container layers | `diagramEdgeLayerId`, `diagramJunctionLayerId`, `diagramContainerLayerId` | 500004 to 500006 | none listed |
| Temporary diagram layers | `temporaryDiagramEdgeLayerId`, `temporaryDiagramJunctionLayerId`, `temporaryDiagramContainerLayerId` | 500007 to 500009 | none listed |
| Dirty Objects (table) | `dirtyObjectsTableId` | 26 | only exists with a telecom domain network |
| Error layers (v3 and earlier only) | `pointErrorsLayerId`, `lineErrorsLayerId`, `polygonErrorsLayerId` | 9, 10, 11 | removed in v4 |

Add the Associations table to a Pro map with *Add Data > From Path* using `.../FeatureServer/500001`; it appears under Standalone Tables. It is hidden by default.

### 10.1 Dirty Areas

Purpose: where the map and topology disagree, and where errors are. Stores each area's extent, edit type, feature GUID and editor.

| Field (alias) | Meaning |
|---|---|
| `STATUS` (Status) | Bitmask: 0 topology disabled; 1 inserted/updated; 2 deleted; 4 associated objects modified; 8 feature error; 16 object error; 32 subnetwork error. Values add (9 = modified and in error). Pop-ups add "Status Description" |
| Network Source ID | class of the feature in error, shown as a string |
| Feature Guid | GUID of the network feature |
| `ERRORCODE` (Error code) | Bitmask of error codes; 0 = none; big integer from v7 (was double) |
| `ERRORMESSAGE` (Error message) | error ID, destination source ID and GUIDs; trimmed at 512 characters (rerun validation if trimmed); error 9 includes rule IDs |
| Editor tracking fields | usable for symbology |

Behaviour: edits create edit dirty areas; a geometry change creates two; disabling topology creates one covering the territory; validate clears edit dirty areas, but error-only areas (no edit bit, i.e. none of Status values 1, 2, 4) are ignored by validate and persist until the cause is fixed. From v4, errors live here too (the v3 point/line/polygon error layers were removed, and `UPDATETYPE` was dropped from this table). Utility network errors have IDs (examples from Esri: 0 wrong data type, 1 empty geometry, 8 no connectivity rule, 25 stacked points, 36 invalid terminal, 46 system inconsistencies; 24 to 47 are subnetwork-update errors that set the subnetwork Invalid).

### 10.2 Associations table (22 fields)

18 core fields plus 4 telecom fields.

| Field | Meaning |
|---|---|
| `FROMNETWORKSOURCEID`, `FROMGLOBALID`, `FROMTERMINALID` | From side: source, row, terminal if applicable |
| `TONETWORKSOURCEID`, `TOGLOBALID`, `TOTERMINALID` | To side |
| `ASSOCIATIONTYPE` | 1 junction-junction, 2 containment, 3 structural attachment, 4 junction-edge From, 5 junction-edge midspan, 6 junction-edge To (subtype field from v6) |
| `ISCONTENTVISIBLE` | containment only |
| `PERCENTALONG` | midspan associations only (v4+) |
| `STATUS` | bits: 0 clean; 1 association deleted; 2 From-side feature deleted; 4 To-side feature deleted; 8 association dirty; 16 From-side object dirty; 32 To-side object dirty (values add) |
| `ERRORCODE`, `ERRORMESSAGE` | bit-encoded errors and context |
| `CREATIONDATE`, `CREATOR`, `LASTUPDATE`, `UPDATEDBY`, `GLOBALID` | tracking and row ID |
| `FROMFIRSTUNIT`, `FROMLASTUNIT`, `TOFIRSTUNIT`, `TOLASTUNIT` | telecom only: grouped unit ranges, added with the first telecom domain network |

Associations have no attributes beyond these, no `Shape`, and do not support relationship classes or join tables. Contents update when topology is enabled or validated and when associations are changed in Modify Associations or through REST. In REST `applyEdits`, `percentAlong` applies only to midspan; `terminalId` applies only to junction sources on traditional domain networks; the three junction-edge types need UN v4+; delete by `deleteAssociations` needs Enterprise 12.0+ and the `supportsDeleteAssociations` capability (legacy `deletes` list is deprecated in 12.0 but supported for traditional networks). Mapping of codes to REST names: `scripts/association_types.py`.

### 10.3 Subnetworks table

One row per **subnetwork controller** (existing and deleted). Read-only. Updated by Update Subnetwork, enable/validate, and controller changes.

| Field | Meaning |
|---|---|
| `SUBNETWORKCONTROLLERNAME`, `SUBNETWORKNAME` | controller name (Esri: unique within the tier) and the subnetwork name (several controllers can share one; Esri's pages read do not state a uniqueness rule for it) |
| `TIERNAME`, `TIERRANK`, `TIERTOPOLOGYTYPE`, `DOMAINNETWORKNAME` | tier and domain context |
| `FEATUREGLOBALID`, `FEATUREASSETGROUP`, `FEATUREASSETTYPE`, `FEATURESOURCEID`, `FEATURETERMINALID` | which terminal on which feature is the controller |
| `ISDIRTY` (alias Status) | 0 Clean, 1 Dirty, 2 Invalid (domain descriptions set in v7; Invalid added v4, requires Pro 3.1+ and Enterprise 11.1+ in enterprise) |
| `ISDELETED` | controller terminal no longer set |
| `SUBNETLINEGLOBALID` | linked `SubnetLine` record |
| `LASTUPDATESUBNETWORK`, `LASTACKEXPORTSUBNETWORK` | last Update Subnetwork; last acknowledged Export Subnetwork |
| `DESCRIPTION`, `NOTES`, tracking fields, `GLOBALID` | free text and tracking |

A nonunique index on `SUBNETWORKNAME` and `SUBNETWORKCONTROLLERNAME` was added in v4. A subnetwork leaves the table only when all its controllers are deleted and Export Subnetwork (acknowledged) removes them.

### 10.4 Rules table

Read-only (query) view of the network rules (`rulesTableId`). The five rule types and their From/To/Via semantics are in section 7.2. The page listing its fields was not retrievable when this file was written: verify field names with a `query` against your own service before depending on them.

### 10.5 `SubnetLine`

One linear feature per subnetwork, built by aggregating the lines the tier's subnetwork definition lists under "Aggregated Lines" (a subset of its Valid Lines). Can be multipart (associations are not represented) and can have empty geometry (disconnected controller, no aggregated lines, overlapping subnetworks) while still carrying summaries. Fields: `ISDIRTY`, `TIERNAME`, `SUBNETWORKNAME`, `SUBNETWORKCONTROLLERNAMES`, `LASTUPDATESUBNETWORK`, `LASTACKEXPORTSUBNETWORK`; you may add fields for trace summaries. Reconcile considers it; post does not, so refresh it in Default after a post.

### 10.6 Dirty Objects (telecom)

Created with the first telecom domain network, because foreign keys (not the Associations table) manage some associations.

| Field | Meaning |
|---|---|
| `SOURCEID`, `GUID` | source and Global ID of the object or association |
| `STATUS` | 0 not dirty; 1 inserted/updated; 2 deleted; 4 in error; 8 circuit in error |
| `ERRORCODE`, `ERRORMESSAGE`, `PARTITIONID` (unused), tracking fields, `GLOBALID` | as elsewhere |

A row is written whenever a nonspatial object or association changes; locatable ones also get a dirty area on the first spatial feature in the hierarchy.

### 10.7 Other system objects

- `UN_<ID>_TRACECONFIGURATIONS` table: named trace configurations (v5+).
- Tables named `TMP_JUNCTIONS`, `TMP_EDGES`, `TMP_CONTAINERS`, `JUNCTIONS`, `EDGES`, `CONTAINERS` appear in Esri's upgrade history with fields such as `Info` (v7) and `ELEMENTUNIT`/`...ELEMENTFIRSTUNIT` (v8). Their role is not explained on the pages read; they appear to back the diagram layers. Verify against the Esri docs for your version before relying on them.
- Network definition metadata (domain networks, network attributes, terminal configurations, categories) is read through REST `queryDataElements` (`layerDataElements[].dataElement`).

## 11. Is it geometric or logical? A decision table

| Relationship | Geometric? | Logical? | Notes |
|---|---|---|---|
| Line end meets device at a terminal | Coincidence | Terminal IDs on the line; rule | Most common electric/gas/water pattern |
| Line meets line at a vertex, same asset group/type | Coincidence | System junction, no rule | Invisible; seen in diagrams |
| Line meets line through a valve placed between | Coincidence | Junction-edge or edge-junction-edge rule | Junction-edge honoured first |
| Two points offset (stacked equipment, 3D) | No | Junction-junction association (type 1) | Features need not be coincident |
| Fiber strand to a port | No | Junction-edge From/To (4, 6) or telecom foreign keys | Nonspatial edge objects |
| Fuse inside vault | Not required | Containment (2) | Content hidden by default |
| Transformer on pole | Not required | Structural attachment (3) | No terminals involved |
| Subnetwork membership | No | Traced result stored in `SUBNETWORKNAME` | Snapshot |
| Is a feature connected to a controller | No | `ISCONNECTED` | Snapshot |

## 12. Limits and numbers Esri states

| Item | Value | Source page |
|---|---|---|
| Structure networks per UN | 1 | structure of a UN |
| Network topologies per UN | 1 | about network topology |
| Classes in a traditional domain network | 5 feature classes + 2 tables, fixed | traditional domain networks |
| Classes in a telecom domain network | 4 feature classes + 5 tables | telecom domain networks |
| Tiers per UN | up to 63 (across domain networks) | tiers |
| Terminals per configuration | 2 to 8; name up to 32 characters | Add Terminal Configuration |
| Valid paths | none needed for 2; required for 3 or 4; not supported for 5 to 8 | about terminal management |
| Terminal configurations per asset type | 1 | same |
| In-line network attribute bits | 64 total; user-defined bits 25 (UN created by Pro 3.0+), 21 (Pro 2.9), 20 (Pro 2.8 and earlier); nullable costs +1 bit; bit size = ceil(log2(max coded value + 1)) | network attributes |
| Network attribute data types | Short, Long, Double, Date, Big integer (v7+) | network attributes |
| Network categories per asset type | no cap stated | about network categories |
| Domain networks per UN | no maximum stated | domain networks |
| `Enable Network Topology` Maximum number of errors | default 10000; -1 or blank = unlimited | Enable Network Topology |
| Dirty-area error message | trimmed at 512 characters | view error features |
| Update Subnetwork name picker | reported not to populate at 10,000+ subnetwork records; not stated on the Esri pages read: Verify against the Esri docs for your version | Update Subnetwork |
| Content in containers | a point cannot be content of more than one container | containment |
| Dataset version choices at creation | Compatible, Current, 8, 7, 6, 5; Compatible is the tool default; per `pro-help/09-dataset-versions-compatibility-upgrade.md`, Compatible and Current still create 7 in Pro 3.7 / Enterprise 12.1 and 8 must be explicit (the create pages do not map them to a number) | create a utility network, dataset administration |
| Enterprise geodatabase minimum | 10.8.1.2.6 for v6 or earlier; 11.2.0 (11.2.0.3.2 per the create page) for v7+ | create a utility network, upgrade history |
| Rank | 1 is the highest; partitioned: you assign, default lowest+1; hierarchical: automatic, per tier group | tiers |

Esri does not publish on these pages a maximum feature count, association count or dirty-area count. For capacity questions use the sizing guidance in `pro-help/06-administration-subnetworks-topology-versioning.md` and verify against the Esri docs for your version.

## 13. Version effects on the schema

| UN dataset version | Schema change (Esri upgrade history) |
|---|---|
| 4 | Nonspatial objects (`JunctionObject`, `EdgeObject`, `StructureJunctionObject`, `StructureEdgeObject`); error sublayers removed; dirty areas table repurposed (`STATUS`, `ERRORCODE`, `ERRORMESSAGE`); associations gain `STATUS`, `ERRORCODE`, `ERRORMESSAGE`, `PERCENTALONG`; `SUPPORTEDSUBNETWORKNAME`; Invalid status (Pro 3.1+) |
| 5 | `SUPPORTINGSUBNETWORKNAME`; `UN_<ID>_TRACECONFIGURATIONS` (named trace configurations) |
| 6 | `ASSOCIATIONTYPE` becomes a subtype field |
| 7 | 64-bit ObjectIDs; `FLOWDIRECTION` on `Line`, `EdgeObject`, `StructureLine`, `StructureEdgeObject`; `ERRORCODE` double to big integer; `UN_<ID>_IsDirty` domain descriptions 0 Clean / 1 Dirty / 2 Invalid; big integer network attributes |
| 8 | `PARTITIONID` on all domain and structure classes; Propagator Resetter category; telecom-related element-unit fields; primarily for telecom domain networks and must be chosen explicitly. Pro 3.7 / Enterprise 12.1; Field Maps and Native Apps SDKs do not support v8 with Enterprise 12.1 |

Full matrix: `pro-help/09-dataset-versions-compatibility-upgrade.md`.

## Common misconceptions

- "Asset type is just a label." It is configuration: rules, terminals, categories, roles and edge policies are keyed on (class, group, type). Domain values cannot be deleted later.
- "Associations are relationship classes." They are rows in a hidden system table with no attributes beyond those listed, no Shape, no join support.
- "Terminal IDs on a line show flow direction." They record which device is at each end only.
- "Containment moves flow." It does not; and a point can be content of at most one container.
- "Telecom is a traditional domain network with extra tables." It has no subnetworks, no terminals, uses foreign keys for some connectivity and containment, and needs v8.
- "ObjectID is a safe key." The UN relationships use Global IDs; ObjectIDs are 64-bit from v7 and not stable across copies.
- "Junction-junction connectivity can make an object locatable." It cannot.
- "`ASSOCIATIONSTATUS` is something I can edit to hide content." It is system maintained; use the content-visible flag through Modify Associations or REST, plus display filters.

## Quick checks

1. Which class and (asset group, asset type) are the two features? Is there a rule for that exact pair, terminal included if the type has terminals?
2. Is the relationship supposed to be geometric or associative? Do the feature restrictions allow it (section 7.3)?
3. For a terminal problem: which configuration is assigned, which path is current (`TERMINALCONFIGURATION`), and were the `FROMDEVICETERMINAL`/`TODEVICETERMINAL` values set by the proper tool?
4. For an association problem: do the From and To Global IDs exist in the named sources; is the association row `STATUS` 0; do duplicate Global IDs exist?
5. For missing nonspatial edits in the topology: is the object locatable?
6. For schema surprises: which dataset version, and does the field you expect exist at that version (`FLOWDIRECTION` v7+, `PARTITIONID` v8+)?
7. For a REST question: have you read `systemLayers` from your own service instead of using example IDs?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/04-rules-and-connectivity-design.md`
- `learn/03-topology-engine-and-validation.md`, `learn/06-tiers-and-subnetworks-in-depth.md`
- `pro-help/02-structure-of-a-utility-network.md`, `pro-help/03-creation-configuration-attributes-categories-rules.md`, `pro-help/04-associations-editing-errors.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`
- `rest-api/05-feature-service-associations-appendix.md`, `rest-api/07-circuits-and-unit-identifiers-telecom.md`
- `arcpy/01-utility-network-module.md`, `pro-sdk/01-csharp-sdk-utility-network-api.md`
- `scripts/association_types.py`, `scripts/decode_dirty_status.py`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/the-structure-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/traditional-domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/telecom-domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/structure-of-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-vocabulary.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/associations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/associations-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/association-status-attribute.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/create-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/geometric-concident-based-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/feature-restrictions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/containment.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/nonspatial-objects.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/device-terminals.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-terminal-management.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetworks-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetline-feature-class.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-life-cycle.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-objects-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-attributes.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-categories.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/create-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-upgrade-history.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-compatibility.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-terminal-configuration.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-domain-network.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-edge-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-association-role.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/an-overview-of-attribute-rules.html
- https://developers.arcgis.com/rest/services-reference/enterprise/appendix-working-with-the-feature-server-utility-network-server/
- https://github.com/Esri/arcgis-pro-sdk/wiki/ProConcepts-Utility-Network
- https://www.esri.com/arcgis-blog/products/utility-network/data-management/load-data-into-a-utility-network-foundation (Esri staff blog)
