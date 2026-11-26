# 0200. The players, the choice panels and the label card draw kit scenes, the composer builds its scenes from the kit, and a hand-painted scene a kit part draws is refused at delivery

Every scene slot of a reaction player, a dip player, a stage player, a choice toggle's stage box and
a label card's seal takes a kit scene beside its free drawing: one to three named parts of the
figure kit with their cited labels, drawn by the site inside the slot's own frame. The interactives
composer builds its reaction and dip scenes from the kit wherever a part draws what the stage's
facts name, and a free scene that paints by hand what a kit part draws is refused at delivery with
the part to use.

Date: 2026-11-24. Status: accepted (the lead's lane `kit-players` of the page-quality round, after
the owner judged the Sanganeri page built over MCP: "the animations that it is creating are
completely lacklustre ... the svg look like shit"). It amends
[decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) (the bar now
holds the players' and cards' scenes at delivery, and the texture rule gives way to the kit),
[decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) (the composed
players' scenes) and
[decision 0202](0202-a-dip-s-colours-from-its-facts-the-crafts-dyes-and-pigments-and-twenty-atoms.md),
item 1 (a dip phase whose colour no token shows is a kit scene drawn in line work, not the outlined
piece). The contracts are `docs/contracts/component-specs-science.md` (Rules every science spec
follows, reaction_player, dip_player, stage_player, choice_toggle and Composed from a craft's
own facts), `docs/contracts/component-specs-plates.md` (label_card) and
`docs/contracts/component-specs-general.md` (checks 7 and 8, Kit scenes, The hand-drawn figure).

| For | Read |
|---|---|
| The kit's parts, its vocabulary and the bar for hand-drawn art | [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) |
| The composer and the kit driving every page's players | [decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) |
| A dip's colours from the substances its stages name | [decision 0202](0202-a-dip-s-colours-from-its-facts-the-crafts-dyes-and-pigments-and-twenty-atoms.md) |
| The named motions and the two reduced-motion switches | [decision 0092](0092-design-system.md) and the kalavigyan-design skill, sections 2.13 and 6 |
| A composed reaction step draws its species, not its stage, and the kit plays every player in view (amends this record) | [decision 0228](0228-players-molecules-and-timelines-that-play-and-a-reaction-s-species-drawn-from-the-kit.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The players still took free drawings.** Decision 0199 composed figures from the kit but left
  a `reaction_player` step's art and its one scene, a `dip_player`'s scene and phases, a
  `stage_player`'s drawing, a `choice_toggle`'s stage box and a `label_card`'s seal as `SvgNode`
  (or plate `DrawingElement`) trees, so every player a contributor or the composer made was drawn
  node by node.
- **The bar was waiting on them.** The art kit's last change held only `drawing` and `diagram` to
  the bar at delivery and kept the scene rules in `drawn_art.scene_problems` uncalled, because the
  composer's own scenes (a rectangle in the colour after, swatches painted per species) would have
  been refused with nothing to draw them with instead (its compose tests failed on the bar).
- **The kit drives players by their markup.** The page kit (`monograph.js`) swaps a dip phase's
  first `svg` into the scene box and shows a reaction step's `.rx`; it binds only Ajrakh's living
  cloth for a stage player, and threw on any other one, stopping the rest of its scope's bindings.

## Decision

1. **One kit scene, one home.** `research/component_specs_kit_scene.py` holds `KitScene`
   (`parts` one to three kit parts of `component_specs_kit`, `motion?` one of the kit's motions
   explaining one of them), told from a drawing by its `parts` (`scene_form`), and the slot unions:
   `SceneDrawing` (a dip scene or phase), `StepArt` (a reaction step's drawings or one kit scene),
   `StillDrawing` and `SealDrawing` (a stage player's drawing, a stage box, a seal: a kit scene there
   names no motion, since nothing shows it again). The five kinds are `KIT_SCENE_KINDS`; a step whose
   art is a kit scene needs no where icon. The web's copy is `lib/componentSpecsKitScene.ts`
   (`kitSceneShape`, `sceneOr`, `stillOr`).
2. **The site draws it in the slot.** `components/artkit/KitScene.tsx` draws a scene's parts with
   `KitPartArt` in a 240 by 160 frame (a single-part seal in its square), filling the slot at every
   width, its ground carried past the frame so a box of another ratio shows no band; the key of
   framed swatches and cited labels sits beside the frame (in the reaction step under its art, in
   the dip strip under each phase's text and under the scene box, under the stage box and after the
   seal), and the kit's textures are drawn once per component. A view that draws no kit scene
   renders exactly as before, so Kutch Ajrakh's parity holds.
3. **A part moves with the state that explains it.** The page kit's chemistry scope plays the
   shown scene's moving part with the design system's named motion (`kitMove` sets the
   `data-playing` hook of `app/motion.css`): a reaction step when the reader chooses it or Play
   reaches it, a dip phase or the scene as Dip again shows it, the dip box's key swapped with its
   drawing. Under either reduced-motion switch the kit never calls it and the motion rules are off,
   so each press shows the state at once. A stage player the kit does not draw is left as drawn
   (`if (!svg) return`), so the rest of its scope still binds. The three copies of the kit (its
   source part, the served script and Ajrakh's static page) carry the same lines.
4. **The composer composes from the kit.** `services/compose_kit.stage_scene` builds a stage's
   scene from the facts that state it: the bath in the vessel they name holding the piece in its
   colour after (`compose_kit.after_token`: the token recorded with its fact, else the one decision
   0202's substance mapping gives the stage's dyes, mordants and resists), else the cloth they name
   or a piece of the shape they name in that colour,
   a printing or resist stage's first coloured material as a paste applied as they name (a printing
   stage prints it when they name no way), and the heat source and water
   form they name; three parts at most, a bath with its piece dips and a cloth takes its colour,
   each part labelled by the fact that names it. Choices the facts do not name are never chosen for
   them, save the cloth's plain swatch. A dip phase the kit cannot draw is left out and named with
   the fact to propose; one whose colour no token shows is drawn by the parts that take no colour
   (the bath without its piece, the paste, the heat and the water), its colour named in words as
   decision 0202 has it; a reaction player draws each step's stage when the kit draws them all, and
   otherwise keeps its one scene in line work, painting no material.
5. **The bar follows.** Check 8 holds every free scene of the five kinds to the bar
   (`drawn_art.scene_problems`, called by `drawn_art_problems`): text on the type scale, six shapes
   and line work in ink, and no depicted material painted by hand, textured or not, which points to
   a kit scene in that slot (`SCENE_POINTER`) naming the part that draws it. The texture rule is
   gone. Check 7 holds every kit scene's part labels to a cited fact
   (`kit_scene_label_problems`). Kutch Ajrakh's authored players never pass through the delivery,
   so they are not re-checked.
6. **The fixtures meet it.** The Bidriware reaction and dip fixtures and the dhokra stage player
   draw kit scenes (a pot of the open vessel, a vessel with its silver inlay, the fire and the
   sprinkled water), citing the facts that state each part; the label card keeps a free seal in ink.

## Consequences

- A contributor's or the composer's player is designed rather than drawn, and a scene drawn by hand
  in a depicted material is refused with the part to use; a `VARIANT` of an authored player redraws
  its scenes from the kit.
- Most real pages compose kit scenes only where their facts name a vessel, the cloth or a shape and
  their materials or colours after have depicted colours: Sanganeri's reaction player keeps its
  line-work scene until its printing stage's material has a depicted colour, which decision 0202's
  records (Bagru's, Dabu's and Pattachitra's) and its mapping of a stage's colour after do not give
  it. The colours a family lacks are asked
  of the design generator, as before.
- The interactives skill's interim rule ("Until a player takes kit parts ...") and the component
  guide's "textured in a player" are replaced by the lead from the lane's report.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_kit_scenes.py`, `backend/tests/research/test_drawn_art.py`,
`backend/tests/compose/test_compose_kit.py`, `backend/tests/compose/test_compose_dip.py`,
`backend/tests/compose/test_compose_reaction.py`, `backend/tests/research/test_kind_fixtures.py`,
`frontend/e2e/kit-players-unit.spec.ts` and `frontend/e2e/composed-interactives-unit.spec.ts`.
