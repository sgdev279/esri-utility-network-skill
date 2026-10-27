# Utility Network: Network Diagrams in Depth (Data Model, Templates, Rules, Life Cycle, Enterprise Service)
*Sources: Esri Pro 3.7 help "Network diagrams" book, Network Diagram toolbox reference and the Network Diagram service REST page (URLs in Sources below). Last reviewed: 2026-10-27.*

> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

**Why this matters / when to read this.** A network diagram is the one UN deliverable that is neither a map nor a trace result: a schematic, generated from the network topology and stored (or not) in the database. People ask for "a diagram of this feeder / pressure zone / pipe run" and get confused about why it goes stale, why it is empty, why containers vanish, why a template edit breaks every diagram, or why the web app cannot draw one.
Read this when someone asks how to generate, store, update or lay out a diagram, which template to use, how to administer templates, or what the diagram REST service can do.
It is domain-neutral. The brief reference is `pro-help/07-network-diagrams.md`; this file goes deeper and links to it, never replaces it. Vocabulary for the whole skill is in `learn/12-glossary-and-concept-map.md`.

## Contents

1. What a network diagram is (and is not)
2. The diagram data model
3. The template catalogue (Basic, ExpandContainers, CollapseContainers, custom)
4. The Pro life cycle: generate, store, find, open, update, append, extend, overwrite, delete
5. Editing a diagram: layouts, reshaping, and what is not synchronized back
6. Administration: template tools, owner and license rules, the rule list
7. Enterprise: NetworkDiagramServer, publishing, web apps
8. Performance limits and cautions
9. Common problems and fixes
10. Quick chooser: which diagram for which question

Esri labels are quoted from the Pro 3.7 help. Where a page gave a dialog label but not a Python parameter name, this file gives only the label; do not invent keyword names, check the tool's Python tab in your release. Facts labelled Practitioner guidance are not from Esri pages.

---

## 1. What a network diagram is (and is not)

**Definition (Esri).** A network diagram is a representation of a set of utility network (or trace network) features and objects, built from three element types (junctions, edges, containers) and generated from a **diagram template**. It is normally shown in a **diagram map** through a **diagram layer**.

**Mechanism.** The diagram does not draw the network features. It builds a separate graph from the *topology* (`learn/03-topology-engine-and-validation.md`), runs the template's rules over it, and stores the result as diagram features that point back at network features. Geometry on a diagram is schematic: it is computed by rules and layouts, not copied from the shape of the network feature (unless a template asks for that).

```
 geographic map (feature geometry)        diagram map (schematic geometry)
 -------------------------------          -------------------------------
 Transformer (point)  ---------------->   Diagram junction  (point symbol)
 Line (polyline)      ---------------->   Diagram edge      (line, usually straight)
 Vault / cabinet      (container)  --->   Diagram container (polygon around contents)
 Containment, connectivity, attachment    optional edges drawn by rules
 associations (no geometry)  ---------->  (only if the template has the rule)
```

### 1.1 Diagram vs map vs trace result

| Question | Map | Trace result | Network diagram |
|---|---|---|---|
| What does it show? | Real geometry of features | A set of element IDs/features (selection, graphics, result types) | A schematic graph, laid out for reading |
| Where is it stored? | Feature classes | Nowhere by default (selection or graphics; `learn/07`) | Diagram tables, temporary or stored |
| Is it live? | Yes (edits show at once) | A snapshot of one run | A snapshot; goes inconsistent as the network changes |
| Does it need topology? | No | Yes (validated topology) | Yes (topology enabled, no dirty areas on its inputs) |
| Is geometry meaningful? | Yes | n/a | No, positions are layout choices |
| Can it be edited back into the network? | Yes | No | No (section 5) |

A trace result can be the *input* to a diagram (select the traced features, then generate), and a diagram template can run a trace itself through the **Trace rule** (section 6.3). They are still different artefacts: the trace result is a list; the diagram is a schematic that you can lay out, store and share.

### 1.2 Why it exists

Real geometry is wrong for some jobs: a substation, valve chamber, cabinet or manhole interior has dense equipment in one point; a feeder, pressure zone or fibre route is long and thin; a connectivity check is easier as a tree. Diagrams let an analyst:

- read connectivity as a tree or loop structure (feeder one-line, pipe run, splice view);
- open the inside of containers, or collapse them to one symbol;
- keep a stable, hand-tuned layout for a subnetwork (system diagrams, section 4.8);
- check "is this really connected" without trusting geographic proximity.

Example (electric, illustrative): select a transformer and everything downstream, generate with a tree template, and the diagram shows the radial structure that the map hides under street geometry. The same shape applies to a gas regulator run or a water main with isolation valves.

---

## 2. The diagram data model

### 2.1 Building blocks

| Term | Definition (Esri vocabulary) | Detail |
|---|---|---|
| **Diagram template** | Base configuration for generating a diagram: rule and layout definitions (content) plus a diagram layer definition (presentation) | Owned by the network owner; one network holds many templates |
| **Diagram rule** | A task that runs during build or update to turn initial content into final content | Run in entry order; each works on the previous output |
| **Diagram layout** | Algorithm that clarifies and spaces diagram features | Run on demand, or automatically when listed on the template |
| **Diagram layer** | Composite layer that joins diagram feature classes with their source classes or object tables | Shown in a **diagram map** |
| **Diagram layer definition** | Template-level display settings (appearance, labels, queries) for the layers in a diagram layer | Stored as `.ndld`; may be shared among templates |
| **Rule and layout definitions** | The ordered rule/layout list of a template | Stored as `.ndbd`; exportable |
| **Diagram features** | Diagram junctions, edges, containers | See 2.2 |
| **Diagram graph / top graph** | The graph the builder maintains while rules run; the *top graph* treats each container as one junction | "Preserve container layout" on layouts works on the top graph |
| **Consistency** | Whether the diagram matches the network (section 2.5) | Field plus icons |
| **System diagram** | Diagram of a subnetwork maintained by Update Subnetwork | Section 4.8 |

### 2.2 The three diagram feature types

| Diagram feature | Geometry | Represents |
|---|---|---|
| **Diagram junction** | Point | Point feature, junction object, system junction, a reduced edge, or a collapsed polygon feature |
| **Diagram edge** | Line | Line feature, edge object, junction-junction connectivity association, a structural attachment not shown on the network map, or a reduction edge |
| **Diagram container** | Polygon | A point junction or junction object that holds other elements, or a polygon structure boundary; computed to fit around its contents |

### 2.3 Diagram feature to network feature relationship

Each diagram feature carries a link to the network feature or object it stands for, and the diagram layer is a *join* of diagram classes to source classes (Esri). Consequences:

- Attributes you see on a diagram feature are the network feature's attributes, joined; they cannot be edited through the diagram (section 5.3).
- The relationship is not always one-to-one. A **reduction edge** or **collapsed junction** is one diagram feature standing for several network elements, called **aggregations**. A template can keep a record of them (**Persist aggregations**, section 2.6) so selection can find them again.
- System junctions (invisible on the map, `learn/02`) can appear as diagram junctions and connectivity-association edges can appear as diagram edges, which is why a diagram sometimes shows things you cannot see on the map.
- Default sublayers when All Layers mode is on: one layer per network source class or object table; System Junctions and System Junction Objects; Connectivity Associations; Structural Attachments; point layers for container polygons/lines/edge objects that become points (collapse, reduce); polygon layers for container points and container junction objects that become polygons (expand); Reduction Edges; telecom only (UN v8+, telecom domain present): Virtual Connectivity and Inferred Connectivity. From UN v6 association layers sit under an Associations subtype group layer.

### 2.4 Diagram storage

Esri-documented points:

- Diagrams live in the network's **diagram dataset** in the geodatabase. The REST service exposes it as the **Diagram Dataset** child resource (`rest-api/03-network-diagram-service.md`).
- The v8 `systemLayers` listing includes diagram layers (`diagramJunctionLayerId`, `diagramEdgeLayerId`, `diagramContainerLayerId`) and temporary ones (`temporaryDiagram*LayerId`); see the table in `learn/02-data-model-in-depth.md`. Table and field names inside the diagram dataset are not documented on the Esri pages reviewed 2026-10-27 (unverifiable); do not script against them.
- **Temporary diagram** (default): flagged by the database for discard when the last diagram map view closes; still sits in the temporary tables until **Purge Temporary Diagrams** runs. Esri's blog says unversioned temporary tables add little size but still need maintenance.
- **Stored diagram**: made with **Store Diagram**; reopened from **Find Diagrams**; carries a name, **access rights** (Public default, Protected, Private) and `#`-separated **tags**; can be edited, updated, extended only per the rules in section 4.
- Branch versioning: stored diagrams in a branch-versioned dataset add rows for every edit to a diagram feature (Esri blog). Diagram edits reconcile with the reconciled version winning on conflict (`learn/08-versioning-and-editing-workflows.md`).
- Time travel: against a historical moment you may generate temporary diagrams and open stored diagrams that existed then, but not edit or store them (Pro 3.7 workflow page).

### 2.5 Consistency states

A diagram's consistency depends on four things (Esri): network topology space (validated since the diagram was built?), network editing space (dirty areas touching its features?), template definition (changed?), and diagram layer state (sublayers matching content?).

| Icon (Contents pane) | State | Typical cause | Fix |
|---|---|---|---|
| **Red** | Inconsistent with the editing space | Dirty areas on network features or objects that feed the diagram, even if reduced/collapsed | Validate the topology over the diagram's features, which turns it orange, then update |
| **Orange** | May be inconsistent with topology or template | Validate over an intersecting extent; topology disabled; any template rule/layout/margin change; `.ndbd` import | Update Diagram (or Overwrite, Append, Extend) |
| **Gray** | Diagram layer state out of date | Sublayers missing or no longer needed after another user's update/extend/overwrite/append; bad layer definition | Update on the Network Diagram tab; if it persists, the template's layer definition needs admin review |
| none | Consistent | | |

Mechanics worth knowing:

- Priority of icons is red, then orange, then gray.
- The database has a `Consistency` field. It becomes true when a diagram is created, updated, appended, overwritten or extended; false on topology disable, validate over an intersecting extent, or template change. It is **not** updated by dirty-area creation or by layer-definition changes, which is why red and gray come from checks at open time instead.
- **Find Diagrams** shows only the stored value (orange for false, empty otherwise); red appears only when the diagram is opened.
- Temporary diagrams always open as consistent. The **Consistency** button on the Network Diagram tab forces a check of all open diagrams.
- Editing network features not used in the diagram leaves a consistent diagram consistent.
- Template change fix at scale (Esri): the network owner scripts Update Diagram on the altered template; in enterprise this must loop through every version.

### 2.6 Extent

Each diagram has an extent (REST `diagramExtent` in the Diagram Info object). Pro search can find diagrams that "cover parts of the active map extent". After manual edits the extent is not recalculated, so **Recalculate Diagram Extent** is needed (section 5.2). Also, "no dirty areas on the diagram extent" is a precondition of Update Diagram.

### 2.7 Template properties (Pro 3.7 Properties, Network Diagrams tab)

| Property | Meaning | Version/note |
|---|---|---|
| Name, Created Time, Last Modified Time, Description | Identity | |
| **Diagram Storage** | Whether diagrams can be stored | `Enable diagram storage`, default checked |
| **Is System** | Template is assigned to a tier for subnetwork system diagrams | Via Set Subnetwork Definition |
| **Extend Diagram** | Diagrams can be extended | `Enable to extend diagram`, default unchecked |
| **Keep Edge Vertices** | Whether network line vertices survive on diagram edges | Needs Pro 3.7 / Enterprise 12.1 to edit |
| **Remove Linear Containers** | Remove linear containers at the end of a build | Pro 3.7+ |
| **Persist Aggregations** | Keep record of collapsed/reduced/removed content | Pro 3.7+; turn-off supported from Enterprise 12.1; default checked |
| **Layer Definitions Sharing** | Shares a layer definition with other templates | Pro 3.7+ |
| **Associated Telecom Domain** | Used when generating circuit diagrams from Find Circuits | Pro 3.7+ |
| Container margin, reflexive edges | Spacing and self-loop drawing | Alter Diagram Template parameters |

---

## 3. The template catalogue

### 3.1 What ships

Esri's page "Introduction to diagram templates" says three templates are included. They are generic, not tied to any domain, and limited in scope; Esri positions them as learning material, not as production configuration.

| Template | Output | Rules, in order (Esri recreation recipe) | Use when |
|---|---|---|---|
| **Basic** (default if none was chosen) | One diagram feature per selected element; content features also get a diagram feature for their container | Alter Diagram Template (keep initial vertices on edges, enable extend), Add Connectivity Associations Rule, Add Structural Attachments Rule | "Show me what I selected, simply" and for diagrams you want to extend or append to |
| **ExpandContainers** | Containers shown expanded, as diagram polygons with their content inside | Alter (keep initial vertices on edges), Add Expand Container Rule (defaults), Connectivity Associations, Structural Attachments | You need to see equipment inside a vault, cabinet, building or substation |
| **CollapseContainers** | Each container and its contents become one collapsed junction or edge | Alter (keep initial vertices on edges), Add Expand Container Rule (Container Type = Junctions only), Connectivity Associations, Add Collapse Container Rule (defaults), Structural Attachments | You want a simplified overview: container interiors hidden, outer connectivity kept |

Notes on the recipes:

- The recipes come from the template page's "re-create" section. In CollapseContainers the Expand rule runs first so the collapse works from a fully expanded graph; **Practitioner guidance**: read it as "open then close, in that order", not as redundancy.
- Basic is the only shipped template with extension enabled. The other two do not list it in the recipe, so Extend/Append are unavailable on them until an admin alters the template (section 6.2). Checked 2026-10-27 against the Esri template page: only Basic's Alter step lists "Enable to extend diagram".
- A template list reflects those tied to the network layer. A template used as a **subnetwork system diagram template** on a tier disappears from the **New** and **Use Trace Locations** lists when consuming a service, but remains visible via a database connection (Esri, section 4.8).
- The **default template** is the first one in the New drop-down at the start of each Pro session; choosing another makes it the new default (Esri vocabulary). Alter Diagram Template's `Default template` option sets it administratively.

### 3.2 Custom templates (where the value is)

Esri says the added value comes from custom templates that (a) trace automatically on each update, or (b) show a simplified graph. Typical building blocks (details in section 6.3):

| Goal | Rules to combine (illustrative; Practitioner guidance for the recipe) |
|---|---|
| Diagram of everything fed from a device | Set Starting Point By Attribute + Trace rule (Downstream) + Connectivity Associations |
| Only the main structure of a corridor | Remove Feature rule (Exclude mode, keep chosen sources) + Reduce Junction + Start/Stop Iteration |
| Overview that hides interiors | Expand then Collapse Container, as in CollapseContainers |
| Tree-shaped view | A tree layout (Smart Tree, Mainline Tree, Radial Tree) at the end, plus Set Root Junction By Attribute |
| Telecom splice or path view | Trace rule (Path or Circuit), Associated Telecom Domain; see `rest-api/07-circuits-and-unit-identifiers-telecom.md` |

Ordering is decisive (Esri): the first rule processes the initial content; each later rule works on the previous output. Placing Remove Feature **first** deletes initial features permanently and speeds later updates (Esri tool page).

### 3.3 Out of scope here

Tier-assigned **subnetwork system diagram templates** have their own specifics (Esri page "Rule and layout definitions specifics for subnetwork diagram templates"), not summarised beyond section 4.8. Circuit diagrams (telecom) have their own workflow; see `rest-api/07-circuits-and-unit-identifiers-telecom.md`.

---

## 4. The Pro life cycle

Common prerequisites repeated across Esri's pages (check them first when anything fails):

1. Network topology is **enabled** (`learn/03`).
2. **Edits are saved**, because the operations are transactional.
3. **No dirty areas** on the input network features, related containers, or (for update/append/extend) the processed features. Validate first.
4. **Source**: a file or mobile geodatabase, or a network diagram **service**. For a utility or trace network in an **enterprise geodatabase** the diagram operations take a **service layer**, not an `.sde` connection (store, update, overwrite, append, extend, layout, delete, Update Diagram all say this).
5. Enterprise: the portal account needs the **ArcGIS Advanced Editing** user type extension (Esri tool pages for Create Diagram, Store Diagram, Update Diagram).
6. If the default version is protected, standard users create and switch to a version first (Pro 3.7 workflow page).

### 4.1 Generate from selected features or objects (New)

1. Open a UN or trace-network project and a map with the network layers and object tables.
2. Optionally review **Network Diagram options** (e.g. "Open diagrams with all diagram template sublayers").
3. Select the inputs: Select tool, rows in junction/edge object tables, Select by Attributes/Location, or a trace (connected, subnetwork, upstream, downstream).
4. Select the network layer in Contents.
5. Utility Network (or Trace Network) tab, **Diagram** group: **New** (default or last template) or the New arrow to pick a template.

Result: a temporary diagram in a new diagram map. If no template was chosen, Basic is used.

Geometry on first build when no automatic layout is set (Esri): point features at their geographic position; polygon features at the centre of their boundary envelope; junction objects inside their spatial container polygon; container polygons as rectangles around contents; edge objects as straight lines; line features keep their vertices only if **Keep Edge Vertices** = Yes, otherwise straight lines.

### 4.2 Generate from a trace result

Esri's page treats a trace result as *a way to select inputs*, not a separate command. Two forms exist:

| Form | How | Floor |
|---|---|---|
| Select the traced features, then **New** | Run the trace so results are selected; **New** | all supported |
| **Use Trace Locations** | Set starting points and barriers (Set Starting Points / Set Barriers, or Trace pane Add Selected; choose a **Terminal** where needed), select the network layer, **Use Trace Locations** | Pro 3.5 / Enterprise 11.5 |

Trace-location diagrams *save* the locations, and updates reuse them. **Overwrite**, **Append**, **Extend** and **Dynamic mode** replace the saved trace locations with the new initial input, so the "re-run my trace" behaviour is lost (Esri caution on each page).

The **Create Diagram** tool has three modes (Esri): selection (or feature layers, in Python), **trace locations** (starting points and barriers from the active map; feature input ignored; unchecked by default), and **circuit name** (telecom). It also exposes REST equivalents (section 7).

### 4.3 Generate from a subnetwork or starting points

- Manual: trace the subnetwork (`learn/06-tiers-and-subnetworks-in-depth.md`), select, **New**. Or set the subnetwork controller as a starting point and use **Use Trace Locations** with a template whose Trace rule is of type **Subnetwork**.
- Automatic: tiers can hold a **system diagram template** (section 4.8); **Update Subnetwork** then builds and maintains the diagram for each subnetwork.
- Path traces need stopping points, which diagram *rules* cannot set; Esri says create the diagram with Create Diagram's trace-locations option (Add Trace Rule page).

### 4.4 Store (Store Diagram)

Requirements: the diagram is temporary, **consistent** (update first), **Dynamic mode off**, template allows storage, edits saved.

| Parameter (label) | Notes |
|---|---|
| Network Diagram Name | Required; special characters limited to underscore, hyphen, space, parentheses |
| Network Diagram Access Rights | **Public** (default; everyone can see, edit, update, overwrite; only owner and network owner change properties with Alter Diagram Properties), **Protected** (others read only), **Private** (hidden from others in Find Diagrams) |
| Tags | Optional; each preceded by `#` (example from Esri: `#Distribution#Feeder015X89`) |

Offline note (Esri): in a file or mobile geodatabase, Public diagrams store without a portal connection; Protected and Private require one.

Store sparingly (Esri): stored diagrams increase database size and slow dataset copy, upgrade and migration. Good candidates are diagrams with a refined layout to keep, or ones to share.

### 4.5 Find and open (Find Diagrams pane)

Open it from the Utility Network/Trace Network tab (**Find**, Diagram group) or the Network Diagram tab (**Find**, Manage group).

- **Basic** tab: "Cover parts of the active map extent" (default on) and "Contains selected features or objects in the active map" (needs a selection). Selected items are found even when hidden or aggregated.
- **SQL** tab: query on diagram name, template name, consistency state, creator/updater, creation/last-update time. Basic and SQL combine with And. No filter returns all diagrams.
- **Exclude the subnetwork system diagrams** checkbox; keyword box filters by name live.
- Columns: Name, Consistency State (orange = may be inconsistent; red only on open), Type (green exclamation = system diagram), Template, Tag.
- Context menu: open, update, export, delete, change owner, **Add To A New Diagram Map**. Export and Add To A New Diagram Map are disabled with multiple checked.
- **Change Owner** needs a file/mobile geodatabase or enterprise connection, and in enterprise the portal user must be the network owner.
- Update is unavailable over a database connection and for system diagrams.

### 4.6 Update, overwrite, append, extend: what each one does

| Operation | Starting point | What it does | Layout of existing features | Works on | Template needs |
|---|---|---|---|---|---|
| **Update** (tool: Update Diagram) | The diagram's own stored input | Re-reads original elements, reruns the template's rules, reports topology changes, removes diagram features whose network features are gone, adds newly returned ones | Kept; automatic layouts only reapplied if **Re-apply automatic layouts** is checked (default off) | Temporary and stored | none |
| **Overwrite** | Current map selection | Rebuilds content from the selection, reapplies rules and automatic layouts | Kept only for stored diagrams, not temporary | Ribbon: temporary only. Stored: Overwrite Diagram tool | none |
| **Append** (Append To Diagram) | Current map selection | Adds listed features/objects missed or created later; full update of old+new content; reruns rules | Kept | Not system diagrams | Template must allow extend |
| **Extend** (Extend Diagram) | Current diagram content | Adds neighbours one level out: **By Connectivity**, **By Traversability** (enabled `Status` only), **By Containment**, **By Attachment** | Kept | Ribbon: temporary only; stored: Extend Diagram tool. Not system diagrams | Template must allow extend; Esri best practice: disable extend on templates using reduce, collapse, expand or trace rules |
| **Dynamic** | Selection changes in the geographic map | Overwrites the active temporary diagram on each selection change | Previous content discarded | Temporary only; Store is disabled until Dynamic is turned off | none |

Update Diagram parameters (labels): Input Network or Network Diagram Layer; Template Names; Diagram Names; **Update inconsistent diagrams only** (default checked; uncheck to update consistent ones too, e.g. after rule changes); **Re-apply automatic layouts on the updated diagrams** (default unchecked). Giving template and diagram names that do not match fails. Esri sets the Diagram Feature Selection To Layout task floor at Pro 3.6 / Enterprise 12.0.

Pre-conditions beyond section 4 intro: for overwrite/append/extend/dynamic the selected items and the diagram must share the same branch version, and **All Layers** mode must be on.

### 4.7 Delete

- Pro: **Delete Diagrams** in Find Diagrams (Shift-click for several), or the **Delete Diagram** tool.
- Permissions (Pro 3.7): standard portal users delete diagrams they own and public diagrams of others; the portal network owner can delete any; **only the portal utility network owner** can delete subnetwork system diagrams.
- A file/mobile network created without an owner can only free system diagrams by disabling topology, which removes the system flag.
- Deleting is not free in a versioned database: it writes rows per feature (Esri blog).
- **Delete Diagram Template** deletes the *template and all diagrams based on it* (tool page); treat it as destructive.

### 4.8 Subnetwork system diagrams (short version)

- Created when a tier has diagram templates assigned in **Set Subnetwork Definition** and **Update Subnetwork** runs. Esri advises custom templates, not the three shipped ones.
- Name format `<DiagramTemplateName>_<SubnetworkName>`; tags carry domain, tier and subnetwork name.
- Only **Update Subnetwork** updates them; Update Diagram, Overwrite, Append and Extend do not apply. Layout edits (geometry) are allowed; name, tags and access rights are not editable.
- They go inconsistent when their network features are edited; validating over the area does **not** by itself make them inconsistent, except for subnetworks with several controllers.
- Disabling topology removes the system flag; re-enable and update subnetwork to restore it.
- Stored system diagrams slow Update Subnetwork (Esri blog), so limit how many system templates a tier carries. Full process: `learn/06-tiers-and-subnetworks-in-depth.md`.

### 4.9 Historical moments

Connect the layer to `sde.Default`, then **Change Moment**. Allowed: generate temporary diagrams, search and open stored diagrams as they were. Not allowed: layout, overwrite, extend, store.

---

## 5. Editing a diagram

### 5.1 Layouts

A layout is an algorithm that repositions diagram features. Apply from the **Diagram Layouts** gallery (Layout group) or the layout tool; automatic layouts are those added to the template and run on build.

| Layout (tool) | One-line behaviour (Esri tool description) | Needs |
|---|---|---|
| Smart Tree | Hierarchical tree; direction left/right/up/down; branches ordered by position, or by attribute from Pro 3.6 / Enterprise 12.0 | Root junction optional (default: smallest topology index) |
| Mainline Tree | Hierarchy along a main line; branches left, right or both | Root, End junction optional |
| Radial Tree | Hierarchical radial tree | Root |
| Relative Mainline | Parallel straight lines | Uses edge vertices (see section 6.2) |
| Rotate Tree | Rotates trees at pivot junctions to an angle | Pivot junctions, barriers |
| Main Ring | Arranges features around a main ring | Barriers optional |
| Force Directed | Emphasises loops | none; good for connectivity checks |
| Grid | Junctions on a predefined magnetic grid | |
| Compression | Compresses features toward the middle | |
| Angle Directed | Moves edges in specified alignment directions | |
| Linear Dispatch | Adds space between junctions that are too close or overlapping | |
| Spatial Dispatch | Separates junctions visibly close to overlapping (defaults: 5 iterations, max shift factor 2) | |
| Partial Overlapping Edges | Spaces collinear edges or edge segments inside a buffer | Uses edge vertices |
| Reshape Diagram Edges | Simple vertex operations on edges | |
| Geo Positions | Moves junctions and edges back to the geographic positions of the network features | |
| Apply Template Layouts | Applies the template's configured layout list | |

Flag tools (Layout group, Set Flags): **Set Root Junction** (green circle), **Set End Junction** (blue square), **Set Pivot Junction** (gray star), **Set Barrier** (red cross). Click a feature to add, click again to remove, click background to clear all of that type.

Options: **Use default parameters to apply layouts** (default checked) applies immediately; unchecked opens the tool pane. For very large diagrams (over 25,000 features, Esri) set **Run in asynchronous mode on the server** per tool, because the synchronous service time-out is 600 seconds (Spatial Dispatch page). Geo Positions note: before Pro 3.7 / Enterprise 12.1, restore-edge-positions was always on; now it follows **Keep initial vertices on edges**.

Layout changes generally cannot be undone, except manual edits on file/mobile diagrams and published stored diagrams in a branch version (Esri blog).

### 5.2 Manual edits (white space editing)

Esri limits manual editing to **reshaping**: Move tool and Vertices tool (Add Vertex, Delete Vertex, drag).

- Turn off **Stretch Topology** on Move so shapes are not preserved relatively (usually unwanted).
- Moving a junction stretches its edges; moving an edge moves its junctions; moving a container moves its contents; moving content redraws the container around it.
- Commands in the Modify group dropdown: **Recalculate Diagram Extent**, **Recalculate Container Geometries** (restores horizontal rectangles; select containers first to limit scope), **Recalculate Edge Geometries** (reconnect an edge that manual editing detached).
- From Pro 3.4, updates keep saved container geometry unless contents are added or removed; earlier, edited containers reset to rectangles.
- **Copy Layout From Diagram** copies geometry from a source diagram to matching features in the active one.

### 5.3 What is, and is not, synchronized back

| Edit | Reaches the network? | Notes (Esri blog, white-space page) |
|---|---|---|
| Move/reshape a diagram feature | **No** | Network feature geometry is unchanged |
| Same element in another diagram | **No** | Each diagram keeps its own geometry |
| Diagram attributes, or joined network attributes through the diagram | **Not editable manually** | |
| Diagram junction Rotation (custom code) | Diagram-side only | Pro SDK |
| Editable network attributes (custom code) | **Yes, changes network data** | Exception; use deliberately |
| Network edits (geometry, attributes, associations) | They reach the diagram **only** via Update / Append / Overwrite | Network edit marks diagram inconsistent after validate |

Rule of thumb (Practitioner guidance): a diagram is a **read-only view with its own layout**. If someone wants "move it on the diagram and fix the map", the answer is no; make the edit in the network map.

### 5.4 Selection propagation between maps

Selections move between geographic and diagram maps via Apply To Maps / Apply To Diagrams. Options (Pro 3.7, Network Diagrams tab): propagate reduced or collapsed elements (default off; from Pro 3.7 / Enterprise 12.1 they are selected in the other map only when **Persist aggregations** is on), zoom to result, add connectivity associations, add structural attachments, select spatial containers. These settings are saved with the project.

---

## 6. Administration

### 6.1 Who may do what

| Task | Who | Where |
|---|---|---|
| Create, alter, delete templates; add rules/layouts; Purge Temporary Diagrams | **Portal network owner**, running from an `.sde` connection to the **default version** as the **database network owner** | File or mobile geodatabase, or enterprise database connection. **Not supported on a service** |
| Set Subnetwork Definition (assign system templates) | Database + portal utility network owner | |
| Generate, store, update, append, extend, overwrite, layout | Any editor with Advanced Editing on the portal | Service (enterprise) or file/mobile |
| Delete own or public diagrams | Standard portal user | |
| Delete any diagram / system diagrams | Portal network owner / portal **utility** network owner | |
| Alter Diagram Properties (rights, tags) | Diagram owner and network owner | |
| Change Owner | Network owner (enterprise) | |

License floors (tool pages): the configuration tools above list Basic **No**, Standard **Yes**, Advanced **Yes**. In enterprise, editing diagrams through services needs the **ArcGIS Advanced Editing** user type extension. The default version must be **public** (not protected) for configuration tools. Add Structural Attachments Rule is documented for a utility network only.

### 6.2 Template tools

| Tool (toolbox Network Diagram Tools, Configuration toolset) | Purpose |
|---|---|
| Add Diagram Template | New template; optional `.ndbd` (rules/layouts) and `.ndld` (layer definition); default layer definition initialised if none supplied; adds a layer definition ID |
| Alter Diagram Template | Rename, set default, remove rule/layout definitions, Keep initial vertices on edges (default off), Container Margin, Enable diagram storage (default on), Enable to extend diagram (default off), Description, reset layer definition, Keep reflexive connectivity associations (default on), Remove linear containers (default off), Reflexive Edge Radius, associate telecom domain, Persist aggregations (default on) |
| Delete Diagram Template | Deletes template and all its diagrams |
| Get Diagram Templates Names | Lists template names |
| Create/Export Diagram Layer Definition | Build or save `.ndld` |
| Export / Import Diagram Template Definitions | `.ndbd` and `.ndld` round-trip, move templates between copies of a network |
| Create Geoprocessing Model From Diagram Template | Builds a model reproducing a template; Esri recommends models for maintaining definitions |

Alter Diagram Template notes: changing container margin or removing definitions makes existing diagrams inconsistent; **Keep initial vertices on edges** costs processing time, enable mainly for Relative Mainline and Partial Overlapping Edges layouts; to reset in a model, start with "Remove the diagram template rule and layout definitions". Turning off **Persist aggregations** shortens builds and reduces growth, at the cost of tracking collapsed, reduced or removed features. Starting a model with that reset is Esri's recommended way to re-baseline a template.

Layer definition levels: **none** (basic settings made at each open; exports an empty `.ndld`), **default** (fixed basic settings; Add/Alter initialise it), **custom** (fewer layers, labels, subtype group layers; made by Create Diagram Layer Definition, Import, or Add Diagram Template with a nonempty `.ndld`).

### 6.3 Rule catalogue (Pro 3.7 Add ... Rule tools)

Every rule tool takes **Input Network** and **Input Diagram Template**, has **Active** (default checked) and usually **Description**, appends at the end of the sequence, and makes existing diagrams inconsistent. Three tool families: `Add <X> Rule` (several sources at once), `Add <X> By Attribute Rule` (one source plus SQL), `Add <X> By Category Rule` (network categories).

| Rule family | Tools | Key parameters and behaviour (Esri) |
|---|---|---|
| **Expand container** | Expand Container Rule; ... By Attribute; ... By Category | Keep containers visible (default checked); Container Type (Junctions only / Edges only / Both, default Both); Rule Process (default Exclude source classes); Container Sources. With defaults and no sources, **every** container expands. Include mode requires sources |
| **Collapse container** | Collapse Container Rule; By Attribute; By Category | Same Container Type / Rule Process / Sources; **Aggregate reconnected edges** (default checked): reconnected edges merge into one reduction edge, even if several edges joined two collapsed junctions |
| **Reduce junction** | Reduce Junction Rule; By Attribute; By Category | Rule Process (default Include); Junction Sources (order = priority; `SystemJunctions` covers system junctions); **Reduce Junctions With** Maximum two (default) or Minimum three; Reduce if unconnected (off), if connected to a single junction (off), if connected to 2 different junctions (on, onto a "super span" reduction edge); Edge Attribute Names (adjacent edges must share values); Use Digitized Direction (Minimum three, Pro 3.4+, UN v7 partitioned tiers) |
| **Reduce edge** | Reduce Edge By Attribute Rule | Edge Source to Reduce, Expression, Aggregate reconnected edges (default checked). A reduction junction represents one line feature or edge object (e.g. a busbar) |
| **Remove feature** | Remove Feature Rule; By Attribute; By Category | Source Type; Rule Process (default Include); Network Sources; connectivity constraints "must be unconnected" / "connected to a single junction" (Pro 2.9+, Junctions only). First in sequence: permanently deletes initial features, which helps speed |
| **Trace** | Add Trace Rule | Trace Type (default Connected; Subnetwork, Upstream, Downstream, Path, Circuit for telecom; Shortest path deprecated in Pro 3.7, use Path); Domain Network, Tier, Target Tier; Num Paths (1), Max Hops (100), Include Structures (off), Include Barriers Features (on), conditions, function barriers, filters, Filter by nearest, Use Digitized Direction (UN v7+; Enterprise 11.3+), Use Trace Configuration (UN v7+). Output asset type/feature type filtering in Pro 3.6 |
| **Set start/root** | Set Starting Point By Attribute; Set Root Junction By Attribute | Starting points feed a later Trace rule (if none match, the trace is skipped); give a **terminal ID** for subnetwork traces. Root junction anchors tree layouts. Create Diagram's trace-locations option overrides starting-point rules |
| **Spatial query** | Add Spatial Query Rule | Add Features, Existing Features, Relationship (Intersect default; Within a distance; Contains / Is contained of; Within; Boundary touches; Share a line segment with; Crossed by the outline of), Search Distance, two query definitions |
| **Associations** | Connectivity Associations Rule; Structural Attachments Rule | Draw straight edges only when both elements are already in the diagram. Time-consuming: skip when another rule already guarantees them (a Trace rule returns connectivity associations; a Remove Feature rule that deletes structures makes Structural Attachments useless) |
| **Iteration** | Start Iteration Rule; Stop Iteration Rule | Loop over the rules between them, typically reductions, because reducing changes connectivity and makes new junctions eligible. Esri: Start marks the beginning and Stop "the end of the rule sequence the diagram builder iterates over". Neither page says whether pairs are mandatory or can nest (unverifiable) |
| **Capability** | Diagram Feature Capability By Attribute; By Category | Capability options: Prevent/Allow related container to collapse (default Prevent), Prevent/Allow reduce junction, Save unconnected empty container junctions as polygons, Ignore to start upstream/downstream trace; valence checkboxes (Pro 3.4+) |

Layout configuration tools (`Add <X> Layout`): Angle Directed, Compression, Force Directed, Grid, Linear Dispatch, Main Ring, Mainline Tree, Partial Overlapping Edges, Radial Tree, Relative Mainline, Reshape Diagram Edges, Smart Tree, Spatial Dispatch, plus **Add Diagram Feature Selection To Layout** (limits the next active layout to a selection; Pro 3.6 / Enterprise 12.0). New layouts are active by default and applied in entry order.

Older note: `pro-help/07-network-diagrams.md` lists Collapse Container By Attribute, Set Root Junction By Attribute, Add Spatial Query and Start Iteration only; the catalogue above completes it and does not contradict it. Python parameter names are not on the pages reviewed 2026-10-27 (unverifiable); check the tool's Python tab.

---

## 7. Enterprise: NetworkDiagramServer

**What it is (Esri REST page).** Endpoint `https://<root>/<serviceName>/NetworkDiagramServer`, GET and POST, introduced at **10.6**, a map-server extension that exposes diagram capabilities to web apps. Default template name in the sample response is Basic.

| Capability | Operations/resources |
|---|---|
| Retrieve stored diagrams | Find Diagram Names (extent, SQL where, element GlobalIDs), Find Diagram Infos |
| Characteristics | Diagram Info and consistency (Query Consistency State) |
| Create (temporary) | Create Diagram From Features (GlobalIDs), **Create Diagram From Trace Locations** (11.5; `template`, `traceLocations` with `traceLocationType` startingPoint/barrier/stoppingPoint, `globalId`, optional `terminalId`, `percentAlong`, `isFilterBarrier`, `firstUnit`, `numUnits`), Create Diagram From Circuit Name (12.1; `template` configured with a Circuit-type Trace rule on a telecom domain, `circuitName`) |
| Edit and maintain | Per-diagram operations: Apply Layout, Save Layout, Append Features, Extend, Clear Flags, Query Diagram Content, others (see `rest-api/03-network-diagram-service.md`) |
| Delete | Delete Diagram |
| Child resources | Diagram Dataset, Diagrams, Diagram Templates |

Per-diagram `findNetworkFeaturesFromOIDs` (11.5; takes diagram `junctionObjectIDs`, `edgeObjectIDs`, `containerObjectIDs`, `includeAggregations`; `pbf` output from 12.0) is not in the service page's operation list but is linked from its description; Esri recommends it over `findNetworkFeatures` from 11.5. Query Consistency State returns `esriDiagramIsConsistent`, `esriDiagramNotConsistentWithTopology` or `esriDiagramHasDirtyFeatures` per diagram name.

**Requirements.** Advanced Editing user type extension for diagram use (REST and Pro pages). Verified 2026-10-27: Find Diagram Infos, Find Diagram Names and Query Consistency State state Advanced Editing only "for versions prior to ArcGIS Enterprise 11.5" and name no extension from 11.5; the earlier "Utility/Trace Network extension" claim in `rest-api/03` was wrong.

**Publishing prerequisites (Pro 3.7 publishing help).**

- A feature service that contains the utility network layer automatically carries the **Utility Network** and **Network Diagram** services. Without the UN layer, there is no Network Diagram service and no trace or diagram support.
- Layers must come from a database connection as the **database utility network owner**; the portal account must be the **portal utility network owner**.
- **Branch versioning** with the feature dataset registered as branch versioned; **Feature** capability on and **Version Management** enabled; keep layer IDs stable; the publishing map must not contain subtype group layers; true-curve options checked in Feature Properties.
- Definition queries and hidden fields are unsupported when the UN layer is present (analyzer error 00270).
- Diagram *templates* are not creatable over REST or a service; they must exist already (`pro-help/07-network-diagrams.md`, `rest-api/03`).
- Esri notes an overall performance limitation for services (section 8).

**Consuming in web apps.** There is no JS SDK 5.1 diagram class or layer (`js-api/03-network-class-loading-and-definition.md`; `js-api/06-functional-api-web-components-calcite.md` records the same gap for `arcgis-rest-js`). Pattern, from the REST surface: call `createDiagramFromFeatures` or `createDiagramFromTraceLocations`, read the Diagram Info (junction/edge/container counts, `isStored`, `canStore`), call query operations on `diagrams/<name>` for content, and draw it yourself (for example as client graphics). Practitioner guidance: keep a "diagram viewer" feature small, and build it on Diagram Info counts so you can refuse oversize results.

Pro SDK note: Pro SDK can build custom layouts and tools (`references/pro-sdk/01-csharp-sdk-utility-network-api.md`); the Esri blog says custom code can edit a diagram junction's Rotation.

---

## 8. Performance limits and cautions

| Item | Fact | Source tag |
|---|---|---|
| Service-built diagram size | Creating a diagram from a **service** with more than 49,999 features fails with error 160243; Esri closed Support bug 000168157 "As Designed" (Pro 3.3, 2024); workaround: select under 50,000 features | Esri Support bug page (verified 2026-10-27: fails at 50,000 or more features) |
| Layout time-out | Synchronous layouts on a service hit a 600-second time-out; use async above about 25,000 features | Esri tool page |
| Template rule cost | Connectivity Associations and Structural Attachments rules are time-consuming; add them only when not guaranteed by other rules | Esri tool pages |
| Keep Edge Vertices | Adds processing time | Esri Alter Diagram Template |
| Persist aggregations | Off reduces build time and growth, loses aggregate tracking | Esri Alter Diagram Template |
| Stored diagrams | Grow the database; slow copy, upgrade, migration; in branch versions each diagram edit adds rows; Update Subnetwork slows with system templates | Esri help and blog |
| Temporary diagrams | Each generation makes one; discarded ones remain until Purge Temporary Diagrams runs (schedule it) | Esri help |
| Extend | Disable on templates with reduce/collapse/expand/trace rules; extension of collapsed content may show little change | Esri help |

Cautions:

- **A template edit invalidates all existing diagrams for that template** (orange). Plan the Update Diagram loop (every version in enterprise).
- Never "test" a rule on a production template; clone it (Export/Import definitions, or the geoprocessing model) first. (Practitioner guidance.)
- Plan for Update Diagram needing validated topology: large validate backlogs mean diagrams stay red.
- Do not build a user workflow on dozens of stored per-user diagrams; prefer generating temporary diagrams from a good template.

---

## 9. Common problems and fixes

| Symptom | Likely cause | Fix |
|---|---|---|
| New is greyed out / "no topology" | Topology disabled; layer not selected in Contents | Enable topology; select the network layer |
| Generation fails with a dirty-area message | Dirty areas on selected features or related containers | Validate topology over those features, save, retry |
| Diagram is **empty** | No valid input selected; only nonnetwork elements selected; a Remove Feature rule removes everything; Set Starting Point matches nothing so the Trace rule is skipped; sublayers hidden because All Layers is off | Select network features; review the template's rule order; open with all template sublayers |
| **Missing containers / contents** | Wrong template (CollapseContainers hides interiors); Collapse rule in Include/Exclude mode misconfigured; Persist/propagation options hide aggregated elements; container not in input | Use ExpandContainers or adjust the Collapse/Expand rule's sources; turn on propagation of reduced/collapsed elements |
| Diagram **out of date** after edits | Edits not saved; topology not validated; Update not run | Save, Validate, then Update; or Overwrite/Append for new features (Esri KB 000033741) |
| Red icon | Dirty areas on feeding features | Validate then update (section 2.5) |
| Orange icon on all diagrams | Template changed, topology disabled or validated over extent | Update Diagram with "inconsistent only" unchecked where rules changed |
| Gray icon | Sublayers out of sync | Update; admin reviews layer definition |
| Store disabled | Dynamic on; diagram already stored; inconsistent; template storage disabled; unsaved edits | Fix the matching condition; Update first |
| Extend/Append unavailable | Template lacks Extend; stored diagram (ribbon); All Layers off; system diagram | Admin enables extend; use the tool for stored; turn All Layers on |
| Update Diagram not available over `.sde` | Diagram operations need a service in enterprise | Use the published service layer |
| Template tools greyed out or fail from a service | Configuration is unsupported on services | `.sde` connection to default as database network owner, portal network owner, public default version |
| System template missing from New list | Template is assigned to a tier | Use a database connection or a separate non-system copy |
| 160243 max-feature error | More than 49,999 features through a service | Reduce selection |
| Layout runs forever / times out | Synchronous layout on a huge diagram | Run asynchronously |
| Layout lost after update | Automatic layouts not reapplied by default; Overwrite on a temporary diagram | Check "Re-apply automatic layouts"; store the diagram you tuned |
| Containers reset to rectangles | Pro earlier than 3.4 | Upgrade; use Recalculate Container Geometries on purpose |
| Diagram feature off screen | Diagram extent not recalculated after manual edits | Recalculate Diagram Extent |

---

## 10. Quick chooser: which diagram for which question

| Question | Start from | Template idea | Layout idea |
|---|---|---|---|
| "What is connected to this asset?" | Select it, or a Connected trace | Basic, then Extend By Connectivity | Force Directed |
| "Show me what is inside this vault/cabinet/building" | Select the container | ExpandContainers | Grid or Smart Tree |
| "Give me an overview without interiors" | Selection of a corridor | CollapseContainers | Smart Tree |
| "Everything downstream or upstream of X" | Use Trace Locations (Pro 3.5+), or Downstream trace then New | Custom with Set Starting Point + Trace rule | Smart or Mainline Tree |
| "A feeder, pressure zone or route that stays current" | The subnetwork | System diagram template on the tier | Tree layout configured on the template |
| "Is my data really connected?" | Selection, Dynamic mode | Template with automatic Force Directed | Force Directed |
| "A shortest or defined path between two points" | Create Diagram with trace locations including stopping points | Template with a Trace rule of type Path | Mainline Tree |
| "Keep this and share it" | A consistent temporary diagram | Any template with storage enabled | Hand-tuned, then Store with tags |
| "Put diagrams in my web app" | NetworkDiagramServer REST calls | An existing template | Apply Layout over REST, custom rendering |
| "Telecom circuit view" | Find Circuits, Create Diagram From Circuit Name | Template associated with the telecom domain | Not documented in the pages reviewed (unverifiable) |

## Common misconceptions

- "A diagram is a map in a different style." It is a separate schematic graph with its own geometry, stored in diagram tables.
- "Moving a symbol on the diagram moves the asset." No; diagram edits never write network geometry.
- "Updating the network updates the diagram." It does not; the diagram goes inconsistent and must be updated.
- "Templates can be made over REST or from the web app." They cannot; they are configured only from a file/mobile geodatabase or an enterprise database connection as the owner.
- "The three shipped templates are a production setup." Esri calls them generic and limited, a learning aid.
- "Stored diagrams are free." They cost size, speed in versioned data and Update Subnetwork time.
- "Update Diagram works with a database connection." Not for enterprise; use the service.
- "The JS SDK has a diagram layer." As of this review (SDK 5.1) it does not (`js-api/03`).

## Quick checks

1. Which network source: file/mobile geodatabase, enterprise `.sde` connection, or a service layer?
2. Is the topology enabled, are edits saved, and are there dirty areas on the inputs?
3. Which template, and has an admin changed its rules recently (orange icons everywhere)?
4. Temporary or stored? Is Dynamic mode on? Is All Layers on?
5. Is this a subnetwork system diagram (only Update Subnetwork changes it)?
6. Does the template allow storage and extension?
7. Which consistency icon, and what does the Find Diagrams column say?
8. How many features is the request (49,999 service limit; async above about 25,000 for layouts)?
9. Which Pro, Enterprise and UN version (3.5/11.5 trace locations; 3.6/12.0 selection-to-layout; 3.7/12.1 new template properties)?
10. Is the portal account licensed with Advanced Editing, and who is the network owner?

## Related files

- `references/pro-help/07-network-diagrams.md` (brief overview and constraints)
- `references/rest-api/03-network-diagram-service.md` (REST detail and worked examples)
- `references/js-api/03-network-class-loading-and-definition.md` (JS gap for diagrams)
- `references/js-api/06-functional-api-web-components-calcite.md` (arcgis-rest-js gap)
- `references/learn/01-mental-model-and-life-of-an-edit.md` (where diagrams sit in the edit cycle)
- `references/learn/02-data-model-in-depth.md` (diagram system layer IDs)
- `references/learn/03-topology-engine-and-validation.md` (dirty areas, validate)
- `references/learn/06-tiers-and-subnetworks-in-depth.md` (system diagram templates, Update Subnetwork)
- `references/learn/07-tracing-in-depth-and-configuration-library.md` (traces feeding diagrams, Trace rule)
- `references/learn/08-versioning-and-editing-workflows.md` (reconcile and diagrams)
- `references/learn/10-performance-scale-and-operations.md` (49,999 feature bug context)
- `references/learn/13-arcgis-pro-fundamentals-and-workflow.md` (Pro surface)
- `references/learn/12-glossary-and-concept-map.md` (vocabulary)
- `references/rest-api/07-circuits-and-unit-identifiers-telecom.md` (circuit diagrams)

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/introduce-diagram-templates.html
- https://pro.arcgis.com/en/pro-app/2.9/help/data/network-diagrams/network-diagrams-vocabulary.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/network-diagrams-vocabulary.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/manage-the-rules-and-layouts-definition-on-your-templates.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/generate-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/store-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/introduce-workflow-with-network-diagrams.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/update-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/search-for-network-diagrams-in-the-database.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/delete-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/lay-out-the-content-of-network-diagrams.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/manage-network-diagram-consistency.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/network-diagram-consistency.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/overwrite-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/append-features-to-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/extend-network-diagram-content-by-connectivity-or-traversability.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/subnetwork-system-diagrams-and-their-specifics.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/network-diagram-options.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/enable-dynamic-diagram-mode-to-refine-diagram-content-or-check-network-connectivity.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/manage-white-space-editing-in-a-network-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/manage-diagram-layer-definitions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/smart-tree-layout-reference.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/mainline-tree-layout-reference.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/an-overview-of-the-configuration-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/an-overview-of-the-layout-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-diagram-template.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/alter-diagram-template.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/delete-diagram-template.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/create-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/update-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/store-diagram.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/purge-temporary-diagrams.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/apply-spatial-dispatch-layout.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-trace-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-reduce-junction-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-reduce-edge-by-attribute-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-expand-container-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-collapse-container-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-connectivity-associations-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-structural-attachments-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-remove-feature-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-spatial-query-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-start-iteration-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-set-starting-point-by-attribute-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-set-root-junction-by-attribute-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/network-diagram/add-diagram-feature-capability-by-attribute-rule.html
- https://developers.arcgis.com/rest/services-reference/enterprise/network-diagram-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/create-diagram-from-trace-locations-network-diagram-service/
- https://www.esri.com/arcgis-blog/products/arcgis-pro/data-management/editing-in-network-diagrams
- https://www.esri.com/arcgis-blog/products/arcgis-pro/data-management/storing-or-not-storing-networks-diagram
- https://support.esri.com/en-us/knowledge-base/network-diagram-is-not-getting-updated-same-as-map-view-000033741
- https://support.esri.com/en-us/bug/creating-a-utility-network-diagram-with-more-than-49999-bug-000168157
