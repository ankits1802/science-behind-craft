# 0246. The last small gaps: small waters on paper, state lines and answer pins at first paint, map downloads that wait and try their mirrors, clip addresses renewed on an open page, clip stills cut at delivery, and a review link that opens its proposal

The PDF and Word maps draw OpenStreetMap's small rivers and dams in a town's frame, the river and
dam a map names strong and named, from a copy of the tiles the API now holds. A places map's still
carries its state lines, so they are drawn at first paint. The answers' supply map draws its pins and
the zoom map its district's name in the layer of screen pixels at the caption size. The Map layers
workflow tries each download at every mirror with a growing wait, checks what it receives, keeps the
ETOPO1 grid in a cache every pull request can read, and fails, naming every address, only when every
address of a file fails. A coded figure's clip address is renewed before it ends and on a play after
it ended, and the frame takes the new address without a reload. A clip's still is cut when the figure
is delivered, so the first export and the Review page have it at once. A review link opens the page
proposal it names even when the Review page does not list it, and says plainly when the person may
not review it.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-1126/polish`, on the owner's word that
no gaps are left; the review link added by the lead the same day). It amends
[decision 0244](0244-every-map-label-at-its-true-size-every-coded-map-whole-on-paper-and-the-dravyavati-by-name.md)
(its "What is left": small waters on paper, a places map's state lines, the answers' pins),
[decision 0239](0239-small-rivers-and-dams-on-the-map-base-a-coded-map-s-still-on-the-base-and-map-labels-in-screen-pixels.md)
(the small waters read only by the web server, the Map layers downloads),
[decision 0245](0245-the-round-s-leftovers-every-upload-scanned-a-held-page-s-critique-films-from-the-media-store-and-upgrade-work.md)
(its "Left as they are": a clip's address not renewed, a still cut on the first export) and
[decision 0243](0243-a-staged-decision-confirmed-in-the-person-s-own-mcp-client.md) (a proposal the Review
page does not list is not opened by its link). The contracts are
`docs/contracts/component-specs-general.md` (The places map: its still and paper),
`component-specs-science.md` (coded_figure: paper, `films`, the export and the Review page),
`craft-page.md` (the clip routes) and `review-queue.md` (A link to one proposal); the data is recorded
in `docs/DATA_SOURCES.md` (the relief layer's downloads, Small rivers and dams, The paper map's base).

| For | Read |
|---|---|
| The small waters, the map base and its labels | [decision 0239](0239-small-rivers-and-dams-on-the-map-base-a-coded-map-s-still-on-the-base-and-map-labels-in-screen-pixels.md), [decision 0244](0244-every-map-label-at-its-true-size-every-coded-map-whole-on-paper-and-the-dravyavati-by-name.md) |
| A coded figure's films from the media store | [decision 0245](0245-the-round-s-leftovers-every-upload-scanned-a-held-page-s-critique-films-from-the-media-store-and-upgrade-work.md) |
| The review link | [decision 0243](0243-a-staged-decision-confirmed-in-the-person-s-own-mcp-client.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Small waters on paper.** OpenStreetMap's tiles lived in `frontend/public/layers/waters`, which only
  the web server reads; the backend release is `git archive` of `backend` and `infra/deploy`, so the
  API held no tile and the export drew no small river or dam.
- **State lines after the script.** A places map's still held relief, rivers, district lines and the
  neighbours, but its state lines came from `StateLines`, which fetches the border file once the
  script runs: missing in the server's markup and without a script.
- **The answers' pins in map units.** `SupplyPins` drew its numbered pins with `MapMarks.Pin` in the
  map's `svg`, and `ZoomDistrictMap` its district tag at a fixed 17 map units, then scaled the map by
  a CSS transform up to three times: the text's size depended on the column's width and on the zoom.
- **Flaky downloads.** Of the Map layers runs of 24 to 26 November, every failure but one was NOAA's
  two ERDDAP servers answering 403 to the runner (runs 45797104933, 45794079387, 45777392515); the
  ETOPO1 cache never helped a new pull request because Actions shares a cache only from `main`, and
  every saved key was a pull request's (`refs/pull/221`, `230`, `232`). A refused download ended the
  step with `curl: (22)` and no account of what had been tried.
- **Clips.** A coded figure's frame got one 5-minute address; a film not loaded by then stayed still
  until the page was opened again. The still was cut on the first export, so the first export waited
  on ffmpeg and the Review page showed no still at all.
- **The review link.** The Review page listed at most twenty waiting proposals of other accounts, and
  a link to any other proposal scrolled to nothing.

## Decision

1. **The API holds the tiles; paper draws them.** `tools/maplayers/mirror.mirror_waters` copies
   `waters.json` and every tile byte for byte into `backend/app/data/layers` (3.6 MB), removing a tile
   the web no longer draws; the map layers build, `tools/maplayers_mirror.py` and
   `tools/maplayers_register.py` all run it, and `tools/tests/test_maplayers_mirror.py` holds the copy
   equal. `app/data/water_tiles` reads the index and a tile it lists (schema 1, refusing any other);
   `app/geo/map_waters` cuts them as the web's `waterLayer.cutWaters` does: only in a frame of at most
   35 per cent of India's width (`shows_waters`, the district lines' rule), every river and unnamed
   line as thin water, each named river strong over a halo with its name at the middle of its longest
   run, each named dam marked by a bar and named, nothing for a name the tiles lack.
   `services/export_map_base.paper_base(box, ask, waters)` paints them with the base and returns the
   still and its datasets together (`PaperBase`), adding `OSM_WATERWAYS` only when something was
   drawn; a places map asks for its plain waters and `emphasis.rivers` and `emphasis.dams`, a coded
   map for its plain waters only when `map.layers` names `rivers`, always for `map.rivers` and
   `map.dams`. The paper's widths and label size are shares of the frame like the rest of the base.
2. **State lines in the still.** `mapStillCut.baseParts` cuts the state lines to the frame
   (`states`, in `mapStillShape`), `PlacesMap` hands them to `IndiaMapBase` as `StillStates`, and
   `IndiaMapBase` loads the border file only when no still is given. A still whose frame crosses no
   state line draws none and loads nothing.
3. **The answers' maps in screen pixels.** `SupplyPins` hands `IndiaMap` a `screenLayer` of
   `ScreenPins`, as the timeline map does. `ZoomDistrictMap` draws its district's name and point in a
   `MapLabelLayer` outside the zoomed drawing, placed on the box the zoom shows
   (`journeyGeometry.zoomedBox`: the transform's translate and scale read back as a map box), so the
   name is the caption size at every width and zoom and sits on the district. The name turns to end
   at the point past 60 per cent of the width so it is not clipped. `DistrictTag` stays for the map
   layer views, which are not this lane's.
4. **Downloads that wait, try their mirrors and say why.** `tools/maplayers_fetch.py` over
   `tools/maplayers/fetch.py` replaces the workflow's `curl` lines. Each file has its addresses in
   `maplayers/sources.py` (the one home of the URLs the workflow held): Natural Earth's CDN then its S3
   bucket, NOAA's coastwatch ERDDAP then upwell, the USGS, Geofabrik then openstreetmap.fr's India
   extract (checked on 2026-11-26 to list `india-latest.osm.pbf`; six other ERDDAP servers were checked
   and serve no `etopo180`). Each address is tried up to four times, waiting 10, 20 and 40 seconds or
   the server's `Retry-After` kept to two minutes; a missing file (400, 401, 404, 405, 410, 414, 451) is
   not asked for again. What comes back is checked before it is kept (an ESRI grid header, a PBF
   header, a zip holding its shapefile), so an error page answered with 200 is a refusal too. A file
   already present and whole, the ETOPO1 grid the cache restored, is not downloaded. The address each
   file came from goes to `fetched.json`, which `Downloads.source` records as the dataset's `url`. Only
   when every address of a file fails does the run stop, with one error naming each address and its
   last reason. The workflow now also runs on a push to `main` touching the map layers' tools and twice
   a week, on those runs fetching only the ETOPO1 grid into the cache keyed `etopo1-ice-india-v1`, so
   the key lives on `main`, where every pull request can restore it.
5. **Clip addresses renewed.** `clipLinks` keeps each link's `expiresAt`; `lib/clipRenewal` asks
   `/film` again a minute before an address ends (`RENEW_AHEAD_MS`), and every 15 seconds after a
   failed renewal while the address lasts, and posts `{kvFilms, kvFilmEnds}` to the frame, which knows
   each clip's end (`kv-film-ends`). The frame moves a paused or failed film to the new address at the
   time it had reached; a film playing on keeps its address until it pauses, fails or ends. A play
   after an address ended, or a failure on an ended one, holds the film and asks the page
   (`{kvFilmAsk: key}`, heard only from the frame's own window, `filmAskFrom`), and the renewed address
   plays on from where it was. The frame's document is never rebuilt, and its policy already names the
   object's path without the query, so a renewed address of the same clip needs no new policy. A
   message for a key that is no clip of the figure, or an address that is not a string, changes
   nothing.
6. **Stills at delivery.** `filmed_spec` returns the clips it holds and `CheckedDelivery` carries
   them; `propose_component`, the one door of every delivered component (the site, MCP, a page proposal,
   a held page's confirmation), cuts their stills with `clip_stills.delivered_stills` once the proposal
   is stored. A cut that fails, a store that does not answer or no bucket never refuses the delivery;
   the first export cuts it then, as before. The Review page draws each clip's still with its credit
   under the figure's own still (`ClipStills`), and says in words when it cannot be shown.
7. **A review link opens its proposal.** Once the list is in, a linked id the list does not hold is read
   by `GET /api/review-queue/pages/{id}` (`linkToRead`) and drawn first, open (`withLinked`). A 403 (the
   person's own proposal), a 404 or any other failure is said in one sentence above the list
   (`linkRefusal`), and an account below Admin is told that Admins review page proposals; the routes'
   own checks are unchanged.
8. **The owner's words over the design skill.** None here: the labels follow the skill's trap on map
   labels, which now names the answers' maps and the places map's state lines.
9. No migration and no new dependency.

## Consequences

- Tested both ways. Small waters on paper: `backend/tests/geo/test_map_waters_base.py` (a town's frame
  reads its two tiles and a wide one none, the Suran strong on its own line and the Tappar dam at its
  record's point, an unknown river or dam drawn nowhere, a coded map without its rivers layer drawing
  only what it names, a tile the index does not list refused), `backend/tests/exports/test_map_exports.py`
  (a Kutch places map on paper with the Suran and the dam named and OpenStreetMap credited, one naming
  nothing drawing the waters unnamed, the wide Bidriware map crediting no OpenStreetMap, a coded map
  naming them and one without them) and `tools/tests/test_maplayers_mirror.py` (the API's copy equal to
  the web's, a changed and a dropped tile followed). State lines: `frontend/e2e/places-map-unit.spec.ts`
  (a map crossing a state border draws them from its still and loads none; one without its still has
  none in its markup). The answers' maps: `frontend/e2e/answer-map-labels-unit.spec.ts` (every pin and
  name at the caption size at 390, 1440 and 1920 px with JavaScript off and on, none in the map's own
  drawing, the zoom's name at the district's point zoomed and at rest). Downloads:
  `tools/tests/test_maplayers_fetch.py` (a refusal tried again after 10 and 20 seconds, the mirror
  after four refusals and recorded, a missing file not asked again, `Retry-After` capped, a failure
  only when every address fails and naming each, an error page refused, a kept grid not downloaded and
  a broken one replaced, a zip without its shapefile refused). Clips:
  `frontend/e2e/clip-renewal-unit.spec.ts` (renewed a minute before its end and again, an ask after the
  end renewed at once and one for no clip ignored, a failed renewal tried again only while the address
  lasts, a stopped renewal silent, only the frame's window asking, a play after the end held and asking
  and the renewed address taken in the same document, one before the end asking nothing) and
  `coded-clips-unit.spec.ts` (the link's end kept; each clip's still on the Review page at the address
  paper reads and none without clips); `backend/tests/media/test_clip_routes.py` (a delivered clip's
  still cut once and kept, nothing kept without a bucket, a cut or a store that fails leaving it to the
  first export) and `backend/tests/db/test_coded_clips_db.py` (a delivered figure's clip cut at
  delivery, a figure without clips cutting nothing, the held clip carried from `filmed_spec`). The
  review link: `frontend/e2e/review-pages-unit.spec.ts` (read only once the list is in and only when it
  does not hold it, drawn first and open, each refusal in its sentence and nothing drawn for it).
- Tests that encoded the old behaviour changed: `coded-clips-unit.spec.ts` read `clipLinks` as
  addresses alone and now reads each link with its end.
- For the owner: until a run on `main` has saved the ETOPO1 grid in the cache (the first push to `main`
  touching the map layers' tools, the twice-weekly schedule, or a run started by hand), a pull request
  that touches the map layers still asks NOAA, now at both of its servers with the waits above; a
  refusal by both is still an outside fault, said in one line.
- Left as they are: a timeline map's export still is unchanged (decision 0244); the zoom map's name is
  placed on the zoom's end state, as the map itself moves to it in one step.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
