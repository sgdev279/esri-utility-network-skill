# Utility Network: Performance, Scale and Operations (Deep Reference)
> Last reviewed: 2026-10-16 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro help and tool reference, ArcGIS Enterprise REST reference, Esri Support knowledge-base and bug pages, Esri blogs and Esri Community posts (full list at the end).*

## Why this matters / when to read this

Almost every "the utility network is slow" complaint is really one of five costs: a validate that has too much to do, an Update Subnetwork that traces too much, a trace that reads or returns too much, a service or client time-out that is shorter than the job, or a database that has not been maintained. This file teaches where each cost comes from, what Esri actually documents about it, and how to operate a network so the costs stay small. It also marks, very explicitly, where Esri gives **no numbers**: Esri's help does not publish a maximum feature count, dirty-area count, subnetwork size or rule count, so capacity planning is mostly a measurement discipline, not a lookup.

Labelling used throughout: **[Esri]** = stated on an Esri help, tool, REST, Support or blog page I read; **[Esri Community]** = a post on Esri Community (staff or user, secondary); **Practitioner guidance** = my reasoning or community experience, to be tested, not a rule.

## Contents

1. Where the time goes: a map of the costs
2. What Esri publishes, and what it does not
3. Loading and migration at scale
4. Validate: dirty-area volume, extent and batching
5. Update Subnetwork: what drives its cost
6. Trace performance
7. Trace result size and the service heap
8. Export Subnetwork, diagrams and other bulk outputs
9. Database tuning and maintenance
10. Service configuration: instances, time-outs, async
11. Maintenance routines and scripting patterns
12. Monitoring and diagnostics
13. Capacity-planning questions by industry
14. Upgrade planning (dataset versions)
15. Triage flow: "it is slow", what do I check first
16. Common misconceptions, quick checks, related files, sources

## 1. Where the time goes: a map of the costs

```
 EDIT --> dirty area --> VALIDATE --------> SUBNETWORK dirty --> UPDATE SUBNETWORK --> EXPORT / diagrams
 (cost: rules,   (volume =    (cost: dirty-area    (validate runs a     (cost: one trace per        (cost: result types,
  attribute      edits x       count, extent,      trace to find        subnetwork, tier config,    fields, geometry)
  rules)         areas)        errors, tier traces) modified subnetworks) edit mode, SubnetLine)

 TRACE (reads the cached topology): cost = elements traversed, not result size alone
 SERVICE: client time-out | UtilityNetworkTools async | heap for big results | instances
 DATABASE: statistics | indexes | I/O for topology pages | version-state housekeeping
```

Mechanism in one paragraph: the network topology is a graph stored in binary pages that traces and diagrams read, with portions cached as they are accessed [Esri, About network topology]. Edits do not touch it; validate does, driven by dirty areas. Validate also runs a trace to find which subnetworks the edit modified and marks them dirty; Update Subnetwork runs a trace per subnetwork and then writes names, propagated values and SubnetLine back to the features. So the same graph walk shows up in validate, update, trace and export, and the same levers (tier definition, barriers, what you include) help all of them.

Example (gas): a pressure zone defined with no stopping condition at closed valves means every validate that touches the zone traces the whole zone. A Support bug (section 5) records exactly this pattern for validation, with a tier-definition fix.

## 2. What Esri publishes, and what it does not

| Question | What Esri documents | Number published? |
|---|---|---|
| Max features / classes / network size | Nothing on the pages read (FAQ, tool pages, REST) | No. The FAQ page was read for limits and gives none |
| Max dirty areas | Not stated. Release-specific stalls with multi-million counts are mentioned in older patch notes (`pro-help/06-administration-subnetworks-topology-versioning.md`) | No |
| Max subnetwork size | Not stated | No |
| Max rules | Not stated (`learn/04-rules-and-connectivity-design.md`) | No |
| Max tiers | At most 63 across all domain networks (`learn/06-tiers-and-subnetworks-in-depth.md`) | Yes (a model limit) |
| Object ID range | UN dataset v7 uses 64-bit ObjectIDs, "more than 2.14 billion features" possible [Esri blog, 2024 release] | Yes (v7+) |
| Client time-outs | Most synchronous UN tools 10 minutes (600 s); Update Subnetwork 30 minutes (1,800 s) [Esri FAQ] | Yes (client side) |
| UtilityNetworkTools time-out | "Longer", preconfigured; FAQ gives no number | No (Esri states none; check your server) |
| Service heap for trace results | Default 64 MB; payload estimation formula and sizing table [Esri Support KB 000025326] | Yes |
| Diagram from a service | Fails above 49,999 features (error 160243) in the Pro 3.3 bug, "As Designed" [Esri Support bug 000168157] | Yes (verify in your release) |
| Name drop-down in tools | Empty when the tier has 10,000+ Subnetworks rows; type the name [Esri tool pages] | Yes (a UI behaviour, not a data limit) |
| Path trace defaults | `maxHops` 100, `numPaths` 1 on both the REST page and Pro tool page (see section 6) | Yes |

Rule for this skill: when a user asks "how big can X be", answer that Esri does not publish a limit, give the measurement method (section 12), and give Practitioner guidance clearly labelled.

## 3. Loading and migration at scale

**Esri documented.**

- Disable the topology before loading large volumes of data to reduce processing time; disabling creates one dirty area over the whole network and edits made while disabled are not tracked, so a re-enable validates everything [Esri, About network topology].
- Disable attribute rules during bulk loads (`learn/05-attributes-categories-and-attribute-rules.md`, section 15) and run batch rules over the loaded extent afterwards.
- Esri's tasks page recommends importing large numbers of associations or subnetwork controllers while topology is disabled (`learn/01-mental-model-and-life-of-an-edit.md`).
- For broad or heavy validation in enterprise, prefer the Validate Network Topology **tool** because it runs asynchronously [Esri, About network topology].
- Enable Network Topology has a *Maximum number of errors* (REST `maxErrorCount`, default 10,000) that stops the process; "Only generate errors" lets you check errors on unversioned data without enabling (`learn/03-topology-engine-and-validation.md`).

**Esri Community report (one case, not a benchmark).** A migration of more than 720,000 linear assets from a geometric network reported Enable Topology taking days, with about 440,000 errors dominating; replies said most enable/validate time goes into generating errors, suggested enabling on an unversioned dataset to iterate faster, and migrating in subsets (for example substation by substation). One reply reported going from over 100,000 errors (a 15-hour run that failed) to under 1,000 errors (25 minutes) after fixing terminals and junctions. A separate post on a very large sewer network (about 45.1 million feet of pipe) in a file geodatabase reported topology disable/enable close to an hour and tier creation over five hours; the accepted reply said a mobile geodatabase and a local drive performed much better, and the poster later had more success on an enterprise geodatabase. **Practitioner guidance:** treat these as shapes, not predictions. The consistent lesson is that error volume, not feature count alone, drives enable time, so clean connectivity errors before enabling.

**Practitioner guidance (loading).**

1. Load in a staging geodatabase (file/mobile for iteration, enterprise for the real thing), fix errors by category, only then load to production.
2. Use projected coordinates. A community reply noted that geographic coordinates would make the dirty area enormous; the case in the thread was projected.
3. Load subnetwork controllers and associations while topology is disabled, then enable once.
4. Take a database backup before the first enable; some changes cannot be undone (`learn/01-...`, "Bulk loads and configuration").

## 4. Validate: dirty-area volume, extent and batching

**Definition.** Validate Network Topology incorporates dirty areas into the topology and clears them where rules pass (`learn/03-topology-engine-and-validation.md`). Its cost is set by how much dirty footprint is in scope, how many errors it must write, and how many subnetworks it must trace.

### 4.1 What creates dirty-area volume [Esri]

A geometry edit creates two dirty areas (old and new envelope). Edits to ASSETGROUP/ASSETTYPE, to fields defined as network attributes, to associations and to terminal configuration also create them. Other attribute edits do not. An error feature gets one. Full table: `learn/03-topology-engine-and-validation.md`, section 3.

Two read-only `arcpy.Describe(un)` properties exist that bear on volume: `createDirtyAreaForAnyAttributeUpdate` (Boolean: dirty areas after any attribute update when topology is enabled) and `minimalDirtyAreaSize` (Integer: the smallest allowed dirty area size). The Esri page lists type and meaning but **no default and no version**, so read them from your own network rather than assuming [Esri, arcpy utility network properties].

**Example (electric).** A crew's data-fix script nudges 40,000 pole points by 0.01 m. That is 80,000 dirty areas even though nothing meaningful changed. **Practitioner guidance:** make bulk edits with the smallest geometry change that achieves the goal, and avoid "touch" scripts (re-writing identical geometry or network-attribute values) on production.

### 4.2 Extent and batching [Esri]

- Validate by extent clips dirty areas to the extent; outside parts stay dirty (Esri: a dirty area associated with an error is fully evaluated when partially inside the extent). Validating the entire extent "can be resource-intensive" [Esri, About network topology].
- Pro's Validate command is synchronous with the client time-out in section 10; the geoprocessing tool is asynchronous through `UtilityNetworkTools` [Esri, Validate tool page].
- On the DEFAULT version only **one session at a time** can validate (or rebuild). Editing and tracing continue during the run [Esri, Validate and Rebuild tool pages].
- In REST, `validateNetworkTopology` accepts `validateArea` (envelope), `validationSet` (sourceId plus globalIds), `validationType` (`normal`, `rebuild`, `forceRebuild`), `async` and (11.1+) `outSR` (`rest-api/02-topology-and-subnetwork-management-operations.md`). The completed response reports `dirtyAreaCount`, `validateErrorsCreated`, `discoveredSubnetworks`, so you can measure each run.
- The tool lists the subnetworks it marked dirty. In hierarchical networks, if every subnetwork in a tier is already dirty, that tier is not traced and its subnetworks are not returned [Esri, Validate tool page].
- Rebuild ignores dirty areas and reprocesses every feature in the extent; use it when validate or a trace fails to complete, not routinely [Esri, Rebuild tool page].

**Practitioner guidance (batching).**

| Pattern | Why |
|---|---|
| Validate small, often (per work area, per edit session, or on a short schedule) | Each run touches a small footprint and a small number of subnetworks |
| One full-DEFAULT validate on a schedule (for example overnight, see section 11) | Catches footprints that editors did not validate; Esri's command-line blog stacks it with subnetwork updates |
| Do not run a whole-network validate right after a bulk load without first reducing errors | Time scales with errors written, per the migration reports in section 3 |
| Use `returnEdits` only on small synchronous calls | The REST page says it is ignored when `async=true` |
| Never run two validates against DEFAULT and expect parallel speed-up | Only one session runs at a time |

### 4.3 Validate also traces: tier definition matters [Esri Support]

Support bug BUG-000149769 (found in Pro 2.9.2, status "Will Not Be Addressed") states that validation runs subnetwork traces, that slow validation was caused by large subnetworks, and that most time went to querying adjacent junctions and edges and testing each element as a condition barrier. The listed workarounds were to change the subnetwork definition to stop at closed device status (validation then took a couple of seconds) and, as an alternative until the data is clean, to set Manage IsDirty to false on all tiers. Both are definition changes, so topology must be disabled to apply them. The page was last modified 2024-06-05; verify the behaviour on Pro 3.7 with the diagnostics in section 12.

Manage IsDirty off has a cost: with it off, a subnetwork always shows Dirty and Export Subnetwork (which needs Clean) is unavailable; Esri's Foundations ship with it off in some models for performance (`learn/06-tiers-and-subnetworks-in-depth.md`, section 7).

## 5. Update Subnetwork: what drives its cost

**Definition.** Update Subnetwork traces each subnetwork from its controllers and writes results back. Esri's processing order: validate controllers, trace, check for invalid features, write subnetwork name, Is connected and propagated values, create or update SubnetLine, update Subnetworks rows, create or update system diagrams [Esri, Update subnetworks].

### 5.1 Cost drivers

| Driver | Mechanism | Source |
|---|---|---|
| Subnetwork size (elements traversed) | One trace per subnetwork; larger zone, larger trace | Diagnostics blog: element count predicts trace time better than result size |
| Tier definition and barriers | Condition barriers and valid-feature lists decide how far a trace goes | Bug 000149769 (section 4.3) |
| Edit mode | *Without eventing* (default) skips editor tracking, attribute rules, related-object updates and history; *With eventing* can slow large subnetworks with many rules or feature-linked annotation, and on DEFAULT holds a **shared lock for the whole operation** that blocks reconcile's exclusive lock | Esri, Update subnetworks |
| First update touches everything | The first update of a subnetwork touches every feature, so it runs longer than later updates | Esri diagnostics blog |
| Structures and containers | Including or updating structures increases time | Esri diagnostics blog |
| Named versus DEFAULT | Named-version Without eventing updates only features edited in that version; DEFAULT updates all features of the subnetwork | Esri, Update subnetworks |
| Hierarchical tiers | A feature can sit in several tiers, so more tier updates touch the same feature | `learn/06-...` |
| SubnetLine aggregated lines | More aggregated line classes mean more geometry to aggregate; see the water and pressure-zone cases below | Esri Community |
| Summaries and propagators | Foundation Water 2.0 removed subnetwork summary fields "to speed Update Subnetwork" | Esri Foundation notes |

### 5.2 Update all versus update one

- **One subnetwork** (Subnetwork Name, or REST `subnetworkName`): predictable, can be run right after editing, good for the edited feeder or zone.
- **All subnetworks in tier** (Pro checkbox, default off; REST `allSubnetworksInTier=true`): runs asynchronously on `UtilityNetworkTools` in the tool, ignores Subnetwork Name, and is the post-load or post-upgrade refresh. Esri warns not to run several All-in-tier processes at the same time, because two processes updating the same subnetwork can fail [Esri, Update Subnetwork tool page].
- **Continue on failure** (default off): the run stops at the first failure unless on. With REST `continueOnFailure=true` the response lists `failures` (`subnetworkName`, `message`) (`rest-api/02-...`).
- **Parallelism.** Esri documents no supported parallel-update pattern beyond the warning above. **Practitioner guidance:** parallelise only across *different* tiers or domain networks that share no features, only after testing, and never across the same subnetwork; prefer one scheduler job that loops in rank order (`learn/06-...`, section 10 gives the rank-order recommendation). The Esri command-line blog's tool updates "all tiers and domain networks in a service" in one execution.
- **Dirty subnetworks only.** Validate marks affected subnetworks dirty; the update step "then processes only those" in Esri's command-line tool, because a clean subnetwork cannot be updated (Update Subnetwork is a no-op on clean). The Support KB script (section 11) catches the `arcpy.ExecuteError` raised when a subnetwork is already clean.

### 5.3 Known product issues (Esri Support bug pages; all version-specific)

| Bug | Symptom | Status as read |
|---|---|---|
| BUG-000179774 | Subnetwork trace for Update Subnetwork queried the Subnetworks table once per controller device, slow | Fixed in Pro 3.7 (record modified 2025-12-05) |
| BUG-000155780 | Update Subnetworks "very slow in the step to remove subnetwork names" (found on Server 10.9.1); the proposed fixes were using the full-text index, skipping the removal on a post-migration first run, and assuming single-valued names rather than a "::"-separated list | In Product Plan (2025-01-08); no workaround listed |
| BUG-000152087 | Update Subnetwork tool slow updating features on the client side in Pro 2.9.1; workaround: run it without the GUI via Python or REST | Fixed in 3.0 |
| Esri Community, Pro 3.3.x | A branch-versioned post took over 10 minutes after subnetwork updates; resolved by moving from Pro 3.3.2 to 3.3.4 with two related branch-versioning bugs identified (000174057, 000173394) | User-reported; patch level was the cause |

**Practitioner guidance:** if Update Subnetwork is slow, check patch level and the release notes before redesigning tiers; two of these bugs were product defects, not data problems.

### 5.4 The pressure-zone / draw-performance case (Esri Community)

A water utility saw map draw times jump from under 2 s to over 30 s when the pressure subnetwork layer was on. The accepted answer said the subnetwork line included services and laterals, which "greatly increases the complexity and draw time", and that limiting aggregated lines to mains helps; a follow-up advised adding an attribute index on frequently queried fields such as the tier-name field. The poster dropped topology, removed laterals from the subnetwork line, re-enabled and saw better drawing. This matches the Foundation change in Water 2.0, which removed service laterals from aggregated lines on all tiers. SubnetLine geometry is a *display and summary* object, so keep it light.

## 6. Trace performance

### 6.1 What the engine does [Esri]

Traces read the cached topology, which makes complex traces on big networks fast; results can be wrong when dirty areas exist, so validate first. The Trace tool's "Validate consistency" fails the trace on reaching a dirty area; the Pro tool text says traces do not check by default, while the REST `traceConfiguration` page lists `validateConsistency` default **true**. Read both as documented, and set the flag explicitly in code.

The Esri Community diagnostics post (Jan 2026, Enterprise 12.1 logs) says traversed element count predicts trace time better than result size; traces with barriers, upstream/downstream searches or update-subnetwork propagation are costlier; network attributes stored in-line avoid extra reads while out-of-line reads add cost that grows with network size; and a hot cache is faster than a cold one (compare tests cold-to-cold).

### 6.2 Levers (what you can set)

| Lever | Pro tool / pane | REST `traceConfiguration` / `resultTypes` | Effect and source |
|---|---|---|---|
| Domain network and tier | Domain Network, Tier, Target Tier | `domainNetworkName`, `tierName`, `targetTierName` | Narrow the search; Practitioner guidance |
| Include containers / content / structures | Include Containers / Content / Structures (all off by default) | `includeContainers`, `includeContent`, `includeStructures` (all default false) | More elements to return; Esri defaults exclude them |
| Include barrier features | on by default | `includeBarriers` (default true) | Affects result set and aggregated geometry end points |
| Result types | Selection (default), Aggregated Geometry, Connectivity, Elements, Features, Associations, Related records, Circuits | `resultTypes`: `elements`, `aggregatedGeometry`, `connectivity`, `features`, `associations`, `paths`, `relatedRecords`; each can carry `includeGeometry`, `includePropagatedValues`, `includeDomainDescriptions`, `networkAttributeNames`, `resultTypeFields` | Cost rises with more types, fields, geometry; Esri diagnostics blog says export cost rises with these |
| Geometry | Include geometry off by default (Enterprise 11.1+ for JSON types) | `includeGeometry` per result type | Practitioner guidance: ask for geometry only for what you will draw |
| Synthesize geometries | off by default; Aggregated Geometry (Enterprise 11.3+) and Circuits (12.1+) | `synthesizeGeometries` (11.3+, aggregatedGeometry only) | Infers geometry for edge objects and associations; extra work, off by default |
| Validate locatability | off by default | `validateLocatability` (default false) | Extra check of containment/attachment/connectivity for traversed features |
| Path traces | Max Hops (default 100) and Num Paths (default 1); both need Enterprise 12.1+ | `maxHops` (default 100; terminals count as two hops), `numPaths` (REST page default 1) | Cap path search; Esri REST and Pro pages agree on defaults (checked 2026-10-16) |
| Filter by nearest | count within a cost measure | `nearestNeighbor` in the configuration schema (`rest-api/08-...`) | Limits results to a count |
| Async | Trace tool async for enterprise (synchronous is default) | `async=true` (10.9.1+); capability flag `supportsAsyncTrace` | Avoids time-out, not cost |
| Named configurations | Trace pane Named Configurations tab | `traceConfigurationGlobalId` (10.9+) | Pro 3.2 runs Named Configurations without the GP framework, which can speed them up [Esri blog, 2024 release] |

Pbf as a REST response format (`f=pbf`, added at 11.2) exists on the Trace operation; whether it reduces transfer cost for your payload is not stated, so measure.

### 6.3 Practitioner guidance (tune by measuring)

1. Constrain by tier and use a function barrier (length or count) while testing so a mis-configured trace cannot run away.
2. Leave containers, content and structures off unless the answer needs them. In telecom, containers are needed to see nonspatial circuit parts, so scope those traces tightly.
3. Ask only for what the client uses. A map highlight needs `aggregatedGeometry` or `elements`, not full `features` with all fields.
4. Rule out dirty areas, errors and Manage IsDirty off before blaming the engine.
5. Telecom path result size is starts x stops x `numPaths`; use circuit queries and counts before tracing every circuit.
6. If cold-run traces are slow but hot ones are fast, look at database I/O and the cache warm-up, not the trace definition.

## 7. Trace result size and the service heap

**Definition.** A trace's JSON result is built in the service's memory. Esri Support KB 000025326 explains that if a trace traverses many features, the result payload can exceed the service heap size (default **64 MB**) and fail with "A networking error occurred" (errors 160213 or 003642).

**Estimation formula in the KB:** about 750 bytes for an empty result, plus about 150 bytes per junction element and 175 bytes per edge element.

| Heap setting | Rough capacity stated by Esri |
|---|---|
| 64 MB (default) | about 200,000 edge and 200,000 junction elements |
| 128 MB | about 400,000 of each |
| 256 MB | about 800,000 of each |

Counting rules from the same KB: a single edge with nine midspan junctions yields ten edge elements; each terminal on a terminal device counts as a junction element. Increase the heap in the utility network service's advanced properties.

**Example (water).** A "downstream from a transmission main" trace on a hierarchical water tier with Include Structures on counts many devices with several terminals each, so element counts are far larger than the feature count.

Verification notes: the KB text I read does not state a revision date or release floor, so confirm the heap property name and defaults for Enterprise 12.1 on your server. The REST `elements` result type is the cheapest way to size a result before asking for `features`.

## 8. Export Subnetwork, diagrams and other bulk outputs

- **Export Subnetwork** writes a JSON file; subnetworks must be Clean first; in enterprise the input must come from a utility network service and it runs asynchronously via `UtilityNetworkTools`. Result types: Connectivity, Features, Containment and attachment associations, Related records (Enterprise 11.5+); Include geometry, Include domain descriptions, Include flow directions (12.1+) and Include propagated values (12.1+) are off by default [Esri tool page]. Esri's diagnostics blog says cost rises with more result types, more fields, more source-table queries and geometry, and that exporting network attributes avoids querying source tables.
- The Pro client has a 10-minute built-in time-out for this tool that the server setting cannot change; Support bug 000131328 ("As Designed", found in Pro 2.5.1) recommends sending the request directly to the REST endpoint, which honours the longer settings. Prefer `exportSubnetwork` with `async=true` (10.9.1+).
- **Export with acknowledgment** records the last-exported time and only works on DEFAULT (`pro-help/06-...`).
- **Network diagrams.** A Pro 3.3 bug records that building a diagram from a *service* with more than 49,999 features fails with error 160243, and Esri closed it "As Designed" for performance reasons. Verify the threshold in your release before designing diagram workflows on very large selections.
- **Associations and synthesis.** The `synthesizeAssociationGeometries` operation exists but its REST page could not be read in this review; treat cost guidance for it as "Verify against the Esri docs for your version".

## 9. Database tuning and maintenance

### 9.1 What Esri documents

| Topic | Statement | Source |
|---|---|---|
| Versioning model | Enterprise UN data must be **branch versioned** | Esri FAQ, publishing topic |
| Compress | Applies to traditional versions and to datasets registered with "move edits to base"; **branch-versioned datasets do not need compress** because edits are tracked in the business table | Esri, geodatabase administration tools page |
| Prune | Use **Prune Branch History** to manage growth of branch-versioned tables (removes retired archived records from DEFAULT while keeping data in use) | same |
| Analyze Datasets | Updates statistics on base, delta and archive tables and their indexes; run it after a compress and after importing, loading or copying data into an enterprise geodatabase; the data owner can run it | same |
| Rebuild Indexes | Rebuilds attribute and spatial indexes; for versioned tables default is delta tables only; rebuilding a feature dataset also rebuilds its feature classes and topology tables; only the geodatabase administrator can do system tables | same |
| Traditional workflow | Reconcile/post, compress, rebuild indexes, analyze datasets; "always update statistics after a compress"; can run nightly as a scheduled Python script or ModelBuilder model; this applies only to traditional versioning | Esri, Recommended version administration workflow |
| UN-specific index | Dataset v4 adds a nonunique attribute index on `SUBNETWORKNAME` and `SUBNETWORKCONTROLLERNAME` in the Subnetworks table; v6 makes `ASSOCIATIONTYPE` a subtype field, which improves performance when displaying diagrams and editing associations | Esri, Utility network upgrade history |
| Network topology | Stored as a graph in binary pages, cached on access; no "network index" tuning knobs are described on the topology page | Esri, About network topology |

### 9.2 What Esri does not say (in the pages I read)

I found no Esri UN page that gives DBMS-specific tuning for **SQL Server, Oracle, PostgreSQL or SAP HANA** (memory settings, vacuum/auto-analyze settings, fill factor, partitioning, statistics sampling). The supported platforms are SQL Server, Oracle, PostgreSQL and SAP HANA at releases supported by your Enterprise version (`pro-help/03-creation-configuration-attributes-categories-rules.md`). The Esri Diagnostic Monitor article says deeper database analysis needs the RDBMS's own tools or SDE Intercept. There is also no Esri statement I read about a separate "spatial index" or "network index" rebuild schedule for UN topology pages. Do not invent one.

### 9.3 Practitioner guidance (database)

| Idea | Rationale and caution |
|---|---|
| Update statistics after any large load, migration, or upgrade (use **Analyze Datasets**) | Esri says to run it after loading data into an enterprise geodatabase; the optimizer plans queries from stale statistics otherwise |
| Rebuild spatial and attribute indexes after bulk loads or very heavy editing (use **Rebuild Indexes**) | The tool exists for this; apply during a quiet window; confirm in your release whether delta-only default makes sense for branch-versioned tables, since Esri's page words the default in terms of versioned tables |
| Keep DBA-native maintenance (SQL Server index/statistics jobs, Oracle stats gathering, PostgreSQL auto-analyze) but do not make UN system tables a special case without Esri guidance | Only the geodatabase administrator can rebuild system-table indexes per Esri |
| Index frequently filtered attribute fields (for example a tier subnetwork-name field) | A reply on Esri Community (accepted answer in the draw-performance thread) advised this for query performance |
| Fast local storage for the DB and any local mobile/file geodatabase used for analysis | Esri's diagnostics post notes the build spills to disk when memory is exceeded; the community sewer thread favoured a mobile geodatabase on a local drive over a shared file geodatabase |
| Prune branch history on a schedule agreed with audit/retention rules | Pruning removes history; check retention requirements first |

## 10. Service configuration: instances, time-outs, async

**Esri documented.**

- The system service `UtilityNetworkTools` (in the System folder of services that include a utility network) is preconfigured, runs UN geoprocessing tasks asynchronously, and has a longer time-out than the client defaults [Esri, tool pages and FAQ]. The FAQ states Pro client time-outs (section 2); asynchronous tools "do not use a client setting" and the limit comes from the service. No numeric service time-out is stated there.
- REST operations with `async` are listed in `rest-api/06-asynchronous-operations-job-status.md`: `trace`, `enableTopology`, `disableTopology`, `exportSubnetwork`, `updateIsConnected`, `Locations query`, `validateNetworkTopology`, `updateSubnetwork`. Poll `statusUrl` (statuses `Pending`, `InProgress`, then a completed body). Do not confuse with the GPServer `esriJob*` vocabulary.
- Publishing requirements (branch versioned, Map Image layer with Feature option, Version Management on, owners, layer IDs preserved) are in `pro-help/10-publishing-ownership-licensing.md`. The publishing topic I read contains **no** instance-count, heap, pooling or time-out guidance.
- Server logging: set to Verbose or Debug without restarting services; verbose adds significant volume, so use it in test or staging; default logs Warnings and above [Esri diagnostics blog].

**Not documented in the pages I read:** recommended min/max instances for the UN feature service or for `UtilityNetworkTools`, dedicated versus shared instance pools, or ArcGIS Server machine sizing for a given network size. The Esri Community discussion on min/max instances for publishing tools could not be opened in this review. For architecture, Esri's blog points to the ArcGIS Architecture Center and ArcGIS Monitor, and an Esri-led architecture assessment is the supported route.

**Practitioner guidance.**

1. Use `async=true` for anything that can exceed a few minutes and poll with back-off; never lengthen a synchronous client wait as the main fix.
2. Keep interactive trace traffic off the instances that run long jobs where your architecture allows (separate scheduled work from user-facing services); test your own isolation, because Esri documents no such pattern.
3. Match test and production (software versions, server types, resources, network layout) so timing results carry over [SSP Innovations].
4. After raising any server property (heap, time-out), re-test with the cold-cache procedure in section 12.

## 11. Maintenance routines and scripting patterns

### 11.1 What a healthy routine looks like

```
 hourly/daily    VALIDATE (DEFAULT, full extent or per area, async)
       |
       v
 hourly/daily    UPDATE SUBNETWORKS (dirty only; by tier in rank order)  --> UPDATE IS CONNECTED (optional)
       |
       v
 daily/weekly    EXPORT SUBNETWORKS for downstream systems (acknowledged export on DEFAULT)
       |
       v
 weekly/monthly  Analyze Datasets / Rebuild Indexes ; Prune Branch History ; log + error review
```

The sequence and "run it often, stack validate with update subnetworks and update IsConnected in one execution, schedule at business-need intervals such as hourly or daily" come from Esri's command-line automation blog. The cadence for the later steps is **Practitioner guidance**.

### 11.2 Esri-documented scripting building blocks

| Block | Detail | Source |
|---|---|---|
| `uncmd` command-line tool | A C# console tool (open-source on GitHub, per the blog) calling the UN REST API: validate (full extent on DEFAULT by default, or a JSON extent), update subnetworks (all tiers and domain networks in a service), update IsConnected; targets one named service or "all" services with "UN" in the name; user must own the service; logs to a folder beside the executable. The blog gives no Python, async, retry or credential-handling guidance | Esri blog, Automating utility network functions |
| Support KB loop script | An `arcpy` loop that toggles a feature's `lifecyclestatus`, runs `ValidateNetworkTopology` with the "DISPLAY" extent option and `UpdateSubnetwork` with the "STOP_ON_FAILURE" option inside try/except, catching `arcpy.ExecuteError` when the subnetwork is already clean; sample uses `range(5)` and the comment "start small"; no timings or recommended counts | Esri Support KB 000038698 |
| `arcpy.un` tools | `ValidateNetworkTopology`, `UpdateSubnetwork`, `ExportSubnetwork`, `RebuildNetworkTopology`, `UpdateIsConnected` follow the tool-name pattern in `arcpy/01-utility-network-module.md`; signatures from the Pro 3.5 tool pages: `arcpy.un.ValidateNetworkTopology(in_utility_network, {extent})` (extent: `MAXOF`, `MINOF`, `DISPLAY`, a layer, an Extent object or "xmin ymin xmax ymax"); `arcpy.un.UpdateSubnetwork(in_utility_network, domain_network, tier, {all_subnetworks_in_tier}, {subnetwork_name}, {continue_on_failure}, {condition_barriers}, {function_barriers}, {include_barriers}, {traversability_scope}, {propagators})` with `ALL_SUBNETWORKS_IN_TIER` (default) or `SPECIFIC_SUBNETWORK`, and `CONTINUE_ON_FAILURE` or `STOP_ON_FAILURE` (default); verify the other tools against the Esri docs for your version | Esri tool pages |
| REST | `validateNetworkTopology`, `updateSubnetwork`, `exportSubnetwork`, `updateIsConnected` with `async=true` | `rest-api/02-...`, `rest-api/06-...` |
| Licensing | Standard or Advanced Pro; for enterprise the portal account needs the ArcGIS Advanced Editing user type extension; the Update Subnetwork and Validate tools need a utility network *service* as input in enterprise | Esri tool pages |

### 11.3 Illustrative REST-based scheduler (pattern, not Esri code)

Names of REST parameters are from `rest-api/02-...`; the token handling, polling interval and tier list are placeholders.

```python
# Illustrative only. Test against a non-production service first.
import time, requests

UNS = "https://host/server/rest/services/Electric/UtilityNetworkServer"   # placeholder
TOKEN = "<token>"                       # obtain per your org's policy
TIERS = [("Electric", "Medium Voltage Radial")]   # (domain network, tier) in rank order

def post(op, **params):
    data = {"f": "json", "token": TOKEN, **params}
    r = requests.post(f"{UNS}/{op}", data=data, timeout=120)
    r.raise_for_status()
    return r.json()

def wait(status_url):
    while True:
        s = requests.get(status_url, params={"f": "json", "token": TOKEN}, timeout=60).json()
        if s.get("status") not in ("Pending", "InProgress"):
            return s
        time.sleep(15)

# 1) validate DEFAULT asynchronously (no sessionId on DEFAULT)
done = wait(post("validateNetworkTopology", gdbVersion="sde.DEFAULT",
                 validationType="normal", **{"async": "true"})["statusUrl"])
print(done.get("dirtyAreaCount"), done.get("validateErrorsCreated"))

# 2) update every subnetwork in each tier, rank order, keep going on failure
for dn, tier in TIERS:
    res = wait(post("updateSubnetwork", domainNetworkName=dn, tierName=tier,
                    allSubnetworksInTier="true", continueOnFailure="true",
                    **{"async": "true"})["statusUrl"])
    print(dn, tier, res.get("success"), res.get("failures"))
```

Notes: `async` is a Python keyword, so the form field is passed through a dict. Log `dirtyAreaCount`, `validateErrorsCreated` and each `failures` list for trend lines. Handle failed jobs by checking `success` and `error`, because the exact failure status string is not documented (`rest-api/06-...`). Add token refresh, retries and per-service error handling before production use.

### 11.4 Notebook Server, Workflow Manager, Python API

- ArcGIS Notebook Server and Workflow Manager: **I found no Esri page describing a utility-network-specific scheduled-task pattern for them.** **Practitioner guidance:** a scheduled notebook or workflow step that calls the REST operations above is architecturally sound, but verify arcpy availability and licensing in the notebook runtime, and prefer REST (no Pro dependency).
- ArcGIS API for Python: I could not confirm UN manager method names in this review; **verify against the API reference for your version** before promising `validate_topology`/`update_subnetwork` wrappers.

### 11.5 Operating rules

- Update a subnetwork with one process at a time (Esri).
- Do not leave topology disabled in production: disabled topology tracks no edits (Esri).
- For named versions, remember that SubnetLine edits are not posted (`learn/06-...`); repeat Update Subnetwork on DEFAULT after the post.
- Log every scheduled run's counts and elapsed time; section 12.

## 12. Monitoring and diagnostics

**Esri documented tools** (Esri blog, Utility Network Diagnostics):

| Tool | What it shows |
|---|---|
| Diagnostic Monitor (Pro; Help tab, Performance group; Ctrl+Alt+M) | HTTP tab (Pro to Enterprise messages) and Log tab (client diagnostics; detailed UN logs with debug logging in single-user) |
| ArcGIS Server logs | Per-service logs; asynchronous GP work under System/UtilityNetworkTools.GPServer |
| Log extraction (Utility Data Management Support toolbox, ArcGIS Solutions) | Extract Logs from Files / from REST into a local SQLite database |
| Build log | Registry DWORD under the UtilityNetwork key (0 none, 1 simple, 2 verbose); needs a pre-created folder |
| ArcGIS Monitor | Architecture-level monitoring |
| Operation logs | `TraceLog`, `UpdateSubnetworkLog` (trace time versus GIS update time), `ExportSubnetworkLog` (trace versus write), `BuildLog` for enable/disable/validate (step duration, features processed, cumulative time, memory) |

**What to record on every scheduled run (the monitoring set):**

| Metric | Where it comes from |
|---|---|
| Elapsed time per operation | job `submissionTime`/`lastUpdatedTime` (async), your own timer |
| Dirty-area count before and after | `dirtyAreaCount` in validate response; or count rows in the Dirty Areas layer |
| Errors created | `validateErrorsCreated` |
| Subnetworks discovered dirty | `discoveredSubnetworks` |
| Update failures | `failures` from `updateSubnetwork` with `continueOnFailure=true` |
| Subnetwork state counts | Subnetworks table: dirty, invalid, null `LASTUPDATESUBNETWORK` (a never-updated subnetwork has an empty Last Update per Esri FAQ) |
| Trace time versus traversed elements | TraceLog |

**Method from the Esri Community diagnostics post (Jan 2026).** Measure per subnetwork and plot time against feature count to find outliers; compare server log time to client-observed time (a big gap points at architecture, not the engine); isolate data/configuration issues by copying the network to a local mobile geodatabase and capturing logs; use cold-cache runs for comparisons; test updates with a realistic number of edits, not the first run or a no-change run. The post stresses logs do not replace monitoring across the whole architecture under load.

## 13. Capacity-planning questions by industry

Esri publishes no per-industry numeric capacity thresholds. The questions below tell you *what to measure and ask*; the example shapes are drawn from the Foundations described in Esri Foundation documentation. Everything numeric here is a prompt to measure, not a limit.

### 13.1 Electric

1. How many feeders (controllers) and what is the **largest feeder's element count** (devices, line segments, terminals counted as junction elements)?
2. Is secondary a tier of its own (thousands of tiny subnetworks) or part of the feeder? Esri says secondary subnetworks are usually created only for large complex areas such as mesh networks.
3. How many phases/propagators and summaries per tier? Each propagated value is written back during Update Subnetwork.
4. Are service points and meters modelled as spatial features or associated nonspatial objects? That drives element counts and the heap estimate in section 7.
5. Peak edit rate during storm restoration: how many switching edits per hour need validated, traced and re-updated promptly?
6. Is Update Subnetwork run With eventing because rules must fire? That holds a shared lock on DEFAULT (section 5.1).

### 13.2 Gas and pipeline

1. How large is the largest **pressure** subnetwork and is it hierarchical under a System tier (a pipe is in several tiers; more tier updates per pipe)?
2. Isolation: how many isolation subnetworks and are valves modelled so the isolation trace has natural boundaries?
3. Is Manage IsDirty off (Foundation default) and, if so, how do you produce Clean-only exports?
4. Do pipeline records carry linear-referencing fields (Route ID, Measure) that add attribute volume?
5. Cathodic protection as a separate tier group: how many CP zones and are services/laterals excluded from aggregated lines for map speed?

### 13.3 Water, wastewater and stormwater

1. Largest pressure zone or DMA element count; are service laterals excluded from SubnetLine (Water 2.0 does this)?
2. Hierarchical stack (System, Pressure, Isolation, DMA): how many subnetworks per tier and who is the controller (pump, PRV, tank)?
3. Sewer sink networks (collection system, sewershed): the largest collection system's element count and the longest expected upstream trace from a deep manhole.
4. Stormwater: catchment/subcatchment layout and the effect of the hierarchical change in Stormwater 2.0 on trace length.
5. How many valve-isolation traces run concurrently during a main break, and is the isolation tier used instead of ad hoc traces?

### 13.4 Telecom

1. Fiber **unit counts**: how many strands/ports exist as individual rows versus grouped rows? Esri's own example: a 96-strand cable is 193 records ungrouped and 3 grouped.
2. Number of circuits and the largest outage footprint (circuit queries return counts; traces return paths).
3. Path traces: starts x stops x `numPaths` (and `maxHops`) set the worst-case result size.
4. Which operations need nonspatial objects in the topology (locatable versus unlocatable)? Edits to locatable ones create dirty areas on the first spatial feature in their containment hierarchy.
5. Dataset version: telecom domain network requires UN v8 (Pro 3.7 / Enterprise 12.1), and Field Maps does not support v8 (`pro-help/09-...`).

## 14. Upgrade planning (dataset versions)

Compatibility matrix and procedure are in `pro-help/09-dataset-versions-compatibility-upgrade.md`; do not duplicate. What bears on performance and operations:

| Version | Performance / scale relevance | Source |
|---|---|---|
| v4 | Nonunique index on `SUBNETWORKNAME` and `SUBNETWORKCONTROLLERNAME` in the Subnetworks table; named-version dirty areas truncated and must be regenerated (enable topology, reconcile named versions) | Esri upgrade history |
| v6 | `ASSOCIATIONTYPE` becomes a subtype field, improving diagram display and association editing | same |
| v7 | 64-bit ObjectIDs (more than 2.14 billion features possible); big integer fields; **indexes on all UN tables are dropped and re-created, so the upgrade can take noticeably longer**; Esri's page does not say whether it is reversible (treat as irreversible and back up); requires enterprise geodatabase 11.2.0+ | Esri upgrade history; 2024 release blog |
| v8 | System-maintained `PARTITIONID` added to domain and structure network classes "to support future tracing and network management improvements"; no direct performance effect described today; only needed for propagation resetters or telecom domain networks | Esri upgrade history |

Upgrade Dataset: backup first; the tool's Utility Network Version parameter defaults to "Compatible" (the newest version your Pro/Enterprise supports), and you can pick a specific version from 5 to 8 [Esri tool page]. In enterprise the version follows the Enterprise release, and the tool checks federated servers in multimachine deployments. The tool page I read does not mention duration, irreversibility or the exclusive lock for UN; the procedure in `pro-help/09-...` (exclusive lock, topology disabled, owners) comes from the Pro help topic. Plan a rehearsal on a copy and measure index rebuild time for v7, then run Analyze Datasets afterwards (Practitioner guidance).

After upgrade: enable topology again, republish services, check service settings (v5 note), test field apps, and run a full validate plus update-all-in-tier on the rehearsal to capture baseline timings for the new version. A scheduled-job regression after an upgrade usually means a changed parameter set or service setting, not a data problem.

## 15. Triage flow: "it is slow", what do I check first

1. **Which operation?** Validate, Update Subnetwork, trace, export, draw, post/reconcile, enable/disable?
2. **Server time or user time?** Compare server log duration to what the user saw (section 12). Big gap: network, Pro client time-out (10 min / 30 min), layer refresh, GP history. Small gap: engine or database.
3. **Is the data clean?** Dirty-area count, error count, Manage IsDirty, subnetworks never updated.
4. **Is the scope bounded?** Extent for validate; tier and barriers for trace; one subnetwork versus all.
5. **Is it a known bug?** Check patch level against section 5.3 and Esri Support bug pages.
6. **What does the log say?** TraceLog / UpdateSubnetworkLog split time between trace and GIS update, and between trace and write.
7. **Database health?** Statistics after the last load, index health, I/O, version housekeeping (Prune Branch History).
8. **Result size?** Heap sizing for large JSON traces (section 7).
9. **Cold versus hot cache?** Re-test cold.

## Common misconceptions

- "Esri publishes a maximum number of features or a maximum subnetwork size." Not in the pages read; section 2.
- "Compress my branch-versioned UN data nightly." Branch versioning does not need compress; Esri points to Prune Branch History (section 9.1).
- "Validate the whole network every few minutes keeps things fast." Entire-extent validate is resource-intensive and only one session runs at a time on DEFAULT; keep it small and scheduled.
- "Update Subnetwork can be run in parallel on the same tier." Esri warns two All-in-tier processes can collide; no parallel pattern is documented.
- "If a trace times out, increase the client time-out." Pro's tool time-outs are fixed (10 / 30 minutes); use async or REST.
- "A bigger heap fixes all trace failures." It fixes result-payload failures (160213 / 003642) only; the traced element count drives cost.
- "Manage IsDirty off is a free speed-up." It makes subnetworks always dirty and blocks Clean-only Export Subnetwork.
- "The SubnetLine should include everything for completeness." Esri Community advice and the Water 2.0 Foundation both exclude laterals for draw and update speed.
- "One slow test proves the design is bad." Cold versus hot cache and the first update's all-features pass distort single measurements.

## Quick checks

1. Which Pro, Enterprise and UN dataset version, and which DBMS and release?
2. Enterprise service or single-user (file/mobile) geodatabase? (Mobile on local disk often outperforms a shared file geodatabase in reports.)
3. Is the slow step synchronous in Pro (10 / 30 minute limit) or a service/async job?
4. How many dirty areas and errors are outstanding, and did a recent bulk edit create them?
5. Is topology ever left disabled during edits?
6. Which edit mode (With or Without eventing) is each tier using, and who holds a shared lock on DEFAULT?
7. What is the largest subnetwork's element count and which tier is it?
8. What does `arcpy.Describe(un)` return for `createDirtyAreaForAnyAttributeUpdate` and `minimalDirtyAreaSize`?
9. When did Analyze Datasets and Rebuild Indexes last run, and after which load or upgrade?
10. What is the service heap for the UN feature service, and what do result sizes look like (use `elements` first)?
11. Is anything scheduled, with logging of elapsed time, dirty-area counts, failures?
12. Has the patch level been checked against the known bug list (section 5.3)?

## Related files

- `learn/03-topology-engine-and-validation.md` (dirty areas, validate mechanics)
- `learn/06-tiers-and-subnetworks-in-depth.md` (tier design, update subnetwork options)
- `learn/07-tracing-in-depth-and-configuration-library.md` (trace configuration, section 17)
- `learn/05-attributes-categories-and-attribute-rules.md` (rules cost, eventing)
- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`
- `pro-help/06-administration-subnetworks-topology-versioning.md`, `pro-help/09-dataset-versions-compatibility-upgrade.md`, `pro-help/10-publishing-ownership-licensing.md`
- `rest-api/02-topology-and-subnetwork-management-operations.md`, `rest-api/06-asynchronous-operations-job-status.md`, `rest-api/08-trace-configuration-full-schema.md`
- `arcpy/01-utility-network-module.md`

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/update-subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/create-and-configure-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-upgrade-history.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/validate-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/rebuild-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/export-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/trace.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/upgrade-dataset.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/recommended-version-administration-workflow.html
- https://pro.arcgis.com/en/pro-app/3.6/help/data/geodatabases/overview/performing-geodatabase-adminstration-tasks-using-geoprocessing.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/utility-network-properties.htm
- https://geo.dot.gov/server/help/en/rest/services-reference/enterprise/trace-utility-network-server (copy of the Esri Enterprise REST Trace page)
- https://support.esri.com/en-us/knowledge-base/determine-the-proper-heap-size-setting-for-trace-result-000025326
- https://support.esri.com/en-us/knowledge-base/how-to-iterate-network-topology-validation-and-subnetwo-000038698
- https://support.esri.com/en-us/bug/slow-performance-when-validating-a-utility-network-topo-bug-000149769
- https://support.esri.com/en-us/bug/the-update-subnetwork-tool-is-taking-too-long-to-update-bug-000152087
- https://support.esri.com/en-us/bug/the-update-subnetworks-tool-is-very-slow-in-the-step-to-bug-000155780
- https://support.esri.com/en-us/bug/the-export-subnetwork-tool-fails-to-honor-the-timeout-s-bug-000131328
- https://support.esri.com/en-us/bug/a-subnetwork-trace-operation-for-update-subnetwork-is-i-bug-000179774
- https://support.esri.com/en-us/bug/creating-a-utility-network-diagram-with-more-than-49999-bug-000168157
- https://www.esri.com/arcgis-blog/products/utility-network/data-management/utility-network-diagnostics
- https://www.esri.com/arcgis-blog/products/utility-network/administration/automating-utility-network-functions-using-command-line
- https://www.esri.com/arcgis-blog/products/utility-network/announcements/whats-new-utility-network-mgmt-release-2024
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/managing-electric-networks-updating-subnetworks
- https://community.esri.com/t5/arcgis-utility-network-blog/parsing-utility-network-diagnostic-logs/ba-p/1675565
- https://community.esri.com/t5/arcgis-utility-network-questions/un-enable-topology-performance/m-p/678334
- https://community.esri.com/t5/arcgis-utility-network-questions/network-topology-performance/m-p/1683978
- https://community.esri.com/t5/arcgis-utility-network-questions/drawing-performance-pressure-subnetwork/td-p/1406291
- https://community.esri.com/t5/arcgis-utility-network-questions/increased-version-post-time-when-updating-subnets/m-p/1639174
- https://sspinnovations.com/blog/lessons-learned-going-live-in-the-utility-network/
