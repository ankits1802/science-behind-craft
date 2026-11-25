# 0215. Every searched picture a page or a zoom serves names its craft's world, and every drawing is judged by the paint a reader sees

A craft page without a dossier and an answer's zoom story now serve a stored or searched picture
by the one rule a section's pictures pass (not a shop's, and a searched picture linked by its words
only while its title names the craft's world), and such a picture never leads a page. The drawing
bar resolves every paint before it judges one (through `currentColor`, a gradient, a pattern and a
`use`, in strokes as in fills), and a data drawing of any kind paints no depicted material. A
generated explainer's motion is refused unless it reads the frame's own flag, and its SMIL, Web
Animations, canvas and script-built drawings, script-written colours and faded attributes are
refused at the bar.

Date: 2026-11-25. Status: accepted (the owner's adversarial review of the quality round, lane
`answers-art`, findings answers-art-1, -2, -3, -4, -5 and -7 of
`.lead/data/advreview-1125/review.json`). It amends
[decision 0207](0207-a-searched-picture-names-its-craft-s-world-and-a-stored-one-that-does-not-is-not-served.md)
(the craft-world rule now holds every path that serves a searched picture),
[decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) and
[decision 0200](0200-players-and-cards-drawn-from-the-kit.md) (the figure and scene bars read
resolved paints, and data drawings are held to the material rule) and
[decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md)
(the explainer's art bar). It builds on the shop rule of
[decision 0211](0211-a-picture-from-a-shop-a-stock-agency-or-an-auction-is-not-shown.md) and leaves
it as it is. The contracts are `docs/contracts/explainer.md` (the zoom story, Choosing, The bar on
a generated explainer's art), `docs/contracts/craft-page.md` (A craft without a dossier) and
`docs/contracts/component-specs-general.md` (check 8, The hand-drawn figure).

| For | Read |
|---|---|
| The craft-world rule it extends | [decision 0207](0207-a-searched-picture-names-its-craft-s-world-and-a-stored-one-that-does-not-is-not-served.md) |
| The shop rule it applies on two more paths | [decision 0211](0211-a-picture-from-a-shop-a-stock-agency-or-an-auction-is-not-shown.md) |
| The figure bar and the kit | [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md), [decision 0200](0200-players-and-cards-drawn-from-the-kit.md) |
| The explainer's art bar and its frame | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md) |
| Why no model call or input token is added | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Two paths served searched pictures past decision 0207.** A craft with no dossier
  (`craft_page_records._stored_extras`) served every picture stored against its claims and gave
  the first the `HERO` role: production's `/api/crafts/Block-Printing-Of-Akola/page` led with the
  Openverse photograph "stretch of art, dhamadka kutch", an Ajrakh picture of Kutch, on a page of
  Rajasthan's Akola printing. The zoom story (`zoom_pictures`) chose and served pictures with no
  craft context and read a level from the title together with Openverse's tag list.
- **The drawing bar read the paint as written, not as drawn.** `drawn_art._materials` read only a
  direct `var()` on a shape's fill, so a material painted through `currentColor` under a `color`
  of `--dye-indigo`, a gradient of `--dye-leuco` to `--dye-indigo`, a pattern or a `use` passed,
  and any `currentColor` stroke counted as ink. Only `drawing`, `diagram` and the five kit scene
  kinds were walked, so an authored `chart` of `form: drawing` painted in indigo passed.
- **The explainer's motion and drawing escaped the bar.** The motion check passed any script whose
  text held the word `reducedMotion`; SMIL and Web Animations were neither refused nor stopped by
  the frame's CSS guard; a `canvas`, a script-built SVG, a colour a script wrote by name and an
  SVG `opacity` attribute were never read.

## Decision

1. **One served rule.** `services/served_pictures.served_picture(picture, context)` refuses a
   stored link when `blocked_picture` refuses its picture, then a `TEXT` link of a searched picture
   (`searched_text_link`: not a curator's pick or a field photo, `CHOSEN_PICTURE_PROVIDERS`) whose
   title names nothing of the craft's world. `section_images.stored_items` reads it instead of its
   own copy, and so do the two paths below. `craft_picture_context.picture_context_of(session,
   craft)` reads the context for a craft already resolved.
2. **A craft page without a dossier.** `_stored_extras` reads each link's relevance and
   `stored_page_pictures(stored, context)` keeps the served links, at most six pictures as before.
   A picture with any searched `TEXT` link left (`PictureRecord.may_lead` false) never takes the
   `HERO` role: `page_pictures` gives it to the first inline picture that may lead, else to none, so
   the masthead falls back to its typographic plate and the searched picture stays a chapter plate.
   The rows stay; nothing is deleted.
3. **The zoom story.** `zoom_ground` reads the craft's context into `ZoomGround.context`, and
   `PicturesAsk` carries it. A searched candidate passes the shop rule (`shown_candidates`) and
   names the craft's world in its title before its level is read; a stored picture is read only
   when `served_picture` holds it. A level is read from the title, with the alt only for a
   curator's pick or a field photo, whose alt a person wrote; a searched picture's description and
   alt (the uploader's tags on Openverse) are never read for a level, as decision 0207 already
   held for the world.
4. **Paints as a reader sees them.** `research/drawn_paints.drawn_paints(root)` walks a drawing
   once, inheriting `fill`, `stroke` and `color` (`inherit` keeps the parent's), and resolves a
   paint: `currentColor` to the nearest `color`, or the page's text colour `--ink-1` when the
   drawing sets none (the colour it inherits on the page and in the frame); `url(#id)` with its
   fallback to every stop of a gradient and every shape of a pattern, following `href`; a `use` to
   what the element it places paints. The bar counts a material in a fill or a stroke, and line
   work in ink only when a stroke resolves to `--ink-1` to `--ink-3`.
5. **Data drawings paint no material.** Every kind outside the figure kinds, the five scene kinds,
   the molecule kinds and the swatch kinds is held by `drawn_art.data_drawing_problems`: a free
   drawing that paints a depicted material is refused, pointing to a composed diagram. Of the
   brief's two alternatives this takes the second: the kit-noun rule does not read a data
   drawing's words, because a chart's or a map's subjects (water, cotton, the sun, layers) are the
   kit's words, and refusing them would send data into a diagram or strip its accessible labels;
   the six-shape and ink rules are a figure's and not a chart's. A swatch's motif
   (`swatch_pair`, `swatch_cards`) is not held either: a swatch shows its material by design (the
   design rules already require its tokens to be materials), and Kutch Ajrakh's own swatch pair
   prints its kut motifs in `--dye-kut`.
6. **The explainer's motion.** A timer must read the frame's own flag (`.dataset.reducedMotion`,
   `.dataset["reducedMotion"]` or `.getAttribute("data-reduced-motion")`), not a word. A SMIL
   element (`animate`, `animateTransform`, `animateMotion`, `animateColor`, `set`), a `marquee` and
   a Web Animations call (`.animate(`, `.beginElement(`, `Animation(`, `KeyframeEffect(`) are
   refused, since neither switch stops them. Of the brief's three ways this takes the refusal,
   which holds at the draft and at reuse (`piece_reuse.reusable_simulation`) without touching the
   web client, which another lane holds.
7. **The explainer's drawing.** A `canvas` element and `getContext`, `OffscreenCanvas` or
   `createElementNS` in a script are refused: the script may change a figure's attributes and text
   but not build it, as the prompt already says. A paint a script writes (`setAttribute` of a
   paint or of `style`, `.style.<property> =`, `style.setProperty`, `cssText`) is judged like a
   declaration, and every named colour of CSS (148) is refused wherever a colour is read; a
   script's words are not, so a label "Indigo" or "Deep fast chocolate-black colour" stays text.
   `opacity`, `fill-opacity` and `stroke-opacity` below 1 are refused as attributes and as
   declarations.

## Consequences

- No model call and no input token is added (decision 0165): the prompt is unchanged, and every
  rule the bar adds is one the prompt already states (a static inline svg, no named colour, nothing
  faded at rest, nothing moving under either switch). A draft that breaks one is redrafted once,
  as any draft below the bar already was.
- An uncurated page whose only stored pictures are searched shows no masthead picture until a
  curator picks one or a vision check holds one, and fewer stored pictures are served on the 461
  crafts' pages; a zoom finds fewer levels, Openverse's short titles naming fewer level words.
- Left for the web client's lane: the frame still sets its motion guard only once its look is read
  (`frontend/lib/sandboxFrame.ts`), so a server render paints a CSS animation until hydration under
  the OS switch, and the frame neither pauses SVG animations nor stubs Web Animations; the bar now
  refuses the two, so no stored or new explainer carries them. A colour passed to a paint through a
  variable is not followed, and a `data:` image is not read as a drawing.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/curation/test_craft_page.py`, `backend/tests/db/test_stored_page_pictures_db.py`,
`backend/tests/journey/test_zoom_story.py`, `backend/tests/research/test_drawn_art.py` and
`backend/tests/research/test_simulation_art.py`.
