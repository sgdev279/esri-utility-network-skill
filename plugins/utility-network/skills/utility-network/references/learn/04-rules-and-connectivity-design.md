# Utility Network: Rules and Connectivity Design
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: Esri ArcGIS Pro 3.7 help and tool reference, Esri Learn tutorial on rules, ArcGIS Runtime API reference (full list at the end).*

## Why this matters / when to read this

Network rules decide which pairs of asset group/asset type may connect, contain each other or attach to each other. They are the most common cause of "I snapped it but it is not connected" (error 8), "validate flags my new device" and "I cannot add this association". Read this when you design or extend a rule base, translate a rule request ("let a transformer sit on a pole") into the right rule family, or triage rule-related validation errors. Topology mechanics (dirty areas, validate, error storage) live in `learn/03-topology-engine-and-validation.md`; tool signatures are in `pro-help/03-creation-configuration-attributes-categories-rules.md`.

## Contents

1. The mental model: restrictions, then rules, default-deny
2. The three rule families and the five rule types
3. How rules are keyed (class, asset group, asset type, terminal)
4. Rule evaluation: when it runs and what you get when no rule exists
5. Stored rules: Network Properties, the Rules system table, CSV round-trip
6. Add, delete, import, export: tools, parameters, constraints
7. Terminal-specific rules
8. Edge, junction and junction-edge-junction specifics (and edge connectivity policy)
9. Devices, junctions and assemblies
10. Rule design method
11. Rule count and scale
12. Worked examples: transformer on a pole, valve on a main, gas regulator station, telecom splice enclosure
13. Troubleshooting table of rule-related errors
14. Common misconceptions, quick checks, related files, sources

## 1. The mental model: restrictions, then rules, default-deny

Two layers decide whether two things may relate:

| Layer | Who controls it | Editable? | Answers |
|---|---|---|---|
| **Feature restrictions** | Built into the UN at the class level | No ("can't be modified or removed", Esri) | Which classes may relate at all, and which rule types may exist (for example "a device cannot be geometrically coincident with another device") |
| **Network rules** | The administrator, at asset group and asset type level | Yes, with topology disabled | Which specific asset-type pairs are allowed among the structurally possible ones |

Rules build on restrictions and never override them: "You can add only rules that respect feature restrictions" (Add Rule tool). A relationship needs both layers to allow it.

**Default-deny.** Once a rule base exists, features can connect or associate only if a rule supports the relationship. A rule is permission, not a requirement: no rule means no connection. The network topology cannot even be enabled until at least one rule exists.

One documented exception: two edges that share an endpoint and have the **same asset group and asset type** connect through a system junction with no user-defined junction or rule; the system junction is created when topology is enabled or validated (network rules and feature restrictions pages).

## 2. The three rule families and the five rule types

| Family | What it controls | Rule type(s) in Pro | Mechanism that carries the relationship |
|---|---|---|---|
| **Connectivity** | Which point and line asset types may connect, optionally at which terminal | Junction-junction, junction-edge, edge-junction-edge | Geometric coincidence, or a connectivity association (for nonspatial objects) |
| **Containment** | Which asset types may hold which others | Containment | Containment association (Associations table; telecom may use foreign keys) |
| **Structural attachment** | Which asset types may attach to which structures | Structural attachment | Structural attachment association |

Per-type detail (Esri Add Rule and network rules pages):

| Rule type | Typical pair | Direction semantics | Terminals? |
|---|---|---|---|
| Junction-junction connectivity | Point to point (junctions, devices, junction objects), geometrically coincident or not | Direction does not matter for matching (Import Rules help) | Yes |
| Junction-edge connectivity | Point (device, junction, junction object) to line or edge object; line-end connectivity, or midspan | From = junction side, To = edge side | Yes, on the point side |
| Edge-junction-edge connectivity | Line to line through an intermediate junction; "a line can connect to either side of a point feature" | From = line, To = line, **Via** = junction or object | Via terminal available |
| Containment | Container holds content (and, where allowed, nested containers) | From = container, To = contents | No |
| Structural attachment | Structure hosts attachment | From = structure, To = attachment | No |

Prerequisites for the association families: the class acting as container or structure must first be given an **association role** (`Set Association Role`, parameter `Role Type` = Container, Structure or None; topology disabled). Only structure junction and structure junction object classes can take the Structure role; any structure or domain network class can take Container (Esri associations page; `pro-help/02-structure-of-a-utility-network.md`).

The .NET Runtime enum `UtilityRuleType` mirrors the five types: `JunctionJunctionConnectivity`, `JunctionEdgeConnectivity`, `EdgeJunctionEdgeConnectivity`, `Containment`, `Attachment` (the last is structural attachment). Its docs repeat that containment and attachment "do not support terminal connectivity" while junction-edge connectivity affects the three junction-to-edge association types: from side, midspan and to side.

## 3. How rules are keyed

A rule is a row keyed by **class + asset group + asset type** on each side, plus terminal where applicable. Feature class alone is never enough: every UN class has `ASSETGROUP` and `ASSETTYPE`, and rules, terminals, categories and roles are keyed on that pair (`pro-help/02-structure-of-a-utility-network.md`).

```
Rule  =  FROM [class | asset group | asset type | (terminal)]
         TO   [class | asset group | asset type | (terminal)]
         (VIA [class | asset group | asset type | (terminal)]  only for edge-junction-edge)
```

Consequences:

- Every new asset type needs its own rules; the rule base does not generalize to "devices".
- Changing a feature's asset group or asset type is an edit that creates a dirty area, because it changes which rules apply (`learn/03-topology-engine-and-validation.md`).
- A terminal is part of the key only for point classes that have a terminal configuration. The Add Rule page: terminal is "required if the asset type has terminals" and inactive for containment and structural attachment.

**Rules table columns by type** (Esri "View network rules", paraphrased):

| Rule type | Columns |
|---|---|
| Junction-Junction | ID, From Class, From Asset Group, From Asset Type, From Terminal, To Class, To Asset Group, To Asset Type, To Terminal, Created Time |
| Junction-Edge | ID, From Class/Group/Type, From Terminal, To Class/Group/Type, Created Time |
| Edge-Junction-Edge | ID, From and To Class/Group/Type, Via Class/Group/Type, Via Terminal, Created Time |
| Containment | ID, Container Class/Group/Type, Content Class/Group/Type, Created Time |
| Structural Attachment | ID, From (structure) Class/Group/Type, To (attachment) Class/Group/Type, Created Time |

## 4. Rule evaluation: when it runs and what you get when no rule exists

Esri: rules are evaluated when topology is **enabled or validated**, and when an association is **created or imported**.

| Situation | When checked | What you see |
|---|---|---|
| Point meets line, geometric coincidence, no junction-edge rule | Enable / validate | Error **8** on the features (feature error, `Status` 8) |
| Two rules both match the same terminal pair, or two terminals both allowed | Enable / validate | Error **9** (ambiguous connectivity) |
| Two lines of different asset group/type end at the same point with no junction | Enable / validate | Error **10** |
| Edit creates a containment association with no rule | At creation in Modify Associations / on import | The tool or pane returns an error; the feature is not added to the pane; no error record. Import Associations fails (Esri) |
| Containment relationship exists but unsupported (e.g. rule later deleted, or edit made outside the pane) | Enable / validate | Error **34** (point/line) or **17** (junction/edge objects) |
| Structural attachment unsupported | Enable / validate | Error **35** (point/line) or **18** (objects) |
| Connectivity association between nonspatial objects with no rule | Enable / validate | Error 8 on junction objects/edge objects (table row: "Point, line, junction object, edge object") |

Order and precedence documented by Esri:

1. Junction-edge rules are evaluated first; edge-junction-edge rules after them.
2. "Conflicting junction-edge rules for the same junction and edge override the edge-junction-edge rule."
3. Esri's page states no general ambiguity-resolution policy beyond this; the tutorial shows that a too-broad rule creates error 9.

Error IDs and fixes: `pro-help/04-associations-editing-errors.md` (ID tables) and `learn/03-topology-engine-and-validation.md` (storage, status bits, resolution). Rule errors are **feature/object errors with error-only `Status` (8 or 16)**: re-validating does not clear them, an edit (or a rule change then an edit or re-enable) does.

## 5. Stored rules: Network Properties, the Rules system table, CSV round-trip

- **Pro:** Layer Properties > **Network Properties** tab > **Rules** section lists each rule type with the columns above. The rule ID shown there is what Delete Rule asks for.
- **Rules system table:** reachable through the feature service at layer ID **500003** (`.../FeatureServer/500003`, `.../query`) as an example value in Esri's feature service appendix (UN v8 example; Associations 500001, Subnetworks 500002); `learn/02-data-model-in-depth.md` notes that Rules and Subnetworks are query-only in the service. Esri says to read the IDs from the `systemLayers` section of your own layer JSON rather than hard-coding.
- **CSV:** Export Rules writes 13 columns: `RULETYPE`, `FROMFEATURECLASS`, `FROMASSETGROUP`, `FROMASSETTYPE`, `FROMTERMINAL`, `TOFEATURECLASS`, `TOASSETGROUP`, `TOASSETTYPE`, `TOTERMINAL`, `VIAFEATURECLASS`, `VIAASSETGROUP`, `VIAASSETTYPE`, `VIATERMINAL`. `RULETYPE` values: Junction Junction Connectivity, Junction Edge Connectivity, Edge Junction Edge Connectivity, Containment, Structural Attachment. An asterisk (`*`) in a terminal column means all terminals of the asset type. `VIA` columns apply only to edge-junction-edge. For containment, FROM is the container; for structural attachment, FROM is the structure.

Example CSV rows (illustrative names; use your own data dictionary):

```
RULETYPE,FROMFEATURECLASS,FROMASSETGROUP,FROMASSETTYPE,FROMTERMINAL,TOFEATURECLASS,TOASSETGROUP,TOASSETTYPE,TOTERMINAL,VIA...
Structural Attachment,StructureJunction,Pole,Wood Pole,,Device,Transformer,Overhead Transformer,,,,,
Junction Edge Connectivity,Device,Transformer,Overhead Transformer,High,Line,Primary,Overhead Primary,,,,,
```

**Practitioner guidance:** export a clean baseline, version it in source control, diff it between releases and re-import into a test network; this is the only practical way to review thousands of rules.

## 6. Add, delete, import, export

### Add Rule (tool page; Standard or Advanced; Basic: no)

Python (from the tool page; terminal and via arguments optional):

```python
arcpy.un.AddRule(in_utility_network, rule_type, from_class, from_assetgroup, from_assettype,
                 to_class, to_assetgroup, to_assettype, {from_terminal}, {to_terminal},
                 {via_class}, {via_assetgroup}, {via_assettype}, {via_terminal})
# rule_type tokens include JUNCTION_JUNCTION_CONNECTIVITY (see the tool page for the rest)
```

(Delete Rule shows the matching tokens `JUNCTION_EDGE_CONNECTIVITY`, `EDGE_JUNCTION_EDGE_CONNECTIVITY`, `CONTAINMENT`, `STRUCTURAL_ATTACHMENT`, `ALL`.)

| Item | Detail |
|---|---|
| From Table | Container or structure for containment/attachment; junction or junction object for junction-edge and edge-junction-edge |
| To Table | Contents/attachment; for edge-junction-edge, the second line |
| Via* | Only for edge-junction-edge |
| Terminals | From/To Terminal required if the asset type has terminals; inactive for containment and attachment. In the Esri tutorial, choosing **All** for the terminal creates one rule per terminal |

### Delete Rule

`arcpy.un.DeleteRule(in_utility_network, rule_type, rule_desc)` where `rule_desc` starts with the rule ID (for example `"2: From[...] From[...]"`, copied from Network Properties). Deleting is permanent and does not disconnect features or remove associations; when topology is re-enabled, features relying on the rule get errors, and geometrically coincident features are disconnected.

### Import Rules / Export Rules

`Import Rules`: parameters Input Utility Network, Rule Type (All or one type), Input File (.csv). `Export Rules`: Input Utility Network, Rule Type, Output File. Both Standard/Advanced. Import requires topology disabled.

### Constraints common to all

| Constraint | Detail |
|---|---|
| Topology | Disabled for Add/Delete/Import (Export is read-only, no topology requirement was stated) |
| Ownership (enterprise) | Connection as the database utility network owner and portal account as the portal utility network owner |
| Version | Manage rules on the default branch version |
| Service | Stop the utility network service before adding or deleting a rule; changes take effect after the service and Pro are restarted (Esri network rules page) |
| Named versions | Rule updates appear in an existing named version only after it is reconciled |
| First enable | Rules must exist before first enable |

## 7. Terminal-specific rules

A terminal is a logical port on a device or junction object. Rules can name the terminal, which is how a high-side/low-side transformer or a two-port valve gets different permissions per port.

Documented behaviours:

- Junction-junction and junction-edge rules support terminals; containment and structural attachment do not.
- "Whenever an asset type's terminal configuration changes, rules must be added that specify connectivity for the available terminals" (Esri tutorial).
- Removing terminals requires deleting the dependent junction-edge rules first, then setting the asset type to a single-terminal configuration; terminal configurations can be removed only **before topology is first enabled** (tutorial).
- Midspan connectivity to terminals is limited; split the line or use an intermediate nonterminal device (network rules page). A multi-terminal device cannot sit midspan (error 38).
- Terminal choice on a line is stored as the line's From/To terminal; an invalid or missing terminal gives error 36; an invalid path gives error 39.
- Ambiguity (error 9) arises when more than one terminal rule is applicable. The Esri fix: choose the terminal in **Modify Terminal Connections**, or ensure only one rule allows the connection.
- `*` / All terminals is convenient but broad: in the tutorial a storage tower with two ports got ALL-terminal rules and error 9 appeared.

Example of the failure mode (water, from the tutorial): ALL-terminals rule from a tower device to a distribution main resolved error 8 but created error 9, because both ports now matched.

## 8. Edge, junction and junction-edge-junction specifics

**Geometric coincidence** is allowed between a point and a line, and between two lines that share an intermediate point feature (feature restrictions page). Everything else is an association.

**Edge connectivity policy** (`Set Edge Connectivity`; topology disabled; owner connections in enterprise): per asset group/type of a line or edge object, **End vertex** (default) allows connection only at ends; **Any vertex** allows connection anywhere along the line including ends. It controls snapping behaviour in Pro; a midspan point on an End-vertex line produces error 13. This is configuration separate from rules, but both must allow a midspan device.

**Edge-junction-edge** is for line-to-line transitions through a junction or device: for example a pipe changing from one asset type to another needs a rule naming the lines and the connecting junction as Via. Without it, error 10. Two lines of the **same** asset group/type need none.

**Nonspatial objects.** Junction-edge rules extend to junction objects and edge objects through connectivity associations. Esri's feature restrictions list the legal association combinations, for example Line to EdgeObject via Device or Junction, EdgeObject to EdgeObject via Device, Junction or JunctionObject, and the StructureLine/StructureEdgeObject equivalents via StructureJunction. Telecom: a grouped edge object cannot connect to an ungrouped junction object without a grouped generic junction carrying the Connector Junction category.

## 9. Devices, junctions and assemblies

| Class | Terminals | Role in rules |
|---|---|---|
| Device (point) | Optional; default "Single terminal"; required for subnetwork controllers | Junction-edge and junction-junction rules, with terminals; cannot be coincident with another device (feature restriction) |
| Junction (point) | No | Simple node; junction-edge rules without terminals |
| Assembly (point) | Not used for flow | Typically a container of devices (for example a transformer bank holding transformers): the containment rule's From side |
| JunctionObject / EdgeObject | JunctionObject can have terminals | Rules via connectivity/containment/attachment associations |
| StructureJunction / StructureLine / StructureBoundary | Structure network; no resource flow | Structure role for attachment; container role for containment; structural attachment rules |

(Classes per `pro-help/02-structure-of-a-utility-network.md`.) Devices that are subnetwork controllers need directional terminal configurations; configure terminals before assigning categories and before writing rules that mention those terminals.

## 10. Rule design method

1. **Start from a Foundation.** Esri ships Utility Network Foundations (electric, gas and pipeline referencing, water, sewer, stormwater, communications, district energy) with asset packages that already include rules, terminal configurations, roles and categories (`pro-help/08-asset-packages-foundations-migration.md`). Esri: default data models "include a recommended set of rules", and rule changes are "mainly needed when adding new asset types or unique drawing standards".
2. **Export the baseline** (`Export Rules`, All) and commit it. This is your control copy.
3. **Add asset types first** (asset package or Pro tools), then terminal configs, roles and categories, **then** rules. Rules that name a missing terminal cannot be written.
4. **Write rules per class family**: connectivity (what hangs on what), then containment (what is inside what), then structural attachment (what mounts where).
5. **Test with Only generate errors**: disable topology, change rules, run Enable Network Topology with *Only generate errors* on a copy (needs nonversioned data) and inspect the error set; Esri's tutorial recommends exactly this.
6. **Fix data before config** (Esri): editing a feature's type is usually less risky than adding a rule. Removing directional terminals can loop or invalidate subnetworks.
7. **Do not over-add** (Esri): "Avoid configuring too many rules, since this often creates additional topology errors." Each rule is a permission; excess permissions create ambiguity (error 9) and let wrong data pass.
8. **Roll out** in a maintenance window: stop service, apply rules, restart service and Pro, enable, validate, update subnetworks, reconcile named versions.

**Practitioner guidance.** Keep a rule request template: *relationship in words, family, from/to class-group-type, terminals, data fixes considered, test result*.

## 11. Rule count and scale

Esri's pages state no maximum rule count ("The page does not specify numeric limits"). Scale is driven by combinatorics: containment and connectivity rules multiply asset types by asset types (and by terminals). Reported Foundation scale: an Esri blog sample for the stormwater Foundation was reported to list roughly 3,000 rules, about 1,607 containment, 802 junction-junction and 441 junction-edge (blog figures not re-verified for this review; the count may have changed; see Esri Foundation documentation). Implications:

- Rule review is a data job: export to CSV, pivot by from-group/to-group.
- Containment dominates in dense station models.
- `*`/All terminals multiplies row counts by terminals.
- Rules live in the network definition (not edit-space features), so they do not create dirty areas; changes take effect after the enable/validate cycle.

## 12. Worked examples

Names below are **illustrative**: asset groups, asset types and terminal names differ by model. Read your data dictionary or Network Properties before writing rules.

### 12.1 Electric: distribution transformer on a pole

Two separate relationships, two rule families.

| Relationship | Family | Rule(s) |
|---|---|---|
| Transformer electrically connects to primary and secondary conductors | Junction-edge connectivity, per terminal | Device: Transformer / Overhead Transformer, **terminal High** -> Line: Primary / Overhead Primary; terminal **Low** -> Line: Secondary / Overhead Secondary |
| Transformer is mounted on the pole | Structural attachment | From: StructureJunction, Pole / Wood Pole (role **Structure**); To: Device, Transformer / Overhead Transformer |

Steps:

1. Set the pole asset type's role to **Structure** (`Set Association Role`, deletion semantics Cascade, Set to none or Restricted; Restricted blocks deleting a pole that has attachments). Topology disabled.
2. Give the transformer a directional terminal configuration (high and low terminals).
3. `Add Rule` junction-edge for each terminal-to-line pairing; do not use All terminals unless both ports may touch the same line type (error 9).
4. `Add Rule` structural attachment (no terminals).
5. Enable/validate; attach the transformer to the pole in **Modify Associations**.

Failures: no attachment rule -> the pane refuses; later validate error 35 if the association was imported or the rule removed. Primary line meets the Low terminal with no rule -> error 8. Both terminals accept the same line type -> error 9 until the line's terminal is specified.

### 12.2 Water: a valve on a main

Case A, the valve has **no terminals** (or one terminal) and the main continues on both sides. The pipe is two lines meeting at the valve.

- Same main type both sides: junction-edge rule Valve -> Main for the connection of each end; two lines of the same type connecting directly need no rule, but with a device between them you need the junction-edge rule(s).
- Main changes type at the valve (for example Transmission to Distribution): add an **edge-junction-edge** rule with Via = the valve asset type; without it error 10.

Case B, the valve has **two terminals** (Esri's tutorial shows a "Flow Valve" with ports): add a junction-edge rule per terminal (or All) with the main, split the main at the valve, and connect each segment to the intended terminal. A multi-terminal valve placed midspan on one unbroken line is error 38; either split the line, relocate the valve to an endpoint, or use a no-terminal valve type. Tutorial outcome: an air-gap valve without terminals plus one junction-edge rule to the main resolved error 8; a flow valve with terminals needed a rule per terminal.

Pitfall: a valve typed as the wrong asset type (for example a service valve versus system valve) is a data error, not a missing rule; check types first.

### 12.3 Gas: a regulator station container

A station groups regulators, valves, relief devices, meters and short pipe runs. Model it with a container.

| Relationship | Family | Rule(s) |
|---|---|---|
| Station holds regulator, valves, piping | Containment | From (container): Assembly or StructureBoundary asset type "Regulator Station" (role **Container**, `View Scale` for containment mode); To: Device Regulator, Device Valve, Line Pipe types inside |
| Station piping connects to the gas main | Junction-edge | Main -> station inlet device/junction, with terminal if the device has terminals |
| Optional nesting | Containment | Container -> nested container if the rules allow (Runtime docs: "content or a nested container, if allowed") |

Notes: `Set Association Role` options include `Split Content` (only for line containers) and deletion semantics. Containment is not terminal-aware: the regulator's inlet/outlet terminals matter for its connectivity rules, not for the containment rule. If devices in the station have no containment rule: pane refuses, or error 34 after validate. Dense station contents are the main reason containment rules dominate rule counts (section 11). Whether your gas model uses an Assembly or a structure boundary as the station is a modelling choice; check the Gas Foundation dictionary.

### 12.4 Telecom: a splice enclosure

A splice closure holds splice trays and spliced strands. In the telecom domain network the strands are nonspatial edge objects grouped into units, and the closure is a container that hands out unit IDs.

| Relationship | Family | Rule(s) |
|---|---|---|
| Closure contains splice tray / splice junction objects | Containment | Container: Device (or junction object) Closure with role Container; contents: Junction Object Splice Tray / Splice (names vary) |
| Cable segments land at the closure | Junction-edge connectivity | Closure -> Line (cable) and closure -> EdgeObject (strands) via connectivity associations |
| Strand-to-strand splice | Junction-junction or edge-junction-edge via a splice junction object | EdgeObject -> EdgeObject Via JunctionObject Splice (feature restrictions allow EdgeObject to EdgeObject via Device, Junction, JunctionObject) |
| Grouped strands to an ungrouped splitter port | Via Connector Junction | Rules must include the Connector Junction grouped junction object |

Telecom specifics: the closure's asset type carries the **Junction Unit Container** network category (Device and JunctionObject classes) and the cable the **Edge Unit Container** category (Line and EdgeObject classes), both of which manage unit IDs (the finer uniqueness behaviour is in Esri Foundation documentation; verify against the Esri docs for your version); topology must be enabled and a connectivity rule must exist for each pair. Unit ranges (`FirstUnit`/`LastUnit`) sit on associations, but the rule only decides whether the **pair of asset types** may connect, not unit counts. Nonspatial objects without an association chain to a spatial feature are unlocatable and silently ignored by topology.

## 13. Troubleshooting table of rule-related errors

| Symptom / error | Meaning | First checks | Fix |
|---|---|---|---|
| **8** No connectivity rule | The two asset types (and terminals) have no junction-edge/junction-junction rule | Network Properties > Rules; correct asset type? terminals assigned? | Change AG/AT, or add rule (disable topology, then enable, validate) |
| **9** Ambiguous connectivity | More than one rule or terminal matches | Rules with All terminals? duplicate rows in export? | Specify terminal in Modify Terminal Connections, or narrow rules |
| **10** Edges differ in AG/AT with no junction | Missing edge-junction-edge path | Is there a junction between them? | Match the types, or insert a valid junction with an edge-junction-edge rule |
| **13** Midspan not allowed | Edge connectivity policy is End vertex | Policy for the line type | Move to a vertex, delete, or set Any vertex (admin) |
| **17 / 34** Containment unsupported | No containment rule for object (17) or point/line (34) | Container's role set? rule From/To order reversed? | Edit attributes or add containment rule; check From = container |
| **18 / 35** Attachment unsupported | No structural attachment rule | Structure role set on the pole/structure type? | Edit attributes or add rule (Esri's table lists a containment rule as the admin option for 18, a probable slip) |
| **23** Asset type not defined for group | Not a rule problem | AG/AT combination valid? | Set valid asset type |
| **31** Association references invalid GlobalID | Bad import | From/To GlobalIDs | Correct the data |
| **36** Invalid terminal on a line | Terminal ID not on the device, or device lost terminals | Device terminal configuration vs line From/To terminal | Fix line terminal or device configuration |
| **38** Multi-terminal device midspan | Terminals and midspan conflict | Where is the device on the line? | Split the line, relocate, or use no-terminal type |
| **39** Point has invalid terminal configuration (path) | Terminal path/configuration value not valid | Valid paths in Network Properties | Modify Terminal Path |
| Pane refuses to add association | No supporting rule (no error record) | Role set? rule direction? | Add rule or change types |
| Import Associations fails | Rule missing for at least one row | CSV From/To order (container first) | Add rules; re-import |
| Rule added but nothing changes | Service not restarted, or named version not reconciled | Stop/start service and Pro; reconcile | Restart; reconcile |
| New rule yet error persists | Error-only row ignored by validate | `Status` 8/16 | Edit the feature, then validate (`learn/03-topology-engine-and-validation.md`) |
| Cannot add rule | Topology enabled, wrong owner connection, or violates feature restrictions | Network topology state; connection as database owner | Disable topology, use owner connection |
| Deleted rule, features now in error / disconnected | Expected | Export before delete | Re-add rule |

## Common misconceptions

- "Rules are optional." Once a rule base exists they are mandatory permissions; none means error 8, 17, 18, 34 or 35.
- "Snapping creates connectivity." Coincidence connects only if a rule supports it and validate has run.
- "A rule on the feature class covers all asset types." Rules key on asset group and asset type.
- "Containment and attachment rules take terminals." They do not.
- "Direction matters for connectivity rules." For junction-junction, junction-edge and edge-junction-edge, no (Import Rules help); for containment and attachment it does.
- "More rules is safer." Esri says too many rules create extra errors.
- "I can add a rule while editing." Topology must be disabled; enterprise needs the service stopped.
- "Deleting a rule disconnects data immediately." It happens at the next enable/validate.

## Quick checks

- Which error ID, and which feature class/asset group/type pair?
- Does the asset type have a terminal configuration? Which terminal does the line use?
- Is the container or structure role set on the From asset type, and is the rule From = container/structure?
- Is topology disabled, and are you the database owner and portal owner?
- Was the service restarted, and was the named version reconciled after the rule change?
- Is the pair also allowed by feature restrictions (class level)?
- Has the rule base been exported recently, so a bad import/delete can be undone?
- Is the line's edge connectivity policy End vertex while the device is midspan?

## Related files

- `learn/01-mental-model-and-life-of-an-edit.md`, `learn/02-data-model-in-depth.md`, `learn/03-topology-engine-and-validation.md`
- `pro-help/02-structure-of-a-utility-network.md`, `pro-help/03-creation-configuration-attributes-categories-rules.md`, `pro-help/04-associations-editing-errors.md`, `pro-help/08-asset-packages-foundations-migration.md`

## Sources

- https://pro.arcgis.com/en/pro-app/3.6/help/data/utility-network/network-rules.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-utility-network-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/feature-restrictions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/associations.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-edge-connectivity-for-line-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/add-rule.html
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/add-rule.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/delete-rule.htm
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/import-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/export-rules.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-association-role.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/enable-network-topology.html
- https://learn.arcgis.com/en/projects/configure-rules-for-a-utility-network
- https://developers.arcgis.com/rest/services-reference/enterprise/appendix-working-with-the-feature-server-utility-network-server/
- https://developers.arcgis.com/net/api-reference/api/netwin/Esri.ArcGISRuntime/Esri.ArcGISRuntime.UtilityNetworks.UtilityRuleType.html
