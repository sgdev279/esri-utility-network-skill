# Utility Network — REST API: Working with the Utility Network via the Feature Service (Appendix, Deep Reference)
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
2. Fetch `.../FeatureServer/<utilityNetworkLayerId>?f=pjson` — the utility
   network layer's own JSON definition groups the related **system layers**
   (associations, dirty areas, etc.) with their **layer IDs**.
3. Use those layer IDs with ordinary feature service operations (`query`,
   `applyEdits`) to read/write that system table directly.

This is the mechanism behind "how do I query dirty areas or associations
from a plain feature-service client" — you don't need a UN-specific SDK
class for read access; you need the right **layer ID** and ordinary feature
service `query`/`applyEdits` calls.

## Writing associations directly via `applyEdits`

`POST .../FeatureServer/applyEdits` (run against the **associations
systemLayer**, targeting **DEFAULT** version, with `useGlobalIds: true`).

### Association attribute schema (as written via applyEdits)
```json
{
  "ASSOCIATIONTYPE": 1,          // 1=junctionJunctionConnectivity, 2=containment, 3=attachment,
                                  // 4=junctionEdgeFromConnectivity,
                                  // 5=junctionEdgeMidspanConnectivity,
                                  // 6=junctionEdgeToConnectivity
  "ISCONTENTVISIBLE": 1,         // optional: 0=false, 1=true
  "FROMNETWORKSOURCEID": 0,
  "FROMGLOBALID": "{...}",
  "FROMTERMINAL": 0
  // ... TO-side equivalents (TONETWORKSOURCEID, TOGLOBALID, TOTERMINAL),
  // PERCENTALONG for midspan connectivity, and (telecom only) toFirstUnit
}
```
These integer codes are the same ones the arcpy `UtilityNetwork` class uses
(`arcpy/01-*.md`). They differ from the text names in the Import/Export
Associations CSV (`pro-help/04-*.md`) and the camelCase names in REST
`associations/query`. `scripts/association_types.py` converts between all
three.

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
