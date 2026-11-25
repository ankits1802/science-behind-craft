# 0232. Every places map an agent delivers is drawn on the site's own map base for its frame, and the agent tells it what the map is about: a frame, the layers to emphasise, routes, rings, district values and a sequence that plays, each cited

A declared `map_layer` is no longer four dots on India's outline. The site draws it on its own map
base, framed to its places: relief bands with their hillshade, rivers and lakes from the open
datasets, the Survey of India outline with state and district lines, neighbouring land, water and
the Rann's salt flats in the design's map tokens, the page's home districts in the place hatch,
place names with halos, a scale bar and the India locator. Beside its places, a spec may ask for a
frame (from some of its places, or a district or a state by its LGD code), the relief, rivers or
water to emphasise and rivers to name, routes drawn as arrows, rings of a stated radius, a value
per district and a sequence of states that plays with Play, Pause and a step to press. Every route,
ring, value and step cites a fact. The web server cuts each places map's still to its frame, so the
map is whole at first paint, and a page delivered before this draws on the new base unchanged.

Date: 2026-11-26. Status: accepted (the UX round of 2026-11-26, lane `maps`, after the owner judged
Sanganeri's map, `sanganeri-hand-block-printing/geography/sanganer-and-neighbours`, far below Kutch
Ajrakh's: "If you cannot even draw maps correctly ... Do you not see the difference between the
quality of maps"). It amends
[decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) (a
contributor's map drawn by the site: the places map now draws on the same base as the timeline map)
and [decision 0220](0220-a-declared-timeline-map-complete-at-rest-from-a-still-the-server-cuts-to-its-frame.md)
(the still: a places map's still also holds neighbouring land, district lines, valued districts,
layer credits and the boundary note). The contract is `docs/contracts/component-specs-general.md`
(The places map).

| For | Read |
|---|---|
| The declared timeline map, its places and its base | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) |
| The still the server cuts to a map's frame | [decision 0220](0220-a-declared-timeline-map-complete-at-rest-from-a-still-the-server-cuts-to-its-frame.md) |
| The map stack, its physical layers and its still cuts | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md), [decision 0220](0220-a-declared-timeline-map-complete-at-rest-from-a-still-the-server-cuts-to-its-frame.md) |
| Motion, the reduced-motion switches and the design's map tokens | `kalavigyan-design`, sections 3 and 6 |
| Every decision, by group | [README.md](README.md) |

## Context

- **Two maps, two bars.** Kutch Ajrakh's map chapter is hand-drawn in its shell: a district climate
  map whose spec alone is 236 KB, a timeline map of 222 KB, and small maps of the Suran dry below
  the dam at Tapar, a 20 km ring round Dhamadka's epicentre and the move from Dhamadka to
  Ajrakhpur, each with relief, rivers, labels with halos, the India locator and a key. An agent's
  places map was drawn by `general/MapLayerView` as India's outline, numbered discs and nothing
  else, framed to the whole country: Sanganeri's four places sat in one corner of a blank India.
- **The stack was there.** The site already draws relief, hillshade, rivers, lakes, state and
  district lines, neighbouring land, salt flats, home hatches, a locator and choropleths
  (`components/map/`, decisions 0196 and 0220), and cuts a still of them on the server for the
  declared timeline map. The places map used none of it.
- **What an agent can say.** A contributor's agent cannot and must not draw geography (decision
  0196, the hand-drawn map refused). What it can do is say what the map is about from the page's
  facts: which places, the area to show, the move between two places, the distance round a place,
  a reading per district, the order in which the story unfolds.

## Decision

1. **One base under every places map.** `components/map/PlacesMap.tsx` draws a declared
   `map_layer` on `IndiaMapBase` for its frame, with the timeline map's own layers
   (`useTimelineMapLayers`: relief and rivers always, the home districts from the component's
   `place:lgd:<code>` subjects), district lines, neighbouring land, the place pins with their names
   beside them in the map label and halo tokens, a scale bar of a round number of kilometres at the
   frame's middle latitude (`mapLayerFrame.scaleBar`), the India locator with the frame marked, a
   key and the source line with the boundary note and each layer's dataset credit. The frame is cut
   to the places at a tighter zoom than the timeline map's (`MAP_LAYER_ZOOM`, at least 8 per cent
   of India's width, about 2.4 degrees), so a craft's town and its neighbours fill the map.
2. **The agent says what the map is about.** `MapParts` (`backend/app/research/component_specs_map_parts.py`)
   is the base of `GeneralMapLayerSpec` and adds six optional parts: `frame` (places, a district or
   a state), `emphasis` (layers and named rivers), `routes` (arrows between two places), `rings` (a
   stated radius round a place), `districts` (a value per district, classed into up to five groups
   of near-equal counts on the density ramp, the value printed at each centre) and `sequence` (2 to
   12 steps, each revealing its places, routes, rings or the district values over the steps before
   it). Every index is checked against the spec's own lists; every route, ring, value and step
   rests on a unit that states what it draws and cites a fact (`component_specs_map_delivery`),
   and a district, state or river the site does not hold is refused by name. A spec of the old
   shape is stored exactly as it came and draws on the new base.
3. **Whole at first paint.** `lib/server/mapStills.withMapStills` now also gives every declared
   `map_layer` a still cut to the frame its view draws, from the same bundled files, with the
   neighbouring land, district lines and valued districts the places map needs and the boundary
   note read from `/map/layers`; a named frame is cut to the shape's own box and sent as
   `still.named`, which the view frames to. The client still holds no copy of the boundary caption.
4. **A sequence plays, and stops under either switch.** The owner's instruction that a sequence
   "plays, like the timeline map" overrides the design's rule that motion runs only on a reader's
   press: a places map's sequence plays once from its first step when it comes into view, a step
   every four seconds (the reaction player's `usePlayback`), and rests on its last step with every
   mark shown. Pause stops it, Play plays it again and each step's number jumps to it. Under either
   reduced-motion switch nothing moves; the map shows its last step at once and Play steps forward
   one state per press.
5. **Comparison through the renderer's own still.** `frontend/e2e/places-map-unit.spec.ts` draws
   Sanganeri's map and a map with every part from the server's still at 390 and 1440 px and keeps
   the pictures as the `places-map-stills` artifact of Frontend checks, set against Kutch Ajrakh's
   map chapter as the parity run captured it.

## Consequences

- **Existing pages get it for free.** Sanganeri's map and every page with a declared places map
  draw on the new base at their next read, framed to their places, without being delivered again.
- **The still grows for places maps only.** A places map's still adds neighbouring land, district
  lines and the valued districts; the timeline map's still is cut as before, byte for byte.
  Sanganeri's still is under 40 KB.
- **What is left.** The rivers in the site's data are Natural Earth's at 1:10m: a town's small
  river (the Suran, the Dravyavati) is not in them, so it cannot be named or emphasised, and the
  relief is ETOPO1's one arc-minute bands. A dam, a dry river and a caravan route along a road are
  drawn by Kutch Ajrakh's shell from OpenStreetMap and are not parts a spec can ask for. The
  declared timeline map keeps its own view (`TimelineMapDeclaredView`, owned by the players lane
  this round) and draws relief and rivers only when it names them; its scale bar and locator are
  left to that view. The map sequence uses the reaction player's playback rather than the timeline
  play the players lane adds this round; the two are to be joined once both are merged.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_map_layer_parts.py` (the old shape stored unchanged; each part
validated and refused; an uncited route, ring, value or step refused, and one whose unit does not
state it; a district, state or river the site does not hold refused and one it holds allowed; the
contract stating the limits) and `frontend/e2e/places-map-unit.spec.ts` (the places map drawn with
relief, rivers, district lines, the home hatch, a scale and the locator; the Survey of India outline
always present; the old shape parsed and drawn; the still small and cut to the view's frame, a named
frame the district's own; a route, ring and sequence drawn from the spec alone and a part off its
shape drawing nothing; a sequence revealing its steps; district classes, ring and scale worked by
hand; the server's pass; the map at 390 and 1440 px), with `frontend/e2e/map-still-unit.spec.ts` and
`frontend/e2e/monograph-kinds-general-unit.spec.ts`.
