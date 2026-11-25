# 0220. A declared timeline map is complete at rest: the server cuts its relief, rivers and home hatch into a small still for its frame, drawn in the map tokens until each layer's file lands, and its minerals key and district legend are drawn whole from data the server holds

When the site's web server reads a page, it cuts each declared timeline map's relief bands, rivers,
lakes and home districts to the frame the map is drawn in, simplifies them to a grid of 500 steps
across that frame and sends them in the map's spec as its `still`, with the minerals key's classes
and counts and a district layer's legend. The view draws the still at first paint in the design's
map tokens, so it follows every theme, and each layer's own drawing takes its part's place in the
same spot when its file lands. The minerals key and a district legend are drawn whole at rest from
the still, exactly as they draw once their data lands.

Date: 2026-11-25. Status: accepted (the lead's leftovers lane `maps` of the review of the quality
round, items 1 and 2 of "Lane maps" in the round's brief; they close what
[decision 0216](0216-a-contributed-drawing-loads-nothing-a-timeline-map-s-key-holds-its-place-and-download-fails-gently.md)
left of finding `web-4` of `.lead/data/advreview-1125/review.json`). It amends decision 0216
(what a declared timeline map's still holds, item 2) and
[decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) (how the
declared timeline map draws its layers). The contract is `docs/contracts/component-specs-general.md`
(The declared timeline map, The still); the design's rule is `kalavigyan-design` section 6.

| For | Read |
|---|---|
| The declared timeline map, its places and layers | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) |
| The key held at rest and the layer files asked for once the page is idle | [decision 0216](0216-a-contributed-drawing-loads-nothing-a-timeline-map-s-key-holds-its-place-and-download-fails-gently.md) |
| Heavy kinds loaded near after their still, and the phone budget | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| The lead chapter drawn by the server and the rest read later | [decision 0209](0209-a-phone-load-s-path-to-its-first-screen-recorded-and-cut.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The map's area and line layers waited on its code and its files.** A declared timeline map's
  relief bands, rivers, lakes and home hatch were drawn from `relief.json` (119 KB), `rivers.json`
  (32 KB) and `district-shapes.json` (278 KB), fetched in effects once the near view had hydrated,
  so a page's HTML and a reader at pace met a bare map. Drawing the layers whole on the server would
  send 451.6 KB of path data for the Bidriware map's relief, rivers and home district, twice:
  in the HTML and again in the page's payload for hydration.
- **The keys that need a file were a line off or more.** The minerals key and a district layer's
  legend held a legend-shaped skeleton (decision 0216), a title, a bar and six short lines, while
  the minerals key draws six rows with a bar under each and labels that wrap on a phone
  ("Manganese, chromium and alloy metals"), and a district legend draws a caption and a dataset
  credit the skeleton had no lines for. Their height cannot be reserved without the labels, and
  the labels live in the files.

## Decision

1. **A still cut on the server, small enough to send.** Four ways were weighed. A raster (WebP)
   still per extent bakes token values into pixels: it needs a server image renderer, two to four
   renders per map for the themes, and CSS that repeats the theme rules to pick one, and it cannot
   follow forced colours. An SVG file per extent loaded as an image cannot read the page's custom
   properties, so it has the same problem. A still written by the backend at placement would need
   a second copy of the web's projection and frame in Python, and a migration for stored specs.
   The chosen way is an inline SVG still the web's server cuts at read, in the map tokens, so every
   theme, high contrast and forced colours follow by themselves. `lib/server/mapStills.withMapStills`
   runs where every reader route reads a document (`lib/monographRenderServer.documentRead`: the
   craft and category pages, their editions and translations and the rest route; the preview; and
   `/design/kinds`). For each declared timeline map it takes the frame the view draws
   (`components/map/timelineMapStill.timelineMapFrame`, the same function the view calls) and cuts,
   with `components/map/mapStillCut.ts` and `components/map/stillGeometry.ts`, from the layer files
   bundled with the server (`lib/server/mapLayerFiles.ts`, loaded only when a page holds such a
   map): the land below the first elevation break and each relief band, the rivers by rank and the
   lakes, clipped to the frame with a two-step margin (so no clipped edge is stroked inside the
   view), simplified within one step, rings under four square steps dropped, written as relative
   paths in whole steps under one `translate` and `scale`; the home districts in tenths of a map
   unit with no scale, so the place hatch's pattern matches the layer's; the minerals key's rows
   (`lib/mapPhysical.mineralKeyRows`); and a district layer's legend (`lib/regionView.layerLegend`),
   read from `/map/layers/{id}` with the same parse the browser uses (`parsedMapLayer`). Each
   frame's geometry is kept in memory, up to 200 frames. The still is sent in the spec as `still`,
   and any `still` a stored timeline map spec brings is removed first; the backend's model refuses
   one from a contributor as an unknown field, and the web parses a still only in its own shape.
2. **Drawn at first paint and replaced in place.** The view draws each part of the still beneath
   its pins (`components/map/MapStillLayers.tsx`: `--elevation-1` to `--elevation-7` under the
   district rule, `--map-river` and `--map-water`, the place hatch), and each layer's own drawing
   takes that part's place in the same `svg` when its file lands
   (`TimelineMapLayers.ReliefUnderOrStill`, `RiversUnderOrStill`, `HomeOrStill`), so nothing moves;
   a still whose box is not the view's frame is not drawn. The full layers still load, prefetched
   at idle (decision 0216), for their hillshade, labels, peaks and full detail.
3. **The keys whole at rest.** `MineralKey` draws from rows, the minerals file's or the still's,
   and `LayerStatus` draws a held legend (`ChoroplethKey`) until the layer and the shapes land, so
   each key's markup at rest is the markup it draws once its data lands. The skeleton is left only
   where no still holds the key: a district layer the server could not read.
4. **Cut only on the server.** No chain from the craft page's client code, the rest's chunks or
   the near views reaches the cutter or the layer files it reads, and the unit spec says so.

## Consequences

- **The bytes.** The Bidriware map's still is 28.2 KB of JSON, against 451.6 KB of path data for
  the same layers drawn whole (measured by `map-still-unit.spec.ts`, which fails over 40 KB or over
  a tenth of the whole). A map in a page's first chapter sends it in the HTML and again in the
  payload; a map in a later chapter, as on the page of every kind, sends it only in the rest, which
  is read after the first screen. On the phone budget's run (45597915081) against the release
  branch's (45589710132), each page's JavaScript grew 0.7 KB (Kutch Ajrakh 684.3 to 685.0 KB, the
  page of every kind 702.1 to 702.8 KB), its document stayed 39.5 and 21.5 KB, its largest element
  moved 20 and 16 ms and its shift stayed 0.0293 loading and 0 reading; both are within
  `e2e/phone-budget.json`, which is not re-recorded.
- **A page's digest now holds its stills.** The cut is deterministic, so the page and its rest
  route agree; a district legend read that fails for one and not the other changes the digest, and
  the rest route then reads the page's version, as for any changed page.
- **What is left.** The mineral symbols (534 sites in the Bidriware frame, about 19 KB as symbols)
  and a district layer's fills (about 79 KB in that frame) are still drawn from their files once
  the view loads; the base map's neighbouring land and state lines on every map, and the relief's
  hillshade and the range, peak and river labels, arrive as before. A district legend at rest
  depends on the server's read of the layer, kept an hour, and otherwise holds the skeleton. These
  stay here and in the report, not in the debt register.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `frontend/e2e/map-still-unit.spec.ts`
(the clipping, simplifying and paths worked by hand; the Bidriware still cut to the view's frame and
its size against the layers drawn whole; the map drawn at rest from the still in the map tokens and
without it from a bare spec or a still cut for another frame; each layer taking its part's place
when its file lands; the minerals key and a district legend drawn at rest exactly as once their data
lands, and the skeleton without a still; a district map's legend held and a map with nothing to wait
for given no still; the server's pass giving a declared map its own still, replacing a brought one
and leaving the authored map without one; the bundled files cutting the same still; a still read
only in its shape; and no client chain reaching the cutter or its files), with
`frontend/e2e/timeline-map-declared-unit.spec.ts` and `frontend/e2e/near-views-unit.spec.ts`.
