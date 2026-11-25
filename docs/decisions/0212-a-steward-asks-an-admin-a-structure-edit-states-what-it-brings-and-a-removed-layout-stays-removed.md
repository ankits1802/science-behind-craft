# 0212. A steward asks an Admin to take another's component off its pages, a structure edit finds in its quotes every value it brings, and a layout's removal never brings back one a removal took off

Only a component's proposer or an Admin takes it off its pages, or replaces it, at once; a steward
of its craft asks, and its withdrawal becomes a staged removal an Admin confirms on the Review page,
its replacement a proposal that waits for review; a withdrawal names a component of the bundle's
own page. An edit of a structure entry or a GI record is refused, when it is staged and again when
it is confirmed, unless every name, colour and number it brings is in a quote of the facts the entry
rests on. Removing a layout restores the latest earlier arrangement that is neither the one removed
nor one a removal took off, or the default arrangement.

Date: 2026-11-25. Status: accepted (the owner's adversarial review of the quality round, findings
`mcp-admin-1`, `mcp-admin-4` and `mcp-admin-6`; the lead's lane brief `stewards`). It amends
[decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md)
(items 1 to 3: who may retire a component, withdrawing and replacing),
[decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) (a structure entry's
gates, a layout's removal) and
[decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) (a staged batch proposed by
an account that does not stage). The contracts are `docs/contracts/open-work.md` (Withdrawn,
replaced, borrowed and held) and `docs/contracts/review-queue.md` (Staged over MCP).

| For | Read |
|---|---|
| Withdrawing, replacing and the one path that takes a component off its pages | [decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md) |
| The edit of published content and the gates the original passed | [decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) |
| Staged review, the dry run and the one-press confirmation | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) |
| Stewardship, self-assigned and never blocking anyone | `docs/contracts/open-work.md`, Stewardship |
| Every decision, by group | [README.md](README.md) |

## Context

- **Stewardship is self-assigned, and it took components off pages.** Any account with
  `PROPOSE_KNOWLEDGE` adopts up to 10 crafts with `steward_craft`, asking no one, and
  `component_retirers.may_retire` let a live steward of a component's craft withdraw or replace it.
  A NEW-tier Researcher could adopt Sanganeri Hand Block Printing and send `propose_page` a one-part
  bundle of withdrawals naming another contributor's component (or a curated one): a single part
  is never held, so `withdraw_registered` hid it at once on every page that placed it, other crafts'
  pages included, and its label stayed retired. The test of who may covered a seeded steward and a
  stranger, never a stranger who adopts the craft first. A withdrawal's label was checked only
  against its pattern, never against the bundle's page.
- **A staged structure edit skipped the quote check.** A structure proposal must give every name,
  colour and number in one of its quotes (`structure_proposals_values.stated_check`), but
  `published_structure._edit` ran only the entry's item model and its target check, and wrote a GI
  record's fields with no check at all. An Admin's AI could stage a certificate number, a proprietor,
  a colour after or a native name that no source states, and one press published it.
- **A layout's removal restored version minus one.** Removing v2 writes v3 as a copy of v1; removing
  v3 then restored v2, the very layout an Admin had removed, with nothing in the batch saying so.

## Decision

1. **At once only by the proposer or an Admin.** `may_retire` is the component's own proposer (the
   proposal its `payload.proposalId` names) or an account with `REVIEW_CONTRIBUTIONS`; a steward is
   no longer one. `component_retirers.stewards_piece` names a live steward of the component's own
   craft, and `component_withdrawals.retirement_waits` is the one rule every path asks: at once for
   the proposer or an Admin, by review for a steward, refused (`not_yours`) for anyone else.
2. **A steward's withdrawal is a staged removal an Admin confirms.** In `propose_page` (a bundle of
   one part or several, a held page once its person confirms, a draft submitted) a steward's
   withdrawal of a component it did not propose, or of a curated one, stores a one-item
   `StagedReview` (`staged_reviews.stage_request`): `COMPONENTS remove` off every page, the steward
   as proposer, `clientName` `propose_page over MCP` or `the site's page proposal`, expiring in 3
   days. Its part answers `ACCEPTED` with status `STAGED`, no id and a message saying the component
   stays on until an Admin confirms; the pages are not refreshed. It needs a reason of 12 to 500
   characters, as every staged decision does, and the same request already waiting is refused.
   Nothing is dry-run at staging, because the steward may not remove it; the Admin's confirmation
   runs `take_off_pages` as the Admin, and may narrow it to one page. The staged batch was chosen
   over the alternatives because it already is a change to published content that an Admin sees
   with its reason and its proposer and confirms with one press, checked again at confirmation,
   audited and lapsing unconfirmed, with no new table or screen: the review queue holds new content
   and would need a new kind and a migration for a removal, and a page hold is confirmed by its own
   proposer, which is no review at all. `edit_draft` and `preview_page` take a steward's withdrawal
   with its reason (the preview says it will be asked for) and refuse a stranger's.
3. **A steward's replacement waits for review.** A proposal whose `replaces` names a component its
   proposer may not retire at once is stored `PENDING` even from a Professor, whose own proposals are
   otherwise approved at once; an Admin's approval then retires the old one as before. The
   proposer's and an Admin's replacements are unchanged.
4. **A withdrawal names a component of the bundle's own page.** For a craft's or a family's bundle
   the component must be one its page draws (`component_library_applies.applies_on`, the
   applies-to query the page reads); for a category's, the category must be among the pages its
   withdrawal refreshes (`piece_owners`). Otherwise it is refused, naming the page.
5. **A structure edit is checked against its entry's quotes.** `published_structure._edit` reads the
   quotes of the facts the entry rests on (a GI record's `claimIds`) and runs
   `structure_proposals_values.edited_check`: every name, colour and number the edited entry gives
   that the entry did not already give must be in one of them, by the same matching as
   `stated_check`. It runs after the item model and the target check, for GI records too, in the
   staging dry run and again at confirmation, and refuses in the check's own words (`Not edited:
   the STATED check refused it. The certificate number (999) appears in none of the quotes.`). Only
   what the edit brings is checked, because a curated entry's values were published through the
   dossier's checks, not this one, and an edit of a language or a script must not be refused for a
   name it leaves as it was.
6. **A layout's removal restores an arrangement no removal took off.** `published_layouts._earlier`
   takes the latest earlier version whose entries are neither the removed version's nor those of
   any version a `layout.removed` audit names, or else the default arrangement; the result says
   which, and why. A copy of a removed layout written later by a restore is skipped by its entries,
   so a chain of removals never brings one back.

## Consequences

- No migration and no new tool. The web reads the new part status `STAGED` as text, and a
  steward's batch on the Review page shows `Proposed through propose_page over MCP by <name>`.
- `component_lifecycle.check_replacement` has no caller now and `component_lifecycle._applies` is
  the same query as `applies_on`; both are in a file the `removed` lane changes this round, so the
  lead removes the one and points the other at `applies_on` at merge. Its `not_yours` sentence
  ("the proposer, a steward of its craft or an Admin may take it off its pages or replace it") stays
  true for a stranger, since a steward may still ask.
- A layout that matches an arrangement once removed is skipped even when it was proposed again and
  approved later; the page then goes further back, which never shows a removed layout.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/db/test_steward_withdrawals_db.py` (a stranger who adopts the craft refused at once
and its request staged, asked once, needing a reason, confirmed only by an Admin; an Admin still at
once and only from a page that places it; a draft holding a steward's withdrawal and refusing a
stranger's; a Professor steward's replacement waiting and an Admin's approved at once),
`backend/tests/db/test_component_lifecycle_db.py` (the proposer and an Admin at once, a steward
not), `backend/tests/db/test_published_structure_db.py` (a GI record's unquoted edit refused when
staged and when confirmed, a native name's quoted edit confirmed, an unquoted one refused, a
language edit passing), `backend/tests/structure/test_structure_proposal_rules.py` (only what an
edit brings is checked) and `backend/tests/db/test_published_content_db.py` (removing a restore goes
to the default arrangement, and a chain of removals restores only what no removal took off).
