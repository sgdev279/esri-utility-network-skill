# Utility Network — Publishing, Ownership, Licensing & Permissions (Deep Reference)
*Sources: ArcGIS Pro Help FAQ, "Utility network dataset administration",
"Network topology actions" and "Publish and consume services with a utility
network"; ArcGIS Enterprise 12.1 "Utility Network services" and "Introduction
to licensing user type extensions".*

> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

Covers who is allowed to do what, and what must be true before a utility
network can be published and used as services. Many "access denied",
"operation only allowed by the owner", and "tool is greyed out" questions
trace back to this file.

## Licensing (single source of truth for this skill)

| Need | Requirement |
|---|---|
| Any UN work in ArcGIS Pro (single-user or enterprise) | ArcGIS Pro **Standard or Advanced** license level (the UN geoprocessing tools are not available at Basic) |
| Enterprise: **create, publish, or edit** a utility network | Portal account with the **ArcGIS Advanced Editing user type extension** |
| Enterprise: **query and trace** | No user type extension needed |
| Validate Network Topology, Update Subnetwork, Export Subnetwork, Enable/Disable Network Topology (tools and the matching services) | Advanced Editing user type extension on the portal account (Esri lists it in each tool's licensing notes) |
| REST named trace configuration management | Verify against the Esri docs for your version |

**Advanced Editing in Enterprise 12.1:** it covers utility network, trace
network, parcel fabric, topology, attribute rules and branch versioning when
accessed through feature layers that reference a registered data store. It is
**included with the Professional and Professional Plus user types** and is an
**add-on for Mobile Worker, Contributor and Creator**. Through Enterprise
11.1 the separate "ArcGIS Utility Network", "Trace Network" and "Parcel Fabric"
user type extensions existed; they were consolidated into Advanced Editing
(11.2 and later). Error 003049 ("account logged into portal is not licensed
with the <value> user type extension") is the symptom: have the portal
administrator review the user's type or add-on license. Older material that
mentions a separate Utility Network extension applies to 11.1 and earlier.
Scoping tip: read-only web apps and dashboards that only trace or query can
run under users without the extension.

## The two owners

| Owner | What it is | Can it change? |
|---|---|---|
| **Database utility network owner** | The database user that created the network; part of the dataset's fully qualified name | No — only by recreating the data |
| **Portal utility network owner** | The portal account signed in to Pro when the network was created; stored as metadata | Yes — **Update Portal Dataset Owner** tool, run while signed in as the current portal owner **or a portal administrator**, through a database connection as the data owner on a branch versioned workspace; it needs an exclusive lock, so close services/connections first. The new owner must have the same user type and privileges as the original owner. Afterwards, also change item ownership of the related portal items (map, image and feature layers). |

### Operations that need an owner

Esri's "Network topology actions" table has an owner-connection column. Many
operations need **both**: a database connection as the database owner *and* the
portal account signed in as the portal owner.

- **Both owners:** Create Utility Network; Enable / Disable Network Topology
  (incl. generate-errors variant); Repair Network Topology; Verify Network
  Topology; Analyze Network Data; Apply Error Resolutions; Update Is Connected;
  Import / Export Rules; most configuration changes (Add Domain Network, Add
  Tier, Add Network Attribute, Set Network Attribute, Add Rule, Delete Rule,
  Set Association Role, Set Network Category, Set Edge Connectivity, terminal
  configuration actions, and so on)
- **Database owner connection:** Import / Export Associations; Import / Export
  Subnetwork Controllers; Update Portal Dataset Owner
- **Portal owner:** Export Subnetwork when run with acknowledgments
- **Upgrade Dataset** → database owner connection (branch versioning) **and**
  portal owner sign-in (Esri "Utility network dataset administration")
- **Apply Asset Package** → verify against the Esri docs for your version
  (see `08-asset-packages-foundations-migration.md`)
- **No owner connection needed:** Load data, Validate Network Topology, Rebuild
  Network Topology, Update Subnetwork, Export Subnetwork (without
  acknowledgments), Verify Circuits, and ordinary feature/attribute editing
- **Network diagram templates:** adding, altering or deleting diagram templates,
  Import Diagram Template Definitions and similar template/maintenance tasks
  require the network owner; creating, storing and updating diagrams does not
  (Esri "Network diagram management tasks")
- Changing the portal owner → current portal owner or a portal administrator

Symptom mapping:
- "Tool disabled/greyed out" or "must be the owner" → check which owner the
  operation needs and how the user is connected (database user *and* portal
  sign-in).
- "Operation is only allowed by the owner of the version" → that's
  **version** ownership (branch versions are private/protected/public),
  not network ownership. See `06-*.md`.

## Publishing prerequisites (enterprise deployment)

1. Data in an **enterprise geodatabase**. Set the database connection's
   versioning type to **Branch** before adding the network to a map (Esri: you
   cannot publish a utility network otherwise) and **register the feature
   dataset as branch versioned** (Feature Dataset Properties → Versioning),
   which also registers the junction and edge object tables. (Some configuration
   steps, e.g. Enable Network Topology with *Only generate errors*, need a
   nonversioned state; that is before publishing.)
2. Publisher signed in to the portal as the **portal utility network owner**
   (account licensed with **Advanced Editing**), with the layer coming from a
   connection as the **database utility network owner**.
3. Add the utility network to a new map and answer **Yes** to add all
   participating classes. Preserve layer IDs (Map Properties → allow unique
   numeric IDs). The map must not contain definition queries or hidden fields on
   the utility network layer, or subtype group layers.
4. **Share → Web Layer → Publish Web Layer**: Data and Layer Type **Map
   Image**, with **Feature** checked under *Reference registered data*;
   confirm **Version Management** is enabled under Capabilities (needs Feature
   and a branch versioned dataset). A feature service that includes the utility
   network layer automatically includes the **Utility Network** and **Network
   Diagram** services. Together the services are: Utility Network (trace,
   subnetworks, tiers, validate topology), Network Diagram, Feature
   (edits/queries), Version Management (branch versions).
5. The database must be registered with ArcGIS Server as a data store
   (by-reference publishing; Analyze offers *Register Data Source with
   Server*).
6. After publishing, add the web layer to a map; enable topology (if not
   already) and validate. For offline use, enable editing and sync and include
   the Service territory class.

After publishing, edits go through services. Direct database connections are
for the initial configuration/QA phase only.

## Roles checklist for common requests

| Request | Who / what they need |
|---|---|
| Web app user who traces | Portal user with view access to the layer; no extension |
| Field or web editor | Advanced Editing user type extension + edit privileges on the layer; named or default version access |
| Validate topology from a web app/script | Extension + edit access to the version being validated |
| Update subnetwork on DEFAULT | Extension; DEFAULT must be writable by that user (protected DEFAULT → owner/admin) |
| Admin tasks (enable topology, upgrade, apply asset package) | The database + portal owners, in a maintenance window (confirm the owner column in Esri's "Network topology actions" for each tool) |

## How to answer

- Name the exact license/role and the specific owner an operation needs;
  don't say "you need admin rights".
- For permission errors, identify which of the three is failing: license
  (user type extension), network ownership, or version ownership.

## Sources

- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/faq.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/utility-network-dataset-administration.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/network-topology-actions.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/data-management/update-portal-dataset-owner.html
- https://doc.esri.com/en/arcgis-pro/3.7/help/data/utility-network/publishing-and-consuming-services-with-the-utility-network.html
- https://doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/network-diagram-management-tasks.html
- https://doc.esri.com/en/arcgis-enterprise/latest/plan/license-user-type-extensions.html
- https://doc.esri.com/en/arcgis-pro/latest/tool-reference/tool-errors-and-warnings/001001-010000/tool-errors-and-warnings-03026-03050-003049.html
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/enable-network-topology.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/disable-network-topology.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/validate-network-topology.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/update-subnetwork.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/export-subnetwork.htm
- https://pdi.scinet.usda.gov/image/help/en/12.1/administer/utility-network-services.html (third-party mirror of the Esri Enterprise 12.1 "Utility Network services" help)
