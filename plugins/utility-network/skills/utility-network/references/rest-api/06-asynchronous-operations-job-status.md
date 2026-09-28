# Utility Network — REST API: Asynchronous Operations & Job Status Polling (Deep Reference)
*Source: developers.arcgis.com/rest/services-reference/enterprise/*

Several `UtilityNetworkServer` operations can run long enough (large trace,
full-extent validate, big subnetwork export) to need an async, poll-for-status
pattern instead of blocking the client on a single request. This is a
distinct, simpler pattern from the classic `GPServer` job system — don't
conflate the two (see the comparison at the end).

## Which operations support `async=true`

Confirmed to accept an `async` boolean parameter (default `false`):

| Operation | `async` introduced | Notes |
|---|---|---|
| `trace` | 10.9.1 | Large/complex traces on big networks are the main use case |
| `enableTopology` | 10.9.1 | Also has `maxErrorCount` (default 10,000) — the error-count threshold that stops the enable process |
| `disableTopology` | 10.9.1 | |
| `exportSubnetwork` | 10.9.1 | |
| `updateIsConnected` | 10.9.1 | Also requires being the **portal utility network owner** and topology enabled |
| `Locations` → `query` | 10.9.1 | |
| `validateNetworkTopology` | — | Esri's own docs state it's "supported synchronously and asynchronously"; treat as following the same `async` pattern, but confirm the exact parameter name against the live docs for the target Enterprise version since it wasn't observed with an explicit `async` param in the same way as the operations above |
| `updateSubnetwork` | — | Also supports async (confirmed via its own response schema showing `statusUrl`) |

### Capability flags (introduced 10.9.1) — check before assuming async is available
```json
{
  "capabilities": {
    "supportsAsyncTrace": true,
    "supportsAsyncEnableTopology": true,
    "supportsAsyncDisableTopology": true,
    "supportsAsyncExportSubnetwork": true,
    "supportsAsyncUpdateIsConnected": true,
    "supportsAsyncLocationsQuery": true
  }
}
```
These live on the `UtilityNetworkServer` root capabilities response
(`rest-api/01-utility-network-server-and-trace.md`). **Always check the
relevant flag before relying on `async=true`** — older utility network
versions or Enterprise releases before 10.9.1 won't support it, and the
operation will behave as if `async` were simply ignored/unsupported.

## The request/response pattern

### 1. Submit with `async=true`
```
POST .../UtilityNetworkServer/enableTopology
f=json
async=true
```
Response:
```json
{ "statusUrl": "https://myserver.esri.com/.../enableTopology/jobs/<jobId>" }
```

### 2. Poll the `statusUrl`
While pending or in progress:
```json
{
  "status": "Pending",          // or "InProgress"
  "submissionTime": 1554336000000,
  "lastUpdatedTime": 1554336005000
}
```
**Confirmed status values for this pattern**: `Pending`, `InProgress`. Keep
polling the same `statusUrl` while either value is returned.

### 3. On completion
The status URL returns the **same JSON body the synchronous (`async=false`)
call would have returned** for that operation — e.g., for `updateSubnetwork`,
the completed status response includes the normal `moment`/`failures`/
`success` fields; for `validateNetworkTopology`, it includes `moment`,
`fullUpdate`, `validateErrorsCreated`, `dirtyAreaCount`, and
`discoveredSubnetworks` exactly as documented in
`rest-api/02-topology-and-subnetwork-management-operations.md`. There is
**no separate "fetch the result" step** beyond continuing to poll the same
URL until the terminal state's full payload appears.

## Don't confuse this with the classic `GPServer` job pattern

Esri's traditional geoprocessing services (`.../GPServer/<taskName>`, used by
Spatial Analysis and Network Analyst services, among others) use a **richer,
differently-named** job model:
```json
{ "jobId": "...", "jobStatus": "esriJobSubmitted" }
```
with status values `esriJobSubmitted → esriJobWaiting → esriJobExecuting →
esriJobSucceeded | esriJobFailed | esriJobTimedOut | esriJobCancelling |
esriJobCancelled`, a `jobs/<jobId>` polling URL, and a separate
`results/<paramName>` sub-resource to fetch each output parameter once
complete.

**`UtilityNetworkServer`'s async pattern is simpler and different**: a flat
`statusUrl`, only `Pending`/`InProgress` as pending states, and the
**completed operation's normal response body** appearing directly at that
same URL — there is no `jobId`/`jobStatus` vocabulary, no separate
`results/` sub-resource, and no `esriJob*` enum values. If a person is
writing polling code from a GPServer example they found, flag this
difference explicitly — copying GPServer-style status-check logic
(checking for `esriJobSucceeded`, hitting a `results/` endpoint) **will not
work** against `UtilityNetworkServer`'s async operations.

## Also distinct: the replica `synchronizeReplica`/`createReplica` async pattern

A **third**, separate async shape exists for feature service replicas
(`synchronizeReplica`/`createReplica`, unrelated to UN specifically): its
status resource returns richer fields (`transportType`, `responseType`,
`replicaName`, `resultUrl`) and a **different status vocabulary**
(`Pending | InProgress | Completed | Failed | ImportChanges | ExportChanges |
... | CompletedWithErrors`) with an explicit `resultUrl` once done — again,
**not** the same shape as `UtilityNetworkServer`'s pattern. Three different
async conventions exist across the ArcGIS REST API family; always match
polling code to the specific service being called rather than assuming one
universal job schema.

## Practical guidance for Claude

1. When someone's UN operation is timing out on a large network, **`async=true`
   is the first thing to suggest** — check the specific operation and
   capability flag support first.
2. When writing polling code, use the **`Pending`/`InProgress` → full
   response body** shape specifically for `UtilityNetworkServer` operations
   — never copy-paste GPServer (`esriJobStatus`) or replica-sync polling
   logic without adapting it.
3. Mention `maxErrorCount` when discussing `enableTopology` on a large or
   messy dataset — a high error count can otherwise halt the enable process
   partway through.
4. For `updateIsConnected`, remind users of the **owner + topology-enabled**
   preconditions regardless of sync/async mode — async doesn't relax those
   requirements.
