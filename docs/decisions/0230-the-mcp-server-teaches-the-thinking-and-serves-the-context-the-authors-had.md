# 0230. The MCP server teaches the thinking and serves the context Kutch Ajrakh's authors had

A contributor's AI is handed an ordered playbook first: find the craft's story in its facts, decide
what a reader must see and do by the design principles, read how Kutch Ajrakh answered the same
questions, then design and build the page's own figures, coding any figure the cited facts support.
The server also serves what the developer sessions that built Ajrakh worked from: the design
system, Ajrakh chapter by chapter with every component's spec, and the kit's stylesheet and script.

Date: 2026-11-26. Status: accepted (the owner, through the lead, 2026-11-26). It amends
[decision 0203](0203-the-guide-handed-over-page-by-page-at-the-step-it-serves.md) (the guide handed
over at the step it serves: the opening guide is now the playbook and the bar) and
[decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) (a craft's own
interactives composed: the composer is now a helper, not the path). The contract is
`docs/contracts/open-work.md` (Guide pages).

| For | Read |
|---|---|
| The guide's pages and steps | [decision 0203](0203-the-guide-handed-over-page-by-page-at-the-step-it-serves.md) |
| The composed interactives | [decision 0198](0198-a-craft-s-own-interactives-composed-and-played-on-every-page.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- On Sanganeri Hand Block Printing a contributor's AI on the same model that built Kutch Ajrakh
  stopped at 19 components against Ajrakh's 80, hand-drew a reaction player's scenes, drew a plain
  timeline for the dated record, and told the owner the rest was "not fixable from here". The
  difference was what the model was given: the developer sessions had the design system, the kit's
  source, the reference boards and Ajrakh's document; the MCP agent had the initialize
  instructions, the checklist's opening, a table of Ajrakh's counts and the tool descriptions.
- The owner, 2026-11-26: "I do not need to dictate anything ... most of it can be done through the
  prompting itself"; "Context is the limitation, then add more context"; and, correcting the first
  plan, "I do not want each and every page to be an exact copy of Ajrakh. I want the design
  principles to be the same, guided by the same thought process." And: the platform guarantees the
  research and the citations, the agent does the design and the build, free to code three.js, d3,
  canvas or film figures as Ajrakh's authors did, every fact from the page's cited research.
- The audit of the contributor journey is in the lead's notes (`.lead/data/ux-1126/audit.md`): 20
  guidance items fixed here and 14 code items for the lead.

## Decision

1. **A playbook, handed first.** A new reference, `references/playbook.md` (one guide page,
   `playbook/1`), in ten steps under The thinking and The making, each naming the guide pages to read
   before it; with what to ask the person (only what they want to contribute and what only they
   hold), when a page is done (no failed rule, every field dense, each mechanism and moment with its
   figure beside its prose, no wall of text; the bar a mirror, never a target) and what to do when
   the site falls short (KalaVigyan's gap, never the person's). The initialize instructions are its
   short form; `get_page` with the fields or a page's coverage and the `curate_page` prompt hand it
   with the bar in place of the checklist's opening, which the playbook's first step names.
2. **A component cookbook.** A new reference, `references/cookbook.md`: one entry for every kind the
   registry knows (`## \`<kind>\``), each with what it shows, when a page needs it, why Kutch Ajrakh
   has one (what in its facts called for it, every Ajrakh component by label, chapter guide and
   anchor), the tool that makes it, its facts, its place (chapter, role, size, crop) and its check,
   and the shape of a spec filled by hand. It opens on how a figure gets made: designed first, coded
   freely, a kind the site draws where it says exactly what is needed, a composer when its result
   fits. `edit_draft` hands a kind outside `KIND_RULES` its cookbook entry. The entries for kinds
   other lanes add read correctly before and after they land: `coded_figure` (decision 0231),
   composed `stage_player` and `timeline_map`, scenes that move (decision 0228) and the one-call
   composition (decision 0229).
3. **The authors' context, served.** The design skill and SYSTEM.md as skill files
   (`kalavigyan-design/1`, `system/1`), byte for byte the files in `.claude/skills/kalavigyan-design`
   and copied to the site; Kutch Ajrakh worked chapter by chapter (`ajrakh-<chapter>/1`,
   `research/bar_references.py`), read at serving time from the document the server holds: the
   chapter in order, then each component's kind, field, anchor, title, description, place and units,
   and its spec with texts past 160 characters, lists past 3 items and drawings below 2 levels cut;
   and the kit's `monograph.css` and `monograph.js` whole in one fence each (`kit-stylesheet/1`,
   `kit-script/1`). A guide's topic is its file's name in lower case.
4. **Every page-building tool says where it sits.** `get_page` (a named page) and `preview_page`
   return a `nextStep`; the descriptions of `get_page`, `get_facts`, `compose_component`,
   `edit_draft`, `preview_page`, `propose_page`, `list_components` and `propose_structure` and the
   next steps of `edit_draft`, `compose_component` and `propose_page` name the playbook's step, the
   cookbook or the next tool, and a full page is proposed in rounds of a draft each.
5. **The design skill where the owner differs.** The owner's direction that a contributor's AI may
   design and code any figure the facts support goes beyond the design skill's components list; the
   design skill's rules for every figure (tokens by role, motion only to explain, complete at rest,
   a pause, both reduced-motion switches) still hold for a coded figure, and the playbook says so.

## Consequences

- An agent reads the design system and Ajrakh's worked chapters before building, and designs a
  page from its own craft's facts; Ajrakh's counts no longer read as the target nor as optional.
- The guide grows by the playbook (1 page), the cookbook, the design skill (12 pages), SYSTEM.md
  (25), thirteen worked chapters and the kit (120 pages); every page stays within 6,000 bytes and
  `contents/1` lists them all.
- Tested in `backend/tests/mcp/test_playbook_cookbook.py` (the playbook's steps in order and its
  thinking, every address it and the cookbook name served, an entry for every registry kind so a
  new kind without one fails, every Ajrakh component in its kind's entry, the worked chapters, a
  spec trimmed to its shape, the kit guides whole, the design skill in three places, each tool's
  place in the playbook), `test_step_guidance.py` (the opening guide, a kind's cookbook entry, the
  next steps, the instructions), `test_guide_pages.py`, `test_mcp_prompt_curate.py` and
  `test_skill_references.py` (the design skill is the source the references draw from, so it is
  served as written and not held to the no-restating rule).
- Left for the lead: the audit's code items, among them the draft's limits of 10 components and
  600 kB, no path for an agent to file a site gap, and the reading and media chapters no
  contribution reaches.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
