# Review queue (decision 0101, items 5, 12, 13 and 14)

One review path for everything other people give: proposed and researched facts, artisans'
testimony, contributed pictures, component proposals and page layout proposals, whatever their
origin (the site, the
Knowledge API, the MCP server, an artisan's conversation). Reviewers see one page of pending items,
newest first, and decide each through one route per action. A reviewer's own contribution is
approved at once by its own write path (`knowledge-writes.md`, `image-contributions.md`,
`open-work.md`) and never enters the queue; the queue also leaves out anything the viewer proposed.

Contract: `backend/app/research/review_queue.py`, with the component body in
`research/review_queue_components.py` and the layout body in `research/layout_proposals.py`.
Services: `services/review_queue.py` (the page), `review_queue_select.py` (what is pending, per kind),
`review_queue_fact_views.py`, `review_queue_components.py` and `review_queue_layouts.py` (what a
reviewer needs to judge an item, and the component and layout decisions), `review_queue_decisions.py`,
`review_queue_facts.py` (decisions) and `review_queue_errors.py`. Route: `api/routes/review_queue.py`.
No table or column of its own: the queue reads the rows each kind already keeps.

## Who sees which kind

Each kind follows the capability its queue names in `research/open_work.py` (`REVIEW_QUEUES`):

| Kind | Capability | Roles |
|---|---|---|
| `FACTS` | `MARK_CLAIM_LEVEL` (`RETRACT_CLAIM` to retract) | Professor and above |
| `TESTIMONY` | `REVIEW_TESTIMONY` | Professor and above |
| `IMAGES` | `REVIEW_CONTRIBUTIONS` | Admin and above |
| `COMPONENTS` | `REVIEW_CONTRIBUTIONS` | Admin and above |
| `LAYOUTS` | `REVIEW_CONTRIBUTIONS` | Admin and above |

So an Admin or Master Admin sees every kind (item 12); a Professor sees facts and testimony. An
account that reviews no kind is refused the route (403).

**Who proposed it is kept privately** (item 13). An item carries `proposer {name, role}` only when
the viewer holds `REVIEW_CONTRIBUTIONS` (Admin and above); for everyone else it is `null`, and the
name is never sent. Research written back by the system has no proposer. Testimony keeps its own
consented credit line (`speaker`, `line`), which the artisan chose and the existing testimony
review already shows.

## What is pending

| Kind | Row | Pending when |
|---|---|---|
| `FACTS` | `Claim` | `status` is `DRAFT` (waiting, hidden: the review switch said `APPROVAL`) or `IN_REVIEW` (live and unreviewed: `AUTO`), it went through the candidate gates (it has `CandidateCheck` rows), and the viewer did not write it |
| `TESTIMONY` | `ArtisanContribution` | `status` `PENDING`, not the viewer's |
| `IMAGES` | `ImageContribution` | `status` `PENDING`, not the viewer's |
| `COMPONENTS` | `ComponentProposal` | `status` `PENDING`, not the viewer's |
| `LAYOUTS` | `LayoutProposal` | `status` `PENDING`, not the viewer's |

**Origins.** A fact's origin is `RESEARCH` when it was written back from an answer's research
(`Claim.origin` `LIVE_RESEARCH`), `AGENT` when a source was found by an agent
(`ClaimSource.foundBy` `AGENT`), else `CONTRIBUTION`. Testimony is `TESTIMONY`, a picture
`CONTRIBUTION`, a component proposal `AGENT`, a layout proposal its own `origin` (`CONTRIBUTION`
from the site or the Knowledge API, `AGENT` from the MCP server).

**Craft.** A fact belongs to a craft through its concept (the craft's own concepts and edges, as
retrieval scopes them); testimony and pictures by `craftId`; a component proposal by `craftId` or a
`CRAFT` subject naming the craft's slug; a layout proposal by `craftId` (a craft's or family's page;
a category's page has no craft).

## `GET /api/review-queue`

Query: `kind` (`FACTS`, `TESTIMONY`, `IMAGES`, `COMPONENTS`, `LAYOUTS`), `craft` (a craft slug), `origin`
(`RESEARCH`, `CONTRIBUTION`, `AGENT`, `TESTIMONY`), `cursor`, `limit` (1 to 50, default 25).

Answer `ReviewQueuePage`:

- `schemaVersion: 1`;
- `kinds`: the kinds this viewer reviews, in the order above;
- `counts`: pending items per kind the viewer reviews, under the craft and origin filters (not the
  kind filter, so the tabs can show every count);
- `total`: the pending items the page's filters select;
- `items`: newest first by `submittedAt`, then id, across kinds;
- `nextCursor`: `"<microseconds since 1970>~<id hex>"` of the last item when more follow, else
  `null`. Pass it back as `cursor` with the same filters.

Each item has `id`, `kind`, `origin`, `submittedAt`, `craft {slug, name, path}` or `null`,
`proposer` (above) and one body:

- `fact`: `statement`, `field`, `fields`, `status`, `level`, `sourcesDiffer`, `concept {name,
  type}`, `sources [{title, url, licence, reliability, quotes [{text, locator}]}]` and `gates
  [{gate, passed, reasons, model, related [{id, text}]}]` in gate order (QUOTES, SOURCE,
  DUPLICATE, NOVELTY); `related` are the held facts a gate compared it with.
- `component`: the proposal (`label`, `title`, `description`, `kind`, `field`, `fields`,
  `subjects`, `consideredLabels`, `extends`, `extension`, `taskKey`) and `closest`: up to three
  library components, most matching reasons first, then the most words shared (`overlap` 0 to 1),
  never the one it extends.
- `layout`: `subject {kind, slug}`, `subjectName`, `pageUrl`, `baseVersion`, `currentVersion` (the
  page's layout now, 0 for none), `stale` (the two differ, so approval is refused), `note`,
  `entryCount` and `changes [{ref, change (ADDED, CHANGED, REMOVED), before, after}]`: the proposal
  against the current layout, entry by entry, in reading order (chapter, then place), each side a
  `PageLayoutEntry` (`research/layout_proposals.layout_changes`).
- `picture`: the `ImageContributionView` of `image-contributions.md`.
- `testimony`: the review item of the testimony review (`/api/testimony/review/{id}`).

Refusals: 403 for an account that reviews nothing, 404 for an unknown craft, 422 for a malformed
filter or cursor.

## Decisions

| Route | Body | For |
|---|---|---|
| `POST /api/review-queue/{kind}/{id}/approve` | `{note?, version?, englishChecked?}` | every kind |
| `POST /api/review-queue/{kind}/{id}/reject` | `{reason, version?, testimonyReason?}` | every kind |
| `POST /api/review-queue/FACTS/{id}/raise` | `{note?}` | facts |
| `POST /api/review-queue/FACTS/{id}/retract` | `{reason}` | facts |

`reason` is 3 to 500 characters and kept with the decision; `note` up to 500. Answer
`QueueDecision {schemaVersion, kind, id, status, level, sourcesDiffer, message}`.

**Facts** (`review_queue_facts.py`), each with a `ReviewEvent` (actor `USER`) and an audit entry
`review.fact_<approved|rejected|raised|retracted>`:

| Action | From | To |
|---|---|---|
| approve | `DRAFT`, `IN_REVIEW` | `APPROVED` at its level |
| reject | `DRAFT`, `IN_REVIEW` | `REJECTED`, the reason as the event's note |
| raise | `DRAFT`, `IN_REVIEW`, `APPROVED` at `PROVISIONAL` | `APPROVED` at `REVIEWED`, `levelReason` "Reviewed against its quoted sources by a <role> on <day>" |
| retract | `IN_REVIEW`, `APPROVED` | `RETRACTED`, the reason as the event's note |

Approving or raising a waiting (`DRAFT`) fact publishes it and calls
`candidate_writes.mark_sources_differ`, so a fact the duplicate gate found to differ from a held
one is shown with that one as "sources differ" (item 5). The page rebuilds through nightly upkeep,
whose page stamps follow the facts' status and level.

**Component proposals** (`review_queue_components.py`): approve records `APPROVED` with the
reviewer, the time and the note: it waits for a builder to build and register it in the library;
nothing is built. Reject records `REJECTED` with the reason. Audit `review.component_<...>`.

**Layout proposals** (`review_queue_layouts.py`): approve writes the proposal's entries as the
page's next `PageLayout` version through `page_layouts.store_layout`, as the reviewer (audited
`PAGE_LAYOUT_WRITTEN`), and records `APPROVED` with the reviewer, the time, the note and the version
written; when the page's layout has moved past `baseVersion` it is refused (409) and the proposal
can only be rejected. Reject records `REJECTED` with the reason; nothing is written. Audit
`review.layout_<...>` with the version.

**Pictures** go through `image_contributions.approve` and `.reject` (the reason is the note), with
an audit entry `review.image_<...>`. **Testimony** goes through `testimony_writes.approve` and
`.reject`: a testimony decision names the `version` it was read at (422 without it; 409 when the
item changed since); approval takes `englishChecked`; a rejection takes `testimonyReason` (one of
the testimony reasons, `OTHER` by default) with `reason` as the note to the artisan. The old routes
(`/api/contributions/images/review/...`, `/api/testimony/review/...`) keep working.

Refusals: 403 for a kind the account does not review or for one's own item, 404 for an unknown item
(and for a fact that never went through the gates), 409 for a decision the item's state does not
allow or a stale testimony version, 422 for a bad body or an action a kind does not have (only a
fact is raised or retracted). Every refusal rolls the session back.

## Erased testimony takes its orphaned concepts

When an artisan withdraws testimony or deletes a conversation, its claims are erased
(`WITHDRAWN`) and `testimony_claims.drop_orphans` removes the testimony concepts of that craft that
nothing else rests on (owner, 2026-11-19): no claim other than erased ones, and no link that
`orphan_concepts.concept_unlinked` names (an edge, a process stage, a material, a component subject
or a term). A concept something still links stays.

## The Review page (`/admin/review`)

In admin settings, for Professors and above (route guard `/admin/review`, gate `queue_reviewer`),
from the menu and the settings hub. Tabs per kind with their counts; filters for origin and craft,
kept in the address (`?kind=&origin=&craft=`). A card per item:

- a fact (`components/review/FactReviewCard.tsx`): the statement, what is shown now, level, fields,
  concept, "sources differ", sources with their verbatim quotes, and each automatic check with its
  reasons and the facts it was compared with;
- a component proposal (`ComponentReviewCard.tsx`): the proposal, the labels its proposer
  considered and the closest library components;
- a layout proposal (`LayoutReviewCard.tsx`, `LayoutChangeList.tsx`): the page (linked from the header
  for a craft or family, from its name for a category), the kind of page and the number of entries,
  the proposer's note, which version it builds on and what approving writes, and each change ("Placed",
  "Moved from ... to ...", "Taken out"), the first 12 and then "Show all N changes"; a stale proposal
  offers Reject only (`frontend/lib/layoutReviewView.ts`);
- a picture: `PictureReviewCard.tsx`; testimony: the testimony `ReviewCard.tsx`, both reused with
  their own decision routes.

Facts, component proposals and layout proposals decide through `QueueDecisionBar.tsx`: an `ActionGroup` of Approve, Approve as
reviewed (facts), then Reject (waiting) or Retract (live) last as the destructive action, with a
Reason field required for either. The client contract is `frontend/lib/reviewQueueContract.ts`;
pure rules are in `frontend/lib/reviewQueueView.ts`. `/admin/pictures` and `/admin/testimony`
stay, and list decided items.

## Tests

`backend/tests/review_queue/` (rules and routes), `backend/tests/db/test_review_queue_db.py` and
`test_review_queue_decisions_db.py`, `test_layout_proposals_db.py`, `backend/tests/layouts/`
(layout proposal rules and routes), `frontend/e2e/review-queue-unit.spec.ts` and
`review-layouts-unit.spec.ts`.
