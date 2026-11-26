# 0236. A reviewer sees a proposed page as it stood and as it will be, drawn and marked chapter by chapter, and decides it whole, by chapter or by component, on the site or staged over MCP for a person to confirm

A page proposed whole is kept as one proposal: the page as it stood and as it will be, each part it
proposed with the chapter it lands in, the renderer's pictures of the preview that drew it, and the
decisions made on it. The Review page and the MCP review tools show it chapter by chapter, each
sentence, component and picture marked added, changed or removed, with both versions drawn at 390 and
1440 px. A reviewer approves or rejects the whole page, one chapter or one component with a note; each
part is decided by its own queue's decision, so every gate still runs, and the note reaches the
contributor's open work.

Date: 2026-11-26. Status: accepted (the lead's UX round of 2026-11-26, lane review-diff, with the
lead's addition of the same day that everything is usable over MCP too). It amends
[decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) (the preview's
pictures, returned to the agent and now also kept) and [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md)
(the decisions an Admin's AI stages, which now include a page proposal's). The contracts are
`docs/contracts/review-queue.md` (Page proposals) and `docs/contracts/open-work.md` (`my_work`'s
`reviews`).

| For | Read |
|---|---|
| The preview, its renderer and its pictures | [decision 0195](0195-a-preview-drawn-seen-and-checked-before-it-is-proposed.md) |
| Staged decisions a person confirms | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) and [decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) |
| The preview card this view follows | [decision 0229](0229-a-preview-card-that-minimises-and-what-a-craft-s-facts-could-show-offered-to-judge.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- The owner wants contributors to "at most review the changes". A whole page proposed over MCP or the
  site reached the queue as unrelated facts, structure items, components, a layout and pictures, each
  a card of data: no rendered page, no picture, no before and after. Reviewing a page meant reading
  specs, and nothing tied the parts back to the page they make.
- `preview_page` already drew the page at 390 and 1440 px on the box's renderer (decision 0195), but
  only returned the pictures to the agent; nothing kept them, so the reviewer never saw them.
- The lead added on the same day that the review must be usable over MCP as well: the review tools
  return the same before and after, an MCP App view draws it, an Admin's AI may propose a decision, and
  a person confirms every one.

## Decision

1. **One record of a page proposed whole.** `propose_page` with more than one part (over MCP or the
   site, `api/page_proposal_deps.page_proposed`) first draws the page as it will be with the preview's
   own assembly (`services/page_preview.previewed_document`, no preview row stored) and the page as it
   stands (`monograph_generated.generated_document_of`), then, once the parts are written, keeps a
   `PageProposal` (migration `0122_review_diff`): the proposer, the subject, the origin, both documents,
   each accepted part with its queue kind, id, chapter, label and title
   (`research/page_proposal_parts.proposal_parts`: a fact's chapter is its field's, a component's the
   chapter the drawn page places it in, a given picture's its plate's, the layout the whole page's),
   the chapter by chapter changes and the decisions. A translation alone, a single part, or a page the
   preview cannot draw (authored, too thin) keeps no documents and, without parts, no record.
2. **Changes read from the two documents.** `research/page_changes.page_changes` compares them
   chapter by chapter: a cited sentence placed on the page by its unit, a component by its label and
   what it draws (its spec with every unit read as its text, its title and the sentences it holds, so
   renumbered units do not read as changes), a picture plate by its picture, caption and credit. Each
   is added, changed (with both texts, and the chapter it moved from) or removed; a chapter keeps its
   counts and at most 60 lines, components and pictures first. A sentence reworded under a new unit
   key reads as removed and added, which is what a reader would see.
3. **The preview's pictures kept, then moved.** `drawn_preview` keeps its pictures
   (`DrawnPicture`, JPEG bytes in Postgres, at most 1 MB a preview, one preview's set per account and
   page, deleted with the preview). When the page is proposed, the pictures of the account's latest
   live preview move to the proposal if that preview drew exactly the document proposed. Postgres over
   S3: the pictures are small, short-lived until proposed and pruned with their preview by a cascade;
   an S3 object would need its own clean-up and a naming rule for keys nobody reads.
4. **Drawn on request.** A proposal without pictures opens all the same, and its Draw it action
   (`POST /api/review-queue/pages/{id}/draw`, one side a call) stores that side's document as the
   reviewer's own short-lived preview and has the renderer draw it, keeping the pictures on the
   proposal. A preview owned by an account that reviews contributions may show a waiting picture
   another account gave (`page_preview_pictures.shown_picture_file`), for the renderer's pass and the
   reviewer's browser, since such an account already sees waiting pictures in the queue.
5. **Decided whole, by chapter or by component.** `POST /api/review-queue/pages/{id}/decide`
   `{action, scope PAGE | CHAPTER | COMPONENT, chapter?, label?, note?}` decides every part in the
   scope that still waits, facts first and the layout last, each through `review_queue_decisions`'
   approve or reject in its own savepoint: a part its own checks refuse (a stale layout, a moved page)
   stays waiting with the reason, a part already decided is skipped, and nothing else is touched. A
   rejection names its reason, at least three characters, as every rejection in the queue does; an
   approval's note is optional. The decision, its note and each part's outcome are kept on the
   proposal and audited (`review.page_approved`, `review.page_rejected`); the proposal closes once
   nothing in it waits. Page proposals are for Admins and Master Admins (`REVIEW_CONTRIBUTIONS`), who
   review every kind a page holds; a reviewer never decides their own.
6. **The note reaches open work.** `my_work` (and `GET /api/knowledge/open-work/mine`) gains
   `reviews`: the latest ten decisions on the account's page proposals of the last 30 days, each with
   its scope, note and each part's outcome, so the contributor's AI can act on it. Each part's own
   reason is kept on the part as before.
7. **On the Review page.** Above the queue, for Admins, each page proposal is a card
   (`components/review/PageProposals.tsx`, `PageProposalCard.tsx`): the page, the proposer, how many
   parts wait and each changed chapter's counts; Show the page as it stands and as it will be opens the
   first screens side by side (`PageShots.tsx`, `DrawnPair.tsx`; pictures load lazily at their drawn
   size), then each chapter (`ChapterChangeList.tsx`) with its pictures, its lines marked Added,
   Changed or Removed in words (`PageChangeLines.tsx`), its changed components drawn from the two
   documents on request (`ChangedComponents.tsx`: `ComponentSlot`, and a coded figure's live run
   through `CodedFigureReview`), and a decision bar for the chapter, each component and the whole page
   (`ScopeDecision.tsx`, reusing `QueueDecisionBar`). The list carries only each chapter's counts; a
   proposal's lines, and its documents, load when it is opened. The `img` elements carry an
   `eslint-disable-next-line @next/next/no-img-element` with its reason, as the picture review card does:
   a private JPEG the API serves at its drawn size, nothing for `next/image` to optimise.
8. **The same over MCP, a person confirming.** `review_queue` lists open page proposals in `pages` and,
   with `page` set to one's id, returns it whole as `page` with the stored pictures beside the result
   (first screens, then the changed chapters, before then after, within 1 MB). The tool draws with a
   new MCP App, `ui://kalavigyan/page-review.html` (`data/design/page-review-view.html`): it starts as
   one line, minimises back to it, minimises the others when opened, and draws each chapter's marked
   changes, each part's state and the decisions made, as text, loading nothing. `stage_reviews` takes
   a page decision as kind `PAGES` with `page {scope, chapter?, label?}`, checked by running it in a
   savepoint as every staged decision is, and stored for a person to confirm on the Review page
   (`StagedDecision.page`; migration `0122_review_diff` widens the staged item kinds). Several chapters
   of one page may be staged in one call. Confirming applies it through the same decision. The server
   never applies what an AI proposes.
9. **Elicitation left as a seam.** The MCP extensions lane's elicitation support is not on `main`, so
   a staged page decision is confirmed on the Review page only. When it lands, the seam is
   `staged_review_confirm.confirm_batch`: a form in the MCP client that confirms one staged batch item
   by item calls it as the Review page's route does, with the person as confirmer.
10. **The owner's words over the design skill.** None here: the view and the cards move nothing, and
    status marks carry words.

## Consequences

- Proposing a whole page assembles the page twice more (as it stands and as it will be); a page the
  preview refuses costs nothing more.
- A preview keeps up to 1 MB of pictures in Postgres until it expires or is replaced; a proposal keeps
  its two documents and up to 2 MB of pictures.
- A page proposal's parts still wait in their own kinds' tabs, and a decision on either side shows on
  the other: a part decided in its tab is skipped by a later page decision.
- The web, the API and the staged contract learn the kind `PAGES`; an older web leaves a staged page
  decision out (decision 0167).

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). The tests: `backend/tests/review_queue/test_page_changes.py` (a
change marked in each direction, a scope's parts), `test_page_proposal_parts.py` (each part's chapter),
`backend/tests/db/test_page_proposal_reviews_db.py` (the record with its pictures, a proposal without
pictures drawn on request, one chapter's approval alone, a rejection's note in `my_work`),
`backend/tests/mcp/test_page_review_view.py` (the view, the pictures beside the result, a staged page
decision), `backend/tests/test_review_diff_migration.py` and `frontend/e2e/review-pages-unit.spec.ts`
(both versions drawn and marked, Draw it without pictures, a chapter's parts, a staged page decision).
