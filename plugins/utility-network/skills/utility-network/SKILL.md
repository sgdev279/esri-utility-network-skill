---
name: utility-network
description: Expert reference for the Esri ArcGIS Utility Network (UN) - data model, Foundations, asset packages, migration and schema mapping, configuration, tracing, subnetworks, dirty areas and errors, versioning, publishing, licensing, dataset versions and upgrades, and every developer surface (REST UtilityNetworkServer, JavaScript SDK, Pro SDK C#, arcpy.un, Experience Builder). Use it whenever someone mentions the utility network or UN in an ArcGIS context, or uses its vocabulary without naming it - subnetwork controllers, Update Subnetwork, domain networks, tiers, dirty areas, Error Inspector, network topology, associations, Apply Asset Package, Migration Wizard, mapping source data to asset groups and types, trace configurations, isolation or upstream traces. Not for Trace Networks, geometric networks (except migrating from one), Network Analyst, or non-Esri meanings of utility network or UN.
---

# Esri ArcGIS Utility Network — Expert Reference

A cross-referenced knowledge base for the Utility Network (UN): concepts,
administration and every API surface. The
reference files hold concrete specifics — field names, tool and REST
signatures, JSON schemas, version limits, known failure modes — so answers can
be exact rather than generic.

## Workflow for every UN request

1. **Classify the request** into one of the answer types in *Output formats*
   below (how-to, troubleshooting, code, concept,
   cross-surface translation).
2. **Pin down the environment.** These facts change the answer; use what the
   person gave, and ask only for what is missing *and* decisive:
   - deployment: **enterprise** (services, branch versioning) or
     **single-user** (file/mobile geodatabase, Pro only, no REST/JS)
   - surface: Pro UI, arcpy, Pro SDK (C#), REST, JS, Experience Builder
   - versions: **UN dataset version** (4–8), **Pro**, **Enterprise**
     (`pro-help/09-*.md` has the matrix)
   - industry/domain network (electric, gas, water, telecom, …)
3. **Load only the reference files that match** (index below). Most real
   questions touch two: e.g. a REST trace question needs
   `pro-help/05-tracing.md` for semantics and `rest-api/01` + `08` for the
   JSON.
4. **Run a script instead of reasoning by hand** when one fits (see
   *Scripts*): decoding a dirty-area Status, converting association-type
   codes, checking a trace request.
5. **Answer in the matching output format**, then flag anything
   version-sensitive or unverified (see *Accuracy rules*).

## Critical disambiguation (check before writing any code)

| The person is building… | Right API | Reference |
|---|---|---|
| A Pro Add-in (desktop extension) | Pro SDK, C# — `ArcGIS.Core.Data.UtilityNetwork` | `pro-sdk/01-*.md` |
| A Python script / GP automation in Pro | `arcpy.un` (GP tools + `arcpy.un.UtilityNetwork` class) | `arcpy/01-*.md` |
| A web app | ArcGIS Maps SDK for JavaScript — `@arcgis/core/networks/*` | `js-api/*.md` |
| A low-code web app | Experience Builder UN widgets | `experience-builder/01-*.md` |
| An integration / backend | REST `UtilityNetworkServer` + `FeatureServer` | `rest-api/*.md` |
| A native/mobile app (.NET MAUI, Qt, Kotlin, Swift) | ArcGIS Maps SDK for Native Apps — **not covered here**; say so and note they don't support UN dataset v8 | — |

Also distinguish:
- `UtilityNetworkServer` vs `TraceNetworkServer` (Trace Networks are a
  different, simpler dataset — out of scope).
- The ArcGIS API for Python (`arcgis` package) has **no** UN module;
  `arcgis.network` is Network Analyst.
- The JS SDK has **no** network diagram support; diagrams in a web app mean
  raw `NetworkDiagramServer` REST + custom rendering.

## Output formats

Pick the one that matches the request. Keep headings short; drop a section
only when it truly doesn't apply. Chat answers stay in markdown; long
deliverables (a runbook, a design doc) follow the same skeleton.

### 1. How-to / configuration
```
**Context assumed:** <deployment, surface, versions — one line>
**Before you start:** <prerequisites that cause failures if skipped:
  topology state, owner connection, DEFAULT vs named version, license>
**Steps:** numbered; each with the exact tool/button/endpoint and key parameters
**Verify:** how to confirm it worked (query, trace, Error Inspector, etc.)
**Watch out for:** 1–3 known gotchas from the references
```

### 2. Troubleshooting / "why is X happening"
```
**Most likely cause:** one sentence
**Why:** the mechanism, tied to the UN concept involved
**Check, in order:** numbered diagnostics, cheapest first, each with what
  result confirms or rules it out
**Fix:** concrete steps for the confirmed cause
**If that's not it:** the next most likely causes
**Version note:** if the behaviour is release- or patch-specific
```

### 3. Code (REST / JS / C# / arcpy)
```
**What this does:** one or two lines, naming the API surface and version floor
**Requirements:** license/user type, topology state, version (DEFAULT/named),
  minimum Pro/Enterprise/JS SDK version
**Code:** complete and runnable; real parameter names from the references;
  placeholders in <ANGLE_BRACKETS>; comments only where a choice matters
**Expected result:** response shape or what appears in the app
**Adapting it:** how to change trace type, version, filters, etc.
```
For REST trace requests, run `scripts/build_trace_request.py --check` on the
JSON before presenting it.

### 4. Concept explanation
Plain-language definition → how it behaves in the network (a small example
from the person's domain) → how it shows up in the surface they use (Pro
pane, REST field, JS property) → common misconception. A diagram helps for
tiers, subnetworks, associations and trace flow.

### 5. Cross-surface translation ("works in Pro, how in REST/JS/C#?")
A mapping table (Pro setting → REST field → JS property → C# member) for the
parts involved, then the code in the target surface (format 3).

## Reference index

**Concepts & administration (ArcGIS Pro Help)**
| File | Read when |
|---|---|
| `pro-help/01-core-concepts-and-vocabulary.md` | Orienting: deployments, structure/domain networks, tiers, asset group/type, associations, topology |
| `pro-help/02-structure-of-a-utility-network.md` | Terminals, subnetwork controllers, tier ranks, Subnetworks table |
| `pro-help/03-creation-configuration-attributes-categories-rules.md` | Manual creation, configure workflow, network attributes (bit packing), categories, rules |
| `pro-help/04-associations-editing-errors.md` | Associations, import/export CSV, dirty areas, Status bitmask, Error Inspector, error IDs |
| `pro-help/05-tracing.md` | Trace types, traversability, filters, outputs, choosing a trace type |
| `pro-help/06-administration-subnetworks-topology-versioning.md` | Subnetwork life cycle, update/export, topology admin, branch version conflicts, patch-level issues |
| `pro-help/07-network-diagrams.md` | Diagram templates and rules |
| `pro-help/08-asset-packages-foundations-migration.md` | Foundations, Utility Network Package Tools, Apply Asset Package failures, migration |
| `pro-help/09-dataset-versions-compatibility-upgrade.md` | UN dataset versions 4–8, Pro/Enterprise compatibility, Upgrade Dataset |
| `pro-help/10-publishing-ownership-licensing.md` | Licensing, database vs portal owner, publishing prerequisites, permission errors |
| `pro-help/11-migration-and-schema-mapping.md` | Migrating geometric networks or plain feature classes to a UN, source-to-target schema mapping, Migrate To Utility Network, Foundation data loading, post-migration errors |

**REST API**
| File | Read when |
|---|---|
| `rest-api/01-utility-network-server-and-trace.md` | Trace request/response, `traceLocations`, `resultTypes`, named trace configurations |
| `rest-api/02-topology-and-subnetwork-management-operations.md` | Resource tree, enable/validate topology, update/export subnetwork, associations/locations query, controllers |
| `rest-api/03-network-diagram-service.md` | `NetworkDiagramServer` operations |
| `rest-api/04-version-management-validation-feature-service.md` | Branch versioning REST, `ValidationServer`, feature service UN extensions |
| `rest-api/05-feature-service-associations-appendix.md` | `systemLayers` discovery, writing associations via `applyEdits` |
| `rest-api/06-asynchronous-operations-job-status.md` | `async=true` + `statusUrl` polling |
| `rest-api/07-circuits-and-unit-identifiers-telecom.md` | Telecom circuits and unit identifiers |
| `rest-api/08-trace-configuration-full-schema.md` | Barriers, filters, functions, propagators, output filters, nearest neighbour JSON |

**Developer SDKs and apps**
| File | Read when |
|---|---|
| `js-api/01-javascript-sdk-utility-network.md` | Loading a UN in JS, `TraceParameters`, named configs |
| `js-api/02-layers-and-rendering.md` | `SubtypeGroupLayer` symbology |
| `js-api/03-network-class-loading-and-definition.md` | `UtilityNetwork` class, `dataElement`, diagrams gap |
| `js-api/04-trace-results-and-widgets.md` | `TraceResult`, `UtilityNetworkTrace` widget |
| `js-api/05-editing-associations-validation.md` | Association edits, `validateTopology`, validate widget |
| `js-api/06-functional-api-web-components-calcite.md` | Functional `trace()`, web components, Calcite, arcgis-rest-js gap |
| `pro-sdk/01-csharp-sdk-utility-network-api.md` | Pro Add-in C#: `UtilityNetwork`, `Job<T>`, associations, tracing |
| `arcpy/01-utility-network-module.md` | `arcpy.un` tools, `UtilityNetwork` class (all methods), `Describe` properties |
| `experience-builder/01-utility-network-widgets.md` | Low-code trace and version widgets |
| `github-ecosystem/01-esri-github-repos.md` | UDMS toolbox, properties extractor, other Esri repos |

## Scripts

| Script | Use for |
|---|---|
| `scripts/decode_dirty_status.py 10 17` | Explain dirty-area Status values (edits vs errors) and the next action |
| `scripts/association_types.py 5` | Convert association types between integer codes, CSV names, REST names, GP keywords |
| `scripts/build_trace_request.py --check req.json` | Catch silent-failure mistakes in a REST trace request; or build one from flags |

## Accuracy rules

- **Licensing** has one source of truth: `pro-help/10-*.md` (Pro Standard or
  Advanced; Advanced Editing user type extension for create/publish/edit in
  enterprise; none needed for query/trace).
- **Association types** have one integer encoding (shared by arcpy, the
  associations table and REST `applyEdits`) and two text encodings (CSV
  names and REST `associations/query` names); use
  `scripts/association_types.py` rather than recalling codes.
- **Version-sensitive facts** (parameters added in a given release, patch
  issues) must be stated with their version or date. Files
  carry a *Last reviewed* date where they were re-verified (Sept 2026:
  licensing, arcpy class, compatibility/upgrade, asset packages, REST
  update/export/validate/associations, trace configuration schema).
- **Don't invent names.** If a property, parameter or tool isn't in the
  references and you can't check it, say it needs verifying against the Esri
  docs for their version rather than guessing. When web search is available
  and the person is about to ship something, check the current Esri page.
- **Single-user vs enterprise**: never offer REST or JS answers for
  a file or mobile geodatabase network.
- **Safety**: when an answer involves enable/disable topology, Upgrade
  Dataset, Apply Asset Package, export with acknowledgement, or bulk
  association edits with validation bypassed, name the side effects (locks,
  deleted errors, downstream systems) and recommend a backup or maintenance
  window.
