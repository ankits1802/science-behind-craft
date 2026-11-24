# 0197. A generated page's colour key is drawn by the site from its cited stage, dye and mordant colours, and a masthead without a photograph names the craft once

A craft page built over MCP opens its chemistry chapter with a colour key, as Kutch Ajrakh opens
its colours with swatches: the site reads every colour the page's own structure states (a stage's
colour after, a mordant bath's swatch, a dye or mordant card's fact), draws each as the depicted
material that shows it or names it in words, and sets its cited sentence and why beside it. A
masthead without a photograph draws the page title and the family's plate, and a screen reader
hears the craft's name once.

Date: 2026-11-24. Status: accepted (the lead's page-quality brief of 2026-11-24, lane colour-key;
the owner judged the Sanganeri Hand Block Printing page far below Kutch Ajrakh's). It amends
[decision 0183](0183-the-shared-template-draws-the-approved-page.md), item 1 (the label card on the
typographic plate), and [decision 0145](0145-monograph-pages-and-speed-without-debt.md), item 7 (the
unit ranges by origin). The contracts are `docs/contracts/page-layout.md` (Colour key),
`docs/contracts/component-specs-plates.md` (`swatch_cards`), `docs/contracts/monograph-renderer.md`
(Label masthead), `docs/contracts/monograph-document.md` and
`docs/contracts/component-specs-general.md` (the delivered range).

| For | Read |
|---|---|
| The generated masthead and the label on its plate | [decision 0183](0183-the-shared-template-draws-the-approved-page.md) |
| One unit pattern, in ranges by origin | [decision 0145](0145-monograph-pages-and-speed-without-debt.md) |
| The specimen tokens and their frame | [decision 0092](0092-design-system.md), and `.claude/skills/kalavigyan-design/references/SYSTEM.md` 2.5 |
| A generated page's kin crafts, drawn the same way | [decision 0180](0180-places-abroad-yearly-series-picture-levels-figures-and-kin-crafts.md) |
| Open-licence pictures for the masthead slot | [decision 0192](0192-open-licence-pictures-placed-by-their-page.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **No colour data, no key.** Kutch Ajrakh's page opens its colours with `swatch_cards` ("One
  cloth, four chemistries"), authored from its boards. A page built over MCP holds only what its
  facts and structure state, and nothing drew a key from them: a contributor would have to deliver
  `swatch_cards` by hand, with a before and after swatch for every colour, and Sanganeri's page had
  no colour stored at all.
- **The colours are already cited.** A stage's `after` names up to three colours, each stated by
  its fact's quote (`STAGE_AFTER`, the `colour` check of `structure_proposals_values`); a stage's
  why is its own cited sentence; the mordant bath figure reads each mordant's colour from facts
  (`signature_rules`); a material card's fact may quote "gives a red". On the Kutch Ajrakh golden
  page eight of fourteen stages name a colour.
- **A swatch must not be invented.** The specimen tokens are records of a craft's material
  (`tools/design/materials.json`); a colour no token depicts has no hue the site may draw.
- **Three names in the masthead.** Without a photograph `MastheadPlateView` drew the title (`h1`),
  the plate's knocked-out name and, over the plate, the label card's name: three times on screen,
  twice to a screen reader (the plate is hidden from it, the label's title is not). With a
  photograph the label's title was read again after the `h1`.

## Decision

1. **The site draws the key.** `place_colour_key` (`services/monograph_generated_colours.py`) adds
   a `swatch_cards` component `<slug>/chemistry/colour-key` at the head of the `chem` chapter of a
   craft's generated document, after the chapter's pictures. `services/colour_key.key_colours`
   reads the page's `DocumentStructure`: each colour of each stage's `after` (its dyes, mordants and
   resists as the agent, the stage as the swatch caption, the after text as the sentence and the
   stage's why after it), each mordant bath swatch (`<dye> on <mordant>`) and each colour a dye or
   mordant material card's fact states as `step_colours` reads its quote. The facts these rest on
   are fetched with the page's sentences (`key_claim_ids`).
2. **A colour appears only where a shown fact names it.** A candidate is kept when its sentence
   names its colour (`states_colour`) and every claim it cites is visible and not a hypothesis; a
   sentence or why the page already tells as a `p` is left off, so no held unit repeats a page
   sentence (rule 25). One card per colour: the first that a token depicts, else the first, in the
   order the page tells them. A page with fewer than two colours, or one already registering a
   `swatch_cards` component, draws no key, never an empty one.
3. **The swatch is the token that depicts the named substance.** `research/colour_key.
   DEPICTED_COLOURS` names, for twelve specimen tokens, the colour word each shows and the
   substances it depicts (indigo blue, its green leuco form, madder and alizarin red and pink,
   harda yellow, iron black on tannin as `kut` only for an iron paste, never bare "iron", lime
   white, kesari orange, gach mud brown, cobalt blue, quartz white, sem green).
   `depicted_material(colour, names)` returns the token whose colour matches and one of whose
   substances is a whole phrase of one agent name, else nothing, and the colour is drawn in words.
   A quote that states the change ("at first green, it turns blue") adds the before swatch joined
   by `becomes`. Each swatch is the existing `SwatchCardsView` figure: the token, the kit's weave,
   the 1px ink-2 frame over the raised mat.
4. **`swatch_cards` takes one swatch, none, and a why.** `ColourCard.before`, `join` and `after`
   are optional, `before` only with its `join` and its `after`; `why` is an optional second cited
   unit drawn after the text in one paragraph. The web shape refuses the same. Kutch Ajrakh's
   spec, with every field, dumps and draws exactly as before.
5. **The key's units have their own range.** `KEY_UNITS` is `u8901` to `u8999`; delivered
   components keep `u5001` to `u8900`. The key's kicker ("Colour key"), title ("<Count> colours
   and what gives each", the count the cards drawn), intro (the colours named) and each card's
   captions, name and agent are plain units; its sentences are cited `span` units held within it.
6. **The masthead names the craft once.** Without a photograph the stage holds the family's plate
   (texture, knocked-out kicker and name, hidden from screen readers) and, over it, a label of the
   GI line and the place alone, or no label when the craft has neither. With a photograph nothing
   on screen changes; the label's title is hidden from screen readers, since the `h1` names the
   page.

## Consequences

- A page whose stages name their colours gets its key on its next build, with no contributor
  delivering a figure; the Kutch Ajrakh golden page keys five colours (yellow by harda, white by
  lime, black by its iron pastes, blue by indigo, red by madder). Sanganeri's gets one once its
  stages' afters name colours: the Skill text teaches agents to propose them.
- A colour from a dye no token depicts (turmeric, pomegranate, lac) is named in words until the
  owner approves a new specimen record for it in `tools/design/materials.json`; the key never
  draws a hue from a colour word alone.
- The answers' step colours (`DYE_FILL`) still map colour words to tokens; they are the answer
  screens', not this key's, and are not changed here.
- A delivered component past `u8900` would be refused for room; none holds a hundredth of that.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_colour_key.py`, `backend/tests/layouts/test_generated_colour_key.py`,
`backend/tests/research/test_component_specs_plates.py`, `backend/tests/research/test_unit_ids.py`,
`frontend/e2e/colour-key-unit.spec.ts`, `frontend/e2e/monograph-generated-unit.spec.ts` and
`frontend/e2e/monograph-kinds-plates-unit.spec.ts` (Kutch Ajrakh's four colours unchanged).
