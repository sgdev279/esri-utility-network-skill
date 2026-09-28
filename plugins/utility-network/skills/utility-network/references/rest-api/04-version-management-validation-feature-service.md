# Utility Network — REST API: Version Management, Validation & Feature Service Extensions (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

## The complete picture: six services work together for one utility network

Per Esri's own "Overview of Utility Network Services" architecture page, a
single published utility network is actually backed by **six** coordinated
REST endpoints, not just `UtilityNetworkServer`:

```
https://<root>/<serviceName>/MapServer
https://<root>/<serviceName>/FeatureServer              (extended for UN concepts)
https://<root>/<serviceName>/UtilityNetworkServer       (trace, validate, subnetworks)
https://<root>/<serviceName>/NetworkDiagramServer       (diagrams)
https://<root>/<serviceName>/VersionManagementServer    (branch versioning)
https://<root>/<serviceName>/ValidationServer           (topology + attribute rule evaluation)
```
**The ArcGIS Utility Network Management extension is required** to use the
utility network and network diagram services at all. Any time someone's UN
service is missing expected capabilities, checking whether this extension is
licensed on the portal/server is a reasonable first troubleshooting step.

## `VersionManagementServer` — branch versioning operations

This is the service that makes **branch versioning** (the mechanism topology,
editing, and conflicts all sit on top of — see
`pro-help/06-administration-subnetworks-topology-versioning.md`) actually
usable over REST/apps rather than only via direct database connection.

### Service-level operations
`create`, `delete`, `purgeLock`, `versionInfos`.

### Per-version resource operations (`.../VersionManagementServer/versions/<versionName>/...`)
`alter`, `conflicts`, `differences`, `inspectConflicts`, `post`, `reconcile`,
`restoreRows`. **Most of these require the ArcGIS Advanced Editing user type
extension** (specifically: Delete, Alter, Purge Lock, Conflicts,
Differences, Inspect Conflicts, Reconcile, Post, Restore Rows).

### `reconcile`
- Detects differences between the edit version and a **target version**
  (typically the parent or DEFAULT) and flags them as **conflicts**.
- **Hard requirement**: you must be the **only user editing the version**,
  and must remain so through to save/post.
- You need **full permissions** on every feature class modified in the
  version.
- Supported **synchronously and asynchronously**.
- `withPost=true` — reconcile and post in one call; obtains a **shared
  version lock on the target** for the duration so the target can't shift
  underneath the operation.

### Capability flags worth checking before scripting a versioning workflow
| Capability | What it unlocks |
|---|---|
| `supportsConflictDetectionByAttribute` | Reconcile's `conflictDetection` parameter can define conflicts **by attribute** rather than only by whole-object — services without this flag treat any co-edited object as a full conflict, even if the edited attributes didn't actually overlap. |
| `supportsPartialPost` | `post` accepts a `rows` parameter to post only a **subset** of the version's edits to DEFAULT — the "partial post" pattern (confirmed in Esri's own Python API guide: `version.post(rows=<subset>)`). |
| `supportsDifferencesWithMoment` | `differences` accepts `fromMoment` to compare against a specific historical moment instead of only "since branch point." |
| `supportsDifferencesWithLayers` | `differences` accepts a `layers` filter instead of always returning differences for every layer. |
| `supportsAsyncReconcile` | Reconcile can run asynchronously (useful for large edit sets that would otherwise block a client). |

### Practical Python pattern (via the ArcGIS API for Python, same concepts as raw REST)
```python
from arcgis.gis import GIS
gis = GIS(profile="your_enterprise_profile")
# feature_layer_collection.versions -> VersionManager

target_version_name = "ARCGIS_PYTHON.workplan_a123"
with version_manager.get(target_version_name, "read") as version:
    version.mode = "edit"
    result = version.reconcile(
        end_with_conflict=True,
        conflict_detection="byAttribute",
        with_post=False,
        future=False,
    )
    if result.get("success"):
        did_post = version.post(rows=None, future=False)  # rows=None -> full post
```

### Legacy versioning endpoints — do not confuse these with `VersionManagementServer`
`createVersion`, `reconcileVersion`, `deleteVersion` on **`LRServer`** (the
older Linear Referencing / ArcMap-publishing versioning endpoints) are
**deprecated starting at ArcGIS Server 11.1/11.2**, exist only for legacy
ArcMap-published services, and require the **ArcGIS Location Referencing**
license. **`VersionManagementServer` is the correct, current service for any
ArcGIS Pro–published, branch-versioned utility network.** If a search result
or old tutorial shows `reconcileVersion` syntax, it's almost certainly this
legacy path, not the one to use for a UN built in Pro.

## `ValidationServer` — topology & attribute rule evaluation

`https://<root>/<serviceName>/ValidationServer`
- **Operations**: `Evaluate`, `Update Errors`, `Write Errors` (and, per some
  version docs, `Write Errors With Sketch Geometries`). Introduced at 10.7.
- Available when the **Validation capability** is enabled at publish time.
- Shares service-instance settings (SOC count, timeouts) with the published
  feature service — it's implemented as a **server object extension (SOE)**
  tied to that feature service, not an independently scaled service.

### `evaluate` operation
- Evaluates rules against a selection set, a geographic extent, or features
  modified in a version, and **persists error features** into
  `GDB_Validation*Errors` tables.
- `evaluationType` (array) accepts: `"topologyRules"`, `"validationRules"`,
  `"calculationRules"`.
- **License note**: requires ArcGIS Advanced Editing user type extension (for
  Enterprise 11.2+); an **ArcGIS Data Reviewer** server extension license is
  additionally required if the datasets use Data Reviewer-based validation
  attribute rules.
- **Known quirk**: the JSON response for `evaluationType: ["topologyRules"]`
  will **always return `errorsIdentified: 0`** — don't rely on that field to
  detect topology errors; check the actual error tables/dirty areas instead
  (this is a documented API surprise, not a sign evaluation silently failed).

### `capabilities` (introduced 11.1)
```json
{
  "name": "Validation Server",
  "type": "Map Server Extension",
  "capabilities": {
    "supportsTopologyValidation": true,
    "supportsTopologyErrorModification": true
  }
}
```
- `supportsTopologyValidation` — whether `evaluate` supports
  `evaluationType: topologyRules` at all.
- `supportsTopologyErrorModification` — whether `Update Errors` supports the
  `errorType`/`ruleType` combination needed to update **topology** error
  features specifically (vs. only attribute-rule validation errors).
- Later versions add `supportsWriteErrors` and
  `supportsWriteErrorsWithSketchGeometries` (writing error rows directly,
  optionally with sketch geometry pairs, rather than only reading/updating
  errors the system already found).

### `Update Errors`
- Updates attributes of error features already persisted in
  `GDB_Validation*Errors` tables (works for **both** `validationRules` and,
  since 10.8.1, `topologyRules` via the `ruleType` property).
- `returnEdits: true` returns full before/after feature detail per layer —
  same `exceededTransferLimit` pagination-guard pattern used elsewhere in the
  REST API; invalidate any client-side cache when that flag comes back true.

## Feature Service extensions for utility networks

The plain `FeatureServer` resource for a UN-backed service gains UN-aware
behavior:
- **New layer types for Utility Networks and annotation layers**, publishable
  from ArcGIS Pro since 2.1 (i.e., a feature service can directly expose
  utility-network-flavored layers, not just plain feature layers).
- **`validationSystemLayers`** property (10.7+) — appears when the service's
  datasets have validation/batch-calculation rules; lists the `layerIds` that
  expose validation error features — the REST-visible link between a plain
  feature service and the `ValidationServer` error tables described above.
- **Topology layers** (10.8.1+) — composite layers with **no capabilities of
  their own** that reference sub-layers describing **error features** and
  **dirty areas**. Used together with `ValidationServer` in clients like
  ArcGIS Pro to support topology validation and error correction UIs — this
  is the REST-level counterpart of the Pro Help "Dirty Areas sublayer /
  Error Inspector" material in `pro-help/04-associations-editing-errors.md`.
- The feature service is explicitly described by Esri as extended to
  "recognize utility network concepts such as associations and dirty area
  management" — i.e., don't assume `FeatureServer` for a UN-backed service
  behaves identically to a plain, non-UN feature service; check for these
  extra properties/layer types before writing generic feature-service client
  code against it.

## Practical guidance
- When someone's UN app needs **collaborative multi-user editing with
  conflict resolution**, that's `VersionManagementServer`, not anything on
  `UtilityNetworkServer` directly — `UtilityNetworkServer` assumes a version
  already exists and is usable; it doesn't create/reconcile/post versions
  itself.
- When someone asks "how do I check my utility network for rule violations
  from code" (as opposed to interactively in Pro), the answer is the
  `evaluate` operation on `ValidationServer` — remember the `topologyRules`
  `errorsIdentified: 0` quirk so they don't misread a successful evaluation
  as "no errors found."
- Both services require licensing beyond the base Utility Network Management
  extension in some cases (Advanced Editing user type, and possibly Data
  Reviewer) — flag license requirements rather than assuming an operation is
  available just because the service resource exists.
