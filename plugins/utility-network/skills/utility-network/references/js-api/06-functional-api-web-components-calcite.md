# Utility Network — JS: Functional Trace API, Web Components, Calcite & arcgis-rest-js (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/, developers.arcgis.com/calcite-design-system/,
developers.arcgis.com/arcgis-rest-js/*

This file closes out the JS-adjacent ecosystem: a lower-level functional
trace call most guides don't mention, the newer HTML-custom-element layer
UN widgets also ship as, where Calcite fits in, and a confirmed gap in
`arcgis-rest-js`.

## The standalone functional `trace()` call

Beyond the `UtilityNetworkTrace` widget and manually building
`TraceParameters` against a loaded `UtilityNetwork` object, there's a third,
more minimal option: a plain function that takes a service URL directly.

```javascript
import { trace } from "@arcgis/core/rest/networks/trace.js";

const result = await trace(url, params, requestOptions);
// url: the UtilityNetworkServer URL
// params: a TraceParameters object
// requestOptions: optional RequestOptions
// returns: Promise<TraceResult>
```
- Doesn't require loading a full `UtilityNetwork`/`Network` instance or a
  web map first — useful for **one-off or server-side trace calls** where
  spinning up the full object model is unnecessary overhead.
- Returns the same `TraceResult` object documented in
  `js-api/04-trace-results-and-widgets.md` — everything about interpreting
  `elements`, `aggregatedGeometry`, `globalFunctionResults`, `warnings`, etc.
  applies identically here.
- **When to use this vs. the `UtilityNetwork.trace()`-style methods**: prefer
  this functional form for scripts, background jobs, or any context that
  already knows the target URL and doesn't otherwise need the network's
  loaded schema; prefer loading a full `UtilityNetwork` instance when the app
  also needs domain network names, categories, terminal configs, or
  named-trace-configuration lookups alongside the trace itself.

## ArcGIS Web Components (`@arcgis/map-components`) — the UN widgets as custom HTML elements

Beyond the imperative widget classes (`esri/widgets/UtilityNetworkTrace`,
etc.), the same functionality ships as **framework-agnostic custom HTML
elements** — useful for teams not building around the imperative
`new Widget({...})` pattern (e.g., plain HTML, or non-Esri-centric frontend
frameworks).

Confirmed component: **`<arcgis-utility-network-validate-topology>`**
```html
<script type="module">
  import "@arcgis/map-components/components/arcgis-utility-network-validate-topology";
</script>
<arcgis-utility-network-validate-topology></arcgis-utility-network-validate-topology>
```
```javascript
const el = document.querySelector("arcgis-utility-network-validate-topology");
el.utilityNetwork = utilityNetwork;   // set programmatically, same as the widget class
el.view = view;
el.extentToValidate = "current";      // "current" | "entire" — attribute: extent-to-validate
el.componentOnReady();
```
Properties mirror the widget class closely (`extentToValidate`, `icon`,
`label`, `utilityNetwork`, `view`, a readonly `state`:
`"disabled" | "executing" | "failed" | "loading" | "ready" | "success"`).
**Same hard constraint as the widget class**: does not support proxied
feature services or feature services using stored credentials.

By the same pattern (confirmed to exist for `arcgis-map` and this component;
treat as the expected shape but verify each specific tag name against live
docs before shipping code), the other UN widgets are very likely also
available as `<arcgis-utility-network-trace>` and
`<arcgis-utility-network-associations>` custom elements — check
developers.arcgis.com's Web Components reference section for the current
confirmed list before promising a specific tag name to a user.

## Where Calcite Design System actually fits in

**Calcite itself has no utility-network-specific components** — it's Esri's
general-purpose design system (buttons, panels, inputs, shell layouts,
alerts, etc.), UN-agnostic by design. The connection is architectural, not
feature-level:
- The **ArcGIS Web Components** described above (and the imperative widgets
  they wrap) are **built using Calcite components internally** for their own
  UI chrome (buttons, panels, lists) — so styling/theming a page with a
  Calcite theme affects how the UN widgets look, even though Calcite itself
  ships no UN logic.
- **Practical implication for app builders**: if someone is building a
  **custom** UN UI (not using the ready-made widgets) — e.g., a bespoke trace
  configuration panel — Calcite is the natural component library to reach
  for the surrounding UI chrome (buttons, dropdowns, panels) so the custom
  UI visually matches the ready-made UN widgets and the rest of an
  Esri-hosted app.
- There is **no Calcite-specific trace/association/topology logic** to
  document beyond this — don't search for it further if it doesn't turn up;
  the architectural relationship above is the whole story.

## `arcgis-rest-js` — confirmed gap, same pattern as Network Diagrams

**`@esri/arcgis-rest-js` has no utility-network-specific package.** Its
published packages cover general concerns: `@esri/arcgis-rest-request`
(core request/auth plumbing), `@esri/arcgis-rest-feature-layer` (query/edit
helpers for plain feature layers), `@esri/arcgis-rest-geocoding`,
`@esri/arcgis-rest-portal`, `@esri/arcgis-rest-routing`,
`@esri/arcgis-rest-demographics`, and similar — **none targeting
`UtilityNetworkServer`, `NetworkDiagramServer`, or `VersionManagementServer`
operations**.

**What this means practically**: a Node.js/server-side script using
`arcgis-rest-js` (rather than the full `@arcgis/core` Maps SDK) that needs
to call UN REST operations must use the **generic `request()` function**
from `@esri/arcgis-rest-request` directly against the raw endpoint URLs
documented in the `rest-api/*.md` files, handling authentication via the
same package's `ArcGISIdentityManager`/`ApiKeyManager`, rather than expecting
a purpose-built `traceUtilityNetwork()`-style helper function to exist.

```javascript
import { request } from "@esri/arcgis-rest-request";

const result = await request(
  "https://myserver.esri.com/server/rest/services/LandUse/UtilityNetworkServer/trace",
  { params: { f: "json", traceType: "connected", traceLocations: [ /* ... */ ], traceConfiguration: { /* ... */ } } }
);
```
This is the right pattern to suggest when someone is specifically in a
lightweight Node/`arcgis-rest-js` context (not a full Maps SDK app) and needs
UN REST access — set the expectation clearly that they're hand-building the
request against the raw API (per `rest-api/01-*.md`'s schemas) rather than
using a dedicated wrapper, exactly like the Network Diagrams JS gap in
`js-api/03-network-class-loading-and-definition.md`.

## Practical guidance for Claude

1. Prefer the **functional `trace()` call** for suggested code in
   script/Node contexts; prefer the widget or loaded-`UtilityNetwork` object
   patterns for full map applications.
2. If someone explicitly asks for `arcgis-rest-js` or wants a lightweight
   Node dependency (not the full `@arcgis/core` bundle), tell them plainly
   there's no dedicated UN package and show the generic `request()` pattern
   — don't imply a purpose-built helper exists.
3. If someone asks about Calcite components "for utility networks,"
   redirect to the actual answer: Calcite provides general UI components;
   the UN-specific pieces are the widgets/web-components/Experience Builder
   widgets covered elsewhere in this skill, which happen to be Calcite-styled
   internally.
