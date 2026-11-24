# 0203. The guide is served in numbered pages and handed over at the step it serves, and a page's first components wait until the design pages are read

Every guide the MCP server serves is cut into numbered pages of at most 6,000 bytes, read by topic
and page as a resource or with `get_page`'s `guide`; the page tools hand the agent the page for the
step it is on, at most two a result with the next named; a page's first components are answered with
the design pages and go in once the call comes back with the token those pages carry; and the
server's instructions say where to start and that the guide comes as the agent works.

Date: 2026-11-24. Status: accepted (the owner: "Paginate the instructions if required", after the
Sanganeri Hand Block Printing page, built by Opus in Claude.ai over MCP, showed no sign that the
agent had opened the contributor skill, the page checklist, the component guide or the design
pages). It amends [decision 0191](0191-room-for-the-page-quality-tools.md) (its point 2, long guidance
paged) and [decision 0110](0110-contributor-supplied-sources.md) (the `curate_page` prompt, which
carried every reference whole). The contract is `docs/contracts/open-work.md` (MCP, Prompts,
Resources and Guide pages), with `knowledge-api.md` (`get_page`) and `mcp-ask-and-upload.md` (the
pictures' reply).

| For | Read |
|---|---|
| The room the list was given, and the rule that long guidance is paged | [decision 0191](0191-room-for-the-page-quality-tools.md) |
| The studio and the `curate_page` prompt this changes | [decision 0110](0110-contributor-supplied-sources.md) |
| The design rules and the figure kit the first components wait for | [decision 0131](0131-drawings-in-the-design.md), [decision 0199](0199-a-kit-of-figure-parts-and-hand-drawn-art-held-to-the-bar.md) |
| The preview's report, whose failed rules hand over their pages, and the bar | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **A client's model sees three things.** Claude.ai shows its model the server's instructions, the
  tool descriptions and the tools' results. The contributor skill, its six references, the
  contracts and the design pages (`kalavigyan://design/drawing.md`, `answer-kit.md`) are resources,
  which its model cannot open by itself: the person must attach one. The Sanganeri page shows the
  rules nobody read: hand-drawn figures, no picture in the first screen, no interactive of its own.
- **The method was whole or nothing.** The `curate_page` prompt carried six skill sections and all
  six references whole, about 100 KB, and only when the person chose the prompt; the tools carried
  none of it. The references are 4.6 to 21.7 KB each and the contracts up to 80 KB.
- **The server keeps no session.** `POST /api/mcp` is stateless: it issues no `Mcp-Session-Id`, and
  an OAuth grant outlives any one conversation, so neither tells the server what a conversation has
  read.

## Decision

1. **Every guide is served in pages.** A guide is every `text/markdown` resource but the index,
   named by its file (`page-checklist`, `components`, `storyboard`, `drawing`, `open-work`,
   `kalavigyan-contributor` and the rest), beside two the server makes: `bar`, Kutch Ajrakh's
   pictures, figures, interactives and maps chapter by chapter, and `contents`, every page of every
   other guide with its sections. `data/guide_pages.paged` cuts a guide into pages of at most
   6,000 bytes: whole `## ` sections while they fit, a longer section at its blank lines, a longer
   paragraph at its lines, a longer line at a character, never at a heading inside a fence. The
   pages joined are the guide byte for byte, so each reference stays its rules' one home; a new
   reference is paged as soon as it is served. Each page names its guide, number, count, the
   sections it holds, the next page and the whole guide, and read as
   `kalavigyan://guides/{topic}/{page}` its text opens on that line.
2. **Resources and an argument, not a new tool.** The pages are a resource template, for clients
   that read resources, and `get_page {guide: "<topic>/<n>"}` reads any of them, for those that do
   not. No tool is added: the finding was that an agent did not choose to open the guide, and a
   tool to fetch it is one more thing to choose, while results reach every client; `get_page` with
   no subject already read the guide's sixteen fields; and the contributor skill, which teaches
   every tool by name, is left to the lead.
3. **The page at the step.** A result's `guide` holds one or two pages and names the next:
   `get_page` with the fields or a page's coverage, and `curate_page`, the checklist's opening and
   the bar; `edit_draft` adding components, each kind's design rules (`KIND_RULES`) and, for a
   `drawing` or `diagram`, the figure kit's part specification; `preview_page`, the checklist page
   of every rule the report fails, rule by rule; `give_pictures`, the pages of rules 2, 3, 7 and 14;
   `compose_component`, the storyboard. A section an anchor names that is renamed fails a test.
4. **Read before building.** A draft's first `edit_draft` that adds components, and a
   `preview_page` of a bundle with components, are answered with a tool error that changes nothing
   and carries the design pages (components' "The design rules for a contributed figure" and "The
   figure kit") and a `read_token`; sent again with it, the call goes on. The reading is known by a
   token the session keeps: `kvread-` and 16 hex digits of the SHA-256 of the design pages'
   addresses and texts. Only a session handed those pages can send it, the server keeps nothing,
   and a changed page changes it. A draft that holds components is not held back again.
5. **The instructions say where to start.** `find_crafts`, `get_page` and `get_facts` to read,
   `curate_page` for a whole page, and that the tools hand the guide over page by page as the agent
   works, with `get_page`'s `guide` and `contents/1` for the rest.
6. **`curate_page` carries pages.** It carries its steps, the checklist's opening and the bar, each
   headed by where it sits, a paragraph on which tool hands which page, and Never; no reference
   whole.

## Consequences

- The tool list keeps 23 tools for a contributor; `get_page`, `edit_draft` and `preview_page` each
  take one more argument, within decision 0191's 100 KB.
- A result that hands pages is up to 12 KB longer; a page's first components, and every preview of
  a bundle with components, cost one more call in a conversation that has not yet been handed the
  design pages.
- A conversation that resumes a draft holding components is not shown the design pages again
  before it adds more; each add still hands its kinds' pages.
- The contributor skill, the curation skill and the interactives skill do not yet name the guide
  pages, `get_page`'s `guide` or `read_token`; the lead merges the lane's skill text.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by `backend/tests/mcp/test_guide_pages.py`,
`backend/tests/mcp/test_step_guidance.py`, `backend/tests/mcp/test_mcp_prompt_curate.py` and
`backend/tests/mcp/test_tool_budget.py`.
