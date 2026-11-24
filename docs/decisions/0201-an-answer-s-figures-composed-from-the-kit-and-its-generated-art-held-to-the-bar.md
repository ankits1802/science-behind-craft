# 0201. An answer's figure of cloth changing colour is composed from the kit with no model call, and a generated explainer's art is held to the bar or left out

An answer section whose cited sentences state a cloth changing from one depicted colour to another
gets a `kit_figure` block, composed by the server from those sentences and drawn by the site with
the figure kit of decision 0199, in place of asking the model for an HTML explainer. Every
generated explainer the model still writes is held to the design's bar (roles for every colour,
the type scale, no painted material, a still first paint, motion read from both reduced-motion
switches, and the figure bar of `research/drawn_art.drawn_art_problems` for its drawings); a draft below
it is redrafted once like any failed check and then left out, and a stored one below it is never
placed again. The frame carries the design's tokens and the reduced-motion switch.

Date: 2026-11-24. Status: accepted (lane `answer-figures` of the page-quality round; the owner,
2026-11-24, on the figures and animations built over MCP: "lacklustre", "the svg look like shit").
It amends [decision 0055](0055-generated-explainers.md) (the generated explainer's builder may draw
a kit figure in its place, and its checks gain the bar),
[decision 0059](0059-sandbox-and-what-if-renderers.md) (the frame's document carries the design's
tokens and the reduced-motion switch) and [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md)
(the kit draws an answer's figure as well as a page's). The contract is `docs/contracts/explainer.md`
(the kinds table, The composed figure, Generated explainers as built).

| For | Read |
|---|---|
| The kit, its parts and the figure bar | [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) |
| The generated explainer, its builder and its checks | [decision 0055](0055-generated-explainers.md), [decision 0087](0087-generated-explainers-per-concept.md) |
| The frame and its policy | [decision 0059](0059-sandbox-and-what-if-renderers.md), [decision 0061](0061-phase-c-review-fixes.md) |
| The depicted colours a cited colour and substance name | [decision 0197](0197-a-colour-key-from-cited-colours-and-a-masthead-that-names-the-craft-once.md) |
| The design's motion and reduced-motion switches | the kalavigyan-design skill, section 6 |
| Every decision, by group | [README.md](README.md) |

## Context

**What the answer's figures draw, measured on the recorded answers** (`shared/explainer.*.golden.json`
and the Kutch Ajrakh dossier the answer tests read):

| Block | Who draws it | Below Kutch Ajrakh's figures |
|---|---|---|
| `simulation` | the model: an HTML fragment with its own style and script in a sandboxed frame | The recorded kut explainer (`explainer.craft-mechanism.golden.json`) names six hex colours, sets 15 px `system-ui` text, paints the cloth as a flat `#d8c9a3` strip said to be "harde-treated cloth", rests its stages at opacity 0.4 until Play, and times its steps with `setInterval` read only from `prefers-reduced-motion`; the recorded iron acetate one (`explainer.simulation-mechanism.golden.json`) the same, less the cloth. The frame was white in every theme and knew neither the tokens nor the site's reduced-motion setting. Eight problems and eleven problems under the bar below. |
| `process_ladder`, `material_card`, `reaction_player` | the site, from stored rows | The reaction player's step colours paint a dye token chosen by the colour word alone (red is drawn as madder for any substance), textured; no part of the stage (cloth, vat, paste) is drawn. |
| `indigo_vat` (lede) | the site (`VatArt`) | At the bar: the approved vat moment. |
| `mordant_bath`, `lost_wax`, `firing` (lede) | the site | Facts in a grid or a list of steps titled as a diagram; nothing is drawn. |
| `molecule_3d`, the zoom story's molecule | the site, from the PubChem conformer (`ConformerCache`) | Turns, tilts and zooms, at once under either switch; hidden where WebGL is missing, where a page draws its server-drawn molecule. |
| `zoom_story`, `timeline_map`, `region_story`, `map_layer`, `seasons`, `supply_map` | the site, from the server's places, datasets and Commons pictures | At the bar: the server's maps, kept. |
| `what_if`, `concept_graph`, `compare` | the site, as controls and text | No art to hold. |

So the answer's own model-drawn art is the generated explainer alone, and every recorded one falls
below the bar on colour, type, rest and motion; the kut one also paints a material the kit draws.

## Decision

1. **A kit figure in an answer.** `research/blocks_kit.KitFigureBlock` is a phase C block
   (`kit_figure`, version 1): the page's declared diagram (`component_specs_kit.DeclaredDiagramSpec`,
   the same layouts, parts, materials and motions) and its `labels[{ref, text, citations?}]`, each
   unit the diagram draws named once, every part's and layer's label cited. It holds no sentence,
   so it is not translated, ledgered or read aloud; its labels are shown labels; it is never kept
   as a piece (`UNSTORED_BLOCK_KINDS`). `models/block_kinds.BLOCK_KINDS` gains it before
   `component`, and migration `0111_answer_figures` widens the `KnowledgePiece` and
   `ComponentProposal` kind checks by it alone (down revision `0103_component_lifecycle`).
2. **Composed from the sentences it rests on, with no model.** `science/kit_figures.concept_kit_figure`
   takes a section's mechanism concept and the craft's stored process: the stage that plays the
   concept's reaction (or holds its resist), its fact claims and the concept's own, and the first of
   them that names cloth (the kit's own words, `art_kit.parts_named_by`) and whose quote states the
   cloth's colour before and after (`reaction_colours.step_colours`). Both colours become depicted
   materials through the colour key's rule (`colour_key.depicted_material`, a cited colour and a
   substance the stage or reaction names). It draws a `before_after`: the first colour, in the
   vessel the stage's sentences name (vat, pot, trough or pit) as a bath with the cloth in it and the
   dip motion when the stage is a mordant or dye bath, else as cloth; then the cloth in the second
   colour with the take motion. The titles and panel names are the colour words; each part's label
   cites the quote that states it. Anything less stated is not composed. On Kutch Ajrakh's indigo
   oxidation (claim C086) it draws "Green to blue": the cloth in the vat in `--dye-leuco`, then blue
   in `--dye-indigo`; the kut concept (C078), whose quotes state only the black it develops, is
   not composed.
3. **In place of the model.** The generated explainer's builder tries the kit figure first for its
   concept and returns it without a model call (`BuilderEntry.draws`, the kinds an entry may draw
   in place of its own, is `{kit_figure}` for `simulation`); only when nothing is composed does it
   go on to reuse or the model, as before.
4. **The bar on the model's art** (`research/simulation_art.simulation_art_problems`, rule `ART`):
   every colour in the style, the markup's paints and the script's colour strings is a design role
   (`--indigo` only on a control, never a drawing, never a `--dye-*` or `--dip-*` material, the
   kit's to draw); text in `var(--font-ui)` or `var(--font-reading)` at 12, 13, 14 or 16 px; no
   `opacity` below 1 at rest; any timer reads `dataset.reducedMotion`; no picture said to show a
   kit subject; and every static `svg` passes `drawn_art.drawn_art_problems` as a `drawing` (the type
   scale, six shapes or more, ink line work, no hand-painted material). The prompt states the bar.
   A draft below it is redrafted once within the 60 s budget with the problems listed, like any
   failed check, and a second failure **leaves the block out**; no new kind of call is added. A
   stored explainer below the bar is never reused or placed in a reused section
   (`piece_reuse.reusable_simulation`), so the next answer for its concept drafts one at the bar.
5. **Motion only to explain, complete at rest.** The kit figure is finished at first paint and moves
   only when the reader presses Play, never under either switch (the kit's own motion, decision
   0199). The generated explainer's frame (`lib/sandboxFrame.sandboxDocument`, `useFrameLook`)
   carries the values of the tokens its HTML names, read from the page in the reader's theme and
   contrast, sets `data-reduced-motion="true"` on its own document when either switch is on, and
   turns every animation and transition off under that attribute and under `prefers-reduced-motion`,
   whatever the model wrote; the frame's ground is `sunk`.
6. **Cost.** A section that draws a kit figure makes no model call where it made one or two; a
   section asked of the model makes at most the two calls it made before (test below).

## Consequences

- An answer on how indigo turns blue draws the vat and the cloth from the kit, cited, for nothing;
  the recorded explainers below the bar would now be left out, and every one the model writes is
  drawn in the design's colours, type and motion or not shown.
- Generated explainers already stored are held to the bar when reused: below it, the concept is
  drafted again once, a call where reuse cost none; answers already saved keep the explainer they
  were saved with until they are asked again.
- The prompt is longer by the bar's lines, so each remaining generated explainer call reads a few
  hundred more input tokens.
- Left for later: a kit figure for a concept whose sentences state a material but no change of
  colour (kut's black print); the mordant bath, lost-wax and firing ledes drawn from the kit; the
  reaction player's step colours taken from the cited substance; an ask result over MCP carrying
  the kit figure (it carries sentences and registered components, so an agent links the answer);
  the frame's text set in the site's faces (its policy loads no font).

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_blocks_kit.py`, `backend/tests/research/test_simulation_art.py`,
`backend/tests/simulations/test_answer_kit_figure.py`,
`backend/tests/simulations/test_craft_mechanism_golden.py`,
`backend/tests/simulations/test_simulation_builder.py`,
`backend/tests/simulations/test_mechanism_reuse.py`,
`backend/tests/contracts/test_component_block_contract.py`,
`backend/tests/contracts/test_golden_fields.py` and `frontend/e2e/answer-kit-figure-unit.spec.ts`.
