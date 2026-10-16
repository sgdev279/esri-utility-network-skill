# Utility Network: ArcGIS Pro as the Working Surface (Anatomy, Build Flow, Daily Operations, Tool Map)
*Sources: Esri Pro 3.7 Utility Network help and tool reference (URLs in Sources below). Last reviewed: 2026-10-16.*

> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

**Why this matters / when to read this.** Every Utility Network (UN) concept in this skill eventually has to be done by a person clicking in ArcGIS Pro or a script calling `arcpy.un`. This file maps the concepts onto the Pro surface: where each button lives, which geoprocessing (GP) tool does which job, in what order a network is built, and what each role does day to day.
Read it when someone asks "where do I click", "what do I run first", "why is this tool greyed out", "which tool does X" or "how is a file geodatabase network different". It is domain-neutral: the same flow serves electric, gas, water, wastewater, stormwater and telecom.
Concept explanations live in `learn/01` to `learn/10`; this file links to them rather than repeating them.

## Contents

1. Pro-side anatomy (ribbon, panes, Contents, Network Properties, Catalog, Subnetworks table, Error Inspector, diagrams)
2. The end-to-end build and administer flow, with owner, license and version at each step
3. Daily operations by role (editor, QA reviewer, analyst, administrator)
4. The tool map (every Utility Network toolbox tool, grouped by purpose)
5. Pro settings that change UN behaviour
6. Single-user (file or mobile geodatabase) differences

Labels below are taken from Esri's Pro 3.7 help ("Utility Network tab", "Network topology actions", the toolset overview pages). Where Esri's page did not give a label or a Python parameter name, this file says so; verify against the Esri docs for your version before scripting.

---

## 1. Pro-side anatomy

### 1.1 The one idea behind the Pro surface

The UN lives in a **geodatabase feature dataset** (`learn/02`). Pro shows it in two different ways, and confusing them is the root of many "I can't find it" questions:

| View | What it is | Where you meet it | What you do there |
|---|---|---|---|
| **Dataset view** | The utility network dataset and its classes as stored | **Catalog** pane (and Catalog view), Geoprocessing tool inputs | Administration: tools take the *dataset* (or a layer) as `Input Utility Network` |
| **Map view** | The **utility network layer** plus the classes you add as subtype group layers | **Contents** pane in a map | Editing, tracing, validating, subnetwork work via the **Utility Network** tab |

```
Catalog pane / dataset (stored)              Map / Contents pane (working surface)
-------------------------------              -------------------------------------
Geodatabase connection                       Subtype group layers (the data classes)
 +- Feature dataset                           <name> Utility Network   <- the UN layer
     +- Utility network dataset                   +- Dirty Areas  (sublayer)
     +- Domain network classes                    +- Dirty Objects (table; telecom only)
     +- Structure network classes             Utility Network contextual tab appears
     +- Service territory
```

The Utility Network tab (ribbon) is **contextual**: it appears only when a UN layer is in the **active map**. No layer in the map, no tab. This is the first thing to check for "my Utility Network tab is missing".

### 1.2 How to put a UN on a map (Esri order)

1. **Insert** tab, **Project** group, **New Map**.
2. **Map** tab, **Layer** group, **Add Data**, then **Subtype Group Layer**. Browse to the data source and select the related feature classes with Ctrl. Do **not** select the utility network dataset itself in this step. (Published service: use the **Portal** tab. Single-user: **Project** or **Computer**.)
3. **Add Data** again and browse to the **utility network dataset** itself. The **Utility Network** tab appears.
4. Click the **Utility Network** tab to activate it.

The UN layer is named "<network name> Utility Network" in Contents (Esri example "EsriCoOp Utility Network"). Use the **Project** tab (database connection) for administration and configuration; use the **Portal** tab (the published service) for editing and analysis.

Pitfalls:

- Adding only the dataset gives the layer without the data classes; adding only classes gives no tab. You need both.
- For publishing, the map must contain all participating classes and no definition queries, hidden fields or subtype group layers on the UN layer (`pro-help/10`).
- Pro 3.x Esri editing quick start for services: **Catalog** pane, **Portal** tab, right-click the UN feature layer, **Add To New**, **Map**.

### 1.3 The Utility Network tab: groups and buttons (Pro 3.7)

Exact labels from Esri's "Utility Network tab" page:

| Group | Button | What it does |
|---|---|---|
| **Network Topology** | **Validate** (drop-down: **Current extent** default, **Entire extent**, **Rebuild current extent**) | Validates dirty areas in the view or the whole network. *Rebuild current extent* rebuilds the topology in the view and ignores dirty areas; use only when validation fails. Runs **synchronously** |
| | **Error Inspector** | Opens the Error Inspector pane (UN version 4+) |
| | **Terminal Paths** | Opens Modify Terminal Paths pane: change the valid path for a selected feature |
| | **Terminal Connections** | Opens Modify Terminal Connections pane: connect a line to a terminal on a device |
| **Associations** | **Modify** | Opens the Modify Associations pane (tabs Connectivity, Containment, Attachment) |
| | **Enter/Exit Containment** | Containment mode: new features become content of the selected container |
| | **Display Content** | Shows or hides container content via the `DisplayContent` display filter (must be configured first, section 5) |
| | **View** | View Associations Mode: draws connectivity and structural attachment associations in the current extent |
| **Tools** | **Trace / Clear All** | Opens the Trace pane; drop-down has Clear All |
| | **Utility Network Tool Gallery** | Trace types (Connected, Subnetwork, Subnetwork Controllers, Upstream, Downstream, Loops, Shortest Path, Isolation, Path); selecting one opens the Trace tool preset. The dialog launcher opens **Network Options** |
| **Selection** | **Apply To Diagrams** | Pushes the map selection to open diagrams (all or one) |
| | **Apply To Maps** | Pushes the selection to other maps in the project |
| **Diagram** | **Find** | Opens the Find Diagrams pane |
| | **New** | Creates a temporary diagram from the selection, using a chosen template |
| | **Overwrite** / **Append** | Replace or add to an open temporary diagram |
| | **Use Trace Locations** | Temporary diagram from the trace locations |
| **Subnetwork** | **Find** | Opens the Find Subnetworks pane |
| | **View** | Opens the Subnetworks table |
| | **Modify Controller** | Opens the Modify Subnetwork Controller pane |
| **Telecom Circuits** | **Find Circuits**, **Create Circuit**, **Manage Unit IDs** | Esri states **Manage Unit IDs** (opens the Unit ID Operations pane) is enabled only when the network contains a telecom domain network; for the other two buttons, verify against the Esri docs for your version |

Notes:

- Esri's gallery list still shows "Shortest Path" next to "Path". Shortest path is deprecated at Pro 3.7 / Enterprise 12.1 in favour of Path (`pro-help/05`).
- There is **no pane called "Utility Network pane"** in Esri's documentation. The working panes are named for their job: Trace, Modify Associations, Modify Subnetwork Controller, Find Subnetworks, Find Diagrams, Error Inspector, Modify Terminal Paths/Connections. If a user says "the Utility Network pane", ask which one.
- Labels change between Pro releases (this list is Pro 3.7). Always match the user's Pro version.

### 1.4 The panes in practice

**Trace pane** (Utility Network tab, Tools group, **Trace**). Tabs **Start**, **Stop**, **Barriers**, plus a **Named Configurations** tab for saved configurations. Key controls: **Add features** (click the map), **Add selected** (use the current selection or attribute-table rows), **Auto Apply** (when unchecked, additions show an asterisk until you click **Apply**), **Delete** and **Clear All**, **Filter Barrier** (Barriers tab), a **Terminal** drop-down for devices with terminals, **First Unit** / **Last Unit** for telecom grouped objects.
Symbols: starting points green circles, stopping points red hexagons, barriers red Xs; gray until applied when added with Add selected. Each edge supports one starting point, one stopping point and one barrier; extra additions overwrite. **Clear All** also deselects the active named configuration. Esri states that runs from the Named Configurations tab bypass geoprocessing and write no GP history; for other pane traces, verify against the Esri docs for your version. The **Tracing** tab of **Network Options** has *Maximum number of starting points and barriers to add at once*, default 10.
The trace types and options themselves are in `learn/07-tracing-in-depth-and-configuration-library.md` and `pro-help/05`.

**Modify Subnetwork Controller pane** (Subnetwork group, **Modify Controller**). Pick the device (Select feature tool) or add rows (Add selected), choose **Terminal**, **Tier** (only tiers where this asset type may be a controller), **Subnetwork Controller Name** (unique in the tier) and **Subnetwork Name** (unique in the network; up to 64 characters, cannot start or end with a colon, no double colon), optional **Description** and **Notes**, then **Apply**. Afterwards validate topology and run Update Subnetwork. The Python equivalent is `arcpy.un.UtilityNetwork.EnableSubnetworkController(...)` inside an edit operation (`arcpy/01`).

**Find Subnetworks pane** (Subnetwork group, **Find**). A grid with **Status** (green check clean, yellow warning dirty, red warning invalid) and **Last Update**, a refresh button, quick filters, a filter expression section and a "Use the current map extent" check box (clear it to read the Subnetworks table instead of only subnetworks whose SubnetLine falls in the view). Right-click a subnetwork for Flash, Zoom To, Pan To, Select, Pop-up (when it has SubnetLine geometry), subnetwork trace, update, select controllers and activate. Esri does not give exact menu labels for those last four; check the app. Whether updates from this pane write GP history: verify against the Esri docs for your version.

**Error Inspector pane** (Network Topology group, **Error Inspector**; UN version 4+). The **Source** field fills from the map's UN layer. The **Map Extent** filter is on by default, so errors elsewhere in the network are hidden until you turn it off. The table shows an `Error(s)` text ("10: Invalid connectivity" style). `Status` and `Error code` are **not** in this table; read them from the Dirty Areas attribute table. Selecting a row shows attributes on the **Details** tab. Meaning of the codes: `pro-help/04`, `learn/09`.

**Modify Associations pane** (Associations group, **Modify**): create, select, edit and delete associations; deletions apply on save. Creation needs a supporting rule and, for containment and attachment, an association role (`learn/08` section 10, `learn/04`).

### 1.5 Contents pane: what the UN layer shows

Expand the UN layer in Contents:

| Item | What it is | Notes |
|---|---|---|
| **Dirty Areas** (sublayer) | Polygons where the map and topology disagree, plus errors | Open the attribute table for `Status`, `Error code`, `Error message` (`learn/02` section 10.1, `learn/03`) |
| **Dirty Objects** (table) | Edits to nonspatial objects and associations | Exists only with a **telecom** domain network |

Esri's layer-access page names only these two items under the layer. Other system objects (Associations, Subnetworks, Rules, diagram layers, trace configurations) are not shown as sublayers: you reach them through tool panes (Modify Associations, Subnetwork **View**) or by adding the service layer ID by path.
Examples Esri documents: the Subnetworks table is service layer **500002** (Add Data, From Path, service URL ending in the ID; it appears under **Standalone tables**). Associations is 500001 per the example IDs in `learn/02` section 10; your service's real IDs come from `systemLayers` in the feature service JSON. Whether the Associations table is hidden by default: verify against the Esri docs for your version.

Right-click the UN layer, **Properties**, for the layer property tabs.

### 1.6 Network Properties: the configuration at a glance

Layer **Properties**, **Network Properties** tab. It is the quickest read-only audit of what the network is. Esri lists these sections:

| Section | What it shows |
|---|---|
| **General** | Creation and last-modified times, version history, cluster keys, the **portal utility network owner**, and for v8 partition ID size and max wavelengths. Owner and upgraded status appear only for an enterprise connection made as the database utility network owner |
| **Network Topology** | Enabled or not, dirty area count, error counts by feature type, timing records for enable/validate/disable |
| **Structure Network** | Name, creation time and the structure datasets, each with asset group/type, association role, container view scale, category, split and connectivity policies |
| **Domain Network** | One section per domain network: general settings, tiers and subnetwork rules, valid controllers, diagram templates, trace configuration, class properties (telecom adds color sets, circuits, divide/combine policies, wavelength schemes) |
| **Rules** | The rule base grouped by rule type |
| **Attributes and Assignments** | Network attributes (type, nullability, domain, apportionable, substitution) and which class/field each maps to |
| **Terminal Configurations** | Directionality, terminals, valid paths |
| **Categories** | Names and creation times |
| **Trace Configurations** | Named configurations: name, description, creator, time, tags |

Use this tab first for "what tiers/rules/attributes does this network have" before writing arcpy `Describe` code (`arcpy/01`). Its Network Topology section is also where you read the dirty-area and error counts without a query.

### 1.7 Catalog: the dataset side

Geodatabases appear under **Databases** in the Catalog pane (and under **Portal** for published layers). Inside the feature dataset you see the UN dataset, the structure network classes, one set of classes per domain network (prefixed by the domain network name), the service territory and system tables (`learn/02` section 1 has the full layout).

What you do from the Catalog side:

| Task | How |
|---|---|
| Choose the tool input | Drag the dataset to a GP tool, or browse to it in the tool's `Input Utility Network` control |
| Add the dataset to a map | Right-click, add to map (or Add Data on the Map tab) |
| Set versioning | Feature dataset **Properties**, **Versioning** (register as branch versioned; registers the junction and edge object tables with it) |
| Copy/transfer the whole network | Core copy and paste keeps topology, subnetwork status, circuits, diagrams and dirty areas; Package toolbox and XML workspace document are the alternatives (`pro-help/08`) |
| Check owner connection | Which database connection the dataset was opened through decides owner-level tool access (section 2) |

Esri's create and dataset-administration pages do not describe Catalog-specific context-menu items beyond the above. Do not promise a specific right-click command for a UN dataset without checking the user's Pro version.

### 1.8 Subnetworks table

Open it from **Utility Network** tab, **Subnetwork** group, **View**, with the UN layer selected (or from path 500002 when the layer is not in the map). It is system-maintained and read-only: one row per controller terminal with `SUBNETWORKNAME`, `TIERNAME`, `ISDIRTY` (clean, dirty or invalid), `ISDELETED`, `LASTUPDATESUBNETWORK`, `LASTACKEXPORTSUBNETWORK` and editor tracking (`pro-help/02`, `learn/06` section 6). Use it as the authoritative status list; the Find Subnetworks pane is a friendlier view of the same data.

### 1.9 Network diagrams in Pro

The diagram tools appear on the **Diagram** group of the Utility Network tab (find, create temporary diagrams) and on the **Network Diagram** tab, which is available in an active diagram map view or as a contextual tab when a diagram layer is selected. Groups on that tab (Esri): **Manage** (Find, Store, Consistency, Dynamic, All Layers), **Modify** (Recalculate, Update, Extend, Overwrite, Append), **Layout** (Diagram Layouts, Set Flags, Copy Layout From), **Selection**.
Esri's tools-and-commands page does not describe a pane called "Network Diagrams pane". The panes are **Find Diagrams** and the **Network Diagrams** tab of the Network Options dialog. A new diagram is temporary until **Store** is used. Template (rule) configuration uses `arcpy.nd` tools on a file/mobile geodatabase or direct database connection, not a service (`pro-help/07`). Changing a template makes existing diagrams inconsistent.

### 1.10 Network Options dialog

Opened from dialog launchers on the Utility Network tab. Esri documents these tabs: **Associations** (max associations returned, default 250; include connectivity and structural attachment, both on by default and drawn dashed; optional bounding box), **Tracing** (max starting points/barriers at once, default 10), **Sharing** (the **Active** check box that makes a named trace configuration available in web maps, off by default), and a **Network Diagrams** tab. Verify other tabs for your version.

---

## 2. The end-to-end build and administer flow

This is the order for a network configured by hand with core tools. The Foundation route (Stage Utility Network, Apply Asset Package) compresses steps 1 to 10 into a package deployment (`pro-help/08`); migration compresses them differently (`pro-help/11`). Understanding the manual flow explains what those packages do.

### 2.0 Ownership, license and version primer

Two owners, and three states that decide whether a tool will run (`pro-help/10`):

| Concept | Meaning in the flow |
|---|---|
| **Database utility network owner** | The database login that created the network. You act as that owner by opening the **database connection** as that user and passing the dataset from it to the tool |
| **Portal utility network owner** | The portal account signed in to Pro when the network was created |
| **Topology state** | Disabled or Enabled (most configuration needs Disabled) |
| **Version** | Configuration runs on **DEFAULT** only; named versions cannot change structure |
| **License** | Pro Standard or Advanced for every UN tool (not Basic). Enterprise: **Advanced Editing** user type extension on the portal account to create, publish, edit, validate and update subnetworks. Query and trace need none |

In Esri's "Network topology actions" table, "owner required" means **both** owner conditions together unless it says "DB owner" or "Portal owner" only.

### 2.1 The flow with exact tools

Legend for the "Needs" column: **Dis** topology disabled; **En** enabled; **Either**; **Pre** only before the first enable; **DB** database connection; **Svc** through the service; **Both** both owner connections; **DB-own** database owner only; **DEF** DEFAULT version only.

| # | Step | Tool (toolbox) | Needs | Notes |
|---|---|---|---|---|
| 1 | Create the dataset | **Create Utility Network** | Dis, DEF, DB, Both | Input Feature Dataset, Utility Network Name, Service Territory Feature Class (m- and z-enabled polygon in the same dataset), Utility Network Version (Compatible, Current, 8, 7, 6, 5). Enterprise: database-authenticated, non-admin, non-OS-authenticated user; geodatabase 11.2.0.3.2+ for v7+ |
| 2 | Add domain networks | **Add Domain Network** (traditional) / **Add Telecom Domain Network** | Dis, DEF, DB, Both | Domain Network Name (prefixes class names), Tier Definition (Hierarchical or Partitioned), Subnetwork Controller Type (Subnetwork source or sink), optional alias. Cannot be deleted later |
| 3 | Classify features | **Add Subtype**, **Create Domain**, **Add Coded Value To Domain**, **Assign Domain To Field** (Data Management) | Either, DEF, DB, Both | `ASSETGROUP` is the subtype field; `ASSETTYPE` is a domain per subtype. Adding/renaming values is allowed enabled or disabled; deleting is not |
| 4 | Terminal configurations | **Add Terminal Configuration**, then **Set Terminal Configuration** | Dis, DEF, DB, Both | Delete or reassign only **before the first enable** (Esri: assignment "cannot be changed after the network topology is enabled for the first time"). Whether existing rules must be removed from an asset type first (reported for Pro 3.5+): verify against the Esri docs for your version |
| 5 | Association roles | **Set Association Role** | Dis, DEF, DB, Both | Container/structure roles, deletion semantics; unassign only before first enable |
| 6 | Network attributes | **Add Network Attribute**, **Set Network Attribute** | Dis, DEF, DB, Both | Define first, then map to class/field. In Line needs a domain (`learn/05`). Cannot be deleted |
| 7 | Network categories | **Add Network Category**, **Set Network Category** | Dis, DEF, DB, Both | Set replaces the whole category set for the asset type. The Subnetwork Controller category needs a directional terminal configuration first (partitioned) |
| 8 | Edge connectivity | **Set Edge Connectivity** | Dis, DEF, DB, Both | Choose **Any vertex** or **End vertex** per asset type (midspan behaviour) |
| 9 | Rules | **Add Rule** (or **Import Rules**) | Dis, DEF, DB, Both | Junction-junction, junction-edge, edge-junction-edge, containment, structural attachment. Import Rules needs Dis and DEF |
| 10 | Tiers and subnetwork definition | **Add Tier Group** (hierarchical only), **Add Tier**, **Set Subnetwork Definition** | Dis, DEF, DB, Both | Add tiers **before** appending data (appending first errors). Definition holds valid devices/lines/junctions/objects, valid controllers, barriers, edit mode, diagram template, summaries |
| 11 | Optional: cluster keys | **Enable Cluster Keys** (v4 to v7 classes; either state), **Calculate Cluster Keys** (Dis) | DEF, DB, no owner | Helps nonspatial-object-heavy networks; enable topology afterwards so values apply |
| 12 | Load data | **Append**, **Load Data Using Workspace**, Foundation data tools, etc. | Either; no owner | Needs spatial indexes on all UN classes before enable. Load order and bulk guidance: `learn/08` section 14 |
| 13 | Load associations and controllers | **Import Associations**, **Import Subnetwork Controllers** | Either, DB, DB-own | Esri advises importing large volumes with topology disabled; rules must exist first |
| 14 | Find errors without enabling | **Enable Network Topology** with **Only generate errors** checked | Dis, DEF, DB, Both, **unversioned** | Errors go to the Dirty Areas table; the run stops at *Maximum number of errors* (default 10000) |
| 15 | Fix errors | Edit features, rules, or use **Analyze Network Data** + **Apply Error Resolutions** (Migration toolset) | varies | Triage by error ID (`pro-help/04`, `learn/09`) |
| 16 | Register as branch versioned (enterprise) | Feature dataset **Properties**, **Versioning**, or the Register As Versioned tool with the branch option | DB | Required before the normal enable and before publishing; the database connection's versioning type must be **Branch** |
| 17 | Enable topology | **Enable Network Topology** | Dis, DEF, DB or Svc, Both, versioned | Prerequisites: exclusive schema lock, spatial indexes, Asset type domains per subtype, at least one rule (per Esri's Pro enable topic), branch versioned, DEFAULT. Blocks other DEFAULT validate/enable sessions; runs asynchronously through `UtilityNetworkTools` since Enterprise 10.9.1 |
| 18 | Validate | **Validate** command or **Validate Network Topology** tool | En, Svc | Clears edit dirty areas; error-only rows persist (`pro-help/04`) |
| 19 | Subnetwork controllers | **Modify Controller** pane, `EnableSubnetworkController`, or Import Subnetwork Controllers | Either, Svc (pane) | Needs the category, the Valid Subnetwork Controller flag, terminal config and unique names. Validate afterwards |
| 20 | Update subnetworks | **Update Subnetwork** (tool or Find Subnetworks pane) | En, Svc, no owner | Needs saved edits, no dirty areas on the subnetwork, controllers dirty. Single subnetwork is synchronous (10-minute time-out); *All subnetworks in tier* is asynchronous (120-minute time-out) |
| 21 | Derived state | **Update Is Connected** | En, Svc, **Both** | Traditional domain networks only |
| 22 | Diagram templates, trace configurations | `arcpy.nd` rule tools; **Add Trace Configuration** | diagram rules: DB/file/mobile; trace configs: Either, Svc, no owner | Diagram template edits need the network owner; trace configuration add/delete does not |
| 23 | Publish and baseline | Share as web layer; **Export Asset Package** (Package toolbox) | owners per `pro-help/10` | Keep a baseline package for dev, test, prod promotion |

### 2.2 Why the order is what it is

- Steps 4 to 10 are **schema** work. They change what the topology will mean, so Esri requires topology disabled and DEFAULT. After the first enable, several of them become partly irreversible (terminal configuration deletion, association role unassign) or are never allowed (deleting domain networks, tiers, network attributes).
- Step 7 before 19: a device cannot be a controller until its asset type has the category and a suitable terminal configuration. Users who try controllers first report the option "not appearing" (`pro-help/03`).
- Step 10 before 12: tiers add the subnetwork name fields; data appended earlier causes an error (Esri, Add Tier).
- Step 14 before 16/17: "Only generate errors" must run **unversioned**, while a normal enable needs **branch versioned**. Do the error pass first, then register, then enable.
- Steps 18 and 20 are separate on purpose: Validate maintains the topology (connectivity truth); Update Subnetwork maintains analytic results (names, SubnetLine, propagated values). `learn/01` and `learn/03` explain the staleness window.

### 2.3 Which owner connection each step needs (summary)

| Owner condition | Steps |
|---|---|
| **Both** (database login as owner **and** portal sign-in as owner) | 1 to 10 (including Add Color Set/Scheme, Add Wavelength Scheme, Set Circuit Properties, telecom combine/divide policies), 14, 17, 21, Disable Network Topology, Repair/Verify Network Topology, Analyze Network Data, Apply Error Resolutions, Import/Export Rules, Modify Terminal Connections, diagram template maintenance |
| **Database owner connection only** | Import/Export Associations, Import/Export Subnetwork Controllers, Update Portal Dataset Owner |
| **Portal owner only** | Export Subnetwork with *Set export acknowledged* |
| **No owner** | Step 11 (Calculate/Enable Cluster Keys), Load data, Validate, Rebuild, Update Subnetwork, Export Subnetwork without acknowledgment, Verify Circuits, Export Circuits, Export/Import Circuit Definitions, add/delete/export/import trace configurations, normal editing |

Source of truth: Esri "Network topology actions" (table reproduced selectively here; consult it for any tool not listed). `pro-help/10` records the same grouping and the symptom mapping ("tool greyed out" vs "only the owner of the version").
Note on Apply Asset Package: Esri's published prerequisites are that maps are closed, topology is disabled, Pro matches the dataset version, and for enterprise the database owner, portal owner and DEFAULT apply (`pro-help/08`).

### 2.4 The version state at each stage

```
 configure (DB connection, DEFAULT, topology off) ------------------> first enable
      unversioned or versioned DB connection                        (enable needs branch versioned)
                                                                          |
 publish (feature service, Version Management capability) <---------------+
      |
 edit in named versions through the service; validate; update subnetwork; reconcile; post
```

Structural changes after publishing: schedule a maintenance window, because a schema change disables topology (one big dirty area), applies on DEFAULT only and is invisible to named versions until they reconcile (`learn/08` section 15).

---

## 3. Daily operations by role

Practitioner guidance layered on Esri-documented steps. Roles are logical; one person may hold several.

### 3.1 Editor (online, in Pro)

| Step | Click or run | Why |
|---|---|---|
| 1 | Open the map with the UN layer from the **Portal** tab; in Contents, **List by Data Source**, feature service, **Versioning** tab, **New Version** (name, optional description, **Private/Protected/Public**, check **Change to this new version**) | Edit in your own branch, not DEFAULT |
| 2 | **Edit** tab, **Snapping** group, **Snapping** | Snapping follows connectivity rules; you can turn it off but cannot choose layers |
| 3 | **Edit** tab, **Features** group, **Create**; pick a template (group or preset templates make associations) | New feature creates a dirty area |
| 4 | **Modify** (Associations group) when a structural or containment link is needed | Associations need rules and roles |
| 5 | **Utility Network** tab, **Validate** > **Current extent** | Clears the dirty area; surfaces errors immediately |
| 6 | **Error Inspector**; fix errors; validate again | Errors do not fix themselves |
| 7 | **Edit** tab, **Manage Edits** group, **Save** | Persist to the version |
| 8 | Hand over to QA (change owner/access, or notify) | Do not post unless authorised |

Esri's own quick start ends at Save and says a full workflow also includes conflicts, upstream tracing and reconcile. Where an editor works through Field Maps or a web app, steps differ (`learn/08` sections 11 and 12).

### 3.2 QA reviewer / version administrator

1. Open the editor's version (Versioning tab; ownership handoff via version properties).
2. **Validate** the work area; review **Error Inspector** and the Dirty Areas table (`Status` values 8, 16, 32 and sums of only error bits never clear by validating; they need a feature edit).
3. Run QA traces in the Trace pane: Connected for continuity, Upstream/Downstream for flow, Isolation for operable devices.
4. Run attribute-rule validation (`Evaluate Rules`) if the network uses batch validation rules (`learn/05`).
5. **Reconcile**, review conflicts in the Conflict Manager, validate again, **Post**. Delete the version.
6. Hand the post-posting work (validate DEFAULT, update subnetworks) to the scheduled job or the administrator.

### 3.3 Analyst

| Question | Where in Pro | Notes |
|---|---|---|
| "What is downstream of this valve?" | **Trace** pane, **Start** tab, trace type Downstream | Needs subnetwork controllers and an updated subnetwork for controller-based flow; or **Use Digitized Direction** |
| "What do I have to close to isolate a pipe or feeder?" | Isolation trace with a filter barrier in the configuration | Named configuration in the Trace pane is easiest to repeat |
| "How many customers in this subnetwork?" | Subnetwork trace with a function or summary, or **Export Subnetwork** | Summaries are stored on SubnetLine (Set Subnetwork Definition) |
| "Show me the circuit/diagram" | Utility Network tab, **Diagram** group, **New** | Temporary until Stored |
| "Run this trace every week" | `arcpy.un.Trace` / **Add Trace Locations** + ModelBuilder or Python | Add Trace Locations makes a reusable feature class of starts and barriers |

Analysts need no Advanced Editing extension for trace and query. Their results are only as fresh as the last validate and Update Subnetwork (`learn/03` section 10).

### 3.4 Administrator (database and portal owner)

Recurring:

| Frequency | Task | Tool or place |
|---|---|---|
| Continuous | Monitor dirty-area count and error counts | Network Properties, Network Topology section; Dirty Areas table |
| Scheduled (often nightly) | Validate DEFAULT, then Update Subnetwork for dirty subnetworks | `Validate Network Topology`, `Update Subnetwork` with *All subnetworks in tier* and *Continue on failure* (or scripted REST, `learn/10` section 11) |
| After posts | Confirm Update Subnetwork ran on DEFAULT, because SubnetLine does not post | Find Subnetworks pane: look for dirty or invalid |
| Occasional | Fix topology system-table inconsistencies | **Verify Network Topology** (log only), then **Repair Network Topology**; **Rebuild Network Topology** for a failing extent |
| Occasional | Structural changes (rules, tiers, categories) | Section 2 flow in a maintenance window |
| Release time | Upgrade dataset | **Upgrade Dataset**, with exclusive lock, topology disabled, owners, backup (`pro-help/09`) |
| Handover | Change portal owner when staff leave | **Update Portal Dataset Owner**, then transfer related item ownership |

Admin checklist when a user reports "tool disabled": (1) Is topology in the right state? (2) Is the user connected as the right owner(s)? (3) Is the user on DEFAULT for config? (4) Is the license adequate (`pro-help/10`)?

---

## 4. The tool map

Source: Esri Utility Network toolbox overview and toolset overview pages (Pro 3.7): 8 tools directly in the toolbox, 40 in Administration, 4 in Trace Configuration, 3 in Migration. The Package toolbox (Stage Utility Network, Apply Asset Package, Export Asset Package) is a separate Esri Solutions toolbox (`pro-help/08`). Network diagram tools are `arcpy.nd`, a separate toolbox (`pro-help/07`).
Parameter names below are the **dialog labels**. For Python keyword names check the Python tab on the live page; `arcpy.un.UpdateSubnetwork` is documented in `arcpy/01`. All tools are available at Standard and Advanced license levels, **not Basic** (Validate Network Topology is "Limited" at Basic for enterprise per its page; treat as not available). Enterprise use also needs Advanced Editing on the portal account for the operations listed in `pro-help/10`.

### 4.1 Create and structure

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Create Utility Network** | Creates the UN in a feature dataset (with the structure network) | Feature dataset, name, service territory, version | Territory must be m- and z-enabled polygon in the same dataset; extent cannot be changed later |
| **Add Domain Network** | Adds a traditional domain network | Name, Tier Definition, Subnetwork Controller Type, alias | Topology off; no delete; Esri's topology-actions table shows no delete, and no tool to change tier definition or source/sink afterwards (verify against the Esri docs for your version) |
| **Add Telecom Domain Network** | Adds a telecom domain network | see tool page | Version 8 is the telecom-oriented dataset version; Compatible and Current still create v7, so choose 8 explicitly |
| **Add Tier Group** | Groups hierarchical tiers | see tool page | Hierarchical definitions only |
| **Add Tier** | Adds a tier | Domain Network, Name (unique network-wide), Rank (1 highest), Topology Type (Radial/Mesh, no current effect), Tier Group Name, Subnetwork Field Name | Add before loading data; hierarchical tiers force Mesh and require a tier group |
| **Set Subnetwork Definition** | Configures what a tier's subnetwork contains and how Update Subnetwork behaves | Valid Devices/Lines/Junctions/Junction Objects/Edge Objects, valid controllers, Aggregated Lines, Diagram Templates, Summaries, barriers, Include Barrier Features, Apply Traversability To, Propagators (Python only), edit modes, Manage IsDirty, Include Containers/Content/Structures, Validate Locatability | Partitioned tiers get *Support Disjoint Subnetwork* off by default; hierarchical on. Rerun to modify. Edit Mode defaults to *Without eventing* |
| **Set Edge Connectivity** | Per asset type: connect at Any vertex or End vertex | Domain Network, Input Table, Asset Group, Asset Type, Edge Connectivity | The "Any vertex" option is what makes midspan taps possible; changing from End vertex to Any vertex needs topology off |
| **Set Association Role** | Container or structure role and deletion semantics | role type, deletion semantics, view scale, split policy | Unassign only before first enable |

### 4.2 Rules, terminals, attributes, categories

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Add Rule** / **Delete Rule** | Adds or permanently removes a network rule | Rule Type, From/To (and Via) table, group, type, terminals | `Delete Rule` is permanent; topology off, DEFAULT, both owners |
| **Import Rules** / **Export Rules** | CSV round trip of connectivity, attachment and containment rules | CSV path | Import needs topology disabled and DEFAULT; Export works either state |
| **Add Terminal Configuration** / **Set Terminal Configuration** / **Delete Terminal Configuration** | Define a terminal layout, assign it to an asset type, delete it | name, directionality, terminals (2 to 8, names up to 32 chars); asset type | Assignment is permanent after first enable. Rules-removal requirement (reported for Pro 3.5+): verify against the Esri docs for your version |
| **Add Network Attribute** / **Set Network Attribute** | Define a network attribute and map it to a class field | name, data type, In Line, Apportionable, Substitution, Nullable | Cannot delete once defined; In Line bits are limited (`learn/05`) |
| **Add Network Category** / **Set Network Category** / **Delete Network Category** | Define, assign, delete categories | name; asset type list | Set replaces the whole category set |
| **Add Color Set**, **Add Color Scheme**, **Delete Color Scheme**, **Add Wavelength Scheme** | Telecom fiber/cable color and wavelength configuration | see tool pages | Delete of color set and wavelength scheme currently not allowed |
| **Set Circuit Properties**, **Set Telecom Object Combine Policy**, **Set Telecom Object Divide Policy** | Telecom circuit and grouped-object behaviour | see tool pages | Combine/divide policies allowed enabled or disabled; circuit properties need disabled |

### 4.3 Topology lifecycle and health

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Enable Network Topology** | Builds the topology; writes existing errors as dirty areas | Maximum number of errors (default 10000, -1 unlimited), Only generate errors (default off) | Needs branch versioned (or unversioned for errors-only), DEFAULT, both owners; blocks other DEFAULT validate/enable; one-time permanent decisions precede it |
| **Disable Network Topology** | Turns the topology off | utility network | Creates one dirty area over the territory; a topology disabled in a named version cannot be re-enabled there |
| **Validate Network Topology** | Evaluates dirty areas | Input Utility Network, Extent; derived Output JSON lists subnetworks marked dirty | Needs a service input (enterprise); one session at a time on DEFAULT; asynchronous via `UtilityNetworkTools` while the ribbon **Validate** is synchronous |
| **Rebuild Network Topology** | Rebuilds the topology in an extent, ignoring dirty areas | Input Utility Network, Extent | Use only when validation fails; service from Enterprise 10.9+; the ribbon equivalent is *Rebuild current extent* |
| **Verify Network Topology** | Checks topology system tables, logs inconsistencies | Output Log File (optional) | Does not change data; pair with Repair |
| **Repair Network Topology** | Repairs topology system-table inconsistencies | Output Log File (optional) | Topology must be enabled; branch versioned; both owners |
| **Update Is Connected** | Fills `ISCONNECTED` | Utility Network | Traditional domain networks only; topology enabled; both owners |
| **Calculate Cluster Keys** / **Enable Cluster Keys** | Group features for performance / create `CLUSTERKEY` on v4 to v7 classes | Overwrite, Extent | Topology must be disabled for Calculate; re-enable after |

### 4.4 Subnetworks

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Update Subnetwork** | Updates Subnetworks table, SubnetLine and system diagrams, names and propagated values | Domain Network, Tier, All subnetworks in tier, Subnetwork Name, Continue on failure, barriers and propagators (Python only) | Traditional domain networks only; saved edits, no dirty areas on the subnetwork, topology on; do not run two All-in-tier runs at once; list is empty above 10,000 records in the tier |
| **Export Subnetwork** | Writes a subnetwork to JSON | Domain Network, Tier, Subnetwork Name, Set export acknowledged, Output JSON, result types, include flags | Run Update Subnetwork first; *Set export acknowledged* needs DEFAULT and the portal owner; related records need Enterprise 11.5+, flow directions and propagated values 12.1+ |
| **Import Subnetwork Controllers** / **Export Subnetwork Controllers** | Bulk controllers via CSV | CSV | Database owner connection; there is no GP tool named "Set Subnetwork Controller" (`arcpy/01`) |

### 4.5 Associations

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Import Associations** / **Export Associations** | CSV round trip of associations | association type, CSV | Database owner connection; features and rules must already exist; use Export of one hand-made association to learn the shape (`pro-help/04`) |

### 4.6 Tracing

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Trace** | Returns features by connectivity or traversability | trace type, starting points, barriers, configuration, result types | See `learn/07`; Path replaces Shortest path at Pro 3.7 / Enterprise 12.1 |
| **Add Trace Locations** | Builds a feature class of starts, stops and barriers | Output Feature Class, Load Selected Features, Clear Trace Locations, Trace Locations value table (Layer Name, Global ID, Terminal, Percent Along), Filter Barrier | Load Selected and Trace Locations table are mutually exclusive; Percent Along defaults to 0.5 on lines; v7+ allows file, mobile or enterprise output |
| **Add Trace Configuration** / **Delete Trace Configuration** | Create or delete named configurations | name, description, tags, trace settings | Works in the versioned service; no owner connection; UN version introduced: verify against the Esri docs for your version |
| **Export Trace Configurations** / **Import Trace Configurations** | JSON round trip | JSON path | Use to move configurations between environments |
| **Verify Circuits**, **Export Circuits** | Telecom circuit checks and export | see tool pages | Telecom only |
| **Export Circuit Definitions** / **Import Circuit Definitions** | Telecom circuit tables to/from CSV | see tool pages | DEFAULT, database connection, no owner |

### 4.7 Migration

| Tool | One-line meaning | Key parameters | Gotchas |
|---|---|---|---|
| **Migrate To Utility Network** | Builds a UN in a mobile geodatabase from source data, schema and mapping | Output folder/name, service territory, domain networks, mapping, Load Data | Output is a basic UN; no advanced capabilities (`pro-help/11`) |
| **Analyze Network Data** | Scans a UN and records errors in an output mobile geodatabase | see tool page | Both owners for enterprise |
| **Apply Error Resolutions** | Applies fixes from the Error Resolutions table | see tool page | Must be unversioned, DEFAULT, both owners |

### 4.8 Other tools you will meet

| Tool | Toolbox | Use |
|---|---|---|
| **Upgrade Dataset** | Data Management | Move a UN to a newer dataset version (`pro-help/09`) |
| **Update Portal Dataset Owner** | Data Management | Reassign the portal owner |
| **Append**, **Rebuild Indexes** | Data Management | Load data; rebuild spatial indexes after big appends |
| **Apply Asset Package** / **Stage Utility Network** / **Export Asset Package** | Utility Network Package (Esri Solutions) | Foundation deployment and baselines (`pro-help/08`) |
| Attribute Rules toolset (**Add Attribute Rule**, **Evaluate Rules**, etc.) | Data Management | Calculation, constraint and validation rules (`learn/05`) |
| **Summarize Utility Network Errors** | Verify against the Esri docs for your version | Error summary tables for migrations (`pro-help/11`); not one of the 55 toolbox tools |

### 4.9 Scripting pointers

- Every GP tool is `arcpy.un.<ToolNameWithoutSpaces>` (for example `arcpy.un.ValidateNetworkTopology`).
- The class `arcpy.un.UtilityNetwork` manages associations and controllers without GP tools (`arcpy/01`).
- Toolbox ordering and dependencies mirror section 2: schema tools in topology-disabled blocks, then Enable, then Validate and Update Subnetwork.
- For long operations, the GP tool runs asynchronously on the `UtilityNetworkTools` service (Enterprise 10.9.1+), which has a longer time-out; the ribbon command runs synchronously.

---

## 5. Pro settings that change UN behaviour

| Setting | Where | Effect |
|---|---|---|
| **Database connection versioning type** | Database connection properties | Must be **Branch** for enterprise UN work (needed before adding the UN layer for publishing) |
| **Feature dataset registered as branch versioned** | Feature dataset **Properties**, **Versioning** | Required for services-based editing; registers junction and edge object tables with it |
| **Current version** | Contents, List by Data Source, **Versioning** tab, **Change Version** / **New Version** | Decides which version tools and edits hit. Config tools need DEFAULT. Version access: Private, Protected, Public |
| **Map Properties, unique numeric IDs** | Map properties | Needed to preserve layer IDs when publishing |
| **Snapping** | **Edit** tab, Snapping group | UN snapping follows junction and edge connectivity rules; you cannot change which layers features snap to |
| **Edit templates** | Create Features pane | Group and preset templates generate associations (Associations tab on the primary template; "Add associations when creating new assets") |
| **Attribute Rules** | Feature class (data owner) | Immediate rules run on save; batch rules need `Evaluate Rules`; rules interact with topology and Update Subnetwork edit mode (`learn/05` section 11) |
| **Edit mode in subnetwork definition** | Set Subnetwork Definition | *Without eventing* (default) updates names in place without attribute rules or editor tracking; *With eventing* fires them but can hold a shared lock on DEFAULT |
| **Network Options, Associations** | Associations group launcher | Max associations returned (250), include connectivity/attachment, bounding box |
| **Network Options, Tracing** | Tools group launcher | Max starting points and barriers at once (10) |
| **Network Options, Sharing** | Network Options | **Active** makes a trace configuration available to web maps (off by default) |
| **DisplayContent display filter** | Layer properties, Display Filters | Manual filter named exactly `DisplayContent` on `associationstatus`: `associationstatus NOT IN (4, 5, 6, 12, 13, 14, 36, 37, 38, 44, 45, 46)`. Without it the Display Content command does nothing |
| **Geoprocessing environments** | Geoprocessing | Most UN tools "use no geoprocessing environments"; Set Edge Connectivity uses *Current Workspace*; Add Trace Locations uses Current Workspace and Output has Z values |
| **Tracing: Validate Consistency** | Trace tool | Unchecked by default in Pro; when checked it fails traces touching dirty areas (`learn/03` section 10) |
| **Pro and dataset version** | Network Properties, General | Pro must be at least the dataset version's floor (v8 needs Pro 3.7 and Enterprise 12.1; `pro-help/09`). Field Maps and Native SDK support for v8: verify against the Esri docs for your version |
| **Background vs foreground** | Tool/ribbon | Ribbon Validate/Rebuild are synchronous and bounded by the client; GP tools go through the server and survive longer runs |
| **Save before UN tools** | Edit tab | Update Subnetwork and others require saved edits |

Practitioner guidance:

- Keep DEFAULT **protected**; edit in named versions; schedule DEFAULT validate.
- Never edit a published, versioned UN directly through the database except for owner bulk loads and initial QA (`learn/08` gotcha 22).
- Document the Pro version used for config scripts; labels and parameters move between releases.

---

## 6. Single-user (file or mobile geodatabase) differences

Esri's FAQ: single-user deployments use file or mobile geodatabases and **do not use versioned editing**; enterprise deployments use branch versioning and services. Utility network and network diagram **services** exist only for enterprise deployments shared through services.

| Topic | Enterprise | Single-user |
|---|---|---|
| Storage | SQL Server, Oracle, PostgreSQL, SAP HANA | File or mobile geodatabase |
| Versioning | Branch versioning, named versions, Version Management | None; no reconcile/post |
| Editing path | Through feature services (after publishing) | Directly in Pro against the geodatabase |
| Owners | Database owner + portal owner | No portal owner; OS authentication records the creator of trace configurations; any user can modify and delete all named trace configurations (Esri, About trace configurations) |
| License | Standard/Advanced plus Advanced Editing for create/publish/edit | Standard/Advanced (no portal) |
| Services, REST, JS | Utility Network, Network Diagram, Version Management services | None; Pro only |
| Concurrency | Many readers, one writer on 12.0+; DEFAULT concurrency | Mobile and file geodatabase locking/concurrency (one editor at a time, lock files): verify against the Esri docs for your version |
| Enable topology | Normal enable needs branch versioned; errors-only needs unversioned | Naturally unversioned, so Only generate errors works |
| Diagram template configuration | Direct database connection, not service | Allowed (file/mobile qualifies) |
| Update Subnetwork input | Must come from a service | Runs against the geodatabase directly |
| Constraints "DEFAULT only" | Apply | Do not apply |
| Dataset version | Constrained by Enterprise release | Follows the Pro release (Compatible = Pro-supported) |
| Offline/Field Maps | Via sync-enabled feature service | Not applicable |
| Practical use | Production | Sandbox for rules/tiers, migration staging, training, very small systems |

Practitioner flow: design in a single-user copy (fast iteration, no owners), export an asset package, then Stage and Apply in enterprise (`pro-help/08`). Migration with the wizard outputs to a mobile geodatabase for the same reason (`pro-help/11`).

---

## Common misconceptions

| Misconception | Reality |
|---|---|
| "There is a Utility Network pane where everything lives." | There is a Utility Network **tab** and several purpose-specific panes (Trace, Find Subnetworks, Modify Controller, Error Inspector, Modify Associations) |
| "Add the dataset to the map and I'm ready." | You also need the data classes (as subtype group layers); the tab appears with the UN layer |
| "Validate fixes all dirty areas." | Error-only rows (Status 8, 16, 32 and sums of error bits) are ignored; edit the feature |
| "Update Subnetwork and Validate are the same." | Validate maintains topology; Update Subnetwork maintains names, SubnetLine and propagated values |
| "I can set a controller with a GP tool." | There is no such tool: use the Modify Controller pane, `EnableSubnetworkController`, or Import Subnetwork Controllers |
| "Configuration works in any version." | Structure changes need DEFAULT and a disabled topology |
| "Compatible dataset version is the newest." | Compatible and Current still create v7; v8 must be chosen explicitly |
| "Trace needs an Advanced Editing license." | Query and trace do not; creating, publishing, editing, validating and updating subnetworks do |
| "Single-user networks can be traced from a web app." | There is no service layer for them |

## Quick checks

1. Which Pro version and which UN dataset version? (Network Properties, General.) Are Pro and Enterprise at or above that version's floor?
2. Enterprise or single-user? Is the data branch versioned? Which version is active?
3. Is the Utility Network tab visible? If not, is the UN layer in the **active** map?
4. For a greyed-out tool: topology state, DEFAULT or named, database connection user, portal sign-in, license (Advanced Editing)?
5. Was the dataset opened through the database connection **as the owner**, or through a different login?
6. For "no controller option": does the asset type have the Subnetwork Controller category, a directional terminal configuration and the Valid Subnetwork Controller flag?
7. For "stale trace": when was the last Validate and Update Subnetwork for that footprint? (`learn/03` section 10)
8. Are all UN feature classes spatially indexed before Enable?
9. Is the Error Inspector Map Extent filter hiding the errors?
10. Are tiers defined **before** data was appended?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md` (state model, staleness)
- `learn/02-data-model-in-depth.md` (dataset layout, system tables and layer IDs)
- `learn/03-topology-engine-and-validation.md` (enable, validate, dirty areas, Only generate errors)
- `learn/04-rules-and-connectivity-design.md` (Add Rule keys)
- `learn/05-attributes-categories-and-attribute-rules.md` (network attributes, categories, attribute rules)
- `learn/06-tiers-and-subnetworks-in-depth.md` (tiers, controllers, Update Subnetwork)
- `learn/07-tracing-in-depth-and-configuration-library.md` (Trace pane and tool)
- `learn/08-versioning-and-editing-workflows.md` (versions, roles, structural changes)
- `learn/09-failure-anatomy-symptom-to-fix.md` (error IDs and symptoms)
- `learn/10-performance-scale-and-operations.md` (scheduling and monitoring)
- `pro-help/02-structure-of-a-utility-network.md` through `pro-help/11-migration-and-schema-mapping.md`
- `arcpy/01-utility-network-module.md` (Python surface)

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-tab.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/access-the-utility-network-layer.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/access-utility-network-layer-properties.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-dataset-administration.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/configure-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/create-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/enable-the-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/validate-a-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-a-subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/update-a-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/find-subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-subnetworks-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetworks-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/manage-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-starting-points-and-barriers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-trace-configurations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/association-visibility.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/create-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-categories.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/network-diagrams-tools-and-commands.html
- https://doc.esri.com/en/arcgis-pro/latest/help/editing/edit-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/an-overview-of-the-utility-network-toolbox.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/an-overview-of-the-administration-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/an-overview-of-the-trace-configuration-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/an-overview-of-the-migration-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-domain-network.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-tier.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-subnetwork-definition.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-edge-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-is-connected.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/rebuild-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/repair-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/verify-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/export-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-trace-locations.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/calculate-cluster-keys.html
