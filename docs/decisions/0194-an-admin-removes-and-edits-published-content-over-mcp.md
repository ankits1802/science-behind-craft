# 0194. An Admin's AI stages the removal or edit of any published content, each checked by the gates the original passed and applied only when a person confirms the batch

An Admin's or Master Admin's AI client with the review scope can now remove published pictures,
layouts, structure entries, readings, map layers, stages and sources, and edit published facts,
components, pictures and structure entries, besides the component removal of decision 0193. It
finds what is published with `review_queue`, stages each change with `stage_reviews`, and a person
sees every edited field's before and after on the Review page and confirms the batch with one
press. Nothing a reader sees changes until then.

Date: 2026-11-24. Status: accepted (the owner: "can an admin remove the content through mcp as
well?" then "removal and edition both", after judging the Sanganeri Hand Block Printing page built
over MCP far below Kutch Ajrakh; the lead's lane brief `admin-curation`). It amends
[decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) (what an Admin's AI stages,
item 6: published pictures over MCP) and
[decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md)
(item 4: the staged action on published content). The contracts are
`docs/contracts/review-queue.md` (Staged over MCP, Published content),
`docs/contracts/image-contributions.md` (Removed or edited by an Admin), `docs/contracts/knowledge-api.md`
(the admin row) and `docs/contracts/mcp-oauth.md` (the review scope).

| For | Read |
|---|---|
| Staged review, the dry run and the one-press confirmation | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) |
| The staged action on published content, a component's removal first | [decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md) |
| Long guidance in a served resource rather than the list | [decision 0191](0191-room-for-the-page-quality-tools.md) |
| A sentence says no more than the quotes it cites | [decision 0120](0120-grounded-sentences.md) |
| How the web reads a field or kind it does not know | [decision 0151](0151-a-release-the-live-side-can-read.md) and [decision 0167](0167-answer-leftovers-kept-true.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- Decision 0170 let an Admin's AI stage queue decisions, source corrections and a cleared differ
  mark, and decision 0193 added one action on published content, a component's removal, with the
  registry a later kind joins (`PUBLISHED_ACTIONS`, `PUBLISHED_KINDS`). Nothing else published could
  be removed except a fact by retracting it, and nothing could be edited except a source's record.
- An AI client could not find most published items to name them: `get_facts` gives facts and their
  sources, `list_components` components, and nothing gave a picture's, reading's, placed stage's,
  layout's, map layer's or structure entry's id.
- Each kind already had its own way to leave the page with its record kept: a component's hide or
  unlink, a picture file's visibility, a reading's or layer's review status, a stage review, a layout's
  versions and the owner page a structure entry lives in.

## Decision

1. **Every kind an Admin reviews has its published actions.** `remove` for pictures (`IMAGES`, a
   staged kind on published pictures only: pictures waiting for review stay on the site), layouts,
   structure entries, readings, map layers, stages and sources; `edit` (a new staged action, the
   `StagedReviewItem` action and kind checks widened by migration `0104_admin_curation`) for facts,
   components, pictures and structure entries. Facts keep `retract` as their removal. One module a
   kind (`services/published_<kind>.py`) gives its name, its listing, its editable fields and one
   function per action, on the shared types of `services/published_kinds.py`.
2. **A removal keeps the record and names who and why.** Each uses its kind's own mechanism: a
   picture's file becomes `PRIVATE`; a layout's next version restores the one before it (or the
   default arrangement), every version kept, and only the current one may be removed; a structure
   entry leaves its owner page with its derived rows (a reaction's `Reaction`, a glossary term's
   `TermCraft`, a conflict's marks, a craft's GI record); a reading is `REJECTED`; an approved map
   layer is `REJECTED`, no longer fit to ship; a placed stage leaves its process, the later stages
   moving up one, its `StageReview` `REJECTED`; a source is unlinked from every fact citing it. Each
   writes its own audit (`picture.removed`, `layout.removed`, `structure.removed`, `reading.removed`,
   `layer.removed`, `stage.removed`, `source.removed`) with the confirming person, the reason and what
   it took away, and returns the pages it touched, which the confirmation refreshes.
3. **A removal is refused while other content depends on it**, naming it: a source that is the only
   source of a fact (retract the fact or give it another source first), whose quotes readings are read
   from, or that is a component's last source; a stage that still holds conditions, reactions or
   pictures.
4. **An edit carries only what changes, and the server keeps what it replaced.** `edit {fields,
   before}`: the fields in their canonical names, and `before`, read by the server at staging and
   never taken from a client, so the batch shows each field's before and after (`StagedItemView.changes`).
   It is checked by the gates the original passed, in the dry run at staging and again at
   confirmation, and refused in the gate's own words: a fact's text by the quote matcher (every
   figure in one of its quotes, at least half of its words in its quotes, each quote still in its
   stored passage; a fact with no quote is retracted and proposed anew); a component's spec and units
   by the delivery checks (`checked_drawing`), citing only the facts it already rests on, so every page
   placing it still holds them; a picture's caption, alt text, focal box (a new nullable
   `ImageContribution.focal`, drawn as the plate's focal unless a layout crops it) and place (a stage
   or material of its craft, or a slot); a structure entry through its own item model and
   `target_problem`. An edit that changes nothing, names a field its kind does not edit, or finds at
   confirmation that a field it changes moved since it was staged, is refused. A stage's why is the
   fact it rests on, so that fact is edited; a reaction is removed and proposed anew, since its
   equation is balanced when proposed; a renamed glossary term likewise.
5. **One press per batch, as before.** Staging never changes what readers see; a person may change a
   staged change's reason (and a component removal's page) but never an edit's values or its action.
   The day's allowance and the three-day expiry of decision 0170 apply.
6. **Found by `review_queue`, taught by a served guide.** `review_queue {published: {kind, subject |
   id, entry?, cursor?}}` lists a page's published items of one kind, 25 at a time, or opens one with
   the fields an edit changes. A structure entry is named by the fact it rests on, with `entry` when
   that fact holds up more than one. The two tools' descriptions point to the served resource
   `kalavigyan://admin/published-content.md` rather than growing, and no tool is added.

## Consequences

- Migration `0104_admin_curation` (parent `0111_answer_figures`) widens the staged action check
  with `edit` and the kind check with `IMAGES`, and adds the nullable `ImageContribution.focal` with
  its object check; the release before reads and writes every table, and its downgrade drops the
  staged items it cannot read.
- The web reads `edit`, `entry` and `changes` as optional, so a release before it parses every batch.
- A removed map layer an engineer already shipped from `tools/maplayers` stays on the maps until the
  engineer takes it out; a picture a curated dossier holds changes with that dossier's import, and a
  removed source's stored passages stay where research reads them.
- The contributor and craft-pages skills are the lead's to merge; the guide is served beside them.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-24; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/research/test_published_content_rules.py`,
`backend/tests/research/test_published_structure_entries.py`,
`backend/tests/db/test_published_content_db.py`, `backend/tests/db/test_published_components_db.py`,
`backend/tests/db/test_published_process_db.py`, `backend/tests/db/test_published_structure_db.py`,
`backend/tests/mcp/test_review_tools.py` and `frontend/e2e/staged-reviews-unit.spec.ts`.
