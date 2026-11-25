# 0214. A page export is filed once by what it is made from, built in its own slots at a pace each caller is held to, and the rebuild its read claims is queued as a page read's is

A page's PDF or Word file is filed under what it is made from alone, and only its download name
carries the day. A file built while a picture could not be read is used again for the hour it was
built in. Each picture is given its own time. Page exports build in two slots of their own and wait
at most five seconds for one. A caller may start ten builds in ten minutes. The export routes queue
the rebuild their read claims, as the page routes do, whatever the export answers.

Date: 2026-11-25. Status: accepted (the lead's lane `exports` of the review fixes of 2026-11-25,
findings `documents-exports-3` and `documents-exports-4` of the adversarial review of the quality
round). It amends
[decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) (the
key: "filed once per served tag" had the day in it),
[decision 0208](0208-every-page-downloaded-from-the-page-with-its-pictures-and-its-words.md) (a
page file built while a picture was unread, and one deadline for all of a page's pictures) and
[decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md) (one semaphore of two builds per
process: page exports now have their own). The contracts are `docs/contracts/monograph-document.md`
(Exports, Pictures on paper), `docs/contracts/page-layout.md` (Routes) and
`docs/contracts/learning.md` (Exports).

| For | Read |
|---|---|
| The page export, its key and its name, which this amends | [decision 0206](0206-every-new-kind-exported-as-its-still-and-read-in-a-page-s-languages.md) |
| The pictures on paper and the family and category routes, which this amends | [decision 0208](0208-every-page-downloaded-from-the-page-with-its-pictures-and-its-words.md) |
| The answer and lesson files, never reused when a picture was unread, two builds at once | [decision 0143](0143-lessons-exports-and-follow-ups-kept-true.md), [decision 0067](0067-lessons-and-exports.md) |
| How a read claims a stale page's rebuild and queues it | [decision 0190](0190-a-voice-turn-bound-and-answered-and-a-page-built-while-its-inputs-move.md), [decision 0186](0186-pages-rebuilt-by-the-release-that-serves-and-a-deploy-that-never-goes-back.md) |
| The shared sliding limits every allowance is counted by | [decision 0139](0139-sources-and-providers-reach-outside-services-once.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- **One caller could keep the box building (`documents-exports-3`).** The public export routes
  (`GET /api/crafts|families|categories/{slug}/monograph/{pdf|docx}`) looked for a file at
  `export_key(owner, sha256 of what it is made from, file name)`, and the file name carries the
  day (`page_file_name(..., made_at=tools.clock())`), so every page, format, language and kept
  version was built again each day. A build with any unread picture was filed under the hash of
  its inputs and the unread ids (`key_without`), which `key()` never looks for, so a page with a
  picture that cannot be read (a deleted Commons file, a removed contribution in a kept version)
  was built in full on every request. The page's pictures were read one after another within one
  30-second deadline, so one slow first picture left the rest unread. Every build queued with no
  wait on the one `asyncio.Semaphore(2)` that answer report, lesson and shared-file exports also
  use, and the routes counted nothing beyond the public read budget (900 reads in 10 minutes per
  address, none for a signed-in account).
- **The export read claimed the rebuild and dropped it (`documents-exports-4`).** All three routes
  reach `read_generated`, which commits the page's rebuild claim (`wantedAt`) when its copy is
  stale. The page routes then queue `rebuild_wanted` (`queue_rebuild`); the export routes took no
  `BackgroundTasks` and ignored `served.rebuild`. For `REBUILD_RETRY` (10 minutes) no later read
  could claim it, so readers and exports were served the stale copy, removed content included.

## Decision

1. **Filed by what it is made from.** A page file is filed at
   `exports/<page owner>/<sha256 of what it is made from>/<stored name>`, the stored name the
   export's name without its day (`KalaVigyan_Craft-Page_<page>[_<language>]_Export_v<n>.<fmt>`,
   `naming.export_file_name(made_at=None)`, which leaves the Date field out as the naming rule
   does for an unknown field). The download name (the link's `fileName` and its
   `Content-Disposition`) keeps the day it is downloaded, so a reader's file is still named for
   its day while every reader on every day is given one file. `ExportFile.stored_name` holds the
   key's leaf; answer and lesson files leave it out, since their names carry their pack's or
   version's own day. The craft route keeps `version`: each kept version is a different document,
   filed once like any other, and what a dropped version answers belongs to the lane that drops
   versions (decision 0213's).
2. **A file built while a picture was unread is used again for its hour.** With
   `ExportFile.unread_reused_for` (`PAGE_UNREAD_REUSED_FOR`, one hour) such a file is filed under
   the hash of its inputs and the start of the clock hour it was built in (`unreadFrom`), and a
   request looks for it after the complete file. A page whose picture cannot be read is therefore
   built at most once an hour per file, and the first build that reads every picture is filed under
   the complete key and served from then on. An hour in the key, rather than the file's age, needs
   only the bucket's `exists`. Answer and lesson files keep decision 0143's rule (never reused):
   their owner asks again to have the picture read again, and they are not anonymous.
3. **Each picture its own time.** `export_pictures` reads at most `PICTURE_READS_AT_ONCE` (4)
   pictures at once, each within `within` seconds of its own read (`PAGE_PICTURE_SECONDS`, 10 s for a
   page; lessons and answers give none, as before), and flattens them one at a time, since a
   picture of 40 megapixels is 160 MB as RGBA. Ten pictures that all stall take 30 s, as the page's
   one deadline did, and a slow picture no longer leaves the others unread.
4. **Slots of their own, and a short wait.** Page exports build under `WaitedSlots`
   (`PAGE_EXPORT_BUILDS_AT_ONCE`, 2, in `api/export_deps`), apart from the semaphore answer,
   lesson and shared-file exports keep. A request waits at most `PAGE_EXPORT_WAIT_SECONDS` (5 s)
   for a slot and is otherwise answered 503 with `Retry-After: 30` (`BuildsBusy`), so page exports
   can never keep an answer or lesson export waiting, and a reader is told to come back rather
   than held until the proxy gives up. `WaitedSlots` is an `asyncio.Semaphore` whose entry waits a
   bounded time, so `stored_export_link` takes either.
5. **A caller's builds are counted.** `core/rate_limit.export_build_attempt(connection, reader)`
   allows `EXPORT_BUILDS_PER_WINDOW` (10) builds in `EXPORT_BUILD_WINDOW_SECONDS` (10 minutes) per
   account when the reader is signed in, else per `client_ip`, counted by the same shared
   `take_sliding` as every other limit (decision 0139); `api/export_deps.page_export_tools` hands it
   to the export as its `admit`. `stored_export_link` asks it only when the file is not yet filed
   and before a slot is taken, so a file already filed is never refused, a campus downloading the
   page its teacher opened counts one build, and a refused caller never holds a slot. Ten is five
   pages' first PDF and Word document; over it the route answers 429 with `Retry-After`
   (`BuildsSpent`). A count that cannot be read refuses, as every limit does.
6. **The claimed rebuild is queued.** The three routes take `BackgroundTasks` and call
   `queue_rebuild(background, served)` before filing, as the page routes do. The route answers a
   busy slot, a spent allowance and a bucket or settings failure (503 `This file can't be made right
   now.`, as the answer and lesson routes do) as a response it returns, never an exception, because
   FastAPI runs a request's background tasks only with the response its handler returns: the
   rebuild is queued whatever the export answers.

## Consequences

- Page files filed before this change, under dated names, are never looked for again; the bucket's
  `expire-exports` rule removes them within seven days, and each page's first download after the
  release builds once.
- `test_a_page_export_is_filed_once_under_its_page_and_named_by_the_naming_rule` asserted that the
  key ends with the download name, the rule this record removes; it now asserts the key ends with
  the stored name and the signed link's disposition carries the dated name.
- The page export routes answer a bucket failure 503 where they answered 500.
- Answer, lesson and shared-file exports are unchanged: one queue of two with no wait (decision
  0143), each asked by its owner or a share token's reader.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-25; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md). Its rules are tested by
`backend/tests/exports/test_page_export_routes.py` (the rebuild queued, the busy slot beside an
answer export, the build allowance), `backend/tests/exports/test_page_files.py` (one file over two
days), `backend/tests/exports/test_page_pictures.py` (each picture its own time),
`backend/tests/learning/test_export_store.py` (the hour's reuse, the wait, the admission, the
golden names and keys) and `backend/tests/db/test_page_exports_db.py`.
