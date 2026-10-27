# Utility Network — REST API: Working with the Utility Network via the Feature Service (Appendix, Deep Reference)
> Last reviewed: 2026-10-27 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Source: developers.arcgis.com/rest/services-reference/enterprise/appendix-working-with-the-feature-server-utility-network-server*

This is the practical "how do I actually write an association from my app"
recipe — the feature-service-level counterpart to the Pro GP tools
(`ImportAssociations`/`Set Association Role`) and the C# SDK's
`AddAssociation`. **This is also exactly what the JS API's `applyEdits`
machinery goes through under the hood**, so it's directly relevant to JS app
development, not just raw REST scripting.

## Finding the systemLayers (associations, dirty areas, etc.)

Utility-network-related system tables (associations, dirty areas, and
others) are exposed as ordinary **layers within the `FeatureServer`
resource**, just with special roles. To find them:
1. Fetch `.../FeatureServer?f=pjson` and locate **`utilityNetworkLayerId`** in
   the JSON.
2. Fetch `.../FeatureServer/<utilityNetworkLayerId>?f=pjson` — read its
   **`systemLayers`** object, which holds the related system layer IDs
   (e.g. `associationsTableId`; Esri's example value is 500001).
3. Use those layer IDs with ordinary feature service operations (`query`,
   `applyEdits`) to read/write that system table directly.

This is the mechanism behind "how do I query dirty areas or associations
from a plain feature-service client" — you don't need a UN-specific SDK
class for read access; you need the right **layer ID** and ordinary feature
service `query`/`applyEdits` calls.

## Writing associations directly via `applyEdits`

`POST .../FeatureServer/applyEdits` (run against the **associations
systemLayer** via its layer id, e.g. `.../FeatureServer/500001/applyEdits` in Esri's example; Esri's examples target the **DEFAULT** version with `useGlobalIds=true`; branch-version/session behaviour is not described on that page - verify against the Esri docs for your version).

### Association attribute schema (as written via applyEdits)
Per the Esri appendix, the add syntax uses camelCase keys and a **string**
`associationType`:
```json
{
  "associationType": "junctionJunctionConnectivity",
  "isContentVisible": true,       // optional: false(0) / true(1)
  "fromNetworkSourceId": 9,
  "fromGlobalId": "{...}",
  "fromTerminalId": 1,            // optional; traditional domain networks, junction sources only
  "toNetworkSourceId": 12,
  "toGlobalId": "{...}",
  "toTerminalId": 1,              // optional
  "percentAlong": 0.5,            // optional; junction-edge midspan connectivity only
  "toFirstUnit": 6                // optional; telecom containment only
}
```
- `associationType` values listed by Esri: `attachment`, `containment`,
  `junctionJunctionConnectivity`, `junctionEdgeFromConnectivity`,
  `junctionMidspanConnectivity`, `junctionEdgeToConnectivity`. The three
  edge-based types require **utility network version 4 or higher**.
- Required vs optional: the page does not label required fields; only
  terminals, `isContentVisible`, `percentAlong` and `toFirstUnit` are marked
  optional, so the from/to network source id + globalId and `associationType`
  are effectively required.
- The page's own examples are inconsistent (`toterminalId` lowercase,
  `"associationType": "connectivity"`, `isContentVisible: -1`); follow the
  syntax block, not the example, and test against your service.
- Integer association codes (1-6) belong to the geodatabase field and the
  arcpy `UtilityNetwork` class (`arcpy/01-*.md`); this appendix does **not**
  document integers for `applyEdits`. Verify against the Esri docs for your
  version before sending integer codes or upper-case field names
  (`ASSOCIATIONTYPE`, `FROMGLOBALID`, ...). `scripts/association_types.py`
  converts between the code, CSV (`pro-help/04-*.md`), REST camelCase and GP
  encodings.
- Deleting: Enterprise 12.0+ (capability `supportsDeleteAssociations`) adds a
  `deleteAssociations` array whose entries need **all** fields (`globalId`,
  `associationType`, `fromSourceId`, `fromGlobalId`, `fromTerminalId`,
  `toSourceId`, `toGlobalId`, `toTerminalId`); the older `deletes` list of
  globalIds is deprecated at 12.0 but still supported for traditional domain
  networks.
- Esri states no numeric limits for these edits.

### Telecom-specific: `toFirstUnit`
For a **containment association in a telecom domain network**, the
`toFirstUnit` property specifies the **unit identifier** on the content
Unit Identifiable object where containment begins — a telecom-only field
with no equivalent in traditional (electric/gas/water) domain network
associations.

### The critical performance/safety trade-off: `utilityNetworkOptions`
```json
{ "applyEditsOptions": { "utilityNetworkOptions": 1 } }
```
- Setting this **bypasses validation** when creating associations via
  `applyEdits` — **faster writes**, especially valuable for bulk-loading many
  associations (e.g., a data migration).
- **The cost**: if one or more of the created associations turn out to be
  **invalid**, they are **not rejected at write time** — they're written, and
  the **next `validateNetworkTopology` run** discovers and flags them as
  errors (dirty areas / error features, per
  `pro-help/04-associations-editing-errors.md`).
- **Practical guidance**: this is the right tool for a **trusted bulk-load**
  scenario (you're confident the data is valid, and speed matters more than
  per-write feedback) and the wrong tool for **interactive, one-at-a-time**
  association creation in an end-user-facing app, where you want immediate
  validation feedback rather than deferred error discovery. Always mention
  this trade-off explicitly when someone asks about writing associations at
  scale — don't just hand them the flag without the caveat.

## Practical guidance for Claude

- When someone asks "how do I get/set associations without the full C#
  SDK or arcpy" (e.g., from a lightweight script, or from JS under the
  hood), point them at this `applyEdits`-on-the-systemLayer pattern rather
  than assuming they need `ImportAssociations` or the C# `AddAssociation`
  method — those are Pro/Add-in-side tools; this is the direct-to-service
  path.
- Always resolve the **actual layer ID** for the target systemLayer first
  (via `utilityNetworkLayerId` → layer definition) rather than guessing a
  layer number — layer IDs are **service-specific**, not a fixed constant
  across different published utility networks.
- If someone is bulk-loading associations, proactively mention
  `utilityNetworkOptions: 1` as a speed option **and** the validation
  deferral trade-off in the same breath.

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/appendix-working-with-the-feature-server-utility-network-server/
