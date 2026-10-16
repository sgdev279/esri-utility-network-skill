# Utility Network — REST `traceConfiguration`: Full Schema (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Source: ArcGIS REST API "Trace (Utility Network Server)" reference (URLs in the
Sources list at the bottom). Complements `01-utility-network-server-and-trace.md`,
which covers the top-level trace request and the boolean flags.*

Use this when hand-writing or debugging a `traceConfiguration` with
barriers, functions, filters, output conditions, propagators or nearest
neighbour. Validate a draft with
`python scripts/build_trace_request.py --check draft.json`.

## Shared operator vocabulary

Every `operator` field accepts:
`equal`, `notEqual`, `greaterThan`, `greaterThanEqual`, `lessThan`,
`lessThanEqual`, `includesTheValues`, `doesNotIncludeTheValues`,
`includesAny`, `doesNotIncludeAny`.

The `includes*` operators are bitwise — use them with bit-packed network
attributes such as phases (e.g. "includesAny" of phase bits). (The Trace page
lists the operators but does not itself explain the bitwise semantics —
**verify against the Esri docs for your version**.)

`functionType` accepts: `add`, `subtract`, `average`, `count`, `min`, `max`.

Condition `type` accepts `networkAttribute` or `category`; scopes
(`traversabilityScope`, `filterScope`) accept `junctions`, `edges`,
`junctionsAndEdges` (default `junctionsAndEdges`); `propagatorFunctionType`
accepts `bitwiseAnd`, `min`, `max`. Trace-level enums (`traceType`,
`traceLocationType`, `resultTypes.type`) are in
`01-utility-network-server-and-trace.md`.

## Traversability — where the trace stops

```json
"conditionBarriers": [
  { "name": "Device status", "type": "networkAttribute",
    "operator": "equal", "value": "1",
    "combineUsingOr": false, "isSpecificValue": true }
],
"functionBarriers": [
  { "functionType": "add", "networkAttributeName": "Shape length",
    "operator": "greaterThan", "value": "1000", "useLocalValues": false }
],
"traversabilityScope": "junctionsAndEdges"
```
- `type`: `networkAttribute` (compare an attribute) or `category` (feature
  is/isn't in a network category). Esri says that to filter on a feature's
  category you "ensure the `name` and `type` are set as `Category`" with
  `isSpecificValue` true and the category in `value` — confirm the exact
  casing of `type` against a trace configuration saved from Pro.
- `isSpecificValue`: `true` compares to `value`; `false` compares to
  **another network attribute** named in `value`.
- `combineUsingOr`: appears on `conditionBarriers`, `filterBarriers`,
  `functions` conditions and `outputConditions`; the Trace page does not define
  it and links to a general page on multiple conditional expressions
  (**verify against the Esri docs for your version** how `true`/`false` joins
  adjacent conditions).
- `useLocalValues` (function barriers): not defined on the Trace page —
  **verify against the Esri docs for your version**.
- `traversabilityScope`: `junctions` | `edges` | `junctionsAndEdges`.

## Filters — isolation/"find the nearest" style traces

```json
"filterBarriers": [
  { "name": "Operable", "operator": "equal", "value": "1",
    "combineUsingOr": false, "isSpecificValue": true }
],
"filterFunctionBarriers": [
  { "functionType": "add", "networkAttributeName": "Customer count",
    "operator": "greaterThan", "value": "50" }
],
"filterScope": "junctionsAndEdges"
```
The REST syntax for `filterBarriers` lists `name`, `operator`, `value`
(numeric string), `combineUsingOr`, `isSpecificValue` and no `type`, and gives
no category example; it describes them as "network attribute or category
conditions". For a category (e.g. Isolating), the only documented rule is the
`conditionBarriers` one: `name` = `Category` with `isSpecificValue` true and
the category in `value`. arcpy's `filterBarriers` object does expose a `type`
property, so a Pro-saved configuration may carry `type` (the checker accepts
it); confirm the exact shape by querying `traceConfigurations` for a
configuration saved from Pro.

Filter barriers **stop the trace**, like condition barriers (Esri Barriers
page: "Filter barriers are like condition barriers"; they are evaluated on a
second pass, after traversability barriers, and only in traces, never in
subnetwork update or export). They do not let the trace keep exploring past
them. In an isolation trace at least one filter barrier is required; it
(e.g. "Isolating" category + operable) defines the isolating devices.
## Functions — aggregate values along the result

```json
"functions": [
  { "functionType": "add", "networkAttributeName": "Customer count",
    "summaryAttributeName": "", "functionName": "",
    "conditions": [
      { "name": "Lifecycle status", "type": "networkAttribute",
        "operator": "equal", "value": "2",
        "combineUsingOr": false, "isSpecificValue": true } ] }
]
```
`summaryAttributeName` and `functionName` are not defined on the Trace page
(its telecom example sets `functionName` to "Fiber length (meters)"; the
`supportsFunctionName` capability flag exists). Results come back in
`globalFunctionResults` (REST) / `FunctionResult` (JS, `js-api/04-*.md`).

## Output — what gets returned

```json
"outputFilters": [
  { "networkSourceId": 9, "assetGroupCode": 3, "assetTypeCode": 12 }
],
"outputConditions": [
  { "name": "Device status", "type": "networkAttribute",
    "operator": "equal", "value": "1",
    "combineUsingOr": false, "isSpecificValue": true }
]
```
`outputFilters` limit results to specific source/asset group/asset type
combinations; `outputConditions` limit by attribute or category. Neither
changes where the trace goes, only what's reported.

## Propagators — phase-style values carried along the network

```json
"propagators": [
  { "networkAttributeName": "Phases normal",
    "substitutionAttributeName": "",
    "propagatorFunctionType": "bitwiseAnd",
    "operator": "includesAny", "value": "7",
    "propagatedAttributeName": "" }
]
```
`propagatorFunctionType`: `bitwiseAnd` | `min` | `max`; `value` is a numeric
string; `substitutionAttributeName` is not defined on the Trace page. The classic use is
electric phasing: `bitwiseAnd` on a phase bitmask so a single-phase tap
stops the trace for the phases it doesn't carry. Request
`includePropagatedValues: true` in `resultTypes` to get the values back.

## Nearest neighbour and shortest path

```json
"nearestNeighbor": {
  "count": 3,
  "costNetworkAttributeName": "Shape length",
  "nearestCategories": ["Protective"],
  "nearestAssets": [ { "networkSourceId": 9, "assetGroupCode": 3, "assetTypeCode": 12 } ]
},
"shortestPathNetworkAttributeName": "Shape length"
```
`shortestPathNetworkAttributeName` names the cost attribute for `shortestPath`
and `path` traces; the Trace Network Server reference states it is required
for `shortestPath` (the Utility Network Trace page states no requirement —
supply it anyway). `shortestPath` is deprecated at 12.1 in favour of `path`.

## Defaults that differ between Pro and REST

| Property | REST (Trace page) | Pro Trace tool / Configure a trace |
|---|---|---|
| `validateConsistency` | `true` | Validate Consistency unchecked (false) by default, for performance |
| `allowIndeterminateFlow` | no default stated (send it explicitly) | checked (true) by default; needs UN dataset v5+ |
| `numPaths` | 1 | 1 (Add Trace Configuration tool page says 2; set it explicitly) |
| `includeFlowDirections` | no default; introduced Enterprise 12.1; elements, features and connectivity results only | unchecked; Enterprise 12.1+ for enterprise geodatabases |

## Newer / specialised properties (12.1 and path, circuit and loops traces)

| Property | Notes |
|---|---|
| `filterBitsetNetworkAttributeName` | upstream/downstream traces: results include any bit set on the starting points for this attribute; loops traces: return only loops where the same bit is set all the way around |
| `inferConnectivity` (boolean, default `false`) | **path traces only** |
| `circuitName` | **circuit traces only** |
| `numPaths` (12.1, default 1) | **path traces only**; paths returned = start locations x stop locations x `numPaths` |
| `maxHops` (12.1, default 100) | **path and circuit traces only**; edges and junction-junction connectivity count 1 hop each, terminal devices count 2 |
| `useDigitizedDirection` (11.3, UN dataset v7+) | when true, `domainNetworkName`, `tierName` and `targetTierName` are ignored |
| `synthesizeGeometries` (11.3) | applies only with the `aggregatedGeometry` result type (see the caveat in `01-*.md`) |

`traceType` values `path` and `circuit` and the stopping-point location type
(`stoppingPoint`) are listed in `01-utility-network-server-and-trace.md`.

## Checklist when a hand-written configuration misbehaves

1. **Names are exact.** Network attribute and category names are
   case-sensitive and must match `queryDataElements` output.
2. **Values are strings** in REST JSON, even for numbers.
3. **Coded values**: compare to the stored code, not the description.
4. **Subnetwork traces** require `domainNetworkName` and `tierName` in the
   configuration (and `subnetworkName` when tracing a specific subnetwork
   without starting points).
5. **Barriers on starting points**: `ignoreBarriersAtStartingPoints` decides
   whether a barrier at a start location stops the trace immediately.
6. **Prefer a named trace configuration** (`traceConfigurationGlobalId`)
   when the admin already built one in Pro — it avoids all of the above.

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-trace-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/create-traceconfiguration-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-traceconfiguration-utility-network-server/
