# 0213. What an Admin removes or edits, a contributor withdraws or a reviewer retracts leaves every kept version of its pages, a one-page removal reaches the stored page, and a page is rebuilt by one rebuild at a time

A change that takes something off a generated page drops that page's kept versions in its own
transaction, and the copy it reached is never kept; the stored page's stamp now names a
component taken off one page and a reading's review, so the page is rebuilt without them; and the
rebuilds of one page wait for one another, so a version number names one document.

Date: 2026-11-25. Status: accepted (lane `removed` of the review fixes of 2026-11-25, findings
`mcp-admin-2`, `documents-exports-1`, `web-2`, `mcp-admin-3`, `documents-exports-2` and
`documents-exports-5`). It amends [decision 0210](0210-a-page-drawn-a-version-behind-reads-its-rest-and-a-where-icon-drawn-at-its-own-size.md)
(every replaced version kept), [decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md)
(what a confirmed removal or edit leaves behind) and [decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md)
(a withdrawal, and a removal from one page). The contracts are `docs/contracts/monograph-document.md`
(the stored copy and `version`), `docs/contracts/craft-page.md` (Caching, the stamp),
`docs/contracts/open-work.md` (taken off one page), `docs/contracts/image-contributions.md`
(removed by an Admin), `docs/contracts/review-queue.md` (decisions and staged over MCP) and
`docs/contracts/infra.md` (Stored pages).

| For | Read |
|---|---|
| The kept versions and the routes that serve them, which this amends | [decision 0210](0210-a-page-drawn-a-version-behind-reads-its-rest-and-a-where-icon-drawn-at-its-own-size.md) |
| An Admin's staged removals and edits | [decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) |
| A contributor's withdrawal and a removal from one page | [decision 0193](0193-components-withdrawn-replaced-or-borrowed-and-pages-held-for-one-confirmation.md) |
| A document built while its inputs move, and the stamp's alarm | [decision 0190](0190-a-voice-turn-bound-and-answered-and-a-page-built-while-its-inputs-move.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Removed content stayed public at every kept version.** Decision 0210 keeps the copy every
  changed rebuild replaces (`StoredDocumentVersion`) and serves it at `?version=N`, at the edition
  `/crafts/<slug>/v<N>`, at the rest `/crafts/<slug>/shell/v<N>-<digest>` and in the craft's
  exports. Nothing dropped those rows except a page losing all its sections, so a picture, a
  component, a structure entry or a source an Admin removed (decision 0194), a fact's old text an
  Admin edited, a fact retracted and a component its contributor withdrew (decision 0193) stayed
  readable without limit. On production, Sanganeri Hand Block Printing was at version 93 and
  `GET /api/crafts/Sanganeri-Hand-Block-Printing/monograph?version=92&part=0` answered 200 with unit
  `fact-policy-0333a8db6103`, a release-check sentence withdrawn within minutes.
- **A removal from one page never reached the stored page.** Taking a component off one page
  writes a `KnowledgePieceUnlink` row and leaves the piece untouched, and a reading's removal or
  rejection changes only `ConditionReading.reviewStatus`; neither stamp read either, so the
  confirmation's refresh found the page current and the stored copy kept drawing what the batch
  reported removed, until an unrelated input moved.
- **Two rebuilds of one page could write one version twice.** `_store` read the stored row
  without a lock and wrote `version + 1`; the refresh job's and the nightly sweep's rebuilds took no
  lock, so two of one page at once could both write the same next version, the second over the
  first, which was then never kept.

## Decision

1. **Removal wins over the archive.** In the transaction of the change itself,
   `stored_document_versions.drop_kept_versions(session, owners, now=)` deletes every kept version,
   in every language, of each page the change names (its owners, the pages its refresh then sends
   to the site: the craft, its sub-category's families and its category, or the category alone),
   and marks each page's current copy `removedAt`. The changes that call it are those that take
   something a page shows off it:
   - an Admin's confirmed staged removal or edit of any published kind (`staged_published.carry_out`,
     decision 0194: facts, components, layouts, structure, readings, layers, stages, sources and
     pictures); the staging dry run calls it inside its savepoint and rolls it back with the rest;
   - a fact that leaves the page (`review_queue_facts.decide_fact`): a shown fact (`APPROVED` or
     `IN_REVIEW`, `research.retrieval.SHOWN_CLAIM_STATUSES`) retracted or rejected, from the Review
     page, a staged batch or MCP; rejecting a waiting fact the page never showed drops nothing;
   - a reading rejected in the queue (`review_queue_readings.decide_reading`), which leaves the page;
   - a contributor's withdrawal of a registered component (`component_lifecycle.withdraw_registered`,
     decision 0193, from the own-proposals route or a page bundle's withdrawals);
   - an Admin hiding a craft's own piece (`craft_page_hiding.set_page_piece_hidden`); showing it
     again drops nothing.
2. **The copy a removal reached is never kept.** `_store` keeps the copy it replaces only when
   that copy has no `removedAt` (migration `0118_removed`). The copy it writes next carries none,
   and a rebuild that finds the page unchanged clears the mark, since that copy held nothing the
   change removed. From the copy after the removal on, versions are kept again as decision 0210 says.
3. **One rebuild of a page at a time.** `stored_document_versions.lock_page` takes a transaction
   lock on the page (`stored-document:<craft|category>:<slug>`, a craft and its family form sharing
   the craft space): at the start of `rebuild_document`, before the stamp and the stored version are
   read; in `stored_copy` before a first copy is built; and in `drop_kept_versions` for each page, in
   a fixed order. A second rebuild of the page waits for the first to commit and then reads its
   version, a removal waits for a rebuild in progress, and the rebuild after a removal reads what
   the removal left. Other pages never wait. Serialising here was chosen over refusing a mismatched
   `?version=N` tag in the API: with one writer at a time, a version names one document.
4. **The stamps name what a removal from one page and a reading's review change.** The craft
   page's stamp (`craft_page_stamp`, which the document's stamp includes) counts the craft's
   `KnowledgePieceUnlink` rows (`unlinks`) and its live stages' and their reactions' conditions and
   readings, with the readings still shown and their latest review (`conditions`, `readings`,
   `readingsShown`, `readingsReviewedAt`); a category's document terms count its own unlinks. This
   was chosen over having a confirmed batch force-rebuild its pages: every path that writes these
   rows (a staged batch, the review queue's reading decisions, whose approval had the same gap before
   this round, and any later tool) then restales the page, a read notices it as well as the refresh,
   and decision 0190's alarm for a document changed under an unchanged stamp stays true.
5. **What an edition cited before a removal shows.** A dropped version answers as a version that
   was never kept: the API 404 `This craft's monograph has no such version.`, and so do the craft
   export routes, which read through the same `served_document` (`page_exports.py` needs no change).
   The web's edition `/crafts/<slug>/v<N>` shows its not-found page and the rest
   `/crafts/<slug>/shell/v<N>-<digest>` answers 404, once the removal's refresh has expired the
   page's document tag (`monograph-document:craft:<slug>`), which both routes read under; the
   refresh runs at once after the change. The page to cite is the current one, at `/crafts/<slug>`
   or its new edition.

## Consequences

- **A removal costs its pages their archive.** Every kept version of each page the change names,
  and the copy current when it was made, are gone, even on a page the change did not alter (the
  owners are the pages the refresh names). Pages only added to or rewritten by a rebuild keep
  decision 0210's archive: approvals, a contributor's replacement (`retire_replaced`), layouts
  written, sections republished and a release's code.
- **Every page is rebuilt once after this release**, as any change to the page code does; with no
  mark, the version each replaces is kept.
- **A confirmation can wait for a rebuild** of one of its pages in progress, and a staged dry run
  likewise; a rebuild of a page waits for another of the same page. Two removals naming the same
  pages in opposite orders across their items can deadlock, and Postgres then refuses one, which
  the Admin confirms again.
- **What is left.** An export file built from a version now dropped and filed in the private
  export bucket before the removal stays there under its key until the export store's own
  clean-up (lane `exports`), and a link to it already handed out lives out its short expiry; the
  route no longer hands it out. Hiding an AI-made picture (`set_page_media_hidden`) and a removed
  contributed picture make the file `PRIVATE`, so an old version names only an address that answers
  404, and they drop nothing. Testimony and field voices are not inputs of a generated document, so
  their withdrawals drop nothing. A rebuild in the nightly sweep still reuses its session's loaded
  rows across pages, as before.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md), the
[contracts](../contracts/README.md) and the [RUNBOOK](../RUNBOOK.md). Its rules are tested by
`backend/tests/db/test_removed_versions_db.py` (a confirmed one-page removal leaving no version
that draws it, its stored copy stale and its rebuild without it; a one-page unlink moving only its
page's stamp; a removal dropping only the versions of the pages it names and holding their locks;
the copy a removal reached not kept and the change after it kept; an unchanged rebuild clearing the
mark; a retracted fact dropping the versions and a waiting fact rejected leaving them; a proposer's
withdrawal dropping them and a stranger's refusal leaving them; a piece hidden from its craft
dropping them and another craft's leaving them), `backend/tests/db/test_published_process_db.py`
(a removed reading moving its craft's stamps while staging alone does not; a reading rejected in
the queue dropping its craft's versions and one approved leaving them) and
`backend/tests/db/test_stored_documents_db.py` (a rebuild holding its page from before it reads the
version, so another connection cannot take that page while other pages stay free).
