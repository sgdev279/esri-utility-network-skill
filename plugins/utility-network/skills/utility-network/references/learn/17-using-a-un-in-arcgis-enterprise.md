# Utility Network: Using a Utility Network in ArcGIS Enterprise (Deployment, Consumption, Versions, Runbook)
> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri Pro 3.7 and Enterprise 12.1 help, Esri REST reference and Esri blogs (URLs under Sources). Builds on `learn/08`, `learn/13`, `learn/14`, `pro-help/09`, `pro-help/10`, `rest-api/01` to `rest-api/06` and `experience-builder/01`.*

**Why this matters / when to read this.** A Utility Network (UN) on a file or mobile geodatabase is a single-user sandbox. A UN that a utility actually runs lives in an enterprise geodatabase and is published through ArcGIS Enterprise, where many people edit, trace and view it at once. This file explains the pieces of that deployment, who owns what, what each client can and cannot do with the published services, how the isolate-edits (branch version) workflow looks from the consumer side, and what an administrator should check when standing the system up. It is domain-neutral.
Read it when someone asks "what do we need to publish a UN", "why can the web app trace but not edit", "can Map Viewer reconcile and post", "who may post to DEFAULT", or "file gdb or enterprise?".
It does not repeat mechanisms already taught elsewhere: reconcile/post and locking internals are in `learn/08`, the Pro surface in `learn/13`, developer surfaces in `learn/14`, owners and licensing tables in `pro-help/10`, dataset versions in `pro-help/09`. Practitioner guidance is labelled as such; where I could not confirm a fact it says "Verify against the Esri docs for your version".

## Contents
1. Deployment architecture
2. What a published UN exposes (the services)
3. Owners, licences and user types, in one view
4. Discovering and consuming the data
5. What each client can and cannot do
6. Branch versioning from the consumer side
7. Security and permissions model for versions
8. Publishing workflow, verification and common failures
9. Upgrades and patch-level issues
10. Decision table: file or mobile geodatabase versus enterprise
11. Admin runbook: standing up an enterprise UN
12. Common misconceptions, quick checks, related files, sources

## 1. Deployment architecture

**Definition.** "Using a UN in Enterprise" means the network data sits in an enterprise geodatabase, an ArcGIS Server site federated with an ArcGIS Enterprise portal publishes it, and people consume it through portal items (web layers, web maps, apps) rather than by opening the database.

**Mechanism.** Four layers cooperate.

```
 Clients      Pro (Portal tab)   Map Viewer   Field Maps   Experience Builder   custom JS / REST scripts
                  \               |             |               |                    /
                   +--------------+-------------+---------------+-------------------+
                                  |  sign in with portal account (user type + extension)
 Portal  ---------------  items (web layer, web map, app), sharing, groups, roles, privileges
                                  |  federated
 Server  ---------------  map service + extensions: Feature, UtilityNetworkServer,
                          NetworkDiagramServer, VersionManagementServer, ValidationServer
                                  |  registered data store (by reference)
 Database  -------------  enterprise geodatabase, branch versioned, owned by the UN data owner
```

| Piece | Role | What to know |
|---|---|---|
| Enterprise geodatabase | Stores the UN dataset, the structure and domain network classes, system tables | Must be branch versioned for the UN to be published (Esri, Pro 3.7 "Publish and consume" topic). Branch registration needs geodatabase release 10.6 or later and a supported DBMS (Db2, SQL Server, Oracle, PostgreSQL or SAP HANA per the registration page) |
| Registered data store | Lets the server read the database by reference | The database must be registered as a data store and the web layer must "reference registered data" (Esri publish branch versioned data page). Analyze can offer to register it |
| ArcGIS Server | Hosts the map service and the UN-aware extensions | Esri's older (10.8-era) help states the site you publish to must be federated with the portal; the 12.1 Enterprise "Utility Network services" page does not mention federation. Treat federation as required unless Esri says otherwise: Verify against the Esri docs for your version |
| Portal | Items, identity, licensing, sharing, roles | The signed-in portal account is part of authorisation: it determines the owner, the user type extension and group access |
| Clients | Everything that calls the services | Each client has its own feature coverage (section 5) |

**Two owners.** The data owner is the database user that created the network (part of the dataset's fully qualified name). The portal owner is the portal account signed in to Pro at creation (stored as metadata, changeable with Update Portal Dataset Owner). Publishing needs both: the layer must come from a connection as the database owner, and Pro must be signed in as the portal owner (Esri). Full tables of which tool needs which owner are in `pro-help/10`.

**Dedicated instances.** Esri's publish-branch-versioned page notes that choosing Map Image plus Feature automatically sets the service instance type to Dedicated. Plan server capacity for dedicated instances, because an edit session pins a service instance (Practitioner guidance; instance sizing is covered in `learn/10`).

**Example (water utility).** The GIS team keeps a PostgreSQL enterprise geodatabase. The data owner `unadmin` builds the network; the GIS administrator signs in to Pro with a portal account that holds Advanced Editing and publishes a service named for the network. Editors open the service from the Portal tab; a field app uses a different, lighter service from the same data.

**Pitfall.** Treating the database as a second edit path. After publishing, edits go through the services; direct database connections are for configuration and QA (`pro-help/10`).

## 2. What a published UN exposes (the services)

**Definition.** One publish produces one map service whose extensions provide the UN capabilities. Esri's Enterprise page lists four service types; the REST reference adds the validation extension.

| Service | Address pattern | What it does | Enabled by |
|---|---|---|---|
| Feature service | `<root>/<serviceName>/FeatureServer` | Edits and queries on UN features; understands associations and dirty areas; exposes system layers (`rest-api/04`, `rest-api/05`) | Feature checked under Reference registered data |
| Utility Network service | `.../UtilityNetworkServer` | Trace, subnetworks and tiers (update, export), validate network topology, enable/disable topology, associations, locations, trace configurations (`rest-api/01`, `rest-api/02`) | Included automatically when the published feature service contains the UN layer |
| Network Diagram service | `.../NetworkDiagramServer` | Create, store, edit and maintain network diagrams (`rest-api/03`) | Included automatically with the UN layer |
| Version Management service | `.../VersionManagementServer` | Create, alter, delete, reconcile, post versions; locks (`learn/08` section 3, `rest-api/04`) | Version Management capability at publish; needs Feature plus a branch versioned dataset |
| Validation service | `.../ValidationServer` | Evaluate rules, update/write errors (`rest-api/04`) | Validation capability; implemented as an extension tied to the feature service |
| Map service | `.../MapServer` | The published map image | Always (Map Image layer type) |

Facts and limits:
- Esri: a feature service that includes the UN layer automatically includes the Utility Network and Network Diagram services. A service published *without* the UN layer (plain feature layers) has no Utility Network or Network Diagram service, so no trace and no diagrams, although edits still create dirty areas that are not visible on the map. Version Management is optional in that case (Esri Pro 3.7 "Publish and consume").
- Esri's "Overview of Utility Network Services" page (read for `rest-api/04`) describes the extension requirement for the utility network and network diagram services as the UN management licensing; the exact licence wording differs by release: Verify against the Esri docs for your version.
- Each extension reports what it supports in its `capabilities` JSON. Read the flags fresh instead of assuming (`rest-api/01`, `rest-api/04`). The flags tell a script whether, for example, async trace or partial post exist on that server.
- The `ValidationServer` and `VersionManagementServer` share the service's instance settings; they do not scale independently (`rest-api/04`).

**Three service shapes commonly published from one dataset** (Practitioner guidance, built on Esri's electric-scenario guidance in the Pro 3.7 "Publish and consume" topic):

| Shape | Contents | Typical consumers |
|---|---|---|
| Full editing and analysis service | All data and the UN layer, Version Management on | Pro editors, QA, analysts |
| Field service | Selected layers, no UN layer, Version Management optional; sync enabled and Service territory included if offline | Field Maps (see section 5 for the version 8 caveat) |
| Viewing service | Selected layers, no UN layer | Dashboards, Map Viewer, simple apps |

**Pitfall.** Expecting trace in an app that points at the viewing service. The viewing service has no `UtilityNetworkServer`, so there is nothing to call.

## 3. Owners, licences and user types, in one view

| Question | Answer (source) |
|---|---|
| Pro licence level for any UN work | Standard or Advanced; not Basic (`pro-help/10`) |
| Create, publish or edit a UN in enterprise | Portal account with the ArcGIS Advanced Editing user type extension (Esri, Enterprise 12.1 "Utility Network services") |
| Query and trace | No extension needed (same page) |
| Which user types carry Advanced Editing | Included with Professional and Professional Plus; add-on for Mobile Worker, Contributor and Creator (Enterprise 12.1 licensing page, summarised in `pro-help/10`) |
| Older releases | Through 11.1 separate Utility Network, Trace Network and Parcel Fabric extensions existed; consolidated into Advanced Editing from 11.2 (`pro-help/10`). Esri's 10.8-era page names the "Utility Network user type extension" |
| Experience Builder trace widget | Esri's widget page states the signed-in account must hold the licence (`experience-builder/01`); that conflicts in spirit with "trace needs no extension" at the service level. Treat as: Verify against the Esri docs for your version before scoping a viewer-only audience |
| Map Viewer version switching | Esri blog lists an Advanced Editing extension among requirements (11.4 or later) |
| Version administrator | Not a licence: a role/privilege, section 7 |
| Error 003049 | Account is not licensed with the user type extension; ask the portal administrator to review the user type or add-on (`pro-help/10`) |

**Practitioner guidance.** Count licences by audience before launch. Viewers who only look at maps need none. Anyone who edits, validates or updates subnetworks needs the extension. Decide early whether trace-only roles use the extension, because the Experience Builder statement and the service-level statement differ.

## 4. Discovering and consuming the data

### 4.1 Items in the portal

Publishing creates portal items. Verify the exact item types in your portal after publishing; the descriptions below are from Esri's publish topics.

| Item | Source | Notes |
|---|---|---|
| Web layer (feature layer backed by the map service) | Share > Web Layer > Publish Web Layer | The unit you share; sublayer IDs matter (preserve layer IDs) |
| Web map | Built in Pro or Map Viewer by adding the web layer | Carries symbology, popups, shared named trace configurations for JS/Experience Builder (`js-api/03`, `experience-builder/01`) |
| Web experience / app | Experience Builder, custom JS | Bind to a web map or a service |
| Data store entry | Server Manager | Not an item; the registration the server needs |

**Layer ID discipline.** Esri recommends allowing unique numeric layer IDs in Map Properties before sharing so sublayer IDs survive an overwrite. Web maps and apps store layer IDs; if they shift, apps break after a republish (Esri Pro 3.7 "Publish and consume"). The same page tells you to uncheck the analyzer's ensure-IDs prompt if you skip assignment.

### 4.2 Sharing, groups and privileges

| Mechanism | Effect | Source |
|---|---|---|
| Sharing level (owner, group, organisation, public) | Who can see the web layer item | Esri Share As Web Layer pane |
| Feature layer editing privileges | Whether a user may edit; combined with version access level | Esri Pro branch version management page |
| Shared update group | **Every member becomes a version administrator for the layer** | Esri "Share branch versioned data" |
| Group ownership | Group membership is therefore a version-security decision, not only a visibility decision | Practitioner guidance |
| Pro analyzer 24099 | Pro needs all participating layers in the map; the web can consume without the full set | Esri Pro 3.7 "Publish and consume" |

**Mechanism.** The portal checks the account against the item (visible, editable, shared to which group), the server checks the service, and the version service checks the version's access level and the user's role. A request can pass the first two and fail the third.

**Example (electric).** A contractor group has update access to the editing service. Because group-based update sharing makes members version administrators, the contractors can reconcile and post anyone's version. The safer pattern is to share viewing or a narrow editing layer to the contractors and keep the full editing service with fewer people (Practitioner guidance).

### 4.3 Reading the service as a developer

Open `<root>/<serviceName>/FeatureServer` and look for `utilityNetworkLayerId`, then the system layers, as described in `learn/08` section 11 and `rest-api/05`. Open each extension URL and read `capabilities`. For the JavaScript SDK, load the web map and let the layer load the network definition (`js-api/03`). For Pro, add the service from the Portal tab (`learn/13` section 1.2).

## 5. What each client can and cannot do

This table is a summary. Clients change by release; each row notes the source. Items from third-party mirrors are marked.

| Client | Can | Cannot or limited |
|---|---|---|
| ArcGIS Pro, Portal tab (full service) | Edit in named versions, validate, update subnetworks, trace, diagrams, create and manage versions, reconcile and post, resolve conflicts (`learn/13`, Esri Pro branch pages) | Admin tasks need database and portal owner connections (`pro-help/10`) |
| ArcGIS Pro, service without UN layer | Edit; dirty areas created but not drawn | No trace, no diagrams (Esri) |
| Map Viewer (Enterprise 11.4+ per Esri blog; Enterprise doc page "Access branch versions") | Show a branch versioned layer, switch version with the Version management tool on the Settings toolbar; defaults to the default version when the map opens; one window per branch versioned layer | Does not support traditional versioned data (Esri). Versions do not persist in the saved web map; saving or refreshing resets to default (blog). Esri blog says create and reconcile are done in Pro; the blog is unclear on post from Map Viewer, so treat post from Map Viewer as unconfirmed: Verify against the Esri docs for your version |
| Field Maps | View connections and structural attachments, containment; named traces online (Enterprise 10.9+); edit geometry and attributes online or offline (Enterprise 11.2+ and the extension); offline supported through a sync-enabled service (summary in `learn/08` section 12, based on a third-party mirror of the Field Maps help: verify on Esri's site) | No UN associations editing, no UN editing tools, connectivity snapping unavailable, connected mode uses the default branch only, **dataset version 8 not supported** (`pro-help/09`) |
| Experience Builder | Utility Network Trace widget; Branch Version Management widget (`experience-builder/01`) | Validate topology and associations management less mature; same preconditions as the JS widgets |
| Web AppBuilder | Esri lists it as deprecated in Enterprise since March 2023, last included in Enterprise 11.5; Online retirement Q2 2027 with the replacement being Experience Builder (Esri WAB retirement page) | No UN-specific widgets were found in the sources read. Do not plan new UN apps on it: Verify against the Esri docs for your version |
| JavaScript SDK apps | Trace, validate, associations, version-aware editing with your own session handling (`js-api/01`, `js-api/05`) | You manage `gdbVersion`, `sessionID` and licence checks (`learn/14`) |
| Maps SDKs for Native Apps | See `learn/14` | Dataset version 8 not supported (Esri compatibility page) |
| REST / ArcGIS API for Python | Everything the services expose, including `VersionManagementServer` operations (`rest-api/04`, section 6.3 below) | You manage locks, session IDs and licences |
| Dashboards, simple viewers | Show the layers | Anything needing the UN or Version Management services is not available unless the app bundles it: Verify against the Esri docs for your version |

**Version constraints that surprise people.**
- A web layer published without Version Management always reads and writes the default version (Esri "Share branch versioned data").
- A client that supports versions may still restrict which versions it can reach. Field Maps connected mode reaches the default branch only, so protecting DEFAULT blocks field edits instead of redirecting them to a version (summary in `learn/08` section 12). Use the offline replica workflow if field crews need a review gate.
- Every client displays what the topology says. If a user edits in a client that cannot validate, dirty areas wait for someone to validate in Pro or a service-capable app (`learn/03`).

## 6. Branch versioning from the consumer side

### 6.1 Benefits (what it gives a consuming team)

Esri's Pro "Versioning types" page compares branch with traditional versioning.

| Aspect | Branch versioning (Esri) |
|---|---|
| Core purpose | Long transactions and multiuser editing for web feature layers in a Web GIS |
| Requirements | Dataset registered as branch versioned; Version Management enabled at publish |
| Clients | Not accessible in ArcMap or ArcGIS Pro before 2.1 |
| Depth | One level of named versions from the default version |
| Reconcile/post | Reconcile and post to DEFAULT; conflicts can be resolved across sessions |
| Access | One editor per named version holding an exclusive lock, or multiple readers (pre-12.0 model; see `learn/08` section 4 for the 12.0 change) |
| Undo/redo | Supported in named versions, not in the default version |
| Archiving | Archiving is enabled on registration and tracks inserts, updates and deletes (registration page) |
| UN | UN, parcel fabric and topology datasets support branch versioning |

For a utility the benefits are practical: crews design for days without disturbing live traces; each edit is attributable (editor tracking and archive fields such as `GDB_FROM_DATE`, `GDB_IS_DELETE`, `GDB_BRANCH_ID`, `GDB_ARCHIVE_OID`, `GDB_DELETED_AT`, `GDB_DELETED_BY` are added at registration); a QA gate sits between design and the live network; history supports moments (`learn/08` section 9).

### 6.2 The isolate-edits workflow, per client

Flow (the same in every client; the buttons differ):

```
 1 create named version (from DEFAULT)
 2 switch the map/layers to it
 3 edit (templates, associations, attributes), validate topology in the version
 4 save
 5 reconcile (pull DEFAULT edits into the version; conflicts found)
 6 review / resolve conflicts
 7 post (push to DEFAULT)
 8 validate and update subnetworks on DEFAULT, optionally delete the version
```

| Step | ArcGIS Pro (Esri Pro help) | Map Viewer | Field Maps | REST (`VersionManagementServer`) |
|---|---|---|---|---|
| Create | Versioning tab > Manage Versions > New (select the web feature layer in the Data Source group); or New Version with "Change to this new version"; or the Create Version geoprocessing tool | Not available (Esri blog) | Not available; offline replica workflow creates one version per downloaded map if configured at publish | `create`: `versionName` max 62 characters, no `.` `;` `'` `"`; `accessPermission` default `private` |
| Switch | Versioning tab change version, Versions view | Version management tool on the Settings toolbar | Connected mode: default branch only | `startReading` / `startEditing` with a `sessionId`, and `gdbVersion` on queries and `applyEdits` |
| Edit | Edit tab, templates, Modify Associations pane | Editing in the version where Map Viewer editing is enabled; UN-specific behaviour not documented in the sources read | Geometry and attributes; no associations | `applyEdits` with `gdbVersion` and `sessionID` |
| Validate | Validate Topology | No | Not in the app; edits leave dirty areas for Pro | `validateNetworkTopology` with the session |
| Reconcile | Versioning tab Reconcile; Reconcile/Post button in Versions view; Reconcile Versions geoprocessing tool | Not available (Esri blog) | Replica version: an administrator reconciles in Pro | `reconcile` (needs an exclusive lock, you must be the only user) |
| Resolve | Conflicts view / Conflict Manager | No | No | `conflicts`, `inspectConflicts`, `differences` |
| Post | Post button; fails if DEFAULT changed since the reconcile | See table above: unconfirmed | Admin posts the replica version in Pro | `post` with the same `sessionId` as the reconcile |
| Delete | Delete in Versions view | No | Replica versions cannot be deleted while an offline map references them | `delete` |

Conflict rules (Esri Pro "Reconcile and post"): target is always the default version; conflicts are resolved in favour of the edit version by default; the Reconcile dialog lets you define conflicts **by attribute** (default) or **by object**; an optional field conflict filter excludes fields from attribute-level detection. Reconcile warns about unreviewed conflicts; undo and discard cannot revert changes made after a reconcile completes. Post cannot be undone. Edits made after a post require reconcile, review and post again. Conflict by object on a UN is stricter: topologically related features can conflict in ways a plain attribute merge will not resolve (`learn/08` section 6, `pro-help/06`).

### 6.3 Scripted example (concepts from the ArcGIS API for Python guide, parameters from the REST pages)

```python
from arcgis.gis import GIS
gis = GIS(profile="enterprise_profile")
# flc = FeatureLayerCollection for the UN feature service; version_manager = flc.versions
with version_manager.get("UNADMIN.workorder_1234", "read") as version:
    version.mode = "edit"
    result = version.reconcile(end_with_conflict=True,
                               conflict_detection="byAttribute",
                               with_post=False, future=False)
    if result.get("success"):
        version.post(rows=None, future=False)   # rows=None posts everything
```
Class and method names come from the Python API guide referenced in `rest-api/04`; confirm them against the API version you have installed. The REST rules that apply: `reconcile` requires an exclusive lock; `post` must follow in the same session and DEFAULT must not have changed (`learn/08` section 4).

### 6.4 Pitfalls from the consumer side
- Map Viewer resets to DEFAULT on save or refresh, so a QA user who reviews a version in a saved map will think the edits vanished.
- A reconcile commits automatically; do not offer "discard" after it (Esri).
- A named version holds an exclusive lock in the pre-12.0 model: two people cannot edit one version (`learn/08` section 4). Split work or upgrade to 12.0 or later for one-writer-many-readers behaviour.
- Pro 3.7 and Enterprise 12.1 behaviours that depend on moments need topology enabled at that moment (`learn/08`, `pro-help/06`).

## 7. Security and permissions model for versions

**Access levels** (Esri, Pro "Manage branch versions"; blog confirms):

| Level | Who can view | Who can edit |
|---|---|---|
| Private (named only) | Owner and version administrators | Owner and version administrators |
| Protected | Any user | Owner and version administrators only |
| Public | Any user | Users with feature editing privileges, if the layer is editable |

Esri's blog describes the private level as viewable and editable by the owner, the feature layer owner and a portal administrator.

**Version administrators** (Esri, "Version administrator for branch versioned data", introduced Enterprise 10.8.1): the service owner (the user who published), portal administrators (default Administrator role), and users whose custom role includes the **Version Management, Manage All** privilege (under General privileges; the privilege compatibility slider must be at "View, edit, create and manage" for it to appear). A version administrator can view and edit others' versions, reconcile and post them, modify properties of all versions, delete branch versions, and manage locks.

**DEFAULT.** Its access is public when the geodatabase is created. Esri recommends setting it to protected if nobody should edit it directly; then only version administrators may edit it or post to it. Only the geodatabase administrator can change DEFAULT's access, with Alter Version or the Versions view, over a branch versioning database connection.

**What this means for governance**

| Decision | Recommended pattern (Practitioner guidance, consistent with Esri's blog) |
|---|---|
| DEFAULT access | Protected |
| Editors | Create their own named versions, public or private; they post nothing |
| Posting | A small group with Manage All or the service owner role |
| Groups | Do not share update access to a broad group, because membership grants version administration |
| Contractors | Narrow service or private versions; hand off with `alter` (`ownerName`) for QA |
| Locks | `purgeLock` discards unsaved edits in active sessions; allowed to the version owner, the service owner and a portal administrator (`learn/08` section 3) |

**Troubleshooting map for permission errors:** license (extension) first, then portal privilege and group, then version ownership/access level, then network ownership (`pro-help/10`). "Operation is only allowed by the owner of the version" is a version ownership problem, not a data problem.

## 8. Publishing workflow, verification and common failures

### 8.1 Workflow checklist (Esri Pro 3.7 "Publish and consume")

1. Enterprise geodatabase; connection's versioning type set to Branch; feature dataset registered as branch versioned (registers junction and edge object tables too).
2. Pro signed in as portal owner (Advanced Editing); connection as database owner.
3. Add the UN to a new map, include all participating classes; preserve layer IDs.
4. The map must have no definition queries, no hidden fields on the UN layer, no subtype group layers, and the unique value renderer unchanged.
5. Share > Web Layer > Publish Web Layer; Map Image; Feature checked under Reference registered data; Version Management enabled.
6. Feature properties: check Allow update of true curves and Only allow true curve updates by true curve clients.
7. Offline: enable Sync, choose a Version Creation option, include the Service territory class.
8. Analyze; fix errors, review warnings; Publish.
9. Protect DEFAULT; set sharing deliberately.
10. Add the web layer to a map and verify.

### 8.2 What to test after publishing

| Test | How | Pass condition |
|---|---|---|
| Services exist | Open `FeatureServer`, `UtilityNetworkServer`, `NetworkDiagramServer`, `VersionManagementServer` URLs | Each responds; `capabilities` read |
| Licence | Sign in as an editor and a viewer | Editor can validate; viewer can trace; viewer cannot validate |
| Version round trip | Create a named version, make one edit, validate, reconcile, post, delete | Edit appears on DEFAULT; no stale lock |
| Trace | Run a named trace configuration on DEFAULT and in the version | Same result outside the edited area; edit visible only in the version until posted |
| Dirty areas | Edit a geometry in the version | Dirty area appears; validate clears it |
| Diagram | Create a diagram from a selection | Succeeds |
| Layer IDs | Overwrite test publish in a staging copy | Web map layers still resolve |
| Offline (if used) | Take a map offline, edit, sync | Replica version or default sync as designed |
| Client matrix | Open in Map Viewer, Field Maps, Experience Builder | As section 5; version 8 issue for field apps |

### 8.3 Common failures

| Symptom | Likely cause | Where to look |
|---|---|---|
| Analyzer error 00270 | Definition queries or hidden fields on the UN layer | Esri publish topic |
| Analyzer warning 24099 | Pro map lacks participating layers | Esri publish topic |
| Publish refused or no Version Management | Data not branch versioned, or Feature not checked | Section 8.1 |
| No utility network or diagram service | Published without the UN layer | Section 2 |
| Error 003049 | Account lacks extension | `pro-help/10` |
| Tool greyed out | Wrong owner connection, not DEFAULT, topology state | `learn/13` |
| Web layer always edits DEFAULT | Version Management not enabled at publish | Esri "Share branch versioned data" |
| Version switch does not persist | Map Viewer behaviour | Section 5 |
| Layer IDs shifted after overwrite | Unique numeric IDs not preserved | Section 4.1 |
| Field Maps cannot open the network | Dataset version 8 | `pro-help/09` |
| `Update Subnetwork` or export fails on a version | DEFAULT-only operation, or owner restrictions | `learn/08` section 8, `pro-help/06` |
| Branch registration blocked | Dataset has unique indexes, archiving already on, no GlobalIDs, or no UTC editor tracking | Esri registration page |

Esri's registration page also advises loading all data before registering, because versioning adds tables, indexes and attributes that slow loading; unregistering needs an exclusive lock and deletes unposted edits in named versions.

## 9. Upgrades and patch-level issues

- Compatibility matrix and upgrade procedure are in `pro-help/09`: dataset v8 needs Pro 3.7 and Enterprise 12.1; new clients work with older networks; Field Maps and Native SDKs do not support v8; v7 remains the default for new networks.
- Upgrading means an exclusive lock, topology disabled, database owner connection and portal owner sign-in, geodatabase at the required level, and a backup (`pro-help/09`). After: re-enable topology, restart and review the service, re-add layers in maps, test field apps.
- After a server or geodatabase upgrade, re-read each extension's `capabilities`; a script that assumes a flag from a previous release will fail on a server that lacks it (`rest-api/01`).
- Patch notes: Esri notes in release history that Enable and Validate Network Topology can stall at very large dirty-area counts, that Update Subnetwork performance has improved across patches, and that Export Subnetwork has required the version owner in some releases (summarised in `pro-help/06`). These are tied to specific patches: Verify against the Esri docs for your version.
- Version service surface changes by release (`learn/08` section 3): locks model changed at 12.0; `lockInfos` and create-with-moment appear at 12.1; `versionInfos` `nameFilter` is documented at 11.6.
- Practitioner guidance: rehearse upgrades on a copy of the geodatabase and a staging portal, keep a list of every client and script that touches the service, and test each with a named version before cutover.

## 10. Decision table: file or mobile geodatabase versus enterprise

| Need | File or mobile gdb (single user) | Enterprise gdb through Enterprise |
|---|---|---|
| Learning, rule design sandbox, training | Good fit | Overkill |
| Migration staging, mapping tests | Good fit (`pro-help/11`) | Later, after staging passes |
| Multi-user editing | No: one editor at a time; a mobile gdb shows a `.geodatabase-conch` lock file (`learn/08` section 13) | Yes |
| Long transactions, QA gate, history | No branch versioning | Yes |
| Web or field apps, trace over REST | No services | Yes |
| Experience Builder, Field Maps, JS | Not possible | Yes (see section 5) |
| Licence | Pro Standard or Advanced; no portal | Pro plus portal accounts with Advanced Editing for create/publish/edit |
| Owners | No portal owner; OS authentication records trace configuration creators (`learn/13` section 6) | Database owner plus portal owner |
| Small utility with one editor and no web needs | Possible, with risks: no concurrent users, no version history | Better if growth is expected |
| Offline package for one person | Possible as a deliverable; check mobile geodatabase constraints | Offline via sync-enabled service |
| Scale and performance | Limited sizing guidance: Verify against the Esri docs for your version | Sizing in `learn/10` |

Heuristic (Practitioner guidance): if more than one person will ever edit, or any web or field client will consume the data, start on enterprise. Use single-user for sandboxes and staging, then move the finished schema with an asset package or rules export (`pro-help/08`).

## 11. Admin runbook: standing up an enterprise UN

Each step: action, owner/licence, verification. Cross-reference for tool names is `learn/13` section 4.

1. **Plan the audience.** List roles: viewer, trace analyst, editor, QA, version admin, field, contractor. Decide which need Advanced Editing. Decide the services shapes (section 2). Verify: licence count and group design written down.
2. **Prepare the platform.** Federated server, portal, supported enterprise geodatabase and DBMS version; install patches. Verify: Esri system requirements for your release; Enterprise 12.1 for dataset v8.
3. **Create the data owner and database connection.** Branch versioning type on the connection. Verify: connection properties show Branch.
4. **Choose the dataset version.** v7 default; v8 only for telecom or when needed; check client support (`pro-help/09`). Verify: client matrix signed off.
5. **Build the network in Pro** (Asset Package or manual), as the database owner with the portal owner signed in: `learn/13` section 2. Verify: Network Properties show configuration.
6. **Load data and enable topology** (database owner, DEFAULT, nonversioned stages only where Esri allows), validate, update subnetworks, QA. Verify: no dirty areas that you did not expect; trace tests pass (`learn/03`).
7. **Register the feature dataset as branch versioned** after loading. Verify: archive and `GDB_*` fields present.
8. **Register the database as a data store** with the server. Verify: validation passes in Server Manager or Analyze.
9. **Set DEFAULT protected** and define who is a version administrator (section 7).
10. **Publish** following section 8.1. Verify with section 8.2.
11. **Share** items to the right groups; avoid update-group over-sharing; set layer IDs.
12. **Publish additional services** (field, viewing) and configure web maps with named trace configurations (`js-api/03`, `experience-builder/01`).
13. **Operational jobs:** schedule validate and update subnetwork on DEFAULT after posting; reconcile and post cadence; version cleanup; backups; monitoring. Verify: a dry run through a full edit cycle.
14. **Document ownership handover:** who is portal owner; Update Portal Dataset Owner and item ownership transfer plan (`pro-help/10`).
15. **Upgrade plan:** compatibility, exclusive-lock window, rollback (section 9).

Maintenance windows: tasks that need an exclusive lock (upgrade, schema changes, owner change) stop the service and close connections first (`pro-help/09`, `pro-help/10`).

## Common misconceptions

| Misconception | Correction |
|---|---|
| "Publishing the UN means publishing one feature service" | A feature service with the UN layer brings Utility Network and Network Diagram services; Version Management is a further capability; validation is an extension (sections 2, 8) |
| "Trace users need an Advanced Editing licence" | Esri says query and trace do not need it; the Experience Builder page states otherwise for its widget, so confirm per app (section 3) |
| "Map Viewer can do the whole edit-reconcile-post cycle" | Per Esri's blog it switches versions; create and reconcile are in Pro; post from Map Viewer is unconfirmed (section 5) |
| "A web map remembers its version" | Versions do not persist; saving or refreshing resets to default (Esri blog) |
| "Protecting DEFAULT blocks all editing" | It forces edits into named versions; it also blocks Field Maps connected mode, which reaches the default branch only |
| "Group sharing is only about visibility" | Sharing to a shared update group makes members version administrators (Esri) |
| "Web AppBuilder is the way to build Enterprise apps" | Deprecated; Experience Builder is the replacement (Esri) |
| "The database is another way to edit after publishing" | Use services; the database connection is for configuration and QA |

## Quick checks

1. What are the UN dataset version, Pro version and Enterprise version? Do all clients support that dataset version?
2. Is the data branch versioned, and was Version Management enabled at publish?
3. Was the web layer published with the UN layer, or as plain feature layers?
4. Which service shape does the client use (editing, field, viewing)?
5. Which portal account is the portal owner? Which database user is the data owner?
6. Does the account hold Advanced Editing? What user type does it have?
7. Is DEFAULT protected? Who has Manage All? Which groups hold update access?
8. Is the user asking about license, version access or network ownership when they see a permission error?
9. Does the client need to validate or manage associations? If it is Field Maps or Map Viewer, plan a Pro step.
10. Which locking model applies: Enterprise 12.0 and later or earlier (`learn/08` section 4)?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/03-topology-engine-and-validation.md`, `learn/08-versioning-and-editing-workflows.md`, `learn/10-performance-scale-and-operations.md`, `learn/13-arcgis-pro-fundamentals-and-workflow.md`, `learn/14-developer-surfaces-and-sdk-fundamentals.md`
- `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`, `pro-help/10-publishing-ownership-licensing.md`
- `rest-api/01-utility-network-server-and-trace.md`, `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/03-network-diagram-service.md`, `rest-api/04-version-management-validation-feature-service.md`, `rest-api/05-feature-service-associations-appendix.md`, `rest-api/06-asynchronous-operations-job-status.md`
- `experience-builder/01-utility-network-widgets.md`, `js-api/03-network-class-loading-and-definition.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/3.7/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://doc.esri.com/en/arcgis-enterprise/latest/administer/utility-network-services.html
- https://modis.arcgis.com/arcgis/help/en/server/latest/publish-services/linux/utility-network-services.htm (a third-party mirror of an older Esri Server help page, 10.8 era; federation and extension licence wording)
- https://doc.esri.com/en/arcgis-enterprise/latest/create/access-branch-versions.html
- https://www.esri.com/arcgis-blog/products/arcgis-enterprise/announcements/working-with-versioned-data-in-map-viewer
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/versioning-types.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/manage-branch-versions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/reconcile-and-post-edits-to-a-branch-version.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/register-a-dataset-as-branch-versioned.html
- https://pro.arcgis.com/en/pro-app/3.6/help/data/geodatabases/overview/publish-branch-versioned-data.htm
- https://www.esri.com/arcgis-blog/products/arcgis-pro/data-management/version-administrator-for-branch-versioned-data/
- https://www.esri.com/arcgis-blog/products/arcgis-enterprise/data-management/branch-versioning-editing-administration
- https://doc.arcgis.com/en/web-appbuilder/latest/create-apps/wab-retirement.htm
- Existing skill files cited inline (which carry their own Esri sources): `learn/08`, `pro-help/09`, `pro-help/10`, `rest-api/04`, `experience-builder/01`.
