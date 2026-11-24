# 0199. A figure is composed from a kit of parts the site draws, and hand-drawn art below the bar is refused at delivery

A contributor's figure names designed parts of the site's kit (cloth, a carved block and its print,
a vat or bath with its liquor, a paste applied, heat or sun, water, a tool in a hand, a layered
section and a shaped piece) and sets them in a row of steps, a before and after, a section or a
sequence with arrows; the web draws every part in the design system at every width, with motion
that explains a change and rests complete. Every other free drawing a delivery carries is held to
a bar and refused with the kit part to use. A kit sheet shows every part in every depicted
material.

Date: 2026-11-24. Status: accepted (the lead's lane `art-kit` of the page-quality round; the owner,
2026-11-24, on the Sanganeri page built over MCP: "the animations that it is creating are
completely lacklustre ... the svg look like shit", "the page all in all lacks any sense of
design"). It amends [decision 0114](0114-kinds-and-datasets.md) (`diagram` takes a declared form
beside its authored one, and the kind fixtures gain a composed diagram) and
[decision 0131](0131-drawings-in-the-design.md) (a delivered drawing is held to a bar beyond the
design's roles). The contracts are `docs/contracts/component-specs-general.md` (The figure kit,
The hand-drawn figure, checks 7 and 8) and `docs/contracts/component-specs-science.md`
(`diagram`).

| For | Read |
|---|---|
| One kind per job and the declared forms | [decision 0114](0114-kinds-and-datasets.md) |
| The design's roles a drawing names | [decision 0131](0131-drawings-in-the-design.md) |
| The design system the parts are drawn in | [decision 0092](0092-design-system.md) and the kalavigyan-design skill, sections 2.5, 2.7 and 2.13 |
| The hand-drawn map refused the same way | [decision 0196](0196-a-contributor-s-map-drawn-by-the-site-from-places-it-resolves.md) |
| The families each part serves | `.claude/skills/kalavigyan-interactives/references/flagships.md` |
| The players, the toggle's stage box and the seal drawn from the kit, and their scenes held to the bar | [decision 0200](0200-players-and-cards-drawn-from-the-kit.md) |
| The kit drawing an answer's figure composed from its cited sentences (amends this record) | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Every contributed figure was drawn node by node.** A `drawing`, a `diagram`, a stage, dip or
  reaction player's scenes, a label card's seal and a toggle panel's art are SVG the model writes
  element by element (`SvgNode` trees, or a `drawing`'s markup). Decision 0131 holds their colours
  to the design's roles, their text to a 12 px floor and their gradients to one role, which says
  nothing about whether the figure is any good: the kind fixtures that proved the kinds on other
  crafts drew a stage player as one ellipse, a dip player's phases as two rectangles each and a
  seal as three circles, and all of them passed.
- **Kutch Ajrakh's figures are made of a few recurring parts.** Cloth in its depicted colour with
  the weave texture and its print, the carved block, the vat sunk in the earth with its liquor, the
  resist and mordant pastes, the sun, running water, the printer's hand and the earth, mud resist
  and cloth in section, each edged in ink, named in a key and labelled by cited sentences. The
  nine families' flagships (`flagships.md`) need the same parts plus a shaped piece: a cast figure,
  a pot, a slab, a billet, a sheet, a culm.
- **A new component kind needs a migration.** `KnowledgePiece.kind` is held by a check constraint
  over `COMPONENT_KINDS` (migration `0034_component_kinds`), and the lane runs beside two others
  that write migrations. `chart`, `fact_table`, `timeline`, `map_layer`, `related_crafts` and
  `timeline_map` already take two forms of one kind (`component_specs_either`).

## Decision

1. **A kit of nine parts, with one vocabulary.** `research/art_kit.py` holds each part's name, the
   families it serves, the words that name what it draws, its choices and the fields that take a
   material: `cloth` (swatch, length, folded; printed with a motif), `block` (its motif and the
   paste on its face), `bath` (vat, pot, trough or pit; its liquor and the piece in it), `paste`
   (spread, printed, outline; its ground and what it dries to), `heat` (sun, fire, furnace, lamp),
   `water` (running, still, sprinkled), `tool` (block, brush, chisel, mallet, knife, stick, in a
   hand unless said otherwise; what it carries), `section` (two to six layers, a material or earth)
   and `piece` (lump, vessel, slab, billet, sheet, figure, culm; its material and inlay). Motifs
   are star, lattice, dots and lines. `shared/art-kit.golden.json` is the vocabulary as both sides
   read it, and `frontend/lib/artKit.ts` is the web's copy. A part takes only what a source can
   state: a material by its depicted token (`--dye-*`, `--dip-*`, the materials the design system
   records), a choice by name, a count of layers, a label unit; never a coordinate, a size or a
   colour of its own.
2. **A figure is a declared `diagram`, not a new kind.** A `diagram` spec with a `head` is composed
   from the kit (`component_specs_kit.DeclaredDiagramSpec`: `head`, `layout`, `alt`, `panels` of
   `{label, text?, via?, motion?, parts}`, one to three parts a panel), and one without is the
   authored drawing or chain of steps it was; `component_specs_either` tells them apart as it does
   for the other declared forms, so no kind and no migration is added and Kutch Ajrakh's three
   diagrams keep their view. A `steps` diagram has two to six panels, a `before_after` two, a
   `section` one holding one section part, a `sequence` two to six joined by arrows; only a
   sequence or a before and after names a change on the arrow into a later panel. Every part's
   label and every layer's label cites a fact (check 7, `kit_label_problems`).
3. **The site draws it.** `frontend/components/artkit/` draws each part as inline SVG in the tokens:
   materials filled with their token, the weave, grain, strata, speckle or ripple texture over them
   and an ink edge, line work in `--ink-1` to `--ink-3` on `--raised` and `--sunk`, earth in the
   hatch grammar's strata, a print tiled in its material, and a key of framed swatches and cited
   labels at the type scale beside the drawing, so no word is set inside the SVG.
   `KitDiagramView` (registered for the declared form in `componentViews.ts` and `serverViews.ts`,
   and drawn by the app, `monographScopes.appDrawn`) frames it as a figure with its kicker,
   title, caption and alt. Panels sit one to a row on a phone (two for steps), two or three to a
   row from 640 px, and four panels in one row from 1024 px; a sequence's arrows point down on a
   phone and along the line from 640 px.
4. **Motion explains one change and rests complete.** A panel may name `dip` (a bath's piece going
   in), `take` (a cloth's colour taking) or `dry` (a paste's wet colour giving way to its dried
   one), and only when it holds the part that change explains. They are the design system's named
   dip and oxidise motions on that part's layer (`artKitMotion.KIT_NAMED_MOTION`), so no keyframe
   is added. The figure is finished at first paint; Play, pressed by the reader, marks each panel
   in turn with `aria-current="step"` and the ink rule, plays its motion on the motion tokens and
   announces it; under either reduced-motion switch nothing moves and each press shows the next
   panel and announces it.
5. **Hand-drawn art is held to a bar at delivery.** `research/drawn_art.drawn_art_problems` runs in
   check 8 on every free drawing a delivery carries (icons and the molecule drawings of
   `structure_diagram` and `molecule_3d` aside). It refuses text off the type scale (12, 13, 14 or
   16 px at 320 px wide), a figure of fewer than six shapes, a figure with no line work in ink,
   and, in a `drawing` or `diagram`, a depicted material painted by hand or words that say it shows
   what a kit part draws, each pointing to a composed diagram and naming the part; in a player or a
   card it refuses a depicted material with no texture laid over the same shape. Kutch Ajrakh's
   authored figures are its page's own and never pass through the delivery check, so they are not
   re-checked.
6. **The fixtures meet the bar.** The `drawing` fixture is a line drawing of a dhokra model wound
   in wax strings, and the stage player's figure, the dip player's four drawings, the reaction
   player's scene and the label card's seal are redrawn with textured materials, ink edges and the
   structure the bar asks for. A composed diagram of Bidriware's blackening (zinc-white, in the
   boiling bath, lifted black) joins the fixtures, so 26 are drawn on `/design/kinds`.
7. **The kit sheet.** `/design/kit` draws every part in every form and in every depicted material
   it takes, and the four layouts, with the design page's theme, contrast, text and motion
   switches, so the owner can judge the kit at phone and desktop widths, light and dark.

## Consequences

- A contributor's figure of cloth, a vat, a paste, a section or a piece is composed rather than
  drawn, and the delivery says which part to use when one is drawn by hand.
- The players and cards cannot place a kit part yet: their renderers are the interactives lane's
  and take `SvgNode` trees. Their art is held to the bar only once they take kit parts
  (`scene_problems`, which the delivery does not call yet), so the scenes `compose_component`
  builds are not refused for want of a part; the kit's `KitPartArt` and `KitFigure` are ready for
  those renderers to draw a kit scene when they take one.
- A family whose materials have no depicted token (wax, cast metal, raw and fired clay, stone,
  wood, lac, hide, pulp, mineral pigments) draws its parts in line work until the design generator
  records the material, as the interactives skill already asks.
- The component guide and the page checklist gain the kit's text from the lead (the lane's
  report); the preview's rendered checks stay the render-review lane's.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_art_kit.py`, `backend/tests/research/test_component_specs_kit.py`,
`backend/tests/research/test_drawn_art.py`, `backend/tests/research/test_kind_fixtures.py`,
`frontend/e2e/art-kit-unit.spec.ts` and `frontend/e2e/kind-fixtures-unit.spec.ts`.
