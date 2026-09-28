# Utility Network — Creation, Configuration, Attributes, Categories & Rules (Deep Reference)
*Source: ArcGIS Pro Help + Tool Reference, "Utility Network" book*

## Create a utility network

**`Create Utility Network`** geoprocessing tool creates the utility network
dataset in a feature dataset (and implicitly creates the structure network
alongside it, since the structure network is shared infrastructure).

**Prerequisites:**
- An existing **feature dataset** to hold the network.
- An existing **m- and z-enabled polygon feature class** to serve as the
  **service territory** feature class — its extent defines the network's spatial
  extent. Must live in the same input feature dataset.
- For enterprise deployments: the utility network **version** created is
  determined by the ArcGIS Pro + ArcGIS Enterprise version pairing at creation
  time. ArcGIS Server must be federated with Portal for ArcGIS.
- The active portal account (enterprise) is recorded as the **portal utility
  network owner** in network properties.

**Supported geodatabases:** enterprise, file, or mobile geodatabase. For
enterprise geodatabases, the underlying DB platform must meet the minimum
ArcGIS Enterprise support level. Supported platforms: **SQL Server, Oracle,
PostgreSQL, SAP HANA**.

**Steps in Pro:** Analysis tab → Geoprocessing group → Tools → search "Create
Utility Network" → run with the feature dataset + service territory inputs.

## Configure a utility network — the full workflow

Per Esri's own "Configure a utility network" topic, manual configuration
(as opposed to using Utility Network Foundations templates or the Migration
Wizard) involves these ordered steps:

1. **Add domain network(s)** — specify tier definition (partitioned/hierarchical)
   and subnetwork controller type (source/sink).
2. **Add subtypes / asset groups & asset types** on each feature class (via
   standard geodatabase subtype + attribute domain mechanisms — `ASSETGROUP` is
   the subtype field, `ASSETTYPE` is domain-constrained beneath it).
3. **Set edge connectivity** for line features (whether/how lines snap and
   connect at non-endpoint vertices — "midspan" connectivity).
4. **Set a terminal configuration** on devices/junction objects that need it.
   For a device/junction object to act as a subnetwork controller in a
   **partitioned traditional domain network**, its terminal configuration needs
   a **minimum of two terminals, with at least one configured as upstream**
   (and correspondingly at least one downstream).
5. **Create rules** — network rules at the asset group/asset type/terminal
   level (see "Network rules" below). Network topology **cannot be enabled**
   until rules exist.
6. **Create and assign network attributes** — see below. Note the built-in
   `LIFECYCLESTATUS` field/attribute pattern: preconfigured with an attribute
   domain for values like *Proposed* / *In service*, usable as a **network
   attribute filter** in a connected trace's traversability expression (e.g.,
   "only trace through in-service features").
7. **Create a Network Attribute**, **Set a network attribute** (assign the
   attribute you defined to specific feature classes/fields).
8. **Create and assign network categories** — tag asset group/asset type
   combinations with system-provided or user-defined categories (see below).

Steps 6–8 can be scripted via geoprocessing tools/arcpy for repeatability
across environments (dev → staging → production schema promotion).

## Network attributes (deep dive)

A network attribute models a characteristic of an asset with more than one
possible state (classic examples: **phase** on electric, **pressure** on
gas/water). Used for two advanced mechanisms:
- **Attribute propagation** — during a trace, calculated values propagate from
  one feature to the next along the traversal path.
- **Attribute substitution** — see below.

### Data types and their supported options
| Attribute Type | In Line | Apportionable | Nullable | Substitution |
|---|---|---|---|---|
| Short | ✅ | ✅ | ✅ | — |
| Long | ✅ | ✅ | ✅ | ✅ (out-of-line only) |
| Double | — | ✅ | ✅ | — |
| Date | — | — | ✅ | — |
| Big integer *(UN version 7+ only)* | — | — | ✅ | — |

- **In Line** — persists the attribute's value packed directly into the network
  topology's internal bitset representation (fast to read during a trace) rather
  than requiring a separate field lookup. Only available for **Short/Long**
  integer types. Requires an **attribute domain** to compute the bit size:
  ```
  bit_size = ceiling(log2(max_domain_coded_value + 1))
  ```
  Nullable In-Line attributes require **one additional bit**.
- **Substitution** — only settable **True** for **Long, out-of-line** network
  attributes. Lets a feature dynamically remap propagated values as a trace
  passes through it (see "Attribute substitution" below) instead of physically
  editing every downstream feature's attribute.
- You can only assign an attribute to a field with a **compatible, matching
  nullability** (non-nullable attribute → non-nullable field only).
- One network attribute can be assigned across **multiple feature
  classes/tables**.

### Attribute substitution mechanics
- Configured via `Add Network Attribute` with `Substitution=True` and a
  `Network Attribute to Substitute` pointing at the target bitset attribute.
- Computationally: substitution maps **each bit** of the target bitset network
  attribute to a new bit — e.g., remapping "phase" so a single device can
  present a different phase value downstream without editing every feature.
- Applied per-tier via the asset type's **attribute substitution** network
  category; the default/standard substitution definition for a tier is set with
  **Set Subnetwork Definition**; can be overridden per-operation via
  ModelBuilder or Python.
- The final propagated (and substituted, if applicable) value writes to the
  attribute's designated **Propagated Attribute field** (e.g., a
  `phaseenergized` field in Esri's worked example).

### Inspecting network attributes via arcpy (read-only reporting pattern)
```python
import arcpy
UN = r"C:\MyProject\databaseConn.sde\mygdb.USER1.Naperville\mygdb.USER1.ElectricNetwork"
d = arcpy.Describe(UN)
for na in d.networkAttributes:
    print(f"ID: {na.Id}")
    print(f"Name: {na.name}")
    print(f"Network Attribute To Substitute: {na.networkAttributeToSubstitute}")
    print(f"Data Type: {na.dataType}")
    print(f"Field Type: {na.fieldType}")
    print(f"Usage Type: {na.usageType}")
    print(f"isEmbedded: {na.isEmbedded}")        # roughly corresponds to "In Line"
    print(f"isApportionable: {na.isApportionable}")
    print(f"isOverridable: {na.isOverridable}")
    print(f"isSubstitution: {na.isSubstitution}")
    print(f"Domain name: {na.domainName}")
```
This `arcpy.Describe(utility_network).networkAttributes` pattern is the
general approach for auditing/documenting an existing network's schema —
useful for building any "explain this network's configuration" tooling.

## Network categories (deep dive)

A network category is a **tag** applied to specific asset group/asset type
combinations (not whole feature classes) — used by **Update Subnetwork,
Export Subnetwork, Verify Circuits, Export Circuits, and Trace** to decide
which features are considered.

- **System-provided categories** exist by default per network type and
  **cannot be deleted** (only optionally assigned):
  - Traditional domain network: **Subnetwork Controller**, **Subnetwork Tap**,
    and others tied to subnetwork/circuit management.
  - Telecom domain network: **Unit Container**, **Unit Identifier**,
    **Splitter**, and others tied to telecom-specific tracing semantics.
- **User-defined categories** (e.g., "Protective," "Disconnect") are created
  with `Add Network Category` and have **no limit** on how many can apply to
  one asset group/asset type combination (e.g., a fuse can be both
  "Disconnect" and "Protective" simultaneously).
- Assignment tool: **`Set Network Category`** — replaces the *entire* category
  set for that asset type (pass an empty/omitted list to unassign all).
  ```python
  import arcpy
  arcpy.un.SetNetworkCategory(
      "Utility Network", "ElectricDistribution",
      "ElectricDistributionDevice", "Fuse", "Air Powered",
      ["Disconnect", "Protective"]
  )
  ```
- **Hard requirement**: network topology must be **disabled** to run
  `Set Network Category` / `Add Network Category`.
- **Subnetwork Controller category gotcha**: only assignable on
  **traditional** domain networks, on the **device feature class or junction
  object table**. In a **partitioned** traditional domain network, the target
  asset type must *already* have a directional terminal configuration with
  **at least one upstream and one downstream terminal** before the category
  can be assigned — this is a common configuration-order trap (people try to
  assign the category before configuring terminals and the option doesn't
  appear in the UI dropdown at all).

## Network rules (deep dive)

Rules are the mechanism that actually constrains **which asset group/asset
type combinations are allowed to connect or associate**, on top of the
broader "feature restrictions" (which define which relationship types are
even structurally possible, e.g., only Device/Junction can have terminals).
**Network topology cannot be enabled without at least one rule present.**
All rules are added/removed with topology **disabled**.

### `Add Rule` — Rule Type options
| Rule Type | From parameter represents | To parameter represents | Notes |
|---|---|---|---|
| **Junction-junction connectivity** | A junction/junction object | Another junction/junction object | Point-to-point connectivity association |
| **Junction-edge connectivity** | Junction/junction object | Line feature | Coincident-geometry connectivity, or connectivity association for edge objects |
| **Edge-junction-edge connectivity** | A line | Another line | Requires a **Via Table** (the junction/junction object the two edges connect through) — 3 classes participate |
| **Containment** | The **container** | The **contents** | From = container, To = contents |
| **Structural attachment** | The **structure** | The **attachment** | From = structure feature/object, To = attached feature/object |

### Key parameters
- `From Table` / `From Asset Group` / `From Asset Type` — for containment and
  structural attachment rules, `From Table` **must** be the container or
  structure network feature.
- `To Table` / `To Asset Group` / `To Asset Type` — the other side of the
  relationship.
- `From Terminal` / `To Terminal` — **required** when the asset type in that
  role has terminals (e.g., specify "high-side" as the From Terminal when
  defining how a transformer connects upstream). These parameters are
  **inactive/disabled** for structural attachment and containment rule types
  (those associations are not terminal-aware, consistent with the structure
  network reference above).
- `Via Table` / `Via Asset Group` / `Via Asset Type` — **only** used for
  **Edge-junction-edge connectivity** rules, since that rule type requires
  three participating classes (edge–junction–edge).

### Practical implication for trace/edit troubleshooting
If a feature "won't connect" to a neighboring feature in the editor, or a
trace unexpectedly stops/skips a feature, the root cause is very often: (a)
a missing `Add Rule` entry for that specific asset-type-to-asset-type pairing,
or (b) a `From Terminal`/`To Terminal` mismatch on a terminal-bearing device.
Both are configuration-time, topology-disabled operations — they cannot be
fixed by editing feature data alone.
