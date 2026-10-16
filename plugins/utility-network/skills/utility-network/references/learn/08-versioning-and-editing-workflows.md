# Utility Network: Versioning and Editing Workflows
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Read this file when the question is "how do several people safely edit a utility network, and what happens to topology, subnetworks and associations when their work is merged?" It covers branch versioning end to end (DEFAULT versus named versions, sessions and locks, reconcile and post, conflicts), the editing paths (Pro, feature services, Field Maps, offline, single-user), bulk loading, and editing the network structure itself. Builds on `learn/01-mental-model-and-life-of-an-edit.md` (the edit lifecycle), `learn/03-topology-engine-and-validation.md` (dirty areas, validate) and `learn/06-tiers-and-subnetworks-in-depth.md` (Update Subnetwork); this file does not repeat their mechanism, it shows how it behaves across versions. Practitioner guidance is labelled as such; everything else is from the Esri pages listed under Sources.

## Contents
1. Why the UN needs branch versioning
2. DEFAULT versus named versions
3. Version lifecycle and the Version Management service
4. Sessions, locks and concurrency
5. Reconcile and post: what happens to topology, subnetworks and associations
6. Conflicts and how they are resolved
7. Validate in a version
8. Update Subnetwork: DEFAULT versus named version
9. Moments and `queryNetworkMoments`
10. Editing in ArcGIS Pro
11. Editing through services (`applyEdits`, system layers)
12. Field Maps, mobile apps and offline
13. Single-user geodatabases (file and mobile)
14. Bulk loading and large batch edits
15. Editing the UN structure itself
16. How electric, gas, water and telecom differ
17. Recommended workflow per role
18. Gotchas list
19. Common misconceptions, quick checks, related files, sources

## 1. Why the UN needs branch versioning

**Definition.** Branch versioning is the geodatabase versioning model used for web (feature service) editing. All versions live in the same tables; each named version is a branch off DEFAULT, and every edit is archived in the base tables, so Esri notes the compress operation is not needed. Reconcile and post still merge branches.

**Mechanism.** Esri's FAQ states it is required that an enterprise utility network be registered as branch versioned to take part in services-based editing and archiving. The things the UN adds on top of ordinary features (the network topology, dirty areas, the Associations table, subnetworks, diagrams) are all stored and time-stamped in the same versioned, archived tables. That gives the engine three capabilities it relies on:

| Capability | Why the UN needs it |
|---|---|
| Isolation of long edits | A pole replacement or a main extension can take days; the topology and traces on DEFAULT stay stable while it is designed |
| Time-travel (moments) | Traces and diagram operations can run at the current moment or a historical moment, provided topology was enabled then (`pro-help/06-*.md`) |
| Services-based editing | Pro, web apps and mobile clients all edit through the feature service, whose `VersionManagementServer` extension provides create, reconcile, post and locking |

**Example (electric).** A crew designs a feeder extension in a version named after the work order. On DEFAULT, the operations team keeps tracing the old feeder. Nothing in the extension is visible to a DEFAULT trace until it is posted and DEFAULT is validated.

**Where it applies.** Enterprise geodatabases only. Esri's FAQ says single-user deployments on file and mobile geodatabases do not use versioned editing (section 13). During initial configuration you can edit the network nonversioned through a database connection, but Esri limits that to quality checks before enabling topology and publishing.

**Licensing.** The ArcGIS Advanced Editing user type extension is needed to create, publish and edit a UN in an enterprise geodatabase; query and trace do not need it (FAQ). For the Version Management service, Esri says the extension applies to certain operations from Enterprise 11.2 and that requirements changed for some operations in 12.0, without listing which; check Esri's license page for your release.

## 2. DEFAULT versus named versions

| | DEFAULT | Named version |
|---|---|---|
| What it is | The shared, authoritative state | A branch created off DEFAULT (`create` on `VersionManagementServer`) |
| Saves | Edits go straight into the data, like short database transactions | Edits accumulate privately until reconcile and post |
| Conflict detection | None; last save wins on the same feature (Esri branch-version scenarios page) | Reconcile with DEFAULT detects conflicts |
| Undo/redo | Not available when Version Management is enabled | Available |
| Topology enable/disable | Enable Network Topology runs on DEFAULT only | Cannot be enabled there; a version where topology was disabled cannot re-enable it and must reconcile to inherit DEFAULT's state (FAQ; `rest-api/02-*.md`) |
| Structure changes (rules, tiers) | Yes, on DEFAULT only | No |
| Validate | One session at a time | Allowed in the version by editors with permission |
| Export Subnetwork (with acknowledgment) | Yes | No, DEFAULT only |
| Branching depth | Parent of all | One level only: no versions of versions |
| Reconcile and post target | n/a | Always DEFAULT, never another named version |

**DEFAULT access level.** Esri describes two strategies: leave DEFAULT public (any editor with permission can edit it and post to it) or set it **protected** so only version administrators edit or post, which forces everyone into named versions. Practitioner guidance for a utility: protected DEFAULT, named versions for every edit, and a small group that posts.

**Version access permissions (Pro help, Versioning tab):**

| Level | Meaning |
|---|---|
| Private | Only the owner or the geodatabase administrator can view or modify |
| Protected | Anyone can view; only the owner or administrator can edit |
| Public | Anyone can view and edit (update, insert, delete) |

The REST `create` operation also accepts `hidden`; its default access is `private`.

**Patterns Esri documents (branch version scenarios page):**

1. One named version per work order or job, deleted after posting. Isolates months-long projects.
2. Protected DEFAULT.
3. Private named versions when a single editor works, to avoid lock contention.
4. Stage-based versions with QA gates (proposed, constructed, as-built): the editor hands ownership to the version administrator, who runs QA and posts.
5. Two published layers from the same data: an editable layer with Version Management on and a read-only query layer for viewers, who see only DEFAULT.
6. Bulk loads run by the data owner through the database, routine edits through the web layer.

## 3. Version lifecycle and the Version Management service

`https://<root>/<serviceName>/VersionManagementServer` exists when the **Version management** capability was enabled when the feature service was shared. It cannot be added after the fact for the offline replica scenario (Esri offline page), so decide at publish time. It is a server object extension that shares the feature service's instance settings.

Service-level operations (Esri): `create`, `delete`, `versionInfos` (name filter from 12.0), `lockInfos` (12.1), `purgeLock`. Per-version operations: `alter`, `conflicts`, `differences`, `inspectConflicts`, `post`, `reconcile`, `restoreRows`, `startReading`, `stopReading`, `startEditing`, `stopEditing`; further detail in `rest-api/04-version-management-validation-feature-service.md`.

| Operation | Key facts (Esri REST pages) |
|---|---|
| `create` | `versionName` max 62 characters and must not contain `.` `;` `'` or `"`; `description` max 64; `accessPermission` default `private`; optional `moment` (12.1) makes the version's common ancestor a past moment between DEFAULT's creation date and now |
| `alter` | Parameters `ownerName`, `versionName`, `description`, `accessPermission` (`private`, `public`, `protected`); only the version owner or the service's version administrator may run it. This is the ownership handoff used in QA workflows |
| `purgeLock` | Deletes all locks on a version (`versionName` as `owner.version`); unsaved edits in active sessions are lost; allowed to the version owner, the service owner and a portal administrator; introduced 10.7.1 |
| `stopEditing` | `saveEdits=true` keeps the session's edits; `false` discards them. A write lock is downgraded to a read lock, not removed |

Capability flags worth checking before scripting (introduced in the release shown, per the Esri service page): `supportsPartialPost` (10.9), `supportsAsyncReconcile` and `supportsAsyncPost` (10.9.1), `supportsPartialPostOperation` (11.5), `supportsMultipleReadersSingleWriterLocking` (12.0), `supportsLockInfos` and `supportsCreateWithMoment` (12.1).

**Naming (Practitioner guidance).** Version names are prefixed with the owner (the Esri example is `UNADMIN.ProjectA`). Encode the work order ID and discipline in the name within the 62 character limit; do not rely on the 64 character description for anything a script must parse.

## 4. Sessions, locks and concurrency

**Definition.** A `sessionId` is a client-generated GUID that identifies one edit or read session on one version. It is the lock token.

**Mechanism.**

```
client                         VersionManagementServer              version
  | startEditing(sessionId=G) ------------->  write lock taken  ----->  locked by G
  | applyEdits(gdbVersion=v, sessionId=G) -->  edits saved under G
  | validateNetworkTopology(.., sessionID=G)
  | updateSubnetwork(.., sessionId=G)
  | stopEditing(sessionId=G, saveEdits=true) -> write lock downgraded to read lock
```

Rules documented by Esri:

- Read and edit sessions use `startReading`/`stopReading` and `startEditing`/`stopEditing`; read and edit operations must use the same `sessionId`.
- `reconcile` needs an **exclusive** lock (a write lock with no read locks). After a reconcile, nobody else can obtain a read or write lock until `post` or `stopEditing` is called. Reconcile commits the edits automatically: you cannot undo them with `stopEditing(saveEdits=false)`.
- `post` must use the same `sessionId` as the preceding reconcile, and DEFAULT must not have changed since that reconcile.
- Operations that cannot get their lock fail; they do not queue.
- On the UN server, `sessionId`/`sessionID` is **required when editing a named version** (`validateNetworkTopology`, `updateSubnetwork`, and others) and must not be given for DEFAULT. A trace or query on a version held under an exclusive lock needs the lock holder's `sessionId`. The spelling differs between pages (`sessionId` vs `sessionID`); use the spelling on the operation's own page (`rest-api/02-*.md`).

**Locking model by release (Esri version resource page):**

| Release | Model |
|---|---|
| Enterprise 12.0 and later | Many readers, one writer. A writer takes a write lock; others can still take read locks. A reconcile still needs the exclusive lock |
| Enterprise 11.5 and earlier | Either many viewers or one editor. Starting an edit needs an exclusive lock with no read locks, and nobody else can read until `stopEditing` |

Esri's scenarios page adds that an editor who starts editing a named version takes an exclusive lock and nobody else can connect (describing the pre-12.0 behaviour); setting the version private keeps others out except elevated users.

**Example (water).** Two crews edit the same work-order version on 11.4. The second crew's connection fails because the first holds an exclusive lock. Fix by splitting the work into two versions, not by `purgeLock`, which discards the first crew's unsaved edits.

**Pitfall.** DEFAULT has no equivalent: multiple editors write to DEFAULT concurrently, and only one validation or enable session may run at a time on DEFAULT. Enable Network Topology blocks other DEFAULT sessions from validate or enable while it runs.

## 5. Reconcile and post: what happens to topology, subnetworks and associations

**Definition.** *Reconcile* pulls DEFAULT's changes into your version and flags conflicts. *Post* pushes your version's changes into DEFAULT. A version must be reconciled immediately before it is posted.

**Mechanism: the flow Esri recommends.** Edit, validate the work area, run QC, reconcile (dirty areas may remain), resolve conflicts, post, then validate and update subnetworks on DEFAULT.

```
 DEFAULT  ----o------------o-----------o----------> (others keep posting)
              \            ^ reconcile  ^ post
 version       o--edit--validate--edit--o--QC--o
```

| Item | Reconcile (DEFAULT into version) | Post (version into DEFAULT) |
|---|---|---|
| Network topology | The version inherits DEFAULT's current topology state; dirty areas are re-created for every feature and object edited in the version | Dirty areas are created in DEFAULT for the posted edits; validate them there |
| Dirty areas | Inherited ones must be validated before posting. Validating them lets you keep working, but posting is blocked until you reconcile again | Esri Support lists dirty areas reappearing after a reconcile as "As Designed" |
| Associations | Ordinary rows in the Associations system table, merged like other edited rows; nonspatial junction/edge object tables show in the Conflicts view | Posted with the version's edits |
| `SubnetLine` and subnetwork state | `SubnetLine` is considered in reconcile (`learn/01-*.md`, `learn/06-*.md`) | `SubnetLine` is not carried by post, because it is valid only in the version where the update ran; after posting, validate and run Update Subnetwork on DEFAULT |
| Diagrams | Diagram edits reconcile with a twist: where both versions changed the same diagram feature, the reconciled version's edit wins | Esri advises validating, then running Update Diagram (with "Update inconsistent diagrams only" unchecked) in the edited version before posting |

**Why dirty areas return.** The topology tables are not merged row by row; the engine records that something changed and revalidates. Esri's blog says dirty areas are created during reconcile and post for any edit made in a user version. This is why a clean version can show dirty areas again after reconcile.

**Example (gas).** A crew's version replaces a regulator station and adds a connected main. After reconcile, the area shows dirty areas again. The editor validates the work extent in the version, runs QC, reconciles once more to pick up DEFAULT changes, posts, and a scheduled job validates DEFAULT overnight. The pressure subnetwork is then updated on DEFAULT.

**How it appears:**

- Pro: Versioning tab (Reconcile, Post, Conflict Manager, Manage Versions); Utility Network tab, Network Topology group, Validate.
- REST: `reconcile` (parameters `sessionId`, `abortIfConflicts` default false, `conflictDetection` `byObject` default or `byAttribute` from 10.8.1, `withPost` default false, `async` from 10.9.1; response `hasConflicts`, `didPost`, `moment`, `success`) and `post` (`sessionId`, `rows`, `async`).
- Partial post: `post` with `rows` (array of `layerId` plus `objectIds`) from 10.9, with utility network class support from 11.3; from 11.5 Esri recommends the separate partial post operation. After a partial post you must reconcile again to see the posted features in the version. Practitioner guidance: avoid partial post of UN edits that depend on each other (a device and its associations, a line and the junction it connects to); a partial set can leave dangling associations or connectivity that DEFAULT's next validate flags.

**Pitfalls.**

- Reconcile is an exclusive-lock operation and auto-commits. Do not start it with unsaved work you might want to abandon.
- A post that creates a large number of dirty areas in DEFAULT is the usual cause of long first validates after a big project. Plan the validate window.
- Rule changes made on DEFAULT do not appear in an existing named version until it is reconciled (Esri network rules page, cited in `learn/03-*.md`).

## 6. Conflicts and how they are resolved

**Types Esri lists (manage branch version conflicts):** update-update, update-delete, delete-update, topological or relationship conflicts (a topologically related feature or relationship class changed in both versions), and, for telecom domain networks, **containment conflicts** (the containment hierarchy of a conflict container differs between versions without row-level updates).

**Detection.** `byObject` flags any row edited in both versions. `byAttribute` flags only rows whose edited attributes actually conflict, and field conflict filters can exclude fields (changing filters needs a service restart). Immediate calculation and constraint attribute rules are evaluated for features updated in both versions, and a constraint violation flags an update-update conflict. Reconcile checks referential integrity for relationship classes.

**Resolution choices.** Replace with current (edit) version, target (DEFAULT) version, or common ancestor, at attribute, feature, sublayer or layer level. Merge geometries works only when different areas of the shape changed. Reviewed flags and notes are available. Defaults matter: conflicts start resolved in favour of the **edit version**, and unreviewed conflicts are auto-resolved to the edit version on the next reconcile or post, clearing review notes.

**UN specifics.** Esri's UN-specific coverage is thin. Practitioner guidance, built from the mechanism:

- A conflict on one feature has knock-on effects the Conflicts view does not show: connectivity (a line and the device it snaps to), associations (a container and its content), and subnetwork membership. After resolving, always validate in the version and review error dirty areas before posting.
- Prefer `byAttribute` detection where your service supports it, to avoid false conflicts when two editors touched different fields of one device.
- For the diagram system, conflicts always resolve to the reconciled version.
- Plan work so two versions rarely edit the same pole, vault or station; coordinate by work order area.

**Example (telecom).** Two versions each reorganize splice-case contents. If the containment hierarchy differs without either changing a row, reconcile reports a containment conflict that no row-level view will show.

## 7. Validate in a version

- Validate runs in a named version when topology is enabled on DEFAULT (the version inherits the state). Required: topology enabled; enterprise input must be a UN service; Advanced Editing extension (Validate Network Topology tool page).
- REST: `validateNetworkTopology` with `gdbVersion`, `sessionID`, `validateArea`, `validationType` (`normal`, `rebuild`, `forceRebuild`) and the rest in `rest-api/02-*.md`.
- Pro: the **Validate** command (Current Extent) runs synchronously; the GP tool runs asynchronously through the `UtilityNetworkTools` service in the System folder (default timeout of 2 hours per Esri's blog).
- Validating clears dirty areas in the version only. Reconcile re-creates inherited ones; post creates them in DEFAULT.
- Attribute-rule validation is separate: batch calculation and validation rules are evaluated by the `ValidationServer` `evaluate` operation (`learn/05-*.md`, `rest-api/04-*.md`). Esri's Evaluate Rules tool page says it evaluates DEFAULT-version rules; do not assume it covers your named version.

## 8. Update Subnetwork: DEFAULT versus named version

Constraints from the Pro 3.7 tool page and the REST page:

- Enterprise: network branch versioned, input from a UN service, edits saved, topology enabled, no dirty areas intersecting subnetwork features, Advanced Editing extension, Standard or Advanced licence. Traditional domain networks only.
- REST `updateSubnetwork` (introduced 10.6): `gdbVersion` defaults to `sde.DEFAULT`; `sessionId` is required for a named version and omitted for DEFAULT; either `subnetworkName` or `allSubnetworksInTier=true`; `continueOnFailure`; `traceConfiguration`; `async`. Success returns `moment` and `success`.
- One update per subnetwork at a time; do not run several "All subnetworks in tier" runs concurrently.

| | DEFAULT | Named version |
|---|---|---|
| Subnetwork name and propagated fields | Updated in place on all traversed features | By default only features and objects edited in that version are updated (edit mode "without eventing") |
| Row deletion in Subnetworks table | Update Subnetwork can delete rows where `Is deleted` is true if the tier does not manage `Is dirty` | Not described for named versions |
| Edit mode | Setting in the subnetwork definition applies to both: without eventing (default) or with eventing | Same setting |
| Export Subnetwork with acknowledgment | Yes (portal owner) | No |

Consequence (Practitioner guidance, from the documented rules): updating a subnetwork in a named version is a validity check and a way to preview; the authoritative update happens on DEFAULT after the post, because `SubnetLine` does not post and named-version updates touch only the edited features. Esri's gas article, cited in Esri Foundation documentation, notes that without events can leave subnetwork names incomplete in named versions.

**Eventing and locks.** With eventing, DEFAULT holds a shared lock for the whole operation and can block reconcile (`learn/06-*.md`). Schedule updates outside the posting window.

## 9. Moments and `queryNetworkMoments`

A *moment* is a point in time (Unix milliseconds on most REST pages) at which a version had a given state. Moments make the UN auditable: traces accept `moment`, and diagrams and exports can run at a past moment if topology was enabled then.

`queryNetworkMoments` on `UtilityNetworkServer` takes `gdbVersion` (default `sde.DEFAULT`), `sessionId`, `moment` and `momentsToReturn` (`initialEnableTopology`, `fullValidateTopology`, `partialValidateTopology`, `enableTopology`, `disableTopology`, `definitionModification`, `updateIsConnected`, `indexUpdate`, `all`). It returns `networkMoments` (each with `moment`, `time`, `duration` in ms) and `validNetworkTopology`. The unit of `time` in the Esri example is not stated; verify against the Esri docs for your version before converting (`rest-api/02-*.md`).

Other uses of moments:

- Responses of most edit and admin operations include a `moment` (for example `stopEditing` from 12.0, reconcile, post, updateSubnetwork).
- `applyEdits` can return `editMoment` with `returnEditMoment=true` (ArcGIS Server services).
- `create` on `VersionManagementServer` accepts `moment` from 12.1, so a version can branch from a past state.
- `differences` can compare from a moment (`supportsDifferencesFromMoment`, 10.9).

**Practitioner guidance.** Use moments to answer "what did the network look like when the outage happened" only after confirming `validNetworkTopology` and that topology was enabled and validated at that time; the dirty-area page says analytics ignore edits not yet reflected in the topology.

## 10. Editing in ArcGIS Pro

**Quick-start flow (Esri, edit a utility network):** add the UN layer to a map; create a branch version (New Version dialog, Versioning tab, "Change to this new version"); locate the area; set snapping and create features from templates; validate topology; save; then trace or diagram. Esri notes this is not the full QA process (conflicts, upstream trace, reconcile).

**Edit templates.**

- Ordinary feature templates carry asset group/type and default attributes. In the UN, snapping follows junction and edge connectivity rules; you may turn snapping off but cannot change which layers features snap to.
- **Group templates** bundle a primary template with secondary templates and builders so one action creates several features (for example a pole plus transformer plus service point). If the primary template creates a UN feature, an **Associations** tab appears; tick "Add associations when creating new assets" to generate associations. Those associations apply only to features the group template creates, not the contents of preset templates assigned to it.
- **Preset templates** create features with associations defined for them (Esri edit page).

**Modify Associations pane.** Create, select, modify and delete associations; tabs Connectivity, Containment, Attachment; add features with Add features or Load selected. Creation requires a supporting network rule; structural attachment and containment also require an association role on the asset group/type set earlier with Set Association Role. Deletions are marked and applied on save; Refresh reverts unapplied changes. Other creation paths: Import Associations tool, ArcPy, attribute rules (`learn/05-*.md`, `pro-help/04-*.md`).

**Attribute rules during edit.** Immediate calculation rules (autonumbering asset IDs, copying attributes from a container), constraint rules and the Foundation's template rules fire as the edit is saved; batch rules wait for evaluate. In a named version they run in the version; in Update Subnetwork they fire only with eventing. The Foundation's attribute rules also create associations on placement (`learn/05-*.md`).

**Dirty areas.** Any creation, move, delete or change to a network attribute or association creates a dirty area; non-network attribute edits do not. Validate before tracing.

**Asset package versus manual loading.** An asset package (`pro-help/08-*.md`) is the way to stand up a Foundation schema with Apply Asset Package and load starter data. Editing afterwards is the same as any UN. For ongoing production edits, do not reapply the package; use templates and the service.

**Pro ownership.** Routine editing, validation, rebuild and Update Subnetwork run through the service and need no owner connection (Esri tasks page). Structure changes need owner connections (section 15).

## 11. Editing through services (`applyEdits`, system layers)

**The feature service is the edit path.** A UN-backed `FeatureServer` knows associations and dirty areas, and exposes them as system layers. Find them via `utilityNetworkLayerId` on the service, then read that layer's JSON for the related system layer IDs (associations, dirty areas); layer IDs are service-specific (`rest-api/05-feature-service-associations-appendix.md`). `validationSystemLayers` (10.7+) lists validation error layers; topology layers (10.8.1+) are composite layers referencing error and dirty-area sublayers (`rest-api/04-*.md`).

**`applyEdits` parameters relevant to versions (Esri):**

| Parameter | Behaviour |
|---|---|
| `gdbVersion` | Target version; only when the layer's `isDataVersioned` is true; if omitted, the published map's version |
| `sessionID` | Client GUID that isolates the session's edits on a branch version (long transaction); introduced 10.6 |
| `useGlobalIds` | Identify features by `globalId`; requires `supportsApplyEditsWithGlobalIds` |
| `rollbackOnFailure` | Default true: all or nothing |
| `async` | 10.9.1; requires `supportsAsyncApplyEdits`; returns `statusUrl` then `resultUrl` |
| `returnEditMoment` | `editMoment` in the response (ArcGIS Server services) |

The Esri `applyEdits` page does not cover association edits; that is in the UN appendix: write rows to the associations system layer with `useGlobalIds: true`, integer `ASSOCIATIONTYPE` codes, and optional `applyEditsOptions: {"utilityNetworkOptions": 1}` to bypass validation. That option makes writes faster, defers invalid associations to the next validate, and is for trusted bulk loads only (`rest-api/05-*.md`). In the JS SDK use `generateAddAssociations`, `canAddAssociation` and `generateDeleteAssociations` (JS names are `gdbVersion` and `globalIdUsed`; see `js-api/05-editing-associations-validation.md`).

**Typical sequence for an app editing a named version** (Practitioner guidance assembled from the per-operation pages):

1. `create` a version (or find one with `versionInfos`).
2. `startEditing` with a new GUID.
3. `applyEdits` against the layers with `gdbVersion` and the session.
4. `validateNetworkTopology` for the edited extent with the same session.
5. `stopEditing(saveEdits=true)`.
6. `reconcile` (new exclusive session), resolve conflicts, `post`.
7. Validate and `updateSubnetwork` on DEFAULT.

Whether your client (Pro, JS SDK component) manages the session for you depends on the client; verify against the Esri docs for the SDK version in use.

**Async.** Validate, enable, update subnetwork, reconcile, post and `applyEdits` accept async from 10.9.1; poll the `statusUrl` (`rest-api/06-*.md`).

## 12. Field Maps, mobile apps and offline

**What Esri's Field Maps page documents (Field Maps help, utility network topic; known gap for this skill, so treat as a summary and verify on the current Field Maps help):**

| Area | Supported | Not supported or limited |
|---|---|---|
| Viewing | Connections and structural attachments layers, containment (View contents, View container) | |
| Tracing | Named traces configured in Pro (upstream, downstream, isolation, subnetwork, connected, loops); needs Enterprise 10.9+ | Not offline; selection results capped at 500 elements (raise with the `maxTraceResults` MDM parameter) |
| Editing | Geometry and attributes of network features, online or offline; needs Advanced Editing extension and Enterprise 11.2+; Esri calls it a limited capability | Subtype group layers, **utility network associations**, connectivity-based snapping, UN editing tools |
| Networks | Electric, gas, water, stormwater, wastewater | Not ArcGIS Online |
| Versions | Connected mode connects only to the **default branch** of a branch-versioned service; set DEFAULT protected to block field edits | |
| Dirty areas | Edits to geometry or network attributes create dirty areas | Must be validated in Pro or Maps SDKs or traces may be wrong |
| Offline | Attribute rules are not in offline map areas; they apply after sync | |

The compatibility page adds that Field Maps and the ArcGIS Maps SDKs for Native Apps do not currently support UN **version 8** with Enterprise 12.1; create or upgrade to an earlier version if you need them (`pro-help/09-*.md`).

**Offline editing (Enterprise offline page, branch versioned data).** Two workflows:

| | Default version | Replica version |
|---|---|---|
| Versions created | None | One per downloaded map |
| Edits synced to | DEFAULT directly | The replica version; an administrator reconciles and posts |
| Conflicts | Last sync overwrites | Detected at reconcile and resolved by an admin |
| QA | None | Possible, including attribute rule checks |

Requirements: publish with Version Management enabled; dedicated server instance type; for replica workflow set Version Creation to one version per downloaded map and enable replica tracking; limits on replica names (30 characters); a replica version cannot be deleted while an offline map references it. The page does not mention the UN. Esri's UN FAQ states offline editing workflows are supported with utility networks via a sync-enabled feature service.

**Practitioner guidance for the field.**

- Use the replica workflow for any crew edit of a UN; the review gate lets a QA person validate, reconcile and post, since the field app cannot create associations or validate.
- Put associations (a pole attachment, a vault containment) in an office step in Pro, or use attribute rules triggered by field edits where your Foundation does this.
- Do not give field apps access to the UN dataset version they do not support; check version first.

## 13. Single-user geodatabases (file and mobile)

- No branch versioning, no feature services, no `VersionManagementServer`, no REST or JS, Pro only (SKILL.md deployment table; FAQ).
- One editor at a time. A mobile geodatabase (SQLite) lets only one user modify data at a time, shows a `.geodatabase-conch` lock file beside the data, and may leave `.geodatabase-wal`, `.geodatabase-shm` or `.geodatabase-journal` files after a crash. Closing the project releases the lock.
- Everything else behaves the same: dirty areas, validate, Update Subnetwork run in Pro against the geodatabase directly, and the "default version only" restrictions in the tasks page do not apply.
- Enable Network Topology with **Only generate errors** requires nonversioned data (`learn/03-*.md`), which is naturally the case here. One practitioner report of inconsistent behaviour on file geodatabases is in `learn/03-*.md`.
- File geodatabase concurrency details are not in the sources read for this file: Verify against the Esri docs for your version.
- Good uses: rule and tier design sandbox, migration staging, training, a UN for a very small system. Not good for: multi-user editing, services, mobile apps, Experience Builder widgets, REST/JS trace.

## 14. Bulk loading and large batch edits

**Definition.** Loading existing GIS data into the UN schema, or making edits that touch many features at once.

**Esri's loading path (Solutions configure pages, UN loading tutorial):**

1. Prepare the schema (Change Asset Package Spatial Reference, copy and set spatial reference, remove sample data).
2. Build mappings: Create Simple Data Mappings and Create Migration Workspace (Copy Fields), then **Load Data Using Workspace**; alternatives are the Append tool, a custom model, Data Interoperability or a partner tool. Use Load Data To Preview to test without writing to the target.
3. Deploy with Asset Package To Geodatabase; the tutorial advises unchecking **Post Process** on the first pass so the deployment does not fail on too many errors.
4. Run Enable Network Topology with a raised maximum error count (default 10,000) and optionally **Only generate errors** first (data must be nonversioned for that run), summarize errors with Summarize Utility Network Errors, fix in source, reload.
5. Configure the multiuser environment (register as branch versioned, publish with Version Management) after the network is clean.

The tasks page says Load data works with topology enabled or disabled, from a database connection or a service, with no versioning or owner connection requirement; and recommends importing large numbers of associations or subnetwork controllers while topology is **disabled**. Disabling creates one dirty area over the service territory; enabling validates all outstanding edits.

**Versioning and bulk edits (Esri scenarios page).** Esri suggests bulk loads by the data owner through the database (Append, Copy Features) while routine edits go through the web feature layer.

**Practitioner guidance:**

- Load order: structure and service territory, then junctions, edges, structure points, then junction objects and edge objects, then associations (they refer to GlobalIDs that must already exist), then subnetwork controllers. The Esri tutorial states no required class order; this ordering is a suggestion from referential dependencies.
- Preserve or deliberately re-key GlobalIDs; duplicates cause dangling associations (`learn/02-*.md`).
- For many edits on a live versioned network, do them in a named version in batches sized so validate finishes within the service timeout, not as one monster post. Esri's reported scale limit: very large dirty-area counts (millions) have stalled enable/validate on some releases (`pro-help/06-*.md`).
- Through services use `applyEdits` with `rollbackOnFailure` and `async=true` for large sets; use `utilityNetworkOptions: 1` only for trusted association loads.
- After a large post, schedule a DEFAULT validate (Esri blog suggests scripting at intervals) and then Update Subnetwork.

## 15. Editing the UN structure itself

Changes to rules, tiers, categories and so on are not edits; they are administrative operations with strict preconditions (Esri "network topology actions" page).

| Change | Topology state | Notes |
|---|---|---|
| Domain networks (standard, telecom), network attributes, terminal configurations, network categories (add, set, delete), tiers and tier groups (add), subnetwork definitions, telecom circuit properties, rules (add, delete), association roles (set) | **Disabled** | |
| Color sets/schemes, telecom combine/divide policies, asset group subtype edits, asset type domain values (add, edit, rename), wavelength scheme (add) | Enabled or disabled | |
| Deleting a terminal configuration, removing a terminal configuration assignment, unassigning an association role | Only **before the first enable** | |
| Deleting color sets, domain networks, network attributes, tiers, wavelength schemes, asset group subtypes, asset type domains | Currently not allowed | |
| Service territory extent update | Currently not allowed | |
| Add/delete trace configurations | Enabled or disabled; service; versioned data | No owner connection |

**Connection requirements.** All configuration changes (except trace configurations) use a **database connection**, on the **DEFAULT** version only, with both owner connections: the database utility network owner (database login) and the portal utility network owner (signed-in portal account). Import Rules requires disabled topology and DEFAULT. Create, enable/disable topology, repair/verify topology, Analyze Network Data, Apply Error Resolutions, Import/Export Rules, Update Is Connected and Modify Terminal Connections need both; Export and Import Associations and Import/Export Subnetwork Controllers need the database owner; Export Subnetwork with acknowledgments needs the portal owner. Enable Network Topology requires versioned data when it is run in the enterprise normal way, and "Only generate errors" requires unversioned data. Update Portal Dataset Owner reassigns the portal owner.

**What it means for versions.** A schema change disables topology (one big dirty area), changes rules on DEFAULT only, and named versions do not see the change until reconciled. Practitioner guidance: freeze posting, have editors post or abandon versions, change the structure in a maintenance window, re-enable topology, then ask editors to reconcile. For a new tier, expect to set subnetwork definitions, controllers and Update Subnetwork afterwards (`learn/06-*.md`).

**Tier changes in production.** Adding tiers and tier groups is allowed (topology disabled); deleting tiers is currently not. Practitioner guidance: rehearse tier and definition changes in a single-user copy first (`learn/04-rules-and-connectivity-design.md`, `learn/06-tiers-and-subnetworks-in-depth.md`).

## 16. How electric, gas, water and telecom differ

| Topic | Electric | Gas | Water/wastewater | Telecom |
|---|---|---|---|---|
| Typical version unit | Work order per feeder segment or design (Practitioner guidance) | Work order per main/regulator project; pressure subnetworks updated on DEFAULT | Work order per main replacement; large bulk edits from CMMS/asset sync | Project per build area or route; containment-heavy |
| Subnetwork update after post | Feeder subnetworks; phase propagation values depend on updates | Pressure systems; Esri's Gas Foundation uses without eventing | Many Foundation subnetworks have Manage IsDirty off (Water Foundation 1.1+) so subnetworks always show Dirty and Export (Clean only) is unavailable (`learn/06-*.md`) | **Not supported**: telecom domain networks have no subnetwork management; Update Subnetwork not used |
| Conflict hotspots | Poles with many attachments, substation containers | Valve/regulator stations, pipe segmentation | Hydrant/valve clusters, service lines | Containment hierarchies (explicit containment conflict type), fibre cuts and splices |
| Associations in field | Pole attachment, transformer in vault | Valve in valve box | Valve in valve chamber | Cable in conduit, fibre in cable, containment stored as foreign keys when possible |
| Operating state edits | Switching changes devices' state; do these on DEFAULT in operations tooling, not in design versions (Practitioner guidance) | Valve/regulator state | Valve open/closed | n/a |
| Dataset version | v7 current for traditional; v8 mainly telecom (Pro 3.7/Ent 12.1), not supported by Field Maps | Same | Same | v8 for telecom features |
| Service rules | Circuit/phase traces | Isolation traces | Isolation zones | Path/circuit traces need a UN service; single-user divide/combine caveat |

Telecom containment can be stored as foreign key fields on domain classes; if a feature already has a container, the extra association goes in the Associations table with `ContainerSourceID` set to a sentinel and `ContainerGlobalID` NULL (Esri associations page). That affects how conflicts and bulk association loads look in telecom.

## 17. Recommended workflow per role

Practitioner guidance unless stated; Esri-documented parts are marked.

**Field editor (online or offline)**

1. Work only in your own named version (a work-order version; DEFAULT protected). Esri documents that Field Maps connects only to DEFAULT in connected mode, so field-originating edits need the offline replica workflow or a Pro/web app for the version.
2. Create features from group/preset templates so associations are generated (Pro); in Field Maps, expect no association edits.
3. Validate the work extent (Pro/Maps SDK) before handing off; do not trace until validated.
4. Save, stop editing, transfer ownership or notify the QA reviewer. Do not reconcile or post yourself unless authorised.

**QA reviewer / version administrator**

1. Open the version (owner handoff via `alter`/Pro version properties).
2. Validate the area; review the Error Inspector and Dirty Areas.
3. Run attribute-rule validation (`evaluate`) and Data Reviewer checks if licensed.
4. Run QA traces (upstream/downstream/isolation) on the version.
5. Reconcile; review the Conflict Manager; resolve with intent; validate again; reconcile again if DEFAULT moved.
6. Update Diagram in the version if diagrams are in play.
7. Post (full post for dependent edits). Delete the version.
8. Validate DEFAULT and run Update Subnetwork for affected subnetworks (or confirm the scheduled job did). Esri recommends this order.

**Administrator (database owner and portal owner)**

1. Own DEFAULT: protect it, schedule DEFAULT validate and Update Subnetwork, monitor dirty areas and `queryNetworkMoments`.
2. Maintain `purgeLock` discipline: only for confirmed orphaned sessions.
3. Structural changes in a maintenance window (section 15); announce reconcile requirement.
4. Keep Pro, Enterprise and dataset version aligned (`pro-help/09-*.md`); verify mobile clients before upgrading to v8.
5. Capture licences: Advanced Editing for editors, validators and subnetwork updaters.

## 18. Gotchas list

1. Validating in a version blocks posting until the next reconcile; reconcile again before post.
2. Reconcile and post create dirty areas; a "clean" version does not stay clean.
3. `SubnetLine` is not posted; run Update Subnetwork on DEFAULT after posting.
4. Named-version Update Subnetwork touches only edited features unless the definition uses eventing.
5. Export Subnetwork with acknowledgment is DEFAULT only and needs the portal owner.
6. Enable Network Topology runs only on DEFAULT and blocks other DEFAULT sessions while it runs.
7. A topology disabled in a named version cannot be re-enabled there.
8. Reconcile auto-commits; unsaved intent is lost.
9. Only one level of named versions; post only to DEFAULT.
10. Locking model changed in 12.0 (many readers, one writer); behaviour on 11.5 and earlier differs.
11. `sessionId` required for named versions on UN operations, forbidden for DEFAULT; the spelling varies by page.
12. `purgeLock` discards unsaved edits.
13. Unreviewed conflicts auto-resolve in favour of the edit version.
14. DEFAULT edits have no conflict detection; use protected DEFAULT.
15. Field Maps connects only to DEFAULT in connected mode and cannot edit associations; v8 unsupported.
16. Attribute rules are not in offline map areas.
17. Rule changes do not show in an existing named version until reconciled.
18. Version names: 62 characters, no `.` `;` `'` `"`.
19. Post must follow a reconcile with the same `sessionId`; DEFAULT must not have changed in between.
20. Partial post of dependent UN edits can leave dangling associations (Practitioner guidance).
21. LRServer `createVersion`/`reconcileVersion` are legacy; use `VersionManagementServer` (`rest-api/04-*.md`).
22. Direct database editing of a published, versioned UN breaks the services-based model; restrict to initial configuration QC and owner bulk loads.

## Common misconceptions

- "Post validates the network." It does not; validation is separate and DEFAULT needs its own validate after a post.
- "A named version has its own topology enable state." It inherits DEFAULT's; you cannot enable it there.
- "Reconcile and post can target any version." Always DEFAULT, one branch level only.
- "Update Subnetwork in my version finishes the job." Named-version updates are partial by default; finish on DEFAULT.
- "Field Maps can do everything Pro can on the UN." It cannot edit associations, and it connects to DEFAULT in connected mode.
- "File and mobile geodatabases are just smaller enterprise ones." They have no versions, no services and one editor.
- "`purgeLock` is a safe unlock." It deletes locks and loses unsaved edits.
- "Telecom subnetworks work like electric feeders." Telecom has no subnetwork management; it uses circuits.

## Quick checks

- Enterprise or single-user? Is the network registered as branch versioned and was Version Management enabled at publish?
- DEFAULT or named version? Is DEFAULT protected? What is the Enterprise release (locking model)?
- Is the user's session holding a lock (`versionInfos`, `lockInfos` on 12.1)? Is the `sessionId` the one that started editing?
- Has the version been validated since the last reconcile? Are there dirty areas intersecting the subnetwork being updated?
- Which subnetwork edit mode (with or without eventing)? Is the update being run on DEFAULT?
- For field editing: which client, which UN dataset version, online or offline, default or replica workflow?
- For structure changes: topology disabled? Connected to DEFAULT through a database connection as the database owner with the portal owner signed in?
- Was a large bulk load staged with topology disabled and a raised maximum error count?
- Is this telecom (circuits, containment conflicts, no subnetworks)?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/03-topology-engine-and-validation.md`, `learn/04-rules-and-connectivity-design.md`, `learn/05-attributes-categories-and-attribute-rules.md`, `learn/06-tiers-and-subnetworks-in-depth.md`, `learn/07-tracing-in-depth-and-configuration-library.md`
- `pro-help/04-associations-editing-errors.md`, `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/08-asset-packages-foundations-migration.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`, `pro-help/10-publishing-ownership-licensing.md`
- `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/04-version-management-validation-feature-service.md`, `rest-api/05-feature-service-associations-appendix.md`, `rest-api/06-asynchronous-operations-job-status.md`, `js-api/05-editing-associations-validation.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/editing/edit-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/associations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-compatibility.html
- https://doc.esri.com/en/arcgis-pro/latest/help/editing/configure-a-group-template.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/manage-branch-version-conflicts.html
- https://pro.arcgis.com/en/pro-app/3.2/help/data/geodatabases/overview/branch-version-scenarios.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/reconcile-diagram-edits-and-post-changes-to-default.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/manage-mobile-gdb/mobile-geodatabase-and-locking.html
- https://developers.arcgis.com/rest/services-reference/enterprise/version-management-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/version/
- https://developers.arcgis.com/rest/services-reference/enterprise/create/
- https://developers.arcgis.com/rest/services-reference/enterprise/alter
- https://developers.arcgis.com/rest/services-reference/enterprise/reconcile
- https://developers.arcgis.com/rest/services-reference/enterprise/post
- https://developers.arcgis.com/rest/services-reference/enterprise/start-editing
- https://developers.arcgis.com/rest/services-reference/enterprise/stop-editing
- https://developers.arcgis.com/rest/services-reference/enterprise/purge-lock
- https://developers.arcgis.com/rest/services-reference/enterprise/updatesubnetwork-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/apply-edits-feature-service-layer/
- https://enterprise.arcgis.com/en/server/12.0/publish-services/linux/offline-maps-and-branch-versioned-data.htm
- https://earthquake.usgs.gov/arcgis/help/en/field-maps/android/use-maps/utility-network.htm (a mirror of the Esri Field Maps help topic; verify on Esri's own site)
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/configure-sewer-utility-network-environment.htm
- https://learn.arcgis.com/en/projects/load-data-into-a-utility-network/
- https://www.esri.com/arcgis-blog/products/utility-network/data-management/dirty-area-management-with-the-utility-network
- https://support.esri.com/en-us/bug/in-arcgis-utility-network-dirty-areas-reappear-during-r-bug-000156036
