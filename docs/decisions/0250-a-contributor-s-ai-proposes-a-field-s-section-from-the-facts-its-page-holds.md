# 0250. A contributor's AI proposes a field's section from the facts its page holds, each sentence gated and the section reviewed before it publishes

A field's written section is a part of a page bundle and of a draft: its sentences in order, each
naming the stored facts it rests on. The preview draws it in place of the published section. When
it is proposed, every sentence must cite shown facts of the page and of the field, and state no
number, name, date or place they do not; a judge, the cheapest model the nightly evaluation holds
reliable for it, finds anything else a sentence says. One refused sentence refuses the whole
section. A section that passes waits in a review queue of its own, beside the published one.
Approval puts it in that section's place, keeps the replaced one in the record, completes the
SECTION task, and the dossier rebuild leaves it standing. No MCP tool is added.

Date: 2026-11-28. Status: accepted (the lead's lane brief `ux-1126/section-proposals`, on the
owner's rules that every feature is usable over MCP with a person confirming, and that a
contributor's AI reaches the Kutch Ajrakh bar unaided). It amends
[decision 0248](0248-what-the-fresh-agent-could-not-fix-on-sanganeri.md) (What is left: no tool wrote
a field's prose from facts the page already holds). Migration `0125_section_proposals`. The
contracts are `docs/contracts/knowledge-writes.md` (Section proposals, and the judges' cases),
`docs/contracts/open-work.md` (the SECTION task, the `write_section` prompt, `edit_draft`,
`preview_page` and `propose_page`) and `docs/contracts/review-queue.md` (Sections), with the
contributor skill (Pages, Drafts, Writing a section and Never).

| For | Read |
|---|---|
| The gap it closes | [decision 0248](0248-what-the-fresh-agent-could-not-fix-on-sanganeri.md), What is left; the research agent's `report_site_gap` of 2026-11-28 |
| The review path it follows | the structure proposals ([decision 0108](0108-structure-proposals-become-curated-facts.md), `services/structure_proposals*.py`) |
| The judge it reuses | the novelty gate and the cheap judge first ([decision 0169](0169-mcp-follow-ups-kept-true.md) and `docs/contracts/knowledge-writes.md`, Cost at the centre) |

## Context

`list_open_work` raised SECTION tasks with the `write_section` prompt, and their acceptance asked
for a section of at least three sentences built from the stored facts, each citing every fact it
uses and adding nothing they do not say. Sanganeri Hand Block Printing had seven such fields with
4 to 12 facts each and no or one published sentence. No tool took a section, and the prompt ended
on "the section is published only through KalaVigyan's own rebuild". How sections are written today
was read first:

1. **The dossier rebuild.** Each deploy imports every dossier, and `publish_dossier_sections`
   writes one sentence a shown claim into its discipline's `ArticleSection`, superseding the
   published row whenever its sentences differ (`publish_section`) and retiring fields the dossier
   no longer holds (`retire_sections`). A contributed section would have been rebuilt away at the
   next deploy.
2. **The composer's section checks.** `services/section_blocks.prose_problems` refuses a sentence
   that cites no stored claim, rests on a hypothesis, states a figure no cited claim or quote holds
   (`unsupported_figures`) or names a month, season, place or river none of them names
   (`unstated_names`). They are deterministic and cost nothing.
3. **The judges.** The novelty gate asks a judge to list every detail a candidate states that its
   held facts do not (`newDetails`), on the cheapest priced model first and the default route only
   for an unusable reply (`thrifty_judges`), scored every night on labelled cases. That list empty
   is exactly "says nothing its facts do not say".
4. **A draft's facts as prose.** Decision 0248 drew a draft's facts as sentences of their field
   (`PageAdditions.sentences`, appended to the published section) and kept a figure's sentence
   while the field holds fewer than three (`told_sentences`).
5. **The review queue.** Each kind has a table of pending rows, a rendered item, approvers and
   rejecters, the refresh of the pages a decision changes, and a staged kind for an Admin's MCP
   client. Structure proposals store their checks and task, approve at once for a Professor or
   above, and otherwise wait for a Professor or Admin. `ArticleSection` has a `PROPOSED` status and
   reviewer columns, but no origin, task, checks or reason, and every count and stamp of a page
   reads its rows, so a waiting section stays out of it.

## Decision

1. **The part** (`research/section_proposals.SectionPart`). `sections` in a page bundle (at most 16,
   one a field) and in a draft (`edit_draft` add; a later section for a field replaces the draft's
   earlier one; remove by part `section` and index): `{field, sentences [{text, claim_ids}], note}`,
   1 to 24 sentences of up to 1000 characters, each citing 1 to 8 stored facts by id, each once
   (`article_sections.SectionSentence`). A section cites stored facts only, never a bundle's
   `fact:N`: a fact proposed beside it joins its field's prose through the draft as before. The
   MCP tool list stays at 26 tools; `edit_draft`'s add types the part, `preview_page`'s and
   `propose_page`'s bundle names it, and their descriptions only describe.
2. **The gates** (`services/section_gates.py`), in order, stopping at the first that fails, each
   reason naming its sentence:
   - **HELD**: every cited fact is held by the page (`page_held_facts.held_claims`) and shown to
     readers (`knowledge_view.claims_by_id`, without a fact held for a failed quote).
   - **FIELD**: every cited fact names the section's field as its primary or one of its secondary
     fields; a fact of another field is refused unless its record names this field too.
   - **SENTENCES**: at least three sentences, or as many as the facts the page holds in the field
     allow (the field coverage's count, or the cited facts of the field if more); the passing
     reason says so ("2 sentences, as many as the 2 facts this page holds in GEOLOGY allow").
   - **STATED**: the composer's own `prose_problems`: a fact, not a hypothesis, and no figure,
     month, season, place or river its cited facts and quotes do not state.
   - **FAITHFUL**: the novelty judge's question asked of each sentence against the texts of the
     facts it cites, read for `newDetails` alone (`candidate_judge.parsed_new_details`, so a detail
     the judge calls too general still refuses); a sentence that restates the fact it cites is not
     asked. The ladder is `thrifty_judges`, the cheapest priced model first. A failed or missing
     judge refuses the part as checks unavailable and stores nothing. The nightly judge evaluation
     scores this reading on six labelled cases (three faithful, three adding a duration, a cause or
     a place) against a floor of 0.8 (`judge_cases.json` `faithful`, `faithful.accuracy`).
3. **The preview** draws a passing section in place of the field's published one, the draft's new
   facts after it (`PageAdditions.written`), and the page checklist reads the drawn page as it reads
   any other. It runs the first four gates only; the judge reads the sentences when the section is
   proposed. A refused section is reported with its reasons and the published section is drawn.
4. **The proposal** is a `SectionProposal` row (migration `0125_section_proposals`: the
   proposer, the craft or category, the field, the sentences, the checks, the SECTION task's key,
   the note, the origin, `PENDING`, `REFUSED`, `APPROVED` or `REJECTED`, the reviewer, the reason and
   the `ArticleSection` it wrote), counted against the structure hour. A refused section is kept
   refused, changing nothing. A section that passes from a Professor's, Admin's or Master Admin's
   account is approved at once, as structure is; a trusted account's draft or several-part bundle
   is still held for the person's one confirmation first. A pending section hides its SECTION task
   from other contributors, as a pending component hides its task.
5. **The review** is the queue kind `SECTIONS` (`MARK_CLAIM_LEVEL`, as structure; origins
   `CONTRIBUTION` and `AGENT`). Its item sets the proposed sentences beside the published section,
   each sentence with the texts of the facts it cites, with the checks and, when a cited fact has
   left the page, why it can only be rejected. It is decided on the Review page (its own card), over
   HTTP, and by an Admin's MCP client with `review_queue` and `stage_reviews` (staged kind
   `SECTIONS`, approve or reject), confirmed by a person; a page proposal carries its section parts
   in the `SECTIONS` queue under the field's chapter.
6. **Publishing.** Approval checks HELD, FIELD and STATED again (refused as stale when the page has
   moved on), then writes a new `PUBLISHED` `ArticleSection` at the field's next version with the
   proposer as `writtenById` (`writtenByKind` `USER`) and the reviewer and time, supersedes the one it
   replaces, which stays in the record, completes the proposer's reservation of the SECTION task,
   and names the page to refresh as structure does. The dossier rebuild (`publish_section`,
   `retire_sections`) leaves a section a person wrote and a reviewer approved standing; only another
   reviewed section replaces it.
7. **The prompt and the skill.** `write_section` walks the task: claim it, read the facts and the
   published section, propose a missing fact first, write the sentences, preview a bundle or draft
   holding the section, and propose it. The contributor skill's Writing a section says how a
   sentence cites and what it may say, and Never no longer forbids proposing prose: a section built
   only from shown facts is the one kind of prose a contributor proposes.

## Consequences

- Sanganeri's seven thin fields, and every SECTION task, can be written over MCP from the facts the
  page already shows, and close once approved.
- A field with a reviewed section no longer follows its dossier's rebuild; a fact added to that field
  later is listed under it until a section that cites it is approved.
- A section costs at most one judge call on the cheapest model, none when its sentences restate
  their facts; the nightly evaluation makes six more judgements.
- The Review page, the staged confirmation and the held-page confirmation know the new kind and part
  before the backend serves them, so neither side meets a value it does not know.
- Tests: `backend/tests/sections/test_section_gates.py` (every gate both ways: an unheld fact, a
  fact of another field and one naming the field, too few sentences and a short field's count, an
  unstated figure, a hypothesis, the judge's details, a judge that finds none, no judge asked for a
  restated fact, no judge at all), `test_section_parts.py` (the part's shape, a bundle writing a
  field twice, a draft replacing and removing a section, `edit_draft`'s add, the page proposal's
  part), `test_section_preview.py` (a section in place of the published one with the draft's facts
  after it, a new field's section, none), `backend/tests/db/test_section_proposals_db.py` (a
  contributor's section waiting beside the published one; approval replacing it, keeping the old
  one and completing the task; the dossier rebuild keeping it; a rejection; HELD, FIELD and
  SENTENCES refusals changing nothing; an unfaithful sentence; a Professor's section written at
  once; the preview drawing a section and storing nothing),
  `backend/tests/test_section_proposals_migration.py`, the judge cases in
  `backend/tests/knowledge_writes/test_judge_eval.py`, the MCP shapes in
  `backend/tests/mcp/test_directory_listing.py` and `test_mcp_body_names.py`, the prompt in
  `test_mcp_prompts_resources.py`, the kinds pinned in `test_staged_contract.py`, `test_open_work.py`,
  `test_review_queue_rules.py`, `test_published_content_rules.py` and `test_review_diff_migration.py`
  (each now with `SECTIONS`), and the web specs `review-sections-unit` and `staged-reviews-unit`.

## What is left

- `get_proposal` reads fact proposals only; a section proposal's outcome is in the part report, the
  draft's result and, once approved, the page.
- Dossiers do not carry sections, so a reviewed section lives in the database alone; a dossier
  edited for a bulk import cannot change it.
- The `kalavigyan-craft-pages` skill's "Where each change goes" table is the lead's to extend, with
  the row in this lane's report.
