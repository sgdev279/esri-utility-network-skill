# Utility Network — Associations, Editing & Error Handling (Deep Reference)
*Source: ArcGIS Pro Help + Tool Reference, "Utility Network" book*

> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

## Association roles (Container / Structure)

Before a feature can *participate* as a container or a structure in an
association, its asset type must be assigned the corresponding **association
role** — this is separate from (and a prerequisite to) the network rules that
say *which* asset types are allowed to associate with it.

- The role is assigned at the feature class or table level for specific asset
  groups and asset types. The structure network classes are `StructureJunction`
  (point), `StructureLine`, `StructureBoundary` (polygon), `StructureJunctionObject`
  and `StructureEdgeObject` (tables). Which classes may take the Container vs
  Structure role is governed by the network's feature restrictions; Esri's
  pages do not list them in one place, so verify against the Esri docs for
  your version before asserting that a given class can or cannot be a
  container or structure.
- Assigned with **`Set Association Role`**
  (`arcpy.un.SetAssociationRole(in_utility_network, domain_network, featureclass,
  assetgroup, assettype, association_role_type, association_deletion_semantics,
  {view_scale}, {split_content})`). Requires **network topology disabled**; for
  enterprise geodatabases, the input utility network must come from a connection
  as the **database utility network owner** and the portal account must be the
  **portal utility network owner**. Key parameters:
  - `association_role_type` — `CONTAINER`, `STRUCTURE` or `NONE` (neither, but
    still connects to structures).
  - `association_deletion_semantics` — controls what happens to
    content/attachment features when the container/structure is deleted:
    | Value | Behavior |
    |---|---|
    | **CASCADE** | Deletes all content/attachment features along with the container/structure. |
    | **SET_TO_NONE** | Content/attachment features are kept but the association is removed. |
    | **RESTRICTED** | Deletion is blocked with an error until content/attachment features are removed first. |
  - `view_scale` — the scale used when entering **containment mode** (the
    special editing view for looking inside a container). Container-only (View
    Scale and Split Policy apply to containers; deletion semantics apply to
    both roles); does not apply to junction and edge objects.
- **Important constraint**: you can only **unassign** a Container/Structure
  role **before** network topology is enabled for the first time. Plan role
  assignments before initial topology enablement — this mirrors the same
  "permanent after first enable" constraint that applies to terminal
  configurations (see `02-structure-of-a-utility-network.md`).

## Import / Export Associations — the CSV workflow

This is the standard way to bulk-load or migrate associations (connectivity,
containment, structural attachment) without manually drawing them in the
editor — e.g., migrating from a geometric network, or scripting associations
from an external asset-management system.

**Prerequisite ordering** (from Esri community guidance, consistent with the
rules requirement above): rules supporting the association type must already
exist (`Add Rule`) before features can be associated — either by hand or via
import.

### CSV schema (identical for Import and Export)
```
ASSOCIATIONTYPE, FROMFEATURECLASS, FROMASSETGROUP, FROMASSETTYPE, FROMGLOBALID,
FROMTERMINAL, TOFEATURECLASS, TOASSETGROUP, TOASSETTYPE, TOGLOBALID, TOTERMINAL,
ISCONTENTVISIBLE, PERCENTALONG
```
- `ASSOCIATIONTYPE` values: `Junction Junction Connectivity`,
  `Junction Edge From Connectivity`, `Junction Edge Midspan Connectivity`,
  `Junction Edge To Connectivity`, `Containment`, `Structural Attachment`.
- `FROMTERMINAL`/`TOTERMINAL` apply only to junction-junction connectivity;
  `ISCONTENTVISIBLE` (True/False) applies only to containment.
- If the network contains a **telecom** domain network, four more columns are
  required even when the target is a traditional domain network:
  `FROMFIRSTUNIT`, `FROMLASTUNIT`, `TOFIRSTUNIT`, `TOLASTUNIT`.
- `PERCENTALONG` — only meaningful for **junction-edge midspan connectivity**
  (a junction object attached partway along a line, e.g. `0.75` = 75% along
  the line from its "from" end).
- `FROMGLOBALID` / `TOGLOBALID` — the actual feature GUIDs; this is why a
  common practical pattern (per Esri Community) is: **(1)** create one
  association manually in the editor, **(2)** `Export Associations` it to see
  the exact CSV shape/values Pro expects, **(3)** append your bulk rows in
  that same shape, **(4)** `Import Associations`.

### `Import Associations` — GP signature
```python
arcpy.un.ImportAssociations(in_utility_network, association_type, csv_file)
```
- `association_type` accepts `ALL`, `JUNCTION_JUNCTION_CONNECTIVITY`,
  `CONTAINMENT`, `STRUCTURAL_ATTACHMENT`, `JUNCTION_EDGE_FROM_CONNECTIVITY`,
  `JUNCTION_EDGE_MIDSPAN_CONNECTIVITY` or `JUNCTION_EDGE_TO_CONNECTIVITY`.
- Requirements: single CSV file; every feature referenced must **already
  exist** in the utility network; supporting rules must already exist; for
  enterprise geodatabases, the input utility network connection must be
  established as the **database utility network owner**.

### `Export Associations` — GP signature
```python
arcpy.un.ExportAssociations(in_utility_network, association_type, out_csv_file)
```
Same ownership requirement as Import for enterprise geodatabases.

## Errors and dirty areas (deep dive)

### What creates a dirty area
- **Any edit** near/on the network (insert/update/delete a feature, modify an
  object, change an association) marks a **dirty area** — a polygon
  encompassing the affected feature's geometry — the next time network
  topology is enabled or validated.
- A dirty area becomes an **error dirty area** specifically when the edit
  causes the feature to **violate a rule or restriction** (as opposed to just
  being an ordinary pending-validation edit).

### The `Status` bitmask (Dirty Areas / Error Inspector attribute)
`Status` is a **bitmask** — individual bit positions correspond to the kind of
operation that produced the dirty area, and **multiple bits sum together**
when several conditions apply to the same dirty area:

| Bit position | Meaning | Bit value (2^n) |
|---|---|---|
| 0 | Inserted/Updated feature | 1 |
| 1 | Deleted feature | 2 |
| 2 | Modified objects | 4 |
| 3 | Feature error | 8 |
| 4 | Object error | 16 |
| 5 | Subnetwork error | 32 |

Example: a `Status` value of **16** means bit 4 ("Object error") is set. If
edits *and* an error both apply, values sum (e.g., insert + feature error =
1 + 8 = 9). `Status` is shown in the Dirty Areas attribute table but is **not**
included in the Error Inspector table itself — use the Dirty Areas
sublayer/table when you need the raw bitmask, use Error Inspector for a
pre-filtered, human-readable error list.
**A `Status` of 0 displays when network topology is disabled.**

### Which dirty areas Validate will and won't touch (verified against Esri's Dirty areas and Errors pages)
Esri: during validation, **only edit dirty areas, or error dirty areas that also
carry an edit bit (1, 2 or 4), are evaluated to be cleaned. Error dirty areas
without an edit bit are ignored.** Consequences worth telling users plainly:

| Status | Edit bit? | Validate re-evaluates it? | What clears it |
|---|---|---|---|
| 1, 2, 4 (and sums such as 3, 5, 7) | yes | yes | Validate Network Topology (as long as no error exists in the validation extent) |
| 9, 10, 12, 17, 33, 41 ... (edit + error) | yes | yes | Fix the cause, then validate; if the feature still violates a rule the error bit stays |
| **8, 16, 32 and sums of only error bits such as 24, 40, 48, 56** | **no** | **no, ignored** | **Edit the feature (geometry, attribute, rule or subnetwork definition) to fix the cause. The edit adds an edit bit, and the next validate can clear it.** Running validate again does nothing |

So "Validate said success but my Status 8 and 40 rows are still there" is
expected behaviour, not a failed validate. "Success" only means the job ran.
Errors originate from enabling topology, validating topology or updating a
subnetwork, and are corrected by editing the feature, the network rules or the
subnetwork definition, then re-validating.

- **Subnetwork errors (bit 32)** are discovered by Update Subnetwork. Esri's
  "Update subnetwork errors" table lists IDs 24, 26, 27 (UN version 1 only), 28,
  29, 30, 33, 40, 41, 42 and 47. When one occurs, the subnetwork status of
  every controller in the Subnetworks table for that subnetwork (and the
  matching SubnetLine row) becomes **Invalid** until it updates cleanly. Fix the
  cause, then Update Subnetwork again.
- **Object errors (bit 16)** concern junction objects and edge objects. Esri
  names IDs 17 (no containment rule), 18 (no structural attachment rule),
  43 (edge object references the same junction object at both ends) and 44
  (stacked junction objects) in the enable/validate table, and IDs 41 and 42
  (junction/edge object not valid for the tier's Valid Junction Objects / Valid
  Edge Objects) in the update-subnetwork table. Association errors are created
  when topology is enabled or validated, not when the association is created
  or imported. Esri's pages do not map each error ID to a specific Status bit,
  so do not assert one beyond the groupings above. Fix by editing attributes or
  adding the rule.
- A 9 is an edit plus a feature error; after validation it becomes 8 if the
  error persists (then it needs a feature edit, not another validate) or
  disappears if the edit fixed it.

### Error Inspector pane
- Opened from the **Utility Network** tab → **Network Topology** group →
  **Error Inspector** (requires UN version 4 or later). The **Dirty Areas**
  sublayer sits under the utility network layer in the **Contents** pane
  (right-click → Attribute Table) for the raw rows, including `Status`.
- The **Map Extent** filter is on by default (only shows dirty areas with errors
  in the current view) — a common troubleshooting gotcha is having errors
  elsewhere in the network that don't appear until you turn this filter off.
- Selecting an error shows its attributes on the **Details** tab. Network
  Source ID (which class the error feature belongs to) and Feature GUID (the
  specific feature) are the usual way to locate the feature in error; Esri's
  page does not enumerate the table columns, so verify the exact column names
  in your Pro version.

### Error IDs (Esri "Utility network error IDs", paraphrased)
Enable and validate network topology errors:

| Error ID | Situation | Feature type |
|---|---|---|
| 0 | Field has an invalid data type | Point, line, junction object, edge object |
| 1 | Network feature has empty geometry (typical fix: delete and re-create it) | Point or line |
| 2 | Subtype unknown (e.g., Asset Group is Unknown) | Point or line |
| 5 | Line shorter than the network tolerance | Line |
| 6 | Vertex along the line cannot be located | Line |
| 8 | No connectivity rule supports the connection | Point, line, junction object, edge object |
| 9 | More than one connectivity rule applies (ambiguous) | Point and line |
| 10 | Connected edge features have different asset group/type | Line |
| 13 | Feature placed midspan violates edge connectivity policy | Point and line |
| 17 | No containment rule supports the association | Junction object, edge object |
| 18 | No structural attachment rule supports the association | Junction object, edge object |
| 19 | Linear feature is multipart | Line |
| 20 | Linear feature is self-intersecting | Line |
| 21 | Duplicate vertices, or fewer than two vertices | Line |
| 23 | Asset type not defined for the feature's asset group | Point, line, junction object, edge object |
| 25 | Point features stacked at the same location | Point |
| 31 | Association references an invalid from/to GlobalID | Point or junction object |
| 32 | Weight value exceeds the reserved bits of an inline network attribute | Point |
| 34 | Unsupported containment relationship | Point and line |
| 35 | Unsupported structural attachment relationship | Point and line |
| 36 | Line has an invalid from/to terminal | Point and line |
| 37 | Subnetwork tap is not midspan to exactly one line | Point and line |
| 38 | Device with multiple terminals placed midspan | Point and line |
| 39 | Point has an invalid terminal configuration | Point |
| 43 | Edge object references the same feature at both ends | Edge object |
| 44 | Junction objects stacked at the same location | Junction object |
| 46 | Validation found system inconsistencies it could not clean | Any network source |

Update subnetwork errors:

| Error ID | Situation | Feature type |
|---|---|---|
| 24 | Line not valid for the tier's Valid Lines setting | Line |
| 26 | Device not valid for the tier's Valid Devices setting | Point |
| 27 | Invalid parent subnetwork (hierarchical; UN version 1 only) | Point |
| 28 | Disjoint subnetwork in a tier that does not support it | Point |
| 29 | Traversable controllers have inconsistent subnetwork names | Point |
| 30 | Parent controllers have inconsistent parent subnetwork names | Point |
| 33 | Controller's asset group or asset type was modified | Point |
| 40 | Junction not valid for the tier's Valid Junctions setting | Point |
| 41 | Junction object not valid for the tier's Valid Junction Objects setting | Junction object |
| 42 | Edge object not valid for the tier's Valid Edge Objects setting | Edge object |
| 47 | Traversable controllers belong to different tiers | Point, junction object |

*(Descriptions are paraphrased from Esri's "Utility network error IDs" tables
as of Pro 3.7. An ID not listed here is not necessarily invalid: always check
the live table for the target Pro version when diagnosing a specific ID.)*

### Practical/operational notes worth carrying into troubleshooting advice
- **`ErrorCode 0` with no `ErrorMessage` and invisible in Error Inspector** is
  a known pattern for an **"edit dirty area"** (a pending-validation dirty
  area with no actual rule violation) rather than a true error dirty area —
  don't assume `ErrorCode 0` always means "no problem"; it can still block
  operations like `Update Subnetwork` if the area simply hasn't been
  re-validated.
- Community-documented gotcha: on ArcGIS Pro 3.5.1, the **"only generate
  errors" option** in certain validate/error-generation workflows has been
  reported to behave inconsistently on enterprise/file geodatabases but work
  correctly against a **mobile geodatabase** — a known-issue workaround (copy
  the network to a mobile geodatabase) rather than a documented permanent
  behavior; treat as version-specific and verify against current release notes.
- **`SummarizeUNErrors`** (community/Esri support tool, not core Pro) produces
  a fuller diagnostic geodatabase with tables for duplicate/dangling
  associations, out-of-sync `AssociationStatus`, duplicate GlobalIDs,
  duplicate subnetwork controller terminals/names, and topology
  inconsistencies (dirty objects with no source record, elements with no
  source, etc.) — useful to mention when a user describes a messy/legacy
  network that needs a full health audit beyond what Error Inspector surfaces
  interactively.

## Sources

- https://doc.esri.com/en/arcgis-pro/3.7/help/data/utility-network/dirty-areas-in-a-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/view-error-features.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/manage-error-features.html
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/set-association-role.htm
- https://pro.arcgis.com/en/pro-app/3.3/help/data/utility-network/set-an-association-role.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/import-associations.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/export-associations.htm
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/the-structure-network.html
