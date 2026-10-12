# Utility Network — arcpy / Python Scripting (Deep Reference)
*Source: doc.esri.com/en/arcgis-pro/latest/arcpy/ (get-started + arcpy.un module docs,
UtilityNetwork class reference)*

> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

**Audience note**: this is for **Python scripting inside ArcGIS Pro**
(standalone scripts, the Python window, model builder script tools) — a
different audience from the Pro SDK C# Add-in developer
(`pro-sdk/01-csharp-sdk-utility-network-api.md`) and from REST/JS web
developers. If someone says "I want to automate this with a Python script in
Pro," this is the right frame, not the C# SDK.

## Where the Utility Network fits into arcpy's module structure

Per Esri's own ArcPy module organization, **Utility Network (`arcpy.un`)**
is listed as **both**:
1. A **toolbox module** — "The Utility Network toolbox contains tools to
   create, configure, and work with utility networks" — this is the
   namespace (`arcpy.un.<ToolName>`) for every geoprocessing tool already
   documented throughout the Pro Help reference files in this skill:
   `Create Utility Network`, `Add Rule`, `Set Terminal Configuration`,
   `Set Network Category`, `Add Network Attribute`, `Import/Export
   Associations`, `Import/Export Subnetwork Controllers`, `Set Association
   Role`, `Update Subnetwork`, `Export Subnetwork`, `Trace`,
   `Validate Network Topology`, and so on — **all of these are called via
   `arcpy.un.<ToolName>` in a Python script** (tool name with spaces removed,
   e.g. `arcpy.un.ValidateNetworkTopology`), exactly as shown in the Python code
   samples already embedded in `pro-help/02-*.md` through `pro-help/07-*.md`.
   The network-diagram tools are a **separate Network Diagram toolbox**
   (`arcpy.nd.*`), not part of `arcpy.un`.

   **There is no GP tool named "Set a Subnetwork Controller" / "Set Subnetwork
   Controller".** "Set a subnetwork controller" is a Pro help topic (done in the
   UI's Modify Subnetwork Controller pane). In Python you set or remove a
   controller with the `arcpy.un.UtilityNetwork` class methods
   `EnableSubnetworkController(...)` / `DisableSubnetworkController(...)`
   (below), or bulk-load them with the `Import Subnetwork Controllers` GP tool
   (`arcpy.un.ImportSubnetworkControllers`). `Export Subnetwork Controllers`
   (`arcpy.un.ExportSubnetworkControllers`) is the matching export.
2. A **module with its own `UtilityNetwork` class** — a lower-level,
   non-GP-tool API for **managing subnetwork controllers and associations
   programmatically** without going through the higher-level GP tool
   wrappers. This is the class documented in the "arcpy vs. C# SDK"
   disambiguation in `pro-sdk/01-csharp-sdk-utility-network-api.md`.

**License requirement** (per the Pro Help FAQ): utility network work needs an
**ArcGIS Pro Standard or Advanced** license. For an **enterprise deployment**,
creating, publishing, or editing also needs the portal account to hold the
**ArcGIS Advanced Editing user type extension**; query and trace do not.
From Enterprise 11.2 the old separate Utility Network, Trace Network and Parcel
Fabric extensions are consolidated into Advanced Editing; older material that
names a separate "Utility Network extension" (through 11.1) is out of date.

## The `arcpy.un.UtilityNetwork` class (lower-level, non-GP API)

```python
import arcpy
un = arcpy.un.UtilityNetwork(utilityNetworkPath)  # path to the utility network dataset/service
```

Full method list (confirmed against the Pro 3.7 class reference):

| Method | Purpose | Returns |
|---|---|---|
| `AddConnectivityAssociation(association_type, from_table, from_global_id, from_terminal_name, to_table, to_global_id, to_terminal_name, percent_along)` | Connectivity between noncoincident features | OBJECTID of new association |
| `AddContainmentAssociation(container_table, container_global_id, content_table, content_global_id, is_content_visible)` | Containment | — |
| `AddStructuralAttachmentAssociation(structure_table, structure_global_id, attachment_table, attachment_global_id)` | Structural attachment | OBJECTID |
| `DeleteConnectivityAssociation(association_type, association_global_id)` | Remove connectivity | — |
| `DeleteContainmentAssociation(association_global_id)` | Remove containment | — |
| `DeleteStructualAttachmentAssociation(association_global_id)` | Remove attachment — **note Esri's documented spelling "Structual"; call it exactly as spelled** | — |
| `EnableSubnetworkController(table, global_id, terminal_name, subnetwork_controller_name, subnetwork_name, tier_name, description, notes)` | Make a device/junction terminal a subnetwork controller | OBJECTID of new Subnetworks row |
| `DisableSubnetworkController(table, global_id, terminal_name)` | Remove controller role | — |
| `HasValidNetworkTopology()` | Is topology enabled | bool |

Details on the most-used ones:
- **`AddConnectivityAssociation(association_type, from_table, from_global_id, from_terminal_name, to_table, to_global_id, to_terminal_name, percent_along)`**
  — creates a connectivity association between two **noncoincident**
  features (i.e., features not touching geometrically, so an explicit
  association is the only way to model the connection). `association_type`
  is an **integer code**: `1` = Junction-Junction Connectivity, `4` =
  Junction-Edge From Connectivity, `5` = Junction-Edge Midspan Connectivity,
  `6` = Junction-Edge To Connectivity. Requires that supporting network
  rules already exist for the asset types involved (same rule-first
  requirement as everywhere else — `pro-help/03-*.md`).
- **`HasValidNetworkTopology()`** — returns `True` when the network's topology
  is enabled. (This method exists on the **arcpy** class only; the Pro SDK C#
  `UtilityNetwork` class has no member of that name — use `GetState()` there.)
  Whether topology must be enabled before creating associations or modifying
  subnetwork controllers: Verify against the Esri docs for your version.
- **`EnableSubnetworkController(...)`** — makes a device/junction terminal a
  subnetwork controller and returns the OBJECTID of the new row in the
  Subnetworks table; run `arcpy.un.UpdateSubnetwork` afterwards to update
  subnetwork names on the member features. Run it inside an edit session on the
  network.

**Note on association-type encodings**: these arcpy codes are the **same
integers** stored in the associations table's `ASSOCIATIONTYPE` field and
written via REST `applyEdits` (`1` junction-junction, `2` containment, `3`
structural attachment, `4`/`5`/`6` junction-edge from/midspan/to). The
**different** encodings are the text names in the Import/Export Associations
CSV (`Junction Junction Connectivity`, …) and the camelCase names in REST
`associations/query` (`junctionJunctionConnectivity`, …). Use
`scripts/association_types.py` to convert between them.

## The `arcpy.Describe()` pattern — schema introspection

Already demonstrated in `pro-help/03-creation-configuration-attributes-categories-rules.md`
for network attributes; the same `Describe` object exposes the **broader**
utility network schema for any read-only "explain this network's
configuration" scripting need:
```python
import arcpy
d = arcpy.Describe(utilityNetworkPath)
print(d.proVersion, d.schemaGeneration)          # schemaGeneration = UN dataset version (e.g. 8)
for dn in d.domainNetworks:
    print(dn.domainNetworkName, dn.isStructureNetwork, dn.tierDefinition,
          dn.subnetworkControllerType, dn.subnetworkTableName)
for a in d.networkAttributes:
    print(a.name, a.dataType, a.usageType, a.bitPosition, a.bitSize)
for c in d.categories:
    print("category", c.name)
for tc in d.terminalConfigurations:
    print(tc.terminalConfigurationName, tc.traversabilityModel,
          [(t.terminalName, t.isUpstreamTerminal) for t in tc.terminals])
```
Property names verified against the Pro 3.7 arcpy "Utility Network properties",
"Domain Network properties", "Terminal Configuration properties", "Network
attribute properties" and "Tier properties" pages (Oct 2026). Other top-level
properties: `associationSource`, `createDirtyAreaForAnyAttributeUpdate`,
`minimalDirtyAreaSize`, `serviceTerritoryFeatureClassName`,
`systemJunctionSource`, `systemJunctionObjectSource`, `creationTime`.
**Tiers are available from the domain network object** (traditional domain
networks only): `dn.tiers` (each tier exposes `name`, `rank`, `tierID`,
`tierGroupName`, `tierTopology`, `subnetworkFieldName`,
`supportDisjointSubnetwork`, `validSubnetworkControllers`,
`updateSubnetworkTraceConfiguration`, ...) and `dn.tierGroups` (hierarchical tier
definitions only). If a property is missing on an older Pro release, run `dir()`
on the object rather than guessing. The same data is available without arcpy
from REST `FeatureServer/queryDataElements`.
This `Describe`-based introspection is the natural starting point for any
"write a script that documents/audits our utility network's configuration"
request — pair it with the field-level detail already captured in the
`pro-help/*.md` files for what each returned property actually means.

## Practical guidance for Claude

1. **Default to GP tool syntax (`arcpy.un.<ToolName>(...)`)** for anything
   that has a direct Pro UI equivalent (creating rules, setting terminal
   configs, importing associations, tracing, validating topology) — these
   are already fully documented with parameter tables across the
   `pro-help/*.md` files; just wrap them in `arcpy.<toolset>.<ToolName>(...)`
   syntax.
2. **Reach for the `arcpy.un.UtilityNetwork` class** specifically when the
   request is about **programmatic association management or subnetwork
   controller checks** that doesn't map cleanly to a single GP tool call, or
   when working with **noncoincident connectivity associations** specifically
   (`AddConnectivityAssociation`'s explicit purpose).
3. When a UN script fails mysteriously, check licensing early: Pro
   **Standard or Advanced** is required, and editing an enterprise network
   needs the portal account to hold the **Advanced Editing user type
   extension** (`pro-help/10-*.md`).
4. When a script needs to create associations, remind the user (as in the
   REST appendix, `rest-api/05-*.md`) that **rules must already exist** for
   the relevant asset type pairs — this is true across every API surface,
   not just REST.

## Sources

- https://pro.arcgis.com/en/pro-app/3.6/arcpy/utility-network/utilitynetwork.htm (arcpy.un.UtilityNetwork class: methods and association_type codes)
- https://pro.arcgis.com/en/pro-app/tool-reference/utility-networks/flisting.htm (Utility Network toolbox tool list)
- https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/set-a-subnetwork-controller.html ("Set a subnetwork controller" help topic; uses the `EnableSubnetworkController` method)
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/import-subnetwork-controllers.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/export-subnetwork-controllers.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/set-network-category.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/trace.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/utility-network-properties.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/domain-networks.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/tiers.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/terminal-configurations.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/network-attributes-utility-network.htm
- https://pro.arcgis.com/en/pro-app/3.6/arcpy/functions/categories.htm
- https://pro.arcgis.com/en/pro-app/3.6/tool-reference/utility-networks/import-associations.htm
- https://pro.arcgis.com/en/pro-app/tool-reference/network-diagram/an-overview-of-the-network-diagram-toolbox.htm (separate Network Diagram toolbox)
