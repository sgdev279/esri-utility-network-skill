# Utility Network: Editing in ArcGIS Pro (Templates, Connectivity, Associations)
*Sources: Esri ArcGIS Pro help (editing and utility network books) and tool reference; full URL list at the end.*

> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

## Why this matters / when to read this

Editing is where a utility network (UN) is made or broken. Every connection a trace later follows was created by an editor either by snapping two features together or by creating an association. Every error a validate run reports was created by an edit that a rule or restriction did not allow. Read this file when you need to know what each Pro editing surface is for, how a feature becomes connected, what a group or preset template really creates, how to make and remove associations, how to prove that a connection is allowed, and how to undo common mistakes. It is domain-neutral. Concepts it builds on: `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`, `learn/03-topology-engine-and-validation.md`, `learn/04-rules-and-connectivity-design.md`. The button map is in `learn/13-arcgis-pro-fundamentals-and-workflow.md`; this file goes deeper on the editing half of it.

## Contents

1. The editing environment: what each surface is for
2. How features connect while you edit
3. Terminals while editing
4. What is enforced at edit time versus validate time
5. Templates: feature, group, preset (and table)
6. Creating, viewing and deleting associations
7. Testing a network rule
8. Data integrity while editing
9. Editing mistakes and the fix
10. Pro editing tools that respect network topology
Common misconceptions, Quick checks, Related files, Sources

## 1. The editing environment: what each surface is for

**Definition.** A UN is edited with the ordinary ArcGIS Pro editing tools, plus a small set of UN-specific panes. Esri's editing reference says snapping, editing tools and templates all apply the network's connectivity rules and associations as you create or change features.

**Mechanism.** Nothing in the editing UI writes to the network topology. Edits go to edit space (feature classes, tables, the Associations table). Each qualifying edit leaves a dirty area; the topology catches up only at validate (`learn/03`). So the editing surfaces below fall into three jobs: *make or change features*, *make or change relationships*, *check and repair*.

| Surface (Pro label) | Where | Job in a UN edit |
|---|---|---|
| **Edit** tab | Ribbon | Home of **Create** (Features group), **Modify**, **Manage Templates**, **Save**/**Discard** (Manage Edits group), **Snapping** group |
| **Create Features** pane | Edit tab > Features group > Create | Pick a template and a construction tool, then sketch. Templates are grouped by layer; group and preset templates appear here too |
| **Manage Templates** pane | Edit tab > Manage Edits group (also reachable from Create Features) | Author, copy, delete and configure templates (**Template Properties** dialog) |
| **Modify Features** pane | Edit tab > Features group > Modify | Move, Move To, Continue, Edit Vertices, Replace Geometry, Split and similar tools; network-aware options such as **Disconnect** and **Stretch Topology** |
| **Attributes** pane | Edit tab (also right-click, or the Select tool) | Set asset group, asset type and other fields; a tree below a selected feature shows its associations with counts; **Associations** tab for From/To of junction and edge objects; right-click for **Add New To Container**, **Remove Association**, **Select Associated Data** |
| **Snapping** (button and drop-down) | Edit tab > Snapping group, and status bar | Turn snapping on; UN snap agents follow the rules (section 2). **Enable Snap Chip** lives here too |
| **Modify Associations** pane | Utility Network tab > Associations group > **Modify** | Create, edit and delete connectivity, containment and structural attachment associations; tabs **Connectivity**, **Containment**, **Attachment** |
| **Enter/Exit Containment** | Utility Network tab > Associations group | Containment mode: new features become content of the selected container |
| **View** (View Associations Mode) | Utility Network tab > Associations group | Draws association lines in the extent so you can see non-geometric links |
| **Terminal Connections** / **Terminal Paths** | Utility Network tab > Network Topology group | Open **Modify Terminal Connections** and **Modify Terminal Paths** panes |
| **Validate** | Utility Network tab > Network Topology group | Clears dirty areas for the current or entire extent |
| **Error Inspector** | Utility Network tab > Network Topology group (UN version 4+) | Lists topology errors; also the entry for attribute rule evaluation (section 8) |
| **Dirty Areas** sublayer | Under the UN layer in **Contents** | Polygons showing where edit space and topology disagree, and where errors exist |
| **Network Properties** tab | Right-click the network in Contents > **Properties** | Read-only view of rules, terminal configurations and categories; the first place to check what is allowed |

Esri notes that for enterprise geodatabases most of the Utility Network tab commands need the network opened through a feature service; **Terminal Connections** also works with an unversioned dataset. Esri's own Utility Network tab page is the source for this split.

Two naming traps:

- There is no pane called "Utility Network pane" in Esri documentation (`learn/13`). Ask which pane the user means.
- "Error Inspector" is reached from two places. Esri's UN pages put it on the **Utility Network** tab, Network Topology group, for topology errors. Esri's attribute rule evaluation page describes it on the **Edit** tab, **Manage Edits** group, with an **Evaluate Rules** section for batch calculation and validation rules. Whether these open exactly the same pane in 3.7: Verify against the Esri docs for your version.

Example (water). An editor draws a new main segment: **Create Features** pane, template "Water Line", construction tool Line, snapping on. The main ends at an existing valve. The new line shows a dirty area at once; nothing in a trace changes until **Validate**.

## 2. How features connect while you edit

There are exactly two ways a feature becomes connected to another (Esri): geometric coincidence, or a connectivity association. Either needs a network rule that allows the pair. Snapping alone creates nothing.

### 2.1 Geometric coincidence: what you do with the mouse

```
 point on line END            junction-edge          [Device]--------line
 two lines + point between    edge-junction-edge     line----[Junction]----line
 point in the MIDDLE of line  midspan (junction-edge) line----+----line   (line gains a vertex, is not split)
                                                              |
                                                          [Device]
```

1. You place features at the same x,y (and z). In Pro you get exact coincidence by snapping to an endpoint, vertex or edge.
2. At validate or enable the topology compares the features using the dataset's x, y, z tolerances. Features offset by less than tolerance are treated as coincident. Esri does not publish the tolerance values on the pages used here.
3. Rules and feature restrictions are then checked. If satisfied, the features connect. If not, both are flagged as errors and remain disconnected.

**Junction-edge versus edge-junction-edge.** A point at the end of a line is judged by a junction-edge rule (one rule per line end). A point between two lines is judged by an edge-junction-edge rule. If both rule types exist for the combination, junction-edge rules win (Esri: a valve between two lines connects under its junction-edge rules even though it would not satisfy an edge-junction-edge rule).

**Same asset group and type.** Two lines with the same asset group and asset type that share an endpoint need no rule and no user-placed junction: validate adds an invisible system junction (visible in a network diagram). This is why most "line meets line" edits just work while "line of one type meets line of another type" produces error 10 until an edge-junction-edge rule exists (`learn/04`, `pro-help/04-associations-editing-errors.md`).

### 2.2 Snapping that follows the rules

- When snap agents are enabled for network features, Esri says snap settings change automatically to match the junction and edge connectivity rules. You can turn snapping off. You cannot choose which layers or features you snap to.
- Practical meaning: if no rule allows a point to connect to a line, the cursor does not snap to that line. The Esri Learn lesson on editing phrases it as: network rules override map snapping, and if no rule allows two features to connect, the snap will not happen.
- Press **T** while creating features to see the snappable elements that the rules allow (Esri editing reference).
- Layers you do not want involved can still be turned off for snapping in the **Contents** pane (Esri snap chip page).
- The Esri Learn lesson uses the **Point**, **Endpoint**, **Vertex** and **Edge** snap agents; the lesson says nothing beyond that about which agents are required. Verify against the Esri docs for your version.

### 2.3 The snap chip

The **snap chip** appears near the pointer when you click where several features share the same x,y. It opens a **Snap To** window so you pick exactly which coincident feature (and, for a device, which terminal) to snap to. Steps (Esri): turn on Snapping, enable the agents you need, turn on **Enable Snap Chip** from the Snapping control on the status bar or the Edit tab, choose a template and start sketching, click the coincident location, open the chip, select the target row (a circle flashes), then apply by **Apply**, double-click or Enter; **Discard** or Esc snaps to the default feature. Hold the **Spacebar** to bypass snapping for a click. It is not available in 3D scenes. Esri's example is a power line snapped to the source or the load terminal of a device.

### 2.4 Midspan connectivity

- A junction-edge rule plus an edge connectivity policy of **Any vertex** (see `learn/04` section 8, set with `Set Edge Connectivity`) permits a point on a line's interior. If a midspan connection is permitted, Pro adds a vertex to the coincident line. If a line is drawn across another and midspan is permitted, vertices are added at each intersection and wherever an endpoint touches the other line. Neither case splits the line.
- If the midspan connection is not permitted, Esri says the features are still created but not connected. There is no hard block at sketch time; the evidence comes later, at validate, as an error (for example error 13 for a midspan point on an End-vertex line, `learn/04` section 8).
- Midspan is not supported for edge-junction-edge connectivity.
- Midspan connection to a device with terminals is limited (network rules page): split the line or use an intermediate non-terminal device. A multi-terminal device placed midspan gives error 38.
- Practitioner guidance: when in doubt, use the **Split** tool on the main line and connect to the new end vertices. It creates a system junction at the split and the device then connects at an end.

### 2.5 Junction-edge-junction chains in practice

A common run is `[Device A] --line-- [Junction] --line-- [Device B]`. Each line end touches a point, so each end is a junction-edge case. If the middle junction sits between two lines, the rule that decides it is junction-edge for each line-end first, and edge-junction-edge only if no junction-edge rule applies. Add a rule for the exact asset types, and add the terminal if the device has terminals (section 3).

### 2.6 Connecting when features are not coincident

Use a connectivity association (section 6): junction-junction (offset points, terminals allowed), junction-edge From/To or midspan for nonspatial edge objects. Esri's geometric coincidence page: to break a connection, move one feature beyond the coincidence tolerance and revalidate; moving them together with the **Move** tool keeps them connected.

## 3. Terminals while editing

**Definition.** A terminal is a logical port on a device or junction object (`learn/02` section 6). It is invisible on the map. A line that ends on a device with terminals needs to say which one it uses.

**Mechanism.** The line's `FROMDEVICETERMINAL` and `TODEVICETERMINAL` fields store the terminal id. "From" and "To" mean the first and last vertex of the line, not the direction of flow (Esri, Modify Terminal Connections page).

| Situation | What happens | What the editor does |
|---|---|---|
| Device has no terminal configuration (Single Terminal) | Nothing to choose | Snap and validate |
| Several terminals, exactly one junction-edge rule applies to the line | Validate fills in the line terminal automatically (Esri) | Validate |
| Several terminals, more than one rule applies | Terminal is ambiguous; error 9 at validate | Choose a terminal (below) |
| Terminal id on the line invalid or missing for the device | Error 36 | Reselect through the pane |
| Current path of a 3 or 4 terminal device is wrong | Error 39 for invalid path; or a path you need changed | **Modify Terminal Paths** |

**Choosing the terminal while editing (two supported tools).**

1. **Snap chip** while sketching the line (section 2.3).
2. **Modify Terminal Connections** pane (Utility Network tab > Network Topology > **Terminal Connections**), Esri steps: with the **Select a line feature** tool active click the line (or use **Change line selection**); the pane lists the line and coincident devices, with an asterisk on devices that need a terminal; pick from the **Terminal** drop-down (only terminals with a valid rule are shown); click **Apply**. To change or remove, load the line, change the drop-down or click **Delete** beside the device (shown struck through), then **Apply**. Requirements: line from the `Line` class, device from the `Device` class, device point coincident with a line endpoint, asset type with a terminal configuration, and at least one matching junction-edge rule. Afterwards validate, and update the subnetwork if the feature is in one.

Esri recommends these tools over typing the From/To terminal attributes by hand, because the attribute editor lacks the logic. If the terminal you want is missing from the drop-down, there is no rule for that pairing (Esri implies this; the fix is a rule, `learn/04`).

**Terminal paths (3 or 4 terminal devices).** New features take the default path of the terminal configuration. **Modify Terminal Paths** (Network Topology group > **Terminal Paths**) changes it: load the feature with **Add features** or **Load selected**, pick the **Active Item** if several, choose from the **Path** drop-down, **Apply**, then validate. Features with other terminal counts are skipped. The current path is held in the `TERMINALCONFIGURATION` field (`learn/02`).

**Terminals on non-coincident links.** For junction objects and junction-junction associations, the terminal is chosen in the **Modify Associations** pane (the **Terminal** drop-down on the **Connectivity** tab, and per-row terminal in the **Junction - Junction** section). Connections to the chosen terminal display in black and other terminals in lighter gray (Esri).

**Terminal configurations are not editable in the editing session.** They are set before first enable (`learn/02`). Editing only assigns terminals and paths.

Example (gas). A regulator has three terminals (inlet, outlet, bypass). The inbound main snaps to the regulator; two rules apply, so the editor picks "inlet" in Modify Terminal Connections. Without that choice, validate reports error 9.

## 4. What is enforced at edit time versus validate time

This is the single most useful table for explaining editing behaviour to a user.

| Check | When it runs | What the editor sees | Source |
|---|---|---|---|
| Snapping to a feature that has a connectivity rule | While sketching | Cursor snaps only where a rule allows; **T** shows targets | Esri editing reference, Esri Learn |
| Midspan permitted or not | Creation | Permitted: vertex added to line. Not permitted: features created, not connected | Esri editing reference |
| Containment or structural attachment rule | When you try to create the association | Pane does not add the feature, or the tool returns an error; Import Associations fails | Esri network rules and associations pages |
| Association role and feature restrictions | Same moment | Same as above (role missing means the feature cannot take part) | Esri associations page |
| Connectivity rule, restriction, midspan policy, terminal validity, asset group or asset type validity, tolerance, geometry validity | **Validate** or **Enable** | Error dirty areas, error rows in the Error Inspector, features left disconnected | Esri dirty areas and network rules pages |
| Network attribute value edits that exceed storage | Validate | Error 32 (inline weight overflow) | `pro-help/04` |
| Attribute rule: immediate calculation, constraint | On insert, update, delete (when the edit is applied) | The value is filled, or the edit fails with the rule's message | Esri attribute rules evaluation page |
| Attribute rule: batch calculation, validation rule | **Evaluate Rules** (Error Inspector or tool) | Values written, or error features created | same |
| Subnetwork tier validity (valid devices, lines, etc.) | **Update Subnetwork** | Subnetwork errors (bit 32) | `learn/03`, `learn/06` |

Esri's network rules page: rules are checked when topology is enabled or validated and when an association is created or imported; structural attachment and containment are also checked during the edit. The take-away, which `learn/04` section 4 already states: *connectivity rules are validate-time checks; association rules are edit-time checks.* An editor can sketch an illegal junction-edge connection without being stopped; the system tells them on **Validate**.

Pitfall: a user says "Pro let me connect it, so the rule must allow it." Not so: only snapping shows rule awareness, and a midspan or coincident placement that skips snapping (snapping off, or Spacebar held) is accepted silently.

## 5. Templates: feature, group, preset (and table)

Esri's editing-template-types page defines four kinds. All are managed in **Manage Templates** and used in **Create Features**.

| Type | Creates | Built from | UN-relevant notes |
|---|---|---|---|
| **Feature template** | One feature on one target layer | The layer (default for every layer) | Carries target layer and default attribute values (asset group, asset type, other fields) |
| **Group template** | Several features across multiple layers in one action | A primary feature template plus secondary templates and builders | Optional **Associations** tab for UN features |
| **Preset template** | A predefined arrangement of existing features, placed as they were when captured | Features selected in the active map | Keeps associations authored with it (Esri editing reference) |
| **Table template** | One or more rows in a table | The table | Can be attached to a feature template so related rows (for example nonspatial objects) are created with each feature |

### 5.1 Feature templates and how asset group, asset type and attributes populate

A feature template belongs to one layer and stores field values. Because UN classes use a subtype (`ASSETGROUP`) and a domain keyed by it (`ASSETTYPE`), a template per asset group and asset type is the normal pattern. Pro generates a default template per subtype when a layer is added to a map; the Esri Learn lesson notes that the templates are pre-populated with default attributes per subtype, and that editing a template's defaults beforehand (the lesson adjusts a phase value) saves editing afterwards. The geodatabase default value on a field is applied if the template does not override it.

Practitioner guidance: set a template's defaults for the fields that are the same for every feature of that type (lifecycle status, owner) and let attribute rules fill the rest (asset id sequences, derived values, section 8). Do not store network-significant defaults in templates if attribute rules should be authoritative: a template edit is local to the Pro project, a rule is in the database.

**Where templates live.** In the Pro project (the map's layer definition) and can be shared as layer files or project templates. They are not stored in the UN dataset. The Foundation asset packages and Esri's Solutions provide templates in their maps; verify which per Foundation (`pro-help/08-asset-packages-foundations-migration.md`).

**Containment tab.** In **Template Properties**, a **Containment** tab appears only when the layer takes part in a containment association. Adding a containment template there makes each new feature create associated nonspatial objects too (Esri). It works like adding a table template on the **Relationship** side tab, and can replace manual use of **Add New To Container** in the Attributes pane.

### 5.2 Group templates

**Definition.** A template that creates several features across layers in one action: you sketch one primary feature and **builders** place secondary features relative to it. Esri's example is sketching a line and having a fitting and a valve added at its end.

**Mechanism.** A group template references existing feature templates; it inherits their target layer, attributes and embedded table templates. The primary template's geometry type and the chosen toolset decide which secondary templates and builders are available.

**Configure (Esri steps):**

1. Open **Manage Templates** (Edit tab > Manage Edits group, or from **Create Features**).
2. Expand **Map**, select the layer linked to the group template, select the group template.
3. Open **Properties** (toolbar, or right-click) to show **Template Properties**.
4. **Tools** tab: choose a toolset (Point, Line, Radial or Polygon, depending on primary geometry), set a default tool, and use the **Toggle tool visibility** check boxes. A point primary with a Line or Radial toolset draws temporary geometry that secondary builders use to place features.
5. **Builders** tab: **Add**, choose a feature template in **Choose a feature template**, choose a builder in **Choose a builder**, set its parameters; to change later hover the secondary template name and use **Edit** or **Delete**. **OK** saves.
6. **Associations** tab (appears only when the primary template creates a UN feature): tick **Add associations when creating new assets** and click **OK**.

The names of individual builders and their parameters are not enumerated on the Esri pages read for this file: Verify against the Esri docs for your version.

**What it can create at once.** Features in several layers (devices, lines, junctions, structure points) and their field values from the referenced templates; table rows through embedded table templates; associations between the group's own features when the **Associations** option is ticked. Esri's example from the editing reference is a line group with an attachment as the snapping device.

**Limits (Esri, Practitioner guidance where marked):**

- The association setting applies only to features the group template creates. It does not extend to the contents of preset templates assigned to the group.
- Which association types are created (containment, structural attachment, connectivity) and between which features is determined by the group's design and the rules; Esri's pages read do not give a list: Verify against the Esri docs for your version.
- Associations are still rule-checked. If a rule or role is missing, an association will not be created even though the features are (Practitioner guidance, consistent with section 6).
- Geometry-dependent builders cannot place a feature where snapping rules reject it; the features are still created, so check coincidence afterwards (Practitioner guidance).
- Group templates reference feature templates; if the referenced template is deleted or its layer changes the group breaks (Practitioner guidance).
- The group does not run validate. A group edit leaves multiple dirty areas.

Example (electric, small). A pole group template: primary template creates the pole (structure junction), a secondary creates a transformer device placed by a builder on the pole, a service point. With **Add associations when creating new assets** ticked, the transformer is attached to the pole by structural attachment association if a rule and a Structure role on the pole asset type allow it.

### 5.3 Preset templates

**Definition.** A preset template is a template made from features you already selected on the map, stored as an arrangement. Using it places a copy of that arrangement. Esri's description of the tool: a template that "creates a preset template from the selected features in the current map".

**Create (Esri steps):** Edit tab > Manage Edits group > **Manage Templates** (or from Create Features). Use the **Select** tool in the Selection group to select the features arranged as wanted. In **Manage Templates** click a layer that contains one of the features, then the template view toolbar **New > Preset Template from selected features**. In **Template Properties**, **General** tab: required **Name**, optional **Description** and **Tags** (Pro adds *Group* and *Preset* tags automatically). Check the **Preview** tab, click **OK**.

**Configure (Esri):** **General**, **Tools** (point construction tools; point with rotation uses a secondary anchor), **Features** (list of features, per-feature attribute values, ability to remove features; raster, attachment and BLOB fields are not supported), **Preview** (primary insertion anchor at the centre of the selection's envelope by default, movable; secondary anchor placed by hovering and pressing **S**; **Reset** restores defaults). The preset's symbol is assigned by Pro and cannot be changed.

**What preset templates add for a UN.** Esri's UN editing reference says preset templates "keep the associations defined when they were authored", whether used alone or as components of a group template. Its example is a transformer bank preset whose components keep their authored associations. In practical terms (read as stated, and Practitioner guidance for the consequences):

| Preset behaviour | Basis |
|---|---|
| Places several features in one click, in the arrangement captured | Esri template types page |
| Attribute values for each feature are editable in the Features tab | Esri configure-a-preset page |
| Associations that existed when authored are created for the placed copies | Esri UN editing reference |
| Which association types are kept (containment, structural attachment, connectivity) and exactly how connectivity by coincidence is re-established | Not enumerated in the Esri pages read here: Verify against the Esri docs for your version |
| Insertion snaps to existing features using the current snap settings | Esri preset pages |

**Limits and practitioner cautions:**

- Rules still apply: an association is created only if a rule and, for containment and attachment, an association role exist (section 6). A preset authored in a network whose rules later changed can fail to recreate associations.
- Preset content is a snapshot. If the network model changes (new asset types, rule changes, terminal configurations) author a new preset.
- Because placement happens at the snapped location with the snap rules, a preset can create connected features at a connection point that must still be validated. Always validate after placing.
- Preset templates do not appear to be portable across networks with different asset group and type codes: they store layers and values. Re-author per dataset (Practitioner guidance).
- Whether a preset records connectivity associations of non-coincident (junction-junction) features, and whether it records terminal ids on lines: Verify against the Esri docs for your version.

### 5.4 Choosing among them

| Need | Use |
|---|---|
| One valve on a main | Feature template |
| A pole plus transformer plus service point drawn from a single sketch, with options | Group template |
| A repeatable standard assembly (substation bay, meter set) with fixed geometry | Preset template |
| Nonspatial objects (cable strands, ports) created with each feature | Containment tab / table template on the feature template |
| Associations created by data logic, not by the editor | Attribute rules (section 8) or Import Associations (`pro-help/04`) |

## 6. Creating, viewing and deleting associations

### 6.1 What the rules and roles must say first

| Association | Needs |
|---|---|
| Connectivity (junction-junction, junction-edge From/To/midspan) | Network topology enabled (Esri create-connectivity page) and a connectivity rule that supports the pair |
| Containment | A containment rule, and the container asset type holds the **Container** association role |
| Structural attachment | A structural attachment rule, and the structure holds the **Structure** role |

Esri's associations page adds: containers can be any network class in structure and domain networks; structures are limited to the structure junction and structure junction object classes; feature restrictions must be honoured (`learn/02` section 7.3). Roles are set with `Set Association Role` before first topology enable (`pro-help/04`). Rules are in **Network Properties**.

A structure cannot be attached to a line or an edge directly: place a point or junction at midspan and attach to that (Esri structural attachment page).

### 6.2 Modify Associations pane: the working surface

Open: Utility Network tab > Associations group > **Modify**. Esri pane anatomy:

- **Add features** (map click) and **Load selected** (use attribute-table rows, needed for junction and edge objects). Both exist at pane level and inside each section (as **Add selected** in some sections).
- **Active Item** drop-down chooses the feature the pane works on.
- Tabs **Connectivity**, **Containment**, **Attachment**, each with a count; tabs can be hidden depending on the active item.
- Menu: **Remove All Associations**, **Remove Connectivity Associations**, **Remove Containment Associations**, **Remove Attachment Associations**, **Select All Associated Records**, **Expand All**, **Collapse All**, **Refresh**, **Clear**.
- New associations show a green indicator before **Apply**. Deletions are only marked; **Refresh** reverts anything not applied.
- After **Apply**, validate (Esri says this on each creation page) so the topology absorbs the association. Update the subnetwork if the feature belongs to one.

### 6.3 Create a connectivity association

Esri steps (Pro create-connectivity page):

- **Junction to junction.** Load the starting feature (**Add features**, or **Load selected**) as Active Item; open the **Connectivity** tab; pick a **Terminal** if it has terminals; in the **Junction - Junction** section add the other features and set their terminals; **Apply**; validate.
- **Junction to edge.** Load the edge (Active Item) from its attribute table with **Load selected**; in the **Junction - Edge** section use **Add selected** for the junctions; set terminals; **Apply**; validate. In telecom networks the grouped edge shows **First Unit** and **Last Unit**; a grouped edge can hold only one From and one To association, and splitting requires `divideGroupedObjects` in an `applyEdits` call (Esri).
- **Junction to edge midspan.** Load the edge; use the **Junction - Edge Midspan** section; enter **% Along** (decimal 0.0 to 1.0, since the edge is nonspatial); **Apply**; validate.
- Python: `AddConnectivityAssociation` in the `arcpy.un` UtilityNetwork class inside an edit operation (`arcpy/01-utility-network-module.md`).

Example (water). A service lateral modelled as an edge object between a tap and a meter: two rows, From at the tap and To at the meter, so direction exists.

### 6.4 Create a containment association

Three ways (Esri create-containment page):

1. **Modify** pane > **Containment** tab: load the container, use the **Contains** section (or **Contained In** if the active item is the content), add features, set **Visibility** (checked: content visible on the map; unchecked is the default), **Apply**, validate.
2. **Enter Containment** (Associations group): with a container selected, features you then create become content automatically (if a rule allows). **Exit Containment** to stop. See `learn/02` section 8.1 for deletion semantics and split policy.
3. Python: `AddContainmentAssociation` in an edit operation.

The **Visibility** setting is only effective with the **Display Content** command, which needs a display filter configured on `ASSOCIATIONSTATUS` (`learn/13` section 5).

### 6.5 Create a structural attachment association

Modify pane > **Attachment** tab: load the structure (for example a pole, with **Add features**; **Load selected** for nonspatial objects), use **Attachments** (active item is the structure) or **Attached To** (active item is the attachment), add features, confirm green indicators, **Apply**, validate. If no rule supports the pair, the feature you click will not be added to the pane (Esri). Through Python: `AddStructuralAttachmentAssociation` (see `arcpy/01`).

### 6.6 View, select and delete

| Task | How (Esri) |
|---|---|
| See associations on the map | **View** (View Associations Mode) draws connectivity and attachment lines in the extent (Esri Learn: dashed lines; connectivity brown, structural attachment green); network diagrams; **Display Content**; trace with **Synthesize Geometries** |
| See what is below a feature | **Attributes** pane tree; each association branch shows a count |
| Select associated features | Attributes pane right-click > **Select Associated Data** with **All**, **Connectivity**, **Contained In**, **Contains**, **Attached To**, **Attachments**; right-click a layer to apply to all selected features in it |
| Delete | **Modify** pane menu **Remove ...** items or per-row delete, then **Apply**; **Remove Association** in the Attributes pane for a nonspatial object in a container |
| What happens when a container or structure is deleted | Per the **deletion semantics** set with the role: Cascade deletes contents, Set to none keeps them and removes the association, Restricted blocks the delete (`pro-help/04`) |

Deleting an association means the topology only forgets the link after the next validate; until then traces still use the old link.

### 6.7 What the rules say about allowed combinations

- Each association type has its own rule type (junction-junction connectivity, junction-edge connectivity, edge-junction-edge, containment, structural attachment; `learn/04` section 2).
- A rule keys on asset group and asset type for both sides (plus terminal for the two connectivity types). The tables of legal classes (feature restrictions) sit under rules and cannot be changed (`learn/02` section 7.3).
- Containment and attachment rules do not support terminals (Esri).
- Deleting a rule does not remove existing associations, but dependent features get errors at the next validate, and coincident connections become disconnected (Esri network rules).

## 7. Testing a network rule

**Goal.** Before telling a user a connection is allowed or blocked, prove it on a safe copy. Esri does not publish a single "test rule" button, so this is a method (Practitioner guidance), built from Esri-documented behaviours.

**Method.**

1. **Read the rule set.** Right-click the network in Contents > **Properties** > **Network Properties** tab. Find the rule type (junction-edge, junction-junction, containment, structural attachment, edge-junction-edge), the From and To asset group and type, and terminal if any. Remember junction-edge beats edge-junction-edge.
2. **Work in a throwaway branch version** (or a copy of the network), never in DEFAULT. Note: rules are changed only on DEFAULT with topology disabled (Esri), so *testing a candidate rule* means a copy, not a version (see step 7).
3. **Create the two features with exactly the asset group and type** (and the terminal configuration) in question, using the real templates.
4. **Predict from snapping.** Hover with a template active and press **T**. If the target does not appear as a snap target, the rule is missing (or snapping is off for that layer). Snapping is a hint, not proof.
5. **For association types** open **Modify Associations** and try to add the pair. A containment or attachment pair with no supporting rule does not appear in the pane; a connectivity association request is rejected (Esri).
6. **Validate** (Current extent). Read **Error Inspector** or the **Dirty Areas** table. The outcome:

| Result | Reading |
|---|---|
| Dirty area cleared, no error | Allowed (and, for coincidence, now connected) |
| Error 8 | No rule supports the connection |
| Error 9 | More than one rule matches (ambiguous, often a terminal choice or a broad All-terminals rule) |
| Error 10 | Lines of different asset type meet with no edge-junction-edge rule |
| Error 13 / 38 | Midspan not permitted by policy, or multi-terminal device midspan |
| Error 34 / 35 / 17 / 18 | Containment or attachment not supported |
| Error 36 / 39 | Terminal or path problem |

7. **Confirm with a trace** from the new feature (connected trace). Passing means the topology really connected it.
8. **If the connection is blocked, the fix is in the rules** (Add Rule, topology disabled, Default version, service stopped, then restart; named versions get the change after reconcile, Esri). Worked example: `learn/11-worked-examples-end-to-end.md` section 6.
9. **Discard** the test edits (delete the version, or Discard in Pro).

**How the error presents.** Error dirty area polygons around the offending features; an `Error(s)` text in the Error Inspector like "8: ..." (the Error Inspector does not show `Status` or `Error code`; read those from the Dirty Areas table, Esri); error-only `Status` of 8 or 16 that Validate will not clear (`learn/03`). Fix by editing the feature or the rules, then validate again.

Pitfall: testing in DEFAULT. A scratch feature left in the shared version leaves dirty areas and errors for everyone.

## 8. Data integrity while editing

### 8.1 Dirty areas

Esri (dirty areas page): edit dirty areas appear for inserted, updated or deleted features, changed associations and terminal configuration; editing geometry, asset group or asset type fields, network attribute fields, associations or terminals creates them, and a geometry change creates two (old footprint and new). Error dirty areas arise at enable, validate and Update Subnetwork. Non-network attribute edits do not create one (`learn/08` section 10). They are cleared when validate processes them with no errors in the extent. If a topology is disabled one dirty area covers the whole territory. The sublayer is toggleable; areas are created even when it is hidden. Symbolise by `Status`, or by editor tracking fields to see who made the edit, and read `Status Description` in the pop-up.

`Status` is a bit flag (1 inserted/updated, 2 deleted, 4 associated objects modified, 8 feature error, 16 object error, 32 subnetwork error; sums are possible, `learn/03`). One wording point: Esri's dirty areas page says validate processes areas with an edit bit but writes the edit values as "0, 1, or 2", while `pro-help/04` and `learn/03` use 1, 2 and 4. If you must rely on the bit set, read the page for your version and use `scripts/decode_dirty_status.py` (Verify against the Esri docs for your version).

### 8.2 Validate extent choices

| Option (Utility Network tab > Validate drop-down) | Use |
|---|---|
| **Current extent** (default) | Normal editing; clips dirty areas to the view. Dirty areas outside the view stay dirty |
| **Entire extent** | End of session, before reconcile or post, or after bulk loads |
| **Rebuild current extent** | Only if validate fails; ignores dirty areas and rebuilds everything in the extent |

The **Validate** command runs synchronously. The `Validate Network Topology` geoprocessing tool (Extent parameter, among Esri's extent options: current display extent, draw extent, layer extent, clipboard, manual coordinates) runs asynchronously through the `UtilityNetworkTools` service, enterprise input must be a UN service, and requires the Advanced Editing user type extension; only one session may validate DEFAULT at a time while the network stays editable. If a validate fails use `Rebuild Network Topology` (Esri). Practitioner guidance: zoom so that the whole work area is in view, validate current extent, then check the Dirty Areas layer for any grey remnants outside; finish with **Entire extent** for large edits.

### 8.3 Editing in versions

Edit in your own branch version, not DEFAULT (`learn/08` sections 1 and 10, `learn/13` section 3.1): create it in the **Versioning** tab, choose **Change to this new version**. Dirty areas live in the version; reconcile re-creates inherited ones, and Esri says inherited dirty areas must be validated before posting. Associations and rules follow the same rules. Rule changes are made on DEFAULT and a named version only sees them after reconcile. Save frequently (**Save** in Manage Edits) so the version, not the session, holds the work.

### 8.4 Attribute rules in the editing flow

Attribute rules are geodatabase logic, separate from network rules (`learn/05` section 9 and 10).

| Kind | When | What the editor sees |
|---|---|---|
| Immediate calculation | On insert, update or delete | Field filled automatically (calculation rules run first, defaults before them) |
| Constraint | Same moment, after calculation | The edit fails with the rule's error message |
| Batch calculation | **Evaluate Rules** | Values written on flagged features |
| Validation | **Evaluate Rules** | Error features in the Point, Line, Polygon, Object Error datasets (**Add Error Layers**), shown in the **Error Inspector** |

Esri notes **Exclude from application evaluation** (off by default) decides whether Pro evaluates an immediate rule locally before sending the edit; some immediate calculation rules must be set to exclude (certain dictionary keywords, sequences, using the field's own value). A validation status field tracks which features still need evaluation. Foundation templates rely on rules for asset ids and for creating associations on placement (`learn/05` section 13). Validate Network Topology does not evaluate attribute rules (`learn/05`); run both. Batch evaluation of web feature layers needs the Advanced Editing extension on Enterprise 11.2 or later (Esri). Whether the Evaluate Rules tool covers a named version: Esri's tool page says default only (`learn/08` section 7).

### 8.5 A daily integrity loop (Practitioner guidance)

1. Create in the right template, snapping on, correct asset group and type.
2. Create associations as needed (section 6).
3. **Validate** current extent; read errors in the **Error Inspector**.
4. Fix, validate again until the Dirty Areas layer is clean in your area.
5. **Evaluate Rules** (batch/validation) for the area.
6. Save. Update subnetwork where needed.
7. Run a quick trace as a business test, then hand over to the version reviewer.

## 9. Editing mistakes and the fix

| Mistake | Symptom | Fix |
|---|---|---|
| Wrong asset type chosen | Error 8, 9 or 10 at validate; wrong symbol | Change `ASSETTYPE` (and `ASSETGROUP`) in Attributes; this is a network edit that makes a dirty area; validate. Do not change a controller's asset group or type casually: error 33 on update subnetwork |
| Placed with snapping off | Features look connected, not connected after validate, or not in traces | Delete the endpoint and re-snap, or use **Edit Vertices** with snapping; move a vertex onto the target with snapping |
| Connected to the wrong terminal | Trace goes through the wrong side; error 9 or 36 | **Modify Terminal Connections**: select terminal, **Apply**, validate |
| Wrong terminal path | Trace stops inside a multi-path device | **Modify Terminal Paths** |
| Midspan point on End-vertex line | Error 13 | Split the line and attach to the end, or set policy to Any vertex (rule change, owner, topology disabled) |
| Multi-terminal device placed midspan | Error 38 | Split the line at the device |
| Association created in the wrong direction (container/content swapped) | Error 34/35/17/18 or missing contents | **Modify** pane: **Remove** the association, **Apply**; re-create from the correct side |
| Deleted a container and lost contents | Cascade semantics | Undo in the session before Save; otherwise restore from the version or reconcile. For future, review deletion semantics (`pro-help/04`) |
| Moved a device and its lines followed (or did not) | Lines stretched, or disconnected | Use the **Disconnect** toggle deliberately; **Move** keeps connected assets with it |
| Line duplicated (two features, same geometry) | Error 25 stacked points, or ambiguity | Delete one; validate |
| Multipart or self-intersecting line | Errors 19 and 20 | Explode or edit vertices to simplify |
| Short or duplicate-vertex line | Errors 5 and 21 | Remove duplicate vertices (Edit Vertices), lengthen the line |
| Validate says success, errors persist | Rows with Status 8, 16 or 32 | Edit the feature to fix the cause (`learn/03` section 8); validate again |
| Edit saved but trace shows old network | Dirty areas not validated | Validate; check you are in the right version and extent |
| Edit in DEFAULT by mistake | Dirty areas for everyone | Tell the administrator; do not try to post/delete without reviewing the version; treat as an incident (`learn/08` section 18) |
| Imported associations failed | Import Associations stops on missing rule | Add the rule first (`pro-help/04`) |
| Hand-edited `FROMDEVICETERMINAL` | Wrong or invalid terminals | Reassign with the pane; avoid attribute edits |
| Tried to delete an association by deleting a record in a table | Esri documents the pane, ArcPy and REST paths, not table edits | Use the **Modify Associations** pane or the ArcPy or REST delete operations (`learn/02` section 10.2) |

Undo: Pro's **Undo** and **Discard** apply to the current edit session; once **Save**d, the correction is a new edit. In a branch version a faulty version can be deleted if it has not been posted (`learn/08`).

## 10. Pro editing tools that respect network topology

From Esri's editing reference; network topology does not take part in map topology.

| Tool | Behaviour for a UN |
|---|---|
| **Stretch Topology** (toggle) | Keeps shape by scaling segment lengths when you move an edge or vertex |
| **Disconnect** (toggle) | Removes moved features from network topology: prevents connected assets from moving |
| **Move** | Moves the feature plus coincident features, container contents and structural attachments; lines stretch to stay connected if midspan is permitted |
| **Move To** | Moves to a coordinate or by offset distance/direction |
| **Continue** | Extends a line; connected features move to the new endpoint by default |
| **Edit Vertices** | Edits vertices and other network features at that location with a rubber band line |
| **Replace Geometry** | Replaces geometry, keeps attributes |
| **Split** | Splits a line into connected parts joined by a system junction; constrained asset types follow the domain split policy; container contents follow the containment split policy of structure line classes (`learn/02` section 8.1) |

Selection filtering: editing tools filter the selection by the edit they do; a brief notice names the tool; press **Esc** or the back arrow in **Modify Features** to restore the full selection. Deactivate the tool before selecting nonspatial objects in a UN attribute table (Esri).

## Common misconceptions

- "The pole symbol shows on the map, so it is in the network." It is in the network only after validate.
- "Snapping to it means connected." Snapping is a guide. Connection is decided at validate.
- "Group templates always create associations." Only when **Add associations when creating new assets** is ticked, only between the group's own features, and only when rules and roles exist.
- "Preset templates are just copies of geometry." Per Esri they keep authored associations; but rule and role checks still apply.
- "Validate fixes errors." Validate re-evaluates edit dirty areas; error-only dirty areas need an edit.
- "Deleting a record in the Associations table is how you remove an association." Use the pane, ArcPy or REST.
- "Editing the From/To terminal fields is fine." Esri recommends the pane or snap chip.
- "Tolerance does the connecting." Tolerance decides coincidence; rules decide permission.

## Quick checks

1. Which version is the user editing in, and is it a named branch version or DEFAULT?
2. Is the template for the right asset group and asset type? Does the new feature show the intended values in the **Attributes** pane?
3. Is snapping on, and does pressing **T** show the target? If not, is there a rule in **Network Properties**?
4. Did the user validate (and for what extent)? What does the **Dirty Areas** layer show, and what are the `Status` values?
5. For a device with terminals: which terminal does the line use? Was it chosen by pane or snap chip?
6. For associations: is the container or structure role assigned? Is there a containment or attachment rule? Was it applied (not just marked) and then validated?
7. Was a group template's **Associations** tab ticked? Were the secondary templates still valid?
8. Are attribute rules involved? Immediate or batch? Was **Evaluate Rules** run?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`, `learn/03-topology-engine-and-validation.md`, `learn/04-rules-and-connectivity-design.md`
- `learn/05-attributes-categories-and-attribute-rules.md`, `learn/08-versioning-and-editing-workflows.md`, `learn/09-failure-anatomy-symptom-to-fix.md`
- `learn/11-worked-examples-end-to-end.md`, `learn/13-arcgis-pro-fundamentals-and-workflow.md`
- `pro-help/04-associations-editing-errors.md`, `pro-help/03-creation-configuration-attributes-categories-rules.md`
- `arcpy/01-utility-network-module.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/editing/utility-network-reference-for-editing.html
- https://pro.arcgis.com/en/pro-app/3.6/help/editing/utility-network-reference-for-editing.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/editing/configure-a-group-template.html
- https://doc.esri.com/en/arcgis-pro/3.7/help/editing/create-a-preset-template.html
- https://pro.arcgis.com/en/pro-app/3.4/help/editing/configure-a-preset-template.htm
- https://pro.arcgis.com/en/pro-app/3.5/help/editing/editing-template-types.htm
- https://pro.arcgis.com/en/pro-app/3.6/help/editing/use-the-snap-chip.htm
- https://pro.arcgis.com/en/pro-app/3.4/help/data/utility-network/modify-terminal-connections.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/modify-terminal-paths.html
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/associations.htm
- https://pro.arcgis.com/en/pro-app/3.6/help/data/utility-network/create-connectivity.htm
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/create-containment-association.htm
- https://pro.arcgis.com/en/pro-app/3.1/help/data/utility-network/create-structural-attachment-association.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/geometric-concident-based-connectivity.html
- https://pro.arcgis.com/en/pro-app/3.6/help/data/utility-network/network-rules.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-tab.html
- https://pro.arcgis.com/en/pro-app/3.4/help/data/utility-network/dirty-areas-in-a-utility-network.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/evaluate-attribute-rules.html
- https://learn.arcgis.com/en/projects/manage-utility-data-using-arcgis-utility-network/
- https://sspinnovations.com/blog/esri-utility-network-editing-associations-connectivity-attachments-containment/ (practitioner blog from the beta period; used only for pitfalls)
