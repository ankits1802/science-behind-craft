# 0206. A page exports to PDF and Word with every new kind as its complete still, one still renderer draws them all, and a component's labels are translated as passages

A reader exports a page as a PDF or a Word document in the language it is served in. Every
component is one figure where the layout places it: its still at rest, drawn by one renderer that
also draws the answers' kit figures and timeline maps, every unit it holds, its citations and
credits, and what it does on the page that paper cannot. The labels a component's spec holds (a
step's name, a lane's species, a molecule's name, a lab's choices) are offered for translation as a
page's passages are and drawn in the reader's language once translated; numbers, formulas, keys,
drawings and a native name never are.

Date: 2026-11-25. Status: accepted (the lead's lane `exports` of the page-quality round; the
owner, 2026-11-24, on the pages built over MCP falling below Kutch Ajrakh's). It amends
[decision 0067](0067-lessons-and-exports.md) (exports: a page export beside the answer and lesson
files, and the report PDF's timeline map now drawn) and
[decision 0117](0117-pages-in-other-languages.md) (a figure's own labels no longer stay English:
they are passages). The contracts are `docs/contracts/monograph-document.md` (Exports; Pages in
other languages), `docs/contracts/component-specs-science.md` (Rules) and
`docs/contracts/learning.md` (PDF).

| For | Read |
|---|---|
| The answer and lesson files, their bucket keys and signed links | [decision 0067](0067-lessons-and-exports.md), [decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md) |
| Passages, their hash, the gates and the variant | [decision 0117](0117-pages-in-other-languages.md) |
| The Download on every page, its pictures, its fixed words and the family and category exports | [decision 0208](0208-every-page-downloaded-from-the-page-with-its-pictures-and-its-words.md) |
| The kinds this export draws | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md), [0197](0197-a-colour-key-from-cited-colours-and-a-masthead-that-names-the-craft-once.md), [0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md), [0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md), [0202](0202-a-dip-s-colours-from-its-facts-the-crafts-dyes-and-pigments-and-twenty-atoms.md) |
| A page file filed by what it is made from alone, its day only in the download name, and the rebuild its read claims queued (amends item 1) | [decision 0214](0214-a-page-export-filed-once-built-in-its-own-slots-at-a-caller-s-pace-and-its-rebuild-queued.md) |
| The coded figure's still on paper (amends this record) | [decision 0231](0231-a-contributor-s-ai-writes-a-figure-s-code-over-the-page-s-cited-data.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **No page could be exported.** The lane was written as though a reader could export a page or an
  answer as PDF or Word. In the code an answer exported as a PDF only (`export_pdfs.explainer_pdf`)
  and a lesson as HTML, PPTX and PDF; a page had no export at all, and nothing anywhere wrote Word.
  The answer PDF drew a timeline map as a list of places with no map, and a molecule as its name.
- **The new kinds draw only in the browser.** A declared timeline map, a composed kit `diagram`,
  the colour key's `swatch_cards`, a dip coloured from facts and a molecule of any of the twenty
  elements are drawn by the web's renderers from specs and the design tokens; the kit's parts are
  TSX (`frontend/components/artkit/parts/`). Paper needs a drawing the server makes, with no
  browser on the box.
- **A component's labels never translated.** Translation covered a page's text units only. The
  composer and contributors write a player's step names, lane labels, species names, a dip's strip
  label, a molecule's name, atoms and key, a lab's and a toggle's choices as plain spec strings
  (`Label`), so a Hindi page showed them in English, and decision 0117 said so ("Figures keep
  their specs").

## Decision

1. **A page exports as a PDF and a Word document.** `GET /api/crafts/{slug}/monograph/{pdf|docx}`
   exports the document the monograph route serves, in its language, filed once per served tag
   under `exports/<page owner, uuid 1>/` and answered as a signed link named
   `KalaVigyan_Craft-Page_<date>_<page>[_<language>]_Export_v<n>.<fmt>` (`naming.export_file_name`,
   which replaces `explainer_file_name` for both). Word is written as WordprocessingML with the
   standard library rather than a new dependency: the export needs paragraphs, runs, styles,
   pictures and links only.
2. **One still renderer.** A still is vector paths and text in the light theme's tokens
   (`services/export_stills.py`). It is made from a component's own SVG drawing (paths with every
   command flattened, shapes, text, transforms, a gradient's first stop; textures, masks and filters
   left out), from kit parts (`export_still_kit*`, the web kit's own path data), from a conformer
   turned to its rest (atoms in `--atom-*`), from depicted-material swatches, or from the site's
   district outlines with numbered pins (`export_still_map`). A PDF draws it as vectors; Word holds
   it as a PNG with the figure's lines as text beneath it, so a translated label is never baked
   into a picture. A composed diagram, a kit scene (`{parts}` in a scene slot) and an answer's kit
   figure all go through `diagram_still`/`scene_still`; the answer PDF's timeline map is drawn by
   `timeline_still`.
3. **Every component is a figure and nothing is left out silently.** A builder per new kind draws
   its still and lists its states, places, panels, colours, steps, phases, stages, models, facts and
   choices with their citation numbers; every other kind gives its drawings and its words. Every
   unit placed in a component appears in its figure (a figure's number and a stage's ordinal are
   numbered by the export instead), a component placed in no chapter is still given, and each
   interactive kind says what it does on the page that paper cannot.
4. **A component's labels are passages.** `Label` and a species' `ShownRich` carry the marker
   `SHOWN_TEXT`; `research/spec_texts` offers every such string as a passage keyed
   `<component label>#<path>`, and `research/page_passages` is the one list of a page's passages
   that the index, the translation view, proposals, the preview and the variant read. The variant
   puts a served translation back at its path. `track` became `HookLabel` (a data hook, never
   shown); a stage named in its own language keeps its name. The index is filed with its edition
   (`i2`); an index of an earlier edition reads as none, so every page is indexed again once with
   its labels, and the document's tag is unchanged.

## Consequences

- A Hindi page exports in Hindi: its translated passages and labels in Hindi, the rest in English
  and marked English in Word (`w:lang`), its numbers, formulas, keys and native names as the
  English page holds them. The export's own fixed words ("Sources", the paper notes, "Drawn:")
  stay English until interface words are sourced for it (decision 0157).
- A Kutch Ajrakh export draws its authored components' specs (all 80) from their SVG drawings and
  words; its fragment-only HTML is not parsed. Its pictures are given by their alt text and credit
  lines: no picture is fetched into a page export yet.
- The TRANSLATE tasks of every page with science components grow by their labels; Kutch Ajrakh's
  native specs' labels are offered too.
- The kit's geometry now lives in the web kit's TSX and in `export_still_kit_parts.py`/`_more.py`;
  a change to a part's drawing changes both.
- The web has no export button yet: placing one on the approved Kutch Ajrakh page changes what the
  owner approved, so where it goes is the owner's to choose.
- The kit-players lane (decision 0200) needs no export change: a scene slot holding `{parts}` is
  drawn by `scene_of`. The answer-figures lane (decision 0201) adds one `draw_figure` case calling
  `export_pdf_kit.kit_figure_pdf(writer, block.diagram, labels)` with its labels' texts.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/exports/`
(`test_export_stills.py`, `test_page_export.py`, `test_page_files.py`, `test_export_languages.py`),
`backend/tests/learning/test_pdf_figures.py` and `test_export_store.py` (the names),
`backend/tests/research/test_page_translation_variant.py` and the translation database tests.
