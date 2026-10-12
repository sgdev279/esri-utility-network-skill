# Utility Network — REST API: Circuits & Unit Identifiers (Telecom) (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

> Last reviewed: 2026-10-12 (JS SDK 5.1 / Enterprise 12.1 / UN dataset v8)

Both resources are **telecom-domain-network-only** and were **introduced at
ArcGIS Enterprise 12.1** (Esri's REST "What's new" lists the `circuits` and
`unitIdentifiers` resources as new at 12.1; nothing telecom-related is listed
at 11.5 or 12.0). The `circuits` resource requires the **ArcGIS Advanced
Editing** user type extension for every operation **except Query**. The
`unitIdentifiers` resource page does not state a license requirement — verify
against the Esri docs for your version. A legacy `insertGap` page still
exists in the REST reference labelled "11.5" (see below); treat that label as
unreliable.

## `Circuits` resource

`https://<root>/<serviceName>/UtilityNetworkServer/circuits`
Operations: **Alter, Create, Delete, Export, Query, Verify**.

A **circuit** models an end-to-end telecom path (e.g., a physical or virtual
circuit composed of one or more **sections**) — the telecom-specific
counterpart to how traditional domain networks model subnetworks.

### `create`
`POST .../circuits/create`
- Parameters: `f`, `gdbVersion` (default `sde.DEFAULT`), `sessionId`,
  `domainNetworkName` (required — the telecom domain network), and
  **`circuit`** (required — the circuit definition; a single circuit object per
  the examples, although the syntax block wraps it in an array — a doc
  inconsistency, so follow the examples).
- Circuit JSON shape (per the REST reference):
  ```json
  {
    "name": "A32/T3U/79232211/82256420",
    "globalId": "{...}",
    "isSectioned": true,
    "sectionOrder": {},
    "circuitType": "Physical",     // "Physical" | "Virtual", default Physical
    "sections": [
      {
        "sectionId": 1,
        "role": "Start and end",     // Start and end | Start | End | Midspan
        "sectionType": "Physical",   // Physical | Virtual
        "startLocation": { "sourceId": 20, "globalId": "{...}", "firstUnit": 1, "lastUnit": 1 },
        "stopLocation":  { "sourceId": 20, "globalId": "{...}", "firstUnit": 1, "lastUnit": 1 }
      }
    ],
    "subcircuits": [
      { "name": "...", "globalId": "{...}", "providerId": "{...}", "consumerId": "{...}",
        "state": "Available" }     // Consumed | Reserved | Available (default Available)
    ],
    "attributes": {}
  }
  ```
  When `isSectioned` is **false**, `startLocation` / `stopLocation` are given
  directly on the circuit (and `sections` / `sectionOrder` are not used).
- A location is `sourceId` + `globalId` + `firstUnit` + `lastUnit` — it
  pinpoints a range of units on a specific feature. **There is no
  `startPoint` / `stopPoint`, `terminalId` or `numUnits` in the circuit
  location object**; those names are not in the documented REST schema.
- Response: `moment`, `exceededTransferLimit`, `serviceEdits[]` (`id`,
  `editedFeatures.adds`), `success`.

### `query`
`.../circuits/query` (Enterprise 12.1; `domainNetworkName` is **required**).
Three mutually exclusive ways to select circuits, in order of precedence:
1. **By circuit name**: `circuits=["CircuitA","CircuitB"]` — if supplied,
   `circuitIds` and `locations` are ignored.
2. **By circuit global ID**: `circuitIds=["{GUID}", ...]` — if supplied,
   `locations` is ignored.
3. **By location**: `locations=[{ "sourceId", "globalId", "firstUnit", "lastUnit" }]`
   plus `locationType` = `start` | `stop` | `all` (default `all`).
- `circuitHierarchy` — `consumers` | `providers` | `consumers and providers` |
  `none` (default). With `locations` and no hierarchy, only the circuits
  passing directly through the location are returned; set it to also return
  consuming and/or providing circuits. **There is no
  `returnConsumingCircuits` parameter** in the REST reference.
- `circuitStatus` — filter by `clean` | `dirty` | `invalid` | `deleted`.
- `resultTypes` — `name` (default; response is `{ "circuitNames": [...], "success" }`)
  or `circuit` (full definitions incl. sections and subcircuits).
- Also accepts `gdbVersion`, `sessionId`, `moment`.

### `alter`, `delete`, `export`, `verify`
All take `domainNetworkName` (required), `gdbVersion`, `sessionId`:
- **`alter`** — `circuit` (required): the full circuit definition **replaces**
  the existing one, so omitted properties are removed.
- **`delete`** — `circuits` (required): array of circuit names; **logical**
  delete; if any circuit fails, the whole operation rolls back.
- **`export`** — `circuits` (required), `moment`, `exportAcknowledgement`
  (if `true`, `gdbVersion` must be the default version), `traceConfiguration`,
  `resultTypes` (`features` | `connectivity` | `associations` | `circuits`;
  default `features`), `async`, `outSR`. One JSON file per circuit.
- **`verify`** — `circuits` (required), `async`, `forceVerify` (default
  `false`; `false` returns an error for clean circuits), `synthesizeGeometries`
  (default `false`), `outSR`. Confirms each circuit still traces start-to-stop
  and that sections/subcircuits are valid.

### Base resource response (when called with no operation)
```json
{ "success": true }
```
or, on failure, the standard `{ "success": false, "error": { "extendedCode", "message", "details" } }` shape used across `UtilityNetworkServer`.

## `Unit Identifiers` resource

`https://<root>/<serviceName>/UtilityNetworkServer/unitIdentifiers`
Operations (Enterprise 12.1 resource page): **Query, Reserve, Reset, Resize**.
A legacy `insertGap` operation page also remains in the REST reference
(labelled "11.5", parameters `object`, `firstUnit`, `numUnits`); it is **not**
in the 12.1 resource's operation list or in the 12.1 "What's new", and it
duplicates `reserve`'s documented behavior. For 12.1 and later code, use
**`reserve`** with `firstUnit`/`lastUnit`; if you must target an older
build, verify against the Esri docs for your version whether `insertGap` is
available.

Manages the **unit identifier space** on **unit container** features (e.g.,
a fiber cable) and the **unit identifiable** objects/features nested inside
them — a telecom-specific allocation system with no traditional-domain-network
equivalent.

### `reserve` (12.1) — reserve a range of unit IDs
```
POST .../unitIdentifiers/reserve
gdbVersion=sde.Default
object={ "sourceId": 16, "globalId": "{...}" }
firstUnit=13
lastUnit=14        // legacy insertGap used numUnits instead of lastUnit
```
- Shifts existing records in the unit container's `NextUnitID` sequence to
  **reserve a range** — inserting at the **end** of the sequence simply
  increases `NEXTUNITID`; inserting in the **middle** shifts existing
  records to make room.
- **Fails with an error** if the reservation would require **regrouping an
  object** or falls in the middle of a **connectivity assignment** — a
  concrete, checkable failure mode worth mentioning proactively.

### `query`
`objects=[{ "sourceId": <n>, "globalIds": ["{...}"] }]` (optional; junction or
edge unit containers) plus optional `gdbVersion` / `moment`. Returns the
current unit identifier layout for each container, including **gaps** and the
individual `unitIdentifiers` entries:
```json
{
  "objects": [
    {
      "sourceId": 9, "globalId": "{...}",
      "gaps": [ { "start": 4, "end": 7 } ],
      "unitIdentifiers": [
        { "sourceId": 13, "globalId": "{...}", "firstUnit": 1, "lastUnit": 1 },
        { "sourceId": 13, "globalId": "{...}", "firstUnit": 2, "lastUnit": 2 }
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
object={ "sourceId": 18, "globalId": "{...}" }
lastUnit=3
```
- Alters the **number of units** a single unit-identifiable feature/object
  occupies — can **increase or decrease** — by giving the new `lastUnit`
  (**not** a `numUnits` parameter). Operates on **one object**, unlike
  `reset`/`query` which take arrays.
- Doc inconsistency: the parameter table names the parameter `object` but the
  page's example sends `objects=` (still a single object). Prefer `object`
  and confirm against the Esri docs for your version.

### Pro Help cross-reference (the UI side of the same operations)
The **Unit ID Operations pane** in ArcGIS Pro exposes the same four
operations interactively: **Query**, **Reserve Unit IDs**, **Reset Unit
IDs** (all three operate on a selected **unit container** feature), and
**Resize Unit IDs** (operates on a selected **unit identifiable**
feature/object instead) — the same container-vs-identifiable object
distinction that governs which REST parameter shape (singular object vs.
array) applies. (Pro Help: Query / Reserve / Reset apply to a **unit
container**; Resize applies to a **unit identifiable** object.)

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
4. Use `reserve` (12.1+); do not generate `insertGap` code unless the user
   explicitly targets a build where that operation is documented.

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/whats-new/
- https://developers.arcgis.com/rest/services-reference/enterprise/circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/create-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/alter-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/delete-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/export-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/verify-circuits-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/unitIdentifiers-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-unitIdentifiers-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/reserve-unitIdentifiers-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/reset-unitIdentifiers-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/resize-unitIdentifiers-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/insertGap-unitIdentifiers-utility-network-server
- https://pro.arcgis.com/en/pro-app/3.5/help/data/utility-network/work-with-unit-identifiers.htm
