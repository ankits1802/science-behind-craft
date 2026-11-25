# 0216. A contributed drawing loads nothing from elsewhere and lays nothing over the page, a declared timeline map's key holds its place at rest with its layer files asked for once the page is idle, and Download says when its list did not load

Every attribute of an inline drawing, a plate's `DrawingElement` and a science `SvgNode` alike, is
held on the server and in the browser to one rule: no handler, no script, nothing loaded from
another address, `href` within the page, no cursor, and a `style` of drawing properties with token,
number or keyword values; the general drawing's intake strips the same values. A declared timeline
map draws its relief and rivers key at first paint and holds a legend's shape for the keys that
wait on a file, and asks for its layer files once the page is loaded and idle. The page's Download
control catches a list that did not load, says so beside the button and loads it afresh on the next
press, and is busy at its own width while it loads.

Date: 2026-11-25. Status: accepted (the lead's lane `review-web` of the review of the quality round,
findings `web-1`, `web-4` and `web-5` of `.lead/data/advreview-1125/review.json`). It amends
[decision 0131](0131-drawings-in-the-design.md) (what a drawing's intake strips),
[decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) (how the
declared timeline map draws its layers), [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md)
(what a near view's still holds) and [decision 0208](0208-every-page-downloaded-from-the-page-with-its-pictures-and-its-words.md)
(how Download loads its list). The contracts are `docs/contracts/component-specs-plates.md`
(`DrawingElement`), `docs/contracts/component-specs-science.md` (drawings),
`docs/contracts/component-specs-general.md` (The SVG intake; The declared timeline map) and
`docs/contracts/monograph-document.md` (Download on the page); the contributor's rule is in
`references/components.md` (Inline drawings load nothing).

| For | Read |
|---|---|
| The drawing vocabulary and the general drawing drawn as an image | [decision 0131](0131-drawings-in-the-design.md) |
| The declared timeline map and its layers | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) |
| Heavy kinds loaded near after their still, and the phone budget | [decision 0205](0205-a-page-measured-on-a-slowed-phone-held-to-its-budget-and-heavy-kinds-loaded-near.md) |
| Download on every page | [decision 0208](0208-every-page-downloaded-from-the-page-with-its-pictures-and-its-words.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **An inline drawing could beacon every reader.** A label card's seal, a swatch pair's motif, a
  player's scene and the other inline drawings are React elements drawn from the spec, and their
  `style` reached the page as an inline style unread. The plates' check refused only handlers, an
  outside `href` and `javascript:`; the science check's `url(` test had no case flag, so
  `URL(https://…)` passed, and `image-set("https://…" 1x)` holds no `url(` at all. The page's
  `img-src` allows `https:`, so an approved component could make every reader's browser ask an
  outside host for a pixel, telling it their address and the time, and `position:fixed` with
  `inset:0` and a `z-index` could lay a figure over the page. The general `drawing` kind was never
  open to it: it is drawn as an image, which loads nothing.
- **A declared timeline map's key arrived late and moved the page.** Its relief, rivers, minerals and
  home hatch came from files fetched in effects, so its still had no key and, with a district
  layer, the line "Drawing the district values"; and since its view hydrates only within two
  screens, those files (relief 119 KB, district shapes 278 KB, rivers 32 KB on slow 4G) started
  then, and a reader at pace could see the key grow beneath the map.
- **A Download list that did not load replaced the page.** `next/dynamic` throws a rejected import
  during render, nothing nearer than `app/error.tsx` caught it, and `React.lazy` keeps the
  rejection, so a release while a reader read, or a dropped request, put the root error page in
  place of the monograph; a press before the list arrived set `aria-expanded` with nothing shown.

## Decision

1. **One rule for every drawing attribute, on both sides.** `research/drawing_attributes.py`
   (`drawing_attribute_problem`, `loads_nothing`, `style_problem`, `STYLE_PROPERTIES`) and
   `frontend/lib/drawingAttributes.ts` (`drawingAttributeRefusal`, `loadsNothing`, `styleKept`,
   `DRAWING_STYLE_PROPERTIES`) refuse, in any case, a handler; a script (`javascript:` with its
   spaces folded, `expression(`, `@import`); a value that loads from another address (a `url()`
   other than an in-drawing `url(#id)`, quoted or not, `image-set()` and `-webkit-image-set()`,
   `cross-fade()`, `image()`, `src()`, or any backslash, which can spell any of them in code
   points); an `href` or `xlink:href` (in any case, since the HTML parser lowers names) that is not
   `#id`; a `cursor`; and a `style` declaration whose property is not one of 52 drawing properties
   (paint, stroke, opacity, transform, text, display, blend, clip and custom properties) or whose
   value is anything but letters, digits, spaces and `.,%#()+_-`, so no quote, colon, slash or `!`
   can carry an address or a priority. `position`, `inset`, `z-index`, `cursor`, backgrounds,
   content, sizes, animation and transition are off the list. The plates' `DrawingElement` and the
   science `SvgNode` call it after their own name checks, on the server at delivery and read and in
   the browser before a view draws; the general drawing's intake strips what `loads_nothing`
   refuses. The cases both sides test are one file, `shared/drawing.attributes.golden.json`.
2. **A timeline map's still holds its key.** The relief key is drawn from the design's elevation
   classes (`lib/mapPalettes.ELEVATION_BREAKS`), at which the relief file is cut, and the rivers key
   needs no file, so both are whole at first paint; the minerals key and a district layer's legend,
   which need their files, hold a legend-shaped skeleton (`Skeleton` shape `legend`, its words for a
   screen reader only) in place of the loading line. The near view asks for the named layers'
   files and the district shapes with `link rel="prefetch"` once the page is loaded and idle
   (`timelineMapFiles`, `nearViews.timelineMapPrefetched`), so they are cached before the view nears.
3. **Download catches its list.** `PageDownload` loads the list with an `import()` it catches
   instead of `next/dynamic`: the button (`DownloadTrigger`, now the kit's `Button`) is busy at its
   own width while it loads (Opening, `aria-busy`, a press ignored) and opens the list when it lands;
   a list that does not arrive leaves the page and the button as they were, and an alert beside the
   button says "The list of downloads did not load. Press Download to try again."; the next press
   imports it afresh. A catching control was chosen over an error boundary because a boundary swaps
   its children for its fallback, which would take the button and the reader's focus with it.

## Consequences

- **No stored drawing is refused.** The check was run over every stored component in the
  repository: 34,839 drawing attributes in 192 files (Kutch Ajrakh's 80 specs with its content,
  the 26 kind fixtures, the golden document, and the curation dossiers with their check files and
  index, which hold no drawings) pass it,
  including the 454 `style` attributes, whose properties are `fill`, `stroke`, `opacity`,
  `transform`, `clip-path`, `display`, `font-size`, `text-anchor`, `mix-blend-mode`,
  `stroke-dasharray` and the kit's custom properties. Pages built over MCP (Sanganeri Hand Block
  Printing among them) live only in the database, which this lane did not read; their drawings are
  checked again when a page is next read or built, and one with a style off the list would be
  refused there with the attribute named, so the lead reads them before the release.
- **The phone budget's bytes do not change at first paint.** The relief and rivers key add a
  legend's markup to a map's still; the layer files are fetched after the load at idle priority,
  as JSON, which the budget does not count, and only for a page that names them.
- **What is left.** A drawing's `class` may still name a site utility (`fixed inset-0`), and a
  root `svg` may still be drawn very large through its `width`, `height` or a `transform`; neither
  loads anything, and both are seen by the reviewer in the preview, unlike a one-pixel beacon. The
  home district's hatch, the relief bands and the rivers are still drawn from their files after the
  view hydrates rather than in the server's HTML: drawing them there would add about 400 KB of
  path data to every page that holds a map, against the phone budget. The minerals key's and a
  district legend's skeletons are shaped like the legend, so they move what follows by a line at
  most when a long class name wraps. These stay here and in the report, not in the debt register.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_drawing_attributes.py` and `frontend/e2e/drawing-attributes-unit.spec.ts`
(the shared cases kept and refused by both drawing models on both sides, a beaconing or overlaying
seal refused and a painted one drawn, a science scene in capitals or as an image set refused, the
general intake stripping an image set and an escape, every stored drawing passing),
`frontend/e2e/timeline-map-declared-unit.spec.ts` and `frontend/e2e/near-views-unit.spec.ts` (the
relief and rivers key whole at rest, the minerals key and district legend held and then drawn, the
layer files asked for and none for a map that names none), `frontend/e2e/map-layers-unit.spec.ts`
(the relief file cut at the design's elevation classes), and `frontend/e2e/page-download-unit.spec.ts`
with `frontend/e2e/page-download.smoke.spec.ts` (Download busy at its own width, a list that does
not arrive said in words with the page and the button kept, and the list opened on the next press).
