# Utility Network — Core Concepts & Vocabulary
*Source: ArcGIS Pro Help, "Utility Network" book (doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/). Licensing section re-verified 2026-09-28 against the FAQ.*

## What is a utility network?

A utility network is the core ArcGIS data model for managing utility and telecom
infrastructure — electric, gas, water, stormwater, wastewater, and telecom. It models
real-world components (wires, pipes, valves, devices, circuits, zones) and encodes
real-world behavior (connectivity, containment, structural attachment) into those
features so the network can be queried, traced, and analyzed the way the physical
system actually behaves.

Four core capabilities:
- **Model** every type of utility equipment as features/objects, with rules governing
  valid connections.
- **Discover connectivity** — how features and objects relate to each other.
- **Trace** how a resource (gas, water, electricity) flows through the network.
- **Analyze** how real-world events (storms, outages, equipment failure) affect the
  network.

## Deployment models

| Model | Description | Where you work |
|---|---|---|
| **Enterprise deployment** | Services-based architecture on ArcGIS Enterprise. Supports large-scale, multiuser editing/tracing/analysis via web maps, apps, mobile, and Pro. This is the model that exposes the REST services (UtilityNetworkServer, NetworkDiagramServer, etc.) | ArcGIS Pro, web apps, mobile apps |
| **Single-user deployment** | Full analytic capability hosted in a file or mobile geodatabase, no services layer. | ArcGIS Pro desktop only |

This distinction matters a lot for the skill: REST API and most JS API workflows
assume an **enterprise deployment** (published feature service backed by
UtilityNetworkServer). Single-user deployments are Pro-only and never exposed via
REST/JS.

## Structural building blocks (vocabulary)

- **Structure network** — one per utility network. Models structural/support features
  (poles, vaults, etc.) shared across all domain networks.
- **Domain network** — the first organizing unit for utility-specific data. A
  domain network is an industry-specific collection of feature classes/objects
  representing one large logical part of the system (e.g., "Electric Distribution,"
  "Gas Transmission"). A utility network has one or more domain networks, plus the
  single structure network.
  - **Traditional domain network** — general-purpose; features are typically points/lines/junctions with standard connectivity rules.
  - **Telecom domain network** — specialized for telecom, with divide/combine policies for cabling.
- **Tier** — organizes a domain network into a hierarchy. Two tier definitions:
  - **Partitioned tier definition** — for sequential networks (electrical, telecom).
    Features belong to exactly one tier; independent tiers.
  - **Hierarchical tier definition** — tiers nest, and always support disjoint subnetworks.
- **Subnetwork** — a subset of a tier rooted at one or more subnetwork controllers.
- **Disjoint subnetwork** — when subnetwork controllers sharing the same subnetwork
  name cannot be traversed to one another, i.e. the subnetwork is split into
  physically separate pieces that share a name. Configured on the tier's subnetwork
  definition; hierarchical tiers always support this, partitioned tiers support it
  only if explicitly enabled (`Set Subnetwork Definition` GP tool → *Support Disjoint
  Subnetworks*).
- **Asset group** — major classification of a utility network feature class. Stored
  in the required `ASSETGROUP` field on (almost) every UN class; doubles as the
  subtype field.
- **Asset type** — minor classification, nested under asset group. Stored in
  `ASSETTYPE`, assigned via attribute domains at the subtype (asset group) level.
  Asset group + asset type together give a two-level classification scheme for every
  feature.
- **Associations** — non-geometric relationships between features: connectivity
  (implicit, from geometric coincidence + rules), containment (one feature
  physically contains another), and structural attachment (one feature is attached
  to/supported by another, e.g. a transformer on a pole).
- **Network topology** — the enabled state that lets the network compute
  connectivity/associations and support tracing and network diagram generation.
  Built on top of branch versioning; must be enabled (and current) before trace or
  diagram operations are trusted. Supports archiving/editor tracking, so analytic
  operations can run at the current moment or at a specified moment in the past.

## Quick tour — where things live in Pro

When a utility network is added to a map:
- The **Utility Network tab** (contextual) appears, exposing network topology
  workflows, association workflows, and the most-used tracing/subnetwork-management
  tools.
- The **Contents** pane shows the utility network layer; its context menu exposes
  **Network Properties** and **dirty areas**.
- The **Catalog** pane shows the underlying utility network dataset.

## Editing & licensing basics (from FAQ)

- Both single-user and enterprise deployments require **ArcGIS Desktop Standard or
  Advanced** license at minimum.
- Enterprise deployment additionally requires the portal to be licensed with the
  **ArcGIS Advanced Editing / Utility Network user type extension** to create,
  publish, and edit a utility network. **Query and trace operations do not require**
  that user type extension — this matters when scoping what a given app/user needs.
- Three paths to create/configure a network:
  1. **Utility Network Foundations** — predefined industry templates (recommended
     starting point for most orgs).
  2. **Utility Network Migration Wizard + Migration toolset** — for migrating an
     existing geometric network or other feature classes into a utility network.
  3. Manual creation with core ArcGIS Pro tools is also possible but is the most
     labor-intensive path (see `03-creation-configuration-attributes-categories-rules.md`).
  Foundations and migration workflows are covered in
  `08-asset-packages-foundations-migration.md`.
- Enterprise deployments are designed for **service-based editing**; direct database
  connections are reserved for the initial configuration/QA phase before network
  topology is enabled and published.

## Where to go next
- Structure network, domain networks, terminals, tiers, subnetworks → `02-*.md`
- Creating and configuring (attributes, categories, rules) → `03-*.md`
- Associations, dirty areas, errors → `04-*.md`
- Tracing → `05-*.md`
- Subnetwork/topology administration, versioning → `06-*.md`
- Network diagrams → `07-*.md`
- Asset packages, Foundations, migration → `08-*.md`
- Dataset versions, compatibility, upgrades → `09-*.md`
- Publishing, ownership, licensing, permissions → `10-*.md`
