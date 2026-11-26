# 0241. Tasks that outlive a deploy, workbooks as they come, slots long enough for several files, and every upload scanned for malware

An MCP task is kept in the database, so a deploy no longer forgets it: the next process reads a task
the last one finished, and a task that was running when its process stopped is failed with a reason
to call the tool again. `propose_dataset` takes an `.xlsx` workbook as well as CSV and reads it into
the same table. A call that sends several files gets slots of 75 minutes. Every uploaded file is
scanned by ClamAV before anything reads it.

Date: 2026-11-26. Status: accepted (the lead's lane brief `mcp-extensions-2`, on the owner's word of
2026-11-26 that the MCP-extensions lane should leave no gaps). It amends
[decision 0235](0235-the-mcp-server-speaks-2026-07-28-with-skills-tasks-questions-and-files.md) (tasks
held in the API process, a spreadsheet only as CSV, a 30-minute slot for every file, no separate
malware scan: its four limits), [decision 0114](0114-kinds-and-datasets.md) (the dataset record gains
`sheet`; a table may come as a workbook) and
[decision 0104](0104-image-contributions-intake.md) (a picture is scanned before it is read byte by
byte). The contracts are `docs/contracts/open-work.md` (Protocol 2026-07-28: Tasks and Files),
`mcp-ask-and-upload.md` (Photographs sent as files), `nightly-upkeep.md` (The report) and
`infra.md` (the upload scanner).

| For | Read |
|---|---|
| The tasks, slots and files this extends | [decision 0235](0235-the-mcp-server-speaks-2026-07-28-with-skills-tasks-questions-and-files.md) |
| The dataset record and its table | [decision 0114](0114-kinds-and-datasets.md) |
| How a picture is read and screened | [decision 0104](0104-image-contributions-intake.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- Tasks lived in a dictionary of the API process. A deploy starts the new colour and stops the old
  one (`infra/deploy/blue_green.sh`), and the watchdog or the kernel's memory ceiling may stop a
  process at any time, so a client polling a long `preview_page` was told the task was unknown.
- `propose_dataset` read UTF-8 CSV only; a contributor with a workbook had to export it first and
  give the export's SHA-256.
- Anthropic's guide to files on a connector (claude.com/docs/connectors/building/files) asks an
  upload target to stay valid for 75 minutes when one call sends several files: the client uploads
  them one after another and may wait for the person between them. Every slot lasted 30 minutes.
- An upload passed its slot's own checks (types by their signatures, a PDF parsed for text, a
  picture screened and re-encoded, a table parsed), and none of them looks for malware.
- The box (read over SSM on 2026-11-26): a t3.large, 2 vCPUs, 7.8 GB of memory with 5.5 GB
  available and 2.3 GB used, 4 GB of swap with 141 MB used, 25 GB of disk free; the API slot held
  559 MB, the worker 238 MB, the fetcher 235 MB, the contributions process 191 MB, the renderer
  121 MB. ClamAV 1.5.4 is in Ubuntu 26.04's archive. clamd holds its signatures in memory, about
  1.0 to 1.4 GB, and by default loads a second copy beside the first while it reloads them.

## Decision

1. **Tasks in the database** (`McpTask`, migration `0123_mcp_tasks`; `services/mcp_task_store.py`;
   `api/mcp_tasks.py`). A row holds the task's id, its account, the tool, the canonical SHA-256 of
   its arguments (the digest `requestState` is bound to), its status, message, result or error, and
   when it was created, last updated, last heard from and expires. `McpTasks` keeps the extension's
   behaviour as decision 0235 set it (the statuses and their messages, `ttlMs` 5,400,000,
   `pollIntervalMs` 2,000, 32 tasks an account and 2,000 in all, `-32602` for a task that is not the
   account's or has expired, `-32603` for one that failed) over a `TaskStore` it is given; the
   database adapter is `SqlTaskStore`, a test's is held in memory. The runner stays in the process
   that started it and writes its end only while the row is still working, so the first end wins;
   while it runs it writes a heartbeat every 30 seconds, and stops itself when its row has ended
   elsewhere (a cancel read by another process). When the API stops, `McpTasks.close` fails every
   task it runs with "The server restarted or stopped while this task ran, so it never finished;
   call the tool again." and `-32603`, before the shielded work drains. A task still working whose
   heartbeat has been silent for 2 minutes and that no runner of the reading process holds is failed
   with the same reason when it is read, which covers a process the kernel or the watchdog killed.
   The nightly upkeep deletes expired tasks (`mcpTasks.expiredDeleted`; `mcpTasksExpired` in a dry
   run).
2. **Workbooks as they come** (`research/dataset_workbooks.py`, `openpyxl` 3.1.5 pinned). A file
   that starts with a zip's signature is read as an `.xlsx` workbook into the lines a CSV gives, then
   through the same table rules (a header row of distinct names, 1 to 20,000 rows, at most 60
   columns, cells of at most 500 characters, 5 MB). The sheet is the record's new `sheet` (at most
   31 characters, Excel's own bound; a sheet named for a CSV or a map layer is refused) or the first.
   The workbook is opened twice in read-only mode, once for the values Excel saved and once for the
   formulas, so a formula whose value was never saved is refused by its cell and formula, and an
   error value by its cell. Macros and controls are refused by their parts (`vbaProject.bin`, macro
   and dialog sheets, ActiveX) and a macro-enabled workbook by its content type. Values are written
   as a CSV export gives them: whole numbers without a decimal point, others to 15 significant
   digits, dates in ISO form, booleans `TRUE` and `FALSE`; empty trailing cells are dropped and short
   rows filled. The package may unpack to 64 MB and a sheet is read to row 100,000 at most. An
   OpenDocument spreadsheet is refused with the advice to save it as `.xlsx` or CSV: no maintained
   library reads both an ODS cell's saved value and its formula (odfpy, which pandas uses, was last
   released in 2020), and a reader of our own would be a second spreadsheet parser to keep.
   `openpyxl` is the maintained reader of the format, pure Python, with `et-xmlfile` its one
   dependency; its streamed sheets are parsed by the standard library's expat, which limits entity
   expansion, and its other parts by the lxml already installed, with entities left unresolved, so
   `defusedxml` is not added. It is imported only when a workbook is read, since it loads Pillow
   and the API loads no file library until a file is made (decision 0070's rule for exports).
3. **Slots long enough for several files** (`research/upload_links.slot_lifetime`). Each slot a
   `give_pictures` call opens for several photographs lasts 75 minutes (`SEVERAL_FILES_LIFETIME`), as
   the file guide asks; a single file's slot keeps 30 minutes, so a slot nobody fills still closes
   soon. `supply_source` and `propose_dataset` take one file each and keep 30 minutes. The
   `requestState` still expires 30 minutes after the latest slot.
4. **Every upload scanned** (`services/malware_scan.py`; `infra/deploy/install_scanner.sh`). ClamAV
   fits: about 1.3 GB beside the 2.3 GB in use leaves some 4 GB for a deploy's second API colour,
   the renderer's browser and the build, provided clamd never holds two copies, so it runs with
   `ConcurrentDatabaseReload no` (a reload pauses scans for its length instead) under `MemoryMax 2G`
   with `Restart=on-failure`. The deploy installs `clamav-daemon`, `clamav-freshclam` and
   `clamdscan` from Ubuntu's archive after the renderer's browser and before the build, waits for
   freshclam's first signatures, starts clamd and proves that a clean table passes and the EICAR test
   file is found; a failure is a warning, so the release goes on and uploads are refused until the
   scanner runs. freshclam's daemon looks for new signatures every hour (the package's 24 checks a
   day), so they are never more than a day old. The API sends the bytes to clamd's `INSTREAM`
   command over its socket (`MALWARE_SCAN_SOCKET`, by default `/var/run/clamav/clamd.ctl`, the
   package's own) in 64 KB chunks within 90 seconds; the protocol is a few lines, so no client
   library is added (the PyPI `clamd` was last released in 2015). The scan runs where each kind of
   upload is first read: `image_screens.screened` before a picture is decoded (a slot, the upload
   link's form, the site's own upload, a picture given in the call, an open-licence picture),
   `supplied_sources.fill_supplied_slot` before a PDF's or text's words are read, and
   `dataset_proposals.fill_dataset_slot` after the SHA-256 and before a table or GeoJSON layer is
   read. A found signature is refused by name (`The file was refused: the malware scan found
   Eicar-Test-Signature in it.` for the test file), 422 on a route and a tool error over MCP. A scanner that does not answer,
   runs out of time or cannot finish refuses the upload, 503 on the upload routes and a tool error
   over MCP, and the slot stays open for another try; nothing else calls the scanner, so every other
   path keeps working.
5. No user-interface change, so nothing here departs from the design skill.
6. One migration, `0123_mcp_tasks`, after `0121_coded_figures` (the lead relinks it behind the
   parallel `0122`), and one dependency, `openpyxl`.

## Consequences

- Tested in `backend/tests/mcp/test_mcp_task_restarts.py` (a finished task read by the next
  process, a running one failed when its process closes, a silent one failed after its heartbeat and
  not before, the running process keeping its own, a cancel from another process stopping the
  runner, tasks counted and kept to their account across processes, an expired one unknown),
  `test_mcp_tasks.py` (decision 0235's behaviour, unchanged, over the store),
  `backend/tests/db/test_mcp_task_store_db.py` (the store against Postgres, the first end winning,
  the counts, the upkeep's sweep, a restart both ways), `backend/tests/research/test_dataset_workbooks.py`
  (a sheet read into the table its CSV gives, the sheet by name or the first, macros, unsaved
  formulas, errors, width, rows, ODS and a plain zip refused), `backend/tests/db/test_upload_scans_db.py`
  (an `.xlsx` through the slot, EICAR refused and a down scanner refusing with the slot left open, for
  tables and supplied files), `backend/tests/mcp/test_upload_slot_lifetimes.py` (75 minutes for
  several photographs, 30 for one), `backend/tests/test_malware_scan.py` (the `INSTREAM` client
  against a stand-in clamd: a clean file whole in chunks, EICAR by its signature, an unfinished scan,
  no socket and silence failing closed; a picture scanned before it is decoded),
  `backend/tests/mcp/test_upload_scan_routes.py` (a down scanner refusing every upload route with 503
  and leaving others answering) and `backend/tests/deploy/test_scanner_install.py` (the deploy step,
  its settings and the runbook). Every test has a scripted scanner by default
  (`backend/tests/conftest.py`), since no test reaches the network or a daemon; the EICAR string is
  kept in two halves in the repository so a developer's own antivirus leaves the files alone.
- For the owner: the first deploy after this downloads about 300 MB of signatures and loads them,
  a few minutes; afterwards `systemctl status clamav-daemon` and `clamdscan --ping=1` show it.
- Left as they are: an OpenDocument spreadsheet is refused rather than read; voice and artisan
  recordings are not scanned, since no tool reads them as files (they go to speech-to-text), nor are
  the pictures the site's own searches find until a contributor gives one as an open-licence
  picture; a scan holds the whole file in memory, as the routes already do.

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
