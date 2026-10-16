# Utility Network: Worked Examples, End to End
> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: this file adds no new Esri facts. Every mechanism, parameter, default and error ID is taken from the other `learn/`, `pro-help/` and `rest-api/` files and, through them, from the Esri pages listed under Sources.*

## Why this matters / when to read this

The other `learn/` files explain one mechanism each. Real problems cross several of them at once: a missing trace result is a topology question, a rule question and a subnetwork question until you find which. Read this file after the fundamentals (`learn/01` to `learn/10`, `learn/13`, `learn/14`) to see them working together on ten complete scenarios, each written as: situation, what the person sees, reasoning chain (with the mechanism and the section that explains it), exact steps, expected result, and what would go wrong and why.

Conventions. Vocabulary is domain-neutral: a **device** (point that controls the resource, for example a valve, switch or regulator), a **line** (carries the resource), a **source** (a subnetwork controller: where the resource enters). Industry flavour is illustration only. Any number that is not an Esri default or limit is marked **(illustrative)**. Names in angle brackets are placeholders for your own schema. Steps assume ArcGIS Pro 3.7, Enterprise 12.1, UN dataset v8 unless stated; version floors are quoted from the files they come from. "Practitioner guidance" marks advice that is not an Esri statement.

## Contents

1. First edit to first correct trace
2. A new asset is invisible to a trace
3. Validate says clean, but the trace is still wrong
4. The subnetwork name or status is stale after an edit
5. Two editors, named versions, reconcile and post
6. A rule blocks a legitimate connection
7. Tier and subnetwork design from a described network
8. A trace returns too much or too little
9. Loading a large batch and getting error-only dirty areas
10. Upgrading the dataset version
- Common misconceptions, Quick checks, Related files, Sources

---

## 1. First edit to first correct trace

**Situation.** A crew adds an in-line device (a valve, a switch) to an existing line in an enterprise network. The line must end up as two lines meeting at the device, and a Connected trace from one side must reach the other. (Illustrative: a water gate valve, an electric disconnect or a gas line valve all behave identically.)

**What the person sees.** The device appears on the map where they clicked. Nothing else tells them whether the network knows about it.

**Reasoning chain.**
1. The edit lands in edit space only. Connectivity is built from geometric coincidence plus rules, and moves into the topology only at validate (`learn/01` section 4 steps 1 to 5; `learn/03` section 1).
2. Snapping needs a rule: Esri notes that snapping does not occur without one, and with none the pair gets error 8 at validate (`learn/04` sections 1 and 4).
3. The line must end exactly at the device. A device with terminals cannot sit midspan (`learn/02` section 6, error 38), so split the line at the device. If the device has no terminal configuration it uses Single Terminal and behaves as if it had none (`learn/02` section 6).
4. The edit creates dirty areas (a geometry change creates two) and nothing validates itself (`learn/03` section 3).
5. A Connected trace uses topology only; it ignores terminal directionality and subnetwork definitions, so it needs no controllers (`learn/07` section 13). That makes it the right first test.

**Exact steps (Pro, enterprise).**
1. Prerequisites an administrator must have in place (`learn/13` section 2): topology enabled; a junction-edge rule from the device's asset group and asset type to the line's pair (`Add Rule`, rule type junction-edge connectivity; terminal named if the device has terminals); the line's edge connectivity policy (default End vertex is enough here because both lines end at the device).
2. Open the map from the **Portal** tab (service layer), Versioning tab, **New Version**, tick **Change to this new version** (`learn/13` section 3.1; `learn/08` section 10). Never edit DEFAULT directly.
3. **Edit** tab, **Features**, **Create**; pick the device template and click on the line. Split the line at the device with the **Split** tool in the **Modify Features** pane (Esri's editing reference places it there and says the split features meet at a system junction; the ribbon location of Modify Features is not stated, so verify against the Esri docs for your version).
4. If the device has terminals: Utility Network tab, Network Topology group, **Terminal Connections**; set the terminal each line end connects to. Do not hand-edit `FROMDEVICETERMINAL`/`TODEVICETERMINAL` (`learn/02` section 6).
5. Utility Network tab, **Validate**, **Current extent** (synchronous). Open the Dirty Areas attribute table or **Error Inspector** (Map Extent filter on by default).
6. **Edit** tab, **Save**.
7. Trace pane, **Start** tab, **Add features**, click a line on one side; choose **Connected**; tick **Validate Consistency** (unchecked by default in the Pro tool; Esri trace tool page); run (`learn/07` sections 13 and 16). Pane tab and button labels follow `learn/13`; verify against the Esri docs for your version.

**Expected result.** After step 5 the Dirty Areas table has no `Status` 1/2/4 rows in the footprint and no error-only rows (8/16/32) there. The trace returns both lines and the device. If subnetworks exist, the feeder or zone containing the device is now Dirty; its stored name on the new device is not yet written (that is scenario 4).

**What would go wrong, and why.**

| Symptom | Cause | Where explained |
|---|---|---|
| Trace stops at the device | No rule, so error 8 and the pair stayed disconnected; the dirty area now shows `Status` 8 (error-only) and further Validate clicks do nothing | `learn/03` section 4; `learn/09` section 1.3 |
| Error 9 | Terminal not chosen, or two rules both match the terminal pair | `learn/04` section 7 |
| Error 38 | Terminal device left midspan on an unbroken line | `learn/09` section 2.1 |
| Error 13 | Device placed at an interior vertex while the line's policy is End vertex | `learn/04` section 8 |
| Trace runs but misses the device with no error | Validate not run and **Validate Consistency** off, so the trace read the old topology | `learn/03` section 10 |
| Trace on DEFAULT misses it | Edit is in a named version; the trace reads the version it is run against | `learn/08` section 2 |

---

## 2. A new asset is invisible to a trace

**Situation.** Yesterday a device was added. Today a downstream trace from upstream of it does not return it, and the editor swears it is snapped.

**What the person sees.** The device is on the map and in the attribute table; the trace result simply lacks it. No error message.

**Reasoning chain.** "Invisible" has five distinct causes, and each leaves different evidence. Work the cheapest evidence first (`learn/03` section 12 decision tree; `learn/09` section 1.1 ranking):

```
Does a Connected trace from a neighbour include the new device?
 |-- no  -> topology problem (A: dirty area, B: error row, C: unlocatable object, D: wrong version/unsaved)
 |-- yes -> topology is fine; the configuration or subnetwork state hides it (E)
```

**Exact steps.**
1. **Which version and is it saved?** Compare the version the editor used with the version the trace ran against (REST `gdbVersion`). Unsaved edits are not seen by a trace.
2. **Dirty Areas table** (Contents, UN layer, Dirty Areas, Attribute Table). Select by location. Decode `Status` with `python scripts/decode_dirty_status.py <value>`:
   - bit 1/2/4 present: not yet validated (A). Validate the footprint, retrace.
   - 8 or 16 only: in error (B). Read `Error message` or the pop-up `Error(s)` field (`learn/03` section 4). Fix by editing (retype, re-terminal, move) then validate; an admin rule fix needs topology disabled (scenario 6).
   - Status 0: topology disabled; edits are not tracked (`learn/03` section 2).
3. **Nonspatial object?** If the new asset is a junction object or edge object, it joins only through associations. An unlocatable object creates no dirty area and is absent from the topology until an association path reaches a spatial feature (C). Use Trace **Validate locatability** or add the association in Modify Associations (`learn/02` section 9).
4. **Rerun the trace with Validate Consistency on.** If it errors with 002041, a dirty area is on the path (`learn/09` section 2.4).
5. **REST check.** In the trace response look at `startingPointsIgnored` and `warnings`. A location without `terminalId` (devices) or `percentAlong` (edges) is silently ignored (`learn/07` section 2). Find the dirty-areas layer id from `systemLayers` in your service JSON, never from an example (`learn/02` section 10).
6. **Subnetwork-based trace?** (Subnetwork, Controllers, Upstream/Downstream within a tier, Isolation.) Check the Subnetworks table `ISDIRTY` for the owning subnetwork, and the new device's `SUBNETWORKNAME` (`Unknown` means not updated or no traversable path to a controller). Run Update Subnetwork (E; see scenario 4).

**Expected result.** Exactly one of the above explains it. After the fix a Connected trace includes the device first; subnetwork-based traces include it after Update Subnetwork.

**What would go wrong, and why.**
- Re-pressing Validate for a `Status` 8 row. Error-only rows are ignored by validate; only an edit (adding the edit bit, 8 becomes 9) re-queues the feature (`learn/03` section 4).
- Validating a small extent that does not cover the whole dirty polygon. Dirty areas crossing the extent are clipped and the remainder stays dirty; a feature is not guaranteed to enter the topology until its entire dirty area is validated (`learn/03` section 6; Esri blog from the Pro 2.5 era, re-test on your build).
- Assuming attribute edits create dirty areas. Only geometry, `ASSETGROUP`/`ASSETTYPE`, fields mapped to network attributes, associations and terminal data do (`learn/03` section 3).
- Blaming the trace when the asset type is simply not in the trace's tier or valid lists (`learn/06` section 4).

---

## 3. Validate says clean, but the trace is still wrong

**Situation.** Validate completed with no complaint, the Dirty Areas layer looks empty in the current view, and a downstream trace from a device returns a whole area that should have been cut off at a closed device. (Illustrative: a closed valve in a pipe network, an open switch in a wire network.)

**What the person sees.** A green completion message and a trace result that is too large.

**Reasoning chain.**
1. "Clean" has three weaker meanings than people assume. A finished job means the job ran, not that errors are gone (`learn/03` section 5); error-only rows (8, 16, 32) persist and the Map Extent filter of Error Inspector hides errors outside the view (`learn/13` section 1.4); and validate does not evaluate attribute rules (`learn/05` section 11).
2. A trace reads **network attributes and categories**, never raw fields. If the "state" field is not mapped to a network attribute, no barrier can see it, and an edit to that field also creates no dirty area, so validate had nothing to do (`learn/07` section 1; `learn/05` section 6).
3. If the barrier exists, it must apply to the right element kind. `traversabilityScope` (Pro: Apply Traversability To) of `edges` makes a device-status condition never fire (`learn/07` section 3).
4. Coded values compare by **stored code**, not description (`learn/07` section 3).
5. Tier-loaded configuration differs between surfaces. Pro auto-loads the tier's barriers; REST and arcpy do not (`learn/07` section 12).
6. Direction-based traces have their own staleness: no controller, a dirty subnetwork, or indeterminate flow with **Allow Indeterminate Flow** on, which includes ambiguous features (`learn/07` section 5).

**Exact steps (check in this order; stop at the first hit).**
1. Dirty Areas table, Map Extent filter off: any row with `Status` 8/16/32 or an edit bit near the result? If so, scenario 2 step 2.
2. Open the device in the attribute table. Is its state field value what you believe? Compare the stored code with the code in the barrier (`value` is a string in REST).
3. Network Properties, **Attributes and Assignments**: is the state field assigned to a network attribute for this device class? (Or `arcpy.Describe(un).networkAttributes`.)
4. Trace pane/tool: Apply Traversability To = both junctions and edges, or junctions for a device condition.
5. Rerun with **Allow Indeterminate Flow** off. Features that drop out were indeterminate (loops, several sources, valves "open" in the data) and need terminals, barriers or controllers (`learn/07` section 5).
6. Confirm the subnetwork (if the trace is directional) is Clean in the Subnetworks table; run Update Subnetwork if Dirty (`learn/06` section 7).
7. Compare Pro and REST: export the Pro configuration from `traceConfigurations/query` and diff the JSON (`learn/07` section 15; `learn/09` section 4).

**Expected result.** The cause is identified from evidence, usually one of: unmapped or mis-scoped barrier, stale stored state, or indeterminate flow. After correction, the trace stops at the device. The device must also be edited in the data if the data was wrong (for example the state field said Open); that edit makes a dirty area only if the field is a mapped network attribute, so validate again.

**What would go wrong, and why.**
- Adding the barrier to the request but not to the tier definition. Update Subnetwork and Export use the tier's configuration, so the trace and the stored subnetwork then disagree (`learn/06` section 4).
- Treating `Validate Consistency` as default-on. The Pro tool default is unchecked; the REST `validateConsistency` default is true. Set it explicitly in code (`learn/03` section 10).
- Fixing a dirty-area `Status` 32 by validating. That is a subnetwork error bit, fixed by Update Subnetwork after correcting the cause; it is unrelated to error ID 32 (`learn/06` section 12).

---

## 4. The subnetwork name or status is stale after an edit

**Situation.** A device was added to an existing subnetwork (a feeder, a pressure zone, a drainage area). The new device shows `SUBNETWORKNAME = Unknown`, and the subnetwork row in the Subnetworks table is Dirty.

**What the person sees.** A trace by subnetwork name misses the device, or the label shows Unknown. The Find Subnetworks pane shows a yellow warning.

**Reasoning chain.**
1. `SUBNETWORKNAME` is a stored snapshot written only by Update Subnetwork; traces see new connectivity right after validate, the stored names do not (`learn/01` section 3).
2. Validate marked the affected subnetwork Dirty after tracing from each dirty feature (`learn/03` section 5 step 4). That is expected, not a fault.
3. Update Subnetwork refuses to run if a dirty area still intersects the subnetwork's features (error 002041), if edits are unsaved, or if topology is disabled (`learn/06` section 10; `learn/09` section 3.1).
4. Status is Clean, Dirty or Invalid. Invalid (Enterprise 11.1+) is skipped by later updates until fixed and validated again. If the tier does not manage `Is dirty`, every subnetwork reads Dirty forever and that is normal (`learn/06` section 7).

**Exact steps (Pro).**
1. Save edits. Validate the footprint and confirm no dirty areas remain on the subnetwork's features (scenario 2 step 2).
2. Utility Network tab, Subnetwork group, **Find**; read **Status** and **Last Update**. Clear "Use the current map extent" to read the Subnetworks table instead of only subnetworks with a SubnetLine in view (`learn/13` section 1.4).
3. Run **Update Subnetwork** (tool or pane): Domain Network, Tier, Subnetwork Name (leave **All subnetworks in tier** off for one). For enterprise the input must be a utility network service (`learn/06` section 10).
4. Re-read Status and the device's `SUBNETWORKNAME`.

**Equivalent calls.**
- arcpy (keywords confirmed on the Esri Update Subnetwork tool page: `subnetwork_name`, `all_subnetworks_in_tier` with `SPECIFIC_SUBNETWORK`, `continue_on_failure`): `arcpy.un.UpdateSubnetwork(un, "<DOMAIN_NETWORK>", "<TIER>", all_subnetworks_in_tier="SPECIFIC_SUBNETWORK", subnetwork_name="<NAME>", continue_on_failure="STOP_ON_FAILURE")`.
- REST: `POST .../UtilityNetworkServer/updateSubnetwork` with `domainNetworkName`, `tierName`, `subnetworkName` (or `allSubnetworksInTier=true`), `gdbVersion`, and `sessionId` on a named version only (`learn/06` section 10; `rest-api/02`).

**Expected result.** The subnetwork becomes Clean, the new device carries the subnetwork name, `SubnetLine` is refreshed, and a subnetwork trace by name includes the device. Propagated values (for example a phase or pressure class) are written at the same time if the tier defines propagators (`learn/05` section 5).

**What would go wrong, and why.**

| Symptom | Cause | Fix |
|---|---|---|
| Update fails with 002041 | A dirty area still intersects (for example you validated only part of the area) | Validate the reported feature, rerun |
| Update fails with errors 24, 26, 40, 41, 42 | The new asset type is not in the tier's valid lists | Reclassify, or an admin adds it in Set Subnetwork Definition with topology disabled |
| Errors 28, 29, 30, 47 | Two sources reach each other with different subnetwork names, or tiers traverse each other | `learn/06` section 12; `learn/09` section 3.2 |
| Unknown persists on containers or structures | Include Containers/Content/Structures or the Update Structure/Domain Network Containers option is off | `learn/06` section 8 |
| Update "did nothing" in a named version | Default edit mode updates only features edited in that version | Run it on DEFAULT after the post (scenario 5) |
| Update stalls reconcile | Edit mode With eventing holds a shared lock on DEFAULT for the whole run | Schedule outside posting windows (`learn/06` section 10) |
| Attribute rules did not fire during update | Default edit mode is Without eventing | Only With eventing triggers rules (`learn/05` section 11) |

---

## 5. Two editors, named versions, reconcile and post

**Situation.** Editor A and editor B each work in their own named version. Both end up touching the same device and one line. A finishes first. DEFAULT is protected. Enterprise 12.1 (many readers, one writer locking; see `learn/08` section 4 for 11.5 and earlier).

**What the person sees.** B's post is blocked ("reconcile again"), B sees conflicts, dirty areas reappear in a version that was clean, and after A's post DEFAULT shows dirty areas and Dirty subnetworks that nobody edited today.

**Reasoning chain.**
1. A named version inherits DEFAULT's topology state. Reconcile pulls DEFAULT's changes into the version and recreates dirty areas for every feature edited in the version; post creates dirty areas in DEFAULT for the posted edits. Esri records dirty areas reappearing as As Designed (`learn/08` section 5; `learn/09` section 6).
2. Validating in the version blocks the next post until you reconcile again; post must use the same `sessionId` as the preceding reconcile and DEFAULT must not have moved since (`learn/08` sections 4 and 5).
3. Conflicts are detected at reconcile: update-update, update-delete, delete-update, topological or relationship conflicts. Unreviewed conflicts auto-resolve in favour of the **edit** version on the next reconcile or post (`learn/08` section 6).
4. `SubnetLine` is considered at reconcile but not carried by post, so subnetwork state on DEFAULT must be refreshed there (`learn/08` section 8).
5. Only one validate or enable session runs on DEFAULT at a time (`learn/03` section 6).

**Exact steps.** Editor A (the first to finish):
1. Validate the work area in the version; clear all edit-bit and error rows; QA traces in the version (Connected, then directional if relevant); run attribute-rule validation (`Evaluate Rules`) if batch rules exist (`learn/08` section 17).
2. Reconcile. Reconcile needs an exclusive lock and auto-commits: do not start it with work you may want to abandon. Review the Conflicts view.
3. Validate again (dirty areas were recreated), then post. REST: `reconcile` then `post` with the same `sessionId`; `abortIfConflicts` defaults to false, so set it deliberately in scripts (`learn/08` section 5).
4. Delete the version if it was per work order.
5. On DEFAULT: validate (asynchronously), then Update Subnetwork for the subnetworks reported in `discoveredSubnetworks`, then optionally Update Is Connected (`learn/10` section 11.1).

Editor B (second):
1. Reconcile now. Conflicts appear on the shared device and line. Choose per feature: current (edit) version, target (DEFAULT) version or common ancestor; merge geometry only if different parts of the shape changed. Practitioner guidance: prefer `byAttribute` conflict detection where supported so two editors changing different fields of one device do not conflict (`learn/08` section 6).
2. After resolving, validate in the version and read the error dirty areas. The Conflicts view does not show knock-on effects on connectivity, associations or subnetwork membership.
3. Reconcile again if DEFAULT moved, then post. Then repeat step 5 of editor A.

**What must be re-validated or re-updated on DEFAULT after each post.**

| Item | Why | Source |
|---|---|---|
| Validate on DEFAULT | Post created dirty areas there | `learn/08` section 5 |
| Update Subnetwork on DEFAULT for discovered subnetworks | `SubnetLine` not posted; named-version updates touched only edited features | `learn/08` section 8 |
| Update Is Connected (if used) | `ISCONNECTED` is a snapshot | `learn/01` section 3 |
| Update Diagram (non-system diagrams) | Validate marks diagrams inconsistent | `learn/01` section 4 step 7 |
| Re-check rule changes | Rule changes reach an existing version only on reconcile | `learn/04` section 6 |

**Expected result.** DEFAULT has both editors' edits (with B's conflicts resolved on purpose), zero edit-bit dirty areas after the DEFAULT validate, subnetworks Clean after update, and the versions deleted.

**What would go wrong, and why.**
- Both editors post without a final reconcile. The second post is blocked, by design.
- Lock contention on 11.5 and earlier: a second user cannot connect to a version another user is editing. Split work into two versions; do not use `purgeLock`, which discards unsaved edits (`learn/08` section 4).
- Skipping the DEFAULT update. Subnetwork names on DEFAULT stay partial, `SubnetLine` is stale and exports (Clean only) are unavailable.
- Partial post of dependent edits (a device without its associations) can leave dangling associations that DEFAULT's next validate flags (Practitioner guidance, `learn/08` section 5).
- Unreviewed conflicts silently resolving to the edit version.
- Session IDs: `sessionId` is required for named versions on UN operations and must be omitted for DEFAULT; the spelling differs by page (`sessionId`/`sessionID`) (`learn/08` section 4).

---

## 6. A rule blocks a legitimate connection

**Situation.** A new asset type (illustrative: a "bypass connector" device) is approved by engineering and must connect to a main line. Editors report that it will not snap, and validate flags the connection.

**What the person sees.** The snap cursor does not engage, or after validate the device shows error 8 (Status 8) and stays disconnected.

**Reasoning chain.**
1. Rules are default-deny permissions keyed on class, asset group, asset type and terminal (`learn/04` sections 1 and 3). A brand-new asset type has no rules, so nothing may connect until some are written.
2. Rules sit on top of feature restrictions, which cannot be changed. A device cannot be coincident with another device (`learn/04` section 1). Before writing a rule, confirm the class pair is structurally possible (`learn/02` section 7.3).
3. A rule problem has three look-alikes that are data problems: wrong asset type chosen, terminal not selected (error 9), edge connectivity policy (error 13). Esri's advice is that fixing the data is usually less risky than adding a rule, and that too many rules cause additional errors (`learn/04` section 10).
4. Rule changes need topology disabled, DEFAULT and both owner connections, and in enterprise the service stopped; they reach existing named versions only on reconcile (`learn/04` section 6).

**Exact steps.**
1. Capture the error ID and the pair from the pop-up `Error(s)` field: from class/asset group/asset type, to class/asset group/asset type, terminal if any.
2. Rule out data causes: is the type right (error 23 would mean a bad group/type pair)? Does the device have a terminal configuration, and was a terminal chosen (error 9)? Is the device midspan on an End-vertex line (error 13/38)?
3. Decide the rule type from the geometry: point to line at a line end is **junction-edge connectivity**; a transition between two lines through the device is **edge-junction-edge** with the device as Via; point to point is junction-junction (`learn/04` section 2).
4. Rehearse on a copy. Export the baseline: `Export Rules` (All). Test the change by running Enable Network Topology with **Only generate errors** on a non-versioned copy (`learn/04` section 10).
5. In the maintenance window: stop the service; connect as the database utility network owner with the portal owner signed in, on DEFAULT; **Disable Network Topology**.
6. Add the narrowest rule. Illustrative CSV row for `Import Rules`, or the equivalent `arcpy.un.AddRule(in_utility_network, rule_type, from_class, from_assetgroup, from_assettype, to_class, to_assetgroup, to_assettype, {from_terminal}, {to_terminal})` (signature from `learn/04` section 6):
   `Junction Edge Connectivity,<DEVICE_CLASS>,<GROUP>,<BYPASS_CONNECTOR>,<TERMINAL>,<LINE_CLASS>,<GROUP>,<MAIN_TYPE>,,,,,`
   Name the terminal when the type has terminals; avoid `*` unless every terminal may touch that line (the water tower example produced error 9; `learn/04` section 7).
7. **Enable Network Topology**. Restart the service and Pro; named versions pick up the rule on reconcile.
8. The failed feature is an error-only row. Esri says features with errors are evaluated the next time topology is enabled or validated (About error features), but its dirty-areas page says validate ignores error rows without an edit bit. So after step 7 check the Dirty Areas table; if the row remains, edit the feature (retype and retype back, or re-snap) so the edit bit re-queues it, then validate (`learn/03` section 4).

**Expected result.** The pair connects at validate, the dirty area clears, a Connected trace crosses the device, and the exported rule CSV shows exactly one new row. Re-enable marks every subnetwork Dirty, so plan an Update Subnetwork pass (`learn/03` section 2).

**What would go wrong, and why.**

| Symptom | Cause |
|---|---|
| New error 9 after the fix | Rule too broad (All terminals or a second overlapping rule); the engine cannot choose (`learn/04` section 7) |
| Rule exists but nothing changes | Service not restarted, named version not reconciled, or the row is error-only, survived the enable and was not edited (`learn/04` section 13) |
| "Cannot add rule" | Topology still enabled, wrong owner connection, not DEFAULT, or the pair violates a feature restriction |
| Neighbouring features break | The topology was disabled and re-enabled; everything outstanding was validated and errors surfaced elsewhere |
| The wrong rule family chosen | Edge-junction-edge needed (a type change across the device) but only junction-edge written, so error 10 remains |
| Deleted a rule to "undo" | `Delete Rule` is permanent and disconnects nothing until the next enable/validate, then features fail; keep the export (`learn/04` section 6) |

---

## 7. Tier and subnetwork design from a described network

**Situation.** An architect describes two networks and asks which tier definition to use and what tiers, controllers and name fields to create. This scenario shows how to turn the description into the five decisions that cannot be undone.

**What the person sees.** A free-text description, for example:
- **Network X.** "Source stations feed lines at a high level, which step down through transformation points to a medium level and then to a low level. A given asset belongs to exactly one level. Where levels meet, the transforming device is shared."
- **Network Y.** "Supply points feed a whole system; the system is divided into pressure zones; each zone is divided into areas we can shut off with valves. A pipe is in all three at once."

**Reasoning chain.**
1. The partitioned/hierarchical choice and the source/sink choice are made once in `Add Domain Network` and are effectively permanent; domain networks cannot be deleted and tier definition shapes terminals, validation cost and tools (`learn/06` section 2).
2. Partitioned: tiers in a linear order, a feature belongs to **one** tier, controllers/barriers may belong to subnetworks of two tiers, topology type radial or mesh. Hierarchical: a feature may be in several tiers, tiers sit in tier groups, only mesh, rank automatic (`learn/06` sections 2 and 3).
3. Controllers: a terminal on a device or junction object. Partitioned requires directional terminals with an upstream and a downstream; hierarchical accepts directional or bidirectional (`learn/02` section 6; `learn/06` section 5).
4. Source versus sink: source-based means the resource flows away from controllers; sink-based means towards them, and in a sink network rank 1 is the tier at the ultimate destination (`learn/06` section 3).

**Exact steps (a design record).**

| Decision | Network X | Network Y | Reason (source) |
|---|---|---|---|
| Domain network type | Traditional | Traditional | Subnetworks needed (telecom has none; `learn/06` section 1) |
| Tier definition | **Partitioned** | **Hierarchical** | One tier per asset versus asset in several tiers at once (`learn/06` section 2) |
| Controller type | Source (stations/transformers) | Source (supply points) | Resource flows away from the controller (`learn/06` section 2). A drainage network would be Sink |
| Tier groups | None | One group (a single-sector network still needs one) | `learn/06` section 3 |
| Tiers and rank | Level 1, 2, 3 at ranks 1, 2, 3; you assign rank (pass it explicitly even though the Tiers page describes a default) | System, Pressure, Isolation; add **highest first** (first created is rank 1), rank automatic | `learn/06` section 3 |
| Controller asset types | Transforming devices, with a **directional** terminal configuration (own configuration, not shared with ordinary devices) | Regulators or supply devices, directional or bidirectional | `learn/02` section 6; `learn/06` section 5 |
| Subnetwork name fields | One system field `Subnetwork name` | The first tier of the group names a string field (length 2000, default `Unknown`); later tiers reuse it | `learn/06` section 3 |
| Valid lists | List only asset types that truly belong; they are **enforced** (errors 24, 26, 40 to 42 otherwise) | Same, per tier | `learn/06` section 4 |
| Manage IsDirty | On if Clean-only export is needed; off makes every subnetwork read Dirty | Same trade-off; some Foundations ship it off for speed | `learn/06` section 7; `learn/10` section 4.3 |
| Support disjoint subnetworks | Off by default; enable deliberately | Always on | `learn/06` section 9 |

Procedure order, all with topology disabled, on DEFAULT, as database owner with portal owner signed in (`learn/13` section 2.1): Add Domain Network; (Network Y) Add Tier Group; Add Tier for each tier **before any data is appended** (the tool adds a non-nullable name field and requires empty classes; tier name unique in the network, at most 64 characters); terminal configurations; Subnetwork Controller category; Set Subnetwork Definition per tier. Topology type (Radial/Mesh) has no current effect on tracing or subnetwork management; record the intent but do not design around it (`learn/06` section 3). A UN can hold at most 63 tiers across all domain networks.

**Expected result.** Network X: three subnetwork layers, each feature carrying one name, hand-off controllers visible in two tiers. Network Y: each pipe carries three names (system, pressure, isolation), update order System then Pressure then Isolation, and a trace at the Pressure tier stops at controllers of its own tier (`learn/07` section 12).

**What would go wrong, and why.**
- Choosing partitioned for Network Y, then needing the same valve in three nested scales. There is no conversion; the domain network cannot be deleted.
- Adding tiers after data was loaded (the tool errors) or forgetting that a hierarchical tier's rank follows creation order (`learn/06` section 3).
- Giving controllers a shared terminal configuration, then having to change it. Esri advises a dedicated configuration for controller asset types and no later changes; configurations are permanent after the first enable (`learn/02` section 6).
- Naming each controller as a different subnetwork when they feed one zone. Use one subnetwork name and unique controller names (`learn/06` section 9).
- One tier spanning several levels because a station crosses them. Practitioner consensus: separate ranked tiers and model station internals with containment (`learn/06` section 3).

---

## 8. A trace returns too much or too little

**Situation.** A downstream trace from a device is meant to return the section until the nearest closed device. Case A returns the whole zone (too much). Case B, after someone "fixed" it, returns three features (too little).

**What the person sees.** A selection of the wrong size, in Pro or in a REST response.

**Reasoning chain.** A trace expands outward; at each element it asks whether it is connected, allowed by terminal paths, stopped by a **traversability** barrier (condition then function) and then by a **filter** (filter barrier then filter function barrier) (`learn/07` section 1). The result then goes through containers/content/structures, barrier inclusion and output filters. Too much means nothing stopped it; too little means something unexpected stopped it early.

**Case A: too much. Exact steps.**
1. Isolate one barrier. Remove all but a single condition barrier and test it alone.
2. Confirm the attribute is mapped (scenario 3 step 3), the scope covers junctions for a device condition, and the value is the stored code string.
3. Confirm flow direction: with controllers, is there a clean subnetwork; with `useDigitizedDirection`, is `FLOWDIRECTION` populated (domain/tier and propagation are then ignored) (`learn/07` section 5).
4. Rerun with **Allow Indeterminate Flow** off to see what was ambiguous.
5. Use a function barrier as a safety cap while testing. REST shape (from `rest-api/08`): `"functionBarriers":[{"functionType":"add","networkAttributeName":"Shape length","operator":"greaterThan","value":"1000","useLocalValues":false}]` (the 1000 is illustrative). A cap on a midspan apportionable attribute makes the whole feature the barrier, so totals can fall short of the threshold (`learn/07` section 3).
6. If the request is an isolation trace, confirm a **filter barrier** exists: isolation without one finds nothing useful, and the filter (for example an "isolating" category plus an operable attribute) is what defines which devices count (`learn/07` section 4).

**Case B: too little. Exact steps.**
1. Read the tier's subnetwork definition: a tier-loaded condition barrier or the valid lists may be stopping the trace. Pro auto-loads these; REST does not, so compare (`learn/07` section 12).
2. Check **Include Barrier Features** (default true). Off hides the stopping features; with a barrier on a midspan edge the whole edge may still be selected (`learn/07` section 3).
3. Check for **Ignore Barriers At Starting Points**: a start sitting on a barrier device returns nothing unless this is on (`learn/07` section 3).
4. Check output filters and output conditions. Filtered-out features are still traced but not reported (`learn/07` section 8). Check Include Containers/Content/Structures (all default off), which hide customers or services modelled as contents.
5. For a start on an edge, a long unsplit line selected whole can look too large; use the Aggregated Geometry result for a partial edge (`learn/07` section 14).
6. Check scope again: `filterScope` and `traversabilityScope` default to both, but a saved configuration may restrict them.

**Illustrative request (placeholders; validate with `python scripts/build_trace_request.py --check req.json`).**
```json
{ "traceType": "downstream",
  "traceLocations": [ { "traceLocationType": "startingPoint", "globalId": "{00000000-0000-0000-0000-000000000001}", "terminalId": 1 } ],
  "traceConfiguration": {
    "domainNetworkName": "<DOMAIN>", "tierName": "<TIER>", "includeBarriers": true, "allowIndeterminateFlow": false,
    "traversabilityScope": "junctionsAndEdges",
    "conditionBarriers": [ { "name": "<STATE_ATTRIBUTE>", "type": "networkAttribute", "operator": "equal", "value": "<CLOSED_CODE>", "combineUsingOr": false, "isSpecificValue": true } ],
    "functionBarriers": [ { "functionType": "add", "networkAttributeName": "Shape length", "operator": "greaterThan", "value": "<CAP>", "useLocalValues": false } ] },
  "resultTypes": [ { "type": "elements" } ] }
```

**Expected result.** The trace stops at the first closed device on each branch. The cap never fires in production runs; its job was to expose the missing barrier. The final configuration is saved as a **named trace configuration** (UN v5+) so every user gets the same behaviour, and shared to web maps with the **Active** check box (`learn/07` section 15).

**What would go wrong, and why.**
- A condition with `isSpecificValue` false compares to another attribute named in `value`; people use it expecting a constant.
- Category names are matched exactly; a typo silently matches nothing (`learn/05` section 8).
- Multi-tier traces reload each tier's barriers, so a barrier written in one tier's attribute names may mean nothing in the next (`learn/07` section 3).
- Fixing the symptom with a very broad output filter, then reporting a result that quietly omits customers.
- Treating flow as hydraulics. Direction is a path-finding estimate (`learn/07` section 5).

---

## 9. Loading a large batch and getting error-only dirty areas

**Situation.** An existing dataset of hundreds of thousands of features is loaded into a new utility network schema. The first Enable produces a very large number of errors, and repeated Validate runs change nothing.

**What the person sees.** The Dirty Areas table full of `Status` 8 and 16 rows, an Enable that stops at the error cap, and validate "succeeding" without reducing the count. (Numbers below are **illustrative**; Esri publishes no volume limits, `learn/10` section 2.)

**Reasoning chain.**
1. Disabled topology tracks no edits: one dirty area covers the service territory, and re-enable validates everything outstanding (`learn/03` section 2). Esri recommends loading and importing associations and controllers while disabled (`learn/08` section 14).
2. Enable evaluates every feature against restrictions and rules; a never-validated load typically produces many errors. Enable stops at **Maximum number of errors** (default 10000; do not raise above it) (`learn/03` section 2).
3. Error rows are error-only (no edit bit), so validate ignores them. They clear only when the cause is fixed and either the feature is edited or the area is re-evaluated by a fresh Enable (`learn/03` sections 4 and 9; the REST enable path deletes and replaces previous errors, `learn/09` section 1.5).
4. Error volume, not feature count alone, drives enable time (`learn/10` section 3). So triage by error ID, not by feature.
5. **Only generate errors** evaluates and records errors without enabling, but requires **unversioned** data, while a normal enable needs branch-versioned data (`learn/13` section 2.2).

**Exact steps.**
1. Stage in a copy (file or mobile geodatabase for iteration). Tiers are defined **before** data is appended. Disable attribute rules for the load, and keep GlobalIDs preserved so associations still point at rows (`learn/05` section 15; `learn/02` section 5). Load order is Practitioner guidance: structure and territory, junctions, edges, structure points, then junction/edge objects, then associations, then controllers (`learn/08` section 14).
2. Confirm spatial indexes on all UN classes; on a first Asset Package deployment uncheck Post Process (`learn/08` section 14).
3. Run Enable Network Topology with **Only generate errors**, Maximum number of errors 10000 **(default)**.
4. Group errors by ID. Decode `Error code` as a bitmask where the error ID is log2 of the value (Practitioner reading of an Esri Support KB, `learn/09` section 2.5):
   ```python
   def error_ids(code: int):          # e.g. 256 -> [8] (no connectivity rule)
       return [n for n in range(64) if code >> n & 1]
   ```
   Decode `Status` with `scripts/decode_dirty_status.py`. Illustrative outcome: 12,400 rows, with most carrying IDs 8, 21 and 25.
5. Fix systematically: IDs 21 (duplicate vertices) and 25 (stacked points) in the source or with **Analyze Network Data** and **Apply Error Resolutions** (non-versioned network, owner connection; `learn/03` section 8b); ID 8 by correcting asset types or adding rules (scenario 6). Rerun step 3 until the count per ID falls.
6. Register the dataset as **branch versioned** (Feature dataset Properties, Versioning; database connection versioning type Branch). Run the normal **Enable Network Topology** as the owners on DEFAULT.
7. Import associations and subnetwork controllers (`Import Associations`, `Import Subnetwork Controllers`) while topology is disabled, then enable once (`learn/13` section 2.1 steps 13 and 17).
8. Run Update Subnetwork per tier in rank order with **All subnetworks in tier** and **Continue on failure** (asynchronous), or the REST equivalent with `async=true`; log `failures` (`learn/10` section 5).
9. Run Analyze Datasets after a large load, publish, and only then open editing to named versions (`learn/10` section 9).

**Expected result.** Per-ID error counts trend to zero; the first versioned Enable completes under the cap; all subnetworks are updated and Clean (or intentionally Dirty where Manage IsDirty is off).

**What would go wrong, and why.**
- Validating repeatedly. Error-only rows are ignored; edit or re-enable (`learn/03` section 4).
- Raising the error cap to see "everything". Esri advises against it; it lengthens the run (`learn/03` section 2).
- A full-network Enable immediately after loading in the live versioned database. Take a backup first; some changes cannot be undone (`learn/01` section 5).
- Associations pointing at nothing because Global IDs were regenerated by the copy path (`learn/02` section 5; error 31).
- Feeding a bulk edit script that rewrites identical geometry. A geometry edit creates two dirty areas whether or not anything changed (`learn/10` section 4.1).
- Assuming a quick answer on capacity. Esri publishes no maximum for features, dirty areas or subnetwork size; measure (`learn/10` section 2).

---

## 10. Upgrading the dataset version

**Situation.** A production network is UN dataset v7 on Pro 3.7 / Enterprise 12.1. The business wants a telecom domain network, which needs v8 (`learn/02` section 13). Field crews use Field Maps.

**What the person sees.** A request to "just upgrade". The Compatible choice in Create/Upgrade maps to a number that is not obvious, and Add Telecom Domain Network refuses to run.

**Reasoning chain.**
1. Three numbers decide everything: UN dataset version (`Describe` `schemaGeneration`), Pro version and Enterprise version. v7 needs Pro 3.3 and Enterprise 11.3; v8 needs Pro 3.7 and Enterprise 12.1 (`pro-help/09`).
2. v8 must be chosen explicitly; Compatible and Current still create v7 in Pro 3.7 / Enterprise 12.1 (`pro-help/09`).
3. **Field Maps and the Native Apps SDKs do not support v8 with Enterprise 12.1.** This alone can stop the upgrade (`learn/08` section 12).
4. Newer clients work with older networks; older Pro cannot share or locally open a newer network. Big integer fields, 64-bit ObjectIDs (from v7) and newer Arcade versions can lock out older clients (`pro-help/09`).
5. Upgrade needs an exclusive lock, topology disabled, owner connections, a suitable geodatabase and a backup (`pro-help/09`).

**Exact steps.**
1. Inventory and decide. If field apps are in scope, the choice is to stay on v7 or move crews to Pro/web workflows. If proceeding, record the answer.
2. List what reads the data: scripts reading `ERRORCODE` as a float (changed to big integer at v7), code assuming 32-bit ObjectIDs, saved trace configurations (need v5+), published services, Native SDK apps, older Pro seats (`learn/09` section 9).
3. Rehearse on a copy of the production database. Time it: v7 drops and re-creates indexes on all UN tables, so it can take noticeably longer (`learn/10` section 14). Capture baseline timings for validate and Update Subnetwork afterwards.
4. Production window: save edits, reconcile and post the named versions you care about; stop the feature service and close every connection; **Disable Network Topology**.
5. Connect as the database utility network owner (branch versioning type) and sign in to Pro as the portal owner; confirm the geodatabase meets the minimum for your target (the 11.2.0 figure is from `pro-help/09`; Esri's compatibility page gives no database minimum, so verify against the Esri docs for your version).
6. Take the backup, then run **Upgrade Dataset** with the Utility Network Version parameter set to **8** explicitly. Esri's pages do not say whether the upgrade is reversible, so treat it as irreversible (`learn/10` section 14).
7. Afterwards: **Enable Network Topology**; restart and review the service; re-add UN layers to maps; reconcile named versions; run Analyze Datasets; run a full validate and Update Subnetwork for each tier to capture new baselines (`pro-help/09`; `learn/10` section 14).
8. Only then add the telecom domain network (topology disabled, Default version, owner connections) with `Add Telecom Domain Network` (`learn/02` section 1).

**What to re-check after the upgrade.**

| Check | Why | Source |
|---|---|---|
| `Describe` `schemaGeneration` equals 8 | Confirms the target | `pro-help/09` |
| System layer ids from your service `systemLayers` | They differ between versions and services (dirty areas 13 versus 12 in Esri examples); never hard-code | `learn/02` section 10 |
| Fields you rely on exist (`PARTITIONID` v8+, `FLOWDIRECTION` v7+) | Schema grows per version | `learn/02` section 13 |
| Named trace configurations still run | Saved names must match | `learn/07` section 15 |
| Scripts reading `ERRORCODE`; ObjectID handling | Big integer and 64-bit | `learn/09` section 9 |
| Subnetworks all Dirty after re-enable; run updates | Enable marks every subnetwork Dirty | `learn/03` section 2 |
| Field apps, Native SDK apps, older Pro seats | Not supported on v8 | `learn/08` section 12 |
| Scheduled jobs and timings | A regression is usually a changed parameter or service setting, not data (`learn/10` section 14) | `learn/10` |

**Expected result.** A v8 network with topology enabled, all clients verified, baselines recorded, and a path to add the telecom domain network.

**What would go wrong, and why.**
- Running the upgrade with a service up or connections open (no exclusive lock) or with topology enabled.
- Running as the wrong owner (database login vs portal account).
- Choosing Compatible and getting v7, then finding Add Telecom Domain Network refuses.
- Upgrading first and discovering the crews' app cannot open the network.
- Upgrading the geodatabase last: the geodatabase must be at least 11.2.0 for v7+ targets.

---

## Common misconceptions

- "A completed job proves the network is correct." It proves the job ran; check error rows, subnetwork status and the trace configuration (scenarios 2, 3).
- "Re-running Validate will clear errors." Error-only rows need an edit or a re-enable (scenarios 6, 9).
- "A trace and a subnetwork name are the same data." The trace reads the topology; the name is a snapshot written by Update Subnetwork (scenario 4).
- "Post finishes the job." DEFAULT needs its own validate and Update Subnetwork (scenario 5).
- "If it snaps, it is connected." Without a rule, no connection (scenarios 1, 6).
- "Tier design can be refined later." Tier definition, source/sink and many terminal choices are effectively permanent (scenario 7).
- "A bigger server or a longer timeout fixes a big trace." Check barriers, scope and flow first (scenario 8).
- "Upgrade is a routine patch." It needs an exclusive lock, owners, a backup and client verification (scenario 10).

## Quick checks

1. Which scenario shape is this? (New connection, invisible, wrong result, stale name, version merge, rule, design, trace size, bulk load, upgrade.)
2. Enterprise or single-user? Which version is edited and which is traced? Saved?
3. Topology enabled? What does the Dirty Areas `Status` say near the problem, decoded?
4. Which error ID and which pair of classes, asset groups, asset types and terminals?
5. Is the answer a stored snapshot (name, `ISCONNECTED`, diagram) and has its tool run since validate?
6. Which owner connections, licence and DEFAULT/named state does the tool need?
7. Which numbers are actually known (UN dataset, Pro, Enterprise versions) rather than guessed?

## Related files

- Mechanisms: `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`, `learn/03-topology-engine-and-validation.md`, `learn/04-rules-and-connectivity-design.md`, `learn/05-attributes-categories-and-attribute-rules.md`, `learn/06-tiers-and-subnetworks-in-depth.md`, `learn/07-tracing-in-depth-and-configuration-library.md`
- Operations: `learn/08-versioning-and-editing-workflows.md`, `learn/09-failure-anatomy-symptom-to-fix.md`, `learn/10-performance-scale-and-operations.md`
- Surfaces: `learn/13-arcgis-pro-fundamentals-and-workflow.md`, `learn/14-developer-surfaces-and-sdk-fundamentals.md`
- Reference: `pro-help/01-core-concepts-and-vocabulary.md`, `pro-help/02-structure-of-a-utility-network.md`, `pro-help/04-associations-editing-errors.md`, `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`, `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/08-trace-configuration-full-schema.md`
- Scripts: `scripts/decode_dirty_status.py`, `scripts/build_trace_request.py`

## Sources

- Facts are drawn from the files linked above. Their own Sources sections carry the Esri URLs; the pages most relied on here are:
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-life-cycle.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-compatibility.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/updatesubnetwork-utility-network-server/
- https://support.esri.com/en-us/knowledge-base/understanding-error-attributes-in-dirty-areas-table-for-000034757
