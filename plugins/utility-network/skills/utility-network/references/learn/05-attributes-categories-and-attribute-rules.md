# Utility Network: Attributes, Categories and Attribute Rules (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)
> Sources: Esri ArcGIS Pro 3.7 help and tool reference, Esri Solutions Foundation attribute-rule inventories, Esri blogs and Community threads (full list at the end). Practitioner statements are labelled as such.

Three different things in a utility network (UN) are called "attributes", and mixing them up is the most common source of confusing answers: ordinary geodatabase **fields**, UN **network attributes** (which the topology engine reads while tracing) and geodatabase **attribute rules** (Arcade scripts that run when data is edited). Read this file when you design what a trace can see, tag asset types with **network categories**, decide what a Foundation's shipped rules do for you, or diagnose why a rule fires (or does not) next to topology validation, subnetwork update and versioning. Tool-by-tool signatures for configuration are in `pro-help/03-*.md`; this file explains the mechanisms behind them.

## Contents
1. Three kinds of "attribute"
2. Network attributes: what they are and how the engine uses them
3. Data types and options
4. In Line storage and the bit budget
5. Apportionable, nullable, substitution, overridable
6. Assigning a network attribute to a field
7. Typical fields every UN class carries
8. Network categories
9. Attribute rules: fundamentals
10. Rule anatomy: types, triggers, batch, Arcade keywords
11. How rules interact with topology, dirty areas and subnetworks
12. Rules and branch versioning
13. Rules the Foundations ship
14. Common utility patterns (Esri-documented versus practitioner)
15. Performance cautions
16. Illustrative Arcade examples
17. Common misconceptions, quick checks, related files, sources

## 1. Three kinds of "attribute"

| Thing | Lives in | Who reads it | Changed by | Example |
|---|---|---|---|---|
| **Field** | feature class / table | everything (editors, maps, SQL) | any edit | `ASSETID`, `LIFECYCLESTATUS`, `PHASESNORMAL` |
| **Network attribute** | the UN dataset definition (a name + type + options), pointed at one field per class | the topology engine during trace, Update Subnetwork, propagation | Add Network Attribute, Set Network Attribute (topology disabled) | "Phases normal", "Lifecycle status", "Shape length" |
| **Attribute rule** | a rule stored on one feature class/table | the geodatabase, on edit or on a batch evaluation | Add Attribute Rule and related tools | "GenerateIDs", "Validate Voltage" |

A field becomes visible to tracing only after it is mapped to a network attribute. A network attribute is not a rule: it constrains nothing at edit time. A rule is not a network rule either: **network rules** (Add Rule) say which asset types may connect, contain or attach (see `pro-help/03-*.md`), whereas attribute rules compute or check values.

## 2. Network attributes: what they are and how the engine uses them

**Definition.** A network attribute models a characteristic that has more than one possible state, for example phase on an electric network or pressure on gas and water. Esri's tool help says network attributes are used by tracing analysis to control **traversability** and to model **path cost**.

**Mechanism.** At topology build time the engine reads the mapped field of each feature and either stores the value packed into the topology ("In Line", fast) or fetches it from the table when needed. A trace can then:

1. compare a network attribute with a value in a condition barrier or filter (for example `Lifecycle status` not equal to `In design`);
2. sum, count, min or max it with a function (for example add `Shape length`, or add `Customer count`);
3. use it as a cost for shortest-path traces;
4. propagate it downstream from a controller (Update Subnetwork, Export Subnetwork or Trace), optionally with substitution.

Industry example (electric): a feeder breaker supplies phases ABC; a lateral carries only phase B. With the network attribute "Phases normal" as a bitset, a propagator can compute the phases actually energised at every downstream feature, and a lateral with no matching bit becomes a barrier.

**Surface mapping.**

| Surface | Where network attributes show up |
|---|---|
| Pro UI | Layer Properties > Network Properties > Network attributes (the Inline (Bit Size) column shows bit usage) |
| GP / arcpy | `arcpy.un.AddNetworkAttribute`, `arcpy.un.SetNetworkAttribute`; `arcpy.Describe(un).networkAttributes` (properties such as `name`, `dataType`, `isEmbedded`, `isApportionable`, `isOverridable`, `isSubstitution`, `domainName`, `networkAttributeToSubstitute`; see `arcpy/01-*.md`) |
| REST | trace `traceConfiguration`: condition `type: "networkAttribute"`, function `networkAttributeName`, `shortestPathNetworkAttributeName`, `filterBitsetNetworkAttributeName` (see `rest-api/08-*.md`) |
| JS | `utilityNetwork.dataElement` holds the definition; function results carry `networkAttributeName` (see `js-api/03-*.md`, `js-api/04-*.md`) |
| Pro SDK | `utilityNetworkDefinition.GetNetworkAttribute(name)`, `NetworkAttributeComparison` (see `pro-sdk/01-*.md`) |

## 3. Data types and options

Esri's network attributes page gives this matrix.

| Type | In Line | Apportionable | Nullable | Substitution | Notes |
|---|---|---|---|---|---|
| Short | yes (domain required) | no | yes | no | integers, small coded states |
| Long | yes (domain required) | no | yes | yes, only when In Line is off | the only type that can use substitution |
| Double | no | yes | yes | no | measured quantities such as length or pressure |
| Date | no | no | yes | no | |
| Big integer | no | no | yes | no | **UN dataset version 7 or later** only |

The Add Network Attribute tool (Pro 3.7 reference) lists these parameters:

| Parameter | Default | Constraint |
|---|---|---|
| Input Utility Network | none | enterprise: connection as the **database utility network owner** |
| Attribute Name | none | |
| Attribute Type | none | Short, Long, Double, Date, Big integer |
| In Line | unchecked | integer types only; the tool page states a limit of 25 in-line attributes per utility network |
| Apportionable | unchecked | Double only, line features show the behaviour |
| Domain Name | none | **required when In Line is checked**; must be a coded value domain |
| Is Overridable | unchecked | **not used in the current release; any value is ignored** |
| Nullable | checked | |
| Substitution | unchecked | Long only |
| Network Attribute to Substitute | none | must be an in-line integer attribute of 8 bits or fewer |

Prerequisites (Esri): network topology **disabled**; enterprise geodatabase tool runs against the **default version**, as the portal utility network owner, with the ArcGIS Advanced Editing user type extension; licence Standard or Advanced (not Basic). The Pro help states that new attributes reach existing named versions through reconcile. The tool page does not give a Python signature in the text I read; for scripting use `pro-help/03-*.md` and the live tool page ("Verify against the Esri docs for your version").

## 4. In Line storage and the bit budget

**Definition.** "In Line" (the `isEmbedded` property in arcpy `Describe`) means the attribute value is stored inside the network topology itself instead of being looked up in the feature class. Esri says it is slightly more efficient to retrieve and recommends it for the most frequently used attributes (for example phase on electric networks, pressure on gas and water).

**Requirements.** Short or Long type; a coded value domain with **sequential codes starting from 0**; the same domain on the field the attribute is set on; field values must be positive. If the attribute is assigned to several classes it should have the same representation in each.

**Bit formula.** For a domain whose largest code is *n*, bits = ceiling(log2(n + 1)). A nullable In Line attribute needs **one extra bit**.

| Bit size | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Max domain code | 1 | 3 | 7 | 15 | 31 | 63 | 127 | 255 | 511 | 1023 | 2047 |

Worked examples:

- Esri's own example: a lifecycle domain with maximum code 3 needs 2 bits; if nullable, 3 bits.
- A phase domain `0..7` (De-energized, C, B, BC, A, AC, AB, ABC, the pattern in Esri's propagation page) needs 3 bits; nullable 4 bits.
- A pressure-zone domain with codes `0..40` needs 6 bits (since 2^6 = 64 > 41).

**Budget.** The topology has 64 bits for In Line attributes in total (system plus user). How many are left for user-defined attributes depends on the Pro release that **created** the dataset (shown under General on the Network Properties tab):

| Created with | User-defined In Line bits |
|---|---|
| ArcGIS Pro 3.0 and later | 25 |
| ArcGIS Pro 2.9 | 21 |
| ArcGIS Pro 2.8 and earlier | 20 |

Consequence: one wide domain (for example a 200-value material code) can eat a third of the budget. **Practitioner guidance:** keep In Line for the handful of attributes every trace uses (lifecycle, phase, device status, closed/open), leave wide domains and descriptive values as ordinary fields, and review the Inline (Bit Size) column before adding another. An upgrade does not widen the budget of an existing dataset by itself; I did not find an Esri statement either way, so verify against `pro-help/09-*.md` and the Upgrade Dataset documentation before relying on it.

## 5. Apportionable, nullable, substitution, overridable

**Apportionable (Double only).** A line feature can be split into several network **edge elements** (for example where devices connect mid-span). An apportionable attribute divides the line's value across those edges according to each edge's percentage position along the feature. Esri's example: a 100-foot line made of five 20-foot edges and `Shape length` counts as 5 in a connected-trace function (five edges), while length is apportioned so partial traces total correctly. The system attribute `Shape length` is apportionable. Only line features and edge objects show the behaviour even though the property can be assigned to junction or polygon classes.

**Nullable.** Nullable attributes allow null values; Esri states that null-valued attributes are treated as **zero traversal cost** in tracing, and a nullable In Line attribute spends one extra bit. A non-nullable attribute can only be set on a non-nullable field.

**Substitution (Long, out-of-line).** Lets a propagated value be swapped for another as the trace crosses a feature, for example phase AC becoming BC at a tap. Configure with Substitution checked and `Network Attribute to Substitute` pointing at the in-line integer attribute (8 bits or fewer) that carries the value being propagated. In the engine this works through the **Attribute substitution** network category on the tap asset types and the **Subnetwork tap** category (section 8). Esri's tool page lists long substitution as out-of-line only while requiring the substituted attribute to be in line; the page does not reconcile the two statements, so test with a small case.

**Overridable.** The tool parameter `Is Overridable` exists, but Esri states it is **not used in the current release** and any value is ignored. Any intended use (such as an external override table fed by live SCADA switch positions) is not described on the current tool page; treat that as unverified. Do not promise this capability to a user.

**Propagation (what the attribute is for).** Propagated attributes are written during Update Subnetwork, Export Subnetwork or Trace. The Esri propagation page names the propagator functions `Propagated_BITWISE_AND`, `Propagated_MIN` and `Propagated_MAX`; propagation starts at a controller and follows traversability; a false operator turns the feature into a barrier; nulls are ignored; propagation is ignored for upstream/downstream traces that use digitized direction; the **Propagator Resetter** category (UN dataset **v8**) makes a feature's own values become the new propagated values. Results are stored in the field you designate (for example "Phases Energized"). For Update Subnetwork, a Propagators definition is set in the tier's subnetwork definition (Python for the trace parameter; see `learn/06-tiers-and-subnetworks-in-depth.md` section 4). Setup order from Esri: field, coded value domain, In Line network attribute, Set Network Attribute, optional output field with domain, then Set Subnetwork Definition.

## 6. Assigning a network attribute to a field

Two tools, always in this order (topology disabled for both):

1. `Add Network Attribute` defines the attribute (name, type, options).
2. `Set Network Attribute` maps it to a field. Parameters per the Pro 3.7 tool page: Input Utility Network, Network Attribute, Domain Network, Input Table, Field. The field's data type must match.

Rules from Esri:

- one attribute maps to **one field per class**; a class can hold many different attributes;
- one attribute can be assigned to many classes or tables;
- a non-nullable attribute can only be set on a non-nullable field;
- a utility network can have any number of network attributes (the In Line bit budget is the real limit);
- the same coded value domain must sit on the field for In Line attributes.

Pitfall: adding a field after data load and then wanting it traced requires disabling topology, mapping, and re-enabling. Plan the traced fields in the schema design stage (Foundations already do this; see `pro-help/08-*.md`). Edits to a field that is mapped to a network attribute create **dirty areas** (section 11), while edits to unmapped fields do not.

## 7. Typical fields every UN class carries

Esri-documented fields (see `pro-help/02-*.md` and the Subnetworks documentation):

| Field | Purpose |
|---|---|
| `ASSETGROUP` | subtype field; major classification |
| `ASSETTYPE` | minor classification, domain nested under the asset group |
| `GLOBALID`, `OBJECTID` | identity; the `GlobalID` is required for attribute rules and associations |
| Subnetwork name field(s) | system-maintained by Update Subnetwork; `Unknown` until updated |
| `ASSOCIATIONSTATUS` | system-maintained bitmask of association roles |
| terminal fields on lines | which terminals each end connects to; do not hand-edit |
| editor tracking fields | needed for batch calculation and validation rules |

Fields such as asset ID, phase, lifecycle status, device status and "maintained by" are **Foundation or model conventions**, not engine requirements. The electric Foundation update blog mentions Lifecycle status trimmed to a minimum value set for tracing, an `Electric_Operating_Status` network attribute (nullable, domain without unknown), a `PhaseChange` field that should only be set where phase changes or at a subnetwork controller, and a domain bit "De-Energized, Traceable". Treat field names as model-specific: read the Foundation or your own schema (`arcpy.Describe(un).networkAttributes`) instead of assuming.

Asset ID: the Foundations fill it with attribute rules (section 13); the engine does not need it, but integrations, labels and work orders do.

## 8. Network categories

**Definition.** A network category is a tag applied to an **asset group / asset type** combination (not to a class). Every feature of that asset type carries the category. Categories are how you tell the engine "these are controllers", "these are protective devices", "stop the trace here".

**Mechanism.** Tools and traces ask "does this feature's asset type have category X?" at run time: Update Subnetwork and Export Subnetwork use Subnetwork Controller; Verify Circuits and Export Circuits use telecom categories; Trace conditions of `type: category` (barriers, filters, output conditions) use user-defined ones. A category does nothing by itself.

**System-provided categories** (Esri, Pro 3.7 "Network categories"; cannot be deleted, assignment optional unless noted):

| Domain network | Category | What it does |
|---|---|---|
| Traditional | Subnetwork controller | required for subnetworks; used by Update/Export Subnetwork; device and junction object classes only |
| Traditional | Subnetwork tap | features tapped off a midspan vertex of a line or edge object; commodity continues on the main line; tap features take the substitution value |
| Traditional | Attribute substitution | marks attributes that use a substitution value for tap features |
| Traditional | Propagator Resetter | resets the propagated value (UN v8) |
| Telecom | Circuit Location | active port that starts or stops circuits; a circuit cannot pass through it; used by Verify Circuits |
| Telecom | Conflict Container | root of a containment hierarchy; used during reconcile to report logical conflicts; only one per hierarchy |
| Telecom | Mux/Demux | multiplexers and demultiplexers; single-hop traversal limit |
| Telecom | Connector Junction | generic grouped junction objects bridging grouped and ungrouped modelling |
| Telecom | Splitter | splitter ports; same single-hop limit as Mux/Demux |
| Telecom | Edge Unit Container | manages unit identifier assignment for Unit Identifiable features; requires the Container association role; `Max Content Unit ID` limits units |
| Telecom | Junction Unit Container | same for grouped junction objects; requires the Container role |
| Telecom | Unit Identifiable | unit identifier management on grouped junction objects; valence-1 objects are traversal candidates |

Note: Esri also surfaces an **isolating** category in gas and water isolation traces (the gas isolation trace uses an "Isolating" network category together with device status); whether it is delivered as a system or Foundation category should be verified in the Foundation you use.

**User-defined categories.** Created with `Add Network Category` (parameters: Input Utility Network, Category Name; topology disabled; enterprise: default version, portal owner, database owner connection). Assigned with `Set Network Category` (Input Utility Network, Domain Network, Input Table, Asset Group, Asset Type, Categories). There is no limit on categories per asset type (a fuse can be both "Disconnect" and "Protective"). Industry examples: electric "Protective" (fuses, reclosers, breakers) for a "trace upstream until protective device", gas "Isolating" (valves), water "Hydrant" for output filters.

**Gotchas.**

- `Set Network Category` **replaces** the whole category set for that asset type; omit the parameter to clear all. Always pass the full list.
- Topology must be disabled; enterprise needs the default version.
- Subnetwork Controller is assignable only on traditional domain networks, only on the Device class and JunctionObject table, and in a partitioned traditional network only if the asset type already has a **directional** terminal configuration with at least one upstream and one downstream terminal (otherwise the choice is not offered).
- Edge Unit Container / Junction Unit Container are valid only on asset types with the Container association role.
- Category names are matched exactly in traces; a typo silently matches nothing (see `rest-api/08-*.md`).

```python
import arcpy
arcpy.un.SetNetworkCategory("Utility Network", "ElectricDistribution",
    "ElectricDistributionDevice", "Fuse", "Air Powered", ["Disconnect", "Protective"])
```
(Pattern from `pro-help/03-*.md`; check the live tool page for your version.)

## 9. Attribute rules: fundamentals

**Definition.** An attribute rule is an Arcade expression stored in the geodatabase on one feature class or table. The geodatabase runs it automatically; it is not a client add-in.

**Esri's three rule types** (Pro 3.7 "Attribute rule fundamentals"):

| Type | Purpose | When it runs |
|---|---|---|
| **Calculation** | populate or change values | immediate (on edit) or batch (later, on existing data) |
| **Constraint** | block an invalid edit and return an error | immediate only |
| **Validation** | find existing violations and create error features | batch only; reviewed in the Error Inspector |

Requirements and limits (Add Attribute Rule tool page and fundamentals page):

- the dataset needs a **GlobalID** field;
- **editor tracking** must be enabled for batch calculation and validation rules;
- in an enterprise geodatabase the operation is done as the data owner;
- rule **name unique, max 64 characters**; error message required for constraint and validation (max 256 characters); description max 256;
- once any rule exists the dataset needs **ArcGIS Pro 2.1** or later and cannot be used in ArcMap; newer Arcade functions can restrict clients further;
- licence Standard or Advanced (not Basic).

Tools in the Attribute Rules toolset (Pro 3.7): Add, Alter, Delete, Disable, Enable, **Evaluate Rules**, Export, Import and **Reorder** Attribute Rule, plus a Templates sub-toolset. Export/Import (CSV) is the supported way to move rules between datasets and into version control.

## 10. Rule anatomy: types, triggers, batch, Arcade keywords

Parameters of `Add Attribute Rule` (arcpy `arcpy.management.AddAttributeRule`; confirm names on the tool page):

| Parameter | Notes |
|---|---|
| Type | `CALCULATION`, `CONSTRAINT`, `VALIDATION_RULE` |
| Triggering Events | `INSERT`, `UPDATE`, `DELETE`; calculation and constraint only; required for non-batch calculation |
| Triggering Fields | update trigger; if none are named, all fields trigger |
| Batch | calculation: `BATCH` or `NOT_BATCH`; validation must be batch; constraint must be not batch |
| Field | calculation rules only; the field to populate |
| Is Editable | calculation only; default checked |
| Exclude from application evaluation | default unchecked; not for validation or batch rules |
| Subtypes | restrict to subtypes (for UN classes, effectively asset groups) |
| Severity | 1 to 5, validation only; 1 most severe |
| Error number / message | required for constraint and validation |
| Tags | searchable labels |

**Arcade profile globals and keywords** (Pro attribute rule help pages):

| Item | Meaning |
|---|---|
| `$feature` | the feature after the edit |
| `$originalfeature` | attributes before the edit (compare to detect real changes) |
| `$editContext.editType` | `INSERT`, `UPDATE`, `DELETE`, or `NA` (batch and validation rules report `NA`) |
| `$datastore` | entry point for `FeatureSetByName(...)` queries on other classes |
| `NextSequenceValue("seq")` | next number from a database sequence (create it with Create Database Sequence); rules using sequences should set Exclude from application evaluation |
| return `result` | single value (needs a target field) or dictionary with `attributes` and `geometry` (dictionary form Pro 2.7 / Enterprise 10.9) |
| return `{"errorMessage": ...}` | reject the edit; cannot be combined with other keywords |
| return `edit` | insert/update/delete rows in other classes via `className` plus `adds`, `updates`, `deletes`; calculation rules only, **requires** Exclude from application evaluation |
| `calculationRequired` / `validationRequired` | mark features for later batch evaluation |
| `^UN_Association` as `className` | edit UN associations (`fromClass`, `fromGlobalID`, `toClass`, `toGlobalID`, `associationType`, `fromTerminal`/`toTerminal`, `isContentVisible`, `percentAlong`) |
| `tag` | handle for a feature not yet created (Pro 2.7 / Enterprise 10.9) |

Association types accepted by rules include `connected`, `container`, `content`, `structure`, `attached` and, from UN version 4, `junctionEdgeFrom`, `junctionEdgeTo`, `midspan`; Esri's `^UN_Association` section lists the type values as `connectivity`, `containment`, `attachment` (plus the same UN v4 additions), so check the keyword page for the form you use. Esri warns: **do not write recursive edits** (infinite loop risk).

"Exclude from application evaluation": my reading of the Esri wording is that the rule is skipped by the client application's own edit-time evaluation and evaluated only by the geodatabase/service, which is why rules that return `edit` or use sequences need it; a practitioner article says it cannot be changed after the rule is saved. Verify against the Esri docs for your version.

## 11. How rules interact with topology, dirty areas and subnetworks

**Documented by Esri.**

1. **Dirty areas come from edits to network-relevant data**: geometry changes, `ASSETGROUP`/`ASSETTYPE` changes, changes to fields mapped as network attributes, association changes and terminal configuration changes. The dirty-areas page does not mention attribute rules.
2. **Rule-made association edits skip network rules.** The `edit` keyword with `^UN_Association` does not apply the UN connectivity/containment rules at edit time; the features are validated later when topology is enabled or validated. So a rule can create an association that Validate then flags.
3. **Update Subnetwork edit mode** decides whether rules fire during the update. *Without eventing* (default for default version, named versions and single-user) updates names and propagated values in place and does **not** trigger editor tracking, attribute rules, related-object updates or history. *With eventing* uses cursor updates, fires attribute rules (and resets validation status), editor tracking and history; use it only when rules must run during update. It can be slow on large subnetworks with many rules or feature-linked annotation, and on the default version holds a **shared lock for the whole operation**, blocking reconcile's exclusive lock. Set per tier in Set Subnetwork Definition (UN v4+).
4. **Update Is Connected** is a separate derived-state tool (see `learn/01-mental-model-and-life-of-an-edit.md`); whether it fires attribute rules or editor tracking is not stated on the pages read, so verify against the Esri docs for your version.
5. **Validate Network Topology does not evaluate attribute rules.** Rule evaluation (batch calculation, validation) is a separate step; in a named-version workflow Esri lists "evaluating attribute rules" as local quality control after validating (see `learn/03-topology-engine-and-validation.md` section 5).

**Inference (label: practitioner reasoning, not an Esri statement).** An immediate rule that writes a field mapped to a network attribute is an edit like any other and should create a dirty area; a rule that writes only unmapped fields should not. Test on a copy.

**Practical consequences.**

- A constraint rule rejects the edit before it reaches topology; a validation rule produces an error feature in a different list from network topology errors. Both appear in the Error Inspector but are fixed differently.
- Rules that cascade (push) into many features create many dirty areas and slow the next Validate.
- If rules that touch network-attribute fields fire during an Update Subnetwork run *with eventing*, check afterwards for new dirty areas and validate again before exporting. (Unverified, from the inference above; confirm on your data.)

## 12. Rules and branch versioning

Documented:

- **Immediate** calculation and constraint rules are stored in the geodatabase and run on edit; I did not find an Esri sentence describing exactly where service edits evaluate them, so verify for your release.
- **Batch calculation and validation rules** in enterprise branch-versioned data are evaluated by the **validation server**; the connection's Versioning Type must be **Branch**. The `Evaluate Rules` tool takes an input workspace (file or mobile geodatabase, or feature service URL), Evaluation Types (calculation and/or validation), optional Extent, and Async (default on for feature services). The page says only rules in the **default version** are evaluated; feature services need the **validation capability**; on Enterprise 11.2+ users need the **ArcGIS Advanced Editing** user type extension.
- REST equivalent: the `ValidationServer` `evaluate` operation (`rest-api/04-*.md`).
- Rules are created as the data owner (Esri fundamentals page); how new or changed rules reach existing named versions is not described on the pages I read, so verify before changing rules while versions are open.

Open points to verify for your release: how a rule that references other classes behaves across version moments, and how long evaluation of a large extent takes. **Practitioner guidance:** evaluate batch rules by extent per work area before reconcile, not for the whole network at once, and use async.

## 13. Rules the Foundations ship

Foundation models ship attribute rules so editors get IDs, derived values and basic checks without custom code. In the asset package they travel in a **B_AttributeRules** table and become ordinary attribute rules when the package is applied (Esri Community answer; see `pro-help/08-*.md` for the package workflow). The Esri rule inventories I read (rule counts and enabled flags are per that document version, so re-read for your release):

| Foundation (document version) | Rules listed | Highlights |
|---|---|---|
| Electric distribution (11.1) | 19 | GenerateIDs on 9 classes (Insert, Update); MeasuredLength From Shape; Create Ducts In Duct Bank; Contain Structure Line in Structure Line; **Validate Subnetwork Tap Lifecycle** (batch); **Transformer kVA** (constraint); **Validate Voltage** (batch); two rules shipped **disabled** (Ductavailable From Content, Distance From Container) |
| Gas and pipeline referencing (11.4) | 17 | GenerateIDs on 7 classes; Symbol Rotation; Cathodic Protection Traceability; Auto Contain By Rules (3 rules, shipped **disabled**); Constrain Material By Asset Type; Asset Type Material to Material Field |
| Water distribution (11.1) | 23 | Generate IDs (Insert only) on 7 classes; Hydrant Valve Size and Restrict Bypass Valve (validation); MeasuredLength From Shape; cathodic protection; rotation; eight "from intersection" copy rules (Diameter, lifecycle status, maintained by, owned by) |

Observations: none of the three inventories contains a subnetwork-name or phase rule (the subnetwork name is maintained by Update Subnetwork and phase by propagation). Rules keyed to Insert and Update both fire on every edit; GenerateIDs on Update works because the script returns early when the ID already has a value (the Esri Generate ID template behaves this way). The inventory documents do not state execution order.

Practice: inspect shipped rules by converting the sample asset package before customising (Esri Community advice), and keep a documented decision on which shipped rules you disable during migration loads.

## 14. Common utility patterns (Esri-documented versus practitioner)

| Pattern | Source status | How |
|---|---|---|
| Auto-populate asset ID from a sequence | **Esri-documented** (Generate ID template, Pro 3.4+; Foundation GenerateIDs rules) | calculation rule, Insert (and Update guarded by "if empty"), sequence via Create Database Sequence, Exclude from application evaluation |
| Compute length from shape | Esri Foundation rule (`MeasuredLength From Shape`) | calculation rule on lines |
| Copy diameter, status or ownership from the intersecting line to a device | Esri Foundation (water "from intersection" rules) | pull pattern with `Intersects` |
| Constrain valid attribute combinations | Esri Foundation (gas `Constrain Material By Asset Type`, electric `Transformer kVA`, `Validate Voltage`) | constraint (edit time) or batch validation (existing data) |
| Create or maintain associations on insert (attach to pole, contain in structure) | Esri blogs and Foundation (containment rules) | `edit` with `^UN_Association` or class `updates` with `associationType`; filter `ASSOCIATIONSTATUS = 0` to skip already-associated features |
| Roll up contained content (bank kVA from transformers) | Esri blog | listen to `associationstatus` change of the content, compare `$originalfeature` and `$feature` |
| **Subnetwork name inheritance** | **Not a rule job in Esri's design**: Update Subnetwork stamps the name on traversable features, and the tier's container options (Update Structure/Domain Network Containers, Include Content) populate supported/supporting names | use subnetwork management; a rule that copies a container's name to loose content is practitioner guidance and goes stale until the next update |
| **Phase from source** | **Not a rule job in Esri's design**: attribute propagation from the controller | a practitioner article recommends propagation for phases energised and traces plus mass updates for section names; use rules only to validate phase combinations |
| Symbol rotation from intersecting line | Esri Foundation (gas, water) | calculation on devices/junctions |

**Practitioner guidance:** do not use a rule where the engine already has the mechanism (subnetwork name, propagated phase, `IsConnected`). Rules are for per-feature data entry assistance and checks.

## 15. Performance cautions

- **Per-feature execution.** Rules run once per edited feature. Community experience (labelled practitioner): rules that query other tables run per row, so bulk inserts and field calculations that read related data are slow; for bulk loads, read the other table once in Python and write results, or use Data Interop or FME.
- **Disable during bulk load.** Esri's Disable Attribute Rules help says disabling rules can avoid performance problems when loading large amounts of data; `Enable Attribute Rules` turns them back on; new and imported rules are enabled by default. After loading, run batch rules over the loaded extent.
- **Order is not guaranteed by you.** Several rules on the same table can run in an order you do not control (community report); put interdependent fields in one rule, or consult the Reorder Attribute Rule tool. Circular dependencies make results depend on the order rules were added (Esri).
- **Triggers.** A rule set to Insert only will not fire on updates; a community report found a rule only running when Insert and Update were both checked. Review `Triggering Events` and `Triggering Fields`.
- **Cascades.** Push rules that update other classes multiply dirty areas and sub-edits; avoid loops and recursion.
- **Update Subnetwork with eventing** multiplies the cost by the number of rules on every traversed feature, and holds a shared lock on the default version (section 11).
- **Migration.** Attribute rules do not affect migration logic and are row-by-row, so migration is a poor time to depend on them (Esri Community, accepted answer). Rebuild Attribute Assistant functions as rules after load.
- **Large expressions.** Keep rules short enough to review; export to text for version control.

## 16. Illustrative Arcade examples

All four are **illustrative**: class names, field names and domain codes are placeholders. Test on a copy and check function signatures against the Arcade reference for your release.

```javascript
// 1. Calculation rule: asset ID from a sequence.
// Field: ASSETID. Triggers: Insert. Exclude from application evaluation: checked.
// Pattern follows Esri's sequence example; sequence name is a placeholder.
if (!IsEmpty($feature.assetid)) { return $feature.assetid }
return "TX-" + Text(NextSequenceValue("tx_assetid_seq"), "00000")
```

```javascript
// 2. Constraint rule (Insert, Update): transformer needs a positive rated kVA.
// 7 stands in for the Transformer asset group code; ratedkva is a placeholder field.
if ($feature.assetgroup == 7 && (IsEmpty($feature.ratedkva) || $feature.ratedkva <= 0)) {
  return { "errorMessage": "Transformers need a positive rated kVA." }
}
return true
```

```javascript
// 3. Calculation rule (Insert, Update), field DIAMETER on a device:
// pull the diameter from the pipe the device sits on (the Foundation "from intersection" idea).
if (!IsEmpty($feature.diameter)) { return $feature.diameter }
var lines = Intersects(FeatureSetByName($datastore, "WaterLine", ["diameter"], false), $feature)
var ln = First(lines)
if (ln == null) { return null }
return ln.diameter
```

```javascript
// 4. Guard pattern: run expensive logic only when the field of interest really changed.
// Adapted from Esri's $originalfeature guidance; field name is a placeholder.
if ($editContext.editType == "UPDATE" && $feature.lifecyclestatus == $originalfeature.lifecyclestatus) {
  return $feature.notes   // no-op for the target field
}
// ... recalculate here, for example set a "needs review" flag.
```

Association-creating rules (return an `edit` array with `^UN_Association` or `updates` with `associationType`) are version-sensitive; start from the Esri blog "Creating Utility Network Associations with Attribute Rules" and the Esri `arcade-expressions` repository (see `github-ecosystem/01-*.md`) rather than writing from memory. Note that blog posts contain typos; the articles I read have incomplete filters, so test before use.

## Common misconceptions

- "Network attribute = field." A network attribute is a named definition mapped to one field per class; the trace reads the mapping, not arbitrary fields.
- "In Line is always better." It is faster to read but spends a shared, small bit budget (25 bits for user attributes in datasets created by Pro 3.0+).
- "Apportionable works on any number." Only Double, and only line features and edge objects apportion.
- "Is Overridable lets SCADA override statuses." The parameter is ignored in the current release.
- "Set Network Category adds a category." It **replaces** the asset type's category list.
- "Telecom categories are Unit Container / Unit Identifier." The Esri names are Edge Unit Container, Junction Unit Container and Unit Identifiable (plus Circuit Location, Conflict Container, Mux/Demux, Connector Junction, Splitter).
- "Validate runs my attribute rules." It does not; rule evaluation is separate (batch rules via Evaluate Rules or `ValidationServer`).
- "Attribute rules run during Update Subnetwork." Only with the *With eventing* edit mode; the default does not trigger them.
- "A rule can create a connectivity association safely." Rule-made associations skip network rules at edit time and are checked at the next validate.
- "Subnetwork name or phase should be set by a rule." The engine owns these (Update Subnetwork, propagation).

## Quick checks

1. Which UN dataset version and which Pro release created it (Network Properties > General)? That sets the In Line bit budget and whether Big integer and Propagator Resetter exist.
2. Is topology disabled, and, for enterprise, are you on the default version as the database and portal utility network owner?
3. Is the field mapped to a network attribute (`arcpy.Describe(un).networkAttributes`), and does it need In Line (frequently traced) or can it stay out of line?
4. Is the domain a coded value domain with sequential codes starting at 0, and is the field non-nullable if the attribute is?
5. Which categories does the asset type carry now? Did you pass the complete list to Set Network Category?
6. For a "rule did not fire" report: type (immediate or batch), triggering events and fields, subtype filter, enabled flag, Exclude from application evaluation, and the client (an edit made by Update Subnetwork without eventing will not fire rules).
7. Is a batch or validation rule involved? Then check editor tracking, GlobalID, Versioning Type Branch, validation capability and the Evaluate Rules extent.
8. Does the rule write a network-attribute field or create associations? Expect dirty areas and a re-validate.
9. Are rules disabled during the bulk load, and were they re-enabled afterwards?

## Related files

- `pro-help/03-creation-configuration-attributes-categories-rules.md` (configuration tools and network rules)
- `pro-help/02-structure-of-a-utility-network.md` (fields, terminals, controllers)
- `pro-help/05-tracing.md` and `rest-api/08-trace-configuration-full-schema.md` (how attributes and categories are used in traces)
- `pro-help/08-asset-packages-foundations-migration.md` (Foundation delivery and asset packages)
- `learn/03-topology-engine-and-validation.md` (dirty areas, validate scope)
- `learn/06-tiers-and-subnetworks-in-depth.md` (propagators, summaries, edit modes)
- `rest-api/04-version-management-validation-feature-service.md` (`ValidationServer`)
- `arcpy/01-utility-network-module.md` (`Describe` properties, network category tool)

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-attributes.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-network-attribute.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-network-attribute.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-categories.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-network-category.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-network-category.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/attribute-propagation.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/update-subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-subnetwork-definition.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/an-overview-of-attribute-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/add-attribute-rule.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/an-overview-of-the-attribute-rules-toolset.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/evaluate-rules.html
- https://pro.arcgis.com/en/pro-app/tool-reference/data-management/disable-attribute-rules.htm
- https://pro.arcgis.com/en/pro-app/3.2/help/data/geodatabases/overview/attribute-rule-dictionary-keywords.htm
- https://pro.arcgis.com/en/pro-app/3.1/help/data/geodatabases/overview/attribute-rule-script-expression.htm
- https://www.esri.com/arcgis-blog/products/arcgis-pro/data-management/attribute-rules-generate-id
- https://www.esri.com/arcgis-blog/products/utility-network/electric-gas/advanced-attribute-rules-creating-utility-network-associations-with-attribute-rules
- https://www.esri.com/arcgis-blog/products/arcgis-pro/data-management/listening-for-utility-network-associations-events-in-attribute-rules
- https://www.esri.com/arcgis-blog/products/arcgis-solutions/electric-gas/utility-network-foundation-solutions-update
- https://doc.arcgis.com/en/arcgis-solutions/11.1/reference/pdf/Electric%20Utility%20Network%20Attribute%20Rules.pdf
- https://doc.arcgis.com/en/arcgis-solutions/11.4/reference/pdf/Gas%20and%20Pipeline%20Referencing%20Utility%20Network%20Attribute%20Rules.pdf
- https://doc.arcgis.com/en/arcgis-solutions/11.1/reference/pdf/Water%20Distribution%20Utility%20Network%20Attribute%20Rules.pdf
- https://community.esri.com/t5/arcgis-pro-questions/lessons-learned-attribute-rules/td-p/1269278 (practitioner)
- https://community.esri.com/t5/arcgis-utility-network-questions/what-place-do-attribute-rules-have-in-utility/td-p/1595295 (practitioner)
- https://sspinnovations.com/blog/streamlining-edits-in-the-utility-network-with-attribute-rules/ (practitioner)
- https://sspinnovations.com/blog/practices-for-attribute-automation-in-the-electric-utility-network/ (practitioner)
