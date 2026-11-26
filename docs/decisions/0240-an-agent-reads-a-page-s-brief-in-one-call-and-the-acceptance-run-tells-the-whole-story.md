# 0240. An agent reads a page's brief in one call, and the acceptance run tells the whole story

`get_page` gains a `brief` part: in one compact result, the page as published (its lede, each
chapter's headings, sentences, fields and figures), every fact as its id and one line under its
chapter, rule 29's opportunities and the layout's version, with a cursor that continues the fact
lines and never repeats one. `get_facts` reads facts whole by `ids`. Playbook step 1 starts from the
brief. The acceptance harness keeps every call's input and result, names each tool error, runs
`preview_page` itself so no picture reaches the model, estimates the tokens and dollars of each
tool, takes a cap up to $40 (default $25) and says how far the build got.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-1126/agent-path`, on the first
acceptance run, workflow run 45774629812). It amends
[decision 0234](0234-a-contributor-s-ai-builds-a-page-over-mcp-from-one-line-and-the-run-keeps-what-it-made.md)
(items 1, 3, 7 and 8: the cap, the tools offered, what is kept and the pictures drawn again),
[decision 0237](0237-a-preview-s-pictures-read-as-a-designer-by-the-agent-and-by-the-server-only-when-asked.md)
(item 8, the server's read in the run; see the reconciliation below) and
[decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md)
(playbook step 1: the brief, then whole facts by id). The contract is `docs/contracts/knowledge-api.md`
(`get_page`, `get_facts`); the operations are in `docs/RUNBOOK.md` (Agent acceptance).

| For | Read |
|---|---|
| The acceptance run this changes | [decision 0234](0234-a-contributor-s-ai-builds-a-page-over-mcp-from-one-line-and-the-run-keeps-what-it-made.md) |
| The playbook and the guide pages | [decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md) |
| Rule 29's opportunities | [decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md) |
| Every decision, by group | [README.md](README.md) |

## Context

The first acceptance run asked Claude Opus 5.5 to deepen Sanganeri Hand Block Printing. It spent
$8.09 of its $12 cap in 3 turns and 51 calls (15 `get_page`, 15 `get_facts`, 8 `read_source`, 5
`edit_draft`, one of them refused, 3 `search_sources`, one each of `find_crafts`,
`list_components`, `list_open_work`, `compose_component` and `preview_page`) and stopped before its
only preview answered. The money: 663,469 cache-written tokens ($3.32), 6,088,143 cache-read tokens
($2.44) and 116,660 output tokens ($2.33). The transcript did keep every call's arguments and result,
cut at 2,000 characters, and the refused edit's message (a borrowed molecule and dip player citing
facts the page does not hold); it kept no result's full size and said nothing per tool.

Measured offline (the guide pages exactly, from the server code at `deploy/main`; the facts
estimated from the live Sanganeri page, its 344 cited claims serialised as `get_facts` serialises
them, 625 bytes each with quotes and locators, its 79 sources at 357 bytes, and the live coverage's
counts, with the two fields whose results were short enough to keep whole, SOCIETY with no fact and
POLICY with one, as observed):

- **The 15 `get_facts` calls** returned about 188 KB: 224 facts for the 192 the page holds, 115
  sources for its 42 and the same craft reference, page link and attribution 15 times. A fact placed
  in several fields came once per field, and a field's sources came again with every field. The
  agent made 15 calls because the tool gives at most 50 facts with no cursor, so one call per field
  (15 of the 16; PHYSICS was skipped) was the only way to read them all, and step 1 said "`get_page`,
  then `get_facts`".
- **The 15 `get_page` calls** returned about 159 KB. One read the coverage and layout: 70.6 KB, of
  which the layout's 528 entries were 58.4 KB and the opening guide (playbook and bar) 7.6 KB. The
  other 14 read guide pages, 88.2 KB: the playbook again (6.2 KB, just handed), the design pages,
  the cookbook, the checklist, the kit, the contents three times (20.3 KB, looking for an address)
  and one contract page. The guide is served one page of at most 6,000 bytes per call.
- **The check.** Turn 1's results come to about 313 KB, 125,000 tokens at 2.5 characters a token;
  the API wrote 171,726 tokens in turn 1, the rest being the prompt, the tool list and the model's
  own output. Every one of those results sat in the context of every later request: about 35
  sampling requests, ten a turn before each pause. Turn 3 also wrote 424,860 tokens for 11 calls,
  most of the context written again after a long stretch of thinking (59,349 thinking tokens).
- **Replayed** through the harness's new estimate with the recorded run's order and requests, the
  tool results and arguments come to about $2.56 of the run's $5.75 of input; with one brief read in
  place of the coverage-and-layout read and no per-field `get_facts`, about $1.05.
- **The brief, built from the live document** by the code below: an outline of 6.2 KB (9 chapters,
  their headings, fields, 19 figures) and fact lines of about 157 bytes each. The live document
  cites 303 claims, sent in two calls (39.9 KB with 214 lines, then 15.6 KB with 89, no line twice);
  the 192 facts `get_facts` holds fit one call of about 36 KB.

The Claude API's MCP connector carries text blocks only in an `mcp_tool_result` (decision 0234),
and whether it hands an image to the model as text is not documented. A harness can change only what
it sends back, and editing a result already in the history breaks the prefix that Claude Opus 5.5's
preserved thinking is bound to.

## Decision

1. **The brief.** `get_page` takes `parts: ["brief"]` (not among the parts read when `parts` is
   absent) and returns `brief: PageBrief` (`backend/app/research/page_brief.py`, built by
   `backend/app/services/page_brief.py`): the name, the lede, each chapter in page order with its
   title, headings, published sentences, fields with claims and standing, figures with label, kind,
   title, role and size from the layout, pictures and facts counted; rule 29's opportunity lines
   (the preview's own `opportunities`, over the stored document and the craft's balanced reactions
   and ordered stages); the layout's version; and every fact the page may cite, once, as its id and
   its text on one line of at most 120 characters, under the chapter its first field is placed in
   (`coverage_chapters.FIELD_CHAPTERS`), in chapter and page order. A result is at most 40,000
   bytes. A researcher's brief keeps held facts, as `get_facts` does.
2. **A cursor that never repeats.** When the lines do not fit, `cursor` (`<offset>:<12 hex>`, the
   offset of the next line and a digest of the ordered fact ids) continues them:
   `get_page` with the same subject, `parts: ["brief"]` and the cursor sends only the lines still to
   come, no outline. A cursor is refused once the page's facts change and when no line is left; a
   cursor without the brief part is refused.
3. **Whole facts by id.** `get_facts` takes `ids` (1 to 50, without `field` or `query`): those facts
   whole with their quotes, locators, details and cited sources, in the page's order, and no open
   work. An id the page does not hold is refused, naming it.
4. **Less said twice.** The brief hands no guide page and no per-fact source or attribution; its
   `nextStep` is the playbook's step 2. The coverage read's `nextStep` and the tool descriptions
   point at the brief first. Playbook step 1 (both copies) and the contributor skill's step 3 (both
   copies) read: the brief, then `get_facts` with `ids` only for the facts a figure or sentence will
   cite, never field by field. The server's `initialize` instructions are left as they are: they hand
   the playbook first, and they belong to the MCP extensions lane this round.
5. **The run calls `preview_page` itself.** The connector's toolset no longer enables
   `preview_page`; the run offers it as a client tool with the server's own description and input
   schema (read once with `tools/list`; a server that lists none stops the run before any request).
   When the model calls it, the turn stops with `tool_use`, the run calls the server over its own
   connection, keeps the pictures as files and hands back a `tool_result` of text only, each picture
   replaced by one line saying the run kept it. History is only appended to. The pictures and report
   in the summary are the model's own last preview's; nothing is drawn again after the run.
6. **The transcript keeps everything.** Schema version 2: every call's arguments and every result,
   the run's calls among them, cut at 4,000 characters with the count left out and the full size in
   `chars`; each call says whether the connector or the run made it.
7. **Each tool's share, estimated.** The API reports usage per request, not per tool, so the summary
   and `cost.json` (`byTool`) estimate it (`tools/acceptance/spend.py`): each argument and result at
   2.5 characters a token (calibrated on turn 1 above), paid once as output when the model wrote it,
   written to the cache once and read by every later request, a request being each tool round of a
   turn. The summary prints the turns' actual input and output beside it.
8. **What failed, and how far it got.** The summary lists each tool error with its turn and message
   (600 characters), and says how far the build got: briefs read, the turn the draft opened, the
   facts and components added in how many edits, whether the page was laid out, and how many
   previews answered with the last one's failing rules. The run prints the same at the end.
9. **The cap.** A dispatch may set it above $1 and up to $40; the default is $25, in the workflow
   and on the command line.

## Consequences

- A step-1 read that carried about 260 KB through every later request (the per-field facts and the
  coverage-and-layout read) carries about 36 KB for a page of 192 facts, and the facts a figure
  needs come whole on demand. The context after the first turn should be about half of run 1's.
- Expected cost, not measured (the lane never dispatches the workflow): the first successful
  `preview_page` at about $4 to $6, mostly the output of writing figures; a run that goes on to fix
  and preview again about $10 to $15, well inside the $25 default.
- A model on this path still never sees its pictures (decision 0234); the run keeps them, the second
  opinion reads them, and they cost the model nothing.
- `get_page` and `get_facts` keep their earlier arguments and answers; a client that never asks for
  the brief or ids sees no change except the descriptions and the coverage read's next step.
- No migration, no new dependency, no new tool (the tool budget stays at 26 of 32).

## Reconciled with decision 0237 (same round)

[Decision 0237](0237-a-preview-s-pictures-read-as-a-designer-by-the-agent-and-by-the-server-only-when-asked.md)
(item 8) had the run draw the last preview again after the loop with `read_pictures: true`. The two
lanes merged into one harness (`fix/agent-path-merged`): the run adds `read_pictures: true` to every
`preview_page` call it makes for the model (`HARNESS_ADDS` in `tools/acceptance/request.py`), since a
model on this path cannot see pictures, which is exactly the client 0237 offers the server's read
to. The server's notes come back in that preview's `structuredContent` (`report.designRead`) and in
its `nextStep` text; the second opinion weighs the last preview's notes and the summary lists them.
No preview is drawn again. Each read spends the site's own judge budget, at most $0.50 for each new
set of pictures (a read is kept by its pictures), outside the run's cap. Tested by
`tools/tests/test_acceptance_design.py` (a handed preview asks for the read; a read's notes, or
none when it was skipped, reach the second opinion and the summary) and
`tools/tests/test_acceptance_harness.py` (a tool the run adds nothing to is called as asked).

In the same merge the server's `initialize` instructions, left by item 4, start a page with the
brief too: `get_page` with `parts: ["brief"]`, then `get_facts` with `ids` for the facts to cite,
as playbook step 1 does (`backend/tests/mcp/test_playbook_cookbook.py`).

## How this record is kept true

It is not edited after acceptance except to mark it superseded. Its rules are tested by
`backend/tests/research/test_page_brief.py` (the outline, the opportunities, one line per fact, the
40,000-byte bound over 600 facts, a cursor that never repeats, and the refused cursors),
`backend/tests/mcp/test_page_brief_reads.py` (the brief part and its cursor through `get_page`, held
facts for a researcher, `ids` read alone and an unknown id refused),
`tools/tests/test_acceptance_harness.py` (pictures stripped and kept, the run's own calls, the
per-tool estimate by hand, the progress lines), `tools/tests/test_acceptance_loop.py` (the client
tool answered and continued, a stray run call stopped, the cap up to $40 and its default) and
`tools/tests/test_acceptance_evidence.py` (4,000-character trims with full sizes, the errors and
the summary's table).
