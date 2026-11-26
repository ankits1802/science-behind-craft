# 0237. A preview's pictures are read as a designer would: by the contributor's own AI against a served rubric, and by the server only for a client that cannot see them

`preview_page` already hands back pictures of the page at 390 and 1440 px. A new reference, the
designer's critique (`design-critique/1`), is the rubric an agent reads them by, chapter by chapter.
`nextStep` asks the agent to write its notes, fix what it found and preview again with the notes as
`critique`. The critique is kept with that preview, shown in the report and the preview card, and
carried by `propose_page` to the reviewer of the page's layout. A client that receives tool results
as text asks the server to read the pictures instead, with `read_pictures`: the site's best vision
judge reads them by the same rubric, at most $0.50 a preview and once for the same pictures. Neither
the critique nor the server's notes ever fail a page.

Date: 2026-11-26. Status: accepted (the lead's lane brief `ux-1126/design-feedback`, redirected the
same day on the owner's direction that design feedback is done through MCP by the contributor's own
AI, the way [decision 0222](0222-contributors-ai-clients-look-at-the-searched-pictures-answers-show.md)
has contributors' clients look at pictures). It amends
[decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) (the agent sees and
judges its pictures), [decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md)
(the card's line and the report beside rule 29) and
[decision 0234](0234-a-contributor-s-ai-builds-a-page-over-mcp-from-one-line-and-the-run-keeps-what-it-made.md)
(the acceptance run's second opinion). The contracts are `docs/contracts/open-work.md` (the report,
`preview_page`, the view), `docs/contracts/review-queue.md` (the layout item) and
`docs/contracts/mcp-ask-and-upload.md` (the view's line).

Amended by [decision 0248](0248-what-the-fresh-agent-could-not-fix-on-sanganeri.md): the server reads a failed drawing's pictures too.

| For | Read |
|---|---|
| The preview and its pictures | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| Clients that look at pictures for the site | [decision 0222](0222-contributors-ai-clients-look-at-the-searched-pictures-answers-show.md) |
| The card and rule 29 | [decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md) |
| The acceptance run | [decision 0234](0234-a-contributor-s-ai-builds-a-page-over-mcp-from-one-line-and-the-run-keeps-what-it-made.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- The owner judges pages by eye against Kutch Ajrakh's design principles: maps of real quality,
  reactions that move, typesetting rather than a wall of text, every figure in the design language.
  Rule 28 checks that a page draws and rule 29 lists what its facts could show, but nothing asked
  the agent to look at the page as a designer would, so it stopped at a page that draws but reads
  badly and the owner had to say what was wrong.
- The brief first asked for the server's vision model to read every preview. The owner redirected it
  the same day: the contributor's own AI does the reading, through MCP, as it already looks at
  searched pictures (decision 0222). The server's read stays only for a client that cannot see
  images: the Claude API's MCP connector passes tool results as text alone, so the acceptance run's
  model never sees its pictures (decision 0234).
- `CAPTION`, the vision task the picture screen uses, has no seeded route and is not routable from
  the settings screen. The seeded `EVAL_JUDGE` routes put Claude Opus 5.5 first ("Evaluation judge"
  in the price list), a model that reads pictures (`CAPTION` is among its catalogued tasks); the
  second judge, Gemini 4 Argon, is not catalogued for pictures.

## Decision

1. **A served rubric.** `references/design-critique.md` (served as
   `kalavigyan://skills/references/design-critique.md`, the guide page `design-critique/1` and
   `/skills/references/design-critique.md`, so the skills lane can publish it) asks nine questions of
   every chapter picture, drawn from the design skill's principles, non-negotiables and colours by role
   in the four themes, with Kutch Ajrakh's chapters (`bar/1`, `ajrakh-<chapter>/1`) as examples of the
   thinking, never a template. It says how a note is written (`chapter`, `where`, `problem`, `fix`, then
   a `verdict`) and that the notes never gate a page. The contributor skill, the curation skill, the
   playbook's step 9 and its Done, and the page checklist (beside rule 29) name it.
2. **The agent writes its critique.** `preview_page` takes `critique: {verdict, notes[]}` (at most 24
   notes, each field at most 300 characters): the agent's notes on the pictures its last preview
   returned. It is kept on the new preview (`PagePreview.critique`) and shown in the report
   (`report.critique`). `nextStep` (`REVIEWED`) now asks for it every time: read the pictures against
   the rubric, write the notes, fix, preview again with them, then propose. No new tool: the tool count
   stays 26.
3. **The reviewer sees what the agent judged.** `propose_page` copies the latest live critique of the
   page by the same account onto the layout it proposes (`LayoutProposal.critique`). The review
   queue's layout item carries it (`LayoutReview.critique`), and the Review page shows it under the
   layout's changes (`components/review/AgentCritique.tsx`) as the proposer's AI's own judgement. A
   bundle without a layout carries none.
4. **The server's read, a fallback only.** `read_pictures: true` asks the server to read the pictures;
   without it nothing runs and nothing is spent. It reads only a drawing that passed rule 28 (a failed
   or unmade drawing is SKIPPED with its reason). It goes to the first `EVAL_JUDGE` route whose
   catalogued model reads pictures and whose adapter takes them, with the rubric, sections 1 to 3 of
   the design skill, Kutch Ajrakh's chapters as set (prose and figures in order, from its live
   document) and every picture under its chapter key, asking for JSON whose `chapter` is one of the
   pictured chapters. Its estimate (the text, 800 tokens a picture and 12,000 output tokens at effort
   `medium`) must stay within $0.50 (`DESIGN_READ_CAP_USD`), or it does not run; the reservation is
   made with that sum as the request's budget and recorded in the usage ledger as a `design read`.
   A read of the same pictures (`pictures_key`, a SHA-256 over every picture's name and bytes and the
   read's version) is taken from `DesignReadCache` for 30 days at no cost. A refusal or failure says
   so and is not cached. No fallback model is added: a refusal ends the read, as decision 0234 chose.
5. **One vision call for two uses.** The picture screen's call moved to `providers/vision_calls.py`
   (the routes of a task whose model reads pictures, the reservation, the call with text and pictures
   for each API shape, the settlement), and the picture screen and the design read both use it.
6. **Never a gate.** Neither the critique nor the server's notes change a rule, a count or the
   report's message; `propose_page` still refuses only a failed drawing and what the truth and safety
   checks refuse.
7. **The card.** The line gains one mark, the count of design notes to judge (the critique's, or the
   server's when there is no critique), or "No design note" as passing. Shown in full, the report sets
   "Your design critique" beside rule 29's opportunities (or asks for one), then the server's read when
   asked, with its model and cost.
8. **The acceptance run.** It draws the last preview again with `read_pictures: true`, so its second
   opinion is handed the server's notes and asked whether the pictures bear each out and what they
   missed; the summary lists the model's own critique and the server's notes as notes, never the
   verdict. The server's read spends the site's own judge budget, at most $0.50 a run, outside the
   run's cap. Reconciled the same round by
   [decision 0240](0240-an-agent-reads-a-page-s-brief-in-one-call-and-the-acceptance-run-tells-the-whole-story.md):
   the run asks for the read on each preview it calls for the model, at most $0.50 for each new set
   of pictures, and draws nothing again.

Nothing here departs from the design skill, and no motion is added.

## Consequences

- An agent that sees images reviews its own page before proposing, at no cost to the site, and the
  reviewer sees what it judged; an agent that cannot see images can still be told, at a bounded cost.
- Migration `0122_design_feedback` (after `0121_coded_figures`) creates `DesignReadCache` (row level
  security on, closed to the public roles) and adds the nullable `critique` to `PagePreview` and
  `LayoutProposal`; its downgrade drops them.
- Tests both ways: the critique kept and shown and absent when not given, carried to the layout and
  the review item, never changing a verdict (`backend/tests/pages/test_page_critique.py`,
  `backend/tests/mcp/test_mcp_preview_critique.py`, `backend/tests/db/test_design_feedback_db.py`); the
  server's read off unless asked, skipped for a failed drawing, read once for the same pictures, never
  changing a verdict and asking by the served rubric (`backend/tests/pages/test_page_design_read.py`);
  recorded model replies, a wall-of-text chapter named in a note and a well-set page given none
  (`backend/tests/research/test_design_read.py`); the route, the cost cap stopping the read before
  anything is reserved or sent, and a refusal (`backend/tests/images/test_design_vision.py`); the card
  (`frontend/e2e/page-preview-card-unit.spec.ts`), the review contract
  (`frontend/e2e/design-critique-unit.spec.ts`) and the acceptance run
  (`tools/tests/test_acceptance_design.py`).
- `backend/tests/images/test_picture_vision.py` now patches the shared call where it lives.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
