# 0227. A generated page is set as its layout places it: each size, the margin, the crop and figures in the prose

A generated monograph draws every entry of its layout record: `COLUMN` at the measure, `WIDE` at
the content width, `BLEED` edge to edge, `MARGIN` (and role `SIDEBAR`) in the right margin of the
paragraph it follows from 1200px and after that paragraph below, and a `crop` as the box it names.
In a chapter whose paragraphs the layout leaves alone, the figures it places stand in the prose after
the paragraphs that tell them, not stacked between the chapter's heading and all of its text.

Date: 2026-11-26. Status: accepted (the lead's UX round of 2026-11-26, lane layout; the owner: "no
effort whatsoever has been put in formatting the entire page, how it should be typeset ... nobody
wants to read a wall of text"). It amends [decision 0106](0106-one-monograph-template-for-every-page.md),
item 3 (the one renderer), and [decision 0183](0183-the-shared-template-draws-the-approved-page.md),
item 4 (margin notes beside each paragraph). The contracts are `docs/contracts/page-layout.md` (How
the web draws a layout) and `docs/contracts/monograph-renderer.md` (The page).

| For | Read |
|---|---|
| One renderer for every page | [decision 0106](0106-one-monograph-template-for-every-page.md) |
| The approved page's margin notes on a generated page | [decision 0183](0183-the-shared-template-draws-the-approved-page.md) |
| The layout record and its rules | [page-layout.md](../contracts/page-layout.md) |
| How the web draws a document | [monograph-renderer.md](../contracts/monograph-renderer.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **The web read the layout for one thing.** `content.data["page-layout"]` reached the page with
  every entry's role, size and crop, and `lib/monographPlacement.ts` read it only to choose the
  masthead picture. A contributor's agent placed Sanganeri Hand Block Printing's 18 components with
  `WIDE`, `BLEED`, `COLUMN` and one `SIDEBAR` at `MARGIN`; the page drew them all in their kinds'
  frames, and the agent reported that "the site ignores margin and crop, so everything still stacks
  in one centered column".
- **Placed figures stacked before the prose.** `arranged_layout` puts the entries a layout names
  first in their chapter, so a layout that names only figures puts all of them between the chapter's
  heading and its text: Sanganeri's chemistry chapter drew eight figures, then 54 sentences of
  chemistry in 18 paragraphs with nothing between them. The renderer already set an unplaced figure
  left at a chapter's end after the paragraph that tells it (the words and sources the two share,
  rarest first), and skipped every figure a layout named.

## Decision

1. **Each size has its frame.** An entry's `size`, else its role's (`SIDEBAR` `MARGIN`, `OPENER`
   `WIDE`, `PLATE` `COLUMN`; `HERO` is the masthead; `FIGURE` and `BODY` keep the kind's frame),
   replaces the box steps of the component's home (`sizedHome`): `COLUMN` `div.screen >
   div.wrap.kv-passage > div.spread > div.main`, `WIDE` `div.screen > div.wrap.kv-passage`, `BLEED`
   the same wrap with `kv-bleed` (no maximum width, the safe-area insets for margins, a caption kept
   off the edge) and `MARGIN` no frame. The home's steps that are not the spread's own
   (`screen`, `wrap`, `kv-passage`, `spread`, `main`) stay as pass-through wrappers, so the kit's
   selectors still reach the view. The home carries `data-size`. A view that draws its own spread
   (an answer block) takes its column from the size: a nested spread is one block in a column or a
   margin, and an answer block spans the content width at `WIDE` and `BLEED`.
2. **The margin is the paragraph's.** A component or text unit at `MARGIN` stands in
   `aside.margin.note.keep` of the run it follows, after that run's source notes, each in
   `div.margin-plate`: beside the paragraph from 1200px (the spread's 240px column), after it in the
   reading column below 1200px, where the kit hides the notes and keeps the plate. A text unit there
   is `p.kv-beside-note`. A `MARGIN` component with no paragraph before it in its chapter is drawn in
   the column.
3. **A crop is the box it names.** A component with a picture and a crop carries `data-crop` and the
   box as `--kv-crop-x`, `-y`, `-w`, `-h` and `--kv-crop-ratio` (the box's width over its height in
   pixels): its frame takes that shape and shows exactly the box. The picture's focal box becomes the
   crop too, so a frame of fixed shape (the masthead's) centres on it.
4. **Figures stand in the prose.** In a chapter where the layout places no paragraph (no `BODY`
   entry naming a text unit), every component it places there but the hero and the chapter's opener
   is set in the prose: after the paragraph that tells it (its title, description, units and the text
   its spec holds against the paragraph's words and sources), figures sharing a paragraph in the
   layout's order, and one no paragraph tells after the figure before it in that order, or the
   chapter's opening paragraph. A text unit placed as `PULL_QUOTE` or `SIDEBAR` there stands after
   the chapter's opening paragraph. A chapter where the layout places a paragraph keeps the layout's
   order exactly, so an editor who places the paragraphs places everything.
5. **A pull quote is drawn as one**: `blockquote.kv-pull > p` in the column, closing its run.
6. **The authored page is never rearranged.** Kutch Ajrakh's shell takes no size, margin, crop or
   prose placement.
7. **The design system holds.** The spread is section 4's (`160px minmax(0, 680px) 240px`, 40px
   gaps) and "no right rail on a tablet" holds, since a margin item folds into the column below
   1200px. Nothing here departs from the system, so no owner instruction overrides it.

## What the documents do not carry yet

Beside Kutch Ajrakh's shell, Sanganeri's live document (19 components, read on 2026-11-26) cannot
show:
- **Dates in the left rail.** Its history prose holds no date per sentence; the dated record is a
  term run ("In the record", drawn as the record strip) and a `timeline` component.
- **Chapter openers and margin plates.** It holds no picture: no `picture_plate`, so no opener, no
  plate beside the prose and no crop to apply.
- **Provenance per chapter.** The document carries the page's sources and grades, not a curation
  date per field.
- **Fact grids and tables beside the prose.** A chapter's term runs and listed facts are units with
  no component of their own, so a layout places them one unit at a time; a `fact_table` component
  would take `MARGIN`.
- **A pull quote of its own.** None is placed; the layout must name the unit.

## Guidance for the contributor skill and the page checklist

The playbook lane owns those files this round; the text the agent needs is:

> Place every figure with intent. A layout entry's size says how wide it is drawn: `COLUMN` at the
> reading measure (a molecule, a choice toggle, a small chart), `WIDE` across the content width (a
> player, a map, swatch cards, a table), `BLEED` edge to edge (one strong picture or map per page,
> no more), `MARGIN` beside the paragraph it follows from 1200px and after it below (a material
> card, a small plate, a short sidebar sentence). With no size, `SIDEBAR` is `MARGIN`, `OPENER`
> `WIDE` and `PLATE` `COLUMN`; `FIGURE` keeps the kind's own width. Name only the figures, pull
> quotes and sidebars of a chapter, and the page sets each one in the prose after the paragraph
> that tells it; name a paragraph's unit as `BODY` only when you want the chapter drawn in exactly
> your order. A `crop` is the part of the picture that is shown. Look at the preview at 390 and
> 1440 px: at 1440 every margin item stands beside its paragraph.

## Consequences

- `lib/monographPlacement.ts` reads every entry (`placedEntries`, `layoutSizes`, `setInProse`,
  `slotPlacement`, `croppedDocument`); `lib/monographLayoutFlow.ts` moves a chapter's placed
  figures out of its flow and its pull quotes and sidebars after its opening paragraph;
  `lib/monographRenderLayout.ts` keeps a passage's margin items (`Passage.asides`) and lists a
  block's components with `blockLabels`, which figure numbering, the first sheet's scopes and the
  kin chapter read; `lib/monographRenderNear.ts` sets placed figures in the prose.
- `components/monograph/ComponentHome.tsx`, `ComponentSlot.tsx`, `BesideItems.tsx`, `NoteList.tsx`
  and `MonographPassage.tsx` draw them; `documentPage.css` holds the bleed, nested-spread, margin
  and crop rules.
- A curated craft's backfilled pictures (`PLATE`, `FIGURE`) move from the head of their chapter into
  its prose, and an `OPENER` picture is drawn at the content width.

## How this is kept true

| Claim | Kept true by |
|---|---|
| A `WIDE`, `BLEED`, `COLUMN` and `MARGIN` entry each take their frame or slot; a margin component's kit scope reaches the first sheet | `frontend/e2e/monograph-placed-layout-unit.spec.ts` |
| A crop reaches the picture as its box, at 1440 in a browser | the same spec |
| A margin entry stands beside its paragraph from 1200px and after it at 390 and 834; each size has its width | the same spec |
| Placed figures stand in the prose; a chapter whose paragraphs are placed keeps its order; a pull quote and a sidebar sentence | the same spec and `frontend/e2e/monograph-homes-unit.spec.ts` |
| A document without layout data, or with a layout naming nothing, draws as before | `frontend/e2e/monograph-placed-layout-unit.spec.ts` |
