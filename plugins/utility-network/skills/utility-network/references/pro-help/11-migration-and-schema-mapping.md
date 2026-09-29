# Utility Network — Migration and Schema Mapping (Deep Reference)
*Sources: [Migrate existing data into a utility network](https://doc.esri.com/en/arcgis-pro/latest/help/data/utility-network/migrate-existing-data.html), [Migrate To Utility Network](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/migrate-to-utility-network.html), [Analyze Network Data](https://doc.esri.com/en/arcgis-pro/latest/tool-reference/utility-networks/analyze-network-data.html), [Introducing the Migration Toolset](https://www.esri.com/arcgis-blog/products/utility-network/data-management/introducing-migration-toolset), [Migration Wizard walkthrough](https://www.esri.com/arcgis-blog/products/utility-network/water/utility-network-migration-wizard), [Load data into a utility network](https://learn.arcgis.com/en/projects/load-data-into-a-utility-network/), [Migrate relationship classes](https://learn.arcgis.com/en/projects/migrate-relationship-classes-to-a-utility-network/), Esri technical paper "Utility Network data migration best practices" (March 2019, dated). Last reviewed: 2026-09-29 (Pro 3.5–3.7 docs; tool availability per release not fully verified).*

How source data (a geometric network, plain feature classes, or a legacy GIS model) becomes a utility network, and how to map source schema to UN schema. Read `08-asset-packages-foundations-migration.md` first for asset package and Package Tools basics.

## Contents
- Choose a path
- The two kinds of mapping
- Path A: Migration Wizard / Migrate To Utility Network tool
- Path B: Foundation data loading (mapping workbook workflow)
- Mapping relationship classes to associations
- Pre-load data quality rules
- After the load: analyze, resolve, configure
- Post-migration deployment order
- Gotchas
- How to answer

## Choose a path

Esri's Pro Help lists four ways to get data into a utility network. They trade schema fidelity against effort.

| Path | Best when | You get | You do afterwards |
|---|---|---|---|
| **Utility Network Foundation** (Electric, Water Distribution, Sewer, etc.) | You want Esri's industry model: associations, nonspatial objects, diagrams | A standard schema and rules; your data is mapped into it | Map every source class to the Foundation; clean data |
| **Migration Wizard** (right-click a geometric network → *To Utility Network…*) | You have a geometric network and want to keep your own schema | A UN in a **mobile geodatabase** with your classes and fields | Analyze/resolve errors; configure advanced capabilities |
| **Migrate To Utility Network** geoprocessing tool | Same as wizard, but scripted or repeatable | Equivalent result to the wizard | Same |
| **Manual** (core Pro tools, `03-*.md`) | Highly custom model | Full control | Everything |

Rule of thumb to give users: keep-my-schema → wizard/tool; adopt-industry-model → Foundation; scripted repeatable runs → the tool plus a saved workspace.

The Migration toolset (Analyze Network Data, Apply Error Resolutions, Migrate To Utility Network) is documented as minimizing changes to the existing schema. Esri states it does **not** handle complex schema-mapping rules or associations for you; those are added by hand later.

## The two kinds of mapping

Esri's migration paper separates them, and users often conflate them.

- **Schema mapping**: which source classes and fields participate at all, and which target fields they feed.
- **Object mapping**: how each source feature becomes a UN object. A UN object is a unique combination of **feature class + asset group + asset type**. Every migrated feature must land on a valid combination.

Fields that must be populated by mapping (or accept a default): Asset Group, Asset Type, and status fields such as Lifecycle Status, Normal Status, Construction Status. System-managed fields (for example Is Subnetwork Controller, Tier Name) populate automatically.

## Path A: Migration Wizard / Migrate To Utility Network tool

Requirements (wizard walkthrough): Pro 3.5 or later; source data in geodatabase classes; a **service territory polygon** in the same spatial reference. Create one covering current and future assets; features outside it cannot be created.

Wizard page order: Domain Networks → Geodatabase Options → Utility Network Mapping → Standalone Class Mapping → Migration Summary → Finish.

**Tool parameters** (Migrate To Utility Network; license Standard or Advanced, not Basic):

| Parameter | Meaning |
|---|---|
| Output Folder / Output Name | Where the mobile geodatabase is written (default name `MigrationDatabase`) |
| Service Territory Feature Class | Polygon extent where UN features may exist |
| Utility Network Name / Feature Dataset Name | Defaults `Network` and `UtilityNetwork` |
| Utility Network Mapping | Source classes → target domain network, asset groups/types, controller eligibility |
| Domain Networks | Name, subnetwork controller type (source or sink), tier structure (partitioned or hierarchical) |
| Standalone Classes | Classes that don't participate in the network; copied across |
| Load Data | Migrate data, or schema only |
| Merge Fields | Combine source fields with UN fields |
| Include Related Classes / Include Attachments | Carry relationship classes and attachment tables |
| Utility Network Version | Target dataset version: 5, 6, 7 or current (see `09-*.md`) |

**Outputs**: a mobile geodatabase with the UN dataset, a `controllers.csv` (when controllers were mapped), a group layer with subtype classification, and a **data loading workspace** you can re-run for iterative migrations.

**Limits Esri documents**
- Sources and standalone classes must be geodatabase classes.
- Related classes and attachments need **Global ID** primary keys.
- Many-to-many and attributed relationship classes can't be migrated by this tool.
- Subtype codes outside **1–1023** are renumbered automatically.
- Editor tracking fields map to the default system fields.
- The result is a basic UN: no advanced capabilities are configured.

## Path B: Foundation data loading (mapping workbook workflow)

This is the Esri tutorial flow for loading source data into a Foundation asset package. The tools come from the ArcGIS Solutions **Utility Data Management Support (UDMS) toolbox** and the Solutions Data Loading toolset (see `github-ecosystem/01-esri-github-repos.md`).

1. **Explore the source**: list classes and the fields that distinguish equipment types.
2. **Create Simple Data Mapping**: inventories the source and writes a mapping **Excel workbook**. You choose the *source type* field(s) that distinguish equipment.
3. **Fill in the workbook**: for each source class, set the target UN class, asset group and asset type. Add new asset types where the Foundation lacks one.
4. **Create Migration Workspace**: turns the workbook into detailed field-level instructions, one workbook per feature class. The *Copy Fields* option keeps extra source fields for pilots (audit trail, larger database).
5. **Refine field mappings**: map source attributes to UN fields, marking direct matches.
6. **Lookup tables**: translate mismatched domain values, for example source 0/1 → the UN's lifecycle status codes; check valid codes in the Foundation data dictionary.
7. **Load Data Using Workspace**: point it at the DataReference workbook to fill the asset package.
8. **Asset Package to Geodatabase**: deploy a local test network. **Turn post-processing off on the first deployment** so you can review errors before topology locks in.
9. **Enable Network Topology** in the generate-errors-only mode, which validates all features and keeps the errors without enabling topology.
10. **Summarize Utility Network Errors**: produces the error summary and error-by-type tables; view them on the map to plan source cleanup.

### Field-mapping rules
- Use **database field names**, not aliases (for example `NORMALLYOPEN`).
- A field can take an **expression or a lookup, not both**.
- Source fields you don't map fall back to UN-defined defaults.
- Source data with no subtypes needs manual source-type definitions (step 2).
- After a pilot, review all copied fields and drop the ones you don't need.
- Source layers with no corresponding UN class need manual handling; they won't migrate on their own.

## Mapping relationship classes to associations

Geodatabase relationship classes don't convert themselves. Esri's tutorial uses the UDMS tools:

1. Run Create Simple Data Mapping as usual.
2. In the mapping workbook, add a row mapping the relationship to the **`C_Associations`** table.
3. Create Migration Workspace, then Load Data Using Workspace.
4. Run **Sync the C Tables** to populate the empty domain and asset columns in the association metadata.

Choose the association type by meaning: **containment** (container and contents), **structural attachment** (for example a transformer on a pole), **junction–junction connectivity**, **junction–edge connectivity** (from, to, midspan variants). For connectivity types, many fields need the specific **terminal IDs**.

Gotchas: Sync the C Tables needs **exclusive locks**, so close all open tables first. Warnings appear when not every source feature has a related record; filter with a definition query on populated GlobalID fields. Attributed or many-to-many relationships need the relationship class itself mapped, not just the destination. For CSV or REST loading of associations after the fact, see `04-associations-editing-errors.md` and `rest-api/05-*.md`.

## Pre-load data quality rules

From Esri's 2019 paper (dated, but the rules still match how the topology validates):
- Data is snapped so connected features are coincident.
- Lines don't self-intersect or have complex geometry.
- Features with identical geometry don't intersect at vertices.
- Every feature maps to a valid asset group/type.
- Attributes are complete and relevant.
- Junctions exist where different line types meet.

Performance guidance from the same paper: error counts above about **10,000** seriously hurt performance and function; aim for as close to zero as possible. Enable branch versioning only after topology validation, and don't version the staged database while validating.

## After the load: analyze, resolve, configure

1. **Analyze Network Data** scans a UN and writes an error resolution geodatabase plus a layer file that links errors to source features. *Set Default Resolution Actions* can pre-fill suggested fixes for some error categories. On an enterprise geodatabase, connect as the **database utility network owner**.
2. Edit the resolution actions, then run **Apply Error Resolutions**. Repeat until the count is acceptable.
3. Fix what tools can't in the **source** data and re-run the load. Errors can't be fixed in the migrated database if you plan to re-migrate.
4. Import subnetwork controllers if you have them (the wizard's `controllers.csv` feeds this; **Import Subnetwork Controllers** tool).
5. Add the advanced configuration the migration doesn't create: connectivity rules refinement, network categories and attributes, tiers and subnetwork definitions, associations, diagrams. See `03-*.md`, `05-tracing.md`, `06-*.md`.

## Post-migration deployment order

Local migration and QA → resolve errors → configure rules, categories, attributes, tiers → Enable Topology → Update Subnetworks → enable branch versioning → publish (owner and licensing rules in `10-*.md`) → export an asset package as a baseline (`08-*.md`).

## Gotchas
- Users skip the service territory and hit "feature outside extent" failures.
- Attachments or relationships without Global IDs silently drop out of scope.
- Running post-processing on the first deployment locks topology before errors are reviewed.
- Enable Topology on a full dataset can run for hours; test on a subset first (`06-*.md`).
- Alias names in mapping sheets cause silent unmapped fields.
- Subtype renumbering (codes outside 1–1023) breaks any downstream code that hard-codes source subtype codes.
- The Esri 2019 paper describes older tooling (Data Interoperability workbenches). Treat its tool names as historical, its rules as current.
- Not verified here: exact per-release availability of Migrate To Utility Network, Analyze Network Data and Apply Error Resolutions. Esri's blog places them at Pro 3.5 (standalone for 3.3); the 3.7 tool pages show 3.7. Ask which Pro version the user has.

## How to answer
- "How do I migrate our geometric network?" → ask: keep own schema or adopt a Foundation? Then give the matching path, service territory prerequisite, and the analyze/resolve loop.
- "How do I map our fields/subtypes?" → explain schema vs object mapping, then the mapping workbook steps and field-mapping rules. Mention aliases and expression-vs-lookup.
- "Migration ran but I have thousands of errors" → Analyze Network Data and Apply Error Resolutions; classify by error code via `04-*.md`; fix source data; don't enable topology on everything at once.
- "What happens to our relationship classes?" → `C_Associations` mapping plus Sync the C Tables; warn about many-to-many limits.
- Give exact tool names, and say when a claim is release-dependent. Don't state Foundation-specific asset groups; send users to the Foundation's own docs.
