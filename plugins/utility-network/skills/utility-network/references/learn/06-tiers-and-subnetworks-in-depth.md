# Utility Network: Tiers and Subnetworks, Design and Operations Walkthrough (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)
> Sources: Esri ArcGIS Pro 3.7 help and tool reference, Esri Solutions Foundation pages, Esri blogs and Community threads (full list at the end). Practitioner statements are labelled.

A tier is a rule set; a subnetwork is the cached result of tracing from controllers under that rule set. Almost every confusing symptom (names showing `Unknown`, Update Subnetwork refusing to run, an Invalid status, "inconsistent controller names") comes from not holding that distinction. Read this file when you are **designing** the tier model for an industry, **setting up** controllers, **operating** the update/export cycle, or **decoding** subnetwork errors. It is the design-and-operations companion to `pro-help/06-administration-subnetworks-topology-versioning.md`, which stays the compact reference for tool defaults and administration; read both for a full picture.

## Contents
1. The model in one picture
2. Domain networks: partitioned versus hierarchical, source versus sink
3. Tiers: ranks, groups, topology type, naming
4. The subnetwork definition: what a tier actually configures
5. Controllers and terminals
6. The Subnetworks table and SubnetLine
7. The life cycle as a flow
8. Tier topology versus subnetwork containment, and name inheritance
9. Multi-source, mesh and mixed situations
10. Update Subnetwork: options and behaviour
11. Export Subnetwork: what it produces
12. Subnetwork errors and the number 32
13. Tier design by industry
14. Common misconceptions, quick checks, related files, sources

## 1. The model in one picture

```
Utility network
 +-- Structure network                 (no tiers, never)
 +-- Domain network "Electric"         (traditional; PARTITIONED; SOURCE)
 |     +-- Tier Transmission  rank 1   --> subnetworks: 765kV, 345kV ...
 |     +-- Tier Distribution  rank 2   --> subnetworks: Circuit 0001, 0002 ...
 +-- Domain network "Pipeline"         (traditional; HIERARCHICAL; SOURCE)
 |     +-- Tier group "Distribution"
 |           +-- Tier System    rank 1 --> subnetworks: Town-border station A ...
 |           +-- Tier Pressure  rank 2 --> subnetworks: Zone 3000 ...
 |           +-- Tier Isolation rank 3 --> subnetworks: Isolation area 17 ...
 +-- Domain network "Comms"            (telecom; NO tiers, NO subnetworks)
```

Vocabulary (Esri): a **tier** is a collection of subnetworks that share the same properties and restrictions. A **subnetwork** is a topological subset of a tier, defined by one or more **controllers**. A **domain network** holds the tier model. A utility network supports up to **63 tiers** across all its domain networks, and the structure network has none.

Mechanism: the stored artefacts of a subnetwork are (a) its name stamped on member features, (b) one Subnetworks-table row per controller, (c) one SubnetLine row, and optionally (d) a system diagram. There is no feature class that "contains" the members; membership is discovered by tracing and cached by Update Subnetwork.

## 2. Domain networks: partitioned versus hierarchical, source versus sink

Two choices are made once, in **Add Domain Network**, and shape everything after:

| Choice | Options | Effect |
|---|---|---|
| Tier definition | Partitioned, Hierarchical | how tiers relate; whether tier groups exist; how many tiers a feature may be in |
| Subnetwork controller type | Source, Sink | whether the resource flows away from controllers (source) or towards them (sink) |

**Partitioned** (Esri: for sequential systems such as electric and telecommunications): tiers are in a linear, ordered relationship; a feature belongs to **only one tier**; barrier features or subnetwork controllers can be boundaries and belong to subnetworks in several tiers; tiers sit directly in the domain network. Topology type may be radial or mesh. **Hierarchical** (Esri: for nested systems such as gas and water): the same feature can be in several tiers; tiers sit in **tier groups**; only mesh topology, set automatically.

Industry intuition: electric transmission and distribution are different physical systems with separate equipment; a distribution transformer is not "inside" a transmission subnetwork. In gas or water, one valve is simultaneously in the supply system, in a pressure zone and in an isolation area. Practitioners summarise it as "partitioned: each feature has one subnetwork and the network does not store the higher or lower relationship (you find it by upstream/downstream tracing); hierarchical: subnetworks nest and a feature carries several subnetwork fields" (Esri Community answers).

Design rules of thumb (Esri guidance, paraphrased):

- need one assignment per asset (one voltage level, one circuit): partitioned;
- need the same asset analysed at nested scales, or need to trace from an inlet to all terminal discharge points: hierarchical (Esri stormwater blog: hierarchical gives "all terminal discharge points", partitioned gives "nearest outfall");
- choose **source or sink before building**; a domain network uses one controller type, not both. Sewer and stormwater are sink-based (many inlets per outlet, so modelling the outlets is more manageable).

Related parameters of the tool: Domain Network Name (prefixes the class names, for example `ElectricDistributionJunction`), optional alias; topology must be disabled; enterprise needs the database utility network owner connection, portal owner and the default version. Telecom uses the separate Add Telecom Domain Network tool, and Esri states a telecom domain network **does not support subnetwork management**; it uses circuit management tables (Circuit, CircuitSection, Subcircuit) instead (`rest-api/07-*.md`, Esri Foundation documentation).

Hard to change later: tier definition and controller type shape rules for terminals, validation cost and tool availability. Decide before loading data.

## 3. Tiers: ranks, groups, topology type, naming

**Rank** (Esri): the position of a tier in the domain network; it controls the trace order of subnetworks across tiers. **Rank 1 is the highest.** Parallel ranks (several tiers at one rank) are allowed for both tier definitions.

| | Partitioned | Hierarchical |
|---|---|---|
| Who sets rank | you, in Add Tier (Esri's Tiers page says an omitted rank becomes lowest rank + 1, but the Add Tier tool page lists Rank as required, so pass it explicitly) | automatic, fixed; add tiers **highest first** (first is rank 1) |
| Scope of ranking | whole domain network | per tier group |
| A tier's rank | exactly one rank, but a rank may hold many tiers | per group |

Pro help example: transmission rank 1, medium voltage rank 2, low voltage rank 3. **Sink-based note:** Esri's stormwater blog uses Catchment rank 1 ("ultimate sink") and Subcatchment rank 2, so in a sink network rank 1 is the tier at the final destination; keep the "rank 1 = highest" statement and read "highest" as "closest to the ultimate source or sink of the system".

**Tier groups** (hierarchical only; Add Tier Group): each group models a sector, such as gathering, transmission, distribution or cathodic protection in gas. Tiers are named by combining the group and the tier, for example "Gathering Isolation". A single-sector network still needs one domain network with one tier group. Partitioned and telecom domain networks do not use tier groups.

**Topology type** (Mesh or Radial): chosen at tier creation. Esri states it **currently makes no difference to tracing or subnetwork management** and is under development for a future release. Hierarchical tiers are mesh only. Do not design around it; record the intent for the future.

**Add Tier** (Esri tool and "Define a tier"): topology disabled; tier name unique in the utility network, at most 64 characters, with a list of forbidden characters (including `. ! ' [ ] ; :: { } | \ < > ? @ $ % ^ * + = ~` and backtick); network classes must be **empty** because the tool adds a non-nullable subnetwork-name field.

**Subnetwork name fields.** Hierarchical: the `Subnetwork Field Name` parameter of the first tier in a group creates a string field on every domain network class (length 2000, indexed, not editable, not nullable, default `Unknown`); later tiers in that group reuse it; different groups may use different fields. Partitioned: one system field, `Subnetwork name`, is added with the first tier.

**Practitioner consensus on substation tiers** (Esri Community thread, several experienced users): keep transmission, sub-transmission and distribution as separate ranked tiers and model substation internals with containment or connectivity associations; a single "substation" tier spanning voltage levels caused rank and trace-order conflicts because a tier belongs to one rank. Verify with your own model before copying.

## 4. The subnetwork definition: what a tier actually configures

Set with **Set Subnetwork Definition** (topology disabled; enterprise: default version, portal owner and database owner; rerun to change). Think of it as three layers:

| Layer | Meaning | Components |
|---|---|---|
| **Supported classes** (what may belong) | enforcement list; a connected feature whose asset type is not valid makes the update fail with an error | Valid Devices, Valid Lines; Valid Junctions, Valid Junction Objects, Valid Edge Objects (UN v4+); Valid Device / Junction Object Subnetwork Controllers |
| **Trace configuration** (how the subnetwork is found) | used by Update, Export and Trace each time | Condition Barriers, Function Barriers, Include Barrier Features (default on), Apply Traversability To (default both), Include Containers / Content / Structures (UN v5+, default off per the tool page), Validate Locatability (UN v5+, off) |
| **Outputs and policy** (what update writes) | results and behaviours | Aggregated Lines for SubnetLine, Summaries, Subnetwork Diagram Templates, Propagators (Python), Update Structure / Domain Network Containers (UN v4+, default on), Manage IsDirty (UN v5+, on unless no controllers are defined), Edit Mode for Default and Named Version (UN v4+, default Without eventing), Support Disjoint Subnetwork (partitioned only; hierarchical always on) |

Notes:

- **Valid lists are enforcement, not hints.** Boundary features are exempt from the Valid Devices check (Esri Update Subnetwork page). Error IDs 24, 26, 40, 41, 42 are the symptoms (section 12).
- **"Supported" versus "propagator":** the *supported* lists decide membership; *propagators* carry an attribute (phase, pressure, voltage) from controllers outward and store it in the Propagated Attribute field on downstream features. Propagators have no effect on membership except that a false propagator expression turns the feature into a barrier.
- **Summaries** (Min, Max, Average, Count, Add, Subtract with optional filter) write one value per SubnetLine field. `Subtract` is not allowed for controller and loop trace types. The Esri tool page has a matrix of valid field types per function.
- **Aggregated lines** must be a subset of Valid Lines and have geometry; they merge into the SubnetLine geometry.
- **Include Containers / Content / Structures:** the tool page defaults them to off, while the Esri "Subnetwork trace configuration" topic describes them as enabled; read the actual setting in Network Properties for your network. The container policies (Update Structure / Domain Network Containers) need Include Containers to have an effect.
- **Python-only parameters:** barriers, Apply Traversability To and Propagators on the Update/Export tools are Python-only (no UI).
- Version note: the Pro 3.7 tool page lists these floors; older datasets expose fewer options. Check `pro-help/09-*.md` before scripting against an old dataset.

## 5. Controllers and terminals

**Definition.** A subnetwork controller is a **terminal** on a device or junction object that marks the origin (source) or destination (sink) of a subnetwork. It is set per terminal, so one device with several terminals can serve several subnetworks.

**Eligibility checklist** (Esri subnetwork controller page, Subnetwork Controller category page):

1. The asset type has a terminal configuration with a suitable terminal. Partitioned tiers accept **directional** terminals only, with at least one upstream and one downstream terminal; hierarchical tiers accept directional or bidirectional.
2. The asset type has the **Subnetwork Controller** network category (traditional domain networks, Device class and JunctionObject table).
3. The asset type is listed as a valid controller in the tier's subnetwork definition.
4. The terminal matches the domain network's controller type: source-based networks offer **downstream** terminals, sink-based offer **upstream** terminals (downstream controllers behave as sources, upstream as sinks).

**The six inputs** (Esri electric, water and gas blogs): tier name; terminal; controller device; **controller name** (unique within the tier; also stored on the device, in the Subnetworks table and in SubnetLine); **subnetwork name** (shared by all controllers of one subnetwork; stored on features); the line(s) connected to the terminal.

Which terminal in practice (examples; asset types and ports come from Esri blogs and Foundation tutorials, and differ by model):

| Network | Controller asset type | Terminal used | Tier |
|---|---|---|---|
| Electric distribution tutorial | Circuit breaker | `CBD:Line Side` | Electric Distribution |
| Electric transmission tutorial | Power transformer | `2wXFR:Secondary` | Transmission (subnetwork name `765kV`) |
| Gas blog | Wellhead / custody transfer meter / compressor / regulator | outlet / outlet / High Pressure Out / low-pressure out | Gas System (first three), Gas Pressure (regulator) |
| Water tutorial | Treatment plant; pressure valve | `Outlet Port`; `Low Pressure Out` | Water System; Water Pressure |
| Sewer tutorial | Treatment plant; Directional Manhole | `Inlet Port`; `Upstream` | Sewer Collection System; Sewershed |

**Pro steps** (Esri tutorials): select the feature, Utility Network tab > Subnetwork group > **Modify Controller**, Add Selected, set terminal first (tutorials report the dialog can default to the wrong, upstream terminal; the Esri help only says to choose the terminal from the drop-down), tier, controller name, subnetwork name, description, Apply, **Validate**, **Save**, then Update Subnetwork. Bulk: **Import Subnetwork Controllers** (disable topology first for speed) from a CSV; Esri's transmission tutorial ships a `SubnetworkControllers.csv`. arcpy has `EnableSubnetworkController` / `DisableSubnetworkController` on the `UtilityNetwork` class (`arcpy/01-*.md`); REST has `enableSubnetworkController` (`rest-api/02-*.md`).

**Restrictions.** A device or junction object serving as a controller **cannot be deleted** and its asset group and type become read-only (changing them anyway creates error 33). Do not remove terminals or alter valid paths of the terminal configuration used by the controller category; give controllers their own configuration. Terminal configurations are permanent per asset type after topology has been enabled once (`pro-help/02-*.md`).

**Multiple controllers.** Radial and mesh subnetworks both support them; they share one subnetwork name and carry different controller names. A trace that meets controllers with different subnetwork names returns an error (all trace types except Connected).

## 6. The Subnetworks table and SubnetLine

**Subnetworks table** (system, read-only, one row per controller terminal). Fields (Esri page): `OBJECTID`, `SUBNETWORKCONTROLLERNAME`, `TIERRANK`, `TIERNAME`, `TIERTOPOLOGYTYPE`, `FEATUREGLOBALID`, `FEATUREASSETGROUP`, `FEATUREASSETTYPE`, `FEATURESOURCEID`, `FEATURETERMINALID`, `DOMAINNETWORKNAME`, `SUBNETWORKNAME`, `ISDIRTY`, `ISDELETED`, `SUBNETLINEGLOBALID`, `LASTUPDATESUBNETWORK`, `LASTACKEXPORTSUBNETWORK`, `DESCRIPTION`, `NOTES`, `CREATIONDATE`, `CREATOR`, `LASTUPDATE`, `UPDATEDBY`, `GLOBALID`.

- `ISDIRTY` has the alias *Is dirty*, or *Status* on newly created utility networks, and holds clean, dirty or invalid. Esri does not publish the stored numeric codes on that page: read a few rows next to the Pro status before filtering on a number.
- `ISDELETED` true means the terminal was removed as a controller. The row persists until an acknowledged export (or, if the tier does not manage `Is dirty` and you update on the default version, until Update Subnetwork removes it).
- `LASTUPDATESUBNETWORK` is the last Update Subnetwork run; `LASTACKEXPORTSUBNETWORK` changes only for an acknowledged export.

Illustrative query (placeholders; use your Subnetworks table name):

```sql
-- Which subnetworks are not clean? Interpret ISDIRTY against what Pro shows.
SELECT TIERNAME, SUBNETWORKNAME, SUBNETWORKCONTROLLERNAME, ISDIRTY, LASTUPDATESUBNETWORK
FROM <SubnetworksTable>
WHERE ISDELETED = 0
ORDER BY TIERRANK, SUBNETWORKNAME
```

**SubnetLine** (system, read-only, one feature per subnetwork): `ISDIRTY`, `TIERNAME` (subtype field), `SUBNETWORKNAME`, `SUBNETWORKCONTROLLERNAMES`, `LASTUPDATESUBNETWORK`, `LASTACKEXPORTSUBNETWORK`, plus summary fields you add. Connected aggregated lines merge into one feature, so it can be multipart; with summaries configured a record exists even without controller-connected lines (empty geometry), useful for non-spatial features or overlapping subnetworks. **Versioning:** reconcile includes SubnetLine, **post does not** because the class is valid only in the version where the update ran; after posting, validate the new dirty areas and update again on the default version. Whether `SubnetLine` carries `ASSETGROUP`/`ASSETTYPE` fields is not stated on the Esri page (the `TIERNAME` field is its subtype field); verify against the Esri docs for your version.

## 7. The life cycle as a flow

```
  [set controller] --> [Validate topology] --> [Update Subnetwork] --> Clean
        |                     |                       |
   Dirty (no rows yet)   marks affected subnetworks   success: Clean
                         Dirty                        failure: Invalid (skipped until made Dirty)
  [modify/remove controller] --> validate --> update
  [Export Subnetwork] (Clean only)
  [Delete]: remove ALL controllers --> validate --> update --> export with acknowledgement
```

Statuses (Esri life-cycle page, tier manages Status):

| Status | Meaning | Left by |
|---|---|---|
| **Dirty** | validated edits not yet processed by Update Subnetwork | successful update |
| **Clean** | Subnetworks table, SubnetLine, system diagrams and feature fields match topology | validate marks it Dirty |
| **Invalid** | validate-consistency failures or subnetwork errors during update; skipped by later updates; Enterprise 11.1+ for this status | fix, validate (makes Dirty), update |

If the tier does not manage `Is dirty`, subnetworks always show Dirty whether updates succeed or fail, and Export Subnetwork (Clean only) is unavailable. Esri's Water Foundation sets Manage IsDirty off for all subnetworks since version 1.1 for performance, per Esri.

Effect of actions on status:

| Action | Controllers, SubnetLine, diagrams |
|---|---|
| Enable topology | all Dirty |
| Disable topology | controllers and SubnetLine Dirty; diagrams stop being system diagrams |
| Create or edit features | no status change (dirty areas only) |
| Validate topology | modified subnetworks Dirty |
| Update (success / failure) | Clean / controllers and SubnetLine Invalid, diagrams stay Dirty |
| Remove controller | `ISDELETED` true, no status change |
| Export with acknowledgement | deleted rows removed; `LASTACKEXPORTSUBNETWORK` set |

**Delete a subnetwork** (Esri): remove all controllers of that subnetwork name (rows marked deleted) > validate > Update Subnetwork (clears names from the features, so analytics no longer see controllers) > Export Subnetwork with **Set export acknowledged** on the default version. With several controllers the subnetwork persists until every one is removed and exported; removing the last also removes the SubnetLine record and system diagram.

**Rename** (practitioner reading of Esri steps): change the name on all controllers, validate, save, update; old rows become `ISDELETED` and new rows are written.

## 8. Tier topology versus subnetwork containment, and name inheritance

Two ideas are easy to confuse:

- **Tier topology** is the *design-time* shape: ranks, tier groups, topology type, valid lists.
- **Subnetwork containment** is the *run-time* result: which features each subnetwork contains, stored as name fields.

**Partitioned** (electric): features belong to one tier. The hand-off points are controllers or barriers, which may belong to subnetworks in two tiers (a station breaker is the controller of a distribution subnetwork and the end of a higher-voltage one). The network stores no pointer from a distribution circuit to its upstream transmission subnetwork; you find the relationship with an upstream trace. Error 47 flags traversable controllers assigned to different tiers.

**Hierarchical** (gas, water): a feature in a lower-tier subnetwork **also participates** in the higher-tier subnetworks (a valve in an isolation subnetwork is in its pressure and system subnetworks). Each tier group's tiers carry their own name field, so one valve can show system, pressure and isolation names at the same time. Error 27 (parent not exactly one rank higher) applies to UN version 1 only; errors 29 and 30 flag inconsistent names of controllers and parent controllers.

**Name fields** (Esri "Subnetwork name"):

| Field | Holds | Notes |
|---|---|---|
| Subnetwork name | subnetwork a traversable feature belongs to | on every class except Assembly; `Unknown` = not updated or no traversable path to a controller |
| Supported subnetwork name | subnetworks a **container or structure** supports | domain classes UN v4+; on structure classes the `Subnetwork name` field carries this alias |
| Supporting subnetwork name | subnetwork of the container that supports a **content** feature | domain classes, UN v5+ |

Several values join with `::` (for example `Subnetwork B::Subnetwork C`). Esri's example: a line in Subnetwork A that contains features of B and C has Subnetwork name A, Supported name `B::C`, Supporting name Unknown; a junction contained by a device in A has Subnetwork name Unknown and Supporting name A.

**Inheritance in practice.** Names are not copied by rules; Update Subnetwork writes them from a trace. Containers and structures pick up names only if the definition enables the container policies and Include Containers/Content/Structures. Hence "my vault shows Unknown" usually means Include Containers is off or the update has not run since the contents changed. Hierarchical inheritance means a lower-tier update writes the lower-tier field only; you still update the higher tiers (water tutorial order: update Water System, then Water Pressure; after adding a pump as pressure controller, update the pressure zone, then update the water system so the source is included).

## 9. Multi-source, mesh and mixed situations

| Situation | How the UN handles it | Design guidance |
|---|---|---|
| Radial feeder with one breaker | one controller, one subnetwork | the default pattern (electric circuit) |
| Two or more sources feeding one area (looped or backup supply) | several controllers with the **same subnetwork name**, different controller names | name the subnetwork, not each controller; mesh tier |
| Meshed secondary / spot network | mesh subnetwork with several controllers (network transformers, per the electric Foundation blog) | Esri notes secondary subnetworks are usually created only for large complex areas such as mesh networks |
| Water pressure zone fed by tanks, towers, pumps and a PRV | one pressure subnetwork, several controllers, one zone name | Esri water blog: three tanks each named after themselves caused errors; recreate with unique controller names and one common zone name, validate, update |
| Backup or standby source with a normally open path | traversing a closed path to a differently named controller raises error 29 | isolate the backup controller (check open device and snapping) or remove its controller assignment |
| Gas pressure systems | regulators/compressors as pressure controllers; wellheads, custody transfer meters at system tier | one regulator per pressure subnetwork unless truly redundant |
| Disjoint pieces with the same name | allowed only if Support Disjoint Subnetwork is true (partitioned) or always (hierarchical); otherwise error 28 | enable support deliberately, since it also hides digitising gaps |

Esri's own overview diagram: tier A radial with one source and subnetwork A1; tier B radial with three sources (B1 one source, B2 two sources and no loops); tier C mesh with C1 three sources and several loops. Remember radial versus mesh is currently informational (section 3).

Subnetworks of different tiers overlapping at a boundary: partitioned boundaries are shared on purpose; hierarchical overlap is by design; inconsistent neighbours at boundary features produce **warnings**, not errors, in Update Subnetwork (resolve the neighbours and rerun).

## 10. Update Subnetwork: options and behaviour

Pro tool parameters (Pro 3.7): Input Utility Network, Domain Network, Tier, **All subnetworks in tier** (default off; on = asynchronous run on the `UtilityNetworkTools` service), Subnetwork Name (ignored with All; the choice list is empty when the tier has 10,000 or more records, so type the name), **Continue on failure** (default off), and Python-only Condition Barriers, Function Barriers, Include Barrier Features (default on), Apply Traversability To, Propagators.

Requirements: topology enabled; edits saved; **no dirty areas intersecting the subnetwork's features**; traditional domain network only; enterprise: branch-versioned network, input from a utility network service, Advanced Editing user type extension; Standard or Advanced licence. Update a given subnetwork with one process at a time; do not run several All-subnetworks processes at once (two can collide).

Processing order (Esri): validate controllers > trace > check the trace for invalid features/objects > write subnetwork name, `Is connected`, substitution and propagated values > create or update SubnetLine > update the Subnetworks rows > create or update system diagrams. On failure the subnetwork goes Invalid and only editor-tracking fields are updated.

**Edit mode** (definition setting):

| | Without eventing (default) | With eventing |
|---|---|---|
| Speed | faster; geodatabase contracts not honoured | slower on large subnetworks with many rules or feature-linked annotation |
| Attribute rules, editor tracking, history | not triggered | triggered |
| Default version | updates all features of the subnetwork | same, but holds a **shared lock for the whole operation** (can block reconcile) |
| Named version | updates only features edited in that version | all traversed features, via cursor updates |

REST: `updateSubnetwork` takes `domainNetworkName`, `tierName`, and either `subnetworkName` or `allSubnetworksInTier=true`, plus `continueOnFailure`, `traceConfiguration` (overrides the tier's configuration), `async`, `gdbVersion`, `sessionId` (named versions) (`rest-api/02-*.md`, `rest-api/06-*.md`). With `continueOnFailure=true` the response lists `failures` items.

Companion tool: **Update Is Connected** (separate, default version, portal owner, traditional only) recalculates `Is connected` for the whole network by connectivity to a controller, independent of traversability; new features start Unknown.

Practitioner guidance (Esri blogs): adopt a zero-tolerance policy for errors and dirty areas before creating subnetworks; you can create a subnetwork with data errors but cannot trace or update it until they are fixed; in a first-time rollout set controllers at the edges/lowest tier of nested zones and work inward, and update tiers in rank order; exclude services, laterals and cathodic protection lines from aggregated lines for readable maps (community advice cited in Esri Foundation documentation).

## 11. Export Subnetwork: what it produces

**Purpose:** write a subnetwork's information to a **JSON file** for external systems such as outage management or asset tracking. It does not change data unless acknowledgement is set. The subnetwork must be **Clean** (so Update Subnetwork first), traditional domain networks only.

Parameters (Pro 3.7): Input Utility Network, Domain Network, Tier, Subnetwork Name, **Set export acknowledged** (default off), Output JSON, Python-only barriers/traversability/propagators, Include Barrier Features (default on), **Include geometry** (default off), Result Types (Connectivity, Features, Containment and attachment associations, Related records), Result Network Attributes, Result Fields, Include domain descriptions, Related Record Fields, Include flow directions, Include propagated values.

Version floors (enterprise): Related records result type **Enterprise 11.5+**; Include flow directions and Include propagated values **Enterprise 12.1+**.

Output (per the page): controllers, feature elements, connectivity, associations, optional geometry, domain descriptions, flow directions (Connectivity and Features types), propagated values (Features type), and values of requested network attributes and fields. REST `exportSubnetwork` returns a URL to the file (`{"moment","url","subnetworkHasBeenDeleted","success"}`) and top-level keys are listed in `rest-api/02-*.md`; no payload is returned inline.

**Acknowledgement:** requires topology enabled and the **default version**; enterprise needs the portal utility network owner. It updates `LASTACKEXPORTSUBNETWORK` on the Subnetworks row and the SubnetLine feature, and physically deletes rows of removed controllers (`ISDELETED` true). When all controllers of a deleted subnetwork are removed and exported with acknowledgement, no JSON file is created.

## 12. Subnetwork errors and the number 32

Two different numbers named 32 exist; mixing them up wastes hours.

| Number | Where | Meaning |
|---|---|---|
| **Status = 32** | dirty-area `Status` bitmask (0 disabled, 1 inserted/updated, 2 deleted, 4 associated objects modified, 8 feature error, 16 object error, **32 subnetwork error**) | an error stored from a subnetwork operation; values combine (for example 33 = edit plus subnetwork error). `scripts/decode_dirty_status.py` decodes it |
| **Error ID 32** | Esri error list: "Error setting weight values" | a point feature has an in-line network attribute value outside the allowed range (see `pro-help/04-*.md` for the full list) |

Subnetwork and tier error IDs (Esri "About error features"):

| ID | Name | Typical cause and fix |
|---|---|---|
| 24 / 26 / 40 / 41 / 42 | invalid line / device / junction / junction object / edge object for tier | asset type not in the tier's Valid list; allow it (topology off), reclassify, or change data |
| 27 | invalid parent subnetwork | hierarchical, **UN version 1 only** |
| 28 | disjoint subnetwork not supported | same-named pieces not connected; enable support (partitioned) or connect them |
| 29 | inconsistent subnetwork name | traversable controllers with different names; align names, isolate the backup controller or remove its assignment |
| 30 | inconsistent parent subnetwork name | hierarchical parents differ; align them |
| 33 | inconsistent controller asset group/type | controller's AG/AT edited; restore or remove the controller first |
| 47 | multiple controllers from different tiers | tiers traverse each other; fix tier assignment or isolate |
| 37 | subnetwork tap placement | tap must sit midspan on exactly one line (enable/validate list) |

How they appear: when Update Subnetwork finds an error the status of all controllers in the Subnetworks table becomes **Invalid** and the SubnetLine row Invalid; the errors are stored as dirty areas (view the dirty-areas sublayer, popups or the Error Inspector); a failed update keeps system diagrams Dirty. Storage details vary by UN version (Esri "View errors"). Invalid subnetworks are skipped by later updates until made Dirty again.

## 13. Tier design by industry

Tier names, counts and ranks below come from Esri documentation, Esri blogs or Foundation tutorials as cited; Foundations change between releases and every utility customises. **Read the tier list in Network Properties of the applied Foundation (and its release notes) before copying a design.** I could not find a single Esri page listing the final tier definitions for each current Foundation; the Foundation tutorial pages I read name only the tiers they use.

**Electric (partitioned, source-based).**

- Esri Pro help: transmission rank 1, medium voltage rank 2, low voltage rank 3; controllers: circuit breakers for the medium-voltage tier, distribution transformers or network protectors for low voltage.
- Esri electric blog: tiers Transmission, Subtransmission, Distribution, Secondary. Controllers named: generation devices, power transformers (`2wXFR:Secondary`), transmission circuit breakers, distribution circuit breakers (`CBD:Line Side`), network transformers.
- Foundation tutorials: **Electric Distribution** tier with circuit breaker controllers (`CBD:Line Side`), subnetwork names like feeder numbers; a **Transmission** tier with power-transformer controllers (subnetwork `765kV`). Unbalanced-distribution tutorial reads one tier only.
- Design notes: model substations by containment/connectivity associations (Community consensus); batch trace tools exist for transmission voltage systems (Esri blog).

**Gas (hierarchical, source-based).**

- Esri gas blog: **Gas System** (shared sources: wellheads, compressors, custody transfer meters), **Gas Pressure** (pressure zone, regulators on the low-pressure out terminal), **Gas Isolation** (predetermined valve-isolatable area), **Cathodic Protection** (corrosion-protection subset; not placed in the hierarchy by the article).
- Pro help: tier groups for gathering, transmission, distribution and cathodic protection; example tiers named "Gathering Isolation" (group + tier). Foundation page: **Pressure** and **System** tiers, Isolation trace using an Isolating category.
- The two sources differ (flat four tiers versus tiers inside groups); both show the pattern, not a schema to copy.

**Water (hierarchical, source-based).**

- Esri water blog: **Water System** (treatment plant, wells, bulk meters as controllers), **Water Pressure** (zones; example controllers tower, tanks, PRV), **Water Isolation**, and named **District Metered Area** and **Cathodic Protection** tiers (not detailed).
- Foundation tutorial: Water System controller = treatment plant on `Outlet Port` (subnetwork "Naperville Water Distribution"); Water Pressure controller = pressure valve on `Low Pressure Out` (subnetwork "3000").
- Pressure zone controllers per Esri blog: pumps or pump stations, storage tanks/towers (confirm with an engineer), PRVs. DMAs: Esri names a DMA tier but I found no setup detail; treat as a design option to confirm.
- Practitioner guidance (Esri blog): the same zone name on all controllers of a zone; unique controller names.

**Sewer and stormwater (sink-based).**

- Sewer Foundation tutorial: **Sewer Collection System** (treatment plant on `Inlet Port`) and **Sewershed** (directional manholes on `Upstream`); processed in that order.
- Stormwater (Esri blog): sink-based, **partitioned** in the example; **Catchment** rank 1 ("ultimate sink") and **Subcatchment** rank 2 (always upstream), outlets registered as controllers, disjoint subnetworks supported. Alternative: hierarchical if you need all discharge points.

**Telecom.** Telecom domain networks have **no tiers and no subnetworks**; use circuits. The Communications Foundation (version 1.1, June 2021) replaced Copper, Coax and Fiber tiers by one **Cable** tier and added a **Communication Circuit** tier for the traditional-domain part (Foundation history not re-verified here; see Esri Foundation documentation and verify against the Esri docs for your version).

## Common misconceptions

- "A subnetwork is a feature or a class." It is a cached result (names, rows, one SubnetLine feature).
- "Deleting the controller device deletes the subnetwork." Controllers cannot be deleted; follow the remove > validate > update > acknowledged export sequence.
- "Radial and mesh topology types change tracing." Esri says currently they do not.
- "Rank 1 is the lowest-voltage / downstream tier." Rank 1 is the highest; in sink networks it is the ultimate destination tier.
- "Hierarchical ranks are mine to set." They are automatic and per tier group; add the highest tier first.
- "Clean means no dirty areas." Update still refuses while dirty areas intersect its features.
- "Status 32 is error 32." Different lists (section 12).
- "Update Subnetwork fires my attribute rules." Only with the With eventing edit mode.
- "Every industry uses subnetworks the same way." Telecom has none; hierarchical industries update every tier.
- "The subnetwork name is unique per controller." The controller name is unique per tier; the subnetwork name is shared by the controllers of one subnetwork.

## Quick checks

1. Which domain network and tier definition (partitioned or hierarchical) and controller type (source or sink)? Is it telecom?
2. Is the tier named in the tool the one the controller was set against, and is the asset type in its valid controller list?
3. Does the asset type carry the Subnetwork Controller category, and does its terminal configuration have a matching upstream/downstream terminal?
4. Are there dirty areas or errors intersecting the subnetwork (Error Inspector, Status values)?
5. What do the Subnetworks-table `ISDIRTY` and `ISDELETED` values and `LASTUPDATESUBNETWORK` say, and does the tier manage `Is dirty`?
6. Do all controllers of one subnetwork share the same subnetwork name and have unique controller names?
7. Which edit mode is set for the version you update in (with or without eventing)? Do rules need to fire?
8. For named versions: was the update repeated on the default version after post (SubnetLine is not posted)?
9. For containers, vaults and structures showing `Unknown`: are Include Containers and the Update Structure/Domain Network Containers options on?
10. Is a REST client sending `allSubnetworksInTier` or `subnetworkName` (not neither), with `async=true` for large tiers?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md` (life of an edit, derived state)
- `learn/03-topology-engine-and-validation.md` (dirty areas and validate)
- `learn/05-attributes-categories-and-attribute-rules.md` (categories, attribute rules, propagation attributes)
- `pro-help/02-structure-of-a-utility-network.md`, `pro-help/06-administration-subnetworks-topology-versioning.md`
- `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/06-asynchronous-operations-job-status.md`
- `arcpy/01-utility-network-module.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-hierarchies-with-tiers.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/tier-groups.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/define-a-tier.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-a-subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-tier.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-domain-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-life-cycle.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-name.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetworks-table.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetline-feature-class.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/update-subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/telecom-domain-networks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-categories.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-subnetwork-definition.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/export-subnetwork.html
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/enable-water-subnetworks.htm
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/enable-unbalanced-distribution-subnetworks.htm
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/enable-electric-transmision-subnetworks.htm
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/enable-subnetworks.htm
- https://doc.arcgis.com/en/arcgis-solutions/11.5/reference/use-gas-and-pipeline-referencing-utility-network-foundation.htm
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/use-water-distribution-utility-network-foundation.htm
- https://doc.arcgis.com/en/arcgis-solutions/latest/reference/introduction-to-communications-utility-network-foundation.htm
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/electric-creating-subnetworks
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/creating-gas-subnetworks
- https://www.esri.com/arcgis-blog/products/utility-network/water/creating-subnetworks-water
- https://www.esri.com/arcgis-blog/products/utility-network/water/water-subnetwork-errors
- https://www.esri.com/arcgis-blog/products/utility-network/water/utility-network-stormwater-networks
- https://community.esri.com/t5/electric-questions/electric-utility-network-subtransmission-and/td-p/1627012 (practitioner)
- https://community.esri.com/t5/arcgis-utility-network-questions/clarification-for-un-tier-type/td-p/1241283 (practitioner)
