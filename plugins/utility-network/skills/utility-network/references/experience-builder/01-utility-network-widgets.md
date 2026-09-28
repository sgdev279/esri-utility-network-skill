# Utility Network — ArcGIS Experience Builder Widgets (Deep Reference)
*Source: doc.arcgis.com/en/experience-builder/ (configure-widgets section)*

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
- **User requirement**: must be **signed in with an ArcGIS Enterprise
  account licensed for the ArcGIS Utility Network user type extension** —
  this is an end-**user** license requirement, not just a publisher-side
  one; a common deployment gotcha when an app is shared broadly but not
  every viewer has the right license type.
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

## Branch Version Management widget

- **Purpose**: end-user version management directly in a web app — switch
  the active version, view/edit version info, and (if configured) create,
  assign, or delete versions. This is the low-code front end for the
  `VersionManagementServer` concepts in
  `rest-api/04-version-management-validation-feature-service.md`.
- Requires **at least one data source registered as a versioned
  feature/map service**.
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
- Known limitation (community-confirmed, check current release notes):
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
