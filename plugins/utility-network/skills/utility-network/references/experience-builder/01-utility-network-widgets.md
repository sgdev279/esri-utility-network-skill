# Utility Network — ArcGIS Experience Builder Widgets (Deep Reference)
> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Sources: see the Sources section at the end.*

**Audience note**: Experience Builder is Esri's **low-code app builder** —
this is the right reference when someone is assembling a UN app by
configuring widgets in a builder UI rather than writing JS/C#/Python code.
It's built on the same underlying JS Maps SDK widgets covered in the
`js-api/*.md` files, exposed as drag-and-drop, configurable building blocks.

## Utility Network Trace widget

- **Purpose**: run traces (connected, upstream, downstream, subnetwork,
  isolation, etc.) interactively — the low-code equivalent of the JS
  `UtilityNetworkTrace` widget (`js-api/04-trace-results-and-widgets.md`).
- **Requires a connected Map widget**, whose data source must be a **2D web
  map published with a utility network (version 5+)** and **shared named
  trace configurations** (Enterprise 10.9+) — identical prerequisites to the
  JS widget, since it's the same underlying capability.
- **User requirement (release-dependent; corrected 2026-10-27)**: the
  **11.1** widget page says users must sign in with an Enterprise account
  holding the "ArcGIS Utility Network" user type extension, and Esri's
  developer guide scopes that to services published at **11.1 or earlier**.
  The **12.1** widget page lists no licensing requirement, consistent with
  Esri's Enterprise 12.1 and Pro 3.7 pages (query and trace need no
  extension; create, publish and edit need Advanced Editing). For a network
  served at 11.1 or earlier, confirm the end-user licence; on 12.1 do not
  require it for trace-only viewers.
- Also: running traces on **map services** is unsupported (use the feature
  service web map); knowledge graph layers are unsupported; results are not
  reliable through dirty areas, so topology must be validated for the traced
  area.
- **Setup path** (same as any UN app): create/configure the utility network
  and publish an Enterprise feature service → in ArcGIS Pro, add named trace
  configurations → share them through a web map → build the Experience
  Builder app against that web map.
- **Example app design requirements** (from Esri's own docs) — useful
  phrasing when helping someone scope a request:
  - Isolation trace to find which valves must close to stop a water outage
    and identify affected customers.
  - Upstream trace to search for contamination sources in stormwater.
  - Connected trace in a **branch version** to verify newly edited features
    connect as expected (before posting to DEFAULT).
  - Subnetwork trace to validate a circuit/zone is defined/edited correctly.

## Branch Version Management widget (deprecated) and Branch Version Editing widget

- **Deprecation (Esri blog, checked 2026-10-27)**: the Branch Version
  Management widget is deprecated at Enterprise 12.1 (final release that
  includes it) and retired at Enterprise 12.2 / Developer Edition 1.22; it
  cannot be added to new apps. In ArcGIS Online it is retired with the
  October 2026 update with no replacement. For Enterprise, use the **Branch
  Version Editing** widget: it needs a Map widget and a web map data source
  with Version Management enabled, and supports switch, create, delete,
  modify, change owner, save/discard, undo/redo, reconcile and post (Post is
  enabled only after a reconcile). End users may need the Advanced Editing
  extension depending on operation. Plan new apps on it; the rest of this
  section describes the older widget for existing apps.

- **Purpose**: end-user version management directly in a web app — switch
  the active version, view/edit version info, and (if configured) create,
  assign, or delete versions. This is the low-code front end for the
  `VersionManagementServer` concepts in
  `rest-api/04-version-management-validation-feature-service.md`.
- Requires **at least one data source registered as a versioned
  feature/map service**, hosted in ArcGIS Enterprise (Esri).
- **Cross-widget effect**: switching versions in this widget changes what
  **other widgets bound to the same service** display — a single version
  switch ripples across the whole app, not just the widget itself. Version
  changes made here are also visible in **other clients**, including
  ArcGIS Pro, when the widget is configured to allow creating new versions.
- **Constraint**: supports `SubtypeGroupLayer` as a data source, but **you
  cannot connect individual `SubtypeSublayer`s directly** — bind at the
  group-layer level (see `js-api/02-layers-and-rendering.md` for the
  underlying layer type).
- **Constraint**: don't point two Branch Version Management widgets at the
  **same** service in one app — unsupported/conflicting configuration.
- Recommended pattern: place it behind a **Widget Controller** (so it opens
  on demand via a button) when using the Advanced arrangement style, rather
  than always-visible.
- Create/delete versions are optional per data source and the widget's
  version management options appear only in the Advanced arrangement style;
  options shown depend on the user's privileges and the version's access
  permission.
- Known limitation (community-confirmed, not in Esri's widget page; verify
  against the Esri docs for your version):
  version switches made by a *custom* widget on a **map service** data
  source have not reliably been picked up/displayed by the Branch Version
  widget — use a **feature service** (`FeatureServer`) rather than a map
  service as the data source to avoid this.

## Validate Topology and Associations in Experience Builder

At the time these docs were written, Esri Community responses describe
validating network topology and managing associations in Experience Builder
as requiring **more manual assembly** than the Trace and Branch Version
widgets — e.g., getting the correct extent to pass to a validation call has
been a recurring point of user confusion, since (per Esri support guidance)
**the validation service requires an extent covering the actual dirty area**,
and Experience Builder doesn't automatically supply this the way ArcGIS Pro's
UI does — the app builder may need an additional widget or custom logic to
capture/pass the right extent. If a request specifically needs
associations-management or topology-validation UI in Experience Builder,
**verify current widget availability and behavior against the live Experience
Builder widget catalog for the target version** rather than assuming full
parity with the JS `UtilityNetworkAssociations`/`UtilityNetworkValidateTopology`
widgets — this area has evolved across releases and may have changed since
this reference was written.

## Practical guidance for Claude

1. Experience Builder UN widgets have the **same underlying preconditions**
   as their JS SDK counterparts (topology enabled + validated, named trace
   configs shared, correct license) — always restate these when helping
   configure a low-code UN app, since the builder UI doesn't always surface
   *why* a widget isn't working.
2. For version-related low-code work, default to the **Branch Version
   Management widget**, and proactively mention the same-service /
   subtype-sublayer / map-service limitations above rather than letting
   someone discover them by trial and error.
3. For validate-topology or associations management specifically in
   Experience Builder, be upfront that this is a less mature area than
   tracing and versioning, and suggest checking the current widget catalog
   rather than assuming a specific ready-made widget exists with full JS-widget
   parity.

## Sources

- https://doc.arcgis.com/en/experience-builder/11.1/configure-widgets/utility-network-trace-widget.htm (licensing statement, 11.1)
- https://doc.arcgis.com/en/experience-builder/12.1/configure-widgets/utility-network-trace-widget.htm (12.1, no licensing statement)
- https://developers.arcgis.com/experience-builder/guide/utility-network-trace-widget/
- https://doc.arcgis.com/en/experience-builder/12.1/configure-widgets/branch-version-management-widget.htm
- https://doc.arcgis.com/en/experience-builder/12.1/configure-widgets/branch-version-editing-widget.htm
- https://www.esri.com/arcgis-blog/products/experience-builder/announcements/deprecation-notice-branch-version-management-widget-in-arcgis-experience-builder
- https://doc.esri.com/en/arcgis-enterprise/latest/administer/utility-network-services.html
