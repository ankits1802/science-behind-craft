# 0251. The release check's test fact goes where no fact is held, a section proposal is followed with get_proposal, and dossiers carry the sections a person wrote

The post-deploy check's test fact no longer goes to Sanganeri's POLICY field: the check reads the
coverage of the site's pages when it runs and proposes to the first craft page, in slug order, that
is not authored and holds no fact in some field, at its first such field. `get_proposal` follows a
section proposal by the id `propose_page` reported. The dossiers carry each section a person wrote
and a reviewer approved, and the import restores one only where the database holds none.

Date: 2026-11-28. Status: accepted (the lead's lane brief `ux-1126/section-leftovers`, after the
release of `6c727f45` failed its post-deploy check on a sound release). It amends
[decision 0250](0250-a-contributor-s-ai-proposes-a-field-s-section-from-the-facts-its-page-holds.md)
(What is left: `get_proposal` reads fact proposals only; dossiers do not carry sections). No
migration. The contracts are `docs/contracts/knowledge-writes.md` (the MCP tools, Section
proposals), `docs/contracts/open-work.md` (the tool table), `docs/contracts/dossier-export.md` (What
it reads, Reviewed sections) and `docs/contracts/curation.md` (Reviewed sections, the import), with
the contributor skill (Proposals and their progress, Writing a section) and `docs/RUNBOOK.md`.

| For | Read |
|---|---|
| The section proposals it completes | [decision 0250](0250-a-contributor-s-ai-proposes-a-field-s-section-from-the-facts-its-page-holds.md) |
| The release check it changes | [decision 0149](0149-a-fact-readers-can-see.md), [decision 0158](0158-a-curated-page-lists-the-facts-contributors-add.md) |
| The gates that settle novelty by distance | [knowledge-writes.md](../contracts/knowledge-writes.md), Cost at the centre |
| The export and import it extends | [decision 0171](0171-imports-keep-approvals-and-differences-settle.md), [dossier-export.md](../contracts/dossier-export.md) |

## Context

1. **Why the check broke.** The Post-deploy run of `6c727f45` (46093996440) failed in "A Professor's
   MCP fact reaches a signed-out reader, then is retracted": the NOVELTY gate refused the test fact
   ("KalaVigyan release check, withdrawn within minutes: the cited page states the words quoted from
   it.") as too general, the judge naming "the held Wikipedia GI fact". The same job passed on
   `26cf8aaf` the day before. The lead's reading was checked in the code and holds:
   - `frontend/e2e/release/mcpContribution.ts` proposed the statement on
     `Sanganeri-Hand-Block-Printing` in `POLICY`, with a quote from one of the craft's closed sources.
   - The contribution worker runs the gates with `GateThrift()` (`scripts/contribution_worker.py`).
     `services/candidate_gates._novelty` settles a candidate by distance, with no judge, when it has
     held facts near it in its field and all are below `NOVELTY_JUDGE_SIMILARITY` (0.75,
     `research/gate_thrift.novel_by_distance`); with none at all `novelty_outcome` passes it ("the
     subject holds no fact in POLICY yet"); otherwise the judge is asked, and it rightly finds a release
     note teaches nothing about the craft.
   - The held facts are the subject's (its own concepts, its family's shared concepts and their
     edges, `retrieval/statements.scope_claims`) in `DRAFT`, `PROPOSED`, `IN_REVIEW` or `APPROVED`,
     open, filed under the field (`services/candidate_store.SqlHeldFacts`); `nearest` and the
     DUPLICATE gate's `twins` share these conditions. The candidate is embedded with its title (the
     craft's name and field, `candidate_text`), as held facts are with theirs, so a fact of the same
     craft and field shares much of its text with any candidate.
   - On 2026-11-28 a page-build agent published 14 facts on Sanganeri over MCP, its GI record in
     POLICY among them; the live coverage now holds a fact in every one of Sanganeri's sixteen
     fields. A POLICY fact came within 0.75, so the judge was asked and the check failed. Crafts are now
     built one after another to the Kutch Ajrakh bar, so any fixed craft and field would fill the same
     way.
2. **What else the check depends on.** The page step reads the craft's stored document and looks
   for the fact in its units; a generated page lists a field's new fact under its section, or under a
   listed section when the field has none (`craft_page_unwritten.with_listed_fields`). An authored
   page (a shell drawn from its own files, Kutch Ajrakh) never lists a new fact, and a craft with too
   few sections has no document: its reader is served the record page, whose `claims` list every
   reader fact. There is no FIELD rule for facts (that check is a section's, decision 0250); the one
   field-dependent fact rule, the SOURCE gate's allowance of a D-only source for a dated ECONOMICS
   price, only loosens, so the statement stands in any field when its source is graded above D.
3. **What decision 0250 left.** `get_proposal` read only `QueuedProposal`; a contributor's AI
   could not see whether its section was approved, rejected or moved on, nor read the reviewer's note.
   A reviewed section (`ArticleSection.writtenByKind = USER`) lived in the database alone, so a
   restore or a diff lost it.

## Decision

1. **The check chooses where it proposes when it runs** (`frontend/e2e/release/mcpContribution.ts`,
   `mcp-contribution.spec.ts`):
   - `pageSlots` reads `GET /api/crafts/coverage` (every curated craft and family page, with the claims
     of each field) and lists, in slug order, each subject with a field holding no fact, at its first
     such field in vocabulary order; a subject whose sixteen fields all hold a fact is passed over. The
     check takes the first whose `GET /api/crafts/{slug}/monograph` is a generated document
     (`shell` null); an authored page is passed over.
   - Past every listed page, `unlistedSlugs` lists the catalogue's other crafts in slug order and the
     check takes the first of at most 12 with a free field (its own coverage), read on its record page
     (`GET /api/crafts/{slug}/page`, the fact among `claims`) when it has no document.
   - The closed-licence quote is still required and sought as before, on the chosen craft's sources
     first, then on the listed pages' (`sourceCrafts`, at most 3 crafts, 6 sources each).
   - Everything else is as it was: the same statement, gates and queue, a `release-check:<time>` key
     the server treats like any other, the reply, `get_facts` signed out, the field's count growing by
     one and back, the page listing the fact, the retraction. No gate is bypassed and no server path
     is added. The summary names the craft, the field and the kind of page.
   Refused: retrying another field after a NOVELTY or DUPLICATE refusal (it would hide a gate that
   refuses wrongly behind a second try, and costs a judge call each time); a test craft or a key the
   server skips (a test-only path the brief rules out); a longer statement meant to fall below 0.75
   (the title shared with the field's facts decides the distance, not the statement).
2. **`get_proposal` follows a section** (`services/section_tickets.followed_proposal`): an id that is
   a `SectionProposal` reads as `SectionTicket` (`kind` `SECTION`: status, subject, field, sentences,
   every check with its reasons, task key, the proposer's note, when it was proposed and reviewed, the
   reviewer's note, and once approved the section it became, its version, its status now and its
   page), the proposer's own or any for an Admin; any other id is read as a fact proposal's, as
   before. The result is `FollowedProposal`, one of the two by `kind`. The tool list stays at 26; its
   description and argument say what the id may be, naming no other tool.
3. **Dossiers carry reviewed sections** (`curation/reviewed_sections.ReviewedSection`, the dossier's
   `sections`, schema 2 unchanged since the part is optional): the export writes each published
   section with `writtenByKind` `USER` of a craft or category, with its sentences, the stored ids of
   the facts they cite, its version, the reviewer's id and the review time; never the writer, who is
   kept privately. The import writes a dossier's reviewed section only where the database holds no
   section a person wrote in that field, in any status, and every cited fact is shown, at its version
   or the field's next if higher; otherwise it leaves the database's. So an exported section imported
   again changes nothing, a file never replaces or brings back a reviewed section, and a file without
   one leaves the published one in place. Machine-written sections stay rebuilt from facts. Writing a
   file's section over a different reviewed one was refused: only a review replaces a review
   (decision 0250).

## Consequences

- The check cannot break as pages fill: each run reads the coverage anew, so a page that fills moves
  the choice to the next page with a free field, and past the curated pages to the catalogue's other
  crafts (461 on 2026-11-28, most holding no fact). It fails by name, before proposing, only if no
  public craft has a page that is not authored and a field without facts. On 2026-11-28 the first
  choice is Agates of Cambay's CLIMATE. Two runs on one release read the same coverage, so they try
  the same craft first. Left open: a held fact the coverage does not count (a contributor's fact
  waiting for review, a family's shared fact) can still sit near the test fact; the field holds no
  shown fact, so such a fact would be one of few.
- A contributor's AI reads its section's outcome and the reviewer's note by the id it already has.
- A restore of the database from git keeps the reviewed sections whose facts it holds, and the
  export's diff shows them. A reviewed section citing a contributed fact the restored database lacks
  is logged and left to the machine's section.
- Tests: `frontend/e2e/release/mcp-contribution-unit.spec.ts` (a craft with a free field is chosen at
  its first, one with every field held is passed over, the choice independent of the listing's
  order, the catalogue's other crafts in slug order, generated, record and authored pages, the
  source crafts, the proposal on the chosen slot); `backend/tests/db/test_section_tickets_db.py` and
  `backend/tests/mcp/test_mcp_fact_tools.py` (waiting, approved with its section, rejected with the
  reason, refused with its check, written at once, another contributor refused and an Admin reading
  any, an unknown id read as a fact's, a fact's ticket unchanged through the tool, no section before
  approval); `backend/tests/db/test_reviewed_sections_export_db.py` (exported with its facts, version
  and reviewer and not its writer; imported again unchanged; an import without it leaving it in place;
  restored when the database lost it; never replacing one a person wrote; not restored when a cited
  fact is unseen) and `backend/tests/curation/test_reviewed_sections.py` (no part when there are none,
  the text read back unchanged, one a field, the diff by field).

## What is left

- The `kalavigyan-craft-pages` skill's "Where each change goes" table is the lead's to extend with the
  row for a reviewed section (in the lane's report).
- The release check proves the record page path only when every curated page is full; until then its
  unit specs and the shared steps are what keep it true.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-28; what the code does today is in the contracts named above and in the tests listed under
Consequences.
