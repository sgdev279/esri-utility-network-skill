# Utility Network — Associations, Editing & Error Handling (Deep Reference)
*Source: ArcGIS Pro Help + Tool Reference, "Utility Network" book*

## Association roles (Container / Structure)

Before a feature can *participate* as a container or a structure in an
association, its asset type must be assigned the corresponding **association
role** — this is separate from (and a prerequisite to) the network rules that
say *which* asset types are allowed to associate with it.

- Only feature classes/tables that satisfy the utility network's **feature
  restrictions** can receive the Container or Structure role (e.g., only
  `StructureJunction`/`StructureJunctionObject` can be Structure; certain
  domain-network classes with polygon/container semantics can be Container —
  e.g., a `StructureBoundary` substation polygon).
- Assigned with **`Set Association Role`**. Requires **network topology
  disabled**. Key parameters:
  - `deletion_semantics` — controls what happens to content/attachment
    features when the container/structure is deleted:
    | Value | Behavior |
    |---|---|
    | **CASCADE** | Deletes all content/attachment features along with the container/structure. |
    | **SET_TO_NONE** | Content/attachment features are kept but the association is removed. |
    | **RESTRICTED** | Deletion is blocked with an error until content/attachment features are removed first. |
  - `view_scale` — the map scale at which **containment mode** (the
    special editing view for looking inside a container) is auto-entered.
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
- `association_type` accepts `ALL` or a specific type keyword (e.g.
  `JUNCTION_JUNCTION_CONNECTIVITY`).
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

- **Subnetwork errors (bit 32)** are discovered by Update Subnetwork (Error IDs
  24 and 26 to 30 in Esri's table). When one occurs, the subnetwork status of
  every controller in the Subnetworks table for that subnetwork becomes
  **Invalid** until it updates cleanly. Fix the cause, then Update Subnetwork
  again.
- **Object errors (bit 16)** come from junction or edge objects with invalid
  containment or structural attachment rules (Error IDs 17, 18 and 41 to 44).
  Fix by editing attributes or adding the rule.
- A 9 is an edit plus a feature error; after validation it becomes 8 if the
  error persists (then it needs a feature edit, not another validate) or
  disappears if the edit fixed it.

### Error Inspector pane
- Opened from the **Contents** pane (expand the utility network layer → the
  **Dirty Areas** sublayer is there).
- Defaults to a **Map Extent** filter (only shows errors in the current view)
  — a common troubleshooting gotcha is having errors elsewhere in the network
  that don't appear until you disable this filter.
- Key attributes surfaced: **Network Source ID** (which class the error
  feature belongs to) and **Feature GUID** (the specific feature) — used to
  locate/select the actual feature in error.

### Sample error IDs (enable/validate network topology)
| Error ID | Situation | Typical fix |
|---|---|---|
| 0 | Wrong data type on a field | Correct the field's data type |
| 1 | Feature geometry is empty | Locate via Network Source ID + Feature GUID; delete and re-create the feature |
*(Esri's full table continues with many more IDs — treat this as a starting
pattern, not an exhaustive list; always check the live "Utility network error
IDs" table for the target Pro version when diagnosing a specific error ID.)*

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
