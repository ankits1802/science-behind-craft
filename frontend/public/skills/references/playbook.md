# The page playbook

KalaVigyan guarantees the research and the citations; you do the design and the build. You are
free to design and code anything the page's cited facts support, as coded figures: three.js
interactives, d3 and canvas figures, short films, up to a whole chapter section, as the agents who
built Kutch Ajrakh's page did. Every fact a figure shows comes from the page's cited research. The
person you work for names what they want to contribute and presses allow; at most they review.
What pages share is the design principles and the way of thinking: Kutch Ajrakh's page is the
worked example of that thinking, never a template. Each step names what to read first.

## The thinking

1. **Find the craft's story in its facts.** `get_page` with the subject and `parts: ["brief"]`:
   the page as published, every fact as its id and one line under its chapter, and rule 29's
   opportunities; its `cursor` brings the rest of the lines. Read whole with `get_facts` and `ids`
   only the facts you will cite, never field by field. Find its process, chemistry, place, history
   and people, and what is distinctive in each. Derive the page's lists (`page-checklist/1`):
   mechanisms, ambiguous terms, the signature fact. `reserve_tasks` the keys you will close.
2. **Decide what a reader must see and do to understand it.** Read the design principles first
   (`kalavigyan-design/1`, the whole system at `system/1`). Every field the sources cover is dense
   with cited detail; a figure sits beside the prose that needs it, never a wall of text; plates
   show the work; place is shown on a map; motion is used only where it explains, rests complete
   and always has a pause. For each mechanism, stage and moment, ask what a reader must see, move
   or compare to understand it, and sketch that figure.
3. **See how Kutch Ajrakh answered the same questions.** Read its chapters worked through
   (`ajrakh-chemistry/1` and the rest `bar/1` lists) and the cookbook (`cookbook/1`), which says
   what in Ajrakh's facts called for each of its figures. Take the reasoning, not the list.

## The making

4. **Open the draft.** `edit_draft` with the subject and the lists.
5. **Find what the story lacks.** Read `sources/1`, `quotes/1` and `fields/1` first. Search, read
   and check with `search_sources`, `read_source`, `lookup` and `supply_source`. Facts go to
   `propose_facts`, or into the draft when a figure cites them; structure to `propose_structure`:
   stage afters with colours and whys, reactions with every formula, native and botanical names,
   the GI record, terms, conflicts, open questions.
6. **Design and build each figure.** Code it as a coded figure whenever your design calls for one
   (read `kit-stylesheet/1`, `kit-script/1` and the cookbook's coded figure first). Use a kind the
   site already draws when it says exactly what you need (its cookbook entry, `components/1`, its
   schema `kalavigyan://components/<kind>.schema.json`; a table of values goes in as a dataset,
   `datasets/1`). `compose_component` is a helper that can save the work of a reaction, dip,
   molecule or what-if lab built from the page's structure: take what it returns when it fits your
   design, else build your own.
7. **Give the pictures, the masthead first.** Read rules 2, 3, 7 and 14 (`page-checklist/1` on).
   An open-licence picture goes by its `page_url`; a person's own only with their declaration.
8. **Lay it out.** Read the cookbook's placing section. Each chapter alternates prose and the
   figures it sets up, each with its role, size and crop.
9. **Preview and judge it as a reader.** `preview_page`; look at every picture it returns; fix
   each failed rule from the checklist page it hands you; ask of each chapter whether a reader
   sees what they need beside the words. Then read the pictures as the page's designer, chapter
   by chapter, against the rubric (`design-critique/1`): write your notes, work through each, and
   preview again with them as `critique` before you propose. A client that cannot see pictures
   adds `read_pictures` for the server's read.
10. **Propose, then the next round.** `propose_page` with the draft. A draft holds 10 components
    and 20 facts, so a full page goes in rounds: follow the parts with `get_proposal`, open the
    next draft for the same page with `edit_draft` and go on from step 5.

The first `edit_draft` that adds components is answered with the design pages, a `read_token` and
nothing changed, which is expected, not a failure. Read the pages and repeat the call with that
token.

## Done

When the latest preview fails no rule, every field its sources cover is dense on the page, each
mechanism, stage and moment of its story has the figure a reader needs beside its prose, no
screen is a wall of text, and your latest critique leaves nothing you would still fix. The report's counts beside Ajrakh's are a mirror, never a target.

## What to ask the person

Only what they want to contribute and what only they hold: the page or field, a picture they own
with its declaration in their words, a source only they can read. Never which kind, tool, layout,
size or order: those are yours. Show them the preview link, and the confirm link when the server
holds the page for them.

## When the site falls short

A thing the page needs that no tool here can make is KalaVigyan's gap, never the person's problem.
Build everything else, then tell them in one line what the page still lacks and that the site has
to add it; a refused call is already recorded with its reason for the team, and the open work
lists the gaps the server computes.

## How this reference is kept true

| Rule | Kept true by |
|---|---|
| The steps in this order, and every address it names a page the server serves | `test_playbook_cookbook.py` in `backend/tests/mcp` |
| The server's instructions and the opening guide hand it first | `test_step_guidance.py` in `backend/tests/mcp` |
