# Knowledge writes: proposals, candidate gates and the review switch (decision 0101, items 5, 8, 12)

Every new fact, whatever its origin, is a candidate. It is published only through four automatic
gates, run in order, and the review switch then decides whether it goes live at once or waits for
a Professor or Admin. The same path serves a person on the site, the Knowledge API, an agent on the
MCP server and our own research write-back.

Code: `research/knowledge_writes.py` (the proposal and the reply), `research/candidate_gates.py`
(the pure gate decisions), `research/candidate_judge.py` (the judge's prompts, schemas and reply
rules), `research/review_switch.py` (the switch and where a fact is placed);
`services/candidate_sources.py` (fetching and grading the sources), `services/candidate_store.py`
(the subject's held facts), `services/candidate_gates.py` (running the gates with the adapters),
`services/candidate_writes.py` (the stored outcomes and sources differ),
`services/proposal_writes.py` and `services/fact_proposals.py` (`propose_fact`),
`services/write_back_gates.py` (the research write-back), `services/app_settings.py` (the switch
setting); `api/routes/knowledge_writes.py`, `api/mcp_fact_tools.py`, `api/proposal_deps.py`.

## Who may do what

| Action | Capability | Roles |
|---|---|---|
| Propose a fact (`POST /api/knowledge/facts`, MCP `propose_fact`) | `PROPOSE_KNOWLEDGE` | Researcher and above |
| Read and set the review switch (`/api/knowledge/review-switch`) | `REVIEW_CONTRIBUTIONS` | Admin, Master Admin |

The MCP tool also needs a signed-in connection holding the `contribute` scope
(`core/mcp_scopes.CONTRIBUTE_SCOPE`); until OAuth sign-in reaches the MCP route the tool answers
with a tool error naming that.

## The proposal (`FactProposal`, schema version 1, camelCase on the wire)

- `subject {kind: craft | category, slug}`: a craft by its slug (merged crafts follow their merge)
  or a category by its slug.
- `field`: one of the 16 fields (`list_fields`); `fields`: up to 3 secondary fields, distinct and
  without the primary one.
- `statement`: 20 to 1,000 characters, one fact, no personal data (emails, phone and
  Aadhaar-like numbers are refused).
- `sources`: 1 to 5, each named once (by canonical URL): `{url (https), title, licence?, quotes:
  [{text (at most 300 characters), locator?}] (1 to 6, each once)}`.

A malformed proposal is refused before any gate (422 on the site; a tool error on MCP).

## The gates, in order

A refusal stops the run; every gate that ran is stored as one `CandidateCheck` row
(`claimId, gate, passed, reasons[], relatedClaimIds[], model, checkedAt`, one per claim and gate).

1. **QUOTES.** Every source is fetched by our fetcher (`research/fetcher.Fetcher`, the same one
   live research uses) and every quote must be found verbatim in the fetched text
   (`research/quotes.quote_occurs`: NFKC, typographic dashes and quotes, line-break hyphens and
   whitespace folded) and be at least 20 characters. Every number or formula in the statement
   must appear in one of its quotes. A page that is refused (robots, size, type), missing or
   blank refuses its quotes with the reason. When our fetcher itself is down nothing is stored
   and the caller is asked to try again (503, or a tool error).
2. **SOURCE.** Each source is graded: a source already stored keeps its own reliability; a newly
   fetched page takes the grade the research pipeline gives a web page (C). A fact resting only on
   D sources is refused, except an ECONOMICS fact stating a price (the curation rule). A source
   stored as RESTRICTED is refused. A licence declared open (CC BY, CC0, public domain) that the
   page itself contradicts is refused. Otherwise the licence passes and is recorded; it decides
   only whether quotes are public: a fetched page's full text is stored for researchers
   (`chunk_acl`), so its quotes are withheld from public views and exports.
3. **DUPLICATE.** The statement is embedded in the stored document form and compared with the
   subject's held facts in the field (primary or secondary): shown or waiting statuses (`DRAFT`,
   `PROPOSED`, `IN_REVIEW`, `APPROVED`), open sensitivity. The same statement once case and final
   stops are folded is refused at once. Otherwise the 8 nearest held facts at cosine similarity
   0.8 or more go to the judge (the structured model, `EVAL_JUDGE`), which names each pair SAME,
   DIFFERS or DISTINCT with a reason. SAME refuses; DIFFERS passes and is kept as sources differ,
   never resolved; DISTINCT passes. Held facts without a vector are found only by the identical
   text.
4. **NOVELTY.** The judge decides whether the fact adds to or changes what the section says,
   against the subject's 12 nearest held facts in the field, and its reason is stored. A fact that
   differs from a held fact passes without the judge (it changes the section), and so does the
   first fact of a field. A refusal names the held facts that already say it.

The subject's facts are the craft's (its own concepts and its sub-category's), or a category's
(its curated claims and the shared concepts named for it). All text sent to the judge is quoted
data in `untrusted_source` blocks.

## The review switch

One admin setting, `knowledge.review_switch`, per origin:

| Origin | Who | Default |
|---|---|---|
| `RESEARCH` | the research write-back of answers and coverage enrichment | `AUTO` |
| `CONTRIBUTION` | the site and the Knowledge API | `APPROVAL` |
| `AGENT` | the MCP server | `APPROVAL` |

| Case | Claim status | Shown | In the review queue | Reply `outcome` |
|---|---|---|---|---|
| Passed, `AUTO` | `IN_REVIEW` (live, unreviewed) | yes, at its level | yes | `PUBLISHED` |
| Passed, `APPROVAL` | `DRAFT` (hidden) | no | yes | `WAITING` |
| Passed, proposed by a Professor, Admin or Master Admin | `APPROVED` | yes | no | `PUBLISHED`, `approvedAtOnce` |
| Refused at a gate | `REJECTED`, kept only for audit | no | no | `REFUSED` |

- The proposer's role is read from their account row at the moment of the write, never from the
  request or the token.
- A quoted fact is stored at `PROVISIONAL`; approval at once does not raise the level (only a
  review does). A fact refused at QUOTES is stored at `HYPOTHESIS`.
- Sources differ: when a differing fact goes live, it and every held fact it differs from get
  `sourcesDiffer`. A waiting fact is flagged when it is approved: the approving review calls
  `services/candidate_writes.mark_sources_differ(session, claim_id)`, which reads the stored
  DUPLICATE outcome.
- Who proposed it is kept privately: `Claim.createdById`, a `ReviewEvent` by the proposer whose
  note names the origin and the placement, and `ClaimSource.foundBy` (`CONTRIBUTION` or `AGENT`).
  A proposed claim's `origin` is `RESEARCHER`, so the craft page shows it as a researcher's.
  A newly stored source is marked `origin CONTRIBUTION` with `addedById`.

## Routes

| Route | Body | Answer |
|---|---|---|
| `POST /api/knowledge/facts` | `FactProposal` | 200 `ProposalReply` (origin `CONTRIBUTION`) |
| `GET /api/knowledge/review-switch` | none | `ReviewSwitchView {current, defaults}`, each `{research, contribution, agent}` of `AUTO` or `APPROVAL` |
| `PUT /api/knowledge/review-switch` | `ReviewSwitchUpdate`, any of `research`, `contribution`, `agent` | `ReviewSwitchView`; audited as `settings.review_switch_updated` |

Refusals: 401 or 403 without the capability; 422 for a malformed proposal or an unknown subject;
403 when the proposer's account no longer exists; 503 when the fetcher, the embedding route or
the judge could not run (nothing is stored).

`ProposalReply {schemaVersion 1, outcome, claimId, status, level, approvedAtOnce, inReviewQueue,
sourcesDiffer, differsFrom[], gates[{gate, passed, reasons[]}], message}`. A refused proposal is
still a 200: the reply's outcome and the failing gate's reasons say why.

## MCP

`propose_fact` (`api/mcp_fact_tools.py`, in `FACT_TOOLS`), scope `contribute`, annotations
`readOnlyHint false`. Arguments `{proposal: FactProposal}`; the result is `ProposalReply` as
structured content. Origin `AGENT`. A missing sign-in, scope or rank, a malformed proposal or an
outage comes back as a tool error the agent can act on.

## The research write-back

`services/research_write_back.store_live_research(..., judge=None)` runs each new claim (one
whose dedupe id is not yet stored) through the same gates with origin `RESEARCH`, using the
documents the research already fetched for gate 1 and the evidence items' grades and licences
for gate 2. A claim already held is re-found as before (new citations, a level raised from
hypothesis), with no gates. A refused claim is not written: the write-back's `skipped` list
carries the gate and its first reason, and when the duplicate or novelty gate named held facts the
answer's sentence cites the first of them instead. A written claim's checks and its vector are
stored; its status follows the switch for `RESEARCH`.

Without a judge (the default until the callers pass one), the duplicate gate refuses only
identical texts and records that no judge compared the close facts, and the novelty gate is
recorded only when it needs no judge. When the embedding route or the judge fails, the write-back
falls back to the identical-text check and logs it; it never fails the answer.

## Versioning

`FactProposal` and `ProposalReply` carry `schemaVersion 1`. A change that removes or renames a
field, or changes its meaning, is a new schema version.
