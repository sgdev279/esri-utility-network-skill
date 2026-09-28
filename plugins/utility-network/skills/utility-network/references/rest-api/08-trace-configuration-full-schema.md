# Utility Network — REST `traceConfiguration`: Full Schema (Deep Reference)
*Source: ArcGIS REST API "Trace (Utility Network Server)" reference.
Last reviewed: 2026-09-28. Complements `01-utility-network-server-and-trace.md`,
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
attributes such as phases (e.g. "includesAny" of phase bits).

`functionType` accepts: `add`, `subtract`, `average`, `count`, `min`, `max`.

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
  is/isn't in a network category; `value` is then the category name).
- `isSpecificValue`: `true` compares to `value`; `false` compares to
  **another network attribute** named in `value`.
- `combineUsingOr`: how this condition joins the **next** one in the list.
- `useLocalValues` (function barriers): evaluate per starting point rather
  than cumulatively from the trace origin.
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
Filter barriers are evaluated **after** traversability: the trace still
explores past them, but they limit what counts. In an isolation trace the
filter barrier (e.g. "Isolating" category + operable) defines the isolating
devices.

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
Results come back in `globalFunctionResults` (REST) / `FunctionResult`
(JS, `js-api/04-*.md`).

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
`propagatorFunctionType`: `bitwiseAnd` | `min` | `max`. The classic use is
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
`shortestPathNetworkAttributeName` is required for `traceType=shortestPath`.

## Checklist when a hand-written configuration misbehaves

1. **Names are exact.** Network attribute and category names are
   case-sensitive and must match `queryDataElements` output.
2. **Values are strings** in REST JSON, even for numbers.
3. **Coded values**: compare to the stored code, not the description.
4. **Subnetwork traces** also need `domainNetworkName`, `tierName` and
   usually `subnetworkName` in the configuration.
5. **Barriers on starting points**: `ignoreBarriersAtStartingPoints` decides
   whether a barrier at a start location stops the trace immediately.
6. **Prefer a named trace configuration** (`traceConfigurationGlobalId`)
   when the admin already built one in Pro — it avoids all of the above.
