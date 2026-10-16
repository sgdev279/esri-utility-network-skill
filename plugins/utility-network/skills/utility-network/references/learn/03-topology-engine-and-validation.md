# Utility Network: Topology Engine and Validation
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro 3.7 help and tool reference, ArcGIS Enterprise REST reference, Esri blog and Esri Support (full list at the end).*

## Why this matters / when to read this

Almost every "my trace is wrong" or "my edit does not show up" question in a utility network is a topology question: the map shows edit space, the trace reads the network topology, and a dirty area is the gap between them. Read this file when you need the mechanism (what the topology is, which edits create dirty areas, what validate actually does, how errors are stored and fixed) and a diagnosis flow for stale or wrong results. It goes one level beneath `pro-help/06-administration-subnetworks-topology-versioning.md` and `pro-help/04-associations-editing-errors.md`, and `learn/01-mental-model-and-life-of-an-edit.md` (the worked end-to-end scenario); this file adds mechanism, the error-storage generations, the resolution tooling and a decision tree.

## Contents

1. What the network topology is
2. Enable and disable, and what happens to existing data
3. Dirty areas: mechanics
4. Status bitmask and error-only rows
5. What Validate Network Topology does, step by step
6. Validation types, extent, async versus sync, cost drivers
7. Errors: where they live (v3 and earlier versus v4+)
8. Resolving errors: by hand, and in bulk
9. The "Only generate errors" option
10. Latency between an edit and a correct trace
11. Topology and versions
12. Decision tree: the trace result is stale or wrong, is it topology?
13. Common misconceptions, quick checks, related files, sources

## 1. What the network topology is

**Definition.** The network topology is the persisted, analysis-ready representation of the utility network: the elements (junctions and edges), their connectivity, associations, terminal paths and network attribute values that traces, subnetwork updates and network diagrams read. Esri describes the Enable tool as one that "evaluates and establishes connectivity between features" to build it, and says the topology is "necessary for analytic operations such as tracing and to use network diagrams". The internal tables are not publicly documented, so treat them as opaque.

**Mechanism: two copies of the truth.**

```
 EDIT SPACE (what editors touch)            NETWORK TOPOLOGY (what analytics read)
 feature classes, tables, associations  --> index of elements, connectivity,
 geometry, ASSETGROUP/ASSETTYPE,            terminal paths, network attributes
 terminals, network-attribute fields
        |                                            ^
        |  edit => dirty area (bookkeeping)          |
        +---------- Validate Network Topology -------+
                    (only moves dirty footprints across)
```

Why it is built this way (reasoning, not an Esri quote): a trace must answer in seconds over millions of features, so it walks a precomputed index instead of re-deriving connectivity from geometry. The price is that an edit lands in edit space immediately but reaches the topology only when a validate incorporates it.

**Example (electric).** An editor drags a service transformer 3 m along a pole line. The map redraws at once. A downstream trace started a minute later still walks the topology as it was before the drag until that footprint is validated.

**Where it appears.**

| Surface | How you see topology state |
|---|---|
| Pro | Network Properties > Network Topology section shows enabled or disabled (Esri FAQ). Dirty Areas sublayer shows un-incorporated footprints. |
| REST | `.../UtilityNetworkServer/enableTopology`, `disableTopology`, `validateNetworkTopology`; dirty areas are a system layer of the FeatureServer (read its ID from your service JSON). See `rest-api/02-topology-and-subnetwork-management-operations.md`. |
| arcpy | `arcpy.un.EnableNetworkTopology`, `ValidateNetworkTopology`, `RebuildNetworkTopology`, `DisableNetworkTopology`; exact Python signatures are not listed on the Esri pages read, so check the tool page for your version. |

## 2. Enable and disable, and what happens to existing data

### Enable Network Topology (tool page, Pro 3.7)

| Parameter | Default | Meaning |
|---|---|---|
| Input Utility Network | none | The network to enable |
| Maximum number of errors | 10000 | Cap on errors written to the dirty areas sublayer; -1 or blank is unbounded; Esri advises against raising it above 10000 because it lengthens the run |
| Only generate errors | unchecked (False) | Evaluate and record errors without enabling (section 9) |

Other documented requirements and behaviours:

- All utility network feature classes need a **spatial index**.
- Time and memory grow with feature count; "some configuration tasks are allowed only before the topology is enabled for the first time" (association roles and terminal configuration removal are examples; see `pro-help/02-structure-of-a-utility-network.md`).
- Enterprise: connect as the **database utility network owner**; the active portal account must be the **portal utility network owner**; run on the **default version**; the network must be **branch versioned**; while it runs, other sessions on default cannot validate or enable. Since **Enterprise 10.9.1** the run is asynchronous through the preconfigured `UtilityNetworkTools` geoprocessing service (System folder).
- Licensing: Standard or Advanced in Pro; enterprise deployments also need the ArcGIS Advanced Editing user type extension on the portal account.
- Network rules: Esri's topology page says applicable network rules must exist for features to connect (see `learn/04-rules-and-connectivity-design.md`); the Enable tool page states no minimum-rule requirement, so Verify against the Esri docs for your version before telling a user Enable will refuse to run without rules.

### What happens to existing data

The Esri tool page says only: "existing errors generate dirty areas" (errors found during enable are written as error dirty areas). It describes no other effect on existing data. What follows is derived from the pages cited in Sources, not stated by Esri as such:

1. Enable evaluates every feature against feature restrictions and network rules, so a freshly loaded, never-validated network typically produces many errors.
2. Features that pass are written into the topology; features that fail get error rows (and, for the REST operation, previous errors are deleted and replaced).
3. The topology is available for analytics only after enable finishes without hitting the error cap. When the cap is reached the operation is cancelled; errors found before the cap remain in the dirty areas table.
4. Enable and disable both mark every subnetwork controller, SubnetLine record and system diagram Dirty (subnetwork life cycle page), so plan an Update Subnetwork pass afterwards.

### Disable Network Topology

Disable is an administrative switch. Needed before changing rules, terminal configurations, network categories, subnetwork definitions and tiers, and recommended before bulk loads and association imports. Esri's Disable tool page does not mention locks or unsaved edits (Verify against the Esri docs for your version); enterprise needs the database utility network owner connection (or portal owner for a service) and only one session can run it. While disabled:

- Edits are **not tracked**; instead one dirty area covers the **service territory** extent and `Status` reads 0.
- Existing error dirty areas remain.
- On re-enable, outstanding edits are validated in one go, which can be very large; Esri does not recommend general editing while disabled.
- A topology disabled in a named version cannot be re-enabled there; enable runs on DEFAULT and the named version inherits the state when reconciled (Esri FAQ).

**Practitioner guidance.** Treat disable/enable as a maintenance window: stop the service, disconnect editors, run on a test copy first (Esri's rules tutorial gives the same advice for rule changes).

## 3. Dirty areas: mechanics

**Definition.** A dirty area is a record (in the Dirty Areas sublayer) that says "this footprint of edit space is not yet reflected in the topology". Dirty areas exist only while the topology is enabled, except for the single whole-territory area created by disabling.

### What creates one

| Cause | Dirty area? | Notes |
|---|---|---|
| Change geometry | Yes, **two** (envelope of old geometry and of new) | Esri dirty areas page |
| Change ASSETGROUP or ASSETTYPE | Yes | These fields define rule keys |
| Change a field defined as a network attribute | Yes | Esri's list of edit dirty areas names no other attribute edits (implied: other attribute edits do not create one) |
| Change associations (containment, attachment, connectivity) | Yes | Association dirty areas are expanded to full extent on partial validates (section 6) |
| Change terminal configuration information | Yes | Esri's wording: "Terminal configuration information" |
| Enable, validate or update-subnetwork finds a rule violation | Yes, an **error dirty area** | Each feature with one or more errors gets one dirty area encompassing its geometry |
| Disable topology | Yes, one covering the service territory | `Status` 0 |
| Reconcile/post in a branch version | Re-created for edits in the version | Esri blog: "in user versions, dirty areas are created during reconcile and post operations for any edit" |
| Edit an unlocatable nonspatial object | No | Never reaches the topology |
| Edit a locatable nonspatial object | Yes, on the first spatial feature in its containment hierarchy | Esri nonspatial objects and dirty areas pages |
| Telecom nonspatial objects | Tracked in the **dirty objects** table | Needed because some association types use foreign keys, not the Associations table |

### Fields on a dirty area

Esri names: the extent (geometry), the type of edit, the feature GlobalID, the editor, `Status` (bit-encoded), and a pop-up expression `Status Description`. Editor tracking is on, so you can symbolize by editor or edit time. The older blog describes a system-managed `UpdateType` field with a coded value domain (the example name is `Electric_42_UpdateType`); Esri's upgrade history says `UPDATETYPE` was removed from the dirty areas table at dataset v4 and `STATUS` repurposed, so on v4+ use `Status`. The v4+ attribute table carries error code and error message columns (section 7). Hiding the layer does not stop dirty areas being created.

### Growth and merging: what is and is not documented

Esri's pages **do not describe** how dirty areas grow, overlap or merge. What is documented:

- A geometry edit makes two areas, so a feature moved far makes two distant footprints.
- An error feature gets one area encompassing its geometry.
- Validate clips dirty areas to the extent you pass (Pro 2.5+); the part outside stays dirty.

Anything beyond that (for example whether overlapping areas are fused into one polygon) is not stated: Verify against the Esri docs for your version before telling a user how many rows to expect.

### Which edits matter (field-level check)

```python
# Illustrative arcpy sketch: list the network attributes whose edits create dirty areas
import arcpy
d = arcpy.Describe(r"<path to utility network>")
for na in d.networkAttributes:
    print(na.name)   # edits to the fields assigned to these attributes create dirty areas
```

Fields assigned to network attributes come from `Describe(...).networkAttributes` (`pro-help/03-creation-configuration-attributes-categories-rules.md`). Rule of thumb (Esri's list): geometry, asset group/asset type fields, network-attribute fields, associations, terminal configuration information.

## 4. Status bitmask and error-only rows

`Status` is a sum of bits. Values from Esri's table:

| Value | Meaning | Kind |
|---|---|---|
| 0 | Topology disabled | n/a |
| 1 | Feature inserted or updated | edit |
| 2 | Feature deleted | edit |
| 4 | Associated objects modified | edit |
| 8 | Feature error | error |
| 16 | Object error | error |
| 32 | Subnetwork error | error |

Sums are meaningful: 9 = modified feature that also has a feature error. Decode any number with `scripts/decode_dirty_status.py` (`--table` prints the bits).

**The rule that surprises people.** During validate, only edit dirty areas, and error dirty areas that also carry an edit bit (1, 2 or 4), are cleaned. **Error-only areas (8, 16, 32, 24, 40...) are ignored.** Mechanism in one line: an error row records that the last evaluation failed; nothing has changed since, so re-evaluating would give the same answer. A new insert, update or delete edit adds an edit bit (8 becomes 9) and that re-queues the feature.

```
Status 8  --validate-->  8   (ignored)
Status 8  --edit the feature-->  9  --validate-->  (cleared if fixed, 8 again if not)
Status 32 (subnetwork error): fixed by changing the feature, or the subnetwork definition
          (topology disabled), then Update Subnetwork
```

**Example (gas).** A regulator is typed as an asset type with no rule to its inlet pipe: `Status` 8, error 8. Pressing Validate ten times does nothing. Either retype the regulator (edit, then 9) or an admin adds the rule with topology disabled, re-enables, then edits or revalidates.

The `Error(s)` pop-up field gives a numbered message such as "10: Invalid connectivity - the edges are different subtypes and cannot connect" (Esri view-errors page). `Status` and `Error code` are columns of the Dirty Areas table and are not shown in Error Inspector (Esri); use the table when you need the raw bitmask.

## 5. What Validate Network Topology does, step by step

1. Collect dirty areas that intersect the requested extent, clipped to it (error-only rows are skipped).
2. For the features in those areas, check feature restrictions, network rules, edge connectivity policies, terminal data and geometry sanity (error IDs 0 to 46 in `pro-help/04-associations-editing-errors.md`).
3. Passing features: write into the topology, remove the dirty area. Failing features: create or refresh an error row (an error dirty area).
4. Subnetwork discovery: place a starting point on each feature with a dirty area and, for each tier whose **Manage IsDirty** is true, run a trace with that tier's subnetwork trace configuration to find the controllers of affected subnetworks, marking them **Dirty**. Esri says this trace is how dirty subnetworks are found.
5. Return results: tool `Output JSON` (dirty subnetworks by name, domain network, tier); REST `discoveredSubnetworks`, `validateErrorsCreated`, `dirtyAreaCount`, `fullUpdate`, `moment`, `success`.

What it does not do: update subnetworks (Update Subnetwork), recalculate `IsConnected` (Update Is Connected), evaluate attribute rules (the `ValidationServer` `evaluate` operation, `rest-api/04-version-management-validation-feature-service.md`), repair broken topology tables (Verify/Repair) or rebuild regardless of dirty areas (Rebuild).

"Success" means the job ran, not that every error is gone. Check `validateErrorsCreated` and `dirtyAreaCount`, or the Dirty Areas table.

## 6. Validation types, extent, async versus sync, cost drivers

### REST `validateNetworkTopology` parameters (Esri REST page)

| Parameter | Default | Notes |
|---|---|---|
| `gdbVersion` | `sde.DEFAULT` | Version to validate |
| `sessionID` | none | Required for a named version; omit for DEFAULT (the syntax example spells it `sessionId`) |
| `validationType` | `normal` | `normal`, `rebuild`, `forceRebuild` (the last two from Enterprise 10.9) |
| `validateArea` | none | Envelope with `xmin, ymin, xmax, ymax, spatialReference` |
| `validationSet` | none | `[{"sourceId": n, "globalIds": [...]}]`; usable alone or with `validateArea` |
| `returnEdits` | false | Ignored when `async` is true |
| `async` | false | true returns `statusUrl`; poll for `Pending`/`InProgress`/`Completed` |
| `outSR` | service SR | Enterprise 11.1+ |

Requires the ArcGIS Advanced Editing user type extension.

### The three validation types

| Type | What it processes | Use |
|---|---|---|
| `normal` | Edit dirty areas (and error areas with an edit bit) in the area/set | Routine |
| `rebuild` | Rebuilds the specified portion, working from the dirty areas in the inputs | After failures (Esri states `rebuild` uses dirty areas) |
| `forceRebuild` | Ignores dirty areas and applies to all features in the inputs | Topology looks inconsistent but no dirty areas explain it |

Esri's tool text: "Rebuilding within an extent ignores dirty areas and applies to all features there" (Rebuild Network Topology tool, which needs Enterprise 10.9+ and is async). Which Pro command maps to which REST value is not stated: do not assert a mapping.

### Extent behaviour

- Pro's Validate command: Current extent (default) or Entire extent; synchronous.
- Tool extent options: display, drawn, a layer's extent (all, selected or visible features), typed coordinates, clipboard.
- Dirty areas that cross the extent are clipped. After a partial validate the remainder is still dirty, and "a feature is not guaranteed to enter the topology until its entire dirty area has been validated" (Esri blog, Pro 2.5 era; re-test on current builds). Exceptions that expand to the full dirty area: association dirty areas and update-subnetwork error dirty areas.

### Async versus sync

| Path | Behaviour |
|---|---|
| Validate command (Pro ribbon) | Synchronous; client time-out about 10 minutes for most UN tools (Esri FAQ) |
| Validate / Rebuild tool on a service | Asynchronous through `UtilityNetworkTools` (System folder), which has its own longer time-out; the blog quotes a 2-hour default, so check your server |
| REST | `async=true` for the job pattern (`rest-api/06-asynchronous-operations-job-status.md`) |
| Concurrency | On DEFAULT only one session can validate (or rebuild) at a time; editing and tracing continue |

### Cost drivers

Documented: number of dirty areas and the extent; one trace per tier with Manage IsDirty; hierarchical networks put a feature in several tiers; very large dirty-area counts have stalled enable/validate on some releases (see `pro-help/06-administration-subnetworks-topology-versioning.md`). **Practitioner guidance:** validate small footprints often, schedule a DEFAULT validate (the Esri blog suggests scripting it), and keep the first-enable error cap at 10000 and triage by error ID.

## 7. Errors: where they live

| Generation | Where errors are stored | How you see them |
|---|---|---|
| **UN version 3 and earlier** | Three noneditable sublayers **Point Errors, Line Errors, Polygon Errors** under the network layer (Esri); the v3 page does not mention object errors | Attribute tables with fields Object ID, Origin Network Source ID, Origin Global ID, Destination Network Source ID, Destination Global ID, Error type, Error text, Global ID, Shape |
| **UN version 4 and later (v8 baseline)** | In the **Dirty Areas** sublayer/table and the Associations table (associations in error show an orange indicator in Modify Associations) | Pop-up `Error(s)` field; **Error Inspector** (Utility Network tab > Network Topology group; requires UN v4+); Dirty Areas table columns `Status`, `Network Source ID`, `Feature Guid`, `Error code`, `Error message` |

Notes:

- In both generations an error is created by exactly three operations: **enable**, **validate**, **update subnetwork**. Creating or importing an association does not create an error record; the tool or pane returns an error instead.
- v3 example from Esri: a point coincident with a line, no rule to connect them: one point error plus one line error, features not snapped.
- Error Inspector defaults to the **Map Extent** filter (errors in the current view only); turn it off to see network-wide errors. Selecting a row shows attributes on the Details tab; `Network Source ID` plus `Feature GUID` locate the feature. Esri does not list all columns, so confirm the exact names in your build.
- Dirty-object errors for nonspatial objects are found through the associated spatial features' dirty areas and the Modify Associations pane (FAQ).
- Check the dataset version first: `pro-help/09-dataset-versions-compatibility-upgrade.md`. A user quoting "Point Errors layer" is on an old dataset or reading old documentation.

## 8. Resolving errors

### 8a. By hand (normal editing)

Esri's workflow on the error page:

1. Identify: open the pop-up or Error Inspector, note error ID, `Network Source ID`, `Feature GUID`.
2. Choose the fix: Esri says Option 1 in the Solution column "usually has the least impact".
3. Edit data: geometry, attributes, asset group/type; use **Modify Terminal Connections**, **Modify Terminal Path** or **Modify Subnetwork Controller** panes where the error concerns terminals or controllers.
4. Admin options (marked in Esri's table) need topology disabled: add a rule, change a subnetwork definition, change an edge connectivity policy.
5. Validate. Errors are evaluated and removed the next time topology is enabled or validated; the dirty area remains until the cause is fixed.

Selected solutions from Esri's error ID table (paraphrased):

| ID | Cause | Data fix | Admin fix |
|---|---|---|---|
| 8 | No connectivity rule | Change AG/AT to match an existing rule | Add a connectivity rule |
| 9 | More than one rule applies | Use Modify Terminal Connections to name the terminal | Make exactly one rule apply |
| 10 | Connected edges differ in AG/AT | Match them, or insert a valid junction | none marked by Esri (a rule for the inserted junction must exist) |
| 13 | Midspan breaks the edge connectivity policy | Move to a permitted vertex, delete, or | Change the edge connectivity policy |
| 17, 18, 34, 35 | Containment/attachment relationship unsupported | Edit attributes | Add the containment or structural attachment rule |
| 23 | Asset type not defined for the asset group | Set a valid asset type | none |
| 36, 38, 39 | Terminal problems | Fix terminal values, split line, relocate device, edit path | none marked |
| 46 | System inconsistency | Revalidate the impacted dirty areas | none marked (Rebuild or Verify/Repair if it persists is practitioner guidance, not in Esri's table) |

Full ID list: `pro-help/04-associations-editing-errors.md`. The Esri table lists error 18 with a containment rule as its admin option even though 18 concerns structural attachment; treat that as a probable documentation slip and confirm in Network Properties which rule family is missing.

### 8b. In bulk: Analyze Network Data and Apply Error Resolutions

These are a migration-era pair, separate from Error Inspector:

| Step | Detail (Esri) |
|---|---|
| **Analyze Network Data** (Migration toolset) | Parameters: Input Utility Network, Output Location, Output Name (default `AnalysisResults`), **Set default resolution actions** (off by default). Creates a mobile geodatabase with `ErrorLocations` (points), `ErrorSummary` (multipoint grouping like errors), `ErrorRecords`, `ErrorResolution` (editable) and a group layer, plus a `RuleCandidates` .csv of rules that could resolve errors |
| Edit the `ErrorResolution` table | Set `ErrorAction` per error group. Actions: Do nothing (default), Update all / Update all but first, Delete all / Delete all but first, Create, Anchor, Snap, Cut. Offsets via `DeltaX`, `DeltaY`, `DeltaZ`, `DeltaStep`; `ActionClassGroupType` for create/update |
| **Apply Error Resolutions** | Parameters: Input Utility Network, Resolution Table, Output Location (optional), Output Name (optional). Writes .csv logs of modified features and unresolved errors |

Constraints: topology may be enabled or disabled for Analyze; Apply Error Resolutions needs a **nonversioned** network, a connection as the database utility network owner (enterprise) and Standard or Advanced licence; utility networks from a feature service are not supported. Not every error has an automatic action; Esri's table offers actions only for IDs such as 1, 2, 5, 10, 19, 20, 21, 23, 25 and for vertex-within-tolerance; rule and ambiguity errors (8, 9, 13) show "N/A". With defaults on, typical choices are Delete all but first for stacked points, duplicate vertices and self-intersections, and Cut for multipart lines.

**Practitioner guidance.** Use the bulk pair on a freshly migrated, nonversioned network before first publish; use Error Inspector and edits for day-to-day corrections on a versioned, live network.

## 9. The "Only generate errors" option

Enable Network Topology with **Only generate errors** checked evaluates the network and writes errors without enabling topology. Documented conditions: the data **must not be registered as versioned** (the opposite of a normal enable), errors go to the dirty areas table, the run stops at *Maximum number of errors*, and afterwards you inspect, fix and then enable. Esri's rules tutorial recommends it to check the effect of a rule change without enabling. One practitioner report (Pro 3.5.1) describes inconsistent results on file/enterprise geodatabases that worked on mobile geodatabases; that is version-specific, not documented behaviour (`pro-help/04-associations-editing-errors.md`).

## 10. Latency between an edit and a correct trace

Esri gives no fixed delay: there is no background process that validates for you. The latency is exactly the time until **someone or something runs validate over that footprint**, plus Update Subnetwork for anything subnetwork-based.

| Step | Who triggers it | Trace becomes correct for... |
|---|---|---|
| Save edit | Editor | nothing yet; dirty area created |
| Validate (command, tool, REST, or a schedule) | Editor, admin job, schedule | connectivity-based traces (Connected, Upstream/Downstream via topology, Loops, Shortest Path) in that footprint |
| Update Subnetwork | Editor/admin/schedule | Subnetwork, Controllers, Subnetwork-scoped isolation results, subnetwork names on features, SubnetLine, system diagrams |
| Update Is Connected | Admin | the `IsConnected` flag (traditional domain networks only) |

Safeguards: the Trace tool's **Validate Consistency** option (Pro Trace tool: unchecked by default; REST `traceConfiguration.validateConsistency`: default true, see `rest-api/08-trace-configuration-full-schema.md`) fails the trace when results touch dirty areas. Left off (the Pro tool default) the trace silently describes the old network. Dirty areas do not act as barriers. Diagram generation is refused where dirty areas intersect the selection. **Validate Locatability** guards unlocatable nonspatial objects.

**Practitioner guidance.** For a live system, publish a validation cadence (for example scheduled DEFAULT validate plus nightly Update Subnetwork) and tell users which freshness to expect.

## 11. Topology and versions

| Aspect | DEFAULT | Named version |
|---|---|---|
| Enable, Verify/Repair, most admin | Here only | Not allowed |
| Edit auto-save | Yes, cannot undo | No |
| Validate | An edit operation, only one session at a time | Can be undone; needs `sessionID` in REST |
| Topology state | Source of truth | Inherits DEFAULT on reconcile; dirty areas re-created for edits in the version |
| Posting | n/a | After validating in the version, post is blocked until you reconcile again |

Esri's recommended flow: edit, validate the work area, run quality control, reconcile (dirty areas may remain), resolve conflicts, post, then validate (and update subnetworks) on DEFAULT. Dirty areas re-appearing in a child after validating in DEFAULT is documented as expected (Esri Support, Pro 2.1.2); workaround: validate in DEFAULT, switch to the child, validate, reconcile, post. Rule changes do not appear in an existing named version until it is reconciled (Esri network rules page). Branch-versioning detail: `rest-api/04-version-management-validation-feature-service.md`.

## 12. Decision tree: the trace result is stale or wrong, is it topology?

```
START: trace result differs from what the map shows
 |
 1. Is topology enabled? (Network Properties; Dirty Areas Status = 0 everywhere?)
 |    no  -> enable (DEFAULT, owner). Nothing else is meaningful until then.
 |    yes
 2. Does a dirty area intersect the features/start point/path?
 |    yes, Status has an edit bit (1,2,4)  -> validate that footprint. Retrace.
 |    yes, Status error-only (8/16/32...)  -> read Error(s); fix by EDITING (section 8). Then validate.
 |    no dirty areas
 3. Was "Validate Consistency" off in the trace? 
 |    yes -> turn on; rerun; step 2 will now show the cause.
 4. Is the trace subnetwork-based (Subnetwork, Controllers, Upstream/Downstream in a tier, Isolation)?
 |    yes -> Subnetworks table: ISDIRTY / Invalid? -> Update Subnetwork (needs no dirty areas on its features)
 5. Does the feature lack a rule, terminal path or association (so it never connected)?
 |    -> that is configuration, not staleness: see learn/04-rules-and-connectivity-design.md
 6. Is it a nonspatial object that is unlocatable?
 |    -> add the association that locates it; enable Validate Locatability.
 7. Edits made in a named version and trace run on DEFAULT (or the reverse)?
 |    -> the trace sees the version it is run against; reconcile/post, validate on DEFAULT.
 8. Validate keeps failing, error 46, or topology seems corrupt?
      -> Rebuild Network Topology for the extent; if still wrong, Verify then Repair (DB owner and portal owner, DEFAULT).
```

Ask in this order; steps 1 to 3 explain most "ghost" results.

## Common misconceptions

- "Validate again" clears error rows. It does not; error-only rows need an edit.
- Validate and Rebuild are the same. Validate works from dirty areas; Rebuild ignores them.
- A green validate means no errors. It means the job completed.
- Saving an edit updates traces. Only validate does, and for subnetwork-based results also Update Subnetwork.
- Every attribute edit makes a dirty area. Only geometry, AG/AT, network-attribute fields, associations and terminal data do.
- Disable is a harmless pause. It stops tracking, dirties all subnetworks and queues a territory-wide validation.
- Partial-extent validate finishes the job. Remnants of clipped dirty areas stay dirty.
- Apply Error Resolutions is the Error Inspector for fixing live edits. It is a nonversioned, migration-stage bulk tool.
- Errors are in Point/Line/Polygon Error layers. That is UN v3 and earlier.

## Quick checks

- What is the dataset version (v3 or earlier versus v4+)? It decides where errors live.
- Is topology enabled? What does Status read in the Dirty Areas table?
- Which Status values are present: edit-only or error-only? Decode with `scripts/decode_dirty_status.py`.
- Is Map Extent filter on in Error Inspector?
- Which version is the user editing, and which is the trace run against?
- Was validation partial (extent) or complete? Did it run on a service (tool) or as the synchronous command?
- Is `validateErrorsCreated` true in the REST response?
- Has Update Subnetwork run since validate, and does the Subnetworks table show Dirty or Invalid?
- Did an admin change a rule while topology was enabled? (Not possible; check for a disable/enable cycle.)

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/06-tiers-and-subnetworks-in-depth.md`, `learn/04-rules-and-connectivity-design.md`
- `pro-help/04-associations-editing-errors.md`, `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`
- `rest-api/01-utility-network-server-and-trace.md`, `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/04-version-management-validation-feature-service.md`, `rest-api/06-asynchronous-operations-job-status.md`
- `scripts/decode_dirty_status.py`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/manage-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/about-error-features-v3.htm
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/view-error-features-v3.htm
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/analyze-and-address-errors.htm
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/apply-error-resolutions.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/rebuild-network-topology.html
- https://developers.arcgis.com/rest/services-reference/enterprise/validatenetworktopology-utiility-network-server/
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/disable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-upgrade-history.html
- https://www.esri.com/arcgis-blog/products/utility-network/data-management/dirty-area-management-with-the-utility-network
- https://learn.arcgis.com/en/projects/configure-rules-for-a-utility-network
- https://support.esri.com/en-us/bug/validating-dirty-areas-in-a-utility-network-reappears-a-bug-000113331
