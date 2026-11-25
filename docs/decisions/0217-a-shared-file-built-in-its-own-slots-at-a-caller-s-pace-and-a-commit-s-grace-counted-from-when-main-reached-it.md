# 0217. A shared answer or lesson file is built in its own slots at a caller's pace, and the hourly check counts a commit's grace from when main reached it

A shared answer's report and a shared lesson's files build in two slots of their own, wait at most
five seconds for one, count against the caller's ten builds in ten minutes with the page files, and
a file built while a picture was unread is used again for its hour. The post-deploy check's hourly
run counts the newest deployable commit's age from the newest run on main that holds it, not from
the commit's own date.

Date: 2026-11-25. Status: accepted (the lead's lane `exports-release` of the leftovers round of
2026-11-25: decision 0214's Left, and the debt entry "The scheduled post-deploy check counts its
grace from the commit's own date"). It amends
[decision 0214](0214-a-page-export-filed-once-built-in-its-own-slots-at-a-caller-s-pace-and-its-rebuild-queued.md)
(shared-file exports were left unchanged; its wait, retry and hour move to one home) and
[decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md) (one semaphore of two for answer,
lesson and shared files, and a file built while a picture was unread never reused). The contracts
are `docs/contracts/learning.md` (Exports, Share links), `docs/contracts/monograph-document.md`
(Exports) and `docs/contracts/infra.md` (CI).

| For | Read |
|---|---|
| The page files' slots, allowance and hour, which this amends and reuses | [decision 0214](0214-a-page-export-filed-once-built-in-its-own-slots-at-a-caller-s-pace-and-its-rebuild-queued.md) |
| The answer and lesson files, two builds at once, never reused when a picture was unread | [decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md), [decision 0067](0067-lessons-and-exports.md) |
| Share links and the files their readers are given | [decision 0097](0097-public-reading-everywhere-but-asking.md), [decision 0155](0155-accounts-and-sharing-kept-true.md) |
| Why a web build can start long after its push: the web build handed to Deploy backend | [decision 0173](0173-a-release-that-keeps-serving-and-its-way-back.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **Shared files built in the owners' slots, at no caller's pace.** `GET /api/shared/answers/{token}/pdf`
  and `GET /api/shared/lessons/{token}/files/{format}` are public reads. They built in the one
  `asyncio.Semaphore(2)` of `export_tools`, the slots every owner's answer report and lesson file
  builds in, queued with no wait, and counted nothing beyond the public read budget (900 reads in 10
  minutes per address, none for a signed-in account). A file built while one of its pictures could
  not be read was filed under its unread ids and never looked for again (decision 0143), so each
  request for such a share built the whole file. One caller with a few share tokens could keep both
  slots busy, and every owner's export waited behind it until the proxy gave up. Decision 0214 gave
  page files their own waited slots and a caller's allowance and left these two routes as they were.
- **A batch of older commits judged behind while its build ran.** The hourly run (`mode` `latest`)
  judged the newest deployable commit `building` only while it was younger than `GRACE_SECONDS`
  (90 minutes) by its committer date. The batch of 2026-11-25 was committed hours before its push:
  the run at 03:10:21Z on `2d7e7286` failed, although its Deploy web app run had started at 02:46:01Z
  and its Deploy backend, which builds the web once the API ships, only at 03:14:26Z. The debt
  entry's suggestion, `gh run list --commit <expected>`, finds nothing for most releases: a deploy
  run carries the head of the push, and the newest deployable commit is often not that head (for
  main at `12607d72`, a status-documents commit, it is the merge `d9eaacee`). A push that changes
  only the backend has no deploy run at all until its Backend checks pass, about half an hour.

## Decision

1. **Slots of their own.** `api/export_deps.shared_export_tools` hands both shared file routes a
   `WaitedSlots` of `SHARED_EXPORT_BUILDS_AT_ONCE` (2, `services/shared_files`) per process, apart
   from the owners' semaphore and the pages' slots. A request waits at most `BUILD_WAIT_SECONDS`
   (5 s) for one and is otherwise answered 503 with `Retry-After: 30` (`BuildsBusy`), so a share's
   readers can never keep an owner's export or a page's waiting. Two, as for pages: a lesson's
   readers ask for its deck, slides and handout together, and one slot would queue each behind the
   last one's pictures; the box's peak grows by two builds, as decision 0214's did.
2. **The caller's allowance, counted with the page files'.** The shared tools' `admit` is 0214's
   `build_admission` (`core/rate_limit.export_build_attempt`: 10 builds in 10 minutes per account
   when signed in, else per address), and `lesson_file_link` and `explainer_pdf_link` now give
   `tools.admit` to `stored_export_link`, which asks it only when the file is not yet filed and
   before a slot is taken. One count for page and shared builds, since both are a caller's builds on
   the same box; over it the route answers 429 with `Retry-After` (`BuildsSpent`). A file already
   filed is given whatever the slots and the count hold. The owners' routes give no admission
   (`export_tools`), so an owner's own files are never counted.
3. **A shared file built while a picture was unread is used again for its hour.** `ExportTools`
   carries `unread_reused_for`, none for the owners' tools (decision 0143's rule: the owner asks
   again to have the picture read again) and `UNREAD_REUSED_FOR` (one hour) for the shared tools,
   and the answer and lesson links file with it as a page file does. Without it the allowance would
   refuse a class: forty students behind one campus address reading a share whose picture cannot be
   read would build forty files and be refused from the eleventh; with it they are given one.
4. **One home for the rules of a file anyone may ask for.** `BUILD_WAIT_SECONDS` (5),
   `BUSY_RETRY_SECONDS` (30, beside `BUILDS_BUSY`, which says half a minute) and
   `UNREAD_REUSED_FOR` move from `page_export_files` (`PAGE_EXPORT_WAIT_SECONDS`,
   `PAGE_EXPORT_RETRY_SECONDS`, `PAGE_UNREAD_REUSED_FOR`) to `services/export_store`, beside
   `WaitedSlots`, and page and shared files import them from there. Each kind keeps its own slot
   count.
5. **A refusal is answered.** Both routes go through one `_shared_file` that returns
   `refused_export` (503 or 429 with `Retry-After`, as the page routes answer) and records the
   signed keys against the share only for a file it gives.
6. **A commit's age from when main reached it.** The verdict step of the `served` job is
   `.github/scripts/post_deploy_verdict.sh`, run with `GH_TOKEN` (the job already reads actions).
   In `latest` mode, when production answers but does not yet serve the newest deployable commit,
   its age is counted from the newest of the twenty newest runs on main of `Backend checks` (pushes
   only), `Deploy backend` and `Deploy web app` whose head holds it (`git merge-base
   --is-ancestor`), and it is `building` while that age is under `GRACE_SECONDS`. A run that holds
   it, not a run of it, because a run carries its push's head. `Backend checks`, because a backend
   push has no deploy run until its checks pass; a dispatched one deploys nothing and is not read.
   The newest run, because Deploy backend starts after its checks and builds the web at its end, so
   the grace counts from the start of the last run that can still be building it; a release takes
   at most 45 minutes (`RELEASE_SECONDS`), within the 90. When no run that holds it can be read, the
   age is counted from its commit date, as before; that date is never after its push, so the
   fallback can only judge `behind` sooner, never hide a build that failed. The other verdicts
   (`deploy` and `asked` modes, `served`, `silent`) are unchanged.

## Consequences

- The shared file routes answer 503 or 429 with `Retry-After` where they used to wait. The web's
  shared pages offer no download, so only a direct caller sees them.
- A shared file filed complete before this change keeps its key and is still given; one filed with
  its unread ids is never looked for again, as before, and the bucket's `expire-exports` rule removes
  it within seven days.
- A caller who started ten new page files in ten minutes is refused a new shared file for the rest
  of that window, and the reverse.
- `backend/tests/learning/test_share_links.py` overrides `shared_export_tools` beside
  `export_tools`, since the shared routes now depend on it, and
  `backend/tests/exports/test_page_export_routes.py` imports `BUSY_RETRY_SECONDS` from its new home.
- Backend checks run on a pull request that changes `.github/workflows/post-deploy.yml`, which a
  deploy test now reads (`test_watched_files`).
- The debt entry is deleted, and the register's count falls from 46 to 45. Nothing of either item is
  left.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/learning/test_shared_file_builds.py` (a full slot refused while an owner's file
builds, a filed file given whatever the slots hold, the allowance and its neighbour, one allowance
with the page files, the hour's reuse beside the owner's never),
`backend/tests/deploy/test_post_deploy_verdict.py` (a commit older than the grace pushed a minute
ago, a backend push, a run past the grace, runs that do not count, runs that cannot be read, the
other verdicts, the workflow's wiring and the workflows it names),
`backend/tests/learning/test_share_links.py` and `backend/tests/contracts/test_watched_files.py`.
