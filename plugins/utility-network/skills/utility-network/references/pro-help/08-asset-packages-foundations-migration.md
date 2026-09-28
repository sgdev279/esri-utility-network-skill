# Utility Network — Asset Packages, Foundations & Migration (Deep Reference)
*Sources: ArcGIS Solutions "Utility Network Package toolbox" reference (overview,
Apply Asset Package), Esri blog "Introducing Utility Network Foundations",
ArcGIS Solutions "Use Water Utility Network Foundation". Last reviewed: 2026-09-28.*

Most real utility networks are **not** built tool-by-tool in Pro. They start
from an Esri **Foundation**, delivered as an **asset package**, deployed with
the **Utility Network Package Tools**. Questions like "Apply Asset Package
failed", "how do I add a second domain network", or "where do I start" belong
here.

## Vocabulary

| Term | What it is |
|---|---|
| **Utility Network Foundation** | An Esri industry starter kit: instructions, an asset package (schema + rules for a domain network), a map for publishing, a map for editing, workflow examples and sample data. Distributed through the ArcGIS Solutions gallery. |
| **Asset package** | A **file geodatabase** holding a utility network's configuration as tables (`B_*` data tables, `D_*` definition tables such as `D_Configurations` and `D_Rename`) plus optional data. It's how UN schema is moved, versioned and backed up. |
| **Utility Network Package Tools** | An ArcGIS Solutions toolbox (installed separately from Pro) that turns asset packages into utility networks and back. |

## The Foundations (per Esri, Sept 2026)

Communications · District Energy · Electric · Gas and Pipeline Referencing ·
Sewer · Stormwater · Water Distribution.

Verified example — **Water Distribution Foundation**: one `Water` domain
network with a **hierarchical** tier definition — a **System** tier (whole
network) and a **Pressure** tier (pressure zones, with subnetwork controllers
on pressure-zone sources). Valves carry the attributes isolation traces rely
on (closeable, normal status).

For any other Foundation's exact tiers and asset groups, read the Foundation's
own documentation page before stating specifics — tier sets change between
Foundation releases.

## Utility Network Package toolbox — tools in workflow order

1. **Stage Utility Network** — creates the feature dataset, the utility
   network and required structure in the target geodatabase.
2. **Asset Package toolset**
   - **Apply Asset Package** — writes the asset package's schema (and
     optionally data) into the staged utility network. **Additive**: applying
     a second package adds domain networks; it never removes or modifies
     existing properties.
   - **Export Asset Package** — dumps an existing utility network's schema
     (and data) to an asset package: backup, promotion from dev → test → prod,
     or sharing a configuration.
   - (Asset Package to Geodatabase and related helpers also live here.)
3. **Data toolset** — tools that create and modify utility network features.

Typical sequence: Stage → Apply the Foundation asset package → optionally
apply more packages (add domain networks) → post-process (enable topology,
update subnetworks, update Is Connected) → publish → Export Asset Package as
a baseline.

## Apply Asset Package — parameters and prerequisites

| Parameter | Notes |
|---|---|
| Asset Package | the .gdb asset package |
| Domain networks to apply | pick which domain networks from the package |
| Utility Network Name | target network |
| Load data (optional) | append data, or apply schema only |
| Calculate Spatial Index and Analyze (optional) | helps performance on some enterprise platforms |
| Configurations to apply (optional) | options from the package's `D_Configurations` table |
| Rename option (optional) | from `D_Rename` |
| Post Process (optional) | enables topology, updates subnetworks, updates Is Connected |

**Prerequisites that cause most failures** — check these first when the
tool errors:
1. **All maps in the project are closed.**
2. **Network topology is disabled.**
3. **Pro version matches the utility network version** (see
   `09-dataset-versions-compatibility-upgrade.md`).
4. Enterprise geodatabase only:
   - the connected **portal account is the portal utility network owner**
   - the **database user is the database utility network owner**
   - you are connected to the **DEFAULT** version.

## Migrating from a geometric network or plain feature classes

Esri's documented path is the **Utility Network Migration Wizard / migration
toolset** (named in the Pro Help FAQ). The practical pattern most
implementers follow:

1. Choose the target Foundation and export it as your target asset package.
2. Map source classes/fields/subtypes to target asset groups/asset types
   (the mapping lives in the asset package's data tables).
3. Load data into the asset package (schema + data), fix data issues there —
   it's a file gdb, so iteration is fast.
4. Stage, Apply Asset Package with Load data = true, post-process.
5. Expect a large first-time error count on Enable Topology; triage by error
   code (`04-associations-editing-errors.md`) rather than fixing features one
   by one.

Scale warning: very large dirty-area counts have made Enable/Validate
Topology stall on some releases (`06-*.md`), so on big migrations enable
topology on a subset first to find systematic rule gaps.

## How to answer

- "Where do I start?" → recommend the matching Foundation + Package Tools,
  not manual `Create Utility Network`.
- "Apply Asset Package failed" → walk the four prerequisites above before
  looking at the package contents.
- "Add gas to our electric network" → Apply Asset Package is additive; apply
  the second domain network's package to the existing network (topology
  disabled, owner connection, DEFAULT).
- "Move config from test to prod" → Export Asset Package → Stage + Apply in
  prod; don't hand-recreate rules.
