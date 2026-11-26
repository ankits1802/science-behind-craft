# Component specs: science group

Twelve science component kinds move from the approved Kutch Ajrakh template to typed specs and
React views. A spec holds everything a view needs that is not a text unit; the view draws the same
elements, classes and text as the approved page, so the kit's `monograph.css` styles it as before.
A thirteenth, `coded_figure`, is a contributor's own code run in a sandboxed frame over the page's
cited data (decision 0231). Engineers changing a player, a drawing or the lab, and a contributor's
agent delivering one, read it.

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
- **Spec text is translated as a page's passages are** (decision 0206). Every field typed `Label`
  and a lane species' `name` (`ShownRich`) carry `SHOWN_TEXT` (`research/shown_text.py`), so
  `research/spec_texts.spec_texts` offers each as a passage keyed `<component label>#<path>` and
  the variant draws its served translation in place. A `Rich` formula, a reaction player's `track`
  (`HookLabel`, a data hook, never shown), keys, ids, colours and drawings are not spec text, and a
  stage named in its own language (`local`) keeps its `name` as its source gives it.
- **Drawings are typed geometry.** `SvgNode {tag, attrs, children}` holds drawing elements only
  (`svg`, `g`, shapes, `text`, gradients, masks, patterns and the colour filters the page uses; no
  `script`, `foreignObject`, `a` or `use`). Attributes refuse `on*` handlers, `javascript:`, an `href` that is not an in-drawing `#id`
  and, as a plate's drawing does, any value that loads from another address or a `style` off the
  drawing list (`research/drawing_attributes`, decision 0216), a `class` the kit's own drawings do not carry, or an
  `svg` drawn past its box (wider or taller than its viewBox, grown or moved by a transform, its overflow shown;
  decision 0218). `fill`, `stroke` and `stop-color` are a token
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
- **A scene is drawn or composed from the kit.** Each scene slot of a player, the toggle's stage
  drawing and the label card's seal (`plates`) take either a free drawing or a kit scene
  (`component_specs_kit_scene.KitScene`, decision 0200): `{parts, motion?}`, one to three named parts
  of the figure kit in the composed `diagram`'s vocabulary (`research/art_kit.py`), each labelled by
  a unit that cites its facts. The two are told apart by `parts` (`scene_form`). The web draws a kit
  scene with `components/artkit/KitScene.tsx`: the parts inside the slot's own frame at every
  width, the kit's textures once per component and the key of framed swatches and cited labels
  beside the frame, never a word inside the drawing. A scene's `motion` (`dip`, `take`, `dry`) is
  allowed only where the reader shows the scene again (a reaction step, a dip phase, a dip player's
  scene); the stage player's drawing, the toggle's stage box and the seal rest as drawn, so a kit
  scene there names none (`KitStill`). The kit plays a shown scene's part with the design system's
  named motion (`kitMove`, the `data-playing` hook of `app/motion.css`) and never under either
  reduced-motion switch.
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
reaction per step (`scene {whereIcon?, where, art}`, desk, tall and phone) with a `key` line; the
second is drawn as `figure.rp.rx-player`. A step's `art` is its drawings (desk, tall and phone, beside
its `whereIcon`) or one kit scene, which draws where the step happens itself, so its where icon may be
left out; the kit shows it with the step and plays its part's motion when the reader chooses the
step or presses Play. The view gives the where drawing its size, never its container
(`lib/reactionWhere.whereDrawing`, decision 0210): an icon, a drawing at most 32 units wide (the
drawing checks' `iconView`), at its own units, one a pixel, with no `vg` class; any other the kit's
92 px vignette, its `vg` class added where the spec leaves it out; either `aria-hidden`, since the
where line says it in words. Ajrakh's vignettes carry both already and are drawn as their spec gives
them. Ajrakh: blue (per-step reactions), red, black, white.

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
at once and says it. The scene and each phase's drawing may be a kit scene: a phase's key sits in the
strip under its text, the scene's key under the scene (`.vat-key`), and the kit shows each phase's
drawing and key in the scene in turn and plays the shown part's motion.

## stage_player

`StagePlayerSpec {key, head, drawing, restName, play, source, stages, finish}`. Each stage has its
name, English name, whether the name is local (italic on the ribbon), its "after" label for the
label card and the script's `data-stages`, and its units (number, heading, texts, why, materials,
and the held "Sources differ" note and after sentence). The view draws each stage's tile, ribbon
and swatch from the page's `#tile-n` patterns, the label card at rest ("Stage 11 of 11") and the
ribbon as a toolbar. The label before each stage's after (`afterLabel`, Ajrakh's "Cloth after", a dhokra
mould's "Model after") is the spec's, and a stage may name a recorded material as its `swatch`, drawn in
place of the page's `#tile-n` pattern, so another craft's stages show their own colours. The
`drawing` may be a kit scene at rest, its key under the stage box (`.lc-key`). The kit binds only
Ajrakh's living cloth (`.lc-bsvg`) and leaves any other stage player as drawn.
Ajrakh: `kutch-ajrakh/process/cloth-after-each-stage`.

## diagram

`DiagramSpec`: either a whole `drawing` (the borewell depth and the Bhuj distances) or a `chain`
of links, each a kicker and ordered parts: text blocks, drawings, step links into a reaction
player (`#rp-blue`, step n, with the figure reference) and a grouped equation with its tick count.
Ajrakh: three. A `diagram` with a `head` is the other form, composed from the figure kit and drawn
by its own view (`DeclaredDiagramSpec`, `components/monograph/kinds/kit/KitDiagramView.tsx`,
[component-specs-general.md](component-specs-general.md), The figure kit, decision 0199); a
delivered drawing of either form meets the bar for hand-drawn art there (The hand-drawn figure).

## molecule_3d

`Molecule3dSpec {head, molecules, side, key}`. Each model has its CID, yaw and pitch, name, dial
label, formula, atom line, note and its at-rest projection as a drawing; the dial's value is the
yaw in whole degrees. With side paragraphs the figure is `mols mol-two`. The kit redraws the model
from the page's molecule data on drag, on the arrow keys, Home and End and on Turn, and zooms it
from 0.6 to 2.5 times on plus and minus, a pinch of two fingers and a trackpad's pinch
(control and wheel); the dial's text names the zoom when it is not 1. Ajrakh: two.

A delivered model carries its own data as `geometry {atoms [[element, x, y, z]], bonds [[first,
second, order]], radius}`: PubChem's 3D conformer centred on its atoms' mean, to 4 decimals, the
radius the farthest atom's distance plus 0.42, or plus its largest atom's radius and 0.04 when
that is more (`science/molecule_conformer`, `science/molecule_elements.model_margin`), so a model
of carbon, hydrogen, nitrogen and oxygen keeps 0.42. A model with its
geometry draws one `<g class="mol-g">` holding each atom once as `data-a` and each bond once as
`data-b`, the groups the kit turns, and a page that places it carries `mol-data[cid] = {atoms,
bonds, R: radius, marks: []}` (`services/document_components_data.kit_data`). Its at-rest drawing
is the kit's own projection (`science/molecule_drawing`): Ajrakh's alizarin drawn from its data at
its yaw and pitch is the approved drawing, with each letter at the 12 px floor or larger. A model
without geometry, Ajrakh's and every authored one, reads `mol-data` from its home page as before.
A molecule key's `--atom-*` swatches are accepted at delivery for the atoms the design colours;
any other swatch is a depicted material.

The atoms the design colours are the molecule kit's table in `tools/design/system.json`
(`molecule.atoms`, decision 0202): carbon, hydrogen, nitrogen and oxygen as the approved kit draws
them, and silver, aluminium, gold, calcium, chlorine, chromium, copper, iron, mercury, potassium,
sodium, lead, sulphur, tin, titanium and zinc, the elements the crafts' held compounds contain.
Each is `--atom-<symbol>` in all four themes, filled through the kit's gradient `ag-<Symbol>`
(written into the kit defs for every atom the table holds, `services/document_kit_defs.atom_defs`)
and drawn at its table radius by the server (`science/molecule_drawing`) and the kit (`RAD` in
`monograph.js`); every atom but carbon and hydrogen carries its letter. The generator writes the
table for the server as `research/molecule_atoms.py`. A compound with an element outside it is not
drawn, and the composer names the element in `missing`.

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
switch, each with the script hook it carries. The stage drawing may be a kit scene at rest, its key
under the stage box. A toggle drawn outside a lab is open. Ajrakh: blue, red and wash water.

## process_replay

`ProcessReplaySpec {play, understood, angles, stages, sourcesKicker, sources, sectionsKicker,
sections, ready}`: the replay's timed stages (start and end in ms), the sources read in order with
their grade, and the sections written with what each drew. Ajrakh:
`kutch-ajrakh/overview/how-this-answer-was-made`; its heading `u1055` is the summary of the fold
around the anchor, outside it, and is not drawn by the view.

## coded_figure

`CodedFigureSpec {head, alt, code, values, texts, libraries?, map?, films?, still?}`
(`research/component_specs_science_coded`, decision 0231): a contributor's own HTML, CSS and script,
run in the answers' sandboxed frame over the page's cited data, as large as a chapter section.

- **`head {title, caption?}` and `alt`**: units; `alt` says what the figure shows and is drawn under it.
- **`code`**: an HTML fragment of at most 64 KiB (`coded_figure_code.CODE_MAX_BYTES`): markup, `style`
  elements and plain `script` elements (no attributes). Its geometry, colours, faces, labels,
  controls and decoration are its own; it is never refused for its look.
- **`values`**, up to 120 `{key, value, reading}`: every number the figure plots, animates or states.
  The frame passes them as `{key: value}` in `#kv-data` (`JSON.parse(document.getElementById("kv-data").textContent)`),
  and each `value` is stated by its `reading`, a unit citing the facts that state it.
- **`texts`**, up to 120 `{key, unit}`: the units whose words the figure shows. An element with
  `data-unit="<key>"` shows the unit's words and `data-unit-label="<key>"` gives them as its
  `aria-label`; when the code sets either attribute to another key, the frame shows that unit's
  words. Every unit the figure shows is listed beneath it with its citations ("Words and sources in
  this figure").
- **`libraries`**: `d3` (7.9.2, the global `d3`) and `three` (0.187.0, the global `THREE`), served
  from `/monographs/kit/vendor/` and loaded before the code.
- **`map {layers, districts}`**: `layers` any of `states`, `districts`, `rivers` and `relief`,
  `districts` up to 30 LGD codes. The frame draws the site's base as the first group of every
  `svg[data-map]`, and again if the code removes it: the land, the relief bands, the rivers, the
  district and state lines, the named districts outlined in place colour, the Rann and the Survey of
  India outline, in the India frame of `components/map/projection.ts` (`kvMap.viewBox`).
  `kvMap.project(longitude, latitude)` gives a point's `{x, y}` in that frame,
  `kvMap.box(west, south, east, north, margin?)` a `viewBox` for a part of it, and `kvMap.places`
  each named district's centre `{lgd, x, y}`. The base's classes (`kv-map-land`, `kv-map-outline`,
  `kv-map-state`, `kv-map-district`, `kv-map-river`, `kv-map-relief-1` to `-7`, `kv-map-home`,
  `kv-map-salt`) are drawn in the map tokens by the frame's sheet.
- **`films`**, up to 4 `{key, src}`: a film the site serves under `/monographs/` (`.mp4`, `.webm`),
  shown by `<video data-film="<key>">`, whose address the frame sets.
- **`still`**: an SVG of the figure at rest. Without it the server cuts the still from the code's
  one `svg` (`coded_figure_still.code_still`); a figure drawn on a canvas or with WebGL sends it. The
  served spec adds the still and its four theme variants (`services/drawing_themes.themed_spec`); a
  spec that sends `themes` is refused.

The frame (`lib/codedFigureFrame`, through `SandboxFrame` and `sandboxDocument`) has
`sandbox="allow-scripts"` and no other permission, and its policy allows inline scripts and styles,
the named library files and films, and `data:` images, nothing else, so the code reaches no network,
cookie, storage, other window or the page around it. It is given the page's tokens in the reader's
theme, a sheet that draws buttons, `aria-pressed`, focus, status lines and the map base in the design
(`FRAME_KIT_SHEET`), and the frame's stillness (decision 0218): under either reduced-motion switch no
timer, animation frame, animation or film plays. On the page the server draws the still, its words
filled from the units, and the frame's code loads within two screens of the viewport
(`kinds/science/NearCodedFrame.tsx`), the frame starting at the still's height. The export draws the
still with the figure's units beneath it (`services/page_export_coded`), and the Review page shows
the still beside a live run (`components/review/CodedFigureReview.tsx`).

Delivery refuses a coded figure only for these, each with its reason:

- **A fact of its own.** A number it shows (in its markup, a text attribute, a stylesheet's `content`,
  a prose string in its script, or its still) that is neither one of its values nor a counting
  number up to 12; a run of free text past a label's 80 characters and six words, which is a unit;
  a `data-unit`, `data-unit-label` or `data-film` key its `texts` or `films` do not hold.
- **Reaching out.** Anything the sandbox's safety rules refuse (`sandbox.sandbox_safety_problems`):
  `fetch` and every other network, storage, cookie, window, navigation and code-loading API, a
  `script` with attributes, a nested frame, a `link`, a `video` without `films`, an address; an
  element with one of the frame's ids (`kv-data`, `kv-words`, `kv-films`, `kv-map`); a library off
  the list; a film off the site.
- **Not at rest.** A script that times motion without reading
  `document.documentElement.dataset.reducedMotion`, which it must read to draw its last state at
  once; no still (no single `svg` and no `still`); a map declared with no `svg[data-map]`, or a map
  drawn by hand without `map` (`drawn_maps`).
- **Past its budget**: code past 64 KiB.

**When to use it.** Compose first: a reaction, a dip, a molecule or a what-if is `compose_component`'s,
and a figure a declared kind or the kit draws is that kind's. A coded figure is for what no kind or
composer expresses and Kutch Ajrakh shows: a reaction's molecules meeting and a bond breaking, a dye
bath scene, a route or a sequence of map states on the site's base, a stage scene that moves, a
three.js model, a film the site holds played beside its cited steps. Its code draws from its values
and its units; it rests on its finished state, draws it at once under reduced motion, and gives the
reader a pause.

## Composed from a craft's own facts

`compose_component {craft, kind, about?}` (MCP, the pages group; `services/compose_components`,
decision 0198) builds a `reaction_player`, `dip_player`, `molecule_3d` or `experiment_lab` with its
`choice_toggle`s finished from the craft's curated page and the facts it owns (`CuratedClaim`),
shown and stated as facts: the reactions in the order of their stages, the bath stages with their
colour after, a compound of its materials with PubChem's conformer, the alternatives its facts
state. A bath stage's colour is the depicted colour recorded with the fact that states it, else the
first colour its after names that a specimen token depicts from the dyes, mordants and resists the
stage uses, by the colour key's substance mapping (`research/colour_key.first_depicted`, decision
0202); a colour no token depicts is drawn in line work, its kit scene painting no colour, and named
in words in its phase's text, a stage whose after names no colour is left out with its reason, and a dip with no depicted
colour at all composes nothing. Every unit cites only those facts; a
label cites none, and a name that holds a number or a formula cites the facts that state it. When
the page holds too little it composes nothing and names what to propose (`open-work.md`, MCP).

Its scenes are kit scenes (`services/compose_kit.stage_scene`, decision 0200), each built from the
stage it draws and the facts that state that stage, at most three parts: the bath in the vessel those
facts name (a vat, pot, trough or pit), holding the piece in the stage's colour after (the token
recorded with its fact, else the one the substance mapping gives, `compose_kit.after_token`);
otherwise the cloth they name, or a piece of the shape they name, in that colour; for a printing
or resist stage, its first material with a recorded colour as a paste, applied as those facts name
(printed, spread or outline; a printing stage prints it when they name no way); and the heat source and the
water form they name. A bath with its piece dips, a cloth takes its colour. Each part is labelled by
the fact that names it (the stage's name for the bath, the colour after's fact for the cloth or piece,
the material's name for the paste). A dip player draws every phase and its scene so, and a phase the
kit cannot draw is left out and named, with the fact to propose; a phase whose colour no token shows
is drawn by the parts that take no colour (the bath without its piece, the paste, the heat and the
water). A reaction player draws each step's
stage as its scene when the kit draws every step's stage; otherwise it keeps one scene for all its
steps, drawn in line work (each species an ink outline, dashed when no colour is recorded for it), so
nothing is painted by hand.

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
| Each kind composed from fixture facts, refused with what to propose, citing only the craft's own facts; its scenes built from kit parts (`test_compose_kit.py`); a dip from colour names alone, a colour in words, a molecule with sulphur and a metal | `backend/tests/compose/`, `backend/tests/mcp/test_compose_tool.py` |
| The atoms the design colours, their radii in the server and the kit, their key labels and the model's margin | `backend/tests/science/test_molecule_elements.py`, `tools/tests/test_design_atoms.py` |
| Every atom's gradient in the kit defs, drawn as Ajrakh's | `backend/tests/research/test_kit_defs.py`, `frontend/e2e/molecule-atoms-unit.spec.ts` |
| Each of the five kinds that take a kit scene takes it beside its free drawing, a scene at rest names no motion, every kit scene label cites a fact, and a free scene painting what a kit part draws is refused | `backend/tests/research/test_kit_scenes.py`, `backend/tests/research/test_drawn_art.py` |
| Each of the five kinds draws its kit scenes and its free drawing, at 360 and 1440 px in light and dark, plays a shown part's motion and none under either reduced-motion switch, and Kutch Ajrakh's authored players draw no kit part | `frontend/e2e/kit-players-unit.spec.ts` |
| On a generated page at 360 and 1440 px, each composed kind whole at rest and worked by the kit, under both reduced-motion switches | `frontend/e2e/composed-interactives-unit.spec.ts` |
| A coded figure refused for a fact of its own, reaching out, not resting or its budget, with its reason, and accepted when it draws from its data with free labels; its still cut and served in four themes, and drawn on paper | `backend/tests/research/test_coded_figures.py`, `backend/tests/exports/test_coded_figure_export.py` |
| A coded figure's still at first paint, its frame sandboxed with its words, data and pinned libraries and nothing reaching the network, at rest under reduced motion, played and paused with motion allowed, its map base and outline kept in the site's projection, and its still beside its run on the Review page | `frontend/e2e/coded-figure-unit.spec.ts` |

Re-read it when a science kind gains a field, a held passage becomes a unit, or the colour rule changes.
