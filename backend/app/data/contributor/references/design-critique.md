# The designer's critique

`preview_page` hands back pictures of the page you built: its first screen at 390 and 1440 px wide
and each chapter at 1440 px, every picture captioned with its chapter. Before you propose, read
them as the page's designer would, chapter by chapter, against this rubric; write down what you
would fix; fix it; and preview again with your notes as `critique`. The critique is feedback you
give yourself and the reviewer, never a gate: only rule 28 and the truth and safety checks refuse a
page. The reviewer of your layout reads it beside the proposal, so they see what you judged.

Read the design system first (`kalavigyan-design/1`, its principles, non-negotiables and colours by
role in the four themes), then how Kutch Ajrakh set the same kind of chapter (`bar/1` lists its
chapters; `ajrakh-<chapter>/1` walks each one). Ajrakh is an example of the thinking, never a
template: ask what this page's reader needs, never for Ajrakh's counts or kinds.

## The rubric

Ask each question of every chapter picture. A chapter that answers them all well gets no note.

1. **Is there something to see?** A screen of prose with no figure, plate, table or margin note
   beside it is a wall of text. Name the passage and the figure its sentences call for: the
   mechanism they explain, the stages they list, the places and dates they name, the quantities
   they compare.
2. **Is it typeset, not stacked?** Figures sit beside the sentences that set them up, in the role,
   size and crop your layout gave them (margin, column, wide, bleed). One centred column of
   alternating blocks, or a figure two screens from its prose, is a note.
3. **Does a change move?** A reaction, a dip, a stage or a dated record is drawn as a player that
   steps through its states with its pause, each state cited. Boxes and arrows standing still where
   the facts describe a change are a note; so is a player whose frame does not show the change it
   names. A still picture cannot show motion: judge the frame.
4. **Is the map about the story?** A map frames the place the chapter is about, on the site's own
   base with the Survey of India outline, the page's place hatched in terracotta and a salt flat
   stippled, never water. A map of all of India for a story in one district is a note.
5. **Is every figure in the design's colours?** Indigo only on what can be pressed; madder only for
   emphasis, disagreement or hazard; terracotta for place; turmeric only as a highlight; data in the
   series and ramp colours; a material in its depicted-material colour with a key. A stock blue, a
   purple, a gradient or an unexplained red is a note, and so is a figure that would vanish in dark
   or high contrast (a fixed white ground, black strokes typed by hand).
6. **Does the type hold?** Reading text in the reading face at its measure, nothing under 12 px,
   labels that fit their boxes. Text running past its column or the phone's width, cut off, or
   overlapping a drawing is a note with the width it shows at.
7. **Are the pictures plates?** Caption first and credit after, under the plate; no picture twice;
   no stock, shopping or AI imagery where a photograph of the work belongs.
8. **Is it complete at rest?** Nothing loading, spinning, half drawn or showing a progress state;
   every figure readable without hover.
9. **Is the first screen the page's?** The masthead picture and the page's name, once, as its one
   headline, at both widths.

## Writing the notes

One note for each thing you would fix, in the order a reader meets them:

- `chapter`: the chapter key from the picture's caption (`opening` for the first screens);
- `where`: the figure or passage, by its heading, figure number or first words;
- `problem`: what is wrong, as the rubric's question finds it;
- `fix`: what you will do about it, concretely enough to act on.

Then a `verdict` of a sentence or two on the whole page. Fix what you noted, then call
`preview_page` again with the same draft and `critique: {verdict, notes}`: the notes you wrote on
the pictures you just read. The report and the preview card show it, and `propose_page` carries the
latest one to the reviewer with your layout. An empty `notes` with a verdict says you read every
chapter and would change nothing.

## When your client cannot see the pictures

A client that receives tool results as text alone (the Claude API's MCP connector is one) never
sees the pictures. It asks the server to read them instead with `read_pictures: true` on
`preview_page`: the server's own vision model reads the pictures by this rubric and returns its
notes in the report as `designRead`. It is off unless asked, runs only when the drawing passes,
spends at most a fixed sum a preview and reads the same pictures once. Its notes are as much
yours to judge as your own, and never fail a page.

## How this reference is kept true

| Rule | Kept true by |
|---|---|
| The critique is recorded with the preview, shown in the report, card and review, and never changes a verdict | `test_page_critique.py` in `backend/tests/pages` |
| The server's read runs only when asked, skips a failed drawing, keeps to its cap and reads the same pictures once | `test_page_design_read.py` in `backend/tests/pages` and `test_design_vision.py` in `backend/tests/images` |
| The server's read asks by this very rubric | `test_design_read.py` in `backend/tests/research` |
