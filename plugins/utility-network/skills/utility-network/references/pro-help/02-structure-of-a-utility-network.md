# Utility Network — Structure of a Utility Network (Deep Reference)
*Source: ArcGIS Pro Help, "Utility Network" book — "Structure of a utility network" section*

This file goes one level deeper than `01-core-concepts-and-vocabulary.md`: exact
field names, geoprocessing tool signatures, and Python samples so Claude can
actually write configuration scripts and explain edge cases, not just describe
concepts.

## The structure network (deep dive)

- Every utility network has **exactly one** structure network, shared across all
  domain networks. It is made of three feature classes, each carrying the same
  `ASSETGROUP` / `ASSETTYPE` key fields as domain network classes:
  - **StructureJunction** (point) — e.g., poles, pads, manholes.
  - **StructureLine** (line) — e.g., trenches, duct runs.
  - **StructureBoundary** (polygon) — e.g., station footprints, easements.
  - (Community sources also mention **StructureJunctionObject**, a nonspatial
    companion table for structure junctions, mirroring the Device/JunctionObject
    split in domain networks — used when a structure needs non-spatial detail,
    e.g. representing a pole's aerial-support-structure hardware separately from
    the pole's point location.)
- Structure features **carry no resource flow** (no water/electricity "flows
  through" a pole) but serve two purposes:
  1. **Containment** — e.g., a vault (structure) contains valves/regulators
     (domain network features), or a substation contains junction boxes, devices,
     wires. This lets a dense cluster of real features be represented/rolled up
     under one container feature.
  2. **Structural attachment** — the association that lets you answer "what's
     attached to this pole?" or, inversely, "which pole is this transformer on?"
- **Why it exists**: it promotes previously "non-networked" data (poles, vaults,
  trenches, casings, cabinets, pits, stations) from the old geometric-network model
  into full network awareness — so it participates in tracing configuration
  (e.g., "Include Structures" option), 3D placement (z-aware), and reporting.

### Structural attachment associations — configuration steps
1. A feature can only be set as a **structure** if its asset group/asset type has
   the **structure association role** assigned. Only `StructureJunction` and
   `StructureJunctionObject` datasets can receive the structure role.
2. Configure **deletion semantics** on the association role — controls what
   happens to attached features when the structure feature is deleted (e.g.,
   require all attachments removed first).
3. Add **structural attachment rules** so specific asset-type pairs (e.g.,
   transformer ↔ pole) are allowed to form the association.
- This association type is **not terminal-aware** (unlike connectivity
  associations, which route through specific terminals).
- Typical attachment patterns: transformer/riser (junction) attached to a pole
  (structure junction); switchgear (assembly) attached to a pad; guy wire
  (structure junction) attached to a pole.
- A structure feature *can* be returned by a trace if the trace's **Include
  Structures** option is enabled, even though no commodity flows through it.

## Domain networks (deep dive)

A domain network groups an industry-specific set of feature classes/objects
representing one large, logically separate part of the system (e.g., "Electric
Distribution" vs. "Electric Transmission" as two domain networks in one electric
utility network).

### Traditional domain network
- The general-purpose model. Feature classes typically include:
  - **Device** (point, with optional terminals)
  - **Line** (line/edge)
  - **Junction** (point, no terminals — simple connectivity node)
  - **Assembly** (point, a container of Devices — e.g., a TransformerBank
    containing individual Transformer devices)
  - **JunctionObject** / **Structure Junction Object** (nonspatial companion
    tables for Device/Junction when non-spatial modeling is needed)
- Standard connectivity rules apply: lines connect to devices/junctions at
  coincident geometry (or via terminals if the device has them).

### Telecom domain network
- Specialized schema for telecom (cabling, fiber). Adds a **divide/combine
  policy** on telecom objects — e.g., a fiber cable "divides" into individual
  strands at a splice point and strands "combine" back into a cable — a pattern
  that doesn't exist in traditional (electric/gas/water) domain networks.
- Configured via the **Set telecom object divide and combine policy** tool
  (listed in the Pro Help TOC; a traditional-network-only concept does not apply
  here).

## Utility feature classification (deep dive)

Every utility network feature class (structure or domain) carries:
- **ASSETGROUP** — required subtype field on the feature class. Represents the
  *major* classification (e.g., "Overhead" vs. "Underground" for a Line class).
  Exception: the `SubnetLine` feature class in a traditional domain network does
  not carry `ASSETGROUP`/`ASSETTYPE`.
- **ASSETTYPE** — *minor* classification nested under the asset group, assigned
  via an attribute domain at the subtype (asset-group) level (e.g., under
  "Overhead," asset types might be "Primary Conductor," "Secondary Conductor").

This two-level scheme (asset group → asset type) is the classification backbone
that nearly every other configuration step keys off of: association roles,
terminal configurations, network categories, and connectivity/association rules
are all assigned **per asset group / asset type**, not per feature class.

## Device terminals (deep dive)

**Concept**: a terminal is a logical connection point on a Device or
JunctionObject, letting you model a feature as having multiple distinct internal
ports rather than one simple coincident-geometry point. Classic example: a
distribution transformer has a high-side terminal (tapped off the primary line)
and a low-side terminal (feeding the secondary line) — internally connected
through the transformer, not through map geometry.

- Terminals are **optional** for devices/junction objects — the default terminal
  configuration for all features is **"Single terminal."**
- Terminals are **required** for a feature to act as a **subnetwork controller**.
- **Directionality**: a terminal configuration is either:
  - **Directional** — flow only permitted one way through the device.
  - **Bidirectional** — flow permitted both ways.
- **Cardinality**: a terminal configuration must specify **2–8 terminals**; each
  terminal name is capped at **32 characters**.
- A terminal configuration is assigned **per asset type** (Device feature class or
  JunctionObject table) — one configuration per asset type, though one
  configuration can be reused across multiple asset types.
- **This assignment is permanent** once network topology has been enabled for the
  first time — cannot be changed afterward. Plan terminal configurations before
  first topology enablement.
- On a **Line** feature that connects to a terminal-bearing device, the line
  carries `FROMTERMINAL`/`TOTERMINAL`-style attribute fields recording which
  terminal each end connects to. Esri explicitly advises against hand-editing
  these fields directly — use the proper editing tools ("Modify terminal
  connections") since the attribute editor doesn't apply the same intelligent
  editing behavior.

### Geoprocessing tools for terminals

**`Add Terminal Configuration`** — creates a new terminal configuration on the
utility network.
| Parameter | Type | Notes |
|---|---|---|
| `in_utility_network` | Utility Network / Utility Network Layer | Target network |
| `name` | String | Terminal configuration name |
| `directionality` | String | `DIRECTIONAL` or `BIDIRECTIONAL` |
| `terminals` | (optional, required if directional) | Name + directional flow per terminal, 2–8 terminals, name ≤ 32 chars |

**`Set Terminal Configuration`** — assigns an existing terminal configuration to
a specific asset type.
| Parameter | Type | Notes |
|---|---|---|
| `in_utility_network` | Utility Network / Utility Network Layer | |
| `domain_network` | String | The (traditional) domain network the asset type belongs to |
| `device_featureclass` | String | Device feature class or JunctionObject table |
| `assetgroup` | String | |
| `assettype` | String | The specific asset type receiving the configuration |
| `terminal_configuration` | String | Name of the configuration to assign |

Python sample pattern (from Esri docs):
```python
import arcpy
arcpy.un.SetTerminalConfiguration(
    "Utility Network", "ElectricDistribution",
    "ElectricDistributionDevice", "Circuit Breaker",
    "<AssetType>", "<TerminalConfigurationName>"
)
```
(Exact positional signature may vary by ArcGIS Pro version — always verify
against the live tool reference page for the target version before shipping a
script.)

## Subnetwork analysis (deep dive)

### Subnetwork controllers
- A subnetwork controller is a **terminal** on a device or junction object,
  designated as the origin (or destination) of a subnetwork.
- To be eligible, a feature/terminal must satisfy **all** of:
  1. It has an available terminal with the correct terminal configuration:
     **directional only** for partitioned tiers; **directional or
     bidirectional** for hierarchical tiers.
  2. Its asset type has been assigned the **Subnetwork Controller network
     category**.
  3. Its asset type is marked **Valid Subnetwork Controller** in the tier's
     subnetwork definition.
  4. The **Subnetwork Name** value is unique across the whole utility network.
- **Source vs. sink** (set per domain network, at the "Add a domain network"
  step — this determines commodity flow direction for that whole domain
  network):
  - **Source-based** domain network (e.g., electric, gas, water distribution —
    resource flows *from* the controller *out to* consumers): only
    **downstream**-designated terminals are valid subnetwork-controller
    terminals for directional terminal configurations.
  - **Sink-based** domain network (e.g., sewer/wastewater, stormwater — resource
    flows *from* consumers *into* the controller, e.g. a treatment plant): only
    **upstream**-designated terminals are valid.
  - Community clarification on a known documentation ambiguity: "subnetwork
    controllers set on terminals designated as downstream behave as sources in a
    source-based network; controllers set on terminals designated as upstream
    behave as sinks in a sink-based network."

### Tiers, ranks, and topology type
- A **tier** is configured with:
  - **Rank** — an integer ordering tiers within a domain network. In a
    **sink-based** network, the convention is that **rank 1 = the tier closest
    to the ultimate destination** (e.g., in a sewer network, the collection
    system feeding the treatment plant is tier 1, sub-areas within it are
    tier 2 — the opposite intuition from a source-based network where rank 1 is
    typically the highest-level "transmission" tier feeding down into
    "distribution").
  - **Topology type** — `Mesh` or `Radial`. Determines structure/traceability
    assumptions for subnetworks in that tier.
- **Partitioned vs. hierarchical, operationally**:
  - **Partitioned**: tiers of different rank are not adjacent; a feature belongs
    to exactly one tier; "upstream/downstream tier rank" is a meaningful
    relationship between ranks (e.g., Transmission rank 1 feeds Distribution
    rank 2).
  - **Hierarchical**: the concept of upstream/downstream tier rank doesn't
    apply the same way — instead, each lower (higher-numbered) tier is a
    **subset** of its parent tier within a tier group (e.g., Isolation (rank 3)
    ⊂ Pressure (rank 2) ⊂ System (rank 1)). A single feature can therefore
    belong to **multiple** tiers simultaneously in a hierarchical network — this
    is precisely why validating a hierarchical network's topology is more
    expensive: every tier with subnetworks must be checked on every edit,
    whereas a partitioned network can often stop once it has explained an edit
    at the first (lowest) tier it checks.
- **Tier groups** aggregate multiple hierarchical tiers to help organize
  subnetworks (`Add tier group` tool).

### Configuration workflow (from "Network management" overview)
1. **Add a domain network** — specify tier definition (hierarchical/partitioned)
   and subnetwork controller type (source/sink) for the whole domain network.
2. **Add tier group** (hierarchical only) — organizes tiers.
3. **Add a tier** — specify rank + topology type (mesh/radial).
4. Use **Add Rule** to create connectivity rules between device terminals and
   other network features.
5. Assign the **Subnetwork Controller** network category to the relevant asset
   group/asset type.
6. Set the **subnetwork definition** for the tier, marking the asset group/type
   combination as a **Valid Subnetwork Controller**.

### The Subnetworks table (system-maintained, read-only)
Every enterprise/single-user utility network maintains a system table recording
one row per subnetwork controller / subnetwork:

| Field | Alias | Description |
|---|---|---|
| `OBJECTID` | Object ID | Row ID |
| `SUBNETWORKCONTROLLERNAME` | Subnetwork controller name | Name of the controlling device/junction object |
| `TIERRANK` | Tier rank | Rank of the owning tier |
| `TIERNAME` | Tier name | Name of the owning tier |
| `TIERTOPOLOGYTYPE` | Tier topology type | Topology type of the tier (mesh or radial) |
| `FEATUREGLOBALID` | Feature global ID | Global ID of the controller's feature |
| `FEATUREASSETGROUP` / `FEATUREASSETTYPE` | Asset group / asset type | Asset group and asset type names of the controller |
| `FEATURESOURCEID` | Feature source ID | Class of the controller |
| `FEATURETERMINALID` | Feature terminal ID | Terminal designated as the subnetwork controller |
| `DOMAINNETWORKNAME` | Domain network name | Domain network that contains the controller |
| `SUBNETWORKNAME` | Subnetwork name | Name of the subnetwork |
| **`ISDIRTY`** | Is dirty | **Whether the subnetwork is clean, dirty or invalid.** The exact stored codes are not given on Esri's table page; read a few rows and compare with the Pro status before filtering on a number |
| `ISDELETED` | Is deleted | Whether the controller terminal still exists (true = removed) |
| `SUBNETLINEGLOBALID` | Subnet line global ID | Global ID of the associated SubnetLine record |
| `LASTUPDATESUBNETWORK` | Last update subnetwork | Last time Update Subnetwork ran for it |
| `LASTACKEXPORTSUBNETWORK` | Last acknowledged export | Last export time when export acknowledgement is enabled |
| `DESCRIPTION`, `NOTES` | Description, notes | Free text about the controller |
| `CREATIONDATE`, `CREATOR`, `LASTUPDATE`, `UPDATEDBY`, `GLOBALID` | Editor tracking | Who and when; row global ID |

*(Field names verified against Esri's "Subnetworks table" page, Sept 2026.)*

This table updates whenever the subnetwork is updated, topology is
enabled/validated, or subnetwork edits occur — it's the authoritative place to
query "what subnetworks exist and are they clean?" rather than inferring it from
feature attributes.

### "Dirty" subnetworks and validation cost (operational nuance worth knowing)
- An edit near/on the network marks the affected subnetwork(s) **dirty**.
- **Validate Network Topology** re-traces to figure out which subnetworks the
  edit actually affected.
  - In a **partitioned** network, validation can stop early: if a single network
    source/sink is found that accounts for the edit at the first tier checked
    (e.g., distribution), it can skip re-analyzing higher tiers (e.g.,
    transmission) — cheaper for small/localized edits.
  - In a **hierarchical** network, because a feature can belong to multiple
    tiers at once, validation must consider *every* tier that has subnetworks —
    inherently more expensive, and cost scales with the number of tiers and
    subnetwork size.
