# Component specs: science group

Twelve science component kinds move from the approved Kutch Ajrakh template to typed specs and
React views. A spec holds everything a view needs that is not a text unit; the view draws the same
elements, classes and text as the approved page, so the kit's `monograph.css` styles it as before.
Engineers changing a player, a drawing or the lab, and a contributor's agent delivering one, read it.

| For | Read |
|---|---|
| Why kinds became specs | [decision 0106](../decisions/0106-one-monograph-template-for-every-page.md), item 4, for the science group |
| The parts every group shares | [component-specs-plates.md](component-specs-plates.md) |
| Delivering one of these kinds through MCP | [component-specs-general.md](component-specs-general.md) |
| A family's flagship interactive, which these kinds carry | [kalavigyan-interactives](../../.claude/skills/kalavigyan-interactives/SKILL.md) |

| Side | Home |
|---|---|
| Models | `backend/app/research/component_specs_science.py` (`SPEC_MODELS_SCIENCE`: kind to model) and its parts `component_specs_science_{parts,figures,geometry,explainers,players,lab}.py` |
| Ajrakh specs | `backend/app/data/monographs/Kutch-Ajrakh/specs/<spec_file_name(label)>`, 21 files |
| Extraction | `python -m app.scripts.extract_specs_science` writes them; `--check` reports a file that differs from what the template extracts to |
| Shapes | `frontend/lib/componentSpecsScience.ts` (`SPEC_SHAPES_SCIENCE`) and its parts `componentSpecsScience{Parts,Figures,Explainers,Players,Lab}.ts` |
| Views | `frontend/components/monograph/kinds/science/` (`index.ts` exports `VIEWS: ComponentViews`) |

## Rules every science spec follows

- **Text units by id only.** A unit is named by its id (`u0123`) and drawn through
  `props.renderUnit`. Cited text is never copied into a spec. Labels the page shows uncited (control
  labels, drawing labels, molecule names, step names, the replay's source titles) are spec text.
- **Drawings are typed geometry.** `SvgNode {tag, attrs, children}` holds drawing elements only
  (`svg`, `g`, shapes, `text`, gradients, masks, patterns and the colour filters the page uses; no
  `script`, `foreignObject`, `a` or `use`). Attributes refuse `on*` handlers, `javascript:` and any
  `url()` that is not an in-drawing `#id`. `fill`, `stroke` and `stop-color` are a token
  (`var(--ink-1)`, `--dye-*`, `--dip-*`, `--mol-*`, `--chart-*`, `--map-*`, the surfaces), a mix of
  two tokens (`color-mix(in srgb, var(--a) N%, var(--b))`), an in-drawing reference, `none`,
  `currentColor`, or white or black for a mask or a highlight (`#fff`, `#000`,
  `rgba(255,255,255,a)`). Swatches outside drawings are a token or a `ColourMix`.
- **Spec text keeps its spaces.** Spec models extend `SpecModel`, which keeps leading and trailing
  spaces (`"in the paste · "`) where `ContractModel` strips them.
- **At rest, finished.** A player rests on the step the page shows at first paint (`current`), the
  dip and stage players on their last phase and stage, a toggle on its first option, the lab on its
  first experiment. Hidden steps, results and panels carry `hidden`, as on the page.
- **Behaviour comes from the kit.** Every view keeps the ids, classes and data attributes the page
  script binds to (`data-step`, `rp-rail`, `rp-play`, `mol-dial`, `data-stages`, `data-x`,
  `data-choice`, `data-v`, `data-res`, `data-tapano`, `data-pa-sw`, `data-kv-made`, `data-srcdoc`
  and the rest), so `monograph.js` drives players, toggles, dials and the replay. No view adds its
  own behaviour, and no view re-renders after the kit binds it (decision 0106, consequences). The
  kit drives a delivered spec as it drives Ajrakh's, on any page that draws it (decision 0198): a
  reaction player by its rail, arrow keys and Play; a dip player whose scene is not Ajrakh's
  animated cloth by its own phases; a lab that is not Ajrakh's by its options; a molecule by its
  own geometry.
- **Nested components are slots.** A `ComponentSlot {component: label}` marks where another
  registered component sits inside this one (the lab's three toggles, a toggle's chart, the
  materials' photograph). The view draws it through `parts/Slot.NestedComponents`, a context whose
  `render(label)` the renderer provides; without a provider a slot draws nothing. The renderer then
  draws a nested component only through its parent.
- **Held passages.** Where the template carries a cited sentence outside any text unit, the
  extraction leaves it out and reports it (`Extraction.held`); the spec field that would show it
  (a unit id) stays empty, and the view draws the passage once the unit exists. Ajrakh has 22:
  16 in the stage player (each stage's "Cloth after" sentence, stage 11's "Why" and the three
  "Sources differ" notes), two in the indigo-vat toggle's "Sources differ" note, and the PubChem
  record citation of each molecule in both structure diagrams (`rm:mol.1`, `rm:mol.6683`).

## reaction_player

`ReactionPlayerSpec {id, track, head, current, steps, scenes, key, status}`. Each step has its rail
`name`, its `text` (kicker, heading, paragraphs, an optional bond note, link and conditions, and a
"Sources differ" note of unit paragraphs) and its `chemistry`, an ordered list of species lanes
(swatch, name, formula, state, PubChem CID), equations (with the atom count and notes) and a
no-equation note. A player either draws one scene for every step (`scenes`, desk and phone) or a
reaction per step (`scene {whereIcon, where, art}`, desk, tall and phone) with a `key` line; the
second is drawn as `figure.rp.rx-player`. Ajrakh: blue (per-step reactions), red, black, white.

## dip_player

`DipPlayerSpec {id, head, phase, scene, stripLabel, phases, dipAgain, status, dipsLabel, dips,
equation?}`: the scene, the strip of phases, each named by its own key in `pose` (a lower-case
word or hyphenated words, each once; the last carries `aria-current="step"`), the label of the
repeat button, the swatches of the successive dips (colour tokens, the last `on`) and, where a source
states one, the balanced equation. The poses are the spec's words, not the model's: Ajrakh's spec
carries vat, lifted and air and its `--dip-1..4`, and Bidriware's fixture carries solution, lifted
and oiled with no equation, because the patina's compounds are unidentified. Ajrakh:
`shared/chemistry/indigo-vat-dip`.

The kit animates Ajrakh's scene, the cloth that goes green into the vat and turns blue in the air
(`.cl-move` and its parts). Any other dip player is played by its own phases (`initDips`): Dip again
moves to the next of its `dips` (after the last, the first) and shows each phase in order, over the
vat's 2,600 ms shared between them, its drawing in the scene, its strip item `aria-current="step"`
and the status line saying `Dip n of N.` with its kicker and text; it rests on the last phase with
the spec's scene back in place. Under either reduced-motion switch each press shows the next phase
at once and says it.

## stage_player

`StagePlayerSpec {key, head, drawing, restName, play, source, stages, finish}`. Each stage has its
name, English name, whether the name is local (italic on the ribbon), its "after" label for the
label card and the script's `data-stages`, and its units (number, heading, texts, why, materials,
and the held "Sources differ" note and after sentence). The view draws each stage's tile, ribbon
and swatch from the page's `#tile-n` patterns, the label card at rest ("Stage 11 of 11") and the
ribbon as a toolbar. The label before each stage's after (`afterLabel`, Ajrakh's "Cloth after", a dhokra
mould's "Model after") is the spec's, and a stage may name a recorded material as its `swatch`, drawn in
place of the page's `#tile-n` pattern, so another craft's stages show their own colours.
Ajrakh: `kutch-ajrakh/process/cloth-after-each-stage`.

## diagram

`DiagramSpec`: either a whole `drawing` (the borewell depth and the Bhuj distances) or a `chain`
of links, each a kicker and ordered parts: text blocks, drawings, step links into a reaction
player (`#rp-blue`, step n, with the figure reference) and a grouped equation with its tick count.
Ajrakh: three.

## molecule_3d

`Molecule3dSpec {head, molecules, side, key}`. Each model has its CID, yaw and pitch, name, dial
label, formula, atom line, note and its at-rest projection as a drawing; the dial's value is the
yaw in whole degrees. With side paragraphs the figure is `mols mol-two`. The kit redraws the model
from the page's molecule data on drag, on the arrow keys, Home and End and on Turn, and zooms it
from 0.6 to 2.5 times on plus and minus, a pinch of two fingers and a trackpad's pinch
(control and wheel); the dial's text names the zoom when it is not 1. Ajrakh: two.

A delivered model carries its own data as `geometry {atoms [[element, x, y, z]], bonds [[first,
second, order]], radius}`: PubChem's 3D conformer centred on its atoms' mean, to 4 decimals, the
radius the farthest atom's distance plus 0.42 (`science/molecule_conformer`). A model with its
geometry draws one `<g class="mol-g">` holding each atom once as `data-a` and each bond once as
`data-b`, the groups the kit turns, and a page that places it carries `mol-data[cid] = {atoms,
bonds, R: radius, marks: []}` (`services/document_components_data.kit_data`). Its at-rest drawing
is the kit's own projection (`science/molecule_drawing`): Ajrakh's alizarin drawn from its data at
its yaw and pitch is the approved drawing, with each letter at the 12 px floor or larger. A model
without geometry, Ajrakh's and every authored one, reads `mol-data` from its home page as before.
A molecule key's `--atom-*` swatches are accepted at delivery; any other swatch is a depicted
material.

## structure_diagram

`StructureDiagramSpec {id, head, dekStyle, scale, molecules, notes, key, swatches, swatchNote}`:
flat structures with name, formula, note, atom units and PubChem record, the marked-ring key, and
(in Hindi) swatches with their labels. Ajrakh: the English and Hindi alizarin and purpurin figures.

## equation_card

`EquationCardSpec {kicker, title, mark, line, why}`: a stated step drawn as an equation line with
the hypothesis mark. Ajrakh: `kutch-ajrakh/chemistry/indoxyl-to-indigo-hypothesis`.

## model_explainer

`ModelExplainerSpec {head, badge, badgeNote, stills, controls, key, model}`: inert stills (wide and
narrow) with their units and drawings, the shared play button, slider and key, and the model-built
document `{title, height, stylesheet, document, sandbox: "allow-scripts"}` that the kit loads into
the frame from `data-srcdoc`. The stylesheet may not contain markup. Ajrakh:
`shared/chemistry/indigo-in-cotton-fibre-explainer`.

## material_cards

`MaterialCardsSpec {id, headingId, heading, intro, cards, after}`: each card's swatch (a dye token
or `crystal`), role, name, local name, botanical name, chemistry and facts as units, and the
nested photograph as a slot. Ajrakh: `kutch-ajrakh/materials/six-materials`.

## experiment_lab

`ExperimentLabSpec {id, figure, number, pickerLabel, experiments}`: the picker and one toggle slot
per experiment. The lab provides `parts/LabContext.OpenExperiment` (its first experiment), so its
other toggles rest closed. Ajrakh: `kutch-ajrakh/chemistry/what-if-lab`. The kit binds every lab
on the page, whatever else the page draws (before decision 0198 the binding sat inside the region
explorer's and the time map's loops, so a lab ran only on a page that drew both): its picker opens
an experiment, and in a lab that is not Ajrakh's (no `data-redsw`) each option of each toggle sets
its own `aria-pressed` and shows its `data-res` and `data-forms`.

## choice_toggle

`ChoiceToggleSpec {experiment, questionId, question, options, textParts, visualParts}`: the
question, its options (each a result of a heading, paragraphs and differs notes) and ordered panel
parts in the text and visual columns: text blocks, formula chips (a PubChem CID or a named source),
a "same either way" note, a chart slot, a stage drawing with its hidden note, a stepper and a
switch, each with the script hook it carries. A toggle drawn outside a lab is open. Ajrakh: blue,
red and wash water.

## process_replay

`ProcessReplaySpec {play, understood, angles, stages, sourcesKicker, sources, sectionsKicker,
sections, ready}`: the replay's timed stages (start and end in ms), the sources read in order with
their grade, and the sections written with what each drew. Ajrakh:
`kutch-ajrakh/overview/how-this-answer-was-made`; its heading `u1055` is the summary of the fold
around the anchor, outside it, and is not drawn by the view.

## Composed from a craft's own facts

`compose_component {craft, kind, about?}` (MCP, the pages group; `services/compose_components`,
decision 0198) builds a `reaction_player`, `dip_player`, `molecule_3d` or `experiment_lab` with its
`choice_toggle`s finished from the craft's curated page and the facts it owns (`CuratedClaim`),
shown and stated as facts: the reactions in the order of their stages, the bath stages with their
colour after and the depicted colour of the dye or mordant they use, a compound of its materials
with PubChem's conformer, the alternatives its facts state. Every unit cites only those facts; a
label cites none, and a name that holds a number or a formula cites the facts that state it. When
the page holds too little it composes nothing and names what to propose (`open-work.md`, MCP).

## How this document is kept true

| Claim | Kept true by |
|---|---|
| A valid and a refused spec of each kind, the drawing and colour rules, spaces kept | `backend/tests/research/test_component_specs_science.py` |
| Every Ajrakh spec validates, shows exactly the units the layout places in its component, nests the components the page nests, holds back the 22 cited passages, and equals what the template extracts to | `backend/tests/research/test_science_spec_files.py` |
| The template reader | `backend/tests/test_extract_specs_science_script.py` |
| Each of the 21 views, drawn from its spec file, gives the template element's markup (attribute order, entity spelling, style spacing and JSON formatting aside), with the held passages removed and foreign nested components as slots | `frontend/e2e/monograph-science-parity-unit.spec.ts` |
| One component of each kind checked by hand against the approved page, the client's kinds against the backend's, and the shape refusals | `frontend/e2e/monograph-science-views-unit.spec.ts` |
| The colours a drawing accepts, as the interactives skill lists them | `backend/tests/mcp/test_interactives_skill.py`, against `COLOUR_TOKEN_PATTERN` |
| A model's geometry and its drawn group, and a molecule key's atom swatches | `backend/tests/research/test_molecule_geometry_spec.py` |
| PubChem's recorded conformer gives Ajrakh's alizarin data, and its projection Ajrakh's drawing | `backend/tests/science/test_molecule_model.py` |
| A delivered molecule carries its own `mol-data` to a generated page | `backend/tests/layouts/test_generated_molecules.py` |
| Each kind composed from fixture facts, refused with what to propose, citing only the craft's own facts | `backend/tests/compose/`, `backend/tests/mcp/test_compose_tool.py` |
| On a generated page at 360 and 1440 px, each composed kind whole at rest and worked by the kit, under both reduced-motion switches | `frontend/e2e/composed-interactives-unit.spec.ts` |

Re-read it when a science kind gains a field, a held passage becomes a unit, or the colour rule changes.
