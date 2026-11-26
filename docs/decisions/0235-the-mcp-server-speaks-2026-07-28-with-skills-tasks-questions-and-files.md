# 0235. The MCP server speaks protocol 2026-07-28: its skills listed as skills, long calls run as tasks, the person asked only what is theirs, and files sent out of band

A client on MCP protocol 2026-07-28 lists KalaVigyan's five skills as skills and loads them when a
contributor asks to build or deepen a page, propose facts or deliver a figure; a long call answers
with a task the client picks up later; the person is asked, in a form, only which craft and what
they want to give, whether to send a page, and the words of a source only they can open; and a PDF,
photograph or CSV goes to its tool without passing through the chat. A client on the 2025-11-25
handshake sees exactly what it saw before.

Date: 2026-11-26. Status: accepted (the lead's lane brief `mcp-extensions`, on the owner's word of
2026-11-26, pointing at Anthropic's article of 2026-11-24 on skills over MCP, tasks and elicitation,
that a contributor should "press allow and at most review", and asking for file uploads). It amends
[decision 0103](0103-mcp-server-read-slice.md) (our own JSON-RPC framing: it now also speaks the
2026-07-28 revision, without a handshake), [decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md)
(the skill, playbook, cookbook, design system and Ajrakh served as resources and guide pages: also as
skills) and [decision 0110](0110-contributor-supplied-sources.md) (a supplied source's words: also by
the person in a form, and its file out of band). The contracts are `docs/contracts/knowledge-api.md`
(The 2026-07-28 protocol and its extensions), `open-work.md` (Protocol 2026-07-28) and
`mcp-ask-and-upload.md` (Photographs sent as files).

| For | Read |
|---|---|
| The endpoint, framing and event stream it extends | [decision 0103](0103-mcp-server-read-slice.md) |
| The skill, references and guides it lists as skills | [decision 0230](0230-the-mcp-server-teaches-the-thinking-and-serves-the-context-the-authors-had.md) |
| Supplied sources and their slot | [decision 0110](0110-contributor-supplied-sources.md) |
| The run that watches a contributor's AI build a page | [decision 0234](0234-a-contributor-s-ai-builds-a-page-over-mcp-from-one-line-and-the-run-keeps-what-it-made.md) |
| A fourth question, asked after `stage_reviews` stores a batch: confirm all, some or none | [decision 0243](0243-a-staged-decision-confirmed-in-the-person-s-own-mcp-client.md) |
| Every decision, by group | [README.md](README.md) |

## Context

- The server spoke 2025-11-25, 2025-06-18 and 2025-03-26 and served the contributor skill, the
  playbook, the cookbook, the design system and Ajrakh as resources and guide pages only. A client
  reads them if it chooses; the agent that rebuilt Sanganeri Hand Block Printing did not.
- Skills over MCP (`io.modelcontextprotocol/skills`, SEP-2640), tasks (`io.modelcontextprotocol/tasks`)
  and file uploads (`io.modelcontextprotocol/files`, an experimental draft) are defined on protocol
  2026-07-28, and Claude Code uses each only on a 2026-07-28 connection (code.claude.com/docs/en/mcp:
  MCP skills, MCP tasks for server authors, elicitation modes). That revision has no `initialize`:
  each request carries its version, capabilities and client in `_meta`, mirrored into the
  `MCP-Protocol-Version`, `Mcp-Method` and `Mcp-Name` headers; elicitation returns as an
  `input_required` result the client answers on a retry with `requestState`; every result names its
  `resultType` and the cacheable ones their `ttlMs` and `cacheScope`.
- Agent Skills limit a description to 1,024 characters and require the name to be its folder's;
  the contributor's, datasets and interactives descriptions were 1,088 to 1,478.
- `preview_page` draws in a sandboxed browser and takes tens of seconds; Claude Code moves a plain
  call to the background after two minutes and reads a task's result by polling.
- Claude transfers files only for a Directory-listed connector whose hosts Anthropic has approved
  (claude.com/docs/connectors/building/files).

## Decision

1. **Both eras on one endpoint** (`api/mcp_meta.py`, `api/mcp_headers.py`, `api/mcp_modern.py`). A
   request carrying `io.modelcontextprotocol/protocolVersion: "2026-07-28"` in `_meta` is served
   under that revision; `initialize` keeps the 2025-11-25 handshake and never agrees 2026-07-28, so
   the MCP client check and every connected client are untouched. `server/discover`, `skills/*` and
   `tasks/*` answer only the new revision. An unknown version (header or `_meta`) is `-32022` with
   the supported versions, missing capabilities or a new-version header without the body field
   `-32602`, a missing or differing mirrored header `-32020` (a `=?base64?…?=` value decoded first),
   a missing capability `-32021`, each with 400 and before an event stream opens; an unknown method
   is `-32601` with 404, and a missing resource `-32602` in place of `-32002`. Results gain
   `resultType`, the server's `serverInfo` in `_meta`, and `ttlMs 300000` with `cacheScope` (private
   for `tools/list`, which depends on the connection, public for the rest). CORS and the site's proxy
   pass `Mcp-Method` and `Mcp-Name`.
2. **Five skills, one source** (`api/mcp_skills.py`). `skills/list` and `skills/get` serve
   `kalavigyan-contributor` (its SKILL.md and the eight references, the playbook and the cookbook
   among them), `kalavigyan-design` (with `SYSTEM.md`), `kalavigyan-interactives` (with its two
   references), `kalavigyan-datasets`, and `kalavigyan-ajrakh` (a SKILL.md of frontmatter, the bar
   and the chapter list, and each worked chapter). Every file is read by the same function as its
   resource or guide, so no copy can drift; manifests carry the SHA-256 and size of the bytes served;
   `resources/read` serves `skill://` uris; directory reading is not offered. The three long
   descriptions are cut under 1,024 characters in every copy, and the contributor's and Ajrakh's say
   to load them whenever someone asks to build or deepen a page, propose facts or deliver a figure.
   A frontmatter is plain `key: value` lines that a YAML reader reads the same, and the server
   refuses to serve one that is not. The resources and guides stay for clients without the
   extension, and the instructions say in one sentence that a skills client lists them.
3. **Long calls as tasks** (`api/mcp_tasks.py`, `api/mcp_calls.py`). `ask`, `search_sources`,
   `read_source`, `edit_draft`, `preview_page`, `propose_page`, `compose_component` and
   `give_pictures` answer a signed-in client that declares the extension with a task
   (`pollIntervalMs` 2,000, `ttlMs` 5,400,000: a half-hour run and an hour kept), run on its own
   session in the API process. `tasks/get` gives `working`, `completed` with the tool's result (a
   refusal as `isError`) or `failed` with `-32603`; `tasks/update` is acknowledged, since every
   question is settled before a task starts; `tasks/cancel` cancels. Only the account that started a
   task reads it; an account holds 32 and the process 2,000, past which the call is answered whole.
   An anonymous caller, a client without the extension and the old protocol get the answer itself.
4. **Questions only the person can answer** (`api/mcp_questions.py`, `api/mcp_input.py`,
   `api/mcp_state.py`). By form elicitation, through `input_required` and a `requestState` sealed
   with an HMAC under a key derived from `JWT_SECRET` and bound to the tool, a canonical digest of
   the arguments, the account and an hour: `edit_draft` with no page named asks which craft (by name,
   matched as `find_crafts` does) and which of five kinds of contribution; `propose_page` sending a
   whole page asks to send it now, showing its parts and the draft's private preview link with its
   expiry or that it has none; `supply_source` with no words asks for the source's words and where
   they stand. Nothing asks how to build anything. A client without form elicitation gets today's
   behaviour and today's refusals. The preview link sits in the form's message although the
   specification says a form should not carry a clickable link: the brief asks for it, it is the
   person's own private link, and the message is shown as text.
5. **Files out of band** (`api/mcp_files.py`, `api/mcp_picture_files.py`), behind
   `MCP_FILE_UPLOADS_ENABLED` (default true, so on in production; false takes the extension out of
   discovery and the tool list and refuses a file). Out of band only, with no inline bytes. To a
   declaring client the tool list adds `supply_source.file` (PDF or text, 20 MB),
   `give_pictures.files` (one photograph per `upload: true` picture, in order, 10 MB each, with the
   call's declaration and confirmation) and `propose_dataset.file` (CSV or GeoJSON, 5 MB, its digest
   held to the record's SHA-256); other clients see today's schemas. The first call runs every check
   that needs no bytes, opens today's single-use slot and answers `upload_required` with the slot's
   url on the API origin (`PUT`, `application/octet-stream`, `credentials: omit`) and a sealed
   `requestState` naming the slot's record and expiring half an hour after the slot. The bytes go
   through the same slot routes, so size, type, a PDF's text, a picture's screens and declaration
   and a table's SHA-256 all apply as before; the retry answers the tool's result once the record is
   filled, never a second upload request. A file the client did not declare `upload` for is
   `-32021`; inline bytes, an empty file, a repeated id or a type or size the tool does not take are
   refusals naming the reason.
6. No migration and no new dependency.

## Consequences

- Tested in `backend/tests/mcp/test_mcp_modern.py` (discovery, the old handshake, the errors and
  statuses, the headers, the result shapes), `test_mcp_skills.py` (the five skills listed, each
  file read back with its digest and size and equal to its resource or guide, the descriptions'
  triggers, the frontmatter reader), `test_mcp_tasks.py` (a result arriving by polling, clients
  without tasks answered whole, cancel, failure, one account's tasks only, a full store),
  `test_mcp_elicitation.py` (only the three decisions ask, each one's question and answers, old
  clients as before, a tampered or borrowed `requestState`) and `test_mcp_file_uploads.py` (a PDF, a
  photograph and a CSV each reaching its tool through its slot, refusals by type, size, inline bytes,
  emptiness and capability, the switch, old clients' slots), with `test_mcp_cors.py` and
  `frontend/e2e/api-proxy-unit.spec.ts`.
- For the owner: Claude sends files only to hosts Anthropic approved for a listed connector, so the
  API host needs approval by email before uploads reach it; MCP skills need Claude Code v2.1.331 or
  later, and a Team or Enterprise organisation turns on Skills over MCP.
- Left as they are: tasks live in the API process, so a restart or a deploy forgets them and the
  client is told the task is unknown, as the extension allows; the design skill's `SYSTEM.md`
  (126 KB) is over the 100 KB a scanned connector skill may hold per file; a spreadsheet goes as
  CSV, since the record's SHA-256 names the very file; a slot lasts 30 minutes where Claude asks 75
  for several targets; no separate malware scanner exists beyond the slots' own checks (types by
  their signatures, PDFs parsed for text, pictures screened and re-encoded).

## How this record is kept true

It is not edited after acceptance except to mark it superseded: a later choice is a new record that
names this one, and the table above links the two both ways. It records the choice as taken on
2026-11-26; what the code does today is in [ARCHITECTURE.md](../ARCHITECTURE.md) and the
[contracts](../contracts/README.md).
