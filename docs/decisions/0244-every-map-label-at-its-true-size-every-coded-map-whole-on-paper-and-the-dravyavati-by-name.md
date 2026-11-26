# 0244. Every map label at its true size, every coded map whole on its still and on paper, and the Dravyavati by name

A timeline map draws its pins, its scale's figure and its river, range and peak labels in the places
map's layer of screen pixels, so every text is the caption size with or without a script. A coded
map's still draws the state lines and, in a zoomed frame, the district lines, as a places map has
them. The page export draws a places map and a coded map on the API's own cut of the site's base,
with its credits and the boundary note, at print resolution. The river register records the
Dravyavati and the Amanisha Nallah of Jaipur as one river, cited to the Jaipur Development
Authority's EIA report and a peer-reviewed paper, so a map may name the Dravyavati; an alias without
such a source is refused.

Date: 2026-11-26. Status: accepted (the UX round of 2026-11-26, lane `map-data-2`,
`.lead/tools/lanes/ux-1126/map-data-2.md`; the owner wants no gaps). It amends
[decision 0239](0239-small-rivers-and-dams-on-the-map-base-a-coded-map-s-still-on-the-base-and-map-labels-in-screen-pixels.md)
(its "What is left": the timeline map's labels, a coded still's state lines, the export's base, the
Dravyavati), [decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md)
(the timeline map's pins and scale), [decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md)
(a coded map's base in the frame and on its still) and
[decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) (a map's
still on paper). The contracts are `docs/contracts/component-specs-general.md` (The places map, The
timeline map) and `docs/contracts/component-specs-science.md` (coded_figure); the data is recorded in
`docs/DATA_SOURCES.md` (Small rivers and dams, The paper map's base).

| For | Read |
|---|---|
| The places map's labels, small waters and the register | [decision 0239](0239-small-rivers-and-dams-on-the-map-base-a-coded-map-s-still-on-the-base-and-map-labels-in-screen-pixels.md) |
| The places map and its base | [decision 0232](0232-every-places-map-drawn-on-the-site-s-own-map-base-and-told-what-it-is-about.md) |
| A coded figure | [decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md) |
| The page export | [decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Timeline map labels by `--k`.** `TimelinePins` (a declared timeline map and an answer's) drew
  its pin numbers in map units (`MapMarks.Pin`), its scale's figure and its river, range and peak
  labels through `RotatedLabel` at `calc(var(--text-caption) * var(--k))`, with `--k` measured on
  the client from an assumed 640 px until then: about 5 px pin numbers on a phone, and labels wrong
  until hydration.
- **A coded still without state lines.** The state lines were a text file only the browser read,
  so the web server's cut of a coded map's still (decision 0239) had none, and the frame drew them
  only when the code asked for `states`.
- **Paper with no base.** The export drew a coded map's still as its SVG alone and a places map as
  its sentences alone; the API held no Survey of India outline and no state lines.
- **The Dravyavati.** OpenStreetMap names Sanganer's river only on one short way, "Amanisha River";
  the Sanganeri dossier's place "Amanishah Nala (Dravyavati river)" agrees with it by no name form.
  Searched through OpenAlex (the scholarly registry the research tools read) and the web on
  2026-11-26: the Jaipur Development Authority's EIA/EMP report for the Dravyavati River project
  (Chapter 2, 2017, on the ministry's environmental clearance portal) states "Dravyavati River was the
  active river of Jaipur which, over the time turned into a Nallah (Amanisha Nallah) ...", and
  Randhawa and Chandra (2017, doi:10.5897/JGRP2017.0620, CC BY 4.0) state "The degraded Dravayawati
  River, commonly regarded as Amanishah Nala (drain) today ...". Both give the river 47.5 km.

## Decision

1. **One layer of screen pixels for every map.** `TimelinePins` hands `IndiaMap` a `screenLayer`;
   `IndiaMap` then draws the pins there (`components/map/ScreenPins.tsx`, discs of 10 px radius, the
   number at the caption token) instead of in its `svg`, keeping the pin controls and hover card. The layer
   (`MapLabelLayer`) also holds the scale (`LabelScale`) and the physical labels
   (`PhysicalLabels`, shared with `PlacesOverlay`: ranges, rivers with the emphasised ones strong,
   peaks), each drawn only inside the frame. `useTimelineMapLayers` gives `labels(frame)` beside an
   overlay of geometry alone (the mineral symbols). `MapScale.tsx`, drawn in map units, is deleted;
   its constants moved to `MapLabelLayer`. `IndiaMap`'s `svg` is `block`, so the layer's shares fall
   on the drawing exactly.
2. **State lines everywhere a map is drawn.** The border files are JSON (`{schemaVersion, lines}`,
   the same encoded lines): the browser fetches them, and the web server imports
   `state-borders.json` into its still files. A coded map's still now carries `states` always and
   `districts` when asked or in a frame of at most 35 per cent of India's width
   (`mapLayerFrame.drawsDistrictLines`), and the frame's base does the same, so the still and the
   live frame agree; `states` in `map.layers` is still accepted and changes nothing.
3. **The base on paper.** The API holds the outline and the state lines the web map draws
   (`backend/app/data/layers/india-outline.json`, `state-borders.json`), mirrored by
   `tools/maplayers_mirror.py` and by the map layers build. `app/geo/map_base.py` cuts the base for a
   frame in the web map's projection (the India frame, width 1000, padding 24): the land with its
   holes, the coast as lines, relief bands by their ETOPO1 step, Natural Earth rivers and lakes,
   state lines, district lines in a zoomed frame or when asked, the home districts' edges.
   `services/export_map_base.py` paints it in the light theme's map tokens. `places_map_figure`
   (registered for `map_layer`) frames a declared places map as the web does (its places and rings at
   `MAP_LAYER_ZOOM`, a named district or state at `NAMED_ZOOM`), pins and numbers its places, draws
   its routes and lists each part's sentence; `coded_figure_figure` draws a coded still whose root is
   `svg[data-map]` over the base cut to its `viewBox`. Both credit the layers they draw (ETOPO1,
   Natural Earth, the district shapes when lines or homes are drawn) and print the boundary note. A
   map still carries `pixels`, so Word draws it 1800 pixels across: 300 dots an inch over its 150 mm.
   OpenStreetMap's small waters are left to the web, whose tiles the API does not hold.
4. **A river alias, cited or refused.** `backend/app/data/rivers/river_aliases.json` (`RIVER_ALIASES`,
   `app/data/river_aliases.py`) records names that sources state are one river, with its districts
   and sources (address, grade, quote, locator, day read). An alias is refused without a source,
   when a quote names fewer than two of its names, or when a name is quoted by none. The register
   (`tools/maplayers/waters_register.site_register`) adds each alias as a river of many names, so an
   OpenStreetMap river that agrees with any of them by a name form and a district answers to all of
   them, the agreement recorded as `RIVER_ALIASES:<id>`. `tools/maplayers_register.py` reads the
   register into the built tiles and the API's names file again without downloading OpenStreetMap
   (`waters_names.registered_waters`, shared with the build); this run renamed one tile, e074n26.
5. **How much of the Dravyavati a map draws.** OpenStreetMap's "Amanisha River" is one way of about
   0.8 km in Jaipur city (near 26.94 N, 75.79 E); the river runs 47.5 km from the Nahargarh hills to
   the Dhund. A map naming "Dravyavati" draws that way strong and labelled "Dravyavati", and the
   page's cited sentence carries the course; no line is drawn that the dataset does not hold.

## Consequences

- **Tests that encoded the refused Dravyavati changed.** `test_map_waters.py`,
  `test_map_layer_parts.py` and `map-waters-unit.spec.ts` refused "Dravyavati" as a name the site does
  not hold; the owner's direction makes it held, so they now hold it and refuse an unrecorded name
  ("Saraswati of Sanganer", "Dhamadka Creek").
- **The Map layers workflow** runs on this change (its paths include `tools/maplayers`); it rebuilds
  from the downloads and tests the rebuilt tiles, which carry the alias the same way.
- **What is left.** OpenStreetMap's small waters and an emphasised small river are not drawn on paper.
  A places map's still draws its state lines once its script loads (`StateLines`), not from the
  still. The timeline map's export still is unchanged (district outlines of its states). The answers'
  zoom and supply maps keep their pins in the `svg`.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`frontend/e2e/timeline-map-labels-unit.spec.ts` (every text of a timeline map at the caption size at
390, 1440 and 1920 px with JavaScript off and on, the pins and scale in the layer, no layer label
outside the frame), `frontend/e2e/map-waters-unit.spec.ts` (a coded still's state and district lines,
the Dravyavati named through its alias and drawn on the Amanisha way, an unrecorded name drawing
nothing), `backend/tests/exports/test_map_exports.py` (a places map and a coded map on paper on the
base with their credits and boundary note, a still that is not the map without it, 300 dots an
inch), `backend/tests/geo/test_map_base.py` (the web map's projection and frame, the base cut to a
zoomed frame), `backend/tests/geo/test_river_aliases.py` (the Dravyavati's cited alias, an alias
without a source refused, a one-name quote refused), `tools/tests/test_maplayers_waters_names.py`
and `test_maplayers_waters_files.py` (the alias agrees in its district only, the committed tiles
carry the register as it stands) and `tools/tests/test_maplayers_mirror.py` (the API's outline and
state lines are the web map's).
