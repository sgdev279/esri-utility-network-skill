# Utility Network — Dataset Versions, Compatibility & Upgrade (Deep Reference)
*Sources: ArcGIS Pro Help "Utility network compatibility", "Utility network
upgrade history", "Utility network dataset administration" (latest docs,
Pro 3.7 / Enterprise 12.1 era). Last reviewed: 2026-09-28.*

"Can Pro 3.x open our network?", "should we upgrade to version 7?", "Field
Maps stopped working after the upgrade" — all of these depend on the
**utility network dataset version** (Describe `schemaGeneration`), which is
separate from the Pro and Enterprise release numbers.

## Compatibility matrix

| UN dataset version | Minimum ArcGIS Pro | Minimum ArcGIS Enterprise |
|---|---|---|
| 4 | 2.6 | 10.8.1 |
| 5 | 2.7 | 10.9 |
| 6 | 3.0 | 11.0 |
| 7 | 3.3 | 11.3 |
| 8 | 3.7 | 12.1 |

- **Version 7 is still the default** for new networks. Version 8 must be
  chosen explicitly and is mainly for the **telecom domain network**.
- **ArcGIS Field Maps and the ArcGIS Maps SDKs for Native Apps do not support
  version 8.** Don't upgrade a network used by field apps to 8 without
  checking this first.

### Client/service rules
- **Newer clients always work with older networks** (Pro 3.5 with v7 on
  Enterprise 11.5; Pro 3.3 with v4–5 on 10.9.1–11.3).
- **Older Pro can use a newer network through services** if the Enterprise
  release supports it and the work doesn't touch newer functionality (Pro 3.3
  with v7 on 11.5; Pro 3.5 with v7 on 12.1).
- Limits: an older Pro **cannot share (publish)** a newer network version,
  and cannot open it **locally** in a single-user deployment (e.g. Pro 3.1
  with v7). Enterprise must also support the version (Pro 3.7 can't share v8
  to Enterprise 11.1).
- Newer data features — big integer fields, 64-bit ObjectIDs, newer Arcade
  versions in attribute rules — can lock out older clients even when the
  version table says they're compatible.

## What each version added

| Version | Added | Schema changes worth knowing | Prerequisites / after upgrade |
|---|---|---|---|
| 8 | Propagation resetters, telecom domain network, faster tracing through nonspatial objects | `PARTITIONID` on all domain/structure classes; "Propagator Resetter" system category; new diagram unit fields | Enterprise gdb ≥ 11.2.0 |
| 7 | 64-bit ObjectIDs, big integer fields, directional tracing via a flow-direction field | ObjectIDs → 64-bit; `FLOWDIRECTION` on line/edge-object classes; `ERRORCODE` double → big integer | Enterprise gdb ≥ 11.2.0 |
| 6 | Internal improvements for network diagrams | `ASSOCIATIONTYPE` became the subtype field of the associations table | — |
| 5 | Named trace configurations, more subnetwork definition options | `SUPPORTINGSUBNETWORKNAME`; `UN_<ID>_TRACECONFIGURATIONS` table | Review service settings |
| 4 | New dirty-area/error model, nonspatial junction/edge objects | Error sublayers removed; new nonspatial object tables; `SUPPORTEDSUBNETWORKNAME` | Register as branch versioned, enable topology, re-add the UN layer to maps, reconcile all named versions |

Practical consequences:
- Named trace configurations (and everything in REST/JS that uses them)
  need **v5+**.
- Scripts that read `ERRORCODE` as a float, or assume 32-bit ObjectIDs, can
  break at **v7**.

## Upgrade Dataset — how to run it safely

Tool: **Upgrade Dataset** (Data Management) on the utility network.

Before running:
1. Save all edits; reconcile/post named versions you care about.
2. Get an **exclusive lock**: stop the feature service and close every
   connection.
3. **Disable network topology.**
4. Enterprise:
   - connect as the **database utility network owner** with branch versioning
   - be signed in to Pro as the **portal utility network owner**
   - geodatabase must be ≥ **10.8.1.2.6** (targets up to v6) or ≥ **11.2.0**
     (targets v7+). Upgrade the geodatabase first if needed.
5. Take a backup (database backup, or Export Asset Package for schema).

After: re-enable topology, restart and review the service, re-add UN layers
in maps, and test field apps against the new version.

## How to answer

- Always ask for (or find) three numbers: **UN dataset version, Pro
  version, Enterprise version**. Most "it doesn't work" compatibility
  questions resolve from the matrix.
- When someone plans an upgrade, list the downstream clients (Field Maps,
  Native SDK apps, older Pro seats, scripts reading `ERRORCODE`) that the
  target version affects.
- For facts newer than this file's review date, point to the "Utility network
  compatibility" page.
