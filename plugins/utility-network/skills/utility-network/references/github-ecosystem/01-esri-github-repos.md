# Utility Network — Esri GitHub Ecosystem (Deep Reference)
*Source: github.com/Esri (organization repos)*

This catalogs the actual Esri-owned GitHub repositories relevant to the
Utility Network — practical tooling and community resources that sit
alongside the official documentation covered elsewhere in this skill. Use
this file when someone wants a **downloadable tool, add-in, or toolbox**
rather than API documentation.

## `Esri/Utility-Data-Management-Support-Tools` (UDMS toolbox) — the most valuable of these

A actively-maintained (releases through 3.7.1 for ArcGIS Pro 3.7 as of this
writing) **geoprocessing toolbox** purpose-built for UN configuration,
migration, and QA — explicitly used as part of Esri's own **Utility Network
Foundations** solution deployments. Distributed as an `.atbx` file, added to
a Pro project like any other toolbox.

Representative tools by toolset (not exhaustive — the toolbox is large and
actively growing):
| Toolset | Tool | Purpose |
|---|---|---|
| Utility Network | `AddUNSystemTables` | Generates views on the utility network's **system tables** (the same system tables — Subnetworks, dirty areas, etc. — referenced throughout `pro-help/*.md`), for easier querying/reporting. |
| Utility Network | `CreateAssociationLines` | Creates actual line **geometry representing associations** — the toolbox-level answer to visualizing associations, complementary to `synthesizeAssociationGeometries` (`rest-api/02-*.md`) and the JS `UtilityNetworkAssociations` widget. |
| Utility Network | `ExportUtilityNetworkMatrix` | Creates **Excel workbooks** for visualizing/modifying network **rules, categories, association roles, and terminal configurations** — a spreadsheet-driven way to review/bulk-edit configuration that would otherwise mean clicking through many `Add Rule`/`Set Network Category` dialogs one at a time. |
| Asset Package | `CreateNetworkCopyingWorkbook` / `ApplyNetworkCopyingWorkbook` | Copy asset groups/types **between** utility networks (e.g., dev → prod, or between similar utilities) via a reviewable workbook rather than manual reconfiguration. |
| Data Migration | `CreateMigrationWorkspace` | Builds a data model + data-loading workspace for use with a Data Loading tool — supports the same migration workflows described conceptually in the Pro Help "Migrate existing data" material this skill references. |
| Data Migration | `CopyFieldsAndDomainsFromMapping` | Copies fields/domains between feature classes/tables per a mapping worksheet — a common step in schema migration. |
| Contingent Values | `CreateContingentValues`, `CreateContingentValuesWorkbook`, `CreateContingentValueAttributeRules` | Manage geodatabase **contingent values** (constrained attribute combinations) for UN schemas, including converting them into attribute rules. |
| Utility Network | `SummarizeUNErrors` | Already referenced in `pro-help/04-associations-editing-errors.md` — produces a diagnostic geodatabase of duplicate/dangling associations, out-of-sync `AssociationStatus`, duplicate subnetwork controllers, and topology inconsistencies. |

**When to point someone here**: any request involving bulk configuration
review/editing (rules, categories, terminal configs via spreadsheet), data
migration tooling beyond the base Migration Wizard, or a deeper error/health
audit than the interactive Error Inspector provides.

## `Esri/utility-network-properties-extractor`

A **C# ArcGIS Pro Add-in** (open source, Apache-2.0) with one-click buttons
that export **Utility Network, Geodatabase, and Map properties to CSV** —
plus six additional efficiency tools for map/machine setup. Built against
layers from feature services, database connections, or file geodatabases;
buttons enable/disable based on what's actually in the current map.
**When to point someone here**: "I need a quick audit/export of our
network's configuration as CSV for a report or a diff between environments"
— lighter-weight than building custom `arcpy.Describe()` scripts
(`arcpy/01-utility-network-module.md`) for the same goal.

## `Esri/utility-network-modeling`

A community-oriented repository of **diagrams and modeling patterns** for
utility data (currently organized with an "Electric" folder), Apache-2.0
licensed, with an open issue tracker where real-world modeling questions get
raised (e.g., "wind farm to station with step-up transformer," "two
generation turbines with step-up transformer") — useful as a **reference
library of how to model specific real-world equipment configurations** in
the UN data model, beyond the abstract data-model rules covered in
`pro-help/02-*.md` and `pro-help/03-*.md`.

## `Esri/di-utility-network-export-subnetwork-by-rest`

A **no-code ArcGIS Data Interoperability (FME) workspace** that automates
calling the `exportSubnetwork` REST operation
(`rest-api/02-topology-and-subnetwork-management-operations.md`) and converts
the resulting JSON into **Mobile GDB, File GDB, CAD, or Shapefile** output.
Requires Data Interoperability for ArcGIS Pro 3.1+ and an Enterprise UN with
schema **UNv6+**. **When to point someone here**: they want subnetwork
exports automated/scheduled without writing custom Python/REST client code —
this is the no-code path for exactly that.

## `Esri/utility-network-sdk` — deprecated, historical only

Esri's own note on this repo's wiki: **"This repository is no longer in
active use. Most of the utility network documentation and samples have been
integrated in with the ArcGIS Pro SDK."** The one thing that hasn't moved
elsewhere is an **SDK Changes document** tracking API changes release over
release. **Don't point anyone here for current guidance** — redirect to
`pro-sdk/01-csharp-sdk-utility-network-api.md` and the live ArcGIS Pro SDK
wiki instead; this repo is worth knowing about only to avoid confusing it
with something current when it surfaces in search results.

## Confirmed gap: the ArcGIS API for Python (`arcgis` package) has no Utility Network module

`arcgis.network` — the network-related module in Esri's Python GIS package
(distinct from `arcpy`) — is entirely about **Network Analyst / routing**:
`RouteLayer`, `ServiceAreaLayer`, `ClosestFacilityLayer`, `NetworkDataset`,
`ODCostMatrixLayer` — closest facility, vehicle routing, location-allocation,
OD cost matrices, service areas. **This has nothing to do with the utility
network** despite the shared "network" name — Esri's own conference material
on this module explicitly scopes it as *not* covering utility network
analysis. If someone asks for "the utility network module in the ArcGIS
Python API," the accurate answer is: **it doesn't exist** — point them
instead at `arcpy.un` (`arcpy/01-utility-network-module.md`, requires being
inside an ArcGIS Pro Python environment) or direct REST calls
(`rest-api/*.md`) if they need Python outside of Pro (e.g., a plain `arcgis`-package
notebook environment) to talk to a utility network service.

## Broader (non-Esri-org) community resources — mention, don't over-promise

The GitHub topic page `github.com/topics/utility-network` aggregates
third-party projects beyond Esri's own org — e.g., community Angular/TypeScript
UN tracing apps, a Swagger/OpenAPI spec someone wrote for the UN REST API, and
even a QGIS-based utility-network-style extension. These are **not
Esri-maintained**, vary widely in currency and quality, and shouldn't be
presented with the same confidence as the official sources in this skill —
mention the topic page exists if someone specifically wants community
examples, but always lead with the official Esri sources first.

## Practical guidance for Claude

1. For **bulk configuration work** (rules, categories, terminal configs
   across many asset types), suggest the UDMS toolbox's `ExportUtilityNetworkMatrix`
   spreadsheet workflow before suggesting someone script it by hand.
2. For **"give me a CSV/report of our network's setup,"** suggest
   `utility-network-properties-extractor` as a ready-made option before
   writing a custom script.
3. For **modeling a specific unusual piece of equipment**, check whether
   `utility-network-modeling`'s issue tracker/diagrams already cover a
   similar pattern before designing one from scratch.
4. Never suggest `arcgis.network` (ArcGIS API for Python) for anything
   utility-network-related — it's the wrong module entirely, reserved for
   routing/Network Analyst.
5. Flag `Esri/utility-network-sdk` as archived/historical if it comes up in
   search results, and redirect to current sources.
