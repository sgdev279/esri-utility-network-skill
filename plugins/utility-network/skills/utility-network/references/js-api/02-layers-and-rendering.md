# Utility Network — JS API: Layers & Rendering (SubtypeGroupLayer) (Deep Reference)
*Source: developers.arcgis.com/javascript/latest/*

## Why this matters for every UN web app

Utility network feature classes are published from Pro with **subtypes**
(recall: `ASSETGROUP` is literally the geodatabase subtype field — see
`pro-help/02-structure-of-a-utility-network.md`). A UN layer with dozens of
asset groups/types needs per-subtype symbology, popups, and visibility — and
the JS API has a **purpose-built layer type** for exactly this instead of
publishing one feature service per subtype.

## `SubtypeGroupLayer`

```javascript
import SubtypeGroupLayer from "@arcgis/core/layers/SubtypeGroupLayer.js";
```
- **Since 4.20**. Inheritance: `SubtypeGroupLayer → Layer → Accessor`.
- A **single layer** that automatically creates one **`SubtypeSublayer`** per
  subtype found in its source feature service — each sublayer gets its own
  visibility, renderer, popup, and label properties, while **all sublayers
  share one underlying feature source/request** (panning/zooming issues a
  single request, not one per subtype) — this is the key performance win
  over publishing N separate feature layers.
- **Hard requirement**: the source feature service **must be published with a
  subtype field**, or the layer fails to load.
- **2D MapViews only** — not supported in a SceneView. **Clustering is not
  supported.** **`DotDensityRenderer` is not supported.**

### Creating from a service URL
```javascript
const stgl = new SubtypeGroupLayer({
  url: "https://sampleserver7.arcgisonline.com/server/rest/services/UtilityNetwork/NapervilleElectric/FeatureServer/0"
});
map.add(stgl);
```

### Creating from a portal item
```javascript
const stgl = new SubtypeGroupLayer({
  portalItem: { id: "8444e275037549c1acab02d2626daae" }
});
map.add(stgl);
```

### Configuring individual sublayers at construction time
```javascript
const stgl = new SubtypeGroupLayer({
  url: "...FeatureServer/0",
  sublayers: [   // autocasts as a Collection of SubtypeSublayer
    { subtypeCode: 12, visible: true,  renderer: simpleRenderer },
    { subtypeCode: 14, visible: false, renderer: classBreaksRenderer },
    { subtypeCode: 16, visible: true,  renderer: classBreaksRenderer, popupTemplate }
  ],
  outFields: ["assettype", "assetgroup", "objectid", "transformer_kva", "subnetworkname"]
});
```
- **Passing a `sublayers` array limits which subtypes actually load** — only
  listed `subtypeCode`s become sublayers; this is a common gotcha when
  someone expects *all* subtypes to appear but only configured a few.
- Set `outFields` at the group level to make asset-group/asset-type and any
  other attributes available for **client-side filtering, labeling, and
  popups** across all sublayers without extra requests.

## `SubtypeSublayer`

```javascript
import SubtypeSublayer from "@arcgis/core/layers/support/SubtypeSublayer.js";
```
- **Not a standalone service** — each instance corresponds to one subtype in
  the parent `SubtypeGroupLayer`'s single source service. This is explicitly
  different from `MapImageLayer` sublayers, which **are** individual map
  services — don't assume the two "sublayer" concepts behave the same way
  when porting code or mental models between them.
- Identified by **`subtypeCode`** (the actual subtype/asset-group integer
  code from the geodatabase).
- Supports **`SimpleRenderer`, `UniqueValueRenderer`, or `ClassBreaksRenderer`**
  independently per sublayer — a very common UN pattern is `UniqueValueRenderer`
  keyed on `ASSETTYPE` **within** a sublayer already split by `ASSETGROUP`
  (i.e., two-level classification, matching the asset group → asset type
  model exactly).
- Each sublayer can have its **own min/max visibility scale** — useful for
  "only show secondary conductors below 1:5,000" style UN cartography
  requirements.

## Practical guidance for Claude

- Whenever someone asks "how do I symbolize my utility network layer in
  JS," default to `SubtypeGroupLayer`/`SubtypeSublayer`, **not** a plain
  `FeatureLayer` with a single renderer — a plain `FeatureLayer` can't cleanly
  express independent per-asset-group symbology, and re-publishing per
  subtype as separate services is the anti-pattern this class exists to
  avoid.
- If someone's sublayers "aren't showing up," check whether they explicitly
  passed a `sublayers` array that only lists a subset of `subtypeCode`s.
- Remind them the source service needs a subtype field published from Pro
  — if their data isn't showing any subtypes at all, that's very likely a
  publishing-time problem, not a client-code problem.
- For rendering **associations** (dashed connector lines, etc.) rather than
  network features themselves, that's the `UtilityNetworkAssociations`
  widget/`SynthesizeAssociationGeometriesParameters` path covered in
  `js-api/05-editing-associations-validation.md`, not `SubtypeGroupLayer`.
