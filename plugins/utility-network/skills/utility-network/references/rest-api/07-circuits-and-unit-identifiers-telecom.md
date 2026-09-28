# Utility Network — REST API: Circuits & Unit Identifiers (Telecom) (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

Both resources are **telecom-domain-network-only** — introduced at **11.5**
(Unit Identifiers' `reserve` operation specifically at **12.1**, replacing/
complementing the earlier `insertGap`). Both require the **ArcGIS Advanced
Editing** user type extension. These were previously only named in this
skill; this file gives them the same depth as everything else.

## `Circuits` resource

`https://<root>/<serviceName>/UtilityNetworkServer/circuits`
Operations: **Alter, Create, Delete, Export, Query, Verify**.

A **circuit** models an end-to-end telecom path (e.g., a physical or virtual
circuit composed of one or more **sections**) — the telecom-specific
counterpart to how traditional domain networks model subnetworks.

### `create`
`POST .../circuits/create`
- Required: `domainNetworkName` (the telecom domain network), `circuits`
  (the circuit definition(s) to create).
- Circuit JSON shape:
  ```json
  {
    "circuits": [
      {
        "name": "A32/T3U/79232211/82256420",
        "globalId": "{...}",
        "isSectioned": true,
        "sectionOrder": "",
        "circuitType": "Physical",     // "Physical" | "Virtual", default Physical
        "sections": [
          {
            "sectionId": 1,
            "role": "Start and end",
            "sectionType": "Physical",
            "startPoint": { "sourceId": 20, "globalId": "{...}", "terminalId": 1, "firstUnit": 1, "numUnits": 1 },
            "stopPoint":  { "sourceId": 20, "globalId": "{...}", "terminalId": 1, "firstUnit": 1, "numUnits": 1 }
          }
        ]
        // when isSectioned is false, startPoint/stopPoint are given directly
        // on the circuit rather than nested under sections
      }
    ]
  }
  ```
- `sourceId`/`globalId`/`terminalId`/`firstUnit`/`numUnits` together pinpoint
  an exact **unit** on a specific feature/terminal — this is the same
  building-block shape used across circuits, unit identifiers, and location
  queries throughout this telecom API surface.

### `query`
`.../circuits/query` — **two query modes**, mutually exclusive:
1. **By circuit name**: pass `circuits=["CircuitA","CircuitB"]` —
   `sourceId`/`globalId`/`terminalId`/`firstUnit`/`lastUnit` are **ignored**
   when a `circuits` array is supplied.
2. **By trace location**: pass `sourceId`, `globalId`, `terminalId`,
   `firstUnit`, `lastUnit`, `locationType` (`"start"` or presumably `"stop"`)
   to find circuits starting/stopping at that specific location instead of
   naming them.
- `returnConsumingCircuits` (boolean) — when **`false`** (with trace-location
  mode), returns only the **immediate** circuits passing through the
  specified feature; when **`true`**, also returns circuits that **consume**
  those immediate circuits (i.e., walks up the containment/consumption
  hierarchy) — an important distinction when someone wants "everything
  ultimately affected here" vs. "just what's directly here."
- `domainNetworkName` is **required** on every query.

### `alter`, `delete`, `export`, `verify`
Named operations on the same resource, following the same general
request-shape conventions (`gdbVersion`, `sessionId`, target circuit
identification) as `create`/`query` above — consult the live docs for the
exact parameter set of each before generating code, since detailed schemas
for these four weren't independently confirmed at the depth `create`/`query`
were here.

### Base resource response (when called with no operation)
```json
{ "success": true }
```
or, on failure, the standard `{ "success": false, "error": { "extendedCode", "message", "details" } }` shape used across `UtilityNetworkServer`.

## `Unit Identifiers` resource

`https://<root>/<serviceName>/UtilityNetworkServer/unitIdentifiers`
Operations (11.5): **Insert Gap, Query, Reset, Resize**. At **12.1**, Esri's
own "what's new" describes the operation set as **query, reserve, reset, and
resize** — i.e., **`reserve`** is the newer/current name for reserving a
range (see below), while `insertGap` remains documented as its own
(seemingly earlier or narrower) operation. **If targeting a specific
Enterprise version, verify which of `insertGap` vs. `reserve` is the
intended/available operation** rather than assuming they're strictly
identical or that one has fully replaced the other.

Manages the **unit identifier space** on **unit container** features (e.g.,
a fiber cable) and the **unit identifiable** objects/features nested inside
them — a telecom-specific allocation system with no traditional-domain-network
equivalent.

### `reserve` (12.1) / `insertGap` (11.5) — reserve a range of unit IDs
```
POST .../unitIdentifiers/reserve
gdbVersion=sde.Default
object={ "sourceId": 16, "globalId": "{...}" }
firstUnit=13
lastUnit=14        // (insertGap uses numUnits instead of lastUnit)
```
- Shifts existing records in the unit container's `NextUnitID` sequence to
  **reserve a range** — inserting at the **end** of the sequence simply
  increases `NEXTUNITID`; inserting in the **middle** shifts existing
  records to make room.
- **Fails with an error** if the reservation would require **regrouping an
  object** or falls in the middle of a **connectivity assignment** — a
  concrete, checkable failure mode worth mentioning proactively.

### `query`
Returns the current unit identifier layout for one or more objects,
including **gaps** and the individual `unitIdentifiers` entries:
```json
{
  "objects": [
    {
      "sourceId": 9, "globalId": "{...}",
      "gaps": [ { "start": 4, "end": 7 } ],
      "unitIdentifiers": [
        { "sourceId": 13, "globalId": "{...}", "firstUnit": 1, "numUnits": 1 },
        { "sourceId": 13, "globalId": "{...}", "firstUnit": 2, "numUnits": 1 }
      ]
    }
  ],
  "success": true
}
```
This is the direct answer to "what unit IDs are free/in use on this cable" —
`gaps` gives the free ranges, `unitIdentifiers` gives the occupied ones.

### `reset`
```
POST .../unitIdentifiers/reset
objects=[{"sourceId": 9, "globalIds": ["{...}"]}]
```
- **Purpose**: condense the unit identifier space, fix data-inconsistency
  issues (unit-identifiable records out of sync with their container), or
  recover from **sequence exhaustion** (running out of available unit IDs).
- Response shape mirrors `query`'s (`gaps` + `unitIdentifiers` after the
  reset).

### `resize`
```
POST .../unitIdentifiers/resize
objects={ "sourceId": 18, "globalId": "{...}" }
numUnits=3
```
- Alters the **number of units** a single unit-identifiable feature/object
  occupies — can **increase or decrease**. Operates on **one object**
  (singular `objects`, not an array, unlike `reset`/`query`) — a parameter
  **shape inconsistency worth double-checking** in generated code (don't
  assume every operation on this resource takes an array uniformly).

### Pro Help cross-reference (the UI side of the same operations)
The **Unit ID Operations pane** in ArcGIS Pro exposes the same four
operations interactively: **Query**, **Reserve Unit IDs**, **Reset Unit
IDs** (all three operate on a selected **unit container** feature), and
**Resize Unit IDs** (operates on a selected **unit identifiable**
feature/object instead) — the same container-vs-identifiable object
distinction that governs which REST parameter shape (singular object vs.
array) applies.

## Practical guidance for Claude

1. Always confirm the domain network is genuinely **telecom** before
   reaching for Circuits/Unit Identifiers — these have no meaning on a
   traditional (electric/gas/water) domain network.
2. For unit ID work, get clear on **container vs. identifiable object**
   first — it determines both which Pro pane/REST parameter shape applies
   and which of Query/Reserve/Reset (container) vs. Resize (identifiable
   object) is even valid.
3. When reserving/inserting unit ID ranges, proactively mention the two
   documented failure modes (object regrouping required, or landing mid
   connectivity-assignment) rather than only showing the happy path.
4. Treat `insertGap` vs. `reserve` as a version-sensitive naming question —
   ask or check the target Enterprise version rather than assuming.
