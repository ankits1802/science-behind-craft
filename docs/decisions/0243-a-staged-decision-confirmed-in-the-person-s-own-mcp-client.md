# 0243. A staged decision is confirmed by its person in their own MCP client: when an Admin's AI stages a batch, a client that shows forms asks that person at once to confirm all, some or none, saying what each item will do, and only their answer confirms, through the Review page's own checks

When an Admin's AI stages review decisions over MCP (queue decisions, corrections, the removal or edit
of published content, a page proposal's decision), a client on protocol 2026-07-28 that declares form
elicitation answers the call with a form put to the signed-in person whose AI staged the batch. The
form says in plain words what each item will do, and for a page decision the chapters and components
it touches and a private link to the page as it stood and as it will be; the person confirms all, the
ones they tick, or none. Only that answer confirms, by the same `confirm_batch` the Review page uses;
anything not confirmed waits on the Review page as before.

Date: 2026-11-26. Status: accepted (the lead's lane brief `review-elicit`, UX round of 2026-11-26, on
the owner's word that everything is usable through MCP with a person confirming every decision). It
amends [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) and
[decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) (a staged batch was
confirmed only on the Review page), [decision 0235](0235-the-mcp-server-speaks-2026-07-28-with-skills-tasks-questions-and-files.md)
(three tools asked the person, each before it ran; one admin tool now asks after it runs) and
[decision 0236](0236-a-reviewer-sees-a-page-as-it-stood-and-as-it-will-be-and-decides-it-whole-by-chapter-or-by-component.md),
item 9 (the seam it left at `staged_review_confirm.confirm_batch`, now filled). The contracts are
`docs/contracts/review-queue.md` (Staged over MCP: Confirmed in the person's client),
`docs/contracts/open-work.md` (Protocol 2026-07-28: Questions to the person) and
`docs/contracts/knowledge-api.md` (The 2026-07-28 protocol and its extensions).

| For | Read |
|---|---|
| Staging, the dry run and the one-press confirmation | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) |
| The removal and edit of published content | [decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) |
| Form elicitation, `input_required` and the sealed `requestState` | [decision 0235](0235-the-mcp-server-speaks-2026-07-28-with-skills-tasks-questions-and-files.md) |
| A page proposal's decision, staged as `PAGES`, and its before and after | [decision 0236](0236-a-reviewer-sees-a-page-as-it-stood-and-as-it-will-be-and-decides-it-whole-by-chapter-or-by-component.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- Decision 0236 lets an Admin's AI stage a page decision with `stage_reviews`, and decisions 0170 and
  0194 let it stage queue decisions, corrections and the removal or edit of published content; a
  person confirmed every one on the web Review page only. Decision 0235 added form elicitation: an
  `input_required` result, answered by the client on a retry that carries the server's sealed
  `requestState` and the person's `inputResponses`.
- The owner wants everything usable through MCP, with a person confirming every decision. The brief
  asks that confirming in the client run exactly `confirm_batch`'s checks and audit, that the form go
  only to the person whose AI staged the batch and only while they hold the review scope, and that an
  AI can never answer it.
- The three questions of decision 0235 are asked before their tool runs, from its arguments. This one
  cannot be: what the form shows (each item's label, the page proposal's parts) exists only once the
  batch is checked and stored, and asking first would run every decision's dry run twice.
- In the protocol the form goes to the client, which shows it to its user; the model chooses only a
  tool's `arguments`. `inputResponses` and `requestState` travel beside the arguments, written by the
  client. The server cannot see who filled a form, so what it can make sure of is where an answer may
  come from.

## Decision

1. **Asked after the tool runs** (`api/mcp_tool_base.AsksAfter` and `FollowUp`, `api/mcp_calls.py`).
   A tool may name `after {ask, answered}`. For a client that declares form elicitation the tool runs
   and commits as before; `ask` then reads its reply and may return one question with the references
   it needs, sealed into the `requestState` under a new purpose, `asked_after` (`api/mcp_state.py`),
   with the tool, the arguments' digest, the account and an hour, as decision 0235's are. The retry
   with that state does not run the tool again: it calls `answered` with the client's answer and the
   sealed references. Only `stage_reviews` names `after`.
2. **The form** (`api/mcp_staged_confirm.py`). Once a batch is stored, `stage_reviews` asks one form
   (`confirm`): a message naming the client, saying nothing changes until a person confirms, that
   every confirmed item runs the Review page's checks again and that what is left waits on the Review
   page for three days, then one numbered line per item; `choice` (`all`, `some`, `none`, required,
   no default) and one tick per item (`item_1` …, titled with its number and label, unticked by
   default). Each line is the item in plain words (`research/staged_review_words.decision_words`):
   the action and label, what readers then see (published, not published and the giver reads why,
   raised, taken off every page, the record keeping a removed or edited item), a re-filing, a source's
   corrected fields, an edit's fields before and after, and the reason given. A page decision adds
   the chapters (by title) and components of the parts in its scope and the link
   `{site}/admin/review?proposal={id}` (`page_proposal_reviews.page_touches`); the Review page opens
   and scrolls to the proposal a link names (`lib/pageProposalView.proposalFromSearch`,
   `PageProposalCard`'s `focused`). The link sits in the message as text, as decision 0235's preview
   link does, and opens only for an Admin.
3. **Only the person whose AI staged it, with the review scope.** The form is asked, and its answer
   taken, only while the account holds the review scope and `REVIEW_CONTRIBUTIONS`, the batch is its
   own, still open, and staged through the same OAuth grant
   (`services/staged_review_summary.own_open_batch`); otherwise the call answers as before, or the
   answer is refused. A connection without the review scope never reaches the tool.
4. **Never answered by an AI.** An answer counts only from the client's `inputResponses` on the retry
   carrying the server's `asked_after` state for that call, account and batch, from a client that
   still declares form elicitation (else `-32602`). The tool's arguments forbid every field but
   `decisions`, so an answer, a `requestState` or a `confirm` put in them is refused before anything
   is staged; an answer sent without the server's state is ignored and the person is asked; no tool
   confirms a batch. A state presented by another account, with other arguments, or tampered is
   `-32602`; one from another client of the same account confirms nothing.
5. **The same rules.** `all` confirms every item and `some` the ticked ones:
   `staged_review_confirm.confirm_as_staged` hands each chosen item to `confirm_batch` exactly as it
   was staged (`StagedDecision.as_staged`), so the checks again, the savepoints, `SKIPPED`, `REFUSED`
   and `APPLIED`, `review.staged_applied` with the client and the decisions' own audits are the
   Review page's; then `staged_review_finish.finish_confirmed`, shared with the confirm route, refreshes
   the pages touched and embeds as the route does. The reply is the staging reply (carried in the
   sealed state, its refusals included) with `batch`, the batch as now confirmed, `published` true
   when an item applied, and a message counting what was confirmed, applied and refused. A partial
   confirmation applies only the ticked items and closes the batch, as Confirm selected does.
6. **Declined waits.** A decline, a cancel, `none`, `some` with nothing ticked, an unknown choice or no
   answer confirms nothing and discards nothing: the batch waits on the Review page and the reply says
   so. Discarding stays on the Review page. A client without form elicitation, and every client on the
   2025-11-25 handshake, is answered exactly as before.
7. **The owner's words over the design skill.** None here: the Review page change opens and scrolls
   to a card, through `scrollToAnchor`, which reads both reduced-motion switches.
8. No migration and no new dependency.

## Consequences

- Tested in `backend/tests/mcp/test_staged_review_elicit.py` (the form and its words, all and some
  confirmed once without staging again, every way of not confirming leaving the batch waiting, old
  clients and clients without forms answered as before, no review scope or rank and no form, an
  answer in the arguments refused, an answer without the state ignored, a state from another
  account, arguments, client or a tampered one confirming nothing, the guard on whose open batch it
  is), `backend/tests/review_queue/test_staged_review_words.py` (each kind of decision in words),
  `test_page_touches.py` (a scope's chapters and components), `backend/tests/db/test_staged_review_elicit_db.py`
  (a batch staged over MCP and confirmed in the form applied and audited, a declined one waiting and
  listed, a partial one applying only the ticked item, an old client and a connection without the
  review scope) and `frontend/e2e/review-pages-unit.spec.ts` (the link names one proposal, which opens
  on arrival).
- The staging reply rides in the sealed `requestState`, up to some 20 KB for twenty refused items.
- Left as they are: a proposal the Review page does not list (beyond its twenty, or the Admin's own)
  is not opened by its link; the server cannot tell a person from a client that fills forms by itself,
  so it relies on the protocol's rule that a client shows elicitation to its user, and on the answer
  being bound to the person's grant, account and call.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
