# Utility Network: Failure Anatomy, Symptom to Fix
> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro 3.7 help (About error features, View errors, FAQ, Update Subnetwork, Verify Network Topology, Import Associations, Upgrade Dataset, Publishing), Esri tool-error pages, Esri Support articles and bug records, Esri electric and gas blogs (full list at the end).*

## Why this matters / when to read this

This file is organised by what the user says is wrong, not by which tool they were using. Utility network failures are rarely random: nearly every one is a stored state (dirty area, error row, subnetwork status, version difference, missing rule, wrong owner) that the engine is faithfully reporting. Use the symptom sections to find the 2 to 4 most likely causes in rank order, run the cheapest check first, then follow the link to the file that explains the mechanism. Section 2 is the error-ID catalogue; the triage flowchart and the "what to ask first" list are at the end.

## Contents

0. How to use this file, and how failures are stored
1. Edits and topology (not in trace, dirty areas won't clear, Status 8/16/32/40, validate fails or times out, errors reappear)
2. Error code catalogue (enable/validate IDs, update-subnetwork IDs, undocumented IDs, tool-level errors, bit decoding)
3. Subnetwork problems
4. Tracing problems
5. Rules and associations problems
6. Versioning and reconcile problems
7. Publishing, services, licensing and permissions problems
8. Data loading and migration problems
9. Upgrade and compatibility problems
10. Industry-specific symptoms (electric, gas, water, telecom)
11. Triage flowchart
12. What to ask the user first

## 0. How to use this file, and how failures are stored

Labels used below: **[Esri]** documented by Esri in the cited page; **[bug]** an Esri Support bug record; **[blog]** Esri blog; **Practitioner guidance** reasoning or community experience, not an Esri statement. Anything I could not confirm says "verify against the Esri docs for your version".

Where a failure leaves evidence (check these before theorising):

| Evidence | Where | What it tells you |
|---|---|---|
| Dirty Areas sublayer/table: `Status`, `Network Source ID`, `Feature Guid`, `Error code`, `Error message` | Contents pane under the UN layer; right-click, Attribute Table (View errors page) | Pending edits (bits 1, 2, 4) and stored errors (8, 16, 32). `Status` 0 means topology is disabled |
| Pop-up field `Error(s)` | Pop-up of the feature in error | Numbered, readable message; error 9 also lists `RuleID(s)`; messages are trimmed at 512 characters |
| Error Inspector | Utility Network tab, Network Topology group (UN v4+) | Filtered list; Map Extent filter is on by default; omits `Status` and `Error code` |
| Subnetworks table (`ISDIRTY`, `ISDELETED`, names) and `SubnetLine` | Network system tables | Dirty / Clean / Invalid per subnetwork |
| Associations table `STATUS`, `ERRORCODE`, `ERRORMESSAGE` | UN v4+ | Orange indicator in Modify Associations for associations in error |
| Network Properties, Network Topology section | Layer properties | Topology on/off, counts, "Nonspatial Objects with Errors" |
| Tool messages / REST `error` object (`extendedCode`, `message`, `details`) | Geoprocessing history, job status | Tool-level numbered errors (section 2.4) |

Mechanism of storage and bit meaning: `learn/03-topology-engine-and-validation.md` (sections 4 and 7). Decode any `Status` with `scripts/decode_dirty_status.py` (the `--table` option prints the bits).

---

## 1. Edits and topology

### 1.1 "I added a new feature and it doesn't show up in the trace"

| Rank | Likely cause | Cheapest diagnostic | Fix |
|---|---|---|---|
| 1 | The edit is saved but **not validated**: a dirty area covers it and the trace reads the old topology. Visible only if the trace has **Validate Consistency** on (default true in REST per the existing reference); with it off the trace silently describes the old network | Open the Dirty Areas table, select by location; `Status` 1/2/4 present? Or rerun the trace with Validate Consistency on and look for error 002041 | Validate Network Topology over the footprint, then retrace |
| 2 | The feature **is in error** (`Status` 8 or 9 etc.): no connectivity rule, ambiguous terminal, bad geometry. It never entered the topology | Pop-up `Error(s)` field or Error Inspector (turn Map Extent filter on or off as needed) | Fix by **editing** (section 1.3), then validate |
| 3 | It is a **nonspatial object** (junction/edge object) with no association chain to a spatial feature: unlocatable, absent from topology | Trace option **Validate locatability** lists unlocatable objects; telecom: Esri Foundation documentation | Add the containment/attachment association with Modify Associations, validate |
| 4 | The trace is **subnetwork-based** (Subnetwork, Controllers, Upstream/Downstream in a tier, Isolation) and Update Subnetwork has not run since the edit | Subnetworks table `ISDIRTY`; feature `SUBNETWORKNAME` still `Unknown` | Update Subnetwork (it fails if dirty areas still intersect, error 002041) |
| 5 | The edit is in a **named version** and the trace is run against DEFAULT (or vice versa); or edits are **unsaved** (traces read saved state) | Compare `gdbVersion`/moment in the request; check Save | Align versions; save; reconcile and post, then validate on DEFAULT |
| 6 | The trace configuration stops before the feature (barrier, filter, wrong tier, start inside the wrong tier) | Rerun with the named configuration's barriers removed one at a time | `learn/07-tracing-in-depth-and-configuration-library.md` section 19 |

Deeper: `learn/03-topology-engine-and-validation.md` section 12 (decision tree) and `learn/01-mental-model-and-life-of-an-edit.md`.

### 1.2 "The dirty areas won't clear"

| Rank | Cause | Check | Fix |
|---|---|---|---|
| 1 | **Error-only rows** (`Status` 8, 16, 32, 24, 40, 48, 56): Esri says error dirty areas without an edit bit are ignored by Validate | Decode `Status`; no 1/2/4 bit means ignored | Change the cause and edit the feature (adds an edit bit); validate again |
| 2 | **Validated only part of the area**: dirty areas crossing the extent are clipped, the remainder stays dirty (practitioner/blog behaviour from the Pro 2.5 era; re-test on your build) | Compare the validate extent with the dirty area polygon | Validate the entire extent; run over the whole dirty polygon |
| 3 | **Errors found during validate**: the feature fails a rule so it keeps an error bit | Error(s) text | Fix the data or the rule (admin: topology disabled) |
| 4 | Dirty areas **re-created after reconcile/post** into DEFAULT: Esri records this as As Designed (BUG-000156036) | Do they appear right after post? | Validate on DEFAULT after posting; see section 6 |
| 5 | **Topology disabled**: edits are not tracked; one dirty area covers the service territory and `Status` is 0 | Network Properties, Network Topology | Enable on DEFAULT as owner; expect a large validate |
| 6 | Another session holds the single validate slot on DEFAULT, or the extent is huge and the run timed out | Job status; tool history | Retry smaller extents or async (1.4) |

An `ErrorCode 0` row with no message that does not show in Error Inspector is typically an **edit** dirty area waiting for validate, not an error (`pro-help/04-associations-editing-errors.md`).

### 1.3 "Status 8, 16, 32 or 40 will not go away" (error-only rows)

Esri: during validation, only edit dirty areas, or error dirty areas that also carry an edit bit (1, 2 or 4), are evaluated. `Status` 8 (feature error), 16 (object error), 32 (subnetwork error) and sums of only those bits (24, 40, 48, 56) are not re-evaluated by Validate. "Success" means the job ran, not that the errors are gone.

| Status | Kind | Which action discovers/clears it | Fix route |
|---|---|---|---|
| 8 | Feature error | Enable/Validate wrote it | Read error ID (section 2.1); edit geometry/attribute/terminal, or admin adds rule (topology disabled), then validate |
| 16 | Object error | Enable/Validate (junction/edge objects, associations) | Edit object attributes, association, or add containment/attachment rule |
| 32 | Subnetwork error | Update Subnetwork | Fix feature or tier definition (section 2.2), then Update Subnetwork |
| 24 / 40 | Combined error-only | both | Fix each cause |
| 9, 17, 33, 41 | Edit plus error | Validate re-queues it | Fix cause; if still violating, the error bit returns |

Example (gas) [from `learn/03`]: a regulator typed as an asset type with no rule to its inlet pipe has `Status` 8, error 8. Retype it (becomes 9) or add the rule while topology is disabled, then validate.

Do not confuse **Status 32** (bit: subnetwork error) with **Error ID 32** (inline weight value out of range). See `learn/06-tiers-and-subnetworks-in-depth.md` section 12.

### 1.4 "Validate fails, hangs, or times out"

| Rank | Cause | Check | Fix |
|---|---|---|---|
| 1 | **Synchronous time-out**: most UN tools in Pro time out at 600 seconds, Update Subnetwork at 1,800 seconds (Esri FAQ); async tools use the `UtilityNetworkTools` service time-out | Elapsed time at failure | Use the async path (REST `async=true`, All-subnetworks mode), smaller extent, or schedule validation |
| 2 | **Very large dirty-area count** (first enable on a freshly loaded network; bulk load; topology disabled for a long time). Historically stalled in the multi-million range on some releases (`pro-help/06-administration-subnetworks-topology-versioning.md`; version-specific) | Count dirty areas in the extent | Validate by area; enable on a subset first; keep error count near zero |
| 3 | **Error cap reached on enable**: Maximum number of errors defaults to 10000; the run is cancelled when reached | Tool message; dirty areas table | Fix systematic errors by ID first (section 2); do not raise the cap above 10000 (Esri advises against) |
| 4 | **Wrong connection or owner**: enable, disable, repair, verify need both database-owner connection and portal-owner sign-in; validate does not | `pro-help/10-publishing-ownership-licensing.md` | Use the correct accounts |
| 5 | **Another session** is validating/enabling on DEFAULT | Retry later | One at a time on DEFAULT |
| 6 | **Error 46** (system inconsistencies it could not clean) | Dirty area error 46 | Revalidate affected areas; if persistent, Rebuild Network Topology for the extent, then Verify then Repair (owners, DEFAULT) |
| 7 | Missing spatial index, locks, unsaved edits | Tool messages | Add spatial index; close other connections; save |

### 1.5 "Errors keep coming back after I fixed them"

1. **The cause was not fixed, only the symptom** (rank 1): validate again re-creates the same row. Example: error 29 returns on every Update Subnetwork until the connecting device state is corrected.
2. **Something regenerates the bad state**: a nightly load or sync overwrites the corrected asset type; an attribute rule re-sets a field; reconcile re-creates dirty areas.
3. **Rebuild or REST validate replaces errors**: some operations delete existing errors before writing new ones (`enableTopology` REST path, `rest-api/02-topology-and-subnetwork-management-operations.md`), so a "new" error is the same old one.
4. **Hidden second error**: messages are trimmed at 512 characters; fix the displayed errors, validate, and the next ones appear.
5. **Edit-version drift**: you fixed it in a version that was never posted.

Practitioner guidance: keep a log of error ID counts per run (group by ID); a fix is working only when the count for that ID drops.

---

## 2. Error code catalogue

### 2.1 Enable and validate network topology errors (Esri "Utility network error IDs", Pro 3.7)

Solutions are paraphrased from the Solution column of the Esri page. Esri notes that option 1 of each solution is generally the least disruptive; options marked (Admin) need topology disabled. "Data" = edit the feature; "Admin" = change configuration.

| ID | Meaning | Feature type | Usual cause | Fix |
|---|---|---|---|---|
| 0 | Field has wrong data type | Point, line, junction object, edge object | Load/migration with mismatched field type | Correct the field data type |
| 1 | Empty geometry | Point or line | Null shape from import. Dirty area appears at the lower-left corner of the service territory extent | Find by `Network Source ID` + `Feature Guid`; delete and re-create; revalidate |
| 2 | Subtype unknown (for example Asset Group = Unknown) | Point or line | New feature never classified | Set a valid asset group |
| 5 | Line shorter than network tolerance | Line | Sliver/split artefact | Lengthen it; or model with a connectivity association or nonspatial edge object; or lower tolerance (Admin) |
| 6 | Vertex along line cannot be located | Line | Corrupt/near-duplicate vertex | Revalidate; if it persists delete the vertex, validate, re-add if needed |
| 8 | No connectivity rule supports the connection | Point, line, junction object, edge object | Asset types never allowed to connect; wrong subtype; terminals | Change asset group/type to match an existing rule; or add rule (Admin) |
| 9 | More than one connectivity rule applies (ambiguous) | Point and line | Multi-terminal device, line not assigned a terminal; overlapping rules. Message lists `RuleID(s)` | Choose the terminal in **Modify Terminal Connections**; or leave one applicable rule (Admin) |
| 10 | Adjacent edges of different asset group/type connect with no junction | Line | Pipe/conductor type change without a transition junction | Match types, or insert a valid junction with an edge-junction-edge rule |
| 13 | Midspan placement violates edge connectivity policy | Point and line | Policy is End vertex; device snapped mid-line | Move to a permitted vertex, delete, or change the policy (Admin) |
| 17 | No containment rule supports the association | Junction object, edge object | Missing/reversed containment rule | Edit attributes, or add containment rule (Admin) |
| 18 | No structural attachment rule supports the association | Junction object, edge object | Missing attachment rule | Edit attributes, or add a structural attachment rule (Admin). Esri's solution text mentions a containment rule, which Esri's own notes treat as a likely copy slip |
| 19 | Line is multipart | Line | Merge/import artefact | Make single-part, or delete and re-create |
| 20 | Line self-intersects | Line | Loop-back digitising | Add vertices at the crossing with adjusted z, or split the line |
| 21 | Duplicate vertices | Line | Double click, snapping | Offset one in x, y or z, or delete one |
| 23 | Asset type not defined for the asset group | Point, line, junction object, edge object | Invalid group/type combination | Set an asset type defined for the group (no admin option) |
| 25 | Points stacked at the same location | Point | Duplicate load, double paste | Offset or delete one |
| 31 | Association references an invalid from/to GlobalID | Point or junction object | Half of a broken association; bad import | Delete the remaining feature; it can be re-created with a new GlobalID |
| 32 | Inline network-attribute weight exceeds range | Point | Attribute value beyond the reserved bits (`learn/05-attributes-categories-and-attribute-rules.md` section 4) | Set a value within the coded value domain range; check network properties |
| 34 | Unsupported containment relationship | Point and line | No containment rule for this point/line | Edit attributes, or add containment rule (Admin) |
| 35 | Unsupported structural attachment relationship | Point and line | No attachment rule | Edit attributes, or add rule (Admin) |
| 36 | Line has an invalid from/to terminal | Point and line | Terminal id not on the device; device retyped. Line shows "Invalid" in the Terminal drop-down | Fix the terminal reference, assign matching terminal configuration, correct the line terminal value, or place a device with matching terminal |
| 37 | Subnetwork tap not midspan on exactly one line | Point and line | Flying tap on an endpoint or on two lines | Edit so the tap sits midspan on exactly one line |
| 38 | Device with terminals placed midspan | Point and line | Transformer/valve/breaker snapped mid-line | Split the line at the device, move to an endpoint, or use a device without a terminal configuration; reconnect terminals |
| 39 | Invalid terminal configuration on a point | Point | Path attribute not valid | Fix with **Modify Terminal Path** or edit to a valid path listed in network properties |
| 43 | Edge object references the same junction object at both ends (self-intersecting) | Edge object | Both From and To point to one junction object | Modify the junction-edge association so From and To differ |
| 44 | Junction objects stacked | Junction object | Duplicate load of same location | Keep one at the location |
| 46 | Validation found system inconsistencies it could not clean | Point, line, polygon, junction object, edge object | Interrupted or conflicted validation | Revalidate the affected dirty areas within the validation extent; Rebuild / Verify and Repair if it persists (practitioner escalation path, see `learn/03`) |

### 2.2 Update subnetwork errors (Esri, Pro 3.7)

These are written when Update Subnetwork runs; they set the subnetwork's controllers and its SubnetLine row to **Invalid** (Enterprise 11.1+ per the existing life-cycle reference).

| ID | Meaning | Feature type | Usual cause | Fix |
|---|---|---|---|---|
| 24 | Line not allowed by the tier's Valid Lines | Line | New asset type not added to the subnetwork definition, or misclassified | Change line asset group/type; or add to the definition (Admin); or disconnect it / break traversability |
| 26 | Device not allowed by Valid Devices | Point | Same | Disconnect or break traversability; change type; or add to Valid Devices (Admin) |
| 27 | Invalid parent subnetwork | Point | Hierarchical domain network, **UN version 1 only** | Parent must be exactly one tier rank higher; correct connectivity |
| 28 | Disjoint subnetwork in a tier that does not support it | Point | Same-named controllers not traversable to each other | Make them traversable; or enable disjoint support in the definition (Admin) |
| 29 | Traversable controllers have inconsistent subnetwork names | Point | Backup source, bad snap, wrong device state, per-device names | Rename controller; or align names; or isolate the pieces; or disconnect controller that should not define the subnetwork (also tool error 002066) |
| 30 | Parent controllers have inconsistent parent subnetwork names | Point | Hierarchical parents differ | Rename parent controller, or disconnect the stray controller |
| 33 | Controller's asset group/type was modified | Point | Retyped a live controller | Restore original asset group/type; to edit safely, disable the controller from the device first |
| 40 | Junction not allowed by Valid Junctions | Point | Not in definition | Change type or add to definition |
| 41 | Junction object not allowed by Valid Junction Objects | Junction object | Not in definition | Change type or add to definition |
| 42 | Edge object not allowed by Valid Edge Objects | Edge object | Not in definition | Change type or add to definition |
| 47 | Traversable controllers from different tiers | Point, junction object | Tiers reach each other; wrong controller tier | Correct the controller's role/tier and re-create it; or isolate the subnetworks |

Tip [blog]: the feature named in a 24/26/40/41/42 error may not be the first invalid feature the trace met. Trace outward from the reported location.

### 2.3 IDs Esri does not document

Esri documents 38 of the IDs between 0 and 47. The following are **not mentioned** on the page: **3, 4, 7, 11, 12, 14, 15, 16, 22, 45**. The page does not say whether they are unused, reserved or retired. If one appears in your data, do not guess a meaning: open the dirty-area `Error message`, check that your Pro version matches the dataset, and ask Esri Support. Likewise treat any ID above 47 as undocumented.

Also note: error 9 and 36 messages carry extra detail (`RuleID(s)`, "Invalid" in the terminal drop-down).

### 2.4 Tool-level and service-level errors Esri documents

| Number or text | Meaning | Cause | Fix | Source |
|---|---|---|---|---|
| **002041** "One or more dirty areas were discovered" | A trace with Validate Consistency, or Update Subnetwork, touched dirty areas. Message gives class and GlobalID; for update, subnetwork name in brackets | Unvalidated edits intersect the traced/updated features | Validate Network Topology at the reported feature, rerun | Esri tool errors page |
| **002066** | Update Subnetwork found controllers that traverse to each other with different subnetwork names; generates point errors (same condition as error 29) | Wrong name, or a connection that should not exist | Rename in Modify Subnetwork Controller, or disconnect the controller that should not define the subnetwork | Esri tool errors page |
| **003049** "account logged into portal is not licensed with the <value> user type extension" | Portal account lacks the extension | Enterprise 11.2+: **Advanced Editing**; before 11.2: Utility Network or Trace Network extension | Portal administrator changes user type or adds the add-on | Esri tool errors page |
| **002144** "The account logged into Portal must be the owner of the utility network to perform this operation" | Not the portal utility network owner | Signed in to the wrong portal account | Sign in as the portal owner (Pro Portals tab; active portal) | Esri FAQ |
| **001400** "Only the data owner may execute <value>" | Not the database utility network owner | Connection made as another database user | Run through a connection as the data owner | Esri FAQ |
| "Operation is only allowed by the owner of the version" | **Version** ownership/access, not network ownership | Export Subnetwork failed for non-owners (BUG-000146789, fixed at 11.0; patches for 10.8.1/10.9.1) or a private/protected version | Run as version owner or use public access; check patch level | Esri Support bug |
| Publishing analyzer **00270** | Definition queries or hidden fields on UN layers unsupported | Map has definition query / hidden field | Remove them from the layer before publishing | Esri publishing page |
| Publishing analyzer warning **24099** | Service consumed without all network layers works on the web but Pro needs all layers | Map missing participating classes | Include all participating classes | Esri publishing page |
| "Apply Asset Package failed"; "Failed to execute (AssetPackageToUtilityNetwork)"; "Invalid GlobalID error"; "This field is too long for some database platforms" | Esri KB 000027843 | Stage Utility Network not run (Create used instead); incomplete package install; corrupt or wrong package; field name over limit | Run Stage Utility Network first; reinstall toolbox/`untools`; shorten field names to 31 characters or fewer | Esri Support KB |

### 2.5 Decoding `Status` and `Error code`

- `Status` bit values: 1 insert/update, 2 delete, 4 modified objects, 8 feature error, 16 object error, 32 subnetwork error; 0 = topology disabled.
- `Error code` is also a bitmask (Esri Support KB): 0 means no error; **the error ID is log2 of the value**. Example from Esri: 256 = 2^8, so error ID 8 (no connectivity rule). Several errors on one dirty area add their bits (inference: Esri's KB shows only the single-bit example).
- Esri's KB covers only single-bit values; it does not explain combined values, so reading several bits is Practitioner guidance (standard bitmask logic).
- Practitioner guidance: this implies bit n of `Error code` equals error ID n. `ERRORCODE` was widened from double to big integer at UN v7 (existing upgrade reference). Esri does not state the reason; scripts that read it as a float break (section 9).
- Sanity check on a query: take the value, loop over bit positions 0 to 47, list those set, then look each up in 2.1 and 2.2.

---

## 3. Subnetwork problems

### 3.1 "Update Subnetwork fails"

| Rank | Cause | Cheapest diagnostic | Fix |
|---|---|---|---|
| 1 | **Dirty areas intersect the subnetwork's features** (error 002041) | Dirty Areas table over the subnetwork; message names the feature | Validate, then rerun. For each controller reporting the problem, validate it first [blog] |
| 2 | **Unsaved edits** or topology disabled (tool disabled / fails) | Save status; Network Properties | Save; enable topology |
| 3 | **Subnetwork errors** (24, 26, 28, 29, 30, 33, 40, 41, 42, 47) | Error Inspector, `Status` 32; tool message | Section 2.2 |
| 4 | **Two processes** updating the same subnetwork, or two All-subnetworks runs at once (Esri) | Job list | Serialise; one process per subnetwork |
| 5 | **Time-out** (1,800 s for single runs; All subnetworks runs async) | Duration | Use All subnetworks in tier (async) or smaller subnetworks |
| 6 | **Enterprise preconditions**: branch-versioned network, input from a utility network service, Advanced Editing extension, traditional domain network only | Tool page; licence | Fix connection/licence. Telecom domain networks have no subnetworks: use circuits |
| 7 | **Invalid** status skipped: later updates skip an Invalid subnetwork until it is made Dirty again | Subnetworks table `ISDIRTY` = 2 (Invalid) | Fix cause, validate (makes Dirty), update |

**Continue on failure** (default off) stops at the first failure in All-subnetworks mode; with it on you get a list of failures instead (REST `continueOnFailure`, response `failures`).

### 3.2 "Inconsistent controller / subnetwork name" (error 29, tool 002066)

Cause pattern: two controllers that can reach each other carry different subnetwork names. Esri blogs list the usual sources: a backup controller with another name, substation internal breakers set as controllers, mesh/spot networks named per device, a tie or valve in the wrong state, or a bad snap or abandoned pipe joining zones that should be separate.

1. Decide: should the controllers be one zone or separate zones?
2. Diagnose: run **Shortest Path** between the two controllers (electric blog: shape length as weight, open devices and not-in-service lifecycle as barriers) and examine the path for the joining device.
3. Fix: separate zones, correct data until isolated; one zone, recreate controllers with a shared subnetwork name and unique controller names (Modify Subnetwork Controller; delete the old subnetworks by the documented steps); backup source, isolate it or disable its controller status.
4. Validate every controller that reported it, then Update Subnetwork again. Skipping this gives "dirty areas were discovered in the subnetwork".

Details: `learn/06-tiers-and-subnetworks-in-depth.md` sections 5 and 9.

### 3.3 "Unknown subnetwork" (`SUBNETWORKNAME = 'Unknown'`)

| Rank | Cause | Check | Fix |
|---|---|---|---|
| 1 | Never updated since the edit | Subnetworks `ISDIRTY`; last update | Update Subnetwork |
| 2 | **No traversable path to a controller**: open device upstream, wrong lifecycle/state, missing connectivity | Upstream trace from the feature; Connected trace | Correct the open device or state, validate, update [electric blog] |
| 3 | Intended exception: guys, neutrals, grounding, proposed/abandoned, dead spans | Compare the lifecycle status | Exempt in the QA query (electric blog queries: `SUBNETWORKNAME = 'Unknown'` with lifecycle and group exclusions) |
| 4 | Container/structure pick up names only if the definition enables container/structure policies | Definition options | Enable Include Containers / Structures and update |
| 5 | Named version: only features **edited in that version** receive new names in the default edit mode | Trace to verify | Verify by trace; update on DEFAULT after post |

### 3.4 "Subnetwork stays dirty" or "stays Invalid" or "Last Update blank"

| Symptom | Cause | Fix |
|---|---|---|
| Stays **Dirty** forever | Tier does not manage `Is dirty` (the Esri Water Foundation sets Manage IsDirty off for performance, per Esri); status is not meaningful | Expected; Export Subnetwork (Clean only) is unavailable |
| Dirty again immediately | Validate marks modified subnetworks Dirty; reconcile re-creates dirty areas | Validate then update on DEFAULT |
| **Invalid** | Update found validate-consistency failures or subnetwork errors | Section 3.1 rank 3 |
| Not listed in Find Subnetworks | Blank/NULL `Last Update` = never updated; no shape in SubnetLine; tier definition lacks valid lines in **Aggregated Lines for SubnetLine Feature Class**; `Is Connected` on features at controllers; "Use the current map extent" unchecked needed | Esri FAQ steps: update it; check definition; clear the extent filter; switch Lines / Subnetworks Table tabs |
| Orphaned after removing controllers | Removed controllers leave rows `ISDELETED` true | Validate, update, then Export Subnetwork with acknowledgement on the default version |

---

## 4. Tracing problems

The most complete list is `learn/07-tracing-in-depth-and-configuration-library.md` section 19; this table adds the failure ranking and the cheapest checks.

| Symptom | Ranked causes | Cheapest diagnostic | Fix |
|---|---|---|---|
| **Empty result, no error** | 1) Starting point ignored (REST: missing `terminalId` or `percentAlong`, ignored without error); 2) start on a barrier; 3) wrong tier; 4) start in dirty/erroneous area filtered | REST `startingPointsIgnored`; try Ignore Barriers At Starting Points; remove tier | Supply terminal/percentAlong; correct tier |
| **Error 002041** | Dirty areas on the path with Validate Consistency on | Message gives class + GlobalID | Validate at that feature |
| **Too large (whole network)** | 1) No barrier fired: scope, unmapped attribute, wrong coded value stored, devices "open" in GIS but state field different; 2) indeterminate flow with Allow Indeterminate Flow on; 3) closed valve not modelled | Test one barrier alone; read stored code value | Fix scope/value; edit device status; turn indeterminate off |
| **Too small** | 1) Tier-loaded condition barrier you didn't know; 2) Include Barrier Features off; 3) containers/content/structures off | Read the tier definition; compare Pro-loaded values | Override in request |
| **Wrong direction (upstream/downstream swapped)** | 1) Source vs sink confusion in controller type; 2) digitised-direction mechanism with flipped line (`Use Digitized Direction`); 3) controller on the wrong terminal | Connected vs Upstream comparison; include flow directions | Fix controller/terminal; flip line (Flip Lines in a version), validate |
| **Upstream/Downstream empty or errors** | No connected controller; dirty subnetwork; wrong domain/tier | Subnetworks table | Create controller; update subnetwork |
| **Slow** | Large subnetwork-based traces, function/propagator cost, huge result geometry, missing validate backlog | Time with simpler config; fewer result types | `learn/07` section 17 |
| **Differs between Pro and REST** | 1) Stored trace type wins over the request; 2) tier defaults not applied by REST (you must send them); 3) `percentAlong` -1 on a line; 4) different `gdbVersion`/moment; 5) unsaved Pro edits | Compare JSON from `traceConfigurations/query`; send only `traceConfigurationGlobalId` | Pass the named configuration by GlobalID; align versions |
| **Differs between users** | Different versions or unsaved edits (a trace reads saved state) | Compare `gdbVersion`, moment | Align |
| **Works yesterday, broken after Foundation update** | Renamed attributes or categories in configs | Read the configuration JSON | Update names (gas: Lifecycle Status renamed Asset Lifecycle Status and Asset State added in Foundation 4.0; water: Lifecycle Status renamed Asset State, Construction Status network attribute removed in the Mar 2026 Foundation; Practitioner guidance from Foundation release notes, not re-verified here, check your Foundation version) |

REST `error` body: `extendedCode`, `message`, `details` (`rest-api/01-utility-network-server-and-trace.md`). A trace on a version under an exclusive lock needs the holder's `sessionId`. Named trace configurations need UN v5+.

---

## 5. Rules and associations problems

### 5.1 Rules

| Symptom | Ranked causes | Check | Fix |
|---|---|---|---|
| Error 8 / 9 / 10 / 13 on new feature | See 2.1 | Network Properties, Rules table | Data fix or add rule |
| "Added the rule but nothing changes" | 1) Service not restarted; 2) **named version not reconciled** (rule changes do not appear in an existing version until reconciled, per Esri rules page); 3) error-only row ignored by validate | Restart; reconcile; `Status` | Restart; reconcile; edit feature |
| "Cannot add rule" | Topology enabled; not the owner connection; rule breaks feature restrictions | State; connection | Disable topology; owner connection |
| Rule deleted and features now in error | Expected | Export before delete | Re-add rule |
| Containment/attachment rule seems right but fails (17/18/34/35) | Role (Container/Structure) not set on asset type; From/To order reversed (From = container) | Set Association Role state | Set role (topology disabled) then rule |
| `Set Association Role` tool refuses | Topology enabled; not database owner connection + portal owner | `pro-help/04-associations-editing-errors.md` | Disable topology; use owners |
| Attribute rule triggers odd dirty areas / errors after updates | Update Subnetwork with eventing fires rules; rule-made associations skip network rules and are validated later | Edit mode in definition | `learn/05-attributes-categories-and-attribute-rules.md` section 11 |

Mechanism and design: `learn/04-rules-and-connectivity-design.md` (troubleshooting table in section 13).

### 5.2 Associations

| Symptom | Ranked causes | Check | Fix |
|---|---|---|---|
| Pane or tool refuses to create association | No supporting rule (no error record is created); role not set | Rules; role | Add rule or change types |
| **Import Associations fails** | 1) Feature in CSV does not exist; 2) feature lacks supporting rules; 3) not the database-owner connection; 4) CSV columns wrong (`ASSOCIATIONTYPE`, from/to class, group, type, GlobalID, terminal, `ISCONTENTVISIBLE`, `PERCENTALONG`); 5) **telecom unit columns missing** (`FROMFIRSTUNIT`, `FROMLASTUNIT`, `TOFIRSTUNIT`, `TOLASTUNIT` are required when the network contains a telecom domain network); 6) container/structure order reversed; 7) values supplied for the wrong association type (terminal only for junction-junction, `ISCONTENTVISIBLE` containment only, `PERCENTALONG` midspan only) | The Esri tool page does not document row-level errors: check the tool messages | Fix the CSV; disable topology first for speed (`pro-help/04-associations-editing-errors.md`) |
| Error 31 | Association references an invalid GlobalID | Association rows | Delete the remaining feature; re-create |
| Association in error (orange in Modify Associations) | Enable/validate found no rule (17/18/34/35) or bad GlobalID | Hover tooltip; `ERRORCODE` bit decode | Section 2.1 |
| Deletion of container blocked | Deletion semantics RESTRICTED (CASCADE deletes contents) | `pro-help/04` | Remove contents first, or change semantics |
| Content has two containers | A point cannot be content of more than one container (Esri) | Associations table | Remove one |
| Nonspatial object conflict shows no features | Unlocatable object (no containment/attachment): Conflict Display empty and a banner says so (Esri FAQ) | Banner | Add the association |
| `ASSOCIATIONSTATUS` out of sync | Legacy or script-edited data (`SummarizeUNErrors` community tool reports it) | Run audit | Verify against Esri docs; repair via supported edit |
| Unexpected association conflicts in named versions after post | BUG-000141682 (found UN v4; Esri lists it fixed in Pro 3.6; Enterprise fix version not confirmed) | Versions | Update; no workaround listed |

---

## 6. Versioning and reconcile problems

Background: `learn/03` section 11, `pro-help/06-administration-subnetworks-topology-versioning.md`, `rest-api/04-version-management-validation-feature-service.md`.

| Symptom | Ranked causes | Check | Fix |
|---|---|---|---|
| **Dirty areas re-appear on DEFAULT after post** | Edits posted from a child create dirty areas in DEFAULT, even if validated in the child. Esri: **As Designed** (BUG-000156036). The network model changes are not carried by reconcile/post, only GIS edits | Look right after post | Validate (and update subnetworks) on DEFAULT after post |
| **Post is blocked** after validating in the version | You must reconcile again after validating before post | Version state | Validate, QC, reconcile, resolve conflicts, then post (Esri flow) |
| Dirty areas return in the child after validating in DEFAULT | Expected (Esri Support, Pro 2.1.2 era) | Child version | Validate DEFAULT, switch to child, validate, reconcile, post |
| **Conflicts you can't see** | Nonspatial junction/edge object without containment/attachment is unlocatable; Conflict Display shows no features | Banner | Fix association; resolve |
| Same feature or topologically related features edited in two versions | Real conflict; resolution can have knock-on effects on subnetworks | Conflict Manager | Choose edit vs target version, then validate and update subnetwork |
| **Topology disabled in a named version, can't enable** | Enable runs on DEFAULT; version inherits the state when reconciled (Esri FAQ) | Network Properties | Enable on DEFAULT; reconcile |
| **"Operation is only allowed by the owner of the version"** | Version ownership/access (private/protected/public); Export Subnetwork bug BUG-000146789 (fixed 11.0) | Version access | Owner or public; patch level |
| Update Subnetwork "did nothing" in a named version | Default edit mode updates only **features edited in that version**; no eventing | Definition edit mode | Update on DEFAULT after post |
| **Reconcile blocked or slow** | Update Subnetwork **with eventing** on DEFAULT holds a shared lock for the whole operation, blocking reconcile's exclusive lock | Edit mode | Schedule updates outside reconcile windows |
| Only one validate at a time | On DEFAULT a single session can validate or rebuild; editing and tracing continue | Retry | Serialise |
| Rule changes missing in a child | Rules reach an existing version only on reconcile | Reconcile | Reconcile |
| Cannot edit or enable on a plain feature class | Branch versioning needed; branch versions can be edited only through feature services | Versioning type | Set Branch before add to map / publish |

---

## 7. Publishing, services, licensing and permissions problems

### 7.1 Who is failing: the three-way test

| What failed | Typical message | Look at | Reference |
|---|---|---|---|
| **Licence** (user type) | **003049** "not licensed with the <value> user type extension" | Portal admin: user type / Advanced Editing add-on | `pro-help/10-publishing-ownership-licensing.md` |
| **Network owner** | **002144** (portal owner) or **001400** (database owner); tool greyed out; hover tooltip on the greyed command | Which sign-in and which connection | same |
| **Version owner** | "Operation is only allowed by the owner of the version" | Version access level | section 6 |

Owner versus portal owner: the **database utility network owner** (database user that created the network; cannot be changed) and the **portal utility network owner** (portal account signed in at creation; changeable with Update Portal Dataset Owner by the current owner or a portal administrator, needs an exclusive lock, new owner needs the same user type and privileges, and afterwards change item ownership of related portal items). Many admin tools need both at once; Validate, Update Subnetwork and ordinary editing need neither (but the licence).

Licensing quick facts [Esri]: Pro Standard or Advanced for any UN work; Enterprise create/publish/edit needs the **Advanced Editing** user type extension (included with Professional and Professional Plus, add-on for Mobile Worker, Contributor, Creator; in 12.1; consolidated from separate extensions at 11.2); query and trace need none. Validate, Update Subnetwork, Export Subnetwork and enable/disable need it.

### 7.2 Publishing and service symptoms

| Symptom | Ranked causes | Fix |
|---|---|---|
| Cannot publish the utility network | 1) Connection not **Branch** versioned; 2) feature dataset not registered as branch versioned; 3) database not registered with the server as a data store; 4) not signed in as portal owner, or layer not from a database-owner connection | Set versioning type to Branch; register dataset; register data store; use owners |
| Analyzer error 00270 | Definition queries or hidden fields on UN layers | Remove them |
| Analyzer error on layer IDs | Unique numeric IDs not enabled in Map Properties | Enable "Allow assignment of unique numeric IDs for sharing web layers" or assign layer IDs manually |
| Publishing blocked by renderer | Subtype group layers or a unique value renderer referencing fields other than asset group | Remove subtype group layers; renderer on asset group only |
| Version Management capability unavailable | Feature not enabled or dataset not branch versioned | Enable Feature; register branch versioned |
| No trace or diagram in the web app | Published without the UN layer (no Utility Network or Network Diagram services) | Republish with the UN layer in the map |
| Edits create dirty areas that nobody sees | Services without the UN layer still trigger UN behaviour, but dirty areas are not shown | Use the full feature service for editors/analysts |
| Offline/sync | Editing and sync not enabled, or service territory missing | Enable both; include Service territory |
| Rule or configuration change not visible | Service not restarted | Stop and start the service and reopen Pro |
| Users can trace but not edit | Missing Advanced Editing extension (query and trace need none) | Assign extension |
| Pro warns layers missing | Pro requires all participating layers (warning 24099) | Add them |

Never edit the published network directly through a database connection; after publishing, edits go through services.

---

## 8. Data loading and migration problems

| Symptom | Ranked causes | Fix |
|---|---|---|
| **Thousands of errors on first enable** | 1) Data quality: not snapped, self-intersections, multipart, stacked points, missing junctions; 2) rule gaps (8/9/10); 3) unclassified subtypes (2/23) | Pre-load quality rules; **Analyze Network Data** + **Apply Error Resolutions** on a nonversioned network (migration-era pair); triage by ID, not feature by feature (`learn/03`) |
| Enable stops at the cap | Maximum number of errors 10000 default | Fix systematic errors, rerun; do not raise the cap above 10000 |
| Error counts above ~10,000 hurt performance | Practitioner guidance (older Esri material, not re-verified); Esri's only stated number is the Enable Network Topology default cap of 10,000, which it advises against raising | Aim near zero before versioning; enable branch versioning after topology validates |
| Errors 'feature outside extent' | No service territory | Create it first (`pro-help/11-migration-and-schema-mapping.md`) |
| Associations/attachments silently dropped | Source relationships/attachments lacked Global IDs | Add Global IDs before load |
| Unmapped fields | Alias names used in the mapping sheet | Use field names |
| Downstream code breaks on subtype codes | Subtype renumbering (codes outside 1 to 1023) | Update hard-coded codes |
| Sync the C Tables fails | Needs exclusive locks | Close all open tables |
| Apply Asset Package fails | 1) Maps open; 2) topology enabled; 3) Pro version vs UN version; 4) enterprise: not portal owner, not database owner, not DEFAULT; plus KB causes (Create instead of Stage; wrong/corrupt package; field name over 31 characters) | `pro-help/08-asset-packages-foundations-migration.md`; section 2.4 |
| Post-process locked topology before review | Post Process option on first pass | First pass with post-processing off |
| Telecom load fails | Import Associations lacks unit columns | Add the four unit columns |
| Analyze/Resolve tools missing | Release dependent (Pro 3.3 standalone, 3.5 wizard integration per blog) | Verify against the Esri docs for your version |

Practitioner guidance: load into a file geodatabase asset package for fast iteration, deploy with post-processing off, and enable topology on a subset to find systematic rule gaps. Full path: `pro-help/11-migration-and-schema-mapping.md`.

---

## 9. Upgrade and compatibility problems

| Symptom | Ranked causes | Check | Fix |
|---|---|---|---|
| **Pro can't open the network** | Dataset version newer than the Pro minimum (v7 needs Pro 3.3+, v8 Pro 3.7) | Describe `schemaGeneration`; matrix in `pro-help/09-dataset-versions-compatibility-upgrade.md` | Upgrade Pro, or open through a service |
| **Cannot share/publish** | Older Pro can't share a newer network; Enterprise must support it (Pro 3.7 can't share v8 to Enterprise 11.1) | Versions | Match Pro and Enterprise |
| **Field Maps / Native SDK app broke** | Field Maps and Native Apps SDKs do not support v8 | Dataset version | Choose an earlier version for field apps (Esri says v8 is unsupported there and does not explicitly confirm v7); v8 is primarily for telecom |
| Upgrade Dataset fails | 1) Not exclusive lock (services running or connections open); 2) topology enabled; 3) not database owner (branch versioning) **and** portal owner; 4) geodatabase below 10.8.1.2.6 (targets up to v6) or 11.2.0 (v7+); 5) no backup | Pro 3.7 tool page itself does not list these; they come from Esri's dataset administration page via the existing reference | Follow the sequence in `pro-help/09` |
| Scripts read `ERRORCODE` wrongly after upgrade | Changed from double to big integer at v7; 32-bit ObjectID assumptions fail (64-bit ObjectIDs) | Field types | Update scripts |
| Named trace configs missing | Need v5+ | Version | Upgrade |
| Old docs mention "Point Errors layer" | Dataset v3 or earlier; v4+ stores errors in Dirty Areas and Associations | Version | Use `learn/03` section 7 |
| Telecom domain network cannot be added | Topology enabled; dataset below v8; not owner; not DEFAULT | Version | Disable topology; Upgrade Dataset to 8 |
| After upgrade nothing renders | Layers need re-adding; services need restart and review | Pro 'Upgrade' steps | Re-add UN layers; restart service; reconcile all named versions (v4 upgrade) |
| Newer data features lock out older clients | Big integer fields, 64-bit ObjectIDs, newer Arcade versions in attribute rules | Client versions | Plan client upgrades first |

Esri's rule: newer clients work with older networks; older Pro can use a newer network through services where Enterprise supports it and the work avoids newer functionality.

---

## 10. Industry-specific symptoms

### 10.1 Electric

| Symptom | Likely causes | Cheapest check | Fix |
|---|---|---|---|
| **Wrong phases / phases missing** (underserved) | 1) Normal Phases vs Energized Phases mismatch after a clean update; 2) a single-phase device or fuse drawn in-line with three-phase; 3) wrong phase opened; 4) stale propagation (update not run); 5) digitised-direction in use | Layer symbolising Normal vs Energized; trace upstream to the first affected point | Fix the most upstream feature first; update subnetwork; downstream re-energizes |
| **De-energized** features lose subnetwork membership | Upstream phase missing | Electric Data Audit display | Fix upstream phasing; update subnetwork |
| **Open points not honoured** (trace passes an open switch) | Device Status / Normal vs Current status fields; stale GIS state; condition barrier misses coded value | Check status field value stored vs expected | Fix status; verify the barrier uses the stored code |
| Open one phase of a gang-operated device | Not modelled by default (devices treated as gang operated) | Mixed-status query | Model separately or per-phase fields (community); verify for your Foundation |
| Error 37 | Tap not midspan to one line | Vertex count | Move tap to a single midspan vertex |
| Error 38 | Transformer/breaker snapped midspan | Split line |  |
| Errors 28/29/30/47 | Island fed by controller in another tier; tie switch closed; spot network; substation internal breakers as controllers | Shortest Path between controllers | Section 3.2; disable controller on internal breakers (blog) |
| Unintended **loop** in radial network | Open point moved in the field, not updated in GIS | Loops trace with a named configuration | Confirm with operations; update the open point; mark intentional loops `Is Valid Loop` |

QA categories and queries (inconsistent name `SUBNETWORKNAME LIKE '%::%'`, unknown, loops, underserved, de-energized): Esri electric quality assurance blog.

### 10.2 Gas

| Symptom | Likely causes | Fix |
|---|---|---|
| **Isolation trace misses valves** | Valve not tagged Isolating/Operable; Device Status wrong; filter barrier combine-using wrong (AND of Operable = True and Category = Isolating) | Repair attributes; fix filter barriers |
| **Isolation returns nothing / fails** | Filter barrier missing (mandatory); wrong tier; Validate Consistency on with dirty areas (002041) | Add filter barrier; fix tier; validate |
| Isolation too large | Long unsplit main; closed valve not modelled | Aggregated Geometry result; split mains |
| "What if this valve fails" | No built-in operation | Workarounds: mark inoperable, add starting points, relax condition (practitioner, test) |
| Squeeze-off | Unverified in current UN | Verify against the Esri docs for your version |
| Pressure zone swallows a higher-pressure ring | Regulator controller on the wrong terminal; valve left open | Fix controller terminal or Device Status |
| Error 9 at regulator/compressor | No terminal chosen | Modify Terminal Connections |
| Export Subnetwork refused | Foundation sets Manage IsDirty false | Use trace export |
| 24/26/40/41/42 | New type not in valid devices for every tier (System, Pressure, Isolation, Cathodic Protection) | Update Subnetwork Definition for all tiers |


### 10.3 Water, wastewater, stormwater

| Symptom | Likely causes | Fix |
|---|---|---|
| **Isolation zones wrong** | Valve states stale; precomputed isolation zone tier (stale until Update Subnetwork) vs on-demand Isolation trace (current) | Fix states; rerun; know which one you used |
| **Flow direction missing or wrong** | Two mechanisms: controllers/barriers/terminals (default) vs digitised direction (UN v7+, Pro 3.3, Enterprise 11.3+); mismatch between the two; indeterminate flow; flipped lines | Pick one mechanism; Connected vs digitised compare; Flip Lines |
| Customers missing from upstream count | Flipped line (digitised backwards); direction-dependent attributes (invert elevations, from/to node ids) don't flip | Flip in a branch version; validate |
| Sewer trace misses outfall | Overshoots/undershoots; midspan connection without vertex | Snap; Connected trace from sinks |
| Error 29 | Controllers of one zone named differently; open valve or abandoned main; backup controller | Rename; close valve; update abandoned status |
| Error 9 at pumps/PRVs | Terminal not chosen | Modify Terminal Connections |
| Error 38 | Terminal device midspan | Split |
| Unknown pressure zone | Abandoned still active; gravity section with no controller; stale closed valve; reversed check-valve terminals | Verify, fix status or record exception |
| Traces broke after Mar 2026 Foundation | Lifecycle Status renamed Asset State; Construction Status removed | Edit named traces and barriers |
| Terminal config can't change | Permanent once topology first enabled | Plan pumps/PRVs before load |


### 10.4 Telecom

| Symptom | Likely causes | Fix |
|---|---|---|
| Add Telecom Domain Network refuses | Topology enabled; dataset below v8; not owner; not DEFAULT | Disable topology; Upgrade Dataset to 8 |
| **Unit/range errors** (Reserve Unit IDs fails; combine rejected; second From/To) | Range would regroup an object or hit a connectivity assignment; gaps between units; one From and one To per grouped edge; grouped edge to ungrouped junction unsupported | Pick a gap boundary; make units consecutive; set combine policy; use a Connector Junction; divide first |
| Reset broke splices | Reset renumbered units | Query first; recheck circuits |
| **No path / one direction only** | Unit sequences differ across a splice; `firstUnit`/`lastUnit` omitted; virtual circuit traced as path | Align units; set trace location units; Circuit trace |
| Many near-identical paths | Splitters without Splitter category; `numPaths` high | Assign Splitter/Mux-Demux; lower `numPaths` |
| **Circuit errors**: Invalid after import; no paths on long routes (Max Hops 100); won't verify (subcircuit Dirty); delete "did nothing" | Imported Dirty by default; locations lack Circuit Location; more than one path; sections out of order | Verify (Force verify); raise Max Hops (topology disabled); verify providers first; Export Circuits with acknowledgment (default version) |
| Edits missing from traces | Unlocatable nonspatial object; not validated | Validate locatability; add associations; validate |
| Circuits REST auth error | Missing Advanced Editing (Query exempt) | Assign extension |
| Import Associations rejects CSV | Unit columns missing | Add them |

Detail: `rest-api/07-circuits-and-unit-identifiers-telecom.md`.

---

## 11. Triage flowchart

```
START: "Something is wrong"
 |
 A. Is it a licence / owner / permission message?  (003049, 002144, 001400, "owner of the version",
 |   greyed-out command)  --yes-->  Section 7.1 (licence, network owner, version owner)
 no
 |
 B. Which surface and versions? (Pro, Enterprise, UN dataset v?, Foundation release)
 |   mismatch with matrix? --yes--> Section 9
 no
 |
 C. Is network topology enabled?  (Network Properties; Status 0 everywhere?)
 |   no --> enable on DEFAULT as owners; expect large validate (1.2 rank 5)
 yes
 |
 D. Dirty areas near the problem?
 |   Status has edit bit (1/2/4)  --> Validate footprint --> retest
 |   Status error-only (8/16/32)  --> read Error(s)/code (2.1, 2.2) --> EDIT the cause --> validate
 |   none
 |
 E. What is the symptom?
 |     trace wrong/empty/slow ---------> Section 4  (then learn/07 section 19)
 |        subnetwork-based? ------------> Subnetworks table: Dirty/Invalid? --> Section 3
 |     subnetwork update fails ---------> Section 3.1 (dirty areas? unsaved? errors 24..47?)
 |     rule / association refused ------> Section 5
 |     differs between versions/users --> Section 6
 |     publish / service problem -------> Section 7.2
 |     load / migrate ------------------> Section 8
 |     domain-specific ----------------->  Section 10 (phases, isolation, flow direction, units/circuits)
 |
 F. Still unexplained?
      Error 46 or odd topology  --> Rebuild Network Topology (extent) --> Verify --> Repair (owners, DEFAULT)
      Whole-network audit       --> Analyze Network Data; community SummarizeUNErrors; Esri Support
```

## 12. What to ask the user first

1. Exact message text and number (tool error, error ID, REST `extendedCode`), and a screenshot of the Dirty Areas row (`Status`, `Error code`, `Error message`).
2. Versions: ArcGIS Pro, ArcGIS Enterprise (and patch), **UN dataset version** (Describe `schemaGeneration`), Foundation and release.
3. Surface: Pro tool, Pro pane, REST/JS, Field Maps, script. Which account and connection (database user and portal sign-in)?
4. Deployment: single-user or enterprise; branch versioned? Which version are they editing and tracing in (DEFAULT or named)? Saved?
5. Topology state: enabled? Last validate (when, what extent, on which version)? Any dirty areas or errors near the feature?
6. Domain network and tier: traditional or telecom; tier name; which trace type, which named configuration.
7. Subnetwork status: Dirty, Clean or Invalid; controllers present; last update; did Update Subnetwork fail?
8. What changed recently: load, rule change, Foundation update, upgrade, reconcile/post, new asset type?
9. Scale: feature count, dirty-area count, error count by ID.
10. Is it intended behaviour? (open points, abandoned assets, backup sources, exceptions.)

## Common misconceptions

- "Validate succeeded, so the errors are gone." Success means the job ran; error-only rows (8/16/32) are ignored and need an edit.
- "Error 32 is the same as Status 32." One is an inline-weight error ID, the other a subnetwork-error bit.
- "Every error ID from 0 to 47 is documented." Ten are not (3, 4, 7, 11, 12, 14, 15, 16, 22, 45).
- "Error 18 needs a containment rule." Esri's text says so, but the condition concerns structural attachment.
- "Dirty areas coming back after post means the validate failed." Esri records it as As Designed.
- "Portal owner and database owner are the same thing." Different accounts, different errors (002144 versus 001400).
- "Trace permission needs the extension." Query and trace do not; create, publish, edit, validate and update do.
- "Unknown subnetwork is always an error." Guys, neutrals, proposed and abandoned features are often valid exceptions.
- "A trace never fails on stale data." With Validate Consistency off, it silently uses the old topology.

## Quick checks

- Does the Dirty Areas table show a `Status` with an edit bit near the feature?
- Is `Error code` decoded (log2) and each bit looked up in sections 2.1 and 2.2?
- Which of the three owners (licence, network owner, version owner) is failing?
- Is the subnetwork Dirty, Clean or Invalid, and did a validate run after the last edit?
- Does the failing ID appear in the undocumented list in section 2.3?
- Was Validate Consistency on in the trace, and is the trace version the same as the edit version?
- Are rule or definition changes visible in this version (reconciled) and service (restarted)?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`
- `learn/03-topology-engine-and-validation.md`
- `learn/04-rules-and-connectivity-design.md`
- `learn/05-attributes-categories-and-attribute-rules.md`
- `learn/06-tiers-and-subnetworks-in-depth.md`
- `learn/07-tracing-in-depth-and-configuration-library.md`
- `pro-help/04-associations-editing-errors.md`
- `pro-help/06-administration-subnetworks-topology-versioning.md`
- `pro-help/08-asset-packages-foundations-migration.md`
- `pro-help/09-dataset-versions-compatibility-upgrade.md`
- `pro-help/10-publishing-ownership-licensing.md`
- `pro-help/11-migration-and-schema-mapping.md`
- `rest-api/01-utility-network-server-and-trace.md`
- `rest-api/02-topology-and-subnetwork-management-operations.md`
- `rest-api/04-version-management-validation-feature-service.md`
- `rest-api/07-circuits-and-unit-identifiers-telecom.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/tool-errors-and-warnings/001001-010000/tool-errors-and-warnings-02026-02050-002041.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/tool-errors-and-warnings/001001-010000/tool-errors-and-warnings-02051-02075-002066.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/tool-errors-and-warnings/001001-010000/tool-errors-and-warnings-03026-03050-003049.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/verify-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/import-associations.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/upgrade-dataset.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://support.esri.com/en-us/knowledge-base/understanding-error-attributes-in-dirty-areas-table-for-000034757
- https://support.esri.com/en-us/knowledge-base/problem-the-apply-asset-package-tool-fails-in-arcgis-pr-000027843
- https://support.esri.com/en-us/bug/unexpected-association-conflicts-occur-in-named-version-bug-000141682
- https://support.esri.com/en-us/bug/in-arcgis-utility-network-dirty-areas-reappear-during-r-bug-000156036
- https://support.esri.com/en-us/bug/the-export-subnetwork-tool-fails-and-returns-the-error-bug-000146789
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/pipeline-subnetwork-errors
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/managing-electric-networks-updating-subnetworks
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/electric-quality-assurance
- https://community.esri.com/t5/arcgis-utility-network-questions/validate-network-topology-workflow/m-p/1133812 (community, secondary)
- Existing reference files in this skill (cited inline) for facts already verified there: dirty-areas page, network topology actions, utility network dataset administration, compatibility and upgrade history pages.
