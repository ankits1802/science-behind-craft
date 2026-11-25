# 0218. An explainer's frame is still from its first paint under either switch, a drawing's paint is read through its variables, and a drawing keeps to the kit's classes and its box

A generated explainer's frame is drawn still until the page has read that neither reduced-motion
switch is on, and under either switch it holds every motion still whatever the explainer's script
does: no SMIL animation, no Web Animation, no CSS animation or transition a script brings, no
animation frame, no interval and no chain of timeouts. The drawing bar follows a paint through the
custom properties the drawing declares, a design role's name included, and refuses a variable the
drawing never declares that the design does not define, where the page could hold a depicted
material. A generated explainer declares no token the frame takes from the page and shows no
`data:` image. A drawing's `class` names only the classes the kit's own drawings carry, and an
`svg` is drawn within its box.

Date: 2026-11-25. Status: accepted (the owner's leftovers round, lane `drawings`, the items decision
0215 and decision 0216 left; `.lead/tools/lanes/review-1125/leftovers.md`). It amends
[decision 0215](0215-every-searched-picture-served-names-its-craft-s-world-and-every-drawing-is-judged-by-the-paint-a-reader-sees.md)
(the paint the bar reads, the explainer's art bar and its frame),
[decision 0216](0216-a-contributed-drawing-loads-nothing-a-timeline-map-s-key-holds-its-place-and-download-fails-gently.md)
(the one rule every drawing attribute meets, on both sides),
[decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md)
(the generated explainer's frame) and
[decision 0055](0055-generated-explainers.md) (the explainer's prompt, which now asks for no image).
The contracts are `docs/contracts/explainer.md` (The bar on a generated explainer's art, The frame,
The frame's stillness), `docs/contracts/component-specs-general.md` (check 8, The hand-drawn
figure), `docs/contracts/component-specs-plates.md` (`DrawingElement`) and
`docs/contracts/component-specs-science.md` (drawings); the contributor's rule is in
`references/components.md` (Inline drawings stay in their box).

| For | Read |
|---|---|
| The paints the bar reads and the explainer's bar and frame | [decision 0215](0215-every-searched-picture-served-names-its-craft-s-world-and-every-drawing-is-judged-by-the-paint-a-reader-sees.md) |
| The rule every drawing attribute meets on both sides | [decision 0216](0216-a-contributed-drawing-loads-nothing-a-timeline-map-s-key-holds-its-place-and-download-fails-gently.md) |
| The explainer's frame and its look | [decision 0201](0201-an-answer-s-figures-composed-from-the-kit-and-its-generated-art-held-to-the-bar.md), [decision 0059](0059-sandbox-and-what-if-renderers.md) |
| Why no model call or input token is added | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The frame moved before the page read its look.** `useFrameLook` has no look on the server and
  in the first client render, and `sandboxDocument` then wrote neither `FRAME_MOTION_GUARD` nor the
  `data-reduced-motion` attribute, so a reader with either switch on saw an explainer's CSS
  animation run until hydration. Under either switch the guard set only `animation` and
  `transition` to `none`, which stops neither a SMIL element, a Web Animation, a `marquee`, a CSS
  animation a script writes `!important` into a `style`, nor a script's own frames and intervals;
  the bar refuses the ones it can read, but a stored explainer or a script that hides one was held
  by nothing in the frame.
- **A paint through a variable was read by its name.** `drawn_paints` took `var(--ink-1)` for ink
  wherever it appeared, so `style="--ink-1: var(--dye-indigo)"` on a group painted every edge below
  it indigo while the bar counted line work in ink and no material. `css_declarations` could not
  even read a custom property whose name holds a digit (`--ink-1`), and the explainer's sheet could
  redeclare the frame's own tokens (`:root{--c-ink-1: …}`) unread. A variable the drawing never
  declares is the page's: the kit sets `--dip-c` to `var(--dip-1)`, a depicted material.
- **A `data:` image was not a drawing to the bar.** The sandbox allows `data:image/…` in a
  generated explainer, and the art bar read only inline `svg`, so a figure shown as an image, or an
  animated one, passed unread and moved under both switches.
- **A drawing's class and size were unbounded.** A contributed drawing's `class` (or `className`,
  which the views pass on) could name a site utility (`fixed inset-0`, `animate-spin`), and an
  `svg`'s `width`, `height`, `transform` or `overflow` could draw it far past its box, over the page.

## Decision

1. **The frame is still until the page reads its look.** `sandboxDocument` with no look (the
   server's render and the first client render) writes `data-reduced-motion="true"` and
   `FRAME_MOTION_GUARD`; with a look it writes the attribute only when either switch is on, as
   before. Of the two ways to close the gap (the server reading the reader's switch, or the frame
   still until the client reads it), this takes the second: the server cannot know the system
   setting, and the design's rule is that the server and first client render move nothing. The
   frame already reloads when its look arrives, so no reload is added.
2. **The frame holds every motion still under either switch** (`FRAME_STILLNESS`, a script in the
   head before the explainer's markup, active when the attribute is set or the frame's own
   `prefers-reduced-motion` matches). It sets the attribute and puts it back if a script removes
   it; it removes every SMIL animation element as it is added, so the drawing rests at its own
   attributes, which the design makes its end state (pausing at time 0 would rest on the first
   frame instead); it stops a `marquee`; it settles every Web Animation as it is made, played,
   reversed, seeked or retimed (finished at its end, or cancelled to the default style when it
   never ends); after every change to the document it settles every running CSS animation and
   transition, which catches one a script or a stronger rule brings past the guard before it is
   painted; and it grants no animation frame and no interval, and drops a timeout set from inside
   a timer's callback, so a figure stepped by a timer stays at rest while a one-off timeout (a
   first draw deferred, a debounce) still runs. With neither switch on it does nothing.
3. **A paint is read through the drawing's own variables** (`research/drawn_paints`). Custom
   properties a group or shape declares in its `style` are inherited with `fill`, `stroke` and
   `color`, and every value is resolved where it is declared, as CSS resolves it: a `var()` takes
   the nearest declaration in scope (an own one first), its fallback is read as well when the
   variable is the page's, and a property that refers to itself, directly or through others, is
   invalid, so a paint that names it falls back to the parent's. `css_declarations` reads a
   custom property's name with its digits. The bar (`drawn_art`) refuses a material reached this
   way as one painted by hand, and refuses a paint that names a variable the drawing does not
   declare and the design does not define for a drawing (not a drawing role, an indigo or a
   molecule token), naming it, since the page may hold a material in it.
4. **The explainer keeps the page's tokens and shows no image** (`research/simulation_art`). A
   declaration, in a sheet, a `style` or a script's `setProperty`, `cssText` or `style`, that sets a
   custom property named for a token the frame takes from the page (a drawing role, the indigo
   family, `--font-ui`, `--font-reading`, or the `--c-` channel of one) is refused; a custom
   property of the explainer's own may hold layout values and design roles but no literal colour
   and no depicted material. Any `data:image/` in the fragment, entities read first, is refused:
   of the brief's two ways (read an embedded SVG image as a drawing, or refuse it) this takes the
   refusal, since a raster image cannot be read at all, an image can animate under both switches,
   and the prompt already asks for a static inline `svg`. The prompt's URL line now asks for no
   image instead of allowing one, a few tokens shorter (decision 0165 counts none added).
5. **A drawing keeps to the kit's classes and its box, on both sides.** A `class` or `className`
   names only `research/drawing_classes.DRAWING_CLASSES`, the 201 classes the kit's own drawings
   carry (the monographs, the kind fixtures and the golden document), stated again in
   `lib/drawingAttributes.DRAWING_CLASSES` and in `shared/drawing.attributes.golden.json`
   (`drawingClasses`), which both sides' tests hold equal to what the stored drawings carry. An
   `svg` element of a `DrawingElement` or an `SvgNode` meets `svg_box_problem` /
   `svgBoxRefusal`: its `width` and `height` are `auto`, a percentage up to 100% or a length no
   larger than its viewBox's, a `transform` (attribute or style) is only a `scale` of 1 or less
   about its own centre, it sets no `transform-origin` or `transform-box`, and its `overflow` is
   not shown. The cases are the golden's `svgBoxes`. The viewBox parser has one home on each side
   (`drawing_attributes.svg_view_box`, which the general intake now imports;
   `drawingAttributes.svgViewBox`, which the where icon now reads).

## Consequences

- No model call is added, and the prompt is a line shorter. A stored explainer that redeclares a
  token, holds a colour in its own custom property or shows a `data:` image is no longer reused
  (`piece_reuse.reusable_simulation`) and is drafted again when next asked for; the sandbox
  corpus's inline data image now falls below the bar and is redrafted.
- No stored drawing is refused: the 3,388 class attributes in 29 of the 109 stored files carry
  only the listed classes, the 150 `svg` elements set no size, transform or overflow, and the kind
  fixtures paint only roles. Kutch Ajrakh's authored figures are not re-checked by the bar, so the
  page's own variables (`--hand`, `--ill-*`) in them stay; a contributor may not use them. A kit
  class may carry the kit's own motion (`fly`, `mv`), which the kit's sheet runs only when neither
  switch is on.
- A reader with motion allowed sees the frame still for the moment before hydration, then the
  explainer as it was written; nothing else changes for them.
- **What is left.** The frame's policy still allows `data:` images (the sandbox contract of
  decision 0059, which the lesson decks share): the bar refuses every one it can read, so only a
  script that assembles one from pieces of a string, which the sandbox's own string rules do not
  catch either, could show one, and an animated image shown that way would move. A loop that waits
  between its steps on a promise rather than a timer's callback escapes the dropped nested timeout;
  the bar's rule that a timer reads the frame's flag holds such a script. These stay here and in
  the report, not in the debt register.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`frontend/e2e/sandbox-frame-still-unit.spec.ts` (the server's frame still, and nothing moving
before the look, under the site's switch and under the system's, a SMIL element, two Web
Animations, two forced CSS animations, a marquee, frames, an interval and a timeout chain among
them, while all of them play with neither switch on), `frontend/e2e/generated-explainer-unit.spec.ts`
and `frontend/e2e/production-checks-unit.spec.ts` (the frame's document and its policy read first
either way), `backend/tests/research/test_drawn_art.py` (a redeclared role read as the material it
holds, a self-reference as nothing, a variable followed where it is declared, and one never
declared refused, with the role-painted drawings kept), `backend/tests/research/test_simulation_art.py`
(a page token redeclared in a sheet, a style or a script refused, an own property holding a colour
or a material refused and one for layout kept, and every way of showing a `data:` image refused),
`backend/tests/simulations/test_simulation_builder.py` (the corpus's data image redrafted), and
`backend/tests/research/test_drawing_attributes.py` with `frontend/e2e/drawing-attributes-unit.spec.ts`
(one class list on both sides equal to what the stored drawings carry, a site class and an
oversized, grown, moved or overflowing `svg` refused by both drawing models, a kit class and an
`svg` within its box kept, and a label card's seal laid over the page refused).
