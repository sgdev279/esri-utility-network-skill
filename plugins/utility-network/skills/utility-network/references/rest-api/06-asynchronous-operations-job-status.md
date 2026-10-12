# Utility Network — REST API: Asynchronous Operations & Job Status Polling (Deep Reference)
> Last reviewed: 2026-10-12 (Pro 3.7 / Enterprise 12.1 / UN dataset v8)

*Source: developers.arcgis.com/rest/services-reference/enterprise/ (URLs in the Sources list at the bottom)*

Several `UtilityNetworkServer` operations can run long enough (large trace,
full-extent validate, big subnetwork export) to need an async, poll-for-status
pattern instead of blocking the client on a single request. This is a
distinct, simpler pattern from the classic `GPServer` job system — don't
conflate the two (see the comparison at the end).

## Which operations support `async=true`

Confirmed to accept an `async` boolean parameter (default `false`):

| Operation | `async` introduced | Notes |
|---|---|---|
| `trace` | no version note on the Trace page (capability flag `supportsAsyncTrace`) | Large/complex traces on big networks are the main use case |
| `enableTopology` | 10.9.1 | Also has `maxErrorCount` (default 10,000) — the error-count threshold that stops the enable process |
| `disableTopology` | 10.9.1 | |
| `exportSubnetwork` | 10.9.1 | |
| `updateIsConnected` | 10.9.1 | Also requires being the **portal utility network owner** and topology enabled |
| `Locations` → `query` | 10.9.1 | |
| `validateNetworkTopology` | no version note on the page | Has an explicit `async` parameter (default `false`). `returnEdits` is ignored when `async=true` |
| `updateSubnetwork` | no version note on the page | Has an explicit `async` parameter (default `false`) |

Operations with **no** `async` parameter: `enableSubnetworkController`,
`disableSubnetworkController`, `synthesizeAssociationGeometries`,
`queryNetworkMoments`, `Associations` `query`/`traverse`, and the
`traceConfigurations` operations.

### Capability flags — check before assuming async is available
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
There are no separate `supportsAsync*` flags for `validateNetworkTopology` or
`updateSubnetwork` in the dataset-version-8 capabilities example. Esri's
service page does not state when each flag was introduced.
These live on the `UtilityNetworkServer` root capabilities response
(`rest-api/01-utility-network-server-and-trace.md`). **Always check the
relevant flag before relying on `async=true`** — the `async` parameters on
`enableTopology`, `disableTopology`, `exportSubnetwork`, `updateIsConnected`
and `Locations` `query` arrived at 10.9.1, so older releases don't have them;
what an older release does with an unknown `async` parameter is not
documented — **verify against the Esri docs for your version**.

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
**Documented in-flight status values for this pattern**: `Pending`,
`InProgress`; the completed body carries `status: "Completed"`. Keep polling
the same `statusUrl` while `Pending` or `InProgress` is returned.

### 3. On completion
The status URL returns the operation's normal response fields plus
`status: "Completed"`, `submissionTime` and `lastUpdatedTime` — e.g., for
`updateSubnetwork`, the completed status response includes `moment`,
`failures` (only with `continueOnFailure=true`) and `success`; for
`validateNetworkTopology`, it includes `moment`, `fullUpdate`,
`validateErrorsCreated`, `dirtyAreaCount` and `discoveredSubnetworks` as
documented in `rest-api/02-topology-and-subnetwork-management-operations.md`
(but never `serviceEdits`, even if `returnEdits` was requested). Esri's pages
for `enableTopology`, `disableTopology`, `updateIsConnected` and
`Locations` `query` do not show the completed-job body — treat it as the sync
body, but **verify against the Esri docs for your version**. There is
**no separate "fetch the result" step** beyond continuing to poll the same
URL until the terminal state's full payload appears. A failed job is reported
with `success: false` and an `error` object (`extendedCode`, `message`,
`details`); the exact `status` value for failure is not documented on these
pages.

## Don't confuse this with the classic `GPServer` job pattern

Esri's traditional geoprocessing services (`.../GPServer/<taskName>`) use a
**richer, differently-named** job model:
```json
{ "jobId": "...", "jobStatus": "esriJobSubmitted" }
```
with `jobStatus` values `esriJobNew`, `esriJobSubmitted`, `esriJobWaiting`,
`esriJobExecuting`, `esriJobSucceeded`, `esriJobFailed`, `esriJobTimedOut`,
`esriJobCancelling`, `esriJobCancelled`, `esriJobDeleting`, `esriJobDeleted`,
a `jobs/<jobId>` polling URL, and a separate `results/<paramName>`
sub-resource to fetch each output parameter once complete.

**`UtilityNetworkServer`'s async pattern is simpler and different**: a flat
`statusUrl`, only `Pending`/`InProgress` as in-flight states, and the
**completed operation's normal response body** (plus `status`) appearing directly at that
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
ExportingData | ExportingSnapshot | ExportAttachments | ImportAttachments |
ProvisioningReplica | UnRegisteringReplica | CompletedWithErrors`) with an explicit `resultUrl` once done — again,
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

## Sources
- https://developers.arcgis.com/rest/services-reference/enterprise/trace-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/enabletopology-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/disabletopology-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/validatenetworktopology-utiility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/updatesubnetwork-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/exportsubnetwork-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/updateisconnected-utility-network-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/query-locations-utilitynetwork-server/
- https://developers.arcgis.com/rest/services-reference/enterprise/utility-network-service/
- https://developers.arcgis.com/rest/services-reference/enterprise/gp-job/
- https://developers.arcgis.com/rest/services-reference/enterprise/synchronize-replica/
