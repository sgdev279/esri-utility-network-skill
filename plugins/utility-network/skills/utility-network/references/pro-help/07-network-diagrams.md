# Utility Network — Network Diagrams (Deep Reference)
*Source: ArcGIS Pro Help, "Network Diagrams" book (doc.esri.com/en/arcgis-pro/latest/help/data/network-diagrams/)*

Network diagrams are simplified, symbolic (not necessarily geographically
accurate) representations of network connectivity — useful for schematics,
one-line diagrams, and connectivity troubleshooting views that would be
cluttered on a true geographic map.

## Vocabulary
- **Network diagram** — contains diagram junctions/edges/containers mapped to
  underlying utility (or trace) network elements. Generated from a **diagram
  template**. Rendered in a **diagram map** via a **diagram layer**, styled by
  a **diagram layer definition**.
- **Temporary by default** — a newly generated diagram is flagged for
  automatic discard once its last open diagram map view closes, unless
  explicitly persisted with **Store Diagram**.
- **Diagram template** — the named configuration (built from diagram rules)
  that determines how a diagram is generated/updated. One template can be
  marked the **active/default template** (used when generating a new diagram
  without explicitly picking a template).
- **Diagram rule** — an individual configuration step within a template (see
  rule types below); rules run in sequence during diagram build/update.

## Diagram rule types (configuration/administration tools)

All are `arcpy.nd.*` geoprocessing tools, each targeting a **utility network
or trace network** + a **named diagram template**, each with an `Active` /
`is_active` toggle (default: active).

| Rule | Purpose |
|---|---|
| **Start Iteration Rule** | Marks the beginning of a rule sequence the diagram builder will **loop over** — typically used around reduction rules, since reducing junctions changes connectivity and can make other junctions newly eligible for reduction on a subsequent pass. |
| **Collapse Container By Attribute Rule** | Collapses all content related to containers matching an **SQL filter** into a simplified representation. Optional **"Aggregate reconnected edges"** — when checked (default), edges reconnecting to the collapsed container junction are merged into a single reduction edge rather than shown individually, even if multiple original edges connected two now-collapsed junctions. |
| **Set Root Junction By Attribute Rule** | Flags junctions from a given source class/table as **root junctions** using an attribute filter — anchors/starting points for diagram layout logic. |
| **Add Spatial Query Rule** | Automatically appends new network features to a diagram based on their **spatial location relative to features already in the diagram** — both the "existing feature" set and the "candidate to append" set can be filtered by SQL expression. |
| *(others exist in the same family, e.g. reduction rules, aggregation rules — not yet pulled in detail; same parameter shape: Input Network, Input Diagram Template, Active, plus rule-specific filters)* |

### Hard constraints worth flagging in any diagram-configuration answer
- **Diagram rule configuration tools are not supported against a utility
  network/trace network *service*.** They require either a **file or mobile
  geodatabase**, or a **direct database connection** to an enterprise
  geodatabase utility/trace network. This means: diagram *templates* are
  configured from a desktop/DB-connected session, never through a published
  service — a common point of confusion for people trying to script diagram
  configuration purely through REST.
- **Changing a template's rules invalidates existing diagrams** built from it:
  every existing diagram based on that template becomes **inconsistent**,
  opening with a consistency-warning icon until explicitly updated. This is
  an important operational warning to surface before someone casually edits a
  diagram template that's in production use — it's not a live, risk-free edit.

## Cross-reference to REST/JS
The **Network Diagram service** (REST, `NetworkDiagramServer`) and the JS API's
diagram-related classes are the *consumption* side of this system — they let
an app request/render/update diagrams built from templates that were
configured here, in Pro, against a file/mobile GDB or direct DB connection.
When someone asks "how do I create a diagram template from my web app," the
accurate answer is: **you can't** — template configuration is a Pro/DB-connection-only
administrative task; the web/REST/JS layers only consume existing templates.
