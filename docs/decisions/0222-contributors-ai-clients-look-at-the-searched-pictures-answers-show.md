# 0222. Contributors' AI clients look at the searched pictures answers show: a refusal hides one at once, and a trusted or agreeing look marks it seen

A searched picture linked to a fact by its words is now offered to contributors' AI clients, which
can see images, as open work: `check_pictures` hands each a batch of stored links, most-served
first, every picture as image content, and records a verdict on each. A `does_not_show` stops the
link being served at once; a `shows` marks it seen (`VISION`) when the account's work publishes at
once or a second account agrees; disagreement waits for an Admin, who can reverse any verdict. No
answer gains a model call or an input token.

Date: 2026-11-25. Status: accepted (the owner asked for it on 2026-11-25; the lead's lane brief
`picture-checks`). It amends
[decision 0166](0166-pictures-terms-and-stored-pieces-kept-true.md) (a stored picture is reused:
now with the verdicts kept on its link),
[decision 0215](0215-every-searched-picture-served-names-its-craft-s-world-and-every-drawing-is-judged-by-the-paint-a-reader-sees.md)
(`served_picture`, which the zoom story and uncurated craft pages use, drops a refused link) and
[decision 0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) (its tools reach the
new `PICTURE_CHECKS` kind). The contracts are `docs/contracts/open-work.md` (Picture checks),
`docs/contracts/review-queue.md` (the `PICTURE_CHECKS` kind) and `docs/contracts/knowledge-api.md`
(the tool groups).

| For | Read |
|---|---|
| How searched pictures are chosen by their words | [decision 0034](0034-images-and-terms.md), [0207](0207-a-searched-picture-names-its-craft-s-world-and-a-stored-one-that-does-not-is-not-served.md), [0211](0211-a-picture-from-a-shop-a-stock-agency-or-an-auction-is-not-shown.md) and [0215](0215-every-searched-picture-served-names-its-craft-s-world-and-every-drawing-is-judged-by-the-paint-a-reader-sees.md) |
| Why no vision call runs on an answer | [decision 0165](0165-answers-counted-as-settled-asked-as-asked.md); `docs/TECH_DEBT.md`, Relevance is by text only |
| The tool budget and the groups | [decision 0111](0111-fewer-mcp-tools.md), `backend/tests/mcp/test_tool_budget.py` |
| Staged review over MCP | [decision 0170](0170-review-over-mcp-staged-and-pages-refreshed-now.md) and [0194](0194-an-admin-removes-and-edits-published-content-over-mcp.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- A picture an answer finds by search is linked to the facts it illustrates (`MediaRefClaim`,
  relevance `TEXT`) when its title names the craft's world and shares content words with the fact,
  from no shop, stock agency or auction. Nobody looks at it, so a picture whose title is right but
  which shows another step, another craft or a product passes, and decision 0166 reuses it for
  every later answer.
- A vision call per answer would add model calls and image tokens to every answer, which the
  owner's rule of 2026-11-23 forbids (decision 0165). The MCP server's contributors connect AI
  clients that see images, and the server already returns image content to them.
- Production, read once through the lead's box runner on 2026-11-25 (read only): 688 links, all
  `TEXT`; 520 of them link 150 searched pictures to 248 facts (Commons 219 links of 52 pictures,
  SearXNG 175 of 73, Openverse 126 of 25). 153 of the 156 stored answers show a searched picture
  (109 pictures; the most shown is in 87 answers, the next in 60 and 49), 158 answers cite a fact
  one is linked to, and 13 crafts' stored pages (26 of 922 page rows) show 7 of them. By host, 184
  links are Commons thumbnails on `thumb.wikimedia.org`, 126 Openverse thumbnails, 35 Commons
  files on `upload.wikimedia.org`, and the 175 SearXNG links sit on shops, magazines and publishers.

## Decision

1. **One task, one tool.** A task kind `CHECK_PICTURES` beside `MISSING_PICTURE`: one open-work
   task for the whole site (`HIGH`; its count the links waiting), listed when no page is asked for.
   One new tool, `check_pictures {verdicts?, take?}` in the `pictures` group, both fetches and
   records: verdicts first, then a batch of `take` (default 5, at most 10). The tool list grows from
   23 to 24 (budget 32), the admin list from 27 to 28 (budget 36); the input and list byte budgets
   are unchanged. Extending `give_pictures` was refused: it gives a craft's pictures under a
   person's declaration, and its arguments would have carried two unrelated jobs.
2. **The batch.** Only searched links wait: relevance `TEXT`, not refused, of a picture that is not
   a curator's pick, a field photo or a contributor's own picture (`CHOSEN_PICTURE_PROVIDERS`,
   `FieldImage`), to a fact readers see, on a host the site's picture fetch reads
   (`PICTURE_HOSTS`; a Commons thumbnail on `thumb.wikimedia.org` is read from `upload.wikimedia.org`
   by the new `commons_upload_url`). The account's own held links come first, then the most
   served: the answers that cite the link's fact (an answer shows the stored pictures of the facts
   it cites), a count one grouped read of `Answer.claimIds` gives; pages add little (13 crafts) and
   are not counted. Each picture is fetched through `picture_files` and `export_pictures` at the
   330 px Commons width, 8 seconds a picture, as JPEG image content; one that cannot be read is left
   out and never reserved, never sent as a link.
3. **Reserved like any task.** Each link a batch gives is a `TaskReservation` of its own,
   `CHECK_PICTURES:<link id>`, for two hours, counted against the account's trust tier, so two
   clients never check the same link at once and many check in parallel; `reserve_tasks` never
   claims one, `release` gives one back, and a verdict completes it. A link needed an id for this,
   for the verdicts and for the review queue: `MediaRefClaim.id`, a unique uuid filled for every
   existing row.
4. **Stored as a table of checks.** `PictureCheck {linkId, userId, verdict SHOWS | DOES_NOT_SHOW,
   reason 12 to 300 characters, ruling, trusted, createdAt}`, never edited or deleted, rather than
   columns on the link: columns would keep only the latest verdict, and the rule needs every one
   (two accounts agreeing, a disagreement, the latest ruling). The link keeps what serving needs:
   `relevance` (`VISION` once seen) and `refusedAt`, written from the checks by one rule.
5. **Trust, both ways** (`research/picture_checks.checked_state`). A `does_not_show` hides the link
   at once: hiding is low-risk, and the picture and its other links are untouched. A `shows` marks
   it `VISION` only from an account whose contributions publish at once (the same
   `trust_tiers.publishes_at_once` with the agent switch the page tools use, kept on the check as
   `trusted`) or with a second agreeing `shows` from another account; otherwise it waits. A link
   holding both waits, hidden, in the review queue's new `PICTURE_CHECKS` kind for an Admin
   (`REVIEW_CONTRIBUTIONS`). One account checks a link once (a partial unique index), each verdict
   counts against 60 `picture checks` an hour (`core/rate_limit`), and only an account with the work
   capability may check.
6. **An Admin reverses any verdict.** Approve or reject on the Review page, or staged over MCP with
   decision 0194's `review_queue` (which opens any checked link by its id) and `stage_reviews`, is a
   `ruling` check: approve shows the link as seen, reject hides it, a later ruling reverses an
   earlier one, and a ruled link takes no more checks. An Admin who checked the link does not rule
   on it. The staged item kind check is widened by migration `0119_picture_checks`.
7. **Served.** `served_picture` drops a refused link, so answers, the zoom story and uncurated craft
   pages stop showing it beside that fact, and an answer's stored pictures put a `VISION` link
   before a `TEXT` one. The craft page stamp counts refusals and `VISION` links, so a stored page is
   rebuilt, and a verdict or ruling that hides or marks a link refreshes the pages of its fact.

## Consequences

- Migration `0119_picture_checks` (parent `0118_removed`) adds `MediaRefClaim.id` (filled by
  `gen_random_uuid()`, unique) and `refusedAt`, the `PictureCheck` table with row level security,
  and `PICTURE_CHECKS` to the staged item kinds; the release before reads and writes every table
  (its inserts take the id's default), and the downgrade drops what it added and the staged items
  of the new kind.
- The web reads the new queue kind and staged kind with a card of the picture, its fact and every
  look; a release before it leaves them out of the Review page (`knownOnly`).
- Left, in the debt entry Relevance is by text only: a picture found for a new answer is unchecked
  until a client checks it; the 175 SearXNG links on hosts the picture fetch does not read cannot
  be offered; a stored answer keeps the pictures it was given.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/images/test_picture_checks.py`, `backend/tests/mcp/test_check_pictures_tool.py`,
`backend/tests/db/test_picture_checks_db.py`, `backend/tests/sources/test_commons_urls.py`,
`backend/tests/mcp/test_tool_budget.py` and `frontend/e2e/review-picture-checks-unit.spec.ts`.
