# 0219. A removal clears the kept versions only of the pages it changes and waits its turn, a page's file leaves the bucket within two days, and every page reads a version a rebuild replaced in its own language, one an hour kept for a week

A removal drops the kept versions only of the pages with a copy that draws what it took, after the
removals' lock, so two removals never deadlock; page exports expire within two days; the category
and family routes read `version`, a kept version is read in a page's language from its English as
the current copy is, and a page keeps at most 168 versions per language.

Date: 2026-11-25. Status: accepted (the lead's leftovers round of 2026-11-25, lane `versions`:
what decisions 0213, 0210 and 0212 left). It amends
[decision 0213](0213-what-is-removed-leaves-every-kept-version-and-a-one-page-removal-reaches-the-stored-page.md)
(item 1, the pages a removal clears, and its Consequences: two crossing removals, the export files
left), [decision 0210](0210-a-page-drawn-a-version-behind-reads-its-rest-and-a-where-icon-drawn-at-its-own-size.md)
(item 2, a kept version served in English alone, and its Consequences: nothing pruned, a category
reading no version) and [decision 0212](0212-a-steward-asks-an-admin-a-structure-edit-states-what-it-brings-and-a-removed-layout-stays-removed.md)
(its Consequences: the lifecycle tidy-ups and the `not_yours` sentence). The contracts are
`docs/contracts/monograph-document.md` (the stored copy, `version`), `docs/contracts/page-layout.md`
(the category and family routes), `docs/contracts/review-queue.md`, `docs/contracts/open-work.md`
(taken off one page) and `docs/contracts/infra.md` (Stored pages, Media); the RUNBOOK's page export
paragraph names the lifecycle rule.

| For | Read |
|---|---|
| What a removal drops, the page locks and the export files it left | [decision 0213](0213-what-is-removed-leaves-every-kept-version-and-a-one-page-removal-reaches-the-stored-page.md) |
| The kept versions and the rest of a page drawn a version behind | [decision 0210](0210-a-page-drawn-a-version-behind-reads-its-rest-and-a-where-icon-drawn-at-its-own-size.md) |
| Who takes a component off its pages, and the lane's tidy-ups | [decision 0212](0212-a-steward-asks-an-admin-a-structure-edit-states-what-it-brings-and-a-removed-layout-stays-removed.md) |
| The page export key, filed once by what it is made from | [decision 0214](0214-a-page-export-filed-once-built-in-its-own-slots-at-a-caller-s-pace-and-its-rebuild-queued.md) |
| Pages in other languages, drawn from the stored English on each read | [decision 0117](0117-pages-in-other-languages.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Two removals could deadlock.** `drop_kept_versions` took its pages' locks in one sorted order,
  but a staged batch carries out its items in their order and drops after each, holding every lock
  to the end of its transaction: a batch removing a fact of craft A and then one of craft B, and
  another removing B's and then A's, each held one page and waited for the other's, and Postgres
  refused one.
- **A removal cleared pages it did not change.** It cleared every page its refresh names, a craft's
  sub-category's families and its category included, so retracting one craft's fact, withdrawing a
  component a family never placed or taking a component off one craft's page cost those pages their
  archive, and a family or category page a cache held at its current version then read no rest once
  it was next rebuilt.
- **A dropped version's export stayed in the bucket.** Page exports are filed once under
  `exports/00000000-0000-0000-0000-000000000001/<sha256 of what it is made from>/` and kept by the
  `expire-exports` rule for 7 days; the bucket is versioned, so an expired file stayed a noncurrent
  version for the bucket's 90 days.
- **Versions were read in one place only.** The category and family routes took no `version`, so a
  category page drawn a version behind read no rest; a kept version was served in English alone, so
  the rest of a translated page drawn a version behind was not found; and kept versions were never
  pruned (`docs/TECH_DEBT.md`, the rollback entry's part from decision 0210).
- **The stewards lane left three tidy-ups**: `component_lifecycle.check_replacement` without a
  caller, `component_lifecycle._applies` the same query as `component_library_applies.applies_on`,
  and a `not_yours` sentence that still named a steward among those who may take a component off.

## Decision

1. **Removals wait in turn.** `drop_kept_versions` takes the removals' transaction lock
   (`stored-document:removals`, `stored_document_versions.REMOVAL_LOCK`) before its pages' locks in
   their sorted order. A transaction that drops more than once holds it from its first drop, so a
   second removal waits for the whole first one before it holds any page, while a rebuild, which
   holds one page and waits for none, still waits only for its own page. This was chosen over
   sorting a batch's pages before its first item, which needs every item's pages before any is
   carried out, and over moving every drop to the end of its transaction, which the six callers
   own in different places; a lock taken at the one place that takes several pages holds for any
   caller. Removals across the site now queue behind one another; they are an Admin's or a
   contributor's single confirmation, seconds long.
2. **A removal clears the pages it changes.** `drop_kept_versions(owners, marks=)` clears, among
   the pages it names, only those with a copy, current or kept, that holds one of its marks as a
   JSON string: a fact's id (a fact retracted or rejected, `review_queue_facts.decide_fact`, and a
   fact's edit) and a component's label (a withdrawal, an Admin's removal or edit of a component, a
   piece hidden). A removal from one page names only that page (`Carried.changed`). A change that
   gives no mark (a layout, a structure entry, a reading, a layer, a stage, a source, a picture)
   clears every page it names, as before: nothing in a stored copy names those by a string the
   server can find, and a guard fails closed. Searching every copy, kept ones too, was chosen over
   comparing each page's stamp with its copy's: the stamp counts every component and picture
   record of the site (a page may borrow any), so it moves on every page at once, and it cannot
   tell that an older version drew what the page no longer draws.
3. **A page's file leaves the bucket within two days.** The `expire-page-exports` lifecycle rule
   (`infra/terraform/s3.tf`) expires page exports a day after they are filed, and `expire-exports`
   now removes an expired export's noncurrent version a day later; answer, lesson and shared files
   keep their 7 days. The rule was chosen over deleting a dropped version's files with it: the key
   is the digest of what the file is made from (its served tag, language and pictures), so a
   removal could not name it without rebuilding that record for every format and language. A page's
   file is then built again at most once a day, on its first download.
4. **Every page reads a version, in its language.** `document_reads.generated_at` serves a
   generated page at the current version or at one a rebuild kept, for the craft, family and
   category routes alike (`version` on `/api/categories/{slug}/monograph` and
   `/api/families/{slug}/monograph`, 404 `That category's monograph has no such version.`). A kept
   version asked in another language is drawn from its stored English by the page's served
   translations, as the current copy is (`page_translation_serving.translated_page`), under the tag
   `v<N>-<hash>-<language>-<16 hex>`, never writing the page's text index, which follows the
   current copy. The web's category rest route and the craft's read through one rule
   (`lib/monographRestRead.addressedDocument`): the current document when the address names it,
   else the version it names, in the address's language or not at all. Drawing the kept English on
   each read was chosen over storing each language's copy when it is replaced: translations are
   kept by their English passage's hash and stay served after the page moves on, so the variant is
   the one the page was drawn with, a translation later rejected leaves every version with it, and
   nothing more is stored or built at a rebuild.
5. **One version an hour, for a week.** `keep_superseded` keeps at most `KEPT_VERSIONS_MAX` versions
   per page and language, the newest, deleting the oldest as it keeps another. A cached page names
   its version until it is built again, at the latest after the pages' revalidate time of 7 days
   (`STATIC_PAGE_REVALIDATE_SECONDS`, held equal to `PAGE_REVALIDATE` by a test), and the page that
   changes most, Sanganeri Hand Block Printing, reached version 93 in its stored copy's first four
   days (2026-11-21 to 25), under one an hour; 7 days at one an hour is 168. A page that changes
   less keeps its versions longer, so its editions stay citable.
6. **The tidy-ups.** `check_replacement` is deleted, the one-page removal asks
   `component_library_applies.applies_on`, and `not_yours` reads "Only the proposer of {label} or an
   Admin may take it off its pages or replace it at once; a steward of its craft may ask."

## Consequences

- **What is left.** A removal of a layout, a structure entry, a reading, a layer, a stage, a source
  or a picture still clears every page it names, the families and category of its craft included:
  narrowing them needs each to give a mark its copies hold (a picture's address, a source's id in
  the cited sources, a reading's id in its stage). A family or category that borrows a component
  withdrawn everywhere is cleared with it, as it should be. The rollback entry in
  `docs/TECH_DEBT.md` now says that a kept version read in another language is validated by the
  same closed models. No entry is added.
- No migration. Every removal takes one more lock; a removal waits for another in progress anywhere.
- Kept versions over the cap are deleted at the next change of their page and language, so the
  busiest pages lose their oldest versions after this release.
- `tests/public/test_craft_monograph_versions.py` asserted that a kept version asked in Hindi was
  served in English; it now asserts the Hindi variant and that the page's index is not written,
  as item 4 decides. `tests/db/test_removed_versions_db.py` hid a craft's player that no copy of
  the page draws (it has no spec) and expected the page cleared; it now hides one the page draws
  for that, and asserts that the player it does not draw leaves the versions, as item 2 decides.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md), the
[contracts](../contracts/README.md) and the [RUNBOOK](../RUNBOOK.md). Its rules are tested by
`backend/tests/db/test_removed_versions_db.py` (a hidden piece the page draws clearing it and one
it does not draw leaving it), `backend/tests/db/test_kept_versions_db.py` (a retracted fact and a withdrawn component clearing the
pages whose copies draw them and leaving a page that never did and a label it only begins, a
one-page removal clearing only its page, a mark no copy holds clearing nothing and no mark every
page, the cap keeping the newest per page and language, two removals crossing the same pages
waiting in turn with neither holding a page the other waits for),
`backend/tests/contracts/test_kept_copies_contract.py` (the cap from the web's revalidate time, the
page export rule and the other exports' week), `backend/tests/db/test_translated_documents_db.py` (a
kept version read in Hindi and English, the index left on the current copy, an unknown version
none), `backend/tests/public/test_craft_monograph_versions.py` and
`backend/tests/layouts/test_page_document_routes.py` (the craft, family and category routes at a
kept version, in English and Hindi, and a version never kept not found),
`backend/tests/db/test_component_lifecycle_db.py` (the `not_yours` sentence, and a one-page removal
of a component its page does not draw refused) and `frontend/e2e/monograph-reads-unit.spec.ts` (a
rest read from the document its address names, from the version it names when the page moved on,
in its language, and not found when that version is gone or untranslated).
