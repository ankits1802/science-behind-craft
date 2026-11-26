# 0239. A zoomed map's base draws OpenStreetMap's small rivers and named dams, named by the dataset and by the site's register where they agree; a coded map's still is drawn on the base; and a places map's labels sit in a layer of screen pixels

A places map framed to a town now draws the small rivers and streams that Natural Earth leaves out,
from OpenStreetMap, and may name one, or mark a dam, in its `emphasis`. A river answers to the name
the dataset gives it and to the names of the site's river register where the two agree by name and
district, so Kutch Ajrakh's Suran can be named. A coded figure's map may name rivers and dams the
same way and read them from `kvMap`, and its still, on the page and on paper, is drawn on the site's
base with the Survey of India outline. First in this lane, on the lead's urgent report, every text
and pin of a places map is drawn at the caption size whether or not the page has hydrated.

Date: 2026-11-26. Status: accepted (the UX round of 2026-11-26, lane `map-data`,
`.lead/tools/lanes/ux-1126/map-data.md`, with the lead's urgent regression of the same day from
Monograph parity run 45772026177). It amends
[decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md)
(the places map's base, its emphasis, its still and its labels) and
[decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md) (a coded
map's base, `kvMap` and its still). The contracts are `docs/contracts/component-specs-general.md` (The
places map) and `docs/contracts/component-specs-science.md` (coded_figure); the dataset is recorded in
`docs/DATA_SOURCES.md` (Small rivers and dams).

| For | Read |
|---|---|
| The places map, its base and its still | [decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md), [decision 0220](0220-a-declared-timeline-map-complete-at-rest-from-a-still-the-server-cuts-to-its-frame.md) |
| A coded figure and its map | [decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md) |
| River names from Wikidata and OpenStreetMap | [decision 0153](0153-rivers-named-groundwater-loaded-and-region-values-chosen.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Labels the size of a heading.** Parity run 45772026177 reported SVG labels 53 to 83 px tall on
  Sanganeri's places map at 360, 834, 1440 and 1920 px. They were caption-size river and range
  labels placed for the whole of India (the Western and Eastern Ghats, the Brahmaputra, the
  Aravalli Range, the Tungabhadra, the Wainganga, the Indo-Gangetic Plain): far outside the town's
  frame, clipped from view but still in the page, with rotated boxes that tall. The same heights at
  every width, and fewer on a phone where the tiered labels hide, gave them away. Separately, the
  map sized every label in map units by `--k`, which the server sets from an assumed 640 px width,
  so before hydration or without a script a label drew at about 7 px on a phone.
- **Rivers too coarse for a town.** The base's rivers are Natural Earth's at 1:10m; the Suran below
  the dam at Tapar and the Dravyavati at Sanganer are not in them, so a map could neither draw nor
  name them, and no dam could be marked. The site's HydroRIVERS basins keep reaches with 100 km2
  upstream and are served only to signed-in readers, as HydroSHEDS' licence allows its data only
  inside the site's maps and never as a download.
- **A coded map with no outline on paper.** A coded figure's map base was drawn only in its frame,
  by script, so its still (the first paint and the export) had no outline (decision 0231's report).

## Decision

1. **Labels in screen pixels.** A places map draws every text and pin (place numbers and names, ring
   and district-value labels, the scale's figure, river, range and peak labels, emphasised rivers,
   dams) in an `svg` over the map with no `viewBox`, each placed by its share of the frame and set at
   `var(--text-caption)` with a 3 px halo (`components/map/MapLabelLayer.tsx`, `PlacesOverlay.tsx`,
   `placesMapLabels.ts`). The size no longer depends on `--k`, and a label whose point lies outside
   the frame is not drawn. The map's own `svg` holds only geometry; routes keep the fitted scale for
   their arrowheads.
2. **OpenStreetMap for the small waters.** `OSM_WATERWAYS` (ODbL), read from the Geofabrik India
   extract by the Map layers workflow (`tools/maplayers/waters.py`, `waters_body.py`): named rivers
   and streams (ways of one name that meet end to end are one river), unnamed rivers as plain lines,
   and dams named by themselves or by the one named reservoir they touch (osmium's area ids read as
   their ways and relations), each simplified at 0.002 degree. HydroRIVERS was not taken for the
   reason above; one dataset names rivers, streams, dams and reservoirs together, its extract is
   already read for river names, and Kutch Ajrakh's shell drew the Suran and the dam at Tapar from
   it. GOODD names no dam; GRanD and the National Register of Large Dams were not read this round.
3. **Tiled by region, read only by the server.** The layer is cut into tiles of two degrees (108,
   3.5 MB in all, the largest 428 KB) with an index and the server's import of each tile
   (`frontend/lib/server/watersTiles.ts`, generated). Only the web server reads them: the pass cuts a
   zoomed places map's still (a frame of at most 35 per cent of India's width) and a coded map's
   still from the tiles of its frame, so no tile reaches a phone and the still stays the only cut
   (decision 0220). Sanganeri's still with its waters stays under 40 KB.
4. **Named by the dataset, and by the register where they agree.** A river carries the dataset's
   name and, where one of its name forms and one of a register river's are the same and they share
   a district, the register's names too, with each agreement recorded. The register is the river
   names datasets and the curated dossiers' river places with their district. A places map's
   `emphasis.rivers`, a coded map's `map.rivers` and the API's check read the same names
   (`backend/app/data/layers/waters-names.json`, `held_river_names`), exactly as written.
5. **A dam marked where its record says.** `emphasis.dams` and a coded map's `map.dams` name up to 6
   dams by OpenStreetMap's name for the dam or its reservoir; each is marked at the middle of its own
   way, as the tile records it, and named. A river or dam the site does not hold is refused by name at
   placement (`held_water_problems`).
6. **A coded map's still on the base.** When a coded figure declares `map` and its still is its
   `svg[data-map]`, the web server's pass (`lib/server/codedMapStills.ts`) cuts the land, the Survey of
   India outline, the relief, rivers, district lines and named districts it asks for, the small
   waters and its named rivers and dams to the still's `viewBox`, served as `base`; the page draws it
   under the still's four theme variants (`CodedStillBase.tsx`), and the frame's base draws the named
   rivers and dams and gives them to the code as `kvMap.rivers` and `kvMap.dams`. A `base` a spec
   brings is dropped.

## Consequences

- **Sanganeri and Ajrakh.** Through the renderer's still cut: a map framed to Dhamadka and Tapar
  draws the Dhamadka stream, which OpenStreetMap names and Kutch Ajrakh's dossier records as
  "Dhamadka River (Suran)", strong and labelled "Suran" when its emphasis names the Suran, and marks
  the dam OpenStreetMap draws below the "Tappar Reservoir". Sanganeri's map draws the small waters of
  its frame; the Dravyavati is in OpenStreetMap only as a short way named "Amanisha River" and some
  unnamed river ways, so a map may name and emphasise "Amanisha River" but not "Dravyavati", which
  no open dataset in hand gives and the dossier's "Amanishah Nala (Dravyavati river)" does not match
  by any name form.
- **What is left.** A coded map's still holds no state lines (they come from a text file the server
  does not bundle; the frame draws them); a coded map wider than 35 per cent of India's width gets no
  small waters and no named rivers or dams. The page export (`services/page_export_coded`) still draws
  a coded map's still without the base. The timeline map's own labels (players lane's
  `TimelineMapDeclaredView`, the answers' `TimelinePins`) still size by `--k`. An in-frame river or
  range label rotated steeply can still be taller than parity's 48 px box although its type is the
  caption. The register agreement is read when the layer is built, so a river place a dossier gains
  answers to its name at the next build.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `frontend/e2e/places-map-unit.spec.ts`
(every text of a places map at the caption size at 390, 1440 and 1920 px with JavaScript off and on,
and no layer label outside the frame), `frontend/e2e/map-waters-unit.spec.ts` (a named small river
drawn strong and labelled and an unknown name drawing nothing, a dam marked at its record's point,
only the tiles of a zoomed frame read, the credits under the map, a coded map's still on the base
with its outline and none for a still that is not the map),
`backend/tests/research/test_map_waters.py` (a held river or dam allowed and an unknown one refused
by name, the old emphasis and coded map stored unchanged, the contracts' limits),
`tools/tests/test_maplayers_waters.py` (reading, grouping, dam naming, tiles and register agreement
from hand-made features) and `tools/tests/test_maplayers_waters_files.py` (the built files agree, keep
to their budget, hold the Suran, the Tapar dam and the Amanisha River).
