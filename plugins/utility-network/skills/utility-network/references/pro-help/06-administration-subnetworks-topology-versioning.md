# Utility Network — Administration: Subnetworks, Topology & Versioning (Deep Reference)
> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)
*Source: ArcGIS Pro Help, "Utility Network" book — administration/subnetwork-management topics*

## Subnetwork life cycle

A subnetwork moves through a defined sequence of states and operations. This
is the operational backbone behind "why won't Update Subnetwork run" support
questions.

### States
- **Clean** — set after a successful update; Subnetworks table, SubnetLine and system diagrams match topology. Update Subnetwork is meant for Dirty subnetworks; Esri does not state what it does to a Clean one (Verify against the Esri docs for your version).
- **Dirty** — created or changed since the last update; eligible for
  `Update Subnetwork`.
- **Invalid** — the update operation ran and found **validate consistency
  failures or subnetwork errors**; the update failed and the subnetwork is
  flagged invalid and is ignored by later updates until it is Dirty again (needs ArcGIS Enterprise 11.1+ in enterprise). Recovery path: **address the underlying errors → validate
  network topology (which re-marks it dirty) → save edits → retry update.**

### Core operations (in typical sequence)
1. **Add Controller** — assign a controller name (unique within the tier) for a (new or
   existing) subnetwork, in the Modify Subnetwork Controller pane or via Import Subnetwork Controllers.
2. **Set a subnetwork controller** (see `02-structure-of-a-utility-network.md`
   for eligibility requirements) → the controller name is stored in the Subnetworks table and SubnetLine; Esri does not say in so many words that this step "creates" the subnetwork.
3. **Validate Network Topology** — marks affected controllers/subnetworks
   dirty (or surfaces errors).
4. **Update Subnetwork** — runs a trace from the controller(s), updates the
   subnetwork name on traversed features, generates `SubnetLine`
   aggregated-geometry records, and marks controllers **Clean** on success (**Invalid** on failure).
5. **Export Subnetwork** — runs a trace and exports the subnetwork to a JSON file
   for external systems; the subnetwork must be **Clean**. The tool must be connected to the **default version**
   (Esri tool page; the topology-actions table lists default-only for both modes). With **Set export acknowledged**
   it updates `LASTACKEXPORTSUBNETWORK` and **removes deleted controllers** from the Subnetworks table; this
   mode also requires the connected portal account to be the **portal utility network owner**.
   Flag this any time someone wants to export from a branch other than DEFAULT.
6. **Delete Controller** — remove the controller setting (the row is flagged deleted and stays until an acknowledged export); the subnetwork
   itself is deleted only when all its controllers are removed, then validate, update, and export with acknowledgment on DEFAULT.

### Subnetwork definition (per-tier configuration, set at admin time)
| Component | Description |
|---|---|
| **Support for disjoint subnetworks** | Whether same-named subnetworks can be non-traversable to each other. Only configurable for **partitioned** tiers (`Set Subnetwork Definition`); **hierarchical** tiers always have this set true. |
| **Aggregated lines for SubnetLine** | A subset of the tier's Valid Lines to aggregate together into `SubnetLine` geometry during Update Subnetwork — controls how much of the subnetwork's line geometry gets rolled up into the summarized subnetwork representation vs. kept as individual line records. |
| *(additional documented components)* | Valid Devices / Valid Device Subnetwork Controllers / Valid Lines / Valid Junction Objects / Valid Junction Object Subnetwork Controllers / Valid Edge Objects (junction/edge object lists need UN version 4+) — see `03-creation-configuration-attributes-categories-rules.md` cross-reference: these are the same asset-type allow-lists referenced when setting up subnetwork controllers. |

## Network topology (admin-level)

- Network topology must be **enabled** before trace or diagram operations are
  trusted, and is built on **branch versioning**.
- Only the utility network owner can manage topology states; Enable runs on the Default version only (Disable can run on Default or a user version); Validate processes only features in dirty areas and is not automatic after each edit; disabling is recommended for large loads.
- **Enable / Disable / Validate Network Topology** are the three core
  lifecycle operations (also exposed as REST operations on `UtilityNetworkServer`
  — see `rest-api/02-topology-and-subnetwork-management-operations.md`).
- Because topology tracks temporal state via editor tracking + branch
  versioning, analytic operations (trace, diagram) can be run either **at the
  current moment** or at a **specified historical moment** — but the topology
  must be enabled *at that moment* for the operation to be trusted.

## Branch versioning & conflicts (vocabulary)

- **Conflicts** occur when the **same feature, or topologically related
  features**, are edited in two different versions. If one version's edits are
  posted to DEFAULT and the other version is then reconciled, conflicts
  surface for any feature modified in both — because it's ambiguous which
  edit should "win." A person or automated process must resolve each conflict
  in favor of the **edit (current) version**, the **target (DEFAULT) version** or the common ancestor. Conflicts start resolved in favor of the edit version, and unreviewed ones are auto-resolved that way on the next reconcile/post. Esri lists update-update, update-delete, delete-update, topologically-related-feature, and (telecom) containment-hierarchy conflicts.
  - Practical implication: utility network edits are *not* just simple
    attribute-level conflicts like ordinary versioned editing — because
    features are topologically related (connectivity, associations,
    subnetwork membership), a conflict on one feature can have knock-on
    implications for subnetwork validity that a plain reconcile/post doesn't
    automatically resolve.

## Known operational issues (from Esri patch notes — treat as version-specific, not universal; not re-verified, Verify against the Esri docs for your version)

Worth knowing as realistic "why is this happening" material, though always
flag these as tied to specific ArcGIS Server/Enterprise patch levels rather
than universal behavior:
- Historically reported: `Enable Network Topology` and `Validate Network
  Topology` can **stall or fail on very large dirty-area counts** (documented
  cases in the multi-million dirty-area range) — a scale consideration worth
  raising for large migrations or bulk-load scenarios before enabling topology
  for the first time on a freshly loaded network.
- `Update Subnetwork` has historically had **performance issues tied to
  `ValidatingSubnetworkTraceResult`** and has been optimized across patches
  to **reduce database/server network traffic** — if someone reports Update
  Subnetwork being slow, patch level is a legitimate thing to check.
- `Export Subnetwork` has required the **version owner** (or a public-access
  version) to run successfully in some releases — if export fails with an
  "Operation is only allowed by the owner of the version" error, check version
  ownership/access before assuming a data problem.
- Branch versions have, in some releases, appeared under a user's name as
  **private** even when not knowingly created/assigned by that user — a
  reported quirk of UN branch versioning display, not necessarily a
  permissions bug.

These are exactly the kind of "known gotcha" facts that make a support-style
answer feel authoritative — but because they're patch/version specific, any
answer citing them should say "this was true as of ArcGIS Server X.Y patch Z;
check current release notes" rather than stating it as a permanent fact.

## Sources
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-life-cycle.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/update-subnetworks.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/subnetwork-controller.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/about-network-topology.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/geodatabases/overview/manage-branch-version-conflicts.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/export-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/update-subnetwork.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/set-subnetwork-definition.html
